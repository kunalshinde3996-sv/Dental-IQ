import { useMemo, useState } from 'react'
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { intelligenceApi } from '../../api'
import type { RiskLevel, StudentAlert, StudentYear } from '../../api/types'
import { ChartTooltip } from '../../components/charts'
import { Drawer } from '../../components/Drawer'
import { RiskBadge } from '../../components/RiskPanel'
import { Badge, Card, EmptyState, ErrorBanner, Input, PageHeader, Select, Spinner, cx } from '../../components/ui'
import { AXIS, GRID, PAIR } from '../../lib/chartColors'
import { DEPARTMENT_SHORT, YEARS, entries } from '../../lib/labels'
import { useApi } from '../../lib/useApi'

type SortKey = 'risk' | 'name' | 'year' | 'attendance' | 'marks' | 'quota' | 'rejection'

const LEVEL_ORDER: Record<RiskLevel, number> = { High: 0, Medium: 1, Low: 2 }
const YEAR_ORDER: Record<StudentYear, number> = { bds1: 1, bds2: 2, bds3: 3, bds4: 4, intern: 5 }

function sortValue(a: StudentAlert, key: SortKey): number | string {
  const s = a.signals
  switch (key) {
    case 'risk': return LEVEL_ORDER[a.risk_level] * 10 - (a.score ?? 0)
    case 'name': return a.name
    case 'year': return YEAR_ORDER[a.year]
    case 'attendance': return s.attendance_pct ?? 999
    case 'marks': return s.marks_avg ?? 999
    case 'quota': return s.pace_ratio ?? 999
    case 'rejection': return -(s.rejection_rate ?? -1)
  }
}

const fmt = (v: number | null | undefined, suffix = '%') => (v === null || v === undefined ? '—' : `${Math.round(v)}${suffix}`)

