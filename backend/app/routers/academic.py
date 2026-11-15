"""Attendance, assessments (marks) and clinical quota configuration."""
from datetime import date

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import col, select

from app.core.deps import AdminUser, CurrentUser, SessionDep, StaffUser, get_student_profile
from app.models import Assessment, Attendance, ClinicalQuota, Student
from app.models.enums import AttendanceSession, ExamType, Role, StudentYear
from app.schemas.academic import (
    AssessmentCreate,
    AssessmentRead,
    AttendanceBulkCreate,
    AttendanceRead,
    QuotaRead,
)

router = APIRouter(prefix="/api", tags=["academics"])


def _scope_student(session, user, student_id: int | None) -> int | None:
    """Students are always scoped to themselves; staff may pass any student_id (or none)."""
    if user.role != Role.student:
        return student_id
    own = get_student_profile(session, user)
    if own is None or (student_id is not None and student_id != own.id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Students can only access their own records")
    return own.id


# --- Attendance -------------------------------------------------------------

@router.get("/attendance", response_model=list[AttendanceRead], summary="Attendance records")
def list_attendance(
    session: SessionDep,
    user: CurrentUser,
    student_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    session_type: AttendanceSession | None = Query(default=None, alias="session"),
    limit: int = Query(default=500, ge=1, le=5000),
):
    student_id = _scope_student(session, user, student_id)
    stmt = select(Attendance)
    if student_id is not None:
        stmt = stmt.where(Attendance.student_id == student_id)
    if date_from:
        stmt = stmt.where(Attendance.date >= date_from)
    if date_to:
        stmt = stmt.where(Attendance.date <= date_to)
    if session_type:
        stmt = stmt.where(Attendance.session == session_type)
    return session.exec(stmt.order_by(col(Attendance.date).desc(), Attendance.student_id).limit(limit)).all()


@router.post("/attendance/bulk", response_model=list[AttendanceRead], status_code=status.HTTP_201_CREATED,
             summary="Mark attendance for a session (faculty/admin). Upserts existing records")
def mark_attendance(body: AttendanceBulkCreate, session: SessionDep, _staff: StaffUser):
    ids = [e.student_id for e in body.entries]
    found = set(session.exec(select(Student.id).where(col(Student.id).in_(ids))).all())
    unknown = sorted(set(ids) - found)
    if unknown:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Unknown student_id(s): {unknown}")

    existing = {
        a.student_id: a
        for a in session.exec(
            select(Attendance).where(
                Attendance.date == body.date, Attendance.session == body.session, col(Attendance.student_id).in_(ids)
            )
        ).all()
    }
    records = []
    for entry in body.entries:
        record = existing.get(entry.student_id) or Attendance(
            student_id=entry.student_id, date=body.date, session=body.session, status=entry.status
        )
        record.status = entry.status
        session.add(record)
        records.append(record)
    session.commit()
    for r in records:
        session.refresh(r)
    return records


# --- Assessments ------------------------------------------------------------

def _assessment_read(a: Assessment) -> AssessmentRead:
    return AssessmentRead(
        id=a.id, student_id=a.student_id, subject=a.subject, exam_type=a.exam_type, marks=a.marks,
        max_marks=a.max_marks, exam_date=a.exam_date, percentage=round(a.marks / a.max_marks * 100, 1),
    )


@router.get("/assessments", response_model=list[AssessmentRead], summary="Marks")
def list_assessments(
    session: SessionDep,
    user: CurrentUser,
    student_id: int | None = None,
    subject: str | None = None,
    exam_type: ExamType | None = None,
    limit: int = Query(default=500, ge=1, le=5000),
):
    student_id = _scope_student(session, user, student_id)
    stmt = select(Assessment)
    if student_id is not None:
        stmt = stmt.where(Assessment.student_id == student_id)
    if subject:
        stmt = stmt.where(Assessment.subject == subject)
    if exam_type:
        stmt = stmt.where(Assessment.exam_type == exam_type)
    rows = session.exec(stmt.order_by(Assessment.student_id, Assessment.subject, Assessment.exam_date).limit(limit))
    return [_assessment_read(a) for a in rows.all()]


@router.post("/assessments", response_model=AssessmentRead, status_code=status.HTTP_201_CREATED,
             summary="Record marks (faculty/admin)")
def create_assessment(body: AssessmentCreate, session: SessionDep, _staff: StaffUser):
    if session.get(Student, body.student_id) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Student not found")
    assessment = Assessment(**body.model_dump())
    session.add(assessment)
    session.commit()
    session.refresh(assessment)
    return _assessment_read(assessment)


@router.delete("/assessments/{assessment_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Delete a marks entry (faculty/admin)")
def delete_assessment(assessment_id: int, session: SessionDep, _staff: StaffUser) -> None:
    assessment = session.get(Assessment, assessment_id)
    if assessment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Assessment not found")
    session.delete(assessment)
    session.commit()


# --- Clinical quotas --------------------------------------------------------

@router.get("/quotas", response_model=list[QuotaRead], summary="Clinical quota requirements")
def list_quotas(session: SessionDep, _user: CurrentUser, year: StudentYear | None = None):
    stmt = select(ClinicalQuota)
    if year:
        stmt = stmt.where(ClinicalQuota.year == year)
    return session.exec(stmt.order_by(ClinicalQuota.year, ClinicalQuota.department)).all()


@router.put("/quotas/{quota_id}", response_model=QuotaRead, summary="Change a quota requirement (admin)")
def update_quota(quota_id: int, required_cases: int = Query(ge=0, le=500), *, session: SessionDep,
                 _admin: AdminUser):
    quota = session.get(ClinicalQuota, quota_id)
    if quota is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Quota not found")
    quota.required_cases = required_cases
    session.add(quota)
    session.commit()
    session.refresh(quota)
    return quota
