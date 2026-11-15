import type { HabitStatus } from '../../api/types'
import { Badge } from '../../components/ui'

interface HabitFields {
  tobacco_smoking: HabitStatus
  smokeless_tobacco: HabitStatus
  alcohol: HabitStatus
}

const HABITS: { key: keyof HabitFields; label: string }[] = [
  { key: 'smokeless_tobacco', label: 'Gutkha/SLT' },
  { key: 'tobacco_smoking', label: 'Smoking' },
  { key: 'alcohol', label: 'Alcohol' },
]

/** Oral-cancer risk habits at a glance: current = red, former = amber. */
export function HabitBadges({ patient }: { patient: HabitFields }) {
  const shown = HABITS.filter((h) => patient[h.key] !== 'never')
  if (shown.length === 0) return <span className="text-xs text-slate-500">None</span>
  return (
    <div className="flex flex-wrap gap-1">
      {shown.map((h) =>
        patient[h.key] === 'current' ? (
          <Badge key={h.key} className="bg-rose-50 text-rose-700 ring-rose-200">
            {h.label}
          </Badge>
        ) : (
          <Badge key={h.key} className="bg-amber-50 text-amber-700 ring-amber-200">
            Ex-{h.label.toLowerCase()}
          </Badge>
        ),
      )}
    </div>
  )
}
