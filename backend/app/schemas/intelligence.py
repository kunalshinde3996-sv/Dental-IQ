from typing import Any

from pydantic import BaseModel

from app.models.enums import Department, StudentYear


class AlertReason(BaseModel):
    code: str
    severity: str  # critical | warning
    text: str


class ModelFactor(BaseModel):
    feature: str
    label: str
    contribution: float
    z_score: float
    direction: str


class WeeklyAttendance(BaseModel):
    weeks_ago: int
    pct: float | None


class StudentAlert(BaseModel):
    student_id: int
    name: str
    roll_no: str
    year: str
    risk_level: str  # High | Medium | Low
    score: float | None
    reasons: list[AlertReason]
    suggested_actions: list[str]
    model_factors: list[ModelFactor]
    signals: dict[str, Any]
    weekly_attendance: list[WeeklyAttendance]


class FocusItem(BaseModel):
    area: str
    title: str
    message: str


class FocusDepartment(BaseModel):
    department: Department
    approved: int
    required: int
    remaining: int
    pending: int
    percent: float
    case_types: list[str]
    where_to_find: str
    double_priority: bool


class SubjectPerformance(BaseModel):
    subject: str
    average_pct: float
    latest_pct: float
    trend: float | None
    exams: int
    related_department: Department | None
    tip: str


class LearningPlan(BaseModel):
    student_id: int
    year: StudentYear
    is_clinical: bool
    summary: str
    focus_departments: list[FocusDepartment]
    focus_subjects: list[SubjectPerformance]
    all_subjects: list[SubjectPerformance]


class FocusAreas(BaseModel):
    student_id: int
    on_track: bool
    items: list[FocusItem]
    strengths: list[str]
    summary: str
