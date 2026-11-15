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
import random
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

from sqlmodel import Session, SQLModel, select

from app.core.security import hash_password
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
DEFAULT_PASSWORD = "Password@123"

DEMO_ACCOUNTS = {
    "admin": ("admin@gdch.demo", "Admin@123"),
    "faculty": ("faculty@gdch.demo", "Faculty@123"),
    "student": ("student@gdch.demo", "Student@123"),
    "atrisk": ("atrisk.student@gdch.demo", "Student@123"),
}


# --------------------------------------------------------------------------- helpers

@dataclass
class StudentProfile:
    """Hidden 'ground truth' used only to generate data. Not stored in the DB."""

    attendance_rate: float
    case_weight: float
    marks_mean: float  # fraction of max marks
    marks_trend: float  # change per successive exam (negative = declining)
    label: str = "typical"


def typical_profile() -> StudentProfile:
    return StudentProfile(
        attendance_rate=RNG.uniform(0.82, 0.97),
        case_weight=RNG.uniform(0.85, 1.25),
        marks_mean=RNG.uniform(0.60, 0.80),
        marks_trend=RNG.uniform(-0.02, 0.03),
    )


def low_attendance() -> dict:
    return {"attendance_rate": RNG.uniform(0.55, 0.68)}


def low_cases() -> dict:
    return {"case_weight": RNG.uniform(0.12, 0.25)}


def weak_marks() -> dict:
    return {"marks_mean": RNG.uniform(0.40, 0.48), "marks_trend": -0.06}


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


def pick_teeth(complaint: str, diagnosis: str, n: int, child: bool) -> list[int]:
    text = f"{complaint} {diagnosis}".lower()
    if "third molar" in text:
        pool = THIRD_MOLARS
    elif "front" in text or "class iii" in text or ", 11" in text or "of 11" in text:
        pool = ANTERIOR
    elif child:
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
                profile = StudentProfile(0.93, 1.3, 0.76, 0.02, "demo: strong student")
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


def choose_template(dept: Department, patient: Patient) -> D.CaseTemplate:
    templates = D.TEMPLATES[dept]
    if dept == Department.oral_medicine:
        user = HabitStatus.current in (patient.smokeless_tobacco, patient.tobacco_smoking)
        lesion_idx = D.TOBACCO_LESION_TEMPLATE_INDEXES
        if user and RNG.random() < 0.45:
            # Suspicious ulcer is rare even among tobacco users
            idx = RNG.choices(lesion_idx, weights=[5, 4, 1], k=1)[0]
            return templates[idx]
        others = [t for i, t in enumerate(templates) if i not in lesion_idx]
        return RNG.choice(others)
    if dept == Department.prosthodontics and patient.age < 50:
        return RNG.choice([t for t in templates if "edentulous maxilla" not in t[1]])
    return RNG.choice(templates)


def case_status(visit: date) -> tuple[CaseStatus, str | None]:
    age_days = (TODAY - visit).days
    if age_days <= 10:
        status = RNG.choices([CaseStatus.draft, CaseStatus.submitted, CaseStatus.approved], weights=[20, 60, 20])[0]
    else:
        status = RNG.choices([CaseStatus.approved, CaseStatus.rejected, CaseStatus.submitted], weights=[88, 7, 5])[0]
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
    for i in range(1, N_PATIENTS + 1):
        patient = make_patient(i)
        n_visits = RNG.choices(range(1, 8), weights=[10, 15, 20, 20, 15, 12, 8])[0]
        first = TODAY - timedelta(days=RNG.randint(5, CASE_HISTORY_DAYS))
        visit_dates = sorted(
            min(TODAY, first + timedelta(days=RNG.randint(0, (TODAY - first).days))) for _ in range(n_visits - 1)
        )
        visit_dates = [first, *visit_dates]
        patient.created_at = as_dt(first, 9)
        session.add(patient)
        session.flush()

        for v, visit in enumerate(visit_dates):
            dept = choose_department(patient, first_visit=v == 0)
            complaint, diagnosis, procedure, finding_specs, (lo, hi) = choose_template(dept, patient)
            student = RNG.choices(clinical, weights=student_weights)[0]
            status, remarks = case_status(visit)
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
                for tooth in pick_teeth(complaint, diagnosis, RNG.randint(lo, hi), patient.age <= 14):
                    case.findings.append(
                        ToothFinding(tooth_number=tooth, condition=condition, surfaces=surfaces, treatment=treatment)
                    )
            session.add(case)
            n_cases += 1
    return N_PATIENTS, n_cases


def create_attendance(session: Session, students: list[Student], profiles: dict[int, StudentProfile]) -> int:
    rows = 0
    days = [TODAY - timedelta(days=d) for d in range(ATTENDANCE_DAYS, 0, -1)]
    days = [d for d in days if d.weekday() != 6]  # Monday-Saturday timetable
    for st in students:
        rate = profiles[st.id].attendance_rate
        if st.year == StudentYear.intern:
            sessions = [AttendanceSession.clinic]
        elif st.year in CLINICAL_YEARS:
            sessions = [AttendanceSession.theory, AttendanceSession.clinic]
        else:
            sessions = [AttendanceSession.theory, AttendanceSession.practical]
        for d in days:
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

def seed(reset: bool) -> None:
    if reset:
        import app.models  # noqa: F401  (register tables before drop)

        SQLModel.metadata.drop_all(engine)
    create_db_and_tables()

    with Session(engine) as session:
        if session.exec(select(User).limit(1)).first():
            raise SystemExit("Database already contains data. Re-run with --reset to wipe and re-seed.")

        students, profiles, faculty_by_dept = create_users(session)
        create_quotas(session)
        n_patients, n_cases = create_patients_and_cases(session, students, profiles, faculty_by_dept)
        n_att = create_attendance(session, students, profiles)
        n_marks = create_assessments(session, students, profiles)
        session.commit()

        print("Seeded SYNTHETIC demo data:")
        print(f"  students={len(students)}  faculty={sum(len(v) for v in faculty_by_dept.values())}  "
              f"patients={n_patients}  cases={n_cases}  attendance={n_att}  assessments={n_marks}")
        print("  Designed at-risk students (ground truth for Phase-2 validation):")
        for st in students:
            if profiles[st.id].label not in ("typical", "demo: strong student"):
                user = session.get(User, st.user_id)
                print(f"    {st.roll_no:<12} {st.year.value:<7} {user.name:<24} {profiles[st.id].label}")
        print("  Demo logins:")
        for role, (email, pwd) in DEMO_ACCOUNTS.items():
            print(f"    {role:<8} {email:<28} {pwd}")
        print(f"  All other generated accounts use password: {DEFAULT_PASSWORD}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed Dental-IQ with synthetic demo data")
    parser.add_argument("--reset", action="store_true", help="drop and recreate all tables first")
    seed(parser.parse_args().reset)
