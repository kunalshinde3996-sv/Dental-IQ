"""Populate the database with SYNTHETIC demo data.

    cd backend
    python -m scripts.seed            # seed an empty database
    python -m scripts.seed --reset    # drop all tables, recreate, seed

All patients are flagged ``is_synthetic = True``. No real patient data is used.
Output is deterministic (fixed RNG seed). Dates are relative to *today*, so the
demo always looks current.

A handful of students are deliberately weak (low attendance, low case count,
low or declining marks) so Phase-2 at-risk detection has signal to find.
"""
from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from sqlmodel import Session, SQLModel, select

from app.core.config import artifact_dir
from app.core.security import hash_password
from app.services.clinical_terms import categorize
from app.database import create_db_and_tables, engine
from app.models import (
    Assessment,
    Attendance,
    Case,
    ClinicalQuota,
    Faculty,
    Patient,
    Student,
    ToothFinding,
    User,
)
from app.models.enums import (
    CLINICAL_YEARS,
    AttendanceSession,
    AttendanceStatus,
    CaseStatus,
    Department,
    ExamType,
    HabitStatus,
    Role,
    Sex,
    StudentYear,
    Taluka,
    ToothCondition,
)
from scripts import seed_data as D

RNG = random.Random(2026)
TODAY = date.today()

N_PATIENTS = 400
STUDENTS_PER_YEAR = 12
ATTENDANCE_DAYS = 91
CASE_HISTORY_DAYS = 180
FOLLOW_UP_DAYS = 90
DEFAULT_PASSWORD = "Dental#2026"  # all demo passwords satisfy app.core.passwords policy (checked below)

DEMO_ACCOUNTS = {
    "admin": ("admin@gdch.demo", "Office#2026"),
    "faculty": ("faculty@gdch.demo", "Clinic#2026"),
    "student": ("student@gdch.demo", "Molar#2026"),
    "atrisk": ("atrisk.student@gdch.demo", "Molar#2026"),
}


# --------------------------------------------------------------------------- helpers

@dataclass
class StudentProfile:
    """Hidden 'ground truth' used only to generate data. Not stored in the DB."""

    attendance_start: float  # attendance probability at the start of the 3-month window
    attendance_end: float  # ... and at the end (linear in between -> trend)
    case_weight: float
    marks_mean: float  # fraction of max marks
    marks_trend: float  # change per successive exam (negative = declining)
    reject_prob: float = 0.06  # chance a reviewed case is rejected
    label: str = "typical"


def typical_profile() -> StudentProfile:
    base = RNG.uniform(0.82, 0.97)
    return StudentProfile(
        attendance_start=base,
        attendance_end=min(0.99, base + RNG.uniform(-0.04, 0.04)),
        case_weight=RNG.uniform(0.85, 1.25),
        marks_mean=RNG.uniform(0.60, 0.80),
        marks_trend=RNG.uniform(-0.02, 0.03),
        reject_prob=RNG.uniform(0.03, 0.09),
    )


def low_attendance() -> dict:
    # Starts acceptable, then drifts down: overall ~60-70%, last month well below 75%.
    return {"attendance_start": RNG.uniform(0.82, 0.90), "attendance_end": RNG.uniform(0.40, 0.52)}


def low_cases() -> dict:
    return {"case_weight": RNG.uniform(0.12, 0.25)}


def weak_marks() -> dict:
    return {"marks_mean": RNG.uniform(0.40, 0.48), "marks_trend": -0.06, "reject_prob": RNG.uniform(0.25, 0.35)}


def sloppy_clinician() -> dict:
    # Decent attendance and marks, but many cases bounced by faculty and slow clinical progress.
    return {"reject_prob": RNG.uniform(0.35, 0.45), "case_weight": RNG.uniform(0.45, 0.55)}


