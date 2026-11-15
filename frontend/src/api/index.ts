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
}

export const patientsApi = {
  list: (query: { q?: string; taluka?: Taluka | ''; limit?: number; offset?: number }) =>
    request<Page<PatientListItem>>('GET', '/patients', { query }),
  get: (id: number) => request<PatientDetail>('GET', `/patients/${id}`),
  create: (body: PatientInput) => request<PatientRead>('POST', '/patients', { body }),
  update: (id: number, body: Partial<PatientInput>) => request<PatientRead>('PATCH', `/patients/${id}`, { body }),
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
