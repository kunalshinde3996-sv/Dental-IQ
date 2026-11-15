import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { overviewApi } from '../api'
import type { CaseStatus, Department } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import { RiskBadge } from '../components/RiskPanel'
import { Badge, Card, CardHeader, EmptyState, ErrorBanner, PageHeader, ProgressBar, Spinner, cx } from '../components/ui'
import { DEPARTMENTS, DEPARTMENT_SHORT } from '../lib/labels'
import { useApi } from '../lib/useApi'

function Tile({ label, value, hint, to, tone }: { label: string; value: ReactNode; hint?: string; to?: string; tone?: 'alert' | 'good' }) {
  const body = (
    <Card className={cx('h-full p-4 transition', to && 'hover:ring-brand-300')}>
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className={cx('mt-1 text-3xl font-semibold tabular-nums', tone === 'alert' ? 'text-rose-700' : tone === 'good' ? 'text-emerald-700' : 'text-slate-900')}>{value}</p>
      {hint && <p className="mt-0.5 text-xs text-slate-500">{hint}</p>}
    </Card>
  )
  return to ? <Link to={to} className="block rounded-xl focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500">{body}</Link> : body
}

function QuickLink({ to, children }: { to: string; children: ReactNode }) {
  return (
    <Link to={to} className="inline-flex items-center gap-1 rounded-lg bg-white px-3 py-2 text-sm font-medium text-brand-700 ring-1 ring-inset ring-slate-200 hover:bg-brand-50">
      {children} <span aria-hidden>→</span>
    </Link>
  )
}

const pct = (v: number | null | undefined) => (v === null || v === undefined ? '—' : `${Math.round(v)}%`)
const sumCases = (c: Record<CaseStatus, number>) => Object.values(c).reduce((a, b) => a + b, 0)