# (year, index within year) -> overrides making that student at-risk
AT_RISK_DESIGN: dict[tuple[StudentYear, int], tuple[str, dict]] = {
    (StudentYear.bds1, 0): ("low attendance", low_attendance()),
    (StudentYear.bds2, 0): ("weak marks", weak_marks()),
    (StudentYear.bds2, 1): ("low attendance", low_attendance()),
    (StudentYear.bds3, 0): ("low attendance + low cases + declining marks",
                            {**low_attendance(), **low_cases(), **weak_marks()}),
    (StudentYear.bds3, 1): ("low attendance", low_attendance()),
    (StudentYear.bds3, 2): ("weak marks", weak_marks()),
    (StudentYear.bds4, 1): ("low cases", low_cases()),
    (StudentYear.bds4, 2): ("low attendance + weak marks", {**low_attendance(), **weak_marks()}),
    (StudentYear.bds4, 3): ("high rejection rate + slow clinical pace", sloppy_clinician()),
    (StudentYear.intern, 0): ("low cases", low_cases()),
}


def random_name(sex: Sex) -> str:
    first = RNG.choice(D.MALE_FIRST if sex == Sex.male else D.FEMALE_FIRST)
    return f"{first} {RNG.choice(D.SURNAMES)}"


def email_slug(name: str) -> str:
    return name.lower().replace("'", "").replace(" ", ".")


def weighted_choice(weights: dict):
    keys = list(weights)
    return RNG.choices(keys, weights=[weights[k] for k in keys], k=1)[0]


def habit(p_current: float, p_former: float) -> HabitStatus:
    r = RNG.random()
    if r < p_current:
        return HabitStatus.current
    if r < p_current + p_former:
        return HabitStatus.former
    return HabitStatus.never


def as_dt(d: date, hour: int = 11) -> datetime:
    return datetime.combine(d, time(hour, RNG.randint(0, 59)), tzinfo=timezone.utc)


ANTERIOR = [11, 12, 13, 21, 22, 23, 31, 32, 33, 41, 42, 43]
POSTERIOR = [14, 15, 16, 17, 24, 25, 26, 27, 34, 35, 36, 37, 44, 45, 46, 47]
THIRD_MOLARS = [18, 28, 38, 48]
CHILD_TEETH = [11, 21, 16, 26, 36, 46, 12, 22]  # permanent teeth erupted in mixed dentition
# Primary (deciduous) teeth, FDI quadrants 5-8: mostly molars for caries in young children.
PRIMARY_TEETH = [54, 55, 64, 65, 74, 75, 84, 85, 51, 61]


def pick_teeth(complaint: str, diagnosis: str, n: int, age: int) -> list[int]:
    text = f"{complaint} {diagnosis}".lower()
    if "third molar" in text:
        pool = THIRD_MOLARS
    elif age <= 9 and "11" not in text:
        pool = PRIMARY_TEETH
    elif "front" in text or "class iii" in text or ", 11" in text or "of 11" in text:
        pool = ANTERIOR
    elif age <= 14:
        pool = CHILD_TEETH
    else:
        pool = POSTERIOR + ANTERIOR[:4]
    return sorted(RNG.sample(pool, min(n, len(pool))))


# --------------------------------------------------------------------------- builders

