from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import func
from sqlmodel import select

from app.core.deps import AdminUser, SessionDep
from app.models import Case, Faculty, Patient, Student
from app.models.enums import CaseStatus

router = APIRouter(prefix="/api/admin", tags=["admin"])


class AdminStats(BaseModel):
    students: int
    faculty: int
    patients: int
    cases: int
    cases_by_status: dict[str, int]


@router.get("/stats", response_model=AdminStats, summary="Headline counts for the admin home page")
def stats(session: SessionDep, _admin: AdminUser) -> AdminStats:
    def count(model) -> int:
        return session.exec(select(func.count()).select_from(model)).one()

    by_status = dict(session.exec(select(Case.status, func.count()).group_by(Case.status)).all())
    return AdminStats(
        students=count(Student),
        faculty=count(Faculty),
        patients=count(Patient),
        cases=count(Case),
        cases_by_status={s.value: by_status.get(s, 0) for s in CaseStatus},
    )
