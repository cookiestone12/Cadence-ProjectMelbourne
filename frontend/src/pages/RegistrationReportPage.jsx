import React, { useState, useEffect, useMemo, useCallback } from 'react'
import axios from 'axios'
import {
  ArrowDownTrayIcon,
  DocumentTextIcon,
  ExclamationTriangleIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  EnvelopeIcon,
  CheckIcon,
  FunnelIcon,
  PaperAirplaneIcon,
  XMarkIcon,
  ArrowPathIcon,
  BookmarkIcon,
  TrashIcon,
  ClockIcon,
  PencilIcon
} from '@heroicons/react/24/outline'
import { CheckCircleIcon, BookmarkIcon as BookmarkSolidIcon } from '@heroicons/react/24/solid'

export default function RegistrationReportPage() {
  const [loading, setLoading] = useState(true)
  const [orgId, setOrgId] = useState(null)
  const [assetType, setAssetType] = useState('songs')
  const [reportData, setReportData] = useState([])
  const [summary, setSummary] = useState({ total: 0, valid: 0, invalid: 0, outstanding: 0, registered: 0 })
  const [selectedCreatorId, setSelectedCreatorId] = useState('')
  const [statusFilter, setStatusFilter] = useState('outstanding')
  const [creators, setCreators] = useState([])
  const [expandedItems, setExpandedItems] = useState(new Set())
  const [selectedItems, setSelectedItems] = useState(new Set())
  const [showEmailModal, setShowEmailModal] = useState(false)
  const [emailForm, setEmailForm] = useState({ email: '', name: '', message: '' })
  const [sending, setSending] = useState(false)
  const [sendResult, setSendResult] = useState(null)
  const [adminContacts, setAdminContacts] = useState([])
  const [selectedAdminId, setSelectedAdminId] = useState('')

  const [savedReports, setSavedReports] = useState([])
  const [viewingSavedReport, setViewingSavedReport] = useState(null)
  const [savingReport, setSavingReport] = useState(false)
  const [refreshingSaved, setRefreshingSaved] = useState(false)
  const [showSaveModal, setShowSaveModal] = useState(false)
  const [saveTitle, setSaveTitle] = useState('')

  useEffect(() => {
    async function init() {
      try {
        const orgRes = await axios.get('/api/organizations/current')
        const currentOrgId = orgRes.data?.id
        if (!currentOrgId) { setLoading(false); return }
        setOrgId(currentOrgId)

        axios.get(`/api/registration-reports/org/${currentOrgId}/creators`)
          .then(res => setCreators(Array.isArray(res.data) ? res.data : []))
          .catch(() => {})

        axios.get(`/api/creative-directory/org/${currentOrgId}`)
          .then(res => {
            const contacts = Array.isArray(res.data) ? res.data : res.data.contacts || []
            setAdminContacts(contacts.filter(c => c.email))
          })
          .catch(() => {})

        axios.get(`/api/registration-reports/org/${currentOrgId}/saved`)
          .then(res => setSavedReports(Array.isArray(res.data) ? res.data : []))
          .catch(() => {})
      } catch {
        setLoading(false)
      }
    }
    init()
  }, [])

  const fetchReport = useCallback((currentOrgId, currentAssetType, creatorId, status) => {
    if (!currentOrgId) return
    setLoading(true)
    const params = new URLSearchParams()
    if (creatorId) params.append('creator_id', creatorId)
    if (status) params.append('status', status)
    const qs = params.toString() ? `?${params.toString()}` : ''
    axios.get(`/api/registration-reports/org/${currentOrgId}/${currentAssetType}${qs}`)
      .then(res => {
        const data = res.data
        setReportData(Array.isArray(data) ? data : data.items || [])
        setSummary({
          total: data.total || 0,
          valid: data.valid || 0,
          invalid: data.invalid || 0,
          outstanding: data.outstanding || 0,
          registered: data.registered || 0
        })
      })
      .catch(() => { setReportData([]); setSummary({ total: 0, valid: 0, invalid: 0, outstanding: 0, registered: 0 }) })
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (orgId && !viewingSavedReport) fetchReport(orgId, assetType, selectedCreatorId, statusFilter)
  }, [orgId, assetType, selectedCreatorId, statusFilter, fetchReport, viewingSavedReport])

  function handleGenerateReport() {
    setSelectedItems(new Set())
    setViewingSavedReport(null)
    fetchReport(orgId, assetType, selectedCreatorId, statusFilter)
  }

  const toggleExpanded = (id) => {
    setExpandedItems(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const toggleSelected = (id) => {
    setSelectedItems(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const toggleSelectAll = () => {
    if (selectedItems.size === reportData.length) {
      setSelectedItems(new Set())
    } else {
      setSelectedItems(new Set(reportData.map(i => i.id)))
    }
  }

  const allSelected = reportData.length > 0 && selectedItems.size === reportData.length

  async function handleExportCSV() {
    if (!orgId) return
    try {
      const params = new URLSearchParams({ asset_type: assetType })
      if (selectedCreatorId) params.append('creator_id', selectedCreatorId)
      if (statusFilter) params.append('status', statusFilter)
      const res = await axios.get(`/api/registration-reports/org/${orgId}/export/csv?${params}`, { responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([res.data], { type: 'text/csv' }))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `Bulk_Registration_${assetType}.csv`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      alert('Failed to export CSV')
    }
  }

  async function handleExportPDF() {
    if (!orgId) return
    if (viewingSavedReport) {
      try {
        const res = await axios.get(
          `/api/registration-reports/org/${orgId}/saved/${viewingSavedReport.id}/pdf`,
          { responseType: 'blob' }
        )
        const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
        const link = document.createElement('a')
        link.href = url
        link.setAttribute('download', `${viewingSavedReport.title || 'Report'}.pdf`)
        document.body.appendChild(link)
        link.click()
        link.remove()
        window.URL.revokeObjectURL(url)
      } catch {
        alert('Failed to export PDF')
      }
      return
    }
    try {
      const itemIds = selectedItems.size > 0 ? Array.from(selectedItems) : []
      const res = await axios.post(
        `/api/registration-reports/org/${orgId}/export/pdf`,
        { asset_type: assetType, item_ids: itemIds },
        { responseType: 'blob' }
      )
      const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `Bulk_Registration_${assetType}.pdf`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      alert('Failed to export PDF')
    }
  }

  function openEmailModal() {
    setSendResult(null)
    setEmailForm({ email: '', name: '', message: '' })
    setSelectedAdminId('')
    setShowEmailModal(true)
  }

  function handleAdminSelect(contactId) {
    setSelectedAdminId(contactId)
    if (contactId) {
      const contact = adminContacts.find(c => c.id === parseInt(contactId))
      if (contact) {
        setEmailForm(prev => ({ ...prev, email: contact.email || '', name: contact.display_name || contact.name || '' }))
      }
    } else {
      setEmailForm(prev => ({ ...prev, email: '', name: '' }))
    }
  }

  async function handleSendEmail() {
    if (!orgId) return
    setSending(true)
    setSendResult(null)
    try {
      const itemIds = selectedItems.size > 0 ? Array.from(selectedItems) : []
      const payload = {
        asset_type: assetType,
        item_ids: itemIds,
        recipient_email: emailForm.email,
        recipient_name: emailForm.name,
        message: emailForm.message
      }
      if (selectedAdminId) {
        payload.admin_contact_id = parseInt(selectedAdminId)
      }
      const res = await axios.post(`/api/registration-reports/org/${orgId}/send-email`, payload)
      setSendResult({ success: true, message: res.data.message || 'Report sent successfully!' })
    } catch (err) {
      setSendResult({ success: false, message: err.response?.data?.detail || 'Failed to send email' })
    } finally {
      setSending(false)
    }
  }

  async function handleSaveReport() {
    if (!orgId) return
    setSavingReport(true)
    try {
      const payload = {
        title: saveTitle || undefined,
        asset_type: assetType,
        creator_id: selectedCreatorId ? parseInt(selectedCreatorId) : undefined,
        filter_status: statusFilter || undefined,
      }
      const res = await axios.post(`/api/registration-reports/org/${orgId}/save`, payload)
      setSavedReports(prev => [res.data, ...prev])
      setShowSaveModal(false)
      setSaveTitle('')
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to save report')
    } finally {
      setSavingReport(false)
    }
  }

  async function handleViewSavedReport(report) {
    if (!orgId) return
    setLoading(true)
    try {
      const res = await axios.get(`/api/registration-reports/org/${orgId}/saved/${report.id}`)
      const data = res.data
      setViewingSavedReport(data)
      setReportData(data.items || [])
      setSummary({
        total: data.item_count || 0,
        valid: data.ready_count || 0,
        invalid: data.needs_attention_count || 0,
        outstanding: data.outstanding_count || 0,
        registered: (data.item_count || 0) - (data.outstanding_count || 0)
      })
      setSelectedItems(new Set())
      setExpandedItems(new Set())
    } catch {
      alert('Failed to load saved report')
    } finally {
      setLoading(false)
    }
  }

  async function handleRefreshSavedReport() {
    if (!orgId || !viewingSavedReport) return
    setRefreshingSaved(true)
    try {
      const res = await axios.put(`/api/registration-reports/org/${orgId}/saved/${viewingSavedReport.id}/refresh`)
      const data = res.data
      setViewingSavedReport(prev => ({ ...prev, ...data }))
      setReportData(data.items || [])
      setSummary({
        total: data.item_count || 0,
        valid: data.ready_count || 0,
        invalid: data.needs_attention_count || 0,
        outstanding: data.outstanding_count || 0,
        registered: (data.item_count || 0) - (data.outstanding_count || 0)
      })
      setSavedReports(prev => prev.map(r => r.id === data.id ? { ...r, ...data } : r))
    } catch {
      alert('Failed to refresh report')
    } finally {
      setRefreshingSaved(false)
    }
  }

  async function handleDeleteSavedReport(reportId) {
    if (!orgId) return
    if (!window.confirm('Delete this saved report?')) return
    try {
      await axios.delete(`/api/registration-reports/org/${orgId}/saved/${reportId}`)
      setSavedReports(prev => prev.filter(r => r.id !== reportId))
      if (viewingSavedReport?.id === reportId) {
        setViewingSavedReport(null)
        fetchReport(orgId, assetType, selectedCreatorId, statusFilter)
      }
    } catch {
      alert('Failed to delete report')
    }
  }

  function exitSavedView() {
    setViewingSavedReport(null)
    fetchReport(orgId, assetType, selectedCreatorId, statusFilter)
  }

  const groupedByCreator = useMemo(() => {
    const groups = {}
    reportData.forEach(item => {
      const itemCreators = item.creators || []
      if (itemCreators.length === 0) {
        const key = 'uncredited'
        if (!groups[key]) groups[key] = { name: 'Uncredited', items: [] }
        groups[key].items.push(item)
      } else {
        itemCreators.forEach(c => {
          const key = `creator_${c.id}`
          if (!groups[key]) groups[key] = { name: c.name, items: [] }
          if (!groups[key].items.find(i => i.id === item.id)) {
            groups[key].items.push(item)
          }
        })
      }
    })
    return Object.entries(groups).sort((a, b) => a[1].name.localeCompare(b[1].name))
  }, [reportData])

  const selectedCount = selectedItems.size
  const outstandingInView = reportData.filter(i => !i.is_registered_with_pro).length

  function formatDate(dateStr) {
    if (!dateStr) return ''
    try {
      const d = new Date(dateStr)
      return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' })
    } catch { return dateStr }
  }

  return (
    <div className="p-4 sm:p-8">
      <div className="bg-gradient-to-r from-[#5B8A72] to-[#7A8580] rounded-2xl p-6 sm:p-8 mb-6 text-white">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <DocumentTextIcon className="w-8 h-8" />
              <h1 className="text-2xl sm:text-3xl font-bold">Bulk Registration</h1>
            </div>
            <p className="text-white/80 text-sm sm:text-base">
              {viewingSavedReport
                ? `Viewing: ${viewingSavedReport.title}`
                : 'PRO registration management — select, report, and send'}
            </p>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            {viewingSavedReport ? (
              <>
                <button
                  onClick={handleRefreshSavedReport}
                  disabled={refreshingSaved}
                  className="flex items-center gap-2 px-4 py-2 bg-white/20 hover:bg-white/30 rounded-xl text-sm font-medium transition-colors disabled:opacity-50"
                >
                  <ArrowPathIcon className={`w-4 h-4 ${refreshingSaved ? 'animate-spin' : ''}`} />
                  Refresh Data
                </button>
                <button
                  onClick={handleExportPDF}
                  className="flex items-center gap-2 px-4 py-2 bg-white/20 hover:bg-white/30 rounded-xl text-sm font-medium transition-colors"
                >
                  <ArrowDownTrayIcon className="w-4 h-4" />
                  PDF
                </button>
                <button
                  onClick={exitSavedView}
                  className="flex items-center gap-2 px-4 py-2 bg-white hover:bg-white/90 text-[#5B8A72] rounded-xl text-sm font-semibold transition-colors shadow-sm"
                >
                  <XMarkIcon className="w-4 h-4" />
                  Back to Live
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={handleGenerateReport}
                  disabled={loading}
                  className="flex items-center gap-2 px-4 py-2 bg-white/20 hover:bg-white/30 rounded-xl text-sm font-medium transition-colors disabled:opacity-50"
                >
                  <ArrowPathIcon className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                  Refresh
                </button>
                <button
                  onClick={() => { setSaveTitle(''); setShowSaveModal(true) }}
                  className="flex items-center gap-2 px-4 py-2 bg-white/20 hover:bg-white/30 rounded-xl text-sm font-medium transition-colors"
                >
                  <BookmarkIcon className="w-4 h-4" />
                  Save
                </button>
                <button
                  onClick={handleExportCSV}
                  className="flex items-center gap-2 px-4 py-2 bg-white/20 hover:bg-white/30 rounded-xl text-sm font-medium transition-colors"
                >
                  <ArrowDownTrayIcon className="w-4 h-4" />
                  CSV
                </button>
                <button
                  onClick={handleExportPDF}
                  className="flex items-center gap-2 px-4 py-2 bg-white/20 hover:bg-white/30 rounded-xl text-sm font-medium transition-colors"
                >
                  <ArrowDownTrayIcon className="w-4 h-4" />
                  {selectedCount > 0 ? `PDF (${selectedCount})` : 'PDF'}
                </button>
                <button
                  onClick={openEmailModal}
                  className="flex items-center gap-2 px-4 py-2 bg-white hover:bg-white/90 text-[#5B8A72] rounded-xl text-sm font-semibold transition-colors shadow-sm"
                >
                  <EnvelopeIcon className="w-4 h-4" />
                  {selectedCount > 0 ? `Send (${selectedCount})` : 'Send Report'}
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      {savedReports.length > 0 && !viewingSavedReport && (
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-3">
            <BookmarkSolidIcon className="w-4 h-4 text-[#5B8A72]" />
            <h2 className="text-sm font-semibold text-[#3D4A44]">Saved Reports</h2>
            <span className="text-xs text-[#7A8580]">({savedReports.length})</span>
          </div>
          <div className="flex gap-3 overflow-x-auto pb-2 no-scrollbar">
            {savedReports.map(report => (
              <div
                key={report.id}
                className="flex-shrink-0 w-64 bg-white rounded-xl border border-[rgba(59,77,67,0.12)] p-4 hover:shadow-md transition-shadow cursor-pointer group"
                onClick={() => handleViewSavedReport(report)}
              >
                <div className="flex items-start justify-between mb-2">
                  <h3 className="text-sm font-semibold text-[#3D4A44] truncate flex-1 mr-2">{report.title}</h3>
                  <button
                    onClick={(e) => { e.stopPropagation(); handleDeleteSavedReport(report.id) }}
                    className="p-1 rounded-lg opacity-0 group-hover:opacity-100 hover:bg-red-50 transition-all"
                  >
                    <TrashIcon className="w-3.5 h-3.5 text-red-400 hover:text-red-600" />
                  </button>
                </div>
                <div className="flex items-center gap-2 mb-2">
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                    report.report_type === 'SONGS' ? 'bg-blue-50 text-blue-700' : 'bg-purple-50 text-purple-700'
                  }`}>
                    {report.report_type || 'SONGS'}
                  </span>
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                    report.status === 'SENT' ? 'bg-emerald-50 text-emerald-700' : 'bg-[#5B8A72]/10 text-[#5B8A72]'
                  }`}>
                    {report.status || 'GENERATED'}
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs text-[#7A8580]">
                  <span>{report.item_count || 0} items</span>
                  {report.outstanding_count > 0 && (
                    <span className="text-red-500">{report.outstanding_count} outstanding</span>
                  )}
                </div>
                <div className="flex items-center gap-1 mt-2 text-[10px] text-[#B0BDB4]">
                  <ClockIcon className="w-3 h-3" />
                  {formatDate(report.generated_at || report.created_at)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {viewingSavedReport && (
        <div className="mb-4 bg-[#5B8A72]/5 border border-[#5B8A72]/15 rounded-xl px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <BookmarkSolidIcon className="w-5 h-5 text-[#5B8A72]" />
            <div>
              <span className="text-sm font-medium text-[#3D4A44]">
                Viewing saved report snapshot
              </span>
              <span className="text-xs text-[#7A8580] ml-2">
                Last generated: {formatDate(viewingSavedReport.generated_at)}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => handleDeleteSavedReport(viewingSavedReport.id)}
              className="flex items-center gap-1 px-3 py-1.5 text-red-600 hover:bg-red-50 rounded-lg text-xs font-medium transition-colors"
            >
              <TrashIcon className="w-3.5 h-3.5" />
              Delete
            </button>
          </div>
        </div>
      )}

      {!viewingSavedReport && (
        <div className="flex flex-col sm:flex-row gap-3 mb-6 items-start sm:items-center flex-wrap">
          <div className="flex bg-white rounded-xl border border-[rgba(59,77,67,0.12)] p-1">
            <button
              onClick={() => { setAssetType('songs'); setSelectedItems(new Set()) }}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                assetType === 'songs' ? 'bg-[#5B8A72] text-white shadow-sm' : 'text-[#7A8580] hover:text-[#3D4A44]'
              }`}
            >
              Songs
            </button>
            <button
              onClick={() => { setAssetType('works'); setSelectedItems(new Set()) }}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                assetType === 'works' ? 'bg-[#5B8A72] text-white shadow-sm' : 'text-[#7A8580] hover:text-[#3D4A44]'
              }`}
            >
              Works
            </button>
          </div>

          <div className="flex bg-white rounded-xl border border-[rgba(59,77,67,0.12)] p-1">
            {[
              { value: '', label: 'All' },
              { value: 'outstanding', label: 'Outstanding' },
              { value: 'registered', label: 'Registered' }
            ].map(opt => (
              <button
                key={opt.value}
                onClick={() => { setStatusFilter(opt.value); setSelectedItems(new Set()) }}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  statusFilter === opt.value ? 'bg-[#3D4A44] text-white shadow-sm' : 'text-[#7A8580] hover:text-[#3D4A44]'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>

          {creators.length > 0 && (
            <select
              value={selectedCreatorId}
              onChange={e => { setSelectedCreatorId(e.target.value); setSelectedItems(new Set()) }}
              className="border border-[rgba(59,77,67,0.12)] rounded-xl px-3 py-2.5 bg-white text-[#3D4A44] focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent text-sm"
            >
              <option value="">All Creators</option>
              {creators.map(c => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          )}
        </div>
      )}

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-2xl border border-[rgba(59,77,67,0.12)] p-5">
          <p className="text-sm text-[#7A8580] mb-1">Total</p>
          <p className="text-3xl font-bold text-[#3D4A44]">{reportData.length}</p>
        </div>
        <div className="bg-white rounded-2xl border border-[rgba(59,77,67,0.12)] p-5">
          <div className="flex items-center gap-2 mb-1">
            <div className="w-2 h-2 rounded-full bg-red-500"></div>
            <p className="text-sm text-[#7A8580]">Outstanding</p>
          </div>
          <p className="text-3xl font-bold text-red-600">{outstandingInView}</p>
        </div>
        <div className="bg-white rounded-2xl border border-[rgba(59,77,67,0.12)] p-5">
          <div className="flex items-center gap-2 mb-1">
            <CheckCircleIcon className="w-4 h-4 text-emerald-500" />
            <p className="text-sm text-[#7A8580]">Ready</p>
          </div>
          <p className="text-3xl font-bold text-emerald-600">{reportData.filter(i => i.is_valid).length}</p>
        </div>
        <div className="bg-white rounded-2xl border border-[rgba(59,77,67,0.12)] p-5">
          <div className="flex items-center gap-2 mb-1">
            <ExclamationTriangleIcon className="w-4 h-4 text-amber-500" />
            <p className="text-sm text-[#7A8580]">Needs Attention</p>
          </div>
          <p className="text-3xl font-bold text-amber-600">{reportData.filter(i => !i.is_valid).length}</p>
        </div>
      </div>

      {selectedCount > 0 && (
        <div className="bg-[#5B8A72]/10 border border-[#5B8A72]/20 rounded-xl px-4 py-3 mb-4 flex items-center justify-between">
          <span className="text-sm font-medium text-[#3D4A44]">
            {selectedCount} item{selectedCount !== 1 ? 's' : ''} selected
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={handleExportPDF}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-[#5B8A72] text-white rounded-lg text-xs font-medium hover:bg-[#4A7660] transition-colors"
            >
              <ArrowDownTrayIcon className="w-3.5 h-3.5" />
              Download PDF
            </button>
            <button
              onClick={openEmailModal}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-[#3D4A44] text-white rounded-lg text-xs font-medium hover:bg-[#2D3A34] transition-colors"
            >
              <EnvelopeIcon className="w-3.5 h-3.5" />
              Send to Admin
            </button>
            <button
              onClick={() => setSelectedItems(new Set())}
              className="text-xs text-[#7A8580] hover:text-[#3D4A44] ml-2"
            >
              Clear
            </button>
          </div>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="text-[#7A8580]">Loading report...</div>
        </div>
      ) : reportData.length === 0 ? (
        <div className="bg-white rounded-2xl border border-[rgba(59,77,67,0.12)] p-12 text-center">
          <DocumentTextIcon className="w-12 h-12 text-[#B0BDB4] mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-[#3D4A44] mb-1">No {assetType} found</h3>
          <p className="text-sm text-[#7A8580] max-w-md mx-auto">
            {statusFilter === 'outstanding' && summary.registered > 0
              ? `All ${assetType} are registered with your PRO. Try the "All" or "Registered" filter to view them.`
              : statusFilter === 'registered' && summary.outstanding > 0
              ? `No ${assetType} have been marked as registered yet. Switch to "Outstanding" to see items awaiting registration.`
              : assetType === 'works'
              ? 'No works found. Works represent compositions (the songwriting/publishing side). Try switching to the Songs tab — your catalog recordings will appear there.'
              : `Add songs to your catalog to track PRO registration. Once added, outstanding songs will appear here for you to select and generate bulk registration reports.`}
          </p>
          {assetType === 'works' && !viewingSavedReport && (
            <button
              onClick={() => { setAssetType('songs'); setSelectedItems(new Set()) }}
              className="mt-4 px-5 py-2.5 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-xl hover:shadow-[0px_4px_12px_rgba(91,138,114,0.3)] transition-all text-sm font-medium"
            >
              Switch to Songs
            </button>
          )}
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-[rgba(59,77,67,0.12)] overflow-hidden">
          <div className="flex items-center gap-3 px-5 py-3 border-b border-[rgba(59,77,67,0.08)] bg-[#F5F7F4]">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={allSelected}
                onChange={toggleSelectAll}
                className="w-4 h-4 rounded border-gray-300 text-[#5B8A72] focus:ring-[#5B8A72]"
              />
              <span className="text-xs font-medium text-[#7A8580]">Select All</span>
            </label>
            <span className="text-xs text-[#7A8580] ml-auto">
              {reportData.length} {assetType}
            </span>
          </div>

          {selectedCreatorId || viewingSavedReport ? (
            <div className="divide-y divide-[rgba(59,77,67,0.06)]">
              {reportData.map(item => (
                <ItemRow
                  key={item.id}
                  item={item}
                  assetType={assetType}
                  orgId={orgId}
                  isSelected={selectedItems.has(item.id)}
                  isExpanded={expandedItems.has(item.id)}
                  onToggleSelect={() => toggleSelected(item.id)}
                  onToggleExpand={() => toggleExpanded(item.id)}
                  onSaved={() => fetchReport(orgId, assetType, selectedCreatorId, statusFilter)}
                />
              ))}
            </div>
          ) : (
            groupedByCreator.map(([key, group]) => (
              <div key={key}>
                <div className="px-5 py-2.5 bg-[#F5F7F4]/60 border-b border-[rgba(59,77,67,0.06)]">
                  <span className="text-xs font-semibold text-[#5B8A72] uppercase tracking-wide">{group.name}</span>
                  <span className="text-xs text-[#7A8580] ml-2">({group.items.length})</span>
                </div>
                <div className="divide-y divide-[rgba(59,77,67,0.06)]">
                  {group.items.map(item => (
                    <ItemRow
                      key={`${key}_${item.id}`}
                      item={item}
                      assetType={assetType}
                      orgId={orgId}
                      isSelected={selectedItems.has(item.id)}
                      isExpanded={expandedItems.has(item.id)}
                      onToggleSelect={() => toggleSelected(item.id)}
                      onToggleExpand={() => toggleExpanded(item.id)}
                      onSaved={() => fetchReport(orgId, assetType, selectedCreatorId, statusFilter)}
                    />
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {showSaveModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md">
            <div className="flex items-center justify-between p-5 border-b border-[rgba(59,77,67,0.1)]">
              <div>
                <h2 className="text-lg font-semibold text-[#3D4A44]">Save Report</h2>
                <p className="text-sm text-[#7A8580] mt-0.5">
                  Save a snapshot of the current report for quick access later
                </p>
              </div>
              <button onClick={() => setShowSaveModal(false)} className="p-2 hover:bg-[#F5F7F4] rounded-lg transition-colors">
                <XMarkIcon className="w-5 h-5 text-[#7A8580]" />
              </button>
            </div>
            <div className="p-5 space-y-4">
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1.5">Report Title (optional)</label>
                <input
                  type="text"
                  value={saveTitle}
                  onChange={e => setSaveTitle(e.target.value)}
                  placeholder={`Bulk Registration — ${assetType.charAt(0).toUpperCase() + assetType.slice(1)}`}
                  className="w-full border border-[rgba(59,77,67,0.15)] rounded-xl px-3 py-2.5 text-[#3D4A44] focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent text-sm"
                />
              </div>
              <div className="bg-[#F5F7F4] rounded-lg p-3 text-xs text-[#7A8580] space-y-1">
                <p>Type: <span className="text-[#3D4A44] font-medium">{assetType.charAt(0).toUpperCase() + assetType.slice(1)}</span></p>
                <p>Filter: <span className="text-[#3D4A44] font-medium">{statusFilter || 'All'}</span></p>
                {selectedCreatorId && (
                  <p>Creator: <span className="text-[#3D4A44] font-medium">{creators.find(c => c.id === parseInt(selectedCreatorId))?.name || 'Selected'}</span></p>
                )}
                <p>Items: <span className="text-[#3D4A44] font-medium">{reportData.length}</span></p>
              </div>
            </div>
            <div className="flex items-center justify-end gap-3 p-5 border-t border-[rgba(59,77,67,0.1)]">
              <button
                onClick={() => setShowSaveModal(false)}
                className="px-4 py-2 text-sm font-medium text-[#7A8580] hover:text-[#3D4A44] transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveReport}
                disabled={savingReport}
                className="flex items-center gap-2 px-5 py-2.5 bg-[#5B8A72] text-white rounded-xl text-sm font-semibold hover:bg-[#4A7660] transition-colors disabled:opacity-50"
              >
                {savingReport ? 'Saving...' : (
                  <>
                    <BookmarkIcon className="w-4 h-4" />
                    Save Report
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {showEmailModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg">
            <div className="flex items-center justify-between p-5 border-b border-[rgba(59,77,67,0.1)]">
              <div>
                <h2 className="text-lg font-semibold text-[#3D4A44]">Send Bulk Registration Report</h2>
                <p className="text-sm text-[#7A8580] mt-0.5">
                  {selectedCount > 0 ? `${selectedCount} item${selectedCount !== 1 ? 's' : ''} selected` : `All outstanding ${assetType}`}
                </p>
              </div>
              <button onClick={() => setShowEmailModal(false)} className="p-2 hover:bg-[#F5F7F4] rounded-lg transition-colors">
                <XMarkIcon className="w-5 h-5 text-[#7A8580]" />
              </button>
            </div>

            <div className="p-5 space-y-4">
              {sendResult && (
                <div className={`p-3 rounded-lg text-sm ${sendResult.success ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-red-50 text-red-700 border border-red-200'}`}>
                  {sendResult.message}
                </div>
              )}

              {adminContacts.length > 0 && (
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1.5">Select Admin Contact</label>
                  <select
                    value={selectedAdminId}
                    onChange={e => handleAdminSelect(e.target.value)}
                    className="w-full border border-[rgba(59,77,67,0.15)] rounded-xl px-3 py-2.5 bg-white text-[#3D4A44] focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent text-sm"
                  >
                    <option value="">— Choose from directory or enter manually —</option>
                    {adminContacts.map(c => (
                      <option key={c.id} value={c.id}>
                        {c.display_name || c.name} — {c.email}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1.5">Recipient Email</label>
                <input
                  type="email"
                  value={emailForm.email}
                  onChange={e => setEmailForm(prev => ({ ...prev, email: e.target.value }))}
                  placeholder="admin@example.com"
                  className="w-full border border-[rgba(59,77,67,0.15)] rounded-xl px-3 py-2.5 text-[#3D4A44] focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent text-sm"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1.5">Recipient Name</label>
                <input
                  type="text"
                  value={emailForm.name}
                  onChange={e => setEmailForm(prev => ({ ...prev, name: e.target.value }))}
                  placeholder="John Smith"
                  className="w-full border border-[rgba(59,77,67,0.15)] rounded-xl px-3 py-2.5 text-[#3D4A44] focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent text-sm"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1.5">Message (optional)</label>
                <textarea
                  value={emailForm.message}
                  onChange={e => setEmailForm(prev => ({ ...prev, message: e.target.value }))}
                  placeholder="Please register the following works/songs with the PRO..."
                  rows={3}
                  className="w-full border border-[rgba(59,77,67,0.15)] rounded-xl px-3 py-2.5 text-[#3D4A44] focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent text-sm resize-none"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 p-5 border-t border-[rgba(59,77,67,0.1)]">
              <button
                onClick={() => setShowEmailModal(false)}
                className="px-4 py-2 text-sm font-medium text-[#7A8580] hover:text-[#3D4A44] transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSendEmail}
                disabled={!emailForm.email || sending}
                className="flex items-center gap-2 px-5 py-2.5 bg-[#5B8A72] text-white rounded-xl text-sm font-semibold hover:bg-[#4A7660] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {sending ? (
                  <>Sending...</>
                ) : (
                  <>
                    <PaperAirplaneIcon className="w-4 h-4" />
                    Send Report
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

const ROLE_OPTIONS_REG = ['Songwriter', 'Producer', 'Artist', 'Composer', 'Lyricist', 'Arranger', 'Featured Artist', 'Musician', 'Engineer']

function ItemRow({ item, assetType, orgId, isSelected, isExpanded, onToggleSelect, onToggleExpand, onSaved }) {
  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [editIsrc, setEditIsrc] = useState('')
  const [editIswc, setEditIswc] = useState('')
  const [editWriters, setEditWriters] = useState([])

  function startEditing() {
    setEditIsrc(item.isrc || '')
    setEditIswc(item.iswc || '')
    setEditWriters((item.writers || []).map(w => ({
      credit_id: w.credit_id,
      creator_id: w.creator_id,
      name: w.name,
      role: w.role || '',
      share: w.share != null ? String(w.share) : '',
      pro: w.pro || '',
      ipi: w.ipi || '',
    })))
    setEditing(true)
  }

  function cancelEditing() {
    setEditing(false)
  }

  async function saveEdits() {
    setSaving(true)
    try {
      const payload = {
        asset_type: assetType,
        asset_id: item.id,
        writers: editWriters.map(w => ({
          credit_id: w.credit_id,
          creator_id: w.creator_id,
          role: w.role,
          share: w.share === '' ? null : parseFloat(w.share),
          pro: w.pro,
          ipi: w.ipi,
        }))
      }
      if (assetType === 'songs') {
        payload.isrc = editIsrc
        payload.iswc = editIswc
      } else {
        payload.iswc = editIswc
      }
      await axios.patch(`/api/registration-reports/org/${orgId}/inline-edit`, payload)
      setEditing(false)
      if (onSaved) onSaved()
    } catch (err) {
      console.error('Inline edit failed:', err)
    } finally {
      setSaving(false)
    }
  }

  function updateWriter(idx, field, value) {
    setEditWriters(prev => prev.map((w, i) => i === idx ? { ...w, [field]: value } : w))
  }

  return (
    <div className={`${isSelected ? 'bg-[#5B8A72]/5' : 'hover:bg-[#F5F7F4]/50'} transition-colors`}>
      <div className="flex items-center gap-3 px-5 py-3.5">
        <input
          type="checkbox"
          checked={isSelected}
          onChange={onToggleSelect}
          className="w-4 h-4 rounded border-gray-300 text-[#5B8A72] focus:ring-[#5B8A72] flex-shrink-0"
        />
        <button
          onClick={onToggleExpand}
          className="flex items-center justify-between flex-1 min-w-0 text-left"
        >
          <div className="flex items-center gap-3 flex-1 min-w-0">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-semibold text-[#3D4A44] truncate">{item.title}</h3>
                {item.is_registered_with_pro ? (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 text-emerald-700 flex-shrink-0">
                    <CheckCircleIcon className="w-3 h-3" />
                    Registered
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-red-100 text-red-700 flex-shrink-0">
                    Outstanding
                  </span>
                )}
              </div>
              <div className="flex items-center gap-3 mt-0.5">
                {(item.iswc || item.isrc) && (
                  <span className="text-xs text-[#7A8580]">{item.iswc || item.isrc}</span>
                )}
                {item.primary_artist && (
                  <span className="text-xs text-[#7A8580]">{item.primary_artist}</span>
                )}
                {item.creators && item.creators.length > 0 && (
                  <span className="text-xs text-[#B0BDB4]">
                    {item.creators.map(c => c.name).join(', ')}
                  </span>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              {item.is_valid ? (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700">
                  <CheckCircleIcon className="w-3 h-3" />
                  Ready
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-50 text-amber-700">
                  <ExclamationTriangleIcon className="w-3 h-3" />
                  Issues
                </span>
              )}
            </div>
          </div>
          <div className="ml-2 flex-shrink-0 text-[#7A8580]">
            {isExpanded ? <ChevronUpIcon className="w-4 h-4" /> : <ChevronDownIcon className="w-4 h-4" />}
          </div>
        </button>
      </div>

      {isExpanded && (
        <div className="px-5 pb-4 ml-7 border-t border-[rgba(59,77,67,0.06)]">
          {!editing ? (
            <>
              {assetType === 'songs' && (
                <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-[#7A8580]">
                  <span>ISRC: <span className={item.isrc ? 'text-[#3D4A44] font-medium' : 'text-amber-500 italic'}>{item.isrc || 'Missing'}</span></span>
                  {item.iswc && <span>ISWC: <span className="text-[#3D4A44] font-medium">{item.iswc}</span></span>}
                </div>
              )}
              {assetType === 'works' && (
                <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-[#7A8580]">
                  <span>ISWC: <span className={item.iswc ? 'text-[#3D4A44] font-medium' : 'text-amber-500 italic'}>{item.iswc || 'Missing'}</span></span>
                </div>
              )}

              {item.writers && item.writers.length > 0 && (
                <div className="mt-3">
                  <h4 className="text-xs font-semibold text-[#3D4A44] mb-2 uppercase tracking-wide">Writers / Credits</h4>
                  <div className="space-y-1.5">
                    {item.writers.map((writer, idx) => (
                      <div key={idx} className="flex flex-wrap items-center gap-x-4 gap-y-1 py-2 px-3 bg-[#F5F7F4] rounded-lg text-sm">
                        <span className="font-medium text-[#3D4A44]">{writer.name}</span>
                        {writer.legal_name && <span className="text-[#7A8580] text-xs">({writer.legal_name})</span>}
                        {writer.role && <span className="text-[#7A8580] text-xs">Role: <span className="text-[#3D4A44]">{writer.role}</span></span>}
                        {writer.pro && <span className="text-[#7A8580] text-xs">PRO: <span className="text-[#3D4A44]">{writer.pro}</span></span>}
                        {writer.ipi && <span className="text-[#7A8580] text-xs">IPI: <span className="text-[#3D4A44]">{writer.ipi}</span></span>}
                        {writer.share != null && <span className="text-[#7A8580] text-xs">Share: <span className="text-[#3D4A44]">{writer.share}%</span></span>}
                        {writer.publisher && typeof writer.publisher === 'object' && writer.publisher.name && (
                          <span className="text-[#7A8580] text-xs">Publisher: <span className="text-[#3D4A44]">{writer.publisher.name}</span></span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {item.validation_issues && item.validation_issues.length > 0 && (
                <div className="mt-3">
                  <h4 className="text-xs font-semibold text-amber-600 mb-2 uppercase tracking-wide">Validation Issues</h4>
                  <ul className="space-y-1">
                    {item.validation_issues.map((issue, idx) => (
                      <li key={idx} className="flex items-start gap-2 text-xs text-amber-600">
                        <ExclamationTriangleIcon className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                        {issue}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <button
                onClick={startEditing}
                className="mt-3 inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-[#5B8A72] bg-[#5B8A72]/10 rounded-lg hover:bg-[#5B8A72]/20 transition-colors"
              >
                <PencilIcon className="w-3.5 h-3.5" />
                Edit Details
              </button>
            </>
          ) : (
            <div className="mt-3 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {assetType === 'songs' && (
                  <div>
                    <label className="block text-xs font-medium text-[#3D4A44] mb-1">ISRC</label>
                    <input
                      type="text"
                      value={editIsrc}
                      onChange={e => setEditIsrc(e.target.value)}
                      placeholder="e.g. USRC17607839"
                      className="w-full border border-[rgba(59,77,67,0.2)] rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                    />
                  </div>
                )}
                <div>
                  <label className="block text-xs font-medium text-[#3D4A44] mb-1">ISWC</label>
                  <input
                    type="text"
                    value={editIswc}
                    onChange={e => setEditIswc(e.target.value)}
                    placeholder="e.g. T-345246800-1"
                    className="w-full border border-[rgba(59,77,67,0.2)] rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  />
                </div>
              </div>

              {editWriters.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-[#3D4A44] mb-2 uppercase tracking-wide">Writers / Credits</h4>
                  <div className="space-y-3">
                    {editWriters.map((writer, idx) => (
                      <div key={writer.credit_id || idx} className="p-3 bg-[#F5F7F4] rounded-lg space-y-2">
                        <p className="text-sm font-medium text-[#3D4A44]">{writer.name}</p>
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                          <div>
                            <label className="block text-[10px] font-medium text-[#7A8580] mb-0.5">Role</label>
                            <select
                              value={writer.role}
                              onChange={e => updateWriter(idx, 'role', e.target.value)}
                              className="w-full border border-[rgba(59,77,67,0.2)] rounded-md px-2 py-1 text-xs bg-white text-[#3D4A44] focus:ring-1 focus:ring-[#5B8A72]"
                            >
                              <option value="">Select</option>
                              {ROLE_OPTIONS_REG.map(r => <option key={r} value={r}>{r}</option>)}
                            </select>
                          </div>
                          <div>
                            <label className="block text-[10px] font-medium text-[#7A8580] mb-0.5">Share %</label>
                            <input
                              type="number"
                              min="0"
                              max="100"
                              step="0.01"
                              value={writer.share}
                              onChange={e => updateWriter(idx, 'share', e.target.value)}
                              placeholder="25"
                              className="w-full border border-[rgba(59,77,67,0.2)] rounded-md px-2 py-1 text-xs bg-white text-[#3D4A44] focus:ring-1 focus:ring-[#5B8A72]"
                            />
                          </div>
                          <div>
                            <label className="block text-[10px] font-medium text-[#7A8580] mb-0.5">PRO</label>
                            <input
                              type="text"
                              value={writer.pro}
                              onChange={e => updateWriter(idx, 'pro', e.target.value)}
                              placeholder="BMI"
                              className="w-full border border-[rgba(59,77,67,0.2)] rounded-md px-2 py-1 text-xs bg-white text-[#3D4A44] focus:ring-1 focus:ring-[#5B8A72]"
                            />
                          </div>
                          <div>
                            <label className="block text-[10px] font-medium text-[#7A8580] mb-0.5">IPI</label>
                            <input
                              type="text"
                              value={writer.ipi}
                              onChange={e => updateWriter(idx, 'ipi', e.target.value)}
                              placeholder="123456789"
                              className="w-full border border-[rgba(59,77,67,0.2)] rounded-md px-2 py-1 text-xs bg-white text-[#3D4A44] focus:ring-1 focus:ring-[#5B8A72]"
                            />
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex items-center gap-2 pt-1">
                <button
                  onClick={saveEdits}
                  disabled={saving}
                  className="inline-flex items-center gap-1.5 px-4 py-1.5 text-xs font-medium text-white bg-[#5B8A72] rounded-lg hover:bg-[#4A7A62] transition-colors disabled:opacity-50"
                >
                  <CheckIcon className="w-3.5 h-3.5" />
                  {saving ? 'Saving...' : 'Save Changes'}
                </button>
                <button
                  onClick={cancelEditing}
                  className="inline-flex items-center gap-1.5 px-4 py-1.5 text-xs font-medium text-[#7A8580] bg-white border border-[rgba(59,77,67,0.15)] rounded-lg hover:bg-[#F5F7F4] transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