def create_users(session: Session) -> tuple[list[Student], dict[int, StudentProfile], dict[Department, list[Faculty]]]:
    shared_hash = hash_password(DEFAULT_PASSWORD)

    # Admin
    email, pwd = DEMO_ACCOUNTS["admin"]
    session.add(User(name="Academic Office (Admin)", email=email, password_hash=hash_password(pwd), role=Role.admin))

    # Faculty: one per department, plus a second in the two busiest departments.
    faculty_by_dept: dict[Department, list[Faculty]] = {d: [] for d in Department}
    depts = list(Department) + [Department.oral_medicine, Department.conservative]
    for i, dept in enumerate(depts):
        sex = RNG.choice([Sex.male, Sex.female])
        name = f"Dr. {random_name(sex)}"
        if i == 0:  # demo faculty: HOD Oral Medicine (sees most submissions)
            email, pwd = DEMO_ACCOUNTS["faculty"]
            pw_hash, designation = hash_password(pwd), "Professor & HOD"
        else:
            email = f"{email_slug(name.removeprefix('Dr. '))}.{i}@faculty.gdch.demo"
            pw_hash = shared_hash
            designation = D.FACULTY_DESIGNATIONS[1 + i % 3] if dept in depts[:i] else D.FACULTY_DESIGNATIONS[0]
        user = User(name=name, email=email, password_hash=pw_hash, role=Role.faculty)
        session.add(user)
        session.flush()
        fac = Faculty(user_id=user.id, department=dept, designation=designation)
        session.add(fac)
        faculty_by_dept[dept].append(fac)

    # Students
    students: list[Student] = []
    profiles: dict[int, StudentProfile] = {}
    roll_seq = 1
    for year in StudentYear:
        for idx in range(STUDENTS_PER_YEAR):
            sex = RNG.choice([Sex.male, Sex.female, Sex.female])  # dental cohorts skew female
            name = random_name(sex)
            profile = typical_profile()
            if (year, idx) in AT_RISK_DESIGN:
                label, overrides = AT_RISK_DESIGN[(year, idx)]
                for k, v in overrides.items():
                    setattr(profile, k, v)
                profile.label = label

            if (year, idx) == (StudentYear.bds4, 0):
                email, pwd = DEMO_ACCOUNTS["student"]
                pw_hash = hash_password(pwd)
                profile = StudentProfile(0.92, 0.94, 1.3, 0.76, 0.02, 0.04, "demo: strong student")
            elif (year, idx) == (StudentYear.bds3, 0):
                email, pwd = DEMO_ACCOUNTS["atrisk"]
                pw_hash = hash_password(pwd)
            else:
                email, pw_hash = f"{email_slug(name)}.{roll_seq}@students.gdch.demo", shared_hash

            user = User(name=name, email=email, password_hash=pw_hash, role=Role.student)
            session.add(user)
            session.flush()
            batch = D.BATCH_BY_YEAR[year]
            st = Student(user_id=user.id, roll_no=f"GDC{batch[:4]}{roll_seq:03d}", year=year, batch=batch)
            session.add(st)
            session.flush()
            students.append(st)
            profiles[st.id] = profile
            roll_seq += 1

    return students, profiles, faculty_by_dept


def create_quotas(session: Session) -> None:
    for year, per_dept in D.QUOTAS.items():
        for dept, required in per_dept.items():
            session.add(ClinicalQuota(department=dept, year=year, required_cases=required))


def latent_pmd(patient: Patient) -> bool:
    """Hidden generative model for potentially malignant disorders (OSMF, leukoplakia, ...).

    A known logistic form makes the Phase-2 risk model's recovered coefficients checkable.
    Not an epidemiological model.
    """
    if patient.age < 18:
        return False
    logit = -3.4
    logit += {HabitStatus.current: 2.0, HabitStatus.former: 1.0}.get(patient.smokeless_tobacco, 0.0)
    logit += {HabitStatus.current: 1.0, HabitStatus.former: 0.4}.get(patient.tobacco_smoking, 0.0)
    logit += 0.5 if patient.alcohol == HabitStatus.current else 0.0
    logit += 0.03 * (patient.age - 40)
    logit += 0.4 if patient.taluka in D.RURAL_TALUKAS else 0.0
    logit += 0.03 * min(patient.habit_duration_years or 0, 30)
    return RNG.random() < 1 / (1 + math.exp(-logit))


