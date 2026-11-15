import { useState, type ReactNode } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { casesApi } from '../../api'
import { useAuth } from '../../auth/AuthContext'
import { FindingsTable, ToothChart } from '../../components/ToothChart'
import { Button, Card, CardHeader, ErrorBanner, PageHeader, Spinner, StatusBadge } from '../../components/ui'
import { formatDate } from '../../lib/format'
import { DEPARTMENTS } from '../../lib/labels'
import { useApi } from '../../lib/useApi'
import { ReviewPanel } from './ReviewPanel'

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="grid grid-cols-1 gap-1 py-3 sm:grid-cols-4 sm:gap-4">
      <dt className="text-sm font-medium text-slate-500">{label}</dt>
      <dd className="text-sm text-slate-900 sm:col-span-3">{children || '—'}</dd>
    </div>
  )
}

export function CaseDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { me } = useAuth()
  const { data: c, error, loading, reload, setData } = useApi(() => casesApi.get(Number(id)), [id])
  const [actionError, setActionError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  if (loading && !c) return <Spinner />
  if (error) return <ErrorBanner message={error} onRetry={reload} />
  if (!c) return null

  const isOwner = me?.student?.id === c.student_id
  const editable = isOwner && (c.status === 'draft' || c.status === 'rejected')
  const canReview = me?.faculty?.id === c.faculty_id && c.status === 'submitted'

  async function run(action: () => Promise<unknown>) {
    setBusy(true)
    setActionError(null)
    try {
      await action()
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Action failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <PageHeader
        title={
          <span className="flex flex-wrap items-center gap-3">
            Case #{c.id} <StatusBadge status={c.status} />
          </span>
        }
        subtitle={`${DEPARTMENTS[c.department]} · ${formatDate(c.visit_date)}`}
        actions={
          editable && (
            <>
              {c.status === 'draft' && (
                <Button variant="ghost" className="text-rose-600 hover:bg-rose-50" disabled={busy}
                  onClick={() => window.confirm('Delete this draft case?') && run(async () => { await casesApi.remove(c.id); navigate('/my-cases') })}>
                  Delete draft
                </Button>
              )}
              <Link to={`/cases/${c.id}/edit`} className="inline-flex items-center rounded-lg bg-white px-4 py-2 text-sm font-medium text-slate-700 ring-1 ring-inset ring-slate-300 hover:bg-slate-50">
                Edit
              </Link>
              <Button
                loading={busy}
                onClick={() =>
                  run(async () => {
                    const updated = await casesApi.submit(c.id)
                    setData(() => updated)
                  })
                }
              >
                Submit for approval
              </Button>
            </>
          )
        }
      />

      {actionError && <div className="mb-4"><ErrorBanner message={actionError} /></div>}

      {c.faculty_remarks && (
        <div className={`mb-6 rounded-lg px-4 py-3 text-sm ring-1 ${c.status === 'rejected' ? 'bg-rose-50 text-rose-800 ring-rose-200' : 'bg-emerald-50 text-emerald-800 ring-emerald-200'}`}>
          <span className="font-semibold">Faculty remarks:</span> {c.faculty_remarks}
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader title="Clinical record" />
          <dl className="divide-y divide-slate-100 px-5">
            <Row label="Patient">
              <Link to={`/patients/${c.patient_id}`} className="font-medium text-brand-700 hover:underline">{c.patient_name}</Link>{' '}
              <span className="text-slate-500">· {c.patient_opd_number}</span>
            </Row>
            <Row label="Chief complaint">{c.chief_complaint}</Row>
            <Row label="Diagnosis">{c.diagnosis}</Row>
            <Row label="Procedure">{c.procedure}</Row>
          </dl>
        </Card>

        <Card>
          <CardHeader title="Supervision" />
          <dl className="divide-y divide-slate-100 px-5">
            <Row label="Student">{c.student_name} <span className="text-slate-500">· {c.student_roll_no}</span></Row>
            <Row label="Faculty">{c.faculty_name}</Row>
            <Row label="Submitted">{formatDate(c.submitted_at)}</Row>
            <Row label="Reviewed">{formatDate(c.reviewed_at)}</Row>
          </dl>
          {canReview && (
            <div className="border-t border-slate-100 p-5">
              <p className="mb-2 text-sm font-semibold text-slate-900">Your review</p>
              <ReviewPanel caseItem={c} onDone={(updated) => setData(() => updated)} />
            </div>
          )}
        </Card>

        <Card className="lg:col-span-3">
          <CardHeader title="Tooth chart (FDI)" subtitle={`${c.findings.length} finding${c.findings.length === 1 ? '' : 's'}`} />
          <div className="space-y-6 p-5">
            <ToothChart findings={c.findings} readOnly />
            <FindingsTable findings={c.findings} />
          </div>
        </Card>
      </div>
    </>
  )
}
