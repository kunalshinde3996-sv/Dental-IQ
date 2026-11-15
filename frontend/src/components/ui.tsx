// Small, consistent UI primitives built on Tailwind.
import { useEffect } from 'react'
import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes } from 'react'
import type { CaseStatus } from '../api/types'
import { CASE_STATUS } from '../lib/labels'

export function cx(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(' ')
}

type Variant = 'primary' | 'secondary' | 'danger' | 'success' | 'ghost'

const VARIANTS: Record<Variant, string> = {
  primary: 'bg-brand-600 text-white hover:bg-brand-700 focus-visible:ring-brand-500',
  secondary: 'bg-white text-slate-700 ring-1 ring-inset ring-slate-300 hover:bg-slate-50 focus-visible:ring-brand-500',
  danger: 'bg-rose-600 text-white hover:bg-rose-700 focus-visible:ring-rose-500',
  success: 'bg-emerald-600 text-white hover:bg-emerald-700 focus-visible:ring-emerald-500',
  ghost: 'text-slate-600 hover:bg-slate-100 focus-visible:ring-brand-500',
}

export function Button({
  variant = 'primary',
  loading = false,
  className,
  children,
  disabled,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; loading?: boolean }) {
  return (
    <button
      className={cx(
        'inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition',
        'focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60',
        VARIANTS[variant],
        className,
      )}
      disabled={disabled || loading}
      {...props}
    >
      {loading && <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-r-transparent" />}
      {children}
    </button>
  )
}

export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={cx('rounded-xl bg-white shadow-sm ring-1 ring-slate-200', className)}>{children}</div>
}

export function CardHeader({ title, subtitle, action }: { title: ReactNode; subtitle?: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 px-5 py-4">
      <div className="min-w-0">
        <h2 className="text-base font-semibold text-slate-900">{title}</h2>
        {subtitle && <p className="mt-0.5 text-sm text-slate-500">{subtitle}</p>}
      </div>
      {action}
    </div>
  )
}

export function PageHeader({ title, subtitle, actions, docTitle }: { title: ReactNode; subtitle?: ReactNode; actions?: ReactNode; docTitle?: string }) {
  useDocumentTitle(docTitle ?? (typeof title === 'string' ? title : undefined))
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  )
}

export function Field({
  label,
  error,
  hint,
  children,
  className,
}: {
  label: string
  error?: string
  hint?: string
  children: ReactNode
  className?: string
}) {
  return (
    <label className={cx('block', className)}>
      <span className="mb-1 block text-sm font-medium text-slate-700">{label}</span>
      {children}
      {error ? (
        <span className="mt-1 block text-xs text-rose-600">{error}</span>
      ) : (
        hint && <span className="mt-1 block text-xs text-slate-500">{hint}</span>
      )}
    </label>
  )
}

const controlClass =
  'block w-full min-w-0 rounded-lg border-0 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm ring-1 ring-inset ring-slate-300 placeholder:text-slate-500 focus:ring-2 focus:ring-inset focus:ring-brand-500 disabled:bg-slate-50'

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cx(controlClass, className)} {...props} />
}

export function Select({ className, children, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select className={cx(controlClass, 'pr-8', className)} {...props}>
      {children}
    </select>
  )
}

export function Textarea({ className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={cx(controlClass, 'min-h-[80px]', className)} {...props} />
}

/** Sets the browser tab title, e.g. "Patients · Dental-IQ". */
export function useDocumentTitle(title?: string) {
  useEffect(() => {
    if (title) document.title = `${title} · Dental-IQ`
  }, [title])
}

/** Loading placeholder: shimmering skeleton rows (announced to screen readers via the label). */
export function Spinner({ label = 'Loading…', rows = 4 }: { label?: string; rows?: number }) {
  return (
    <div className="space-y-3 p-5" role="status" aria-live="polite">
      <span className="sr-only">{label}</span>
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="flex animate-pulse items-center gap-3" aria-hidden>
          <div className="h-9 w-9 shrink-0 rounded-full bg-slate-200 dark:bg-slate-700" />
          <div className="flex-1 space-y-2">
            <div className="h-3 rounded bg-slate-200 dark:bg-slate-700" style={{ width: `${70 - i * 9}%` }} />
            <div className="h-2.5 rounded bg-slate-100 dark:bg-slate-700/60" style={{ width: `${45 - i * 5}%` }} />
          </div>
        </div>
      ))}
    </div>
  )
}

