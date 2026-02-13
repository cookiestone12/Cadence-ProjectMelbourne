import React, { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import axios from 'axios'
import {
  XMarkIcon, CheckCircleIcon, XCircleIcon, MinusCircleIcon,
  MusicalNoteIcon, ChartBarIcon, DocumentTextIcon, LinkIcon,
  DocumentArrowUpIcon, ArrowDownTrayIcon, TrashIcon, PlayIcon, UserIcon,
  ScaleIcon, PencilSquareIcon, PlusIcon
} from '@heroicons/react/24/outline'

export default function SongDetailModal({ song, onClose, onSongUpdated }) {
  const [activeTab, setActiveTab] = useState('overview')
  const [songDetails, setSongDetails] = useState(null)
  const [loading, setLoading] = useState(true)
  const [contracts, setContracts] = useState([])
  const [linkedContracts, setLinkedContracts] = useState([])
  const [uploading, setUploading] = useState(false)
  const [rightsData, setRightsData] = useState([])
  const [rightsLoading, setRightsLoading] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [editForm, setEditForm] = useState({})
  const [saving, setSaving] = useState(false)
  const [editFeedback, setEditFeedback] = useState(null)
  const fileInputRef = useRef(null)
  const [songSplits, setSongSplits] = useState([])
  const [showSplitForm, setShowSplitForm] = useState(false)
  const [splitForm, setSplitForm] = useState({ rights_holder_id: '', rights_holder_name: '', rights_type: 'PUBLISHING', share_percentage: '', notes: '' })
  const [splitSaving, setSplitSaving] = useState(false)
  const [splitCreators, setSplitCreators] = useState([])
  const [showAddClient, setShowAddClient] = useState(false)
  const [addClientCreatorId, setAddClientCreatorId] = useState('')
  const [addClientRole, setAddClientRole] = useState('PRIMARY_ARTIST')
  
  useEffect(() => {
    loadSongDetails()
    loadContracts()
    loadLinkedContracts()
    loadRightsData()
    loadSongSplits()
    loadSplitCreators()
  }, [song.id])
  
  async function loadSongDetails() {
    try {
      const token = localStorage.getItem('token')
      const response = await axios.get(`/api/songs/${song.id}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      setSongDetails(response.data)
    } catch (error) {
      console.error('Failed to load song details:', error)
    } finally {
      setLoading(false)
    }
  }
  
  async function loadContracts() {
    try {
      const token = localStorage.getItem('token')
      const response = await axios.get(`/api/contracts/song/${song.id}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      setContracts(response.data)
    } catch (error) {
      console.error('Failed to load contracts:', error)
    }
  }

  async function loadLinkedContracts() {
    try {
      const token = localStorage.getItem('token')
      const response = await axios.get(`/api/rights/contracts/song/${song.id}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      setLinkedContracts(response.data.contracts || [])
    } catch (error) {
      console.error('Failed to load linked contracts:', error)
    }
  }
  
  async function loadRightsData() {
    setRightsLoading(true)
    try {
      const orgResponse = await axios.get('/api/organizations/current')
      const orgId = orgResponse.data.id
      const response = await axios.get(`/api/rights/asset/${orgId}?asset_type=SONG&asset_id=${song.id}`)
      setRightsData(response.data.contracts || [])
    } catch (error) {
      console.error('Failed to load rights data:', error)
      setRightsData([])
    } finally {
      setRightsLoading(false)
    }
  }

  async function loadSongSplits() {
    try {
      const response = await axios.get(`/api/rights/song-splits/${song.id}`)
      setSongSplits(response.data.splits || [])
    } catch (error) {
      console.error('Failed to load song splits:', error)
    }
  }

  async function loadSplitCreators() {
    try {
      const orgResponse = await axios.get('/api/organizations/current')
      const orgId = orgResponse.data.id
      const response = await axios.get(`/api/creators/org/${orgId}`)
      setSplitCreators(response.data || [])
    } catch (error) {
      console.error('Failed to load creators:', error)
    }
  }

  async function handleAddSongSplit() {
    if (!splitForm.rights_holder_id && !splitForm.rights_holder_name) return
    if (!splitForm.share_percentage) return
    setSplitSaving(true)
    try {
      const payload = {
        rights_type: splitForm.rights_type,
        share_percentage: parseFloat(splitForm.share_percentage),
        notes: splitForm.notes || ''
      }
      if (splitForm.rights_holder_id) {
        payload.rights_holder_id = parseInt(splitForm.rights_holder_id)
      } else {
        payload.rights_holder_name = splitForm.rights_holder_name
      }
      await axios.post(`/api/rights/song-splits/${song.id}`, payload)
      setSplitForm({ rights_holder_id: '', rights_holder_name: '', rights_type: 'PUBLISHING', share_percentage: '', notes: '' })
      setShowSplitForm(false)
      loadSongSplits()
      loadRightsData()
    } catch (error) {
      console.error('Failed to add split:', error)
      alert(error.response?.data?.detail || 'Failed to add split')
    } finally {
      setSplitSaving(false)
    }
  }

  async function handleDownloadSplitSheet() {
    const standaloneSplit = songSplits.find(s => s.is_standalone && s.contract_id)
    const contractIds = [...new Set(songSplits.filter(s => s.contract_id).map(s => s.contract_id))]
    const downloadContractId = standaloneSplit ? standaloneSplit.contract_id : contractIds[0]
    if (!downloadContractId) return
    try {
      const response = await axios.get(`/api/rights/contracts/${downloadContractId}/split-sheet`, {
        params: { split_type: 'both' },
        responseType: 'blob',
      })
      const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `Split_Sheet_${song.title.replace(/[^a-zA-Z0-9]/g, '_')}.pdf`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Failed to download split sheet:', error)
      alert('Failed to download split sheet PDF')
    }
  }

  async function handleDeleteSongSplit(splitId) {
    if (!confirm('Remove this split?')) return
    try {
      await axios.delete(`/api/rights/song-splits/${splitId}`)
      loadSongSplits()
      loadRightsData()
    } catch (error) {
      console.error('Failed to delete split:', error)
    }
  }

  async function handleContractUpload(event) {
    const file = event.target.files[0]
    if (!file) return
    
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      alert('Only PDF files are allowed')
      return
    }
    
    setUploading(true)
    try {
      const token = localStorage.getItem('token')
      const formData = new FormData()
      formData.append('file', file)
      formData.append('contract_type', 'Agreement')
      
      await axios.post(`/api/contracts/upload/${song.id}`, formData, {
        headers: { 
          'Content-Type': 'multipart/form-data',
          'Authorization': `Bearer ${token}`
        }
      })
      
      await loadContracts()
      await loadSongDetails()
    } catch (error) {
      console.error('Failed to upload contract:', error)
      alert('Failed to upload contract')
    } finally {
      setUploading(false)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }
  
  async function handleDeleteContract(contractId) {
    if (!confirm('Are you sure you want to delete this contract?')) return
    
    try {
      const token = localStorage.getItem('token')
      await axios.delete(`/api/contracts/${contractId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      await loadContracts()
      await loadSongDetails()
    } catch (error) {
      console.error('Failed to delete contract:', error)
    }
  }
  
  function downloadContract(contractId) {
    const token = localStorage.getItem('token')
    window.open(`/api/contracts/download/${contractId}?token=${token}`, '_blank')
  }

  function startEditing() {
    setEditForm({
      title: songDetails.title || '',
      primary_artist: songDetails.primary_artist || '',
      isrc: songDetails.isrc || '',
      iswc: songDetails.iswc || '',
      project_title: songDetails.project_title || '',
      label: songDetails.label || '',
      release_date: songDetails.release_date || '',
      recording_code: songDetails.recording_code || '',
      notes: songDetails.notes || '',
      media_url: songDetails.media_url || '',
      publishing_percentage: songDetails.publishing_percentage ?? '',
      master_percentage: songDetails.master_percentage ?? '',
      advance_amount: songDetails.advance_amount ?? '',
      contract_location: songDetails.contract_location || '',
      payment_status: songDetails.payment_status || 'PENDING',
      is_paid: (() => { const s = String(songDetails.is_paid ?? '').toLowerCase(); if (s === 'true') return 'Yes'; if (s === 'false') return 'No'; return songDetails.is_paid || 'N/A' })(),
      is_invoiced: (() => { if (songDetails.is_invoiced == null) return 'N/A'; const s = String(songDetails.is_invoiced).toLowerCase(); if (s === 'n/a' || s === 'na') return 'N/A'; if (s === 'true' || s === 'yes' || s === 'false' || s === 'no' || s === '') return ''; return String(songDetails.is_invoiced) })(),
      is_registered_with_dsp: (() => { if (songDetails.is_registered_with_dsp == null) return 'N/A'; const s = String(songDetails.is_registered_with_dsp).toLowerCase(); if (s === 'n/a' || s === 'na') return 'N/A'; if (s === 'true' || s === 'yes' || s === 'false' || s === 'no' || s === '') return ''; return String(songDetails.is_registered_with_dsp) })(),
    })
    setIsEditing(true)
    setEditFeedback(null)
  }

  function cancelEditing() {
    setIsEditing(false)
    setEditForm({})
    setEditFeedback(null)
  }

  async function saveEdits() {
    setSaving(true)
    setEditFeedback(null)
    try {
      const token = localStorage.getItem('token')
      const payload = {}
      if (editForm.title !== (songDetails.title || '')) payload.title = editForm.title
      if (editForm.primary_artist !== (songDetails.primary_artist || '')) payload.primary_artist = editForm.primary_artist
      if (editForm.isrc !== (songDetails.isrc || '')) payload.isrc = editForm.isrc || null
      if (editForm.iswc !== (songDetails.iswc || '')) payload.iswc = editForm.iswc || null
      if (editForm.project_title !== (songDetails.project_title || '')) payload.project_title = editForm.project_title || null
      if (editForm.label !== (songDetails.label || '')) payload.label = editForm.label || null
      if (editForm.release_date !== (songDetails.release_date || '')) payload.release_date = editForm.release_date || null
      if (editForm.recording_code !== (songDetails.recording_code || '')) payload.recording_code = editForm.recording_code || null
      if (editForm.notes !== (songDetails.notes || '')) payload.notes = editForm.notes || null
      if (editForm.media_url !== (songDetails.media_url || '')) payload.media_url = editForm.media_url || null
      if (editForm.contract_location !== (songDetails.contract_location || '')) payload.contract_location = editForm.contract_location || null
      if (editForm.payment_status !== (songDetails.payment_status || 'PENDING')) payload.payment_status = editForm.payment_status

      const pubPct = editForm.publishing_percentage === '' ? null : parseFloat(editForm.publishing_percentage)
      if (pubPct !== (songDetails.publishing_percentage ?? null)) payload.publishing_percentage = pubPct

      const masterPct = editForm.master_percentage === '' ? null : parseFloat(editForm.master_percentage)
      if (masterPct !== (songDetails.master_percentage ?? null)) payload.master_percentage = masterPct

      const advAmt = editForm.advance_amount === '' ? null : parseInt(editForm.advance_amount, 10)
      if (advAmt !== (songDetails.advance_amount ?? null)) payload.advance_amount = advAmt

      if (editForm.is_paid !== (songDetails.is_paid || 'N/A')) payload.is_paid = editForm.is_paid
      if (editForm.is_invoiced !== (songDetails.is_invoiced || 'N/A')) payload.is_invoiced = editForm.is_invoiced
      if (editForm.is_registered_with_dsp !== (songDetails.is_registered_with_dsp || 'N/A')) payload.is_registered_with_dsp = editForm.is_registered_with_dsp

      if (Object.keys(payload).length === 0) {
        setIsEditing(false)
        return
      }

      if (!payload.title && !songDetails.title) {
        setEditFeedback({ type: 'error', message: 'Title is required' })
        setSaving(false)
        return
      }
      if (payload.title === '') {
        setEditFeedback({ type: 'error', message: 'Title cannot be empty' })
        setSaving(false)
        return
      }

      await axios.patch(`/api/songs/${songDetails.id}`, payload, {
        headers: { 'Authorization': `Bearer ${token}` }
      })

      await loadSongDetails()
      setIsEditing(false)
      setEditFeedback({ type: 'success', message: 'Song updated successfully' })
      if (onSongUpdated) onSongUpdated()
      setTimeout(() => setEditFeedback(null), 3000)
    } catch (error) {
      console.error('Failed to update song:', error)
      setEditFeedback({ type: 'error', message: error.response?.data?.detail || 'Failed to update song' })
    } finally {
      setSaving(false)
    }
  }

  function handleEditChange(field, value) {
    setEditForm(prev => ({ ...prev, [field]: value }))
  }
  
  const getStatusIcon = (value) => {
    const strVal = String(value ?? '').toLowerCase()
    if (strVal === 'yes' || strVal === 'true' || value === true) return <CheckCircleIcon className="w-5 h-5 text-[#5B9A6E]" />
    if (strVal === 'no' || strVal === 'false' || value === false) return <XCircleIcon className="w-5 h-5 text-[#C47068]" />
    if (value && strVal !== 'n/a' && strVal !== '') {
      const num = parseFloat(value)
      if (!isNaN(num)) {
        return (
          <span className="inline-flex items-center gap-1 text-[13px] font-medium text-[#5B9A6E]">
            <CheckCircleIcon className="w-5 h-5" />
            ${num.toLocaleString()}
          </span>
        )
      }
    }
    return <MinusCircleIcon className="w-5 h-5 text-[#7A8580]" />
  }

  const DollarOrNAInput = ({ value, onChange }) => {
    const isNA = value === 'N/A'
    const displayVal = (value === 'true' || value === true) ? '' : (value === 'false' || value === false) ? '' : value
    return (
      <div className="flex items-center gap-1 mt-1">
        {isNA ? (
          <button
            type="button"
            onClick={() => onChange('')}
            className="w-full px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-[10px] text-sm bg-[#F5F7F4] text-[#7A8580] hover:bg-[#EEF1EC] transition-colors text-center"
          >
            N/A
          </button>
        ) : (
          <div className="flex items-center gap-1 w-full">
            <div className="relative flex-1">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-[#7A8580] text-[15px] font-medium">$</span>
              <input
                type="number"
                min="0"
                step="0.01"
                value={displayVal}
                onChange={(e) => onChange(e.target.value)}
                className="w-full pl-7 pr-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-[10px] text-[#3D4A44] text-[15px] focus:outline-none focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                placeholder="Amount"
              />
            </div>
            <button
              type="button"
              onClick={() => onChange('N/A')}
              className="px-2 py-2 text-xs font-medium text-[#7A8580] hover:text-[#5B8A72] hover:bg-[#F5F7F4] rounded-lg transition-colors whitespace-nowrap border border-transparent hover:border-[rgba(0,0,0,0.1)]"
              title="Set to N/A"
            >
              N/A
            </button>
          </div>
        )}
      </div>
    )
  }
  
  const formatCurrency = (cents) => {
    if (!cents) return '$0.00'
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(cents / 100)
  }
  
  const formatNumber = (num) => {
    if (!num) return '0'
    return new Intl.NumberFormat('en-US').format(num)
  }
  
  if (loading || !songDetails) {
    return (
      <div className="fixed inset-0 bg-black/20 backdrop-blur-sm z-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-[18px] p-8 shadow-[0px_4px_12px_rgba(0,0,0,0.08)]">
          <div className="text-[#7A8580]">Loading song details...</div>
        </div>
      </div>
    )
  }
  
  return (
    <div className="fixed inset-0 bg-black/20 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div 
        className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] max-w-6xl w-full max-h-[90vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-6 border-b border-[rgba(59,77,67,0.08)] bg-white">
          {editFeedback && (
            <div className={`mb-4 px-4 py-3 rounded-[12px] text-[14px] font-medium ${
              editFeedback.type === 'success' 
                ? 'bg-[rgba(91,154,110,0.12)] text-[#5B9A6E] border border-[rgba(91,154,110,0.2)]' 
                : 'bg-[rgba(196,112,104,0.12)] text-[#C47068] border border-[rgba(196,112,104,0.2)]'
            }`}>
              {editFeedback.message}
            </div>
          )}
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <h2 className="text-[28px] font-semibold text-[#3D4A44] mb-2 leading-tight">{songDetails.title}</h2>
              <p className="text-[17px] text-[#7A8580] mb-3">{songDetails.primary_artist}</p>
              <div className="flex flex-wrap gap-2">
                {songDetails.is_released && (
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-[13px] font-medium bg-[rgba(91,154,110,0.15)] text-[#5B9A6E]">
                    Released
                  </span>
                )}
                {!songDetails.is_released && (
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-[13px] font-medium bg-[rgba(196,149,107,0.15)] text-[#C4956B]">
                    Unreleased
                  </span>
                )}
                {songDetails.payment_status === 'PAID' && (
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-[13px] font-medium bg-[rgba(90,138,154,0.15)] text-[#5A8A9A]">
                    Paid
                  </span>
                )}
                {songDetails.label && (
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-[13px] font-medium bg-[rgba(91,138,114,0.15)] text-[#5B8A72]">
                    {songDetails.label}
                  </span>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2">
              {!isEditing && (
                <button
                  onClick={startEditing}
                  className="flex items-center gap-1.5 px-4 py-2 text-[#5B8A72] hover:bg-[rgba(91,138,114,0.08)] rounded-[12px] font-medium text-[14px] transition-colors"
                >
                  <PencilSquareIcon className="w-5 h-5" />
                  <span>Edit</span>
                </button>
              )}
              <button
                onClick={onClose}
                className="text-[#7A8580] hover:text-[#3D4A44] transition-colors"
              >
                <XMarkIcon className="w-7 h-7" />
              </button>
            </div>
          </div>
        </div>
        
        <div className="border-b border-[rgba(59,77,67,0.08)] px-6 bg-white">
          <div className="flex space-x-8">
            {[
              { id: 'overview', label: 'Overview', icon: MusicalNoteIcon },
              { id: 'rights', label: 'Rights & Splits', icon: ScaleIcon },
              { id: 'placement', label: 'Placement Status', icon: DocumentTextIcon },
              { id: 'streaming', label: 'Streaming & Valuation', icon: ChartBarIcon },
              { id: 'links', label: 'Credits & Links', icon: LinkIcon }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center space-x-2 py-4 px-1 border-b-2 font-medium text-[15px] transition-colors ${
                  activeTab === tab.id
                    ? 'border-[#5B8A72] text-[#5B8A72]'
                    : 'border-transparent text-[#7A8580] hover:text-[#3D4A44]'
                }`}
              >
                <tab.icon className="w-5 h-5" />
                <span>{tab.label}</span>
              </button>
            ))}
          </div>
        </div>
        
        <div className="flex-1 overflow-y-auto p-6 bg-[#F5F7F4]">
          {activeTab === 'overview' && (
            <div className="space-y-6">
              {isEditing && (
                <div className="flex items-center justify-end gap-3">
                  <button
                    onClick={cancelEditing}
                    disabled={saving}
                    className="px-4 py-2 text-[#7A8580] hover:text-[#3D4A44] font-medium text-[14px] rounded-[12px] hover:bg-white transition-colors disabled:opacity-50"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={saveEdits}
                    disabled={saving}
                    className="px-5 py-2 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-[12px] font-medium text-[14px] hover:shadow-[0px_4px_12px_rgba(91,138,114,0.3)] transition-all disabled:opacity-50"
                  >
                    {saving ? 'Saving...' : 'Save Changes'}
                  </button>
                </div>
              )}
              <div className="grid grid-cols-2 gap-6">
                <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-5 space-y-4">
                  <h3 className="text-[17px] font-semibold text-[#3D4A44] mb-4">Basic Information</h3>
                  <div>
                    <label className="text-[13px] font-medium text-[#7A8580]">Title</label>
                    {isEditing ? (
                      <input
                        type="text"
                        value={editForm.title}
                        onChange={(e) => handleEditChange('title', e.target.value)}
                        className="w-full mt-1 px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-[10px] text-[#3D4A44] text-[15px] focus:outline-none focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                      />
                    ) : (
                      <p className="text-[#3D4A44]">{songDetails.title}</p>
                    )}
                  </div>
                  <div>
                    <label className="text-[13px] font-medium text-[#7A8580]">Primary Artist</label>
                    {isEditing ? (
                      <input
                        type="text"
                        value={editForm.primary_artist}
                        onChange={(e) => handleEditChange('primary_artist', e.target.value)}
                        className="w-full mt-1 px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-[10px] text-[#3D4A44] text-[15px] focus:outline-none focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                      />
                    ) : (
                      <p className="text-[#3D4A44]">{songDetails.primary_artist}</p>
                    )}
                  </div>
                  <div className="col-span-full">
                    <label className="text-[13px] font-medium text-[#7A8580] mb-1 block">Clients</label>
                    <div className="space-y-2">
                      {songDetails.credits && songDetails.credits.length > 0 ? (
                        songDetails.credits.map((credit) => (
                          <div key={credit.id} className="flex items-center justify-between p-2 bg-[#F5F7F4] rounded-[10px]">
                            <Link
                              to={`/roster/${credit.creator_id}`}
                              onClick={onClose}
                              className="flex items-center gap-2 text-[#5B8A72] hover:text-[#7BA594]"
                            >
                              <UserIcon className="w-4 h-4" />
                              <span className="font-medium text-sm">{credit.creator_name || credit.creator?.display_name || 'Unknown'}</span>
                              <span className="text-xs text-[#7A8580]">({credit.role})</span>
                            </Link>
                            <button
                              onClick={async () => {
                                if (!confirm(`Remove ${credit.creator_name || credit.creator?.display_name || 'this client'} from this song?`)) return
                                try {
                                  await axios.delete(`/api/songs/${song.id}/credits/${credit.id}`)
                                  await loadSongDetails()
                                  if (onSongUpdated) onSongUpdated()
                                } catch (err) {
                                  console.error('Failed to remove credit:', err)
                                  alert('Failed to remove client')
                                }
                              }}
                              className="p-1 text-[#7A8580] hover:text-red-500 rounded-lg hover:bg-red-50 transition-colors"
                              title="Remove client"
                            >
                              <XMarkIcon className="w-4 h-4" />
                            </button>
                          </div>
                        ))
                      ) : (
                        <p className="text-[#7A8580] text-sm">No clients assigned</p>
                      )}
                      {showAddClient ? (
                        <div className="flex items-center gap-2">
                          <select
                            value={addClientCreatorId}
                            onChange={(e) => setAddClientCreatorId(e.target.value)}
                            className="flex-1 px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-[10px] text-sm text-[#3D4A44] bg-white focus:outline-none focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                          >
                            <option value="">Select a client...</option>
                            {splitCreators
                              .filter(c => !songDetails.credits?.some(cr => cr.creator_id === c.id))
                              .map(c => (
                                <option key={c.id} value={c.id}>{c.display_name}</option>
                              ))
                            }
                          </select>
                          <select
                            value={addClientRole}
                            onChange={(e) => setAddClientRole(e.target.value)}
                            className="px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-[10px] text-sm text-[#3D4A44] bg-white focus:outline-none focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                          >
                            <option value="PRIMARY_ARTIST">Primary Artist</option>
                            <option value="FEATURED_ARTIST">Featured Artist</option>
                            <option value="SONGWRITER">Songwriter</option>
                            <option value="PRODUCER">Producer</option>
                            <option value="COMPOSER">Composer</option>
                            <option value="LYRICIST">Lyricist</option>
                          </select>
                          <button
                            onClick={async () => {
                              if (!addClientCreatorId) return
                              try {
                                await axios.post(`/api/songs/${song.id}/credits`, {
                                  creator_id: parseInt(addClientCreatorId),
                                  role: addClientRole
                                })
                                setAddClientCreatorId('')
                                setShowAddClient(false)
                                await loadSongDetails()
                                if (onSongUpdated) onSongUpdated()
                              } catch (err) {
                                console.error('Failed to add credit:', err)
                                alert(err.response?.data?.detail || 'Failed to add client')
                              }
                            }}
                            disabled={!addClientCreatorId}
                            className="px-3 py-2 bg-[#5B8A72] text-white rounded-[10px] text-sm font-medium hover:bg-[#4A7A62] transition-colors disabled:opacity-50"
                          >
                            Add
                          </button>
                          <button
                            onClick={() => { setShowAddClient(false); setAddClientCreatorId('') }}
                            className="p-2 text-[#7A8580] hover:text-[#3D4A44] rounded-[10px] hover:bg-[#EEF1EC] transition-colors"
                          >
                            <XMarkIcon className="w-4 h-4" />
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => setShowAddClient(true)}
                          disabled={!songDetails || splitCreators.length === 0}
                          className="flex items-center gap-1.5 text-sm text-[#5B8A72] hover:text-[#4A7A62] font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                          title={splitCreators.length === 0 ? 'Add creators to your roster first' : 'Add a client to this song'}
                        >
                          <PlusIcon className="w-4 h-4" />
                          Add Client
                        </button>
                      )}
                    </div>
                  </div>
                  <div>
                    <label className="text-[13px] font-medium text-[#7A8580]">Project/Album</label>
                    {isEditing ? (
                      <input
                        type="text"
                        value={editForm.project_title}
                        onChange={(e) => handleEditChange('project_title', e.target.value)}
                        className="w-full mt-1 px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-[10px] text-[#3D4A44] text-[15px] focus:outline-none focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                      />
                    ) : (
                      <p className="text-[#3D4A44]">{songDetails.project_title || 'N/A'}</p>
                    )}
                  </div>
                  <div>
                    <label className="text-[13px] font-medium text-[#7A8580]">Label</label>
                    {isEditing ? (
                      <input
                        type="text"
                        value={editForm.label}
                        onChange={(e) => handleEditChange('label', e.target.value)}
                        className="w-full mt-1 px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-[10px] text-[#3D4A44] text-[15px] focus:outline-none focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                      />
                    ) : (
                      <p className="text-[#3D4A44]">{songDetails.label || 'N/A'}</p>
                    )}
                  </div>
                  <div>
                    <label className="text-[13px] font-medium text-[#7A8580]">Release Date</label>
                    {isEditing ? (
                      <input
                        type="date"
                        value={editForm.release_date}
                        onChange={(e) => handleEditChange('release_date', e.target.value)}
                        className="w-full mt-1 px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-[10px] text-[#3D4A44] text-[15px] focus:outline-none focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                      />
                    ) : (
                      <p className="text-[#3D4A44]">{songDetails.release_date || 'N/A'}</p>
                    )}
                  </div>
                  <div>
                    <label className="text-[13px] font-medium text-[#7A8580]">Media URL</label>
                    {isEditing ? (
                      <input
                        type="url"
                        value={editForm.media_url}
                        onChange={(e) => handleEditChange('media_url', e.target.value)}
                        placeholder="https://..."
                        className="w-full mt-1 px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-[10px] text-[#3D4A44] text-[15px] focus:outline-none focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                      />
                    ) : songDetails.media_url ? (
                      <a 
                        href={songDetails.media_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center space-x-2 text-[#5B8A72] hover:text-[#7BA594] mt-1"
                      >
                        <PlayIcon className="w-5 h-5" />
                        <span>Listen / Download</span>
                      </a>
                    ) : (
                      <p className="text-[#7A8580]">N/A</p>
                    )}
                  </div>
                </div>
                
                <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-5 space-y-4">
                  <h3 className="text-[17px] font-semibold text-[#3D4A44] mb-4">Metadata</h3>
                  <div>
                    <label className="text-[13px] font-medium text-[#7A8580]">ISRC</label>
                    {isEditing ? (
                      <input
                        type="text"
                        value={editForm.isrc}
                        onChange={(e) => handleEditChange('isrc', e.target.value)}
                        placeholder="e.g. USRC17607839"
                        className="w-full mt-1 px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-[10px] text-[#3D4A44] text-[15px] font-mono focus:outline-none focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                      />
                    ) : (
                      <p className="text-[#3D4A44] font-mono">{songDetails.isrc || 'N/A'}</p>
                    )}
                  </div>
                  <div>
                    <label className="text-[13px] font-medium text-[#7A8580]">ISWC</label>
                    {isEditing ? (
                      <input
                        type="text"
                        value={editForm.iswc}
                        onChange={(e) => handleEditChange('iswc', e.target.value)}
                        placeholder="e.g. T-345246800-1"
                        className="w-full mt-1 px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-[10px] text-[#3D4A44] text-[15px] font-mono focus:outline-none focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                      />
                    ) : (
                      <p className="text-[#3D4A44] font-mono">{songDetails.iswc || 'N/A'}</p>
                    )}
                  </div>
                  <div>
                    <label className="text-[13px] font-medium text-[#7A8580]">Recording Code</label>
                    {isEditing ? (
                      <input
                        type="text"
                        value={editForm.recording_code}
                        onChange={(e) => handleEditChange('recording_code', e.target.value)}
                        className="w-full mt-1 px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-[10px] text-[#3D4A44] text-[15px] font-mono focus:outline-none focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                      />
                    ) : (
                      <p className="text-[#3D4A44] font-mono">{songDetails.recording_code || 'N/A'}</p>
                    )}
                  </div>
                  <div>
                    <label className="text-[13px] font-medium text-[#7A8580]">Health Score</label>
                    <div className="flex items-center space-x-3 mt-1">
                      <div className="flex-1 h-2 bg-[#EEF1EC] rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-gradient-to-r from-[#5B8A72] to-[#7BA594]"
                          style={{ width: `${songDetails.status_health_score || 0}%` }}
                        ></div>
                      </div>
                      <span className="text-[13px] font-semibold text-[#3D4A44]">
                        {Math.round(songDetails.status_health_score || 0)}%
                      </span>
                    </div>
                  </div>
                  <div>
                    <label className="text-[13px] font-medium text-[#7A8580]">Publishing %</label>
                    {isEditing ? (
                      <input
                        type="number"
                        min="0"
                        max="100"
                        step="0.01"
                        value={editForm.publishing_percentage}
                        onChange={(e) => handleEditChange('publishing_percentage', e.target.value)}
                        className="w-full mt-1 px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-[10px] text-[#3D4A44] text-[15px] focus:outline-none focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                      />
                    ) : (
                      <p className="text-[#3D4A44]">{songDetails.publishing_percentage != null ? `${songDetails.publishing_percentage}%` : 'N/A'}</p>
                    )}
                  </div>
                  <div>
                    <label className="text-[13px] font-medium text-[#7A8580]">Master %</label>
                    {isEditing ? (
                      <input
                        type="number"
                        min="0"
                        max="100"
                        step="0.01"
                        value={editForm.master_percentage}
                        onChange={(e) => handleEditChange('master_percentage', e.target.value)}
                        className="w-full mt-1 px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-[10px] text-[#3D4A44] text-[15px] focus:outline-none focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                      />
                    ) : (
                      <p className="text-[#3D4A44]">{songDetails.master_percentage != null ? `${songDetails.master_percentage}%` : 'N/A'}</p>
                    )}
                  </div>
                  <div>
                    <label className="text-[13px] font-medium text-[#7A8580]">Advance Amount ($)</label>
                    {isEditing ? (
                      <input
                        type="number"
                        min="0"
                        value={editForm.advance_amount}
                        onChange={(e) => handleEditChange('advance_amount', e.target.value)}
                        className="w-full mt-1 px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-[10px] text-[#3D4A44] text-[15px] focus:outline-none focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                      />
                    ) : (
                      <p className="text-[#3D4A44]">{songDetails.advance_amount != null ? `$${songDetails.advance_amount.toLocaleString()}` : 'N/A'}</p>
                    )}
                  </div>
                  <div>
                    <label className="text-[13px] font-medium text-[#7A8580]">Contract Location</label>
                    {isEditing ? (
                      <input
                        type="text"
                        value={editForm.contract_location}
                        onChange={(e) => handleEditChange('contract_location', e.target.value)}
                        className="w-full mt-1 px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-[10px] text-[#3D4A44] text-[15px] focus:outline-none focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                      />
                    ) : (
                      <p className="text-[#3D4A44]">{songDetails.contract_location || 'N/A'}</p>
                    )}
                  </div>
                  <div>
                    <label className="text-[13px] font-medium text-[#7A8580]">Payment Status</label>
                    {isEditing ? (
                      <select
                        value={editForm.payment_status}
                        onChange={(e) => handleEditChange('payment_status', e.target.value)}
                        className="w-full mt-1 px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-[10px] text-[#3D4A44] text-[15px] focus:outline-none focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white"
                      >
                        <option value="PENDING">Pending</option>
                        <option value="INVOICED">Invoiced</option>
                        <option value="PAID">Paid</option>
                        <option value="OVERDUE">Overdue</option>
                      </select>
                    ) : (
                      <p className="text-[#3D4A44]">{songDetails.payment_status || 'N/A'}</p>
                    )}
                  </div>
                  <div>
                    <label className="text-[13px] font-medium text-[#7A8580]">Paid</label>
                    {isEditing ? (
                      <select
                        value={editForm.is_paid}
                        onChange={(e) => handleEditChange('is_paid', e.target.value)}
                        className="w-full mt-1 px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-[10px] text-[#3D4A44] text-[15px] focus:outline-none focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white"
                      >
                        <option value="N/A">N/A</option>
                        <option value="Yes">Yes</option>
                        <option value="No">No</option>
                      </select>
                    ) : (
                      <p className="text-[#3D4A44]">{songDetails.is_paid || 'N/A'}</p>
                    )}
                  </div>
                  <div>
                    <label className="text-[13px] font-medium text-[#7A8580]">Advance</label>
                    {isEditing ? (
                      <DollarOrNAInput
                        value={editForm.is_invoiced}
                        onChange={(val) => handleEditChange('is_invoiced', val)}
                      />
                    ) : (
                      <p className="text-[#3D4A44]">{songDetails.is_invoiced || 'N/A'}</p>
                    )}
                  </div>
                  <div>
                    <label className="text-[13px] font-medium text-[#7A8580]">Fee</label>
                    {isEditing ? (
                      <DollarOrNAInput
                        value={editForm.is_registered_with_dsp}
                        onChange={(val) => handleEditChange('is_registered_with_dsp', val)}
                      />
                    ) : (
                      <p className="text-[#3D4A44]">{songDetails.is_registered_with_dsp || 'N/A'}</p>
                    )}
                  </div>
                </div>
                
                <div className="col-span-2 bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-5">
                  <h3 className="text-[17px] font-semibold text-[#3D4A44] mb-2">Notes</h3>
                  {isEditing ? (
                    <textarea
                      value={editForm.notes}
                      onChange={(e) => handleEditChange('notes', e.target.value)}
                      rows={4}
                      placeholder="Add notes about this song..."
                      className="w-full px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-[10px] text-[#3D4A44] text-[15px] focus:outline-none focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent resize-y"
                    />
                  ) : songDetails.notes ? (
                    <div className="bg-[rgba(196,149,107,0.08)] border border-[rgba(196,149,107,0.15)] rounded-[12px] p-4">
                      <p className="text-[15px] text-[#3D4A44] whitespace-pre-wrap">{songDetails.notes}</p>
                    </div>
                  ) : (
                    <p className="text-[#7A8580] text-[15px]">No notes added</p>
                  )}
                </div>
              </div>
              {isEditing && (
                <div className="flex items-center justify-end gap-3">
                  <button
                    onClick={cancelEditing}
                    disabled={saving}
                    className="px-4 py-2 text-[#7A8580] hover:text-[#3D4A44] font-medium text-[14px] rounded-[12px] hover:bg-white transition-colors disabled:opacity-50"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={saveEdits}
                    disabled={saving}
                    className="px-5 py-2 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-[12px] font-medium text-[14px] hover:shadow-[0px_4px_12px_rgba(91,138,114,0.3)] transition-all disabled:opacity-50"
                  >
                    {saving ? 'Saving...' : 'Save Changes'}
                  </button>
                </div>
              )}
            </div>
          )}
          
          {activeTab === 'rights' && (
            <div className="space-y-6">
              <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-5">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-[17px] font-semibold text-[#3D4A44]">Song Splits</h3>
                  <div className="flex items-center space-x-2">
                    {songSplits.length > 0 && (
                      <button
                        onClick={handleDownloadSplitSheet}
                        className="flex items-center space-x-1 px-3 py-1.5 border border-[rgba(59,77,67,0.12)] text-[#3D4A44] rounded-lg hover:bg-[#EEF1EC] transition-colors text-sm"
                      >
                        <ArrowDownTrayIcon className="w-4 h-4" />
                        <span>Split Sheet PDF</span>
                      </button>
                    )}
                    <button
                      onClick={() => setShowSplitForm(true)}
                      className="flex items-center space-x-1 px-3 py-1.5 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] transition-colors text-sm"
                    >
                      <PlusIcon className="w-4 h-4" />
                      <span>Add Split</span>
                    </button>
                  </div>
                </div>

                {showSplitForm && (
                  <div className="mb-4 p-4 bg-[#F5F7F4] rounded-[12px] space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-medium text-[#7A8580] mb-1">Rights Holder</label>
                        <select
                          value={splitForm.rights_holder_id}
                          onChange={(e) => setSplitForm(prev => ({ ...prev, rights_holder_id: e.target.value, rights_holder_name: e.target.value ? '' : prev.rights_holder_name }))}
                          className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                        >
                          <option value="">Select from roster...</option>
                          {splitCreators.map(c => (
                            <option key={c.id} value={c.id}>{c.display_name}</option>
                          ))}
                        </select>
                        {!splitForm.rights_holder_id && (
                          <input
                            type="text"
                            placeholder="Or type external contributor name"
                            value={splitForm.rights_holder_name}
                            onChange={(e) => setSplitForm(prev => ({ ...prev, rights_holder_name: e.target.value }))}
                            className="w-full mt-2 border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                          />
                        )}
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-[#7A8580] mb-1">Rights Type</label>
                        <select
                          value={splitForm.rights_type}
                          onChange={(e) => setSplitForm(prev => ({ ...prev, rights_type: e.target.value }))}
                          className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                        >
                          <option value="PUBLISHING">Publishing</option>
                          <option value="MASTER">Master</option>
                          <option value="PERFORMANCE">Performance</option>
                          <option value="MECHANICAL">Mechanical</option>
                          <option value="DISTRIBUTION">Distribution</option>
                          <option value="SYNC">Sync</option>
                          <option value="OTHER">Other</option>
                        </select>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-medium text-[#7A8580] mb-1">Share Percentage</label>
                        <input
                          type="number"
                          placeholder="e.g. 50"
                          value={splitForm.share_percentage}
                          onChange={(e) => setSplitForm(prev => ({ ...prev, share_percentage: e.target.value }))}
                          className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                          min="0" max="100" step="0.1"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-[#7A8580] mb-1">Notes</label>
                        <input
                          type="text"
                          placeholder="Optional notes"
                          value={splitForm.notes}
                          onChange={(e) => setSplitForm(prev => ({ ...prev, notes: e.target.value }))}
                          className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                        />
                      </div>
                    </div>
                    <div className="flex justify-end space-x-2">
                      <button
                        onClick={() => { setShowSplitForm(false); setSplitForm({ rights_holder_id: '', rights_holder_name: '', rights_type: 'PUBLISHING', share_percentage: '', notes: '' }) }}
                        className="px-4 py-2 text-sm text-[#7A8580] border border-[rgba(59,77,67,0.12)] rounded-lg hover:bg-[#EEF1EC] transition-colors"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleAddSongSplit}
                        disabled={splitSaving || (!splitForm.rights_holder_id && !splitForm.rights_holder_name) || !splitForm.share_percentage}
                        className="px-4 py-2 text-sm bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] transition-colors disabled:opacity-50"
                      >
                        {splitSaving ? 'Saving...' : 'Save Split'}
                      </button>
                    </div>
                  </div>
                )}

                {songSplits.length > 0 ? (
                  <div className="space-y-2">
                    <div className="grid grid-cols-5 gap-4 px-3 py-2 text-[12px] font-medium text-[#7A8580] uppercase tracking-wider">
                      <span>Rights Holder</span>
                      <span>Rights Type</span>
                      <span>Share</span>
                      <span>Notes</span>
                      <span></span>
                    </div>
                    {songSplits.map((split) => (
                      <div key={split.id} className="grid grid-cols-5 gap-4 px-3 py-3 bg-[#F5F7F4] rounded-[12px] items-center">
                        <span className="font-medium text-[#3D4A44] text-[14px]">{split.rights_holder_name}</span>
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[12px] font-medium w-fit ${
                          split.rights_type === 'MASTER' ? 'bg-purple-50 text-purple-600' :
                          split.rights_type === 'PUBLISHING' ? 'bg-blue-50 text-blue-600' :
                          split.rights_type === 'PERFORMANCE' ? 'bg-amber-50 text-amber-600' :
                          split.rights_type === 'MECHANICAL' ? 'bg-indigo-50 text-indigo-600' :
                          'bg-gray-50 text-gray-600'
                        }`}>
                          {split.rights_type}
                        </span>
                        <div className="flex items-center gap-2">
                          <div className="flex-1 h-2 bg-[#EEF1EC] rounded-full overflow-hidden max-w-[80px]">
                            <div className="h-full bg-gradient-to-r from-[#5B8A72] to-[#7BA594] rounded-full" style={{ width: `${Math.min(split.share_percentage, 100)}%` }}></div>
                          </div>
                          <span className="text-[14px] font-semibold text-[#3D4A44]">{split.share_percentage}%</span>
                        </div>
                        <span className="text-[13px] text-[#7A8580] truncate">{split.notes || '-'}</span>
                        <div className="flex justify-end">
                          <button onClick={() => handleDeleteSongSplit(split.id)} className="p-1 text-[#7A8580] hover:text-[#C47068] rounded transition-colors" title="Remove split">
                            <TrashIcon className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : !showSplitForm ? (
                  <div className="text-center py-6 bg-[#F5F7F4] rounded-[12px]">
                    <ScaleIcon className="w-10 h-10 text-[#7A8580] mx-auto mb-2" />
                    <p className="text-[#3D4A44] font-medium text-sm">No splits defined yet</p>
                    <p className="text-[12px] text-[#7A8580] mt-1">Click "Add Split" to define ownership percentages</p>
                  </div>
                ) : null}
              </div>

              {rightsData.length > 0 && (
                <div>
                  <h3 className="text-[13px] font-semibold text-[#7A8580] uppercase tracking-wide mb-3">Contract-Based Splits</h3>
                  {rightsData.map((contractInfo, idx) => (
                    <div key={idx} className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-5 mb-4">
                      <div className="flex items-center justify-between mb-4">
                        <div>
                          <h3 className="text-[17px] font-semibold text-[#3D4A44]">{contractInfo.contract_title}</h3>
                          <div className="flex items-center gap-2 mt-1">
                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[12px] font-medium ${
                              contractInfo.contract_type === 'MASTER' ? 'bg-purple-100 text-purple-700' :
                              contractInfo.contract_type === 'PUBLISHING' ? 'bg-blue-100 text-blue-700' :
                              contractInfo.contract_type === 'SYNC_LICENSE' ? 'bg-teal-100 text-teal-700' :
                              'bg-gray-100 text-gray-700'
                            }`}>
                              {(contractInfo.contract_type || '').replace(/_/g, ' ')}
                            </span>
                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[12px] font-medium ${
                              contractInfo.contract_status === 'ACTIVE' ? 'bg-green-100 text-green-700' :
                              contractInfo.contract_status === 'PENDING' ? 'bg-yellow-100 text-yellow-700' :
                              contractInfo.contract_status === 'EXPIRED' ? 'bg-red-100 text-red-700' :
                              'bg-gray-100 text-gray-700'
                            }`}>
                              {contractInfo.contract_status}
                            </span>
                          </div>
                        </div>
                      </div>
                      {contractInfo.splits && contractInfo.splits.length > 0 ? (
                        <div className="space-y-2">
                          <div className="grid grid-cols-4 gap-4 px-3 py-2 text-[12px] font-medium text-[#7A8580] uppercase tracking-wider">
                            <span>Rights Holder</span>
                            <span>Rights Type</span>
                            <span>Share</span>
                            <span>Notes</span>
                          </div>
                          {contractInfo.splits.map((split, sidx) => (
                            <div key={sidx} className="grid grid-cols-4 gap-4 px-3 py-3 bg-[#F5F7F4] rounded-[12px] items-center">
                              <span className="font-medium text-[#3D4A44] text-[14px]">{split.rights_holder_name}</span>
                              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[12px] font-medium w-fit ${
                                split.rights_type === 'MASTER' ? 'bg-purple-50 text-purple-600' :
                                split.rights_type === 'PUBLISHING' ? 'bg-blue-50 text-blue-600' :
                                split.rights_type === 'PERFORMANCE' ? 'bg-amber-50 text-amber-600' :
                                split.rights_type === 'MECHANICAL' ? 'bg-indigo-50 text-indigo-600' :
                                'bg-gray-50 text-gray-600'
                              }`}>
                                {split.rights_type}
                              </span>
                              <div className="flex items-center gap-2">
                                <div className="flex-1 h-2 bg-[#EEF1EC] rounded-full overflow-hidden max-w-[80px]">
                                  <div className="h-full bg-gradient-to-r from-[#5B8A72] to-[#7BA594] rounded-full" style={{ width: `${Math.min(split.share_percentage, 100)}%` }}></div>
                                </div>
                                <span className="text-[14px] font-semibold text-[#3D4A44]">{split.share_percentage}%</span>
                              </div>
                              <span className="text-[13px] text-[#7A8580] truncate">{split.notes || '-'}</span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-[13px] text-[#7A8580] py-4 text-center bg-[#F5F7F4] rounded-[12px]">No splits defined for this asset yet</p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
          
          {activeTab === 'placement' && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-6">
                <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-5">
                  <h3 className="text-[17px] font-semibold text-[#3D4A44] mb-4">Ownership</h3>
                  <div className="space-y-4">
                    <div>
                      <label className="text-[13px] font-medium text-[#7A8580]">Publishing %</label>
                      <p className="text-[28px] font-semibold text-[#3D4A44]">
                        {songDetails.publishing_percentage 
                          ? `${Math.min(songDetails.publishing_percentage, 100).toFixed(2)}%`
                          : 'N/A'
                        }
                      </p>
                    </div>
                    <div>
                      <label className="text-[13px] font-medium text-[#7A8580]">Master %</label>
                      <p className="text-[28px] font-semibold text-[#3D4A44]">
                        {songDetails.master_percentage 
                          ? `${Math.min(songDetails.master_percentage, 100).toFixed(2)}%`
                          : 'N/A'
                        }
                      </p>
                    </div>
                    <div>
                      <label className="text-[13px] font-medium text-[#7A8580]">Advance</label>
                      <p className="text-[28px] font-semibold text-[#3D4A44]">
                        {songDetails.advance_amount 
                          ? `$${songDetails.advance_amount.toLocaleString()}`
                          : 'N/A'
                        }
                      </p>
                    </div>
                  </div>
                </div>
                
                <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-5">
                  <h3 className="text-[17px] font-semibold text-[#3D4A44] mb-4">Status Checklist</h3>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-[15px] text-[#3D4A44]">Contract Executed</span>
                      {getStatusIcon(songDetails.has_contract_executed)}
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-[15px] text-[#3D4A44]">Contract Location</span>
                      <span className="text-[15px] font-medium text-[#3D4A44]">{songDetails.contract_location || 'N/A'}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-[15px] text-[#3D4A44]">PRO Registered</span>
                      {getStatusIcon(songDetails.is_registered_with_pro)}
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-[15px] text-[#3D4A44]">Fee</span>
                      {getStatusIcon(songDetails.is_registered_with_dsp)}
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-[15px] text-[#3D4A44]">SoundExchange Registered</span>
                      {getStatusIcon(songDetails.soundexchange_registered)}
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-[15px] text-[#3D4A44]">Paid</span>
                      {getStatusIcon(songDetails.is_paid)}
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-[15px] text-[#3D4A44]">Advance</span>
                      {getStatusIcon(songDetails.is_invoiced)}
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-[15px] text-[#3D4A44]">Payment Status</span>
                      <span className={`inline-flex items-center px-3 py-1 rounded-full text-[13px] font-medium ${
                        songDetails.payment_status === 'PAID' 
                          ? 'bg-[rgba(91,154,110,0.15)] text-[#5B9A6E]' 
                          : 'bg-[rgba(0,0,0,0.05)] text-[#7A8580]'
                      }`}>
                        {songDetails.payment_status || 'N/A'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
              
              <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-5">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-[17px] font-semibold text-[#3D4A44]">Contracts & Agreements</h3>
                  <div>
                    <input
                      type="file"
                      ref={fileInputRef}
                      onChange={handleContractUpload}
                      accept=".pdf"
                      className="hidden"
                    />
                    <button
                      onClick={() => fileInputRef.current?.click()}
                      disabled={uploading}
                      className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-[12px] font-medium text-[15px] hover:shadow-[0px_4px_12px_rgba(91,138,114,0.3)] transition-all disabled:opacity-50"
                    >
                      <DocumentArrowUpIcon className="w-5 h-5" />
                      <span>{uploading ? 'Uploading...' : 'Upload Contract'}</span>
                    </button>
                  </div>
                </div>
                
                {linkedContracts.length > 0 && (
                  <div className="mb-4">
                    <h4 className="text-[13px] font-semibold text-[#7A8580] uppercase tracking-wide mb-2">Linked Contracts</h4>
                    <div className="space-y-2">
                      {linkedContracts.map((lc) => (
                        <div key={lc.id} className="flex items-center justify-between p-4 bg-[#F5F7F4] rounded-[12px] border border-[rgba(59,77,67,0.08)]">
                          <div className="flex items-center space-x-3">
                            <DocumentTextIcon className="w-8 h-8 text-[#5B8A72]" />
                            <div>
                              <p className="font-medium text-[#3D4A44]">{lc.title}</p>
                              <p className="text-[13px] text-[#7A8580]">
                                {lc.contract_type || 'Contract'}
                                {lc.reference_number ? ` • ${lc.reference_number}` : ''}
                                {lc.status ? ` • ${lc.status}` : ''}
                              </p>
                              {(lc.start_date || lc.end_date) && (
                                <p className="text-[12px] text-[#7A8580]">
                                  {lc.start_date ? new Date(lc.start_date).toLocaleDateString() : ''}
                                  {lc.start_date && lc.end_date ? ' – ' : ''}
                                  {lc.end_date ? new Date(lc.end_date).toLocaleDateString() : ''}
                                </p>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {contracts.length > 0 || linkedContracts.length === 0 ? (
                  <>
                    {contracts.length > 0 && linkedContracts.length > 0 && (
                      <h4 className="text-[13px] font-semibold text-[#7A8580] uppercase tracking-wide mb-2">Uploaded Documents</h4>
                    )}
                    {contracts.length > 0 ? (
                      <div className="space-y-2">
                        {contracts.map((contract) => (
                          <div key={contract.id} className="flex items-center justify-between p-4 bg-[#F5F7F4] rounded-[12px] border border-[rgba(59,77,67,0.08)]">
                            <div className="flex items-center space-x-3">
                              <DocumentTextIcon className="w-8 h-8 text-[#5B8A72]" />
                              <div>
                                <p className="font-medium text-[#3D4A44]">{contract.file_name}</p>
                                <p className="text-[13px] text-[#7A8580]">
                                  {contract.contract_type || 'Contract'} • {new Date(contract.created_at).toLocaleDateString()}
                                </p>
                              </div>
                            </div>
                            <div className="flex items-center space-x-2">
                              <button
                                onClick={() => downloadContract(contract.id)}
                                className="p-2 text-[#7A8580] hover:text-[#5B8A72] hover:bg-[rgba(91,138,114,0.1)] rounded-[8px] transition-colors"
                                title="Download"
                              >
                                <ArrowDownTrayIcon className="w-5 h-5" />
                              </button>
                              <button
                                onClick={() => handleDeleteContract(contract.id)}
                                className="p-2 text-[#7A8580] hover:text-[#C47068] hover:bg-[rgba(196,112,104,0.1)] rounded-[8px] transition-colors"
                                title="Delete"
                              >
                                <TrashIcon className="w-5 h-5" />
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-8 bg-[#F5F7F4] rounded-[12px] border-2 border-dashed border-[rgba(59,77,67,0.08)]">
                        <DocumentTextIcon className="w-12 h-12 text-[#7A8580] mx-auto mb-3" />
                        <p className="text-[#3D4A44]">No contracts uploaded yet</p>
                        <p className="text-[13px] text-[#7A8580]">Upload a PDF to attach it to this song</p>
                      </div>
                    )}
                  </>
                ) : null}
              </div>
            </div>
          )}
          
          {activeTab === 'streaming' && (
            <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-5">
              <div className="text-center text-[#7A8580] py-12">
                Streaming metrics and valuation data will be displayed here
              </div>
            </div>
          )}
          
          {activeTab === 'links' && (
            <div className="space-y-6">
              <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-5">
                <h3 className="text-[17px] font-semibold text-[#3D4A44] mb-4">Credits</h3>
                {songDetails.credits && songDetails.credits.length > 0 ? (
                  <div className="space-y-2">
                    {songDetails.credits.map((credit, idx) => (
                      <div key={idx} className="flex items-center justify-between p-3 bg-[#F5F7F4] rounded-[12px]">
                        <div>
                          <p className="font-medium text-[#3D4A44]">{credit.creator?.display_name || 'Unknown'}</p>
                          <p className="text-[13px] text-[#7A8580]">{credit.role}</p>
                        </div>
                        <span className="text-[15px] font-medium text-[#3D4A44]">
                          {credit.share_percentage ? `${credit.share_percentage}%` : '-'}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-[#7A8580]">No credits added yet</p>
                )}
              </div>
              
              <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-5">
                <h3 className="text-[17px] font-semibold text-[#3D4A44] mb-4">DSP Links</h3>
                {songDetails.dsp_links && songDetails.dsp_links.length > 0 ? (
                  <div className="space-y-2">
                    {songDetails.dsp_links.map((link, idx) => (
                      <a
                        key={idx}
                        href={link.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center justify-between p-3 bg-[#F5F7F4] rounded-[12px] hover:bg-[#EEF1EC] transition-colors"
                      >
                        <span className="font-medium text-[#3D4A44]">{link.platform}</span>
                        <LinkIcon className="w-5 h-5 text-[#7A8580]" />
                      </a>
                    ))}
                  </div>
                ) : (
                  <p className="text-[#7A8580]">No DSP links added yet</p>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
