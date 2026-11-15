import { useState } from 'react'
import { facultyApi, studentsApi } from '../../api'
import type { StudentYear } from '../../api/types'
import { Card, EmptyState, ErrorBanner, Input, PageHeader, Select, Spinner } from '../../components/ui'
import { DEPARTMENTS, YEARS, entries } from '../../lib/labels'
import { useApi, useDebounced } from '../../lib/useApi'

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
