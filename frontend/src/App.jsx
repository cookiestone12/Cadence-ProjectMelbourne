import React, { useState, useEffect, Component } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import axios from 'axios'
import { apiUrl } from './lib/apiBase'

// Global axios request interceptor: route every legacy `/api/...` call
// through the single API_BASE constant in lib/apiBase.js (currently
// `/api/v1`). This is the one place every existing call site reads the
// base URL from — change API_BASE there and every request follows. The
// helper is a no-op for absolute URLs and for paths already prefixed
// with `/api/v1/`.
axios.interceptors.request.use((config) => {
  if (config.url) {
    config.url = apiUrl(config.url)
  }
  return config
})

class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }
  componentDidCatch(error, info) {
    console.error('Page crashed:', error, info)
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center h-full p-8">
          <div className="bg-white rounded-2xl border border-[rgba(59,77,67,0.12)] p-8 max-w-md text-center shadow-sm">
            <h2 className="text-xl font-bold text-[#3D4A44] mb-2">Something went wrong</h2>
            <p className="text-[#7A8580] mb-4">This page ran into an issue. Try refreshing or going back.</p>
            <button
              onClick={() => { this.setState({ hasError: false, error: null }); window.location.href = '/' }}
              className="px-5 py-2 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] transition-colors text-sm font-medium"
            >
              Go to Home
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

import HomePage from './pages/HomePage'
import RosterPage from './pages/RosterPage'
import CreatorDetailPage from './pages/CreatorDetailPage'
import NewCatalogPage from './pages/NewCatalogPage'
import ReportsPage from './pages/ReportsPage'
import ValuationPage from './pages/ValuationPage'
import Settings from './pages/Settings'
import Login from './pages/Login'
import ForcedChangePassword from './pages/ForcedChangePassword'
import AdminDashboard from './pages/AdminDashboard'
import LeadsPage from './pages/LeadsPage'
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
import AuditPage from './pages/AuditPage'
import BriefBuilderPage from './pages/BriefBuilderPage'
import StorageScanPage from './pages/StorageScanPage'
import CreditsPage from './pages/CreditsPage'
import ClientPortalPage from './pages/ClientPortalPage'
import SharedContactsPage from './pages/SharedContactsPage'
import SharedCreditsPage from './pages/SharedCreditsPage'
import SharedWithMePage from './pages/SharedWithMePage'
import SupportPage from './pages/SupportPage'
import LandingPage from './pages/LandingPage'
import CareersPage from './pages/CareersPage'
import InvestorsPage from './pages/InvestorsPage'
import AboutPage from './pages/AboutPage'
import TermsPage from './pages/TermsPage'
import PrivacyPolicyPage from './pages/PrivacyPolicyPage'
import AntiFraudPage from './pages/AntiFraudPage'
import ContentPolicyPage from './pages/ContentPolicyPage'
import BetaTermsPage from './pages/BetaTermsPage'
import HelpCenterPage from './pages/HelpCenterPage'
import WhatIsCadencePage from './pages/WhatIsCadencePage'
import AcceptInvitePage from './pages/AcceptInvitePage'
import InternalLayout from './internal/InternalLayout'
import InternalLogin from './internal/InternalLogin'
import InternalDashboard from './internal/Dashboard'
import InternalOrganizations from './internal/Organizations'
import InternalUsers from './internal/Users'
import InternalDatabase from './internal/Database'
import InternalLogs from './internal/Logs'
import InternalSourceViewer from './internal/SourceViewer'
import InternalConfig from './internal/Config'
import InternalOnboarding from './internal/Onboarding'
import Sidebar from './components/Sidebar'
import AssistantChat from './components/AssistantChat'
import OnboardingTour from './components/OnboardingTour'

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)
  // Task #206 — show the one-time post-login onboarding tour for any
  // authenticated user whose `onboarding_completed_at` is still null.
  // Client-portal users get a stripped-down app surface, so we skip the
  // tour for them (it talks about Catalog/Royalties they don't see).
  const showOnboarding =
    isAuthenticated &&
    user &&
    !user.must_change_password &&
    !user.onboarding_completed_at &&
    user.role !== 'CLIENT'

  const handleOnboardingDismiss = () => {
    const updated = { ...user, onboarding_completed_at: new Date().toISOString() }
    localStorage.setItem('user', JSON.stringify(updated))
    setUser(updated)
  }

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

  // Internal staff portal lives outside the regular client auth flow.
  // It uses an httpOnly cookie (cadence_internal_token) for auth and its own
  // login screen; we serve the routes here regardless of whether the
  // main client app is authenticated.
  if (typeof window !== 'undefined' && window.location.pathname.startsWith('/internal')) {
    // Auth lives in an httpOnly cookie that JS cannot read; we use the
    // presence of the non-sensitive `internal_user` profile blob as a
    // hint that the user has logged in. If the cookie is actually
    // missing or expired, the api.js interceptor will catch the 401 on
    // the next portal call and bounce back to /internal/login.
    const internalUser = localStorage.getItem('internal_user')
    return (
      <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Routes>
          <Route path="/internal/login" element={<InternalLogin />} />
          <Route
            path="/internal"
            element={internalUser ? <InternalLayout /> : <Navigate to="/internal/login" />}
          >
            <Route index element={<Navigate to="/internal/dashboard" replace />} />
            <Route path="dashboard" element={<InternalDashboard />} />
            <Route path="organizations" element={<InternalOrganizations />} />
            <Route path="users" element={<InternalUsers />} />
            <Route path="database" element={<InternalDatabase />} />
            <Route path="logs" element={<InternalLogs />} />
            <Route path="source" element={<InternalSourceViewer />} />
            <Route path="config" element={<InternalConfig />} />
            <Route path="onboarding" element={<InternalOnboarding />} />
          </Route>
        </Routes>
      </Router>
    )
  }

  // Task #207 — accounts provisioned by an admin land with a temporary
  // password and must_change_password=true. Trap them on the forced
  // change-password screen until they rotate the credential. Runs even
  // for super-admins / internal-looking users since they're outside the
  // /internal portal here.
  if (isAuthenticated && user?.must_change_password) {
    const handlePasswordChanged = () => {
      const updated = { ...user, must_change_password: false }
      localStorage.setItem('user', JSON.stringify(updated))
      setUser(updated)
    }
    return (
      <ForcedChangePassword
        user={user}
        onPasswordChanged={handlePasswordChanged}
        onLogout={handleLogout}
      />
    )
  }

  if (!isAuthenticated) {
    return (
      <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/careers" element={<CareersPage />} />
          <Route path="/investors" element={<InvestorsPage />} />
          <Route path="/about" element={<AboutPage />} />
          <Route path="/terms" element={<TermsPage />} />
          <Route path="/privacy" element={<PrivacyPolicyPage />} />
          <Route path="/anti-fraud" element={<AntiFraudPage />} />
          <Route path="/content-policy" element={<ContentPolicyPage />} />
          <Route path="/beta-terms" element={<BetaTermsPage />} />
          <Route path="/help" element={<HelpCenterPage />} />
          <Route path="/what-is-cadence" element={<WhatIsCadencePage />} />
          <Route path="/login" element={<Login onLogin={handleLogin} />} />
          <Route path="/accept-invite" element={<AcceptInvitePage onLogin={handleLogin} />} />
          <Route path="/guide" element={<UserGuidePage />} />
          <Route path="/shared/contacts/:token" element={<SharedContactsPage />} />
          <Route path="/shared/credits/:token" element={<SharedCreditsPage />} />
          <Route path="*" element={<Navigate to="/" />} />
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
        <main className="flex-1 min-w-0 bg-[#F5F7F4]">
          <div className="lg:hidden sticky top-0 z-30 bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
            <button
              onClick={() => setSidebarOpen(true)}
              aria-label="Open menu"
              className="text-gray-600 hover:text-gray-900"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <button
              onClick={() => {
                if (isRefreshing) return
                setIsRefreshing(true)
                setTimeout(() => window.location.reload(), 200)
              }}
              disabled={isRefreshing}
              aria-label="Refresh page"
              className="text-gray-600 hover:text-gray-900 disabled:opacity-60"
            >
              <svg
                className={`w-6 h-6 ${isRefreshing ? 'animate-spin' : ''}`}
                fill="none"
                stroke="currentColor"
                strokeWidth={2}
                viewBox="0 0 24 24"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M1 4v6h6" />
                <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
              </svg>
            </button>
          </div>
          <ErrorBoundary>
          <Routes>
            {user?.role === 'CLIENT' ? (
              <>
                <Route path="/client-portal" element={<ClientPortalPage />} />
                <Route path="/support" element={<SupportPage />} />
                <Route path="/settings" element={<Settings />} />
                <Route path="/guide" element={<UserGuidePage />} />
                <Route path="*" element={<Navigate to="/client-portal" />} />
              </>
            ) : (
              <>
                <Route path="/" element={<HomePage />} />
                <Route path="/search" element={<SearchPage />} />
                <Route path="/roster" element={<RosterPage />} />
                <Route path="/roster/:id" element={<CreatorDetailPage />} />
                <Route path="/directory" element={<CreativeDirectoryPage />} />
                <Route path="/catalog" element={<NewCatalogPage />} />
                <Route path="/catalog/unreleased" element={<WorksPage />} />
                <Route path="/works" element={<Navigate to="/catalog/unreleased" replace />} />
                <Route path="/releases" element={<ReleasesPage />} />
                <Route path="/contracts" element={<ContractsPage />} />
                <Route path="/actions" element={<ActionItemsPage />} />
                <Route path="/royalties" element={<RoyaltiesPage />} />
                <Route path="/placements" element={<PlacementsPage />} />
                <Route path="/reports" element={<ReportsPage />} />
                <Route path="/valuation" element={<ValuationPage />} />
                <Route path="/registration-reports" element={<RegistrationReportPage />} />
                <Route path="/audit" element={<AuditPage />} />
                <Route path="/sync-reports" element={<Navigate to="/placements?tab=reports" replace />} />
                <Route path="/brief-builder" element={<BriefBuilderPage />} />
                <Route path="/credits" element={<CreditsPage />} />
                <Route path="/storage-scan" element={<StorageScanPage />} />
                <Route path="/shared-with-me" element={<SharedWithMePage />} />
                <Route path="/support" element={<SupportPage />} />
                <Route path="/client-portal" element={<ClientPortalPage />} />
                <Route path="/settings" element={<Settings />} />
                <Route path="/guide" element={<UserGuidePage />} />
                <Route path="/shared/contacts/:token" element={<SharedContactsPage />} />
                <Route path="/shared/credits/:token" element={<SharedCreditsPage />} />
                <Route path="/org-admin" element={<TenantAdminPage />} />
                {user?.is_super_admin && (
                  <Route path="/admin" element={<AdminDashboard />} />
                )}
                {user?.is_super_admin && (
                  <Route path="/admin/leads" element={<LeadsPage />} />
                )}
                <Route path="*" element={<Navigate to="/" />} />
              </>
            )}
          </Routes>
          </ErrorBoundary>
          <div className="flex items-center justify-center gap-2 py-6 opacity-30">
            <img src="/cadence-logo.png" alt="Powered by Cadence" className="h-6 w-auto object-contain" />
            <span className="text-[9px] font-semibold tracking-wide uppercase text-[#5B8A72] bg-[#5B8A72]/10 px-1.5 py-0.5 rounded-md">Beta</span>
          </div>
        </main>
        <AssistantChat user={user} />
        {showOnboarding && (
          <OnboardingTour user={user} onDismiss={handleOnboardingDismiss} />
        )}
      </div>
    </Router>
  )
}

export default App
