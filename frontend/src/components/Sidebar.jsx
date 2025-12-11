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
  XMarkIcon
} from '@heroicons/react/24/outline'

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
        flex flex-col border-r border-[rgba(0,0,0,0.07)]
        shadow-apple-nav
        transform transition-transform duration-300 ease-in-out
        ${isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
      <div className="p-5 border-b border-[rgba(0,0,0,0.07)]">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <img 
              src="/logo-small.png" 
              alt="Ampersound" 
              className="h-10 w-10"
            />
            <div>
              <h1 className="text-lg font-semibold text-[#1D1D1F]">
                Ampersound
              </h1>
              <p className="text-xs text-[#86868B]">Catalog Manager</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="lg:hidden text-[#86868B] hover:text-[#1D1D1F] transition-colors"
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
                  ? 'bg-gradient-to-r from-[#A020F0] to-[#E540AC] text-white shadow-lg shadow-purple-500/20' 
                  : 'text-[#1D1D1F] hover:bg-[#F2F2F5]'
              }`}
            >
              <Icon className="w-5 h-5" />
              <span className={`${active ? 'font-semibold' : 'font-medium'}`}>{item.label}</span>
            </Link>
          )
        })}
      </nav>
      
      <div className="p-4 border-t border-[rgba(0,0,0,0.07)] space-y-3">
        <div className="flex items-center space-x-3 px-3 py-2">
          <div className="w-8 h-8 rounded-full bg-gradient-to-r from-[#A020F0] to-[#E540AC] flex items-center justify-center text-sm font-bold text-white shadow-md">
            {user?.username?.charAt(0).toUpperCase() || 'U'}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-[#1D1D1F] truncate">{user?.username || 'User'}</p>
            <p className="text-xs text-[#86868B]">{user?.role || 'Admin'}</p>
          </div>
        </div>
        
        <Link
          to="/settings"
          onClick={() => window.innerWidth < 1024 && onClose()}
          className={`flex items-center space-x-3 px-3 py-2 rounded-xl transition-all duration-200 ${
            isActive('/settings')
              ? 'bg-[#F2F2F5] text-[#A020F0] font-medium'
              : 'text-[#86868B] hover:bg-[#F2F2F5] hover:text-[#1D1D1F]'
          }`}
        >
          <Cog6ToothIcon className="w-5 h-5" />
          <span className="text-sm">Settings</span>
        </Link>
        
        <button 
          onClick={onLogout}
          className="w-full px-3 py-2 text-sm text-[#86868B] hover:text-[#FF3B30] hover:bg-red-50 rounded-xl transition-all duration-200 text-left flex items-center space-x-3"
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
