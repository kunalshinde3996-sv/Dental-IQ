"""Explainable at-risk student alerts: transparent rules + a logistic-regression score.

Signals (per student, as of a given day):
  attendance %          last 12 weeks; trend = last 4 weeks minus weeks 5-12
  marks average %       all assessments; trend = latest minus first exam, averaged over subjects
  quota pace            overall quota progress / cohort median progress for the same year (clinical years)
  rejection rate        rejected / reviewed cases (needs >= 5 reviewed)

Rules produce human-readable REASONS and SUGGESTED ACTIONS. The model produces a continuous score
(trained by weak supervision on the critical rules, because no historical outcome labels exist yet)
and per-signal contributions. The final alert level is a hybrid of both.
"""
from __future__ import annotations

import json
import math
import statistics
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone

import numpy as np
from sklearn.linear_model import LogisticRegression
from sqlalchemy import func
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sqlmodel import Session, select

from app.core.config import artifact_dir
from app.models import Assessment, Attendance, Case, Student, User
from app.models.enums import CLINICAL_YEARS, AttendanceStatus, CaseStatus, Department
from app.services.academic_policy import ATTENDANCE_MIN_PCT, ATTENDANCE_WINDOW_DAYS
from app.services.quota import student_quota_progress
from ml.common import load_bundle, save_bundle

MODEL_NAME = "student_risk"
DEPT_SHORT = {
    Department.oral_medicine: "Oral Medicine", Department.conservative: "Conservative",
    Department.endodontics: "Endo", Department.periodontics: "Perio", Department.prosthodontics: "Prostho",
    Department.oral_surgery: "Oral Surgery", Department.pedodontics: "Pedo", Department.orthodontics: "Ortho",
}

# Thresholds (documented in docs/ml-report.md)
ATT_MIN = ATTENDANCE_MIN_PCT  # DCI attendance requirement
ATT_DROP = 10.0
MARKS_PASS = 50.0
MARKS_DROP = 8.0
PACE_CRITICAL = 0.6
PACE_WARNING = 0.8
REJECT_RATE = 0.20
MIN_REVIEWED = 5
HIGH_SCORE, MEDIUM_SCORE = 0.8, 0.5

MODEL_FEATURES: list[tuple[str, str]] = [
    ("attendance_pct", "Attendance %"),
    ("attendance_trend", "Attendance trend (last 4 weeks)"),
    ("marks_avg", "Marks average %"),
    ("marks_trend", "Marks trend"),
    ("pace_ratio", "Clinical quota pace vs cohort"),
    ("rejection_rate", "Case rejection rate"),
]
# Neutral values for students without that signal (pre-clinical / interns without marks).
IMPUTE = {"marks_avg": 65.0, "marks_trend": 0.0, "pace_ratio": 1.0, "rejection_rate": 0.05}


# --------------------------------------------------------------------------- signals

@dataclass
class Flag:
    code: str
    severity: str  # critical | warning
    reason: str
    action: str


@dataclass
class StudentSignals:
    student_id: int
    name: str
    roll_no: str
    year: str
    attendance_pct: float | None = None
    attendance_recent_pct: float | None = None
    attendance_prior_pct: float | None = None
    attendance_trend: float | None = None
    attendance_sessions: int = 0
    attendance_attended: int = 0
    marks_avg: float | None = None
    marks_trend: float | None = None
    weakest_subject: str | None = None
    weakest_subject_pct: float | None = None
    is_clinical: bool = False
    quota_percent: float | None = None
    cohort_median_percent: float | None = None
    pace_ratio: float | None = None
    quota_gaps: list[dict] = field(default_factory=list)  # [{department, approved, required, remaining}]
    reviewed_cases: int = 0
    rejected_cases: int = 0
    rejection_rate: float | None = None
    weekly_attendance: list[dict] = field(default_factory=list)

    def model_vector(self) -> list[float]:
        out = []
        for name, _ in MODEL_FEATURES:
            v = getattr(self, name)
            out.append(IMPUTE.get(name, 0.0) if v is None else float(v))
        return out


def _pct(n: int, d: int) -> float | None:
    return round(n / d * 100, 1) if d else None