def make_patient(i: int) -> Patient:
    taluka: Taluka = weighted_choice(D.TALUKA_WEIGHTS)
    rural = taluka in D.RURAL_TALUKAS
    # Age mix: ~16% children (5-14), the rest adults skewed to 20-60.
    if RNG.random() < 0.16:
        age = RNG.randint(5, 14)
    else:
        age = int(min(85, max(15, RNG.gauss(40, 15))))
    sex = RNG.choice([Sex.male, Sex.female])
    male = sex == Sex.male
    adult = age >= 18

    smoking = habit(0.20 if male else 0.02, 0.08 if male else 0.01) if adult else HabitStatus.never
    smokeless = (habit((0.30 if rural else 0.20) if male else (0.12 if rural else 0.05), 0.06)
                 if age >= 15 else HabitStatus.never)
    alcohol = habit(0.38 if male else 0.08, 0.06) if adult else HabitStatus.never
    any_habit = HabitStatus.current in (smoking, smokeless, alcohol) or HabitStatus.former in (smoking, smokeless, alcohol)

    abha = None
    if RNG.random() < 0.45:
        digits = f"{RNG.randint(10, 99)}{RNG.randint(0, 10**12 - 1):012d}"
        abha = f"{digits[:2]}-{digits[2:6]}-{digits[6:10]}-{digits[10:]}"

    return Patient(
        opd_number=f"GDC-{TODAY.year}-{i:06d}",
        abha_id=abha,
        name=random_name(sex),
        age=age,
        sex=sex,
        taluka=taluka,
        phone=f"70000{RNG.randint(0, 99999):05d}" if RNG.random() < 0.9 else None,  # synthetic numbers
        tobacco_smoking=smoking,
        smokeless_tobacco=smokeless,
        alcohol=alcohol,
        habit_duration_years=RNG.randint(1, max(1, age - 14)) if any_habit else None,
        has_diabetes=adult and RNG.random() < (0.04 + age / 400),
        has_hypertension=adult and RNG.random() < (0.03 + age / 300),
        has_cardiac_disease=age > 45 and RNG.random() < 0.06,
        allergies=RNG.choice(["Penicillin", "Sulpha drugs", "Latex"]) if RNG.random() < 0.05 else None,
        medical_history_notes=None,
        is_synthetic=True,
    )


def choose_department(patient: Patient, first_visit: bool) -> Department:
    if patient.age <= 14:
        return weighted_choice({Department.pedodontics: 70, Department.orthodontics: 10, Department.oral_medicine: 20})
    if first_visit and RNG.random() < 0.6:
        return Department.oral_medicine  # patients are registered and screened in Oral Medicine first
    weights = dict(D.DEPARTMENT_WEIGHTS)
    weights[Department.pedodontics] = 0
    if patient.age > 25:
        weights[Department.orthodontics] = 0.5
    if patient.age > 55:
        weights[Department.prosthodontics] *= 3
    return weighted_choice(weights)


def pmd_template(patient: Patient) -> D.CaseTemplate:
    """OSMF / leukoplakia / suspicious ulcer; OSMF dominates in smokeless-tobacco (areca) users."""
    osmf, leuko, ulcer = D.TOBACCO_LESION_TEMPLATE_INDEXES
    if patient.smokeless_tobacco != HabitStatus.never:
        idx = RNG.choices([osmf, leuko, ulcer], weights=[60, 34, 6])[0]
    else:
        idx = RNG.choices([osmf, leuko, ulcer], weights=[15, 75, 10])[0]
    return D.TEMPLATES[Department.oral_medicine][idx]


def latent_caries(patient: Patient) -> bool:
    """Hidden per-patient caries status; prevalence rises with age (see seed_data)."""
    p = next(prob for max_age, prob in D.CARIES_PREVALENCE_BY_AGE if patient.age <= max_age)
    return RNG.random() < p


def implies_caries(template: D.CaseTemplate) -> bool:
    """Same definition the analytics use, so seed and dashboard agree on what 'caries' means."""
    return "caries" in categorize(template[1], [f[0] for f in template[3]])


