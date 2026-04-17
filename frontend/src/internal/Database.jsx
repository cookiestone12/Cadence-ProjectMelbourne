import React, { useEffect, useState } from 'react'
import internal from './api'

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
