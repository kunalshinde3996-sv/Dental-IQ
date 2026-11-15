"""Case serialisation and access rules shared by the case/student/faculty routers."""
from collections.abc import Sequence

from fastapi import HTTPException, status
from sqlalchemy.orm import aliased
from sqlmodel import Session, select

from app.models import Case, Faculty, Patient, Student, User
from app.models.enums import CaseStatus, Role
from app.schemas.cases import CaseRead, ToothFindingRead

EDITABLE_STATUSES = (CaseStatus.draft, CaseStatus.rejected)

StudentUser = aliased(User)
FacultyUser = aliased(User)


def case_query():
    """SELECT Case with patient, student and faculty names in one round trip."""
    return (
        select(Case, Patient.name, Patient.opd_number, StudentUser.name, Student.roll_no, FacultyUser.name)
        .join(Patient, Patient.id == Case.patient_id)
        .join(Student, Student.id == Case.student_id)
        .join(StudentUser, StudentUser.id == Student.user_id)
        .join(Faculty, Faculty.id == Case.faculty_id)
        .join(FacultyUser, FacultyUser.id == Faculty.user_id)
    )


def to_case_read(row: Sequence) -> CaseRead:
    case, patient_name, opd, student_name, roll_no, faculty_name = row
    return CaseRead(
        id=case.id,
        patient_id=case.patient_id,
        patient_name=patient_name,
        patient_opd_number=opd,
        student_id=case.student_id,
        student_name=student_name,
        student_roll_no=roll_no,
        faculty_id=case.faculty_id,
        faculty_name=faculty_name,
        department=case.department,
        visit_date=case.visit_date,
        chief_complaint=case.chief_complaint,
        diagnosis=case.diagnosis,
        procedure=case.procedure,
        status=case.status,
        faculty_remarks=case.faculty_remarks,
        submitted_at=case.submitted_at,
        reviewed_at=case.reviewed_at,
        created_at=case.created_at,
        updated_at=case.updated_at,
        findings=[ToothFindingRead.model_validate(f) for f in sorted(case.findings, key=lambda f: f.tooth_number)],
    )


def load_case_read(session: Session, case_id: int) -> CaseRead:
    row = session.exec(case_query().where(Case.id == case_id)).first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found")
    return to_case_read(row)


def get_case_or_404(session: Session, case_id: int) -> Case:
    case = session.get(Case, case_id)
    if case is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found")
    return case


def ensure_can_view(session: Session, user: User, case: Case) -> None:
    """Students may only see their own cases; staff can see all."""
    if user.role == Role.student:
        student = session.exec(select(Student).where(Student.user_id == user.id)).first()
        if student is None or case.student_id != student.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found")


def ensure_owner_can_edit(student: Student, case: Case) -> None:
    if case.student_id != student.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found")
    if case.status not in EDITABLE_STATUSES:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Case is '{case.status.value}' and can no longer be edited (only draft or rejected cases can)",
        )


def validate_supervisor(session: Session, faculty_id: int, department) -> Faculty:
    faculty = session.get(Faculty, faculty_id)
    if faculty is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Supervising faculty not found")
    if faculty.department != department:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Supervising faculty belongs to '{faculty.department.value}', not '{department.value}'",
        )
    return faculty
