// Shared chart pieces: tooltip, stat tile, insight card.
import type { ReactNode } from 'react'
import type { Insight } from '../api/types'
import { Card, cx } from './ui'

interface TooltipEntry {
  name?: string | number
  value?: number | string
  color?: string
  dataKey?: string | number
}

/** Recharts tooltip with consistent styling. `format` renders each value. */
export function ChartTooltip({
  active,
  payload,
  label,
  format = (v) => String(v),
  labelFormat = (l) => l,
}: {
  active?: boolean
  payload?: TooltipEntry[]
  label?: string
  format?: (v: number | string, entry: TooltipEntry) => string
  labelFormat?: (l: string) => string
}) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-lg bg-white px-3 py-2 text-xs shadow-lg ring-1 ring-slate-200">
      {label !== undefined && <p className="mb-1 font-semibold text-slate-900">{labelFormat(String(label))}</p>}
      <ul className="space-y-0.5">
        {payload.map((p) => (
          <li key={String(p.dataKey ?? p.name)} className="flex items-center gap-2 text-slate-700">
            <span className="h-2.5 w-2.5 rounded-sm" style={{ background: p.color }} />
            <span>{p.name}</span>
            <span className="ml-auto pl-3 font-semibold tabular-nums text-slate-900">{p.value !== undefined ? format(p.value, p) : '—'}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

export function StatTile({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <Card className="p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums text-slate-900">{value}</p>
      {hint && <p className="mt-0.5 text-xs text-slate-500">{hint}</p>}
    </Card>
  )
}

const TONES: Record<Insight['tone'], { label: string; className: string; icon: string }> = {
  critical: { label: 'High priority', className: 'bg-rose-50 text-rose-700 ring-rose-200', icon: '!' },
  warning: { label: 'Watch', className: 'bg-amber-50 text-amber-800 ring-amber-200', icon: '▲' },
  info: { label: 'Insight', className: 'bg-sky-50 text-sky-700 ring-sky-200', icon: 'i' },
}

export function InsightCard({ insight }: { insight: Insight }) {
  const tone = TONES[insight.tone]
  return (
    <Card className="flex flex-col p-4">
      <span className={cx('inline-flex w-max items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset', tone.className)}>
        <span aria-hidden className="font-bold">{tone.icon}</span>
        {tone.label}
      </span>
      <h3 className="mt-2 text-sm font-semibold text-slate-900">{insight.title}</h3>
      <p className="mt-1 text-sm text-slate-600">{insight.text}</p>
      <p className="mt-auto pt-3 text-xs text-slate-500">
        <span className="font-semibold text-slate-700">Suggested action:</span> {insight.action}
      </p>
    </Card>
  )
}

/** Legend row for multi-series charts (identity is never colour-only: names are always shown). */
export function Legend({ items }: { items: { label: string; color: string }[] }) {
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1">
      {items.map((i) => (
        <span key={i.label} className="inline-flex items-center gap-1.5 text-xs text-slate-600">
          <span className="h-2.5 w-2.5 rounded-sm" style={{ background: i.color }} />
          {i.label}
        </span>
      ))}
    </div>
  )
}