def compute_signals(session: Session, as_of: date | None = None) -> dict[int, StudentSignals]:
    today = as_of or date.today()
    start, recent_start = today - timedelta(days=ATTENDANCE_WINDOW_DAYS), today - timedelta(days=28)
    students = session.exec(select(Student, User).join(User, User.id == Student.user_id)).all()
    sig = {s.id: StudentSignals(s.id, u.name, s.roll_no, s.year.value, is_clinical=s.year in CLINICAL_YEARS)
           for s, u in students}

    # Attendance (excused sessions are excluded from the denominator).
    counts: dict[int, dict[str, list[int]]] = defaultdict(lambda: {"all": [0, 0], "recent": [0, 0], "prior": [0, 0]})
    weekly: dict[int, dict[int, list[int]]] = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for sid, day, st in session.exec(
        select(Attendance.student_id, Attendance.date, Attendance.status)
        .where(Attendance.date > start, Attendance.date <= today)
    ).all():
        if st == AttendanceStatus.excused:
            continue
        hit = int(st in (AttendanceStatus.present, AttendanceStatus.late))
        bucket = "recent" if day > recent_start else "prior"
        for key in ("all", bucket):
            counts[sid][key][0] += hit
            counts[sid][key][1] += 1
        week = (today - day).days // 7
        weekly[sid][week][0] += hit
        weekly[sid][week][1] += 1
    for sid, c in counts.items():
        s = sig[sid]
        s.attendance_attended, s.attendance_sessions = c["all"]
        s.attendance_pct = _pct(*c["all"])
        s.attendance_recent_pct = _pct(*c["recent"])
        s.attendance_prior_pct = _pct(*c["prior"])
        if s.attendance_recent_pct is not None and s.attendance_prior_pct is not None:
            s.attendance_trend = round(s.attendance_recent_pct - s.attendance_prior_pct, 1)
        s.weekly_attendance = [
            {"weeks_ago": w, "pct": _pct(*weekly[sid][w])} for w in sorted(weekly[sid], reverse=True)
        ]

    # Marks
    by_subject: dict[int, dict[str, list[tuple[date, float]]]] = defaultdict(lambda: defaultdict(list))
    for a in session.exec(select(Assessment)).all():
        by_subject[a.student_id][a.subject].append((a.exam_date or date.min, a.marks / a.max_marks * 100))
    for sid, subjects in by_subject.items():
        s = sig[sid]
        all_scores = [p for rows in subjects.values() for _, p in rows]
        s.marks_avg = round(statistics.mean(all_scores), 1)
        trends = []
        subject_avg = {}
        for subject, rows in subjects.items():
            rows.sort()
            subject_avg[subject] = statistics.mean(p for _, p in rows)
            if len(rows) >= 2:
                trends.append(rows[-1][1] - rows[0][1])
        s.marks_trend = round(statistics.mean(trends), 1) if trends else None
        s.weakest_subject = min(subject_avg, key=subject_avg.get)
        s.weakest_subject_pct = round(subject_avg[s.weakest_subject], 1)

    # Clinical quota pace relative to the cohort median of the same year.
    progress = {}
    for st, _u in students:
        if st.year in CLINICAL_YEARS:
            progress[st.id] = student_quota_progress(session, st)
    medians = {}
    for year in CLINICAL_YEARS:
        vals = [p.overall_percent for sid, p in progress.items() if sig[sid].year == year.value]
        medians[year.value] = statistics.median(vals) if vals else None
    for sid, p in progress.items():
        s = sig[sid]
        s.quota_percent = p.overall_percent
        s.cohort_median_percent = medians[s.year]
        if s.cohort_median_percent:
            s.pace_ratio = round(p.overall_percent / s.cohort_median_percent, 2)
        s.quota_gaps = sorted(
            ({"department": d.department, "approved": d.approved, "required": d.required, "remaining": d.remaining,
              "percent": d.percent} for d in p.departments if d.remaining > 0),
            key=lambda g: (g["percent"], -g["remaining"]),
        )

    # Rejection rate of reviewed cases
    for sid, status, n in session.exec(
        select(Case.student_id, Case.status, func.count(Case.id))
        .where(Case.status.in_([CaseStatus.approved, CaseStatus.rejected]))
        .group_by(Case.student_id, Case.status)
    ).all():
        s = sig[sid]
        s.reviewed_cases += n
        if status == CaseStatus.rejected:
            s.rejected_cases += n
    for s in sig.values():
        if s.reviewed_cases >= MIN_REVIEWED:
            s.rejection_rate = round(s.rejected_cases / s.reviewed_cases, 3)
    return sig


