import { intelligenceApi } from '../../api'
import { Badge, Card, CardHeader, ProgressBar, Spinner, cx } from '../../components/ui'
import { DEPARTMENTS } from '../../lib/labels'
import { useApi } from '../../lib/useApi'

/** Personalised learning plan: departments to seek cases in, subjects to revise. */
export function LearningPlanCard({ studentId }: { studentId: number }) {
  const { data, error } = useApi(() => intelligenceApi.learningPlan(studentId), [studentId])
  return (
    <Card>
      <CardHeader title="Your learning plan" subtitle={data?.summary ?? 'Where to focus next'} />
      {error && <p className="p-5 text-sm text-slate-500">Learning plan unavailable right now.</p>}
      {!data && !error && <Spinner />}
      {data && (
        <div className="grid grid-cols-1 gap-6 p-5 lg:grid-cols-2">
          <section>
            <h3 className="mb-3 text-sm font-semibold text-slate-900">Cases to seek</h3>
            {!data.is_clinical && <p className="text-sm text-slate-500">Clinical postings start in BDS III.</p>}
            {data.is_clinical && data.focus_departments.length === 0 && <p className="text-sm text-slate-500">All department quotas complete.</p>}
            <ul className="space-y-4">
              {data.focus_departments.map((d) => (
                <li key={d.department}>
                  <div className="mb-1 flex flex-wrap items-baseline justify-between gap-2">
                    <span className="text-sm font-medium text-slate-800">
                      {DEPARTMENTS[d.department]}
                      {d.double_priority && <Badge className="ml-2 bg-rose-50 text-rose-700 ring-rose-200">Also weak in theory</Badge>}
                    </span>
                    <span className="text-xs tabular-nums text-slate-500">{d.approved}/{d.required} · {d.remaining} to go</span>
                  </div>
                  <ProgressBar percent={d.percent} tone={d.percent < 25 ? 'rose' : d.percent < 50 ? 'amber' : 'brand'} label={`${DEPARTMENTS[d.department]} quota`} />
                  <ul className="mt-2 list-disc space-y-0.5 pl-5 text-sm text-slate-700">
                    {d.case_types.map((c) => <li key={c}>{c}</li>)}
                  </ul>
                  <p className="mt-1 text-xs text-slate-500">{d.where_to_find}</p>
                </li>
              ))}
            </ul>
          </section>
          <section>
            <h3 className="mb-3 text-sm font-semibold text-slate-900">Subjects to revise</h3>
            {data.focus_subjects.length === 0 && <p className="text-sm text-slate-500">No weak subjects: nice work.</p>}
            <ul className="space-y-3">
              {data.focus_subjects.map((s) => (
                <li key={s.subject} className="rounded-lg bg-slate-50 p-3">
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="text-sm font-medium text-slate-800">{s.subject}</span>
                    <span className={cx('text-sm font-semibold tabular-nums', s.average_pct < 50 ? 'text-rose-700' : 'text-amber-700')}>{s.average_pct}%</span>
                  </div>
                  <p className="text-xs text-slate-500">
                    Latest {s.latest_pct}%{s.trend !== null && ` · ${s.trend >= 0 ? '+' : ''}${s.trend} pts since first exam`}
                  </p>
                  <p className="mt-1 text-sm text-slate-700">{s.tip}</p>
                </li>
              ))}
            </ul>
          </section>
        </div>
      )}
    </Card>
  )
}
