# Dental-IQ

**AI-ready dental records + student competency platform for Goa Dental College & Hospital.**
Hackathon prototype · Phase 1 of 3 (foundation + core data flow).

In a dental college, students treat hospital patients under faculty supervision. Dental-IQ makes
**one clinical case entry** feed three things at once:

```
Student records a case (FDI tooth chart) ──► Faculty approves / rejects with remarks
        │
        ├─► Patient EHR        – full visit history on the patient profile
        ├─► Student competency – approved cases count toward per-department clinical quotas
        └─► Population data    – diagnosis + findings + risk habits + taluka (analytics in Phase 2)
```

### Differentiators
1. **One case entry → patient record + student competency + population data**
2. **India-ready**: optional ABHA ID, tobacco / gutkha (smokeless) / alcohol history for oral-cancer risk, Goa taluka geography
3. **Explainable at-risk alerts** (Phase 2): reasons + suggested action, not just a score
4. **Smart patient allocation** (Phase 2): route patients to students with the largest quota gaps

See [`docs/existing-solutions.md`](docs/existing-solutions.md) for the market gap analysis and
[`docs/data-model.md`](docs/data-model.md) for the schema.

---

## Tech stack

| Layer | Stack |
|---|---|
| Backend | Python 3.11+ · FastAPI · SQLModel (SQLAlchemy 2) · SQLite (PostgreSQL via `DATABASE_URL`) · JWT (PyJWT) · bcrypt |
| Frontend | React 19 · TypeScript · Vite · Tailwind CSS · React Router |
| Tests | pytest (12 end-to-end API tests on an isolated temp DB) |

## Quick start

Prerequisites: **Python 3.11+** and **Node 18+**.

### 1. Backend (http://localhost:8000, Swagger at http://localhost:8000/docs)

```bash
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\activate        macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                       # Windows cmd: copy .env.example .env
python -m scripts.seed --reset             # synthetic demo data (~10 s)
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend (http://localhost:5173)

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api/*` to the backend, so no CORS setup is needed in development.

### Demo logins

The login page also has one-click buttons for these.

| Role | Email | Password | What to try |
|---|---|---|---|
| Student (strong, BDS IV) | `student@gdch.demo` | `Student@123` | My Cases + quota bars → New Case → tooth chart → Submit |
| Student (at-risk, BDS III) | `atrisk.student@gdch.demo` | `Student@123` | Low attendance (~68%) and quota progress (~4%) |
| Faculty (HOD Oral Medicine) | `faculty@gdch.demo` | `Faculty@123` | Pending Approvals → approve / reject with remarks |
| Admin | `admin@gdch.demo` | `Admin@123` | Overview, Students, Faculty, Patients |

All other generated accounts use the password `Password@123` (emails are listed under Admin → Students/Faculty).

### Tests

```bash
cd backend
python -m pytest -q
```

## Synthetic data

`python -m scripts.seed --reset` generates **synthetic, deterministic** data. No real patients are involved, and every
patient row has `is_synthetic = true`.

- 400 patients across Goa's 12 talukas, weighted towards those near Bambolim. Distributions for age, sex, smoking,
  smokeless tobacco (higher in rural talukas), alcohol, ABHA coverage (~45%) and diabetes/hypertension are plausible
  but hand-tuned. They are **not** epidemiological estimates.
- 60 students (12 each in BDS I–IV and interns), 10 faculty across 8 departments, clinical quotas for BDS III, BDS IV and interns.
- ~1,500 supervised cases with FDI tooth findings. Tobacco users show more OSMF, leukoplakia and suspicious-ulcer cases.
- 3 months of attendance (Mon–Sat) and internal/sessional/practical marks.
- **10 deliberately at-risk students** (low attendance, low case count, weak or declining marks). The seed prints them
  as ground truth for validating Phase-2 at-risk detection.

## Project structure

