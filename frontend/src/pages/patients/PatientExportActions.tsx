import { useState } from 'react'
import { Link } from 'react-router-dom'
import { patientsApi } from '../../api'
import { Button } from '../../components/ui'
import { downloadJson } from '../../lib/download'

/** "Export FHIR" (R4 Bundle JSON download) and "Print summary" actions for a patient. */
export function PatientExportActions({ patientId, opdNumber }: { patientId: number; opdNumber: string }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function exportFhir() {
    setBusy(true)
    setError(null)
    try {
      const bundle = await patientsApi.fhirBundle(patientId)
      downloadJson(bundle, `${opdNumber}-fhir-bundle.json`, 'application/fhir+json')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Export failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <Link to={`/patients/${patientId}/print`} className="inline-flex items-center rounded-lg bg-white px-4 py-2 text-sm font-medium text-slate-700 ring-1 ring-inset ring-slate-300 hover:bg-slate-50 dark:bg-slate-800 dark:text-slate-200 dark:ring-slate-600 dark:hover:bg-slate-700">
        Print summary
      </Link>
      <Button variant="secondary" loading={busy} onClick={exportFhir} title="Download a FHIR R4 Bundle (Patient, Encounter, Condition, Procedure, RiskAssessment)">
        Export FHIR
      </Button>
      {error && <span role="alert" className="self-center text-xs text-rose-600">{error}</span>}
    </>
  )
}
