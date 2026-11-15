import { useState } from 'react'
import { Link } from 'react-router-dom'
import { facultyApi } from '../../api'
import type { CaseRead } from '../../api/types'
import { useAuth } from '../../auth/AuthContext'
import { FindingsTable } from '../../components/ToothChart'
import { Card, EmptyState, ErrorBanner, PageHeader, Spinner, StatusBadge, cx } from '../../components/ui'
import { formatDate } from '../../lib/format'
import { DEPARTMENTS } from '../../lib/labels'
import { useApi } from '../../lib/useApi'
import { ReviewPanel } from '../cases/ReviewPanel'

function PendingCaseCard({ c, onReviewed }: { c: CaseRead; onReviewed: (updated: CaseRead) => void }) {
  const [open, setOpen] = useState(false)
  return (
    <Card>
      <button className="flex w-full flex-wrap items-center justify-between gap-3 px-5 py-4 text-left" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        <div className="min-w-0">
          <p className="text-sm font-semibold text-slate-900">
            {c.student_name} <span className="font-normal text-slate-500">· {c.student_roll_no}</span>
          </p>
          <p className="truncate text-sm text-slate-600">
            {c.patient_name} · {c.diagnosis ?? c.chief_complaint}
          </p>
        </div>
        <div className="flex items-center gap-3 text-xs text-slate-500">
          <span>{formatDate(c.visit_date)}</span>
          <span className="text-slate-500">{open ? '▲' : '▼'}</span>
        </div>
      </button>
      {open && (
        <div className="grid grid-cols-1 gap-6 border-t border-slate-100 p-5 lg:grid-cols-5">
          <div className="space-y-3 text-sm lg:col-span-3">
            <p><span className="text-slate-500">Patient:</span>{' '}
              <Link to={`/patients/${c.patient_id}`} className="font-medium text-brand-700 hover:underline">{c.patient_name}</Link> · {c.patient_opd_number}
            </p>
            <p><span className="text-slate-500">Chief complaint:</span> {c.chief_complaint}</p>
            <p><span className="text-slate-500">Diagnosis:</span> {c.diagnosis ?? '—'}</p>
            <p><span className="text-slate-500">Procedure:</span> {c.procedure ?? '—'}</p>
            <FindingsTable findings={c.findings} />
            <Link to={`/cases/${c.id}`} className="inline-block text-sm font-medium text-brand-700 hover:underline">Open full case with tooth chart →</Link>
          </div>
          <div className="lg:col-span-2">
            <ReviewPanel caseItem={c} onDone={onReviewed} />
          </div>
        </div>
      )}
    </Card>
  )
}

export function ApprovalsPage() {
  const { me } = useAuth()
  const [tab, setTab] = useState<'pending' | 'reviewed'>('pending')
  const pending = useApi(() => facultyApi.pending(), [])
  const reviewed = useApi(() => facultyApi.reviewed(), [tab])

  function onReviewed(updated: CaseRead) {
    pending.setData((prev) => prev && { ...prev, items: prev.items.filter((c) => c.id !== updated.id), total: prev.total - 1 })
  }

  return (
    <>
      <PageHeader
        title="Pending Approvals"
        subtitle={me?.faculty ? `${DEPARTMENTS[me.faculty.department]} · cases you supervise, oldest first` : undefined}
      />
      <div className="mb-4 flex gap-1">
        {(['pending', 'reviewed'] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={cx('rounded-lg px-3 py-1.5 text-sm font-medium', tab === t ? 'bg-brand-600 text-white' : 'text-slate-600 hover:bg-slate-100')}>
            {t === 'pending' ? `Pending${pending.data ? ` (${pending.data.total})` : ''}` : 'Recently reviewed'}
          </button>
        ))}
      </div>

      {tab === 'pending' && (
        <>
          {pending.error && <ErrorBanner message={pending.error} onRetry={pending.reload} />}
          {pending.loading && !pending.data && <Spinner />}
          {pending.data?.items.length === 0 && <Card><EmptyState title="All caught up">No cases are waiting for your review.</EmptyState></Card>}
          <div className="space-y-3">
            {pending.data?.items.map((c) => <PendingCaseCard key={c.id} c={c} onReviewed={onReviewed} />)}
          </div>
        </>
      )}

      {tab === 'reviewed' && (
        <Card>
          {reviewed.error && <div className="p-4"><ErrorBanner message={reviewed.error} /></div>}
          {reviewed.loading && !reviewed.data && <Spinner />}
          {reviewed.data?.items.length === 0 && <EmptyState title="Nothing reviewed yet" />}
          <ul className="divide-y divide-slate-100">
            {reviewed.data?.items.map((c) => (
              <li key={c.id}>
                <Link to={`/cases/${c.id}`} className="flex flex-wrap items-center justify-between gap-2 px-5 py-3 hover:bg-brand-50/40">
                  <span className="min-w-0">
                    <span className="block text-sm font-medium text-slate-900">{c.student_name} · {c.patient_name}</span>
                    <span className="block truncate text-xs text-slate-500">{c.faculty_remarks ?? c.diagnosis}</span>
                  </span>
                  <span className="flex items-center gap-2 text-xs text-slate-500">
                    {formatDate(c.reviewed_at)} <StatusBadge status={c.status} />
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </>
  )
}
