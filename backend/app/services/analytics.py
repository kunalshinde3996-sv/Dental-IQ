"""Population oral-health analytics.

All figures are computed from DB queries at request time. A filtered set of case and
patient facts is loaded once, then every section is aggregated from that same
in-memory dataset, so the numbers on the dashboard are mutually consistent.

Scope: cases with status *submitted* or *approved* (drafts are incomplete and rejected cases
failed faculty validation). A patient counts as "having" a condition if any in-scope case
records it.
"""
from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlmodel import Session, select

from app.models import Case, Patient, ToothFinding
from app.models.enums import CaseStatus, Department, HabitStatus, Sex, Taluka
from app.services.clinical_terms import CATEGORY_LABELS, categorize

IN_SCOPE_STATUSES = (CaseStatus.submitted, CaseStatus.approved)

AGE_BANDS: list[tuple[str, int, int]] = [
    ("5-12", 0, 12), ("13-17", 13, 17), ("18-34", 18, 34), ("35-49", 35, 49), ("50-64", 50, 64), ("65+", 65, 200),
]
TALUKA_CONDITIONS = ("caries", "periodontal", "pmd", "oral_lesion", "edentulism")
HABIT_OUTCOMES = ("osmf", "leukoplakia", "pmd", "oral_lesion")
HABITS: dict[str, str] = {
    "smokeless_tobacco": "Gutkha / smokeless tobacco",
    "tobacco_smoking": "Smoking",
    "alcohol": "Alcohol",
    "any_tobacco": "Any tobacco",
}
# Minimum group sizes before a number is reported in an insight.
MIN_GROUP = 12


# --------------------------------------------------------------------------- dataset

@dataclass
class Filters:
    date_from: date | None = None
    date_to: date | None = None
    taluka: Taluka | None = None
    department: Department | None = None


@dataclass
class CaseFact:
    id: int
    patient_id: int
    department: Department
    visit_date: date
    diagnosis: str | None
    procedure: str | None
    categories: set[str] = field(default_factory=set)


@dataclass
class PatientFact:
    id: int
    age: int
    sex: Sex
    taluka: Taluka
    smoking: HabitStatus
    smokeless: HabitStatus
    alcohol: HabitStatus
    has_abha: bool
    categories: set[str] = field(default_factory=set)

    def habit(self, name: str) -> bool:
        """'Ever' exposure (current or former)."""
        if name == "any_tobacco":
            return self.smokeless != HabitStatus.never or self.smoking != HabitStatus.never
        value = {"smokeless_tobacco": self.smokeless, "tobacco_smoking": self.smoking, "alcohol": self.alcohol}[name]
        return value != HabitStatus.never


@dataclass
class PopulationDataset:
    cases: list[CaseFact]
    patients: dict[int, PatientFact]

    @property
    def adults(self) -> list[PatientFact]:
        return [p for p in self.patients.values() if p.age >= 18]


def _where(filters: Filters) -> list:
    clauses = [Case.status.in_(IN_SCOPE_STATUSES)]
    if filters.date_from:
        clauses.append(Case.visit_date >= filters.date_from)
    if filters.date_to:
        clauses.append(Case.visit_date <= filters.date_to)
    if filters.taluka:
        clauses.append(Patient.taluka == filters.taluka)
    if filters.department:
        clauses.append(Case.department == filters.department)
    return clauses


def load_dataset(session: Session, filters: Filters) -> PopulationDataset:
    where = _where(filters)
    rows = session.exec(
        select(Case.id, Case.patient_id, Case.department, Case.visit_date, Case.diagnosis, Case.procedure, Patient)
        .join(Patient, Patient.id == Case.patient_id)
        .where(*where)
    ).all()
    conditions: dict[int, list] = defaultdict(list)
    for case_id, condition in session.exec(
        select(ToothFinding.case_id, ToothFinding.condition)
        .join(Case, Case.id == ToothFinding.case_id)
        .join(Patient, Patient.id == Case.patient_id)
        .where(*where)
    ).all():
        conditions[case_id].append(condition)

    cases: list[CaseFact] = []
    patients: dict[int, PatientFact] = {}
    for case_id, patient_id, dept, visit, diagnosis, procedure, p in rows:
        cats = categorize(diagnosis, conditions.get(case_id, ()))
        cases.append(CaseFact(case_id, patient_id, dept, visit, diagnosis, procedure, cats))
        fact = patients.get(patient_id)
        if fact is None:
            fact = patients[patient_id] = PatientFact(
                p.id, p.age, p.sex, p.taluka, p.tobacco_smoking, p.smokeless_tobacco, p.alcohol, bool(p.abha_id)
            )
        fact.categories |= cats
    return PopulationDataset(cases, patients)


