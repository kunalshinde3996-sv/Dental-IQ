// Display labels and colours for backend enum values (single source for the UI).
import type {
  CaseStatus,
  Department,
  HabitStatus,
  Role,
  Sex,
  StudentYear,
  Taluka,
  ToothCondition,
} from '../api/types'

export const DEPARTMENTS: Record<Department, string> = {
  oral_medicine: 'Oral Medicine & Radiology',
  conservative: 'Conservative Dentistry',
  endodontics: 'Endodontics',
  periodontics: 'Periodontics',
  prosthodontics: 'Prosthodontics',
  oral_surgery: 'Oral & Maxillofacial Surgery',
  pedodontics: 'Pedodontics',
  orthodontics: 'Orthodontics',
}

export const DEPARTMENT_SHORT: Record<Department, string> = {
  oral_medicine: 'Oral Med',
  conservative: 'Conservative',
  endodontics: 'Endo',
  periodontics: 'Perio',
  prosthodontics: 'Prostho',
  oral_surgery: 'Oral Surgery',
  pedodontics: 'Pedo',
  orthodontics: 'Ortho',
}

export const TALUKAS: Record<Taluka, string> = {
  pernem: 'Pernem',
  bardez: 'Bardez',
  tiswadi: 'Tiswadi',
  bicholim: 'Bicholim',
  sattari: 'Sattari',
  ponda: 'Ponda',
  mormugao: 'Mormugao',
  salcete: 'Salcete',
  quepem: 'Quepem',
  sanguem: 'Sanguem',
  canacona: 'Canacona',
  dharbandora: 'Dharbandora',
}

export const YEARS: Record<StudentYear, string> = {
  bds1: 'BDS I',
  bds2: 'BDS II',
  bds3: 'BDS III',
  bds4: 'BDS IV',
  intern: 'Intern',
}

export const SEXES: Record<Sex, string> = { male: 'Male', female: 'Female', other: 'Other' }

export const ROLES: Record<Role, string> = { admin: 'Admin', faculty: 'Faculty', student: 'Student' }

export const HABITS: Record<HabitStatus, string> = { never: 'Never', former: 'Former', current: 'Current' }

export const CASE_STATUS: Record<CaseStatus, { label: string; className: string }> = {
  draft: { label: 'Draft', className: 'bg-slate-100 text-slate-700 ring-slate-200' },
  submitted: { label: 'Pending review', className: 'bg-amber-50 text-amber-800 ring-amber-200' },
  approved: { label: 'Approved', className: 'bg-emerald-50 text-emerald-700 ring-emerald-200' },
  rejected: { label: 'Rejected', className: 'bg-rose-50 text-rose-700 ring-rose-200' },
}

/** Tooth-chart colours. `fill` is used in the SVG; `swatch` for legends/badges. */
export const TOOTH_CONDITIONS: Record<ToothCondition, { label: string; fill: string; swatch: string }> = {
  sound: { label: 'Sound', fill: '#d1fae5', swatch: 'bg-emerald-200' },
  caries: { label: 'Caries', fill: '#f87171', swatch: 'bg-red-400' },
  filled: { label: 'Filled', fill: '#60a5fa', swatch: 'bg-blue-400' },
  rct: { label: 'RCT', fill: '#a78bfa', swatch: 'bg-violet-400' },
  crown: { label: 'Crown', fill: '#fbbf24', swatch: 'bg-amber-400' },
  missing: { label: 'Missing', fill: '#e2e8f0', swatch: 'bg-slate-200' },
  mobility: { label: 'Mobility', fill: '#fb923c', swatch: 'bg-orange-400' },
  lesion: { label: 'Lesion', fill: '#f472b6', swatch: 'bg-pink-400' },
  fractured: { label: 'Fractured', fill: '#c2410c', swatch: 'bg-orange-700' },
  impacted: { label: 'Impacted', fill: '#64748b', swatch: 'bg-slate-500' },
  extraction_indicated: { label: 'Extraction indicated', fill: '#991b1b', swatch: 'bg-red-800' },
}

export const SURFACES: { code: string; label: string }[] = [
  { code: 'M', label: 'Mesial' },
  { code: 'O', label: 'Occlusal' },
  { code: 'D', label: 'Distal' },
  { code: 'B', label: 'Buccal' },
  { code: 'L', label: 'Lingual' },
  { code: 'I', label: 'Incisal' },
  { code: 'F', label: 'Facial' },
]

export function entries<K extends string>(record: Record<K, unknown>): K[] {
  return Object.keys(record) as K[]
}
