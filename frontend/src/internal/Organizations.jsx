import React, { useEffect, useMemo, useState } from 'react'
import internal from './api'

const SORTS = {
  newest: (a, b) => b.id - a.id,
  oldest: (a, b) => a.id - b.id,
  name: (a, b) => (a.name || '').localeCompare(b.name || ''),
  size: (a, b) => (b.song_count + b.creator_count) - (a.song_count + a.creator_count),
}

export default function Organizations() {
  const [rows, setRows] = useState([])
  const [q, setQ] = useState('')
  const [type, setType] = useState('')
  const [sort, setSort] = useState('newest')
  const [selected, setSelected] = useState(null)
  const [detail, setDetail] = useState(null)
  const [viewAs, setViewAs] = useState(false)
  const [accessCode, setAccessCode] = useState(null)

  const load = async () => {
    const { data } = await internal.get('/api/internal/portal/organizations', {
      params: q ? { q } : undefined,
    })
    setRows(data.rows)
  }

  const visibleRows = useMemo(() => {
    let list = rows
    if (type) list = list.filter((r) => r.type === type)
    return list.slice().sort(SORTS[sort] || SORTS.newest)
  }, [rows, sort, type])

  const openDetail = async (id) => {
    setSelected(id); setDetail(null); setAccessCode(null); setViewAs(false)
    const { data } = await internal.get(`/api/internal/portal/organizations/${id}`)
    setDetail(data)
  }

  const fetchAccessCode = async () => {
    if (!selected) return
    try {
      const { data } = await internal.get(
        `/api/internal/portal/organizations/${selected}/access-code`
      )
      setAccessCode(data.access_code)
    } catch (e) {
      alert(e?.response?.data?.detail || 'Failed to fetch access code')
    }
  }

  const createOrg = async () => {
    const name = window.prompt('Organization name?')
    if (!name) return
    const orgType = window.prompt('Type (MANAGER, LABEL, PUBLISHER):', 'MANAGER') || 'MANAGER'
    try {
      await internal.post('/api/admin/organizations', { name, type: orgType })
      load()
    } catch (e) {
      alert(e?.response?.data?.detail || 'Create failed (master admin only)')
    }
  }

  useEffect(() => { load() }, [])

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Organizations</h1>
        <button
          onClick={createOrg}
          className="px-3 py-1.5 text-sm bg-slate-900 text-white rounded-md"
        >
          + New org
        </button>
      </div>
      <div className="flex gap-2 flex-wrap">
        <input
          className="border border-slate-300 rounded-md px-3 py-1.5 text-sm flex-1 min-w-[180px]"
          placeholder="Search by name…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && load()}
        />
        <select
          value={type}
          onChange={(e) => setType(e.target.value)}
          className="border border-slate-300 rounded-md px-2 py-1.5 text-sm"
        >
          <option value="">All types</option>
          <option value="MANAGER">Manager</option>
          <option value="LABEL">Label</option>
          <option value="PUBLISHER">Publisher</option>
        </select>
        <select
          value={sort}
          onChange={(e) => setSort(e.target.value)}
          className="border border-slate-300 rounded-md px-2 py-1.5 text-sm"
        >
          <option value="newest">Sort: Newest</option>
          <option value="oldest">Sort: Oldest</option>
          <option value="name">Sort: Name A→Z</option>
          <option value="size">Sort: Largest catalog</option>
        </select>
        <button onClick={load} className="px-3 py-1.5 bg-slate-200 rounded-md text-sm">
          Search
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="md:col-span-2 border border-slate-200 rounded-md overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-100 text-left">
              <tr>
                <th className="px-3 py-2">ID</th>
                <th className="px-3 py-2">Name</th>
                <th className="px-3 py-2">Type</th>
                <th className="px-3 py-2">Members</th>
                <th className="px-3 py-2">Songs</th>
                <th className="px-3 py-2">Creators</th>
              </tr>
            </thead>
            <tbody>
              {visibleRows.map((o) => (
                <tr
                  key={o.id}
                  onClick={() => openDetail(o.id)}
                  className={`border-t border-slate-200 cursor-pointer hover:bg-slate-50 ${
                    selected === o.id ? 'bg-slate-100' : ''
                  }`}
                >
                  <td className="px-3 py-2 text-slate-500">{o.id}</td>
                  <td className="px-3 py-2 font-medium">{o.name}</td>
                  <td className="px-3 py-2">{o.type}</td>
                  <td className="px-3 py-2">{o.member_count}</td>
                  <td className="px-3 py-2">{o.song_count}</td>
                  <td className="px-3 py-2">{o.creator_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="border border-slate-200 rounded-md p-4 text-sm">
          {!selected ? (
            <div className="text-slate-500">Select an organization to view details.</div>
          ) : !detail ? (
            <div className="text-slate-500">Loading…</div>
          ) : (
            <div className="space-y-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="text-lg font-semibold">{detail.name}</div>
                  <div className="text-xs text-slate-500">
                    {detail.type} · {detail.account_type || '—'}
                  </div>
                </div>
                <label className="text-xs flex items-center gap-1 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={viewAs}
                    onChange={(e) => setViewAs(e.target.checked)}
                  />
                  <span>View as OWNER (read-only)</span>
                </label>
              </div>
              {viewAs && (
                <div className="text-[11px] bg-amber-50 border border-amber-200 text-amber-800 rounded px-2 py-1">
                  Read-only owner view: showing the same fields an OWNER would see.
                  Writes are not enabled.
                </div>
              )}
              <div className="text-xs text-slate-500">Created {detail.created_at}</div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="bg-slate-50 p-2 rounded">Songs: <b>{detail.song_count}</b></div>
                <div className="bg-slate-50 p-2 rounded">Creators: <b>{detail.creator_count}</b></div>
              </div>
              <div className="border-t border-slate-200 pt-3">
                <div className="font-medium mb-1">Access code</div>
                {accessCode ? (
                  <div className="font-mono text-base bg-slate-100 px-2 py-1 rounded inline-block">
                    {accessCode}
                  </div>
                ) : (
                  <button onClick={fetchAccessCode} className="text-xs text-sky-700 hover:underline">
                    Show access code
                  </button>
                )}
              </div>
              <div>
                <div className="font-medium mb-1">Members</div>
                <ul className="text-xs space-y-0.5 max-h-40 overflow-y-auto">
                  {detail.members.map((m) => (
                    <li key={m.user_id}>
                      {m.username} <span className="text-slate-500">({m.role})</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <div className="font-medium mb-1">Recent audit</div>
                <ul className="text-xs space-y-0.5 max-h-40 overflow-y-auto">
                  {detail.recent_audit.map((r) => (
                    <li key={r.id} className="truncate">
                      <span className="text-slate-500">{r.created_at?.slice(0, 16)}</span>
                      {' · '}{r.action}{r.entity_name ? ` · ${r.entity_name}` : ''}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
