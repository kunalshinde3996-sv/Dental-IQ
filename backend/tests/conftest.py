"""Test fixtures: an isolated temporary SQLite DB with a minimal set of users."""
import os
import tempfile

# Must be set before the app (and its engine) is imported.
_tmpdir = tempfile.mkdtemp(prefix="dentaliq-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(_tmpdir, 'test.db')}"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["ML_ARTIFACT_DIR"] = os.path.join(_tmpdir, "artifacts")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import Session, SQLModel  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.database import engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import ClinicalQuota, Faculty, Patient, Student, User  # noqa: E402
from app.models.enums import Department, Role, Sex, StudentYear, Taluka  # noqa: E402

PASSWORD = "Secret@123"


@pytest.fixture()
def db():
    import app.models  # noqa: F401

    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        pw = hash_password(PASSWORD)

        def user(name, email, role):
            u = User(name=name, email=email, password_hash=pw, role=role)
            session.add(u)
            session.flush()
            return u

        user("Admin", "admin@test.demo", Role.admin)
        f1 = Faculty(user_id=user("Dr. Om", "om@test.demo", Role.faculty).id, department=Department.oral_medicine)
        f2 = Faculty(user_id=user("Dr. Endo", "endo@test.demo", Role.faculty).id, department=Department.endodontics)
        s1 = Student(user_id=user("Asha", "asha@test.demo", Role.student).id, roll_no="R1",
                     year=StudentYear.bds4, batch="2023-28")
        s2 = Student(user_id=user("Ben", "ben@test.demo", Role.student).id, roll_no="R2",
                     year=StudentYear.bds4, batch="2023-28")
        session.add_all([f1, f2, s1, s2])
        session.add(Patient(opd_number="GDC-T-1", name="Test Patient", age=40, sex=Sex.male,
                            taluka=Taluka.tiswadi, is_synthetic=True))
        session.add(ClinicalQuota(department=Department.oral_medicine, year=StudentYear.bds4, required_cases=2))
        session.add(ClinicalQuota(department=Department.endodontics, year=StudentYear.bds4, required_cases=1))
        session.commit()
        ids = {"f1": f1.id, "f2": f2.id, "s1": s1.id, "s2": s2.id}
    yield ids


@pytest.fixture(autouse=True)
def _reset_login_rate_limiter():
    """The limiter is process-wide; keep tests independent of each other's failed logins."""
    from app.routers.auth import limiter

    limiter._failures.clear()
    yield
    limiter._failures.clear()


@pytest.fixture()
def client(db):
    with TestClient(app) as c:
        yield c


def login(client: TestClient, email: str) -> dict[str, str]:
    res = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}
