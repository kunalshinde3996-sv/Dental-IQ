// Chart colours. Categorical slots are assigned in a FIXED order to entities
// (never by rank), so a department keeps its colour whatever the filter.
// Values are the validated reference categorical palette (light mode).
import type { Department } from '../api/types'

export const SERIES = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#6250d6', '#e34948']

export const DEPARTMENT_COLORS: Record<Department, string> = {
  oral_medicine: SERIES[0],
  conservative: SERIES[1],
  endodontics: SERIES[2],
  periodontics: SERIES[3],
  prosthodontics: SERIES[4],
  oral_surgery: SERIES[5],
  pedodontics: SERIES[6],
  orthodontics: SERIES[7],
}

/** Two-entity comparisons (e.g. exposed vs non-exposed, male vs female) use slots 1 and 2. */
export const PAIR = { a: SERIES[0], b: SERIES[1] }

/** Single-hue sequential ramp (brand teal) for magnitude, light -> dark. */
const RAMP = ['#effcfb', '#d6f5f3', '#b0ebe8', '#7bdbd8', '#40c1c1', '#25a5a7', '#1f848b', '#1f6a71']

/** Map value in [0, max] onto the ramp; returns background + readable text colour. */
export function heat(value: number, max: number): { background: string; color: string } {
  if (max <= 0) return { background: RAMP[0], color: '#0f172a' }
  const idx = Math.min(RAMP.length - 1, Math.round((value / max) * (RAMP.length - 1)))
  return { background: RAMP[idx], color: idx >= 5 ? '#ffffff' : '#0f172a' }
}

export const AXIS = { stroke: '#cbd5e1', tick: { fill: '#64748b', fontSize: 12 } }
export const GRID = '#e2e8f0'
