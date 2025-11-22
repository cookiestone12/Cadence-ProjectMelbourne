import React from 'react'
import { Link, useLocation } from 'react-router-dom'

export default function Navigation({ user, onLogout }) {
  const location = useLocation()
  
  const isActive = (path) => location.pathname === path
  
  return (
    <nav className="bg-surface-black text-white shadow-lg border-b border-border-grey">
      <div className="container mx-auto px-4 py-4">
        <div className="flex justify-between items-center">
          <div className="flex items-center space-x-8">
            <img src="/ampersound-logo-3d.png" alt="Ampersound Intelligence" className="h-12" />
            <h1 className="text-2xl font-bold font-heading uppercase tracking-wide">Ampersound Intelligence</h1>
            <div className="flex space-x-4">
              <Link 
                to="/catalog" 
                className={`hover:text-signal-red pb-1 border-b-2 transition-colors duration-200 uppercase text-sm tracking-wide ${
                  isActive('/catalog') ? 'border-signal-red text-signal-red' : 'border-transparent'
                }`}
              >
                Catalog
              </Link>
              <Link 
                to="/search" 
                className={`hover:text-signal-red pb-1 border-b-2 transition-colors duration-200 uppercase text-sm tracking-wide ${
                  isActive('/search') ? 'border-signal-red text-signal-red' : 'border-transparent'
                }`}
              >
                Search
              </Link>
              {user?.is_admin && (
                <Link 
                  to="/settings" 
                  className={`hover:text-signal-red pb-1 border-b-2 transition-colors duration-200 uppercase text-sm tracking-wide ${
                    isActive('/settings') ? 'border-signal-red text-signal-red' : 'border-transparent'
                  }`}
                >
                  Settings
                </Link>
              )}
            </div>
          </div>
          <div className="flex items-center space-x-4">
            <span className="text-sm bg-signal-red px-2 py-1 rounded text-white font-mono">INTERNAL DEMO</span>
            <span className="text-tech-grey">{user?.username}</span>
            <button onClick={onLogout} className="bg-signal-red text-white px-4 py-2 rounded shadow-red-glow hover:shadow-red-glow-intense hover:scale-105 transition-all duration-200 font-bold uppercase text-sm tracking-wide">
              Logout
            </button>
          </div>
        </div>
      </div>
    </nav>
  )
}
