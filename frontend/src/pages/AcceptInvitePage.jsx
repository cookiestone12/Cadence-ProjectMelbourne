import React, { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import axios from 'axios'

export default function AcceptInvitePage({ onLogin }) {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const token = params.get('token') || ''

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token) setError('This invitation link is missing its token. Please use the link from your invitation email.')
  }, [token])

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    if (!token) return
    if (!username.trim()) { setError('Pick a username.'); return }
    if (password.length < 6) { setError('Password must be at least 6 characters.'); return }
    if (password !== confirm) { setError('Passwords do not match.'); return }

    setSubmitting(true)
    try {
      const res = await axios.post('/api/auth/accept-invite', {
        token,
        username: username.trim(),
        password,
      })
      const { access_token, user } = res.data || {}
      if (access_token) {
        localStorage.setItem('token', access_token)
        if (user) localStorage.setItem('user', JSON.stringify(user))
        axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
        if (typeof onLogin === 'function') {
          onLogin(access_token, user)
        }
        navigate('/', { replace: true })
      } else {
        navigate('/login', { replace: true })
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not accept invitation. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#FAFBF9] px-4">
      <div className="w-full max-w-md bg-white rounded-[18px] shadow-[0px_4px_18px_rgba(0,0,0,0.08)] p-8">
        <h1 className="text-[26px] font-medium text-[#3D4A44] mb-2">Accept your invitation</h1>
        <p className="text-[14px] text-[#7A8580] mb-6">
          Pick a username and set a password to finish setting up your Cadence account.
        </p>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-50 text-red-700 text-[13px] border border-red-200">
            {error}
          </div>
        )}

        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="block text-[13px] font-medium text-[#3D4A44] mb-1">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              disabled={submitting || !token}
              className="w-full px-3 py-2 border border-[rgba(59,77,67,0.18)] rounded-lg focus:outline-none focus:border-[#5B8A72]"
              required
            />
          </div>
          <div>
            <label className="block text-[13px] font-medium text-[#3D4A44] mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
              disabled={submitting || !token}
              className="w-full px-3 py-2 border border-[rgba(59,77,67,0.18)] rounded-lg focus:outline-none focus:border-[#5B8A72]"
              required
              minLength={6}
            />
          </div>
          <div>
            <label className="block text-[13px] font-medium text-[#3D4A44] mb-1">Confirm password</label>
            <input
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              autoComplete="new-password"
              disabled={submitting || !token}
              className="w-full px-3 py-2 border border-[rgba(59,77,67,0.18)] rounded-lg focus:outline-none focus:border-[#5B8A72]"
              required
              minLength={6}
            />
          </div>
          <button
            type="submit"
            disabled={submitting || !token}
            className="w-full py-2.5 rounded-lg bg-[#5B8A72] text-white font-medium hover:bg-[#4f7a64] disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
          >
            {submitting ? 'Setting up your account…' : 'Accept invitation'}
          </button>
        </form>

        <div className="mt-5 text-[12px] text-[#7A8580] text-center">
          Already have a Cadence account?{' '}
          <a href="/login" className="text-[#5B8A72] hover:underline">Sign in</a>
        </div>
      </div>
    </div>
  )
}
