import React, { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import axios from 'axios'

import HomePage from './pages/HomePage'
import RosterPage from './pages/RosterPage'
import CreatorDetailPage from './pages/CreatorDetailPage'
import CatalogView from './pages/CatalogView'
import PlacementsPage from './pages/PlacementsPage'
import ReportsPage from './pages/ReportsPage'
import ValuationPage from './pages/ValuationPage'
import Settings from './pages/Settings'
import Login from './pages/Login'
import Sidebar from './components/Sidebar'

axios.defaults.baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
      setIsAuthenticated(true)
      setUser({ username: 'Demo User', role: 'Admin' })
    }
    setLoading(false)
  }, [])

  const handleLogin = (token, userData) => {
    localStorage.setItem('token', token)
    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
    setIsAuthenticated(true)
    setUser(userData)
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    delete axios.defaults.headers.common['Authorization']
    setIsAuthenticated(false)
    setUser(null)
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-gray-600">Loading...</div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return (
      <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Routes>
          <Route path="/login" element={<Login onLogin={handleLogin} />} />
          <Route path="*" element={<Navigate to="/login" />} />
        </Routes>
      </Router>
    )
  }

  return (
    <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <div className="min-h-screen bg-gray-100 flex">
        <Sidebar user={user} onLogout={handleLogout} />
        <main className="flex-1 overflow-auto">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/roster" element={<RosterPage />} />
            <Route path="/roster/:id" element={<CreatorDetailPage />} />
            <Route path="/catalog" element={<CatalogView />} />
            <Route path="/placements" element={<PlacementsPage />} />
            <Route path="/reports" element={<ReportsPage />} />
            <Route path="/valuation" element={<ValuationPage />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="*" element={<Navigate to="/" />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

export default App
