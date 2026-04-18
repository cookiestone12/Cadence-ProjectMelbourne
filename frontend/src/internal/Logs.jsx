import React, { useEffect, useState, useRef } from 'react'
import internal from './api'

const LEVELS = ['', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']

const COLOR = {
  DEBUG: 'text-slate-400',
  INFO: 'text-slate-700',
  WARNING: 'text-amber-700',
  ERROR: 'text-red-700',
  CRITICAL: 'text-red-800 font-semibold',
}

export default function Logs() {
  const [level, setLevel] = useState('')
  const [since, setSince] = useState('')
  const [until, setUntil] = useState('')
  const [q, setQ] = useState('')
  const [requestId, setRequestId] = useState('')
  const [entries, setEntries] = useState([])
  const [auto, setAuto] = useState(true)
  const tref = useRef(null)

  const load = async () => {
    try {
      const { data } = await internal.get('/api/internal/portal/logs/search', {
        params: {
          level: level || undefined,
          since: since || undefined,
          until: until || undefined,
          q: q || undefined,
          request_id: requestId || undefined,
          limit: 500,
        },
      })
      setEntries(data.entries)
    } catch (e) { /* swallow */ }
  }

  useEffect(() => {
    load()
    if (auto) tref.current = setInterval(load, 10_000)
    return () => clearInterval(tref.current)
  }, [auto, level, since, until, q, requestId])

  const downloadJsonl = async () => {
    const params = new URLSearchParams()
    if (level) params.set('level', level)
    if (since) params.set('since', since)
    if (until) params.set('until', until)
    if (q) params.set('q', q)
    if (requestId) params.set('request_id', requestId)
    const r = await fetch(
      `/api/internal/portal/logs/download?${params}`,
      { credentials: 'include' },
    )
    const blob = await r.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `cadence-logs.jsonl`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h1 className="text-2xl font-semibold">Logs</h1>
        <label className="text-xs flex items-center gap-1">
          <input type="checkbox" checked={auto} onChange={(e) => setAuto(e.target.checked)} />
          Auto-refresh 10s
        </label>
      </div>
      <div className="flex flex-wrap gap-2 items-center">
        <select
          className="border border-slate-300 rounded-md px-2 py-1 text-sm"
          value={level}
          onChange={(e) => setLevel(e.target.value)}
        >
          {LEVELS.map((l) => <option key={l} value={l}>{l || 'All levels'}</option>)}
        </select>
        <label className="text-xs flex items-center gap-1">
          From
          <input
            type="datetime-local"
            className="border border-slate-300 rounded-md px-2 py-1 text-sm"
            value={since}
            onChange={(e) => setSince(e.target.value)}
          />
        </label>
        <label className="text-xs flex items-center gap-1">
          To
          <input
            type="datetime-local"
            className="border border-slate-300 rounded-md px-2 py-1 text-sm"
            value={until}
            onChange={(e) => setUntil(e.target.value)}
          />
        </label>
        <input
          type="text"
          placeholder="search message…"
          className="border border-slate-300 rounded-md px-2 py-1 text-sm flex-1 min-w-[160px]"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <input
          type="text"
          placeholder="request_id"
          className="border border-slate-300 rounded-md px-2 py-1 text-sm font-mono w-48"
          value={requestId}
          onChange={(e) => setRequestId(e.target.value)}
        />
        <button onClick={load} className="px-3 py-1 bg-slate-200 rounded text-sm">Refresh</button>
        <button onClick={downloadJsonl} className="px-3 py-1 bg-slate-900 text-white rounded text-sm">
          Download JSONL
        </button>
        <span className="text-xs text-slate-500">{entries.length} entries</span>
      </div>
      <div className="border border-slate-200 rounded-md bg-slate-50 max-h-[70vh] overflow-y-auto font-mono text-xs">
        {entries.slice().reverse().map((e, i) => (
          <div key={i} className="px-3 py-1 border-b border-slate-200">
            <span className="text-slate-400">{e.timestamp?.slice(11, 19)}</span>{' '}
            <span className={COLOR[e.level] || ''}>{e.level}</span>{' '}
            <span className="text-slate-500">{e.logger}</span>{' '}
            {e.request_id && (
              <button
                onClick={() => setRequestId(e.request_id)}
                title="Filter by this request_id"
                className="text-violet-600 hover:underline mr-1"
              >
                [{e.request_id.slice(0, 8)}]
              </button>
            )}
            <span>{e.message}</span>
            {e.exception && (
              <pre className="text-red-700 mt-1 whitespace-pre-wrap">{e.exception}</pre>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
