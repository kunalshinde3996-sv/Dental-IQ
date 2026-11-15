"""Audit log browsing (admin) and in-app notifications (every user)."""
from datetime import date, datetime, time, timezone

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, or_
from sqlmodel import col, select

from app.core.deps import AdminUser, CurrentUser, SessionDep
from app.models import AuditEvent, Notification
from app.models._base import utcnow
from app.schemas.common import Page
from app.services.notifications import refresh_at_risk_alerts

router = APIRouter(tags=["trust & notifications"])


class AuditEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    user_id: int | None
    user_name: str | None
    user_role: str | None
    action: str
    entity_type: str
    entity_id: int | None
    summary: str
    ip_address: str | None


class AuditFacets(BaseModel):
    actions: list[str]
    entity_types: list[str]


@router.get("/api/audit", response_model=Page[AuditEventRead], summary="Browse the audit trail (admin)")
def list_audit(
    session: SessionDep,
    _admin: AdminUser,
    action: str | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
    user_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    q: str | None = Query(default=None, max_length=100, description="Search user name or summary"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    filters = []
    if action:
        filters.append(AuditEvent.action == action)
    if entity_type:
        filters.append(AuditEvent.entity_type == entity_type)
    if entity_id is not None:
        filters.append(AuditEvent.entity_id == entity_id)
    if user_id is not None:
        filters.append(AuditEvent.user_id == user_id)
    if date_from:
        filters.append(AuditEvent.created_at >= datetime.combine(date_from, time.min, tzinfo=timezone.utc))
    if date_to:
        filters.append(AuditEvent.created_at <= datetime.combine(date_to, time.max, tzinfo=timezone.utc))
    if q and q.strip():
        term = f"%{q.strip().lower()}%"
        filters.append(or_(func.lower(AuditEvent.summary).like(term), func.lower(AuditEvent.user_name).like(term)))
    total = session.exec(select(func.count()).select_from(AuditEvent).where(*filters)).one()
    rows = session.exec(select(AuditEvent).where(*filters)
                        .order_by(col(AuditEvent.created_at).desc(), col(AuditEvent.id).desc())
                        .offset(offset).limit(limit)).all()
    return Page(items=rows, total=total, limit=limit, offset=offset)


@router.get("/api/audit/facets", response_model=AuditFacets, summary="Distinct actions / entity types for filters")
def audit_facets(session: SessionDep, _admin: AdminUser):
    return AuditFacets(
        actions=sorted(session.exec(select(AuditEvent.action).distinct()).all()),
        entity_types=sorted(session.exec(select(AuditEvent.entity_type).distinct()).all()),
    )


# --- Notifications --------------------------------------------------------------------------

class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: str
    title: str
    body: str
    link: str | None
    created_at: datetime
    read_at: datetime | None


class UnreadCount(BaseModel):
    unread: int


@router.get("/api/notifications", response_model=list[NotificationRead], summary="My notifications, newest first")
def my_notifications(session: SessionDep, user: CurrentUser, unread_only: bool = False,
                     limit: int = Query(default=30, ge=1, le=200)):
    stmt = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        stmt = stmt.where(col(Notification.read_at).is_(None))
    return session.exec(stmt.order_by(col(Notification.created_at).desc(), col(Notification.id).desc())
                        .limit(limit)).all()


@router.get("/api/notifications/unread-count", response_model=UnreadCount)
def unread_count(session: SessionDep, user: CurrentUser):
    n = session.exec(select(func.count()).select_from(Notification)
                     .where(Notification.user_id == user.id, col(Notification.read_at).is_(None))).one()
    return UnreadCount(unread=n)


@router.post("/api/notifications/{notification_id}/read", response_model=NotificationRead)
def mark_read(notification_id: int, session: SessionDep, user: CurrentUser):
    n = session.get(Notification, notification_id)
    if n is None or n.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notification not found")
    if n.read_at is None:
        n.read_at = utcnow()
        session.add(n)
        session.commit()
        session.refresh(n)
    return n


@router.post("/api/notifications/read-all", response_model=UnreadCount)
def mark_all_read(session: SessionDep, user: CurrentUser):
    rows = session.exec(select(Notification).where(Notification.user_id == user.id,
                                                   col(Notification.read_at).is_(None))).all()
    now = utcnow()
    for n in rows:
        n.read_at = now
        session.add(n)
    session.commit()
    return UnreadCount(unread=0)


@router.post("/api/notifications/refresh-alerts", response_model=UnreadCount,
             summary="Re-scan students and notify staff of new High at-risk alerts (admin)")
def refresh_alerts(session: SessionDep, admin: AdminUser):
    refresh_at_risk_alerts(session)
    return unread_count(session, admin)
