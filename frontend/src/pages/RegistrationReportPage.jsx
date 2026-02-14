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
  ArrowPathIcon
} from '@heroicons/react/24/outline'
import { CheckCircleIcon } from '@heroicons/react/24/solid'

export default function RegistrationReportPage() {
  const [loading, setLoading] = useState(true)
  const [orgId, setOrgId] = useState(null)
  const [assetType, setAssetType] = useState('works')
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
    if (orgId) fetchReport(orgId, assetType, selectedCreatorId, statusFilter)
  }, [orgId, assetType, selectedCreatorId, statusFilter, fetchReport])

  function handleGenerateReport() {
    setSelectedItems(new Set())
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
      link.setAttribute('download', `Registration_Report_${assetType}.csv`)
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
      link.setAttribute('download', `Registration_Report_${assetType}.pdf`)
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

  return (
    <div className="p-4 sm:p-8">
      <div className="bg-gradient-to-r from-[#5B8A72] to-[#7A8580] rounded-2xl p-6 sm:p-8 mb-6 text-white">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <DocumentTextIcon className="w-8 h-8" />
              <h1 className="text-2xl sm:text-3xl font-bold">Registration Reports</h1>
            </div>
            <p className="text-white/80 text-sm sm:text-base">PRO registration management — select, report, and send</p>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <button
              onClick={handleGenerateReport}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-white/20 hover:bg-white/30 rounded-xl text-sm font-medium transition-colors disabled:opacity-50"
            >
              <ArrowPathIcon className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Generate
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
          </div>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row gap-3 mb-6 items-start sm:items-center flex-wrap">
        <div className="flex bg-white rounded-xl border border-[rgba(59,77,67,0.12)] p-1">
          <button
            onClick={() => { setAssetType('works'); setSelectedItems(new Set()) }}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              assetType === 'works' ? 'bg-[#5B8A72] text-white shadow-sm' : 'text-[#7A8580] hover:text-[#3D4A44]'
            }`}
          >
            Works
          </button>
          <button
            onClick={() => { setAssetType('songs'); setSelectedItems(new Set()) }}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              assetType === 'songs' ? 'bg-[#5B8A72] text-white shadow-sm' : 'text-[#7A8580] hover:text-[#3D4A44]'
            }`}
          >
            Songs
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
          <p className="text-sm text-[#7A8580]">
            {statusFilter === 'outstanding' 
              ? `All ${assetType} are registered! Try changing the filter.`
              : `Add ${assetType} to your catalog to generate registration reports.`}
          </p>
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

          {selectedCreatorId ? (
            <div className="divide-y divide-[rgba(59,77,67,0.06)]">
              {reportData.map(item => (
                <ItemRow
                  key={item.id}
                  item={item}
                  assetType={assetType}
                  isSelected={selectedItems.has(item.id)}
                  isExpanded={expandedItems.has(item.id)}
                  onToggleSelect={() => toggleSelected(item.id)}
                  onToggleExpand={() => toggleExpanded(item.id)}
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
                      isSelected={selectedItems.has(item.id)}
                      isExpanded={expandedItems.has(item.id)}
                      onToggleSelect={() => toggleSelected(item.id)}
                      onToggleExpand={() => toggleExpanded(item.id)}
                    />
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {showEmailModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg">
            <div className="flex items-center justify-between p-5 border-b border-[rgba(59,77,67,0.1)]">
              <div>
                <h2 className="text-lg font-semibold text-[#3D4A44]">Send Registration Report</h2>
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

function ItemRow({ item, assetType, isSelected, isExpanded, onToggleSelect, onToggleExpand }) {
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
        </div>
      )}
    </div>
  )
}
