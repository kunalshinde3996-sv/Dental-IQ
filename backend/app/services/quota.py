"""Clinical quota progress: approved cases per department vs. the year's requirement.

This is the core signal for Phase 2 (smart patient allocation by quota gap,
and the "low case count" factor in at-risk alerts).
"""
from sqlalchemy import func
from sqlmodel import Session, select

from app.models import Case, ClinicalQuota, Student
from app.models.enums import CLINICAL_YEARS, CaseStatus, Department
from app.schemas.academic import QuotaProgress, StudentQuotaProgress


def _counts(session: Session, student_id: int, status: CaseStatus) -> dict[Department, int]:
    rows = session.exec(
        select(Case.department, func.count(Case.id))
        .where(Case.student_id == student_id, Case.status == status)
        .group_by(Case.department)
    ).all()
    return {dept: n for dept, n in rows}


def student_quota_progress(session: Session, student: Student) -> StudentQuotaProgress:
    quotas = session.exec(select(ClinicalQuota).where(ClinicalQuota.year == student.year)).all()
    required = {q.department: q.required_cases for q in quotas}
    approved = _counts(session, student.id, CaseStatus.approved)
    pending = _counts(session, student.id, CaseStatus.submitted)

    departments: list[QuotaProgress] = []
    for dept in Department:
        req = required.get(dept, 0)
        done = approved.get(dept, 0)
        if req == 0 and done == 0:
            continue
        departments.append(QuotaProgress(
            department=dept,
            required=req,
            approved=done,
            pending=pending.get(dept, 0),
            remaining=max(0, req - done),
            percent=round(min(100.0, done / req * 100), 1) if req else 100.0,
        ))

    total_req = sum(required.values())
    # Overall progress counts approved cases only up to each department's requirement,
    # so surplus in one department cannot hide a gap in another.
    total_done = sum(min(approved.get(d, 0), r) for d, r in required.items())
    return StudentQuotaProgress(
        student_id=student.id,
        year=student.year,
        is_clinical=student.year in CLINICAL_YEARS,
        departments=departments,
        total_required=total_req,
        total_approved=total_done,
        overall_percent=round(total_done / total_req * 100, 1) if total_req else 0.0,
    )