```
backend/
  app/
    core/        config (env), security (bcrypt, JWT), deps (auth + role guards)
    models/      SQLModel tables + enums
    schemas/     request/response validation (Pydantic)
    services/    shared logic: quota progress, case serialisation & access rules
    routers/     auth, patients, cases (+ tooth findings), students, faculty, academic, admin
    main.py      app factory, CORS, error handlers
  scripts/       seed.py + seed_data.py (synthetic vocabularies)
  tests/         pytest end-to-end API tests
frontend/
  src/
    api/         typed fetch client + endpoint functions + TS types mirroring the backend
    auth/        AuthContext (session, login/logout), RequireAuth (role guard)
    components/  UI kit, AppLayout (role-based nav), ToothChart (interactive FDI odontogram)
    lib/         labels/colours for enums, formatting, useApi hook
    pages/       patients/, cases/, student/, faculty/, admin/, LoginPage
docs/            existing-solutions.md, data-model.md
```

## API overview

Full interactive docs: **http://localhost:8000/docs** (use *Authorize* with a demo email and password).

| Area | Endpoints |
|---|---|
| Auth | `POST /api/auth/login` (JSON) · `POST /api/auth/token` (OAuth2 form) · `GET /api/auth/me` |
| Patients | `GET /api/patients?q=&taluka=` · `POST /api/patients` · `GET/PATCH /api/patients/{id}` · `DELETE` (admin) |
| Cases | `GET /api/cases` · `POST /api/cases` (student) · `GET/PATCH/DELETE /api/cases/{id}` · `POST /{id}/submit` · `POST /{id}/review` (supervising faculty) |
| Tooth findings | `PUT /api/cases/{id}/findings` · `POST /api/cases/{id}/findings` · `DELETE /api/cases/{id}/findings/{tooth}` |
| Students | `GET /api/students` (staff) · `/me` · `/{id}/cases` · `/{id}/quota-progress` · `/{id}/attendance-summary` |
| Faculty | `GET /api/faculty?department=` · `/me/pending-cases` · `/me/reviewed-cases` |
| Academics | `GET /api/attendance` · `POST /api/attendance/bulk` (upsert) · `GET/POST /api/assessments` · `GET /api/quotas` · `PUT /api/quotas/{id}` (admin) |
| Admin | `GET /api/admin/stats` |

**Rules enforced server-side:**
- Students only see their own cases, marks and attendance.
- Only the supervising faculty can review a case.
- The supervisor must belong to the case's department.
- Only draft or rejected cases are editable.
- Submitting a case requires a diagnosis and a procedure.
- Rejecting a case requires remarks.
- FDI numbers are validated (11–48) and each tooth may appear once per case.
- ABHA numbers must have 14 digits and be unique.
- Phone numbers must be 10-digit Indian mobile numbers.
- Errors use proper status codes: 401, 403, 404, 409 or 422.

### Switching to PostgreSQL

```bash
pip install psycopg2-binary
# backend/.env
DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/dentaliq
python -m scripts.seed --reset
```

## Roadmap

### Phase 1 – done
Research doc, monorepo scaffold, data model, synthetic seed, REST API with JWT + RBAC, tests, and a role-based
frontend: patients, interactive FDI tooth chart, case lifecycle, faculty approvals, quota progress, admin lists.

### Phase 2 – next
- **Population insights**: taluka-wise disease burden, tobacco/gutkha ↔ OSMF/leukoplakia association, caries (DMFT)
  by age band, department load trends.
- **Explainable at-risk detection**: per-student signals (attendance %, marks trend, quota pace vs. calendar) →
  risk level with human-readable reasons and suggested actions. Validate against the seeded ground truth.
- **Smart patient allocation**: rank students by quota gap × availability for an incoming patient's department.
- Attendance-marking and marks-entry screens for faculty, plus student marks view (APIs already exist).
- Alembic migrations.

### Phase 3 – later
UI polish, ABDM sandbox integration (ABHA verification, FHIR R4 bundles: Encounter / Condition / Procedure),
primary-dentition chart, audit log, deployment (Docker, PostgreSQL), refresh tokens and stronger password policy.

---
*All data in this prototype is synthetic. Not for clinical use.*
