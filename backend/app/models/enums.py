"""Domain enumerations.

Member names deliberately equal their values (lower-case) so the database
stores human-readable strings, which keeps Phase-2 SQL analytics simple.
"""
from enum import Enum


class Role(str, Enum):
    admin = "admin"
    faculty = "faculty"
    student = "student"


class StudentYear(str, Enum):
    bds1 = "bds1"
    bds2 = "bds2"
    bds3 = "bds3"
    bds4 = "bds4"
    intern = "intern"


#: Years with clinical postings (BDS 1-2 are pre-clinical in the DCI curriculum).
CLINICAL_YEARS = (StudentYear.bds3, StudentYear.bds4, StudentYear.intern)


class Department(str, Enum):
    oral_medicine = "oral_medicine"
    conservative = "conservative"
    endodontics = "endodontics"
    periodontics = "periodontics"
    prosthodontics = "prosthodontics"
    oral_surgery = "oral_surgery"
    pedodontics = "pedodontics"
    orthodontics = "orthodontics"


class Sex(str, Enum):
    male = "male"
    female = "female"
    other = "other"


class Taluka(str, Enum):
    """The 12 talukas of Goa (North Goa + South Goa districts)."""

    # North Goa
    pernem = "pernem"
    bardez = "bardez"
    tiswadi = "tiswadi"
    bicholim = "bicholim"
    sattari = "sattari"
    ponda = "ponda"
    # South Goa
    mormugao = "mormugao"
    salcete = "salcete"
    quepem = "quepem"
    sanguem = "sanguem"
    canacona = "canacona"
    dharbandora = "dharbandora"


class HabitStatus(str, Enum):
    never = "never"
    former = "former"
    current = "current"


class CaseStatus(str, Enum):
    draft = "draft"
    submitted = "submitted"
    approved = "approved"
    rejected = "rejected"


class ToothCondition(str, Enum):
    sound = "sound"
    caries = "caries"
    missing = "missing"
    filled = "filled"
    rct = "rct"
    crown = "crown"
    mobility = "mobility"
    lesion = "lesion"
    fractured = "fractured"
    impacted = "impacted"
    extraction_indicated = "extraction_indicated"


class AttendanceSession(str, Enum):
    theory = "theory"
    practical = "practical"
    clinic = "clinic"


class AttendanceStatus(str, Enum):
    present = "present"
    absent = "absent"
    late = "late"
    excused = "excused"


class ExamType(str, Enum):
    internal = "internal"
    sessional = "sessional"
    practical = "practical"
    viva = "viva"
    university = "university"
