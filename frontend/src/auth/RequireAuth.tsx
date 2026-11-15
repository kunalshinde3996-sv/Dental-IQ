import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import type { Role } from '../api/types'
import { Spinner } from '../components/ui'
import { HOME_BY_ROLE, useAuth } from './AuthContext'

/** Gate a route on login and (optionally) on role. Wrong role -> that role's home page. */
export function RequireAuth({ roles, children }: { roles?: Role[]; children: ReactNode }) {
  const { me, initialising } = useAuth()
  const location = useLocation()

  if (initialising) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner label="Restoring session…" />
      </div>
    )
  }
  if (!me) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  if (roles && !roles.includes(me.user.role)) return <Navigate to={HOME_BY_ROLE[me.user.role]} replace />
  return <>{children}</>
}
