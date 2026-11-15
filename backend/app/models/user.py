"""Users and their role-specific profiles (Student / Faculty)."""
from datetime import datetime

from sqlmodel import Field, SQLModel

from app.models._base import UTCDateTime, utcnow
from app.models.enums import Department, Role, StudentYear


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=120)
    email: str = Field(max_length=255, unique=True, index=True)
    password_hash: str = Field(max_length=255)
    role: Role = Field(index=True)
    is_active: bool = True
    created_at: datetime = Field(default_factory=utcnow, sa_type=UTCDateTime)


class Student(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True, ondelete="CASCADE")
    roll_no: str = Field(max_length=30, unique=True, index=True)
    year: StudentYear = Field(index=True)
    batch: str = Field(max_length=20, description="Admission batch, e.g. '2022-27'")


class Faculty(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True, ondelete="CASCADE")
    department: Department = Field(index=True)
    designation: str = Field(default="Lecturer", max_length=60)