# --------------------------------------------------------------------------- helpers

def pct(n: int, d: int) -> float:
    return round(n / d * 100, 1) if d else 0.0


def prevalence_ratio(a: int, n1: int, c: int, n0: int) -> tuple[float | None, float | None, float | None]:
    """PR = (a/n1)/(c/n0) with a 95% CI on the log scale. None when undefined (zero cells)."""
    if not (a and c and n1 and n0):
        return None, None, None
    pr = (a / n1) / (c / n0)
    se = math.sqrt(1 / a - 1 / n1 + 1 / c - 1 / n0)
    return round(pr, 2), round(math.exp(math.log(pr) - 1.96 * se), 2), round(math.exp(math.log(pr) + 1.96 * se), 2)


def age_band(age: int) -> str:
    return next(label for label, lo, hi in AGE_BANDS if lo <= age <= hi)


# --------------------------------------------------------------------------- sections

def summary(ds: PopulationDataset) -> dict:
    adults = ds.adults
    current_tobacco = [p for p in adults if HabitStatus.current in (p.smokeless, p.smoking)]
    return {
        "patients": len(ds.patients),
        "cases": len(ds.cases),
        "pmd_patients": sum("pmd" in p.categories for p in ds.patients.values()),
        "caries_patients": sum("caries" in p.categories for p in ds.patients.values()),
        "abha_linked_pct": pct(sum(p.has_abha for p in ds.patients.values()), len(ds.patients)),
        "adult_current_tobacco_pct": pct(len(current_tobacco), len(adults)),
    }


def taluka_burden(ds: PopulationDataset) -> list[dict]:
    by_taluka: dict[Taluka, list[PatientFact]] = defaultdict(list)
    for p in ds.patients.values():
        by_taluka[p.taluka].append(p)
    rows = []
    for taluka in Taluka:
        group = by_taluka.get(taluka, [])
        counts = {c: sum(c in p.categories for p in group) for c in TALUKA_CONDITIONS}
        rows.append({
            "taluka": taluka,
            "patients": len(group),
            "cases": sum(1 for c in ds.cases if ds.patients[c.patient_id].taluka == taluka),
            "counts": counts,
            "prevalence_pct": {c: pct(n, len(group)) for c, n in counts.items()},
        })
    return sorted(rows, key=lambda r: -r["patients"])


def habit_associations(ds: PopulationDataset, people: list[PatientFact] | None = None) -> list[dict]:
    """Prevalence of each outcome among adults ever exposed vs never exposed to each habit."""
    people = ds.adults if people is None else people
    rows = []
    for habit, habit_label in HABITS.items():
        exposed = [p for p in people if p.habit(habit)]
        unexposed = [p for p in people if not p.habit(habit)]
        for outcome in HABIT_OUTCOMES:
            a = sum(outcome in p.categories for p in exposed)
            c = sum(outcome in p.categories for p in unexposed)
            pr, lo, hi = prevalence_ratio(a, len(exposed), c, len(unexposed))
            rows.append({
                "habit": habit, "habit_label": habit_label, "outcome": outcome,
                "outcome_label": CATEGORY_LABELS[outcome],
                "exposed_n": len(exposed), "exposed_cases": a, "exposed_pct": pct(a, len(exposed)),
                "unexposed_n": len(unexposed), "unexposed_cases": c, "unexposed_pct": pct(c, len(unexposed)),
                "prevalence_ratio": pr, "ci_low": lo, "ci_high": hi,
            })
    return rows


def caries_by_age_sex(ds: PopulationDataset) -> list[dict]:
    rows = []
    for label, _lo, _hi in AGE_BANDS:
        row: dict = {"age_group": label}
        for sex in (Sex.male, Sex.female):
            group = [p for p in ds.patients.values() if age_band(p.age) == label and p.sex == sex]
            n = sum("caries" in p.categories for p in group)
            row[sex.value] = {"patients": len(group), "caries": n, "pct": pct(n, len(group))}
        rows.append(row)
    return rows


