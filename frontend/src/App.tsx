import { BrowserRouter, Link, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, HOME_BY_ROLE, useAuth } from './auth/AuthContext'
import { RequireAuth } from './auth/RequireAuth'
import { AppLayout } from './components/AppLayout'
import { AdminFacultyPage, AdminOverviewPage, AdminStudentsPage } from './pages/admin/AdminPages'
import { CaseDetailPage } from './pages/cases/CaseDetailPage'
import { CaseFormPage } from './pages/cases/CaseFormPage'
import { ApprovalsPage } from './pages/faculty/ApprovalsPage'
import { LoginPage } from './pages/LoginPage'
import { PatientFormPage } from './pages/patients/PatientFormPage'
import { PatientProfilePage } from './pages/patients/PatientProfilePage'
import { PatientsListPage } from './pages/patients/PatientsListPage'
import { MyCasesPage } from './pages/student/MyCasesPage'

function HomeRedirect() {
  const { me } = useAuth()
  return <Navigate to={me ? HOME_BY_ROLE[me.user.role] : '/login'} replace />
}

function NotFound() {
  return (
    <div className="py-20 text-center">
      <p className="text-5xl font-semibold text-brand-600">404</p>
      <p className="mt-2 text-slate-600">This page does not exist.</p>
      <Link to="/" className="mt-4 inline-block text-sm font-medium text-brand-700 hover:underline">Go home</Link>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<RequireAuth><AppLayout /></RequireAuth>}>
            <Route index element={<HomeRedirect />} />

            {/* Shared by all roles */}
            <Route path="patients" element={<PatientsListPage />} />
            <Route path="patients/new" element={<PatientFormPage />} />
            <Route path="patients/:id" element={<PatientProfilePage />} />
            <Route path="patients/:id/edit" element={<PatientFormPage />} />
            <Route path="cases/:id" element={<CaseDetailPage />} />

            {/* Student */}
            <Route path="my-cases" element={<RequireAuth roles={['student']}><MyCasesPage /></RequireAuth>} />
            <Route path="cases/new" element={<RequireAuth roles={['student']}><CaseFormPage /></RequireAuth>} />
            <Route path="cases/:id/edit" element={<RequireAuth roles={['student']}><CaseFormPage /></RequireAuth>} />

            {/* Faculty */}
            <Route path="approvals" element={<RequireAuth roles={['faculty']}><ApprovalsPage /></RequireAuth>} />

            {/* Admin */}
            <Route path="admin" element={<RequireAuth roles={['admin']}><AdminOverviewPage /></RequireAuth>} />
            <Route path="admin/students" element={<RequireAuth roles={['admin']}><AdminStudentsPage /></RequireAuth>} />
            <Route path="admin/faculty" element={<RequireAuth roles={['admin']}><AdminFacultyPage /></RequireAuth>} />

            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
