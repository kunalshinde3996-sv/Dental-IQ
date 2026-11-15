"""Clinical case: one supervised patient visit.

A single Case row is the core of Dental-IQ. It is at once the patient's EHR
entry, the student's competency-log entry (once approved) and a data point
for population insights.
"""
from datetime import date, datetime

from sqlmodel import Field, Relationship, SQLModel

from app.models._base import UTCDateTime, utcnow
from app.models.enums import CaseStatus, Department, ToothCondition


class Case(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="patient.id", index=True, ondelete="CASCADE")
    student_id: int = Field(foreign_key="student.id", index=True)
    faculty_id: int = Field(foreign_key="faculty.id", index=True)
    department: Department = Field(index=True)

    visit_date: date = Field(index=True)
    chief_complaint: str = Field(max_length=500)
    diagnosis: str | None = Field(default=None, max_length=500)
    procedure: str | None = Field(default=None, max_length=500)

    status: CaseStatus = Field(default=CaseStatus.draft, index=True)
    faculty_remarks: str | None = Field(default=None, max_length=1000)
    submitted_at: datetime | None = Field(default=None, sa_type=UTCDateTime)
    reviewed_at: datetime | None = Field(default=None, sa_type=UTCDateTime)

    created_at: datetime = Field(default_factory=utcnow, sa_type=UTCDateTime)
    updated_at: datetime = Field(default_factory=utcnow, sa_type=UTCDateTime)

    findings: list["ToothFinding"] = Relationship(
        back_populates="case",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"},
    )


class ToothFinding(SQLModel, table=True):
    __tablename__ = "tooth_finding"

    id: int | None = Field(default=None, primary_key=True)
    case_id: int = Field(foreign_key="case.id", index=True, ondelete="CASCADE")
    # FDI two-digit notation: quadrant (1-4) + tooth (1-8), e.g. 36 = lower-left first molar.
    tooth_number: int = Field(index=True)
    condition: ToothCondition = Field(index=True)
    surfaces: str | None = Field(default=None, max_length=5, description="Any of M,O,D,B,L e.g. 'MOD'")
    treatment: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=500)

    case: Case | None = Relationship(back_populates="findings")
