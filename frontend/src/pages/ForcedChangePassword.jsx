import React, { useState } from 'react'
import axios from 'axios'

export default function ForcedChangePassword({ user, onPasswordChanged, onLogout }) {
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    if (newPassword !== confirmPassword) {
      setError('New passwords do not match.')
      return
    }
    if (newPassword.length < 6) {
      setError('New password must be at least 6 characters.')
      return
    }
    if (newPassword === currentPassword) {
      setError('Pick a new password different from the temporary one.')
      return
    }

    setLoading(true)
    try {
      await axios.put('/api/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword,
      })
      onPasswordChanged()
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not change password. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#5B8A72] via-[#7BA594] to-[#6B9A84] flex items-center justify-center p-4">
      <div className="bg-white/95 backdrop-blur-xl rounded-[24px] shadow-am-xl p-8 w-full max-w-md">
        <div className="text-center mb-6">
          <img
            src="/cadence-logo.png"
            alt="Cadence"
            className="h-[110px] w-auto mx-auto drop-shadow-md"
          />
          <h1 className="mt-4 text-xl font-bold text-[#3D4A44]">Set a new password</h1>
          <p className="mt-2 text-sm text-[#7A8580]">
            Your account was created with a temporary password. Pick a new one
            to continue into Cadence{user?.username ? `, ${user.username}` : ''}.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-[14px] font-medium text-am-text mb-2">
              Temporary password
            </label>
            <input
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              className="am-input"
              required
              disabled={loading}
              autoComplete="current-password"
            />
          </div>

          <div>
            <label className="block text-[14px] font-medium text-am-text mb-2">
              New password
            </label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="am-input"
              required
              minLength={6}
              disabled={loading}
              autoComplete="new-password"
            />
          </div>

          <div>
            <label className="block text-[14px] font-medium text-am-text mb-2">
              Confirm new password
            </label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="am-input"
              required
              minLength={6}
              disabled={loading}
              autoComplete="new-password"
            />
          </div>

          {error && (
            <div className="bg-red-50 border border-red-100 text-am-error px-4 py-3 rounded-xl text-[14px]">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full am-btn am-btn-primary am-btn-pill text-[17px] font-semibold py-3.5"
          >
            {loading ? 'Updating…' : 'Update password'}
          </button>

          <button
            type="button"
            onClick={onLogout}
            className="w-full text-center text-sm text-[#7A8580] hover:text-[#3D4A44] mt-2"
          >
            Sign out
          </button>
        </form>
      </div>
    </div>
  )
}
