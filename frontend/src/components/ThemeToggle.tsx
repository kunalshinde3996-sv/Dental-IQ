import { useTheme, type ThemeChoice } from '../lib/theme'
import { cx } from './ui'

const OPTIONS: { value: ThemeChoice; label: string; icon: string }[] = [
  { value: 'light', label: 'Light', icon: 'M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z' },
  { value: 'dark', label: 'Dark', icon: 'M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z' },
  { value: 'system', label: 'System', icon: 'M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z' },
]

/** Light / Dark / System switch (radio group, keyboard accessible). */
export function ThemeToggle() {
  const { choice, setChoice } = useTheme()
  return (
    <div role="radiogroup" aria-label="Colour theme" className="flex rounded-lg bg-brand-800/60 p-0.5">
      {OPTIONS.map((o) => (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={choice === o.value}
          title={`${o.label} theme`}
          onClick={() => setChoice(o.value)}
          className={cx(
            'flex flex-1 items-center justify-center gap-1 rounded-md px-2 py-1 text-xs font-medium transition focus:outline-none focus-visible:ring-2 focus-visible:ring-white',
            choice === o.value ? 'bg-brand-600 text-white' : 'text-brand-100 hover:text-white',
          )}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} className="h-3.5 w-3.5" aria-hidden><path strokeLinecap="round" strokeLinejoin="round" d={o.icon} /></svg>
          {o.label}
        </button>
      ))}
    </div>
  )
}
