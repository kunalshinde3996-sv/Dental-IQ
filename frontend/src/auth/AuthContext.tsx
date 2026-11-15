import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { authApi } from '../api'
import { getToken, setToken, setUnauthorizedHandler } from '../api/client'
import type { MeResponse, Role } from '../api/types'

/** Why the last session ended (shown on the login page). */
export type EndReason = 'expired' | 'signed_out' | null

interface AuthState {
  me: MeResponse | null
  /** True while restoring a session from a stored token. */
  initialising: boolean
  endReason: EndReason
  login: (email: string, password: string) => Promise<MeResponse>
  logout: () => void
}

const AuthContext = createContext<AuthState | null>(null)

export const HOME_BY_ROLE: Record<Role, string> = {
  student: '/my-cases',
  faculty: '/approvals',
  admin: '/admin',
}

/** Read the `exp` claim (ms epoch) without verifying: the server still verifies every request. */
function tokenExpiry(token: string | null): number | null {
  try {
    const payload = JSON.parse(atob(token!.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')))
    return typeof payload.exp === 'number' ? payload.exp * 1000 : null
  } catch {
    return null
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<MeResponse | null>(null)
  const [initialising, setInitialising] = useState(() => Boolean(getToken()))
  const [endReason, setEndReason] = useState<EndReason>(null)
  const expiryTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const clearSession = useCallback((reason: EndReason) => {
    if (expiryTimer.current) clearTimeout(expiryTimer.current)
    setToken(null)
    setMe(null)
    setEndReason(reason)
  }, [])

  /** Log out at the token's expiry time, so the UI never shows stale data after it lapses. */
  const scheduleExpiry = useCallback((token: string) => {
    if (expiryTimer.current) clearTimeout(expiryTimer.current)
    const exp = tokenExpiry(token)
    if (exp === null) return
    const ms = exp - Date.now()
    if (ms <= 0) clearSession('expired')
    else expiryTimer.current = setTimeout(() => clearSession('expired'), Math.min(ms, 2 ** 31 - 1))
  }, [clearSession])

  const logout = useCallback(() => {
    // Revoke on the server (best effort), then clear locally either way.
    if (getToken()) authApi.logout().catch(() => undefined)
    clearSession('signed_out')
  }, [clearSession])

  useEffect(() => {
    setUnauthorizedHandler(() => clearSession('expired'))
    return () => setUnauthorizedHandler(null)
  }, [clearSession])

  // Restore session on first load.
  useEffect(() => {
    const token = getToken()
    if (!token) return
    authApi
      .me()
      .then((profile) => {
        setMe(profile)
        scheduleExpiry(token)
      })
      .catch(() => setToken(null))
      .finally(() => setInitialising(false))
  }, [scheduleExpiry])

  const login = useCallback(async (email: string, password: string) => {
    const res = await authApi.login(email, password)
    setToken(res.access_token)
    scheduleExpiry(res.access_token)
    const profile: MeResponse = { user: res.user, student: res.student, faculty: res.faculty }
    setEndReason(null)
    setMe(profile)
    return profile
  }, [scheduleExpiry])

  const value = useMemo(() => ({ me, initialising, endReason, login, logout }), [me, initialising, endReason, login, logout])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
