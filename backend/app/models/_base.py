from datetime import datetime, timezone

from sqlalchemy.types import DateTime, TypeDecorator


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator):
    """Stores naive UTC; always returns timezone-aware UTC datetimes.

    SQLite drops tzinfo, which made the API emit offset-less timestamps that browsers read as
    local time (e.g. "6 h ago" in IST for something created a minute earlier).
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect):
        if value is not None and value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    def process_result_value(self, value: datetime | None, dialect):
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value
