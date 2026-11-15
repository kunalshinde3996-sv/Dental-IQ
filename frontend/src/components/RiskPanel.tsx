// Oral cancer / PMD risk screening: badge + explanation panel.
import { useEffect, useState } from 'react'
import { patientsApi } from '../api'
import type { RiskLevel, RiskScreening } from '../api/types'
import { Badge, ErrorBanner, cx } from './ui'

const LEVEL: Record<RiskLevel, { className: string; icon: string; bar: string }> = {
  High: { className: 'bg-rose-50 text-rose-700 ring-rose-200', icon: '▲', bar: 'bg-rose-500' },
  Medium: { className: 'bg-amber-50 text-amber-800 ring-amber-200', icon: '●', bar: 'bg-amber-500' },
  Low: { className: 'bg-emerald-50 text-emerald-700 ring-emerald-200', icon: '✓', bar: 'bg-emerald-500' },
}

export function RiskBadge({ level, percent }: { level: RiskLevel; percent?: number }) {
  const l = LEVEL[level]
  return (
    <Badge className={l.className}>
      <span aria-hidden className="mr-1">{l.icon}</span>
      {level} risk{percent !== undefined && ` · ${percent}%`}
    </Badge>
  )
}

/**
 * Fetches and explains the patient's oral-cancer risk. `lesionObserved` lets the New Case
 * form include a lesion charted in the current (unsaved) visit.
 */
export function RiskPanel({ patientId, lesionObserved, compact = false }: { patientId: number; lesionObserved?: boolean; compact?: boolean }) {
  const [data, setData] = useState<RiskScreening | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    patientsApi
      .riskScreening(patientId, lesionObserved)
      .then((r) => !cancelled && setData(r))
      .catch((e: Error) => !cancelled && setError(e.message))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [patientId, lesionObserved])

  if (error) return <ErrorBanner message={`Risk screening unavailable: ${error}`} />
  if (!data) return <p className="text-sm text-slate-500">{loading ? 'Calculating oral cancer risk…' : ''}</p>

  const raising = data.factors.filter((f) => f.direction === 'increases')
  const lowering = data.factors.filter((f) => f.direction === 'decreases')
  const maxMult = Math.max(...raising.map((f) => f.odds_multiplier), 2)

  return (
    <div className={cx('space-y-4', loading && 'opacity-60')}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <RiskBadge level={data.risk_level} percent={data.risk_level === data.model_risk_level ? data.risk_percent : undefined} />
        {data.known_pmd_diagnosis && (
          <Badge className="bg-slate-100 text-slate-700 ring-slate-200">PMD on record</Badge>
        )}
      </div>

      <div className="rounded-lg bg-slate-50 p-3 text-sm">
        <p className="font-semibold text-slate-900">Suggested action</p>
        <p className="mt-0.5 text-slate-700">{data.suggested_action}</p>
        {data.additional_actions.length > 0 && (
          <ul className="mt-2 list-disc space-y-0.5 pl-5 text-slate-600">
            {data.additional_actions.map((a) => <li key={a}>{a}</li>)}
          </ul>
        )}
      </div>

      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">
          Why: factors raising risk {raising.length === 0 && '(none)'}
        </p>
        <ul className="space-y-2">
          {raising.slice(0, compact ? 3 : 6).map((f) => (
            <li key={f.feature} className="text-sm">
              <div className="flex items-baseline justify-between gap-2">
                <span className="text-slate-700">{f.label}</span>
                <span className="shrink-0 font-semibold tabular-nums text-slate-900">×{f.odds_multiplier.toFixed(2)} odds</span>
              </div>
              <div className="mt-1 h-1.5 rounded-full bg-slate-100">
                <div className={cx('h-full rounded-full', LEVEL[data.risk_level].bar)} style={{ width: `${(Math.log(f.odds_multiplier) / Math.log(maxMult)) * 100}%` }} />
              </div>
            </li>
          ))}
        </ul>
        {!compact && lowering.length > 0 && (
          <p className="mt-2 text-xs text-slate-500">
            Lowering risk: {lowering.map((f) => `${f.label} (×${f.odds_multiplier.toFixed(2)})`).join(', ')}
          </p>
        )}
      </div>

      {data.lesion_source === 'override' && (
        <p className="text-xs text-slate-500">Includes the lesion charted in this visit.</p>
      )}
      {data.notes.map((n) => <p key={n} className="text-xs text-amber-700">{n}</p>)}
      <p className="border-t border-slate-100 pt-2 text-[11px] leading-snug text-slate-500">
        Logistic-regression model v{data.model.version}, CV AUC {data.model.auc_cv ?? '—'} on {data.model.n_train} synthetic patients.
        Reference: 40-year-old non-user, urban, no lesion ({(data.baseline_probability * 100).toFixed(1)}%). {data.disclaimer}
      </p>
    </div>
  )
}
