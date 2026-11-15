"""Database models. Importing this package registers every table with SQLModel."""
from app.models.academic import Assessment, Attendance, ClinicalQuota
from app.models.case import Case, ToothFinding
from app.models.patient import Patient
from app.models.user import Faculty, Student, User

__all__ = [
    "Assessment",
    "Attendance",
    "Case",
    "ClinicalQuota",
    "Faculty",
    "Patient",
    "Student",
    "ToothFinding",
    "User",
]
