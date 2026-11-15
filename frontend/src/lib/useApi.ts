import { useCallback, useEffect, useRef, useState } from 'react'

interface ApiState<T> {
  data: T | null
  error: string | null
  loading: boolean
  reload: () => void
  setData: (updater: (prev: T | null) => T | null) => void
}

/**
 * Run an async loader on mount and whenever `deps` change.
 * Stale responses (from an earlier deps value) are ignored.
 */
export function useApi<T>(loader: () => Promise<T>, deps: unknown[]): ApiState<T> {
  const [data, setDataState] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [tick, setTick] = useState(0)
  const requestId = useRef(0)

  useEffect(() => {
    const id = ++requestId.current
    setLoading(true)
    setError(null)
    loader()
      .then((result) => {
        if (id === requestId.current) setDataState(result)
      })
      .catch((err: unknown) => {
        if (id === requestId.current) setError(err instanceof Error ? err.message : 'Something went wrong')
      })
      .finally(() => {
        if (id === requestId.current) setLoading(false)
      })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick])

  const reload = useCallback(() => setTick((t) => t + 1), [])
  const setData = useCallback((updater: (prev: T | null) => T | null) => setDataState(updater), [])
  return { data, error, loading, reload, setData }
}

/** Debounce a fast-changing value (e.g. search input). */
export function useDebounced<T>(value: T, delayMs = 300): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delayMs)
    return () => clearTimeout(t)
  }, [value, delayMs])
  return debounced
}
