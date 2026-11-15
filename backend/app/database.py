"""Database engine and session dependency.

The engine is built from ``DATABASE_URL`` so switching SQLite -> PostgreSQL
is a configuration change only.
"""
from collections.abc import Iterator

from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import get_settings

settings = get_settings()

_is_sqlite = settings.database_url.startswith("sqlite")
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    pool_pre_ping=not _is_sqlite,
)

if _is_sqlite:
    # SQLite does not enforce foreign keys unless asked to.
    @event.listens_for(engine, "connect")
    def _enable_sqlite_fk(dbapi_conn, _record):  # pragma: no cover - driver hook
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def create_db_and_tables() -> None:
    # Importing models registers them on SQLModel.metadata.
    import app.models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
