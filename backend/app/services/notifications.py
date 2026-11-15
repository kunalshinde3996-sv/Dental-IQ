"""In-app notifications: producers for case reviews, allocations and at-risk alerts."""
from datetime import timedelta

from sqlmodel import Session, select

from app.models import Case, Faculty, Notification, Patient, Student, User
from app.models._base import utcnow
from app.models.enums import CaseStatus, Role



def DEPT(department) -> str:  # noqa: N802 - reads like a label constant at call sites
    return department.value.replace("_", " ").title()

AT_RISK_DEDUPE_DAYS = 7


def notify(session: Session, user_id: int, kind: str, title: str, body: str, link: str | None = None,
           dedupe_key: str | None = None) -> Notification:
    n = Notification(user_id=user_id, kind=kind, title=title[:200], body=body[:1000], link=link, dedupe_key=dedupe_key)
    session.add(n)
    return n


def _student_user_id(session: Session, student_id: int) -> int | None:
    student = session.get(Student, student_id)
    return student.user_id if student else None


def case_reviewed(session: Session, case: Case) -> None:
    uid = _student_user_id(session, case.student_id)
    patient = session.get(Patient, case.patient_id)
    if uid is None or patient is None:
        return
    if case.status == CaseStatus.approved:
        notify(session, uid, "case_approved", f"Case #{case.id} approved",
               f"{DEPT(case.department)} case for {patient.name} was approved and counts toward your quota."
               + (f" Remarks: {case.faculty_remarks}" if case.faculty_remarks else ""), f"/cases/{case.id}")
    elif case.status == CaseStatus.rejected:
        notify(session, uid, "case_rejected", f"Case #{case.id} needs changes",
               f"{DEPT(case.department)} case for {patient.name} was returned: {case.faculty_remarks}",
               f"/cases/{case.id}")


def patient_allocated(session: Session, case: Case, by: User) -> None:
    uid = _student_user_id(session, case.student_id)
    patient = session.get(Patient, case.patient_id)
    if uid is None or patient is None:
        return
    notify(session, uid, "patient_allocated", f"New patient allocated: {patient.name}",
           f"{by.name} allocated a {DEPT(case.department)} patient to you ({case.chief_complaint}). "
           f"A draft case is ready.", f"/cases/{case.id}")


def _alert_recipients(session: Session) -> list[int]:
    """Admins and heads of department receive at-risk alerts."""
    admins = session.exec(select(User.id).where(User.role == Role.admin, User.is_active)).all()
    hods = session.exec(
        select(User.id).join(Faculty, Faculty.user_id == User.id)
        .where(Faculty.designation.contains("HOD"), User.is_active)
    ).all()
    return list(dict.fromkeys([*admins, *hods]))


def refresh_at_risk_alerts(session: Session) -> int:
    """Notify staff about students currently at High risk (once per student per week). Returns count."""
    from ml.student_risk import assess_all  # local import: ML stack loads only when needed

    recipients = _alert_recipients(session)
    if not recipients:
        return 0
    since = utcnow() - timedelta(days=AT_RISK_DEDUPE_DAYS)
    created = 0
    for alert in assess_all(session):
        if alert["risk_level"] != "High":
            continue
        key = f"at_risk:{alert['student_id']}"
        if session.exec(select(Notification.id).where(Notification.dedupe_key == key,
                                                      Notification.created_at >= since)).first():
            continue
        reason = alert["reasons"][0]["text"] if alert["reasons"] else "Elevated model score."
        for uid in recipients:
            notify(session, uid, "at_risk_alert", f"At-risk: {alert['name']} ({alert['roll_no']})",
                   reason, "/at-risk", dedupe_key=key)
        created += 1
    session.commit()
    return created


def refresh_at_risk_alerts_background() -> None:
    """Entry point for FastAPI BackgroundTasks (own session; never raises into the request)."""
    import logging

    from app.database import engine

    try:
        with Session(engine) as session:
            refresh_at_risk_alerts(session)
    except Exception:  # pragma: no cover - background best effort
        logging.getLogger("dental_iq").exception("Failed to refresh at-risk notifications")
