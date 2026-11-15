"""Student profiles, competency (case log + quota progress) and attendance summary."""
from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlmodel import select

from app.core.deps import CurrentStudent, CurrentUser, SessionDep, StaffUser, get_student_profile
from app.models import Attendance, Case, Student, User
from app.models.enums import AttendanceStatus, CaseStatus, Department, Role, StudentYear
from app.schemas.academic import AttendanceSummary, StudentQuotaProgress
from app.schemas.cases import CaseRead
from app.schemas.common import Page
from app.schemas.users import StudentRead
from app.services.cases import case_query, to_case_read
from app.services.people import get_student_read, student_read
from app.services.academic_policy import ATTENDANCE_WINDOW_DAYS
from app.services.quota import student_quota_progress

router = APIRouter(prefix="/api/students", tags=["students"])


def resolve_student(session, user: User, student_id: int) -> Student:
    """Load a student; a student user may only access their own record."""
    student = session.get(Student, student_id)
    if student is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Student not found")
    if user.role == Role.student:
        own = get_student_profile(session, user)
        if own is None or own.id != student.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Students can only access their own records")
    return student


@router.get("", response_model=list[StudentRead], summary="List students (faculty/admin)")
def list_students(
    session: SessionDep,
    _staff: StaffUser,
    year: StudentYear | None = None,
    q: str | None = Query(default=None, max_length=100, description="Name, roll no. or email"),
):
    stmt = select(Student, User).join(User, User.id == Student.user_id)
    if year:
        stmt = stmt.where(Student.year == year)
    if q and q.strip():
        term = f"%{q.strip().lower()}%"
        stmt = stmt.where(or_(func.lower(User.name).like(term), func.lower(Student.roll_no).like(term),
                              func.lower(User.email).like(term)))
    rows = session.exec(stmt.order_by(Student.year, Student.roll_no)).all()
    return [student_read(s, u) for s, u in rows]


@router.get("/me", response_model=StudentRead, summary="Current student's profile")
def my_profile(session: SessionDep, student: CurrentStudent):
    return get_student_read(session, student.id)


@router.get("/{student_id}", response_model=StudentRead)
def get_student(student_id: int, session: SessionDep, user: CurrentUser):
    student = resolve_student(session, user, student_id)
    return get_student_read(session, student.id)


@router.get("/{student_id}/cases", response_model=Page[CaseRead], summary="Student case log")
def student_cases(
    student_id: int,
    session: SessionDep,
    user: CurrentUser,
    status_: CaseStatus | None = Query(default=None, alias="status"),
    department: Department | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    resolve_student(session, user, student_id)
    filters = [Case.student_id == student_id]
    if status_:
        filters.append(Case.status == status_)
    if department:
        filters.append(Case.department == department)
    total = session.exec(select(func.count()).select_from(Case).where(*filters)).one()
    rows = session.exec(
        case_query().where(*filters).order_by(Case.visit_date.desc(), Case.id.desc()).offset(offset).limit(limit)
    ).all()
    return Page(items=[to_case_read(r) for r in rows], total=total, limit=limit, offset=offset)


@router.get("/{student_id}/quota-progress", response_model=StudentQuotaProgress,
            summary="Approved cases vs. clinical quota, per department")
def quota_progress(student_id: int, session: SessionDep, user: CurrentUser):
    student = resolve_student(session, user, student_id)
    return student_quota_progress(session, student)


@router.get("/{student_id}/attendance-summary", response_model=AttendanceSummary)
def attendance_summary(
    student_id: int,
    session: SessionDep,
    user: CurrentUser,
    days: int = Query(default=ATTENDANCE_WINDOW_DAYS, ge=1, le=3650,
                      description="Look-back window; default matches the at-risk alerts (12 weeks)"),
):
    resolve_student(session, user, student_id)
    today = date.today()
    rows = session.exec(
        select(Attendance.session, Attendance.status, func.count())
        .where(Attendance.student_id == student_id, Attendance.date > today - timedelta(days=days),
               Attendance.date <= today)
        .group_by(Attendance.session, Attendance.status)
    ).all()

    counts = {s: 0 for s in AttendanceStatus}
    per_session: dict[str, dict[AttendanceStatus, int]] = {}
    for sess, st, n in rows:
        counts[st] += n
        per_session.setdefault(sess.value, {s: 0 for s in AttendanceStatus})[st] += n

    def pct(c: dict[AttendanceStatus, int]) -> float:
        attended = c[AttendanceStatus.present] + c[AttendanceStatus.late]
        countable = sum(c.values()) - c[AttendanceStatus.excused]
        return round(attended / countable * 100, 1) if countable else 0.0

    return AttendanceSummary(
        student_id=student_id,
        total_sessions=sum(counts.values()),
        present=counts[AttendanceStatus.present],
        late=counts[AttendanceStatus.late],
        absent=counts[AttendanceStatus.absent],
        excused=counts[AttendanceStatus.excused],
        percentage=pct(counts),
        by_session={k: pct(v) for k, v in per_session.items()},
    )
