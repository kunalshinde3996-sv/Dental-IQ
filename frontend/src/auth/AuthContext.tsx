import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { authApi } from '../api'
import { getToken, setToken, setUnauthorizedHandler } from '../api/client'
import type { MeResponse, Role } from '../api/types'

interface AuthState {
  me: MeResponse | null
  /** True while restoring a session from a stored token. */
  initialising: boolean
  login: (email: string, password: string) => Promise<MeResponse>
  logout: () => void
}

const AuthContext = createContext<AuthState | null>(null)

export const HOME_BY_ROLE: Record<Role, string> = {
  student: '/my-cases',
  faculty: '/approvals',
  admin: '/admin',
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<MeResponse | null>(null)
  const [initialising, setInitialising] = useState(() => Boolean(getToken()))

  const logout = useCallback(() => {
    setToken(null)
    setMe(null)
  }, [])

  useEffect(() => {
    setUnauthorizedHandler(logout)
    return () => setUnauthorizedHandler(null)
  }, [logout])

  // Restore session on first load.
  useEffect(() => {
    if (!getToken()) return
    authApi
      .me()
      .then(setMe)
      .catch(() => setToken(null))
      .finally(() => setInitialising(false))
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const res = await authApi.login(email, password)
    setToken(res.access_token)
    const profile: MeResponse = { user: res.user, student: res.student, faculty: res.faculty }
    setMe(profile)
    return profile
  }, [])

  const value = useMemo(() => ({ me, initialising, login, logout }), [me, initialising, login, logout])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
