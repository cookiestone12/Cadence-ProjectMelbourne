import React, { useState, useEffect } from 'react'
import axios from 'axios'
import {
  MagnifyingGlassIcon, PlusIcon, XMarkIcon, TrashIcon,
  PencilIcon, UserGroupIcon, LinkIcon, DocumentTextIcon,
  MusicalNoteIcon, CalendarIcon, CurrencyDollarIcon,
  ChevronDownIcon, ArrowDownTrayIcon, PaperClipIcon, CloudArrowUpIcon
} from '@heroicons/react/24/outline'

const STATUS_COLORS = {
  DRAFT: 'bg-gray-100 text-gray-700',
  PENDING: 'bg-yellow-100 text-yellow-700',
  ACTIVE: 'bg-green-100 text-green-700',
  EXPIRED: 'bg-red-100 text-red-700',
  TERMINATED: 'bg-red-100 text-red-800',
}

const TYPE_COLORS = {
  MASTER: 'bg-purple-100 text-purple-700',
  PUBLISHING: 'bg-blue-100 text-blue-700',
  SYNC_LICENSE: 'bg-teal-100 text-teal-700',
  DISTRIBUTION: 'bg-orange-100 text-orange-700',
}

const TYPE_LABELS = {
  MASTER: 'Master',
  PUBLISHING: 'Publishing',
  SYNC_LICENSE: 'Sync License',
  DISTRIBUTION: 'Distribution',
  MECHANICAL: 'Mechanical',
  PERFORMANCE: 'Performance',
  OTHER: 'Other',
}

const PARTY_ROLES = ['LICENSOR', 'LICENSEE', 'PUBLISHER', 'ARTIST', 'LABEL', 'MANAGER', 'PRODUCER', 'OTHER']

const RIGHTS_TYPES = ['MECHANICAL', 'PERFORMANCE', 'SYNC', 'MASTER', 'PUBLISHING', 'DISTRIBUTION', 'OTHER']

const CURRENCIES = ['USD', 'EUR', 'GBP', 'CAD', 'AUD', 'JPY']

const emptyCreateForm = {
  title: '', contract_type: 'MASTER', status: 'DRAFT', reference_number: '',
  start_date: '', end_date: '', territory: '', advance_amount: '', advance_currency: 'USD',
  notes: '', terms_summary: '',
}

const emptyPartyForm = { party_name: '', party_role: 'ARTIST', creator_id: '', contact_email: '' }

