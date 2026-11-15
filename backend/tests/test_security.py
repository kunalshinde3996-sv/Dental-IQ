"""Phase-3 trust & security: audit trail, auth hardening, notifications."""
import pytest

from app.core.config import ConfigError, Settings
from app.core.passwords import password_problems
from tests.conftest import PASSWORD, login


# --- auth hardening -------------------------------------------------------------------------

def test_login_rate_limited_after_repeated_failures(client):
    bad = {"email": "asha@test.demo", "password": "wrong"}
    for _ in range(5):
        assert client.post("/api/auth/login", json=bad).status_code == 401
    blocked = client.post("/api/auth/login", json=bad)
    assert blocked.status_code == 429 and int(blocked.headers["Retry-After"]) > 0
    # Even the right password is refused while blocked (no oracle for the attacker).
    assert client.post("/api/auth/login", json={**bad, "password": PASSWORD}).status_code == 429
    # Other accounts are unaffected.
    assert client.post("/api/auth/login", json={"email": "ben@test.demo", "password": PASSWORD}).status_code == 200


def test_unknown_email_and_wrong_password_look_the_same(client):
    a = client.post("/api/auth/login", json={"email": "nobody@test.demo", "password": "x"})
    b = client.post("/api/auth/login", json={"email": "asha@test.demo", "password": "x"})
    assert a.status_code == b.status_code == 401 and a.json() == b.json()


def test_logout_revokes_token(client):
    h = login(client, "asha@test.demo")
    assert client.get("/api/auth/me", headers=h).status_code == 200
    assert client.post("/api/auth/logout", headers=h).status_code == 204
    assert client.get("/api/auth/me", headers=h).status_code == 401
    # A fresh login still works.
    assert client.get("/api/auth/me", headers=login(client, "asha@test.demo")).status_code == 200


def test_login_returns_expiry_and_rejects_tampered_tokens(client):
    res = client.post("/api/auth/login", json={"email": "asha@test.demo", "password": PASSWORD}).json()
    assert res["expires_at"]
    tampered = res["access_token"][:-4] + ("AAAA" if not res["access_token"].endswith("AAAA") else "BBBB")
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {tampered}"}).status_code == 401


def test_password_policy_and_change(client):
    assert password_problems("short") and password_problems("alllowercase1!") and password_problems("NoDigits!!")
    assert "must not contain your email name" in password_problems("Asha#20261", "asha@test.demo")
    assert password_problems("Goa#Clinic2026", "asha@test.demo") == []

    h = login(client, "asha@test.demo")
    url = "/api/auth/change-password"
    assert client.post(url, headers=h, json={"current_password": "nope", "new_password": "Goa#Clinic2026"}).status_code == 400
    weak = client.post(url, headers=h, json={"current_password": PASSWORD, "new_password": "password"})
    assert weak.status_code == 422 and "upper-case" in weak.json()["detail"]
    assert client.post(url, headers=h, json={"current_password": PASSWORD, "new_password": "Goa#Clinic2026"}).status_code == 204
    assert client.post("/api/auth/login", json={"email": "asha@test.demo", "password": "Goa#Clinic2026"}).status_code == 200


def test_production_refuses_weak_secret_and_wildcard_cors():
    with pytest.raises(ConfigError):
        Settings(app_env="production", jwt_secret="change-me-to-a-long-random-string").validate_security()
    with pytest.raises(ConfigError):
        Settings(app_env="production", jwt_secret="x" * 40, cors_origins="*").validate_security()
    dev = Settings(app_env="development", jwt_secret=None)
    dev.validate_security()
    assert dev.jwt_secret and len(dev.jwt_secret) >= 32  # random per-process secret
    prod = Settings(app_env="production", jwt_secret="y" * 48, auto_create_tables=True)
    prod.validate_security()
    assert prod.create_tables_on_startup is False  # Alembic owns the schema in production


