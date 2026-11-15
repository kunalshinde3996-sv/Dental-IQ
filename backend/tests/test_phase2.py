"""Phase-2 tests on a fully seeded (synthetic) database: analytics consistency, ML sanity, alerts, allocation."""
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlmodel import SQLModel

import app.models as _models  # noqa: F401  (register tables for the migration comparison)
from app.core.config import get_settings
from app.main import app

PASSWORDS = {
    "admin@gdch.demo": "Office#2026",
    "faculty@gdch.demo": "Clinic#2026",
    "student@gdch.demo": "Molar#2026",
    "atrisk.student@gdch.demo": "Molar#2026",
}


@pytest.fixture(scope="module")
def seeded():
    from scripts.seed import seed

    seed(reset=True, train=True, verbose=False)
    with TestClient(app) as client:
        yield client


def auth(client: TestClient, email: str) -> dict[str, str]:
    res = client.post("/api/auth/login", json={"email": email, "password": PASSWORDS[email]})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


# --- Step 1: population analytics -----------------------------------------------------

def test_population_report_is_internally_consistent(seeded):
    rep = seeded.get("/api/analytics/population", headers=auth(seeded, "admin@gdch.demo")).json()
    s = rep["summary"]
    assert s["patients"] > 300 and s["cases"] > 1000

    # Every patient belongs to exactly one taluka row.
    assert sum(r["patients"] for r in rep["taluka_burden"]) == s["patients"]
    assert sum(r["cases"] for r in rep["taluka_burden"]) == s["cases"]
    assert sum(r["counts"]["pmd"] for r in rep["taluka_burden"]) == s["pmd_patients"]
    # Caries table sums to the summary figure (all patients fall in an age band x sex... except 'other').
    caries = sum(r["male"]["caries"] + r["female"]["caries"] for r in rep["caries_by_age_sex"])
    assert caries <= s["caries_patients"]
    # Monthly trend totals add up to the case count.
    assert sum(m["total"] for m in rep["monthly_trend"]) == s["cases"]
    # Exposed + unexposed = adults, for every habit row.
    adults = {r["exposed_n"] + r["unexposed_n"] for r in rep["habit_associations"]}
    assert len(adults) == 1

    # The seeded generative model makes smokeless tobacco a strong PMD risk: the analytics must recover it.
    slt_pmd = next(r for r in rep["habit_associations"] if r["habit"] == "smokeless_tobacco" and r["outcome"] == "pmd")
    assert slt_pmd["prevalence_ratio"] > 2 and slt_pmd["ci_low"] > 1

    # Insights are generated from data and carry evidence.
    assert rep["insights"] and all(i["text"] and i["evidence"] for i in rep["insights"])


def test_seeded_caries_is_plausible_and_rises_with_age(seeded):
    """Guard against the Phase-2 artefact where ~80% of every age group had caries."""
    rows = seeded.get("/api/analytics/caries", headers=auth(seeded, "admin@gdch.demo")).json()

    def share(groups):
        n = sum(r["male"]["patients"] + r["female"]["patients"] for r in rows if r["age_group"] in groups)
        k = sum(r["male"]["caries"] + r["female"]["caries"] for r in rows if r["age_group"] in groups)
        return k / n * 100

    children, adults = share({"5-12", "13-17"}), share({"18-34", "35-49", "50-64", "65+"})
    assert 35 <= children <= 65, children
    assert 55 <= adults <= 75, adults
    assert adults > children


def test_population_filters_match_unfiltered_rows(seeded):
    h = auth(seeded, "faculty@gdch.demo")
    full = seeded.get("/api/analytics/population", headers=h).json()
    bardez_row = next(r for r in full["taluka_burden"] if r["taluka"] == "bardez")
    bardez = seeded.get("/api/analytics/population", params={"taluka": "bardez"}, headers=h).json()
    assert bardez["summary"]["patients"] == bardez_row["patients"]
    assert bardez["summary"]["cases"] == bardez_row["cases"]

    endo = seeded.get("/api/analytics/case-trend", params={"department": "endodontics"}, headers=h).json()
    assert sum(m["total"] for m in endo) == sum(m["endodontics"] for m in full["monthly_trend"])

    bad = seeded.get("/api/analytics/population", params={"date_from": "2026-02-01", "date_to": "2026-01-01"}, headers=h)
    assert bad.status_code == 422


