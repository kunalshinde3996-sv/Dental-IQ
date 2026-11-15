import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'

export type ThemeChoice = 'light' | 'dark' | 'system'
const KEY = 'dentaliq.theme'

interface ThemeState {
  choice: ThemeChoice
  /** The theme actually applied after resolving 'system'. */
  resolved: 'light' | 'dark'
  setChoice: (c: ThemeChoice) => void
}

const ThemeContext = createContext<ThemeState | null>(null)

function readChoice(): ThemeChoice {
  try {
    const v = localStorage.getItem(KEY)
    return v === 'light' || v === 'dark' || v === 'system' ? v : 'system'
  } catch {
    return 'system'
  }
}

const systemDark = () => typeof window !== 'undefined' && window.matchMedia?.('(prefers-color-scheme: dark)').matches

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [choice, setChoiceState] = useState<ThemeChoice>(readChoice)
  const [osDark, setOsDark] = useState<boolean>(systemDark)

  useEffect(() => {
    const mq = window.matchMedia?.('(prefers-color-scheme: dark)')
    if (!mq) return
    const onChange = () => setOsDark(mq.matches)
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])

  const resolved: 'light' | 'dark' = choice === 'system' ? (osDark ? 'dark' : 'light') : choice

  useEffect(() => {
    const root = document.documentElement
    root.classList.toggle('dark', resolved === 'dark')
    root.style.colorScheme = resolved
  }, [resolved])

  const setChoice = useCallback((c: ThemeChoice) => {
    setChoiceState(c)
    try {
      localStorage.setItem(KEY, c)
    } catch {
      /* storage unavailable: choice lasts for this tab only */
    }
  }, [])

  const value = useMemo(() => ({ choice, resolved, setChoice }), [choice, resolved, setChoice])
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useTheme(): ThemeState {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme must be used inside <ThemeProvider>')
  return ctx
}
