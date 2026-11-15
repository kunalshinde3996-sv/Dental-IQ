"""Smart patient allocation + department resource view.

Ranking is a transparent weighted score (weights below), each component turned into a
plain-language "why". Quota numbers come from services/quota.py so they match the
student's own progress bars exactly.
"""
from __future__ import annotations

import statistics
from datetime import date, timedelta

from sqlalchemy import func
from sqlmodel import Session, select

from app.models import Attendance, Case, ClinicalQuota, Faculty, Patient, Student, User
from app.models.enums import CLINICAL_YEARS, AttendanceStatus, CaseStatus, Department, StudentYear
from app.services.quota import student_quota_progress

WEIGHTS = {"quota_gap": 0.45, "workload": 0.25, "pace": 0.15, "seniority": 0.15}
SENIORITY = {StudentYear.intern: 1.0, StudentYear.bds4: 0.7, StudentYear.bds3: 0.4}
WORKLOAD_CAP = 6  # open cases at which the workload component reaches zero
OPEN_WINDOW_DAYS = 14
LOW_AVAILABILITY_PCT = 60.0
AVAILABILITY_PENALTY = 0.5
# Resource view thresholds (relative to the college average, so they adapt to any volume).
OVERLOAD_INDEX = 1.3  # cases per faculty vs mean
BACKLOG_INDEX = 1.5  # pending reviews per faculty vs mean
SHORT_SUPPLY_WEEKS = 20
DEPT_NAME = {
    Department.oral_medicine: "Oral Medicine", Department.conservative: "Conservative Dentistry",
    Department.endodontics: "Endodontics", Department.periodontics: "Periodontics",
    Department.prosthodontics: "Prosthodontics", Department.oral_surgery: "Oral Surgery",
    Department.pedodontics: "Pedodontics", Department.orthodontics: "Orthodontics",
}


def _open_cases(session: Session, today: date) -> dict[int, int]:
    rows = session.exec(
        select(Case.student_id, func.count(Case.id))
        .where(Case.status.in_([CaseStatus.draft, CaseStatus.submitted]),
               Case.visit_date > today - timedelta(days=OPEN_WINDOW_DAYS))
        .group_by(Case.student_id)
    ).all()
    return dict(rows)


def _recent_attendance(session: Session, today: date) -> dict[int, float]:
    totals: dict[int, list[int]] = {}
    for sid, st in session.exec(
        select(Attendance.student_id, Attendance.status).where(Attendance.date > today - timedelta(days=28))
    ).all():
        if st == AttendanceStatus.excused:
            continue
        t = totals.setdefault(sid, [0, 0])
        t[0] += st in (AttendanceStatus.present, AttendanceStatus.late)
        t[1] += 1
    return {sid: a / n * 100 for sid, (a, n) in totals.items() if n}


def patient_warnings(patient: Patient, department: Department) -> list[str]:
    warnings = []
    if department == Department.pedodontics and patient.age > 14:
        warnings.append(f"Patient is {patient.age}: Pedodontics normally treats children up to 14.")
    if department != Department.pedodontics and patient.age <= 12 and department != Department.orthodontics:
        warnings.append(f"Patient is {patient.age}: consider Pedodontics.")
    return warnings


def recommend(session: Session, patient: Patient, department: Department, limit: int = 5,
              today: date | None = None) -> dict:
    today = today or date.today()
    eligible_years = {q.year for q in session.exec(
        select(ClinicalQuota).where(ClinicalQuota.department == department, ClinicalQuota.required_cases > 0)
    ).all()}
    rows = session.exec(
        select(Student, User).join(User, User.id == Student.user_id)
        .where(Student.year.in_([y for y in CLINICAL_YEARS if y in eligible_years]))
    ).all()
    progress = {s.id: student_quota_progress(session, s) for s, _ in rows}
    medians = {}
    for year in eligible_years:
        vals = [p.overall_percent for (s, _), p in zip(rows, progress.values()) if s.year == year]
        medians[year] = statistics.median(vals) if vals else 0
    open_cases = _open_cases(session, today)
    attendance = _recent_attendance(session, today)

    candidates = []
    for student, user in rows:
        p = progress[student.id]
        dept = next((d for d in p.departments if d.department == department), None)
        if dept is None or dept.required == 0:
            continue
        gap = dept.remaining / dept.required
        median = medians.get(student.year) or 0
        pace_ratio = p.overall_percent / median if median else 1.0
        behind = max(0.0, min(1.0, 1 - pace_ratio))
        load = open_cases.get(student.id, 0)
        workload = 1 - min(load, WORKLOAD_CAP) / WORKLOAD_CAP
        seniority = SENIORITY[student.year]
        components = {"quota_gap": gap, "workload": workload, "pace": behind, "seniority": seniority}
        score = sum(WEIGHTS[k] * v for k, v in components.items())

        reasons = []
        if dept.remaining > 0:
            reasons.append(f"Needs {dept.remaining} more {DEPT_NAME[department]} case"
                           f"{'s' if dept.remaining != 1 else ''} ({dept.approved}/{dept.required} done"
                           f"{f', {dept.pending} pending review' if dept.pending else ''}).")
        else:
            reasons.append(f"{DEPT_NAME[department]} quota already complete ({dept.approved}/{dept.required}).")
        reasons.append(f"{'Light' if load <= 2 else 'Moderate' if load <= 4 else 'Heavy'} workload: "
                       f"{load} open case{'s' if load != 1 else ''} in the last {OPEN_WINDOW_DAYS} days.")
        if behind > 0.2:
            reasons.append(f"Behind cohort overall ({p.overall_percent:.0f}% vs median {median:.0f}%): "
                           f"this case helps them catch up.")
        if student.year == StudentYear.intern:
            reasons.append("Intern: completing requirements before the internship ends.")
        elif student.year == StudentYear.bds4:
            reasons.append("Final-year student.")

        att = attendance.get(student.id)
        available = att is None or att >= LOW_AVAILABILITY_PCT
        if not available:
            score *= AVAILABILITY_PENALTY
            reasons.append(f"Recent attendance {att:.0f}%: may be unavailable; confirm before assigning.")

        candidates.append({
            "student_id": student.id,
            "name": user.name,
            "roll_no": student.roll_no,
            "year": student.year,
            "score": round(score, 3),
            "components": {k: round(v, 3) for k, v in components.items()},
            "approved": dept.approved,
            "required": dept.required,
            "remaining": dept.remaining,
            "pending": dept.pending,
            "open_cases": load,
            "recent_attendance_pct": round(att, 1) if att is not None else None,
            "available": available,
            "reasons": reasons,
        })

    candidates.sort(key=lambda c: (-c["score"], -c["remaining"], c["open_cases"]))
    return {
        "patient_id": patient.id,
        "patient_name": patient.name,
        "department": department,
        "eligible_count": len(candidates),
        "eligible_years": sorted(y.value for y in eligible_years),
        "candidates": candidates[:limit],
        "weights": WEIGHTS,
        "warnings": patient_warnings(patient, department),
    }


