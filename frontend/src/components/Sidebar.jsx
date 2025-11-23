import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { 
  HomeIcon, 
  UsersIcon, 
  MusicalNoteIcon, 
  DocumentTextIcon,
  ChartBarIcon,
  CurrencyDollarIcon,
  Cog6ToothIcon
} from '@heroicons/react/24/outline'

export default function Sidebar({ user, onLogout }) {
  const location = useLocation()
  
  const isActive = (path) => {
    if (path === '/') return location.pathname === '/'
    return location.pathname.startsWith(path)
  }
  
  const navItems = [
    { path: '/', label: 'Home', icon: HomeIcon },
    { path: '/roster', label: 'Roster', icon: UsersIcon },
    { path: '/catalog', label: 'Catalog', icon: MusicalNoteIcon },
    { path: '/placements', label: 'Placements', icon: DocumentTextIcon },
    { path: '/reports', label: 'Reports', icon: ChartBarIcon },
    { path: '/valuation', label: 'Valuation', icon: CurrencyDollarIcon },
  ]
  
  return (
    <div className="h-screen w-64 bg-gradient-to-b from-gray-900 to-black text-white flex flex-col border-r border-gray-800">
      <div className="p-6 border-b border-gray-800">
        <h1 className="text-2xl font-bold bg-gradient-to-r from-purple-400 to-pink-500 bg-clip-text text-transparent">
          Gotcha
        </h1>
        <p className="text-sm text-gray-400 mt-1">Catalog Manager</p>
      </div>
      
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon
          const active = isActive(item.path)
          
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center space-x-3 px-3 py-2.5 rounded-lg transition-all duration-200 ${
                active 
                  ? 'bg-gradient-to-r from-purple-600 to-pink-600 text-white shadow-lg' 
                  : 'text-gray-300 hover:bg-gray-800 hover:text-white'
              }`}
            >
              <Icon className="w-5 h-5" />
              <span className="font-medium">{item.label}</span>
            </Link>
          )
        })}
      </nav>
      
      <div className="p-4 border-t border-gray-800 space-y-3">
        <div className="flex items-center space-x-3 px-3 py-2">
          <div className="w-8 h-8 rounded-full bg-gradient-to-r from-purple-500 to-pink-500 flex items-center justify-center text-sm font-bold">
            {user?.username?.charAt(0).toUpperCase() || 'U'}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white truncate">{user?.username || 'User'}</p>
            <p className="text-xs text-gray-400">{user?.role || 'Admin'}</p>
          </div>
        </div>
        
        <Link
          to="/settings"
          className={`flex items-center space-x-3 px-3 py-2 rounded-lg transition-all duration-200 ${
            isActive('/settings')
              ? 'bg-gray-800 text-white'
              : 'text-gray-400 hover:bg-gray-800 hover:text-white'
          }`}
        >
          <Cog6ToothIcon className="w-5 h-5" />
          <span className="text-sm">Settings</span>
        </Link>
        
        <button 
          onClick={onLogout}
          className="w-full px-3 py-2 text-sm text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-all duration-200 text-left"
        >
          Sign Out
        </button>
      </div>
    </div>
  )
}