# --------------------------------------------------------------------------- rules

def gap_phrase(gaps: list[dict], n: int = 2) -> str:
    parts = [f"{min(g['remaining'], 3)} {DEPT_SHORT[g['department']]}" for g in gaps[:n]]
    return " and ".join(parts) + " cases" if parts else "additional cases"


def evaluate_rules(s: StudentSignals) -> list[Flag]:
    flags: list[Flag] = []
    if s.attendance_pct is not None and s.attendance_pct < ATT_MIN:
        flags.append(Flag("attendance_low", "critical",
                          f"Attendance is {s.attendance_pct:.0f}% over the last 12 weeks (DCI minimum {ATT_MIN:.0f}%).",
                          "Schedule a mentor meeting and issue an attendance advisory; check for health or personal issues."))
    if (s.attendance_trend is not None and s.attendance_trend <= -ATT_DROP
            and s.attendance_recent_pct is not None and s.attendance_recent_pct < 85):
        sev = "critical" if s.attendance_recent_pct < 70 else "warning"
        flags.append(Flag("attendance_drop", sev,
                          f"Attendance fell from {s.attendance_prior_pct:.0f}% to {s.attendance_recent_pct:.0f}% "
                          f"in the last 4 weeks.",
                          "Contact the student this week to understand the recent drop."))
    if s.marks_avg is not None and s.marks_avg < MARKS_PASS:
        flags.append(Flag("marks_low", "critical",
                          f"Marks average is {s.marks_avg:.0f}% (pass mark {MARKS_PASS:.0f}%); weakest: "
                          f"{s.weakest_subject} at {s.weakest_subject_pct:.0f}%.",
                          f"Enrol in remedial sessions for {s.weakest_subject}."))
    if s.marks_trend is not None and s.marks_trend <= -MARKS_DROP:
        flags.append(Flag("marks_drop", "warning",
                          f"Marks dropped by {abs(s.marks_trend):.0f} points from the first internal to the latest exam.",
                          "Review exam preparation with the subject teacher."))
    if s.is_clinical and s.pace_ratio is not None and s.pace_ratio < PACE_WARNING:
        sev = "critical" if s.pace_ratio < PACE_CRITICAL else "warning"
        flags.append(Flag("quota_pace", sev,
                          f"Clinical quota {s.quota_percent:.0f}% complete vs cohort median {s.cohort_median_percent:.0f}% "
                          f"({s.pace_ratio * 100:.0f}% of expected pace).",
                          f"Assign {gap_phrase(s.quota_gaps)} via Smart Allocation."))
    if s.rejection_rate is not None and s.rejection_rate > REJECT_RATE:
        flags.append(Flag("rejections", "warning",
                          f"{s.rejected_cases} of {s.reviewed_cases} reviewed cases were rejected "
                          f"({s.rejection_rate * 100:.0f}%).",
                          "Arrange a case-documentation review with the supervising faculty."))
    return flags


# --------------------------------------------------------------------------- model

def _model():
    return make_pipeline(StandardScaler(), LogisticRegression(C=0.5, class_weight="balanced", max_iter=2000))


def load_ground_truth() -> dict[str, bool] | None:
    path = artifact_dir() / "seed_ground_truth.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return {row["roll_no"]: bool(row["at_risk"]) for row in data["students"]}


def _prf(truth: list[bool], pred: list[bool]) -> dict:
    tp = sum(t and p for t, p in zip(truth, pred))
    fp = sum((not t) and p for t, p in zip(truth, pred))
    fn = sum(t and (not p) for t, p in zip(truth, pred))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": round(precision, 3), "recall": round(recall, 3), "f1": round(f1, 3),
            "flagged": tp + fp, "true_positives": tp}


