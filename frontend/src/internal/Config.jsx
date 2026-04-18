import React, { useEffect, useState } from 'react'
import internal from './api'

function ConfigRow({ item, onSave }) {
  const [value, setValue] = useState(item.value)
  const [saving, setSaving] = useState(false)
  const [savedAt, setSavedAt] = useState(0)

  useEffect(() => { setValue(item.value) }, [item.value])

  const dirty = JSON.stringify(value) !== JSON.stringify(item.value)

  const save = async () => {
    setSaving(true)
    try {
      await onSave(item.key, value)
      setSavedAt(Date.now())
    } finally {
      setSaving(false)
    }
  }

  let editor = null
  if (item.value_type === 'bool') {
    editor = (
      <label className="inline-flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={!!value}
          onChange={(e) => setValue(e.target.checked)}
        />
        {value ? 'on' : 'off'}
      </label>
    )
  } else if (item.value_type === 'int' || item.value_type === 'float') {
    editor = (
      <input
        type="number"
        step={item.value_type === 'float' ? 'any' : '1'}
        className="border border-slate-300 rounded px-2 py-1 text-sm w-40"
        value={value ?? ''}
        onChange={(e) => setValue(item.value_type === 'int'
          ? parseInt(e.target.value || '0', 10)
          : parseFloat(e.target.value || '0'))}
      />
    )
  } else if (item.value_type === 'json') {
    editor = (
      <textarea
        className="border border-slate-300 rounded px-2 py-1 text-xs font-mono w-full"
        rows={3}
        value={typeof value === 'string' ? value : JSON.stringify(value, null, 2)}
        onChange={(e) => {
          try { setValue(JSON.parse(e.target.value)) }
          catch { setValue(e.target.value) }
        }}
      />
    )
  } else {
    editor = (
      <input
        type="text"
        className="border border-slate-300 rounded px-2 py-1 text-sm w-full max-w-md"
        value={value ?? ''}
        onChange={(e) => setValue(e.target.value)}
      />
    )
  }

  return (
    <tr className="border-t border-slate-200">
      <td className="px-3 py-2 align-top">
        <div className="font-mono text-xs">{item.key}</div>
        {item.description && (
          <div className="text-xs text-slate-500 mt-0.5">{item.description}</div>
        )}
      </td>
      <td className="px-3 py-2 align-top">
        <div className="text-xs text-slate-400 mb-1">{item.value_type}</div>
        {editor}
      </td>
      <td className="px-3 py-2 align-top whitespace-nowrap">
        <button
          disabled={!dirty || saving}
          onClick={save}
          className="text-xs px-3 py-1 bg-slate-900 text-white rounded disabled:bg-slate-300"
        >
          {saving ? 'Saving…' : 'Save'}
        </button>
        {savedAt > 0 && Date.now() - savedAt < 2000 && (
          <div className="text-xs text-emerald-600 mt-1">Saved</div>
        )}
      </td>
    </tr>
  )
}

export default function Config() {
  const [grouped, setGrouped] = useState({})
  const [err, setErr] = useState('')

  const load = async () => {
    try {
      const { data } = await internal.get('/api/internal/portal/config')
      setGrouped(data.grouped)
    } catch (e) {
      setErr(e?.response?.data?.detail || 'Failed to load')
    }
  }

  useEffect(() => { load() }, [])

  const save = async (key, value) => {
    await internal.put(`/api/internal/portal/config/${encodeURIComponent(key)}`, { value })
    await load()
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold">Feature flags & config</h1>
        <p className="text-xs text-slate-500">
          Live runtime knobs — changes take effect immediately. Every change is recorded
          in the audit log.
        </p>
      </div>
      {err && <div className="text-xs text-red-600">{err}</div>}
      {Object.keys(grouped).sort().map((cat) => (
        <section key={cat}>
          <h2 className="font-semibold text-slate-900 mb-2">{cat}</h2>
          <div className="border border-slate-200 rounded-md overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-slate-100 text-left text-xs">
                <tr>
                  <th className="px-3 py-2 w-1/2">Key</th>
                  <th className="px-3 py-2">Value</th>
                  <th className="px-3 py-2"></th>
                </tr>
              </thead>
              <tbody>
                {grouped[cat].map((it) => (
                  <ConfigRow key={it.key} item={it} onSave={save} />
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ))}
    </div>
  )
}
