import { useEffect, type ReactNode } from 'react'
import { Link, useParams } from 'react-router-dom'
import { patientsApi } from '../../api'
import type { ToothFindingInput } from '../../api/types'
import { useAuth } from '../../auth/AuthContext'
import { Logo } from '../../components/Logo'
import { RiskPanel } from '../../components/RiskPanel'
import { FindingsTable, ToothChart, isPrimary } from '../../components/ToothChart'
import { Button, ErrorBanner, Spinner, StatusBadge, useDocumentTitle } from '../../components/ui'
import { formatDate } from '../../lib/format'
import { DEPARTMENTS, HABITS, SEXES, TALUKAS } from '../../lib/labels'
import { useTheme } from '../../lib/theme'
import { useApi } from '../../lib/useApi'

function Section({ title, children, keepTogether = true }: { title: string; children: ReactNode; keepTogether?: boolean }) {
  return (
    <section className={keepTogether ? 'break-inside-avoid border-t border-slate-200 pt-4' : 'border-t border-slate-200 pt-4'}>
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-brand-800">{title}</h2>
      {children}
    </section>
  )
}

function Item({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div>
      <dt className="text-[11px] uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="text-sm text-slate-900">{value || '—'}</dd>
    </div>
  )
}

/** Latest recorded finding per tooth across all visits (chronological, newest wins). */
function currentChart(cases: { visit_date: string; id: number; findings: ToothFindingInput[] }[]): ToothFindingInput[] {
  const byTooth = new Map<number, ToothFindingInput>()
  for (const c of [...cases].sort((a, b) => a.visit_date.localeCompare(b.visit_date) || a.id - b.id)) {
    for (const f of c.findings) byTooth.set(f.tooth_number, f)
  }
  return [...byTooth.values()].sort((a, b) => a.tooth_number - b.tooth_number)
}

