"""Clinical cases: create (student), edit/submit (owner), review (supervising faculty)."""
from datetime import date

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func
from sqlmodel import select

from app.core.deps import CurrentFaculty, CurrentStudent, CurrentUser, SessionDep, get_student_profile
from app.models import Case, Patient, ToothFinding
from app.models._base import utcnow
from app.models.enums import CaseStatus, Department, Role
from app.schemas.cases import CaseCreate, CaseRead, CaseReview, CaseUpdate, ToothFindingIn, ToothFindingRead
from app.schemas.common import Page
from app.services.cases import (
    case_query,
    ensure_can_view,
    ensure_owner_can_edit,
    get_case_or_404,
    load_case_read,
    to_case_read,
    validate_supervisor,
)

router = APIRouter(prefix="/api/cases", tags=["cases"])


def _replace_findings(case: Case, findings: list[ToothFindingIn]) -> None:
    case.findings.clear()
    for f in findings:
        case.findings.append(ToothFinding(**f.model_dump()))


def _require_complete_for_submit(case: Case) -> None:
    missing = [name for name in ("diagnosis", "procedure") if not (getattr(case, name) or "").strip()]
    if missing:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Cannot submit: {', '.join(missing)} required. Save as draft or complete the case.",
        )


@router.get("", response_model=Page[CaseRead], summary="List cases (students see only their own)")
def list_cases(
    session: SessionDep,
    user: CurrentUser,
    status_: CaseStatus | None = Query(default=None, alias="status"),
    department: Department | None = None,
    student_id: int | None = None,
    faculty_id: int | None = None,
    patient_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    filters = []
    if user.role == Role.student:
        own = get_student_profile(session, user)
        if own is None or (student_id is not None and student_id != own.id):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Students can only list their own cases")
        student_id = own.id
    if status_:
        filters.append(Case.status == status_)
    if department:
        filters.append(Case.department == department)
    if student_id is not None:
        filters.append(Case.student_id == student_id)
    if faculty_id is not None:
        filters.append(Case.faculty_id == faculty_id)
    if patient_id is not None:
        filters.append(Case.patient_id == patient_id)
    if date_from:
        filters.append(Case.visit_date >= date_from)
    if date_to:
        filters.append(Case.visit_date <= date_to)

    total = session.exec(select(func.count()).select_from(Case).where(*filters)).one()
    rows = session.exec(
        case_query().where(*filters).order_by(Case.visit_date.desc(), Case.id.desc()).offset(offset).limit(limit)
    ).all()
    return Page(items=[to_case_read(r) for r in rows], total=total, limit=limit, offset=offset)


@router.post("", response_model=CaseRead, status_code=status.HTTP_201_CREATED,
             summary="Create a case (student). One entry feeds patient EHR + competency log")
def create_case(body: CaseCreate, session: SessionDep, student: CurrentStudent):
    if session.get(Patient, body.patient_id) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Patient not found")
    validate_supervisor(session, body.faculty_id, body.department)

    case = Case(**body.model_dump(exclude={"findings", "submit"}), student_id=student.id)
    _replace_findings(case, body.findings)
    if body.submit:
        _require_complete_for_submit(case)
        case.status = CaseStatus.submitted
        case.submitted_at = utcnow()
    session.add(case)
    session.commit()
    return load_case_read(session, case.id)


@router.get("/{case_id}", response_model=CaseRead, summary="Get one case with tooth findings")
def get_case(case_id: int, session: SessionDep, user: CurrentUser):
    case = get_case_or_404(session, case_id)
    ensure_can_view(session, user, case)
    return load_case_read(session, case_id)


@router.patch("/{case_id}", response_model=CaseRead, summary="Edit a draft/rejected case (owner only)")
def update_case(case_id: int, body: CaseUpdate, session: SessionDep, student: CurrentStudent):
    case = get_case_or_404(session, case_id)
    ensure_owner_can_edit(student, case)
    changes = body.model_dump(exclude_unset=True, exclude={"findings"})
    for required in ("faculty_id", "department", "visit_date", "chief_complaint"):
        if required in changes and changes[required] is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"'{required}' cannot be null")
    for key, value in changes.items():
        setattr(case, key, value)
    if "faculty_id" in changes or "department" in changes:
        validate_supervisor(session, case.faculty_id, case.department)
    if body.findings is not None:
        _replace_findings(case, body.findings)
    case.updated_at = utcnow()
    session.add(case)
    session.commit()
    return load_case_read(session, case.id)


