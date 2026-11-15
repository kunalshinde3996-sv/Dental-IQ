# Existing Solutions & Gap Analysis

> Scope: what a dental college in India (e.g. Goa Dental College & Hospital) could use today, and where Dental-IQ fits.

| Solution | What it does | Gaps for an Indian dental college |
|---|---|---|
| **Dentrix / Dentrix Ascend** (Henry Schein One) | Private-practice management: odontogram charting, treatment plans, scheduling, US insurance billing. | Built for a single private clinic, not a teaching hospital. No student/faculty roles, no competency tracking, no population analytics. US-centric (insurance, CDT codes), costly licences. |
| **Open Dental** | Open-source practice management; flexible charting, scheduling, reporting; data portability. | Same private-practice model. Customisable, but nothing for academic workflows, attendance or at-risk students. No ABHA integration or Indian risk-factor fields. |
| **axiUm / axiUm Ascend** (Exan / Henry Schein One) | The de-facto dental-*school* system in North America: patient records, faculty start-checks and approvals, student clinical grading, CODA accreditation reports. | Closest match, but expensive, US/CODA-oriented, and users call it clunky (G2 avg ~3.1/5). Grading is approval-centric: no *explainable* at-risk detection, no quota-gap-driven patient allocation, and no public-health insight layer. |
| **Moodle / college ERPs** (e.g. generic Indian campus ERPs) | Attendance, internal marks, timetables, fees, LMS content. | Treat clinical work as invisible: no link between a patient treated and a student's clinical quota. At-risk flags (if any) are threshold scores without explanation. No EHR. |
| **ABDM / ABHA** (National Health Authority) | National digital-health rails: ABHA ID per citizen, HIP/HIU roles, FHIR R4 record linking and consented sharing. | It is infrastructure, not an application. A hospital still needs an EHR that captures records and links them to ABHA. Integration is staged (M1 → M2 → M3). |

## The gap

Nothing on the market connects the **three things a dental college does at once**: treating patients (EHR), training students (competency), and serving a population (public-health data). Practice software sees only patients; ERPs see only students; ABDM sees only identity and exchange.

## How Dental-IQ's differentiators address the gap

1. **One case entry → three outputs.** A supervised clinical case (with FDI tooth findings) becomes the patient's EHR entry, a credit in the student's departmental competency log once faculty approve it, and an anonymised data point for population insights. No double entry. axiUm comes closest but stops at grading.
2. **India-ready by design.** Optional **ABHA ID** on every patient (a ready hook for ABDM M1/M2 linking); structured **tobacco / gutkha / alcohol** habit fields for oral-cancer and potentially malignant disorder screening (smokeless tobacco is highly prevalent; one Goa study of Katkari tribe members found 66% smokeless-tobacco use); **taluka**-level geography for Goa-specific insights. None of the US tools model these.
3. **Explainable at-risk alerts.** Instead of a bare score, each alert says *why* (e.g. "Attendance fell from 72% to 42% in the last 4 weeks." or "Clinical quota 10% complete vs cohort median 55% (19% of expected pace).") and *what to do* (mentor meeting, remedial sessions, assign specific cases). ERPs offer thresholds at best.
4. **Smart patient allocation.** New patients are matched to students with the largest clinical-quota gaps in the relevant department, so students graduate with balanced competency and patients are seen sooner. No surveyed product does this.

**Status (v1.0.0):** all four differentiators are implemented in the prototype: case entry with FDI charting and faculty approval; ABHA field, habit history, taluka analytics and a FHIR R4 export (ABDM-*ready*, no live ABDM integration, see [abdm-roadmap.md](abdm-roadmap.md)); explainable at-risk alerts; and smart allocation. The prototype runs on **synthetic data**; model metrics are in [ml-report.md](ml-report.md).

**Sources:** [Henry Schein One – axiUm](https://www.henryscheinone.com/products/axium/) · [G2 – axiUm Ascend reviews](https://www.g2.com/products/axium-ascend/reviews) · [Louisville – axiUm faculty overview](https://louisville.edu/dentistry/informatics/di-docs/Application-Support/FacultyAccessOverview.pdf/at_download/file) · [G2 – Dentrix vs Open Dental](https://www.g2.com/compare/dentrix-vs-open-dental) · [Siotek – PMS IT comparison](https://siotek.net/resources/dental-practice-management-software-comparison) · [DPI Global – ABDM](https://www.dpi.global/globaldpi/abdm) · [Medical Dialogues – ABDM integrations](https://medicaldialogues.in/news/health/over-100-health-programmes-and-apps-integrated-with-ayushman-bharat-digital-mission-111367) · [Katkari tribe oral health study, Goa (Spec Care Dentist)](https://www.citedrive.com/en/discovery/assessment-of-oral-health-status-oral-health-beliefs-and-tobacco-habits-among-the-katkari-tribe-in-goa-india-a-crosssectional-study/) · [The Goan – oral cancer in Goa](https://www.thegoan.net/life-sunday/﻿the-healthy-goan-rising-threat-of-oral-cancer-in-goa-and-how-you-can-spot-it-early/149276.html)
