import { useMemo, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { analyticsApi } from '../../api'
import type { Department, PopulationQuery, PopulationReport, Taluka } from '../../api/types'
import { ChartTooltip, InsightCard, Legend, StatTile } from '../../components/charts'
import { Button, Card, CardHeader, ErrorBanner, Field, Input, PageHeader, Select, Spinner, cx } from '../../components/ui'
import { heat, useChartTheme } from '../../lib/chartColors'
import { DEPARTMENTS, DEPARTMENT_SHORT, TALUKAS, entries } from '../../lib/labels'
import { useApi } from '../../lib/useApi'

const CONDITIONS = ['caries', 'periodontal', 'pmd', 'oral_lesion', 'edentulism'] as const
const CONDITION_SHORT: Record<string, string> = {
  caries: 'Caries',
  periodontal: 'Periodontal',
  pmd: 'PMD',
  oral_lesion: 'Oral lesion',
  edentulism: 'Edentulism',
  osmf: 'OSMF',
  leukoplakia: 'Leukoplakia',
}
const OUTCOMES = ['osmf', 'leukoplakia', 'pmd', 'oral_lesion'] as const

function monthLabel(m: string) {
  const [y, mo] = m.split('-').map(Number)
  return new Date(y, mo - 1, 1).toLocaleDateString('en-IN', { month: 'short', year: '2-digit' })
}

export function PopulationInsightsPage() {
  const [filters, setFilters] = useState<PopulationQuery>({})
  const { data, error, loading, reload } = useApi(() => analyticsApi.population(filters), [JSON.stringify(filters)])
  const set = (patch: Partial<PopulationQuery>) => setFilters((f) => ({ ...f, ...patch }))
  const active = Object.values(filters).some(Boolean)

  return (
    <>
      <PageHeader
        title="Population Insights"
        subtitle="Oral-health patterns across Goa from submitted and approved clinical cases. Synthetic demo data."
      />

      <Card className="mb-6">
        <div className="grid grid-cols-1 gap-3 p-4 sm:grid-cols-2 lg:grid-cols-5">
          <Field label="From">
            <Input type="date" value={filters.date_from ?? ''} onChange={(e) => set({ date_from: e.target.value || undefined })} />
          </Field>
          <Field label="To">
            <Input type="date" value={filters.date_to ?? ''} onChange={(e) => set({ date_to: e.target.value || undefined })} />
          </Field>
          <Field label="Taluka">
            <Select value={filters.taluka ?? ''} onChange={(e) => set({ taluka: e.target.value as Taluka | '' })}>
              <option value="">All talukas</option>
              {entries(TALUKAS).map((t) => <option key={t} value={t}>{TALUKAS[t]}</option>)}
            </Select>
          </Field>
          <Field label="Department">
            <Select value={filters.department ?? ''} onChange={(e) => set({ department: e.target.value as Department | '' })}>
              <option value="">All departments</option>
              {entries(DEPARTMENTS).map((d) => <option key={d} value={d}>{DEPARTMENTS[d]}</option>)}
            </Select>
          </Field>
          <div className="flex items-end">
            <Button variant="secondary" className="w-full" disabled={!active} onClick={() => setFilters({})}>
              Reset filters
            </Button>
          </div>
        </div>
      </Card>

      {error && <ErrorBanner message={error} onRetry={reload} />}
      {loading && !data && <Spinner label="Crunching population data…" />}
      {data && (
        <div className={cx('space-y-6 transition-opacity', loading && 'opacity-60')}>
          <Report data={data} />
        </div>
      )}
    </>
  )
}

function Report({ data }: { data: PopulationReport }) {
  const s = data.summary
  if (s.patients === 0) {
    return <Card className="p-10 text-center text-sm text-slate-500">No cases match these filters.</Card>
  }
  return (
    <>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
        <StatTile label="Patients" value={s.patients.toLocaleString('en-IN')} />
        <StatTile label="Cases" value={s.cases.toLocaleString('en-IN')} />
        <StatTile label="PMD patients" value={s.pmd_patients} hint="OSMF / leukoplakia / suspicious" />
        <StatTile label="Adult tobacco use" value={`${s.adult_current_tobacco_pct}%`} hint="current users" />
        <StatTile label="ABHA linked" value={`${s.abha_linked_pct}%`} />
      </div>

      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">Key insights</h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {data.insights.map((i) => <InsightCard key={i.id} insight={i} />)}
        </div>
      </section>

      <TalukaSection data={data} />
      <HabitSection data={data} />
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <CariesSection data={data} />
        <TrendSection data={data} />
      </div>
      <TopTermsSection data={data} />
    </>
  )
}

function TalukaSection({ data }: { data: PopulationReport }) {
  const { AXIS, GRID, PAIR } = useChartTheme()
  const [metric, setMetric] = useState<(typeof CONDITIONS)[number]>('pmd')
  const rows = data.taluka_burden.filter((r) => r.patients > 0)
  const chartData = useMemo(
    () =>
      [...rows]
        .sort((a, b) => b.prevalence_pct[metric] - a.prevalence_pct[metric])
        .map((r) => ({ taluka: TALUKAS[r.taluka], value: r.prevalence_pct[metric], patients: r.patients })),
    [rows, metric],
  )
  const maxByCondition = Object.fromEntries(CONDITIONS.map((c) => [c, Math.max(...rows.map((r) => r.prevalence_pct[c]), 0)]))

  return (
    <Card>
      <CardHeader
        title="Disease burden by taluka"
        subtitle="Share of patients from each taluka with the condition"
        action={
          <Select value={metric} onChange={(e) => setMetric(e.target.value as typeof metric)} className="w-44" aria-label="Condition">
            {CONDITIONS.map((c) => <option key={c} value={c}>{CONDITION_SHORT[c]}</option>)}
          </Select>
        }
      />
      <div className="grid grid-cols-1 gap-6 p-5 lg:grid-cols-2">
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} layout="vertical" margin={{ left: 8, right: 24 }}>
              <CartesianGrid horizontal={false} stroke={GRID} />
              <XAxis type="number" unit="%" {...AXIS} />
              <YAxis type="category" dataKey="taluka" width={90} {...AXIS} />
              <Tooltip
                cursor={{ fill: '#f1f5f9' }}
                content={<ChartTooltip format={(v, e) => `${v}% (n=${(e as { payload?: { patients: number } }).payload?.patients ?? ''})`} />}
              />
              <Bar isAnimationActive={false} dataKey="value" name={CONDITION_SHORT[metric]} fill={PAIR.a} radius={[0, 4, 4, 0]} barSize={14} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-xs">
            <thead>
              <tr className="text-left text-slate-500">
                <th className="py-1.5 pr-2 font-medium">Taluka</th>
                <th className="py-1.5 pr-2 text-right font-medium">n</th>
                {CONDITIONS.map((c) => <th key={c} className="px-1 py-1.5 text-center font-medium">{CONDITION_SHORT[c]}</th>)}
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.taluka}>
                  <td className="py-0.5 pr-2 font-medium text-slate-800">{TALUKAS[r.taluka]}</td>
                  <td className="py-0.5 pr-2 text-right tabular-nums text-slate-500">{r.patients}</td>
                  {CONDITIONS.map((c) => (
                    <td key={c} className="p-0.5">
                      <div
                        className="rounded px-1.5 py-1 text-center tabular-nums"
                        style={heat(r.prevalence_pct[c], maxByCondition[c])}
                        title={`${TALUKAS[r.taluka]} · ${CONDITION_SHORT[c]}: ${r.counts[c]} of ${r.patients} patients`}
                      >
                        {r.prevalence_pct[c]}%
                      </div>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-2 text-xs text-slate-500">Shading is per column (darker = higher within that condition). Small talukas give unstable percentages; check n.</p>
        </div>
      </div>
    </Card>
  )
}

function HabitSection({ data }: { data: PopulationReport }) {
  const { AXIS, GRID, PAIR } = useChartTheme()
  const [outcome, setOutcome] = useState<(typeof OUTCOMES)[number]>('osmf')
  const rows = data.habit_associations.filter((r) => r.outcome === outcome)
  const chartData = rows.map((r) => ({ habit: r.habit_label, exposed: r.exposed_pct, unexposed: r.unexposed_pct }))

  return (
    <Card>
      <CardHeader
        title="Risk habits vs oral lesions"
        subtitle="Adults who ever used each habit vs never-users. Prevalence ratio (PR) with 95% CI."
        action={
          <Select value={outcome} onChange={(e) => setOutcome(e.target.value as typeof outcome)} className="w-44" aria-label="Outcome">
            {OUTCOMES.map((o) => <option key={o} value={o}>{CONDITION_SHORT[o]}</option>)}
          </Select>
        }
      />
      <div className="grid grid-cols-1 gap-6 p-5 lg:grid-cols-2">
        <div>
          <Legend items={[{ label: 'Ever used', color: PAIR.b }, { label: 'Never used', color: PAIR.a }]} />
          <div className="mt-2 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} barGap={2} margin={{ right: 8 }}>
                <CartesianGrid vertical={false} stroke={GRID} />
                <XAxis dataKey="habit" {...AXIS} interval={0} tick={{ ...AXIS.tick, fontSize: 11 }} />
                <YAxis unit="%" {...AXIS} />
                <Tooltip cursor={{ fill: '#f1f5f9' }} content={<ChartTooltip format={(v) => `${v}%`} />} />
                <Bar isAnimationActive={false} dataKey="exposed" name="Ever used" fill={PAIR.b} radius={[4, 4, 0, 0]} barSize={22} />
                <Bar isAnimationActive={false} dataKey="unexposed" name="Never used" fill={PAIR.a} radius={[4, 4, 0, 0]} barSize={22} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-slate-500">
                <th className="py-2 pr-3 font-medium">Habit</th>
                <th className="py-2 pr-3 text-right font-medium">Users</th>
                <th className="py-2 pr-3 text-right font-medium">Non-users</th>
                <th className="py-2 text-right font-medium">PR (95% CI)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rows.map((r) => (
                <tr key={r.habit}>
                  <td className="py-2 pr-3 font-medium text-slate-800">{r.habit_label}</td>
                  <td className="py-2 pr-3 text-right tabular-nums">
                    {r.exposed_pct}% <span className="text-xs text-slate-500">({r.exposed_cases}/{r.exposed_n})</span>
                  </td>
                  <td className="py-2 pr-3 text-right tabular-nums">
                    {r.unexposed_pct}% <span className="text-xs text-slate-500">({r.unexposed_cases}/{r.unexposed_n})</span>
                  </td>
                  <td className="py-2 text-right tabular-nums">
                    {r.prevalence_ratio === null ? (
                      <span className="text-slate-500">n/a</span>
                    ) : (
                      <>
                        <span className={cx('font-semibold', r.ci_low! > 1 ? 'text-rose-700' : 'text-slate-700')}>{r.prevalence_ratio.toFixed(1)}×</span>{' '}
                        <span className="text-xs text-slate-500">({r.ci_low}–{r.ci_high})</span>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-2 text-xs text-slate-500">Red PR: the 95% CI lies entirely above 1. Associations, not causal estimates.</p>
        </div>
      </div>
    </Card>
  )
}

function CariesSection({ data }: { data: PopulationReport }) {
  const { AXIS, GRID, PAIR } = useChartTheme()
  const chartData = data.caries_by_age_sex.map((r) => ({
    age: r.age_group,
    male: r.male.pct,
    female: r.female.pct,
    n_m: r.male.patients,
    n_f: r.female.patients,
  }))
  return (
    <Card>
      <CardHeader title="Caries prevalence by age and sex" subtitle="Share of patients with dental caries" />
      <div className="p-5">
        <Legend items={[{ label: 'Male', color: PAIR.a }, { label: 'Female', color: PAIR.b }]} />
        <div className="mt-2 h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} barGap={2}>
              <CartesianGrid vertical={false} stroke={GRID} />
              <XAxis dataKey="age" {...AXIS} />
              <YAxis unit="%" domain={[0, 100]} {...AXIS} />
              <Tooltip
                cursor={{ fill: '#f1f5f9' }}
                content={
                  <ChartTooltip
                    labelFormat={(l) => `Age ${l}`}
                    format={(v, e) => {
                      const p = (e as { payload?: { n_m: number; n_f: number } }).payload
                      return `${v}% (n=${e.dataKey === 'male' ? p?.n_m : p?.n_f})`
                    }}
                  />
                }
              />
              <Bar isAnimationActive={false} dataKey="male" name="Male" fill={PAIR.a} radius={[4, 4, 0, 0]} barSize={16} />
              <Bar isAnimationActive={false} dataKey="female" name="Female" fill={PAIR.b} radius={[4, 4, 0, 0]} barSize={16} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </Card>
  )
}

function TrendSection({ data }: { data: PopulationReport }) {
  const { AXIS, GRID, DEPARTMENT_COLORS } = useChartTheme()
  const depts = entries(DEPARTMENTS)
  return (
    <Card>
      <CardHeader title="Monthly cases by department" subtitle="The current month is partial" />
      <div className="p-5">
        <Legend items={depts.map((d) => ({ label: DEPARTMENT_SHORT[d], color: DEPARTMENT_COLORS[d] }))} />
        <div className="mt-2 h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data.monthly_trend} margin={{ right: 8 }}>
              <CartesianGrid vertical={false} stroke={GRID} />
              <XAxis dataKey="month" tickFormatter={monthLabel} {...AXIS} />
              <YAxis allowDecimals={false} {...AXIS} />
              <Tooltip content={<ChartTooltip labelFormat={monthLabel} />} />
              {depts.map((d) => (
                <Line isAnimationActive={false} key={d} type="monotone" dataKey={d} name={DEPARTMENT_SHORT[d]} stroke={DEPARTMENT_COLORS[d]} strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
        <details className="mt-3 text-sm">
          <summary className="cursor-pointer text-xs font-medium text-brand-700">View as table</summary>
          <div className="mt-2 overflow-x-auto">
            <table className="min-w-full text-xs">
              <thead>
                <tr className="text-left text-slate-500">
                  <th className="py-1 pr-3 font-medium">Month</th>
                  {depts.map((d) => <th key={d} className="px-2 py-1 text-right font-medium">{DEPARTMENT_SHORT[d]}</th>)}
                  <th className="px-2 py-1 text-right font-medium">Total</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 tabular-nums">
                {data.monthly_trend.map((m) => (
                  <tr key={m.month}>
                    <td className="py-1 pr-3 text-slate-700">{monthLabel(m.month)}</td>
                    {depts.map((d) => <td key={d} className="px-2 py-1 text-right">{m[d] ?? 0}</td>)}
                    <td className="px-2 py-1 text-right font-semibold">{m.total}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      </div>
    </Card>
  )
}

function RankedList({ title, items }: { title: string; items: PopulationReport['top_terms']['diagnoses'] }) {
  const { PAIR } = useChartTheme()
  const max = Math.max(...items.map((i) => i.count), 1)
  return (
    <div>
      <h3 className="mb-3 text-sm font-semibold text-slate-900">{title}</h3>
      <ol className="space-y-2">
        {items.map((i) => (
          <li key={i.term} className="text-sm">
            <div className="flex items-baseline justify-between gap-3">
              <span className="min-w-0 truncate text-slate-700" title={i.term}>{i.term}</span>
              <span className="shrink-0 tabular-nums text-slate-500">
                <span className="font-semibold text-slate-900">{i.count}</span> · {i.pct}%
              </span>
            </div>
            <div className="mt-1 h-1.5 rounded-full bg-slate-100">
              <div className="h-full rounded-full" style={{ width: `${(i.count / max) * 100}%`, background: PAIR.a }} />
            </div>
          </li>
        ))}
      </ol>
    </div>
  )
}

function TopTermsSection({ data }: { data: PopulationReport }) {
  return (
    <Card>
      <CardHeader title="Top diagnoses and procedures" subtitle="Share of in-scope cases" />
      <div className="grid grid-cols-1 gap-8 p-5 lg:grid-cols-2">
        <RankedList title="Diagnoses" items={data.top_terms.diagnoses} />
        <RankedList title="Procedures" items={data.top_terms.procedures} />
      </div>
    </Card>
  )
}