def choose_template(dept: Department, patient: Patient, has_pmd: bool, has_caries: bool) -> D.CaseTemplate | None:
    """Pick a template consistent with the patient's hidden conditions; None if the department has none."""
    templates = D.TEMPLATES[dept]
    if dept == Department.oral_medicine:
        if has_pmd and RNG.random() < 0.5:
            return pmd_template(patient)  # follow-up review of the lesion
        templates = [t for i, t in enumerate(templates) if i not in D.TOBACCO_LESION_TEMPLATE_INDEXES]
    elif dept == Department.oral_surgery and has_pmd and RNG.random() < 0.5:
        return templates[3]  # incisional biopsy of the oral lesion
    elif dept == Department.prosthodontics and patient.age < 50:
        templates = [t for t in templates if "edentulous maxilla" not in t[1]]
    if not has_caries:
        templates = [t for t in templates if not implies_caries(t)]
    return RNG.choice(templates) if templates else None


def caries_template(patient: Patient) -> tuple[Department, D.CaseTemplate]:
    dept = Department.pedodontics if patient.age <= 14 else Department.conservative
    return dept, RNG.choice([t for t in D.TEMPLATES[dept] if implies_caries(t)])


def plan_visits(patient: Patient, visit_dates: list[date], has_pmd: bool, has_caries: bool):
    """Department + template per visit, consistent with the patient's hidden PMD / caries status."""
    plan = []
    for v, visit in enumerate(visit_dates):
        if v == 0 and has_pmd:
            # PMD patients are always screened and diagnosed in Oral Medicine at their first visit.
            plan.append((visit, Department.oral_medicine, pmd_template(patient)))
            continue
        for _ in range(10):
            dept = choose_department(patient, first_visit=v == 0)
            template = choose_template(dept, patient, has_pmd, has_caries)
            if template is not None:
                break
        else:  # departments that only treat caries (e.g. Conservative) for a caries-free patient
            dept = Department.oral_medicine
            template = choose_template(dept, patient, False, False)
        plan.append((visit, dept, template))
    if has_caries and not any(implies_caries(t) for _, _, t in plan):
        # Make sure the caries is actually recorded: the last non-PMD-diagnosis visit treats it.
        idx = len(plan) - 1 if not (has_pmd and len(plan) == 1) else None
        if idx is not None and not (has_pmd and idx == 0):
            plan[idx] = (plan[idx][0], *caries_template(patient))
        else:
            plan.append((visit_dates[-1], *caries_template(patient)))
    return plan


def case_status(visit: date, reject_prob: float) -> tuple[CaseStatus, str | None]:
    age_days = (TODAY - visit).days
    if age_days <= 10:
        status = RNG.choices([CaseStatus.draft, CaseStatus.submitted, CaseStatus.approved], weights=[20, 60, 20])[0]
    elif RNG.random() < 0.05:
        status = CaseStatus.submitted  # still waiting for review
    else:
        status = CaseStatus.rejected if RNG.random() < reject_prob else CaseStatus.approved
    if status == CaseStatus.rejected:
        return status, RNG.choice(D.REJECTION_REMARKS)
    if status == CaseStatus.approved:
        return status, RNG.choice(D.APPROVAL_REMARKS)
    return status, None