/** Clean, printable patient summary (use the browser's "Save as PDF" to get a PDF). */
export function PatientPrintPage() {
  const { id } = useParams()
  const { me } = useAuth()
  const patient = useApi(() => patientsApi.get(Number(id)), [id])
  const { resolved } = useTheme()
  useDocumentTitle(patient.data ? `${patient.data.name}: summary` : 'Patient summary')

  // A printed record is always light, whatever the app theme.
  useEffect(() => {
    document.documentElement.classList.remove('dark')
    return () => {
      document.documentElement.classList.toggle('dark', resolved === 'dark')
    }
  }, [resolved])

  if (patient.error) return <div className="p-6"><ErrorBanner message={patient.error} /></div>
  if (!patient.data) return <Spinner label="Preparing summary…" />
  const p = patient.data
  const recorded = p.visits.filter((c) => c.status !== 'draft')
  const chart = currentChart(recorded)
  const permanent = chart.filter((f) => !isPrimary(f.tooth_number))
  const primary = chart.filter((f) => isPrimary(f.tooth_number))
  const conditions = [p.has_diabetes && 'Diabetes', p.has_hypertension && 'Hypertension', p.has_cardiac_disease && 'Cardiac disease'].filter(Boolean)

  return (
    <div className="min-h-screen bg-slate-100 py-6 print:bg-white print:py-0">
      <div className="mx-auto mb-4 flex max-w-4xl justify-between gap-2 px-4 print:hidden">
        <Link to={`/patients/${p.id}`} className="inline-flex items-center rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-200">← Back to patient</Link>
        <Button onClick={() => window.print()}>Print / Save as PDF</Button>
      </div>

      <article className="mx-auto max-w-4xl space-y-5 bg-white p-4 text-slate-900 shadow sm:p-8 print:max-w-none print:p-0 print:shadow-none">
        <header className="flex items-start justify-between gap-4">
          <div>
            <Logo className="text-slate-900" />
            <p className="mt-1 text-xs text-slate-500">Patient dental summary</p>
          </div>
          <div className="text-right text-xs text-slate-500">
            <p>Generated {new Date().toLocaleString('en-IN')}</p>
            <p>by {me?.user.name}</p>
          </div>
        </header>

        {p.is_synthetic && (
          <p className="rounded border border-amber-300 bg-amber-50 px-3 py-1.5 text-xs text-amber-900">
            Synthetic demo record: not a real patient. Not for clinical use.
          </p>
        )}

        <Section title="Patient">
          <h1 className="mb-3 text-xl font-semibold">{p.name}</h1>
          <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4 print:grid-cols-4">
            <Item label="OPD number" value={p.opd_number} />
            <Item label="ABHA number" value={p.abha_id ?? 'Not linked'} />
            <Item label="Age / sex" value={`${p.age} · ${SEXES[p.sex]}`} />
            <Item label="Taluka" value={TALUKAS[p.taluka]} />
            <Item label="Mobile" value={p.phone} />
            <Item label="Smokeless tobacco" value={HABITS[p.smokeless_tobacco]} />
            <Item label="Smoking" value={HABITS[p.tobacco_smoking]} />
            <Item label="Alcohol" value={HABITS[p.alcohol]} />
            <Item label="Medical conditions" value={conditions.length ? conditions.join(', ') : 'None reported'} />
            <Item label="Allergies" value={p.allergies ?? 'None reported'} />
          </dl>
        </Section>

        <Section title="Oral cancer risk screening">
          <RiskPanel patientId={p.id} compact />
        </Section>

        <Section title="Dental chart (latest finding per tooth)" keepTogether={false}>
          {chart.length === 0 && <p className="text-sm text-slate-500">No tooth findings recorded.</p>}
          {(permanent.length > 0 || primary.length === 0) && chart.length > 0 && (
            <div className="overflow-x-auto print:overflow-visible"><ToothChart findings={permanent} readOnly preferredDentition="permanent" hideDentitionToggle /></div>
          )}
          {primary.length > 0 && (
            <div className="mt-4 overflow-x-auto print:overflow-visible"><ToothChart findings={primary} readOnly preferredDentition="primary" hideDentitionToggle /></div>
          )}
          {chart.length > 0 && <div className="mt-4 overflow-x-auto print:overflow-visible"><FindingsTable findings={chart} /></div>}
        </Section>

        <Section title={`Visit history (${recorded.length})`} keepTogether={false}>
          {recorded.length === 0 ? <p className="text-sm text-slate-500">No recorded visits.</p> : (
            <div className="overflow-x-auto print:overflow-visible"><table className="w-full text-left text-xs">
              <thead className="text-slate-500">
                <tr><th className="py-1 pr-2">Date</th><th className="py-1 pr-2">Department</th><th className="py-1 pr-2">Diagnosis</th><th className="py-1 pr-2">Procedure</th><th className="py-1 pr-2">Clinician</th><th className="py-1">Status</th></tr>
              </thead>
              <tbody className="divide-y divide-slate-100 align-top">
                {recorded.map((c) => (
                  <tr key={c.id} className="break-inside-avoid">
                    <td className="whitespace-nowrap py-1.5 pr-2">{formatDate(c.visit_date)}</td>
                    <td className="py-1.5 pr-2">{DEPARTMENTS[c.department]}</td>
                    <td className="py-1.5 pr-2">{c.diagnosis ?? '—'}</td>
                    <td className="py-1.5 pr-2">{c.procedure ?? '—'}</td>
                    <td className="py-1.5 pr-2">{c.student_name}<br /><span className="text-slate-500">sup. {c.faculty_name}</span></td>
                    <td className="py-1.5"><StatusBadge status={c.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table></div>
          )}
        </Section>

        <footer className="border-t border-slate-200 pt-3 text-[10px] text-slate-500">
          Dental-IQ · Confidential health record: handle per institutional policy. Risk estimates come from a model
          trained on synthetic data and are a screening aid only.
        </footer>
      </article>
    </div>
  )
}
