"""Population oral-health intelligence (faculty/admin only)."""
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.deps import SessionDep, StaffUser
from app.models.enums import Department, Taluka
from app.schemas.analytics import (
    CariesAgeSex,
    HabitAssociation,
    Insight,
    PopulationReport,
    TalukaBurden,
    TopTerms,
)
from app.services import analytics as A

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def population_filters(
    date_from: date | None = None,
    date_to: date | None = None,
    taluka: Taluka | None = None,
    department: Department | None = None,
) -> A.Filters:
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "date_from must be on or before date_to")
    return A.Filters(date_from, date_to, taluka, department)


FiltersDep = Annotated[A.Filters, Depends(population_filters)]


@router.get("/population", response_model=PopulationReport,
            summary="Full population report (all sections + key insights) for the given filters")
def population(session: SessionDep, _staff: StaffUser, filters: FiltersDep):
    return A.population_report(session, filters)


@router.get("/taluka-burden", response_model=list[TalukaBurden], summary="Disease burden by Goa taluka")
def taluka_burden(session: SessionDep, _staff: StaffUser, filters: FiltersDep):
    return A.taluka_burden(A.load_dataset(session, filters))


@router.get("/habit-associations", response_model=list[HabitAssociation],
            summary="Tobacco / gutkha / alcohol vs OSMF, leukoplakia and oral lesions (prevalence ratios)")
def habit_associations(session: SessionDep, _staff: StaffUser, filters: FiltersDep):
    return A.habit_associations(A.load_dataset(session, filters))


@router.get("/caries", response_model=list[CariesAgeSex], summary="Caries prevalence by age group and sex")
def caries(session: SessionDep, _staff: StaffUser, filters: FiltersDep):
    return A.caries_by_age_sex(A.load_dataset(session, filters))


@router.get("/case-trend", summary="Monthly case counts per department")
def case_trend(session: SessionDep, _staff: StaffUser, filters: FiltersDep) -> list[dict]:
    return A.monthly_trend(A.load_dataset(session, filters))


@router.get("/top-terms", response_model=TopTerms, summary="Most frequent diagnoses and procedures")
def top_terms(session: SessionDep, _staff: StaffUser, filters: FiltersDep,
              limit: int = Query(default=10, ge=1, le=50)):
    return A.top_terms(A.load_dataset(session, filters), limit)


@router.get("/insights", response_model=list[Insight], summary="Auto-generated plain-language key insights")
def insights(session: SessionDep, _staff: StaffUser, filters: FiltersDep):
    return A.key_insights(A.load_dataset(session, filters))
