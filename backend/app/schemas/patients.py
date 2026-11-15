import re
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import CaseStatus, Department, HabitStatus, Sex, Taluka

_ABHA_DIGITS = re.compile(r"^\d{14}$")
_PHONE = re.compile(r"^[6-9]\d{9}$")


def normalise_abha(value: str | None) -> str | None:
    """Accept 14 digits with or without separators; store as XX-XXXX-XXXX-XXXX."""
    if value is None or not value.strip():
        return None
    digits = re.sub(r"[\s-]", "", value)
    if not _ABHA_DIGITS.match(digits):
        raise ValueError("ABHA number must be 14 digits (e.g. 91-1234-5678-9012)")
    return f"{digits[:2]}-{digits[2:6]}-{digits[6:10]}-{digits[10:]}"


def normalise_phone(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    digits = re.sub(r"[\s-]", "", value)
    if digits.startswith("+91"):
        digits = digits[3:]
    if not _PHONE.match(digits):
        raise ValueError("Phone must be a 10-digit Indian mobile number")
    return digits


class PatientFields(BaseModel):
    abha_id: str | None = Field(default=None, description="14-digit ABHA number (optional)")
    name: str = Field(min_length=2, max_length=120)
    age: int = Field(ge=0, le=120)
    sex: Sex
    taluka: Taluka
    phone: str | None = None
    tobacco_smoking: HabitStatus = HabitStatus.never
    smokeless_tobacco: HabitStatus = Field(default=HabitStatus.never, description="gutkha / khaini / mishri")
    alcohol: HabitStatus = HabitStatus.never
    habit_duration_years: int | None = Field(default=None, ge=0, le=100)
    has_diabetes: bool = False
    has_hypertension: bool = False
    has_cardiac_disease: bool = False
    allergies: str | None = Field(default=None, max_length=255)
    medical_history_notes: str | None = Field(default=None, max_length=2000)


class _PatientInputValidators(BaseModel):
    @field_validator("abha_id", check_fields=False)
    @classmethod
    def _abha(cls, v: str | None) -> str | None:
        return normalise_abha(v)

    @field_validator("phone", check_fields=False)
    @classmethod
    def _phone(cls, v: str | None) -> str | None:
        return normalise_phone(v)

    @field_validator("name", check_fields=False)
    @classmethod
    def _name(cls, v: str | None) -> str | None:
        return " ".join(v.split()) if v else v


class PatientCreate(PatientFields, _PatientInputValidators):
    pass


class PatientUpdate(_PatientInputValidators):
    """Partial update: only fields present in the request body are changed."""

    abha_id: str | None = None
    name: str | None = Field(default=None, min_length=2, max_length=120)
    age: int | None = Field(default=None, ge=0, le=120)
    sex: Sex | None = None
    taluka: Taluka | None = None
    phone: str | None = None
    tobacco_smoking: HabitStatus | None = None
    smokeless_tobacco: HabitStatus | None = None
    alcohol: HabitStatus | None = None
    habit_duration_years: int | None = Field(default=None, ge=0, le=100)
    has_diabetes: bool | None = None
    has_hypertension: bool | None = None
    has_cardiac_disease: bool | None = None
    allergies: str | None = Field(default=None, max_length=255)
    medical_history_notes: str | None = Field(default=None, max_length=2000)


class PatientRead(PatientFields):
    model_config = ConfigDict(from_attributes=True)

    id: int
    opd_number: str
    is_synthetic: bool
    created_at: datetime


class PatientListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    opd_number: str
    abha_id: str | None
    name: str
    age: int
    sex: Sex
    taluka: Taluka
    phone: str | None
    tobacco_smoking: HabitStatus
    smokeless_tobacco: HabitStatus
    alcohol: HabitStatus
    last_visit: date | None = None
    visit_count: int = 0


class VisitSummary(BaseModel):
    id: int
    visit_date: date
    department: Department
    chief_complaint: str
    diagnosis: str | None
    procedure: str | None
    status: CaseStatus
    student_name: str
    faculty_name: str
    findings_count: int


class PatientDetail(PatientRead):
    visits: list[VisitSummary]


# --- Oral cancer risk screening (Phase 2) -----------------------------------------

class RiskScreeningRequest(BaseModel):
    lesion_observed: bool | None = Field(
        default=None,
        description="Set true if a mucosal lesion is seen at today's exam (e.g. while filling a new case). "
        "Lesions already recorded on the patient's cases are always included.",
    )


class RiskFactor(BaseModel):
    feature: str
    label: str
    value: float
    contribution: float = Field(description="Log-odds contribution relative to the reference patient")
    odds_multiplier: float
    direction: str


class RiskModelInfo(BaseModel):
    version: str
    trained_at: str
    auc_cv: float | None
    n_train: int
    thresholds: dict[str, float]


class RiskScreening(BaseModel):
    patient_id: int
    probability: float
    risk_percent: float
    risk_level: str = Field(description="Final level: Low / Medium / High (High whenever a PMD is on record)")
    model_risk_level: str = Field(description="Level from the model probability alone")
    baseline_probability: float
    factors: list[RiskFactor]
    lesion_observed: bool
    lesion_source: str = Field(description="recorded / override / none")
    known_pmd_diagnosis: bool
    suggested_action: str
    additional_actions: list[str]
    notes: list[str]
    model: RiskModelInfo
    disclaimer: str
