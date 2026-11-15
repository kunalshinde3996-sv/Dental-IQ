# Dental-IQ

**AI-ready dental records + student competency platform for Goa Dental College & Hospital.**
Hackathon prototype · **Phase 2 of 3** (intelligence layer: analytics + explainable ML).

In a dental college, students treat hospital patients under faculty supervision. Dental-IQ makes
**one clinical case entry** feed three things at once:

```
Student records a case (FDI tooth chart) ──► Faculty approves / rejects with remarks
        │
        ├─► Patient EHR        – visit history + explainable oral-cancer risk screening
        ├─► Student competency – quota progress, at-risk alerts, learning plan, smart allocation
        └─► Population data    – taluka-wise disease burden, habit ↔ lesion associations, insights
```

### Differentiators
1. **One case entry → patient record + student competency + population data**
2. **India-ready**: ABHA ID, tobacco / gutkha / alcohol history driving an **oral-cancer risk screen**, Goa **taluka** insights
3. **Explainable at-risk alerts**: reasons ("Attendance fell from 72% to 49% in the last 4 weeks") + suggested actions, never a bare score
4. **Smart patient allocation**: patients routed to the students with the largest quota gaps, with a "why" for each

Docs: [`docs/existing-solutions.md`](docs/existing-solutions.md) (gap analysis) ·
[`docs/data-model.md`](docs/data-model.md) (schema) · [`docs/ml-report.md`](docs/ml-report.md) (models & metrics)

---

## Tech stack

| Layer | Stack |
|---|---|
| Backend | Python 3.11+ · FastAPI · SQLModel · SQLite (PostgreSQL via `DATABASE_URL`) · Alembic · JWT · bcrypt |
| ML | scikit-learn (logistic regression only: every prediction is decomposable) · NumPy · joblib |
| Frontend | React 19 · TypeScript · Vite · Tailwind CSS · React Router · Recharts |
| Tests | pytest: 30 tests (Phase-1 API + Phase-2 analytics consistency, ML sanity, alerts, allocation, migrations) |

## Quick start

Prerequisites: **Python 3.11+** and **Node 18+**.

### 1. Backend (http://localhost:8000, Swagger at http://localhost:8000/docs)

```bash
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\activate        macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                       # Windows cmd: copy .env.example .env
python -m scripts.seed --reset             # synthetic data + trains both ML models (~15 s)
python -m ml.train                         # optional: retrain and rewrite docs/ml-report.md
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend (http://localhost:5173)

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api/*` to the backend.

### Demo logins

The login page has one-click buttons for these.

| Role | Email | Password | What to try |
|---|---|---|---|
| Student (strong, BDS IV) | `student@gdch.demo` | `Molar#2026` | My Cases: quota bars, Focus areas, Learning plan → New Case (risk panel updates when you chart a lesion; Pedodontics opens the primary-teeth chart) |
| Student (at-risk, BDS III) | `atrisk.student@gdch.demo` | `Molar#2026` | Gentle focus areas (attendance, quota, weak subject) and learning plan |
| Faculty (HOD Oral Medicine) | `faculty@gdch.demo` | `Clinic#2026` | At-Risk Students (sort + drawer), Allocate Patient, Department Load, Population Insights, Mark Attendance, Marks Entry, Pending Approvals |
| Admin | `admin@gdch.demo` | `Office#2026` | Everything faculty can see + student/faculty lists |

All other generated accounts use `Dental#2026`.

### Tests

```bash
cd backend
python -m pytest -q
```

### Database migrations

The app creates missing tables at start-up for convenience (`AUTO_CREATE_TABLES=true`). For a shared or
production database set `AUTO_CREATE_TABLES=false` and use Alembic:

```bash
cd backend
alembic upgrade head                          # create / upgrade the schema
alembic revision --autogenerate -m "..."      # after changing app/models
```

Switching to PostgreSQL: `pip install psycopg2-binary`, set
`DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/dentaliq`, then `alembic upgrade head` and seed.

## Phase 2 features

