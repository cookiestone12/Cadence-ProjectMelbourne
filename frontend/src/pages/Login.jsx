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
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-mime-purple to-mime-orange">
      <div className="bg-white p-8 rounded-lg shadow-xl max-w-md w-full">
        <h2 className="text-3xl font-bold text-center mb-6 text-mime-purple">
          MIME Catalog Intelligence
        </h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-2 border rounded focus:ring-2 focus:ring-mime-purple"
              required
            />
          </div>
          {isRegister && (
            <div>
              <label className="block text-sm font-medium mb-1">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-2 border rounded focus:ring-2 focus:ring-mime-purple"
                required
              />
            </div>
          )}
          <div>
            <label className="block text-sm font-medium mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2 border rounded focus:ring-2 focus:ring-mime-purple"
              required
            />
          </div>
          {error && <p className="text-red-500 text-sm">{error}</p>}
          <button
            type="submit"
            className="w-full bg-mime-purple text-white py-2 rounded hover:bg-opacity-90"
          >
            {isRegister ? 'Register' : 'Login'}
          </button>
        </form>
        <p className="mt-4 text-center text-sm">
          {isRegister ? 'Already have an account?' : "Don't have an account?"}
          <button
            onClick={() => setIsRegister(!isRegister)}
            className="ml-2 text-mime-purple hover:underline"
          >
            {isRegister ? 'Login' : 'Register'}
          </button>
        </p>
      </div>
    </div>
  )
}
