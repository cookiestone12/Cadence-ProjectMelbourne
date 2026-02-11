import React, { useState, useEffect, useCallback } from 'react'
import axios from 'axios'
import {
  MagnifyingGlassIcon, PlusIcon, FunnelIcon, XMarkIcon,
  TrashIcon, PencilSquareIcon, MusicalNoteIcon,
  CalendarIcon, ExclamationTriangleIcon, CheckCircleIcon,
  ChevronLeftIcon, ChevronDownIcon, ChevronUpIcon, ArrowDownTrayIcon, ArrowPathIcon,
  ShieldCheckIcon, ClipboardDocumentCheckIcon, PhotoIcon,
  InformationCircleIcon, CheckIcon, LinkIcon, DocumentTextIcon
} from '@heroicons/react/24/outline'

const READINESS_TOOLTIPS = {
  'UPC/EAN code': 'A Universal Product Code is required by all digital stores and streaming platforms to identify your release.',
  'Catalog number': 'Your internal catalog reference number helps distributors and stores organize your catalog.',
  'Release date': 'Stores need a release date to schedule your release and coordinate with editorial playlists.',
  'Primary artist': 'The main performing artist name is displayed on all streaming platforms and stores.',
  'Label name': 'The label name appears on store pages and is used for royalty reporting and crediting.',
  'Genre': 'Genre classification helps platforms categorize your release and recommend it to the right listeners.',
  'Cover artwork': 'High-quality artwork (min 3000x3000px recommended) is required by all major platforms.',
  'Copyright notice': 'The copyright notice (© or ℗) protects your intellectual property and is legally required for distribution.',
  'Copyright notice (℗/©)': 'The copyright notice (© or ℗) protects your intellectual property and is legally required for distribution.',
  'Copyright year': 'The copyright year establishes when the work was first published or the recording was made.',
  'ISRC': 'International Standard Recording Code uniquely identifies each track for royalty tracking and radio play monitoring.',
  'Track title': 'Each track must have a title for proper display on streaming platforms.',
  'Track artist': 'The performing artist for each track helps platforms display proper credits.',
  'Credits/contributors': 'Adding credits (writers, producers) ensures proper royalty splits and legal compliance.',
}

const STATUS_COLORS = {
  DRAFT: 'bg-gray-100 text-gray-700',
  READY: 'bg-blue-100 text-blue-700',
  SUBMITTED: 'bg-amber-100 text-amber-700',
  RELEASED: 'bg-green-100 text-green-700',
}

const TYPE_LABELS = {
  SINGLE: 'Single',
  EP: 'EP',
  ALBUM: 'Album',
  COMPILATION: 'Compilation',
  MIXTAPE: 'Mixtape',
}

