"""End-to-end API tests for the Phase-1 core flow."""
from datetime import date

from tests.conftest import login


# --- auth & RBAC -------------------------------------------------------------

def test_login_success_returns_profile(client):
    res = client.post("/api/auth/login", json={"email": "ASHA@test.demo", "password": "Secret@123"})
    assert res.status_code == 200
    body = res.json()
    assert body["user"]["role"] == "student"
    assert body["student"]["roll_no"] == "R1"
    assert body["access_token"]


def test_login_wrong_password(client):
    res = client.post("/api/auth/login", json={"email": "asha@test.demo", "password": "nope"})
    assert res.status_code == 401


def test_requires_token(client):
    assert client.get("/api/patients").status_code == 401


def test_invalid_token(client):
    assert client.get("/api/patients", headers={"Authorization": "Bearer junk"}).status_code == 401


def test_student_cannot_list_students(client):
    assert client.get("/api/students", headers=login(client, "asha@test.demo")).status_code == 403


def test_admin_stats(client):
    res = client.get("/api/admin/stats", headers=login(client, "admin@test.demo"))
    assert res.status_code == 200
    assert res.json()["students"] == 2


# --- patients ---------------------------------------------------------------

def test_patient_create_search_and_validation(client):
    h = login(client, "asha@test.demo")
    payload = {"name": "  Ravi   Naik ", "age": 52, "sex": "male", "taluka": "ponda",
               "abha_id": "91 1234 5678 9012", "phone": "+91 98765 43210", "smokeless_tobacco": "current"}
    res = client.post("/api/patients", json=payload, headers=h)
    assert res.status_code == 201, res.text
    p = res.json()
    assert p["name"] == "Ravi Naik"
    assert p["abha_id"] == "91-1234-5678-9012"
    assert p["phone"] == "9876543210"
    assert p["opd_number"].startswith("GDC-")

    # duplicate ABHA -> 409
    assert client.post("/api/patients", json=payload, headers=h).status_code == 409
    # bad ABHA -> 422
    assert client.post("/api/patients", json={**payload, "abha_id": "123"}, headers=h).status_code == 422
    # search by ABHA fragment
    found = client.get("/api/patients", params={"q": "5678"}, headers=h).json()
    assert found["total"] == 1 and found["items"][0]["name"] == "Ravi Naik"
    # partial update
    upd = client.patch(f"/api/patients/{p['id']}", json={"age": 53}, headers=h)
    assert upd.status_code == 200 and upd.json()["age"] == 53
    # only admin can delete
    assert client.delete(f"/api/patients/{p['id']}", headers=h).status_code == 403
    assert client.delete(f"/api/patients/{p['id']}", headers=login(client, "admin@test.demo")).status_code == 204


# --- the core flow: case -> approval -> competency + EHR ---------------------

def _new_case(client, h, faculty_id, **overrides):
    body = {
        "patient_id": 1, "faculty_id": faculty_id, "department": "oral_medicine",
        "chief_complaint": "White patch on cheek", "diagnosis": "Leukoplakia",
        "procedure": "Examination", "findings": [{"tooth_number": 36, "condition": "caries", "surfaces": "mod"}],
    }
    body.update(overrides)
    return client.post("/api/cases", json=body, headers=h)


def test_case_lifecycle_feeds_ehr_and_quota(client, db):
    student = login(client, "asha@test.demo")
    faculty = login(client, "om@test.demo")

    res = _new_case(client, student, db["f1"])
    assert res.status_code == 201, res.text
    case = res.json()
    assert case["status"] == "draft"
    assert case["findings"][0]["surfaces"] == "MOD"

    # Add a finding to an existing case, then submit
    assert client.post(f"/api/cases/{case['id']}/findings",
                       json={"tooth_number": 11, "condition": "fractured"}, headers=student).status_code == 201
    sub = client.post(f"/api/cases/{case['id']}/submit", headers=student)
    assert sub.status_code == 200 and sub.json()["status"] == "submitted"
    assert len(sub.json()["findings"]) == 2

    # Submitted cases are locked for the student
    assert client.patch(f"/api/cases/{case['id']}", json={"diagnosis": "x"}, headers=student).status_code == 409

    # Faculty sees it pending; reject requires remarks
    pending = client.get("/api/faculty/me/pending-cases", headers=faculty).json()
    assert pending["total"] == 1
    assert client.post(f"/api/cases/{case['id']}/review", json={"decision": "reject"},
                       headers=faculty).status_code == 422
    rej = client.post(f"/api/cases/{case['id']}/review",
                      json={"decision": "reject", "remarks": "Chart all surfaces"}, headers=faculty)
    assert rej.json()["status"] == "rejected"

    # Student fixes and resubmits; faculty approves
    assert client.patch(f"/api/cases/{case['id']}", json={"procedure": "Exam + biopsy referral"},
                        headers=student).status_code == 200
    client.post(f"/api/cases/{case['id']}/submit", headers=student)
    appr = client.post(f"/api/cases/{case['id']}/review", json={"decision": "approve", "remarks": "Good"},
                       headers=faculty)
    assert appr.json()["status"] == "approved"

    # -> competency: quota progress counts it
    quota = client.get(f"/api/students/{db['s1']}/quota-progress", headers=student).json()
    om = next(d for d in quota["departments"] if d["department"] == "oral_medicine")
    assert om["approved"] == 1 and om["required"] == 2 and om["percent"] == 50.0
    assert quota["total_required"] == 3 and quota["total_approved"] == 1

    # -> EHR: visit appears in the patient profile
    patient = client.get("/api/patients/1", headers=faculty).json()
    assert patient["visits"][0]["id"] == case["id"]
    assert patient["visits"][0]["findings_count"] == 2


