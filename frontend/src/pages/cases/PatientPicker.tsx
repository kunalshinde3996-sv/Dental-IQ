import { useEffect, useState } from 'react'
import { patientsApi } from '../../api'
import type { PatientListItem } from '../../api/types'
import { Button, Input, cx } from '../../components/ui'
import { SEXES, TALUKAS } from '../../lib/labels'
import { useDebounced } from '../../lib/useApi'

export interface PickedPatient {
  id: number
  name: string
  opd_number: string
  detail: string
}

export function toPicked(p: Pick<PatientListItem, 'id' | 'name' | 'opd_number' | 'age' | 'sex' | 'taluka'>): PickedPatient {
  return { id: p.id, name: p.name, opd_number: p.opd_number, detail: `${p.age} · ${SEXES[p.sex]} · ${TALUKAS[p.taluka]}` }
}

/** Search-as-you-type patient selector. */
export function PatientPicker({ value, onChange, error }: { value: PickedPatient | null; onChange: (p: PickedPatient | null) => void; error?: string }) {
  const [q, setQ] = useState('')
  const query = useDebounced(q, 250)
  const [results, setResults] = useState<PatientListItem[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (value || query.trim().length < 2) {
      setResults([])
      return
    }
    let cancelled = false
    setLoading(true)
    patientsApi
      .list({ q: query, limit: 8 })
      .then((page) => !cancelled && setResults(page.items))
      .catch(() => !cancelled && setResults([]))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [query, value])

  if (value) {
    return (
      <div className="flex items-center justify-between gap-3 rounded-lg bg-brand-50 px-4 py-3 ring-1 ring-brand-200">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-slate-900">{value.name}</p>
          <p className="truncate text-xs text-slate-600">
            {value.opd_number} · {value.detail}
          </p>
        </div>
        <Button variant="secondary" className="px-3 py-1" onClick={() => onChange(null)}>
          Change
        </Button>
      </div>
    )
  }

  return (
    <div className="relative">
      <Input
        type="search"
        placeholder="Search by name, OPD no., ABHA or phone (min. 2 characters)"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        aria-label="Search patient"
        className={cx(error && 'ring-rose-400')}
      />
      {error && <p className="mt-1 text-xs text-rose-600">{error}</p>}
      {(results.length > 0 || loading) && (
        <ul className="absolute z-10 mt-1 max-h-72 w-full overflow-auto rounded-lg bg-white py-1 shadow-lg ring-1 ring-slate-200">
          {loading && results.length === 0 && <li className="px-4 py-2 text-sm text-slate-500">Searching…</li>}
          {results.map((p) => (
            <li key={p.id}>
              <button type="button" className="w-full px-4 py-2 text-left hover:bg-brand-50" onClick={() => onChange(toPicked(p))}>
                <span className="block text-sm font-medium text-slate-900">{p.name}</span>
                <span className="block text-xs text-slate-500">
                  {p.opd_number} · {p.age} · {SEXES[p.sex]} · {TALUKAS[p.taluka]}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {!loading && query.trim().length >= 2 && results.length === 0 && (
        <p className="mt-1 text-xs text-slate-500">No match. Register the patient first from the Patients page.</p>
      )}
    </div>
  )
}
