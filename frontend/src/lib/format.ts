const dateFmt = new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })

/** Format an ISO date (YYYY-MM-DD) or datetime for display, e.g. "15 Nov 2026". */
export function formatDate(value: string | null | undefined): string {
  if (!value) return '—'
  const d = value.length === 10 ? new Date(`${value}T00:00:00`) : new Date(value)
  return Number.isNaN(d.getTime()) ? value : dateFmt.format(d)
}

/** Today's date as YYYY-MM-DD in local time. */
export function todayIso(): string {
  const d = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

export function initials(name: string): string {
  return name
    .replace(/^Dr\.\s*/, '')
    .split(/\s+/)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? '')
    .join('')
}
