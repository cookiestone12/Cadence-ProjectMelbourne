import React, { useState, useEffect } from 'react'
import axios from 'axios'
import {
  ShareIcon, DocumentTextIcon, MusicalNoteIcon,
  BanknotesIcon, UserGroupIcon, ClockIcon, XMarkIcon,
  ArrowDownTrayIcon, PlusCircleIcon, EyeIcon,
  CheckCircleIcon, ChevronDownIcon, ChevronUpIcon,
  DocumentDuplicateIcon
} from '@heroicons/react/24/outline'

export default function SharedWithMePage() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('received')
  const [sentItems, setSentItems] = useState([])
  const [expandedId, setExpandedId] = useState(null)
  const [detailsCache, setDetailsCache] = useState({})
  const [detailsLoading, setDetailsLoading] = useState({})
  const [importing, setImporting] = useState({})
  const [importedItems, setImportedItems] = useState({})

  useEffect(() => {
    loadItems()
  }, [])

  async function loadItems() {
    setLoading(true)
    try {
      const [received, sent] = await Promise.all([
        axios.get('/api/sharing/shared-with-me'),
        axios.get('/api/sharing/shared-by-me'),
      ])
      setItems(received.data || [])
      setSentItems(sent.data || [])
    } catch (error) {
      console.error('Failed to load shared items:', error)
    } finally {
      setLoading(false)
    }
  }

  async function handleRevoke(shareId) {
    if (!confirm('Revoke this share?')) return
    try {
      await axios.post(`/api/sharing/${shareId}/revoke`)
      setSentItems(prev => prev.map(i => i.id === shareId ? { ...i, status: 'REVOKED' } : i))
    } catch (error) {
      console.error('Failed to revoke:', error)
      alert('Failed to revoke share')
    }
  }

  async function toggleDetails(shareId) {
    if (expandedId === shareId) {
      setExpandedId(null)
      return
    }
    setExpandedId(shareId)
    if (detailsCache[shareId]) return
    setDetailsLoading(prev => ({ ...prev, [shareId]: true }))
    try {
      const res = await axios.get(`/api/sharing/${shareId}/details`)
      setDetailsCache(prev => ({ ...prev, [shareId]: res.data }))
    } catch (error) {
      console.error('Failed to load details:', error)
      setDetailsCache(prev => ({ ...prev, [shareId]: { error: error.response?.data?.detail || 'Failed to load details' } }))
    } finally {
      setDetailsLoading(prev => ({ ...prev, [shareId]: false }))
    }
  }

  async function handleDownload(shareId, itemName) {
    try {
      const res = await axios.get(`/api/sharing/${shareId}/download`, { responseType: 'blob' })
      const contentDisposition = res.headers['content-disposition']
      let filename = itemName || 'download'
      if (contentDisposition) {
        const match = contentDisposition.match(/filename="?([^";\n]+)"?/)
        if (match) filename = match[1]
      }
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', filename)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Download failed:', error)
      alert(error.response?.data?.detail || 'Failed to download file')
    }
  }

  async function handleImport(shareId) {
    if (importing[shareId]) return
    setImporting(prev => ({ ...prev, [shareId]: true }))
    try {
      const res = await axios.post(`/api/sharing/${shareId}/import`)
      setImportedItems(prev => ({ ...prev, [shareId]: res.data }))
    } catch (error) {
      console.error('Import failed:', error)
      alert(error.response?.data?.detail || 'Failed to import item')
    } finally {
      setImporting(prev => ({ ...prev, [shareId]: false }))
    }
  }

  const typeIcons = {
    DOCUMENT: DocumentTextIcon,
    AUDIO: MusicalNoteIcon,
    STATEMENT: BanknotesIcon,
    CONTACT_CARD: UserGroupIcon,
    SONG: MusicalNoteIcon,
    CONTRACT: DocumentDuplicateIcon,
  }
  const typeLabels = {
    DOCUMENT: 'Document',
    AUDIO: 'Audio File',
    STATEMENT: 'Statement',
    CONTACT_CARD: 'Contact Card',
    SONG: 'Catalog Entry',
    CONTRACT: 'Contract',
  }
  const typeColors = {
    DOCUMENT: 'bg-blue-50 text-blue-600',
    AUDIO: 'bg-purple-50 text-purple-600',
    STATEMENT: 'bg-amber-50 text-amber-600',
    CONTACT_CARD: 'bg-teal-50 text-teal-600',
    SONG: 'bg-green-50 text-green-600',
    CONTRACT: 'bg-indigo-50 text-indigo-600',
  }

  const canDownload = (type) => ['DOCUMENT', 'STATEMENT'].includes(type)
  const canImport = (type) => ['SONG', 'CONTACT_CARD'].includes(type)
  const importLabel = (type) => type === 'SONG' ? 'Add to Catalog' : type === 'CONTACT_CARD' ? 'Add to Directory' : 'Import'

  function formatDate(dateStr) {
    if (!dateStr) return ''
    const d = new Date(dateStr)
    const now = new Date()
    const diff = now - d
    if (diff < 60000) return 'Just now'
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`
    if (diff < 604800000) return `${Math.floor(diff / 86400000)}d ago`
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  }

  function renderDetails(detail) {
    if (!detail) return null
    if (detail.error) return <p className="text-xs text-red-500">{detail.error}</p>
    const data = detail.data
    if (!data) return <p className="text-xs text-[#7A8580]">Item data is no longer available</p>

    if (detail.item_type === 'SONG') {
      return (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-4 gap-y-2 text-xs">
          <div><span className="text-[#7A8580]">Title:</span> <span className="text-[#3D4A44] font-medium">{data.title}</span></div>
          <div><span className="text-[#7A8580]">Artist:</span> <span className="text-[#3D4A44] font-medium">{data.primary_artist}</span></div>
          {data.isrc && <div><span className="text-[#7A8580]">ISRC:</span> <span className="text-[#3D4A44]">{data.isrc}</span></div>}
          {data.iswc && <div><span className="text-[#7A8580]">ISWC:</span> <span className="text-[#3D4A44]">{data.iswc}</span></div>}
          {data.label && <div><span className="text-[#7A8580]">Label:</span> <span className="text-[#3D4A44]">{data.label}</span></div>}
          {data.project_title && <div><span className="text-[#7A8580]">Project:</span> <span className="text-[#3D4A44]">{data.project_title}</span></div>}
          {data.release_date && <div><span className="text-[#7A8580]">Release:</span> <span className="text-[#3D4A44]">{data.release_date}</span></div>}
          {data.publishing_percentage != null && <div><span className="text-[#7A8580]">Publishing %:</span> <span className="text-[#3D4A44]">{data.publishing_percentage}%</span></div>}
          {data.master_percentage != null && <div><span className="text-[#7A8580]">Master %:</span> <span className="text-[#3D4A44]">{data.master_percentage}%</span></div>}
          {data.notes && <div className="col-span-full"><span className="text-[#7A8580]">Notes:</span> <span className="text-[#3D4A44]">{data.notes}</span></div>}
        </div>
      )
    }

    if (detail.item_type === 'CONTACT_CARD') {
      return (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-4 gap-y-2 text-xs">
          <div><span className="text-[#7A8580]">Name:</span> <span className="text-[#3D4A44] font-medium">{data.display_name}</span></div>
          {data.legal_name && <div><span className="text-[#7A8580]">Legal:</span> <span className="text-[#3D4A44]">{data.legal_name}</span></div>}
          {data.email && <div><span className="text-[#7A8580]">Email:</span> <span className="text-[#3D4A44]">{data.email}</span></div>}
          {data.phone && <div><span className="text-[#7A8580]">Phone:</span> <span className="text-[#3D4A44]">{data.phone}</span></div>}
          {data.pro && <div><span className="text-[#7A8580]">PRO:</span> <span className="text-[#3D4A44]">{data.pro}</span></div>}
          {data.ipi && <div><span className="text-[#7A8580]">IPI:</span> <span className="text-[#3D4A44]">{data.ipi}</span></div>}
          {data.publisher_name && <div><span className="text-[#7A8580]">Publisher:</span> <span className="text-[#3D4A44]">{data.publisher_name}</span></div>}
          {(data.roles || []).length > 0 && (
            <div className="col-span-full"><span className="text-[#7A8580]">Roles:</span> <span className="text-[#3D4A44]">{data.roles.join(', ')}</span></div>
          )}
          {data.territory && <div><span className="text-[#7A8580]">Territory:</span> <span className="text-[#3D4A44]">{data.territory}</span></div>}
          {data.notes && <div className="col-span-full"><span className="text-[#7A8580]">Notes:</span> <span className="text-[#3D4A44]">{data.notes}</span></div>}
        </div>
      )
    }

    if (detail.item_type === 'DOCUMENT') {
      return (
        <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
          <div><span className="text-[#7A8580]">File:</span> <span className="text-[#3D4A44] font-medium">{data.file_name}</span></div>
          {data.file_size_bytes && <div><span className="text-[#7A8580]">Size:</span> <span className="text-[#3D4A44]">{(data.file_size_bytes / 1024 / 1024).toFixed(2)} MB</span></div>}
          {data.description && <div className="col-span-full"><span className="text-[#7A8580]">Description:</span> <span className="text-[#3D4A44]">{data.description}</span></div>}
        </div>
      )
    }

    if (detail.item_type === 'STATEMENT') {
      return (
        <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
          <div><span className="text-[#7A8580]">Source:</span> <span className="text-[#3D4A44] font-medium">{data.source_name}</span></div>
          {data.source_type && <div><span className="text-[#7A8580]">Type:</span> <span className="text-[#3D4A44]">{data.source_type}</span></div>}
          {data.period_start && <div><span className="text-[#7A8580]">Period:</span> <span className="text-[#3D4A44]">{data.period_start} - {data.period_end}</span></div>}
          {data.file_name && <div><span className="text-[#7A8580]">File:</span> <span className="text-[#3D4A44]">{data.file_name}</span></div>}
        </div>
      )
    }

    if (detail.item_type === 'AUDIO') {
      return (
        <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
          <div><span className="text-[#7A8580]">Name:</span> <span className="text-[#3D4A44] font-medium">{data.name}</span></div>
          {data.provider && <div><span className="text-[#7A8580]">Source:</span> <span className="text-[#3D4A44]">{data.provider}</span></div>}
          {data.duration_seconds && <div><span className="text-[#7A8580]">Duration:</span> <span className="text-[#3D4A44]">{Math.floor(data.duration_seconds / 60)}:{String(Math.floor(data.duration_seconds % 60)).padStart(2, '0')}</span></div>}
          {data.size_bytes && <div><span className="text-[#7A8580]">Size:</span> <span className="text-[#3D4A44]">{(data.size_bytes / 1024 / 1024).toFixed(2)} MB</span></div>}
        </div>
      )
    }

    if (detail.item_type === 'CONTRACT') {
      return (
        <div className="space-y-3">
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-4 gap-y-2 text-xs">
            <div><span className="text-[#7A8580]">Title:</span> <span className="text-[#3D4A44] font-medium">{data.title}</span></div>
            <div><span className="text-[#7A8580]">Type:</span> <span className="text-[#3D4A44]">{data.contract_type?.replace(/_/g, ' ')}</span></div>
            <div><span className="text-[#7A8580]">Status:</span> <span className="text-[#3D4A44]">{data.status}</span></div>
            {data.payment_direction && <div><span className="text-[#7A8580]">Direction:</span> <span className="text-[#3D4A44]">{data.payment_direction}</span></div>}
            {data.reference_number && <div><span className="text-[#7A8580]">Ref #:</span> <span className="text-[#3D4A44]">{data.reference_number}</span></div>}
            {data.start_date && <div><span className="text-[#7A8580]">Start:</span> <span className="text-[#3D4A44]">{data.start_date}</span></div>}
            {data.end_date && <div><span className="text-[#7A8580]">End:</span> <span className="text-[#3D4A44]">{data.end_date}</span></div>}
            {(data.territory || []).length > 0 && <div className="col-span-full"><span className="text-[#7A8580]">Territory:</span> <span className="text-[#3D4A44]">{data.territory.join(', ')}</span></div>}
            {data.advance_amount > 0 && <div><span className="text-[#7A8580]">Advance:</span> <span className="text-[#3D4A44]">{data.advance_currency} {data.advance_amount?.toLocaleString()}</span></div>}
            {data.terms_summary && <div className="col-span-full"><span className="text-[#7A8580]">Terms:</span> <span className="text-[#3D4A44]">{data.terms_summary}</span></div>}
            {data.notes && <div className="col-span-full"><span className="text-[#7A8580]">Notes:</span> <span className="text-[#3D4A44]">{data.notes}</span></div>}
          </div>
          {(data.parties || []).length > 0 && (
            <div>
              <p className="text-xs font-medium text-[#7A8580] mb-1">Parties</p>
              <div className="space-y-1">
                {data.parties.map((p, i) => (
                  <div key={i} className="text-xs text-[#3D4A44] flex items-center gap-2">
                    <span className="font-medium">{p.party_name}</span>
                    <span className="text-[#7A8580]">({p.party_role})</span>
                    {p.contact_email && <span className="text-[#7A8580]">{p.contact_email}</span>}
                  </div>
                ))}
              </div>
            </div>
          )}
          {(data.assets || []).length > 0 && (
            <div>
              <p className="text-xs font-medium text-[#7A8580] mb-1">Linked Assets</p>
              <div className="flex flex-wrap gap-1.5">
                {data.assets.map((a, i) => (
                  <span key={i} className="px-2 py-0.5 bg-[rgba(91,138,114,0.08)] text-[#3D4A44] rounded-full text-xs">
                    {a.name}
                  </span>
                ))}
              </div>
            </div>
          )}
          {(data.documents || []).length > 0 && (
            <div>
              <p className="text-xs font-medium text-[#7A8580] mb-1">Attached Documents</p>
              <div className="space-y-1">
                {data.documents.map((d, i) => (
                  <div key={i} className="text-xs text-[#3D4A44] flex items-center gap-2">
                    <DocumentTextIcon className="w-3.5 h-3.5 text-[#7A8580]" />
                    <span>{d.file_name}</span>
                    {d.description && <span className="text-[#7A8580]">- {d.description}</span>}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )
    }

    return null
  }

  const displayItems = activeTab === 'received' ? items : sentItems

  return (
    <div className="min-h-screen bg-[#F5F5F0]">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 bg-[rgba(91,138,114,0.1)] rounded-xl flex items-center justify-center">
            <ShareIcon className="w-5 h-5 text-[#5B8A72]" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-[#3D4A44]">Shared With Me</h1>
            <p className="text-sm text-[#7A8580]">Documents, catalog entries, and contacts shared with you</p>
          </div>
        </div>

        <div className="flex gap-2 mb-6">
          <button
            onClick={() => setActiveTab('received')}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
              activeTab === 'received'
                ? 'bg-[#5B8A72] text-white'
                : 'bg-white text-[#7A8580] hover:bg-[#F8F8FB]'
            }`}
          >
            Received ({items.length})
          </button>
          <button
            onClick={() => setActiveTab('sent')}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
              activeTab === 'sent'
                ? 'bg-[#5B8A72] text-white'
                : 'bg-white text-[#7A8580] hover:bg-[#F8F8FB]'
            }`}
          >
            Sent ({sentItems.length})
          </button>
        </div>

        {loading ? (
          <div className="text-center py-16">
            <div className="w-8 h-8 border-2 border-[#5B8A72] border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-sm text-[#7A8580] mt-3">Loading...</p>
          </div>
        ) : displayItems.length === 0 ? (
          <div className="bg-white rounded-2xl border border-[rgba(59,77,67,0.08)] p-12 text-center">
            <ShareIcon className="w-12 h-12 text-[#9CA8A3] mx-auto mb-4" />
            <p className="text-lg font-medium text-[#3D4A44]">
              {activeTab === 'received' ? 'Nothing shared with you yet' : 'You haven\'t shared anything yet'}
            </p>
            <p className="text-sm text-[#7A8580] mt-1">
              {activeTab === 'received' ? 'Shared documents and contacts will appear here' : 'Items you share will be tracked here'}
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {displayItems.map(item => {
              const Icon = typeIcons[item.item_type] || DocumentTextIcon
              const colorClass = typeColors[item.item_type] || 'bg-gray-50 text-gray-600'
              const isExpanded = expandedId === item.id
              const detail = detailsCache[item.id]
              const isLoadingDetail = detailsLoading[item.id]
              const imported = importedItems[item.id]
              const isImporting = importing[item.id]

              return (
                <div key={item.id} className="bg-white rounded-2xl border border-[rgba(59,77,67,0.08)] hover:shadow-sm transition-shadow">
                  <div className="p-4">
                    <div className="flex items-start gap-4">
                      <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${colorClass}`}>
                        <Icon className="w-5 h-5" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="text-sm font-semibold text-[#3D4A44] truncate">{item.item_name || 'Unnamed Item'}</h3>
                          <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${colorClass}`}>
                            {typeLabels[item.item_type] || item.item_type}
                          </span>
                          {item.status === 'REVOKED' && (
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-red-50 text-red-500">Revoked</span>
                          )}
                        </div>
                        <div className="flex items-center gap-3 text-xs text-[#7A8580]">
                          {activeTab === 'received' ? (
                            <>
                              <span>From: <strong className="text-[#3D4A44]">{item.shared_by?.username || 'Unknown'}</strong></span>
                              {item.shared_by_org && <span>· {item.shared_by_org}</span>}
                            </>
                          ) : (
                            <>
                              <span>To: <strong className="text-[#3D4A44]">
                                {item.shared_with?.username || item.shared_with?.email || 'Unknown'}
                              </strong></span>
                            </>
                          )}
                          <span className="flex items-center gap-1">
                            <ClockIcon className="w-3 h-3" />
                            {formatDate(item.created_at)}
                          </span>
                        </div>
                        {item.message && (
                          <p className="mt-2 text-xs text-[#7A8580] bg-[#F8F8FB] rounded-lg px-3 py-2 italic">
                            "{item.message}"
                          </p>
                        )}
                      </div>

                      <div className="flex items-center gap-2 flex-shrink-0">
                        {activeTab === 'received' && item.status !== 'REVOKED' && (
                          <>
                            <button
                              onClick={() => toggleDetails(item.id)}
                              className="flex items-center gap-1 text-xs text-[#5B8A72] hover:bg-[#EEF1EC] px-2.5 py-1.5 rounded-lg transition-colors"
                              title="View details"
                            >
                              <EyeIcon className="w-3.5 h-3.5" />
                              <span className="hidden sm:inline">Details</span>
                              {isExpanded ? <ChevronUpIcon className="w-3 h-3" /> : <ChevronDownIcon className="w-3 h-3" />}
                            </button>

                            {canDownload(item.item_type) && (
                              <button
                                onClick={() => handleDownload(item.id, item.item_name)}
                                className="flex items-center gap-1 text-xs text-[#5B8A72] hover:bg-[#EEF1EC] px-2.5 py-1.5 rounded-lg transition-colors"
                                title="Download file"
                              >
                                <ArrowDownTrayIcon className="w-3.5 h-3.5" />
                                <span className="hidden sm:inline">Download</span>
                              </button>
                            )}

                            {canImport(item.item_type) && !imported && (
                              <button
                                onClick={() => handleImport(item.id)}
                                disabled={isImporting}
                                className="flex items-center gap-1 text-xs text-white bg-[#5B8A72] hover:bg-[#4A7A62] px-3 py-1.5 rounded-lg transition-colors disabled:opacity-50"
                                title={importLabel(item.item_type)}
                              >
                                {isImporting ? (
                                  <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                ) : (
                                  <PlusCircleIcon className="w-3.5 h-3.5" />
                                )}
                                <span className="hidden sm:inline">{importLabel(item.item_type)}</span>
                              </button>
                            )}

                            {imported && (
                              <span className="flex items-center gap-1 text-xs text-[#5B8A72] bg-[#EEF1EC] px-3 py-1.5 rounded-lg">
                                <CheckCircleIcon className="w-3.5 h-3.5" />
                                <span className="hidden sm:inline">Added</span>
                              </span>
                            )}
                          </>
                        )}
                        {activeTab === 'sent' && item.status === 'ACTIVE' && (
                          <button
                            onClick={() => handleRevoke(item.id)}
                            className="text-xs text-[#C47068] hover:bg-red-50 px-3 py-1.5 rounded-lg transition-colors"
                          >
                            Revoke
                          </button>
                        )}
                      </div>
                    </div>
                  </div>

                  {activeTab === 'received' && isExpanded && (
                    <div className="px-4 pb-4 pt-0">
                      <div className="bg-[#FAFBF9] rounded-xl p-4 border border-[rgba(59,77,67,0.06)]">
                        {isLoadingDetail ? (
                          <div className="flex items-center gap-2">
                            <div className="w-4 h-4 border-2 border-[#5B8A72] border-t-transparent rounded-full animate-spin" />
                            <span className="text-xs text-[#7A8580]">Loading details...</span>
                          </div>
                        ) : (
                          renderDetails(detail)
                        )}
                      </div>
                      {imported && (
                        <div className="mt-3 flex items-center gap-2 text-xs text-[#5B8A72] bg-[#EEF1EC] rounded-lg px-3 py-2">
                          <CheckCircleIcon className="w-4 h-4" />
                          <span>{imported.message}</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
