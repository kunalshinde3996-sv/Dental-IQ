import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { notificationsApi } from '../api'
import type { AppNotification } from '../api/types'
import { cx } from './ui'

const POLL_MS = 30_000

const KIND_STYLE: Record<string, { label: string; className: string }> = {
  case_approved: { label: 'Approved', className: 'bg-emerald-100 text-emerald-800' },
  case_rejected: { label: 'Needs changes', className: 'bg-rose-100 text-rose-800' },
  patient_allocated: { label: 'Allocation', className: 'bg-sky-100 text-sky-800' },
  at_risk_alert: { label: 'At-risk', className: 'bg-amber-100 text-amber-900' },
}

function timeAgo(iso: string): string {
  const mins = Math.round((Date.now() - new Date(iso).getTime()) / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins} min ago`
  const hrs = Math.round(mins / 60)
  return hrs < 24 ? `${hrs} h ago` : `${Math.round(hrs / 24)} d ago`
}

/** Bell with unread badge; polls the unread count and opens a list panel. */
export function NotificationBell({ placement = 'up' }: { placement?: 'up' | 'down' }) {
  const navigate = useNavigate()
  const [count, setCount] = useState(0)
  const [open, setOpen] = useState(false)
  const [items, setItems] = useState<AppNotification[] | null>(null)
  const panel = useRef<HTMLDivElement>(null)

  const refreshCount = useCallback(() => {
    notificationsApi.unreadCount().then((r) => setCount(r.unread)).catch(() => undefined)
  }, [])

  useEffect(() => {
    refreshCount()
    const t = setInterval(refreshCount, POLL_MS)
    return () => clearInterval(t)
  }, [refreshCount])

  useEffect(() => {
    if (!open) return
    notificationsApi.list().then(setItems).catch(() => setItems([]))
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    const onClick = (e: MouseEvent) => panel.current && !panel.current.contains(e.target as Node) && setOpen(false)
    window.addEventListener('keydown', onKey)
    window.addEventListener('mousedown', onClick)
    return () => {
      window.removeEventListener('keydown', onKey)
      window.removeEventListener('mousedown', onClick)
    }
  }, [open])

  async function openItem(n: AppNotification) {
    if (!n.read_at) {
      await notificationsApi.markRead(n.id).catch(() => undefined)
      setCount((c) => Math.max(0, c - 1))
    }
    setOpen(false)
    if (n.link) navigate(n.link)
  }

  async function markAll() {
    await notificationsApi.markAllRead().catch(() => undefined)
    setCount(0)
    setItems((list) => list?.map((n) => ({ ...n, read_at: n.read_at ?? new Date().toISOString() })) ?? null)
  }

  return (
    <div className="relative" ref={panel}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="relative rounded-md p-1.5 text-brand-100 hover:bg-brand-700 hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-white"
        aria-label={count ? `Notifications, ${count} unread` : 'Notifications'}
        aria-expanded={open}
        aria-haspopup="dialog"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} className="h-5 w-5" aria-hidden>
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 17h5l-1.4-1.4A2 2 0 0118 14.2V11a6 6 0 00-4-5.7V5a2 2 0 10-4 0v.3A6 6 0 006 11v3.2c0 .5-.2 1-.6 1.4L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
        </svg>
        {count > 0 && (
          <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-rose-500 px-1 text-[10px] font-bold text-white">
            {count > 99 ? '99+' : count}
          </span>
        )}
      </button>
      {open && (
        <div
          role="dialog"
          aria-label="Notifications"
          className={cx(
            'absolute z-50 w-80 max-w-[calc(100vw-2rem)] overflow-hidden rounded-xl bg-white text-slate-900 shadow-xl ring-1 ring-slate-200 dark:bg-slate-800 dark:text-slate-100 dark:ring-slate-700',
            placement === 'up' ? 'bottom-full left-0 mb-2' : 'right-0 top-full mt-2',
          )}
        >
          <div className="flex items-center justify-between border-b border-slate-100 px-4 py-2.5 dark:border-slate-700">
            <span className="text-sm font-semibold">Notifications</span>
            <button onClick={markAll} disabled={count === 0} className="text-xs font-medium text-brand-700 hover:underline disabled:text-slate-400 disabled:no-underline dark:text-brand-300">
              Mark all read
            </button>
          </div>
          <ul className="max-h-96 divide-y divide-slate-100 overflow-y-auto dark:divide-slate-700">
            {items === null && <li className="px-4 py-6 text-center text-sm text-slate-500">Loading…</li>}
            {items?.length === 0 && <li className="px-4 py-6 text-center text-sm text-slate-500">You're all caught up.</li>}
            {items?.map((n) => {
              const style = KIND_STYLE[n.kind] ?? { label: 'Update', className: 'bg-slate-100 text-slate-700' }
              return (
                <li key={n.id}>
                  <button onClick={() => openItem(n)} className={cx('block w-full px-4 py-3 text-left hover:bg-slate-50 dark:hover:bg-slate-700/50', !n.read_at && 'bg-brand-50/60 dark:bg-brand-900/30')}>
                    <div className="flex items-center gap-2">
                      <span className={cx('rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase', style.className)}>{style.label}</span>
                      <span className="ml-auto text-[11px] text-slate-500 dark:text-slate-400">{timeAgo(n.created_at)}</span>
                      {!n.read_at && <span className="h-2 w-2 rounded-full bg-brand-500" aria-label="unread" />}
                    </div>
                    <p className="mt-1 text-sm font-medium">{n.title}</p>
                    <p className="line-clamp-2 text-xs text-slate-600 dark:text-slate-300">{n.body}</p>
                  </button>
                </li>
              )
            })}
          </ul>
        </div>
      )}
    </div>
  )
}
