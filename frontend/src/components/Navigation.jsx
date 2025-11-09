import React from 'react'
import { Link } from 'react-router-dom'

export default function Navigation({ user, onLogout }) {
  return (
    <nav className="bg-gradient-to-r from-mime-purple to-mime-orange text-white shadow-lg">
      <div className="container mx-auto px-4 py-4">
        <div className="flex justify-between items-center">
          <div className="flex items-center space-x-8">
            <h1 className="text-2xl font-bold">MIME Catalog Intelligence</h1>
            <div className="flex space-x-4">
              <Link to="/dashboard" className="hover:text-gray-200">Dashboard</Link>
              <Link to="/upload" className="hover:text-gray-200">Upload</Link>
              {user?.is_admin && (
                <Link to="/settings" className="hover:text-gray-200">Settings</Link>
              )}
            </div>
          </div>
          <div className="flex items-center space-x-4">
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