def monthly_trend(ds: PopulationDataset) -> list[dict]:
    counts: dict[str, Counter] = defaultdict(Counter)
    for c in ds.cases:
        counts[c.visit_date.strftime("%Y-%m")][c.department] += 1
    if not counts:
        return []
    months = sorted(counts)
    # Fill gaps so the x-axis is continuous.
    y, m = map(int, months[0].split("-"))
    end = months[-1]
    filled = []
    while True:
        key = f"{y:04d}-{m:02d}"
        filled.append({"month": key, "total": sum(counts[key].values()),
                       **{d.value: counts[key].get(d, 0) for d in Department}})
        if key == end:
            break
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return filled


def top_terms(ds: PopulationDataset, limit: int = 10) -> dict:
    def top(values: list[str | None]) -> list[dict]:
        clean = [v.strip() for v in values if v and v.strip()]
        total = len(clean)
        return [{"term": t, "count": n, "pct": pct(n, total)} for t, n in Counter(clean).most_common(limit)]

    return {"diagnoses": top([c.diagnosis for c in ds.cases]), "procedures": top([c.procedure for c in ds.cases])}


# --------------------------------------------------------------------------- insights

def _fmt_pr(pr: float) -> str:
    return f"{pr:.1f}x"


def key_insights(ds: PopulationDataset, today: date | None = None) -> list[dict]:
    """Plain-language findings generated from the dataset. Each insight carries its evidence."""
    today = today or date.today()
    insights: list[dict] = []
    if not ds.patients:
        return insights

    # 1. Strongest habit-outcome association overall (PMD-type outcomes only).
    assoc = [r for r in habit_associations(ds) if r["prevalence_ratio"] and r["exposed_cases"] >= 5
             and r["outcome"] in ("osmf", "leukoplakia", "pmd")]
    if assoc:
        # Rank by the CI lower bound: the most *robust* association, not the noisiest large ratio.
        best = max(assoc, key=lambda r: r["ci_low"])
        insights.append({
            "id": "habit-association", "tone": "critical",
            "title": f"{best['habit_label']} strongly linked to {best['outcome_label'].split(' (')[0].lower()}",
            "text": (f"Adults who use or used {best['habit_label'].lower()} show {_fmt_pr(best['prevalence_ratio'])} "
                     f"higher prevalence of {best['outcome_label'].split(' (')[0].lower()} than non-users "
                     f"({best['exposed_pct']}% of {best['exposed_n']} vs {best['unexposed_pct']}% of "
                     f"{best['unexposed_n']}; 95% CI {best['ci_low']}-{best['ci_high']})."),
            "action": "Prioritise tobacco-cessation counselling and mucosal screening for every habit-positive patient.",
            "evidence": best,
        })

    # 2. Same association inside individual talukas (where groups are large enough).
    by_taluka: dict[Taluka, list[PatientFact]] = defaultdict(list)
    for p in ds.adults:
        by_taluka[p.taluka].append(p)
    local = []
    for taluka, people in by_taluka.items():
        for r in habit_associations(ds, people):
            if (r["habit"] == "any_tobacco" and r["outcome"] == "pmd" and r["prevalence_ratio"]
                    and r["exposed_n"] >= MIN_GROUP and r["unexposed_n"] >= MIN_GROUP):
                local.append((taluka, r))
    if local:
        taluka, r = max(local, key=lambda t: t[1]["ci_low"])
        insights.append({
            "id": "taluka-habit", "tone": "warning",
            "title": f"Tobacco risk is sharpest in {taluka.value.title()}",
            "text": (f"Tobacco users in {taluka.value.title()} show {_fmt_pr(r['prevalence_ratio'])} higher prevalence "
                     f"of potentially malignant disorders than non-users ({r['exposed_pct']}% of {r['exposed_n']} "
                     f"vs {r['unexposed_pct']}% of {r['unexposed_n']})."),
            "action": f"Consider a tobacco-cessation and oral-screening camp in {taluka.value.title()}.",
            "evidence": {"taluka": taluka, **r},
        })

    # 3. Taluka with the highest PMD burden.
    burden = [r for r in taluka_burden(ds) if r["patients"] >= MIN_GROUP * 2]
    if burden:
        top = max(burden, key=lambda r: r["prevalence_pct"]["pmd"])
        overall = pct(sum("pmd" in p.categories for p in ds.patients.values()), len(ds.patients))
        if top["prevalence_pct"]["pmd"] > overall:
            insights.append({
                "id": "taluka-burden", "tone": "warning",
                "title": f"Highest PMD burden: {top['taluka'].value.title()}",
                "text": (f"{top['prevalence_pct']['pmd']}% of {top['patients']} patients from "
                         f"{top['taluka'].value.title()} have a potentially malignant disorder, against "
                         f"{overall}% across all talukas in scope."),
                "action": "Target outreach screening and early referral pathways to this taluka.",
                "evidence": {"taluka": top["taluka"], "prevalence_pct": top["prevalence_pct"]["pmd"],
                             "patients": top["patients"], "overall_pct": overall},
            })

    # 4. Caries peak by age band.
    caries_rows = []
    for row in caries_by_age_sex(ds):
        n = row["male"]["patients"] + row["female"]["patients"]
        k = row["male"]["caries"] + row["female"]["caries"]
        if n >= MIN_GROUP:
            caries_rows.append((row["age_group"], pct(k, n), n))
    overall_caries = pct(sum("caries" in p.categories for p in ds.patients.values()), len(ds.patients))
    if caries_rows:
        low = min(caries_rows, key=lambda t: t[1])
        high = max(caries_rows, key=lambda t: t[1])
        if high[1] - low[1] < 5:
            insights.append({
                "id": "caries-age", "tone": "info",
                "title": f"Caries is widespread across age groups ({overall_caries}%)",
                "text": (f"{overall_caries}% of {len(ds.patients)} patients have dental caries; every age group with "
                         f"at least {MIN_GROUP} patients lies between {low[1]}% and {high[1]}%."),
                "action": "Population-wide prevention: fluoride, diet counselling and recall at every visit.",
                "evidence": {"overall_pct": overall_caries, "by_age": caries_rows},
            })
        else:
            insights.append({
                "id": "caries-age", "tone": "info",
                "title": f"Caries burden is highest at {high[0]} years",
                "text": (f"Caries ranges from {low[1]}% of patients aged {low[0]} (n={low[2]}) to {high[1]}% of those "
                         f"aged {high[0]} (n={high[2]}); {overall_caries}% overall."),
                "action": ("School-based sealant and fluoride programmes." if high[0] in ("5-12", "13-17")
                           else "Prioritise restorative capacity and preventive recall for this age group."),
                "evidence": {"lowest": low, "highest": high, "overall_pct": overall_caries, "by_age": caries_rows},
            })

    # 5. Department demand shift: last 30 days vs the 30 before.
    recent_start, prior_start = today - timedelta(days=30), today - timedelta(days=60)
    recent = Counter(c.department for c in ds.cases if recent_start < c.visit_date <= today)
    prior = Counter(c.department for c in ds.cases if prior_start < c.visit_date <= recent_start)
    changes = [(d, recent[d], prior[d], (recent[d] - prior[d]) / prior[d] * 100)
               for d in Department if prior[d] >= 10]
    if changes:
        d, r, p, change = max(changes, key=lambda t: abs(t[3]))
        if abs(change) >= 15:
            name = d.value.replace("_", " ").title()
            insights.append({
                "id": "department-trend", "tone": "info",
                "title": f"{name} demand {'up' if change > 0 else 'down'} {abs(change):.0f}%",
                "text": f"{name} saw {r} cases in the last 30 days versus {p} in the previous 30 days.",
                "action": ("Review chair and faculty allocation for this department." if change > 0
                           else "Spare capacity: route quota-short students here."),
                "evidence": {"department": d, "recent": r, "prior": p, "change_pct": round(change, 1)},
            })

    # 6. Tobacco burden + ABHA readiness.
    s = summary(ds)
    insights.append({
        "id": "tobacco-burden", "tone": "info",
        "title": f"{s['adult_current_tobacco_pct']}% of adult patients currently use tobacco",
        "text": (f"{s['adult_current_tobacco_pct']}% of {len(ds.adults)} adult patients report current smoking or "
                 f"smokeless-tobacco use. {s['abha_linked_pct']}% of patients in scope have an ABHA number linked."),
        "action": "Record habit status at every visit; link ABHA to enable longitudinal follow-up.",
        "evidence": {"adult_current_tobacco_pct": s["adult_current_tobacco_pct"], "adults": len(ds.adults),
                     "abha_linked_pct": s["abha_linked_pct"]},
    })
    return insights


def population_report(session: Session, filters: Filters) -> dict:
    ds = load_dataset(session, filters)
    return {
        "filters": filters.__dict__,
        "summary": summary(ds),
        "taluka_burden": taluka_burden(ds),
        "habit_associations": habit_associations(ds),
        "caries_by_age_sex": caries_by_age_sex(ds),
        "monthly_trend": monthly_trend(ds),
        "top_terms": top_terms(ds),
        "insights": key_insights(ds),
        "condition_labels": CATEGORY_LABELS,
    }
