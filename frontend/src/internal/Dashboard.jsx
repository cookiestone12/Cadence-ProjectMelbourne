import React, { useEffect, useState } from 'react'
import internal from './api'

function Stat({ label, value }) {
  return (
    <div className="border border-slate-200 rounded-lg p-4 bg-slate-50">
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-slate-900">{value}</div>
    </div>
  )
}

export default function Dashboard() {
  const [data, setData] = useState(null)
  const [health, setHealth] = useState('checking')
  const [err, setErr] = useState('')

  const load = async () => {
    try {
      const { data } = await internal.get('/api/internal/portal/dashboard')
      setData(data)
    } catch (e) {
      setErr(e?.response?.data?.detail || 'Failed to load dashboard')
    }
  }

  const pingHealth = async () => {
    try {
      const r = await fetch('/health')
      setHealth(r.ok ? 'ok' : `error ${r.status}`)
    } catch {
      setHealth('down')
    }
  }

  useEffect(() => {
    load()
    pingHealth()
    const a = setInterval(load, 30_000)
    const b = setInterval(pingHealth, 30_000)
    return () => { clearInterval(a); clearInterval(b) }
  }, [])

  if (err) return <div className="text-red-600 text-sm">{err}</div>
  if (!data) return <div className="text-slate-500 text-sm">Loading…</div>

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <p className="text-sm text-slate-500">Platform-wide operational health</p>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Stat label="Organizations" value={data.org_count} />
        <Stat label="Users" value={data.user_count} />
        <Stat label="Songs" value={data.song_count} />
        <Stat label="Statements (30d)" value={data.statements_30d} />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <Stat label="DB" value={data.db_status} />
        <Stat label="/health" value={health} />
        <Stat label="Backend health" value={data.health_status} />
      </div>

      <section>
        <h2 className="font-semibold text-slate-900 mb-2">Scheduled jobs</h2>
        {data.scheduler_jobs.length === 0 ? (
          <div className="text-sm text-slate-500">No scheduler jobs reported.</div>
        ) : (
          <table className="w-full text-sm border border-slate-200 rounded-md overflow-hidden">
            <thead className="bg-slate-100 text-left">
              <tr>
                <th className="px-3 py-2">Job</th>
                <th className="px-3 py-2">Last run</th>
                <th className="px-3 py-2">Next run</th>
              </tr>
            </thead>
            <tbody>
              {data.scheduler_jobs.map((j) => (
                <tr key={j.id} className="border-t border-slate-200">
                  <td className="px-3 py-2 font-mono text-xs">{j.name}</td>
                  <td className="px-3 py-2 text-xs">{j.last_run_time || '—'}</td>
                  <td className="px-3 py-2 text-xs">{j.next_run_time || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section>
        <h2 className="font-semibold text-slate-900 mb-2">Recent audit log</h2>
        <div className="border border-slate-200 rounded-md overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-100 text-left">
              <tr>
                <th className="px-3 py-2">When</th>
                <th className="px-3 py-2">Org</th>
                <th className="px-3 py-2">User</th>
                <th className="px-3 py-2">Action</th>
                <th className="px-3 py-2">Entity</th>
              </tr>
            </thead>
            <tbody>
              {data.recent_audit.map((r) => (
                <tr key={r.id} className="border-t border-slate-200">
                  <td className="px-3 py-2 text-xs text-slate-500">{r.created_at}</td>
                  <td className="px-3 py-2">{r.organization_id}</td>
                  <td className="px-3 py-2">{r.user_name || '—'}</td>
                  <td className="px-3 py-2 font-mono text-xs">{r.action}</td>
                  <td className="px-3 py-2">
                    {r.entity_type}{r.entity_name ? ` · ${r.entity_name}` : ''}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
