import type { StudentQuotaProgress } from '../../api/types'
import { Card, CardHeader, EmptyState, ProgressBar } from '../../components/ui'
import { DEPARTMENTS } from '../../lib/labels'

function tone(percent: number) {
  if (percent >= 100) return 'emerald' as const
  if (percent >= 50) return 'brand' as const
  if (percent >= 25) return 'amber' as const
  return 'rose' as const
}

/** Approved cases vs. required clinical quota, per department. */
export function QuotaProgressCard({ progress }: { progress: StudentQuotaProgress }) {
  if (!progress.is_clinical) {
    return (
      <Card>
        <CardHeader title="Clinical quota" />
        <EmptyState title="Pre-clinical year">Clinical quotas start from BDS III.</EmptyState>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader
        title="Clinical quota progress"
        subtitle={`${progress.total_approved} of ${progress.total_required} required cases approved`}
        action={<span className="text-2xl font-semibold tabular-nums text-brand-700">{Math.round(progress.overall_percent)}%</span>}
      />
      <ul className="grid grid-cols-1 gap-x-8 gap-y-4 p-5 md:grid-cols-2">
        {progress.departments.map((d) => (
          <li key={d.department}>
            <div className="mb-1.5 flex items-baseline justify-between gap-2 text-sm">
              <span className="font-medium text-slate-800">{DEPARTMENTS[d.department]}</span>
              <span className="whitespace-nowrap tabular-nums text-slate-600">
                <span className="font-semibold text-slate-900">{d.approved}</span> / {d.required}
                {d.pending > 0 && <span className="ml-1.5 text-xs text-amber-700">+{d.pending} pending</span>}
              </span>
            </div>
            <ProgressBar percent={d.percent} tone={tone(d.percent)} label={`${DEPARTMENTS[d.department]} quota`} />
          </li>
        ))}
      </ul>
    </Card>
  )
}