/** Inline spinner for small, in-place waits (buttons use their own). */
export function InlineSpinner({ label = 'Loading…' }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-sm text-slate-500" role="status">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-brand-500 border-r-transparent" aria-hidden />
      {label}
    </span>
  )
}

export function ErrorBanner({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-rose-50 px-4 py-3 text-sm text-rose-800 ring-1 ring-rose-200" role="alert">
      <span>{message}</span>
      {onRetry && (
        <button className="font-medium underline" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  )
}

export function EmptyState({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="px-6 py-12 text-center">
      <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-brand-50 text-brand-600 dark:bg-brand-900/40 dark:text-brand-300" aria-hidden>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} className="h-6 w-6"><path strokeLinecap="round" strokeLinejoin="round" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.6a1 1 0 00-.7.3l-2.4 2.4a1 1 0 01-.7.3h-3.2a1 1 0 01-.7-.3l-2.4-2.4a1 1 0 00-.7-.3H4" /></svg>
      </div>
      <p className="text-sm font-medium text-slate-900">{title}</p>
      {children && <div className="mt-1 text-sm text-slate-500">{children}</div>}
      {action && <div className="mt-4 flex justify-center">{action}</div>}
    </div>
  )
}

export function Badge({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <span className={cx('inline-flex items-center whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset', className)}>
      {children}
    </span>
  )
}

export function StatusBadge({ status }: { status: CaseStatus }) {
  const s = CASE_STATUS[status]
  return <Badge className={s.className}>{s.label}</Badge>
}

export function ProgressBar({ percent, tone = 'brand', label = 'Progress' }: { percent: number; tone?: 'brand' | 'amber' | 'rose' | 'emerald'; label?: string }) {
  const tones = { brand: 'bg-brand-500', amber: 'bg-amber-500', rose: 'bg-rose-500', emerald: 'bg-emerald-500' }
  const value = Math.max(0, Math.min(100, percent))
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100" role="progressbar" aria-label={label} aria-valuenow={Math.round(value)} aria-valuemin={0} aria-valuemax={100}>
      <div className={cx('h-full rounded-full transition-all', tones[tone])} style={{ width: `${value}%` }} />
    </div>
  )
}

export function Pagination({ total, limit, offset, onChange }: { total: number; limit: number; offset: number; onChange: (offset: number) => void }) {
  if (total <= limit) return null
  const page = Math.floor(offset / limit) + 1
  const pages = Math.ceil(total / limit)
  return (
    <div className="flex items-center justify-between gap-3 border-t border-slate-100 px-5 py-3 text-sm text-slate-600">
      <span>
        {offset + 1}–{Math.min(offset + limit, total)} of {total}
      </span>
      <div className="flex items-center gap-2">
        <Button variant="secondary" className="px-3 py-1" disabled={page <= 1} onClick={() => onChange(offset - limit)}>
          Previous
        </Button>
        <span className="hidden sm:inline">
          Page {page} / {pages}
        </span>
        <Button variant="secondary" className="px-3 py-1" disabled={page >= pages} onClick={() => onChange(offset + limit)}>
          Next
        </Button>
      </div>
    </div>
  )
}

/** Segmented control for small enums (e.g. habit status). */
export function Segmented<T extends string>({
  value,
  options,
  onChange,
  name,
}: {
  value: T
  options: { value: T; label: string; activeClass?: string }[]
  onChange: (v: T) => void
  name: string
}) {
  return (
    <div className="inline-flex rounded-lg bg-slate-100 p-0.5" role="radiogroup" aria-label={name}>
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={value === o.value}
          onClick={() => onChange(o.value)}
          className={cx(
            'rounded-md px-3 py-1 text-xs font-medium transition',
            value === o.value ? o.activeClass ?? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900',
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}
