from fastapi import APIRouter, Query
from sqlalchemy import func
from sqlmodel import select

from app.core.deps import CurrentFaculty, CurrentUser, SessionDep
from app.models import Case, Faculty, User
from app.models.enums import CaseStatus, Department
from app.schemas.cases import CaseRead
from app.schemas.common import Page
from app.schemas.users import FacultyRead
from app.services.cases import case_query, to_case_read
from app.services.people import faculty_read

router = APIRouter(prefix="/api/faculty", tags=["faculty"])


@router.get("", response_model=list[FacultyRead],
            summary="List faculty (any role; students use it to pick a supervisor)")
def list_faculty(session: SessionDep, _user: CurrentUser, department: Department | None = None):
    stmt = select(Faculty, User).join(User, User.id == Faculty.user_id)
    if department:
        stmt = stmt.where(Faculty.department == department)
    rows = session.exec(stmt.order_by(Faculty.department, User.name)).all()
    return [faculty_read(f, u) for f, u in rows]


@router.get("/me/pending-cases", response_model=Page[CaseRead],
            summary="Submitted cases awaiting this faculty member's review")
def pending_cases(
    session: SessionDep,
    faculty: CurrentFaculty,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    filters = [Case.faculty_id == faculty.id, Case.status == CaseStatus.submitted]
    total = session.exec(select(func.count()).select_from(Case).where(*filters)).one()
    rows = session.exec(
        # Oldest first: fair queue for students waiting on sign-off.
        case_query().where(*filters).order_by(Case.submitted_at, Case.id).offset(offset).limit(limit)
    ).all()
    return Page(items=[to_case_read(r) for r in rows], total=total, limit=limit, offset=offset)


@router.get("/me/reviewed-cases", response_model=Page[CaseRead], summary="Cases this faculty member has reviewed")
def reviewed_cases(
    session: SessionDep,
    faculty: CurrentFaculty,
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    filters = [Case.faculty_id == faculty.id, Case.status.in_([CaseStatus.approved, CaseStatus.rejected])]
    total = session.exec(select(func.count()).select_from(Case).where(*filters)).one()
    rows = session.exec(
        case_query().where(*filters).order_by(Case.reviewed_at.desc(), Case.id.desc()).offset(offset).limit(limit)
    ).all()
    return Page(items=[to_case_read(r) for r in rows], total=total, limit=limit, offset=offset)
