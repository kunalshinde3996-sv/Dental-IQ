"""Trust & security tables: audit trail, revoked tokens (logout), in-app notifications."""
from datetime import datetime

from sqlmodel import Field, SQLModel

from app.models._base import UTCDateTime, utcnow


class AuditEvent(SQLModel, table=True):
    """Append-only record of who did what to which record. Never updated or deleted by the app."""

    __tablename__ = "audit_event"

    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow, sa_type=UTCDateTime, index=True)
    # Nullable: failed logins have no authenticated user. Name/role are snapshots at event time.
    user_id: int | None = Field(default=None, foreign_key="user.id", index=True, ondelete="SET NULL")
    user_name: str | None = Field(default=None, max_length=120)
    user_role: str | None = Field(default=None, max_length=20)
    action: str = Field(max_length=30, index=True)  # view, create, update, delete, approve, reject, ...
    entity_type: str = Field(max_length=30, index=True)  # patient, case, auth, allocation, ...
    entity_id: int | None = Field(default=None, index=True)
    summary: str = Field(max_length=500)
    ip_address: str | None = Field(default=None, max_length=64)


class RevokedToken(SQLModel, table=True):
    """JWT IDs revoked by logout. Rows can be purged once `expires_at` has passed."""

    __tablename__ = "revoked_token"

    jti: str = Field(primary_key=True, max_length=64)
    user_id: int = Field(foreign_key="user.id", index=True, ondelete="CASCADE")
    expires_at: datetime = Field(sa_type=UTCDateTime, index=True)
    revoked_at: datetime = Field(default_factory=utcnow, sa_type=UTCDateTime)


class Notification(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True, ondelete="CASCADE")
    kind: str = Field(max_length=30, index=True)  # case_approved, case_rejected, patient_allocated, at_risk_alert
    title: str = Field(max_length=200)
    body: str = Field(max_length=1000)
    link: str | None = Field(default=None, max_length=200)
    # Lets producers avoid duplicates, e.g. one at-risk alert per student per week.
    dedupe_key: str | None = Field(default=None, max_length=100, index=True)
    created_at: datetime = Field(default_factory=utcnow, sa_type=UTCDateTime, index=True)
    read_at: datetime | None = Field(default=None, sa_type=UTCDateTime)
