import React from 'react'
import { NavLink, useNavigate, Outlet } from 'react-router-dom'
import {
  ChartBarIcon, BuildingOffice2Icon, UsersIcon, CircleStackIcon,
  DocumentTextIcon, CodeBracketIcon, AdjustmentsHorizontalIcon,
  RocketLaunchIcon,
} from '@heroicons/react/24/outline'
import internal from './api'

const NAV = [
  { to: '/internal/dashboard', label: 'Dashboard', Icon: ChartBarIcon },
  { to: '/internal/organizations', label: 'Organizations', Icon: BuildingOffice2Icon },
  { to: '/internal/users', label: 'Users', Icon: UsersIcon },
  { to: '/internal/database', label: 'Database', Icon: CircleStackIcon },
  { to: '/internal/logs', label: 'Logs', Icon: DocumentTextIcon },
  { to: '/internal/source', label: 'Source viewer', Icon: CodeBracketIcon },
  { to: '/internal/config', label: 'Feature flags', Icon: AdjustmentsHorizontalIcon },
  { to: '/internal/onboarding', label: 'Onboarding', Icon: RocketLaunchIcon },
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
          {NAV.map(item => {
            const Icon = item.Icon
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors ${
                    isActive
                      ? 'bg-slate-700 text-white font-medium'
                      : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                  }`
                }
              >
                {Icon && <Icon className="w-4 h-4 shrink-0" />}
                <span>{item.label}</span>
              </NavLink>
            )
          })}
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
