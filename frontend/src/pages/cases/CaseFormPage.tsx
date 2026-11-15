import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { casesApi, facultyApi, patientsApi } from '../../api'
import { ApiError } from '../../api/client'
import type { Department, FacultyRead, ToothFindingInput } from '../../api/types'
import { FindingsTable, ToothChart } from '../../components/ToothChart'
import { Button, Card, CardHeader, ErrorBanner, Field, Input, PageHeader, Select, Spinner, Textarea } from '../../components/ui'
import { todayIso } from '../../lib/format'
import { DEPARTMENTS, entries } from '../../lib/labels'
import { PatientPicker, toPicked, type PickedPatient } from './PatientPicker'

/**
 * New case (/cases/new[?patient_id=]) or edit a draft/rejected case (/cases/:id/edit).
 * One entry -> patient EHR + student competency log + population data.
 */
export function CaseFormPage() {
  const { id } = useParams()
  const editing = Boolean(id)
  const [params] = useSearchParams()
  const navigate = useNavigate()

  const [patient, setPatient] = useState<PickedPatient | null>(null)
  const [department, setDepartment] = useState<Department | ''>('')
  const [facultyId, setFacultyId] = useState<number | ''>('')
  const [faculty, setFaculty] = useState<FacultyRead[]>([])
  const [visitDate, setVisitDate] = useState(todayIso())
  const [complaint, setComplaint] = useState('')
  const [diagnosis, setDiagnosis] = useState('')
  const [procedure, setProcedure] = useState('')
  const [findings, setFindings] = useState<ToothFindingInput[]>([])
  const [remarks, setRemarks] = useState<string | null>(null)

  const [loading, setLoading] = useState(editing || params.has('patient_id'))
  const [saving, setSaving] = useState<'draft' | 'submit' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  // Load an existing case for editing, or preselect a patient from ?patient_id=
  useEffect(() => {
    if (id) {
      casesApi
        .get(Number(id))
        .then((c) => {
          if (c.status !== 'draft' && c.status !== 'rejected') {
            navigate(`/cases/${c.id}`, { replace: true })
            return
          }
          setPatient({ id: c.patient_id, name: c.patient_name, opd_number: c.patient_opd_number, detail: '' })
          setDepartment(c.department)
          setFacultyId(c.faculty_id)
          setVisitDate(c.visit_date)
          setComplaint(c.chief_complaint)
          setDiagnosis(c.diagnosis ?? '')
          setProcedure(c.procedure ?? '')
          setFindings(c.findings.map(({ tooth_number, condition, surfaces, treatment, notes }) => ({ tooth_number, condition, surfaces, treatment, notes })))
          setRemarks(c.status === 'rejected' ? c.faculty_remarks : null)
        })
        .catch((e: Error) => setError(e.message))
        .finally(() => setLoading(false))
      return
    }
    const pid = params.get('patient_id')
    if (pid) {
      patientsApi
        .get(Number(pid))
        .then((p) => setPatient(toPicked(p)))
        .catch(() => setError('Could not load the selected patient'))
        .finally(() => setLoading(false))
    }
  }, [id, params, navigate])

  // Supervisors are filtered to the chosen department.
  useEffect(() => {
    if (!department) {
      setFaculty([])
      return
    }
    facultyApi
      .list(department)
      .then((list) => {
        setFaculty(list)
        setFacultyId((cur) => (list.some((f) => f.id === cur) ? cur : list.length === 1 ? list[0].id : ''))
      })
      .catch(() => setFaculty([]))
  }, [department])

  async function save(mode: 'draft' | 'submit') {
    const errs: Record<string, string> = {}
    if (!patient) errs.patient_id = 'Select a patient'
    if (!department) errs.department = 'Select a department'
    if (!facultyId) errs.faculty_id = 'Select the supervising faculty'
    if (complaint.trim().length < 3) errs.chief_complaint = 'Chief complaint is required'
    if (mode === 'submit') {
      if (!diagnosis.trim()) errs.diagnosis = 'Diagnosis is required to submit'
      if (!procedure.trim()) errs.procedure = 'Procedure is required to submit'
    }
    setFieldErrors(errs)
    if (Object.keys(errs).length) {
      setError('Please complete the highlighted fields.')
      return
    }

    setSaving(mode)
    setError(null)
    const body = {
      patient_id: patient!.id,
      faculty_id: Number(facultyId),
      department: department as Department,
      visit_date: visitDate,
      chief_complaint: complaint.trim(),
      diagnosis: diagnosis.trim() || null,
      procedure: procedure.trim() || null,
      findings,
    }
    try {
      let saved
      if (editing) {
        const { patient_id: _ignored, ...update } = body
        void _ignored
        saved = await casesApi.update(Number(id), update)
        if (mode === 'submit') saved = await casesApi.submit(saved.id)
      } else {
        saved = await casesApi.create({ ...body, submit: mode === 'submit' })
      }
      navigate(`/cases/${saved.id}`, { replace: true })
    } catch (err) {
      if (err instanceof ApiError) {
        setFieldErrors(err.fieldErrors)
        setError(err.message)
      } else setError('Could not save the case')
    } finally {
      setSaving(null)
    }
  }

  if (loading) return <Spinner />

  return (
    <>
      <PageHeader
        title={editing ? 'Edit case' : 'New clinical case'}
        subtitle="Saved to the patient record. Counts toward your clinical quota once approved."
      />

      <div className="space-y-6">
        {error && <ErrorBanner message={error} />}
        {remarks && (
          <div className="rounded-lg bg-rose-50 px-4 py-3 text-sm text-rose-800 ring-1 ring-rose-200">
            <span className="font-semibold">Returned by faculty:</span> {remarks}
          </div>
        )}

        <Card>
          <CardHeader title="Patient & supervision" />
          <div className="grid grid-cols-1 gap-4 p-5 md:grid-cols-2">
            <div className="md:col-span-2">
              <span className="mb-1 block text-sm font-medium text-slate-700">Patient *</span>
              {editing && patient ? (
                <div className="rounded-lg bg-slate-50 px-4 py-3 text-sm ring-1 ring-slate-200">
                  <span className="font-semibold">{patient.name}</span> <span className="text-slate-500">· {patient.opd_number}</span>
                </div>
              ) : (
                <PatientPicker value={patient} onChange={setPatient} error={fieldErrors.patient_id} />
              )}
            </div>
            <Field label="Department *" error={fieldErrors.department}>
              <Select value={department} onChange={(e) => setDepartment(e.target.value as Department)}>
                <option value="" disabled>Select department</option>
                {entries(DEPARTMENTS).map((d) => (
                  <option key={d} value={d}>{DEPARTMENTS[d]}</option>
                ))}
              </Select>
            </Field>
            <Field label="Supervising faculty *" error={fieldErrors.faculty_id}>
              <Select value={facultyId} disabled={!department} onChange={(e) => setFacultyId(Number(e.target.value))}>
                <option value="" disabled>{department ? 'Select faculty' : 'Choose a department first'}</option>
                {faculty.map((f) => (
                  <option key={f.id} value={f.id}>{f.name} ({f.designation})</option>
                ))}
              </Select>
            </Field>
            <Field label="Visit date *" error={fieldErrors.visit_date}>
              <Input type="date" max={todayIso()} value={visitDate} onChange={(e) => setVisitDate(e.target.value)} />
            </Field>
          </div>
        </Card>

        <Card>
          <CardHeader title="Clinical notes" />
          <div className="grid grid-cols-1 gap-4 p-5">
            <Field label="Chief complaint *" error={fieldErrors.chief_complaint}>
              <Textarea maxLength={500} value={complaint} onChange={(e) => setComplaint(e.target.value)} placeholder="In the patient's words, e.g. pain in lower right back tooth for 3 days" />
            </Field>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <Field label="Diagnosis" error={fieldErrors.diagnosis} hint="Required to submit">
                <Textarea maxLength={500} value={diagnosis} onChange={(e) => setDiagnosis(e.target.value)} />
              </Field>
              <Field label="Procedure / treatment done" error={fieldErrors.procedure} hint="Required to submit">
                <Textarea maxLength={500} value={procedure} onChange={(e) => setProcedure(e.target.value)} />
              </Field>
            </div>
          </div>
        </Card>

        <Card>
          <CardHeader title="Tooth chart (FDI)" subtitle={`${findings.length} tooth finding${findings.length === 1 ? '' : 's'} recorded`} />
          <div className="space-y-6 p-5">
            <ToothChart findings={findings} onChange={setFindings} />
            {findings.length > 0 && <FindingsTable findings={findings} />}
          </div>
        </Card>

        <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Link to={editing ? `/cases/${id}` : '/my-cases'} className="inline-flex items-center justify-center rounded-lg px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100">
            Cancel
          </Link>
          <Button variant="secondary" loading={saving === 'draft'} disabled={saving !== null} onClick={() => save('draft')}>
            Save draft
          </Button>
          <Button loading={saving === 'submit'} disabled={saving !== null} onClick={() => save('submit')}>
            Submit for approval
          </Button>
        </div>
      </div>
    </>
  )
}
