import React, { useState, useEffect, useCallback, useRef } from 'react'
import axios from 'axios'
import {
  PlusIcon,
  XMarkIcon,
  FunnelIcon,
  TrashIcon,
  PencilSquareIcon,
  CurrencyDollarIcon,
  ArrowPathIcon,
  ChevronRightIcon,
  FilmIcon,
  TvIcon,
  MusicalNoteIcon,
  MegaphoneIcon,
  PlayCircleIcon,
  CheckCircleIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  ArrowTrendingUpIcon,
  BanknotesIcon,
  CalendarIcon,
  EnvelopeIcon,
  UserIcon,
  DocumentTextIcon,
  GlobeAltIcon
} from '@heroicons/react/24/outline'

const STATUS_BADGE_STYLES = {
  PITCHED: { bg: 'rgba(91, 138, 114, 0.12)', text: '#5B8A72' },
  IN_REVIEW: { bg: 'rgba(90, 138, 154, 0.12)', text: '#5A8A9A' },
  IN_NEGOTIATION: { bg: 'rgba(196, 149, 107, 0.15)', text: '#C4956B' },
  SECURED: { bg: 'rgba(91, 154, 110, 0.15)', text: '#5B9A6E' },
  DELIVERED: { bg: 'rgba(91, 138, 114, 0.15)', text: '#5B8A72' },
  AIRED: { bg: 'rgba(90, 138, 154, 0.15)', text: '#5A8A9A' },
  PAID: { bg: 'rgba(91, 154, 110, 0.2)', text: '#3D7A4E' },
  DECLINED: { bg: 'rgba(196, 112, 104, 0.15)', text: '#C47068' },
  CANCELLED: { bg: 'rgba(196, 112, 104, 0.12)', text: '#C47068' },
}

const PLACEMENT_TYPE_ICONS = {
  SYNC: MusicalNoteIcon,
  ADVERTISING: MegaphoneIcon,
  FILM: FilmIcon,
  TV: TvIcon,
  GAMING: PlayCircleIcon,
  TRAILER: FilmIcon,
  OTHER: DocumentTextIcon,
}

const PLACEMENT_TYPES = ['SYNC', 'ADVERTISING', 'FILM', 'TV', 'GAMING', 'TRAILER', 'OTHER']
const PLACEMENT_STATUSES = ['PITCHED', 'IN_REVIEW', 'IN_NEGOTIATION', 'SECURED', 'DELIVERED', 'AIRED', 'PAID', 'DECLINED', 'CANCELLED']
const MEDIA_TYPES = ['FILM', 'TV_SHOW', 'COMMERCIAL', 'VIDEO_GAME', 'TRAILER', 'PODCAST', 'SOCIAL_MEDIA', 'OTHER']

const STATUS_TRANSITIONS = {
  PITCHED: ['IN_REVIEW', 'IN_NEGOTIATION', 'DECLINED', 'CANCELLED'],
  IN_REVIEW: ['IN_NEGOTIATION', 'PITCHED', 'DECLINED', 'CANCELLED'],
  IN_NEGOTIATION: ['SECURED', 'IN_REVIEW', 'DECLINED', 'CANCELLED'],
  SECURED: ['DELIVERED', 'CANCELLED'],
  DELIVERED: ['AIRED', 'PAID'],
  AIRED: ['PAID'],
  PAID: [],
  DECLINED: ['PITCHED'],
  CANCELLED: ['PITCHED'],
}

