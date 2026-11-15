import { useState } from 'react'
import { Link } from 'react-router-dom'
import { allocationApi } from '../../api'
import type { AllocationRecommendation, CaseRead, Department } from '../../api/types'
import { Badge, Button, Card, CardHeader, ErrorBanner, Field, Input, PageHeader, ProgressBar, Select, cx } from '../../components/ui'
import { DEPARTMENTS, YEARS, entries } from '../../lib/labels'
import { PatientPicker, type PickedPatient } from '../cases/PatientPicker'

const DEFAULT_COMPLAINT: Record<Department, string> = {
  oral_medicine: 'Referred for oral examination and screening',
  conservative: 'Referred for restorative treatment',
  endodontics: 'Referred for root canal treatment',
  periodontics: 'Referred for periodontal treatment',
  prosthodontics: 'Referred for prosthetic rehabilitation',
  oral_surgery: 'Referred for extraction / minor oral surgery',
  pedodontics: 'Referred for paediatric dental care',
  orthodontics: 'Referred for orthodontic assessment',
}

const COMPONENT_LABEL: Record<string, string> = {
  quota_gap: 'Quota gap in department',
  workload: 'Light current workload',
  pace: 'Behind cohort overall',
  seniority: 'Seniority (intern > BDS IV > BDS III)',
}

export function AllocatePatientPage() {
  const [patient, setPatient] = useState<PickedPatient | null>(null)
  const [department, setDepartment] = useState<Department | ''>('')
  const [complaint, setComplaint] = useState('')
  const [result, setResult] = useState<AllocationRecommendation | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [assigning, setAssigning] = useState<number | null>(null)
  const [assigned, setAssigned] = useState<CaseRead | null>(null)

  async function find() {
    if (!patient || !department) return
    setLoading(true)
    setError(null)
    setAssigned(null)
    try {
      setResult(await allocationApi.recommend(patient.id, department))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load recommendations')
    } finally {
      setLoading(false)
    }
  }

  async function assign(studentId: number) {
    if (!patient || !department) return
    setAssigning(studentId)
    setError(null)
    try {
      setAssigned(await allocationApi.assign({
        patient_id: patient.id, department, student_id: studentId,
        chief_complaint: complaint.trim() || DEFAULT_COMPLAINT[department],
      }))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Assignment failed')
    } finally {
      setAssigning(null)
    }
  }

  return (
    <>
      <PageHeader title="Allocate Patient" subtitle="Route the patient to the students who need this kind of case most." />

      <Card className="mb-6">
        <CardHeader title="Patient and treatment need" />
        <div className="grid grid-cols-1 gap-4 p-5 md:grid-cols-2">
          <div className="md:col-span-2">
            <span className="mb-1 block text-sm font-medium text-slate-700">Patient</span>
            <PatientPicker value={patient} onChange={(p) => { setPatient(p); setResult(null); setAssigned(null) }} />
          </div>
          <Field label="Department needed">
            <Select value={department} onChange={(e) => { setDepartment(e.target.value as Department); setResult(null); setAssigned(null) }}>
              <option value="" disabled>Select department</option>
              {entries(DEPARTMENTS).map((d) => <option key={d} value={d}>{DEPARTMENTS[d]}</option>)}
            </Select>
          </Field>
          <Field label="Reason for referral (chief complaint)" hint="Pre-fills the student's draft case">
            <Input value={complaint} maxLength={500} placeholder={department ? DEFAULT_COMPLAINT[department] : 'Choose a department first'} onChange={(e) => setComplaint(e.target.value)} />
          </Field>
          <div className="md:col-span-2 flex justify-end">
            <Button onClick={find} loading={loading} disabled={!patient || !department}>Find best students</Button>
          </div>
        </div>
      </Card>

      {error && <div className="mb-4"><ErrorBanner message={error} /></div>}
      {assigned && (
        <div className="mb-4 rounded-lg bg-emerald-50 px-4 py-3 text-sm text-emerald-800 ring-1 ring-emerald-200" role="status">
          Draft case <Link to={`/cases/${assigned.id}`} className="font-semibold underline">#{assigned.id}</Link> created for{' '}
          <span className="font-semibold">{assigned.student_name}</span>, supervised by {assigned.faculty_name}. It now appears in their My Cases.
        </div>
      )}

      {result && (
        <>
          {result.warnings.map((w) => (
            <div key={w} className="mb-3 rounded-lg bg-amber-50 px-4 py-2 text-sm text-amber-900 ring-1 ring-amber-200">{w}</div>
          ))}
          <p className="mb-3 text-sm text-slate-500">
            Top {result.candidates.length} of {result.eligible_count} eligible students ({result.eligible_years.map((y) => YEARS[y]).join(', ')}) for{' '}
            {DEPARTMENTS[result.department]}.
          </p>
          <ol className="space-y-3">
            {result.candidates.map((c, i) => (
              <li key={c.student_id}>
                <Card className={cx('p-4', !c.available && 'opacity-80')}>
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="flex min-w-0 items-start gap-3">
                      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-600 text-sm font-semibold text-white">{i + 1}</span>
                      <div className="min-w-0">
                        <p className="font-semibold text-slate-900">{c.name} <span className="font-normal text-slate-500">· {c.roll_no} · {YEARS[c.year]}</span></p>
                        <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                          <span>Match score <span className="font-semibold tabular-nums text-slate-900">{Math.round(c.score * 100)}</span>/100</span>
                          {!c.available && <Badge className="bg-amber-50 text-amber-800 ring-amber-200">Check availability</Badge>}
                        </div>
                      </div>
                    </div>
                    <Button variant={i === 0 ? 'primary' : 'secondary'} loading={assigning === c.student_id} disabled={assigning !== null} onClick={() => assign(c.student_id)}>
                      Assign
                    </Button>
                  </div>
                  <div className="mt-3 grid grid-cols-1 gap-4 md:grid-cols-2">
                    <div>
                      <div className="mb-1 flex justify-between text-xs text-slate-600">
                        <span>{DEPARTMENTS[result.department]} quota</span>
                        <span className="tabular-nums">{c.approved}/{c.required}{c.pending ? ` (+${c.pending} pending)` : ''}</span>
                      </div>
                      <ProgressBar percent={(c.approved / c.required) * 100} tone={c.approved / c.required < 0.25 ? 'rose' : 'brand'} />
                      <ul className="mt-3 space-y-1 text-sm text-slate-700">
                        {c.reasons.map((r) => <li key={r} className="flex gap-2"><span className="text-brand-600">›</span>{r}</li>)}
                      </ul>
                    </div>
                    <div>
                      <p className="mb-1 text-xs font-medium text-slate-500">Why this rank</p>
                      <ul className="space-y-1.5">
                        {Object.entries(c.components).map(([k, v]) => (
                          <li key={k} className="text-xs">
                            <div className="flex justify-between text-slate-600">
                              <span>{COMPONENT_LABEL[k]} <span className="text-slate-400">(×{result.weights[k]})</span></span>
                              <span className="tabular-nums">{Math.round(v * 100)}%</span>
                            </div>
                            <div className="mt-0.5 h-1.5 rounded-full bg-slate-100">
                              <div className="h-full rounded-full bg-brand-500" style={{ width: `${v * 100}%` }} />
                            </div>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </Card>
              </li>
            ))}
          </ol>
          {result.candidates.length === 0 && <Card className="p-8 text-center text-sm text-slate-500">No eligible students for this department.</Card>}
        </>
      )}
    </>
  )
}
