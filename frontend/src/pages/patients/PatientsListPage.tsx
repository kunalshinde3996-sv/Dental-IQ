import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { patientsApi } from '../../api'
import type { Taluka } from '../../api/types'
import { Card, EmptyState, ErrorBanner, Input, PageHeader, Pagination, Select, Spinner } from '../../components/ui'
import { formatDate } from '../../lib/format'
import { SEXES, TALUKAS, entries } from '../../lib/labels'
import { useApi, useDebounced } from '../../lib/useApi'
import { HabitBadges } from './HabitBadges'

const PAGE_SIZE = 20

export function PatientsListPage() {
  const navigate = useNavigate()
  const [q, setQ] = useState('')
  const [taluka, setTaluka] = useState<Taluka | ''>('')
  const [offset, setOffset] = useState(0)
  const query = useDebounced(q)

  const { data, error, loading, reload } = useApi(
    () => patientsApi.list({ q: query, taluka, limit: PAGE_SIZE, offset }),
    [query, taluka, offset],
  )

  return (
    <>
      <PageHeader
        title="Patients"
        subtitle="Search by name, OPD number, ABHA ID or phone."
        actions={
          <Link to="/patients/new" className="inline-flex items-center rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700">
            + Register patient
          </Link>
        }
      />

      <Card>
        <div className="flex flex-col gap-3 border-b border-slate-100 p-4 sm:flex-row">
          <Input
            type="search"
            placeholder="Search patients…"
            value={q}
            onChange={(e) => {
              setQ(e.target.value)
              setOffset(0)
            }}
            className="sm:max-w-sm"
            aria-label="Search patients"
          />
          <Select
            value={taluka}
            onChange={(e) => {
              setTaluka(e.target.value as Taluka | '')
              setOffset(0)
            }}
            className="sm:w-48"
            aria-label="Filter by taluka"
          >
            <option value="">All talukas</option>
            {entries(TALUKAS).map((t) => (
              <option key={t} value={t}>
                {TALUKAS[t]}
              </option>
            ))}
          </Select>
        </div>

        {error && (
          <div className="p-4">
            <ErrorBanner message={error} onRetry={reload} />
          </div>
        )}
        {loading && !data && <Spinner />}
        {data && data.items.length === 0 && <EmptyState title="No patients found">Try a different search or register a new patient.</EmptyState>}

        {data && data.items.length > 0 && (
          <>
            {/* Table on larger screens */}
            <div className={`hidden overflow-x-auto md:block ${loading ? 'opacity-60' : ''}`}>
              <table className="min-w-full text-sm">
                <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-5 py-3 font-medium">Patient</th>
                    <th className="px-5 py-3 font-medium">Age / Sex</th>
                    <th className="px-5 py-3 font-medium">Taluka</th>
                    <th className="px-5 py-3 font-medium">Risk habits</th>
                    <th className="px-5 py-3 font-medium">Visits</th>
                    <th className="px-5 py-3 font-medium">Last visit</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {data.items.map((p) => (
                    <tr key={p.id} className="cursor-pointer hover:bg-brand-50/50" onClick={() => navigate(`/patients/${p.id}`)}>
                      <td className="px-5 py-3">
                        <Link to={`/patients/${p.id}`} className="font-medium text-slate-900 hover:text-brand-700" onClick={(e) => e.stopPropagation()}>
                          {p.name}
                        </Link>
                        <div className="text-xs text-slate-500">
                          {p.opd_number}
                          {p.abha_id && <span className="ml-2 rounded bg-sky-50 px-1.5 py-0.5 text-sky-700">ABHA</span>}
                        </div>
                      </td>
                      <td className="px-5 py-3 text-slate-600">
                        {p.age} · {SEXES[p.sex]}
                      </td>
                      <td className="px-5 py-3 text-slate-600">{TALUKAS[p.taluka]}</td>
                      <td className="px-5 py-3">
                        <HabitBadges patient={p} />
                      </td>
                      <td className="px-5 py-3 tabular-nums text-slate-600">{p.visit_count}</td>
                      <td className="px-5 py-3 text-slate-600">{formatDate(p.last_visit)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Cards on mobile */}
            <ul className="divide-y divide-slate-100 md:hidden">
              {data.items.map((p) => (
                <li key={p.id}>
                  <Link to={`/patients/${p.id}`} className="block px-4 py-3 hover:bg-brand-50/50">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium text-slate-900">{p.name}</span>
                      <span className="text-xs text-slate-500">{formatDate(p.last_visit)}</span>
                    </div>
                    <div className="mt-0.5 text-xs text-slate-500">
                      {p.opd_number} · {p.age} {SEXES[p.sex]} · {TALUKAS[p.taluka]}
                    </div>
                    <div className="mt-1.5">
                      <HabitBadges patient={p} />
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
            <Pagination total={data.total} limit={PAGE_SIZE} offset={offset} onChange={setOffset} />
          </>
        )}
      </Card>
    </>
  )
}