function AlertsCard({ alerts, high }: { alerts: { student_id: number; name: string; roll_no: string; reason: string }[]; high: number }) {
  return (
    <Card>
      <CardHeader title="Students needing attention" subtitle={`${high} at High risk`} action={<QuickLink to="/at-risk">All alerts</QuickLink>} />
      {alerts.length === 0 ? <EmptyState title="No High-risk students right now" /> : (
        <ul className="divide-y divide-slate-100">
          {alerts.map((a) => (
            <li key={a.student_id} className="flex flex-wrap items-start justify-between gap-2 px-5 py-3">
              <div className="min-w-0">
                <p className="text-sm font-medium text-slate-900">{a.name} <span className="font-normal text-slate-500">· {a.roll_no}</span></p>
                <p className="text-xs text-slate-600">{a.reason}</p>
              </div>
              <RiskBadge level="High" />
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}

function DepartmentFlags({ overloaded, short }: { overloaded: Department[]; short: Department[] }) {
  return (
    <Card>
      <CardHeader title="Department load (30 days)" action={<QuickLink to="/department-load">Details</QuickLink>} />
      <div className="space-y-3 p-5 text-sm">
        <div>
          <p className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-500">Overloaded</p>
          {overloaded.length ? <div className="flex flex-wrap gap-1.5">{overloaded.map((d) => <Badge key={d} className="bg-rose-50 text-rose-700 ring-rose-200">{DEPARTMENT_SHORT[d]}</Badge>)}</div> : <p className="text-slate-500">None</p>}
        </div>
        <div>
          <p className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-500">Short of patients</p>
          {short.length ? <div className="flex flex-wrap gap-1.5">{short.map((d) => <Badge key={d} className="bg-amber-50 text-amber-800 ring-amber-200">{DEPARTMENT_SHORT[d]}</Badge>)}</div> : <p className="text-slate-500">None</p>}
        </div>
      </div>
    </Card>
  )
}

/** Landing page after login: the few numbers each role needs first. */
export function OverviewPage() {
  const { me } = useAuth()
  const { data, error, loading, reload } = useApi(() => overviewApi.get(), [])
  if (!me) return null
  const first = me.user.name.replace(/^Dr\.\s*/, '').split(' ')[0]
  const greeting = new Date().getHours() < 12 ? 'Good morning' : new Date().getHours() < 17 ? 'Good afternoon' : 'Good evening'

  return (
    <>
      <PageHeader title={`${greeting}, ${first}`} docTitle="Overview" subtitle="Your most important numbers at a glance." />
      {error && <ErrorBanner message={error} onRetry={reload} />}
      {loading && !data && <Card><Spinner label="Loading overview…" rows={5} /></Card>}

      {data?.student && (() => {
        const s = data.student
        return (
          <div className="space-y-6">
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
              <Tile label="Clinical quota" value={pct(s.quota_percent)} hint={s.quota_percent === null ? 'Pre-clinical year' : `${s.quota_approved} of ${s.quota_required} approved`} to="/my-cases" />
              <Tile label="Attendance" value={s.attendance_pct === null ? '—' : `${s.attendance_pct.toFixed(1)}%`} hint="Last 12 weeks · 75% required" tone={(s.attendance_pct ?? 100) < 75 ? 'alert' : undefined} />
              <Tile label="Awaiting review" value={s.cases.submitted} hint="Submitted cases" to="/my-cases" />
              <Tile label="Needs changes" value={s.cases.rejected} hint="Returned by faculty" tone={s.cases.rejected ? 'alert' : undefined} to="/my-cases" />
            </div>
            {s.quota_percent !== null && <Card className="p-5"><p className="mb-2 text-sm font-medium text-slate-800">Overall quota progress</p><ProgressBar percent={s.quota_percent} label="Overall quota progress" /></Card>}
            <Card>
              <CardHeader title="Focus this month" subtitle={s.focus.summary} action={<QuickLink to="/my-cases">Learning plan</QuickLink>} />
              {s.focus.items.length === 0 ? <EmptyState title="Nothing to fix: you're on track">{s.focus.strengths.join(' ')}</EmptyState> : (
                <ul className="divide-y divide-slate-100">
                  {s.focus.items.map((i) => <li key={i.title + i.message} className="px-5 py-3 text-sm"><span className="font-semibold text-slate-900">{i.title}: </span><span className="text-slate-700">{i.message}</span></li>)}
                </ul>
              )}
            </Card>
            <div className="flex flex-wrap gap-2">
              <QuickLink to="/cases/new">Record a new case</QuickLink>
              {s.next_department && <QuickLink to="/cases/new">Seek {DEPARTMENTS[s.next_department]} cases</QuickLink>}
              <QuickLink to="/patients">Find a patient</QuickLink>
            </div>
          </div>
        )
      })()}

      {data?.faculty && (() => {
        const f = data.faculty
        return (
          <div className="space-y-6">
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
              <Tile label="Awaiting your review" value={f.pending_reviews} to="/approvals" tone={f.pending_reviews > 20 ? 'alert' : undefined} hint="Submitted cases you supervise" />
              <Tile label="High-risk students" value={f.at_risk.High} to="/at-risk" tone={f.at_risk.High ? 'alert' : 'good'} hint={`${f.at_risk.Medium} more on the watch list`} />
              <Tile label="Cases you reviewed" value={f.reviewed_by_me} hint="Approved + returned" />
              <Tile label="Unread notifications" value={data.unread_notifications} hint="Bell icon in the sidebar" />
            </div>
            <Card className="p-5">
              <p className="text-sm text-slate-700">
                <span className="font-semibold text-slate-900">{DEPARTMENTS[f.department]}</span>: {f.department_load.cases_per_faculty ?? '—'} cases per faculty member in the last 30 days, {f.department_load.pending_reviews} awaiting review.{' '}
                <Badge className={f.department_load.status === 'overloaded' ? 'bg-rose-50 text-rose-700 ring-rose-200' : 'bg-slate-100 text-slate-700 ring-slate-200'}>{f.department_load.status.replace('_', ' ')}</Badge>
              </p>
              {f.department_load.reasons.map((r) => <p key={r} className="mt-1 text-xs text-slate-600">{r}</p>)}
            </Card>
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
              <div className="lg:col-span-2"><AlertsCard alerts={f.top_alerts} high={f.at_risk.High} /></div>
              <DepartmentFlags overloaded={f.overloaded_departments} short={f.short_supply_departments} />
            </div>
            <div className="flex flex-wrap gap-2">
              <QuickLink to="/approvals">Review queue</QuickLink>
              <QuickLink to="/allocate">Allocate a patient</QuickLink>
              <QuickLink to="/insights">Population insights</QuickLink>
            </div>
          </div>
        )
      })()}

      {data?.admin && (() => {
        const a = data.admin
        return (
          <div className="space-y-6">
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
              <Tile label="Students" value={a.students} to="/admin/students" />
              <Tile label="Faculty" value={a.faculty} to="/admin/faculty" />
              <Tile label="Patients" value={a.patients.toLocaleString('en-IN')} hint={`${a.abha_linked_pct}% ABHA-linked`} to="/patients" />
              <Tile label="Clinical cases" value={sumCases(a.cases).toLocaleString('en-IN')} hint={`${a.cases.submitted} awaiting review`} />
              <Tile label="High-risk students" value={a.at_risk.High} to="/at-risk" tone={a.at_risk.High ? 'alert' : 'good'} hint={`${a.at_risk.Medium} on the watch list`} />
              <Tile label="Overloaded departments" value={a.overloaded_departments.length} to="/department-load" tone={a.overloaded_departments.length ? 'alert' : 'good'} />
              <Tile label="Audit events today" value={a.audit_events_today} to="/audit" />
              <Tile label="Failed logins today" value={a.failed_logins_today} to="/audit" tone={a.failed_logins_today > 10 ? 'alert' : undefined} />
            </div>
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
              <div className="lg:col-span-2"><AlertsCard alerts={a.top_alerts} high={a.at_risk.High} /></div>
              <DepartmentFlags overloaded={a.overloaded_departments} short={a.short_supply_departments} />
            </div>
          </div>
        )
      })()}
    </>
  )
}