const formatStatus = (s) => {
  if (!s) return ''
  return s.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

const formatCurrency = (amount, currency = 'USD') => {
  if (amount == null) return '—'
  return new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(amount)
}

const formatDate = (dateStr) => {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

const emptyCreateForm = {
  title: '',
  description: '',
  placement_type: 'SYNC',
  song_id: '',
  work_id: '',
  contract_id: '',
  client_name: '',
  project_name: '',
  media_type: '',
  license_fee: '',
  license_currency: 'USD',
  license_type: '',
  territory: '',
  usage_notes: '',
  pitched_date: '',
  contact_name: '',
  contact_email: '',
  notes: '',
  assigned_to_user_id: '',
}

export default function PlacementsPage() {
  const [orgId, setOrgId] = useState(null)
  const [placements, setPlacements] = useState([])
  const [summary, setSummary] = useState({ status_counts: {}, total_pipeline_value: 0, total_paid: 0, total_placements: 0 })
  const [loading, setLoading] = useState(true)
  const [filterStatus, setFilterStatus] = useState('')
  const [filterType, setFilterType] = useState('')
  const [showFilters, setShowFilters] = useState(false)
  const [selectedPlacement, setSelectedPlacement] = useState(null)
  const [detailData, setDetailData] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [editMode, setEditMode] = useState(false)
  const [editForm, setEditForm] = useState({})
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [createForm, setCreateForm] = useState({ ...emptyCreateForm })
  const [saving, setSaving] = useState(false)
  const [transitioning, setTransitioning] = useState(false)
  const [error, setError] = useState('')
  const [createSongTitle, setCreateSongTitle] = useState('')
  const [editSongTitle, setEditSongTitle] = useState('')

  useEffect(() => {
    loadInitialData()
  }, [])

  useEffect(() => {
    if (orgId) {
      loadPlacements()
    }
  }, [filterStatus, filterType, orgId])

  const loadInitialData = async () => {
    try {
      const orgResponse = await axios.get('/api/organizations/current')
      const id = orgResponse.data?.id
      if (!id) { setLoading(false); return }
      setOrgId(id)
      await Promise.all([loadPlacements(id), loadSummary(id)])
    } catch (err) {
      console.error('Failed to load data:', err)
    } finally {
      setLoading(false)
    }
  }

  const loadPlacements = async (id) => {
    const oid = id || orgId
    if (!oid) return
    try {
      const params = new URLSearchParams()
      if (filterStatus) params.append('status', filterStatus)
      if (filterType) params.append('placement_type', filterType)
      const response = await axios.get(`/api/placements/org/${oid}?${params}`)
      setPlacements(response.data)
    } catch (err) {
      console.error('Failed to load placements:', err)
    }
  }

  const loadSummary = async (id) => {
    const oid = id || orgId
    if (!oid) return
    try {
      const response = await axios.get(`/api/placements/org/${oid}/summary`)
      setSummary(response.data)
    } catch (err) {
      console.error('Failed to load summary:', err)
    }
  }

  const loadDetail = async (placementId) => {
    setDetailLoading(true)
    setError('')
    try {
      const response = await axios.get(`/api/placements/${placementId}`)
      setDetailData(response.data)
      setEditSongTitle(response.data.song_title || '')
      setEditForm({
        title: response.data.title || '',
        description: response.data.description || '',
        placement_type: response.data.placement_type || 'SYNC',
        song_id: response.data.song_id || '',
        work_id: response.data.work_id || '',
        contract_id: response.data.contract_id || '',
        client_name: response.data.client_name || '',
        project_name: response.data.project_name || '',
        media_type: response.data.media_type || '',
        license_fee: response.data.license_fee || '',
        license_currency: response.data.license_currency || 'USD',
        license_type: response.data.license_type || '',
        territory: response.data.territory || '',
        usage_notes: response.data.usage_notes || '',
        pitched_date: response.data.pitched_date || '',
        secured_date: response.data.secured_date || '',
        delivery_date: response.data.delivery_date || '',
        air_date: response.data.air_date || '',
        contact_name: response.data.contact_name || '',
        contact_email: response.data.contact_email || '',
        notes: response.data.notes || '',
        assigned_to_user_id: response.data.assigned_to_user_id || '',
      })
    } catch (err) {
      console.error('Failed to load detail:', err)
    } finally {
      setDetailLoading(false)
    }
  }

  const handleSelectPlacement = (p) => {
    setSelectedPlacement(p.id)
    setEditMode(false)
    loadDetail(p.id)
  }

  const handleCreate = async (e) => {
    e.preventDefault()
    if (!createForm.title.trim()) return
    setSaving(true)
    setError('')
    try {
      const payload = { ...createForm }
      if (payload.song_id) payload.song_id = parseInt(payload.song_id)
      else delete payload.song_id
      if (payload.work_id) payload.work_id = parseInt(payload.work_id)
      else delete payload.work_id
      if (payload.contract_id) payload.contract_id = parseInt(payload.contract_id)
      else delete payload.contract_id
      if (payload.assigned_to_user_id) payload.assigned_to_user_id = parseInt(payload.assigned_to_user_id)
      else delete payload.assigned_to_user_id
      if (payload.license_fee) payload.license_fee = parseFloat(payload.license_fee)
      else delete payload.license_fee
      if (!payload.media_type) delete payload.media_type
      if (!payload.pitched_date) delete payload.pitched_date
      if (!payload.description) delete payload.description
      if (!payload.license_type) delete payload.license_type
      if (!payload.territory) delete payload.territory
      if (!payload.usage_notes) delete payload.usage_notes
      if (!payload.contact_name) delete payload.contact_name
      if (!payload.contact_email) delete payload.contact_email
      if (!payload.notes) delete payload.notes
      if (!payload.client_name) delete payload.client_name
      if (!payload.project_name) delete payload.project_name

      await axios.post(`/api/placements/org/${orgId}`, payload)
      setShowCreateModal(false)
      setCreateForm({ ...emptyCreateForm })
      setCreateSongTitle('')
      await Promise.all([loadPlacements(), loadSummary()])
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create placement')
    } finally {
      setSaving(false)
    }
  }

  const handleUpdate = async () => {
    setSaving(true)
    setError('')
    try {
      const payload = { ...editForm }
      if (payload.song_id) payload.song_id = parseInt(payload.song_id)
      else payload.song_id = null
      if (payload.work_id) payload.work_id = parseInt(payload.work_id)
      else payload.work_id = null
      if (payload.contract_id) payload.contract_id = parseInt(payload.contract_id)
      else payload.contract_id = null
      if (payload.assigned_to_user_id) payload.assigned_to_user_id = parseInt(payload.assigned_to_user_id)
      else payload.assigned_to_user_id = null
      if (payload.license_fee) payload.license_fee = parseFloat(payload.license_fee)
      else payload.license_fee = null
      if (!payload.pitched_date) payload.pitched_date = null
      if (!payload.secured_date) payload.secured_date = null
      if (!payload.delivery_date) payload.delivery_date = null
      if (!payload.air_date) payload.air_date = null

      await axios.put(`/api/placements/${selectedPlacement}`, payload)
      setEditMode(false)
      await Promise.all([loadDetail(selectedPlacement), loadPlacements(), loadSummary()])
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update placement')
    } finally {
      setSaving(false)
    }
  }

  const handleTransition = async (targetStatus) => {
    setTransitioning(true)
    setError('')
    try {
      await axios.post(`/api/placements/${selectedPlacement}/transition?target_status=${targetStatus}`)
      await Promise.all([loadDetail(selectedPlacement), loadPlacements(), loadSummary()])
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to transition status')
    } finally {
      setTransitioning(false)
    }
  }

  const handleDelete = async () => {
    if (!window.confirm('Are you sure you want to delete this placement?')) return
    try {
      await axios.delete(`/api/placements/${selectedPlacement}`)
      setSelectedPlacement(null)
      setDetailData(null)
      await Promise.all([loadPlacements(), loadSummary()])
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete placement')
    }
  }

  const activeCount = Object.entries(summary.status_counts || {})
    .filter(([s]) => !['DECLINED', 'CANCELLED', 'PAID'].includes(s))
    .reduce((sum, [, c]) => sum + c, 0)

  const hasActiveFilters = filterStatus || filterType

  if (loading) {
    return (
      <div className="min-h-screen bg-[#F5F7F4] flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-[#5B8A72] border-t-transparent"></div>
          <p className="mt-4 text-[#7A8580]">Loading placements...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#F5F7F4]">
      <div className="bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white">
        <div className="max-w-7xl mx-auto px-6 py-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold">Sync Placements</h1>
              <p className="mt-1 text-white/80">Sync licensing, film, TV & advertising pipeline</p>
            </div>
            <button
              onClick={() => setShowCreateModal(true)}
              className="flex items-center gap-2 bg-white/20 hover:bg-white/30 backdrop-blur-sm text-white px-5 py-2.5 rounded-xl font-medium transition-all"
            >
              <PlusIcon className="w-5 h-5" />
              New Placement
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 -mt-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-[18px] border border-[rgba(59,77,67,0.08)] shadow-sm p-5">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-9 h-9 rounded-xl bg-[rgba(91,138,114,0.12)] flex items-center justify-center">
                <ArrowTrendingUpIcon className="w-5 h-5 text-[#5B8A72]" />
              </div>
              <span className="text-xs font-medium text-[#7A8580] uppercase tracking-wide">Pipeline Value</span>
            </div>
            <p className="text-2xl font-bold text-[#3D4A44]">{formatCurrency(summary.total_pipeline_value)}</p>
          </div>
          <div className="bg-white rounded-[18px] border border-[rgba(59,77,67,0.08)] shadow-sm p-5">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-9 h-9 rounded-xl bg-[rgba(91,154,110,0.15)] flex items-center justify-center">
                <BanknotesIcon className="w-5 h-5 text-[#5B9A6E]" />
              </div>
              <span className="text-xs font-medium text-[#7A8580] uppercase tracking-wide">Total Paid</span>
            </div>
            <p className="text-2xl font-bold text-[#3D4A44]">{formatCurrency(summary.total_paid)}</p>
          </div>
          <div className="bg-white rounded-[18px] border border-[rgba(59,77,67,0.08)] shadow-sm p-5">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-9 h-9 rounded-xl bg-[rgba(90,138,154,0.12)] flex items-center justify-center">
                <ClockIcon className="w-5 h-5 text-[#5A8A9A]" />
              </div>
              <span className="text-xs font-medium text-[#7A8580] uppercase tracking-wide">Active</span>
            </div>
            <p className="text-2xl font-bold text-[#3D4A44]">{activeCount}</p>
          </div>
          <div className="bg-white rounded-[18px] border border-[rgba(59,77,67,0.08)] shadow-sm p-5">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-9 h-9 rounded-xl bg-[rgba(91,138,114,0.08)] flex items-center justify-center">
                <DocumentTextIcon className="w-5 h-5 text-[#5B8A72]" />
              </div>
              <span className="text-xs font-medium text-[#7A8580] uppercase tracking-wide">Total</span>
            </div>
            <p className="text-2xl font-bold text-[#3D4A44]">{summary.total_placements}</p>
          </div>
        </div>

        <div className="flex flex-wrap gap-2 mb-2">
          {Object.entries(summary.status_counts || {}).map(([status, count]) => {
            const style = STATUS_BADGE_STYLES[status] || { bg: '#eee', text: '#666' }
            return (
              <button
                key={status}
                onClick={() => setFilterStatus(filterStatus === status ? '' : status)}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                  filterStatus === status ? 'ring-2 ring-offset-1 ring-[#5B8A72]' : ''
                }`}
                style={{ backgroundColor: style.bg, color: style.text }}
              >
                {formatStatus(status)}
                <span className="font-bold">{count}</span>
              </button>
            )
          })}
        </div>

        <div className="flex items-center gap-3 mb-6">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all border ${
              hasActiveFilters
                ? 'bg-[#5B8A72] text-white border-[#5B8A72]'
                : 'bg-white text-[#3D4A44] border-[rgba(59,77,67,0.08)] hover:border-[#5B8A72]'
            }`}
          >
            <FunnelIcon className="w-4 h-4" />
            Filters
            {hasActiveFilters && (
              <span className="ml-1 bg-white/30 rounded-full px-1.5 text-xs">
                {(filterStatus ? 1 : 0) + (filterType ? 1 : 0)}
              </span>
            )}
          </button>
          {hasActiveFilters && (
            <button
              onClick={() => { setFilterStatus(''); setFilterType('') }}
              className="text-sm text-[#C47068] hover:underline"
            >
              Clear filters
            </button>
          )}
          <button
            onClick={() => { loadPlacements(); loadSummary() }}
            className="ml-auto flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm text-[#7A8580] hover:text-[#3D4A44] hover:bg-white transition-all"
          >
            <ArrowPathIcon className="w-4 h-4" />
            Refresh
          </button>
        </div>

        {showFilters && (
          <div className="bg-white rounded-[18px] border border-[rgba(59,77,67,0.08)] shadow-sm p-5 mb-6 flex flex-wrap gap-4">
            <div>
              <label className="block text-xs font-medium text-[#7A8580] mb-1">Status</label>
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="border border-[rgba(59,77,67,0.15)] rounded-lg px-3 py-2 text-sm text-[#3D4A44] bg-white focus:outline-none focus:ring-2 focus:ring-[#5B8A72]/30"
              >
                <option value="">All Statuses</option>
                {PLACEMENT_STATUSES.map(s => (
                  <option key={s} value={s}>{formatStatus(s)}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-[#7A8580] mb-1">Placement Type</label>
              <select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                className="border border-[rgba(59,77,67,0.15)] rounded-lg px-3 py-2 text-sm text-[#3D4A44] bg-white focus:outline-none focus:ring-2 focus:ring-[#5B8A72]/30"
              >
                <option value="">All Types</option>
                {PLACEMENT_TYPES.map(t => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pb-8">
          {placements.map((p) => {
            const statusStyle = STATUS_BADGE_STYLES[p.status] || { bg: '#eee', text: '#666' }
            const TypeIcon = PLACEMENT_TYPE_ICONS[p.placement_type] || DocumentTextIcon
            return (
              <div
                key={p.id}
                onClick={() => handleSelectPlacement(p)}
                className={`bg-white rounded-[18px] border shadow-sm p-5 cursor-pointer transition-all hover:shadow-md hover:-translate-y-0.5 ${
                  selectedPlacement === p.id
                    ? 'border-[#5B8A72] ring-2 ring-[#5B8A72]/20'
                    : 'border-[rgba(59,77,67,0.08)]'
                }`}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-lg bg-[rgba(91,138,114,0.1)] flex items-center justify-center">
                      <TypeIcon className="w-4 h-4 text-[#5B8A72]" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-[#3D4A44] text-sm leading-tight">{p.title}</h3>
                      <p className="text-xs text-[#7A8580]">{p.placement_type}</p>
                    </div>
                  </div>
                  <span
                    className="inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-semibold"
                    style={{ backgroundColor: statusStyle.bg, color: statusStyle.text }}
                  >
                    {formatStatus(p.status)}
                  </span>
                </div>

                {(p.client_name || p.project_name) && (
                  <div className="mb-2">
                    {p.client_name && <p className="text-xs text-[#3D4A44] font-medium">{p.client_name}</p>}
                    {p.project_name && <p className="text-xs text-[#7A8580]">{p.project_name}</p>}
                  </div>
                )}

                {p.song_title && (
                  <div className="flex items-center gap-1.5 mb-2">
                    <MusicalNoteIcon className="w-3.5 h-3.5 text-[#7A8580]" />
                    <span className="text-xs text-[#7A8580]">{p.song_title}</span>
                  </div>
                )}

                <div className="flex items-center justify-between mt-3 pt-3 border-t border-[rgba(59,77,67,0.06)]">
                  <span className="text-sm font-semibold text-[#3D4A44]">
                    {p.license_fee ? formatCurrency(p.license_fee, p.license_currency) : '—'}
                  </span>
                  <div className="flex items-center gap-1 text-xs text-[#7A8580]">
                    <CalendarIcon className="w-3.5 h-3.5" />
                    {p.pitched_date ? formatDate(p.pitched_date) : (p.created_at ? formatDate(p.created_at) : '—')}
                  </div>
                </div>
              </div>
            )
          })}

          {placements.length === 0 && (
            <div className="col-span-full bg-white rounded-[18px] border border-[rgba(59,77,67,0.08)] shadow-sm p-12 text-center">
              <FilmIcon className="w-12 h-12 text-[#7A8580] mx-auto mb-3 opacity-40" />
              <p className="text-[#7A8580] text-lg font-medium">No placements found</p>
              <p className="text-[#7A8580]/70 text-sm mt-1">
                {hasActiveFilters ? 'Try adjusting your filters' : 'Create your first placement to get started'}
              </p>
              {!hasActiveFilters && (
                <button
                  onClick={() => setShowCreateModal(true)}
                  className="mt-4 bg-[#5B8A72] hover:bg-[#4A7A62] text-white px-5 py-2.5 rounded-xl font-medium transition-all inline-flex items-center gap-2"
                >
                  <PlusIcon className="w-4 h-4" />
                  New Placement
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {selectedPlacement && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div className="absolute inset-0 bg-black/20 backdrop-blur-sm" onClick={() => { setSelectedPlacement(null); setDetailData(null); setEditMode(false) }} />
          <div className="relative w-full max-w-xl bg-[#F5F7F4] shadow-2xl overflow-y-auto animate-slide-in">
            <div className="sticky top-0 z-10 bg-white border-b border-[rgba(59,77,67,0.08)] px-6 py-4 flex items-center justify-between">
              <h2 className="text-lg font-bold text-[#3D4A44]">Placement Details</h2>
              <div className="flex items-center gap-2">
                {!editMode && (
                  <button
                    onClick={() => setEditMode(true)}
                    className="p-2 rounded-lg text-[#7A8580] hover:bg-[#EEF1EC] transition-all"
                  >
                    <PencilSquareIcon className="w-5 h-5" />
                  </button>
                )}
                <button
                  onClick={handleDelete}
                  className="p-2 rounded-lg text-[#C47068] hover:bg-[rgba(196,112,104,0.1)] transition-all"
                >
                  <TrashIcon className="w-5 h-5" />
                </button>
                <button
                  onClick={() => { setSelectedPlacement(null); setDetailData(null); setEditMode(false) }}
                  className="p-2 rounded-lg text-[#7A8580] hover:bg-[#EEF1EC] transition-all"
                >
                  <XMarkIcon className="w-5 h-5" />
                </button>
              </div>
            </div>

            {detailLoading ? (
              <div className="p-12 text-center">
                <div className="inline-block animate-spin rounded-full h-8 w-8 border-3 border-[#5B8A72] border-t-transparent"></div>
              </div>
            ) : detailData ? (
              <div className="p-6 space-y-5">
                {error && (
                  <div className="bg-[rgba(196,112,104,0.1)] border border-[rgba(196,112,104,0.2)] rounded-xl p-3 text-sm text-[#C47068]">
                    {error}
                  </div>
                )}

                {!editMode ? (
                  <>
                    <div className="bg-white rounded-[18px] border border-[rgba(59,77,67,0.08)] shadow-sm p-5">
                      <div className="flex items-start justify-between mb-4">
                        <div>
                          <h3 className="text-xl font-bold text-[#3D4A44]">{detailData.title}</h3>
                          <p className="text-sm text-[#7A8580] mt-0.5">{detailData.placement_type} • {detailData.media_type || 'No media type'}</p>
                        </div>
                        <span
                          className="inline-flex items-center px-3 py-1.5 rounded-full text-xs font-semibold"
                          style={{
                            backgroundColor: (STATUS_BADGE_STYLES[detailData.status] || {}).bg,
                            color: (STATUS_BADGE_STYLES[detailData.status] || {}).text
                          }}
                        >
                          {formatStatus(detailData.status)}
                        </span>
                      </div>
                      {detailData.description && (
                        <p className="text-sm text-[#7A8580] mb-4">{detailData.description}</p>
                      )}
                      <div className="grid grid-cols-2 gap-4">
                        <InfoField label="Client" value={detailData.client_name} />
                        <InfoField label="Project" value={detailData.project_name} />
                        <InfoField label="License Fee" value={detailData.license_fee ? formatCurrency(detailData.license_fee, detailData.license_currency) : null} />
                        <InfoField label="Territory" value={detailData.territory} />
                        <InfoField label="License Type" value={detailData.license_type} />
                        <InfoField label="Assigned To" value={detailData.assigned_to_name} />
                      </div>
                    </div>

                    <div className="bg-white rounded-[18px] border border-[rgba(59,77,67,0.08)] shadow-sm p-5">
                      <h4 className="text-sm font-semibold text-[#3D4A44] mb-3">Linked Records</h4>
                      <div className="grid grid-cols-2 gap-4">
                        <InfoField label="Song" value={detailData.song_title} icon={<MusicalNoteIcon className="w-3.5 h-3.5" />} />
                        <InfoField label="Work" value={detailData.work_title} />
                        <InfoField label="Contract" value={detailData.contract_title} />
                      </div>
                    </div>

                    <div className="bg-white rounded-[18px] border border-[rgba(59,77,67,0.08)] shadow-sm p-5">
                      <h4 className="text-sm font-semibold text-[#3D4A44] mb-3">Contact</h4>
                      <div className="grid grid-cols-2 gap-4">
                        <InfoField label="Name" value={detailData.contact_name} icon={<UserIcon className="w-3.5 h-3.5" />} />
                        <InfoField label="Email" value={detailData.contact_email} icon={<EnvelopeIcon className="w-3.5 h-3.5" />} />
                      </div>
                    </div>

                    <div className="bg-white rounded-[18px] border border-[rgba(59,77,67,0.08)] shadow-sm p-5">
                      <h4 className="text-sm font-semibold text-[#3D4A44] mb-3">Timeline</h4>
                      <div className="grid grid-cols-2 gap-4">
                        <InfoField label="Pitched" value={formatDate(detailData.pitched_date)} />
                        <InfoField label="Secured" value={formatDate(detailData.secured_date)} />
                        <InfoField label="Delivered" value={formatDate(detailData.delivery_date)} />
                        <InfoField label="Aired" value={formatDate(detailData.air_date)} />
                      </div>
                    </div>

                    {detailData.usage_notes && (
                      <div className="bg-white rounded-[18px] border border-[rgba(59,77,67,0.08)] shadow-sm p-5">
                        <h4 className="text-sm font-semibold text-[#3D4A44] mb-2">Usage Notes</h4>
                        <p className="text-sm text-[#7A8580]">{detailData.usage_notes}</p>
                      </div>
                    )}

                    {detailData.notes && (
                      <div className="bg-white rounded-[18px] border border-[rgba(59,77,67,0.08)] shadow-sm p-5">
                        <h4 className="text-sm font-semibold text-[#3D4A44] mb-2">Notes</h4>
                        <p className="text-sm text-[#7A8580]">{detailData.notes}</p>
                      </div>
                    )}

                    {(STATUS_TRANSITIONS[detailData.status] || []).length > 0 && (
                      <div className="bg-white rounded-[18px] border border-[rgba(59,77,67,0.08)] shadow-sm p-5">
                        <h4 className="text-sm font-semibold text-[#3D4A44] mb-3">Status Workflow</h4>
                        <div className="flex flex-wrap gap-2">
                          {(STATUS_TRANSITIONS[detailData.status] || []).map((nextStatus) => {
                            const isNegative = ['DECLINED', 'CANCELLED'].includes(nextStatus)
                            const isPositive = ['SECURED', 'PAID'].includes(nextStatus)
                            return (
                              <button
                                key={nextStatus}
                                onClick={() => handleTransition(nextStatus)}
                                disabled={transitioning}
                                className={`px-4 py-2 rounded-xl text-sm font-medium transition-all disabled:opacity-50 ${
                                  isNegative
                                    ? 'bg-[rgba(196,112,104,0.1)] text-[#C47068] hover:bg-[rgba(196,112,104,0.2)]'
                                    : isPositive
                                    ? 'bg-[#5B8A72] text-white hover:bg-[#4A7A62]'
                                    : 'bg-[#EEF1EC] text-[#3D4A44] hover:bg-[#E0E4DD]'
                                }`}
                              >
                                {transitioning ? '...' : `→ ${formatStatus(nextStatus)}`}
                              </button>
                            )
                          })}
                        </div>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="bg-white rounded-[18px] border border-[rgba(59,77,67,0.08)] shadow-sm p-5">
                    <h4 className="text-sm font-semibold text-[#3D4A44] mb-4">Edit Placement</h4>
                    <div className="space-y-4">
                      <FormField label="Title" value={editForm.title} onChange={(v) => setEditForm({ ...editForm, title: v })} />
                      <FormField label="Description" value={editForm.description} onChange={(v) => setEditForm({ ...editForm, description: v })} textarea />
                      <FormSelect label="Placement Type" value={editForm.placement_type} onChange={(v) => setEditForm({ ...editForm, placement_type: v })} options={PLACEMENT_TYPES} />
                      <FormSelect label="Media Type" value={editForm.media_type} onChange={(v) => setEditForm({ ...editForm, media_type: v })} options={MEDIA_TYPES} allowEmpty />
                      <FormField label="Client Name" value={editForm.client_name} onChange={(v) => setEditForm({ ...editForm, client_name: v })} />
                      <FormField label="Project Name" value={editForm.project_name} onChange={(v) => setEditForm({ ...editForm, project_name: v })} />
                      <div className="grid grid-cols-2 gap-4">
                        <FormField label="License Fee" value={editForm.license_fee} onChange={(v) => setEditForm({ ...editForm, license_fee: v })} type="number" />
                        <FormField label="Currency" value={editForm.license_currency} onChange={(v) => setEditForm({ ...editForm, license_currency: v })} />
                      </div>
                      <FormField label="License Type" value={editForm.license_type} onChange={(v) => setEditForm({ ...editForm, license_type: v })} />
                      <FormField label="Territory" value={editForm.territory} onChange={(v) => setEditForm({ ...editForm, territory: v })} />
                      <FormField label="Usage Notes" value={editForm.usage_notes} onChange={(v) => setEditForm({ ...editForm, usage_notes: v })} textarea />
                      <SongSearchField
                        label="Linked Song"
                        orgId={orgId}
                        value={editForm.song_id}
                        songTitle={editSongTitle}
                        onChange={(id, title) => { setEditForm({ ...editForm, song_id: id }); setEditSongTitle(title) }}
                        onClear={() => { setEditForm({ ...editForm, song_id: '' }); setEditSongTitle('') }}
                      />
                      <FormField label="Work ID" value={editForm.work_id} onChange={(v) => setEditForm({ ...editForm, work_id: v })} type="number" />
                      <div className="grid grid-cols-2 gap-4">
                        <FormField label="Contract ID" value={editForm.contract_id} onChange={(v) => setEditForm({ ...editForm, contract_id: v })} type="number" />
                        <FormField label="Assigned User ID" value={editForm.assigned_to_user_id} onChange={(v) => setEditForm({ ...editForm, assigned_to_user_id: v })} type="number" />
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <FormField label="Pitched Date" value={editForm.pitched_date} onChange={(v) => setEditForm({ ...editForm, pitched_date: v })} type="date" />
                        <FormField label="Secured Date" value={editForm.secured_date} onChange={(v) => setEditForm({ ...editForm, secured_date: v })} type="date" />
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <FormField label="Delivery Date" value={editForm.delivery_date} onChange={(v) => setEditForm({ ...editForm, delivery_date: v })} type="date" />
                        <FormField label="Air Date" value={editForm.air_date} onChange={(v) => setEditForm({ ...editForm, air_date: v })} type="date" />
                      </div>
                      <FormField label="Contact Name" value={editForm.contact_name} onChange={(v) => setEditForm({ ...editForm, contact_name: v })} />
                      <FormField label="Contact Email" value={editForm.contact_email} onChange={(v) => setEditForm({ ...editForm, contact_email: v })} type="email" />
                      <FormField label="Notes" value={editForm.notes} onChange={(v) => setEditForm({ ...editForm, notes: v })} textarea />

                      <div className="flex items-center gap-3 pt-2">
                        <button
                          onClick={handleUpdate}
                          disabled={saving}
                          className="bg-[#5B8A72] hover:bg-[#4A7A62] text-white px-5 py-2.5 rounded-xl font-medium transition-all disabled:opacity-50"
                        >
                          {saving ? 'Saving...' : 'Save Changes'}
                        </button>
                        <button
                          onClick={() => setEditMode(false)}
                          className="px-5 py-2.5 rounded-xl font-medium text-[#7A8580] hover:bg-[#EEF1EC] transition-all"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ) : null}
          </div>
        </div>
      )}

      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/20 backdrop-blur-sm" onClick={() => setShowCreateModal(false)} />
          <div className="relative w-full max-w-lg max-h-[90vh] bg-white rounded-[18px] shadow-2xl overflow-y-auto">
            <div className="sticky top-0 z-10 bg-white border-b border-[rgba(59,77,67,0.08)] px-6 py-4 flex items-center justify-between rounded-t-[18px]">
              <h2 className="text-lg font-bold text-[#3D4A44]">New Placement</h2>
              <button
                onClick={() => setShowCreateModal(false)}
                className="p-2 rounded-lg text-[#7A8580] hover:bg-[#EEF1EC] transition-all"
              >
                <XMarkIcon className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleCreate} className="p-6 space-y-4">
              {error && (
                <div className="bg-[rgba(196,112,104,0.1)] border border-[rgba(196,112,104,0.2)] rounded-xl p-3 text-sm text-[#C47068]">
                  {error}
                </div>
              )}
              <FormField label="Title *" value={createForm.title} onChange={(v) => setCreateForm({ ...createForm, title: v })} required />
              <FormField label="Description" value={createForm.description} onChange={(v) => setCreateForm({ ...createForm, description: v })} textarea />
              <FormSelect label="Placement Type" value={createForm.placement_type} onChange={(v) => setCreateForm({ ...createForm, placement_type: v })} options={PLACEMENT_TYPES} />
              <FormSelect label="Media Type" value={createForm.media_type} onChange={(v) => setCreateForm({ ...createForm, media_type: v })} options={MEDIA_TYPES} allowEmpty />
              <FormField label="Client Name" value={createForm.client_name} onChange={(v) => setCreateForm({ ...createForm, client_name: v })} />
              <FormField label="Project Name" value={createForm.project_name} onChange={(v) => setCreateForm({ ...createForm, project_name: v })} />
              <div className="grid grid-cols-2 gap-4">
                <FormField label="License Fee" value={createForm.license_fee} onChange={(v) => setCreateForm({ ...createForm, license_fee: v })} type="number" />
                <FormField label="Currency" value={createForm.license_currency} onChange={(v) => setCreateForm({ ...createForm, license_currency: v })} />
              </div>
              <FormField label="License Type" value={createForm.license_type} onChange={(v) => setCreateForm({ ...createForm, license_type: v })} />
              <FormField label="Territory" value={createForm.territory} onChange={(v) => setCreateForm({ ...createForm, territory: v })} />
              <SongSearchField
                label="Linked Song"
                orgId={orgId}
                value={createForm.song_id}
                songTitle={createSongTitle}
                onChange={(id, title) => { setCreateForm({ ...createForm, song_id: id }); setCreateSongTitle(title) }}
                onClear={() => { setCreateForm({ ...createForm, song_id: '' }); setCreateSongTitle('') }}
              />
              <FormField label="Pitched Date" value={createForm.pitched_date} onChange={(v) => setCreateForm({ ...createForm, pitched_date: v })} type="date" />
              <FormField label="Contact Name" value={createForm.contact_name} onChange={(v) => setCreateForm({ ...createForm, contact_name: v })} />
              <FormField label="Contact Email" value={createForm.contact_email} onChange={(v) => setCreateForm({ ...createForm, contact_email: v })} type="email" />
              <FormField label="Notes" value={createForm.notes} onChange={(v) => setCreateForm({ ...createForm, notes: v })} textarea />

              <div className="flex items-center gap-3 pt-2">
                <button
                  type="submit"
                  disabled={saving || !createForm.title.trim()}
                  className="bg-[#5B8A72] hover:bg-[#4A7A62] text-white px-5 py-2.5 rounded-xl font-medium transition-all disabled:opacity-50"
                >
                  {saving ? 'Creating...' : 'Create Placement'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-5 py-2.5 rounded-xl font-medium text-[#7A8580] hover:bg-[#EEF1EC] transition-all"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <style>{`
        @keyframes slide-in {
          from { transform: translateX(100%); }
          to { transform: translateX(0); }
        }
        .animate-slide-in {
          animation: slide-in 0.3s cubic-bezier(0.25, 0.1, 0.25, 1);
        }
      `}</style>
    </div>
  )
}

function InfoField({ label, value, icon }) {
  return (
    <div>
      <span className="text-xs text-[#7A8580] block mb-0.5">{label}</span>
      <span className="text-sm text-[#3D4A44] flex items-center gap-1.5">
        {icon}
        {value || '—'}
      </span>
    </div>
  )
}

function SongSearchField({ label, orgId, value, songTitle, onChange, onClear }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [showDropdown, setShowDropdown] = useState(false)
  const debounceRef = useRef(null)
  const containerRef = useRef(null)

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setShowDropdown(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleSearch = (searchQuery) => {
    setQuery(searchQuery)
    if (debounceRef.current) clearTimeout(debounceRef.current)
    if (searchQuery.length < 2) {
      setResults([])
      setShowDropdown(false)
      return
    }
    debounceRef.current = setTimeout(async () => {
      setLoading(true)
      try {
        const response = await axios.get(`/api/songs/org/${orgId}?search=${encodeURIComponent(searchQuery)}`)
        const songs = response.data.songs || response.data || []
        setResults(songs)
        setShowDropdown(true)
      } catch (err) {
        console.error('Song search failed:', err)
        setResults([])
      } finally {
        setLoading(false)
      }
    }, 300)
  }

  const handleSelect = (song) => {
    const displayTitle = song.artist_name ? `${song.title} - ${song.artist_name}` : song.title
    onChange(song.id, displayTitle)
    setQuery('')
    setResults([])
    setShowDropdown(false)
  }

  const handleClear = () => {
    onClear()
    setQuery('')
    setResults([])
    setShowDropdown(false)
  }

  const inputCls = "w-full border border-[rgba(59,77,67,0.15)] rounded-lg px-3 py-2 text-sm text-[#3D4A44] bg-white focus:outline-none focus:ring-2 focus:ring-[#5B8A72]/30 placeholder:text-[#7A8580]/50"

  return (
    <div ref={containerRef}>
      <label className="block text-xs font-medium text-[#7A8580] mb-1">{label}</label>
      <div className="relative">
        {value && songTitle ? (
          <div className={`${inputCls} flex items-center justify-between`}>
            <span className="truncate">{songTitle}</span>
            <button
              type="button"
              onClick={handleClear}
              className="ml-2 flex-shrink-0 p-0.5 rounded hover:bg-[#EEF1EC] text-[#7A8580] hover:text-[#C47068] transition-colors"
            >
              <XMarkIcon className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <input
            type="text"
            value={query}
            onChange={(e) => handleSearch(e.target.value)}
            onFocus={() => { if (results.length > 0) setShowDropdown(true) }}
            placeholder="Search songs..."
            className={inputCls}
          />
        )}
        {loading && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2">
            <div className="animate-spin rounded-full h-4 w-4 border-2 border-[#5B8A72] border-t-transparent"></div>
          </div>
        )}
        {showDropdown && results.length > 0 && (
          <div className="absolute z-50 w-full mt-1 bg-white border border-[rgba(59,77,67,0.15)] rounded-lg shadow-lg max-h-48 overflow-y-auto">
            {results.map((song) => (
              <div
                key={song.id}
                onClick={() => handleSelect(song)}
                className="px-3 py-2 text-sm hover:bg-[#EEF1EC] cursor-pointer"
              >
                <span className="font-medium text-[#3D4A44]">{song.title}</span>
                {song.artist_name && <span className="text-[#7A8580]"> — {song.artist_name}</span>}
              </div>
            ))}
          </div>
        )}
        {showDropdown && query.length >= 2 && !loading && results.length === 0 && (
          <div className="absolute z-50 w-full mt-1 bg-white border border-[rgba(59,77,67,0.15)] rounded-lg shadow-lg">
            <div className="px-3 py-2 text-sm text-[#7A8580]">No songs found</div>
          </div>
        )}
      </div>
    </div>
  )
}

function FormField({ label, value, onChange, type = 'text', textarea, required }) {
  const cls = "w-full border border-[rgba(59,77,67,0.15)] rounded-lg px-3 py-2 text-sm text-[#3D4A44] bg-white focus:outline-none focus:ring-2 focus:ring-[#5B8A72]/30 placeholder:text-[#7A8580]/50"
  return (
    <div>
      <label className="block text-xs font-medium text-[#7A8580] mb-1">{label}</label>
      {textarea ? (
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          rows={3}
          className={cls}
        />
      ) : (
        <input
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          required={required}
          className={cls}
        />
      )}
    </div>
  )
}

function FormSelect({ label, value, onChange, options, allowEmpty }) {
  return (
    <div>
      <label className="block text-xs font-medium text-[#7A8580] mb-1">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full border border-[rgba(59,77,67,0.15)] rounded-lg px-3 py-2 text-sm text-[#3D4A44] bg-white focus:outline-none focus:ring-2 focus:ring-[#5B8A72]/30"
      >
        {allowEmpty && <option value="">—</option>}
        {options.map(o => <option key={o} value={o}>{o.replace(/_/g, ' ')}</option>)}
      </select>
    </div>
  )
}
