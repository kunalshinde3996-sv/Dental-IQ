import { useState } from 'react'
import { Link } from 'react-router-dom'
import { auditApi } from '../../api'
import { Badge, Card, EmptyState, ErrorBanner, Field, Input, PageHeader, Pagination, Select, Spinner, cx } from '../../components/ui'
import { ROLES } from '../../lib/labels'
import { useApi, useDebounced } from '../../lib/useApi'

const PAGE_SIZE = 25

const ACTION_STYLE: Record<string, string> = {
  view: 'bg-slate-100 text-slate-700 ring-slate-200',
  create: 'bg-sky-50 text-sky-700 ring-sky-200',
  update: 'bg-indigo-50 text-indigo-700 ring-indigo-200',
  approve: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  reject: 'bg-rose-50 text-rose-700 ring-rose-200',
  delete: 'bg-rose-50 text-rose-700 ring-rose-200',
  login_failed: 'bg-amber-50 text-amber-800 ring-amber-200',
}

function entityLink(type: string, id: number | null): string | null {
  if (id === null) return null
  if (type === 'patient') return `/patients/${id}`
  if (type === 'case') return `/cases/${id}`
  return null
}

const dt = new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', second: '2-digit' })

/** Admin: browse who viewed / created / changed / approved records. */
export function AuditLogPage() {
  const [action, setAction] = useState('')
  const [entityType, setEntityType] = useState('')
  const [entityId, setEntityId] = useState('')
  const [q, setQ] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [offset, setOffset] = useState(0)
  const query = useDebounced(q)
  const id = useDebounced(entityId)

  const facets = useApi(() => auditApi.facets(), [])
  const { data, error, loading, reload } = useApi(
    () => auditApi.list({ action, entity_type: entityType, entity_id: id ? Number(id) : '', q: query, date_from: dateFrom, date_to: dateTo, limit: PAGE_SIZE, offset }),
    [action, entityType, id, query, dateFrom, dateTo, offset],
  )
  const reset = (fn: () => void) => { fn(); setOffset(0) }

  return (
    <>
      <PageHeader title="Audit Log" subtitle="Append-only record of who viewed, created, edited, approved or exported records." />
      <Card className="mb-6">
        <div className="grid grid-cols-1 gap-3 p-4 sm:grid-cols-3 lg:grid-cols-6">
          <Field label="Search" className="sm:col-span-2 lg:col-span-2">
            <Input type="search" value={q} placeholder="User name or summary" onChange={(e) => reset(() => setQ(e.target.value))} />
          </Field>
          <Field label="Action">
            <Select value={action} onChange={(e) => reset(() => setAction(e.target.value))}>
              <option value="">All actions</option>
              {facets.data?.actions.map((a) => <option key={a} value={a}>{a.replace('_', ' ')}</option>)}
            </Select>
          </Field>
          <Field label="Record type">
            <Select value={entityType} onChange={(e) => reset(() => setEntityType(e.target.value))}>
              <option value="">All types</option>
              {facets.data?.entity_types.map((t) => <option key={t} value={t}>{t}</option>)}
            </Select>
          </Field>
          <Field label="Record ID">
            <Input inputMode="numeric" value={entityId} onChange={(e) => reset(() => setEntityId(e.target.value.replace(/\D/g, '')))} placeholder="e.g. 62" />
          </Field>
          <div className="grid grid-cols-2 gap-2">
            <Field label="From"><Input type="date" value={dateFrom} onChange={(e) => reset(() => setDateFrom(e.target.value))} /></Field>
            <Field label="To"><Input type="date" value={dateTo} onChange={(e) => reset(() => setDateTo(e.target.value))} /></Field>
          </div>
        </div>
      </Card>

      <Card>
        {error && <div className="p-4"><ErrorBanner message={error} onRetry={reload} /></div>}
        {loading && !data && <Spinner />}
        {data && data.items.length === 0 && <EmptyState title="No audit events match these filters" />}
        {data && data.items.length > 0 && (
          <>
            <div className={cx('overflow-x-auto', loading && 'opacity-60')}>
              <table className="min-w-full text-sm">
                <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-800/60">
                  <tr>
                    <th scope="col" className="px-4 py-3 font-medium">When</th>
                    <th scope="col" className="px-4 py-3 font-medium">Who</th>
                    <th scope="col" className="px-4 py-3 font-medium">Action</th>
                    <th scope="col" className="px-4 py-3 font-medium">Record</th>
                    <th scope="col" className="hidden px-4 py-3 font-medium lg:table-cell">Details</th>
                    <th scope="col" className="hidden px-4 py-3 font-medium xl:table-cell">IP</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                  {data.items.map((e) => {
                    const link = entityLink(e.entity_type, e.entity_id)
                    return (
                      <tr key={e.id} className="align-top">
                        <td className="whitespace-nowrap px-4 py-2.5 tabular-nums text-slate-600 dark:text-slate-300">{dt.format(new Date(e.created_at))}</td>
                        <td className="px-4 py-2.5">
                          <span className="font-medium">{e.user_name ?? 'Anonymous'}</span>
                          {e.user_role && <span className="block text-xs text-slate-500">{ROLES[e.user_role]}</span>}
                        </td>
                        <td className="px-4 py-2.5"><Badge className={ACTION_STYLE[e.action] ?? 'bg-slate-100 text-slate-700 ring-slate-200'}>{e.action.replace('_', ' ')}</Badge></td>
                        <td className="whitespace-nowrap px-4 py-2.5">
                          {link ? <Link to={link} className="font-medium text-brand-700 hover:underline dark:text-brand-300">{e.entity_type} #{e.entity_id}</Link>
                            : <span>{e.entity_type}{e.entity_id !== null ? ` #${e.entity_id}` : ''}</span>}
                          <span className="block text-xs text-slate-500 lg:hidden">{e.summary}</span>
                        </td>
                        <td className="hidden px-4 py-2.5 text-slate-700 dark:text-slate-300 lg:table-cell">{e.summary}</td>
                        <td className="hidden px-4 py-2.5 font-mono text-xs text-slate-500 xl:table-cell">{e.ip_address ?? '—'}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
            <Pagination total={data.total} limit={PAGE_SIZE} offset={offset} onChange={setOffset} />
          </>
        )}
      </Card>
    </>
  )
}