@router.post("/{case_id}/submit", response_model=CaseRead, summary="Submit a draft/rejected case for approval")
def submit_case(case_id: int, session: SessionDep, student: CurrentStudent):
    case = get_case_or_404(session, case_id)
    ensure_owner_can_edit(student, case)
    _require_complete_for_submit(case)
    case.status = CaseStatus.submitted
    case.submitted_at = case.updated_at = utcnow()
    session.add(case)
    session.commit()
    return load_case_read(session, case.id)


@router.post("/{case_id}/review", response_model=CaseRead,
             summary="Approve or reject a submitted case (supervising faculty)")
def review_case(case_id: int, body: CaseReview, session: SessionDep, faculty: CurrentFaculty):
    case = get_case_or_404(session, case_id)
    if case.faculty_id != faculty.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the supervising faculty can review this case")
    if case.status != CaseStatus.submitted:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Only submitted cases can be reviewed (status: {case.status.value})")
    case.status = CaseStatus.approved if body.decision == "approve" else CaseStatus.rejected
    case.faculty_remarks = (body.remarks or "").strip() or None
    case.reviewed_at = case.updated_at = utcnow()
    session.add(case)
    session.commit()
    return load_case_read(session, case.id)


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a draft case (owner only)")
def delete_case(case_id: int, session: SessionDep, student: CurrentStudent) -> None:
    case = get_case_or_404(session, case_id)
    ensure_owner_can_edit(student, case)
    if case.status != CaseStatus.draft:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only draft cases can be deleted")
    session.delete(case)
    session.commit()


# --- Tooth findings within a case -------------------------------------------

@router.put("/{case_id}/findings", response_model=list[ToothFindingRead],
            summary="Replace all tooth findings of a case")
def replace_findings(case_id: int, body: list[ToothFindingIn], session: SessionDep, student: CurrentStudent):
    case = get_case_or_404(session, case_id)
    ensure_owner_can_edit(student, case)
    teeth = [f.tooth_number for f in body]
    if len(teeth) != len(set(teeth)):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Each tooth may appear only once per case")
    _replace_findings(case, body)
    case.updated_at = utcnow()
    session.add(case)
    session.commit()
    session.refresh(case)
    return sorted(case.findings, key=lambda f: f.tooth_number)


@router.post("/{case_id}/findings", response_model=ToothFindingRead, status_code=status.HTTP_201_CREATED,
             summary="Add or overwrite the finding for one tooth")
def upsert_finding(case_id: int, body: ToothFindingIn, session: SessionDep, student: CurrentStudent):
    case = get_case_or_404(session, case_id)
    ensure_owner_can_edit(student, case)
    finding = next((f for f in case.findings if f.tooth_number == body.tooth_number), None)
    if finding is None:
        finding = ToothFinding(case_id=case.id, **body.model_dump())
    else:
        for key, value in body.model_dump().items():
            setattr(finding, key, value)
    case.updated_at = utcnow()
    session.add_all([finding, case])
    session.commit()
    session.refresh(finding)
    return finding


@router.delete("/{case_id}/findings/{tooth_number}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Remove the finding for one tooth")
def delete_finding(case_id: int, tooth_number: int, session: SessionDep, student: CurrentStudent) -> None:
    case = get_case_or_404(session, case_id)
    ensure_owner_can_edit(student, case)
    finding = next((f for f in case.findings if f.tooth_number == tooth_number), None)
    if finding is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No finding for that tooth")
    case.findings.remove(finding)
    case.updated_at = utcnow()
    session.add(case)
    session.commit()