| Area | Where | What |
|---|---|---|
| **Population Insights** | Faculty/Admin → Population Insights | Disease burden by taluka (bar + heat table), habits vs OSMF / leukoplakia / lesions with **prevalence ratios + 95% CI**, caries by age & sex, monthly cases per department, top diagnoses & procedures. Filters: date range, taluka, department. **Key-insight cards are generated from the queried data** (e.g. *"Adults who use or used gutkha / smokeless tobacco show 37.7x higher prevalence of OSMF ... 95% CI 9.0-157"*; wide intervals are shown, not hidden), ranked by the CI lower bound with minimum group sizes |
| **Oral cancer risk screening** | Patient profile; New Case form | Logistic regression on age, sex, smokeless tobacco, smoking, alcohol, habit duration, rural-belt taluka and observed lesion → Low/Medium/High, probability, **top factors with odds multipliers**, suggested action (biopsy referral, cessation counselling, recall). Updates live when a lesion is charted. A recorded PMD diagnosis sets the final level to High (the model's own level stays visible) |
| **At-risk student alerts** | Faculty/Admin → At-Risk Students | Signals: 12-week attendance + 4-week trend, marks average + trend, quota pace vs cohort median, rejection rate. **Rules give reasons + actions**, a logistic-regression score ranks and adds per-signal contributions. Sortable table, detail drawer with weekly attendance chart |
| **Focus areas** | Student → My Cases | Same signals in gentle, actionable wording ("Attending your next 18 sessions will take you past 75%") |
| **Learning plan** | Student → My Cases | Weakest departments (quota gaps) with **kinds of cases to seek** and where to find them; weakest subjects with an exam-type tip; weak subject + lagging department = "double priority" |
| **Smart allocation** | Faculty/Admin → Allocate Patient | Rank eligible students by quota gap (0.45), workload (0.25), pace behind cohort (0.15), seniority (0.15); low recent attendance halves the score. Each candidate shows reasons + component bars. **Assign** creates a draft case for that student |
| **Department Load** | Faculty/Admin → Department Load | Cases per faculty vs college average, review backlog, weeks needed to clear outstanding quotas → overloaded / patient shortage / balanced / spare capacity |
| **Phase-1 gaps closed** | Faculty/Admin → Mark Attendance, Marks Entry | Bulk attendance (P/L/A/E) and marks entry (upsert); **primary teeth** (FDI 51–85) with a Permanent/Primary toggle; **Alembic** migrations |

### Consistency guarantees
- Disease categories come from **one module** (`services/clinical_terms.py`), used by the dashboard, the insights and the risk-model labels.
- Quota numbers everywhere (progress bars, alerts, allocation, learning plan) come from `services/quota.py`.
- Attendance uses one 12-week window (`services/academic_policy.py`) on the dashboard card, alerts and focus areas.
- Tests assert these cross-page equalities (e.g. taluka rows sum to the summary, trend totals = case count, alert attendance = attendance card).

## Synthetic data

`python -m scripts.seed --reset` generates **synthetic, deterministic** data. Every patient is `is_synthetic = true`.

- 400 patients across Goa's 12 talukas (weighted towards Bambolim's neighbours). A **hidden logistic model** assigns
  potentially malignant disorders from smokeless tobacco, smoking, alcohol, age, habit duration and rural taluka, so the
  analytics and the risk model have a known ground truth to recover. Young children get **primary-tooth** findings.
- 60 students, 10 faculty, ~1,400 supervised cases (follow-ups within ~3 months of the first visit), 12 weeks of attendance, internal/sessional/practical marks.
- **Caries** is also a hidden per-patient condition whose probability rises with age: about **50% of children and 66% of adults**
  in the current seed (it was ~80% at every age before Phase 3).
- **10 deliberately at-risk students**: declining attendance, low case count, weak/declining marks, high rejection rate.
  Their labels are written to `ml/artifacts/seed_ground_truth.json` (never to the DB) for offline evaluation only.
- Distributions are plausible but hand-tuned. **They are not epidemiological estimates.**

## Key numbers (current seed; see `docs/ml-report.md`)