def test_case_validation(client, db):
    student = login(client, "asha@test.demo")
    # invalid FDI tooth
    assert _new_case(client, student, db["f1"], findings=[{"tooth_number": 19, "condition": "caries"}]).status_code == 422
    # duplicate tooth
    dup = [{"tooth_number": 11, "condition": "caries"}, {"tooth_number": 11, "condition": "filled"}]
    assert _new_case(client, student, db["f1"], findings=dup).status_code == 422
    # supervisor from another department
    assert _new_case(client, student, db["f2"]).status_code == 422
    # submit without diagnosis
    assert _new_case(client, student, db["f1"], diagnosis=None, submit=True).status_code == 422
    # future date
    assert _new_case(client, student, db["f1"], visit_date="2999-01-01").status_code == 422
    # faculty cannot create cases
    assert _new_case(client, login(client, "om@test.demo"), db["f1"]).status_code == 403


def test_case_privacy_and_review_permissions(client, db):
    asha, ben = login(client, "asha@test.demo"), login(client, "ben@test.demo")
    case = _new_case(client, asha, db["f1"], submit=True).json()
    assert client.get(f"/api/cases/{case['id']}", headers=ben).status_code == 404
    assert client.get("/api/cases", params={"student_id": db["s1"]}, headers=ben).status_code == 403
    assert client.get(f"/api/students/{db['s1']}/quota-progress", headers=ben).status_code == 403
    # a faculty member who is not the supervisor cannot review
    res = client.post(f"/api/cases/{case['id']}/review", json={"decision": "approve"},
                      headers=login(client, "endo@test.demo"))
    assert res.status_code == 403


# --- attendance & marks -----------------------------------------------------

def test_attendance_bulk_upsert_and_summary(client, db):
    staff = login(client, "om@test.demo")
    today = date.today().isoformat()
    body = {"date": today, "session": "clinic", "entries": [
        {"student_id": db["s1"], "status": "present"}, {"student_id": db["s2"], "status": "absent"}]}
    assert client.post("/api/attendance/bulk", json=body, headers=staff).status_code == 201
    body["entries"][1]["status"] = "late"  # correction -> upsert, not duplicate
    assert client.post("/api/attendance/bulk", json=body, headers=staff).status_code == 201

    ben = login(client, "ben@test.demo")
    summary = client.get(f"/api/students/{db['s2']}/attendance-summary", headers=ben).json()
    assert summary["total_sessions"] == 1 and summary["late"] == 1 and summary["percentage"] == 100.0
    # student cannot mark attendance
    assert client.post("/api/attendance/bulk", json=body, headers=ben).status_code == 403


def test_assessments(client, db):
    staff = login(client, "om@test.demo")
    ok = {"student_id": db["s1"], "subject": "Periodontology", "exam_type": "internal", "marks": 38, "max_marks": 50}
    res = client.post("/api/assessments", json=ok, headers=staff)
    assert res.status_code == 201 and res.json()["percentage"] == 76.0
    assert client.post("/api/assessments", json={**ok, "marks": 60}, headers=staff).status_code == 422
    # students only see their own marks
    ben = login(client, "ben@test.demo")
    assert client.get("/api/assessments", headers=ben).json() == []
    assert client.get("/api/assessments", params={"student_id": db["s1"]}, headers=ben).status_code == 403