def test_analytics_is_staff_only(seeded):
    res = seeded.get("/api/analytics/population", headers=auth(seeded, "student@gdch.demo"))
    assert res.status_code == 403


# --- Step 2: oral cancer risk screening ---------------------------------------------------

def _pmd_patient_id(client, headers) -> int:
    rows = client.get("/api/cases", params={"limit": 500, "department": "oral_medicine", "status": "approved"},
                      headers=headers).json()["items"]
    return next(c["patient_id"] for c in rows if "OSMF" in (c["diagnosis"] or "") or "leukoplakia" in (c["diagnosis"] or "").lower())


def test_oral_risk_model_trained_with_sane_metrics():
    from ml.common import load_bundle

    b = load_bundle("oral_risk")
    assert b is not None and b["n_positive"] >= 10
    assert b["metrics"]["cv5"]["auc"] > 0.7  # recovers the seeded habit-driven signal
    coefs = dict(zip(b["features"], b["coef"]))
    assert coefs["smokeless_current"] > 0 and coefs["lesion_observed"] > 0


def test_explanation_is_exact_decomposition():
    import math

    from ml.common import load_bundle
    from ml.oral_risk import FEATURE_NAMES, PatientFeatures, explain

    b = load_bundle("oral_risk")
    feats = PatientFeatures({n: v for n, v in zip(FEATURE_NAMES, [1.5, 1, 1, 0, 1, 0, 1, 2.0, 1, 0])})
    out = explain(b, feats)
    logit = b["intercept"] + sum(c * feats.values[n] for n, c in zip(b["features"], b["coef"]))
    assert math.isclose(out["probability"], 1 / (1 + math.exp(-logit)), rel_tol=1e-9)


def test_risk_screening_endpoint(seeded):
    h = auth(seeded, "student@gdch.demo")
    # A never-user child-free adult: lesion observed must raise the probability and change the action.
    base = seeded.post("/api/patients/3/risk-screening", headers=h).json()
    assert base["risk_level"] in ("Low", "Medium", "High") and 0 <= base["probability"] <= 1
    assert base["suggested_action"] and base["model"]["auc_cv"]
    with_lesion = seeded.post("/api/patients/3/risk-screening", json={"lesion_observed": True}, headers=h).json()
    assert with_lesion["probability"] >= base["probability"]
    assert with_lesion["lesion_observed"] is True

    # Known PMD on record -> final level High, with the model's own level kept for transparency.
    pid = _pmd_patient_id(seeded, auth(seeded, "faculty@gdch.demo"))
    known = seeded.post(f"/api/patients/{pid}/risk-screening", headers=h).json()
    assert known["known_pmd_diagnosis"] is True and known["risk_level"] == "High"
    assert known["model_risk_level"] in ("Low", "Medium", "High")

    assert seeded.post("/api/patients/999999/risk-screening", headers=h).status_code == 404


# --- Step 3: explainable at-risk student alerts -------------------------------------------

def _ground_truth() -> dict[str, bool]:
    from ml.student_risk import load_ground_truth

    gt = load_ground_truth()
    assert gt is not None
    return gt


def test_alerts_find_every_designed_at_risk_student(seeded):
    alerts = seeded.get("/api/alerts/students", headers=auth(seeded, "faculty@gdch.demo")).json()
    gt = _ground_truth()
    assert len(alerts) == len(gt) == 60
    assert sum(gt.values()) == 10
    by_roll = {a["roll_no"]: a for a in alerts}
    for roll, at_risk in gt.items():
        if at_risk:
            a = by_roll[roll]
            assert a["risk_level"] == "High", roll
            assert a["reasons"] and a["suggested_actions"], roll  # never a bare score
    # Highest risk first
    order = {"High": 0, "Medium": 1, "Low": 2}
    levels = [order[a["risk_level"]] for a in alerts]
    assert levels == sorted(levels)