def train(session: Session) -> dict:
    signals = compute_signals(session)
    rows = list(signals.values())
    X = np.array([s.model_vector() for s in rows])
    y = np.array([int(any(f.severity == "critical" for f in evaluate_rules(s))) for s in rows])
    if len(set(y.tolist())) < 2:
        raise ValueError("Weak labels contain a single class; cannot train the student-risk model")
    model = _model().fit(X, y)
    bundle = {
        "name": MODEL_NAME,
        "version": "1.0",
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "features": [f for f, _ in MODEL_FEATURES],
        "coef": model[-1].coef_[0].tolist(),
        "intercept": float(model[-1].intercept_[0]),
        "n_train": len(rows),
        "n_positive": int(y.sum()),
        "model": model,
    }
    save_bundle(MODEL_NAME, bundle)
    bundle["evaluation"] = evaluate(session, signals)
    save_bundle(MODEL_NAME, bundle)
    return bundle


def evaluate(session: Session, signals: dict[int, StudentSignals] | None = None) -> dict | None:
    truth = load_ground_truth()
    if truth is None:
        return None
    alerts = assess_all(session, signals)
    alerts = [a for a in alerts if a["roll_no"] in truth]
    t = [truth[a["roll_no"]] for a in alerts]
    rules_pred = [bool(a["reasons"]) for a in alerts]
    model_pred = [a["score"] is not None and a["score"] >= 0.5 for a in alerts]
    hybrid_pred = [a["risk_level"] in ("High", "Medium") for a in alerts]
    high_pred = [a["risk_level"] == "High" for a in alerts]
    return {
        "students": len(alerts),
        "positives": sum(t),
        "rules": _prf(t, rules_pred),
        "model": _prf(t, model_pred),
        "hybrid": _prf(t, hybrid_pred),
        "hybrid_high": _prf(t, high_pred),
        "missed": [a["roll_no"] for a, tt, p in zip(alerts, t, hybrid_pred) if tt and not p],
        "false_alarms": [a["roll_no"] for a, tt, p in zip(alerts, t, hybrid_pred) if p and not tt],
    }


# --------------------------------------------------------------------------- inference

def _score(bundle: dict | None, s: StudentSignals) -> tuple[float | None, list[dict]]:
    if bundle is None:
        return None, []
    pipe = bundle["model"]
    x = np.array([s.model_vector()])
    prob = float(pipe.predict_proba(x)[0, 1])
    z = pipe[0].transform(x)[0]
    contribs = []
    for (name, label), coef, zi in zip(MODEL_FEATURES, pipe[-1].coef_[0], z):
        c = float(coef * zi)
        if abs(c) >= 0.25:
            contribs.append({"feature": name, "label": label, "contribution": round(c, 2),
                             "z_score": round(float(zi), 2),
                             "direction": "raises" if c > 0 else "lowers"})
    contribs.sort(key=lambda c: -abs(c["contribution"]))
    return prob, contribs


def hybrid_level(flags: list[Flag], score: float | None) -> str:
    if any(f.severity == "critical" for f in flags) or (score is not None and score >= HIGH_SCORE):
        return "High"
    if flags or (score is not None and score >= MEDIUM_SCORE):
        return "Medium"
    return "Low"


def assess(s: StudentSignals, bundle: dict | None) -> dict:
    flags = evaluate_rules(s)
    score, contribs = _score(bundle, s)
    level = hybrid_level(flags, score)
    actions = list(dict.fromkeys(f.action for f in flags))
    if level != "Low" and not flags:
        actions.append("Score is elevated from several small signals: check in informally with the student.")
    signals = asdict(s)
    signals.pop("weekly_attendance")
    signals["quota_gaps"] = [{**g, "department": g["department"].value} for g in s.quota_gaps]
    return {
        "student_id": s.student_id,
        "name": s.name,
        "roll_no": s.roll_no,
        "year": s.year,
        "risk_level": level,
        "score": round(score, 3) if score is not None else None,
        "reasons": [{"code": f.code, "severity": f.severity, "text": f.reason} for f in flags],
        "suggested_actions": actions,
        "model_factors": contribs,
        "signals": signals,
        "weekly_attendance": s.weekly_attendance,
    }


