from typing import Any

from pydantic import BaseModel


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


class FocusAreas(BaseModel):
    student_id: int
    on_track: bool
    items: list[FocusItem]
    strengths: list[str]
    summary: str
