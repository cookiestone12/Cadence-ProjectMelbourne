import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { 
  HomeIcon, 
  UsersIcon, 
  MusicalNoteIcon, 
  DocumentTextIcon,
  ChartBarIcon,
  CurrencyDollarIcon,
  Cog6ToothIcon,
  XMarkIcon,
  ShieldCheckIcon
} from '@heroicons/react/24/outline'
import NotificationBell from './NotificationBell'

export default function Sidebar({ user, onLogout, isOpen, onClose }) {
  const location = useLocation()
  
  const isActive = (path) => {
    if (path === '/') return location.pathname === '/'
    return location.pathname.startsWith(path)
  }
  
  const navItems = [
    { path: '/', label: 'Home', icon: HomeIcon },
    { path: '/roster', label: 'Roster', icon: UsersIcon },
    { path: '/catalog', label: 'Catalog', icon: MusicalNoteIcon },
    { path: '/reports', label: 'Reports', icon: ChartBarIcon },
    { path: '/valuation', label: 'Valuation', icon: CurrencyDollarIcon },
  ]
  
  return (
    <>
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/20 backdrop-blur-sm z-40 lg:hidden"
          onClick={onClose}
        />
      )}
      
      <div className={`
        fixed lg:relative inset-y-0 left-0 z-50
        h-screen w-64 bg-white 
        flex flex-col border-r border-[rgba(59,77,67,0.08)]
        shadow-apple-nav
        transform transition-transform duration-300 ease-in-out
        ${isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
      <div className="p-5 border-b border-[rgba(59,77,67,0.08)]">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <img 
              src="/logo-small.png" 
              alt="Ampersound" 
              className="h-10 w-10"
            />
            <div>
              <h1 className="text-lg font-semibold text-[#3D4A44]">
                Ampersound
              </h1>
              <p className="text-xs text-[#7A8580]">Catalog Manager</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="lg:hidden text-[#7A8580] hover:text-[#3D4A44] transition-colors"
          >
            <XMarkIcon className="w-6 h-6" />
          </button>
        </div>
      </div>
      
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon
          const active = isActive(item.path)
          
          return (
            <Link
              key={item.path}
              to={item.path}
              onClick={() => window.innerWidth < 1024 && onClose()}
              className={`flex items-center space-x-3 px-3 py-2.5 rounded-xl transition-all duration-200 ${
                active 
                  ? 'bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white shadow-lg shadow-[rgba(91,138,114,0.25)]' 
                  : 'text-[#3D4A44] hover:bg-[#EEF1EC]'
              }`}
            >
              <Icon className="w-5 h-5" />
              <span className={`${active ? 'font-semibold' : 'font-medium'}`}>{item.label}</span>
            </Link>
          )
        })}
      </nav>
      
      <div className="p-4 border-t border-[rgba(59,77,67,0.08)] space-y-3">
        <div className="flex items-center space-x-3 px-3 py-2">
          <div className="w-8 h-8 rounded-full bg-gradient-to-r from-[#5B8A72] to-[#7BA594] flex items-center justify-center text-sm font-bold text-white shadow-md">
            {user?.username?.charAt(0).toUpperCase() || 'U'}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-[#3D4A44] truncate">{user?.username || 'User'}</p>
            <p className="text-xs text-[#7A8580]">{user?.is_super_admin ? 'Super Admin' : user?.is_admin ? 'Admin' : 'Member'}</p>
          </div>
          <NotificationBell />
        </div>
        
        {user?.is_super_admin && (
          <Link
            to="/admin"
            onClick={() => window.innerWidth < 1024 && onClose()}
            className={`flex items-center space-x-3 px-3 py-2 rounded-xl transition-all duration-200 ${
              isActive('/admin')
                ? 'bg-gradient-to-r from-[#5A8A9A] to-[#7BA594] text-white font-medium shadow-md'
                : 'text-[#7A8580] hover:bg-[#EEF1EC] hover:text-[#3D4A44]'
            }`}
          >
            <ShieldCheckIcon className="w-5 h-5" />
            <span className="text-sm">Admin</span>
          </Link>
        )}
        
        <Link
          to="/settings"
          onClick={() => window.innerWidth < 1024 && onClose()}
          className={`flex items-center space-x-3 px-3 py-2 rounded-xl transition-all duration-200 ${
            isActive('/settings')
              ? 'bg-[#EEF1EC] text-[#5B8A72] font-medium'
              : 'text-[#7A8580] hover:bg-[#EEF1EC] hover:text-[#3D4A44]'
          }`}
        >
          <Cog6ToothIcon className="w-5 h-5" />
          <span className="text-sm">Settings</span>
        </Link>
        
        <button 
          onClick={onLogout}
          className="w-full px-3 py-2 text-sm text-[#7A8580] hover:text-[#C47068] hover:bg-red-50 rounded-xl transition-all duration-200 text-left flex items-center space-x-3"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15m3 0l3-3m0 0l-3-3m3 3H9" />
          </svg>
          <span>Sign Out</span>
        </button>
      </div>
    </div>
    </>
  )
}