def assess_all(session: Session, signals: dict[int, StudentSignals] | None = None) -> list[dict]:
    bundle = load_bundle(MODEL_NAME)
    signals = signals or compute_signals(session)
    order = {"High": 0, "Medium": 1, "Low": 2}
    out = [assess(s, bundle) for s in signals.values()]
    return sorted(out, key=lambda a: (order[a["risk_level"]], -(a["score"] or 0)))


# --------------------------------------------------------------------------- student-facing view

def focus_areas(s: StudentSignals, priority_departments: list[Department] | None = None) -> dict:
    """Gentle, actionable wording for the student's own dashboard (no 'at-risk' labels).

    ``priority_departments`` (from the learning plan) keeps both dashboard cards in the same order.
    """
    items: list[dict] = []
    if s.attendance_pct is not None and s.attendance_pct < ATT_MIN and s.attendance_sessions:
        # Consecutive sessions needed so that (attended + n) / (total + n) >= minimum.
        need = math.ceil((ATT_MIN / 100 * s.attendance_sessions - s.attendance_attended) / (1 - ATT_MIN / 100))
        items.append({"area": "attendance", "title": "Attendance",
                      "message": f"You're at {s.attendance_pct:.1f}%. Attending your next {max(need, 0)} sessions "
                                 f"will take you past the {ATT_MIN:.0f}% requirement."})
    elif s.attendance_trend is not None and s.attendance_trend <= -ATT_DROP:
        items.append({"area": "attendance", "title": "Attendance",
                      "message": f"Your attendance dipped recently ({s.attendance_prior_pct:.0f}% to "
                                 f"{s.attendance_recent_pct:.0f}% over the last 4 weeks). If something is getting "
                                 f"in the way, your mentor is happy to help."})
    if s.is_clinical and s.pace_ratio is not None and s.pace_ratio < PACE_WARNING and s.quota_gaps:
        gaps = s.quota_gaps
        if priority_departments:
            rank = {d: i for i, d in enumerate(priority_departments)}
            gaps = sorted(gaps, key=lambda g: rank.get(g["department"], len(rank)))
        depts = ", ".join(f"{DEPT_SHORT[g['department']]} ({g['approved']}/{g['required']})" for g in gaps[:3])
        items.append({"area": "clinical", "title": "Clinical cases",
                      "message": f"Your quota is {s.quota_percent:.0f}% complete. Prioritise {depts}, and "
                                 f"ask your faculty to allocate matching patients."})
    if s.weakest_subject and s.weakest_subject_pct is not None and s.weakest_subject_pct < 60:
        items.append({"area": "marks", "title": "Studies",
                      "message": f"Give {s.weakest_subject} some extra time; your average there is "
                                 f"{s.weakest_subject_pct:.0f}%."})
    if s.marks_trend is not None and s.marks_trend <= -MARKS_DROP:
        items.append({"area": "marks", "title": "Recent exams",
                      "message": "Your latest exam scores are lower than earlier ones. A short revision plan "
                                 "with your subject teacher can turn this around."})
    if s.rejection_rate is not None and s.rejection_rate > REJECT_RATE:
        items.append({"area": "documentation", "title": "Case documentation",
                      "message": f"{s.rejected_cases} of your {s.reviewed_cases} reviewed cases came back for "
                                 f"corrections. Ask your supervisor to glance at your notes before submitting."})
    strengths = []
    if s.attendance_pct is not None and s.attendance_pct >= 85:
        strengths.append(f"Great attendance ({s.attendance_pct:.0f}%).")
    if s.pace_ratio is not None and s.pace_ratio >= 1.1:
        strengths.append("Your clinical progress is ahead of your batch.")
    if s.marks_avg is not None and s.marks_avg >= 70:
        strengths.append(f"Strong marks ({s.marks_avg:.0f}% average).")
    return {
        "student_id": s.student_id,
        "on_track": not items,
        "items": items,
        "strengths": strengths,
        "summary": "You're on track. Keep it up!" if not items else
                   f"{len(items)} area{'s' if len(items) > 1 else ''} to focus on this month.",
    }