export default function ReleasesPage() {
  const [releases, setReleases] = useState([])
  const [totalCount, setTotalCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [organizationId, setOrganizationId] = useState(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [selectedRelease, setSelectedRelease] = useState(null)
  const [detailData, setDetailData] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [editMode, setEditMode] = useState(false)
  const [editForm, setEditForm] = useState({})
  const [songs, setSongs] = useState([])
  const [addTrackSongId, setAddTrackSongId] = useState('')
  const [readiness, setReadiness] = useState(null)
  const [readinessLoading, setReadinessLoading] = useState(false)
  const [transitionLoading, setTransitionLoading] = useState(false)
  const [transitionError, setTransitionError] = useState('')
  const [showSubmitConfirm, setShowSubmitConfirm] = useState(false)
  const [editingIsrc, setEditingIsrc] = useState(null)
  const [isrcValue, setIsrcValue] = useState('')
  const [showFilters, setShowFilters] = useState(false)
  const [filters, setFilters] = useState({ status: '', release_type: '' })
  const [artworkUrls, setArtworkUrls] = useState({})
  const [detailArtworkUrl, setDetailArtworkUrl] = useState(null)
  const [expandedTrack, setExpandedTrack] = useState(null)
  const [trackEdits, setTrackEdits] = useState({})
  const [savingTrack, setSavingTrack] = useState(null)
  const [creators, setCreators] = useState([])
  const [createForm, setCreateForm] = useState({
    title: '',
    release_type: 'SINGLE',
    primary_artist: '',
    label: '',
    upc: '',
    catalog_number: '',
    release_date: '',
    genre: '',
    copyright_line: '',
    copyright_year: '',
    description: '',
    creator_id: '',
  })

  useEffect(() => {
    loadReleases()
    loadCreators()
  }, [filters])

  async function fetchArtworkBlob(releaseId) {
    try {
      const response = await axios.get(`/api/releases/${releaseId}/artwork`, { responseType: 'blob' })
      return URL.createObjectURL(response.data)
    } catch {
      return null
    }
  }

  async function loadCreators() {
    try {
      const orgResponse = await axios.get('/api/organizations/current')
      const orgId = orgResponse.data?.id
      if (!orgId) return
      const response = await axios.get(`/api/creators/org/${orgId}`)
      setCreators(Array.isArray(response.data) ? response.data : [])
    } catch (error) {
      console.error('Failed to load creators:', error)
    }
  }

  async function loadReleases() {
    try {
      const orgResponse = await axios.get('/api/organizations/current')
      const orgId = orgResponse.data?.id
      if (!orgId) { setLoading(false); return }
      setOrganizationId(orgId)

      const params = new URLSearchParams()
      if (filters.status) params.append('status', filters.status)
      if (filters.release_type) params.append('release_type', filters.release_type)
      params.append('limit', '500')

      const response = await axios.get(`/api/releases/org/${orgId}?${params}`)
      const releasesData = response.data.releases || []
      setReleases(releasesData)
      setTotalCount(response.data.total || 0)
      const withArt = releasesData.filter(r => r.cover_art_url)
      if (withArt.length > 0) {
        const urls = {}
        await Promise.all(withArt.map(async (r) => {
          const blobUrl = await fetchArtworkBlob(r.id)
          if (blobUrl) urls[r.id] = blobUrl
        }))
        setArtworkUrls(prev => ({ ...prev, ...urls }))
      }
    } catch (error) {
      console.error('Failed to load releases:', error)
    } finally {
      setLoading(false)
    }
  }

  async function loadReleaseDetail(releaseId) {
    setDetailLoading(true)
    setDetailArtworkUrl(null)
    try {
      const response = await axios.get(`/api/releases/${releaseId}`)
      setDetailData(response.data)
      loadReadiness(releaseId)
      if (response.data.cover_art_url) {
        fetchArtworkBlob(releaseId).then(url => {
          if (url) {
            setDetailArtworkUrl(url)
            setArtworkUrls(prev => ({ ...prev, [releaseId]: url }))
          }
        })
      }
      setEditForm({
        title: response.data.title || '',
        release_type: response.data.release_type || 'SINGLE',
        primary_artist: response.data.primary_artist || '',
        label: response.data.label || '',
        upc: response.data.upc || '',
        catalog_number: response.data.catalog_number || '',
        release_date: response.data.release_date || '',
        genre: response.data.genre || '',
        subgenre: response.data.subgenre || '',
        description: response.data.description || '',
        copyright_line: response.data.copyright_line || '',
        copyright_year: response.data.copyright_year || '',
        notes: response.data.notes || '',
        creator_id: response.data.creator_id || '',
      })

      if (organizationId) {
        const songsResponse = await axios.get(`/api/songs/org/${organizationId}?limit=1000`)
        setSongs(Array.isArray(songsResponse.data) ? songsResponse.data : [])
      }
    } catch (error) {
      console.error('Failed to load release detail:', error)
    } finally {
      setDetailLoading(false)
    }
  }

  async function handleCreateRelease(e) {
    e.preventDefault()
    try {
      const payload = { ...createForm }
      if (payload.copyright_year) payload.copyright_year = parseInt(payload.copyright_year)
      if (!payload.release_date) delete payload.release_date
      if (payload.creator_id) payload.creator_id = parseInt(payload.creator_id)
      else delete payload.creator_id

      await axios.post(`/api/releases/org/${organizationId}`, payload)
      setShowCreateModal(false)
      setCreateForm({
        title: '',
        release_type: 'SINGLE',
        primary_artist: '',
        label: '',
        upc: '',
        catalog_number: '',
        release_date: '',
        genre: '',
        copyright_line: '',
        copyright_year: '',
        description: '',
        creator_id: '',
      })
      loadReleases()
    } catch (error) {
      console.error('Failed to create release:', error)
    }
  }

  async function handleUpdateRelease() {
    try {
      const payload = { ...editForm }
      if (payload.copyright_year) payload.copyright_year = parseInt(payload.copyright_year)
      if (!payload.release_date) delete payload.release_date
      if (payload.creator_id) payload.creator_id = parseInt(payload.creator_id)
      else payload.creator_id = null

      await axios.put(`/api/releases/${selectedRelease}`, payload)
      setEditMode(false)
      loadReleaseDetail(selectedRelease)
      loadReleases()
    } catch (error) {
      console.error('Failed to update release:', error)
    }
  }

  async function handleDeleteRelease(releaseId) {
    if (!window.confirm('Are you sure you want to delete this release?')) return
    try {
      await axios.delete(`/api/releases/${releaseId}`)
      setSelectedRelease(null)
      setDetailData(null)
      loadReleases()
    } catch (error) {
      console.error('Failed to delete release:', error)
    }
  }

  async function handleAddTrack() {
    if (!addTrackSongId) return
    try {
      await axios.post(`/api/releases/${selectedRelease}/tracks`, { song_id: parseInt(addTrackSongId) })
      setAddTrackSongId('')
      loadReleaseDetail(selectedRelease)
    } catch (error) {
      console.error('Failed to add track:', error)
    }
  }

  async function handleRemoveTrack(songId) {
    try {
      await axios.delete(`/api/releases/${selectedRelease}/tracks/${songId}`)
      loadReleaseDetail(selectedRelease)
    } catch (error) {
      console.error('Failed to remove track:', error)
    }
  }

  async function loadReadiness(releaseId) {
    setReadinessLoading(true)
    try {
      const response = await axios.get(`/api/releases/${releaseId}/readiness`)
      setReadiness(response.data)
    } catch (error) {
      console.error('Failed to load readiness:', error)
    } finally {
      setReadinessLoading(false)
    }
  }

  async function handleTransition(newStatus, force = false) {
    if (newStatus === 'SUBMITTED' && readiness && !readiness.is_ready && !force) {
      setShowSubmitConfirm(true)
      return
    }
    setTransitionLoading(true)
    setTransitionError('')
    setShowSubmitConfirm(false)
    try {
      await axios.post(`/api/releases/${selectedRelease}/transition`, { new_status: newStatus, force })
      loadReleaseDetail(selectedRelease)
      loadReadiness(selectedRelease)
      loadReleases()
    } catch (error) {
      setTransitionError(error.response?.data?.detail || 'Failed to update status')
    } finally {
      setTransitionLoading(false)
    }
  }

  async function handleSaveIsrc(songId) {
    try {
      await axios.patch(`/api/songs/${songId}`, { isrc: isrcValue })
      setEditingIsrc(null)
      setIsrcValue('')
      loadReleaseDetail(selectedRelease)
      loadReadiness(selectedRelease)
    } catch (error) {
      console.error('Failed to update ISRC:', error)
    }
  }

  async function handleSaveTrackFields(songId) {
    const edits = trackEdits[songId]
    if (!edits) return
    setSavingTrack(songId)
    try {
      await axios.patch(`/api/songs/${songId}`, edits)
      loadReleaseDetail(selectedRelease)
      setSavingTrack(null)
    } catch (error) {
      console.error('Failed to save track fields:', error)
      setSavingTrack(null)
    }
  }

  function handleExport(format) {
    const token = localStorage.getItem('token')
    const url = `/api/releases/${selectedRelease}/export/${format}`
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then(res => {
        if (!res.ok) throw new Error('Export failed')
        return res.blob()
      })
      .then(blob => {
        const a = document.createElement('a')
        a.href = URL.createObjectURL(blob)
        a.download = `release_export.${format === 'csv' ? 'csv' : 'pdf'}`
        a.click()
        URL.revokeObjectURL(a.href)
      })
      .catch(err => console.error('Export failed:', err))
  }

  const filteredReleases = releases.filter(r => {
    if (!searchTerm) return true
    const term = searchTerm.toLowerCase()
    return (
      (r.title && r.title.toLowerCase().includes(term)) ||
      (r.primary_artist && r.primary_artist.toLowerCase().includes(term)) ||
      (r.upc && r.upc.toLowerCase().includes(term))
    )
  })

  const hasActiveFilters = filters.status || filters.release_type

  const statusCounts = {
    DRAFT: releases.filter(r => r.status === 'DRAFT').length,
    READY: releases.filter(r => r.status === 'READY').length,
    SUBMITTED: releases.filter(r => r.status === 'SUBMITTED').length,
    RELEASED: releases.filter(r => r.status === 'RELEASED').length,
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-[#7A8580]">Loading releases...</div>
      </div>
    )
  }

  if (selectedRelease && detailData) {
    const existingTrackSongIds = (detailData.tracks || []).map(t => t.song_id)
    const availableSongs = songs.filter(s => !existingTrackSongIds.includes(s.id))

    return (
      <div className="p-8">
        <button
          onClick={() => { setSelectedRelease(null); setDetailData(null); setEditMode(false) }}
          className="flex items-center space-x-2 text-[#7A8580] hover:text-[#3D4A44] mb-6 transition-colors"
        >
          <ChevronLeftIcon className="w-5 h-5" />
          <span>Back to Releases</span>
        </button>

        <div className="flex items-start justify-between mb-6">
          <div className="flex items-center space-x-4">
            <div className="relative group w-20 h-20">
              <div className="w-20 h-20 bg-[#EEF1EC] rounded-xl flex items-center justify-center overflow-hidden">
                {(detailArtworkUrl || detailData.cover_art_url) ? (
                  <img src={detailArtworkUrl || ''} alt={detailData.title} className="w-20 h-20 rounded-xl object-cover" onError={(e) => e.target.style.display='none'} />
                ) : (
                  <MusicalNoteIcon className="w-10 h-10 text-[#7A8580]" />
                )}
              </div>
              <label className="absolute inset-0 bg-black/40 rounded-xl flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer">
                <PhotoIcon className="w-6 h-6 text-white" />
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp,image/gif"
                  className="hidden"
                  onChange={async (e) => {
                    const file = e.target.files[0]
                    if (!file) return
                    const formData = new FormData()
                    formData.append('file', file)
                    try {
                      await axios.post(`/api/releases/${selectedRelease}/artwork`, formData, {
                        headers: { 'Content-Type': 'multipart/form-data' }
                      })
                      loadReleaseDetail(selectedRelease)
                    } catch (err) {
                      alert(err.response?.data?.detail || 'Failed to upload artwork')
                    }
                  }}
                />
              </label>
            </div>
            <div>
              <h1 className="text-3xl font-bold text-[#3D4A44]">{detailData.title}</h1>
              <div className="flex items-center space-x-3 mt-1">
                <span className="text-[#7A8580]">{detailData.primary_artist || 'No artist'}</span>
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[detailData.status] || STATUS_COLORS.DRAFT}`}>
                  {detailData.status}
                </span>
                <span className="text-xs text-[#7A8580] bg-[#EEF1EC] px-2 py-0.5 rounded-full">
                  {TYPE_LABELS[detailData.release_type] || detailData.release_type}
                </span>
              </div>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={() => setEditMode(!editMode)}
              className="flex items-center space-x-2 px-4 py-2 bg-[#EEF1EC] text-[#3D4A44] rounded-lg hover:bg-[#E4E8E2] transition-colors"
            >
              <PencilSquareIcon className="w-5 h-5" />
              <span>{editMode ? 'Cancel' : 'Edit'}</span>
            </button>
            <button
              onClick={() => handleDeleteRelease(selectedRelease)}
              className="flex items-center space-x-2 px-4 py-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 transition-colors"
            >
              <TrashIcon className="w-5 h-5" />
              <span>Delete</span>
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <div className="bg-[#FAFBF9] rounded-xl shadow-sm p-6">
              <h2 className="text-lg font-semibold text-[#3D4A44] mb-4">Release Details</h2>
              {editMode ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
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
                      value={editForm.release_type}
                      onChange={(e) => setEditForm(prev => ({ ...prev, release_type: e.target.value }))}
                      className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                    >
                      <option value="SINGLE">Single</option>
                      <option value="EP">EP</option>
                      <option value="ALBUM">Album</option>
                      <option value="COMPILATION">Compilation</option>
                      <option value="MIXTAPE">Mixtape</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-[#3D4A44] mb-1">Status</label>
                    <div className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 bg-[#EEF1EC] text-[#7A8580] text-sm">
                      {detailData?.status || 'DRAFT'} — Use the status workflow buttons to change status
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-[#3D4A44] mb-1">Primary Artist</label>
                    <input
                      type="text"
                      value={editForm.primary_artist}
                      onChange={(e) => setEditForm(prev => ({ ...prev, primary_artist: e.target.value }))}
                      className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-[#3D4A44] mb-1">Assign to Client</label>
                    <select
                      value={editForm.creator_id}
                      onChange={(e) => setEditForm(prev => ({ ...prev, creator_id: e.target.value }))}
                      className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                    >
                      <option value="">— No client assigned —</option>
                      {creators.map(c => (
                        <option key={c.id} value={c.id}>{c.display_name}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-[#3D4A44] mb-1">Label</label>
                    <input
                      type="text"
                      value={editForm.label}
                      onChange={(e) => setEditForm(prev => ({ ...prev, label: e.target.value }))}
                      className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-[#3D4A44] mb-1">UPC</label>
                    <input
                      type="text"
                      value={editForm.upc}
                      onChange={(e) => setEditForm(prev => ({ ...prev, upc: e.target.value }))}
                      className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-[#3D4A44] mb-1">Catalog Number</label>
                    <input
                      type="text"
                      value={editForm.catalog_number}
                      onChange={(e) => setEditForm(prev => ({ ...prev, catalog_number: e.target.value }))}
                      className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-[#3D4A44] mb-1">Release Date</label>
                    <input
                      type="date"
                      value={editForm.release_date}
                      onChange={(e) => setEditForm(prev => ({ ...prev, release_date: e.target.value }))}
                      className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-[#3D4A44] mb-1">Genre</label>
                    <input
                      type="text"
                      value={editForm.genre}
                      onChange={(e) => setEditForm(prev => ({ ...prev, genre: e.target.value }))}
                      className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-[#3D4A44] mb-1">Copyright Line</label>
                    <input
                      type="text"
                      value={editForm.copyright_line}
                      onChange={(e) => setEditForm(prev => ({ ...prev, copyright_line: e.target.value }))}
                      className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-[#3D4A44] mb-1">Copyright Year</label>
                    <input
                      type="number"
                      value={editForm.copyright_year}
                      onChange={(e) => setEditForm(prev => ({ ...prev, copyright_year: e.target.value }))}
                      className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                    />
                  </div>
                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-[#3D4A44] mb-1">Description</label>
                    <textarea
                      value={editForm.description}
                      onChange={(e) => setEditForm(prev => ({ ...prev, description: e.target.value }))}
                      rows={3}
                      className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                    />
                  </div>
                  <div className="md:col-span-2 flex justify-end space-x-3">
                    <button
                      onClick={() => setEditMode(false)}
                      className="px-4 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg text-[#3D4A44] hover:bg-[#EEF1EC] transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleUpdateRelease}
                      className="px-4 py-2 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] transition-colors"
                    >
                      Save Changes
                    </button>
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <div>
                    <p className="text-xs text-[#7A8580]">Type</p>
                    <p className="text-sm font-medium text-[#3D4A44]">{TYPE_LABELS[detailData.release_type] || detailData.release_type}</p>
                  </div>
                  <div>
                    <p className="text-xs text-[#7A8580]">Label</p>
                    <p className="text-sm font-medium text-[#3D4A44]">{detailData.label || '-'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-[#7A8580]">UPC</p>
                    <p className="text-sm font-medium text-[#3D4A44]">{detailData.upc || '-'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-[#7A8580]">Release Date</p>
                    <p className="text-sm font-medium text-[#3D4A44]">{detailData.release_date || '-'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-[#7A8580]">Genre</p>
                    <p className="text-sm font-medium text-[#3D4A44]">{detailData.genre || '-'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-[#7A8580]">Assigned Client</p>
                    <p className="text-sm font-medium text-[#3D4A44]">{detailData.creator_name || 'Not assigned'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-[#7A8580]">Catalog #</p>
                    <p className="text-sm font-medium text-[#3D4A44]">{detailData.catalog_number || '-'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-[#7A8580]">Copyright</p>
                    <p className="text-sm font-medium text-[#3D4A44]">
                      {detailData.copyright_line ? `${detailData.copyright_line} (${detailData.copyright_year || '-'})` : '-'}
                    </p>
                  </div>
                  {detailData.description && (
                    <div className="col-span-2 md:col-span-3">
                      <p className="text-xs text-[#7A8580]">Description</p>
                      <p className="text-sm text-[#3D4A44]">{detailData.description}</p>
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="bg-[#FAFBF9] rounded-xl shadow-sm p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-[#3D4A44]">
                  Tracks ({(detailData.tracks || []).length})
                </h2>
              </div>

              <div className="flex items-center space-x-3 mb-4">
                <select
                  value={addTrackSongId}
                  onChange={(e) => setAddTrackSongId(e.target.value)}
                  className="flex-1 border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                >
                  <option value="">Select a song to add...</option>
                  {availableSongs.map(song => (
                    <option key={song.id} value={song.id}>{song.title} — {song.primary_artist}</option>
                  ))}
                </select>
                <button
                  onClick={handleAddTrack}
                  disabled={!addTrackSongId}
                  className="flex items-center space-x-2 px-4 py-2 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <PlusIcon className="w-5 h-5" />
                  <span>Add</span>
                </button>
              </div>

              {(detailData.tracks || []).length === 0 ? (
                <div className="text-center py-8 text-[#7A8580]">No tracks added yet</div>
              ) : (
                <div className="divide-y divide-[rgba(59,77,67,0.08)]">
                  {(detailData.tracks || []).map((track) => {
                    const isExpanded = expandedTrack === track.song_id
                    const currentEdits = trackEdits[track.song_id] || {}
                    const hasAudio = track.audio_file_url || currentEdits.audio_file_url
                    const hasLyrics = track.lyrics || currentEdits.lyrics
                    return (
                    <div key={track.id}>
                      <div className="flex items-center justify-between py-3">
                        <div className="flex items-center space-x-4 flex-1 min-w-0">
                          <span className="text-sm font-medium text-[#7A8580] w-12 flex-shrink-0">
                            {track.disc_number > 1 ? `${track.disc_number}-` : ''}{track.track_number}
                          </span>
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center space-x-2">
                              <p className="text-sm font-medium text-[#3D4A44]">{track.title}</p>
                              {hasAudio && <LinkIcon className="w-3.5 h-3.5 text-[#5B8A72] flex-shrink-0" title="Has audio link" />}
                              {hasLyrics && <DocumentTextIcon className="w-3.5 h-3.5 text-[#5B8A72] flex-shrink-0" title="Has lyrics" />}
                            </div>
                            <div className="flex items-center space-x-1">
                              <p className="text-xs text-[#7A8580]">{track.primary_artist}</p>
                              {editingIsrc === track.song_id ? (
                                <div className="flex items-center space-x-1 ml-1">
                                  <span className="text-xs text-[#7A8580]">·</span>
                                  <input
                                    type="text"
                                    value={isrcValue}
                                    onChange={(e) => setIsrcValue(e.target.value.toUpperCase())}
                                    placeholder="e.g. USRC12345678"
                                    className="text-xs border border-[#5B8A72] rounded px-1.5 py-0.5 w-36 focus:ring-1 focus:ring-[#5B8A72] focus:outline-none bg-white text-[#3D4A44]"
                                    autoFocus
                                    onKeyDown={(e) => {
                                      if (e.key === 'Enter') handleSaveIsrc(track.song_id)
                                      if (e.key === 'Escape') { setEditingIsrc(null); setIsrcValue('') }
                                    }}
                                  />
                                  <button onClick={() => handleSaveIsrc(track.song_id)} className="text-[#5B8A72] hover:text-[#4A7A62]">
                                    <CheckIcon className="w-3.5 h-3.5" />
                                  </button>
                                  <button onClick={() => { setEditingIsrc(null); setIsrcValue('') }} className="text-[#7A8580] hover:text-red-500">
                                    <XMarkIcon className="w-3.5 h-3.5" />
                                  </button>
                                </div>
                              ) : (
                                <button
                                  onClick={() => { setEditingIsrc(track.song_id); setIsrcValue(track.isrc || '') }}
                                  className="flex items-center space-x-1 ml-1 group/isrc"
                                  title={track.isrc ? 'Edit ISRC' : 'Add ISRC'}
                                >
                                  {track.isrc ? (
                                    <span className="text-xs text-[#7A8580]">· {track.isrc}</span>
                                  ) : (
                                    <span className="text-xs text-amber-500">· Add ISRC</span>
                                  )}
                                  <PencilSquareIcon className="w-3 h-3 text-[#7A8580] opacity-0 group-hover/isrc:opacity-100 transition-opacity" />
                                </button>
                              )}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center space-x-2 flex-shrink-0">
                          <button
                            onClick={() => {
                              if (isExpanded) {
                                setExpandedTrack(null)
                              } else {
                                setExpandedTrack(track.song_id)
                                if (!trackEdits[track.song_id]) {
                                  setTrackEdits(prev => ({
                                    ...prev,
                                    [track.song_id]: {
                                      audio_file_url: track.audio_file_url || '',
                                      lyrics: track.lyrics || '',
                                    }
                                  }))
                                }
                              }
                            }}
                            className="text-[#7A8580] hover:text-[#5B8A72] transition-colors"
                            title="Edit audio link & lyrics"
                          >
                            {isExpanded ? <ChevronUpIcon className="w-5 h-5" /> : <ChevronDownIcon className="w-5 h-5" />}
                          </button>
                          <button
                            onClick={() => handleRemoveTrack(track.song_id)}
                            className="text-[#7A8580] hover:text-red-500 transition-colors"
                          >
                            <XMarkIcon className="w-5 h-5" />
                          </button>
                        </div>
                      </div>
                      {isExpanded && (
                        <div className="pb-4 pl-16 pr-4 space-y-3">
                          <div>
                            <label className="flex items-center space-x-1.5 text-xs font-medium text-[#7A8580] mb-1">
                              <LinkIcon className="w-3.5 h-3.5" />
                              <span>Audio File Link</span>
                            </label>
                            <input
                              type="url"
                              value={currentEdits.audio_file_url || ''}
                              onChange={(e) => setTrackEdits(prev => ({
                                ...prev,
                                [track.song_id]: { ...prev[track.song_id], audio_file_url: e.target.value }
                              }))}
                              placeholder="Dropbox, Google Drive, or direct link to audio file"
                              className="w-full text-sm border border-[rgba(59,77,67,0.15)] rounded-lg px-3 py-2 focus:ring-1 focus:ring-[#5B8A72] focus:border-[#5B8A72] focus:outline-none bg-white text-[#3D4A44]"
                            />
                            {currentEdits.audio_file_url && (
                              <a href={currentEdits.audio_file_url} target="_blank" rel="noopener noreferrer" className="text-xs text-[#5B8A72] hover:underline mt-1 inline-block">
                                Open link
                              </a>
                            )}
                          </div>
                          <div>
                            <label className="flex items-center space-x-1.5 text-xs font-medium text-[#7A8580] mb-1">
                              <DocumentTextIcon className="w-3.5 h-3.5" />
                              <span>Lyrics</span>
                            </label>
                            <textarea
                              value={currentEdits.lyrics || ''}
                              onChange={(e) => setTrackEdits(prev => ({
                                ...prev,
                                [track.song_id]: { ...prev[track.song_id], lyrics: e.target.value }
                              }))}
                              placeholder="Paste or type lyrics here..."
                              rows={6}
                              className="w-full text-sm border border-[rgba(59,77,67,0.15)] rounded-lg px-3 py-2 focus:ring-1 focus:ring-[#5B8A72] focus:border-[#5B8A72] focus:outline-none bg-white text-[#3D4A44] resize-y"
                            />
                          </div>
                          <div className="flex justify-end">
                            <button
                              onClick={() => handleSaveTrackFields(track.song_id)}
                              disabled={savingTrack === track.song_id}
                              className="flex items-center space-x-1.5 px-4 py-1.5 bg-[#5B8A72] text-white text-sm rounded-lg hover:bg-[#4A7A62] transition-colors disabled:opacity-50"
                            >
                              <CheckIcon className="w-4 h-4" />
                              <span>{savingTrack === track.song_id ? 'Saving...' : 'Save'}</span>
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  )})}
                </div>
              )}
            </div>
          </div>

          <div className="space-y-6">
            <div className="bg-[#FAFBF9] rounded-xl shadow-sm p-6">
              <div className="flex items-center space-x-2 mb-4">
                <ArrowPathIcon className="w-5 h-5 text-[#5B8A72]" />
                <h2 className="text-lg font-semibold text-[#3D4A44]">Status Workflow</h2>
              </div>
              <div className="flex items-center space-x-2 mb-4">
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${STATUS_COLORS[detailData.status] || STATUS_COLORS.DRAFT}`}>
                  {detailData.status}
                </span>
              </div>
              <div className="space-y-2">
                {detailData.status === 'DRAFT' && (
                  <button
                    onClick={() => handleTransition('READY')}
                    disabled={transitionLoading}
                    className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] transition-colors disabled:opacity-50"
                  >
                    <ShieldCheckIcon className="w-5 h-5" />
                    <span>{transitionLoading ? 'Updating...' : 'Mark as Ready'}</span>
                  </button>
                )}
                {detailData.status === 'READY' && (
                  <>
                    <button
                      onClick={() => handleTransition('SUBMITTED')}
                      disabled={transitionLoading}
                      className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] transition-colors disabled:opacity-50"
                    >
                      <ClipboardDocumentCheckIcon className="w-5 h-5" />
                      <span>{transitionLoading ? 'Updating...' : 'Submit for Distribution'}</span>
                    </button>
                    {showSubmitConfirm && (
                      <div className="mt-2 p-4 bg-amber-50 border border-amber-200 rounded-lg">
                        <div className="flex items-start space-x-2 mb-3">
                          <ExclamationTriangleIcon className="w-5 h-5 text-amber-500 mt-0.5 flex-shrink-0" />
                          <div>
                            <p className="text-sm font-medium text-amber-800">Incomplete readiness ({Math.round(readiness?.readiness_score || 0)}%)</p>
                            <p className="text-xs text-amber-600 mt-1">Some required items are still missing. Submitting without completing them may cause delays or rejections from distributors.</p>
                            {readiness && (
                              <ul className="mt-2 space-y-0.5">
                                {(readiness.release_checks || []).filter(c => c.required && !c.passed).map((c, i) => (
                                  <li key={i} className="text-xs text-amber-700">• {c.label}</li>
                                ))}
                                {(readiness.track_checks || []).flatMap(t => (t.checks || []).filter(c => !c.passed).map((c, i) => (
                                  <li key={`${t.song_id}-${i}`} className="text-xs text-amber-700">• {t.title}: {c.label}</li>
                                )))}
                              </ul>
                            )}
                          </div>
                        </div>
                        <div className="flex items-center space-x-2">
                          <button
                            onClick={() => handleTransition('SUBMITTED', true)}
                            disabled={transitionLoading}
                            className="flex-1 px-3 py-1.5 bg-amber-500 text-white text-sm rounded-lg hover:bg-amber-600 transition-colors disabled:opacity-50"
                          >
                            {transitionLoading ? 'Submitting...' : 'Submit Anyway'}
                          </button>
                          <button
                            onClick={() => setShowSubmitConfirm(false)}
                            className="flex-1 px-3 py-1.5 border border-amber-300 text-amber-700 text-sm rounded-lg hover:bg-amber-100 transition-colors"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    )}
                    <button
                      onClick={() => handleTransition('DRAFT')}
                      disabled={transitionLoading}
                      className="w-full flex items-center justify-center space-x-2 px-4 py-2 border border-[rgba(59,77,67,0.12)] text-[#3D4A44] rounded-lg hover:bg-[#EEF1EC] transition-colors disabled:opacity-50"
                    >
                      <span>{transitionLoading ? 'Updating...' : 'Back to Draft'}</span>
                    </button>
                  </>
                )}
                {detailData.status === 'SUBMITTED' && (
                  <>
                    <button
                      onClick={() => handleTransition('RELEASED')}
                      disabled={transitionLoading}
                      className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] transition-colors disabled:opacity-50"
                    >
                      <CheckCircleIcon className="w-5 h-5" />
                      <span>{transitionLoading ? 'Updating...' : 'Mark as Released'}</span>
                    </button>
                    <button
                      onClick={() => handleTransition('READY')}
                      disabled={transitionLoading}
                      className="w-full flex items-center justify-center space-x-2 px-4 py-2 border border-[rgba(59,77,67,0.12)] text-[#3D4A44] rounded-lg hover:bg-[#EEF1EC] transition-colors disabled:opacity-50"
                    >
                      <span>{transitionLoading ? 'Updating...' : 'Back to Ready'}</span>
                    </button>
                  </>
                )}
                {detailData.status === 'RELEASED' && (
                  <div className="flex items-center space-x-2 text-[#5B8A72] py-2">
                    <CheckCircleIcon className="w-5 h-5" />
                    <span className="text-sm font-medium">Released</span>
                  </div>
                )}
              </div>
              {transitionError && (
                <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg">
                  <div className="flex items-start space-x-2">
                    <ExclamationTriangleIcon className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
                    <span className="text-sm text-red-700">{transitionError}</span>
                  </div>
                </div>
              )}
            </div>

            <div className="bg-[#FAFBF9] rounded-xl shadow-sm p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-2">
                  <ShieldCheckIcon className="w-5 h-5 text-[#5B8A72]" />
                  <h2 className="text-lg font-semibold text-[#3D4A44]">Distribution Readiness</h2>
                </div>
                <button
                  onClick={() => loadReadiness(selectedRelease)}
                  className="text-[#7A8580] hover:text-[#3D4A44] transition-colors"
                  title="Refresh readiness"
                >
                  <ArrowPathIcon className={`w-4 h-4 ${readinessLoading ? 'animate-spin' : ''}`} />
                </button>
              </div>
              {readinessLoading && !readiness ? (
                <div className="flex items-center justify-center py-6">
                  <ArrowPathIcon className="w-6 h-6 text-[#7A8580] animate-spin" />
                </div>
              ) : readiness ? (
                <>
                  <div className="flex items-center space-x-3 mb-2">
                    <div className="flex-1 h-3 bg-[#EEF1EC] rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-[#5B8A72] to-[#7BA594] transition-all duration-300"
                        style={{ width: `${readiness.readiness_score || 0}%` }}
                      />
                    </div>
                    <span className="text-lg font-bold text-[#3D4A44]">
                      {Math.round(readiness.readiness_score || 0)}%
                    </span>
                  </div>
                  <p className="text-xs text-[#7A8580] mb-4">
                    {readiness.passed_required}/{readiness.total_required} required checks passed
                  </p>

                  {readiness.release_checks && readiness.release_checks.length > 0 && (
                    <div className="mb-4">
                      <p className="text-xs font-semibold text-[#3D4A44] uppercase tracking-wider mb-2">Release Checks</p>
                      {(() => {
                        const grouped = {}
                        readiness.release_checks.forEach(check => {
                          const cat = check.category || 'other'
                          if (!grouped[cat]) grouped[cat] = []
                          grouped[cat].push(check)
                        })
                        return Object.entries(grouped).map(([category, checks]) => (
                          <div key={category} className="mb-3">
                            <p className="text-xs text-[#7A8580] capitalize mb-1">{category}</p>
                            <div className="space-y-1">
                              {checks.map((check, idx) => (
                                <div key={idx} className="flex items-center space-x-2 group/tip">
                                  {check.passed ? (
                                    <CheckCircleIcon className="w-4 h-4 text-[#5B8A72] flex-shrink-0" />
                                  ) : (
                                    <XMarkIcon className="w-4 h-4 text-red-500 flex-shrink-0" />
                                  )}
                                  <span className={`text-xs ${check.passed ? 'text-[#3D4A44]' : 'text-red-600'}`}>
                                    {check.label}
                                    {check.required && <span className="text-[#7A8580]"> *</span>}
                                  </span>
                                  {READINESS_TOOLTIPS[check.label] && (
                                    <div className="relative">
                                      <InformationCircleIcon className="w-3.5 h-3.5 text-[#7A8580] opacity-50 hover:opacity-100 cursor-help peer" />
                                      <div className="absolute left-5 bottom-0 w-52 p-2 bg-[#3D4A44] text-white text-[10px] leading-snug rounded-lg shadow-lg opacity-0 invisible peer-hover:opacity-100 peer-hover:visible transition-all z-50 pointer-events-none">
                                        {READINESS_TOOLTIPS[check.label]}
                                      </div>
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        ))
                      })()}
                    </div>
                  )}

                  {readiness.track_checks && readiness.track_checks.length > 0 && (
                    <div>
                      <p className="text-xs font-semibold text-[#3D4A44] uppercase tracking-wider mb-2">Track Checks</p>
                      {readiness.track_checks.map((track) => (
                        <div key={track.song_id} className="mb-3">
                          <p className="text-xs font-medium text-[#3D4A44] mb-1">
                            {track.disc_number > 1 ? `${track.disc_number}-` : ''}{track.track_number}. {track.title}
                          </p>
                          <div className="space-y-1 pl-2">
                            {(track.checks || []).map((check, idx) => (
                              <div key={idx} className="flex items-center space-x-2">
                                {check.passed ? (
                                  <CheckCircleIcon className="w-3.5 h-3.5 text-[#5B8A72] flex-shrink-0" />
                                ) : (
                                  <XMarkIcon className="w-3.5 h-3.5 text-red-500 flex-shrink-0" />
                                )}
                                <span className={`text-xs ${check.passed ? 'text-[#3D4A44]' : 'text-red-600'}`}>
                                  {check.label}
                                </span>
                                {READINESS_TOOLTIPS[check.label] && (
                                  <div className="relative">
                                    <InformationCircleIcon className="w-3 h-3 text-[#7A8580] opacity-50 hover:opacity-100 cursor-help peer" />
                                    <div className="absolute left-4 bottom-0 w-48 p-2 bg-[#3D4A44] text-white text-[10px] leading-snug rounded-lg shadow-lg opacity-0 invisible peer-hover:opacity-100 peer-hover:visible transition-all z-50 pointer-events-none">
                                      {READINESS_TOOLTIPS[check.label]}
                                    </div>
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {readiness.is_ready && (
                    <div className="flex items-center space-x-2 text-[#5B8A72] mt-3 pt-3 border-t border-[rgba(59,77,67,0.08)]">
                      <CheckCircleIcon className="w-5 h-5" />
                      <span className="text-sm font-medium">Ready for distribution</span>
                    </div>
                  )}
                </>
              ) : (
                <p className="text-sm text-[#7A8580]">No readiness data available</p>
              )}
            </div>

            <div className="bg-[#FAFBF9] rounded-xl shadow-sm p-6">
              <div className="flex items-center space-x-2 mb-4">
                <ArrowDownTrayIcon className="w-5 h-5 text-[#5B8A72]" />
                <h2 className="text-lg font-semibold text-[#3D4A44]">Export</h2>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <button
                  onClick={() => handleExport('csv')}
                  disabled={!(detailData.tracks || []).length}
                  className="flex items-center justify-center space-x-2 px-4 py-2 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ArrowDownTrayIcon className="w-4 h-4" />
                  <span className="text-sm">Export CSV</span>
                </button>
                <button
                  onClick={() => handleExport('pdf')}
                  disabled={!(detailData.tracks || []).length}
                  className="flex items-center justify-center space-x-2 px-4 py-2 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ArrowDownTrayIcon className="w-4 h-4" />
                  <span className="text-sm">Export PDF</span>
                </button>
              </div>
            </div>
          </div>
        </div>

        {detailLoading && (
          <div className="fixed inset-0 bg-black/20 flex items-center justify-center z-50">
            <div className="bg-white rounded-xl p-6 shadow-xl">
              <div className="text-[#7A8580]">Loading...</div>
            </div>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="p-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold text-[#3D4A44] mb-2">Releases</h1>
          <p className="text-[#7A8580]">{totalCount} total releases</p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            className="flex items-center space-x-2 px-4 py-2 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] transition-colors"
            onClick={() => setShowCreateModal(true)}
          >
            <PlusIcon className="w-5 h-5" />
            <span>Create Release</span>
          </button>
        </div>
      </div>

      <div className="mb-6 border-b border-[rgba(59,77,67,0.08)]">
        <div className="flex space-x-8">
          {['ALL', 'DRAFT', 'READY', 'SUBMITTED', 'RELEASED'].map(status => (
            <button
              key={status}
              onClick={() => setFilters(prev => ({ ...prev, status: status === 'ALL' ? '' : status }))}
              className={`pb-3 px-1 border-b-2 font-medium transition-colors ${
                (status === 'ALL' && !filters.status) || filters.status === status
                  ? 'border-[#5B8A72] text-[#5B8A72]'
                  : 'border-transparent text-[#7A8580] hover:text-[#3D4A44]'
              }`}
            >
              {status === 'ALL' ? `All (${totalCount})` : `${status.charAt(0) + status.slice(1).toLowerCase()} (${statusCounts[status] || 0})`}
            </button>
          ))}
        </div>
      </div>

      <div className="bg-[#FAFBF9] rounded-xl shadow-sm p-4 mb-6">
        <div className="flex items-center space-x-4">
          <div className="flex-1 relative">
            <MagnifyingGlassIcon className="w-5 h-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-[#7A8580]" />
            <input
              type="text"
              placeholder="Search releases, artists, or UPC..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
            />
          </div>
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-colors ${
              hasActiveFilters
                ? 'bg-[#5B8A72] text-white'
                : 'bg-[#EEF1EC] text-[#3D4A44] hover:bg-[#E4E8E2]'
            }`}
          >
            <FunnelIcon className="w-5 h-5" />
            <span>Filters</span>
          </button>
        </div>

        {showFilters && (
          <div className="mt-4 pt-4 border-t border-[rgba(59,77,67,0.08)] grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-[#3D4A44] mb-1">Type</label>
              <select
                value={filters.release_type}
                onChange={(e) => setFilters(prev => ({ ...prev, release_type: e.target.value }))}
                className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
              >
                <option value="">All Types</option>
                <option value="SINGLE">Single</option>
                <option value="EP">EP</option>
                <option value="ALBUM">Album</option>
                <option value="COMPILATION">Compilation</option>
                <option value="MIXTAPE">Mixtape</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-[#3D4A44] mb-1">Status</label>
              <select
                value={filters.status}
                onChange={(e) => setFilters(prev => ({ ...prev, status: e.target.value }))}
                className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
              >
                <option value="">All Statuses</option>
                <option value="DRAFT">Draft</option>
                <option value="READY">Ready</option>
                <option value="SUBMITTED">Submitted</option>
                <option value="RELEASED">Released</option>
              </select>
            </div>
            <div className="flex items-end">
              <button
                onClick={() => setFilters({ status: '', release_type: '' })}
                className="w-full px-4 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg text-[#3D4A44] hover:bg-[#EEF1EC] transition-colors"
              >
                Clear Filters
              </button>
            </div>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {filteredReleases.map((release) => (
          <div
            key={release.id}
            onClick={() => {
              setSelectedRelease(release.id)
              loadReleaseDetail(release.id)
            }}
            className="bg-[#FAFBF9] rounded-xl shadow-sm hover:shadow-md cursor-pointer transition-all hover:translate-y-[-2px] overflow-hidden"
          >
            <div className="aspect-square bg-[#EEF1EC] flex items-center justify-center">
              {(artworkUrls[release.id] || release.cover_art_url) ? (
                <img src={artworkUrls[release.id] || ''} alt={release.title} className="w-full h-full object-cover" onError={(e) => e.target.style.display='none'} />
              ) : (
                <MusicalNoteIcon className="w-16 h-16 text-[#7A8580]" />
              )}
            </div>
            <div className="p-4">
              <div className="flex items-center justify-between mb-1">
                <h3 className="font-semibold text-[#3D4A44] truncate flex-1">{release.title}</h3>
              </div>
              <p className="text-sm text-[#7A8580] truncate mb-2">{release.primary_artist || 'No artist'}</p>
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[release.status] || STATUS_COLORS.DRAFT}`}>
                    {release.status}
                  </span>
                  <span className="text-xs text-[#7A8580] bg-[#EEF1EC] px-2 py-0.5 rounded-full">
                    {TYPE_LABELS[release.release_type] || release.release_type}
                  </span>
                </div>
              </div>
              <div className="flex items-center justify-between mt-3 text-xs text-[#7A8580]">
                <div className="flex items-center space-x-1">
                  <MusicalNoteIcon className="w-3.5 h-3.5" />
                  <span>{release.track_count || 0} tracks</span>
                </div>
                {release.release_date && (
                  <div className="flex items-center space-x-1">
                    <CalendarIcon className="w-3.5 h-3.5" />
                    <span>{release.release_date}</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}

        {filteredReleases.length === 0 && (
          <div className="col-span-full text-center py-12 text-[#7A8580]">
            No releases found
          </div>
        )}
      </div>

      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-[#3D4A44]">Create Release</h3>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-[#7A8580] hover:text-[#3D4A44] transition-colors"
              >
                <XMarkIcon className="w-6 h-6" />
              </button>
            </div>
            <form onSubmit={handleCreateRelease}>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Title *</label>
                  <input
                    type="text"
                    required
                    value={createForm.title}
                    onChange={(e) => setCreateForm(prev => ({ ...prev, title: e.target.value }))}
                    className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Release Type</label>
                  <select
                    value={createForm.release_type}
                    onChange={(e) => setCreateForm(prev => ({ ...prev, release_type: e.target.value }))}
                    className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  >
                    <option value="SINGLE">Single</option>
                    <option value="EP">EP</option>
                    <option value="ALBUM">Album</option>
                    <option value="COMPILATION">Compilation</option>
                    <option value="MIXTAPE">Mixtape</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Primary Artist</label>
                  <input
                    type="text"
                    value={createForm.primary_artist}
                    onChange={(e) => setCreateForm(prev => ({ ...prev, primary_artist: e.target.value }))}
                    className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Assign to Client</label>
                  <select
                    value={createForm.creator_id}
                    onChange={(e) => setCreateForm(prev => ({ ...prev, creator_id: e.target.value }))}
                    className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  >
                    <option value="">— No client assigned —</option>
                    {creators.map(c => (
                      <option key={c.id} value={c.id}>{c.display_name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Label</label>
                  <input
                    type="text"
                    value={createForm.label}
                    onChange={(e) => setCreateForm(prev => ({ ...prev, label: e.target.value }))}
                    className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">UPC</label>
                  <input
                    type="text"
                    value={createForm.upc}
                    onChange={(e) => setCreateForm(prev => ({ ...prev, upc: e.target.value }))}
                    className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Catalog Number</label>
                  <input
                    type="text"
                    value={createForm.catalog_number}
                    onChange={(e) => setCreateForm(prev => ({ ...prev, catalog_number: e.target.value }))}
                    className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Release Date</label>
                  <input
                    type="date"
                    value={createForm.release_date}
                    onChange={(e) => setCreateForm(prev => ({ ...prev, release_date: e.target.value }))}
                    className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Genre</label>
                  <input
                    type="text"
                    value={createForm.genre}
                    onChange={(e) => setCreateForm(prev => ({ ...prev, genre: e.target.value }))}
                    className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Copyright Line</label>
                  <input
                    type="text"
                    value={createForm.copyright_line}
                    onChange={(e) => setCreateForm(prev => ({ ...prev, copyright_line: e.target.value }))}
                    className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Copyright Year</label>
                  <input
                    type="number"
                    value={createForm.copyright_year}
                    onChange={(e) => setCreateForm(prev => ({ ...prev, copyright_year: e.target.value }))}
                    className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Description</label>
                  <textarea
                    value={createForm.description}
                    onChange={(e) => setCreateForm(prev => ({ ...prev, description: e.target.value }))}
                    rows={3}
                    className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  />
                </div>
              </div>
              <div className="flex items-center justify-end space-x-3 mt-6">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg text-[#3D4A44] hover:bg-[#EEF1EC] transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] transition-colors"
                >
                  Create Release
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
