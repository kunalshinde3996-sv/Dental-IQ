import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { casesApi, studentsApi } from '../../api'
import type { CaseStatus } from '../../api/types'
import { useAuth } from '../../auth/AuthContext'
import { Card, CardHeader, EmptyState, ErrorBanner, PageHeader, Pagination, Spinner, StatusBadge, cx } from '../../components/ui'
import { formatDate } from '../../lib/format'
import { CASE_STATUS, DEPARTMENT_SHORT, entries } from '../../lib/labels'
import { useApi } from '../../lib/useApi'
import { FocusAreasCard } from './FocusAreasCard'
import { LearningPlanCard } from './LearningPlanCard'
import { QuotaProgressCard } from './QuotaProgressCard'

const PAGE_SIZE = 15

export function MyCasesPage() {
  const { me } = useAuth()
  const navigate = useNavigate()
  const studentId = me!.student!.id
  const [status, setStatus] = useState<CaseStatus | ''>('')
  const [offset, setOffset] = useState(0)

  const quota = useApi(() => studentsApi.quotaProgress(studentId), [studentId])
  const attendance = useApi(() => studentsApi.attendanceSummary(studentId), [studentId])
  const cases = useApi(() => casesApi.list({ status, limit: PAGE_SIZE, offset }), [status, offset])

  const att = attendance.data?.percentage
  return (
    <>
      <PageHeader
        title="My Cases"
        subtitle={`Welcome, ${me!.user.name}. Your clinical log and competency progress.`}
        actions={
          <Link to="/cases/new" className="inline-flex items-center rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700">
            + New case
          </Link>
        }
      />

      <div className="mb-6 grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          {quota.loading && !quota.data && <Card><Spinner /></Card>}
          {quota.error && <ErrorBanner message={quota.error} onRetry={quota.reload} />}
          {quota.data && <QuotaProgressCard progress={quota.data} />}
        </div>
        <Card>
          <CardHeader title="Attendance" subtitle="Last 12 weeks" />
          <div className="p-5">
            {att === undefined ? (
              attendance.error ? <ErrorBanner message={attendance.error} /> : <Spinner />
            ) : (
              <>
                <p className={cx('text-4xl font-semibold tabular-nums', att < 75 ? 'text-rose-600' : 'text-brand-700')}>{att}%</p>
                <p className="mt-1 text-sm text-slate-500">
                  {attendance.data!.present + attendance.data!.late} of {attendance.data!.total_sessions - attendance.data!.excused} sessions attended
                </p>
                {att < 75 && (
                  <p className="mt-3 rounded-lg bg-rose-50 px-3 py-2 text-xs text-rose-700 ring-1 ring-rose-200">
                    Below the 75% attendance requirement.
                  </p>
                )}
              </>
            )}
          </div>
        </Card>
      </div>

      <div className="mb-6 space-y-6">
        <FocusAreasCard studentId={studentId} />
        <LearningPlanCard studentId={studentId} />
      </div>

      <Card>
        <div className="flex flex-wrap gap-1 border-b border-slate-100 p-3">
          {(['', ...entries(CASE_STATUS)] as (CaseStatus | '')[]).map((s) => (
            <button
              key={s || 'all'}
              onClick={() => {
                setStatus(s)
                setOffset(0)
              }}
              className={cx(
                'rounded-lg px-3 py-1.5 text-sm font-medium transition',
                status === s ? 'bg-brand-600 text-white' : 'text-slate-600 hover:bg-slate-100',
              )}
            >
              {s ? CASE_STATUS[s].label : 'All'}
            </button>
          ))}
        </div>

        {cases.error && <div className="p-4"><ErrorBanner message={cases.error} onRetry={cases.reload} /></div>}
        {cases.loading && !cases.data && <Spinner />}
        {cases.data && cases.data.items.length === 0 && (
          <EmptyState title="No cases here yet">Record your first case with the New case button.</EmptyState>
        )}
        {cases.data && cases.data.items.length > 0 && (
          <>
            <ul className={cx('divide-y divide-slate-100', cases.loading && 'opacity-60')}>
              {cases.data.items.map((c) => (
                <li key={c.id}>
                  <button onClick={() => navigate(`/cases/${c.id}`)} className="flex w-full flex-col gap-1 px-5 py-3 text-left hover:bg-brand-50/40 sm:flex-row sm:items-center sm:gap-4">
                    <span className="w-24 shrink-0 text-xs text-slate-500">{formatDate(c.visit_date)}</span>
                    <span className="w-28 shrink-0 text-sm font-medium text-brand-700">{DEPARTMENT_SHORT[c.department]}</span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-medium text-slate-900">{c.patient_name}</span>
                      <span className="block truncate text-xs text-slate-500">{c.diagnosis ?? c.chief_complaint}</span>
                    </span>
                    <span className="flex items-center gap-2">
                      {c.findings.length > 0 && <span className="text-xs text-slate-500">{c.findings.length} teeth</span>}
                      <StatusBadge status={c.status} />
                    </span>
                  </button>
                </li>
              ))}
            </ul>
            <Pagination total={cases.data.total} limit={PAGE_SIZE} offset={offset} onChange={setOffset} />
          </>
        )}
      </Card>
    </>
  )
}
