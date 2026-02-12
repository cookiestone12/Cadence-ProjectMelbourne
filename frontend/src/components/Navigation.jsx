import React from 'react'
import { Link, useLocation } from 'react-router-dom'

export default function Navigation({ user, onLogout }) {
  const location = useLocation()
  
  const isActive = (path) => location.pathname === path
  
  return (
    <nav className="bg-[#3D4A44] text-white shadow-lg border-b border-[rgba(59,77,67,0.3)]">
      <div className="container mx-auto px-4 py-4">
        <div className="flex justify-between items-center">
          <div className="flex items-center space-x-8">
            <img src="/logo-small.png" alt="Rythm" className="h-12" />
            <h1 className="text-2xl font-bold font-heading uppercase tracking-wide">Rythm</h1>
            <div className="flex space-x-4">
              <Link 
                to="/catalog" 
                className={`hover:text-[#7BA594] pb-1 border-b-2 transition-colors duration-200 uppercase text-sm tracking-wide ${
                  isActive('/catalog') ? 'border-[#7BA594] text-[#7BA594]' : 'border-transparent'
                }`}
              >
                Catalog
              </Link>
              <Link 
                to="/search" 
                className={`hover:text-[#7BA594] pb-1 border-b-2 transition-colors duration-200 uppercase text-sm tracking-wide ${
                  isActive('/search') ? 'border-[#7BA594] text-[#7BA594]' : 'border-transparent'
                }`}
              >
                Search
              </Link>
              {user?.is_admin && (
                <Link 
                  to="/settings" 
                  className={`hover:text-[#7BA594] pb-1 border-b-2 transition-colors duration-200 uppercase text-sm tracking-wide ${
                    isActive('/settings') ? 'border-[#7BA594] text-[#7BA594]' : 'border-transparent'
                  }`}
                >
                  Settings
                </Link>
              )}
            </div>
          </div>
          <div className="flex items-center space-x-4">
            <span className="text-sm bg-[#5B8A72] px-2 py-1 rounded text-white font-mono">INTERNAL DEMO</span>
            <span className="text-[#9AA69E]">{user?.username}</span>
            <button onClick={onLogout} className="bg-[#5B8A72] text-white px-4 py-2 rounded shadow-[0_0_15px_rgba(91,138,114,0.3)] hover:shadow-[0_0_25px_rgba(91,138,114,0.5)] hover:scale-105 transition-all duration-200 font-bold uppercase text-sm tracking-wide">
              Logout
            </button>
          </div>
        </div>
      </div>
    </nav>
  )
}
