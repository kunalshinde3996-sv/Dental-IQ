from datetime import date
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import func, or_
from sqlmodel import col, select

from app.core.deps import AdminUser, CurrentUser, SessionDep
from app.models import Case, Patient
from app.models.enums import Taluka
from app.schemas.common import Page
from app.schemas.patients import (
    PatientCreate,
    PatientDetail,
    PatientListItem,
    PatientRead,
    PatientUpdate,
    RiskScreening,
    RiskScreeningRequest,
    VisitSummary,
)
from app.services import audit
from app.services.cases import case_query

router = APIRouter(prefix="/api/patients", tags=["patients"])


def _get_or_404(session, patient_id: int) -> Patient:
    patient = session.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")
    return patient


def _ensure_abha_unique(session, abha_id: str | None, exclude_id: int | None = None) -> None:
    if not abha_id:
        return
    existing = session.exec(select(Patient).where(Patient.abha_id == abha_id)).first()
    if existing and existing.id != exclude_id:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"ABHA ID already registered to patient {existing.opd_number}",
        )


@router.get("", response_model=Page[PatientListItem], summary="Search / list patients")
def list_patients(
    session: SessionDep,
    _user: CurrentUser,
    q: str | None = Query(default=None, max_length=100, description="Name, OPD no., ABHA ID or phone"),
    taluka: Taluka | None = None,
    limit: int = Query(default=25, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    filters = []
    if q and q.strip():
        term = f"%{q.strip().lower()}%"
        filters.append(or_(
            func.lower(Patient.name).like(term),
            func.lower(Patient.opd_number).like(term),
            col(Patient.abha_id).like(term),
            col(Patient.phone).like(term),
        ))
    if taluka:
        filters.append(Patient.taluka == taluka)

    total = session.exec(select(func.count()).select_from(Patient).where(*filters)).one()

    visits = (
        select(Case.patient_id, func.max(Case.visit_date).label("last_visit"), func.count(Case.id).label("n"))
        .group_by(Case.patient_id)
        .subquery()
    )
    rows = session.exec(
        select(Patient, visits.c.last_visit, visits.c.n)
        .outerjoin(visits, visits.c.patient_id == Patient.id)
        .where(*filters)
        .order_by(visits.c.last_visit.desc().nulls_last(), Patient.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()

    items = []
    for patient, last_visit, n in rows:
        item = PatientListItem.model_validate(patient)
        item.last_visit = date.fromisoformat(last_visit) if isinstance(last_visit, str) else last_visit
        item.visit_count = n or 0
        items.append(item)
    return Page(items=items, total=total, limit=limit, offset=offset)


@router.post("", response_model=PatientRead, status_code=status.HTTP_201_CREATED, summary="Register a patient")
def create_patient(body: PatientCreate, session: SessionDep, user: CurrentUser, request: Request):
    _ensure_abha_unique(session, body.abha_id)
    patient = Patient(**body.model_dump(), opd_number=f"TMP-{uuid4().hex[:12]}")
    session.add(patient)
    session.flush()  # assign id
    patient.opd_number = f"GDC-{date.today().year}-{patient.id:06d}"
    audit.record(session, user, "create", "patient", patient.id, f"Registered patient {patient.opd_number}", request)
    session.commit()
    session.refresh(patient)
    return patient


@router.get("/{patient_id}", response_model=PatientDetail, summary="Patient profile with full visit history")
def get_patient(patient_id: int, session: SessionDep, user: CurrentUser, request: Request):
    patient = _get_or_404(session, patient_id)
    audit.record_view(session, user, "patient", patient.id, f"Viewed patient record {patient.opd_number}", request)
    rows = session.exec(
        case_query().where(Case.patient_id == patient_id).order_by(Case.visit_date.desc(), Case.id.desc())
    ).all()
    visits = [
        VisitSummary(
            id=c.id, visit_date=c.visit_date, department=c.department, chief_complaint=c.chief_complaint,
            diagnosis=c.diagnosis, procedure=c.procedure, status=c.status,
            student_name=student_name, faculty_name=faculty_name, findings_count=len(c.findings),
        )
        for c, _pn, _opd, student_name, _roll, faculty_name in rows
    ]
    return PatientDetail(**PatientRead.model_validate(patient).model_dump(), visits=visits)


@router.patch("/{patient_id}", response_model=PatientRead, summary="Update patient details")
def update_patient(patient_id: int, body: PatientUpdate, session: SessionDep, user: CurrentUser,
                   request: Request):
    patient = _get_or_404(session, patient_id)
    changes = body.model_dump(exclude_unset=True)
    for required in ("name", "age", "sex", "taluka"):
        if required in changes and changes[required] is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"'{required}' cannot be null")
    if "abha_id" in changes:
        _ensure_abha_unique(session, changes["abha_id"], exclude_id=patient.id)
    for key, value in changes.items():
        setattr(patient, key, value)
    session.add(patient)
    fields = ", ".join(sorted(changes)) or "no fields"
    audit.record(session, user, "update", "patient", patient.id, f"Edited {patient.opd_number}: {fields}", request)
    session.commit()
    session.refresh(patient)
    return patient


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete patient (admin only)")
def delete_patient(patient_id: int, session: SessionDep, admin: AdminUser, request: Request) -> None:
    patient = _get_or_404(session, patient_id)
    # ORM cascade on Case.findings removes tooth findings with each case.
    for case in session.exec(select(Case).where(Case.patient_id == patient_id)).all():
        session.delete(case)
    audit.record(session, admin, "delete", "patient", patient.id,
                 f"Deleted patient {patient.opd_number} and their cases", request)
    session.delete(patient)
    session.commit()


@router.post("/{patient_id}/risk-screening", response_model=RiskScreening,
             summary="Oral cancer / PMD risk screening with explanation and suggested action")
def risk_screening(patient_id: int, session: SessionDep, user: CurrentUser, request: Request,
                   body: RiskScreeningRequest | None = None):
    from ml.oral_risk import screen  # imported lazily: keeps app start-up light

    patient = _get_or_404(session, patient_id)
    try:
        result = screen(session, patient, body.lesion_observed if body else None)
    except FileNotFoundError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from None
    audit.record_view(session, user, "patient", patient.id,
                      f"Risk screening for {patient.opd_number}: {result['risk_level']}", request)
    return result
