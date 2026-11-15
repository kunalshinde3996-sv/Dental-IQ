"""Patient demographic + risk-factor record (the EHR header)."""
from datetime import datetime

from sqlmodel import Field, SQLModel

from app.models._base import utcnow
from app.models.enums import HabitStatus, Sex, Taluka


class Patient(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    # Hospital OPD registration number, e.g. "GDC-2026-000123".
    opd_number: str = Field(max_length=30, unique=True, index=True)
    # Ayushman Bharat Health Account number (14 digits, stored as XX-XXXX-XXXX-XXXX).
    # Optional, and the hook for ABDM M1/M2 record linking later.
    abha_id: str | None = Field(default=None, max_length=17, unique=True, index=True)

    name: str = Field(max_length=120, index=True)
    age: int
    sex: Sex
    taluka: Taluka = Field(index=True)
    phone: str | None = Field(default=None, max_length=15)

    # Oral-cancer risk factors, structured for population analytics.
    tobacco_smoking: HabitStatus = HabitStatus.never  # cigarette / bidi
    smokeless_tobacco: HabitStatus = HabitStatus.never  # gutkha / khaini / mishri
    alcohol: HabitStatus = HabitStatus.never
    habit_duration_years: int | None = None

    # Medical history: structured flags + free text.
    has_diabetes: bool = False
    has_hypertension: bool = False
    has_cardiac_disease: bool = False
    allergies: str | None = Field(default=None, max_length=255)
    medical_history_notes: str | None = Field(default=None, max_length=2000)

    is_synthetic: bool = Field(default=False, description="True for generated demo data")
    created_at: datetime = Field(default_factory=utcnow)
