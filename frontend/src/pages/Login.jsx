import React, { useState } from 'react'
import axios from 'axios'

export default function Login({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const response = await axios.post('/api/auth/login', {
        username,
        password
      })

      const { access_token } = response.data
      onLogin(access_token, { username, role: 'Admin' })
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#A020F0] via-[#E540AC] to-[#7D7AFF] flex items-center justify-center p-4">
      <div className="bg-white rounded-[24px] shadow-[0px_20px_60px_rgba(0,0,0,0.15)] p-8 w-full max-w-md">
        <div className="text-center mb-8">
          <div className="flex justify-center mb-4">
            <img 
              src="/logo-medium.png" 
              alt="Ampersound Intelligence" 
              className="h-20 w-auto"
            />
          </div>
          <h1 className="text-[28px] font-semibold text-[#1D1D1F] mb-1">
            Ampersound Intelligence
          </h1>
          <p className="text-[17px] text-[#86868B]">Catalog Manager</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label htmlFor="username" className="block text-[15px] font-medium text-[#1D1D1F] mb-2">
              Username
            </label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-3 border border-[rgba(0,0,0,0.1)] rounded-xl focus:ring-2 focus:ring-[#A020F0] focus:border-transparent text-[#1D1D1F] bg-white text-[17px] transition-all duration-200"
              required
              disabled={loading}
              autoComplete="username"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-[15px] font-medium text-[#1D1D1F] mb-2">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-3 border border-[rgba(0,0,0,0.1)] rounded-xl focus:ring-2 focus:ring-[#A020F0] focus:border-transparent text-[#1D1D1F] bg-white text-[17px] transition-all duration-200"
              autoComplete="current-password"
              required
              disabled={loading}
            />
          </div>

          {error && (
            <div className="bg-[rgba(255,59,48,0.1)] border border-[rgba(255,59,48,0.2)] text-[#FF3B30] px-4 py-3 rounded-xl text-[15px]">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-gradient-to-r from-[#A020F0] to-[#E540AC] text-white py-3.5 rounded-xl font-semibold text-[17px] hover:shadow-lg hover:shadow-purple-500/30 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <div className="mt-6 p-4 bg-[#F2F2F5] rounded-xl">
          <p className="text-[13px] text-[#86868B] text-center mb-2">Demo Credentials</p>
          <div className="text-[13px] text-[#1D1D1F] space-y-1 text-center">
            <p><span className="font-medium">Username:</span> admin</p>
            <p><span className="font-medium">Password:</span> demo123</p>
          </div>
        </div>
      </div>
    </div>
  )
}
