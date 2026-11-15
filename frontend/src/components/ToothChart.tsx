// Interactive FDI odontogram for the 32 permanent teeth.
//
// Layout follows the clinical convention (viewer facing the patient):
//   upper right 18..11 | upper left 21..28
//   lower right 48..41 | lower left 31..38
import { useState } from 'react'
import type { ToothCondition, ToothFindingInput } from '../api/types'
import { SURFACES, TOOTH_CONDITIONS, entries } from '../lib/labels'
import { Button, Field, Input, cx } from './ui'

const UPPER = [18, 17, 16, 15, 14, 13, 12, 11, 21, 22, 23, 24, 25, 26, 27, 28]
const LOWER = [48, 47, 46, 45, 44, 43, 42, 41, 31, 32, 33, 34, 35, 36, 37, 38]

const QUADRANT = ['', 'Upper right', 'Upper left', 'Lower left', 'Lower right']
const TOOTH_NAME = ['', 'central incisor', 'lateral incisor', 'canine', 'first premolar',
  'second premolar', 'first molar', 'second molar', 'third molar']

export function toothName(fdi: number): string {
  return `${QUADRANT[Math.floor(fdi / 10)]} ${TOOTH_NAME[fdi % 10]}`
}

type Kind = 'incisor' | 'canine' | 'premolar' | 'molar'

function kindOf(fdi: number): Kind {
  const t = fdi % 10
  if (t <= 2) return 'incisor'
  if (t === 3) return 'canine'
  if (t <= 5) return 'premolar'
  return 'molar'
}

const WIDTH: Record<Kind, number> = { incisor: 24, canine: 26, premolar: 28, molar: 36 }
const H = 64

/** SVG tooth drawn root-up (upper arch); lower-arch teeth are mirrored vertically. */
function ToothShape({ fdi, condition }: { fdi: number; condition?: ToothCondition }) {
  const kind = kindOf(fdi)
  const w = WIDTH[kind]
  const lower = fdi >= 31
  const missing = condition === 'missing'
  const crownFill = condition ? TOOTH_CONDITIONS[condition].fill : '#ffffff'
  const stroke = missing ? '#94a3b8' : '#64748b'
  const dash = missing ? '3 2' : undefined

  const crown = `M2 34 Q2 30 6 30 H${w - 6} Q${w - 2} 30 ${w - 2} 34 V50 Q${w - 2} 62 ${w / 2} 62 Q2 62 2 50 Z`
  const rootTip = kind === 'canine' ? 1 : 6
  const roots =
    kind === 'molar'
      ? [
          `M${w * 0.12} 31 L${w * 0.22} 7 Q${w * 0.3} 2 ${w * 0.38} 7 L${w * 0.46} 31 Z`,
          `M${w * 0.54} 31 L${w * 0.62} 7 Q${w * 0.7} 2 ${w * 0.78} 7 L${w * 0.88} 31 Z`,
        ]
      : [`M${w * 0.24} 31 L${w * 0.4} ${rootTip + 4} Q${w / 2} ${rootTip} ${w * 0.6} ${rootTip + 4} L${w * 0.76} 31 Z`]

  return (
    <svg viewBox={`0 0 ${w} ${H}`} className="h-12 sm:h-14" style={{ width: 'auto', aspectRatio: `${w} / ${H}` }} aria-hidden>
      <g transform={lower ? `translate(0 ${H}) scale(1 -1)` : undefined} opacity={missing ? 0.55 : 1}>
        {roots.map((d, i) => (
          <path key={i} d={d} fill={condition === 'rct' ? '#ddd6fe' : '#f8fafc'} stroke={stroke} strokeWidth={1.2} strokeDasharray={dash} />
        ))}
        {condition === 'rct' &&
          roots.map((_, i) => {
            const x = kind === 'molar' ? (i === 0 ? w * 0.3 : w * 0.7) : w / 2
            return <line key={`c${i}`} x1={x} y1={10} x2={x} y2={31} stroke="#7c3aed" strokeWidth={1.6} />
          })}
        <path d={crown} fill={missing ? '#f1f5f9' : crownFill} stroke={stroke} strokeWidth={1.2} strokeDasharray={dash} />
        {missing && (
          <path d={`M5 33 L${w - 5} 59 M${w - 5} 33 L5 59`} stroke="#64748b" strokeWidth={1.5} />
        )}
      </g>
    </svg>
  )
}

