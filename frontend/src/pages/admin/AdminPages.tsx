import { useState } from 'react'
import { Link } from 'react-router-dom'
import { adminApi, facultyApi, studentsApi } from '../../api'
import type { StudentYear } from '../../api/types'
import { Card, CardHeader, EmptyState, ErrorBanner, Input, PageHeader, Select, Spinner } from '../../components/ui'
import { CASE_STATUS, DEPARTMENTS, YEARS, entries } from '../../lib/labels'
import { useApi, useDebounced } from '../../lib/useApi'

export function AdminOverviewPage() {
  const { data, error, loading, reload } = useApi(() => adminApi.stats(), [])
  if (loading && !data) return <Spinner />
  if (error) return <ErrorBanner message={error} onRetry={reload} />
  if (!data) return null

  const tiles = [
    { label: 'Students', value: data.students, to: '/admin/students' },
    { label: 'Faculty', value: data.faculty, to: '/admin/faculty' },
    { label: 'Patients', value: data.patients, to: '/patients' },
    { label: 'Clinical cases', value: data.cases },
  ]
  return (
    <>
      <PageHeader title="Overview" subtitle="Phase 1 · core records. Analytics dashboards arrive in Phase 2." />
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {tiles.map((t) => {
          const body = (
            <Card className="p-5 transition hover:ring-brand-300">
              <p className="text-sm text-slate-500">{t.label}</p>
              <p className="mt-1 text-3xl font-semibold tabular-nums text-slate-900">{t.value.toLocaleString('en-IN')}</p>
            </Card>
          )
          return t.to ? <Link key={t.label} to={t.to}>{body}</Link> : <div key={t.label}>{body}</div>
        })}
      </div>
      <Card className="mt-6">
        <CardHeader title="Cases by status" />
        <dl className="grid grid-cols-2 gap-4 p-5 sm:grid-cols-4">
          {entries(CASE_STATUS).map((s) => (
            <div key={s}>
              <dt className="text-sm text-slate-500">{CASE_STATUS[s].label}</dt>
              <dd className="text-xl font-semibold tabular-nums">{data.cases_by_status[s] ?? 0}</dd>
            </div>
          ))}
        </dl>
      </Card>
    </>
  )
}

export function AdminStudentsPage() {
  const [year, setYear] = useState<StudentYear | ''>('')
  const [q, setQ] = useState('')
  const query = useDebounced(q)
  const { data, error, loading, reload } = useApi(() => studentsApi.list({ year, q: query }), [year, query])

  return (
    <>
      <PageHeader title="Students" subtitle={data ? `${data.length} students` : undefined} />
      <Card>
        <div className="flex flex-col gap-3 border-b border-slate-100 p-4 sm:flex-row">
          <Input type="search" placeholder="Search name, roll no. or email" value={q} onChange={(e) => setQ(e.target.value)} className="sm:max-w-sm" aria-label="Search students" />
          <Select value={year} onChange={(e) => setYear(e.target.value as StudentYear | '')} className="sm:w-40" aria-label="Filter by year">
            <option value="">All years</option>
            {entries(YEARS).map((y) => <option key={y} value={y}>{YEARS[y]}</option>)}
          </Select>
        </div>
        {error && <div className="p-4"><ErrorBanner message={error} onRetry={reload} /></div>}
        {loading && !data && <Spinner />}
        {data?.length === 0 && <EmptyState title="No students match" />}
        {data && data.length > 0 && (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-5 py-3 font-medium">Roll no.</th>
                  <th className="px-5 py-3 font-medium">Name</th>
                  <th className="px-5 py-3 font-medium">Year</th>
                  <th className="px-5 py-3 font-medium">Batch</th>
                  <th className="hidden px-5 py-3 font-medium md:table-cell">Email</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.map((s) => (
                  <tr key={s.id}>
                    <td className="px-5 py-3 font-mono text-xs">{s.roll_no}</td>
                    <td className="px-5 py-3 font-medium text-slate-900">{s.name}</td>
                    <td className="px-5 py-3">{YEARS[s.year]}</td>
                    <td className="px-5 py-3 text-slate-600">{s.batch}</td>
                    <td className="hidden px-5 py-3 text-slate-600 md:table-cell">{s.email}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  )
}

export function AdminFacultyPage() {
  const { data, error, loading, reload } = useApi(() => facultyApi.list(), [])
  return (
    <>
      <PageHeader title="Faculty" subtitle={data ? `${data.length} faculty members` : undefined} />
      <Card>
        {error && <div className="p-4"><ErrorBanner message={error} onRetry={reload} /></div>}
        {loading && !data && <Spinner />}
        {data && (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-5 py-3 font-medium">Name</th>
                  <th className="px-5 py-3 font-medium">Department</th>
                  <th className="px-5 py-3 font-medium">Designation</th>
                  <th className="hidden px-5 py-3 font-medium md:table-cell">Email</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.map((f) => (
                  <tr key={f.id}>
                    <td className="px-5 py-3 font-medium text-slate-900">{f.name}</td>
                    <td className="px-5 py-3">{DEPARTMENTS[f.department]}</td>
                    <td className="px-5 py-3 text-slate-600">{f.designation}</td>
                    <td className="hidden px-5 py-3 text-slate-600 md:table-cell">{f.email}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  )
}
