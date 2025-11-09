import React, { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import Home from './pages/Home'
import CatalogView from './pages/CatalogView'
import Search from './pages/Search'
import SongDetail from './pages/SongDetail'
import Settings from './pages/Settings'
import Login from './pages/Login'
import Navigation from './components/Navigation'

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [user, setUser] = useState(null)

  useEffect(() => {
    const token = localStorage.getItem('token')
    const userData = localStorage.getItem('user')
    if (token && userData) {
      setIsAuthenticated(true)
      setUser(JSON.parse(userData))
    }
  }, [])

  const handleLogin = (token, userData) => {
    localStorage.setItem('token', token)
    localStorage.setItem('user', JSON.stringify(userData))
    setIsAuthenticated(true)
    setUser(userData)
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setIsAuthenticated(false)
    setUser(null)
  }

  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        {isAuthenticated && <Navigation user={user} onLogout={handleLogout} />}
        <Routes>
          <Route path="/login" element={
            isAuthenticated ? <Navigate to="/catalog" /> : <Login onLogin={handleLogin} />
          } />
          <Route path="/" element={
            isAuthenticated ? <Navigate to="/catalog" /> : <Home />
          } />
          <Route path="/catalog" element={
            isAuthenticated ? <CatalogView /> : <Navigate to="/login" />
          } />
          <Route path="/search" element={
            isAuthenticated ? <Search /> : <Navigate to="/login" />
          } />
          <Route path="/song/:id" element={
            isAuthenticated ? <SongDetail /> : <Navigate to="/login" />
          } />
          <Route path="/settings" element={
            isAuthenticated && user?.is_admin ? <Settings /> : <Navigate to="/catalog" />
          } />
        </Routes>
      </div>
    </Router>
  )
}

export default App
