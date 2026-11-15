// TypeScript mirrors of the backend Pydantic schemas (backend/app/schemas).

export type Role = 'admin' | 'faculty' | 'student'
export type StudentYear = 'bds1' | 'bds2' | 'bds3' | 'bds4' | 'intern'
export type Department =
  | 'oral_medicine'
  | 'conservative'
  | 'endodontics'
  | 'periodontics'
  | 'prosthodontics'
  | 'oral_surgery'
  | 'pedodontics'
  | 'orthodontics'
export type Sex = 'male' | 'female' | 'other'
export type Taluka =
  | 'pernem' | 'bardez' | 'tiswadi' | 'bicholim' | 'sattari' | 'ponda'
  | 'mormugao' | 'salcete' | 'quepem' | 'sanguem' | 'canacona' | 'dharbandora'
export type HabitStatus = 'never' | 'former' | 'current'
export type CaseStatus = 'draft' | 'submitted' | 'approved' | 'rejected'
export type ToothCondition =
  | 'sound' | 'caries' | 'missing' | 'filled' | 'rct' | 'crown'
  | 'mobility' | 'lesion' | 'fractured' | 'impacted' | 'extraction_indicated'
export type ExamType = 'internal' | 'sessional' | 'practical' | 'viva' | 'university'

export interface Page<T> {
  items: T[]
  total: number
  limit: number
  offset: number
}

export interface UserRead {
  id: number
  name: string
  email: string
  role: Role
}

export interface StudentRead {
  id: number
  user_id: number
  name: string
  email: string
  roll_no: string
  year: StudentYear
  batch: string
}

export interface FacultyRead {
  id: number
  user_id: number
  name: string
  email: string
  department: Department
  designation: string
}

export interface MeResponse {
  user: UserRead
  student: StudentRead | null
  faculty: FacultyRead | null
}

export interface TokenResponse extends MeResponse {
  access_token: string
  token_type: string
}

export interface PatientInput {
  abha_id?: string | null
  name: string
  age: number
  sex: Sex
  taluka: Taluka
  phone?: string | null
  tobacco_smoking: HabitStatus
  smokeless_tobacco: HabitStatus
  alcohol: HabitStatus
  habit_duration_years?: number | null
  has_diabetes: boolean
  has_hypertension: boolean
  has_cardiac_disease: boolean
  allergies?: string | null
  medical_history_notes?: string | null
}

export interface PatientRead extends PatientInput {
  id: number
  opd_number: string
  is_synthetic: boolean
  created_at: string
}

export interface PatientListItem {
  id: number
  opd_number: string
  abha_id: string | null
  name: string
  age: number
  sex: Sex
  taluka: Taluka
  phone: string | null
  tobacco_smoking: HabitStatus
  smokeless_tobacco: HabitStatus
  alcohol: HabitStatus
  last_visit: string | null
  visit_count: number
}

export interface VisitSummary {
  id: number
  visit_date: string
  department: Department
  chief_complaint: string
  diagnosis: string | null
  procedure: string | null
  status: CaseStatus
  student_name: string
  faculty_name: string
  findings_count: number
}

export interface PatientDetail extends PatientRead {
  visits: VisitSummary[]
}

export interface ToothFindingInput {
  tooth_number: number
  condition: ToothCondition
  surfaces?: string | null
  treatment?: string | null
  notes?: string | null
}

export interface ToothFindingRead extends ToothFindingInput {
  id: number
  case_id: number
}

export interface CaseInput {
  patient_id: number
  faculty_id: number
  department: Department
  visit_date: string
  chief_complaint: string
  diagnosis?: string | null
  procedure?: string | null
  findings: ToothFindingInput[]
}

export interface CaseRead {
  id: number
  patient_id: number
  patient_name: string
  patient_opd_number: string
  student_id: number
  student_name: string
  student_roll_no: string
  faculty_id: number
  faculty_name: string
  department: Department
  visit_date: string
  chief_complaint: string
  diagnosis: string | null
  procedure: string | null
  status: CaseStatus
  faculty_remarks: string | null
  submitted_at: string | null
  reviewed_at: string | null
  created_at: string
  updated_at: string
  findings: ToothFindingRead[]
}

export interface QuotaProgress {
  department: Department
  required: number
  approved: number
  pending: number
  remaining: number
  percent: number
}

export interface StudentQuotaProgress {
  student_id: number
  year: StudentYear
  is_clinical: boolean
  departments: QuotaProgress[]
  total_required: number
  total_approved: number
  overall_percent: number
}

export interface AttendanceSummary {
  student_id: number
  total_sessions: number
  present: number
  late: number
  absent: number
  excused: number
  percentage: number
  by_session: Record<string, number>
}

export interface AssessmentRead {
  id: number
  student_id: number
  subject: string
  exam_type: ExamType
  marks: number
  max_marks: number
  exam_date: string | null
  percentage: number
}

export interface AdminStats {
  students: number
  faculty: number
  patients: number
  cases: number
  cases_by_status: Record<CaseStatus, number>
}

// ---------------------------------------------------------------- Phase 2: analytics

export interface PopulationQuery {
  date_from?: string
  date_to?: string
  taluka?: Taluka | ''
  department?: Department | ''
}

export interface TalukaBurden {
  taluka: Taluka
  patients: number
  cases: number
  counts: Record<string, number>
  prevalence_pct: Record<string, number>
}

export interface HabitAssociation {
  habit: string
  habit_label: string
  outcome: string
  outcome_label: string
  exposed_n: number
  exposed_cases: number
  exposed_pct: number
  unexposed_n: number
  unexposed_cases: number
  unexposed_pct: number
  prevalence_ratio: number | null
  ci_low: number | null
  ci_high: number | null
}

