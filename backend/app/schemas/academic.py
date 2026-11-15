from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import AttendanceSession, AttendanceStatus, Department, ExamType, StudentYear


# --- Attendance -------------------------------------------------------------

class AttendanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    date: date
    session: AttendanceSession
    status: AttendanceStatus


class AttendanceEntry(BaseModel):
    student_id: int
    status: AttendanceStatus


class AttendanceBulkCreate(BaseModel):
    """Mark one session for many students. Existing records for the same slot are updated."""

    date: date
    session: AttendanceSession
    entries: list[AttendanceEntry] = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def _check(self) -> "AttendanceBulkCreate":
        if self.date > date.today():
            raise ValueError("Cannot mark attendance for a future date")
        ids = [e.student_id for e in self.entries]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate student_id in entries")
        return self


class AttendanceSummary(BaseModel):
    student_id: int
    total_sessions: int
    present: int
    late: int
    absent: int
    excused: int
    percentage: float = Field(description="(present + late) / (total - excused) * 100")
    by_session: dict[str, float]


# --- Assessments ------------------------------------------------------------

class AssessmentCreate(BaseModel):
    student_id: int
    subject: str = Field(min_length=2, max_length=80)
    exam_type: ExamType
    marks: float = Field(ge=0)
    max_marks: float = Field(gt=0, le=1000)
    exam_date: date | None = None

    @model_validator(mode="after")
    def _check(self) -> "AssessmentCreate":
        if self.marks > self.max_marks:
            raise ValueError("marks cannot exceed max_marks")
        return self


class MarkEntry(BaseModel):
    student_id: int
    marks: float = Field(ge=0)


class AssessmentBulkCreate(BaseModel):
    """Record one exam for many students. Re-saving the same exam updates the marks (upsert)."""

    subject: str = Field(min_length=2, max_length=80)
    exam_type: ExamType
    max_marks: float = Field(gt=0, le=1000)
    exam_date: date
    entries: list[MarkEntry] = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def _check(self) -> "AssessmentBulkCreate":
        if self.exam_date > date.today():
            raise ValueError("exam_date cannot be in the future")
        ids = [e.student_id for e in self.entries]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate student_id in entries")
        over = [e.student_id for e in self.entries if e.marks > self.max_marks]
        if over:
            raise ValueError(f"marks exceed max_marks for student_id(s) {over}")
        return self


class AssessmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    subject: str
    exam_type: ExamType
    marks: float
    max_marks: float
    exam_date: date | None
    percentage: float


# --- Quotas -----------------------------------------------------------------

class QuotaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    department: Department
    year: StudentYear
    required_cases: int


class QuotaProgress(BaseModel):
    department: Department
    required: int
    approved: int
    pending: int = Field(description="Submitted, awaiting faculty review")
    remaining: int
    percent: float = Field(description="approved / required * 100, capped at 100")


class StudentQuotaProgress(BaseModel):
    student_id: int
    year: StudentYear
    is_clinical: bool
    departments: list[QuotaProgress]
    total_required: int
    total_approved: int
    overall_percent: float