def test_security_headers_and_cors(client):
    res = client.get("/api/health")
    assert res.headers["X-Content-Type-Options"] == "nosniff" and res.headers["X-Frame-Options"] == "DENY"
    pre = {"Access-Control-Request-Method": "GET"}
    good = client.options("/api/health", headers={**pre, "Origin": "http://localhost:5173"})
    assert good.headers.get("access-control-allow-origin") == "http://localhost:5173"
    evil = client.options("/api/health", headers={**pre, "Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in evil.headers


# --- audit trail ------------------------------------------------------------------------------

def _case(client, h, faculty_id):
    return client.post("/api/cases", headers=h, json={
        "patient_id": 1, "faculty_id": faculty_id, "department": "oral_medicine",
        "chief_complaint": "Check-up", "diagnosis": "Gingivitis", "procedure": "Scaling", "submit": True}).json()


def test_audit_records_views_changes_and_approvals(client, db):
    student, faculty, admin = (login(client, e) for e in ("asha@test.demo", "om@test.demo", "admin@test.demo"))
    client.get("/api/patients/1", headers=faculty)
    client.patch("/api/patients/1", headers=faculty, json={"age": 41})
    case = _case(client, student, db["f1"])
    client.post(f"/api/cases/{case['id']}/review", headers=faculty, json={"decision": "approve", "remarks": "Good"})
    client.post("/api/auth/login", json={"email": "asha@test.demo", "password": "bad"})

    events = client.get("/api/audit", headers=admin, params={"limit": 100}).json()["items"]
    seen = {(e["action"], e["entity_type"]) for e in events}
    assert {("view", "patient"), ("update", "patient"), ("create", "case"), ("approve", "case"),
            ("login", "auth"), ("login_failed", "auth")} <= seen
    approve = next(e for e in events if e["action"] == "approve")
    assert approve["user_name"] == "Dr. Om" and approve["entity_id"] == case["id"]
    # Filters
    only_patient = client.get("/api/audit", headers=admin, params={"entity_type": "patient", "entity_id": 1}).json()
    assert only_patient["total"] >= 2 and all(e["entity_type"] == "patient" for e in only_patient["items"])
    facets = client.get("/api/audit/facets", headers=admin).json()
    assert "approve" in facets["actions"] and "case" in facets["entity_types"]
    # Admin only
    assert client.get("/api/audit", headers=faculty).status_code == 403


# --- notifications --------------------------------------------------------------------------

def test_case_review_notifies_student(client, db):
    student, faculty = login(client, "asha@test.demo"), login(client, "om@test.demo")
    case = _case(client, student, db["f1"])
    client.post(f"/api/cases/{case['id']}/review", headers=faculty, json={"decision": "reject", "remarks": "Chart MOD"})
    assert client.get("/api/notifications/unread-count", headers=student).json()["unread"] == 1
    note = client.get("/api/notifications", headers=student).json()[0]
    assert note["kind"] == "case_rejected" and "Chart MOD" in note["body"] and note["link"] == f"/cases/{case['id']}"
    # Another user cannot read or mark it
    ben = login(client, "ben@test.demo")
    assert client.post(f"/api/notifications/{note['id']}/read", headers=ben).status_code == 404
    assert client.post(f"/api/notifications/{note['id']}/read", headers=student).json()["read_at"]
    assert client.get("/api/notifications/unread-count", headers=student).json()["unread"] == 0
    assert client.get("/api/notifications", headers=student, params={"unread_only": True}).json() == []


def test_api_timestamps_are_timezone_aware(client, db):
    """SQLite drops tzinfo; the API must still emit UTC offsets so browsers show correct local times."""
    student, faculty = login(client, "asha@test.demo"), login(client, "om@test.demo")
    case = _case(client, student, db["f1"])
    client.post(f"/api/cases/{case['id']}/review", headers=faculty, json={"decision": "approve"})
    note = client.get("/api/notifications", headers=student).json()[0]
    reviewed = client.get(f"/api/cases/{case['id']}", headers=student).json()["reviewed_at"]
    for ts in (note["created_at"], reviewed):
        assert ts.endswith("Z") or ts.endswith("+00:00"), ts