def pick_supervisor(session: Session, department: Department) -> Faculty:
    """Department faculty member with the fewest cases awaiting review."""
    faculty = session.exec(select(Faculty).where(Faculty.department == department)).all()
    if not faculty:
        raise ValueError(f"No faculty in {department.value}")
    pending = dict(session.exec(
        select(Case.faculty_id, func.count(Case.id)).where(Case.status == CaseStatus.submitted)
        .group_by(Case.faculty_id)
    ).all())
    return min(faculty, key=lambda f: (pending.get(f.id, 0), f.id))


def resources(session: Session, days: int = 30, today: date | None = None) -> dict:
    today = today or date.today()
    since = today - timedelta(days=days)
    case_counts = dict(session.exec(
        select(Case.department, func.count(Case.id))
        .where(Case.visit_date > since, Case.status != CaseStatus.draft).group_by(Case.department)
    ).all())
    pending = dict(session.exec(
        select(Case.department, func.count(Case.id)).where(Case.status == CaseStatus.submitted).group_by(Case.department)
    ).all())
    faculty = dict(session.exec(select(Faculty.department, func.count(Faculty.id)).group_by(Faculty.department)).all())

    # Outstanding quota demand: remaining approved cases needed across all clinical students.
    demand = {d: 0 for d in Department}
    eligible = {d: 0 for d in Department}
    for student in session.exec(select(Student).where(Student.year.in_(CLINICAL_YEARS))).all():
        for dp in student_quota_progress(session, student).departments:
            if dp.required:
                demand[dp.department] += dp.remaining
                eligible[dp.department] += 1

    rows = []
    for d in Department:
        n_fac = faculty.get(d, 0)
        cases = case_counts.get(d, 0)
        rows.append({
            "department": d,
            "faculty": n_fac,
            "cases": cases,
            "cases_per_faculty": round(cases / n_fac, 1) if n_fac else None,
            "pending_reviews": pending.get(d, 0),
            "pending_per_faculty": round(pending.get(d, 0) / n_fac, 1) if n_fac else None,
            "eligible_students": eligible[d],
            "quota_remaining": demand[d],
            "weeks_to_clear_quota": round(demand[d] / (cases / (days / 7)), 1) if cases else None,
        })
    loads = [r["cases_per_faculty"] for r in rows if r["cases_per_faculty"] is not None]
    backlog = [r["pending_per_faculty"] for r in rows if r["pending_per_faculty"] is not None]
    mean_load = statistics.mean(loads) if loads else 0
    mean_backlog = statistics.mean(backlog) if backlog else 0
    for r in rows:
        r["load_index"] = round(r["cases_per_faculty"] / mean_load, 2) if mean_load and r["cases_per_faculty"] else None
        backlog_index = (r["pending_per_faculty"] / mean_backlog) if mean_backlog and r["pending_per_faculty"] else 0
        overloaded, reasons = False, []
        if r["load_index"] and r["load_index"] >= OVERLOAD_INDEX:
            overloaded = True
            reasons.append(f"{r['cases_per_faculty']} cases per faculty member in {days} days "
                           f"({r['load_index']:.1f}x the college average).")
        if backlog_index >= BACKLOG_INDEX:
            overloaded = True
            reasons.append(f"{r['pending_reviews']} cases waiting for review: {r['pending_per_faculty']} per faculty "
                           f"member ({backlog_index:.1f}x average). Consider an extra reviewer.")
        short = bool(r["weeks_to_clear_quota"] and r["weeks_to_clear_quota"] > SHORT_SUPPLY_WEEKS)
        if short:
            reasons.append(f"At the current patient flow, outstanding quotas need {r['weeks_to_clear_quota']:.0f} weeks: "
                           f"route more referrals here.")
        if overloaded:
            r["status"] = "overloaded"
        elif short:
            r["status"] = "short_supply"
        elif r["load_index"] is not None and r["load_index"] <= 0.7:
            r["status"] = "spare_capacity"
            reasons.append(f"Below-average load ({r['load_index']:.1f}x): can absorb more patients.")
        else:
            r["status"] = "balanced"
        r["reasons"] = reasons
    rows.sort(key=lambda r: -(r["load_index"] or 0))
    return {"days": days, "mean_cases_per_faculty": round(mean_load, 1), "departments": rows}
