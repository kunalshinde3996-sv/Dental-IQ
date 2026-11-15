import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from 'react'

type Tone = 'success' | 'error' | 'info'
interface Toast {
  id: number
  tone: Tone
  message: string
}

interface ToastApi {
  success: (message: string) => void
  error: (message: string) => void
  info: (message: string) => void
}

const ToastContext = createContext<ToastApi | null>(null)
const DURATION_MS = 4500
const STYLE: Record<Tone, { className: string; icon: string; label: string }> = {
  success: { className: 'bg-emerald-600', icon: '✓', label: 'Success' },
  error: { className: 'bg-rose-600', icon: '!', label: 'Error' },
  info: { className: 'bg-slate-800', icon: 'i', label: 'Info' },
}

/** One consistent toast system; messages are announced to screen readers via aria-live. */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const nextId = useRef(1)

  const dismiss = useCallback((id: number) => setToasts((t) => t.filter((x) => x.id !== id)), [])
  const push = useCallback((tone: Tone, message: string) => {
    const id = nextId.current++
    setToasts((t) => [...t.slice(-3), { id, tone, message }])
    setTimeout(() => dismiss(id), DURATION_MS)
  }, [dismiss])

  const api = useMemo<ToastApi>(() => ({
    success: (m) => push('success', m),
    error: (m) => push('error', m),
    info: (m) => push('info', m),
  }), [push])

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div aria-live="polite" aria-atomic="false" className="pointer-events-none fixed inset-x-0 bottom-4 z-[60] flex flex-col items-center gap-2 px-4 sm:bottom-6 sm:items-end sm:pr-6 print:hidden">
        {toasts.map((t) => (
          <div key={t.id} role="status" className={`pointer-events-auto flex max-w-sm items-start gap-3 rounded-lg px-4 py-3 text-sm text-white shadow-lg ${STYLE[t.tone].className}`}>
            <span aria-hidden className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-white/25 text-xs font-bold">{STYLE[t.tone].icon}</span>
            <span className="sr-only">{STYLE[t.tone].label}: </span>
            <span className="flex-1">{t.message}</span>
            <button onClick={() => dismiss(t.id)} className="rounded px-1 text-white/80 hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-white" aria-label="Dismiss notification">✕</button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useToast(): ToastApi {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used inside <ToastProvider>')
  return ctx
}
