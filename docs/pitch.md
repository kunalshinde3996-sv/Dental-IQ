# Dental-IQ: one-page pitch

## Problem
A dental college runs a hospital and a school at the same time. Students treat hospital patients
under faculty supervision, yet records, competency logs and public-health data live in separate
registers (or on paper). Faculty discover struggling students late, patients wait while students
hunt for the right cases, and the college's rich clinical data on tobacco-driven oral disease in Goa
is never analysed.

## Solution
**One supervised clinical case entry feeds three outcomes:**

1. the **patient's dental record** (FDI tooth chart, visit history, printable summary, FHIR export);
2. the **student's competency log** (department quotas, faculty approval, learning plan);
3. **population oral-health intelligence** (taluka-wise burden, habit-lesion associations, plain-language insights).

## What makes it different
| Differentiator | In the product |
|---|---|
| **One entry, three outcomes** | No double entry: approval of a case instantly updates the EHR, the quota and the dashboards |
| **India-ready** | ABHA number field, gutkha / smokeless tobacco, smoking and alcohol history, Goa talukas, FHIR R4 export as the base for ABDM |
| **Explainable at-risk alerts** | Reasons (e.g. "Attendance fell from 72% to 42% in the last 4 weeks.", from the demo data) + suggested actions, never a bare score; students see gentle "focus areas" instead of labels |
| **Smart patient allocation** | Patients routed to the students with the largest quota gaps and lightest workload, with a "why" for each |
| **Oral-cancer risk screening** | Explainable model (odds multipliers per factor) that updates live while a lesion is charted |

## vs existing solutions
Practice software (Dentrix, Open Dental) sees only patients; college ERPs and Moodle see only students;
axiUm-type dental-school systems grade students but give no explainable risk alerts, no quota-driven
allocation and no population analytics, and are costly and US-centric; ABDM is infrastructure, not an
application. Details: [existing-solutions.md](existing-solutions.md).

## Impact (what the prototype demonstrates)
- **Students**: see their gaps and what cases to seek; get patients matched to those gaps.
- **Faculty**: one review queue, early, explained warnings about students, workload visibility per department.
- **College**: an audit trail and role-based access suitable for health records, plus evidence for
  outreach (e.g. which talukas need tobacco-cessation and screening camps).
- On the synthetic demo data, High at-risk alerts identified all 10 deliberately at-risk students with no
  false alarms, and the oral-risk model reached a cross-validated AUC of 0.92 (0.80 without the lesion
  input). **These numbers come from synthetic data and are not clinical evidence.**

## Scalability
- Stateless API behind nginx; PostgreSQL via one environment variable; Alembic migrations.
- `docker compose up` starts the full stack; CI tests on SQLite and PostgreSQL.
- Analytics are computed on demand from indexed tables. At much larger scale, materialised views or a
  nightly analytics job and a shared rate-limit store (Redis) are the next steps.
- Models are small logistic regressions (milliseconds per prediction), retrained with one command.

## Roadmap
1. **Pilot readiness**: consented, de-identified real data; re-train with real outcomes; ethics review; MFA.
2. **ABDM**: sandbox, ABHA verification (M1), SNOMED CT coding, NRCeS-profiled bundles, HIP flows (M2). See [abdm-roadmap.md](abdm-roadmap.md).
3. **Operations**: faculty timetables for true availability, appointment scheduling, SMS reminders.
4. **Scale**: multi-college deployment and state-level oral-health dashboards for public-health planning.

*Prototype with synthetic data. Not for clinical use.*
