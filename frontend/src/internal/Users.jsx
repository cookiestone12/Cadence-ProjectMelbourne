import React, { useEffect, useState } from 'react'
import internal from './api'

export default function Users() {
  const [rows, setRows] = useState([])
  const [q, setQ] = useState('')
  const [sessions, setSessions] = useState({ userId: null, list: [] })

  const load = async () => {
    const { data } = await internal.get('/api/internal/portal/users', {
      params: q ? { q } : undefined,
    })
    setRows(data.rows)
  }
  useEffect(() => { load() }, [])

  const openSessions = async (uid) => {
    setSessions({ userId: uid, list: [] })
    const { data } = await internal.get(`/api/internal/portal/users/${uid}/sessions`)
    setSessions({ userId: uid, list: data.rows })
  }

  const provision = async () => {
    const username = window.prompt('Staff username?'); if (!username) return
    const email = window.prompt('Staff email?'); if (!email) return
    const password = window.prompt('Initial password?'); if (!password) return
    try {
      await internal.post('/api/internal/provision-staff-user', {
        username, email, password,
      })
      load()
    } catch (e) {
      alert(e?.response?.data?.detail || 'Provision failed')
    }
  }

  const deprovision = async (uid) => {
    if (!window.confirm('Deprovision this staff user?')) return
    try {
      // Backend takes the user_id in the body, not the URL
      // (see backend/routes/internal.py:deprovision_staff_user).
      await internal.post('/api/internal/deprovision-staff-user', {
        user_id: uid,
        role_note: 'deprovisioned via internal portal',
      })
      load()
    } catch (e) {
      alert(e?.response?.data?.detail || 'Deprovision failed')
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Users</h1>
        <button
          onClick={provision}
          className="px-3 py-1.5 text-sm bg-slate-900 text-white rounded-md"
        >
          + Provision staff user
        </button>
      </div>
      <div className="flex gap-2">
        <input
          className="border border-slate-300 rounded-md px-3 py-1.5 text-sm flex-1"
          placeholder="Search username or email…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && load()}
        />
        <button onClick={load} className="px-3 py-1.5 bg-slate-200 rounded-md text-sm">
          Search
        </button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="md:col-span-2 border border-slate-200 rounded-md overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-100 text-left">
              <tr>
                <th className="px-3 py-2">User</th>
                <th className="px-3 py-2">Email</th>
                <th className="px-3 py-2">Roles</th>
                <th className="px-3 py-2">Last login</th>
                <th className="px-3 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((u) => (
                <tr key={u.id} className="border-t border-slate-200">
                  <td className="px-3 py-2 font-medium">{u.username}</td>
                  <td className="px-3 py-2 text-slate-600">{u.email}</td>
                  <td className="px-3 py-2 text-xs">
                    {u.is_super_admin && <span className="mr-1 px-1.5 py-0.5 bg-amber-100 text-amber-800 rounded">Super</span>}
                    {u.is_cadence_staff && <span className="mr-1 px-1.5 py-0.5 bg-sky-100 text-sky-800 rounded">Staff</span>}
                    {u.is_admin && <span className="mr-1 px-1.5 py-0.5 bg-violet-100 text-violet-800 rounded">Admin</span>}
                    {!u.is_active && <span className="px-1.5 py-0.5 bg-red-100 text-red-700 rounded">Disabled</span>}
                  </td>
                  <td className="px-3 py-2 text-xs">{u.last_login_at?.slice(0, 16) || '—'}</td>
                  <td className="px-3 py-2 text-xs space-x-2">
                    <button onClick={() => openSessions(u.id)} className="text-sky-700 hover:underline">
                      Sessions
                    </button>
                    {u.is_cadence_staff && (
                      <button onClick={() => deprovision(u.id)} className="text-red-600 hover:underline">
                        Deprovision
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="border border-slate-200 rounded-md p-4 text-sm">
          <div className="font-medium mb-2">Active sessions</div>
          {!sessions.userId ? (
            <div className="text-slate-500 text-xs">Select a user.</div>
          ) : sessions.list.length === 0 ? (
            <div className="text-slate-500 text-xs">No active sessions.</div>
          ) : (
            <ul className="space-y-2 text-xs">
              {sessions.list.map((s) => (
                <li key={s.id} className="bg-slate-50 p-2 rounded">
                  <div className="font-mono">{s.ip_address || '?'}</div>
                  <div className="text-slate-500 truncate">{s.user_agent}</div>
                  <div className="text-slate-400 mt-1">expires {s.expires_at?.slice(0, 16)}</div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}