def test_alert_numbers_match_other_pages(seeded):
    h = auth(seeded, "faculty@gdch.demo")
    alerts = seeded.get("/api/alerts/students", headers=h).json()
    a = next(x for x in alerts if x["signals"]["is_clinical"])
    summary = seeded.get(f"/api/students/{a['student_id']}/attendance-summary", headers=h).json()
    assert summary["percentage"] == a["signals"]["attendance_pct"]
    quota = seeded.get(f"/api/students/{a['student_id']}/quota-progress", headers=h).json()
    assert quota["overall_percent"] == a["signals"]["quota_percent"]


def test_student_risk_evaluation_recorded():
    from ml.common import load_bundle

    ev = load_bundle("student_risk")["evaluation"]
    assert ev["positives"] == 10
    assert ev["hybrid"]["recall"] == 1.0 and ev["hybrid_high"]["recall"] == 1.0


def test_alerts_and_focus_access(seeded):
    student = auth(seeded, "atrisk.student@gdch.demo")
    assert seeded.get("/api/alerts/students", headers=student).status_code == 403
    me = seeded.get("/api/auth/me", headers=student).json()["student"]["id"]
    focus = seeded.get(f"/api/students/{me}/focus-areas", headers=student).json()
    assert focus["on_track"] is False and focus["items"]
    assert all("risk" not in i["message"].lower() for i in focus["items"])  # gentle wording
    strong = auth(seeded, "student@gdch.demo")
    strong_id = seeded.get("/api/auth/me", headers=strong).json()["student"]["id"]
    assert seeded.get(f"/api/students/{strong_id}/focus-areas", headers=student).status_code == 403
    assert seeded.get(f"/api/students/{strong_id}/focus-areas", headers=strong).json()["on_track"] is True
    assert seeded.get(f"/api/students/{me}/risk", headers=student).status_code == 403


# --- Step 4: smart allocation + resource view ----------------------------------------------

def test_allocation_ranks_by_quota_gap_with_reasons(seeded):
    h = auth(seeded, "faculty@gdch.demo")
    rec = seeded.get("/api/allocation/recommendations", params={"patient_id": 3, "department": "endodontics"},
                     headers=h).json()
    cands = rec["candidates"]
    assert 1 <= len(cands) <= 5 and rec["eligible_count"] >= len(cands)
    assert [c["score"] for c in cands] == sorted((c["score"] for c in cands), reverse=True)
    assert all(c["reasons"] for c in cands)
    # The top candidate still needs Endodontics cases, and quota numbers match the student's own view.
    top = cands[0]
    assert top["remaining"] > 0
    q = seeded.get(f"/api/students/{top['student_id']}/quota-progress", headers=h).json()
    endo = next(d for d in q["departments"] if d["department"] == "endodontics")
    assert (endo["approved"], endo["required"]) == (top["approved"], top["required"])
    # Designed low-case students should surface near the top.
    gt = _ground_truth()
    assert any(gt.get(c["roll_no"]) for c in cands[:3])


def test_assign_creates_draft_case_for_student(seeded):
    h = auth(seeded, "faculty@gdch.demo")
    rec = seeded.get("/api/allocation/recommendations", params={"patient_id": 5, "department": "oral_medicine"},
                     headers=h).json()
    sid = rec["candidates"][0]["student_id"]
    res = seeded.post("/api/allocation/assign", headers=h, json={
        "patient_id": 5, "department": "oral_medicine", "student_id": sid, "chief_complaint": "Screening referral"})
    assert res.status_code == 201, res.text
    case = res.json()
    assert case["status"] == "draft" and case["student_id"] == sid and case["department"] == "oral_medicine"
    me = seeded.get("/api/auth/me", headers=h).json()
    assert case["faculty_id"] == me["faculty"]["id"]  # caller is Oral Medicine faculty -> supervises
    # Students cannot allocate; unknown student -> 422
    assert seeded.post("/api/allocation/assign", headers=auth(seeded, "student@gdch.demo"), json={
        "patient_id": 5, "department": "oral_medicine", "student_id": sid, "chief_complaint": "x" * 5}).status_code == 403
    assert seeded.post("/api/allocation/assign", headers=h, json={
        "patient_id": 5, "department": "oral_medicine", "student_id": 99999, "chief_complaint": "Referral"}).status_code == 422


