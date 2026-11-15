import { useEffect, useMemo, useState } from 'react'
import { useToast } from '../../lib/toast'
import { attendanceApi, studentsApi } from '../../api'
import type { AttendanceSessionType, AttendanceStatus, StudentRead, StudentYear } from '../../api/types'
import { Button, Card, ErrorBanner, Field, Input, PageHeader, Select, Spinner, cx } from '../../components/ui'
import { todayIso } from '../../lib/format'
import { YEARS, entries } from '../../lib/labels'

const STATUSES: { value: AttendanceStatus; short: string; label: string; active: string }[] = [
  { value: 'present', short: 'P', label: 'Present', active: 'bg-emerald-600 text-white ring-emerald-600' },
  { value: 'late', short: 'L', label: 'Late', active: 'bg-amber-500 text-white ring-amber-500' },
  { value: 'absent', short: 'A', label: 'Absent', active: 'bg-rose-600 text-white ring-rose-600' },
  { value: 'excused', short: 'E', label: 'Excused', active: 'bg-slate-600 text-white ring-slate-600' },
]
const SESSIONS: Record<AttendanceSessionType, string> = { theory: 'Theory', practical: 'Practical (pre-clinical)', clinic: 'Clinic' }

/** Faculty: mark one session's attendance for a whole year in one go (upserts existing marks). */
export function AttendancePage() {
  const [date, setDate] = useState(todayIso())
  const [session, setSession] = useState<AttendanceSessionType>('clinic')
  const [year, setYear] = useState<StudentYear>('bds3')
  const [students, setStudents] = useState<StudentRead[] | null>(null)
  const [marks, setMarks] = useState<Record<number, AttendanceStatus>>({})
  const [existing, setExisting] = useState(0)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState<string | null>(null)
  const toast = useToast()

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    setSaved(null)
    Promise.all([studentsApi.list({ year }), attendanceApi.list({ date_from: date, date_to: date, session })])
      .then(([list, records]) => {
        if (cancelled) return
        const ids = new Set(list.map((s) => s.id))
        const prior = records.filter((r) => ids.has(r.student_id))
        const byId = Object.fromEntries(prior.map((r) => [r.student_id, r.status]))
        setStudents(list)
        setExisting(prior.length)
        setMarks(Object.fromEntries(list.map((s) => [s.id, byId[s.id] ?? 'present'])))
      })
      .catch((e: Error) => !cancelled && setError(e.message))
      .finally(() => !cancelled && setLoading(false))
    return () => { cancelled = true }
  }, [date, session, year])

  const tally = useMemo(() => {
    const t: Record<AttendanceStatus, number> = { present: 0, late: 0, absent: 0, excused: 0 }
    Object.values(marks).forEach((m) => t[m]++)
    return t
  }, [marks])

  async function save() {
    if (!students) return
    setSaving(true)
    setError(null)
    try {
      const res = await attendanceApi.bulk({ date, session, entries: students.map((s) => ({ student_id: s.id, status: marks[s.id] })) })
      setExisting(res.length)
      setSaved(`Saved ${res.length} records for ${YEARS[year]} · ${SESSIONS[session]} · ${date}.`)
      toast.success(`Attendance saved for ${res.length} students`)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not save attendance')
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <PageHeader title="Mark Attendance" subtitle="Everyone starts as Present; tap to change. Saving again updates the same session." />
      <Card className="mb-6">
        <div className="grid grid-cols-1 gap-3 p-4 sm:grid-cols-3">
          <Field label="Date"><Input type="date" max={todayIso()} value={date} onChange={(e) => setDate(e.target.value)} /></Field>
          <Field label="Session">
            <Select value={session} onChange={(e) => setSession(e.target.value as AttendanceSessionType)}>
              {entries(SESSIONS).map((s) => <option key={s} value={s}>{SESSIONS[s]}</option>)}
            </Select>
          </Field>
          <Field label="Year">
            <Select value={year} onChange={(e) => setYear(e.target.value as StudentYear)}>
              {entries(YEARS).map((y) => <option key={y} value={y}>{YEARS[y]}</option>)}
            </Select>
          </Field>
        </div>
      </Card>

      {error && <div className="mb-4"><ErrorBanner message={error} /></div>}
      {saved && <p className="mb-4 text-sm text-slate-600">Last saved: {saved}</p>}
      {loading && <Spinner />}
      {!loading && students && (
        <Card>
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 p-4">
            <div className="flex flex-wrap gap-3 text-sm text-slate-600">
              {STATUSES.map((s) => <span key={s.value}>{s.label}: <span className="font-semibold tabular-nums text-slate-900">{tally[s.value]}</span></span>)}
              {existing > 0 && <span className="text-xs text-amber-700">{existing} already recorded for this session (editing)</span>}
            </div>
            <div className="flex gap-2">
              <Button variant="secondary" onClick={() => setMarks(Object.fromEntries(students.map((s) => [s.id, 'present'])))}>All present</Button>
              <Button onClick={save} loading={saving}>Save attendance</Button>
            </div>
          </div>
          <ul className="divide-y divide-slate-100">
            {students.map((s) => (
              <li key={s.id} className="flex flex-wrap items-center justify-between gap-3 px-4 py-2.5">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-slate-900">{s.name}</p>
                  <p className="text-xs text-slate-500">{s.roll_no}</p>
                </div>
                <div className="flex gap-1" role="radiogroup" aria-label={`Attendance for ${s.name}`}>
                  {STATUSES.map((st) => (
                    <button key={st.value} type="button" role="radio" aria-checked={marks[s.id] === st.value} title={st.label}
                      onClick={() => setMarks((m) => ({ ...m, [s.id]: st.value }))}
                      className={cx('h-8 w-8 rounded-md text-xs font-semibold ring-1 transition',
                        marks[s.id] === st.value ? st.active : 'bg-white text-slate-500 ring-slate-300 hover:ring-slate-400')}>
                      {st.short}
                    </button>
                  ))}
                </div>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </>
  )
}