export interface SexCell {
  patients: number
  caries: number
  pct: number
}

export interface CariesAgeSex {
  age_group: string
  male: SexCell
  female: SexCell
}

export interface TermCount {
  term: string
  count: number
  pct: number
}

export interface Insight {
  id: string
  tone: 'critical' | 'warning' | 'info'
  title: string
  text: string
  action: string
  evidence: Record<string, unknown>
}

export interface PopulationReport {
  summary: {
    patients: number
    cases: number
    pmd_patients: number
    caries_patients: number
    abha_linked_pct: number
    adult_current_tobacco_pct: number
  }
  taluka_burden: TalukaBurden[]
  habit_associations: HabitAssociation[]
  caries_by_age_sex: CariesAgeSex[]
  monthly_trend: ({ month: string; total: number } & Partial<Record<Department, number>>)[]
  top_terms: { diagnoses: TermCount[]; procedures: TermCount[] }
  insights: Insight[]
  condition_labels: Record<string, string>
}

// ---------------------------------------------------------------- Phase 2: oral cancer risk

export type RiskLevel = 'Low' | 'Medium' | 'High'

export interface RiskFactor {
  feature: string
  label: string
  value: number
  contribution: number
  odds_multiplier: number
  direction: 'increases' | 'decreases'
}

export interface RiskScreening {
  patient_id: number
  probability: number
  risk_percent: number
  risk_level: RiskLevel
  model_risk_level: RiskLevel
  baseline_probability: number
  factors: RiskFactor[]
  lesion_observed: boolean
  lesion_source: 'recorded' | 'override' | 'none'
  known_pmd_diagnosis: boolean
  suggested_action: string
  additional_actions: string[]
  notes: string[]
  model: { version: string; trained_at: string; auc_cv: number | null; n_train: number; thresholds: Record<string, number> }
  disclaimer: string
}

// ---------------------------------------------------------------- Phase 2: student intelligence

export interface AlertReason {
  code: string
  severity: 'critical' | 'warning'
  text: string
}

export interface StudentSignals {
  attendance_pct: number | null
  attendance_recent_pct: number | null
  attendance_prior_pct: number | null
  attendance_trend: number | null
  marks_avg: number | null
  marks_trend: number | null
  weakest_subject: string | null
  weakest_subject_pct: number | null
  is_clinical: boolean
  quota_percent: number | null
  cohort_median_percent: number | null
  pace_ratio: number | null
  quota_gaps: { department: Department; approved: number; required: number; remaining: number; percent: number }[]
  reviewed_cases: number
  rejected_cases: number
  rejection_rate: number | null
}

export interface StudentAlert {
  student_id: number
  name: string
  roll_no: string
  year: StudentYear
  risk_level: RiskLevel
  score: number | null
  reasons: AlertReason[]
  suggested_actions: string[]
  model_factors: { feature: string; label: string; contribution: number; z_score: number; direction: 'raises' | 'lowers' }[]
  signals: StudentSignals
  weekly_attendance: { weeks_ago: number; pct: number | null }[]
}

export interface FocusAreas {
  student_id: number
  on_track: boolean
  items: { area: string; title: string; message: string }[]
  strengths: string[]
  summary: string
}

// ---------------------------------------------------------------- Phase 2: allocation

export interface AllocationCandidate {
  student_id: number
  name: string
  roll_no: string
  year: StudentYear
  score: number
  components: Record<'quota_gap' | 'workload' | 'pace' | 'seniority', number>
  approved: number
  required: number
  remaining: number
  pending: number
  open_cases: number
  recent_attendance_pct: number | null
  available: boolean
  reasons: string[]
}

export interface AllocationRecommendation {
  patient_id: number
  patient_name: string
  department: Department
  eligible_count: number
  eligible_years: StudentYear[]
  candidates: AllocationCandidate[]
  weights: Record<string, number>
  warnings: string[]
}

export type LoadStatus = 'overloaded' | 'short_supply' | 'balanced' | 'spare_capacity'

export interface DepartmentLoad {
  department: Department
  faculty: number
  cases: number
  cases_per_faculty: number | null
  pending_reviews: number
  pending_per_faculty: number | null
  eligible_students: number
  quota_remaining: number
  weeks_to_clear_quota: number | null
  load_index: number | null
  status: LoadStatus
  reasons: string[]
}

export interface ResourceView {
  days: number
  mean_cases_per_faculty: number
  departments: DepartmentLoad[]
}

// ---------------------------------------------------------------- Phase 2: learning plan

export interface SubjectPerformance {
  subject: string
  average_pct: number
  latest_pct: number
  trend: number | null
  exams: number
  related_department: Department | null
  tip: string
}

export interface LearningPlan {
  student_id: number
  year: StudentYear
  is_clinical: boolean
  summary: string
  focus_departments: {
    department: Department
    approved: number
    required: number
    remaining: number
    pending: number
    percent: number
    case_types: string[]
    where_to_find: string
    double_priority: boolean
  }[]
  focus_subjects: SubjectPerformance[]
  all_subjects: SubjectPerformance[]
}

// ---------------------------------------------------------------- Phase 2: attendance + marks entry

export type AttendanceSessionType = 'theory' | 'practical' | 'clinic'
export type AttendanceStatus = 'present' | 'absent' | 'late' | 'excused'

export interface AttendanceRead {
  id: number
  student_id: number
  date: string
  session: AttendanceSessionType
  status: AttendanceStatus
}