export function AtRiskStudentsPage() {
  const { data, error, loading, reload } = useApi(() => intelligenceApi.alerts(), [])
  const [level, setLevel] = useState<RiskLevel | ''>('')
  const [year, setYear] = useState<StudentYear | ''>('')
  const [q, setQ] = useState('')
  const [sort, setSort] = useState<{ key: SortKey; asc: boolean }>({ key: 'risk', asc: true })
  const [selected, setSelected] = useState<StudentAlert | null>(null)

  const rows = useMemo(() => {
    const term = q.trim().toLowerCase()
    const list = (data ?? []).filter(
      (a) => (!level || a.risk_level === level) && (!year || a.year === year) &&
        (!term || a.name.toLowerCase().includes(term) || a.roll_no.toLowerCase().includes(term)),
    )
    return [...list].sort((a, b) => {
      const va = sortValue(a, sort.key), vb = sortValue(b, sort.key)
      const cmp = typeof va === 'string' ? va.localeCompare(vb as string) : (va as number) - (vb as number)
      return sort.asc ? cmp : -cmp
    })
  }, [data, level, year, q, sort])

  const counts = { High: 0, Medium: 0, Low: 0 }
  data?.forEach((a) => counts[a.risk_level]++)

  const Th = ({ k, children, className }: { k: SortKey; children: string; className?: string }) => (
    <th className={cx('px-4 py-3 font-medium', className)} aria-sort={sort.key === k ? (sort.asc ? 'ascending' : 'descending') : 'none'}>
      <button className="inline-flex items-center gap-1 hover:text-slate-800" onClick={() => setSort((s) => ({ key: k, asc: s.key === k ? !s.asc : true }))}>
        {children}
        <span className="text-[10px]">{sort.key === k ? (sort.asc ? '▲' : '▼') : '↕'}</span>
      </button>
    </th>
  )

  return (
    <>
      <PageHeader
        title="At-Risk Students"
        subtitle="Explainable alerts: transparent rules give the reasons, a logistic-regression score ranks within level."
      />

      <div className="mb-4 grid grid-cols-3 gap-3 sm:max-w-md">
        {(['High', 'Medium', 'Low'] as RiskLevel[]).map((l) => (
          <button key={l} onClick={() => setLevel(level === l ? '' : l)}
            className={cx('rounded-xl bg-white p-3 text-left shadow-sm ring-1 transition', level === l ? 'ring-2 ring-brand-500' : 'ring-slate-200 hover:ring-slate-300')}>
            <RiskBadge level={l} />
            <p className="mt-1 text-2xl font-semibold tabular-nums">{data ? counts[l] : '—'}</p>
          </button>
        ))}
      </div>

      <Card>
        <div className="flex flex-col gap-3 border-b border-slate-100 p-4 sm:flex-row">
          <Input type="search" placeholder="Search name or roll no." value={q} onChange={(e) => setQ(e.target.value)} className="sm:max-w-xs" aria-label="Search students" />
          <Select value={year} onChange={(e) => setYear(e.target.value as StudentYear | '')} className="sm:w-40" aria-label="Year">
            <option value="">All years</option>
            {entries(YEARS).map((y) => <option key={y} value={y}>{YEARS[y]}</option>)}
          </Select>
          <Select value={level} onChange={(e) => setLevel(e.target.value as RiskLevel | '')} className="sm:w-40" aria-label="Risk level">
            <option value="">All levels</option>
            <option value="High">High</option>
            <option value="Medium">Medium</option>
            <option value="Low">Low</option>
          </Select>
        </div>
        {error && <div className="p-4"><ErrorBanner message={error} onRetry={reload} /></div>}
        {loading && !data && <Spinner label="Computing student signals…" />}
        {data && rows.length === 0 && <EmptyState title="No students match these filters" />}
        {rows.length > 0 && (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <Th k="risk">Risk</Th>
                  <Th k="name">Student</Th>
                  <Th k="year">Year</Th>
                  <Th k="attendance" className="text-right">Attend.</Th>
                  <Th k="marks" className="text-right">Marks</Th>
                  <Th k="quota" className="text-right">Quota pace</Th>
                  <Th k="rejection" className="hidden text-right lg:table-cell">Rejected</Th>
                  <th className="hidden px-4 py-3 font-medium xl:table-cell">Top reason</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {rows.map((a) => (
                  <tr key={a.student_id} className="cursor-pointer hover:bg-brand-50/40" onClick={() => setSelected(a)}>
                    <td className="px-4 py-3">
                      <RiskBadge level={a.risk_level} />
                      {a.score !== null && <span className="ml-2 text-xs tabular-nums text-slate-400">{a.score.toFixed(2)}</span>}
                    </td>
                    <td className="px-4 py-3">
                      <button className="text-left font-medium text-slate-900 hover:text-brand-700" onClick={(e) => { e.stopPropagation(); setSelected(a) }}>
                        {a.name}
                      </button>
                      <div className="text-xs text-slate-500">{a.roll_no}</div>
                    </td>
                    <td className="px-4 py-3 text-slate-600">{YEARS[a.year]}</td>
                    <td className={cx('px-4 py-3 text-right tabular-nums', (a.signals.attendance_pct ?? 100) < 75 && 'font-semibold text-rose-700')}>{fmt(a.signals.attendance_pct)}</td>
                    <td className={cx('px-4 py-3 text-right tabular-nums', (a.signals.marks_avg ?? 100) < 50 && 'font-semibold text-rose-700')}>{fmt(a.signals.marks_avg)}</td>
                    <td className={cx('px-4 py-3 text-right tabular-nums', (a.signals.pace_ratio ?? 1) < 0.6 && 'font-semibold text-rose-700')}>
                      {a.signals.pace_ratio === null ? '—' : `${Math.round(a.signals.pace_ratio * 100)}%`}
                    </td>
                    <td className="hidden px-4 py-3 text-right tabular-nums lg:table-cell">{a.signals.rejection_rate === null ? '—' : fmt(a.signals.rejection_rate * 100)}</td>
                    <td className="hidden max-w-xs truncate px-4 py-3 text-slate-600 xl:table-cell" title={a.reasons[0]?.text}>{a.reasons[0]?.text ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="border-t border-slate-100 px-4 py-2 text-xs text-slate-500">
              Quota pace = overall quota progress ÷ cohort median for the same year (100% = on par). Click a row for reasons and actions.
            </p>
          </div>
        )}
      </Card>

      <Drawer open={selected !== null} onClose={() => setSelected(null)}
        title={selected?.name} subtitle={selected && `${selected.roll_no} · ${YEARS[selected.year]}`}>
        {selected && <AlertDetail a={selected} />}
      </Drawer>
    </>
  )
}

function AlertDetail({ a }: { a: StudentAlert }) {
  const s = a.signals
  const weekly = a.weekly_attendance.map((w) => ({ week: w.weeks_ago === 0 ? 'This wk' : `-${w.weeks_ago}w`, pct: w.pct }))
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-2">
        <RiskBadge level={a.risk_level} />
        {a.score !== null && <Badge className="bg-slate-100 text-slate-700 ring-slate-200">Model score {a.score.toFixed(2)}</Badge>}
      </div>

      <section>
        <h3 className="mb-2 text-sm font-semibold text-slate-900">Reasons</h3>
        {a.reasons.length === 0 ? (
          <p className="text-sm text-slate-500">No rule thresholds crossed.</p>
        ) : (
          <ul className="space-y-2">
            {a.reasons.map((r) => (
              <li key={r.code} className={cx('rounded-lg px-3 py-2 text-sm ring-1', r.severity === 'critical' ? 'bg-rose-50 text-rose-800 ring-rose-200' : 'bg-amber-50 text-amber-900 ring-amber-200')}>
                <span className="mr-1 font-semibold">{r.severity === 'critical' ? 'Critical:' : 'Warning:'}</span>{r.text}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <h3 className="mb-2 text-sm font-semibold text-slate-900">Suggested actions</h3>
        {a.suggested_actions.length === 0 ? <p className="text-sm text-slate-500">None needed.</p> : (
          <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">
            {a.suggested_actions.map((x) => <li key={x}>{x}</li>)}
          </ul>
        )}
      </section>

      <section>
        <h3 className="mb-1 text-sm font-semibold text-slate-900">Weekly attendance (last 12 weeks)</h3>
        <div className="h-36">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={weekly} margin={{ top: 8, right: 8, left: -16 }}>
              <CartesianGrid vertical={false} stroke={GRID} />
              <XAxis dataKey="week" {...AXIS} tick={{ ...AXIS.tick, fontSize: 10 }} interval={1} />
              <YAxis domain={[0, 100]} unit="%" {...AXIS} tick={{ ...AXIS.tick, fontSize: 10 }} />
              <ReferenceLine y={75} stroke="#e11d48" strokeDasharray="4 3" label={{ value: '75% min', fill: '#e11d48', fontSize: 10, position: 'insideBottomRight' }} />
              <Tooltip content={<ChartTooltip format={(v) => `${v}%`} />} />
              <Line isAnimationActive={false} dataKey="pct" name="Attendance" stroke={PAIR.a} strokeWidth={2} dot={{ r: 3 }} connectNulls />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section>
        <h3 className="mb-2 text-sm font-semibold text-slate-900">Signals</h3>
        <dl className="grid grid-cols-2 gap-3 text-sm">
          <Signal label="Attendance (12 wk)" value={fmt(s.attendance_pct)} hint={s.attendance_trend !== null ? `${s.attendance_trend > 0 ? '+' : ''}${s.attendance_trend} pts last 4 wk` : undefined} />
          <Signal label="Marks average" value={fmt(s.marks_avg)} hint={s.weakest_subject ? `Weakest: ${s.weakest_subject} ${fmt(s.weakest_subject_pct)}` : undefined} />
          <Signal label="Quota progress" value={fmt(s.quota_percent)} hint={s.cohort_median_percent !== null ? `Cohort median ${fmt(s.cohort_median_percent)}` : 'Pre-clinical'} />
          <Signal label="Rejected cases" value={`${s.rejected_cases}/${s.reviewed_cases}`} hint={s.rejection_rate !== null ? fmt(s.rejection_rate * 100) : 'Too few reviewed'} />
        </dl>
        {s.quota_gaps.length > 0 && (
          <p className="mt-3 text-xs text-slate-600">
            <span className="font-semibold">Largest quota gaps:</span>{' '}
            {s.quota_gaps.slice(0, 4).map((g) => `${DEPARTMENT_SHORT[g.department]} ${g.approved}/${g.required}`).join(' · ')}
          </p>
        )}
      </section>

      {a.model_factors.length > 0 && (
        <section>
          <h3 className="mb-2 text-sm font-semibold text-slate-900">What drives the model score</h3>
          <ul className="space-y-1 text-sm">
            {a.model_factors.map((f) => (
              <li key={f.feature} className="flex justify-between gap-3">
                <span className="text-slate-700">{f.label} <span className="text-xs text-slate-400">({f.z_score > 0 ? '+' : ''}{f.z_score} SD vs cohort)</span></span>
                <span className={cx('tabular-nums', f.direction === 'raises' ? 'text-rose-700' : 'text-emerald-700')}>{f.direction} {Math.abs(f.contribution).toFixed(2)}</span>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-xs text-slate-400">Contributions in log-odds from standardised signals. Model trained on synthetic data.</p>
        </section>
      )}
    </div>
  )
}

function Signal({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-lg bg-slate-50 p-3">
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd className="text-lg font-semibold tabular-nums text-slate-900">{value}</dd>
      {hint && <dd className="text-xs text-slate-500">{hint}</dd>}
    </div>
  )
}