export default function ContractsPage() {
  const [contracts, setContracts] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [organizationId, setOrganizationId] = useState(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [selectedContract, setSelectedContract] = useState(null)
  const [contractDetail, setContractDetail] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [songs, setSongs] = useState([])
  const [works, setWorks] = useState([])
  const [creators, setCreators] = useState([])
  const [editMode, setEditMode] = useState(false)
  const [editForm, setEditForm] = useState({})
  const [createForm, setCreateForm] = useState({ ...emptyCreateForm })
  const [createParties, setCreateParties] = useState([])
  const [createError, setCreateError] = useState('')
  const [createLoading, setCreateLoading] = useState(false)
  const [activeDetailTab, setActiveDetailTab] = useState('overview')
  const [partyForm, setPartyForm] = useState({ ...emptyPartyForm })
  const [assetSearch, setAssetSearch] = useState('')
  const [showAssetDropdown, setShowAssetDropdown] = useState(false)
  const [assetTypeFilter, setAssetTypeFilter] = useState('SONG')
  const [splitForms, setSplitForms] = useState({})
  const [editingSplit, setEditingSplit] = useState(null)
  const [editSplitForm, setEditSplitForm] = useState({})
  const [contractDocuments, setContractDocuments] = useState([])
  const [docUploading, setDocUploading] = useState(false)
  const [docDescription, setDocDescription] = useState('')
  const [docLinkType, setDocLinkType] = useState('')
  const [docLinkId, setDocLinkId] = useState('')

  useEffect(() => {
    loadData()
  }, [])

  async function loadData() {
    try {
      const orgResponse = await axios.get('/api/organizations/current')
      const orgId = orgResponse.data?.id
      if (!orgId) { setLoading(false); return }
      setOrganizationId(orgId)

      axios.get(`/api/rights/contracts/org/${orgId}`).then(res => {
        const data = res.data
        setContracts(Array.isArray(data) ? data : data.contracts || [])
      }).catch(e => console.error('Failed to load contracts:', e))
        .finally(() => setLoading(false))

      axios.get(`/api/songs/org/${orgId}?limit=1000`).then(res => {
        setSongs(Array.isArray(res.data) ? res.data : [])
      }).catch(e => console.error('Failed to load songs:', e))

      axios.get(`/api/works/org/${orgId}?limit=500`).then(res => {
        setWorks(res.data?.works || (Array.isArray(res.data) ? res.data : []))
      }).catch(e => console.error('Failed to load works:', e))

      axios.get(`/api/creators/org/${orgId}`).then(res => {
        setCreators(Array.isArray(res.data) ? res.data : [])
      }).catch(e => console.error('Failed to load creators:', e))

      axios.get(`/api/releases/org/${orgId}?limit=500`).then(res => {
        setReleases(res.data?.releases || (Array.isArray(res.data) ? res.data : []))
      }).catch(e => console.error('Failed to load releases:', e))
    } catch (error) {
      console.error('Failed to load contracts page:', error)
      setLoading(false)
    }
  }

  const filteredContracts = contracts.filter(c => {
    if (statusFilter && c.status !== statusFilter) return false
    if (typeFilter && c.contract_type !== typeFilter) return false
    if (!searchTerm) return true
    const term = searchTerm.toLowerCase()
    return (
      (c.title && c.title.toLowerCase().includes(term)) ||
      (c.reference_number && c.reference_number.toLowerCase().includes(term))
    )
  })

  async function openContractDetail(contract) {
    setSelectedContract(contract)
    setDetailLoading(true)
    setActiveDetailTab('overview')
    setEditMode(false)
    setSplitForms({})
    setEditingSplit(null)
    setContractDocuments([])
    setDocDescription('')
    setDocLinkType('')
    setDocLinkId('')
    try {
      const res = await axios.get(`/api/rights/contracts/${contract.id}`)
      setContractDetail(res.data)
      setEditForm({
        title: res.data.title || '',
        contract_type: res.data.contract_type || 'MASTER',
        status: res.data.status || 'DRAFT',
        reference_number: res.data.reference_number || '',
        start_date: res.data.start_date || '',
        end_date: res.data.end_date || '',
        territory: Array.isArray(res.data.territory) ? res.data.territory.join(', ') : (res.data.territory || ''),
        advance_amount: res.data.advance_amount || '',
        advance_currency: res.data.advance_currency || 'USD',
        notes: res.data.notes || '',
        terms_summary: res.data.terms_summary || '',
      })
      loadDocuments(contract.id)
    } catch (error) {
      console.error('Failed to load contract detail:', error)
    } finally {
      setDetailLoading(false)
    }
  }

  async function refreshDetail() {
    if (!contractDetail) return
    try {
      const res = await axios.get(`/api/rights/contracts/${contractDetail.id}`)
      setContractDetail(res.data)
    } catch (error) {
      console.error('Failed to refresh contract detail:', error)
    }
  }

  async function loadDocuments(contractId) {
    try {
      const res = await axios.get(`/api/rights/contracts/${contractId}/documents`)
      setContractDocuments(Array.isArray(res.data) ? res.data : [])
    } catch (error) {
      console.error('Failed to load documents:', error)
    }
  }

  async function handleUploadDocument(file) {
    if (!contractDetail) return
    setDocUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      if (docDescription.trim()) formData.append('description', docDescription.trim())
      if (docLinkType === 'song' && docLinkId) formData.append('song_id', docLinkId)
      if (docLinkType === 'work' && docLinkId) formData.append('work_id', docLinkId)
      if (docLinkType === 'release' && docLinkId) formData.append('release_id', docLinkId)
      await axios.post(`/api/rights/contracts/${contractDetail.id}/documents`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      setDocDescription('')
      setDocLinkType('')
      setDocLinkId('')
      loadDocuments(contractDetail.id)
      refreshDetail()
    } catch (error) {
      console.error('Failed to upload document:', error)
      alert(error.response?.data?.detail || 'Failed to upload document')
    } finally {
      setDocUploading(false)
    }
  }

  async function handleDownloadDocument(doc) {
    try {
      const res = await axios.get(`/api/rights/contracts/documents/${doc.id}/download`, {
        responseType: 'blob'
      })
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', doc.file_name)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Failed to download document:', error)
    }
  }

  async function handleDeleteDocument(docId) {
    if (!confirm('Delete this document?')) return
    try {
      await axios.delete(`/api/rights/contracts/documents/${docId}`)
      loadDocuments(contractDetail.id)
      refreshDetail()
    } catch (error) {
      console.error('Failed to delete document:', error)
    }
  }

  const [releases, setReleases] = useState([])

  async function handleCreateContract() {
    if (!createForm.title.trim()) {
      setCreateError('Please enter a contract title.')
      return
    }
    setCreateError('')
    setCreateLoading(true)
    try {
      const payload = { ...createForm }
      if (payload.advance_amount) payload.advance_amount = parseFloat(payload.advance_amount)
      else delete payload.advance_amount
      if (!payload.start_date) delete payload.start_date
      if (!payload.end_date) delete payload.end_date
      if (!payload.reference_number) delete payload.reference_number
      if (payload.territory && typeof payload.territory === 'string') {
        payload.territory = payload.territory.split(',').map(t => t.trim()).filter(Boolean)
      } else if (!payload.territory) {
        payload.territory = []
      }
      if (createParties.length > 0) payload.parties = createParties
      await axios.post(`/api/rights/contracts/org/${organizationId}`, payload)
      setShowCreateModal(false)
      setCreateForm({ ...emptyCreateForm })
      setCreateParties([])
      setCreateError('')
      await loadData()
    } catch (error) {
      console.error('Failed to create contract:', error)
      setCreateError(error.response?.data?.detail || 'Failed to create contract. Please try again.')
    } finally {
      setCreateLoading(false)
    }
  }

  async function handleUpdateContract() {
    if (!contractDetail) return
    try {
      const payload = { ...editForm }
      if (payload.advance_amount) payload.advance_amount = parseFloat(payload.advance_amount)
      else payload.advance_amount = null
      if (payload.territory && typeof payload.territory === 'string') {
        payload.territory = payload.territory.split(',').map(t => t.trim()).filter(Boolean)
      } else if (!payload.territory) {
        payload.territory = []
      }
      await axios.put(`/api/rights/contracts/${contractDetail.id}`, payload)
      setEditMode(false)
      await loadData()
      await refreshDetail()
    } catch (error) {
      console.error('Failed to update contract:', error)
    }
  }

  async function handleDeleteContract() {
    if (!contractDetail) return
    if (!window.confirm('Are you sure you want to delete this contract?')) return
    try {
      await axios.delete(`/api/rights/contracts/${contractDetail.id}`)
      setSelectedContract(null)
      setContractDetail(null)
      await loadData()
    } catch (error) {
      console.error('Failed to delete contract:', error)
    }
  }

  async function handleAddParty() {
    if (!contractDetail || !partyForm.party_name.trim()) return
    try {
      const payload = { ...partyForm }
      if (payload.creator_id) payload.creator_id = parseInt(payload.creator_id)
      else delete payload.creator_id
      if (!payload.contact_email) delete payload.contact_email
      await axios.post(`/api/rights/contracts/${contractDetail.id}/parties`, payload)
      setPartyForm({ ...emptyPartyForm })
      await refreshDetail()
    } catch (error) {
      console.error('Failed to add party:', error)
    }
  }

  async function handleRemoveParty(partyId) {
    if (!contractDetail) return
    try {
      await axios.delete(`/api/rights/contracts/${contractDetail.id}/parties/${partyId}`)
      await refreshDetail()
    } catch (error) {
      console.error('Failed to remove party:', error)
    }
  }

  async function handleLinkAsset(assetType, assetId) {
    if (!contractDetail) return
    try {
      await axios.post(`/api/rights/contracts/${contractDetail.id}/assets`, {
        asset_type: assetType,
        asset_id: assetId
      })
      setShowAssetDropdown(false)
      setAssetSearch('')
      await refreshDetail()
    } catch (error) {
      console.error('Failed to link asset:', error)
    }
  }

  async function handleUnlinkAsset(contractAssetId) {
    if (!contractDetail) return
    try {
      await axios.delete(`/api/rights/contracts/${contractDetail.id}/assets/${contractAssetId}`)
      await refreshDetail()
    } catch (error) {
      console.error('Failed to unlink asset:', error)
    }
  }

  async function handleAddSplit(contractAssetId) {
    if (!contractDetail) return
    const form = splitForms[contractAssetId]
    if (!form || !form.rights_holder_id || !form.rights_type || !form.share_percentage) return
    try {
      await axios.post(`/api/rights/contracts/${contractDetail.id}/assets/${contractAssetId}/splits`, {
        rights_holder_id: parseInt(form.rights_holder_id),
        rights_type: form.rights_type,
        share_percentage: parseFloat(form.share_percentage),
        notes: form.notes || ''
      })
      setSplitForms(prev => ({ ...prev, [contractAssetId]: undefined }))
      await refreshDetail()
    } catch (error) {
      console.error('Failed to add split:', error)
    }
  }

  async function handleUpdateSplit(splitId) {
    try {
      await axios.put(`/api/rights/splits/${splitId}`, {
        rights_type: editSplitForm.rights_type,
        share_percentage: parseFloat(editSplitForm.share_percentage),
        notes: editSplitForm.notes || ''
      })
      setEditingSplit(null)
      setEditSplitForm({})
      await refreshDetail()
    } catch (error) {
      console.error('Failed to update split:', error)
    }
  }

  async function handleDeleteSplit(splitId) {
    try {
      await axios.delete(`/api/rights/splits/${splitId}`)
      await refreshDetail()
    } catch (error) {
      console.error('Failed to delete split:', error)
    }
  }

  function formatDate(dateStr) {
    if (!dateStr) return '-'
    return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  }

  function formatCurrency(amount, currency) {
    if (!amount) return null
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: currency || 'USD' }).format(amount)
  }

  function getTypeBadgeClass(type) {
    return TYPE_COLORS[type] || 'bg-gray-100 text-gray-700'
  }

  function getStatusBadgeClass(status) {
    return STATUS_COLORS[status] || 'bg-gray-100 text-gray-700'
  }

  function getSplitTotalsByType(splits) {
    const totals = {}
    ;(splits || []).forEach(s => {
      if (!totals[s.rights_type]) totals[s.rights_type] = 0
      totals[s.rights_type] += parseFloat(s.share_percentage || 0)
    })
    return totals
  }

  const linkedAssetIds = contractDetail?.assets?.map(a => `${a.asset_type}-${a.asset_id}`) || []

  const availableAssets = assetTypeFilter === 'SONG'
    ? songs.filter(s => {
        if (linkedAssetIds.includes(`SONG-${s.id}`)) return false
        if (!assetSearch) return true
        return s.title.toLowerCase().includes(assetSearch.toLowerCase()) ||
          (s.primary_artist && s.primary_artist.toLowerCase().includes(assetSearch.toLowerCase()))
      })
    : works.filter(w => {
        if (linkedAssetIds.includes(`WORK-${w.id}`)) return false
        if (!assetSearch) return true
        return w.title.toLowerCase().includes(assetSearch.toLowerCase())
      })

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-[#7A8580]">Loading contracts...</div>
      </div>
    )
  }

  return (
    <div className="p-4 sm:p-8">
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <div>
            <h1 className="text-2xl sm:text-4xl font-bold text-[#3D4A44] mb-2">Contracts & Rights</h1>
            <p className="text-[#7A8580]">
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-[#EEF1EC] text-[#3D4A44] mr-2">
                {contracts.length}
              </span>
              total contracts
            </p>
          </div>
        </div>
        <button
          className="flex items-center space-x-2 px-4 py-2 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] transition-colors"
          onClick={() => { setShowCreateModal(true); setCreateError(''); setCreateLoading(false) }}
        >
          <PlusIcon className="w-5 h-5" />
          <span>New Contract</span>
        </button>
      </div>

      <div className="bg-[#FAFBF9] rounded-xl shadow-sm p-4 mb-6">
        <div className="flex items-center space-x-4">
          <div className="flex-1 relative">
            <MagnifyingGlassIcon className="w-5 h-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-[#7A8580]" />
            <input
              type="text"
              placeholder="Search by title or reference number..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 bg-white text-[#3D4A44] text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
          >
            <option value="">All Statuses</option>
            <option value="DRAFT">Draft</option>
            <option value="PENDING">Pending</option>
            <option value="ACTIVE">Active</option>
            <option value="EXPIRED">Expired</option>
            <option value="TERMINATED">Terminated</option>
          </select>
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 bg-white text-[#3D4A44] text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
          >
            <option value="">All Types</option>
            {Object.entries(TYPE_LABELS).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredContracts.map(contract => (
          <div
            key={contract.id}
            onClick={() => openContractDetail(contract)}
            className="bg-[#FAFBF9] rounded-xl shadow-sm p-5 hover:shadow-md cursor-pointer transition-all hover:bg-[rgba(91,138,114,0.04)]"
          >
            <div className="flex items-start justify-between mb-3">
              <h3 className="font-semibold text-[#3D4A44] text-sm leading-tight flex-1 mr-2">{contract.title}</h3>
              <span className={`px-2 py-0.5 rounded-full text-xs font-medium whitespace-nowrap ${getStatusBadgeClass(contract.status)}`}>
                {contract.status}
              </span>
            </div>
            <div className="flex items-center space-x-2 mb-3">
              <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getTypeBadgeClass(contract.contract_type)}`}>
                {TYPE_LABELS[contract.contract_type] || contract.contract_type}
              </span>
              {contract.territory && (Array.isArray(contract.territory) ? contract.territory.length > 0 : contract.territory) && (
                <span className="px-2 py-0.5 rounded-full text-xs bg-[#EEF1EC] text-[#7A8580]">
                  {Array.isArray(contract.territory) ? contract.territory.join(', ') : contract.territory}
                </span>
              )}
            </div>
            <div className="flex items-center text-xs text-[#7A8580] space-x-3 mb-2">
              <span className="flex items-center space-x-1">
                <CalendarIcon className="w-3.5 h-3.5" />
                <span>{formatDate(contract.start_date)} — {formatDate(contract.end_date)}</span>
              </span>
            </div>
            {contract.advance_amount > 0 && (
              <div className="flex items-center text-xs text-[#5B8A72] font-medium mb-2">
                <CurrencyDollarIcon className="w-3.5 h-3.5 mr-1" />
                {formatCurrency(contract.advance_amount, contract.advance_currency)}
              </div>
            )}
            <div className="flex items-center space-x-4 text-xs text-[#7A8580] pt-2 border-t border-[rgba(59,77,67,0.08)]">
              <span className="flex items-center space-x-1">
                <UserGroupIcon className="w-3.5 h-3.5" />
                <span>{contract.party_count || (contract.parties ? contract.parties.length : 0)} parties</span>
              </span>
              <span className="flex items-center space-x-1">
                <LinkIcon className="w-3.5 h-3.5" />
                <span>{contract.asset_count || 0} assets</span>
              </span>
            </div>
          </div>
        ))}
        {filteredContracts.length === 0 && (
          <div className="col-span-full py-12 text-center text-[#7A8580]">
            No contracts found
          </div>
        )}
      </div>

      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl mx-4 max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between p-6 border-b border-[rgba(59,77,67,0.08)]">
              <h3 className="text-lg font-semibold text-[#3D4A44]">New Contract</h3>
              <button onClick={() => { setShowCreateModal(false); setCreateParties([]) }} className="text-[#7A8580] hover:text-[#3D4A44]">
                <XMarkIcon className="w-5 h-5" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Title *</label>
                  <input
                    type="text"
                    value={createForm.title}
                    onChange={(e) => setCreateForm(prev => ({ ...prev, title: e.target.value }))}
                    className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                    placeholder="Contract title"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Type</label>
                  <select
                    value={createForm.contract_type}
                    onChange={(e) => setCreateForm(prev => ({ ...prev, contract_type: e.target.value }))}
                    className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  >
                    {Object.entries(TYPE_LABELS).map(([k, v]) => (
                      <option key={k} value={k}>{v}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Status</label>
                  <select
                    value={createForm.status}
                    onChange={(e) => setCreateForm(prev => ({ ...prev, status: e.target.value }))}
                    className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  >
                    {Object.keys(STATUS_COLORS).map(s => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Reference Number</label>
                  <input
                    type="text"
                    value={createForm.reference_number}
                    onChange={(e) => setCreateForm(prev => ({ ...prev, reference_number: e.target.value }))}
                    className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                    placeholder="REF-001"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Territory</label>
                  <input
                    type="text"
                    value={createForm.territory}
                    onChange={(e) => setCreateForm(prev => ({ ...prev, territory: e.target.value }))}
                    className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                    placeholder="Worldwide, US, EU..."
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Start Date</label>
                  <input
                    type="date"
                    value={createForm.start_date}
                    onChange={(e) => setCreateForm(prev => ({ ...prev, start_date: e.target.value }))}
                    className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">End Date</label>
                  <input
                    type="date"
                    value={createForm.end_date}
                    onChange={(e) => setCreateForm(prev => ({ ...prev, end_date: e.target.value }))}
                    className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Advance Amount</label>
                  <input
                    type="number"
                    value={createForm.advance_amount}
                    onChange={(e) => setCreateForm(prev => ({ ...prev, advance_amount: e.target.value }))}
                    className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                    placeholder="0.00"
                    min="0"
                    step="0.01"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Currency</label>
                  <select
                    value={createForm.advance_currency}
                    onChange={(e) => setCreateForm(prev => ({ ...prev, advance_currency: e.target.value }))}
                    className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  >
                    {CURRENCIES.map(c => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Notes</label>
                  <textarea
                    value={createForm.notes}
                    onChange={(e) => setCreateForm(prev => ({ ...prev, notes: e.target.value }))}
                    className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                    rows={2}
                    placeholder="Additional notes..."
                  />
                </div>
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Terms Summary</label>
                  <textarea
                    value={createForm.terms_summary}
                    onChange={(e) => setCreateForm(prev => ({ ...prev, terms_summary: e.target.value }))}
                    className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                    rows={2}
                    placeholder="Key terms..."
                  />
                </div>
              </div>

              <div className="border-t border-[rgba(59,77,67,0.08)] pt-4">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-sm font-semibold text-[#3D4A44]">Parties</h4>
                </div>
                {createParties.map((p, idx) => (
                  <div key={idx} className="flex items-center space-x-2 mb-2 p-2 bg-[#F5F7F4] rounded-lg">
                    <span className="text-sm text-[#3D4A44] flex-1">{p.party_name}</span>
                    <span className="text-xs px-2 py-0.5 bg-[#EEF1EC] rounded-full text-[#7A8580]">{p.party_role}</span>
                    {p.contact_email && <span className="text-xs text-[#7A8580]">{p.contact_email}</span>}
                    <button onClick={() => setCreateParties(prev => prev.filter((_, i) => i !== idx))} className="text-[#7A8580] hover:text-red-500">
                      <XMarkIcon className="w-4 h-4" />
                    </button>
                  </div>
                ))}
                <div className="grid grid-cols-4 gap-2">
                  <input
                    type="text"
                    placeholder="Name"
                    value={partyForm.party_name}
                    onChange={(e) => setPartyForm(prev => ({ ...prev, party_name: e.target.value }))}
                    className="border border-[rgba(59,77,67,0.12)] rounded-lg px-2 py-1.5 text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  />
                  <select
                    value={partyForm.party_role}
                    onChange={(e) => setPartyForm(prev => ({ ...prev, party_role: e.target.value }))}
                    className="border border-[rgba(59,77,67,0.12)] rounded-lg px-2 py-1.5 text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  >
                    {PARTY_ROLES.map(r => <option key={r} value={r}>{r}</option>)}
                  </select>
                  <input
                    type="email"
                    placeholder="Email"
                    value={partyForm.contact_email}
                    onChange={(e) => setPartyForm(prev => ({ ...prev, contact_email: e.target.value }))}
                    className="border border-[rgba(59,77,67,0.12)] rounded-lg px-2 py-1.5 text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  />
                  <button
                    onClick={() => {
                      if (!partyForm.party_name.trim()) return
                      setCreateParties(prev => [...prev, { ...partyForm }])
                      setPartyForm({ ...emptyPartyForm })
                    }}
                    className="px-3 py-1.5 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] transition-colors text-sm"
                  >
                    Add
                  </button>
                </div>
              </div>
            </div>
            {createError && (
              <div className="mx-6 mb-0 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                {createError}
              </div>
            )}
            <div className="flex justify-end space-x-3 p-6 border-t border-[rgba(59,77,67,0.08)]">
              <button
                onClick={() => { setShowCreateModal(false); setCreateParties([]); setCreateError('') }}
                className="px-4 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg text-[#3D4A44] hover:bg-[#EEF1EC] transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateContract}
                disabled={!createForm.title.trim() || createLoading}
                className="px-4 py-2 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {createLoading ? 'Creating...' : 'Create Contract'}
              </button>
            </div>
          </div>
        </div>
      )}

      {selectedContract && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-3xl mx-4 max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between p-6 border-b border-[rgba(59,77,67,0.08)]">
              <div className="flex items-center space-x-3">
                <h3 className="text-lg font-semibold text-[#3D4A44]">
                  {contractDetail?.title || selectedContract.title}
                </h3>
                {contractDetail && (
                  <>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getStatusBadgeClass(contractDetail.status)}`}>
                      {contractDetail.status}
                    </span>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getTypeBadgeClass(contractDetail.contract_type)}`}>
                      {TYPE_LABELS[contractDetail.contract_type] || contractDetail.contract_type}
                    </span>
                  </>
                )}
              </div>
              <div className="flex items-center space-x-2">
                {!editMode && contractDetail && (
                  <>
                    <button
                      onClick={() => setEditMode(true)}
                      className="p-2 text-[#7A8580] hover:text-[#5B8A72] hover:bg-[#EEF1EC] rounded-lg transition-colors"
                    >
                      <PencilIcon className="w-5 h-5" />
                    </button>
                    <button
                      onClick={handleDeleteContract}
                      className="p-2 text-[#7A8580] hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                    >
                      <TrashIcon className="w-5 h-5" />
                    </button>
                  </>
                )}
                <button
                  onClick={() => { setSelectedContract(null); setContractDetail(null); setEditMode(false); setSplitForms({}); setEditingSplit(null) }}
                  className="p-2 text-[#7A8580] hover:text-[#3D4A44] hover:bg-[#EEF1EC] rounded-lg transition-colors"
                >
                  <XMarkIcon className="w-5 h-5" />
                </button>
              </div>
            </div>

            <div className="border-b border-[rgba(59,77,67,0.08)]">
              <div className="flex space-x-6 px-6">
                {['overview', 'parties', 'assets', 'documents'].map(tab => (
                  <button
                    key={tab}
                    onClick={() => setActiveDetailTab(tab)}
                    className={`pb-3 pt-3 px-1 border-b-2 font-medium text-sm transition-colors ${
                      activeDetailTab === tab
                        ? 'border-[#5B8A72] text-[#5B8A72]'
                        : 'border-transparent text-[#7A8580] hover:text-[#3D4A44]'
                    }`}
                  >
                    {tab === 'overview' ? 'Overview' :
                     tab === 'parties' ? `Parties (${contractDetail?.parties?.length || 0})` :
                     tab === 'assets' ? `Assets & Splits (${contractDetail?.assets?.length || 0})` :
                     `Documents (${contractDocuments.length})`}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-6">
              {detailLoading ? (
                <div className="flex items-center justify-center py-12">
                  <div className="text-[#7A8580]">Loading...</div>
                </div>
              ) : contractDetail && activeDetailTab === 'overview' && (
                editMode ? (
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="col-span-2">
                        <label className="block text-sm font-medium text-[#3D4A44] mb-1">Title</label>
                        <input
                          type="text"
                          value={editForm.title}
                          onChange={(e) => setEditForm(prev => ({ ...prev, title: e.target.value }))}
                          className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-[#3D4A44] mb-1">Type</label>
                        <select
                          value={editForm.contract_type}
                          onChange={(e) => setEditForm(prev => ({ ...prev, contract_type: e.target.value }))}
                          className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                        >
                          {Object.entries(TYPE_LABELS).map(([k, v]) => (
                            <option key={k} value={k}>{v}</option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-[#3D4A44] mb-1">Status</label>
                        <select
                          value={editForm.status}
                          onChange={(e) => setEditForm(prev => ({ ...prev, status: e.target.value }))}
                          className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                        >
                          {Object.keys(STATUS_COLORS).map(s => (
                            <option key={s} value={s}>{s}</option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-[#3D4A44] mb-1">Reference Number</label>
                        <input
                          type="text"
                          value={editForm.reference_number}
                          onChange={(e) => setEditForm(prev => ({ ...prev, reference_number: e.target.value }))}
                          className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-[#3D4A44] mb-1">Territory</label>
                        <input
                          type="text"
                          value={editForm.territory}
                          onChange={(e) => setEditForm(prev => ({ ...prev, territory: e.target.value }))}
                          className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-[#3D4A44] mb-1">Start Date</label>
                        <input
                          type="date"
                          value={editForm.start_date}
                          onChange={(e) => setEditForm(prev => ({ ...prev, start_date: e.target.value }))}
                          className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-[#3D4A44] mb-1">End Date</label>
                        <input
                          type="date"
                          value={editForm.end_date}
                          onChange={(e) => setEditForm(prev => ({ ...prev, end_date: e.target.value }))}
                          className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-[#3D4A44] mb-1">Advance Amount</label>
                        <input
                          type="number"
                          value={editForm.advance_amount}
                          onChange={(e) => setEditForm(prev => ({ ...prev, advance_amount: e.target.value }))}
                          className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                          min="0"
                          step="0.01"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-[#3D4A44] mb-1">Currency</label>
                        <select
                          value={editForm.advance_currency}
                          onChange={(e) => setEditForm(prev => ({ ...prev, advance_currency: e.target.value }))}
                          className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                        >
                          {CURRENCIES.map(c => <option key={c} value={c}>{c}</option>)}
                        </select>
                      </div>
                      <div className="col-span-2">
                        <label className="block text-sm font-medium text-[#3D4A44] mb-1">Notes</label>
                        <textarea
                          value={editForm.notes}
                          onChange={(e) => setEditForm(prev => ({ ...prev, notes: e.target.value }))}
                          className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                          rows={2}
                        />
                      </div>
                      <div className="col-span-2">
                        <label className="block text-sm font-medium text-[#3D4A44] mb-1">Terms Summary</label>
                        <textarea
                          value={editForm.terms_summary}
                          onChange={(e) => setEditForm(prev => ({ ...prev, terms_summary: e.target.value }))}
                          className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                          rows={2}
                        />
                      </div>
                    </div>
                    <div className="flex justify-end space-x-3 pt-2">
                      <button
                        onClick={() => setEditMode(false)}
                        className="px-4 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg text-[#3D4A44] hover:bg-[#EEF1EC] transition-colors"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleUpdateContract}
                        className="px-4 py-2 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] transition-colors"
                      >
                        Save Changes
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-xs font-medium text-[#7A8580] mb-1">Title</p>
                        <p className="text-sm text-[#3D4A44]">{contractDetail.title}</p>
                      </div>
                      <div>
                        <p className="text-xs font-medium text-[#7A8580] mb-1">Reference Number</p>
                        <p className="text-sm text-[#3D4A44]">{contractDetail.reference_number || '-'}</p>
                      </div>
                      <div>
                        <p className="text-xs font-medium text-[#7A8580] mb-1">Contract Type</p>
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getTypeBadgeClass(contractDetail.contract_type)}`}>
                          {TYPE_LABELS[contractDetail.contract_type] || contractDetail.contract_type}
                        </span>
                      </div>
                      <div>
                        <p className="text-xs font-medium text-[#7A8580] mb-1">Status</p>
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getStatusBadgeClass(contractDetail.status)}`}>
                          {contractDetail.status}
                        </span>
                      </div>
                      <div>
                        <p className="text-xs font-medium text-[#7A8580] mb-1">Start Date</p>
                        <p className="text-sm text-[#3D4A44]">{formatDate(contractDetail.start_date)}</p>
                      </div>
                      <div>
                        <p className="text-xs font-medium text-[#7A8580] mb-1">End Date</p>
                        <p className="text-sm text-[#3D4A44]">{formatDate(contractDetail.end_date)}</p>
                      </div>
                      <div>
                        <p className="text-xs font-medium text-[#7A8580] mb-1">Territory</p>
                        <p className="text-sm text-[#3D4A44]">{Array.isArray(contractDetail.territory) ? contractDetail.territory.join(', ') : (contractDetail.territory || '-')}</p>
                      </div>
                      <div>
                        <p className="text-xs font-medium text-[#7A8580] mb-1">Advance</p>
                        <p className="text-sm text-[#3D4A44]">
                          {contractDetail.advance_amount
                            ? `${formatCurrency(contractDetail.advance_amount, contractDetail.advance_currency)} (Recouped: ${formatCurrency(contractDetail.advance_recouped || 0, contractDetail.advance_currency)})`
                            : '-'}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs font-medium text-[#7A8580] mb-1">Created</p>
                        <p className="text-sm text-[#3D4A44]">{formatDate(contractDetail.created_at)}</p>
                      </div>
                    </div>
                    {contractDetail.notes && (
                      <div>
                        <p className="text-xs font-medium text-[#7A8580] mb-1">Notes</p>
                        <p className="text-sm text-[#3D4A44] whitespace-pre-wrap">{contractDetail.notes}</p>
                      </div>
                    )}
                    {contractDetail.terms_summary && (
                      <div>
                        <p className="text-xs font-medium text-[#7A8580] mb-1">Terms Summary</p>
                        <p className="text-sm text-[#3D4A44] whitespace-pre-wrap">{contractDetail.terms_summary}</p>
                      </div>
                    )}
                  </div>
                )
              )}

              {contractDetail && activeDetailTab === 'parties' && (
                <div className="space-y-4">
                  {contractDetail.parties?.length > 0 && (
                    <div className="space-y-2">
                      {contractDetail.parties.map(party => (
                        <div key={party.id} className="flex items-center justify-between p-3 bg-[#F5F7F4] rounded-lg">
                          <div className="flex items-center space-x-3">
                            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#5B8A72] to-[#7BA594] flex items-center justify-center text-white text-xs font-semibold">
                              {party.party_name?.charAt(0)?.toUpperCase() || '?'}
                            </div>
                            <div>
                              <p className="text-sm font-medium text-[#3D4A44]">{party.party_name}</p>
                              <div className="flex items-center space-x-2">
                                <span className="text-xs px-2 py-0.5 bg-[#EEF1EC] rounded-full text-[#7A8580]">{party.party_role}</span>
                                {party.contact_email && <span className="text-xs text-[#7A8580]">{party.contact_email}</span>}
                              </div>
                            </div>
                          </div>
                          <button
                            onClick={() => handleRemoveParty(party.id)}
                            className="p-1.5 text-[#7A8580] hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                          >
                            <XMarkIcon className="w-4 h-4" />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                  {contractDetail.parties?.length === 0 && (
                    <p className="text-sm text-[#7A8580] text-center py-4">No parties added yet</p>
                  )}
                  <div className="border-t border-[rgba(59,77,67,0.08)] pt-4">
                    <h4 className="text-sm font-semibold text-[#3D4A44] mb-3">Add Party</h4>
                    <div className="grid grid-cols-2 gap-2">
                      <input
                        type="text"
                        placeholder="Party name"
                        value={partyForm.party_name}
                        onChange={(e) => setPartyForm(prev => ({ ...prev, party_name: e.target.value }))}
                        className="border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                      />
                      <select
                        value={partyForm.party_role}
                        onChange={(e) => setPartyForm(prev => ({ ...prev, party_role: e.target.value }))}
                        className="border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                      >
                        {PARTY_ROLES.map(r => <option key={r} value={r}>{r}</option>)}
                      </select>
                      <select
                        value={partyForm.creator_id}
                        onChange={(e) => setPartyForm(prev => ({ ...prev, creator_id: e.target.value }))}
                        className="border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                      >
                        <option value="">Link to creator (optional)</option>
                        {creators.map(c => (
                          <option key={c.id} value={c.id}>{c.name || c.artist_name || `Creator ${c.id}`}</option>
                        ))}
                      </select>
                      <input
                        type="email"
                        placeholder="Contact email"
                        value={partyForm.contact_email}
                        onChange={(e) => setPartyForm(prev => ({ ...prev, contact_email: e.target.value }))}
                        className="border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                      />
                    </div>
                    <button
                      onClick={handleAddParty}
                      disabled={!partyForm.party_name.trim()}
                      className="mt-2 px-4 py-2 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] transition-colors text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Add Party
                    </button>
                  </div>
                </div>
              )}

              {contractDetail && activeDetailTab === 'assets' && (
                <div className="space-y-4">
                  <div className="relative">
                    <button
                      onClick={() => setShowAssetDropdown(!showAssetDropdown)}
                      className="flex items-center space-x-2 px-4 py-2 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] transition-colors text-sm"
                    >
                      <LinkIcon className="w-4 h-4" />
                      <span>Link Asset</span>
                    </button>
                    {showAssetDropdown && (
                      <div className="absolute top-full left-0 mt-2 w-96 bg-white rounded-xl shadow-lg border border-[rgba(59,77,67,0.12)] z-10 p-3">
                        <div className="flex space-x-2 mb-2">
                          <button
                            onClick={() => setAssetTypeFilter('SONG')}
                            className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${assetTypeFilter === 'SONG' ? 'bg-[#5B8A72] text-white' : 'bg-[#EEF1EC] text-[#3D4A44]'}`}
                          >
                            Songs
                          </button>
                          <button
                            onClick={() => setAssetTypeFilter('WORK')}
                            className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${assetTypeFilter === 'WORK' ? 'bg-[#5B8A72] text-white' : 'bg-[#EEF1EC] text-[#3D4A44]'}`}
                          >
                            Works
                          </button>
                        </div>
                        <input
                          type="text"
                          placeholder="Search assets..."
                          value={assetSearch}
                          onChange={(e) => setAssetSearch(e.target.value)}
                          className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-1.5 text-sm mb-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                        />
                        <div className="max-h-48 overflow-y-auto space-y-1">
                          {availableAssets.slice(0, 20).map(asset => (
                            <button
                              key={asset.id}
                              onClick={() => handleLinkAsset(assetTypeFilter, asset.id)}
                              className="w-full text-left px-3 py-2 rounded-lg hover:bg-[#F5F7F4] transition-colors"
                            >
                              <p className="text-sm font-medium text-[#3D4A44]">{asset.title}</p>
                              {assetTypeFilter === 'SONG' && asset.primary_artist && (
                                <p className="text-xs text-[#7A8580]">{asset.primary_artist}</p>
                              )}
                            </button>
                          ))}
                          {availableAssets.length === 0 && (
                            <p className="text-xs text-[#7A8580] text-center py-2">No available assets</p>
                          )}
                        </div>
                        <button
                          onClick={() => { setShowAssetDropdown(false); setAssetSearch('') }}
                          className="mt-2 w-full text-center text-xs text-[#7A8580] hover:text-[#3D4A44]"
                        >
                          Close
                        </button>
                      </div>
                    )}
                  </div>

                  {contractDetail.assets?.length === 0 && (
                    <p className="text-sm text-[#7A8580] text-center py-4">No assets linked yet</p>
                  )}

                  {contractDetail.assets?.map(asset => {
                    const splitTotals = getSplitTotalsByType(asset.splits)
                    const showSplitForm = splitForms[asset.id] !== undefined

                    return (
                      <div key={asset.id} className="bg-[#F5F7F4] rounded-xl p-4">
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center space-x-3">
                            <div className="w-8 h-8 rounded-lg bg-[#EEF1EC] flex items-center justify-center">
                              {asset.asset_type === 'SONG'
                                ? <MusicalNoteIcon className="w-4 h-4 text-[#7A8580]" />
                                : <DocumentTextIcon className="w-4 h-4 text-[#7A8580]" />}
                            </div>
                            <div>
                              <p className="text-sm font-medium text-[#3D4A44]">{asset.asset_title}</p>
                              <div className="flex items-center space-x-2">
                                <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${asset.asset_type === 'SONG' ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'}`}>
                                  {asset.asset_type}
                                </span>
                                {asset.asset_artist && <span className="text-xs text-[#7A8580]">{asset.asset_artist}</span>}
                              </div>
                            </div>
                          </div>
                          <button
                            onClick={() => handleUnlinkAsset(asset.id)}
                            className="p-1.5 text-[#7A8580] hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                          >
                            <TrashIcon className="w-4 h-4" />
                          </button>
                        </div>

                        {Object.entries(splitTotals).length > 0 && (
                          <div className="mb-3 space-y-1">
                            {Object.entries(splitTotals).map(([type, total]) => (
                              <div key={type} className="flex items-center space-x-2">
                                <span className="text-xs text-[#7A8580] w-24">{type}</span>
                                <div className="flex-1 h-2 bg-[#EEF1EC] rounded-full overflow-hidden">
                                  <div
                                    className={`h-full rounded-full transition-all ${total > 100 ? 'bg-red-400' : 'bg-[#5B8A72]'}`}
                                    style={{ width: `${Math.min(total, 100)}%` }}
                                  />
                                </div>
                                <span className={`text-xs font-medium ${total > 100 ? 'text-red-500' : 'text-[#3D4A44]'}`}>
                                  {total.toFixed(1)}%
                                </span>
                              </div>
                            ))}
                          </div>
                        )}

                        {asset.splits?.length > 0 && (
                          <div className="overflow-x-auto mb-3">
                            <table className="w-full text-sm">
                              <thead>
                                <tr className="border-b border-[rgba(59,77,67,0.12)]">
                                  <th className="text-left py-1.5 text-xs font-medium text-[#7A8580]">Rights Holder</th>
                                  <th className="text-left py-1.5 text-xs font-medium text-[#7A8580]">Type</th>
                                  <th className="text-right py-1.5 text-xs font-medium text-[#7A8580]">Share %</th>
                                  <th className="text-right py-1.5 text-xs font-medium text-[#7A8580] w-20"></th>
                                </tr>
                              </thead>
                              <tbody>
                                {asset.splits.map(split => (
                                  <tr key={split.id} className="border-b border-[rgba(59,77,67,0.06)]">
                                    {editingSplit === split.id ? (
                                      <>
                                        <td className="py-1.5 text-[#3D4A44]">{split.rights_holder_name}</td>
                                        <td className="py-1.5">
                                          <select
                                            value={editSplitForm.rights_type}
                                            onChange={(e) => setEditSplitForm(prev => ({ ...prev, rights_type: e.target.value }))}
                                            className="border border-[rgba(59,77,67,0.12)] rounded px-1 py-0.5 text-xs bg-white text-[#3D4A44]"
                                          >
                                            {RIGHTS_TYPES.map(r => <option key={r} value={r}>{r}</option>)}
                                          </select>
                                        </td>
                                        <td className="py-1.5 text-right">
                                          <input
                                            type="number"
                                            value={editSplitForm.share_percentage}
                                            onChange={(e) => setEditSplitForm(prev => ({ ...prev, share_percentage: e.target.value }))}
                                            className="w-16 border border-[rgba(59,77,67,0.12)] rounded px-1 py-0.5 text-xs text-right bg-white text-[#3D4A44]"
                                            min="0"
                                            max="100"
                                            step="0.1"
                                          />
                                        </td>
                                        <td className="py-1.5 text-right">
                                          <div className="flex items-center justify-end space-x-1">
                                            <button
                                              onClick={() => handleUpdateSplit(split.id)}
                                              className="text-xs text-[#5B8A72] hover:text-[#4A7A62] font-medium"
                                            >
                                              Save
                                            </button>
                                            <button
                                              onClick={() => { setEditingSplit(null); setEditSplitForm({}) }}
                                              className="text-xs text-[#7A8580] hover:text-[#3D4A44]"
                                            >
                                              Cancel
                                            </button>
                                          </div>
                                        </td>
                                      </>
                                    ) : (
                                      <>
                                        <td className="py-1.5 text-[#3D4A44]">{split.rights_holder_name}</td>
                                        <td className="py-1.5">
                                          <span className="text-xs px-1.5 py-0.5 bg-[#EEF1EC] rounded text-[#7A8580]">{split.rights_type}</span>
                                        </td>
                                        <td className="py-1.5 text-right text-[#3D4A44] font-medium">{split.share_percentage}%</td>
                                        <td className="py-1.5 text-right">
                                          <div className="flex items-center justify-end space-x-1">
                                            <button
                                              onClick={() => {
                                                setEditingSplit(split.id)
                                                setEditSplitForm({
                                                  rights_type: split.rights_type,
                                                  share_percentage: split.share_percentage,
                                                  notes: split.notes || ''
                                                })
                                              }}
                                              className="p-1 text-[#7A8580] hover:text-[#5B8A72] rounded transition-colors"
                                            >
                                              <PencilIcon className="w-3.5 h-3.5" />
                                            </button>
                                            <button
                                              onClick={() => handleDeleteSplit(split.id)}
                                              className="p-1 text-[#7A8580] hover:text-red-500 rounded transition-colors"
                                            >
                                              <TrashIcon className="w-3.5 h-3.5" />
                                            </button>
                                          </div>
                                        </td>
                                      </>
                                    )}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        )}

                        {showSplitForm ? (
                          <div className="bg-white rounded-lg p-3 space-y-2">
                            <div className="grid grid-cols-4 gap-2">
                              <select
                                value={splitForms[asset.id]?.rights_holder_id || ''}
                                onChange={(e) => setSplitForms(prev => ({ ...prev, [asset.id]: { ...prev[asset.id], rights_holder_id: e.target.value } }))}
                                className="border border-[rgba(59,77,67,0.12)] rounded-lg px-2 py-1.5 text-xs focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                              >
                                <option value="">Rights holder</option>
                                {creators.map(c => (
                                  <option key={c.id} value={c.id}>{c.name || c.artist_name || `Creator ${c.id}`}</option>
                                ))}
                              </select>
                              <select
                                value={splitForms[asset.id]?.rights_type || ''}
                                onChange={(e) => setSplitForms(prev => ({ ...prev, [asset.id]: { ...prev[asset.id], rights_type: e.target.value } }))}
                                className="border border-[rgba(59,77,67,0.12)] rounded-lg px-2 py-1.5 text-xs focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                              >
                                <option value="">Rights type</option>
                                {RIGHTS_TYPES.map(r => <option key={r} value={r}>{r}</option>)}
                              </select>
                              <input
                                type="number"
                                placeholder="Share %"
                                value={splitForms[asset.id]?.share_percentage || ''}
                                onChange={(e) => setSplitForms(prev => ({ ...prev, [asset.id]: { ...prev[asset.id], share_percentage: e.target.value } }))}
                                className="border border-[rgba(59,77,67,0.12)] rounded-lg px-2 py-1.5 text-xs focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                                min="0"
                                max="100"
                                step="0.1"
                              />
                              <div className="flex space-x-1">
                                <button
                                  onClick={() => handleAddSplit(asset.id)}
                                  className="flex-1 px-2 py-1.5 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] transition-colors text-xs"
                                >
                                  Add
                                </button>
                                <button
                                  onClick={() => setSplitForms(prev => ({ ...prev, [asset.id]: undefined }))}
                                  className="px-2 py-1.5 border border-[rgba(59,77,67,0.12)] rounded-lg text-[#7A8580] hover:bg-[#EEF1EC] transition-colors text-xs"
                                >
                                  Cancel
                                </button>
                              </div>
                            </div>
                          </div>
                        ) : (
                          <button
                            onClick={() => setSplitForms(prev => ({ ...prev, [asset.id]: { rights_holder_id: '', rights_type: '', share_percentage: '', notes: '' } }))}
                            className="text-xs text-[#5B8A72] hover:text-[#4A7A62] font-medium flex items-center space-x-1"
                          >
                            <PlusIcon className="w-3.5 h-3.5" />
                            <span>Add Split</span>
                          </button>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}

              {contractDetail && activeDetailTab === 'documents' && (
                <div className="space-y-4">
                  <div className="bg-[#F5F7F4] rounded-xl p-4">
                    <h4 className="text-sm font-medium text-[#3D4A44] mb-3 flex items-center space-x-2">
                      <CloudArrowUpIcon className="w-4 h-4" />
                      <span>Upload Document</span>
                    </h4>
                    <div className="space-y-3">
                      <div>
                        <label className="block text-xs text-[#7A8580] mb-1">Description (optional)</label>
                        <input
                          type="text"
                          placeholder="e.g. Signed master agreement"
                          value={docDescription}
                          onChange={(e) => setDocDescription(e.target.value)}
                          className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                        />
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="block text-xs text-[#7A8580] mb-1">Link to (optional)</label>
                          <select
                            value={docLinkType}
                            onChange={(e) => { setDocLinkType(e.target.value); setDocLinkId('') }}
                            className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                          >
                            <option value="">None</option>
                            <option value="song">Song</option>
                            <option value="work">Work</option>
                            <option value="release">Release</option>
                          </select>
                        </div>
                        {docLinkType && (
                          <div>
                            <label className="block text-xs text-[#7A8580] mb-1">
                              {docLinkType === 'song' ? 'Select Song' : docLinkType === 'work' ? 'Select Work' : 'Select Release'}
                            </label>
                            <select
                              value={docLinkId}
                              onChange={(e) => setDocLinkId(e.target.value)}
                              className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                            >
                              <option value="">Choose...</option>
                              {docLinkType === 'song' && songs.map(s => (
                                <option key={s.id} value={s.id}>{s.title}</option>
                              ))}
                              {docLinkType === 'work' && works.map(w => (
                                <option key={w.id} value={w.id}>{w.title}</option>
                              ))}
                              {docLinkType === 'release' && releases.map(r => (
                                <option key={r.id} value={r.id}>{r.title || r.name}</option>
                              ))}
                            </select>
                          </div>
                        )}
                      </div>
                      <div>
                        <label
                          className={`flex items-center justify-center space-x-2 px-4 py-3 border-2 border-dashed rounded-xl cursor-pointer transition-colors ${
                            docUploading
                              ? 'border-[rgba(59,77,67,0.12)] bg-gray-50 text-[#7A8580]'
                              : 'border-[rgba(91,138,114,0.3)] hover:border-[#5B8A72] hover:bg-[#F0F5F2] text-[#5B8A72]'
                          }`}
                        >
                          <CloudArrowUpIcon className="w-5 h-5" />
                          <span className="text-sm font-medium">
                            {docUploading ? 'Uploading...' : 'Choose file to upload'}
                          </span>
                          <input
                            type="file"
                            className="hidden"
                            disabled={docUploading}
                            accept=".pdf,.doc,.docx,.png,.jpg,.jpeg,.xls,.xlsx"
                            onChange={(e) => {
                              if (e.target.files[0]) handleUploadDocument(e.target.files[0])
                              e.target.value = ''
                            }}
                          />
                        </label>
                        <p className="text-xs text-[#7A8580] mt-1">PDF, DOC, DOCX, images, or Excel files up to 50MB</p>
                      </div>
                    </div>
                  </div>

                  {contractDocuments.length === 0 ? (
                    <p className="text-sm text-[#7A8580] text-center py-4">No documents uploaded yet</p>
                  ) : (
                    <div className="space-y-2">
                      {contractDocuments.map(doc => (
                        <div key={doc.id} className="flex items-center justify-between bg-[#F5F7F4] rounded-xl p-3">
                          <div className="flex items-center space-x-3 min-w-0 flex-1">
                            <div className="w-8 h-8 rounded-lg bg-[#EEF1EC] flex items-center justify-center flex-shrink-0">
                              <PaperClipIcon className="w-4 h-4 text-[#7A8580]" />
                            </div>
                            <div className="min-w-0 flex-1">
                              <p className="text-sm font-medium text-[#3D4A44] truncate">{doc.file_name}</p>
                              <div className="flex items-center space-x-2 text-xs text-[#7A8580]">
                                {doc.description && <span>{doc.description}</span>}
                                {doc.file_size_bytes && (
                                  <span>{(doc.file_size_bytes / 1024).toFixed(0)} KB</span>
                                )}
                                {doc.linked_asset_name && (
                                  <span className="px-1.5 py-0.5 bg-[#EEF1EC] rounded text-xs">
                                    {doc.linked_asset_type}: {doc.linked_asset_name}
                                  </span>
                                )}
                                {doc.created_at && (
                                  <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                                )}
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center space-x-1 ml-2">
                            <button
                              onClick={() => handleDownloadDocument(doc)}
                              className="p-1.5 text-[#5B8A72] hover:bg-[#EEF1EC] rounded-lg transition-colors"
                              title="Download"
                            >
                              <ArrowDownTrayIcon className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => handleDeleteDocument(doc.id)}
                              className="p-1.5 text-[#7A8580] hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                              title="Delete"
                            >
                              <TrashIcon className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
