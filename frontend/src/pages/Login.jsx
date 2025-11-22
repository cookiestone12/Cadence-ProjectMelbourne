import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'

export default function Login({ onLogin }) {
  const [isRegister, setIsRegister] = useState(false)
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    
    try {
      const endpoint = isRegister ? '/api/auth/register' : '/api/auth/login'
      const payload = isRegister 
        ? { username, email, password }
        : { username, password }
      
      const response = await axios.post(endpoint, payload)
      onLogin(response.data.access_token, response.data.user)
      navigate('/dashboard')
    } catch (err) {
      setError(err.response?.data?.detail || 'An error occurred')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-void-black">
      <div className="bg-surface-black border border-border-grey p-8 rounded shadow-lg max-w-md w-full hover:border-signal-red transition-colors duration-200">
        <div className="flex justify-center mb-6">
          <img src="/ampersound-logo-3d.png" alt="Ampersound Intelligence" className="h-24" />
        </div>
        <h2 className="text-3xl font-bold font-heading text-center mb-6 text-signal-red uppercase tracking-wide">
          Ampersound Catalog Intelligence
        </h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1 text-tech-grey uppercase text-xs tracking-wide">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-2 bg-black bg-opacity-50 border border-border-grey rounded text-white focus:ring-2 focus:ring-signal-red focus:border-signal-red"
              required
            />
          </div>
          {isRegister && (
            <div>
              <label className="block text-sm font-medium mb-1 text-tech-grey uppercase text-xs tracking-wide">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-2 bg-black bg-opacity-50 border border-border-grey rounded text-white focus:ring-2 focus:ring-signal-red focus:border-signal-red"
                required
              />
            </div>
          )}
          <div>
            <label className="block text-sm font-medium mb-1 text-tech-grey uppercase text-xs tracking-wide">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2 bg-black bg-opacity-50 border border-border-grey rounded text-white focus:ring-2 focus:ring-signal-red focus:border-signal-red"
              required
            />
          </div>
          {error && <p className="text-signal-red text-sm border border-signal-red bg-signal-red bg-opacity-10 p-2 rounded">{error}</p>}
          <button
            type="submit"
            className="w-full bg-signal-red text-white py-2 rounded shadow-red-glow hover:shadow-red-glow-intense hover:scale-105 transition-all duration-200 font-bold uppercase text-sm tracking-wide"
          >
            {isRegister ? 'Register' : 'Login'}
          </button>
        </form>
        <p className="mt-4 text-center text-sm text-tech-grey">
          {isRegister ? 'Already have an account?' : "Don't have an account?"}
          <button
            onClick={() => setIsRegister(!isRegister)}
            className="ml-2 text-signal-red hover:underline font-bold"
          >
            {isRegister ? 'Login' : 'Register'}
          </button>
        </p>
      </div>
    </div>
  )
}
