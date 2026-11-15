from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Department, Role, StudentYear


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: Role


class StudentRead(BaseModel):
    id: int
    user_id: int
    name: str
    email: str
    roll_no: str
    year: StudentYear
    batch: str


class FacultyRead(BaseModel):
    id: int
    user_id: int
    name: str
    email: str
    department: Department
    designation: str


class MeResponse(BaseModel):
    user: UserRead
    student: StudentRead | None = None
    faculty: FacultyRead | None = None


class TokenResponse(MeResponse):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
