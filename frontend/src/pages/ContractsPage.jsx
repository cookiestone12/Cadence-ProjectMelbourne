import React, { useState, useEffect, useRef, Component } from 'react'
import axios from 'axios'
import {
  MagnifyingGlassIcon, PlusIcon, XMarkIcon, TrashIcon,
  PencilIcon, UserGroupIcon, LinkIcon, DocumentTextIcon,
  MusicalNoteIcon, CalendarIcon, CurrencyDollarIcon,
  ChevronDownIcon, ArrowDownTrayIcon, PaperClipIcon, CloudArrowUpIcon
} from '@heroicons/react/24/outline'
import ContractAdvancesSection from '../components/ContractAdvancesSection'

function SearchableSelect({ options, value, onChange, placeholder, className }) {
  const [search, setSearch] = useState('')
  const [isOpen, setIsOpen] = useState(false)
  const containerRef = useRef(null)

  useEffect(() => {
    function handleClickOutside(e) {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const selectedOption = options.find(o => String(o.id) === String(value))

  const filtered = options
    .filter(o => {
      if (!search) return true
      const term = search.toLowerCase()
      return o.label.toLowerCase().includes(term) || (o.sublabel && o.sublabel.toLowerCase().includes(term))
    })
    .sort((a, b) => a.label.localeCompare(b.label))

  return (
    <div ref={containerRef} className="relative">
      <div className="relative">
        <input
          type="text"
          placeholder={selectedOption ? selectedOption.label : (placeholder || 'Search...')}
          value={selectedOption && !isOpen ? '' : search}
          onChange={(e) => { setSearch(e.target.value); setIsOpen(true) }}
          onFocus={() => setIsOpen(true)}
          className={className || 'w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]'}
        />
        {selectedOption && (
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); onChange(''); setSearch(''); setIsOpen(false) }}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-[#7A8580] hover:text-[#3D4A44]"
          >
            <XMarkIcon className="w-4 h-4" />
          </button>
        )}
      </div>
      {isOpen && (
        <div className="absolute z-50 w-full mt-1 bg-white border border-[rgba(59,77,67,0.12)] rounded-lg shadow-lg max-h-48 overflow-y-auto">
          {filtered.length === 0 ? (
            <div className="px-3 py-2 text-sm text-[#7A8580]">No results found</div>
          ) : (
            filtered.map(o => (
              <button
                key={o.id}
                type="button"
                onClick={() => { onChange(String(o.id)); setSearch(''); setIsOpen(false) }}
                className={`w-full text-left px-3 py-2 text-sm hover:bg-[#EEF1EC] transition-colors ${String(o.id) === String(value) ? 'bg-[#F0F5F2] text-[#5B8A72] font-medium' : 'text-[#3D4A44]'}`}
              >
                <div>{o.label}</div>
                {o.sublabel && <div className="text-xs text-[#7A8580]">{o.sublabel}</div>}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  )
}

class ContractsErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }
  componentDidCatch(error, info) {
    console.error('ContractsPage error:', error, info)
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center h-full p-8">
          <div className="bg-red-50 border border-red-200 rounded-xl p-6 max-w-md text-center">
            <h2 className="text-lg font-semibold text-red-700 mb-2">Something went wrong</h2>
            <p className="text-sm text-red-600 mb-4">{this.state.error?.message || 'An unexpected error occurred'}</p>
            <button
              onClick={() => { this.setState({ hasError: false, error: null }); window.location.reload() }}
              className="px-4 py-2 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62]"
            >
              Reload Page
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

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
  title: '', contract_type: 'MASTER', payment_direction: 'INCOMING', status: 'DRAFT', reference_number: '',
  start_date: '', end_date: '', territory: '', advance_amount: '', advance_currency: 'USD',
  notes: '', terms_summary: '', creator_id: '',
}

const emptyPartyForm = { party_name: '', party_role: 'ARTIST', creator_id: '', contact_email: '' }

function ContractsPageInner() {
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
  const [releases, setReleases] = useState([])
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [uploadFile, setUploadFile] = useState(null)
  const [uploadCreatorId, setUploadCreatorId] = useState('')
  const [uploadSongId, setUploadSongId] = useState('')
  const [uploadDescription, setUploadDescription] = useState('')
  const [uploadLoading, setUploadLoading] = useState(false)
  const [uploadError, setUploadError] = useState('')
  const [uploadContractId, setUploadContractId] = useState('')
  const [showSplitSheetMenu, setShowSplitSheetMenu] = useState(false)
  const splitSheetRef = useRef(null)

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
        payment_direction: res.data.payment_direction || 'INCOMING',
        status: res.data.status || 'DRAFT',
        reference_number: res.data.reference_number || '',
        start_date: res.data.start_date || '',
        end_date: res.data.end_date || '',
        territory: Array.isArray(res.data.territory) ? res.data.territory.join(', ') : (res.data.territory || ''),
        advance_amount: res.data.advance_amount || '',
        advance_currency: res.data.advance_currency || 'USD',
        notes: res.data.notes || '',
        terms_summary: res.data.terms_summary || '',
        creator_id: res.data.creator_id || '',
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
      if (payload.creator_id) payload.creator_id = parseInt(payload.creator_id)
      else delete payload.creator_id
      if (createParties.length > 0) {
        payload.parties = createParties.map(p => {
          const cleaned = { ...p }
          if (cleaned.creator_id) cleaned.creator_id = parseInt(cleaned.creator_id)
          else delete cleaned.creator_id
          if (!cleaned.contact_email) delete cleaned.contact_email
          return cleaned
        })
      }
      await axios.post(`/api/rights/contracts/org/${organizationId}`, payload)
      setShowCreateModal(false)
      setCreateForm({ ...emptyCreateForm })
      setCreateParties([])
      setCreateError('')
      await loadData()
    } catch (error) {
      console.error('Failed to create contract:', error)
      const detail = error.response?.data?.detail
      setCreateError(typeof detail === 'string' ? detail : JSON.stringify(detail) || 'Failed to create contract. Please try again.')
    } finally {
      setCreateLoading(false)
    }
  }

  async function handleUploadContractDoc() {
    if (!uploadFile) {
      setUploadError('Please select a file to upload.')
      return
    }
    if (!uploadContractId) {
      setUploadError('Please select which contract to attach this document to.')
      return
    }
    setUploadError('')
    setUploadLoading(true)
    try {
      const formData = new FormData()
      formData.append('file', uploadFile)
      formData.append('description', uploadDescription || uploadFile.name)
      if (uploadSongId) formData.append('song_id', uploadSongId)
      await axios.post(`/api/rights/contracts/${uploadContractId}/documents`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      setShowUploadModal(false)
      setUploadFile(null)
      setUploadCreatorId('')
      setUploadSongId('')
      setUploadDescription('')
      setUploadContractId('')
      setUploadError('')
      if (contractDetail && contractDetail.id === parseInt(uploadContractId)) {
        await refreshDetail()
      }
    } catch (error) {
      console.error('Failed to upload document:', error)
      const detail = error.response?.data?.detail
      setUploadError(typeof detail === 'string' ? detail : 'Failed to upload document. Please try again.')
    } finally {
      setUploadLoading(false)
    }
  }

  async function handleDownloadSplitSheet(splitType) {
    if (!contractDetail) return
    setShowSplitSheetMenu(false)
    try {
      const response = await axios.get(`/api/rights/contracts/${contractDetail.id}/split-sheet`, {
        params: { split_type: splitType },
        responseType: 'blob'
      })
      const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `Split_Sheet_${contractDetail.title.replace(/[^a-zA-Z0-9]/g, '_')}.pdf`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Failed to download split sheet:', error)
      alert('Failed to generate split sheet. Make sure the contract has linked assets with splits.')
    }
  }

  useEffect(() => {
    function handleClickOutside(e) {
      if (splitSheetRef.current && !splitSheetRef.current.contains(e.target)) {
        setShowSplitSheetMenu(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const filteredSongsForUpload = songs.filter(s => {
    if (!uploadCreatorId) return true
    return s.creator_id === parseInt(uploadCreatorId)
  })

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
      if (payload.creator_id) payload.creator_id = parseInt(payload.creator_id)
      else payload.creator_id = null
      if (!payload.start_date) payload.start_date = null
      if (!payload.end_date) payload.end_date = null
      if (!payload.reference_number) payload.reference_number = null
      if (!payload.notes) payload.notes = null
      if (!payload.terms_summary) payload.terms_summary = null
      if (payload.advance_currency === '') payload.advance_currency = null
      await axios.put(`/api/rights/contracts/${contractDetail.id}`, payload)
      setEditMode(false)
      await loadData()
      await refreshDetail()
    } catch (error) {
      console.error('Failed to update contract:', error)
      alert('Failed to save changes. Please check the form fields and try again.')
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
    if (!form || (!form.rights_holder_id && !form.rights_holder_name) || !form.rights_type || !form.share_percentage) return
    try {
      const payload = {
        rights_type: form.rights_type,
        share_percentage: parseFloat(form.share_percentage),
        notes: form.notes || ''
      }
      if (form.rights_holder_id) {
        payload.rights_holder_id = parseInt(form.rights_holder_id)
      } else {
        payload.rights_holder_name = form.rights_holder_name
      }
      await axios.post(`/api/rights/contracts/${contractDetail.id}/assets/${contractAssetId}/splits`, payload)
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
        <div className="flex items-center space-x-3">
          <button
            className="flex items-center space-x-2 px-4 py-2 border border-[#5B8A72] text-[#5B8A72] rounded-lg hover:bg-[rgba(91,138,114,0.08)] transition-colors"
            onClick={() => { setShowUploadModal(true); setUploadError(''); setUploadFile(null); setUploadCreatorId(''); setUploadSongId(''); setUploadDescription(''); setUploadContractId('') }}
          >
            <CloudArrowUpIcon className="w-5 h-5" />
            <span>Upload Contract</span>
          </button>
          <button
            className="flex items-center space-x-2 px-4 py-2 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] transition-colors"
            onClick={() => { setShowCreateModal(true); setCreateError(''); setCreateLoading(false) }}
          >
            <PlusIcon className="w-5 h-5" />
            <span>New Contract</span>
          </button>
        </div>
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
            {contract.creator_name && (
              <p className="text-xs text-[#5B8A72] font-medium mb-2 flex items-center space-x-1">
                <UserGroupIcon className="w-3.5 h-3.5" />
                <span>{contract.creator_name}</span>
              </p>
            )}
            <div className="flex items-center space-x-2 mb-3 flex-wrap gap-y-1">
              <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getTypeBadgeClass(contract.contract_type)}`}>
                {TYPE_LABELS[contract.contract_type] || contract.contract_type}
              </span>
              <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${contract.payment_direction === 'OUTGOING' ? 'bg-amber-100 text-amber-700' : 'bg-green-100 text-green-700'}`}>
                {contract.payment_direction === 'OUTGOING' ? '↑ Outgoing' : '↓ Incoming'}
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
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Payment Direction</label>
                  <select
                    value={createForm.payment_direction}
                    onChange={(e) => setCreateForm(prev => ({ ...prev, payment_direction: e.target.value }))}
                    className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  >
                    <option value="INCOMING">Receiving (Income)</option>
                    <option value="OUTGOING">Paying Out (Expense)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Client</label>
                  <select
                    value={createForm.creator_id}
                    onChange={(e) => setCreateForm(prev => ({ ...prev, creator_id: e.target.value }))}
                    className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  >
                    <option value="">None</option>
                    {creators.map(c => (
                      <option key={c.id} value={c.id}>{c.display_name || c.legal_name || c.name}</option>
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

      {showUploadModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg mx-4 max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between p-6 border-b border-[rgba(59,77,67,0.08)]">
              <h3 className="text-lg font-semibold text-[#3D4A44]">Upload Contract Document</h3>
              <button onClick={() => setShowUploadModal(false)} className="text-[#7A8580] hover:text-[#3D4A44]">
                <XMarkIcon className="w-5 h-5" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              <div className="border-2 border-dashed border-[rgba(59,77,67,0.2)] rounded-lg p-6 text-center hover:border-[#5B8A72] transition-colors">
                {uploadFile ? (
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <PaperClipIcon className="w-5 h-5 text-[#5B8A72]" />
                      <span className="text-sm text-[#3D4A44] truncate max-w-[250px]">{uploadFile.name}</span>
                      <span className="text-xs text-[#7A8580]">({(uploadFile.size / 1024 / 1024).toFixed(2)} MB)</span>
                    </div>
                    <button onClick={() => setUploadFile(null)} className="text-[#7A8580] hover:text-red-500">
                      <XMarkIcon className="w-4 h-4" />
                    </button>
                  </div>
                ) : (
                  <label className="cursor-pointer">
                    <CloudArrowUpIcon className="w-10 h-10 text-[#7A8580] mx-auto mb-2" />
                    <p className="text-sm text-[#5B8A72] font-medium">Click to select a contract file</p>
                    <p className="text-xs text-[#7A8580] mt-1">PDF, DOC, DOCX, Excel, or images (max 50MB)</p>
                    <input
                      type="file"
                      className="hidden"
                      accept=".pdf,.doc,.docx,.xls,.xlsx,.jpg,.jpeg,.png"
                      onChange={(e) => { if (e.target.files[0]) setUploadFile(e.target.files[0]) }}
                    />
                  </label>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Attach to Contract *</label>
                <select
                  value={uploadContractId}
                  onChange={(e) => setUploadContractId(e.target.value)}
                  className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                >
                  <option value="">Select a contract...</option>
                  {contracts.map(c => (
                    <option key={c.id} value={c.id}>{c.title}{c.reference_number ? ` (${c.reference_number})` : ''}</option>
                  ))}
                </select>
                {contracts.length === 0 && (
                  <p className="text-xs text-[#7A8580] mt-1">No contracts yet. Create a contract first, then upload documents.</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Client (optional)</label>
                <select
                  value={uploadCreatorId}
                  onChange={(e) => { setUploadCreatorId(e.target.value); setUploadSongId('') }}
                  className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                >
                  <option value="">All clients</option>
                  {creators.map(c => (
                    <option key={c.id} value={c.id}>{c.display_name || c.legal_name || c.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Song (optional)</label>
                <SearchableSelect
                  options={filteredSongsForUpload.map(s => ({ id: s.id, label: s.title, sublabel: s.artist || s.primary_artist }))}
                  value={uploadSongId}
                  onChange={(val) => setUploadSongId(val)}
                  placeholder="Search songs..."
                  className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Description (optional)</label>
                <input
                  type="text"
                  value={uploadDescription}
                  onChange={(e) => setUploadDescription(e.target.value)}
                  className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  placeholder="e.g., Signed master agreement"
                />
              </div>
            </div>
            {uploadError && (
              <div className="mx-6 mb-0 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                {uploadError}
              </div>
            )}
            <div className="flex justify-end space-x-3 p-6 border-t border-[rgba(59,77,67,0.08)]">
              <button
                onClick={() => setShowUploadModal(false)}
                className="px-4 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg text-[#3D4A44] hover:bg-[#EEF1EC] transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleUploadContractDoc}
                disabled={!uploadFile || !uploadContractId || uploadLoading}
                className="flex items-center space-x-2 px-4 py-2 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <CloudArrowUpIcon className="w-5 h-5" />
                <span>{uploadLoading ? 'Uploading...' : 'Upload Document'}</span>
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
                    <div className="relative" ref={splitSheetRef}>
                      <button
                        onClick={() => setShowSplitSheetMenu(!showSplitSheetMenu)}
                        className="p-2 text-[#7A8580] hover:text-[#5B8A72] hover:bg-[#EEF1EC] rounded-lg transition-colors"
                        title="Download Split Sheet"
                      >
                        <ArrowDownTrayIcon className="w-5 h-5" />
                      </button>
                      {showSplitSheetMenu && (
                        <div className="absolute right-0 top-full mt-1 w-52 bg-white rounded-xl shadow-lg border border-[rgba(59,77,67,0.12)] z-20 py-1">
                          <p className="px-3 py-1.5 text-xs font-medium text-[#7A8580]">Download Split Sheet</p>
                          <button
                            onClick={() => handleDownloadSplitSheet('both')}
                            className="w-full text-left px-3 py-2 text-sm text-[#3D4A44] hover:bg-[#F5F7F4] transition-colors"
                          >
                            Publishing & Master
                          </button>
                          <button
                            onClick={() => handleDownloadSplitSheet('publishing')}
                            className="w-full text-left px-3 py-2 text-sm text-[#3D4A44] hover:bg-[#F5F7F4] transition-colors"
                          >
                            Publishing Only
                          </button>
                          <button
                            onClick={() => handleDownloadSplitSheet('master')}
                            className="w-full text-left px-3 py-2 text-sm text-[#3D4A44] hover:bg-[#F5F7F4] transition-colors"
                          >
                            Master Only
                          </button>
                        </div>
                      )}
                    </div>
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
              <div className="flex space-x-6 px-6 overflow-x-auto no-scrollbar">
                {['overview', 'parties', 'assets', 'documents', 'advances'].map(tab => (
                  <button
                    key={tab}
                    onClick={() => setActiveDetailTab(tab)}
                    className={`pb-3 pt-3 px-1 border-b-2 font-medium text-sm transition-colors whitespace-nowrap ${
                      activeDetailTab === tab
                        ? 'border-[#5B8A72] text-[#5B8A72]'
                        : 'border-transparent text-[#7A8580] hover:text-[#3D4A44]'
                    }`}
                  >
                    {tab === 'overview' ? 'Overview' :
                     tab === 'parties' ? `Parties (${contractDetail?.parties?.length || 0})` :
                     tab === 'assets' ? `Assets & Splits (${contractDetail?.assets?.length || 0})` :
                     tab === 'advances' ? 'Advances' :
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
                        <label className="block text-sm font-medium text-[#3D4A44] mb-1">Payment Direction</label>
                        <select
                          value={editForm.payment_direction}
                          onChange={(e) => setEditForm(prev => ({ ...prev, payment_direction: e.target.value }))}
                          className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                        >
                          <option value="INCOMING">Receiving (Income)</option>
                          <option value="OUTGOING">Paying Out (Expense)</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-[#3D4A44] mb-1">Client</label>
                        <select
                          value={editForm.creator_id}
                          onChange={(e) => setEditForm(prev => ({ ...prev, creator_id: e.target.value }))}
                          className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                        >
                          <option value="">None</option>
                          {creators.map(c => (
                            <option key={c.id} value={c.id}>{c.display_name || c.legal_name || c.name}</option>
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
                        <p className="text-xs font-medium text-[#7A8580] mb-1">Payment Direction</p>
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${contractDetail.payment_direction === 'OUTGOING' ? 'bg-amber-100 text-amber-700' : 'bg-green-100 text-green-700'}`}>
                          {contractDetail.payment_direction === 'OUTGOING' ? '↑ Outgoing (Expense)' : '↓ Incoming (Income)'}
                        </span>
                      </div>
                      <div>
                        <p className="text-xs font-medium text-[#7A8580] mb-1">Client</p>
                        <p className="text-sm text-[#3D4A44]">{contractDetail.creator_name || '-'}</p>
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
                                <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${asset.asset_type === 'SONG' ? 'bg-purple-100 text-purple-700' : asset.asset_type === 'RELEASE' ? 'bg-amber-100 text-amber-700' : 'bg-blue-100 text-blue-700'}`}>
                                  {asset.asset_type}
                                </span>
                                {asset.asset_artist && <span className="text-xs text-[#7A8580]">{asset.asset_artist}</span>}
                                {asset.audio_linked ? (
                                  <span className="inline-flex items-center space-x-1 text-xs px-1.5 py-0.5 rounded bg-green-100 text-green-700 font-medium" title={asset.audio_linked.path_display || asset.audio_linked.name}>
                                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M9 9l10.5-3m0 6.553v3.75a2.25 2.25 0 01-1.632 2.163l-1.32.377a1.803 1.803 0 11-.99-3.467l2.31-.66a2.25 2.25 0 001.632-2.163zm0 0V4.462c0-.746-.57-1.369-1.31-1.447L7.94 2.12A2.25 2.25 0 005.69 4.335v13.29" /></svg>
                                    <span>Audio Linked</span>
                                  </span>
                                ) : (asset.asset_type === 'SONG' || asset.asset_type === 'RELEASE') ? (
                                  <span className="text-xs px-1.5 py-0.5 rounded bg-[#EEF1EC] text-[#7A8580]">No Audio</span>
                                ) : null}
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
                              <div className="flex flex-col space-y-1">
                                <select
                                  value={splitForms[asset.id]?.rights_holder_id || ''}
                                  onChange={(e) => setSplitForms(prev => ({ ...prev, [asset.id]: { ...prev[asset.id], rights_holder_id: e.target.value, rights_holder_name: e.target.value ? '' : prev[asset.id]?.rights_holder_name || '' } }))}
                                  className="border border-[rgba(59,77,67,0.12)] rounded-lg px-2 py-1.5 text-xs focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                                >
                                  <option value="">Select from roster</option>
                                  {creators.map(c => (
                                    <option key={c.id} value={c.id}>{c.name || c.artist_name || `Creator ${c.id}`}</option>
                                  ))}
                                </select>
                                {!splitForms[asset.id]?.rights_holder_id && (
                                  <input
                                    type="text"
                                    placeholder="Or type external name"
                                    value={splitForms[asset.id]?.rights_holder_name || ''}
                                    onChange={(e) => setSplitForms(prev => ({ ...prev, [asset.id]: { ...prev[asset.id], rights_holder_name: e.target.value } }))}
                                    className="border border-[rgba(59,77,67,0.12)] rounded-lg px-2 py-1.5 text-xs focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                                  />
                                )}
                              </div>
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
                          <div className="flex items-center space-x-2">
                            <button
                              onClick={() => setSplitForms(prev => ({ ...prev, [asset.id]: { rights_holder_id: '', rights_holder_name: '', rights_type: 'PUBLISHING', share_percentage: '', notes: '' } }))}
                              className="text-xs text-[#5B8A72] hover:text-[#4A7A62] font-medium flex items-center space-x-1 border border-[#5B8A72] rounded-lg px-2 py-1 hover:bg-[rgba(91,138,114,0.08)] transition-colors"
                            >
                              <PlusIcon className="w-3.5 h-3.5" />
                              <span>Add Publishing Split</span>
                            </button>
                            <button
                              onClick={() => setSplitForms(prev => ({ ...prev, [asset.id]: { rights_holder_id: '', rights_holder_name: '', rights_type: 'MASTER', share_percentage: '', notes: '' } }))}
                              className="text-xs text-[#5B8A72] hover:text-[#4A7A62] font-medium flex items-center space-x-1 border border-[#5B8A72] rounded-lg px-2 py-1 hover:bg-[rgba(91,138,114,0.08)] transition-colors"
                            >
                              <PlusIcon className="w-3.5 h-3.5" />
                              <span>Add Master Split</span>
                            </button>
                            <button
                              onClick={() => setSplitForms(prev => ({ ...prev, [asset.id]: { rights_holder_id: '', rights_holder_name: '', rights_type: '', share_percentage: '', notes: '' } }))}
                              className="text-xs text-[#5B8A72] hover:text-[#4A7A62] font-medium flex items-center space-x-1"
                            >
                              <PlusIcon className="w-3.5 h-3.5" />
                              <span>Add Split</span>
                            </button>
                          </div>
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
                            <SearchableSelect
                              options={
                                docLinkType === 'song'
                                  ? songs.map(s => ({ id: s.id, label: s.title, sublabel: s.artist || s.primary_artist }))
                                  : docLinkType === 'work'
                                    ? works.map(w => ({ id: w.id, label: w.title }))
                                    : releases.map(r => ({ id: r.id, label: r.title || r.name }))
                              }
                              value={docLinkId}
                              onChange={(val) => setDocLinkId(val)}
                              placeholder="Search..."
                              className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                            />
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

              {contractDetail && activeDetailTab === 'advances' && (
                <ContractAdvancesSection orgId={organizationId} contractId={contractDetail.id} />
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default function ContractsPage() {
  return (
    <ContractsErrorBoundary>
      <ContractsPageInner />
    </ContractsErrorBoundary>
  )
}
