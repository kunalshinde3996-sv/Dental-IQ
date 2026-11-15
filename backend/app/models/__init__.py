"""Database models. Importing this package registers every table with SQLModel."""
from app.models.academic import Assessment, Attendance, ClinicalQuota
from app.models.case import Case, ToothFinding
from app.models.patient import Patient
from app.models.security import AuditEvent, Notification, RevokedToken
from app.models.user import Faculty, Student, User

__all__ = [
    "Assessment",
    "Attendance",
    "AuditEvent",
    "Case",
    "ClinicalQuota",
    "Faculty",
    "Notification",
    "Patient",
    "RevokedToken",
    "Student",
    "ToothFinding",
    "User",
]
