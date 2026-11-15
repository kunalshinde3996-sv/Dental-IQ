// Minimal fetch wrapper: base URL, bearer token, JSON, and normalised errors.

const BASE_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? '/api'
const TOKEN_KEY = 'dentaliq.token'
// Generous enough to ride out a free-tier host cold start (first request after idle can take ~60s).
const REQUEST_TIMEOUT_MS = 90_000
const WAKING_MESSAGE = 'Waking up the server, this can take up to a minute on first load. Please retry in a moment.'

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function setToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    /* storage unavailable (private mode) - session will not persist */
  }
}

/** Error thrown for non-2xx responses. `fieldErrors` maps field name -> message for 422s. */
export class ApiError extends Error {
  status: number
  fieldErrors: Record<string, string>

  constructor(status: number, message: string, fieldErrors: Record<string, string> = {}) {
    super(message)
    this.status = status
    this.fieldErrors = fieldErrors
  }
}

let onUnauthorized: (() => void) | null = null
/** Registered by AuthProvider so an expired token logs the user out everywhere. */
export function setUnauthorizedHandler(handler: (() => void) | null): void {
  onUnauthorized = handler
}

interface ValidationIssue {
  loc: (string | number)[]
  msg: string
}

function parseError(status: number, body: unknown): ApiError {
  const detail = (body as { detail?: unknown } | null)?.detail
  if (typeof detail === 'string') return new ApiError(status, detail)
  if (Array.isArray(detail)) {
    const fieldErrors: Record<string, string> = {}
    const messages: string[] = []
    for (const issue of detail as ValidationIssue[]) {
      const field = issue.loc.filter((p) => p !== 'body').join('.')
      const msg = issue.msg.replace(/^Value error, /, '')
      if (field) fieldErrors[field] = msg
      messages.push(field ? `${field}: ${msg}` : msg)
    }
    return new ApiError(status, messages.join('; ') || 'Validation failed', fieldErrors)
  }
  return new ApiError(status, `Request failed (${status})`)
}

type Query = Record<string, string | number | boolean | null | undefined>

export async function request<T>(
  method: string,
  path: string,
  options: { body?: unknown; query?: Query } = {},
): Promise<T> {
  const url = new URL(BASE_URL + path, window.location.origin)
  for (const [key, value] of Object.entries(options.query ?? {})) {
    if (value !== undefined && value !== null && value !== '') url.searchParams.set(key, String(value))
  }

  const headers: Record<string, string> = { Accept: 'application/json' }
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  if (options.body !== undefined) headers['Content-Type'] = 'application/json'

  // Never leave the UI spinning forever on a stuck connection.
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)
  let res: Response
  try {
    res = await fetch(url, {
      method,
      headers,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
      signal: controller.signal,
    })
  } catch {
    // Timeouts and dropped connections are almost always the backend spinning up from idle.
    throw new ApiError(0, WAKING_MESSAGE)
  } finally {
    clearTimeout(timer)
  }

  if (res.status === 204) return undefined as T
  const body: unknown = await res.json().catch(() => null)
  if (!res.ok) {
    if (res.status === 401 && token) onUnauthorized?.()
    // The hosting proxy answers 502/503/504 while the backend is still booting.
    if ((res.status === 502 || res.status === 503 || res.status === 504) && typeof (body as { detail?: unknown } | null)?.detail !== 'string') {
      throw new ApiError(res.status, WAKING_MESSAGE)
    }
    throw parseError(res.status, body)
  }
  return body as T
}
