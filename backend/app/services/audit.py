"""Audit trail helper: who viewed / created / changed / approved which record.

`record()` only adds the event to the session; it is committed together with the change it
describes (or by `record_view()` for read-only access), so a failed change never leaves a
misleading audit row behind.
"""
from fastapi import Request
from sqlmodel import Session

from app.core.config import get_settings
from app.models import AuditEvent, User


def client_ip(request: Request | None) -> str | None:
    if request is None:
        return None
    if get_settings().trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()[:64]
    return request.client.host if request.client else None


def record(session: Session, user: User | None, action: str, entity_type: str, entity_id: int | None,
           summary: str, request: Request | None = None) -> AuditEvent:
    event = AuditEvent(
        user_id=user.id if user else None,
        user_name=user.name if user else None,
        user_role=user.role.value if user else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        summary=summary[:500],
        ip_address=client_ip(request),
    )
    session.add(event)
    return event


def record_view(session: Session, user: User, entity_type: str, entity_id: int, summary: str,
                request: Request | None = None) -> None:
    """Read access to a health record is itself auditable; commit it on its own."""
    record(session, user, "view", entity_type, entity_id, summary, request)
    session.commit()
