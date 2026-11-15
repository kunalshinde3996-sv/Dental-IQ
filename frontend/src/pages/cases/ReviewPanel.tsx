import { useState } from 'react'
import { casesApi } from '../../api'
import type { CaseRead } from '../../api/types'
import { Button, ErrorBanner, Textarea } from '../../components/ui'

/** Approve / reject controls for the supervising faculty. Remarks are required to reject. */
export function ReviewPanel({ caseItem, onDone }: { caseItem: CaseRead; onDone: (updated: CaseRead) => void }) {
  const [remarks, setRemarks] = useState('')
  const [busy, setBusy] = useState<'approve' | 'reject' | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function review(decision: 'approve' | 'reject') {
    if (decision === 'reject' && !remarks.trim()) {
      setError('Add remarks so the student knows what to fix.')
      return
    }
    setBusy(decision)
    setError(null)
    try {
      onDone(await casesApi.review(caseItem.id, decision, remarks.trim()))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Review failed')
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="space-y-3">
      {error && <ErrorBanner message={error} />}
      <Textarea
        value={remarks}
        maxLength={1000}
        onChange={(e) => setRemarks(e.target.value)}
        placeholder="Remarks for the student (required when rejecting)"
        aria-label="Faculty remarks"
      />
      <div className="flex flex-wrap justify-end gap-2">
        <Button variant="danger" loading={busy === 'reject'} disabled={busy !== null} onClick={() => review('reject')}>
          Reject
        </Button>
        <Button variant="success" loading={busy === 'approve'} disabled={busy !== null} onClick={() => review('approve')}>
          Approve
        </Button>
      </div>
    </div>
  )
}
