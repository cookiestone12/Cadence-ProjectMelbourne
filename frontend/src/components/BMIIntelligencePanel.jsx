import React, { useEffect, useState } from 'react'
import axios from 'axios'

const fmtCents = (c) => (c == null ? '—' : (c / 100).toLocaleString('en-US', { style: 'currency', currency: 'USD' }))
const fmtPct = (v, digits = 2) => (v == null ? '—' : `${(Number(v) * 100).toFixed(digits)}%`)
const fmtNum = (n) => (n == null ? '—' : Number(n).toLocaleString('en-US'))

const FLAG_STYLES = {
  LOW: 'bg-amber-100 text-amber-700',
  HIGH: 'bg-purple-100 text-purple-700',
  NORMAL: 'bg-green-100 text-green-700',
  NO_BENCHMARK: 'bg-gray-100 text-gray-600',
}

export default function BMIIntelligencePanel({ orgId, statementId }) {
  const [validation, setValidation] = useState(null)
  const [rates, setRates] = useState(null)
  const [trajectories, setTrajectories] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true); setError(null)
      try {
        const base = `/api/v1/royalty-intelligence/${orgId}`
        const [v, r, t] = await Promise.all([
          statementId
            ? axios.get(`${base}/statements/${statementId}/validation`).then(x => x.data).catch(() => null)
            : Promise.resolve(null),
          axios.get(`${base}/rates`, { params: statementId ? { statement_id: statementId } : {} }).then(x => x.data),
          axios.get(`${base}/trajectories`).then(x => x.data),
        ])
        if (cancelled) return
        setValidation(v); setRates(r); setTrajectories(t)
      } catch (e) {
        if (!cancelled) setError(e?.response?.data?.detail || e.message || 'Failed to load')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    if (orgId) load()
    return () => { cancelled = true }
  }, [orgId, statementId])

  if (loading) return <div className="p-6 text-gray-500">Loading BMI intelligence…</div>
  if (error) return <div className="p-6 text-red-600">Error: {error}</div>

  const ratesList = rates?.rates ? Object.entries(rates.rates) : []
  const decay = trajectories?.catalog_decay
  const split = trajectories?.new_vs_catalog

  return (
    <div className="space-y-6 p-6">
      {validation && (
        <div className="rounded-2xl border border-gray-200 bg-white p-5">
          <h3 className="text-base font-semibold text-gray-900 mb-3">Stated vs. Computed</h3>
          <div className="grid grid-cols-4 gap-4 text-sm">
            <div>
              <div className="text-gray-500">Stated total</div>
              <div className="font-semibold text-gray-900">{fmtCents(validation.stated_total_cents)}</div>
            </div>
            <div>
              <div className="text-gray-500">Computed total</div>
              <div className="font-semibold text-gray-900">{fmtCents(validation.computed_total_cents)}</div>
            </div>
            <div>
              <div className="text-gray-500">Delta</div>
              <div className={`font-semibold ${Math.abs(validation.delta_cents || 0) > 100 ? 'text-amber-600' : 'text-green-600'}`}>
                {fmtCents(validation.delta_cents)} ({fmtPct(validation.delta_pct, 3)})
              </div>
            </div>
            <div>
              <div className="text-gray-500">Parse quality</div>
              <div className="font-semibold text-gray-900">
                {validation.parse_quality == null ? '—' : `${(validation.parse_quality * 100).toFixed(1)}%`}
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="rounded-2xl border border-gray-200 bg-white p-5">
        <h3 className="text-base font-semibold text-gray-900 mb-3">Per-Platform Effective Rates</h3>
        {ratesList.length === 0 ? (
          <div className="text-sm text-gray-500">No BMI platform data available.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 border-b border-gray-200">
                  <th className="py-2 pr-4">Source</th>
                  <th className="py-2 pr-4 text-right">Streams</th>
                  <th className="py-2 pr-4 text-right">Royalty</th>
                  <th className="py-2 pr-4 text-right">Avg Writer Share</th>
                  <th className="py-2 pr-4 text-right">Raw ¢/stream</th>
                  <th className="py-2 pr-4 text-right">Effective ¢/stream</th>
                  <th className="py-2 pr-4">Band</th>
                </tr>
              </thead>
              <tbody>
                {ratesList.map(([source, row]) => (
                  <tr key={source} className="border-b border-gray-100">
                    <td className="py-2 pr-4 font-medium text-gray-900">{source}</td>
                    <td className="py-2 pr-4 text-right">{fmtNum(row.total_streams)}</td>
                    <td className="py-2 pr-4 text-right">${row.total_royalty_dollars?.toFixed(2)}</td>
                    <td className="py-2 pr-4 text-right">{row.avg_writer_share_pct?.toFixed(2)}%</td>
                    <td className="py-2 pr-4 text-right">{row.raw_rate_cents_per_stream?.toFixed(4)}</td>
                    <td className="py-2 pr-4 text-right">{row.effective_rate_cents_per_stream?.toFixed(4)}</td>
                    <td className="py-2 pr-4">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${FLAG_STYLES[row.rate_flag] || ''}`}>
                        {row.rate_flag}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="rounded-2xl border border-gray-200 bg-white p-5">
        <h3 className="text-base font-semibold text-gray-900 mb-3">Catalog Trajectory</h3>
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div>
            <div className="text-gray-500">Measured catalog decay (median per quarter)</div>
            <div className="font-semibold text-gray-900">
              {decay?.catalog_decay_rate == null ? '—' : `${(decay.catalog_decay_rate * 100).toFixed(2)}%`}
              {decay?.decay_quality && (
                <span className="ml-2 text-xs text-gray-500">({decay.decay_quality}, n={decay.songs_used})</span>
              )}
            </div>
          </div>
          <div>
            <div className="text-gray-500">Catalog revenue share</div>
            <div className="font-semibold text-gray-900">
              {fmtPct(split?.catalog_pct, 1)}
              <span className="ml-2 text-xs text-gray-500">({split?.catalog_song_count} songs)</span>
            </div>
          </div>
          <div>
            <div className="text-gray-500">New revenue share</div>
            <div className="font-semibold text-gray-900">
              {fmtPct(split?.new_pct, 1)}
              <span className="ml-2 text-xs text-gray-500">({split?.new_song_count} songs)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
