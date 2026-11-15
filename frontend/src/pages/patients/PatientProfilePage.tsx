import type { ReactNode } from 'react'
import { Link, useParams } from 'react-router-dom'
import { patientsApi } from '../../api'
import { useAuth } from '../../auth/AuthContext'
import { RiskPanel } from '../../components/RiskPanel'
import { Card, CardHeader, EmptyState, ErrorBanner, PageHeader, Spinner, StatusBadge } from '../../components/ui'
import { formatDate } from '../../lib/format'
import { DEPARTMENTS, HABITS, SEXES, TALUKAS } from '../../lib/labels'
import { useApi } from '../../lib/useApi'
import { HabitBadges } from './HabitBadges'
import { PatientExportActions } from './PatientExportActions'

function Detail({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="mt-0.5 text-sm text-slate-800">{value || '—'}</dd>
    </div>
  )
}

export function PatientProfilePage() {
  const { id } = useParams()
  const { me } = useAuth()
  const { data: p, error, loading, reload } = useApi(() => patientsApi.get(Number(id)), [id])

  if (loading && !p) return <Spinner />
  if (error) return <ErrorBanner message={error} onRetry={reload} />
  if (!p) return null

  const conditions = [p.has_diabetes && 'Diabetes', p.has_hypertension && 'Hypertension', p.has_cardiac_disease && 'Cardiac disease'].filter(Boolean)

  return (
    <>
      <PageHeader
        title={p.name}
        subtitle={
          <>
            {p.opd_number} · {p.age} yrs · {SEXES[p.sex]} · {TALUKAS[p.taluka]}
            {p.is_synthetic && <span className="ml-2 rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-500">Synthetic record</span>}
          </>
        }
        actions={
          <>
            <PatientExportActions patientId={p.id} opdNumber={p.opd_number} />
            <Link to={`/patients/${p.id}/edit`} className="inline-flex items-center rounded-lg bg-white px-4 py-2 text-sm font-medium text-slate-700 ring-1 ring-inset ring-slate-300 hover:bg-slate-50">
              Edit details
            </Link>
            {me?.user.role === 'student' && (
              <Link to={`/cases/new?patient_id=${p.id}`} className="inline-flex items-center rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700">
                + New case
              </Link>
            )}
          </>
        }
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-1">
          <Card>
            <CardHeader title="Oral cancer risk screening" subtitle="Explainable model · habits, age, taluka, lesions" />
            <div className="p-5">
              <RiskPanel patientId={p.id} />
            </div>
          </Card>
          <Card>
            <CardHeader title="Patient details" />
            <dl className="grid grid-cols-2 gap-4 p-5">
              <Detail label="ABHA number" value={p.abha_id ? <span className="font-mono">{p.abha_id}</span> : 'Not linked'} />
              <Detail label="Mobile" value={p.phone} />
              <Detail label="Registered" value={formatDate(p.created_at)} />
              <Detail label="Visits" value={p.visits.length} />
            </dl>
          </Card>
          <Card>
            <CardHeader title="Risk profile" />
            <div className="space-y-4 p-5">
              <HabitBadges patient={p} />
              <dl className="grid grid-cols-2 gap-4">
                <Detail label="Smokeless tobacco" value={HABITS[p.smokeless_tobacco]} />
                <Detail label="Smoking" value={HABITS[p.tobacco_smoking]} />
                <Detail label="Alcohol" value={HABITS[p.alcohol]} />
                <Detail label="Habit duration" value={p.habit_duration_years != null ? `${p.habit_duration_years} yrs` : null} />
              </dl>
            </div>
          </Card>
          <Card>
            <CardHeader title="Medical history" />
            <dl className="space-y-4 p-5">
              <Detail label="Conditions" value={conditions.length ? conditions.join(', ') : 'None reported'} />
              <Detail label="Allergies" value={p.allergies ?? 'None reported'} />
              {p.medical_history_notes && <Detail label="Notes" value={p.medical_history_notes} />}
            </dl>
          </Card>
        </div>

        <Card className="lg:col-span-2">
          <CardHeader title="Visit history" subtitle="Every supervised clinical case for this patient, newest first." />
          {p.visits.length === 0 ? (
            <EmptyState title="No visits yet" />
          ) : (
            <ol className="relative space-y-0 p-5">
              {p.visits.map((v, i) => (
                <li key={v.id} className="relative pb-6 pl-8 last:pb-0">
                  {i < p.visits.length - 1 && <span className="absolute left-[11px] top-6 h-full w-px bg-slate-200" aria-hidden />}
                  <span className="absolute left-0 top-1 flex h-6 w-6 items-center justify-center rounded-full bg-brand-100 ring-4 ring-white">
                    <span className="h-2 w-2 rounded-full bg-brand-600" />
                  </span>
                  <Link to={`/cases/${v.id}`} className="block rounded-lg p-3 ring-1 ring-slate-200 transition hover:bg-brand-50/40 hover:ring-brand-300">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="text-sm font-semibold text-slate-900">{DEPARTMENTS[v.department]}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-slate-500">{formatDate(v.visit_date)}</span>
                        <StatusBadge status={v.status} />
                      </div>
                    </div>
                    <p className="mt-1 text-sm text-slate-700">
                      <span className="text-slate-500">C/O:</span> {v.chief_complaint}
                    </p>
                    {v.diagnosis && (
                      <p className="text-sm text-slate-700">
                        <span className="text-slate-500">Dx:</span> {v.diagnosis}
                      </p>
                    )}
                    {v.procedure && (
                      <p className="text-sm text-slate-700">
                        <span className="text-slate-500">Rx:</span> {v.procedure}
                      </p>
                    )}
                    <p className="mt-1.5 text-xs text-slate-500">
                      {v.student_name} · supervised by {v.faculty_name}
                      {v.findings_count > 0 && ` · ${v.findings_count} tooth finding${v.findings_count > 1 ? 's' : ''}`}
                    </p>
                  </Link>
                </li>
              ))}
            </ol>
          )}
        </Card>
      </div>
    </>
  )
}