def create_patients_and_cases(session: Session, students: list[Student], profiles: dict[int, StudentProfile],
                              faculty_by_dept: dict[Department, list[Faculty]]) -> tuple[int, int]:
    clinical = [s for s in students if s.year in CLINICAL_YEARS]
    year_factor = {StudentYear.bds3: 0.8, StudentYear.bds4: 1.0, StudentYear.intern: 1.3}
    student_weights = [profiles[s.id].case_weight * year_factor[s.year] for s in clinical]

    n_cases = 0
    n_pmd = 0
    for i in range(1, N_PATIENTS + 1):
        patient = make_patient(i)
        has_pmd = latent_pmd(patient)
        n_pmd += has_pmd
        n_visits = RNG.choices(range(1, 9), weights=[8, 12, 17, 19, 16, 13, 9, 6])[0]
        first = TODAY - timedelta(days=RNG.randint(5, CASE_HISTORY_DAYS))
        # Follow-ups fall within ~3 months of the first visit (a course of treatment), so case volume
        # is spread evenly over time instead of piling up in recent weeks.
        # Follow-ups that would fall after today are future appointments: not generated.
        follow_ups = (first + timedelta(days=RNG.randint(3, FOLLOW_UP_DAYS)) for _ in range(n_visits - 1))
        visit_dates = sorted(d for d in follow_ups if d <= TODAY)
        visit_dates = [first, *visit_dates]
        patient.created_at = as_dt(first, 9)
        session.add(patient)
        session.flush()

        has_caries = latent_caries(patient)
        for visit, dept, template in plan_visits(patient, visit_dates, has_pmd, has_caries):
            complaint, diagnosis, procedure, finding_specs, (lo, hi) = template
            student = RNG.choices(clinical, weights=student_weights)[0]
            status, remarks = case_status(visit, profiles[student.id].reject_prob)
            created = as_dt(visit, 10)
            case = Case(
                patient_id=patient.id,
                student_id=student.id,
                faculty_id=RNG.choice(faculty_by_dept[dept]).id,
                department=dept,
                visit_date=visit,
                chief_complaint=complaint,
                diagnosis=diagnosis,
                procedure=procedure,
                status=status,
                faculty_remarks=remarks,
                submitted_at=as_dt(visit, 13) if status != CaseStatus.draft else None,
                reviewed_at=as_dt(visit, 16) if status in (CaseStatus.approved, CaseStatus.rejected) else None,
                created_at=created,
                updated_at=created,
            )
            if finding_specs and hi > 0:
                condition, surfaces, treatment = finding_specs[0]
                for tooth in pick_teeth(complaint, diagnosis, RNG.randint(lo, hi), patient.age):
                    case.findings.append(
                        ToothFinding(tooth_number=tooth, condition=condition, surfaces=surfaces, treatment=treatment)
                    )
            session.add(case)
            n_cases += 1
    return N_PATIENTS, n_cases, n_pmd


def create_attendance(session: Session, students: list[Student], profiles: dict[int, StudentProfile]) -> int:
    rows = 0
    days = [TODAY - timedelta(days=d) for d in range(ATTENDANCE_DAYS, 0, -1)]
    days = [d for d in days if d.weekday() != 6]  # Monday-Saturday timetable
    for st in students:
        p = profiles[st.id]
        if st.year == StudentYear.intern:
            sessions = [AttendanceSession.clinic]
        elif st.year in CLINICAL_YEARS:
            sessions = [AttendanceSession.theory, AttendanceSession.clinic]
        else:
            sessions = [AttendanceSession.theory, AttendanceSession.practical]
        for k, d in enumerate(days):
            rate = p.attendance_start + (p.attendance_end - p.attendance_start) * k / (len(days) - 1)
            for sess in sessions:
                if RNG.random() < rate:
                    status = AttendanceStatus.late if RNG.random() < 0.05 else AttendanceStatus.present
                else:
                    status = AttendanceStatus.excused if RNG.random() < 0.1 else AttendanceStatus.absent
                session.add(Attendance(student_id=st.id, date=d, session=sess, status=status))
                rows += 1
    return rows


def create_assessments(session: Session, students: list[Student], profiles: dict[int, StudentProfile]) -> int:
    exams = [(ExamType.internal, 50, 75), (ExamType.sessional, 100, 40), (ExamType.practical, 50, 12)]
    rows = 0
    for st in students:
        p = profiles[st.id]
        for subject in D.SUBJECTS_BY_YEAR[st.year]:
            subject_skill = RNG.uniform(-0.06, 0.06)
            for k, (exam_type, max_marks, days_ago) in enumerate(exams):
                frac = p.marks_mean + subject_skill + p.marks_trend * k + RNG.gauss(0, 0.05)
                frac = min(0.98, max(0.15, frac))
                session.add(Assessment(
                    student_id=st.id, subject=subject, exam_type=exam_type,
                    marks=round(frac * max_marks * 2) / 2, max_marks=max_marks,
                    exam_date=TODAY - timedelta(days=days_ago),
                ))
                rows += 1
    return rows


# --------------------------------------------------------------------------- main

