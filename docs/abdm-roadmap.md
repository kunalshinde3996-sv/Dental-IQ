# ABDM Readiness & Roadmap

> **Status: ABDM-ready data model and export. No live ABDM integration exists.**
> Dental-IQ has not been registered with the National Health Authority, has not connected to the
> ABDM sandbox, and does not verify ABHA numbers against the national registry.

## What exists today (Phase 3)

| Capability | Where | Notes |
|---|---|---|
| ABHA number on the patient record | `patient.abha_id` | Optional, unique. Accepts 14 digits with or without separators, stored as `XX-XXXX-XXXX-XXXX` (`app/schemas/patients.py`). **Format check only**: it is not verified with ABDM. |
| FHIR R4 export | `GET /api/patients/{id}/fhir`, **Export FHIR** button on the patient profile | `Bundle` of type `collection` containing `Patient`, `Encounter`, `Condition`, `Procedure` and (if the model is trained) `RiskAssessment`. Built in `app/services/fhir.py`. |
| Export audit | Audit Log (`action = export`) | Every export records who exported which patient's record. |
| Printable summary | `/patients/{id}/print` | Patient, risk screening, dental chart and visit history; "Save as PDF" from the browser. |

### FHIR mapping

| Dental-IQ | FHIR R4 resource | Key elements |
|---|---|---|
| Patient | `Patient` | `identifier` (OPD number; ABHA number with system `https://healthid.ndhm.gov.in`), `name`, `gender`, `telecom`, `address` (taluka, North/South Goa district, state Goa), `meta.tag` = synthetic for demo data |
| Clinical case (submitted / approved / rejected) | `Encounter` | `status=finished`, `class=AMB`, `serviceType` = department, `period`, `reasonCode` = chief complaint, `participant` = treating student |
| Case diagnosis | `Condition` | `verificationStatus` = `confirmed` if faculty-approved, else `provisional`; `category=encounter-diagnosis`; `code.text` |
| Tooth finding (non-sound) | `Condition` | `code.text` (e.g. "Dental caries"), `bodySite.text` = "Tooth 36 (FDI), surfaces MO" |
| Case procedure | `Procedure` | `status=completed`, `performedDateTime`, `performer`, `bodySite` for treated teeth, `note` when documentation was returned or awaits sign-off |
| Oral-cancer risk screening | `RiskAssessment` | `prediction.probabilityDecimal`, `qualitativeRisk`, `rationale` (top factors), `mitigation` (suggested action), disclaimer note |

Draft cases are not exported (incomplete records).

### How the export was validated
- The automated test `test_fhir_export_is_valid_and_audited` parses every exported bundle with the
  [`fhir.resources`](https://pypi.org/project/fhir.resources/) **R4B** models (pydantic). For the
  resources used here, R4B is structurally equivalent to R4 (4.0.1).
- The test also checks that every `reference` resolves to a `fullUrl` inside the bundle, and that the
  ABHA identifier is present.
- **Not yet done:** validation with the official HL7 FHIR Validator (Java 11+ was not available in the
  development environment), and validation against the ABDM / NRCeS profiles.

### Known gaps (be precise about these)
- **Terminology:** diagnoses, procedures and tooth findings are exported as **text only**. There is no
  SNOMED CT / ICD-10 coding yet. ABDM profiles expect coded concepts (SNOMED CT is free for use in India).
- **Profiles:** resources do not declare or meet the NRCeS profiles (`meta.profile`), e.g. the
  OPConsultRecord document structure (`Composition` + `Bundle.type = document`).
- **Practitioners / organisation:** students and faculty appear as `display` text, not as `Practitioner`
  resources with HPR (Health Professional Registry) IDs. There is no HFR (Health Facility Registry) ID.
- **Identifier system:** the ABHA identifier system URL follows NRCeS examples and must be re-checked
  against the current implementation guide.
- **Birth date:** only age is stored, so `Patient.birthDate` is omitted.

## Roadmap to a live ABDM integration

| Step | Work | ABDM milestone |
|---|---|---|
| 1 | Register the facility in **HFR** and practitioners in **HPR**; apply for **ABDM sandbox** credentials | Prerequisite |
| 2 | **ABHA verification/creation** via the sandbox ABHA APIs (Aadhaar/mobile OTP); link verified ABHA to `patient.abha_id` | M1 |
| 3 | Map diagnoses, procedures and tooth findings to **SNOMED CT** (dental hierarchy) and ICD-10; add `Practitioner` / `Organization` resources | M2 prep |
| 4 | Produce **NRCeS-profiled** bundles (OPConsultRecord / document bundles); validate with the HL7 validator + NRCeS IG | M2 prep |
| 5 | Implement the **HIP** flows: care-context discovery and linking, consent-artefact handling, encrypted data transfer (Fidelius ECDH), callbacks | M2 |
| 6 | Optional **HIU** role to pull a patient's prior records with consent | M3 |
| 7 | Security review, audit retention policy, DPDP Act 2023 compliance review, NHA certification | Go-live |

The existing audit trail, role-based access and FHIR export are the foundations for steps 3-7.
