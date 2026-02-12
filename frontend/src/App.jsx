import React, { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import axios from 'axios'

import HomePage from './pages/HomePage'
import RosterPage from './pages/RosterPage'
import CreatorDetailPage from './pages/CreatorDetailPage'
import NewCatalogPage from './pages/NewCatalogPage'
import ReportsPage from './pages/ReportsPage'
import ValuationPage from './pages/ValuationPage'
import Settings from './pages/Settings'
import Login from './pages/Login'
import AdminDashboard from './pages/AdminDashboard'
import WorksPage from './pages/WorksPage'
import ReleasesPage from './pages/ReleasesPage'
import ContractsPage from './pages/ContractsPage'
import ActionItemsPage from './pages/ActionItemsPage'
import RoyaltiesPage from './pages/RoyaltiesPage'
import PlacementsPage from './pages/PlacementsPage'
import SearchPage from './pages/SearchPage'
import UserGuidePage from './pages/UserGuidePage'
import TenantAdminPage from './pages/TenantAdminPage'
import CreativeDirectoryPage from './pages/CreativeDirectoryPage'
import RegistrationReportPage from './pages/RegistrationReportPage'
import Sidebar from './components/Sidebar'

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [sidebarOpen, setSidebarOpen] = useState(false)

  useEffect(() => {
    const token = localStorage.getItem('token')
    const storedUser = localStorage.getItem('user')
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
      setIsAuthenticated(true)
      if (storedUser) {
        try {
          setUser(JSON.parse(storedUser))
        } catch {
          setUser({ username: 'User', is_admin: false, is_super_admin: false })
        }
      } else {
        setUser({ username: 'User', is_admin: false, is_super_admin: false })
      }
    }
    setLoading(false)

    // Add axios interceptor to handle expired tokens
    const interceptor = axios.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          // Token expired or invalid - log user out
          localStorage.removeItem('token')
          delete axios.defaults.headers.common['Authorization']
          setIsAuthenticated(false)
          setUser(null)
        }
        return Promise.reject(error)
      }
    )

    return () => {
      axios.interceptors.response.eject(interceptor)
    }
  }, [])

  const handleLogin = (token, userData) => {
    localStorage.setItem('token', token)
    localStorage.setItem('user', JSON.stringify(userData))
    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
    setIsAuthenticated(true)
    setUser(userData)
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
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
          <Route path="/guide" element={<UserGuidePage />} />
          <Route path="*" element={<Navigate to="/login" />} />
        </Routes>
      </Router>
    )
  }

  return (
    <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <div className="min-h-screen bg-gray-100 flex">
        <Sidebar 
          user={user} 
          onLogout={handleLogout} 
          isOpen={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
        />
        <main className="flex-1 overflow-auto bg-[#F5F7F4]">
          <div className="lg:hidden sticky top-0 z-30 bg-white border-b border-gray-200 px-4 py-3">
            <button
              onClick={() => setSidebarOpen(true)}
              className="text-gray-600 hover:text-gray-900"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          </div>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/roster" element={<RosterPage />} />
            <Route path="/roster/:id" element={<CreatorDetailPage />} />
            <Route path="/directory" element={<CreativeDirectoryPage />} />
            <Route path="/catalog" element={<NewCatalogPage />} />
            <Route path="/works" element={<WorksPage />} />
            <Route path="/releases" element={<ReleasesPage />} />
            <Route path="/contracts" element={<ContractsPage />} />
            <Route path="/actions" element={<ActionItemsPage />} />
            <Route path="/royalties" element={<RoyaltiesPage />} />
            <Route path="/placements" element={<PlacementsPage />} />
            <Route path="/reports" element={<ReportsPage />} />
            <Route path="/valuation" element={<ValuationPage />} />
            <Route path="/registration-reports" element={<RegistrationReportPage />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/guide" element={<UserGuidePage />} />
            <Route path="/org-admin" element={<TenantAdminPage />} />
            {user?.is_super_admin && (
              <Route path="/admin" element={<AdminDashboard />} />
            )}
            <Route path="*" element={<Navigate to="/" />} />
          </Routes>
          <div className="flex items-center justify-center py-6 opacity-30">
            <img src="/rythm-logo.png" alt="Powered by Rythm" className="h-6 w-auto object-contain" />
          </div>
        </main>
      </div>
    </Router>
  )
}

export default App
