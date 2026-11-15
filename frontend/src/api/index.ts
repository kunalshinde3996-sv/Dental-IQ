// Typed API functions, grouped by resource. Mirrors backend/app/routers.
import { request } from './client'
import type {
  AdminStats,
  AssessmentRead,
  AttendanceSummary,
  CaseInput,
  CaseRead,
  CaseStatus,
  Department,
  FacultyRead,
  MeResponse,
  Page,
  PatientDetail,
  PatientInput,
  PatientListItem,
  PatientRead,
  PopulationQuery,
  PopulationReport,
  RiskScreening,
  StudentAlert,
  FocusAreas,
  LearningPlan,
  AttendanceRead,
  AttendanceSessionType,
  AttendanceStatus,
  ExamType,
  AuditEvent,
  AppNotification,
  AllocationRecommendation,
  ResourceView,
  StudentQuotaProgress,
  StudentRead,
  StudentYear,
  Taluka,
  TokenResponse,
} from './types'

export const authApi = {
  login: (email: string, password: string) =>
    request<TokenResponse>('POST', '/auth/login', { body: { email, password } }),
  me: () => request<MeResponse>('GET', '/auth/me'),
  logout: () => request<void>('POST', '/auth/logout'),
  changePassword: (current_password: string, new_password: string) =>
    request<void>('POST', '/auth/change-password', { body: { current_password, new_password } }),
}

export const patientsApi = {
  list: (query: { q?: string; taluka?: Taluka | ''; limit?: number; offset?: number }) =>
    request<Page<PatientListItem>>('GET', '/patients', { query }),
  get: (id: number) => request<PatientDetail>('GET', `/patients/${id}`),
  create: (body: PatientInput) => request<PatientRead>('POST', '/patients', { body }),
  update: (id: number, body: Partial<PatientInput>) => request<PatientRead>('PATCH', `/patients/${id}`, { body }),
  fhirBundle: (id: number) => request<Record<string, unknown>>('GET', `/patients/${id}/fhir`),
  riskScreening: (id: number, lesionObserved?: boolean) =>
    request<RiskScreening>('POST', `/patients/${id}/risk-screening`, {
      body: { lesion_observed: lesionObserved ?? null },
    }),
}

export const casesApi = {
  list: (query: { status?: CaseStatus | ''; department?: Department | ''; limit?: number; offset?: number }) =>
    request<Page<CaseRead>>('GET', '/cases', { query }),
  get: (id: number) => request<CaseRead>('GET', `/cases/${id}`),
  create: (body: CaseInput & { submit: boolean }) => request<CaseRead>('POST', '/cases', { body }),
  update: (id: number, body: Partial<CaseInput>) => request<CaseRead>('PATCH', `/cases/${id}`, { body }),
  submit: (id: number) => request<CaseRead>('POST', `/cases/${id}/submit`),
  review: (id: number, decision: 'approve' | 'reject', remarks: string) =>
    request<CaseRead>('POST', `/cases/${id}/review`, { body: { decision, remarks: remarks || null } }),
  remove: (id: number) => request<void>('DELETE', `/cases/${id}`),
}

export const studentsApi = {
  list: (query: { year?: StudentYear | ''; q?: string } = {}) =>
    request<StudentRead[]>('GET', '/students', { query }),
  quotaProgress: (id: number) => request<StudentQuotaProgress>('GET', `/students/${id}/quota-progress`),
  attendanceSummary: (id: number) => request<AttendanceSummary>('GET', `/students/${id}/attendance-summary`),
}

export const facultyApi = {
  list: (department?: Department) => request<FacultyRead[]>('GET', '/faculty', { query: { department } }),
  pending: (limit = 100) => request<Page<CaseRead>>('GET', '/faculty/me/pending-cases', { query: { limit } }),
  reviewed: (limit = 20) => request<Page<CaseRead>>('GET', '/faculty/me/reviewed-cases', { query: { limit } }),
}

export const academicApi = {
  assessments: (studentId?: number) =>
    request<AssessmentRead[]>('GET', '/assessments', { query: { student_id: studentId } }),
}

export const adminApi = {
  stats: () => request<AdminStats>('GET', '/admin/stats'),
}

export const analyticsApi = {
  population: (query: PopulationQuery) => request<PopulationReport>('GET', '/analytics/population', { query: { ...query } }),
}

export const intelligenceApi = {
  alerts: () => request<StudentAlert[]>('GET', '/alerts/students'),
  focusAreas: (studentId: number) => request<FocusAreas>('GET', `/students/${studentId}/focus-areas`),
  learningPlan: (studentId: number) => request<LearningPlan>('GET', `/students/${studentId}/learning-plan`),
}

export const allocationApi = {
  recommend: (patientId: number, department: Department) =>
    request<AllocationRecommendation>('GET', '/allocation/recommendations', { query: { patient_id: patientId, department } }),
  assign: (body: { patient_id: number; department: Department; student_id: number; chief_complaint: string }) =>
    request<CaseRead>('POST', '/allocation/assign', { body }),
  resources: (days: number) => request<ResourceView>('GET', '/allocation/resources', { query: { days } }),
}

export const attendanceApi = {
  list: (query: { date_from?: string; date_to?: string; session?: AttendanceSessionType; student_id?: number }) =>
    request<AttendanceRead[]>('GET', '/attendance', { query: { ...query, limit: 5000 } }),
  bulk: (body: { date: string; session: AttendanceSessionType; entries: { student_id: number; status: AttendanceStatus }[] }) =>
    request<AttendanceRead[]>('POST', '/attendance/bulk', { body }),
}

export const marksApi = {
  subjects: (year?: StudentYear) => request<string[]>('GET', '/assessments/subjects', { query: { year } }),
  list: (query: { subject?: string; exam_type?: ExamType }) =>
    request<AssessmentRead[]>('GET', '/assessments', { query: { ...query, limit: 5000 } }),
  bulk: (body: { subject: string; exam_type: ExamType; max_marks: number; exam_date: string; entries: { student_id: number; marks: number }[] }) =>
    request<AssessmentRead[]>('POST', '/assessments/bulk', { body }),
}

export const auditApi = {
  list: (query: { action?: string; entity_type?: string; entity_id?: number | ''; q?: string; date_from?: string; date_to?: string; limit?: number; offset?: number }) =>
    request<Page<AuditEvent>>('GET', '/audit', { query }),
  facets: () => request<{ actions: string[]; entity_types: string[] }>('GET', '/audit/facets'),
}

export const notificationsApi = {
  list: (unreadOnly = false) => request<AppNotification[]>('GET', '/notifications', { query: { unread_only: unreadOnly, limit: 30 } }),
  unreadCount: () => request<{ unread: number }>('GET', '/notifications/unread-count'),
  markRead: (id: number) => request<AppNotification>('POST', `/notifications/${id}/read`),
  markAllRead: () => request<{ unread: number }>('POST', '/notifications/read-all'),
}
