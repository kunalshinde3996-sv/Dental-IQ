import { useState, type FormEvent } from 'react'
import { useToast } from '../lib/toast'
import { authApi } from '../api'
import { useAuth } from '../auth/AuthContext'
import { Button, Card, CardHeader, ErrorBanner, Field, Input, PageHeader } from '../components/ui'
import { ROLES, YEARS } from '../lib/labels'

// Mirrors backend/app/core/passwords.py so users see problems before submitting.
const RULES: { label: string; test: (pw: string) => boolean }[] = [
  { label: 'At least 8 characters', test: (pw) => pw.length >= 8 },
  { label: 'An upper-case letter', test: (pw) => /[A-Z]/.test(pw) },
  { label: 'A lower-case letter', test: (pw) => /[a-z]/.test(pw) },
  { label: 'A digit', test: (pw) => /\d/.test(pw) },
  { label: 'A symbol', test: (pw) => /[^A-Za-z0-9]/.test(pw) },
]

export function AccountPage() {
  const { me } = useAuth()
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState(false)
  const toast = useToast()
  if (!me) return null

  const unmet = RULES.filter((r) => !r.test(next))
  const mismatch = confirm.length > 0 && confirm !== next

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (unmet.length || next !== confirm) return
    setSaving(true)
    setError(null)
    setDone(false)
    try {
      await authApi.changePassword(current, next)
      setDone(true)
      toast.success('Password changed')
      setCurrent('')
      setNext('')
      setConfirm('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not change password')
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <PageHeader title="Account" subtitle="Your profile and sign-in security." />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader title="Profile" />
          <dl className="grid grid-cols-2 gap-4 p-5 text-sm">
            <div><dt className="text-xs uppercase tracking-wide text-slate-500">Name</dt><dd className="mt-0.5 font-medium">{me.user.name}</dd></div>
            <div><dt className="text-xs uppercase tracking-wide text-slate-500">Role</dt><dd className="mt-0.5">{ROLES[me.user.role]}</dd></div>
            <div className="col-span-2"><dt className="text-xs uppercase tracking-wide text-slate-500">Email</dt><dd className="mt-0.5 break-all">{me.user.email}</dd></div>
            {me.student && <div><dt className="text-xs uppercase tracking-wide text-slate-500">Year</dt><dd className="mt-0.5">{YEARS[me.student.year]} · {me.student.roll_no}</dd></div>}
            {me.faculty && <div><dt className="text-xs uppercase tracking-wide text-slate-500">Designation</dt><dd className="mt-0.5">{me.faculty.designation}</dd></div>}
          </dl>
        </Card>

        <Card>
          <CardHeader title="Change password" subtitle="Your other sessions stay signed in until their tokens expire." />
          <form onSubmit={submit} className="space-y-4 p-5">
            {error && <ErrorBanner message={error} />}
            {done && <p className="text-sm text-slate-600">Password updated. Use it the next time you sign in.</p>}
            <Field label="Current password">
              <Input type="password" autoComplete="current-password" required value={current} onChange={(e) => setCurrent(e.target.value)} />
            </Field>
            <Field label="New password">
              <Input type="password" autoComplete="new-password" required value={next} onChange={(e) => setNext(e.target.value)} aria-describedby="pw-rules" />
            </Field>
            <ul id="pw-rules" className="grid grid-cols-1 gap-1 text-xs sm:grid-cols-2">
              {RULES.map((r) => {
                const ok = r.test(next)
                return (
                  <li key={r.label} className={ok ? 'text-emerald-700 dark:text-emerald-400' : 'text-slate-500'}>
                    <span aria-hidden>{ok ? '✓' : '○'}</span> {r.label}
                  </li>
                )
              })}
            </ul>
            <Field label="Confirm new password" error={mismatch ? 'Passwords do not match' : undefined}>
              <Input type="password" autoComplete="new-password" required value={confirm} onChange={(e) => setConfirm(e.target.value)} />
            </Field>
            <div className="flex justify-end">
              <Button type="submit" loading={saving} disabled={unmet.length > 0 || !current || next !== confirm}>Change password</Button>
            </div>
          </form>
        </Card>
      </div>
    </>
  )
}