def write_ground_truth(session: Session, students: list[Student], profiles: dict[int, StudentProfile]) -> Path:
    """Persist the designed at-risk labels OUTSIDE the database, for offline ML evaluation only."""
    rows = [
        {"roll_no": st.roll_no, "year": st.year.value, "at_risk": profiles[st.id].label not in NOT_AT_RISK,
         "design": profiles[st.id].label}
        for st in students
    ]
    path = artifact_dir() / "seed_ground_truth.json"
    path.write_text(json.dumps({"generated": TODAY.isoformat(), "students": rows}, indent=2), encoding="utf-8")
    return path


NOT_AT_RISK = ("typical", "demo: strong student")


def check_demo_passwords() -> None:
    """Demo accounts must obey the same password policy the API enforces."""
    from app.core.passwords import password_problems

    for email, pwd in [*DEMO_ACCOUNTS.values(), ("someone@students.gdch.demo", DEFAULT_PASSWORD)]:
        problems = password_problems(pwd, email)
        if problems:
            raise SystemExit(f"Demo password for {email} violates the password policy: {problems}")


def seed(reset: bool, train: bool = True, verbose: bool = True) -> None:
    check_demo_passwords()
    say = print if verbose else (lambda *_a, **_k: None)
    if reset:
        import app.models  # noqa: F401  (register tables before drop)

        SQLModel.metadata.drop_all(engine)
        with engine.begin() as conn:  # alembic bookkeeping table, if migrations were used
            conn.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")
    create_db_and_tables()
    stamp_alembic_head()

    with Session(engine) as session:
        if session.exec(select(User).limit(1)).first():
            raise SystemExit("Database already contains data. Re-run with --reset to wipe and re-seed.")

        students, profiles, faculty_by_dept = create_users(session)
        create_quotas(session)
        n_patients, n_cases, n_pmd = create_patients_and_cases(session, students, profiles, faculty_by_dept)
        n_att = create_attendance(session, students, profiles)
        n_marks = create_assessments(session, students, profiles)
        session.commit()
        gt_path = write_ground_truth(session, students, profiles)

        say("Seeded SYNTHETIC demo data:")
        say(f"  students={len(students)}  faculty={sum(len(v) for v in faculty_by_dept.values())}  "
            f"patients={n_patients} (latent PMD={n_pmd})  cases={n_cases}  attendance={n_att}  assessments={n_marks}")
        say(f"  Designed at-risk students (ground truth written to {gt_path}):")
        for st in students:
            if profiles[st.id].label not in NOT_AT_RISK:
                user = session.get(User, st.user_id)
                say(f"    {st.roll_no:<12} {st.year.value:<7} {user.name:<24} {profiles[st.id].label}")
        say("  Demo logins:")
        for role, (email, pwd) in DEMO_ACCOUNTS.items():
            say(f"    {role:<8} {email:<28} {pwd}")
        say(f"  All other generated accounts use password: {DEFAULT_PASSWORD}")

    if train:
        try:
            from ml.train import train_all
        except ImportError:  # ML layer not installed
            return
        train_all(report=False, verbose=verbose)
        from app.services.notifications import refresh_at_risk_alerts

        with Session(engine) as session:
            n = refresh_at_risk_alerts(session)
        say(f"  at-risk notifications created for {n} students (sent to admins and HODs)")


def stamp_alembic_head() -> None:
    """Tables were created directly from the models, so mark the DB as up to date for Alembic."""
    try:
        from alembic import command
        from alembic.config import Config
    except ImportError:  # pragma: no cover - alembic is in requirements
        return
    root = Path(__file__).resolve().parents[1]
    if not (root / "migrations").is_dir():
        return
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("script_location", str(root / "migrations"))
    command.stamp(cfg, "head")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed Dental-IQ with synthetic demo data")
    parser.add_argument("--reset", action="store_true", help="drop and recreate all tables first")
    parser.add_argument("--no-train", action="store_true", help="skip training the ML models afterwards")
    args = parser.parse_args()
    seed(args.reset, train=not args.no_train)
