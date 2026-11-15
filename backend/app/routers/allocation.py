"""Smart patient allocation and department resource view (faculty/admin)."""
from datetime import date

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlmodel import select

from app.core.deps import SessionDep, StaffUser, get_faculty_profile
from app.models import Case, ClinicalQuota, Patient, Student
from app.models.enums import Department, Role
from app.schemas.allocation import AllocationAssign, AllocationRecommendation, ResourceView
from app.schemas.cases import CaseRead
from app.services import allocation as AL
from app.services import audit, notifications
from app.services.cases import load_case_read, validate_supervisor

router = APIRouter(prefix="/api/allocation", tags=["allocation"])


def _patient(session, patient_id: int) -> Patient:
    patient = session.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")
    return patient


@router.get("/recommendations", response_model=AllocationRecommendation,
            summary="Top students for a patient in a department, ranked by quota gap, workload, pace and year")
def recommendations(
    session: SessionDep,
    _staff: StaffUser,
    patient_id: int,
    department: Department,
    limit: int = Query(default=5, ge=1, le=20),
):
    return AL.recommend(session, _patient(session, patient_id), department, limit)


@router.post("/assign", response_model=CaseRead, status_code=status.HTTP_201_CREATED,
             summary="Assign the patient to a student: creates a draft case for that student")
def assign(body: AllocationAssign, session: SessionDep, user: StaffUser, request: Request):
    _patient(session, body.patient_id)
    student = session.get(Student, body.student_id)
    if student is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Student not found")
    quota = session.exec(select(ClinicalQuota).where(
        ClinicalQuota.department == body.department, ClinicalQuota.year == student.year,
        ClinicalQuota.required_cases > 0)).first()
    if quota is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            f"{student.year.value} students do not take {body.department.value} cases")

    if body.faculty_id is not None:
        faculty = validate_supervisor(session, body.faculty_id, body.department)
    else:
        me = get_faculty_profile(session, user) if user.role == Role.faculty else None
        faculty = me if me and me.department == body.department else AL.pick_supervisor(session, body.department)

    case = Case(patient_id=body.patient_id, student_id=student.id, faculty_id=faculty.id,
                department=body.department, visit_date=date.today(), chief_complaint=body.chief_complaint.strip())
    session.add(case)
    session.flush()
    audit.record(session, user, "allocate", "case", case.id,
                 f"Allocated patient #{case.patient_id} to student #{student.id} ({body.department.value})", request)
    notifications.patient_allocated(session, case, user)
    session.commit()
    return load_case_read(session, case.id)


@router.get("/resources", response_model=ResourceView,
            summary="Department case load vs faculty availability, highlighting overloaded departments")
def resources(session: SessionDep, _staff: StaffUser, days: int = Query(default=30, ge=7, le=365)):
    return AL.resources(session, days)