| Model | Metric |
|---|---|
| Oral-cancer / PMD risk | 5-fold CV ROC AUC **0.92** (0.80 without the lesion feature); High threshold P/R 0.63 / 0.46 |
| At-risk students (hybrid) | vs 10 designed at-risk students: **High alerts P/R 1.00 / 1.00**; watch list (High + Medium) P/R 0.77 / 1.00 |

These describe recovery of the generator's assumptions on synthetic data, **not** clinical or academic validity.

## Project structure

```
backend/
  app/
    core/        config (env), security (bcrypt, JWT), deps (auth + role guards)
    models/      SQLModel tables + enums
    schemas/     Pydantic request/response models
    services/    quota, cases, clinical_terms, analytics, allocation, learning, academic_policy
    routers/     auth, patients (+risk-screening), cases, students, faculty, academic,
                 admin, analytics, intelligence (alerts/focus/learning plan), allocation
  ml/            oral_risk, student_risk, train (CLI), report (renders docs/ml-report.md), artifacts/ (generated)
  migrations/    Alembic environment + versions
  scripts/       seed.py + seed_data.py
  tests/         test_api.py (Phase 1), test_phase2.py (Phase 2)
frontend/src/
  api/           typed client + endpoint functions + TS types
  auth/          session context, role guard
  components/    UI kit, AppLayout, ToothChart (permanent + primary), RiskPanel, charts, Drawer
  lib/           labels, chart colours (validated palette), formatting, useApi
  pages/         patients/, cases/, student/, faculty/, allocation/, analytics/, admin/
docs/            existing-solutions.md, data-model.md, ml-report.md
```

## API overview (Phase 2 additions)

Full interactive docs at **http://localhost:8000/docs**.

| Area | Endpoints |
|---|---|
| Population analytics (staff) | `GET /api/analytics/population` (all sections) · `/taluka-burden` · `/habit-associations` · `/caries` · `/case-trend` · `/top-terms` · `/insights`. All take `date_from`, `date_to`, `taluka`, `department` |
| Oral cancer risk | `POST /api/patients/{id}/risk-screening` (optional `{"lesion_observed": true}`) |
| Student intelligence | `GET /api/alerts/students` (staff) · `GET /api/students/{id}/risk` (staff) · `GET /api/students/{id}/focus-areas` · `GET /api/students/{id}/learning-plan` |
| Allocation (staff) | `GET /api/allocation/recommendations?patient_id=&department=` · `POST /api/allocation/assign` · `GET /api/allocation/resources?days=` |
| Academics | `POST /api/assessments/bulk` · `GET /api/assessments/subjects` (+ Phase-1 attendance/marks endpoints) |

Phase-1 endpoints (auth, patients, cases, tooth findings, students, faculty, attendance, quotas, admin) are unchanged.

## Roadmap

### Phase 1 – done
Research doc, scaffold, data model, synthetic seed, JWT + RBAC API, role-based UI with the FDI tooth chart, case lifecycle, approvals, quota progress.

### Phase 2 – done
Population insights dashboard, explainable oral-cancer risk screening, hybrid at-risk alerts with reasons and actions,
student focus areas and learning plans, smart patient allocation, department load view, attendance and marks entry
screens, primary-teeth charting, Alembic migrations, ML report.

### Phase 3 – next
- **UI polish**: dark mode, empty/loading skeletons, print-friendly patient summary, accessibility audit.
- **Deployment**: Docker Compose (API + PostgreSQL + static frontend), HTTPS, `AUTO_CREATE_TABLES=false` + migrations in CI.
- **ABDM integration**: ABHA verification (sandbox), FHIR R4 bundles (Encounter / Condition / Procedure) for HIP linking.
- **Real-data readiness**: consented de-identified data, re-training with real outcomes (detained/failed) instead of
  weak labels, prospective validation, model monitoring and versioned model cards.
- Security hardening: refresh tokens, password policy, rate limiting, audit log of record access.
- Faculty timetables (true availability in allocation), notifications for new alerts and allocations.

---
*All data in this prototype is synthetic. Not for clinical use.*
