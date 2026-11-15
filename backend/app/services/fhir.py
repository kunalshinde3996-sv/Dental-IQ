"""Export a patient's record as a FHIR R4 Bundle (JSON).

Scope (honest): this is an *export format*, built so a future ABDM HIP integration can reuse it.
It is not a live ABDM integration and does not claim conformance to the NRCeS (ABDM) FHIR
profiles. See docs/abdm-roadmap.md.

Contents
- Patient            demographics, OPD number + ABHA number identifiers, Goa district/taluka
- Encounter          one per submitted/approved/rejected case (drafts are incomplete; excluded)
- Condition          the case diagnosis + one per charted tooth finding (FDI tooth in bodySite)
- Procedure          the procedure performed in the case
- RiskAssessment     the latest oral-cancer risk screening, if the model is trained (optional)

Clinical concepts are exported as text: Dental-IQ does not yet map them to SNOMED CT / ICD-10.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlmodel import Session, select

from app.models import Case, Faculty, Patient, Student, User
from app.models.enums import CaseStatus, Sex, Taluka, ToothCondition

FHIR_VERSION = "4.0.1"
# Identifier systems. The OPD system is local to this demo; the ABHA system follows the ABDM
# Health ID namespace used in NRCeS examples and must be re-checked against the current IG.
OPD_SYSTEM = "urn:dental-iq:opd-number"
ABHA_SYSTEM = "https://healthid.ndhm.gov.in"

NORTH_GOA = {Taluka.pernem, Taluka.bardez, Taluka.tiswadi, Taluka.bicholim, Taluka.sattari, Taluka.ponda}
CONDITION_TEXT = {
    ToothCondition.sound: "Sound tooth", ToothCondition.caries: "Dental caries", ToothCondition.missing: "Missing tooth",
    ToothCondition.filled: "Restored tooth", ToothCondition.rct: "Root canal treated tooth",
    ToothCondition.crown: "Crowned tooth", ToothCondition.mobility: "Tooth mobility",
    ToothCondition.lesion: "Oral mucosal lesion", ToothCondition.fractured: "Fractured tooth",
    ToothCondition.impacted: "Impacted tooth", ToothCondition.extraction_indicated: "Tooth requiring extraction",
}
EXPORTED_STATUSES = (CaseStatus.submitted, CaseStatus.approved, CaseStatus.rejected)


def _ref(uid: str, display: str | None = None) -> dict:
    ref = {"reference": f"urn:uuid:{uid}"}
    if display:
        ref["display"] = display
    return ref


def _coding(system: str, code: str, display: str | None = None) -> dict:
    c = {"system": system, "code": code}
    if display:
        c["display"] = display
    return {"coding": [c]}


def _patient_resource(p: Patient, uid: str) -> dict:
    identifiers = [{"use": "usual", "system": OPD_SYSTEM, "value": p.opd_number, "type": {"text": "OPD number"}}]
    if p.abha_id:
        identifiers.append({"use": "official", "system": ABHA_SYSTEM, "value": p.abha_id, "type": {"text": "ABHA number"}})
    parts = p.name.split()
    name = {"use": "official", "text": p.name}
    if len(parts) > 1:
        name["family"] = parts[-1]
        name["given"] = parts[:-1]
    else:
        name["given"] = parts
    res = {
        "resourceType": "Patient",
        "id": uid,
        "identifier": identifiers,
        "active": True,
        "name": [name],
        "gender": {Sex.male: "male", Sex.female: "female"}.get(p.sex, "other"),
        "address": [{
            "use": "home",
            "text": f"{p.taluka.value.title()} taluka, {'North' if p.taluka in NORTH_GOA else 'South'} Goa, Goa, India",
            "district": "North Goa" if p.taluka in NORTH_GOA else "South Goa",
            "state": "Goa",
            "country": "IN",
        }],
    }
    if p.phone:
        res["telecom"] = [{"system": "phone", "value": p.phone, "use": "mobile"}]
    if p.is_synthetic:
        res["meta"] = {"tag": [{"system": "urn:dental-iq:tags", "code": "synthetic", "display": "Synthetic demo record"}]}
    return res


def build_bundle(session: Session, patient: Patient, risk: dict | None = None) -> dict:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    p_uid = str(uuid.uuid4())
    entries: list[dict] = [{"fullUrl": f"urn:uuid:{p_uid}", "resource": _patient_resource(patient, p_uid)}]
    p_ref = _ref(p_uid, patient.name)

    rows = session.exec(
        select(Case, User.name, Faculty.department)
        .join(Student, Student.id == Case.student_id).join(User, User.id == Student.user_id)
        .join(Faculty, Faculty.id == Case.faculty_id)
        .where(Case.patient_id == patient.id, Case.status.in_(EXPORTED_STATUSES))
        .order_by(Case.visit_date, Case.id)
    ).all()
    for case, student_name, _dept in rows:
        approved = case.status == CaseStatus.approved
        visit = case.visit_date.isoformat()
        dept = case.department.value.replace("_", " ").title()
        e_uid = str(uuid.uuid4())
        entries.append({"fullUrl": f"urn:uuid:{e_uid}", "resource": {
            "resourceType": "Encounter",
            "id": e_uid,
            "identifier": [{"system": "urn:dental-iq:case-id", "value": str(case.id)}],
            "status": "finished",
            "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "AMB",
                      "display": "ambulatory"},
            "serviceType": {"text": dept},
            "subject": p_ref,
            "participant": [{"individual": {"display": f"{student_name} (dental student, supervised)"}}],
            "period": {"start": visit, "end": visit},
            "reasonCode": [{"text": case.chief_complaint}],
        }})
        e_ref = _ref(e_uid)
        verification = "confirmed" if approved else "provisional"

        def condition(text: str, body_site: str | None = None) -> dict:
            c_uid = str(uuid.uuid4())
            res = {
                "resourceType": "Condition",
                "id": c_uid,
                "clinicalStatus": _coding("http://terminology.hl7.org/CodeSystem/condition-clinical", "active", "Active"),
                "verificationStatus": _coding("http://terminology.hl7.org/CodeSystem/condition-ver-status",
                                              verification, verification.title()),
                "category": [_coding("http://terminology.hl7.org/CodeSystem/condition-category",
                                     "encounter-diagnosis", "Encounter Diagnosis")],
                "code": {"text": text},
                "subject": p_ref,
                "encounter": e_ref,
                "recordedDate": visit,
            }
            if body_site:
                res["bodySite"] = [{"text": body_site}]
            return {"fullUrl": f"urn:uuid:{c_uid}", "resource": res}

        if case.diagnosis:
            entries.append(condition(case.diagnosis))
        for f in sorted(case.findings, key=lambda f: f.tooth_number):
            if f.condition == ToothCondition.sound:
                continue
            site = f"Tooth {f.tooth_number} (FDI)" + (f", surfaces {f.surfaces}" if f.surfaces else "")
            entries.append(condition(CONDITION_TEXT[f.condition], site))

        if case.procedure:
            pr_uid = str(uuid.uuid4())
            proc = {
                "resourceType": "Procedure",
                "id": pr_uid,
                "status": "completed",
                "code": {"text": case.procedure},
                "subject": p_ref,
                "encounter": e_ref,
                "performedDateTime": visit,
                "performer": [{"actor": {"display": f"{student_name} (dental student)"}}],
            }
            treated = [f"Tooth {f.tooth_number} (FDI)" for f in case.findings if f.treatment]
            if treated:
                proc["bodySite"] = [{"text": t} for t in treated]
            if case.status == CaseStatus.rejected:
                proc["note"] = [{"text": "Case documentation was returned by the supervising faculty for correction."}]
            elif case.status == CaseStatus.submitted:
                proc["note"] = [{"text": "Awaiting supervising faculty sign-off."}]
            entries.append({"fullUrl": f"urn:uuid:{pr_uid}", "resource": proc})

    if risk is not None:
        r_uid = str(uuid.uuid4())
        entries.append({"fullUrl": f"urn:uuid:{r_uid}", "resource": {
            "resourceType": "RiskAssessment",
            "id": r_uid,
            "status": "final",
            "subject": p_ref,
            "occurrenceDateTime": now,
            "method": {"text": f"Dental-IQ oral-cancer screening model v{risk['model']['version']} "
                               "(logistic regression trained on synthetic data)"},
            "prediction": [{
                "outcome": {"text": "Potentially malignant oral disorder (OSMF / leukoplakia / suspicious lesion)"},
                "probabilityDecimal": risk["probability"],
                "qualitativeRisk": {"text": risk["risk_level"]},
                "rationale": "; ".join(f"{f['label']} (x{f['odds_multiplier']} odds)" for f in risk["factors"][:4])
                             or "No elevating factors",
            }],
            "mitigation": risk["suggested_action"],
            "note": [{"text": risk["disclaimer"]}],
        }})

    return {
        "resourceType": "Bundle",
        "id": str(uuid.uuid4()),
        "meta": {"lastUpdated": now},
        "identifier": {"system": "urn:dental-iq:export", "value": f"{patient.opd_number}-{now}"},
        "type": "collection",
        "timestamp": now,
        "entry": entries,
    }
