import { cx } from './ui'

/** Dental-IQ mark: a tooth on a teal-to-blue tile with an "insight" spark. Inline so it themes and prints. */
export function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={cx('h-8 w-8 shrink-0', className)} role="img" aria-label="Dental-IQ">
      <defs>
        <linearGradient id="diq-tile" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#25a5a7" />
          <stop offset="1" stopColor="#1d5f9e" />
        </linearGradient>
      </defs>
      <rect width="32" height="32" rx="8" fill="url(#diq-tile)" />
      <path
        d="M10.2 7.5c-2.6 0-4.2 2.1-4.2 5.1 0 3 1.5 5.1 2.5 8.1.7 2.2 1 4.3 2.5 4.3s1.8-2.6 2.5-4.6c.4-1.2.9-1.5 2.5-1.5s2.1.3 2.5 1.5c.7 2 1 4.6 2.5 4.6s1.8-2.1 2.5-4.3c1-3 2.5-5.1 2.5-8.1 0-3-1.6-5.1-4.2-5.1-2 0-3.4 1-5.8 1s-3.8-1-5.8-1z"
        fill="#fff"
      />
      <circle cx="24.5" cy="7.5" r="2.2" fill="#fde68a" stroke="#fff" strokeWidth="1" />
    </svg>
  )
}

export function Logo({ className, subtitle }: { className?: string; subtitle?: string }) {
  return (
    <div className={cx('flex items-center gap-2', className)}>
      <LogoMark />
      <div className="leading-tight">
        <span className="text-lg font-semibold tracking-tight">
          Dental<span className="text-brand-400">-IQ</span>
        </span>
        {subtitle && <span className="block text-[11px] font-normal opacity-80">{subtitle}</span>}
      </div>
    </div>
  )
}
