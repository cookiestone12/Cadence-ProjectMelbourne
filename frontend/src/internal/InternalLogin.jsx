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
      // cookie-login sets the JWT as an httpOnly cookie; we only
      // persist a minimal display profile in localStorage so the
      // sidebar can show the staff member's name.
      const { data } = await internal.post(
        '/api/internal/portal/cookie-login',
        { username, password }
      )
      localStorage.setItem('internal_user', JSON.stringify(data.user))
      navigate('/internal/dashboard')
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
