import React from 'react'
import { Link, useLocation } from 'react-router-dom'

export default function Navigation({ user, onLogout }) {
  const location = useLocation()
  
  const isActive = (path) => location.pathname === path
  
  return (
    <nav className="bg-gradient-to-r from-mime-purple to-mime-orange text-white shadow-lg">
      <div className="container mx-auto px-4 py-4">
        <div className="flex justify-between items-center">
          <div className="flex items-center space-x-8">
            <img src="/mime-publishing-logo.png" alt="MIME Publishing" className="h-12" />
            <h1 className="text-2xl font-bold">MIME Catalog Intelligence</h1>
            <div className="flex space-x-4">
              <Link 
                to="/catalog" 
                className={`hover:text-gray-200 pb-1 border-b-2 ${
                  isActive('/catalog') ? 'border-white' : 'border-transparent'
                }`}
              >
                Catalog
              </Link>
              <Link 
                to="/search" 
                className={`hover:text-gray-200 pb-1 border-b-2 ${
                  isActive('/search') ? 'border-white' : 'border-transparent'
                }`}
              >
                Search
              </Link>
              {user?.is_admin && (
                <Link 
                  to="/settings" 
                  className={`hover:text-gray-200 pb-1 border-b-2 ${
                    isActive('/settings') ? 'border-white' : 'border-transparent'
                  }`}
                >
                  Settings
                </Link>
              )}
            </div>
          </div>
          <div className="flex items-center space-x-4">
            <span className="text-sm">Internal Demo</span>
            <span>{user?.username}</span>
            <button onClick={onLogout} className="bg-white text-mime-purple px-4 py-2 rounded hover:bg-gray-100">
              Logout
            </button>
          </div>
        </div>
      </div>
    </nav>
  )
}
