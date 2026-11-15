import { Component, type ErrorInfo, type ReactNode } from 'react'

interface State {
  error: Error | null
}

/** Last-resort guard: a rendering bug shows a recovery screen instead of a blank page. */
export class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Unhandled UI error', error, info.componentStack)
  }

  render() {
    if (!this.state.error) return this.props.children
    return (
      <div role="alert" className="flex min-h-screen items-center justify-center bg-slate-50 p-6 dark:bg-slate-900">
        <div className="max-w-md rounded-xl bg-white p-6 text-center shadow ring-1 ring-slate-200 dark:bg-slate-800 dark:ring-slate-700">
          <p className="text-lg font-semibold text-slate-900 dark:text-slate-100">Something went wrong on this page</p>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">Your data is safe. Reload the page or go back to your home screen.</p>
          <div className="mt-4 flex justify-center gap-2">
            <button onClick={() => window.location.reload()} className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700">Reload</button>
            <a href="/" className="rounded-lg px-4 py-2 text-sm font-medium text-slate-700 ring-1 ring-slate-300 hover:bg-slate-50 dark:text-slate-200">Home</a>
          </div>
        </div>
      </div>
    )
  }
}
