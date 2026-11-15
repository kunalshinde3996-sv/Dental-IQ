"""Role-specific landing-page numbers, computed with the same services the detail pages use."""
from datetime import datetime, time, timezone

from fastapi import APIRouter
from sqlalchemy import func
from sqlmodel import col, select

from app.core.deps import CurrentUser, SessionDep, get_faculty_profile, get_student_profile
from app.models import AuditEvent, Case, Faculty, Notification, Patient, Student
from app.models.enums import CaseStatus, Role

router = APIRouter(prefix="/api/overview", tags=["overview"])


def _unread(session, user_id: int) -> int:
    return session.exec(select(func.count()).select_from(Notification)
                        .where(Notification.user_id == user_id, col(Notification.read_at).is_(None))).one()


def _case_counts(session, *where) -> dict[str, int]:
    rows = session.exec(select(Case.status, func.count()).where(*where).group_by(Case.status)).all()
    return {s.value: dict(rows).get(s, 0) for s in CaseStatus}


@router.get("", summary="Most important numbers for the signed-in user's role")
def overview(session: SessionDep, user: CurrentUser) -> dict:
    from app.services.allocation import resources
    from ml.student_risk import assess_all, compute_signals, focus_areas

    out: dict = {"role": user.role.value, "unread_notifications": _unread(session, user.id)}

    if user.role == Role.student:
        from app.services.learning import learning_plan
        from app.services.quota import student_quota_progress

        student = get_student_profile(session, user)
        signals = compute_signals(session)[student.id]
        plan = learning_plan(session, student)
        quota = student_quota_progress(session, student)
        out["student"] = {
            "quota_percent": quota.overall_percent if quota.is_clinical else None,
            "quota_approved": quota.total_approved,
            "quota_required": quota.total_required,
            "attendance_pct": signals.attendance_pct,
            "marks_avg": signals.marks_avg,
            "cases": _case_counts(session, Case.student_id == student.id),
            "focus": focus_areas(signals, [d["department"] for d in plan["focus_departments"]]),
            "next_department": plan["focus_departments"][0]["department"] if plan["focus_departments"] else None,
        }
        return out

    alerts = assess_all(session)
    levels = {lvl: sum(a["risk_level"] == lvl for a in alerts) for lvl in ("High", "Medium", "Low")}
    load = resources(session, 30)["departments"]
    staff = {
        "at_risk": levels,
        "top_alerts": [{"student_id": a["student_id"], "name": a["name"], "roll_no": a["roll_no"],
                        "reason": a["reasons"][0]["text"] if a["reasons"] else "Elevated model score"}
                       for a in alerts if a["risk_level"] == "High"][:5],
        "overloaded_departments": [d["department"] for d in load if d["status"] == "overloaded"],
        "short_supply_departments": [d["department"] for d in load if d["status"] == "short_supply"],
    }

    if user.role == Role.faculty:
        faculty = get_faculty_profile(session, user)
        mine = next(d for d in load if d["department"] == faculty.department)
        out["faculty"] = {
            **staff,
            "department": faculty.department,
            "pending_reviews": session.exec(select(func.count()).select_from(Case).where(
                Case.faculty_id == faculty.id, Case.status == CaseStatus.submitted)).one(),
            "reviewed_by_me": session.exec(select(func.count()).select_from(Case).where(
                Case.faculty_id == faculty.id, Case.status.in_([CaseStatus.approved, CaseStatus.rejected]))).one(),
            "department_load": {"status": mine["status"], "cases_per_faculty": mine["cases_per_faculty"],
                                "pending_reviews": mine["pending_reviews"], "reasons": mine["reasons"]},
        }
        return out

    today = datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)
    patients = session.exec(select(func.count()).select_from(Patient)).one()
    abha = session.exec(select(func.count()).select_from(Patient).where(col(Patient.abha_id).is_not(None))).one()
    out["admin"] = {
        **staff,
        "students": session.exec(select(func.count()).select_from(Student)).one(),
        "faculty": session.exec(select(func.count()).select_from(Faculty)).one(),
        "patients": patients,
        "abha_linked_pct": round(abha / patients * 100, 1) if patients else 0.0,
        "cases": _case_counts(session),
        "audit_events_today": session.exec(select(func.count()).select_from(AuditEvent)
                                           .where(AuditEvent.created_at >= today)).one(),
        "failed_logins_today": session.exec(select(func.count()).select_from(AuditEvent).where(
            AuditEvent.created_at >= today, AuditEvent.action == "login_failed")).one(),
    }
    return out
