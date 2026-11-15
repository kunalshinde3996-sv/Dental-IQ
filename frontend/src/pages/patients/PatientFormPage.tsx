import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { patientsApi } from '../../api'
import { ApiError } from '../../api/client'
import type { HabitStatus, PatientInput, Sex, Taluka } from '../../api/types'
import { Button, Card, CardHeader, ErrorBanner, Field, Input, PageHeader, Segmented, Select, Spinner, Textarea } from '../../components/ui'
import { HABITS, SEXES, TALUKAS, entries } from '../../lib/labels'

interface FormState {
  name: string
  age: string
  sex: Sex
  taluka: Taluka | ''
  phone: string
  abha_id: string
  tobacco_smoking: HabitStatus
  smokeless_tobacco: HabitStatus
  alcohol: HabitStatus
  habit_duration_years: string
  has_diabetes: boolean
  has_hypertension: boolean
  has_cardiac_disease: boolean
  allergies: string
  medical_history_notes: string
}

const EMPTY: FormState = {
  name: '', age: '', sex: 'female', taluka: '', phone: '', abha_id: '',
  tobacco_smoking: 'never', smokeless_tobacco: 'never', alcohol: 'never', habit_duration_years: '',
  has_diabetes: false, has_hypertension: false, has_cardiac_disease: false, allergies: '', medical_history_notes: '',
}

const HABIT_OPTIONS = entries(HABITS).map((h) => ({
  value: h,
  label: HABITS[h],
  activeClass:
    h === 'current' ? 'bg-rose-600 text-white shadow-sm' : h === 'former' ? 'bg-amber-500 text-white shadow-sm' : undefined,
}))

function toPayload(f: FormState): PatientInput {
  const anyHabit = [f.tobacco_smoking, f.smokeless_tobacco, f.alcohol].some((h) => h !== 'never')
  return {
    name: f.name.trim(),
    age: Number(f.age),
    sex: f.sex,
    taluka: f.taluka as Taluka,
    phone: f.phone.trim() || null,
    abha_id: f.abha_id.trim() || null,
    tobacco_smoking: f.tobacco_smoking,
    smokeless_tobacco: f.smokeless_tobacco,
    alcohol: f.alcohol,
    habit_duration_years: anyHabit && f.habit_duration_years ? Number(f.habit_duration_years) : null,
    has_diabetes: f.has_diabetes,
    has_hypertension: f.has_hypertension,
    has_cardiac_disease: f.has_cardiac_disease,
    allergies: f.allergies.trim() || null,
    medical_history_notes: f.medical_history_notes.trim() || null,
  }
}