interface ToothChartProps {
  findings: ToothFindingInput[]
  onChange?: (findings: ToothFindingInput[]) => void
  readOnly?: boolean
}

export function ToothChart({ findings, onChange, readOnly = false }: ToothChartProps) {
  const [selected, setSelected] = useState<number | null>(null)
  const byTooth = new Map(findings.map((f) => [f.tooth_number, f]))
  const current = selected !== null ? byTooth.get(selected) : undefined

  function upsert(tooth: number, patch: Partial<ToothFindingInput>) {
    if (!onChange) return
    const existing = byTooth.get(tooth)
    const next: ToothFindingInput = { tooth_number: tooth, condition: 'caries', ...existing, ...patch }
    onChange([...findings.filter((f) => f.tooth_number !== tooth), next].sort((a, b) => a.tooth_number - b.tooth_number))
  }

  function remove(tooth: number) {
    onChange?.(findings.filter((f) => f.tooth_number !== tooth))
  }

  function toggleSurface(code: string) {
    if (selected === null || !current) return
    const set = new Set((current.surfaces ?? '').split('').filter(Boolean))
    if (set.has(code)) set.delete(code)
    else set.add(code)
    const ordered = SURFACES.map((s) => s.code).filter((c) => set.has(c)).join('')
    upsert(selected, { surfaces: ordered || null })
  }

  const renderTooth = (fdi: number, arch: 'upper' | 'lower') => {
    const f = byTooth.get(fdi)
    const title = f
      ? `${fdi} · ${TOOTH_CONDITIONS[f.condition].label}${f.surfaces ? ` (${f.surfaces})` : ''}${f.treatment ? ` · ${f.treatment}` : ''}`
      : `${fdi} · ${toothName(fdi)}`
    const number = (
      <span className={cx('text-[10px] font-semibold tabular-nums sm:text-xs', f ? 'text-slate-900' : 'text-slate-400')}>{fdi}</span>
    )
    return (
      <button
        key={fdi}
        type="button"
        title={title}
        aria-label={title}
        aria-pressed={selected === fdi}
        disabled={readOnly}
        onClick={() => setSelected(selected === fdi ? null : fdi)}
        className={cx(
          'flex flex-col items-center gap-0.5 rounded-md px-0.5 py-1 transition',
          !readOnly && 'hover:bg-brand-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500',
          selected === fdi && 'bg-brand-50 ring-2 ring-brand-500',
          readOnly && 'cursor-default',
        )}
      >
        {arch === 'lower' && number}
        <ToothShape fdi={fdi} condition={f?.condition} />
        {arch === 'upper' && number}
      </button>
    )
  }

  return (
    <div>
      <div className="overflow-x-auto pb-2">
        <div className="mx-auto w-max min-w-full">
          <div className="flex justify-between px-1 text-[11px] font-medium uppercase tracking-wide text-slate-400">
            <span>Upper right</span>
            <span>Upper left</span>
          </div>
          <div className="flex items-end justify-center">
            <div className="flex items-end gap-0.5 border-r-2 border-dashed border-slate-200 pr-1">{UPPER.slice(0, 8).map((t) => renderTooth(t, 'upper'))}</div>
            <div className="flex items-end gap-0.5 pl-1">{UPPER.slice(8).map((t) => renderTooth(t, 'upper'))}</div>
          </div>
          <div className="my-1 border-t-2 border-dashed border-slate-200" />
          <div className="flex items-start justify-center">
            <div className="flex items-start gap-0.5 border-r-2 border-dashed border-slate-200 pr-1">{LOWER.slice(0, 8).map((t) => renderTooth(t, 'lower'))}</div>
            <div className="flex items-start gap-0.5 pl-1">{LOWER.slice(8).map((t) => renderTooth(t, 'lower'))}</div>
          </div>
          <div className="flex justify-between px-1 text-[11px] font-medium uppercase tracking-wide text-slate-400">
            <span>Lower right</span>
            <span>Lower left</span>
          </div>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1.5">
        {entries(TOOTH_CONDITIONS).map((c) => (
          <span key={c} className="inline-flex items-center gap-1.5 text-xs text-slate-600">
            <span className={cx('h-3 w-3 rounded-sm ring-1 ring-slate-300', TOOTH_CONDITIONS[c].swatch)} />
            {TOOTH_CONDITIONS[c].label}
          </span>
        ))}
      </div>

      {!readOnly && selected === null && (
        <p className="mt-4 rounded-lg bg-slate-50 px-4 py-3 text-sm text-slate-500">
          Click a tooth to record its condition, surfaces and treatment.
        </p>
      )}

      {!readOnly && selected !== null && (
        <div className="mt-4 rounded-xl border border-brand-200 bg-brand-50/40 p-4">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-sm font-semibold text-slate-900">
              Tooth {selected} <span className="font-normal text-slate-500">· {toothName(selected)}</span>
            </h3>
            <div className="flex gap-2">
              {current && (
                <Button variant="ghost" className="px-2 py-1 text-rose-600 hover:bg-rose-50" onClick={() => { remove(selected); setSelected(null) }}>
                  Clear tooth
                </Button>
              )}
              <Button variant="secondary" className="px-3 py-1" onClick={() => setSelected(null)}>
                Done
              </Button>
            </div>
          </div>

          <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-slate-500">Condition</p>
          <div className="mb-4 flex flex-wrap gap-1.5">
            {entries(TOOTH_CONDITIONS).map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => upsert(selected, { condition: c })}
                className={cx(
                  'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ring-1 transition',
                  current?.condition === c ? 'bg-slate-900 text-white ring-slate-900' : 'bg-white text-slate-700 ring-slate-300 hover:ring-slate-400',
                )}
              >
                <span className={cx('h-2.5 w-2.5 rounded-sm', TOOTH_CONDITIONS[c].swatch)} />
                {TOOTH_CONDITIONS[c].label}
              </button>
            ))}
          </div>

          {current && (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-slate-500">Surfaces</p>
                <div className="flex flex-wrap gap-1.5">
                  {SURFACES.map((s) => {
                    const on = (current.surfaces ?? '').includes(s.code)
                    return (
                      <button
                        key={s.code}
                        type="button"
                        title={s.label}
                        aria-pressed={on}
                        onClick={() => toggleSurface(s.code)}
                        className={cx(
                          'h-8 w-8 rounded-md text-xs font-semibold ring-1 transition',
                          on ? 'bg-brand-600 text-white ring-brand-600' : 'bg-white text-slate-600 ring-slate-300 hover:ring-brand-400',
                        )}
                      >
                        {s.code}
                      </button>
                    )
                  })}
                </div>
              </div>
              <Field label="Treatment">
                <Input
                  value={current.treatment ?? ''}
                  maxLength={200}
                  placeholder="e.g. Composite restoration"
                  onChange={(e) => upsert(selected, { treatment: e.target.value || null })}
                />
              </Field>
              <Field label="Notes">
                <Input
                  value={current.notes ?? ''}
                  maxLength={500}
                  placeholder="Optional"
                  onChange={(e) => upsert(selected, { notes: e.target.value || null })}
                />
              </Field>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/** Compact table listing of findings (used alongside the chart). */
export function FindingsTable({ findings }: { findings: ToothFindingInput[] }) {
  if (findings.length === 0) return <p className="text-sm text-slate-500">No tooth findings recorded.</p>
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="text-left text-xs uppercase tracking-wide text-slate-500">
            <th className="py-2 pr-4 font-medium">Tooth</th>
            <th className="py-2 pr-4 font-medium">Condition</th>
            <th className="py-2 pr-4 font-medium">Surfaces</th>
            <th className="py-2 pr-4 font-medium">Treatment</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {findings.map((f) => (
            <tr key={f.tooth_number}>
              <td className="py-2 pr-4">
                <span className="font-semibold tabular-nums">{f.tooth_number}</span>{' '}
                <span className="hidden text-slate-500 sm:inline">{toothName(f.tooth_number)}</span>
              </td>
              <td className="py-2 pr-4">
                <span className="inline-flex items-center gap-1.5">
                  <span className={cx('h-2.5 w-2.5 rounded-sm', TOOTH_CONDITIONS[f.condition].swatch)} />
                  {TOOTH_CONDITIONS[f.condition].label}
                </span>
              </td>
              <td className="py-2 pr-4 font-mono text-xs">{f.surfaces ?? '—'}</td>
              <td className="py-2 pr-4 text-slate-600">{f.treatment ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
