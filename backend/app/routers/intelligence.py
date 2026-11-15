"""Student intelligence: explainable at-risk alerts (staff), personal focus areas and learning plan."""
from fastapi import APIRouter, HTTPException, Query, status

from app.core.deps import CurrentUser, SessionDep, StaffUser
from app.models.enums import StudentYear
from app.routers.students import resolve_student
from app.schemas.intelligence import FocusAreas, LearningPlan, StudentAlert
from app.services.learning import learning_plan as build_learning_plan
from ml import student_risk as SR
from ml.common import load_bundle

router = APIRouter(tags=["student intelligence"])


@router.get("/api/alerts/students", response_model=list[StudentAlert],
            summary="Explainable at-risk alerts for all students (rules + model), highest risk first")
def student_alerts(
    session: SessionDep,
    _staff: StaffUser,
    level: str | None = Query(default=None, pattern="^(High|Medium|Low)$"),
    year: StudentYear | None = None,
):
    alerts = SR.assess_all(session)
    if level:
        alerts = [a for a in alerts if a["risk_level"] == level]
    if year:
        alerts = [a for a in alerts if a["year"] == year.value]
    return alerts


@router.get("/api/students/{student_id}/risk", response_model=StudentAlert,
            summary="At-risk assessment for one student with reasons, actions and weekly attendance")
def student_risk_detail(student_id: int, session: SessionDep, _staff: StaffUser):
    signals = SR.compute_signals(session)
    if student_id not in signals:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Student not found")
    return SR.assess(signals[student_id], load_bundle(SR.MODEL_NAME))


@router.get("/api/students/{student_id}/focus-areas", response_model=FocusAreas,
            summary="Gentle personal focus areas (visible to the student themself)")
def focus_areas(student_id: int, session: SessionDep, user: CurrentUser):
    student = resolve_student(session, user, student_id)
    plan = build_learning_plan(session, student)
    priority = [d["department"] for d in plan["focus_departments"]]
    return SR.focus_areas(SR.compute_signals(session)[student_id], priority)


@router.get("/api/students/{student_id}/learning-plan", response_model=LearningPlan,
            summary="Personalised suggestions: weakest departments (quota gaps) and subjects (marks)")
def learning_plan(student_id: int, session: SessionDep, user: CurrentUser):
    return build_learning_plan(session, resolve_student(session, user, student_id))
