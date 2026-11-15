import { useState, type FormEvent } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { HOME_BY_ROLE, useAuth } from '../auth/AuthContext'
import { Logo } from '../components/AppLayout'
import { Button, ErrorBanner, Field, Input } from '../components/ui'

// Demo accounts created by `python -m scripts.seed` (synthetic data only).
const DEMO_ACCOUNTS = [
  { label: 'Student', email: 'student@gdch.demo', password: 'Student@123' },
  { label: 'At-risk student', email: 'atrisk.student@gdch.demo', password: 'Student@123' },
  { label: 'Faculty', email: 'faculty@gdch.demo', password: 'Faculty@123' },
  { label: 'Admin', email: 'admin@gdch.demo', password: 'Admin@123' },
]

export function LoginPage() {
  const { me, login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  if (me) return <Navigate to={HOME_BY_ROLE[me.user.role]} replace />

  async function doLogin(e: string, p: string) {
    setLoading(true)
    setError(null)
    try {
      const profile = await login(e, p)
      const from = (location.state as { from?: string } | null)?.from
      navigate(from && from !== '/login' ? from : HOME_BY_ROLE[profile.user.role], { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    void doLogin(email, password)
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="relative hidden flex-col justify-between overflow-hidden bg-gradient-to-br from-brand-800 via-brand-700 to-sky-700 p-12 text-white lg:flex">
        <Logo />
        <div className="max-w-md">
          <h1 className="text-3xl font-semibold leading-tight">One clinical case. Three outcomes.</h1>
          <p className="mt-4 text-brand-100">
            Every supervised case updates the patient&apos;s dental record, the student&apos;s competency log and
            Goa&apos;s oral-health picture, all from a single entry.
          </p>
          <ul className="mt-8 space-y-3 text-sm text-brand-50">
            {['FDI tooth charting with ABHA-ready patient records', 'Tobacco, gutkha & alcohol risk capture by taluka', 'Clinical quota tracking & faculty approvals'].map((t) => (
              <li key={t} className="flex items-center gap-3">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-white/20 text-xs">✓</span>
                {t}
              </li>
            ))}
          </ul>
        </div>
        <p className="text-xs text-brand-200">Goa Dental College &amp; Hospital · Hackathon prototype · Synthetic demo data</p>
      </div>

      <div className="flex items-center justify-center bg-slate-50 px-4 py-12">
        <div className="w-full max-w-sm">
          <Logo className="mb-8 lg:hidden" />
          <h2 className="text-2xl font-semibold text-slate-900">Sign in</h2>
          <p className="mt-1 text-sm text-slate-500">Use your college account.</p>

          <form onSubmit={onSubmit} className="mt-6 space-y-4">
            {error && <ErrorBanner message={error} />}
            <Field label="Email">
              <Input type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@gdch.demo" />
            </Field>
            <Field label="Password">
              <Input type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
            </Field>
            <Button type="submit" className="w-full" loading={loading}>
              Sign in
            </Button>
          </form>

          <div className="mt-8">
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-400">Demo accounts</p>
            <div className="grid grid-cols-2 gap-2">
              {DEMO_ACCOUNTS.map((a) => (
                <button
                  key={a.email}
                  type="button"
                  disabled={loading}
                  onClick={() => {
                    setEmail(a.email)
                    setPassword(a.password)
                    void doLogin(a.email, a.password)
                  }}
                  className="rounded-lg bg-white px-3 py-2 text-left text-sm ring-1 ring-slate-200 transition hover:ring-brand-400 disabled:opacity-60"
                >
                  <span className="block font-medium text-slate-800">{a.label}</span>
                  <span className="block truncate text-xs text-slate-500">{a.email}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
