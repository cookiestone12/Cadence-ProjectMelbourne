import React, { useState, useEffect, useCallback } from 'react'
import axios from 'axios'
import {
  DocumentArrowDownIcon,
  TableCellsIcon,
  FunnelIcon,
  ChartBarIcon,
  CurrencyDollarIcon,
  ClipboardDocumentListIcon,
} from '@heroicons/react/24/outline'

const STATUSES = ['', 'PITCHED', 'IN_REVIEW', 'IN_NEGOTIATION', 'SECURED', 'DELIVERED', 'AIRED', 'PAID']

export default function SyncReportsPage() {
  const [orgId, setOrgId] = useState(null)
  const [clients, setClients] = useState([])
  const [clientFilter, setClientFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [reportData, setReportData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [pdfLoading, setPdfLoading] = useState(false)

  useEffect(() => {
    const init = async () => {
      try {
        const orgRes = await axios.get('/api/organizations/current')
        const id = orgRes.data?.id
        if (!id) { setLoading(false); return }
        setOrgId(id)
        const clientsRes = await axios.get(`/api/placements/org/${id}/clients`)
        setClients(clientsRes.data || [])
      } catch (e) {
        console.error('Failed to load org data', e)
      }
      setLoading(false)
    }
    init()
  }, [])

  const fetchReport = useCallback(async () => {
    if (!orgId) return
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (clientFilter) params.set('client_name', clientFilter)
      if (statusFilter) params.set('status', statusFilter)
      if (dateFrom) params.set('date_from', dateFrom)
      if (dateTo) params.set('date_to', dateTo)
      const res = await axios.get(`/api/placements/org/${orgId}/sync-report?${params.toString()}`)
      setReportData(res.data)
    } catch (e) {
      console.error('Failed to load report', e)
    }
    setLoading(false)
  }, [orgId, clientFilter, statusFilter, dateFrom, dateTo])

  useEffect(() => {
    if (orgId) fetchReport()
  }, [orgId, fetchReport])

  const downloadPdf = async () => {
    if (!orgId) return
    setPdfLoading(true)
    try {
      const params = new URLSearchParams()
      params.set('format', 'pdf')
      if (clientFilter) params.set('client_name', clientFilter)
      if (statusFilter) params.set('status', statusFilter)
      if (dateFrom) params.set('date_from', dateFrom)
      if (dateTo) params.set('date_to', dateTo)
      const res = await axios.get(`/api/placements/org/${orgId}/sync-report?${params.toString()}`, {
        responseType: 'blob'
      })
      const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `Sync_Report_${new Date().toISOString().slice(0,10)}.pdf`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (e) {
      console.error('PDF download failed', e)
    }
    setPdfLoading(false)
  }

  const exportCsv = () => {
    if (!reportData?.placements?.length) return
    const headers = ['Title', 'Song', 'Client', 'Status', 'License Fee', 'Currency', 'Type', 'Pitched Date', 'Secured Date', 'Delivery Date', 'Air Date', 'Territory', 'Contact']
    const rows = reportData.placements.map(p => [
      p.title || '',
      p.song_title || p.work_title || '',
      p.client_name || '',
      p.status || '',
      p.license_fee || 0,
      p.license_currency || 'USD',
      p.placement_type || '',
      p.pitched_date || '',
      p.secured_date || '',
      p.delivery_date || '',
      p.air_date || '',
      p.territory || '',
      p.contact_name || '',
    ])
    const csvContent = [headers, ...rows].map(r => r.map(v => `"${String(v).replace(/"/g, '""')}"`).join(',')).join('\n')
    const blob = new Blob([csvContent], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `Sync_Report_${new Date().toISOString().slice(0,10)}.csv`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  }

  const summary = reportData?.summary || { total_placements: 0, total_revenue: 0, by_status: {}, by_client: {} }

  const statusColor = (s) => {
    const map = {
      PITCHED: 'bg-blue-100 text-blue-700',
      IN_REVIEW: 'bg-yellow-100 text-yellow-700',
      IN_NEGOTIATION: 'bg-orange-100 text-orange-700',
      SECURED: 'bg-green-100 text-green-700',
      DELIVERED: 'bg-teal-100 text-teal-700',
      AIRED: 'bg-purple-100 text-purple-700',
      PAID: 'bg-emerald-100 text-emerald-800',
      DECLINED: 'bg-red-100 text-red-700',
      CANCELLED: 'bg-gray-100 text-gray-600',
    }
    return map[s] || 'bg-gray-100 text-gray-600'
  }

  return (
    <div className="p-4 md:p-6 lg:p-8 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-[#3D4A44]">Sync Reports</h1>
          <p className="text-sm text-[#7A8580] mt-1">Generate and export sync placement reports</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={downloadPdf}
            disabled={pdfLoading || !reportData?.placements?.length}
            className="flex items-center gap-2 px-4 py-2 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] transition-colors text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <DocumentArrowDownIcon className="w-4 h-4" />
            {pdfLoading ? 'Generating...' : 'Generate PDF'}
          </button>
          <button
            onClick={exportCsv}
            disabled={!reportData?.placements?.length}
            className="flex items-center gap-2 px-4 py-2 bg-white border border-[#A3C4B5] text-[#3D4A44] rounded-lg hover:bg-[#E8F0EC] transition-colors text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <TableCellsIcon className="w-4 h-4" />
            Export CSV
          </button>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-[rgba(59,77,67,0.12)] p-4 mb-6 shadow-sm">
        <div className="flex items-center gap-2 mb-3">
          <FunnelIcon className="w-4 h-4 text-[#5B8A72]" />
          <span className="text-sm font-medium text-[#3D4A44]">Filters</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <div>
            <label className="block text-xs font-medium text-[#7A8580] mb-1">Client</label>
            <select
              value={clientFilter}
              onChange={e => setClientFilter(e.target.value)}
              className="w-full px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-lg text-sm text-[#3D4A44] bg-white focus:outline-none focus:ring-2 focus:ring-[#5B8A72]/30 focus:border-[#5B8A72]"
            >
              <option value="">All Clients</option>
              {clients.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-[#7A8580] mb-1">Status</label>
            <select
              value={statusFilter}
              onChange={e => setStatusFilter(e.target.value)}
              className="w-full px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-lg text-sm text-[#3D4A44] bg-white focus:outline-none focus:ring-2 focus:ring-[#5B8A72]/30 focus:border-[#5B8A72]"
            >
              <option value="">All Statuses</option>
              {STATUSES.filter(Boolean).map(s => <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-[#7A8580] mb-1">From Date</label>
            <input
              type="date"
              value={dateFrom}
              onChange={e => setDateFrom(e.target.value)}
              className="w-full px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-lg text-sm text-[#3D4A44] bg-white focus:outline-none focus:ring-2 focus:ring-[#5B8A72]/30 focus:border-[#5B8A72]"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-[#7A8580] mb-1">To Date</label>
            <input
              type="date"
              value={dateTo}
              onChange={e => setDateTo(e.target.value)}
              className="w-full px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-lg text-sm text-[#3D4A44] bg-white focus:outline-none focus:ring-2 focus:ring-[#5B8A72]/30 focus:border-[#5B8A72]"
            />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <div className="bg-white rounded-xl border border-[rgba(59,77,67,0.12)] p-5 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-[#E8F0EC] flex items-center justify-center">
              <ClipboardDocumentListIcon className="w-5 h-5 text-[#5B8A72]" />
            </div>
            <div>
              <p className="text-xs text-[#7A8580] font-medium">Total Placements</p>
              <p className="text-2xl font-bold text-[#3D4A44]">{summary.total_placements}</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl border border-[rgba(59,77,67,0.12)] p-5 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-[#E8F0EC] flex items-center justify-center">
              <CurrencyDollarIcon className="w-5 h-5 text-[#5B8A72]" />
            </div>
            <div>
              <p className="text-xs text-[#7A8580] font-medium">Total Revenue</p>
              <p className="text-2xl font-bold text-[#3D4A44]">${summary.total_revenue?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl border border-[rgba(59,77,67,0.12)] p-5 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-[#E8F0EC] flex items-center justify-center">
              <ChartBarIcon className="w-5 h-5 text-[#5B8A72]" />
            </div>
            <div>
              <p className="text-xs text-[#7A8580] font-medium">Pipeline Breakdown</p>
              <div className="flex flex-wrap gap-1 mt-1">
                {Object.entries(summary.by_status || {}).map(([s, count]) => (
                  <span key={s} className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium ${statusColor(s)}`}>
                    {s}: {count}
                  </span>
                ))}
                {Object.keys(summary.by_status || {}).length === 0 && (
                  <span className="text-xs text-[#7A8580]">No data</span>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-[rgba(59,77,67,0.12)] shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-[rgba(59,77,67,0.08)]">
          <h2 className="text-sm font-semibold text-[#3D4A44]">Placement Details</h2>
        </div>
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <div className="w-6 h-6 border-2 border-[#5B8A72] border-t-transparent rounded-full animate-spin" />
          </div>
        ) : !reportData?.placements?.length ? (
          <div className="flex flex-col items-center justify-center py-16 text-[#7A8580]">
            <ClipboardDocumentListIcon className="w-10 h-10 mb-2 opacity-40" />
            <p className="text-sm">No placements found for the selected filters</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-[#F5F7F4]">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-[#7A8580] uppercase tracking-wider">Title</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-[#7A8580] uppercase tracking-wider">Song</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-[#7A8580] uppercase tracking-wider">Client</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-[#7A8580] uppercase tracking-wider">Status</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-[#7A8580] uppercase tracking-wider">License Fee</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-[#7A8580] uppercase tracking-wider hidden md:table-cell">Pitched</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-[#7A8580] uppercase tracking-wider hidden lg:table-cell">Secured</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[rgba(59,77,67,0.06)]">
                {reportData.placements.map(p => (
                  <tr key={p.id} className="hover:bg-[#F5F7F4]/50 transition-colors">
                    <td className="px-4 py-3 font-medium text-[#3D4A44] max-w-[200px] truncate">{p.title}</td>
                    <td className="px-4 py-3 text-[#7A8580] max-w-[160px] truncate">{p.song_title || p.work_title || '—'}</td>
                    <td className="px-4 py-3 text-[#7A8580] max-w-[140px] truncate">{p.client_name || '—'}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${statusColor(p.status)}`}>
                        {p.status?.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right font-medium text-[#3D4A44]">
                      {p.license_fee ? `$${Number(p.license_fee).toLocaleString(undefined, { minimumFractionDigits: 2 })}` : '—'}
                    </td>
                    <td className="px-4 py-3 text-[#7A8580] hidden md:table-cell">{p.pitched_date || '—'}</td>
                    <td className="px-4 py-3 text-[#7A8580] hidden lg:table-cell">{p.secured_date || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
