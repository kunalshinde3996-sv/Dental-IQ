import { useEffect, useState } from 'react'
import { marksApi, studentsApi } from '../../api'
import type { ExamType, StudentRead, StudentYear } from '../../api/types'
import { Button, Card, ErrorBanner, Field, Input, PageHeader, Select, Spinner, cx } from '../../components/ui'
import { todayIso } from '../../lib/format'
import { YEARS, entries } from '../../lib/labels'

const EXAMS: Record<ExamType, string> = {
  internal: 'Internal assessment', sessional: 'Sessional', practical: 'Practical', viva: 'Viva voce', university: 'University',
}
const NEW_SUBJECT = '__new__'

/** Faculty: enter one exam's marks for a whole year. Re-saving the same exam updates the marks. */
export function MarksEntryPage() {
  const [year, setYear] = useState<StudentYear>('bds4')
  const [subjects, setSubjects] = useState<string[]>([])
  const [subject, setSubject] = useState('')
  const [customSubject, setCustomSubject] = useState('')
  const [examType, setExamType] = useState<ExamType>('internal')
  const [maxMarks, setMaxMarks] = useState('50')
  const [examDate, setExamDate] = useState(todayIso())
  const [students, setStudents] = useState<StudentRead[] | null>(null)
  const [values, setValues] = useState<Record<number, string>>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setSaved(null)
    Promise.all([studentsApi.list({ year }), marksApi.subjects(year)])
      .then(([list, subs]) => {
        if (cancelled) return
        setStudents(list)
        setSubjects(subs)
        setSubject(subs[0] ?? NEW_SUBJECT)
        setValues({})
      })
      .catch((e: Error) => !cancelled && setError(e.message))
      .finally(() => !cancelled && setLoading(false))
    return () => { cancelled = true }
  }, [year])

  const subjectName = subject === NEW_SUBJECT ? customSubject.trim() : subject
  const max = Number(maxMarks)
  const invalid = (v: string) => v !== '' && (Number.isNaN(Number(v)) || Number(v) < 0 || Number(v) > max)
  const filled = Object.entries(values).filter(([, v]) => v !== '')
  const hasInvalid = filled.some(([, v]) => invalid(v))

  async function save() {
    if (!subjectName || !max || hasInvalid || filled.length === 0) return
    setSaving(true)
    setError(null)
    try {
      const res = await marksApi.bulk({
        subject: subjectName, exam_type: examType, max_marks: max, exam_date: examDate,
        entries: filled.map(([id, v]) => ({ student_id: Number(id), marks: Number(v) })),
      })
      const avg = res.reduce((s, a) => s + a.percentage, 0) / res.length
      setSaved(`Saved ${res.length} marks for ${subjectName} (${EXAMS[examType]}). Class average ${avg.toFixed(1)}%.`)
      if (!subjects.includes(subjectName)) setSubjects((s) => [...s, subjectName].sort())
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not save marks')
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <PageHeader title="Marks Entry" subtitle="Leave a box empty to skip that student. Marks feed the learning plans and at-risk alerts." />
      <Card className="mb-6">
        <div className="grid grid-cols-1 gap-3 p-4 sm:grid-cols-2 lg:grid-cols-5">
          <Field label="Year">
            <Select value={year} onChange={(e) => setYear(e.target.value as StudentYear)}>
              {entries(YEARS).map((y) => <option key={y} value={y}>{YEARS[y]}</option>)}
            </Select>
          </Field>
          <Field label="Subject">
            <Select value={subject} onChange={(e) => setSubject(e.target.value)}>
              {subjects.map((s) => <option key={s} value={s}>{s}</option>)}
              <option value={NEW_SUBJECT}>+ Other subject…</option>
            </Select>
          </Field>
          <Field label="Exam">
            <Select value={examType} onChange={(e) => setExamType(e.target.value as ExamType)}>
              {entries(EXAMS).map((x) => <option key={x} value={x}>{EXAMS[x]}</option>)}
            </Select>
          </Field>
          <Field label="Max marks"><Input type="number" min={1} max={1000} value={maxMarks} onChange={(e) => setMaxMarks(e.target.value)} /></Field>
          <Field label="Exam date"><Input type="date" max={todayIso()} value={examDate} onChange={(e) => setExamDate(e.target.value)} /></Field>
          {subject === NEW_SUBJECT && (
            <Field label="New subject name" className="sm:col-span-2">
              <Input value={customSubject} maxLength={80} onChange={(e) => setCustomSubject(e.target.value)} placeholder="e.g. Public Health Dentistry" />
            </Field>
          )}
        </div>
      </Card>

      {error && <div className="mb-4"><ErrorBanner message={error} /></div>}
      {saved && <div className="mb-4 rounded-lg bg-emerald-50 px-4 py-3 text-sm text-emerald-800 ring-1 ring-emerald-200" role="status">{saved}</div>}
      {loading && <Spinner />}
      {!loading && students && (
        <Card>
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 p-4">
            <span className="text-sm text-slate-600">{filled.length} of {students.length} entered{hasInvalid && <span className="ml-2 text-rose-600">Some marks are outside 0–{max}.</span>}</span>
            <Button onClick={save} loading={saving} disabled={!subjectName || !max || hasInvalid || filled.length === 0}>Save marks</Button>
          </div>
          <ul className="divide-y divide-slate-100">
            {students.map((s) => (
              <li key={s.id} className="flex items-center justify-between gap-3 px-4 py-2">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-slate-900">{s.name}</p>
                  <p className="text-xs text-slate-500">{s.roll_no}</p>
                </div>
                <div className="flex items-center gap-2">
                  <Input type="number" inputMode="decimal" step="0.5" min={0} max={max} aria-label={`Marks for ${s.name}`}
                    value={values[s.id] ?? ''} onChange={(e) => setValues((v) => ({ ...v, [s.id]: e.target.value }))}
                    className={cx('w-24 text-right', invalid(values[s.id] ?? '') && 'ring-rose-400')} />
                  <span className="w-12 text-xs text-slate-500">/ {max || '—'}</span>
                </div>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </>
  )
}
