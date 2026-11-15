"""Personalised learning suggestions: weakest departments (quota gaps) and subjects (marks).

Uses the same quota service and assessment data as every other page, so the numbers match.
"""
from __future__ import annotations

import statistics
from collections import defaultdict

from sqlmodel import Session, select

from app.models import Assessment, Student
from app.models.enums import CLINICAL_YEARS, Department, ExamType
from app.services.quota import student_quota_progress

#: Kinds of cases to seek per department, and where such patients usually come from.
CASE_GUIDE: dict[Department, tuple[list[str], str]] = {
    Department.oral_medicine: (
        ["Comprehensive examination and charting of new OPD patients",
         "Tobacco / gutkha users for mucosal screening (OSMF, leukoplakia)",
         "IOPA and OPG interpretation"],
        "Spend OPD registration hours in Oral Medicine: every new patient is screened there first."),
    Department.conservative: (
        ["Class I and II composite / GIC restorations", "Class III anterior restorations",
         "Replacement of defective restorations"],
        "Ask Oral Medicine to refer patients with dentinal caries."),
    Department.endodontics: (
        ["Single-rooted anterior RCT (good first cases)", "Premolar RCT", "Molar RCT once anteriors are signed off"],
        "Patients with irreversible pulpitis or apical abscess referred from Oral Medicine."),
    Department.periodontics: (
        ["Full-mouth scaling and polishing", "Scaling and root planing", "Assisting in flap surgery"],
        "Most adult screening patients have gingivitis: request Periodontics referrals."),
    Department.prosthodontics: (
        ["Removable partial dentures (Kennedy Class III / IV)", "Complete dentures for elderly patients",
         "Crowns on endodontically treated teeth"],
        "Elderly patients, and your own completed RCT cases that need crowns."),
    Department.oral_surgery: (
        ["Simple extractions under LA", "Non-restorable, grossly decayed teeth",
         "Assisting in impaction surgery and biopsies"],
        "Extraction referrals from Oral Medicine and Periodontics (grade III mobility)."),
    Department.pedodontics: (
        ["Pit and fissure sealants", "Pulpotomy with stainless-steel crowns",
         "Restorations and fluoride varnish on primary teeth"],
        "School screening camps and the paediatric OPD."),
    Department.orthodontics: (
        ["Study models and diagnostic records", "Cephalometric tracing", "Removable appliance cases"],
        "Teenagers with crowding referred from Pedodontics and Oral Medicine."),
}

#: Subject -> department it maps to (theory supporting a clinical skill).
SUBJECT_DEPARTMENT: dict[str, Department] = {
    "Oral Medicine & Radiology": Department.oral_medicine,
    "Oral Pathology": Department.oral_medicine,
    "Conservative Dentistry & Endodontics": Department.endodontics,
    "Pre-clinical Conservative Dentistry": Department.conservative,
    "Periodontology": Department.periodontics,
    "Prosthodontics": Department.prosthodontics,
    "Pre-clinical Prosthodontics": Department.prosthodontics,
    "Oral & Maxillofacial Surgery": Department.oral_surgery,
    "Pedodontics": Department.pedodontics,
    "Orthodontics": Department.orthodontics,
}

EXAM_TIP: dict[ExamType, str] = {
    ExamType.practical: "Your weakest exam was the practical: book extra lab / clinic practice time.",
    ExamType.viva: "Your weakest exam was the viva: practise answering aloud with a peer.",
    ExamType.internal: "Your weakest exam was an internal: revise core topics early with past papers.",
    ExamType.sessional: "Your weakest exam was the sessional: build a weekly revision timetable.",
    ExamType.university: "Plan structured revision with your mentor before the university exam.",
}

WEAK_SUBJECT_PCT = 60.0
MAX_ITEMS = 3


def learning_plan(session: Session, student: Student) -> dict:
    # --- Departments (clinical years only) ---------------------------------------------------
    departments = []
    if student.year in CLINICAL_YEARS:
        progress = student_quota_progress(session, student)
        gaps = sorted((d for d in progress.departments if d.required and d.remaining > 0),
                      key=lambda d: (d.percent, -d.remaining))
        for d in gaps:
            cases, where = CASE_GUIDE[d.department]
            departments.append({
                "department": d.department, "approved": d.approved, "required": d.required,
                "remaining": d.remaining, "pending": d.pending, "percent": d.percent,
                "case_types": cases, "where_to_find": where, "double_priority": False,
            })

    # --- Subjects ------------------------------------------------------------------------------
    rows: dict[str, list[Assessment]] = defaultdict(list)
    for a in session.exec(select(Assessment).where(Assessment.student_id == student.id)).all():
        rows[a.subject].append(a)
    subjects = []
    for subject, exams in rows.items():
        exams.sort(key=lambda a: a.exam_date or a.id)
        pcts = [a.marks / a.max_marks * 100 for a in exams]
        worst = min(exams, key=lambda a: a.marks / a.max_marks)
        subjects.append({
            "subject": subject,
            "average_pct": round(statistics.mean(pcts), 1),
            "latest_pct": round(pcts[-1], 1),
            "trend": round(pcts[-1] - pcts[0], 1) if len(pcts) > 1 else None,
            "exams": len(pcts),
            "related_department": SUBJECT_DEPARTMENT.get(subject),
            "tip": EXAM_TIP[worst.exam_type],
        })
    subjects.sort(key=lambda s: s["average_pct"])
    weak = [s for s in subjects if s["average_pct"] < WEAK_SUBJECT_PCT]
    if not weak and subjects:
        weak = subjects[:1] if subjects[0]["average_pct"] < 70 else []

    # Weak subject + lagging department = double priority.
    weak_depts = {s["related_department"] for s in weak if s["related_department"]}
    for d in departments:
        if d["department"] in weak_depts and d["percent"] < 50:
            d["double_priority"] = True
    departments.sort(key=lambda d: (not d["double_priority"], d["percent"]))

    focus_d, focus_s = departments[:MAX_ITEMS], weak[:MAX_ITEMS]
    if not focus_d and not focus_s:
        summary = "No gaps right now: keep your current rhythm and help a batch-mate."
    else:
        parts = []
        if focus_d:
            parts.append("clinical: " + ", ".join(d["department"].value.replace("_", " ").title() for d in focus_d))
        if focus_s:
            parts.append("studies: " + ", ".join(s["subject"] for s in focus_s))
        summary = "Focus next on " + "; ".join(parts) + "."
    return {
        "student_id": student.id,
        "year": student.year,
        "is_clinical": student.year in CLINICAL_YEARS,
        "summary": summary,
        "focus_departments": focus_d,
        "focus_subjects": focus_s,
        "all_subjects": subjects,
    }