def test_resource_view_flags_departments_consistently(seeded):
    h = auth(seeded, "admin@gdch.demo")
    view = seeded.get("/api/allocation/resources", params={"days": 30}, headers=h).json()
    depts = view["departments"]
    assert len(depts) == 8
    assert sum(d["faculty"] for d in depts) == 10
    statuses = {d["status"] for d in depts}
    assert statuses <= {"overloaded", "short_supply", "balanced", "spare_capacity"}
    assert all(d["reasons"] for d in depts if d["status"] != "balanced")
    # Not everything can be overloaded: thresholds are relative to the college average.
    assert sum(d["status"] == "overloaded" for d in depts) < len(depts)


# --- Step 5: personalised learning plan ------------------------------------------------------

def test_learning_plan_matches_quota_and_marks(seeded):
    h = auth(seeded, "atrisk.student@gdch.demo")
    me = seeded.get("/api/auth/me", headers=h).json()["student"]["id"]
    plan = seeded.get(f"/api/students/{me}/learning-plan", headers=h).json()
    assert plan["is_clinical"] and plan["focus_departments"] and plan["focus_subjects"]
    quota = {d["department"]: d for d in seeded.get(f"/api/students/{me}/quota-progress", headers=h).json()["departments"]}
    for d in plan["focus_departments"]:
        assert (d["approved"], d["required"]) == (quota[d["department"]]["approved"], quota[d["department"]]["required"])
        assert d["case_types"] and d["where_to_find"]
    # Weakest subject first, and every focus subject is genuinely weak.
    avgs = [s["average_pct"] for s in plan["all_subjects"]]
    assert avgs == sorted(avgs)
    assert plan["focus_subjects"][0]["subject"] == plan["all_subjects"][0]["subject"]
    # Focus areas card lists departments in the same priority order as the learning plan.
    focus = seeded.get(f"/api/students/{me}/focus-areas", headers=h).json()
    clinical = next(i for i in focus["items"] if i["area"] == "clinical")["message"]
    first = plan["focus_departments"][0]
    assert f"({first['approved']}/{first['required']})" in clinical.split(",")[0]


def test_learning_plan_preclinical_and_access(seeded):
    admin = auth(seeded, "admin@gdch.demo")
    bds1 = seeded.get("/api/students", params={"year": "bds1"}, headers=admin).json()[0]
    plan = seeded.get(f"/api/students/{bds1['id']}/learning-plan", headers=admin).json()
    assert plan["is_clinical"] is False and plan["focus_departments"] == []
    other = seeded.get(f"/api/students/{bds1['id']}/learning-plan", headers=auth(seeded, "student@gdch.demo"))
    assert other.status_code == 403


# --- Step 6: marks entry, primary teeth, migrations ------------------------------------------

def test_bulk_marks_upsert_and_validation(seeded):
    h = auth(seeded, "faculty@gdch.demo")
    bds4 = seeded.get("/api/students", params={"year": "bds4"}, headers=h).json()[:3]
    subjects = seeded.get("/api/assessments/subjects", params={"year": "bds4"}, headers=h).json()
    assert "Periodontology" in subjects
    body = {"subject": "Public Health Dentistry", "exam_type": "viva", "max_marks": 20, "exam_date": "2026-01-10",
            "entries": [{"student_id": s["id"], "marks": 15} for s in bds4]}
    first = seeded.post("/api/assessments/bulk", json=body, headers=h)
    assert first.status_code == 201 and len(first.json()) == 3
    body["entries"][0]["marks"] = 18  # correction -> update, not a duplicate row
    second = seeded.post("/api/assessments/bulk", json=body, headers=h).json()
    assert {a["id"] for a in second} == {a["id"] for a in first.json()}
    assert second[0]["marks"] == 18 and second[0]["percentage"] == 90.0
    body["entries"][1]["marks"] = 25  # above max
    assert seeded.post("/api/assessments/bulk", json=body, headers=h).status_code == 422
    assert seeded.post("/api/assessments/bulk", json=body, headers=auth(seeded, "student@gdch.demo")).status_code == 403


def test_primary_teeth_in_seeded_cases(seeded):
    h = auth(seeded, "faculty@gdch.demo")
    cases = seeded.get("/api/cases", params={"department": "pedodontics", "limit": 500}, headers=h).json()["items"]
    teeth = {f["tooth_number"] for c in cases for f in c["findings"]}
    assert any(t >= 51 for t in teeth), "pedodontic cases should chart primary teeth"


