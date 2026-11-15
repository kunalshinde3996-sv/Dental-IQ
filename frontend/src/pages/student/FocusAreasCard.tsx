import { intelligenceApi } from '../../api'
import { Card, CardHeader, Spinner } from '../../components/ui'
import { useApi } from '../../lib/useApi'

const ICON: Record<string, string> = { attendance: 'A', clinical: 'C', marks: 'S', documentation: 'D' }

/** Gentle personal "focus areas": same signals as the faculty alerts, student-friendly wording. */
export function FocusAreasCard({ studentId }: { studentId: number }) {
  const { data, error } = useApi(() => intelligenceApi.focusAreas(studentId), [studentId])
  return (
    <Card>
      <CardHeader title="Focus areas" subtitle={data?.summary ?? 'Personal suggestions for this month'} />
      <div className="p-5">
        {error && <p className="text-sm text-slate-500">Focus areas are unavailable right now.</p>}
        {!data && !error && <Spinner />}
        {data && (
          <div className="space-y-3">
            {data.items.map((i) => (
              <div key={i.title + i.message} className="flex gap-3 rounded-lg bg-brand-50/60 p-3 ring-1 ring-brand-100">
                <span aria-hidden className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand-600 text-xs font-semibold text-white">{ICON[i.area] ?? '•'}</span>
                <div>
                  <p className="text-sm font-semibold text-slate-900">{i.title}</p>
                  <p className="text-sm text-slate-700">{i.message}</p>
                </div>
              </div>
            ))}
            {data.strengths.length > 0 && (
              <ul className="space-y-1 text-sm text-emerald-700">
                {data.strengths.map((s) => <li key={s}>✓ {s}</li>)}
              </ul>
            )}
          </div>
        )}
      </div>
    </Card>
  )
}
