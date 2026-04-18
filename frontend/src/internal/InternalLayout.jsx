import React from 'react'
import { NavLink, useNavigate, Outlet } from 'react-router-dom'
import internal from './api'

const NAV = [
  { to: '/internal/dashboard', label: 'Dashboard' },
  { to: '/internal/organizations', label: 'Organizations' },
  { to: '/internal/users', label: 'Users' },
  { to: '/internal/database', label: 'Database' },
  { to: '/internal/logs', label: 'Logs' },
  { to: '/internal/source', label: 'Source viewer' },
  { to: '/internal/config', label: 'Feature flags' },
  { to: '/internal/onboarding', label: 'Onboarding' },
]

export default function InternalLayout() {
  const navigate = useNavigate()
  const user = JSON.parse(localStorage.getItem('internal_user') || 'null')

  const logout = async () => {
    try { await internal.post('/api/internal/portal/cookie-logout') } catch {}
    localStorage.removeItem('internal_user')
    navigate('/internal/login')
  }

  return (
    <div className="min-h-screen flex bg-white text-slate-900">
      <aside className="w-60 bg-slate-900 text-slate-100 flex flex-col">
        <div className="px-5 py-5 border-b border-slate-700">
          <div className="text-lg font-semibold tracking-tight">Cadence Staff</div>
          <div className="text-xs text-slate-400 mt-0.5">Internal Portal</div>
        </div>
        <nav className="flex-1 px-2 py-3 space-y-0.5">
          {NAV.map(item => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `block px-3 py-2 rounded-md text-sm transition-colors ${
                  isActive
                    ? 'bg-slate-700 text-white font-medium'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-slate-700 px-4 py-3 text-xs text-slate-400">
          <div className="text-slate-200 font-medium truncate">
            {user?.username || 'Staff'}
          </div>
          <div className="truncate">
            {user?.is_super_admin ? 'Master Admin' : 'Cadence Staff'}
          </div>
          <button
            onClick={logout}
            className="mt-2 w-full text-left text-slate-400 hover:text-white text-xs"
          >
            Sign out
          </button>
        </div>
      </aside>
      <main className="flex-1 min-w-0 bg-white">
        <div className="px-8 py-6 max-w-[1400px]">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
