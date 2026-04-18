import React, { useEffect, useState } from 'react'
import internal from './api'

function SqlRunner() {
  const [sql, setSql] = useState('SELECT id, email FROM users LIMIT 10;')
  const [name, setName] = useState('')
  const [result, setResult] = useState(null)
  const [err, setErr] = useState('')
  const [running, setRunning] = useState(false)
  const [saved, setSaved] = useState([])
  const [history, setHistory] = useState([])

  const loadSidecars = async () => {
    try {
      const [s, h] = await Promise.all([
        internal.get('/api/internal/portal/queries/saved'),
        internal.get('/api/internal/portal/queries/history'),
      ])
      setSaved(s.data.rows); setHistory(h.data.rows)
    } catch (e) { /* ignore */ }
  }
  useEffect(() => { loadSidecars() }, [])

  const run = async () => {
    setRunning(true); setErr(''); setResult(null)
    try {
      const { data } = await internal.post('/api/internal/portal/queries/run', {
        sql, limit: 200,
      })
      setResult(data)
    } catch (e) {
      setErr(e?.response?.data?.detail || 'Query failed')
    } finally {
      setRunning(false)
      loadSidecars()
    }
  }

  const save = async () => {
    if (!name.trim()) return
    try {
      await internal.post('/api/internal/portal/queries/saved', { name, sql })
      setName('')
      loadSidecars()
    } catch (e) {
      setErr(e?.response?.data?.detail || 'Failed to save')
    }
  }

  const remove = async (id) => {
    await internal.delete(`/api/internal/portal/queries/saved/${id}`)
    loadSidecars()
  }

  const exportCsv = async () => {
    const r = await fetch('/api/internal/portal/queries/run.csv', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sql, limit: 10000 }),
    })
    if (!r.ok) {
      setErr('CSV export failed')
      return
    }
    const blob = await r.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = 'query.csv'; a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <section className="border border-slate-200 rounded-md p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold">SQL runner</h2>
        <span className="text-xs text-slate-500">SELECT/WITH only · max 1000 rows</span>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-3">
        <div className="lg:col-span-3 space-y-2">
          <textarea
            value={sql}
            onChange={(e) => setSql(e.target.value)}
            className="w-full border border-slate-300 rounded-md font-mono text-xs p-2"
            rows={6}
          />
          <div className="flex flex-wrap items-center gap-2">
            <button onClick={run} disabled={running}
              className="px-3 py-1 bg-slate-900 text-white rounded text-sm disabled:bg-slate-400">
              {running ? 'Running…' : 'Run'}
            </button>
            <button onClick={exportCsv} className="px-3 py-1 bg-slate-200 rounded text-sm">
              Export CSV
            </button>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="name to save…"
              className="border border-slate-300 rounded px-2 py-1 text-sm"
            />
            <button onClick={save} className="px-3 py-1 bg-slate-200 rounded text-sm">Save</button>
          </div>
          {err && <div className="text-xs text-red-600">{err}</div>}
          {result && (
            <div className="border border-slate-200 rounded overflow-auto max-h-[40vh]">
              <table className="text-xs">
                <thead className="bg-slate-100 sticky top-0">
                  <tr>
                    {result.columns.map((c) => (
                      <th key={c} className="px-2 py-1 text-left font-mono whitespace-nowrap">{c}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {result.rows.map((row, i) => (
                    <tr key={i} className="border-t border-slate-200">
                      {row.map((v, j) => (
                        <td key={j} className="px-2 py-1 align-top whitespace-nowrap max-w-[280px] truncate">
                          {v === null ? <span className="text-slate-400">null</span> : String(v)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="px-2 py-1 text-xs text-slate-500 bg-slate-50">
                {result.row_count} row(s)
              </div>
            </div>
          )}
        </div>
        <div className="space-y-3 text-xs">
          <div>
            <div className="font-semibold text-slate-700 mb-1">Saved</div>
            {saved.length === 0 && <div className="text-slate-400">None yet</div>}
            <ul className="space-y-1">
              {saved.map((s) => (
                <li key={s.id} className="flex items-center gap-1">
                  <button
                    onClick={() => setSql(s.sql)}
                    className="flex-1 text-left px-2 py-1 rounded hover:bg-slate-100 truncate"
                    title={s.sql}
                  >
                    {s.name}
                  </button>
                  <button
                    onClick={() => remove(s.id)}
                    className="text-slate-400 hover:text-red-600"
                    title="Delete"
                  >
                    ×
                  </button>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <div className="font-semibold text-slate-700 mb-1">Recent</div>
            {history.length === 0 && <div className="text-slate-400">No history</div>}
            <ul className="space-y-1 max-h-[40vh] overflow-y-auto">
              {history.map((h) => (
                <li key={h.id}>
                  <button
                    onClick={() => setSql(h.sql)}
                    className={`w-full text-left px-2 py-1 rounded hover:bg-slate-100 font-mono truncate ${
                      h.success ? '' : 'text-red-600'
                    }`}
                    title={h.sql}
                  >
                    {h.sql.slice(0, 60)}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  )
}

export default function Database() {
  const [tables, setTables] = useState([])
  const [table, setTable] = useState('')
  const [page, setPage] = useState(null)
  const [colFilters, setColFilters] = useState({})
  const [offset, setOffset] = useState(0)
  const limit = 50

  useEffect(() => {
    internal.get('/api/internal/portal/database/tables')
      .then(({ data }) => setTables(data.tables))
  }, [])

  const load = async (t = table, off = offset) => {
    if (!t) return
    const { data } = await internal.get(`/api/internal/portal/database/${t}`, {
      params: { limit, offset: off },
    })
    setPage(data)
  }

  const pickTable = (t) => {
    setTable(t); setOffset(0); setColFilters({})
    load(t, 0)
  }

  const exportCsv = async () => {
    if (!table) return
    // Cookie carries auth — withCredentials + same origin is enough.
    const r = await fetch(
      `/api/internal/portal/database/${table}/export.csv`,
      { credentials: 'include' },
    )
    const blob = await r.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = `${table}.csv`; a.click()
    URL.revokeObjectURL(url)
  }

  const filteredRows = page
    ? page.rows.filter((row) =>
        page.columns.every((c, idx) => {
          const f = (colFilters[c] || '').toLowerCase()
          if (!f) return true
          return String(row[idx] ?? '').toLowerCase().includes(f)
        })
      )
    : []

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Database browser</h1>
      <p className="text-xs text-slate-500">
        Read-only. Every load is recorded as an INTERNAL_DB_VIEW audit entry.
        Tables holding credential material are hidden.
      </p>
      <SqlRunner />
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="border border-slate-200 rounded-md p-2 max-h-[600px] overflow-y-auto">
          {tables.map((t) => (
            <button
              key={t}
              onClick={() => pickTable(t)}
              className={`block w-full text-left px-2 py-1 rounded text-xs font-mono ${
                t === table ? 'bg-slate-900 text-white' : 'hover:bg-slate-100'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
        <div className="md:col-span-3 space-y-2">
          {!page ? (
            <div className="text-sm text-slate-500">Select a table.</div>
          ) : (
            <>
              <div className="flex items-center gap-2 flex-wrap">
                <div className="text-sm font-mono">{page.table}</div>
                <div className="text-xs text-slate-500">
                  {page.total} rows · showing {page.rows.length}
                </div>
                <button
                  onClick={() => setColFilters({})}
                  className="px-2 py-1 bg-slate-100 rounded text-xs"
                >
                  Clear filters
                </button>
                <button onClick={exportCsv} className="px-2 py-1 bg-slate-200 rounded text-xs">
                  Export CSV
                </button>
                <button
                  disabled={offset === 0}
                  onClick={() => { const o = Math.max(0, offset - limit); setOffset(o); load(table, o) }}
                  className="px-2 py-1 bg-slate-200 rounded text-xs disabled:opacity-40"
                >
                  Prev
                </button>
                <button
                  disabled={offset + limit >= page.total}
                  onClick={() => { const o = offset + limit; setOffset(o); load(table, o) }}
                  className="px-2 py-1 bg-slate-200 rounded text-xs disabled:opacity-40"
                >
                  Next
                </button>
              </div>
              <div className="border border-slate-200 rounded-md overflow-auto max-h-[600px]">
                <table className="text-xs">
                  <thead className="bg-slate-100 sticky top-0">
                    <tr>
                      {page.columns.map((c) => (
                        <th key={c} className="px-2 py-1 text-left font-mono whitespace-nowrap">{c}</th>
                      ))}
                    </tr>
                    <tr>
                      {page.columns.map((c) => (
                        <th key={c} className="px-2 py-1 bg-slate-50">
                          <input
                            className="w-full border border-slate-200 rounded px-1 py-0.5 text-xs font-normal"
                            placeholder="filter…"
                            value={colFilters[c] || ''}
                            onChange={(e) =>
                              setColFilters({ ...colFilters, [c]: e.target.value })
                            }
                          />
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {filteredRows.map((row, i) => (
                      <tr key={i} className="border-t border-slate-200">
                        {row.map((v, j) => (
                          <td key={j} className="px-2 py-1 align-top whitespace-nowrap max-w-[280px] truncate">
                            {v === null ? <span className="text-slate-400">null</span> : String(v)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
