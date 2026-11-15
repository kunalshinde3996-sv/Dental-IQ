import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import type { Role } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import { initials } from '../lib/format'
import { ROLES, YEARS } from '../lib/labels'
import { cx } from './ui'

interface NavItem {
  to: string
  label: string
  icon: string // SVG path (24x24, stroke)
}

const ICONS = {
  cases: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.6a1 1 0 01.7.3l5.4 5.4a1 1 0 01.3.7V19a2 2 0 01-2 2z',
  plus: 'M12 4v16m8-8H4',
  patients: 'M17 20h5v-2a3 3 0 00-5.4-1.8M17 20H7m10 0v-2c0-.7-.1-1.3-.4-1.8M7 20H2v-2a3 3 0 015.4-1.8M7 20v-2c0-.7.1-1.3.4-1.8m0 0a5 5 0 019.2 0M15 7a3 3 0 11-6 0 3 3 0 016 0z',
  check: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z',
  home: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6',
  students: 'M12 14l9-5-9-5-9 5 9 5zm0 0v6m0-6l6.2-3.4A12 12 0 0119 17.1 12 12 0 0012 20a12 12 0 00-7-2.9 12 12 0 01.8-6.5L12 14z',
  faculty: 'M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z',
  alert: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z',
  chart: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z',
}

const NAV: Record<Role, NavItem[]> = {
  student: [
    { to: '/my-cases', label: 'My Cases', icon: ICONS.cases },
    { to: '/cases/new', label: 'New Case', icon: ICONS.plus },
    { to: '/patients', label: 'Patients', icon: ICONS.patients },
  ],
  faculty: [
    { to: '/approvals', label: 'Pending Approvals', icon: ICONS.check },
    { to: '/at-risk', label: 'At-Risk Students', icon: ICONS.alert },
    { to: '/insights', label: 'Population Insights', icon: ICONS.chart },
    { to: '/patients', label: 'Patients', icon: ICONS.patients },
  ],
  admin: [
    { to: '/admin', label: 'Overview', icon: ICONS.home },
    { to: '/admin/students', label: 'Students', icon: ICONS.students },
    { to: '/admin/faculty', label: 'Faculty', icon: ICONS.faculty },
    { to: '/at-risk', label: 'At-Risk Students', icon: ICONS.alert },
    { to: '/insights', label: 'Population Insights', icon: ICONS.chart },
    { to: '/patients', label: 'Patients', icon: ICONS.patients },
  ],
}

function Icon({ d, className }: { d: string; className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" className={cx('h-5 w-5 shrink-0', className)} aria-hidden>
      <path d={d} />
    </svg>
  )
}

export function Logo({ className }: { className?: string }) {
  return (
    <div className={cx('flex items-center gap-2', className)}>
      <img src="/favicon.svg" alt="" className="h-8 w-8" />
      <span className="text-lg font-semibold tracking-tight">
        Dental<span className="text-brand-500">-IQ</span>
      </span>
    </div>
  )
}

export function AppLayout() {
  const { me, logout } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  if (!me) return null
  const role = me.user.role
  const subtitle = me.student
    ? `${YEARS[me.student.year]} · ${me.student.roll_no}`
    : me.faculty
      ? me.faculty.designation
      : ROLES[role]

  const nav = (
    <nav className="flex flex-col gap-1">
      {NAV[role].map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.to === '/admin'}
          onClick={() => setMenuOpen(false)}
          className={({ isActive }) =>
            cx(
              'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition',
              isActive ? 'bg-brand-600 text-white shadow-sm' : 'text-brand-100 hover:bg-brand-800 hover:text-white',
            )
          }
        >
          <Icon d={item.icon} />
          {item.label}
        </NavLink>
      ))}
    </nav>
  )

  const userBox = (
    <div className="flex items-center gap-3 rounded-lg bg-brand-800/60 p-3">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-500 text-sm font-semibold text-white">
        {initials(me.user.name)}
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-white">{me.user.name}</p>
        <p className="truncate text-xs text-brand-200">{subtitle}</p>
      </div>
      <button onClick={logout} className="rounded-md p-1.5 text-brand-200 hover:bg-brand-700 hover:text-white" title="Log out" aria-label="Log out">
        <Icon d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
      </button>
    </div>
  )

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col justify-between bg-brand-900 p-4 text-white lg:flex">
        <div>
          <Logo className="mb-8 px-2 pt-1" />
          {nav}
        </div>
        {userBox}
      </aside>

      {/* Mobile top bar */}
      <header className="sticky top-0 z-30 flex items-center justify-between bg-brand-900 px-4 py-3 text-white lg:hidden">
        <Logo />
        <button onClick={() => setMenuOpen((o) => !o)} className="rounded-md p-2 hover:bg-brand-800" aria-label="Toggle menu" aria-expanded={menuOpen}>
          <Icon d={menuOpen ? 'M6 18L18 6M6 6l12 12' : 'M4 6h16M4 12h16M4 18h16'} />
        </button>
      </header>
      {menuOpen && (
        <div className="fixed inset-x-0 top-[60px] z-20 space-y-4 bg-brand-900 p-4 shadow-lg lg:hidden">
          {nav}
          {userBox}
        </div>
      )}

      <main className="lg:pl-64">
        <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
