import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import internal from './api'

export default function InternalLogin() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const submit = async (e) => {
    e.preventDefault()
    setErr(''); setLoading(true)
    try {
      // Two-step login per spec:
      //   1. POST /api/auth/login to verify credentials and create a
      //      regular UserSession row (returns the JWT in the body).
      //   2. Hand the token off to /cookie-login which re-uses the same
      //      session and sets the cadence_internal_token httpOnly
      //      cookie. The token never lives in localStorage on this side.
      const auth = await internal.post('/api/auth/login', { username, password })
      const accessToken = auth?.data?.access_token
      if (!accessToken) throw new Error('Login response missing token')
      const { data } = await internal.post(
        '/api/internal/portal/cookie-login',
        { access_token: accessToken }
      )
      localStorage.setItem('internal_user', JSON.stringify(data.user))
      window.location.href = '/internal/dashboard'
    } catch (e) {
      setErr(e?.response?.data?.detail || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
      <form
        onSubmit={submit}
        className="bg-white rounded-xl shadow-xl p-8 w-full max-w-sm space-y-4"
      >
        <div>
          <div className="text-xl font-semibold text-slate-900">Cadence Staff</div>
          <div className="text-sm text-slate-500">Internal Portal sign-in</div>
        </div>
        <input
          autoFocus
          className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm"
          placeholder="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
        <input
          type="password"
          className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        {err && <div className="text-sm text-red-600">{err}</div>}
        <button
          disabled={loading}
          className="w-full bg-slate-900 text-white py-2 rounded-md text-sm font-medium disabled:opacity-50"
        >
          {loading ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
    </div>
  )
}