def test_alembic_migration_matches_models(tmp_path, monkeypatch):
    """`alembic upgrade head` on an empty DB must produce exactly the SQLModel schema."""
    root = Path(__file__).resolve().parents[1]
    url = f"sqlite:///{(tmp_path / 'migrated.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()  # env.py reads DATABASE_URL through the cached settings
    try:
        cfg = Config(str(root / "alembic.ini"))
        cfg.set_main_option("script_location", str(root / "migrations"))
        command.upgrade(cfg, "head")
        engine = create_engine(url)
        with engine.connect() as conn:
            diff = compare_metadata(MigrationContext.configure(conn), SQLModel.metadata)
        engine.dispose()
        assert diff == [], diff
        command.downgrade(cfg, "base")
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()


# --- Phase 3: notifications produced from the seeded data ----------------------------------

def test_at_risk_and_allocation_notifications(seeded):
    admin = auth(seeded, "admin@gdch.demo")
    notes = seeded.get("/api/notifications", headers=admin, params={"limit": 200}).json()
    at_risk = [n for n in notes if n["kind"] == "at_risk_alert"]
    gt = _ground_truth()
    flagged_rolls = {n["title"].split("(")[-1].rstrip(")") for n in at_risk}
    assert flagged_rolls == {roll for roll, risk in gt.items() if risk}
    # Re-running the scan inside the dedupe window creates nothing new.
    before = len(at_risk)
    seeded.post("/api/notifications/refresh-alerts", headers=admin)
    again = [n for n in seeded.get("/api/notifications", headers=admin, params={"limit": 200}).json()
             if n["kind"] == "at_risk_alert"]
    assert len(again) == before

    faculty = auth(seeded, "faculty@gdch.demo")
    rec = seeded.get("/api/allocation/recommendations", params={"patient_id": 7, "department": "periodontics"},
                     headers=faculty).json()
    sid = rec["candidates"][0]["student_id"]
    seeded.post("/api/allocation/assign", headers=faculty, json={
        "patient_id": 7, "department": "periodontics", "student_id": sid, "chief_complaint": "Scaling referral"})
    student_user = next(s for s in seeded.get("/api/students", headers=admin).json() if s["id"] == sid)
    from sqlmodel import Session, select

    from app.database import engine
    from app.models import Notification

    with Session(engine) as s:
        kinds = s.exec(select(Notification.kind).where(Notification.user_id == student_user["user_id"])).all()
    assert "patient_allocated" in kinds


# --- Phase 3: FHIR export ---------------------------------------------------------------------

def test_fhir_export_is_valid_and_audited(seeded):
    from fhir.resources.R4B.bundle import Bundle

    h = auth(seeded, "faculty@gdch.demo")
    patients = seeded.get("/api/patients", params={"limit": 200}, headers=h).json()["items"]
    pid = next(p["id"] for p in patients if p["abha_id"] and p["visit_count"] >= 2)
    res = seeded.get(f"/api/patients/{pid}/fhir", headers=h)
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("application/fhir+json")
    assert "attachment" in res.headers["content-disposition"]
    bundle = res.json()

    parsed = Bundle.model_validate(bundle)  # structural validation against FHIR R4B models
    assert parsed.type == "collection"
    types = [e["resource"]["resourceType"] for e in bundle["entry"]]
    assert types[0] == "Patient" and {"Encounter", "Condition", "Procedure", "RiskAssessment"} <= set(types)

    patient = bundle["entry"][0]["resource"]
    systems = {i["system"] for i in patient["identifier"]}
    assert "https://healthid.ndhm.gov.in" in systems  # ABHA number exported
    assert patient["address"][0]["state"] == "Goa"

    full_urls = {e["fullUrl"] for e in bundle["entry"]}
    for e in bundle["entry"]:
        for value in e["resource"].values():
            if isinstance(value, dict) and "reference" in value:
                assert value["reference"] in full_urls  # every reference resolves inside the bundle

    # Exports are audited
    audit = seeded.get("/api/audit", params={"action": "export", "entity_id": pid},
                       headers=auth(seeded, "admin@gdch.demo")).json()
    assert audit["total"] >= 1
