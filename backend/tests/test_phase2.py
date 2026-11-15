"""Phase-2 tests on a fully seeded (synthetic) database: analytics consistency, ML sanity, alerts, allocation."""
import pytest
from fastapi.testclient import TestClient

from app.main import app

PASSWORDS = {
    "admin@gdch.demo": "Admin@123",
    "faculty@gdch.demo": "Faculty@123",
    "student@gdch.demo": "Student@123",
    "atrisk.student@gdch.demo": "Student@123",
}


@pytest.fixture(scope="module")
def seeded():
    from scripts.seed import seed

    seed(reset=True, train=False, verbose=False)
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
