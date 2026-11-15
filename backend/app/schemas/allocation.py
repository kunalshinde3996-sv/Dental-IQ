from pydantic import BaseModel, Field

from app.models.enums import Department, StudentYear


class AllocationCandidate(BaseModel):
    student_id: int
    name: str
    roll_no: str
    year: StudentYear
    score: float
    components: dict[str, float]
    approved: int
    required: int
    remaining: int
    pending: int
    open_cases: int
    recent_attendance_pct: float | None
    available: bool
    reasons: list[str]


class AllocationRecommendation(BaseModel):
    patient_id: int
    patient_name: str
    department: Department
    eligible_count: int
    eligible_years: list[str]
    candidates: list[AllocationCandidate]
    weights: dict[str, float]
    warnings: list[str]


class AllocationAssign(BaseModel):
    patient_id: int
    department: Department
    student_id: int
    chief_complaint: str = Field(min_length=3, max_length=500)
    faculty_id: int | None = Field(default=None, description="Supervisor; defaults to the caller (if faculty "
                                   "of that department) or the department member with the fewest pending reviews")


class DepartmentLoad(BaseModel):
    department: Department
    faculty: int
    cases: int
    cases_per_faculty: float | None
    pending_reviews: int
    pending_per_faculty: float | None
    eligible_students: int
    quota_remaining: int
    weeks_to_clear_quota: float | None
    load_index: float | None
    status: str  # overloaded | short_supply | balanced | spare_capacity
    reasons: list[str]


class ResourceView(BaseModel):
    days: int
    mean_cases_per_faculty: float
    departments: list[DepartmentLoad]
