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
  const [isAuthenticated, setIsAuthenticated] = useState(true)
  const [user, setUser] = useState({ username: 'Demo User', is_admin: true })

  const handleLogout = () => {
  }

  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        <Navigation user={user} onLogout={handleLogout} />
        <Routes>
          <Route path="/login" element={<Navigate to="/catalog" />} />
          <Route path="/" element={<Home />} />
          <Route path="/catalog" element={<CatalogView />} />
          <Route path="/search" element={<Search />} />
          <Route path="/catalog/songs/:id" element={<SongDetail />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </div>
    </Router>
  )
}

export default App
