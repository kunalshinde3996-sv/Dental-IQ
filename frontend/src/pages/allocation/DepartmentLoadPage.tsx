import { useState } from 'react'
import { allocationApi } from '../../api'
import type { LoadStatus } from '../../api/types'
import { Badge, Card, CardHeader, ErrorBanner, PageHeader, Select, Spinner, cx } from '../../components/ui'
import { DEPARTMENTS } from '../../lib/labels'
import { useApi } from '../../lib/useApi'

const STATUS: Record<LoadStatus, { label: string; className: string; bar: string; icon: string }> = {
  overloaded: { label: 'Overloaded', className: 'bg-rose-50 text-rose-700 ring-rose-200', bar: 'bg-rose-500', icon: '▲' },
  short_supply: { label: 'Patient shortage', className: 'bg-amber-50 text-amber-800 ring-amber-200', bar: 'bg-amber-500', icon: '!' },
  balanced: { label: 'Balanced', className: 'bg-slate-100 text-slate-700 ring-slate-200', bar: 'bg-brand-500', icon: '•' },
  spare_capacity: { label: 'Spare capacity', className: 'bg-emerald-50 text-emerald-700 ring-emerald-200', bar: 'bg-emerald-500', icon: '✓' },
}

export function DepartmentLoadPage() {
  const [days, setDays] = useState(30)
  const { data, error, loading, reload } = useApi(() => allocationApi.resources(days), [days])
  const max = Math.max(...(data?.departments.map((d) => d.cases_per_faculty ?? 0) ?? [1]), 1)

  return (
    <>
      <PageHeader
        title="Department Load"
        subtitle="Clinical case load against faculty strength, review backlog and outstanding student quotas."
        actions={
          <Select value={days} onChange={(e) => setDays(Number(e.target.value))} aria-label="Period" className="w-40">
            <option value={30}>Last 30 days</option>
            <option value={60}>Last 60 days</option>
            <option value={90}>Last 90 days</option>
          </Select>
        }
      />
      {error && <ErrorBanner message={error} onRetry={reload} />}
      {loading && !data && <Spinner />}
      {data && (
        <div className={cx('grid grid-cols-1 gap-6 xl:grid-cols-5', loading && 'opacity-60')}>
          <Card className="xl:col-span-2">
            <CardHeader title="Cases per faculty member" subtitle={`College average ${data.mean_cases_per_faculty} in ${data.days} days`} />
            <ul className="space-y-3 p-5">
              {data.departments.map((d) => (
                <li key={d.department}>
                  <div className="flex items-baseline justify-between gap-2 text-sm">
                    <span className="font-medium text-slate-800">{DEPARTMENTS[d.department]}</span>
                    <span className="tabular-nums text-slate-600">{d.cases_per_faculty ?? '—'}</span>
                  </div>
                  <div className="relative mt-1 h-2 rounded-full bg-slate-100">
                    <div className={cx('h-full rounded-full', STATUS[d.status].bar)} style={{ width: `${((d.cases_per_faculty ?? 0) / max) * 100}%` }} />
                    <div className="absolute top-[-3px] h-[14px] w-px bg-slate-500" style={{ left: `${(data.mean_cases_per_faculty / max) * 100}%` }} title="College average" />
                  </div>
                </li>
              ))}
            </ul>
            <p className="px-5 pb-4 text-xs text-slate-500">The grey tick marks the college average. Bar colour shows each department's status.</p>
          </Card>

          <Card className="xl:col-span-3">
            <CardHeader title="Department detail" />
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-4 py-3 font-medium">Department</th>
                    <th className="px-4 py-3 text-right font-medium">Faculty</th>
                    <th className="px-4 py-3 text-right font-medium">Cases</th>
                    <th className="px-4 py-3 text-right font-medium">Pending</th>
                    <th className="px-4 py-3 text-right font-medium">Quota left</th>
                    <th className="px-4 py-3 text-right font-medium">Weeks</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {data.departments.map((d) => (
                    <tr key={d.department} className="align-top">
                      <td className="px-4 py-3">
                        <p className="font-medium text-slate-900">{DEPARTMENTS[d.department]}</p>
                        <Badge className={cx('mt-1', STATUS[d.status].className)}>
                          <span aria-hidden className="mr-1">{STATUS[d.status].icon}</span>{STATUS[d.status].label}
                        </Badge>
                        {d.reasons.map((r) => <p key={r} className="mt-1 max-w-sm text-xs text-slate-600">{r}</p>)}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums">{d.faculty}</td>
                      <td className="px-4 py-3 text-right tabular-nums">{d.cases}</td>
                      <td className="px-4 py-3 text-right tabular-nums">{d.pending_reviews}</td>
                      <td className="px-4 py-3 text-right tabular-nums">{d.quota_remaining}</td>
                      <td className="px-4 py-3 text-right tabular-nums">{d.weeks_to_clear_quota ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="border-t border-slate-100 px-4 py-2 text-xs text-slate-500">
              Weeks = outstanding approved-case quota across eligible students ÷ weekly case flow. Faculty availability is head-count (no timetable data yet).
            </p>
          </Card>
        </div>
      )}
    </>
  )
}
