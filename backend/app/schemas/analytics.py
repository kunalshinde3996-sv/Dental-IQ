from datetime import date
from typing import Any

from pydantic import BaseModel

from app.models.enums import Department, Taluka


class PopulationFilters(BaseModel):
    date_from: date | None = None
    date_to: date | None = None
    taluka: Taluka | None = None
    department: Department | None = None


class PopulationSummary(BaseModel):
    patients: int
    cases: int
    pmd_patients: int
    caries_patients: int
    abha_linked_pct: float
    adult_current_tobacco_pct: float


class TalukaBurden(BaseModel):
    taluka: Taluka
    patients: int
    cases: int
    counts: dict[str, int]
    prevalence_pct: dict[str, float]


class HabitAssociation(BaseModel):
    habit: str
    habit_label: str
    outcome: str
    outcome_label: str
    exposed_n: int
    exposed_cases: int
    exposed_pct: float
    unexposed_n: int
    unexposed_cases: int
    unexposed_pct: float
    prevalence_ratio: float | None
    ci_low: float | None
    ci_high: float | None


class SexCell(BaseModel):
    patients: int
    caries: int
    pct: float


class CariesAgeSex(BaseModel):
    age_group: str
    male: SexCell
    female: SexCell


class TermCount(BaseModel):
    term: str
    count: int
    pct: float


class TopTerms(BaseModel):
    diagnoses: list[TermCount]
    procedures: list[TermCount]


class Insight(BaseModel):
    id: str
    tone: str  # critical | warning | info
    title: str
    text: str
    action: str
    evidence: dict[str, Any]


class PopulationReport(BaseModel):
    filters: PopulationFilters
    summary: PopulationSummary
    taluka_burden: list[TalukaBurden]
    habit_associations: list[HabitAssociation]
    caries_by_age_sex: list[CariesAgeSex]
    monthly_trend: list[dict[str, Any]]  # {month, total, <department>: count, ...}
    top_terms: TopTerms
    insights: list[Insight]
    condition_labels: dict[str, str]
