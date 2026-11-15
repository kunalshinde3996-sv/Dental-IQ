# User Guide

A short walkthrough per role. Every account lands on **Overview** after signing in; the bell icon
shows notifications and the theme switch (Light / Dark / System) sits above your name. Click your
name to open **Account** (change password).

Demo logins are listed in the [README](../README.md#demo-logins). All data is synthetic.

## Student

1. **Overview**: clinical quota %, attendance (12 weeks), cases awaiting review, cases returned for changes, and this month's focus areas.
2. **New Case**:
   - Pick the patient (search by name, OPD number, ABHA or phone), the department and your supervising faculty.
   - The **oral cancer risk** card appears for the selected patient. Chart a *Lesion* on any tooth and it updates immediately, together with the suggested action (e.g. biopsy referral, cessation counselling).
   - Fill chief complaint, diagnosis and procedure.
   - **Tooth chart**: click a tooth (or Tab into the chart and use the arrow keys, Enter to edit, Escape to close), choose the condition, surfaces and treatment. Use **Permanent / Primary** for children; Pedodontics opens the primary chart automatically.
   - **Save draft** or **Submit for approval**.
3. **My Cases**: quota progress per department, attendance, *Focus areas* (gentle, specific suggestions) and *Your learning plan* (departments where you need cases, the kinds of cases to seek, and subjects to revise). Returned cases show the faculty remarks; edit and resubmit them.
4. **Patients**: search, register a patient (ABHA number optional; tobacco, gutkha and alcohol habits; medical history), open a profile to see the visit history, risk screening, **Print summary** and **Export FHIR**.
5. **Notifications** tell you when a case is approved or returned, or when faculty allocate a patient to you (the draft case is ready in My Cases).

## Faculty

1. **Overview**: your review queue, High-risk students, your department's load and the students needing attention.
2. **Pending Approvals**: oldest first. Expand a case, read the clinical notes and tooth findings, then **Approve** or **Reject** (remarks are required to reject). The student is notified.
3. **At-Risk Students**: sortable by risk, attendance, marks, quota pace or rejections. Click a student for the reasons, suggested actions, a weekly attendance chart and what drives the model score.
4. **Allocate Patient**: choose a patient and the department needed. Dental-IQ ranks the top 5 eligible students by quota gap, workload, pace and year, and explains each rank. **Assign** creates a draft case for that student and notifies them.
5. **Department Load**: cases per faculty member against the college average, review backlog and weeks needed to clear outstanding quotas (overloaded, short of patients, balanced, spare capacity).
6. **Population Insights**: filter by date, taluka and department. Read the auto-generated key insights, the taluka burden table, habit vs lesion prevalence ratios (with 95% confidence intervals), caries by age and sex, monthly trends and top diagnoses. Every chart has a table or tooltip with the exact numbers.
7. **Mark Attendance**: pick date, session and year; everyone starts *Present*; tap P / L / A / E; save. Saving the same session again updates it.
8. **Marks Entry**: pick year, subject, exam, max marks and date; type marks (leave blank to skip); save.

Heads of department also receive **at-risk notifications** (once per student per week).

## Admin

Everything faculty can see (except reviewing cases), plus:

1. **Overview**: totals, High-risk students, overloaded departments, ABHA coverage, audit events and failed logins today.
2. **Students / Faculty**: searchable lists.
3. **Audit Log**: who viewed, created, edited, approved, exported or signed in, filterable by action, record type, record ID, date and free text. Click a patient or case to open it.

## Exports and printing

- **Print summary** (patient profile): demographics, risk screening, latest dental chart and visit history on A4. Use the browser's *Save as PDF*.
- **Export FHIR** (patient profile): a FHIR R4 `Bundle` (Patient, Encounter, Condition, Procedure, RiskAssessment). Every export is recorded in the audit log. See [abdm-roadmap.md](abdm-roadmap.md) for what this does and does not do.
