import React, { useState, useEffect, useCallback } from 'react'
import axios from 'axios'
import ExportButton from '../components/ExportButton'
import {
  ShieldCheckIcon,
  ExclamationTriangleIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  ArrowUpTrayIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline'

const SEVERITY_STYLES = {
  CRITICAL: 'bg-red-100 text-red-800 border-red-200',
  HIGH: 'bg-orange-100 text-orange-800 border-orange-200',
  MEDIUM: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  LOW: 'bg-blue-100 text-blue-800 border-blue-200',
}

const TYPE_LABELS = {
  CROSS_STATEMENT: 'Cross-statement mismatch',
  RATE_CHECK: 'Rate below market',
  MISSING_PERIOD: 'Missing period',
  DECAY_ANOMALY: 'Decay anomaly',
}

function fmtMoney(cents) {
  if (cents == null) return '—'
  return `$${(cents / 100).toFixed(2)}`
}

export default function AuditPage() {
  const [orgId, setOrgId] = useState(null)
  const [summary, setSummary] = useState(null)
  const [findings, setFindings] = useState([])
  const [loading, setLoading] = useState(false)
  const [scanning, setScanning] = useState(false)
  const [filterType, setFilterType] = useState('')
  const [filterSeverity, setFilterSeverity] = useState('')
  const [showResolved, setShowResolved] = useState(false)
  const [error, setError] = useState(null)
  const [resolveTarget, setResolveTarget] = useState(null)
  const [resolveNotes, setResolveNotes] = useState('')
  const [importing, setImporting] = useState(false)
  const [importResult, setImportResult] = useState(null)

  useEffect(() => {
    axios.get('/api/organizations/current/membership')
      .then(r => setOrgId(r.data?.organization_id))
      .catch(() => setError('Could not determine current organization'))
  }, [])

  const loadSummary = useCallback(async () => {
    if (!orgId) return
    try {
      const r = await axios.get(`/api/organizations/${orgId}/audit/summary`)
      setSummary(r.data)
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to load audit summary')
    }
  }, [orgId])

  const loadFindings = useCallback(async () => {
    if (!orgId) return
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams()
      if (filterType) params.set('audit_type', filterType)
      if (filterSeverity) params.set('severity', filterSeverity)
      params.set('resolved', showResolved ? 'true' : 'false')
      params.set('limit', '200')
      const r = await axios.get(
        `/api/organizations/${orgId}/audit/findings?${params}`,
      )
      setFindings(r.data.findings || [])
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to load findings')
    } finally {
      setLoading(false)
    }
  }, [orgId, filterType, filterSeverity, showResolved])

  useEffect(() => {
    loadSummary()
    loadFindings()
  }, [loadSummary, loadFindings])

  const runScan = async () => {
    if (!orgId) return
    setScanning(true)
    setError(null)
    try {
      await axios.post(`/api/organizations/${orgId}/audit/scan`)
      await loadSummary()
      await loadFindings()
    } catch (e) {
      setError(e.response?.data?.detail || 'Scan failed')
    } finally {
      setScanning(false)
    }
  }

  const resolve = async () => {
    if (!resolveTarget || !orgId) return
    try {
      await axios.post(
        `/api/organizations/${orgId}/audit/findings/${resolveTarget.id}/resolve`,
        { resolution_notes: resolveNotes || null },
      )
      setResolveTarget(null)
      setResolveNotes('')
      await loadSummary()
      await loadFindings()
    } catch (e) {
      setError(e.response?.data?.detail || 'Could not resolve finding')
    }
  }

  const reopen = async (finding) => {
    if (!orgId) return
    try {
      await axios.post(
        `/api/organizations/${orgId}/audit/findings/${finding.id}/reopen`,
      )
      await loadSummary()
      await loadFindings()
    } catch (e) {
      setError(e.response?.data?.detail || 'Could not reopen finding')
    }
  }

  const importLuminate = async (event) => {
    const file = event.target.files?.[0]
    if (!file || !orgId) return
    setImporting(true)
    setImportResult(null)
    setError(null)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const r = await axios.post(
        `/api/organizations/${orgId}/audit/luminate/import`,
        fd,
        { headers: { 'Content-Type': 'multipart/form-data' } },
      )
      setImportResult(r.data)
      await loadSummary()
      await loadFindings()
    } catch (e) {
      setError(e.response?.data?.detail || 'Luminate import failed')
    } finally {
      setImporting(false)
      event.target.value = ''
    }
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <ShieldCheckIcon className="w-8 h-8 text-[#5B8A72]" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Royalty Audit</h1>
            <p className="text-sm text-gray-500">
              Detect cross-statement discrepancies, off-market rates,
              missing periods, and decay anomalies in your catalog.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <label className="cursor-pointer flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-lg shadow-sm hover:bg-gray-50 text-sm">
            <ArrowUpTrayIcon className="w-4 h-4" />
            {importing ? 'Importing…' : 'Import Luminate CSV'}
            <input
              type="file"
              accept=".csv"
              className="hidden"
              onChange={importLuminate}
              disabled={importing}
            />
          </label>
          <button
            onClick={runScan}
            disabled={scanning || !orgId}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[#5B8A72] text-white text-sm hover:bg-[#4a7660] disabled:opacity-50"
          >
            <ArrowPathIcon className={`w-4 h-4 ${scanning ? 'animate-spin' : ''}`} />
            {scanning ? 'Scanning…' : 'Run Audit Scan'}
          </button>
          {orgId && (
            <ExportButton
              baseUrl={`/api/organizations/${orgId}/audit/report/pdf`}
              filename={`cadence_audit_report_${new Date().toISOString().slice(0, 10)}`}
              formats={['pdf']}
              variant="secondary"
              size="md"
              onError={(msg) => setError(msg)}
            />
          )}
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-800 flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)}><XMarkIcon className="w-4 h-4" /></button>
        </div>
      )}

      {importResult && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-800">
          Luminate import: {importResult.import?.matched ?? 0} matched,
          {' '}{importResult.import?.unmatched ?? 0} unmatched.
          {importResult.rescan && (
            <span> Re-scan produced {Object.values(importResult.rescan).reduce((a, b) => a + b, 0)} findings.</span>
          )}
        </div>
      )}

      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
          <div className="p-4 bg-white border border-gray-200 rounded-lg">
            <div className="text-xs text-gray-500 uppercase">Open</div>
            <div className="text-2xl font-bold text-gray-900">{summary.open_total}</div>
          </div>
          {['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map(sev => (
            <div key={sev} className={`p-4 border rounded-lg ${SEVERITY_STYLES[sev]}`}>
              <div className="text-xs uppercase opacity-70">{sev}</div>
              <div className="text-2xl font-bold">{summary.by_severity?.[sev] || 0}</div>
            </div>
          ))}
        </div>
      )}

      <div className="flex flex-wrap gap-2 mb-4">
        <select
          value={filterType}
          onChange={e => setFilterType(e.target.value)}
          className="px-3 py-2 border border-gray-200 rounded-lg text-sm"
        >
          <option value="">All check types</option>
          {Object.entries(TYPE_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
        <select
          value={filterSeverity}
          onChange={e => setFilterSeverity(e.target.value)}
          className="px-3 py-2 border border-gray-200 rounded-lg text-sm"
        >
          <option value="">All severities</option>
          {['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map(s => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <label className="flex items-center gap-2 text-sm text-gray-600 px-3 py-2">
          <input
            type="checkbox"
            checked={showResolved}
            onChange={e => setShowResolved(e.target.checked)}
          />
          Show resolved
        </label>
      </div>

      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-gray-500 text-sm">Loading…</div>
        ) : findings.length === 0 ? (
          <div className="p-12 text-center">
            <CheckCircleIcon className="w-12 h-12 text-green-500 mx-auto mb-3" />
            <p className="text-gray-700 font-medium">No findings.</p>
            <p className="text-sm text-gray-500">
              {showResolved
                ? 'No resolved findings match your filters.'
                : 'Run a scan to look for new discrepancies.'}
            </p>
          </div>
        ) : (
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Severity</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Description</th>
                <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Discrepancy</th>
                <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {findings.map(f => (
                <tr key={f.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <span className={`inline-flex px-2 py-0.5 text-xs font-semibold border rounded ${SEVERITY_STYLES[f.severity] || ''}`}>
                      {f.severity}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-700">
                    {TYPE_LABELS[f.audit_type] || f.audit_type}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-900">
                    {f.description}
                    {f.song_id && (
                      <span className="ml-2 text-xs text-gray-400">song #{f.song_id}</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-sm text-right font-mono text-gray-700">
                    {fmtMoney(f.discrepancy_cents)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {f.resolved ? (
                      <button
                        onClick={() => reopen(f)}
                        className="text-xs text-gray-500 hover:text-gray-700"
                      >
                        Reopen
                      </button>
                    ) : (
                      <button
                        onClick={() => { setResolveTarget(f); setResolveNotes('') }}
                        className="text-xs px-2 py-1 bg-[#5B8A72] text-white rounded hover:bg-[#4a7660]"
                      >
                        Resolve
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {resolveTarget && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-2">
                <ExclamationTriangleIcon className="w-6 h-6 text-yellow-500" />
                <h3 className="font-semibold text-gray-900">Resolve finding</h3>
              </div>
              <button onClick={() => setResolveTarget(null)}>
                <XMarkIcon className="w-5 h-5 text-gray-400" />
              </button>
            </div>
            <p className="text-sm text-gray-700 mb-3">{resolveTarget.description}</p>
            <textarea
              value={resolveNotes}
              onChange={e => setResolveNotes(e.target.value)}
              placeholder="Resolution notes (optional)…"
              rows={3}
              className="w-full border border-gray-200 rounded p-2 text-sm mb-3"
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setResolveTarget(null)}
                className="px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-100 rounded"
              >
                Cancel
              </button>
              <button
                onClick={resolve}
                className="px-3 py-1.5 text-sm bg-[#5B8A72] text-white rounded hover:bg-[#4a7660]"
              >
                Mark Resolved
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
