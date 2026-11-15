"""Academic records: attendance, assessments, clinical quotas."""
import datetime as dt

from sqlmodel import Field, SQLModel, UniqueConstraint

from app.models.enums import (
    AttendanceSession,
    AttendanceStatus,
    Department,
    ExamType,
    StudentYear,
)


class Attendance(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("student_id", "date", "session"),)

    id: int | None = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="student.id", index=True, ondelete="CASCADE")
    date: dt.date = Field(index=True)
    session: AttendanceSession
    status: AttendanceStatus


class Assessment(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="student.id", index=True, ondelete="CASCADE")
    subject: str = Field(max_length=80, index=True)
    exam_type: ExamType
    marks: float
    max_marks: float
    exam_date: dt.date | None = None


class ClinicalQuota(SQLModel, table=True):
    """Minimum number of approved cases a student of `year` must log in `department`."""

    __tablename__ = "clinical_quota"
    __table_args__ = (UniqueConstraint("department", "year"),)

    id: int | None = Field(default=None, primary_key=True)
    department: Department
    year: StudentYear
    required_cases: int