/** Register a new patient (/patients/new) or edit one (/patients/:id/edit). */
export function PatientFormPage() {
  const { id } = useParams()
  const editing = Boolean(id)
  const navigate = useNavigate()
  const [form, setForm] = useState<FormState>(EMPTY)
  const [loadingExisting, setLoadingExisting] = useState(editing)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  useEffect(() => {
    if (!id) return
    patientsApi
      .get(Number(id))
      .then((p) =>
        setForm({
          name: p.name, age: String(p.age), sex: p.sex, taluka: p.taluka, phone: p.phone ?? '', abha_id: p.abha_id ?? '',
          tobacco_smoking: p.tobacco_smoking, smokeless_tobacco: p.smokeless_tobacco, alcohol: p.alcohol,
          habit_duration_years: p.habit_duration_years?.toString() ?? '', has_diabetes: p.has_diabetes,
          has_hypertension: p.has_hypertension, has_cardiac_disease: p.has_cardiac_disease,
          allergies: p.allergies ?? '', medical_history_notes: p.medical_history_notes ?? '',
        }),
      )
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoadingExisting(false))
  }, [id])

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) => setForm((f) => ({ ...f, [key]: value }))
  const anyHabit = [form.tobacco_smoking, form.smokeless_tobacco, form.alcohol].some((h) => h !== 'never')

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    setError(null)
    setFieldErrors({})
    try {
      const payload = toPayload(form)
      const saved = editing ? await patientsApi.update(Number(id), payload) : await patientsApi.create(payload)
      navigate(`/patients/${saved.id}`, { replace: editing })
    } catch (err) {
      if (err instanceof ApiError) {
        setFieldErrors(err.fieldErrors)
        setError(Object.keys(err.fieldErrors).length ? 'Please correct the highlighted fields.' : err.message)
      } else {
        setError('Could not save patient')
      }
    } finally {
      setSaving(false)
    }
  }

  if (loadingExisting) return <Spinner />

  return (
    <>
      <PageHeader
        title={editing ? 'Edit patient' : 'Register patient'}
        subtitle="Demographics, oral-cancer risk habits and medical history."
      />
      <form onSubmit={onSubmit} className="space-y-6">
        {error && <ErrorBanner message={error} />}

        <Card>
          <CardHeader title="Demographics" />
          <div className="grid grid-cols-1 gap-4 p-5 sm:grid-cols-2 lg:grid-cols-3">
            <Field label="Full name *" error={fieldErrors.name} className="sm:col-span-2 lg:col-span-1">
              <Input required minLength={2} maxLength={120} value={form.name} onChange={(e) => set('name', e.target.value)} />
            </Field>
            <Field label="Age *" error={fieldErrors.age}>
              <Input required type="number" min={0} max={120} value={form.age} onChange={(e) => set('age', e.target.value)} />
            </Field>
            <Field label="Sex *" error={fieldErrors.sex}>
              <Select value={form.sex} onChange={(e) => set('sex', e.target.value as Sex)}>
                {entries(SEXES).map((s) => (
                  <option key={s} value={s}>{SEXES[s]}</option>
                ))}
              </Select>
            </Field>
            <Field label="Taluka *" error={fieldErrors.taluka}>
              <Select required value={form.taluka} onChange={(e) => set('taluka', e.target.value as Taluka)}>
                <option value="" disabled>Select taluka</option>
                {entries(TALUKAS).map((t) => (
                  <option key={t} value={t}>{TALUKAS[t]}</option>
                ))}
              </Select>
            </Field>
            <Field label="Mobile" error={fieldErrors.phone} hint="10-digit Indian mobile">
              <Input type="tel" inputMode="numeric" value={form.phone} onChange={(e) => set('phone', e.target.value)} placeholder="98XXXXXXXX" />
            </Field>
            <Field label="ABHA number" error={fieldErrors.abha_id} hint="Optional · 14 digits (Ayushman Bharat Health Account)">
              <Input inputMode="numeric" value={form.abha_id} onChange={(e) => set('abha_id', e.target.value)} placeholder="XX-XXXX-XXXX-XXXX" />
            </Field>
          </div>
        </Card>

        <Card>
          <CardHeader title="Risk habits" subtitle="Used for oral cancer and potentially malignant disorder screening." />
          <div className="grid grid-cols-1 gap-5 p-5 sm:grid-cols-2">
            {([
              ['smokeless_tobacco', 'Smokeless tobacco (gutkha / khaini / mishri)'],
              ['tobacco_smoking', 'Smoking (cigarette / bidi)'],
              ['alcohol', 'Alcohol'],
            ] as const).map(([key, label]) => (
              <div key={key}>
                <p className="mb-1.5 text-sm font-medium text-slate-700">{label}</p>
                <Segmented name={label} value={form[key]} options={HABIT_OPTIONS} onChange={(v) => set(key, v)} />
              </div>
            ))}
            {anyHabit && (
              <Field label="Habit duration (years)" error={fieldErrors.habit_duration_years}>
                <Input type="number" min={0} max={100} value={form.habit_duration_years} onChange={(e) => set('habit_duration_years', e.target.value)} />
              </Field>
            )}
          </div>
        </Card>

        <Card>
          <CardHeader title="Medical history" />
          <div className="space-y-4 p-5">
            <div className="flex flex-wrap gap-x-6 gap-y-2">
              {([
                ['has_diabetes', 'Diabetes'],
                ['has_hypertension', 'Hypertension'],
                ['has_cardiac_disease', 'Cardiac disease'],
              ] as const).map(([key, label]) => (
                <label key={key} className="inline-flex items-center gap-2 text-sm text-slate-700">
                  <input type="checkbox" className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500" checked={form[key]} onChange={(e) => set(key, e.target.checked)} />
                  {label}
                </label>
              ))}
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Field label="Allergies" error={fieldErrors.allergies}>
                <Input maxLength={255} value={form.allergies} onChange={(e) => set('allergies', e.target.value)} placeholder="e.g. Penicillin" />
              </Field>
              <Field label="Other medical history" error={fieldErrors.medical_history_notes} className="sm:col-span-2">
                <Textarea maxLength={2000} value={form.medical_history_notes} onChange={(e) => set('medical_history_notes', e.target.value)} />
              </Field>
            </div>
          </div>
        </Card>

        <div className="flex justify-end gap-2">
          <Link to={editing ? `/patients/${id}` : '/patients'} className="inline-flex items-center rounded-lg px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100">
            Cancel
          </Link>
          <Button type="submit" loading={saving}>
            {editing ? 'Save changes' : 'Register patient'}
          </Button>
        </div>
      </form>
    </>
  )
}
