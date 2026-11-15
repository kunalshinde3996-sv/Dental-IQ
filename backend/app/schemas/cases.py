from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import CaseStatus, Department, ToothCondition

#: Valid permanent-dentition FDI numbers: quadrants 1-4, teeth 1-8.
FDI_PERMANENT = frozenset(q * 10 + t for q in range(1, 5) for t in range(1, 9))
_SURFACE_CODES = set("MODBLIF")  # mesial, occlusal, distal, buccal, lingual, incisal, facial


class ToothFindingIn(BaseModel):
    tooth_number: int = Field(description="FDI notation, 11-48")
    condition: ToothCondition
    surfaces: str | None = Field(default=None, description="Combination of M,O,D,B,L,I,F e.g. 'MOD'")
    treatment: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("tooth_number")
    @classmethod
    def _fdi(cls, v: int) -> int:
        if v not in FDI_PERMANENT:
            raise ValueError("tooth_number must be a valid FDI permanent tooth (11-18, 21-28, 31-38, 41-48)")
        return v

    @field_validator("surfaces")
    @classmethod
    def _surfaces(cls, v: str | None) -> str | None:
        if v is None or not v.strip():
            return None
        v = v.strip().upper()
        if not set(v) <= _SURFACE_CODES or len(set(v)) != len(v) or len(v) > 5:
            raise ValueError("surfaces must be unique letters from M,O,D,B,L,I,F (max 5)")
        return v


class ToothFindingRead(ToothFindingIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: int


def _unique_teeth(findings: list[ToothFindingIn] | None) -> None:
    if findings:
        teeth = [f.tooth_number for f in findings]
        if len(teeth) != len(set(teeth)):
            raise ValueError("Each tooth may appear only once per case")


class CaseCreate(BaseModel):
    patient_id: int
    faculty_id: int = Field(description="Supervising faculty (must belong to the case department)")
    department: Department
    visit_date: date = Field(default_factory=date.today)
    chief_complaint: str = Field(min_length=3, max_length=500)
    diagnosis: str | None = Field(default=None, max_length=500)
    procedure: str | None = Field(default=None, max_length=500)
    findings: list[ToothFindingIn] = Field(default_factory=list, max_length=32)
    submit: bool = Field(default=False, description="Submit for approval immediately instead of saving a draft")

    @model_validator(mode="after")
    def _check(self) -> "CaseCreate":
        _unique_teeth(self.findings)
        if self.visit_date > date.today():
            raise ValueError("visit_date cannot be in the future")
        return self


class CaseUpdate(BaseModel):
    """Editable while the case is a draft or was rejected. ``findings`` (if given) replaces all findings."""

    faculty_id: int | None = None
    department: Department | None = None
    visit_date: date | None = None
    chief_complaint: str | None = Field(default=None, min_length=3, max_length=500)
    diagnosis: str | None = Field(default=None, max_length=500)
    procedure: str | None = Field(default=None, max_length=500)
    findings: list[ToothFindingIn] | None = Field(default=None, max_length=32)

    @model_validator(mode="after")
    def _check(self) -> "CaseUpdate":
        _unique_teeth(self.findings)
        if self.visit_date and self.visit_date > date.today():
            raise ValueError("visit_date cannot be in the future")
        return self


class CaseReview(BaseModel):
    decision: Literal["approve", "reject"]
    remarks: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def _remarks_on_reject(self) -> "CaseReview":
        if self.decision == "reject" and not (self.remarks and self.remarks.strip()):
            raise ValueError("Remarks are required when rejecting a case")
        return self


class CaseRead(BaseModel):
    id: int
    patient_id: int
    patient_name: str
    patient_opd_number: str
    student_id: int
    student_name: str
    student_roll_no: str
    faculty_id: int
    faculty_name: str
    department: Department
    visit_date: date
    chief_complaint: str
    diagnosis: str | None
    procedure: str | None
    status: CaseStatus
    faculty_remarks: str | None
    submitted_at: datetime | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    findings: list[ToothFindingRead]
