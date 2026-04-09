import React, { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import axios from 'axios'
import {
  XMarkIcon, CheckCircleIcon, XCircleIcon, MinusCircleIcon,
  MusicalNoteIcon, ChartBarIcon, DocumentTextIcon, LinkIcon,
  DocumentArrowUpIcon, ArrowDownTrayIcon, TrashIcon, PlayIcon, UserIcon,
  ScaleIcon, PencilSquareIcon, PlusIcon, SpeakerWaveIcon,
  FolderIcon, FolderOpenIcon, ArrowLeftIcon, DocumentDuplicateIcon, ShareIcon,
  ArrowTopRightOnSquareIcon, ExclamationTriangleIcon
} from '@heroicons/react/24/outline'

import ShareModal from './ShareModal'
import useBodyScrollLock from '../hooks/useBodyScrollLock'

export default function SongDetailModal({ song, onClose, onSongUpdated }) {
  useBodyScrollLock(!!song)
  const [activeTab, setActiveTab] = useState('overview')
  const [shareTarget, setShareTarget] = useState(null)
  const [songDetails, setSongDetails] = useState(null)
  const [loading, setLoading] = useState(true)
  const [contracts, setContracts] = useState([])
  const [linkedContracts, setLinkedContracts] = useState([])
  const [uploading, setUploading] = useState(false)
  const [rightsData, setRightsData] = useState([])
  const [rightsLoading, setRightsLoading] = useState(false)
  const [editingField, setEditingField] = useState(null)
  const [editValue, setEditValue] = useState('')
  const [saving, setSaving] = useState(false)
  const [editFeedback, setEditFeedback] = useState(null)
  const [directoryContacts, setDirectoryContacts] = useState([])
  const [splitSearchQuery, setSplitSearchQuery] = useState('')
  const [showSplitSearch, setShowSplitSearch] = useState(false)
  const splitSearchRef = useRef(null)
  const fileInputRef = useRef(null)
  const [songSplits, setSongSplits] = useState([])
  const [showSplitForm, setShowSplitForm] = useState(false)
  const [splitForm, setSplitForm] = useState({ rights_holder_id: '', rights_holder_name: '', rights_type: 'PUBLISHING', share_percentage: '', role: '', contact_id: '', ipi: '', pro: '' })
  const [splitSaving, setSplitSaving] = useState(false)
  const [splitCreators, setSplitCreators] = useState([])
  const [showAddClient, setShowAddClient] = useState(false)
  const [addClientCreatorId, setAddClientCreatorId] = useState('')
  const [addClientRole, setAddClientRole] = useState('PRIMARY_ARTIST')
  const [addClientPubShare, setAddClientPubShare] = useState('')
  const [addClientMasterShare, setAddClientMasterShare] = useState('')
  const [editingCreditId, setEditingCreditId] = useState(null)
  const [editCreditForm, setEditCreditForm] = useState({ role: '', pub_share: '', master_share: '' })
  const [resolvingCreditId, setResolvingCreditId] = useState(null)
  const [resolveCreatorId, setResolveCreatorId] = useState(null)
  const [resolveNewName, setResolveNewName] = useState('')
  const [allCreators, setAllCreators] = useState([])
  const [audioAssets, setAudioAssets] = useState([])
  const [audioLoading, setAudioLoading] = useState(false)
  const [showDropboxPicker, setShowDropboxPicker] = useState(false)
  const [dropboxFiles, setDropboxFiles] = useState([])
  const [dropboxPath, setDropboxPath] = useState('')
  const [dropboxLoading, setDropboxLoading] = useState(false)
  const [selectedFiles, setSelectedFiles] = useState([])
  const [analyzing, setAnalyzing] = useState({})
  const [dropboxConnected, setDropboxConnected] = useState(false)
  const [showAddTag, setShowAddTag] = useState(null)
  const [newTagName, setNewTagName] = useState('')
  const [newTagType, setNewTagType] = useState('MOOD')
  const [showSpotifySearch, setShowSpotifySearch] = useState(false)
  const [spotifyQuery, setSpotifyQuery] = useState('')
  const [spotifyResults, setSpotifyResults] = useState([])
  const [spotifySearching, setSpotifySearching] = useState(false)
  const [spotifyLinking, setSpotifyLinking] = useState(null)
  const [spotifyError, setSpotifyError] = useState(null)
  const [streamingData, setStreamingData] = useState(null)
  const [streamingLoading, setStreamingLoading] = useState(false)
  const streamingRequestRef = useRef(null)
  
  useEffect(() => {
    setActiveTab('overview')
    setStreamingData(null)
    loadSongDetails()
    loadContracts()
    loadLinkedContracts()
    loadRightsData()
    loadSongSplits()
    loadSplitCreators()
    loadDirectoryContacts()
  }, [song.id])

  useEffect(() => {
    function handleClickOutside(e) {
      if (splitSearchRef.current && !splitSearchRef.current.contains(e.target)) {
        setShowSplitSearch(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  useEffect(() => {
    if (activeTab === 'audio') {
      loadAudioAssets()
      checkDropboxStatus()
    }
    if (activeTab === 'streaming') {
      loadStreamingData()
    }
  }, [activeTab, song.id])

  async function loadStreamingData() {
    const requestId = Date.now()
    streamingRequestRef.current = requestId
    setStreamingLoading(true)
    try {
      const token = localStorage.getItem('token')
      const response = await axios.get(`/api/songs/${song.id}/streaming`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (streamingRequestRef.current === requestId) {
        setStreamingData(response.data)
      }
    } catch (error) {
      console.error('Failed to load streaming data:', error)
      if (streamingRequestRef.current === requestId) {
        setStreamingData(null)
      }
    } finally {
      if (streamingRequestRef.current === requestId) {
        setStreamingLoading(false)
      }
    }
  }
  
  async function loadSongDetails() {
    try {
      const token = localStorage.getItem('token')
      const response = await axios.get(`/api/songs/${song.id}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      setSongDetails(response.data)
      const hasUnmatched = response.data.credits?.some(c => c.needs_review)
      if (hasUnmatched && allCreators.length === 0) {
        try {
          const creatorsRes = await axios.get('/api/creators', { headers: { 'Authorization': `Bearer ${token}` } })
          setAllCreators(creatorsRes.data)
        } catch (e) { /* ignore */ }
      }
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
      const orgId = song?.organization_id
      if (orgId) {
        const response = await axios.get(`/api/creators/org/${orgId}`)
        setSplitCreators((response.data || []).filter(c => !c.shared))
      } else {
        const orgResponse = await axios.get('/api/organizations/current')
        const response = await axios.get(`/api/creators/org/${orgResponse.data.id}`)
        setSplitCreators((response.data || []).filter(c => !c.shared))
      }
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
        role: splitForm.role || ''
      }
      if (splitForm.rights_holder_id) {
        payload.rights_holder_id = parseInt(splitForm.rights_holder_id)
        payload.rights_holder_name = splitForm.rights_holder_name
      } else {
        payload.rights_holder_name = splitForm.rights_holder_name
        if (splitForm.contact_id) payload.contact_id = parseInt(splitForm.contact_id)
      }
      if (splitForm.ipi) payload.ipi = splitForm.ipi
      if (splitForm.pro) payload.pro = splitForm.pro
      await axios.post(`/api/rights/song-splits/${song.id}`, payload)
      setSplitForm({ rights_holder_id: '', rights_holder_name: '', rights_type: 'PUBLISHING', share_percentage: '', role: '', contact_id: '', ipi: '', pro: '' })
      setSplitSearchQuery('')
      setShowSplitForm(false)
      loadSongSplits()
      loadRightsData()
      loadDirectoryContacts()
      await loadSongDetails()
      if (onSongUpdated) onSongUpdated()
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
      await loadSongDetails()
      if (onSongUpdated) onSongUpdated()
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

  const [duplicating, setDuplicating] = useState(false)

  async function handleDuplicate() {
    setDuplicating(true)
    try {
      const token = localStorage.getItem('token')
      const res = await axios.post(`/api/songs/${song.id}/duplicate`, {}, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (onSongUpdated) onSongUpdated(res.data, 'duplicate')
      onClose()
    } catch (error) {
      console.error('Failed to duplicate song:', error)
      alert(error.response?.data?.detail || 'Failed to duplicate song')
    } finally {
      setDuplicating(false)
    }
  }

  function startInlineEdit(field, currentValue) {
    setEditingField(field)
    setEditValue(currentValue ?? '')
  }

  async function saveInlineEdit(field, value) {
    if (saving) return
    if (editingField !== field) return

    if (field === 'title' && !value?.trim()) {
      setEditFeedback({ type: 'error', message: 'Title cannot be empty' })
      setTimeout(() => setEditFeedback(null), 2000)
      return
    }

    setEditingField(null)
    const payload = {}

    const numericFields = []
    const intFields = ['advance_amount']

    if (numericFields.includes(field)) {
      const parsed = value === '' ? null : parseFloat(value)
      if (parsed !== null && !Number.isFinite(parsed)) return
      if (parsed === (songDetails[field] ?? null)) return
      payload[field] = parsed
    } else if (intFields.includes(field)) {
      const parsed = value === '' ? null : parseInt(value, 10)
      if (parsed !== null && !Number.isFinite(parsed)) return
      if (parsed === (songDetails[field] ?? null)) return
      payload[field] = parsed
    } else {
      const current = songDetails[field] || ''
      if (value === current) return
      payload[field] = value || null
    }

    setSaving(true)
    try {
      const token = localStorage.getItem('token')
      await axios.patch(`/api/songs/${songDetails.id}`, payload, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      await loadSongDetails()
      if (onSongUpdated) onSongUpdated()
      setEditFeedback({ type: 'success', message: 'Saved' })
      setTimeout(() => setEditFeedback(null), 1500)
    } catch (error) {
      console.error('Failed to update:', error)
      setEditFeedback({ type: 'error', message: error.response?.data?.detail || 'Failed to save' })
      setTimeout(() => setEditFeedback(null), 3000)
    } finally {
      setSaving(false)
    }
  }

  async function saveStatusField(field, value) {
    setSaving(true)
    try {
      const token = localStorage.getItem('token')
      await axios.patch(`/api/songs/${songDetails.id}`, { [field]: value }, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      await loadSongDetails()
      if (onSongUpdated) onSongUpdated()
    } catch (error) {
      console.error('Failed to update:', error)
    } finally {
      setSaving(false)
    }
  }

  function cycleStatusValue(field) {
    const statusNorm = (v) => { if (v == null) return 'N/A'; const s = String(v).toLowerCase(); if (s === 'n/a' || s === 'na') return 'N/A'; if (s === 'true' || s === 'yes') return 'Yes'; if (s === 'false' || s === 'no') return 'No'; return 'N/A' }
    const current = statusNorm(songDetails[field])
    const next = current === 'N/A' ? 'Yes' : current === 'Yes' ? 'No' : 'N/A'
    saveStatusField(field, next)
  }

  async function loadDirectoryContacts() {
    try {
      const orgResponse = await axios.get('/api/organizations/current')
      const res = await axios.get(`/api/creative-directory/org/${orgResponse.data.id}`)
      setDirectoryContacts(res.data.contacts || [])
    } catch (e) {
      console.error('Failed to load directory contacts:', e)
    }
  }

  async function searchSpotify() {
    if (!spotifyQuery.trim()) return
    setSpotifySearching(true)
    setSpotifyError(null)
    try {
      const token = localStorage.getItem('token')
      const response = await axios.post('/api/spotify/search', { query: spotifyQuery, limit: 5 }, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      setSpotifyResults(response.data.results || [])
    } catch (err) {
      console.error('Spotify search failed:', err)
      setSpotifyResults([])
      const detail = err.response?.data?.detail
      if (detail) {
        setSpotifyError(detail)
      } else {
        setSpotifyError('Spotify search failed. Please try again.')
      }
    } finally {
      setSpotifySearching(false)
    }
  }

  async function linkSpotifyTrack(track) {
    setSpotifyLinking(track.spotify_id)
    try {
      const token = localStorage.getItem('token')
      await axios.post('/api/spotify/link-to-song', {
        song_id: song.id,
        spotify_url: track.spotify_url,
        spotify_id: track.spotify_id,
        isrc: track.isrc,
        album_art: track.album_art,
        album_name: track.album_name,
        release_date: track.release_date,
        popularity: track.popularity
      }, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      setShowSpotifySearch(false)
      setSpotifyResults([])
      setSpotifyQuery('')
      await loadSongDetails()
      if (onSongUpdated) onSongUpdated()
    } catch (err) {
      console.error('Failed to link Spotify track:', err)
    } finally {
      setSpotifyLinking(null)
    }
  }

  function openSpotifySearch() {
    const q = songDetails ? `${songDetails.title || ''} ${songDetails.primary_artist || ''}`.trim() : ''
    setSpotifyQuery(q)
    setSpotifyResults([])
    setShowSpotifySearch(true)
  }

  async function loadAudioAssets() {
    setAudioLoading(true)
    try {
      const token = localStorage.getItem('token')
      const response = await axios.get(`/api/audio/song/${song.id}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      setAudioAssets(response.data?.assets || response.data || [])
    } catch (error) {
      console.error('Failed to load audio assets:', error)
      setAudioAssets([])
    } finally {
      setAudioLoading(false)
    }
  }

  async function checkDropboxStatus() {
    try {
      const token = localStorage.getItem('token')
      const response = await axios.get('/api/integrations/status', {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      const dropbox = response.data?.integrations?.find(i => i.provider === 'DROPBOX' || i.provider?.toLowerCase() === 'dropbox')
      setDropboxConnected(!!dropbox)
    } catch (error) {
      console.error('Failed to check Dropbox status:', error)
      setDropboxConnected(false)
    }
  }

  async function browseDropbox(path) {
    setDropboxLoading(true)
    try {
      const token = localStorage.getItem('token')
      const response = await axios.get(`/api/integrations/dropbox/files?path=${encodeURIComponent(path)}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      setDropboxFiles(response.data?.files || response.data?.entries || [])
      setDropboxPath(path)
    } catch (error) {
      console.error('Failed to browse Dropbox:', error)
    } finally {
      setDropboxLoading(false)
    }
  }

  async function linkFile(file) {
    try {
      const token = localStorage.getItem('token')
      await axios.post(`/api/audio/song/${song.id}/link`, {
        provider_file_id: file.id || file.path_display || file.path,
        path_display: file.path_display || file.path,
        name: file.name,
        size_bytes: file.size || file.size_bytes || null,
        file_type: "MAIN",
        mime_type: null,
      }, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      await loadAudioAssets()
    } catch (error) {
      console.error('Failed to link file:', error)
      alert(error.response?.data?.detail || 'Failed to link file')
    }
  }

  async function unlinkFile(assetId) {
    if (!confirm('Unlink this audio file?')) return
    try {
      const token = localStorage.getItem('token')
      await axios.delete(`/api/audio/${assetId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      await loadAudioAssets()
    } catch (error) {
      console.error('Failed to unlink file:', error)
    }
  }

  async function analyzeFile(assetId) {
    setAnalyzing(prev => ({ ...prev, [assetId]: true }))
    try {
      const token = localStorage.getItem('token')
      await axios.post(`/api/audio/${assetId}/analyze`, {}, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      const analysisRes = await axios.get(`/api/audio/${assetId}/analysis`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      setAudioAssets(prev => prev.map(a => a.id === assetId ? { ...a, analysis: analysisRes.data } : a))
    } catch (error) {
      console.error('Failed to analyze file:', error)
      alert(error.response?.data?.detail || 'Failed to analyze file')
    } finally {
      setAnalyzing(prev => ({ ...prev, [assetId]: false }))
    }
  }

  async function addTag(assetId, name, tagType) {
    try {
      const token = localStorage.getItem('token')
      await axios.post(`/api/audio/${assetId}/tags`, { name, tag_type: tagType }, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      const analysisRes = await axios.get(`/api/audio/${assetId}/analysis`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      setAudioAssets(prev => prev.map(a => a.id === assetId ? { ...a, analysis: analysisRes.data } : a))
      setShowAddTag(null)
      setNewTagName('')
      setNewTagType('MOOD')
    } catch (error) {
      console.error('Failed to add tag:', error)
    }
  }

  async function removeTag(assetId, tagId) {
    try {
      const token = localStorage.getItem('token')
      await axios.delete(`/api/audio/${assetId}/tags/${tagId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      const analysisRes = await axios.get(`/api/audio/${assetId}/analysis`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      setAudioAssets(prev => prev.map(a => a.id === assetId ? { ...a, analysis: analysisRes.data } : a))
    } catch (error) {
      console.error('Failed to remove tag:', error)
    }
  }

  async function updateFileType(assetId, fileType) {
    try {
      const token = localStorage.getItem('token')
      await axios.put(`/api/audio/${assetId}/type`, { file_type: fileType }, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      setAudioAssets(prev => prev.map(a => a.id === assetId ? { ...a, file_type: fileType } : a))
    } catch (error) {
      console.error('Failed to update file type:', error)
    }
  }

  function formatFileSize(bytes) {
    if (!bytes) return '—'
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / 1048576).toFixed(1) + ' MB'
  }

  function isAudioFile(filename) {
    const ext = (filename || '').toLowerCase().split('.').pop()
    return ['mp3', 'wav', 'flac', 'aiff', 'm4a', 'ogg'].includes(ext)
  }

  function handleOpenDropboxPicker() {
    setShowDropboxPicker(true)
    setDropboxPath('')
    setSelectedFiles([])
    browseDropbox('')
  }

  function handleSelectFile(file) {
    setSelectedFiles(prev => {
      const exists = prev.find(f => f.path_display === file.path_display || f.path === file.path)
      if (exists) return prev.filter(f => (f.path_display || f.path) !== (file.path_display || file.path))
      return [...prev, file]
    })
  }

  async function handleLinkSelected() {
    for (const file of selectedFiles) {
      await linkFile(file)
    }
    setShowDropboxPicker(false)
    setSelectedFiles([])
  }

  function getTagColor(tagType) {
    switch ((tagType || '').toUpperCase()) {
      case 'MOOD': return 'bg-blue-50 text-blue-700 border-blue-200'
      case 'TEXTURE': return 'bg-purple-50 text-purple-700 border-purple-200'
      case 'SYNC': return 'bg-amber-50 text-amber-700 border-amber-200'
      default: return 'bg-green-50 text-green-700 border-green-200'
    }
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
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 min-w-0">
              <h2 className="text-[20px] sm:text-[28px] font-semibold text-[#3D4A44] mb-2 leading-tight break-words">{songDetails.title}</h2>
              <p className="text-[15px] sm:text-[17px] text-[#7A8580] mb-3">{songDetails.primary_artist}</p>
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
            <div className="flex items-center gap-1 sm:gap-2 flex-shrink-0">
              <button
                onClick={() => setShareTarget({ type: 'SONG', id: song.id, name: `${songDetails?.title || song.title} - ${songDetails?.primary_artist || song.primary_artist}` })}
                className="flex items-center gap-1.5 p-2 sm:px-4 sm:py-2 text-[#5B8A72] hover:bg-[rgba(91,138,114,0.08)] rounded-[12px] font-medium text-[14px] transition-colors"
                title="Share this song"
              >
                <ShareIcon className="w-5 h-5" />
                <span className="hidden sm:inline">Share</span>
              </button>
              <button
                onClick={handleDuplicate}
                disabled={duplicating}
                className="flex items-center gap-1.5 p-2 sm:px-4 sm:py-2 text-[#5A8A9A] hover:bg-[rgba(90,138,154,0.08)] rounded-[12px] font-medium text-[14px] transition-colors disabled:opacity-50"
                title="Duplicate this song"
              >
                <DocumentDuplicateIcon className="w-5 h-5" />
                <span className="hidden sm:inline">{duplicating ? 'Duplicating...' : 'Duplicate'}</span>
              </button>
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
          <div className="flex space-x-8 overflow-x-auto no-scrollbar" style={{ WebkitOverflowScrolling: 'touch', touchAction: 'pan-x' }}>
            {[
              { id: 'overview', label: 'Overview', icon: MusicalNoteIcon },
              { id: 'rights', label: 'Rights & Splits', icon: ScaleIcon },
              { id: 'streaming', label: 'Streaming & Valuation', icon: ChartBarIcon },
              { id: 'links', label: 'Credits & Links', icon: LinkIcon },
              { id: 'audio', label: 'Audio', icon: SpeakerWaveIcon }
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
                <tab.icon className="w-5 h-5 flex-shrink-0" />
                <span className="whitespace-nowrap">{tab.label}</span>
              </button>
            ))}
          </div>
        </div>
        
        <div className="flex-1 overflow-y-auto p-6 bg-[#F5F7F4]" style={{ overscrollBehavior: 'contain', WebkitOverflowScrolling: 'touch' }}>
          {activeTab === 'overview' && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-5 space-y-4">
                  <h3 className="text-[17px] font-semibold text-[#3D4A44] mb-4">Basic Information</h3>
                  <div>
                    <label className="text-[13px] font-medium text-[#7A8580]">Title</label>
                    {editingField === 'title' ? (
                      <input
                        type="text"
                        autoFocus
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        onBlur={() => saveInlineEdit('title', editValue)}
                        onKeyDown={(e) => { if (e.key === 'Enter') saveInlineEdit('title', editValue); if (e.key === 'Escape') setEditingField(null) }}
                        className="w-full mt-1 px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-[10px] text-[#3D4A44] text-[15px] focus:outline-none focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                      />
                    ) : (
                      <p className="group flex items-center gap-1.5 text-[#3D4A44] cursor-pointer hover:bg-[rgba(91,138,114,0.04)] rounded-lg px-1 -mx-1 py-0.5 transition-colors" onClick={() => startInlineEdit('title', songDetails.title)}>
                        <span>{songDetails.title || 'Untitled'}</span>
                        <PencilSquareIcon className="w-3.5 h-3.5 text-[#7A8580] opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                      </p>
                    )}
                  </div>
                  <div>
                    <label className="text-[13px] font-medium text-[#7A8580]">Primary Artist</label>
                    {editingField === 'primary_artist' ? (
                      <input
                        type="text"
                        autoFocus
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        onBlur={() => saveInlineEdit('primary_artist', editValue)}
                        onKeyDown={(e) => { if (e.key === 'Enter') saveInlineEdit('primary_artist', editValue); if (e.key === 'Escape') setEditingField(null) }}
                        className="w-full mt-1 px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-[10px] text-[#3D4A44] text-[15px] focus:outline-none focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                      />
                    ) : (
                      <p className="group flex items-center gap-1.5 text-[#3D4A44] cursor-pointer hover:bg-[rgba(91,138,114,0.04)] rounded-lg px-1 -mx-1 py-0.5 transition-colors" onClick={() => startInlineEdit('primary_artist', songDetails.primary_artist)}>
                        <span>{songDetails.primary_artist || 'N/A'}</span>
                        <PencilSquareIcon className="w-3.5 h-3.5 text-[#7A8580] opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                      </p>
                    )}
                  </div>
                  <div className="col-span-full">
                    <label className="text-[13px] font-medium text-[#7A8580] mb-1 block">Clients</label>
                    <div className="space-y-2">
                      {songDetails.credits && songDetails.credits.length > 0 ? (
                        songDetails.credits.map((credit) => (
                          editingCreditId === credit.id ? (
                            <div key={credit.id} className="p-3 bg-[#F5F7F4] rounded-[10px] space-y-2">
                              <div className="flex items-center gap-2">
                                <UserIcon className="w-4 h-4 text-[#5B8A72]" />
                                <span className={`font-medium text-sm ${credit.creator_name ? 'text-[#3D4A44]' : 'text-amber-600 underline'}`}>{credit.creator_name || 'Unmatched — Review Needed'}</span>
                              </div>
                              <div className="space-y-2 sm:space-y-0 sm:grid sm:grid-cols-3 sm:gap-2">
                                <div>
                                  <label className="text-[11px] text-[#7A8580]">Role</label>
                                  <select
                                    value={editCreditForm.role}
                                    onChange={(e) => setEditCreditForm(prev => ({ ...prev, role: e.target.value }))}
                                    className="w-full px-2 py-1.5 border border-[rgba(59,77,67,0.15)] rounded-[8px] text-xs text-[#3D4A44] bg-white focus:outline-none focus:ring-2 focus:ring-[#5B8A72]"
                                  >
                                    <option value="PRIMARY_ARTIST">Primary Artist</option>
                                    <option value="FEATURED_ARTIST">Featured Artist</option>
                                    <option value="SONGWRITER">Songwriter</option>
                                    <option value="PRODUCER">Producer</option>
                                    <option value="COMPOSER">Composer</option>
                                    <option value="LYRICIST">Lyricist</option>
                                    <option value="ARTIST">Artist</option>
                                  </select>
                                </div>
                                <div>
                                  <label className="text-[11px] text-[#7A8580]">Pub %</label>
                                  <input
                                    type="number"
                                    min="0"
                                    max="100"
                                    step="0.01"
                                    value={editCreditForm.pub_share}
                                    onChange={(e) => setEditCreditForm(prev => ({ ...prev, pub_share: e.target.value }))}
                                    placeholder="—"
                                    className="w-full px-2 py-1.5 border border-[rgba(59,77,67,0.15)] rounded-[8px] text-xs text-[#3D4A44] focus:outline-none focus:ring-2 focus:ring-[#5B8A72]"
                                  />
                                </div>
                                <div>
                                  <label className="text-[11px] text-[#7A8580]">Master %</label>
                                  <input
                                    type="number"
                                    min="0"
                                    max="100"
                                    step="0.01"
                                    value={editCreditForm.master_share}
                                    onChange={(e) => setEditCreditForm(prev => ({ ...prev, master_share: e.target.value }))}
                                    placeholder="—"
                                    className="w-full px-2 py-1.5 border border-[rgba(59,77,67,0.15)] rounded-[8px] text-xs text-[#3D4A44] focus:outline-none focus:ring-2 focus:ring-[#5B8A72]"
                                  />
                                </div>
                              </div>
                              <div className="flex justify-end gap-2">
                                <button
                                  onClick={() => setEditingCreditId(null)}
                                  className="px-3 py-1 text-xs text-[#7A8580] hover:text-[#3D4A44] rounded-[8px] hover:bg-white transition-colors"
                                >
                                  Cancel
                                </button>
                                <button
                                  onClick={async () => {
                                    try {
                                      const payload = { role: editCreditForm.role }
                                      payload.pub_share = editCreditForm.pub_share === '' ? null : parseFloat(editCreditForm.pub_share)
                                      payload.master_share = editCreditForm.master_share === '' ? null : parseFloat(editCreditForm.master_share)
                                      await axios.patch(`/api/songs/${song.id}/credits/${credit.id}`, payload)
                                      setEditingCreditId(null)
                                      await loadSongDetails()
                                      loadSongSplits()
                                      loadRightsData()
                                      if (onSongUpdated) onSongUpdated()
                                    } catch (err) {
                                      console.error('Failed to update credit:', err)
                                      alert(err.response?.data?.detail || 'Failed to update client')
                                    }
                                  }}
                                  className="px-3 py-1 text-xs bg-[#5B8A72] text-white rounded-[8px] font-medium hover:bg-[#4A7A62] transition-colors"
                                >
                                  Save
                                </button>
                              </div>
                            </div>
                          ) : credit.needs_review ? (
                            <div key={credit.id} className="p-3 bg-amber-50 border border-amber-200 rounded-[10px] space-y-2">
                              <div className="flex items-center justify-between">
                                <div className="flex items-center gap-1.5">
                                  <ExclamationTriangleIcon className="w-4 h-4 text-amber-500" />
                                  <span className="font-medium text-sm text-amber-700">"{credit.unmatched_artist_name}" — Unmatched</span>
                                  <span className="text-xs text-[#7A8580]">({credit.role})</span>
                                </div>
                                <button
                                  onClick={async () => {
                                    if (!confirm(`Remove this unmatched credit?`)) return
                                    try {
                                      await axios.delete(`/api/songs/${song.id}/credits/${credit.id}`)
                                      await loadSongDetails()
                                      if (onSongUpdated) onSongUpdated()
                                    } catch (err) {
                                      alert('Failed to remove credit')
                                    }
                                  }}
                                  className="p-1 text-[#7A8580] hover:text-red-500 rounded-lg hover:bg-red-50 transition-colors"
                                  title="Remove"
                                >
                                  <XMarkIcon className="w-4 h-4" />
                                </button>
                              </div>
                              {resolvingCreditId === credit.id ? (
                                <div className="space-y-2">
                                  <select
                                    value={resolveCreatorId || ''}
                                    onChange={(e) => {
                                      setResolveCreatorId(e.target.value ? parseInt(e.target.value) : null)
                                      if (e.target.value) setResolveNewName('')
                                    }}
                                    className="w-full px-2 py-1.5 border border-amber-200 rounded-[8px] text-xs text-[#3D4A44] bg-white focus:outline-none focus:ring-2 focus:ring-amber-400"
                                  >
                                    <option value="">-- Select existing creator --</option>
                                    {allCreators.map(c => (
                                      <option key={c.id} value={c.id}>{c.display_name}</option>
                                    ))}
                                  </select>
                                  <div className="flex items-center gap-2">
                                    <span className="text-xs text-[#7A8580]">or</span>
                                    <input
                                      type="text"
                                      value={resolveNewName}
                                      onChange={(e) => {
                                        setResolveNewName(e.target.value)
                                        if (e.target.value) setResolveCreatorId(null)
                                      }}
                                      placeholder="Create new creator..."
                                      className="flex-1 px-2 py-1.5 border border-amber-200 rounded-[8px] text-xs text-[#3D4A44] focus:outline-none focus:ring-2 focus:ring-amber-400"
                                    />
                                  </div>
                                  <div className="flex gap-2">
                                    <button
                                      onClick={async () => {
                                        try {
                                          const body = resolveCreatorId
                                            ? { creator_id: resolveCreatorId }
                                            : { new_creator_name: resolveNewName }
                                          await axios.post(`/api/songs/${song.id}/credits/${credit.id}/resolve`, body)
                                          setResolvingCreditId(null)
                                          setResolveCreatorId(null)
                                          setResolveNewName('')
                                          await loadSongDetails()
                                          if (onSongUpdated) onSongUpdated()
                                        } catch (err) {
                                          alert(err.response?.data?.detail || 'Failed to resolve')
                                        }
                                      }}
                                      disabled={!resolveCreatorId && !resolveNewName.trim()}
                                      className="px-3 py-1.5 bg-amber-500 text-white text-xs rounded-lg hover:bg-amber-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                    >
                                      Resolve
                                    </button>
                                    <button
                                      onClick={() => { setResolvingCreditId(null); setResolveCreatorId(null); setResolveNewName('') }}
                                      className="px-3 py-1.5 text-[#7A8580] text-xs rounded-lg hover:bg-[rgba(59,77,67,0.06)] transition-colors"
                                    >
                                      Cancel
                                    </button>
                                  </div>
                                </div>
                              ) : (
                                <button
                                  onClick={() => {
                                    setResolvingCreditId(credit.id)
                                    setResolveCreatorId(null)
                                    setResolveNewName(credit.unmatched_artist_name || '')
                                  }}
                                  className="text-xs text-amber-600 hover:text-amber-700 font-medium underline"
                                >
                                  Match to Creator
                                </button>
                              )}
                            </div>
                          ) : (
                            <div key={credit.id} className="flex flex-wrap items-center gap-1.5 sm:gap-2 p-2 bg-[#F5F7F4] rounded-[10px]">
                              <Link
                                to={`/roster/${credit.creator_id}`}
                                onClick={onClose}
                                className="flex items-center gap-1.5 text-[#5B8A72] hover:text-[#7BA594] min-w-0"
                              >
                                <UserIcon className="w-4 h-4 flex-shrink-0" />
                                <span className="font-medium text-sm truncate max-w-[120px] sm:max-w-none">{credit.creator_name}</span>
                              </Link>
                              <span className="text-xs text-[#7A8580] flex-shrink-0">({credit.role})</span>
                              <span className={`text-xs px-1.5 py-0.5 rounded flex-shrink-0 hidden sm:inline ${credit.pub_share != null ? 'text-[#5B8A72] bg-[rgba(91,138,114,0.1)]' : 'text-[#B0BDB4] bg-[rgba(59,77,67,0.04)]'}`}>Pub {credit.pub_share != null ? `${credit.pub_share}%` : '—'}</span>
                              <span className={`text-xs px-1.5 py-0.5 rounded flex-shrink-0 hidden sm:inline ${credit.master_share != null ? 'text-[#5A8A9A] bg-[rgba(90,138,154,0.1)]' : 'text-[#B0BDB4] bg-[rgba(59,77,67,0.04)]'}`}>Master {credit.master_share != null ? `${credit.master_share}%` : '—'}</span>
                              <div className="flex items-center gap-1 ml-auto flex-shrink-0">
                                <button
                                  onClick={() => {
                                    setEditingCreditId(credit.id)
                                    setEditCreditForm({
                                      role: credit.role,
                                      pub_share: credit.pub_share != null ? String(credit.pub_share) : '',
                                      master_share: credit.master_share != null ? String(credit.master_share) : ''
                                    })
                                  }}
                                  className="p-1 text-[#7A8580] hover:text-[#5B8A72] rounded-lg hover:bg-[rgba(91,138,114,0.08)] transition-colors"
                                  title="Edit role & splits"
                                >
                                  <PencilSquareIcon className="w-4 h-4" />
                                </button>
                                <button
                                  onClick={async () => {
                                    if (!confirm(`Remove ${credit.creator_name} from this song?`)) return
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
                            </div>
                          )
                        ))
                      ) : (
                        <p className="text-[#7A8580] text-sm">No clients assigned</p>
                      )}
                      {showAddClient ? (
                        <div className="p-3 bg-[#F5F7F4] rounded-[10px] space-y-2">
                          <select
                            value={addClientCreatorId}
                            onChange={(e) => setAddClientCreatorId(e.target.value)}
                            className="w-full px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-[10px] text-sm text-[#3D4A44] bg-white focus:outline-none focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
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
                            className="w-full px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-[10px] text-sm text-[#3D4A44] bg-white focus:outline-none focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                          >
                            <option value="PRIMARY_ARTIST">Primary Artist</option>
                            <option value="FEATURED_ARTIST">Featured Artist</option>
                            <option value="SONGWRITER">Songwriter</option>
                            <option value="PRODUCER">Producer</option>
                            <option value="COMPOSER">Composer</option>
                            <option value="LYRICIST">Lyricist</option>
                          </select>
                          <div className="grid grid-cols-2 gap-2">
                            <div>
                              <label className="text-[11px] text-[#7A8580]">Pub Split %</label>
                              <input
                                type="number"
                                min="0"
                                max="100"
                                step="0.01"
                                value={addClientPubShare}
                                onChange={(e) => setAddClientPubShare(e.target.value)}
                                placeholder="Optional"
                                className="w-full px-2 py-1.5 border border-[rgba(59,77,67,0.15)] rounded-[8px] text-xs text-[#3D4A44] focus:outline-none focus:ring-2 focus:ring-[#5B8A72]"
                              />
                            </div>
                            <div>
                              <label className="text-[11px] text-[#7A8580]">Master Split %</label>
                              <input
                                type="number"
                                min="0"
                                max="100"
                                step="0.01"
                                value={addClientMasterShare}
                                onChange={(e) => setAddClientMasterShare(e.target.value)}
                                placeholder="Optional"
                                className="w-full px-2 py-1.5 border border-[rgba(59,77,67,0.15)] rounded-[8px] text-xs text-[#3D4A44] focus:outline-none focus:ring-2 focus:ring-[#5B8A72]"
                              />
                            </div>
                          </div>
                          <div className="flex items-center justify-between pt-1">
                            <button
                              onClick={() => { setShowAddClient(false); setAddClientCreatorId(''); setAddClientPubShare(''); setAddClientMasterShare('') }}
                              className="px-3 py-1.5 text-xs text-[#7A8580] hover:text-[#3D4A44] rounded-[8px] hover:bg-white transition-colors"
                            >
                              Cancel
                            </button>
                            <button
                              onClick={async () => {
                                if (!addClientCreatorId) return
                                try {
                                  const payload = {
                                    creator_id: parseInt(addClientCreatorId),
                                    role: addClientRole
                                  }
                                  if (addClientPubShare !== '') payload.pub_share = parseFloat(addClientPubShare)
                                  if (addClientMasterShare !== '') payload.master_share = parseFloat(addClientMasterShare)
                                  await axios.post(`/api/songs/${song.id}/credits`, payload)
                                  setAddClientCreatorId('')
                                  setAddClientPubShare('')
                                  setAddClientMasterShare('')
                                  setShowAddClient(false)
                                  await loadSongDetails()
                                  loadSongSplits()
                                  loadRightsData()
                                  if (onSongUpdated) onSongUpdated()
                                } catch (err) {
                                  console.error('Failed to add credit:', err)
                                  alert(err.response?.data?.detail || 'Failed to add client')
                                }
                              }}
                              disabled={!addClientCreatorId}
                              className="px-4 py-1.5 text-xs bg-[#5B8A72] text-white rounded-[8px] font-medium hover:bg-[#4A7A62] transition-colors disabled:opacity-50"
                            >
                              Add Client
                            </button>
                          </div>
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
                    {editingField === 'project_title' ? (
                      <input
                        type="text"
                        autoFocus
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        onBlur={() => saveInlineEdit('project_title', editValue)}
                        onKeyDown={(e) => { if (e.key === 'Enter') saveInlineEdit('project_title', editValue); if (e.key === 'Escape') setEditingField(null) }}
                        className="w-full mt-1 px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-[10px] text-[#3D4A44] text-[15px] focus:outline-none focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                      />
                    ) : (
                      <p className="group flex items-center gap-1.5 text-[#3D4A44] cursor-pointer hover:bg-[rgba(91,138,114,0.04)] rounded-lg px-1 -mx-1 py-0.5 transition-colors" onClick={() => startInlineEdit('project_title', songDetails.project_title)}>
                        <span>{songDetails.project_title || 'N/A'}</span>
                        <PencilSquareIcon className="w-3.5 h-3.5 text-[#7A8580] opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                      </p>
                    )}
                  </div>
                  <div>
                    <label className="text-[13px] font-medium text-[#7A8580]">Label</label>
                    {editingField === 'label' ? (
                      <input
                        type="text"
                        autoFocus
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        onBlur={() => saveInlineEdit('label', editValue)}
                        onKeyDown={(e) => { if (e.key === 'Enter') saveInlineEdit('label', editValue); if (e.key === 'Escape') setEditingField(null) }}
                        className="w-full mt-1 px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-[10px] text-[#3D4A44] text-[15px] focus:outline-none focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                      />
                    ) : (
                      <p className="group flex items-center gap-1.5 text-[#3D4A44] cursor-pointer hover:bg-[rgba(91,138,114,0.04)] rounded-lg px-1 -mx-1 py-0.5 transition-colors" onClick={() => startInlineEdit('label', songDetails.label)}>
                        <span>{songDetails.label || 'N/A'}</span>
                        <PencilSquareIcon className="w-3.5 h-3.5 text-[#7A8580] opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                      </p>
                    )}
                  </div>
                  <div>
                    <label className="text-[13px] font-medium text-[#7A8580]">Release Date</label>
                    {editingField === 'release_date' ? (
                      <input
                        type="date"
                        autoFocus
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        onBlur={() => saveInlineEdit('release_date', editValue)}
                        onKeyDown={(e) => { if (e.key === 'Enter') saveInlineEdit('release_date', editValue); if (e.key === 'Escape') setEditingField(null) }}
                        className="w-full mt-1 px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-[10px] text-[#3D4A44] text-[15px] focus:outline-none focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                      />
                    ) : (
                      <p className="group flex items-center gap-1.5 text-[#3D4A44] cursor-pointer hover:bg-[rgba(91,138,114,0.04)] rounded-lg px-1 -mx-1 py-0.5 transition-colors" onClick={() => startInlineEdit('release_date', songDetails.release_date)}>
                        <span>{songDetails.release_date || 'N/A'}</span>
                        <PencilSquareIcon className="w-3.5 h-3.5 text-[#7A8580] opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                      </p>
                    )}
                  </div>
                  <div>
                    <label className="text-[13px] font-medium text-[#7A8580]">Media URL</label>
                    {editingField === 'media_url' ? (
                      <input
                        type="url"
                        autoFocus
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        onBlur={() => saveInlineEdit('media_url', editValue)}
                        onKeyDown={(e) => { if (e.key === 'Enter') saveInlineEdit('media_url', editValue); if (e.key === 'Escape') setEditingField(null) }}
                        placeholder="https://..."
                        className="w-full mt-1 px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-[10px] text-[#3D4A44] text-[15px] focus:outline-none focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                      />
                    ) : songDetails.media_url ? (
                      <div className="group flex items-center gap-2">
                        <a 
                          href={songDetails.media_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center space-x-2 text-[#5B8A72] hover:text-[#7BA594] mt-1"
                        >
                          <PlayIcon className="w-5 h-5" />
                          <span>Listen / Download</span>
                        </a>
                        <button onClick={() => startInlineEdit('media_url', songDetails.media_url)} className="p-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                          <PencilSquareIcon className="w-3.5 h-3.5 text-[#7A8580]" />
                        </button>
                      </div>
                    ) : (
                      <p className="group flex items-center gap-1.5 text-[#7A8580] cursor-pointer hover:bg-[rgba(91,138,114,0.04)] rounded-lg px-1 -mx-1 py-0.5 transition-colors" onClick={() => startInlineEdit('media_url', '')}>
                        <span>N/A</span>
                        <PencilSquareIcon className="w-3.5 h-3.5 text-[#7A8580] opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                      </p>
                    )}
                  </div>
                </div>
                
                <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-5 space-y-4">
                  <h3 className="text-[17px] font-semibold text-[#3D4A44] mb-4">Metadata</h3>
                  <div>
                    <label className="text-[13px] font-medium text-[#7A8580]">ISRC</label>
                    {editingField === 'isrc' ? (
                      <input
                        type="text"
                        autoFocus
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        onBlur={() => saveInlineEdit('isrc', editValue)}
                        onKeyDown={(e) => { if (e.key === 'Enter') saveInlineEdit('isrc', editValue); if (e.key === 'Escape') setEditingField(null) }}
                        placeholder="e.g. USRC17607839"
                        className="w-full mt-1 px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-[10px] text-[#3D4A44] text-[15px] font-mono focus:outline-none focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                      />
                    ) : (
                      <p className="group flex items-center gap-1.5 text-[#3D4A44] font-mono cursor-pointer hover:bg-[rgba(91,138,114,0.04)] rounded-lg px-1 -mx-1 py-0.5 transition-colors" onClick={() => startInlineEdit('isrc', songDetails.isrc)}>
                        <span>{songDetails.isrc || 'N/A'}</span>
                        <PencilSquareIcon className="w-3.5 h-3.5 text-[#7A8580] opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                      </p>
                    )}
                  </div>
                  <div>
                    <label className="text-[13px] font-medium text-[#7A8580]">ISWC</label>
                    {editingField === 'iswc' ? (
                      <input
                        type="text"
                        autoFocus
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        onBlur={() => saveInlineEdit('iswc', editValue)}
                        onKeyDown={(e) => { if (e.key === 'Enter') saveInlineEdit('iswc', editValue); if (e.key === 'Escape') setEditingField(null) }}
                        placeholder="e.g. T-345246800-1"
                        className="w-full mt-1 px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-[10px] text-[#3D4A44] text-[15px] font-mono focus:outline-none focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                      />
                    ) : (
                      <p className="group flex items-center gap-1.5 text-[#3D4A44] font-mono cursor-pointer hover:bg-[rgba(91,138,114,0.04)] rounded-lg px-1 -mx-1 py-0.5 transition-colors" onClick={() => startInlineEdit('iswc', songDetails.iswc)}>
                        <span>{songDetails.iswc || 'N/A'}</span>
                        <PencilSquareIcon className="w-3.5 h-3.5 text-[#7A8580] opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                      </p>
                    )}
                  </div>
                  <div>
                    <label className="text-[13px] font-medium text-[#7A8580]">Recording Code</label>
                    {editingField === 'recording_code' ? (
                      <input
                        type="text"
                        autoFocus
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        onBlur={() => saveInlineEdit('recording_code', editValue)}
                        onKeyDown={(e) => { if (e.key === 'Enter') saveInlineEdit('recording_code', editValue); if (e.key === 'Escape') setEditingField(null) }}
                        className="w-full mt-1 px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-[10px] text-[#3D4A44] text-[15px] font-mono focus:outline-none focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                      />
                    ) : (
                      <p className="group flex items-center gap-1.5 text-[#3D4A44] font-mono cursor-pointer hover:bg-[rgba(91,138,114,0.04)] rounded-lg px-1 -mx-1 py-0.5 transition-colors" onClick={() => startInlineEdit('recording_code', songDetails.recording_code)}>
                        <span>{songDetails.recording_code || 'N/A'}</span>
                        <PencilSquareIcon className="w-3.5 h-3.5 text-[#7A8580] opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                      </p>
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
                    {(() => {
                      const hasCreditSplits = (songDetails.credits || []).some(c => c.pub_share != null)
                      const pubVal = songDetails.publishing_percentage
                      return (
                        <div>
                          <p className="flex items-center gap-1.5 text-[#3D4A44] px-1 -mx-1 py-0.5">
                            <span className="font-medium">{pubVal != null ? `${pubVal}%` : '0%'}</span>
                            {pubVal != null && pubVal > 100 && (
                              <span className="text-xs text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded">Exceeds 100%</span>
                            )}
                          </p>
                          {!hasCreditSplits && pubVal != null && (
                            <p className="text-[11px] text-amber-600 mt-0.5">Legacy value — add credit-level splits in Rights tab</p>
                          )}
                          {pubVal == null && (
                            <p className="text-[11px] text-[#7A8580] mt-0.5">Add splits in the Rights tab</p>
                          )}
                        </div>
                      )
                    })()}
                  </div>
                  <div>
                    <label className="text-[13px] font-medium text-[#7A8580]">Master %</label>
                    {(() => {
                      const hasCreditSplits = (songDetails.credits || []).some(c => c.master_share != null)
                      const masterVal = songDetails.master_percentage
                      return (
                        <div>
                          <p className="flex items-center gap-1.5 text-[#3D4A44] px-1 -mx-1 py-0.5">
                            <span className="font-medium">{masterVal != null ? `${masterVal}%` : '0%'}</span>
                            {masterVal != null && masterVal > 100 && (
                              <span className="text-xs text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded">Exceeds 100%</span>
                            )}
                          </p>
                          {!hasCreditSplits && masterVal != null && (
                            <p className="text-[11px] text-amber-600 mt-0.5">Legacy value — add credit-level splits in Rights tab</p>
                          )}
                          {masterVal == null && (
                            <p className="text-[11px] text-[#7A8580] mt-0.5">Add splits in the Rights tab</p>
                          )}
                        </div>
                      )
                    })()}
                  </div>
                  <div>
                    <label className="text-[13px] font-medium text-[#7A8580]">Advance Amount ($)</label>
                    {editingField === 'advance_amount' ? (
                      <input
                        type="number"
                        autoFocus
                        min="0"
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        onBlur={() => saveInlineEdit('advance_amount', editValue)}
                        onKeyDown={(e) => { if (e.key === 'Enter') saveInlineEdit('advance_amount', editValue); if (e.key === 'Escape') setEditingField(null) }}
                        className="w-full mt-1 px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-[10px] text-[#3D4A44] text-[15px] focus:outline-none focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                      />
                    ) : (
                      <p className="group flex items-center gap-1.5 text-[#3D4A44] cursor-pointer hover:bg-[rgba(91,138,114,0.04)] rounded-lg px-1 -mx-1 py-0.5 transition-colors" onClick={() => startInlineEdit('advance_amount', songDetails.advance_amount ?? '')}>
                        <span>{songDetails.advance_amount != null ? `$${songDetails.advance_amount.toLocaleString()}` : 'N/A'}</span>
                        <PencilSquareIcon className="w-3.5 h-3.5 text-[#7A8580] opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                      </p>
                    )}
                  </div>
                  <div>
                    <label className="text-[13px] font-medium text-[#7A8580]">Contract Location</label>
                    {editingField === 'contract_location' ? (
                      <input
                        type="text"
                        autoFocus
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        onBlur={() => saveInlineEdit('contract_location', editValue)}
                        onKeyDown={(e) => { if (e.key === 'Enter') saveInlineEdit('contract_location', editValue); if (e.key === 'Escape') setEditingField(null) }}
                        className="w-full mt-1 px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-[10px] text-[#3D4A44] text-[15px] focus:outline-none focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                      />
                    ) : (
                      <p className="group flex items-center gap-1.5 text-[#3D4A44] cursor-pointer hover:bg-[rgba(91,138,114,0.04)] rounded-lg px-1 -mx-1 py-0.5 transition-colors" onClick={() => startInlineEdit('contract_location', songDetails.contract_location)}>
                        <span>{songDetails.contract_location || 'N/A'}</span>
                        <PencilSquareIcon className="w-3.5 h-3.5 text-[#7A8580] opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                      </p>
                    )}
                  </div>
                  <div>
                    <label className="text-[13px] font-medium text-[#7A8580]">Payment Status</label>
                    {editingField === 'payment_status' ? (
                      <select
                        autoFocus
                        value={editValue}
                        onChange={(e) => { setEditValue(e.target.value); saveInlineEdit('payment_status', e.target.value) }}
                        onBlur={() => setEditingField(null)}
                        className="w-full mt-1 px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-[10px] text-[#3D4A44] text-[15px] focus:outline-none focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white"
                      >
                        <option value="PENDING">Pending</option>
                        <option value="INVOICED">Invoiced</option>
                        <option value="PAID">Paid</option>
                        <option value="OVERDUE">Overdue</option>
                      </select>
                    ) : (
                      <p className="group flex items-center gap-1.5 text-[#3D4A44] cursor-pointer hover:bg-[rgba(91,138,114,0.04)] rounded-lg px-1 -mx-1 py-0.5 transition-colors" onClick={() => startInlineEdit('payment_status', songDetails.payment_status || 'PENDING')}>
                        <span>{songDetails.payment_status || 'N/A'}</span>
                        <PencilSquareIcon className="w-3.5 h-3.5 text-[#7A8580] opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                      </p>
                    )}
                  </div>
                  <div>
                    <label className="text-[13px] font-medium text-[#7A8580]">Paid</label>
                    <p className="group flex items-center gap-1.5 text-[#3D4A44] cursor-pointer hover:bg-[rgba(91,138,114,0.04)] rounded-lg px-1 -mx-1 py-0.5 transition-colors" onClick={() => cycleStatusValue('is_paid')}>
                      <span>{(() => { const v = songDetails.is_paid; if (v == null) return 'N/A'; const s = String(v).toLowerCase(); if (s === 'true' || s === 'yes') return 'Yes'; if (s === 'false' || s === 'no') return 'No'; return v || 'N/A' })()}</span>
                      <PencilSquareIcon className="w-3.5 h-3.5 text-[#7A8580] opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                    </p>
                  </div>
                  <div>
                    <label className="text-[13px] font-medium text-[#7A8580]">Advance</label>
                    {editingField === 'is_invoiced' ? (
                      <DollarOrNAInput
                        value={editValue}
                        onChange={(val) => { saveInlineEdit('is_invoiced', val) }}
                      />
                    ) : (
                      <p className="group flex items-center gap-1.5 text-[#3D4A44] cursor-pointer hover:bg-[rgba(91,138,114,0.04)] rounded-lg px-1 -mx-1 py-0.5 transition-colors" onClick={() => startInlineEdit('is_invoiced', songDetails.is_invoiced)}>
                        <span>{songDetails.is_invoiced || 'N/A'}</span>
                        <PencilSquareIcon className="w-3.5 h-3.5 text-[#7A8580] opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                      </p>
                    )}
                  </div>
                  <div>
                    <label className="text-[13px] font-medium text-[#7A8580]">Fee</label>
                    {editingField === 'is_registered_with_dsp' ? (
                      <DollarOrNAInput
                        value={editValue}
                        onChange={(val) => { saveInlineEdit('is_registered_with_dsp', val) }}
                      />
                    ) : (
                      <p className="group flex items-center gap-1.5 text-[#3D4A44] cursor-pointer hover:bg-[rgba(91,138,114,0.04)] rounded-lg px-1 -mx-1 py-0.5 transition-colors" onClick={() => startInlineEdit('is_registered_with_dsp', songDetails.is_registered_with_dsp)}>
                        <span>{songDetails.is_registered_with_dsp || 'N/A'}</span>
                        <PencilSquareIcon className="w-3.5 h-3.5 text-[#7A8580] opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                      </p>
                    )}
                  </div>
                </div>
                
                <div className="col-span-2 bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-5">
                  <h3 className="text-[17px] font-semibold text-[#3D4A44] mb-2">Notes</h3>
                  {editingField === 'notes' ? (
                    <textarea
                      autoFocus
                      value={editValue}
                      onChange={(e) => setEditValue(e.target.value)}
                      onBlur={() => saveInlineEdit('notes', editValue)}
                      rows={4}
                      placeholder="Add notes about this song..."
                      className="w-full px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-[10px] text-[#3D4A44] text-[15px] focus:outline-none focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent resize-y"
                    />
                  ) : songDetails.notes ? (
                    <div className="group bg-[rgba(196,149,107,0.08)] border border-[rgba(196,149,107,0.15)] rounded-[12px] p-4 cursor-pointer hover:border-[rgba(196,149,107,0.3)] transition-colors" onClick={() => startInlineEdit('notes', songDetails.notes)}>
                      <p className="text-[15px] text-[#3D4A44] whitespace-pre-wrap">{songDetails.notes}</p>
                      <PencilSquareIcon className="w-3.5 h-3.5 text-[#7A8580] opacity-0 group-hover:opacity-100 transition-opacity mt-2" />
                    </div>
                  ) : (
                    <p className="group flex items-center gap-1.5 text-[#7A8580] text-[15px] cursor-pointer hover:bg-[rgba(91,138,114,0.04)] rounded-lg px-1 -mx-1 py-0.5 transition-colors" onClick={() => startInlineEdit('notes', '')}>
                      <span>No notes added</span>
                      <PencilSquareIcon className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                    </p>
                  )}
                </div>

                <div className="col-span-2 bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-5">
                  <h3 className="text-[17px] font-semibold text-[#3D4A44] mb-4">Status Checklist</h3>
                  <div className="space-y-3">
                    {[
                      { label: 'Contract Executed', field: 'has_contract_executed' },
                      { label: 'PRO Registered', field: 'is_registered_with_pro' },
                      { label: 'MLC Registered', field: 'mlc_registered' },
                    ].map(({ label, field }) => (
                      <div key={field} className="group flex items-center justify-between cursor-pointer hover:bg-[rgba(91,138,114,0.04)] rounded-lg px-2 -mx-2 py-1 transition-colors" onClick={() => cycleStatusValue(field)}>
                        <span className="text-[15px] text-[#3D4A44]">{label}</span>
                        <div className="flex items-center gap-1.5">
                          {getStatusIcon(songDetails[field])}
                          <PencilSquareIcon className="w-3 h-3 text-[#7A8580] opacity-0 group-hover:opacity-40" />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="col-span-2 bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-5">
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
                        className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-[12px] font-medium text-[14px] hover:shadow-[0px_4px_12px_rgba(91,138,114,0.3)] transition-all disabled:opacity-50"
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
                                  {lc.reference_number ? ` \u2022 ${lc.reference_number}` : ''}
                                  {lc.status ? ` \u2022 ${lc.status}` : ''}
                                </p>
                                {(lc.start_date || lc.end_date) && (
                                  <p className="text-[12px] text-[#7A8580]">
                                    {lc.start_date ? new Date(lc.start_date).toLocaleDateString() : ''}
                                    {lc.start_date && lc.end_date ? ' \u2013 ' : ''}
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
                                    {contract.contract_type || 'Contract'} \u2022 {new Date(contract.created_at).toLocaleDateString()}
                                  </p>
                                </div>
                              </div>
                              <div className="flex items-center space-x-2">
                                <button
                                  onClick={() => setShareTarget({ type: 'DOCUMENT', id: contract.id, name: contract.file_name })}
                                  className="p-2 text-[#7A8580] hover:text-[#5A8A9A] hover:bg-[rgba(90,138,154,0.1)] rounded-[8px] transition-colors"
                                  title="Share"
                                >
                                  <LinkIcon className="w-5 h-5" />
                                </button>
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
                        <div className="text-center py-6 bg-[#F5F7F4] rounded-[12px] border-2 border-dashed border-[rgba(59,77,67,0.08)]">
                          <DocumentTextIcon className="w-10 h-10 text-[#7A8580] mx-auto mb-2" />
                          <p className="text-[#3D4A44] text-sm">No contracts uploaded yet</p>
                          <p className="text-[12px] text-[#7A8580]">Upload a PDF to attach it to this song</p>
                        </div>
                      )}
                    </>
                  ) : null}
                </div>
              </div>
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
                        <div className="relative" ref={splitSearchRef}>
                          <input
                            type="text"
                            placeholder="Search roster, directory, or type new name..."
                            value={splitSearchQuery || splitForm.rights_holder_name}
                            onChange={(e) => {
                              const val = e.target.value
                              setSplitSearchQuery(val)
                              setSplitForm(prev => ({ ...prev, rights_holder_id: '', rights_holder_name: val, contact_id: '', ipi: '', pro: '' }))
                              setShowSplitSearch(val.length > 0)
                            }}
                            onFocus={() => {
                              const q = splitSearchQuery || splitForm.rights_holder_name
                              if (q) setShowSplitSearch(true)
                            }}
                            className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                          />
                          {splitForm.rights_holder_name && !showSplitSearch && (
                            <button
                              type="button"
                              onClick={() => {
                                setSplitSearchQuery('')
                                setSplitForm(prev => ({ ...prev, rights_holder_id: '', rights_holder_name: '', contact_id: '', ipi: '', pro: '' }))
                              }}
                              className="absolute right-2 top-1/2 -translate-y-1/2 text-[#7A8580] hover:text-[#3D4A44] transition-colors"
                            >
                              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4"><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
                            </button>
                          )}
                          {showSplitSearch && (splitSearchQuery || splitForm.rights_holder_name) && (() => {
                            const splitRoleOptions = ['Writer', 'Producer', 'Artist', 'Engineer', 'Composer', 'Lyricist', 'Arranger', 'Publisher', 'Administrator']
                            const mapToSplitRole = (roles) => {
                              if (!roles || !roles.length) return ''
                              for (const r of roles) {
                                const match = splitRoleOptions.find(o => o.toLowerCase() === (r || '').toLowerCase())
                                if (match) return match
                              }
                              const partialMap = { 'songwriter': 'Writer', 'writing': 'Writer', 'producing': 'Producer', 'vocalist': 'Artist', 'singer': 'Artist', 'mixing': 'Engineer', 'mastering': 'Engineer', 'composition': 'Composer', 'lyrics': 'Lyricist', 'arrangement': 'Arranger', 'admin': 'Administrator', 'publishing': 'Publisher' }
                              for (const r of roles) {
                                const key = (r || '').toLowerCase()
                                if (partialMap[key]) return partialMap[key]
                              }
                              return ''
                            }
                            const q = (splitSearchQuery || splitForm.rights_holder_name).toLowerCase()
                            const rosterMatches = splitCreators.filter(c => c.display_name?.toLowerCase().includes(q))
                            const dirMatches = directoryContacts.filter(c => c.display_name?.toLowerCase().includes(q) && !rosterMatches.some(r => c.creator_id && c.creator_id === r.id))
                            const hasResults = rosterMatches.length > 0 || dirMatches.length > 0
                            return (
                              <div className="absolute z-20 left-0 right-0 mt-1 bg-white border border-[rgba(59,77,67,0.12)] rounded-lg shadow-lg max-h-52 overflow-y-auto">
                                {rosterMatches.length > 0 && (
                                  <>
                                    <div className="px-3 py-1.5 text-[10px] font-semibold text-[#7A8580] uppercase tracking-wider bg-[#F5F7F4] border-b border-[rgba(59,77,67,0.08)]">Roster</div>
                                    {rosterMatches.map(creator => {
                                      const linked = directoryContacts.find(c => c.creator_id === creator.id)
                                      return (
                                        <button
                                          key={`roster-${creator.id}`}
                                          type="button"
                                          className="w-full text-left px-3 py-2 text-sm hover:bg-[rgba(91,138,114,0.08)] transition-colors flex items-center justify-between gap-2"
                                          onClick={() => {
                                            const derivedRole = mapToSplitRole(linked?.roles || creator.roles)
                                            setSplitForm(prev => ({
                                              ...prev,
                                              rights_holder_id: String(creator.id),
                                              rights_holder_name: creator.display_name,
                                              contact_id: linked ? String(linked.id) : '',
                                              ipi: linked?.ipi || creator.primary_ipi || '',
                                              pro: linked?.pro || creator.primary_pro || '',
                                              role: prev.role || derivedRole
                                            }))
                                            setSplitSearchQuery('')
                                            setShowSplitSearch(false)
                                          }}
                                        >
                                          <span className="text-[#3D4A44] truncate">{creator.display_name}</span>
                                          <div className="flex items-center gap-1.5 flex-shrink-0">
                                            {(creator.primary_ipi || linked?.ipi) && <span className="text-[10px] text-[#7A8580]">IPI: {creator.primary_ipi || linked?.ipi}</span>}
                                            <span className="text-[9px] px-1.5 py-0.5 rounded bg-[rgba(91,138,114,0.12)] text-[#5B8A72] font-medium">Roster</span>
                                          </div>
                                        </button>
                                      )
                                    })}
                                  </>
                                )}
                                {dirMatches.length > 0 && (
                                  <>
                                    <div className="px-3 py-1.5 text-[10px] font-semibold text-[#7A8580] uppercase tracking-wider bg-[#F5F7F4] border-b border-[rgba(59,77,67,0.08)]">Directory</div>
                                    {dirMatches.map(contact => (
                                      <button
                                        key={`dir-${contact.id}`}
                                        type="button"
                                        className="w-full text-left px-3 py-2 text-sm hover:bg-[rgba(91,138,114,0.08)] transition-colors flex items-center justify-between gap-2"
                                        onClick={() => {
                                          const derivedRole = mapToSplitRole(contact.roles)
                                          setSplitForm(prev => ({
                                            ...prev,
                                            rights_holder_id: '',
                                            rights_holder_name: contact.display_name,
                                            contact_id: String(contact.id),
                                            ipi: contact.ipi || '',
                                            pro: contact.pro || '',
                                            role: prev.role || derivedRole
                                          }))
                                          setSplitSearchQuery('')
                                          setShowSplitSearch(false)
                                        }}
                                      >
                                        <span className="text-[#3D4A44] truncate">{contact.display_name}</span>
                                        <div className="flex items-center gap-1.5 flex-shrink-0">
                                          {contact.ipi && <span className="text-[10px] text-[#7A8580]">IPI: {contact.ipi}</span>}
                                          <span className="text-[9px] px-1.5 py-0.5 rounded bg-[rgba(178,154,101,0.15)] text-[#8B7355] font-medium">Directory</span>
                                        </div>
                                      </button>
                                    ))}
                                  </>
                                )}
                                {!hasResults && (
                                  <div className="px-3 py-2.5 text-xs text-[#7A8580] flex items-center gap-2">
                                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-3.5 h-3.5"><path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" /></svg>
                                    No matches — a new directory contact will be created
                                  </div>
                                )}
                              </div>
                            )
                          })()}
                        </div>
                        {(splitForm.rights_holder_id || splitForm.contact_id) && (
                          <div className="mt-1.5 flex items-center gap-2 flex-wrap">
                            {splitForm.rights_holder_id && (
                              <span className="text-[10px] px-2 py-0.5 rounded-full bg-[rgba(91,138,114,0.1)] text-[#5B8A72] font-medium">Roster Creator</span>
                            )}
                            {splitForm.contact_id && !splitForm.rights_holder_id && (
                              <span className="text-[10px] px-2 py-0.5 rounded-full bg-[rgba(178,154,101,0.12)] text-[#8B7355] font-medium">Directory Contact</span>
                            )}
                            {splitForm.ipi && <span className="text-[10px] text-[#7A8580]">IPI: {splitForm.ipi}</span>}
                            {splitForm.pro && <span className="text-[10px] text-[#7A8580]">PRO: {splitForm.pro}</span>}
                          </div>
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
                        <label className="block text-xs font-medium text-[#7A8580] mb-1">IPI Number</label>
                        <input
                          type="text"
                          placeholder="e.g. 00123456789"
                          value={splitForm.ipi}
                          onChange={(e) => setSplitForm(prev => ({ ...prev, ipi: e.target.value }))}
                          className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-[#7A8580] mb-1">PRO</label>
                        <select
                          value={splitForm.pro}
                          onChange={(e) => setSplitForm(prev => ({ ...prev, pro: e.target.value }))}
                          className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                        >
                          <option value="">Select PRO</option>
                          <option value="ASCAP">ASCAP</option>
                          <option value="BMI">BMI</option>
                          <option value="SESAC">SESAC</option>
                          <option value="GMR">GMR</option>
                          <option value="PRS">PRS</option>
                          <option value="SOCAN">SOCAN</option>
                          <option value="GEMA">GEMA</option>
                          <option value="SACEM">SACEM</option>
                          <option value="APRA">APRA</option>
                          <option value="Other">Other</option>
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
                        <label className="block text-xs font-medium text-[#7A8580] mb-1">Role</label>
                        <select
                          value={splitForm.role}
                          onChange={(e) => setSplitForm(prev => ({ ...prev, role: e.target.value }))}
                          className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                        >
                          <option value="">Select Role</option>
                          <option value="Writer">Writer</option>
                          <option value="Producer">Producer</option>
                          <option value="Artist">Artist</option>
                          <option value="Engineer">Engineer</option>
                          <option value="Composer">Composer</option>
                          <option value="Lyricist">Lyricist</option>
                          <option value="Arranger">Arranger</option>
                          <option value="Publisher">Publisher</option>
                          <option value="Administrator">Administrator</option>
                          <option value="Other">Other</option>
                        </select>
                      </div>
                    </div>
                    <div className="flex justify-end space-x-2">
                      <button
                        onClick={() => { setShowSplitForm(false); setSplitForm({ rights_holder_id: '', rights_holder_name: '', rights_type: 'PUBLISHING', share_percentage: '', role: '', contact_id: '', ipi: '', pro: '' }); setSplitSearchQuery('') }}
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
                    <div className="hidden sm:grid grid-cols-5 gap-4 px-3 py-2 text-[12px] font-medium text-[#7A8580] uppercase tracking-wider">
                      <span>Rights Holder</span>
                      <span>Rights Type</span>
                      <span>Share</span>
                      <span>Role</span>
                      <span></span>
                    </div>
                    {songSplits.map((split) => (
                      <div key={split.id} className="flex flex-col sm:grid sm:grid-cols-5 gap-2 sm:gap-4 px-3 py-3 bg-[#F5F7F4] rounded-[12px]">
                        <div className="flex items-center justify-between sm:contents">
                          <span className="font-medium text-[#3D4A44] text-[14px]">{split.rights_holder_name}</span>
                          <div className="flex items-center gap-2 sm:hidden">
                            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium ${
                              split.rights_type === 'MASTER' ? 'bg-purple-50 text-purple-600' :
                              split.rights_type === 'PUBLISHING' ? 'bg-blue-50 text-blue-600' :
                              split.rights_type === 'PERFORMANCE' ? 'bg-amber-50 text-amber-600' :
                              split.rights_type === 'MECHANICAL' ? 'bg-indigo-50 text-indigo-600' :
                              'bg-gray-50 text-gray-600'
                            }`}>
                              {split.rights_type}
                            </span>
                            <button onClick={() => handleDeleteSongSplit(split.id)} className="p-1 text-[#7A8580] hover:text-[#C47068] rounded transition-colors" title="Remove split">
                              <TrashIcon className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                        <span className={`hidden sm:inline-flex items-center px-2 py-0.5 rounded-full text-[12px] font-medium w-fit ${
                          split.rights_type === 'MASTER' ? 'bg-purple-50 text-purple-600' :
                          split.rights_type === 'PUBLISHING' ? 'bg-blue-50 text-blue-600' :
                          split.rights_type === 'PERFORMANCE' ? 'bg-amber-50 text-amber-600' :
                          split.rights_type === 'MECHANICAL' ? 'bg-indigo-50 text-indigo-600' :
                          'bg-gray-50 text-gray-600'
                        }`}>
                          {split.rights_type}
                        </span>
                        <div className="flex items-center justify-between sm:contents">
                          <div className="flex items-center gap-2">
                            <div className="hidden sm:block flex-1 h-2 bg-[#EEF1EC] rounded-full overflow-hidden max-w-[80px]">
                              <div className="h-full bg-gradient-to-r from-[#5B8A72] to-[#7BA594] rounded-full" style={{ width: `${Math.min(split.share_percentage, 100)}%` }}></div>
                            </div>
                            <span className="text-[14px] font-semibold text-[#3D4A44]">{split.share_percentage}%</span>
                          </div>
                          <span className="text-[13px] text-[#7A8580]">{split.role || '-'}</span>
                          <div className="hidden sm:flex justify-end">
                            <button onClick={() => handleDeleteSongSplit(split.id)} className="p-1 text-[#7A8580] hover:text-[#C47068] rounded transition-colors" title="Remove split">
                              <TrashIcon className="w-4 h-4" />
                            </button>
                          </div>
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
                          <div className="hidden sm:grid grid-cols-4 gap-4 px-3 py-2 text-[12px] font-medium text-[#7A8580] uppercase tracking-wider">
                            <span>Rights Holder</span>
                            <span>Rights Type</span>
                            <span>Share</span>
                            <span>Role</span>
                          </div>
                          {contractInfo.splits.map((split, sidx) => (
                            <div key={sidx} className="flex flex-col sm:grid sm:grid-cols-4 gap-1.5 sm:gap-4 px-3 py-3 bg-[#F5F7F4] rounded-[12px]">
                              <div className="flex items-center justify-between sm:block">
                                <span className="font-medium text-[#3D4A44] text-[14px]">{split.rights_holder_name}</span>
                                <span className={`sm:hidden inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium ${
                                  split.rights_type === 'MASTER' ? 'bg-purple-50 text-purple-600' :
                                  split.rights_type === 'PUBLISHING' ? 'bg-blue-50 text-blue-600' :
                                  split.rights_type === 'PERFORMANCE' ? 'bg-amber-50 text-amber-600' :
                                  split.rights_type === 'MECHANICAL' ? 'bg-indigo-50 text-indigo-600' :
                                  'bg-gray-50 text-gray-600'
                                }`}>
                                  {split.rights_type}
                                </span>
                              </div>
                              <span className={`hidden sm:inline-flex items-center px-2 py-0.5 rounded-full text-[12px] font-medium w-fit ${
                                split.rights_type === 'MASTER' ? 'bg-purple-50 text-purple-600' :
                                split.rights_type === 'PUBLISHING' ? 'bg-blue-50 text-blue-600' :
                                split.rights_type === 'PERFORMANCE' ? 'bg-amber-50 text-amber-600' :
                                split.rights_type === 'MECHANICAL' ? 'bg-indigo-50 text-indigo-600' :
                                'bg-gray-50 text-gray-600'
                              }`}>
                                {split.rights_type}
                              </span>
                              <div className="flex items-center justify-between sm:contents">
                              <div className="flex items-center gap-2">
                                <div className="flex-1 h-2 bg-[#EEF1EC] rounded-full overflow-hidden max-w-[80px]">
                                  <div className="h-full bg-gradient-to-r from-[#5B8A72] to-[#7BA594] rounded-full" style={{ width: `${Math.min(split.share_percentage, 100)}%` }}></div>
                                </div>
                                <span className="text-[14px] font-semibold text-[#3D4A44]">{split.share_percentage}%</span>
                              </div>
                              <span className="text-[13px] text-[#7A8580]">{split.role || '-'}</span>
                              </div>
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
          
          {activeTab === 'streaming' && (
            <div className="space-y-4">
              {streamingLoading ? (
                <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-5">
                  <div className="flex items-center justify-center py-12">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#3D4A44]"></div>
                    <span className="ml-3 text-[#7A8580]">Calculating streaming estimates...</span>
                  </div>
                </div>
              ) : streamingData ? (
                <>
                  <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-5">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-[17px] font-semibold text-[#3D4A44]">Total Estimated Streams</h3>
                      {streamingData.last_updated && (
                        <span className="text-[12px] text-[#7A8580]">Updated {streamingData.last_updated}</span>
                      )}
                    </div>
                    {streamingData.total_streams > 0 ? (
                      <div>
                        <p className="text-[36px] font-bold text-[#3D4A44] tracking-tight">
                          {streamingData.total_streams.toLocaleString()}
                        </p>
                        {streamingData.riaa_equivalents && (streamingData.riaa_equivalents.single_units > 0 || streamingData.riaa_equivalents.album_units > 0) && (
                          <div className="flex items-center gap-3 mt-2">
                            {streamingData.riaa_equivalents.single_units > 0 && (
                              <span className="inline-flex items-center px-2.5 py-1 rounded-full text-[12px] font-medium bg-[#EEF1EC] text-[#3D4A44]">
                                {streamingData.riaa_equivalents.single_units.toLocaleString()} single units
                              </span>
                            )}
                            {streamingData.riaa_equivalents.album_units > 0 && (
                              <span className="inline-flex items-center px-2.5 py-1 rounded-full text-[12px] font-medium bg-[#E8EDE6] text-[#3D4A44]">
                                {streamingData.riaa_equivalents.album_units.toLocaleString()} album units
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="py-6">
                        <p className="text-[#7A8580] text-[15px]">No streaming estimates available yet.</p>
                        <p className="text-[#9BA8A0] text-[13px] mt-1">
                          {streamingData.has_spotify_link
                            ? 'Estimates will be calculated once the Spotify API connection is active.'
                            : 'Link this song to Spotify in the Links tab to generate streaming estimates.'}
                        </p>
                      </div>
                    )}
                  </div>

                  <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-5">
                    <h3 className="text-[17px] font-semibold text-[#3D4A44] mb-4">Platform Breakdown</h3>
                    {streamingData.platforms && Object.values(streamingData.platforms).some(p => p.streams > 0) ? (
                      <div className="space-y-3">
                        {Object.entries(streamingData.platforms)
                          .sort(([,a], [,b]) => b.streams - a.streams)
                          .map(([key, platform]) => {
                            const maxStreams = Math.max(...Object.values(streamingData.platforms).map(p => p.streams), 1)
                            const barWidth = platform.streams > 0 ? Math.max((platform.streams / maxStreams) * 100, 4) : 0
                            return (
                              <div key={key} className="flex items-center gap-3">
                                <div className="w-[110px] flex-shrink-0">
                                  <span className="text-[13px] font-medium text-[#3D4A44]">{platform.name}</span>
                                </div>
                                <div className="flex-1 h-[28px] bg-[#F5F7F4] rounded-full overflow-hidden relative">
                                  {platform.streams > 0 && (
                                    <div
                                      className="h-full rounded-full transition-all duration-500"
                                      style={{ width: `${barWidth}%`, backgroundColor: platform.color }}
                                    />
                                  )}
                                </div>
                                <div className="w-[90px] text-right flex-shrink-0">
                                  <span className="text-[13px] font-medium text-[#3D4A44]">
                                    {platform.streams > 0 ? platform.streams.toLocaleString() : '-'}
                                  </span>
                                </div>
                              </div>
                            )
                          })}
                        {streamingData.confidence > 0 && (
                          <div className="mt-3 pt-3 border-t border-[#EEF1EC]">
                            <div className="flex items-center gap-2">
                              <span className="text-[12px] text-[#9BA8A0]">Confidence:</span>
                              <div className="flex-1 h-1.5 bg-[#F5F7F4] rounded-full max-w-[120px]">
                                <div
                                  className="h-full bg-[#6B8F71] rounded-full"
                                  style={{ width: `${Math.round(streamingData.confidence * 100)}%` }}
                                />
                              </div>
                              <span className="text-[12px] text-[#9BA8A0]">{Math.round(streamingData.confidence * 100)}%</span>
                            </div>
                          </div>
                        )}
                      </div>
                    ) : (
                      <p className="text-[#7A8580] text-[14px] py-4">No platform data available.</p>
                    )}
                  </div>

                  <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-5">
                    <h3 className="text-[17px] font-semibold text-[#3D4A44] mb-4">DSP Links</h3>
                    {streamingData.dsp_links && streamingData.dsp_links.length > 0 ? (
                      <div className="space-y-2">
                        {streamingData.dsp_links.map((link) => (
                          <a
                            key={link.id}
                            href={link.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center justify-between p-3 bg-[#F5F7F4] rounded-[12px] hover:bg-[#EEF1EC] transition-colors"
                          >
                            <span className="text-[14px] font-medium text-[#3D4A44]">{link.platform}</span>
                            <ArrowTopRightOnSquareIcon className="w-4 h-4 text-[#7A8580]" />
                          </a>
                        ))}
                      </div>
                    ) : (
                      <p className="text-[#7A8580] text-[14px]">No DSP links found. Link this song in the Links tab.</p>
                    )}
                  </div>
                </>
              ) : (
                <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-5">
                  <div className="text-center text-[#7A8580] py-12">
                    Unable to load streaming data.
                  </div>
                </div>
              )}
            </div>
          )}
          
          {activeTab === 'links' && (
            <div className="space-y-6">
              <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-5">
                <h3 className="text-[17px] font-semibold text-[#3D4A44] mb-4">Credits</h3>
                {songDetails.credits && songDetails.credits.length > 0 ? (
                  <div className="space-y-2">
                    {songDetails.credits.map((credit, idx) => (
                      <div key={idx} className="flex flex-wrap items-center gap-2 p-3 bg-[#F5F7F4] rounded-[12px]">
                        <div className="min-w-0">
                          {credit.creator_name ? (
                            <Link to={`/roster/${credit.creator_id}`} onClick={onClose} className="font-medium text-[#5B8A72] hover:text-[#7BA594]">{credit.creator_name}</Link>
                          ) : (
                            <Link to="/roster" onClick={onClose} className="font-medium text-amber-600 underline hover:text-amber-700">Unmatched — Review Needed</Link>
                          )}
                          <p className="text-[13px] text-[#7A8580]">{credit.role}</p>
                        </div>
                        <div className="flex items-center gap-1.5 ml-auto flex-shrink-0">
                          <span className={`text-xs px-1.5 py-0.5 rounded ${credit.pub_share != null ? 'text-[#5B8A72] bg-[rgba(91,138,114,0.1)]' : 'text-[#B0BDB4] bg-[rgba(59,77,67,0.04)]'}`}>Pub {credit.pub_share != null ? `${credit.pub_share}%` : '—'}</span>
                          <span className={`text-xs px-1.5 py-0.5 rounded ${credit.master_share != null ? 'text-[#5A8A9A] bg-[rgba(90,138,154,0.1)]' : 'text-[#B0BDB4] bg-[rgba(59,77,67,0.04)]'}`}>Master {credit.master_share != null ? `${credit.master_share}%` : '—'}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-[#7A8580]">No credits added yet</p>
                )}
              </div>
              
              <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-5">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-[17px] font-semibold text-[#3D4A44]">DSP Links</h3>
                  {!showSpotifySearch && (
                    <button
                      onClick={openSpotifySearch}
                      className="flex items-center space-x-1.5 px-3 py-1.5 bg-[#1DB954] text-white rounded-full font-medium text-[13px] hover:bg-[#1AA34A] transition-colors"
                    >
                      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/></svg>
                      <span>Link Spotify</span>
                    </button>
                  )}
                </div>

                {showSpotifySearch && (
                  <div className="mb-4 p-4 bg-[#F5F7F4] rounded-[14px] space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-[14px] font-semibold text-[#3D4A44]">Search Spotify</span>
                      <button onClick={() => { setShowSpotifySearch(false); setSpotifyResults([]); setSpotifyQuery('') }} className="text-[#7A8580] hover:text-[#3D4A44]">
                        <XMarkIcon className="w-5 h-5" />
                      </button>
                    </div>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={spotifyQuery}
                        onChange={(e) => setSpotifyQuery(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && searchSpotify()}
                        placeholder="Search by title, artist..."
                        className="flex-1 px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-[10px] text-[14px] text-[#3D4A44] focus:outline-none focus:ring-2 focus:ring-[#1DB954] focus:border-transparent"
                      />
                      <button
                        onClick={searchSpotify}
                        disabled={spotifySearching || !spotifyQuery.trim()}
                        className="px-4 py-2 bg-[#1DB954] text-white rounded-[10px] font-medium text-[13px] hover:bg-[#1AA34A] transition-colors disabled:opacity-50"
                      >
                        {spotifySearching ? 'Searching...' : 'Search'}
                      </button>
                    </div>

                    {spotifyResults.length > 0 && (
                      <div className="space-y-2 max-h-[280px] overflow-y-auto">
                        {spotifyResults.map((track) => (
                          <div key={track.spotify_id} className="flex items-center gap-3 p-2.5 bg-white rounded-[12px] border border-[rgba(59,77,67,0.08)] hover:border-[#1DB954] transition-colors">
                            {track.album_art ? (
                              <img src={track.album_art} alt="" className="w-12 h-12 rounded-[8px] object-cover flex-shrink-0" />
                            ) : (
                              <div className="w-12 h-12 rounded-[8px] bg-[#EEF1EC] flex items-center justify-center flex-shrink-0">
                                <MusicalNoteIcon className="w-6 h-6 text-[#7A8580]" />
                              </div>
                            )}
                            <div className="flex-1 min-w-0">
                              <p className="text-[14px] font-medium text-[#3D4A44] truncate">{track.title}</p>
                              <p className="text-[12px] text-[#7A8580] truncate">{track.primary_artist}{track.album_name ? ` · ${track.album_name}` : ''}</p>
                              {track.isrc && <p className="text-[11px] text-[#9CA8A2]">ISRC: {track.isrc}</p>}
                            </div>
                            <button
                              onClick={() => linkSpotifyTrack(track)}
                              disabled={spotifyLinking === track.spotify_id}
                              className="flex-shrink-0 px-3 py-1.5 bg-[#1DB954] text-white rounded-full font-medium text-[12px] hover:bg-[#1AA34A] transition-colors disabled:opacity-50"
                            >
                              {spotifyLinking === track.spotify_id ? 'Linking...' : 'Link'}
                            </button>
                          </div>
                        ))}
                      </div>
                    )}

                    {spotifySearching && (
                      <div className="flex items-center justify-center py-4">
                        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-[#1DB954]"></div>
                      </div>
                    )}

                    {spotifyError && (
                      <div className="text-[13px] text-[#C47068] bg-[rgba(196,112,104,0.08)] border border-[rgba(196,112,104,0.15)] rounded-[10px] p-3 text-center">
                        {spotifyError}
                      </div>
                    )}
                    {!spotifySearching && !spotifyError && spotifyResults.length === 0 && spotifyQuery && (
                      <p className="text-[13px] text-[#7A8580] text-center py-2">No results yet. Press Search or Enter.</p>
                    )}
                  </div>
                )}

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
                        <div className="flex items-center space-x-2">
                          {(link.platform === 'Spotify' || link.platform === 'SPOTIFY') && (
                            <svg className="w-5 h-5 text-[#1DB954]" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/></svg>
                          )}
                          <span className="font-medium text-[#3D4A44]">{link.platform}</span>
                        </div>
                        <LinkIcon className="w-5 h-5 text-[#7A8580]" />
                      </a>
                    ))}
                  </div>
                ) : (
                  !showSpotifySearch && <p className="text-[#7A8580]">No DSP links added yet</p>
                )}
              </div>
            </div>
          )}

          {activeTab === 'audio' && (
            <div className="space-y-6">
              <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-5">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-[17px] font-semibold text-[#3D4A44]">Audio Files</h3>
                  {dropboxConnected && (
                    <button
                      onClick={handleOpenDropboxPicker}
                      className="flex items-center space-x-2 px-4 py-2 bg-[#5B8A72] text-white rounded-[12px] font-medium text-[14px] hover:bg-[#4A7A62] transition-colors"
                    >
                      <LinkIcon className="w-4 h-4" />
                      <span>Link from Dropbox</span>
                    </button>
                  )}
                </div>

                {audioLoading ? (
                  <div className="text-center py-8 text-[#7A8580]">Loading audio files...</div>
                ) : audioAssets.length > 0 ? (
                  <div className="space-y-3">
                    <div className="grid grid-cols-[1fr_140px_80px_90px_auto_auto] gap-3 px-3 py-2 text-[12px] font-medium text-[#7A8580] uppercase tracking-wider">
                      <span>Filename</span>
                      <span>Type</span>
                      <span>Size</span>
                      <span>Status</span>
                      <span>Analysis</span>
                      <span></span>
                    </div>
                    {audioAssets.map((asset) => (
                      <div key={asset.id}>
                        <div className="grid grid-cols-[1fr_140px_80px_90px_auto_auto] gap-3 px-3 py-3 bg-[#F5F7F4] rounded-[12px] items-center">
                          <div className="flex items-center gap-2 min-w-0">
                            <SpeakerWaveIcon className="w-5 h-5 text-[#5B8A72] flex-shrink-0" />
                            <span className="font-medium text-[#3D4A44] text-[14px] truncate">{asset.name || asset.filename}</span>
                          </div>
                          <select
                            value={asset.file_type || 'Other'}
                            onChange={(e) => updateFileType(asset.id, e.target.value)}
                            className="border border-[rgba(59,77,67,0.12)] rounded-lg px-2 py-1.5 text-[13px] bg-white text-[#3D4A44] focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                          >
                            <option value="Main Mix">Main Mix</option>
                            <option value="Instrumental">Instrumental</option>
                            <option value="Clean">Clean</option>
                            <option value="Alt Mix">Alt Mix</option>
                            <option value="Stems">Stems</option>
                            <option value="Other">Other</option>
                          </select>
                          <span className="text-[13px] text-[#7A8580]">{formatFileSize(asset.size_bytes || asset.size)}</span>
                          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[12px] font-medium w-fit ${
                            asset.is_available !== false
                              ? 'bg-[rgba(91,154,110,0.15)] text-[#5B9A6E]'
                              : 'bg-[rgba(196,112,104,0.15)] text-[#C47068]'
                          }`}>
                            {asset.is_available !== false ? 'Available' : 'Unavailable'}
                          </span>
                          <div className="flex items-center gap-2">
                            {asset.analysis ? (
                              <div className="flex items-center gap-1.5">
                                {asset.analysis.bpm && (
                                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-[rgba(91,138,114,0.12)] text-[#5B8A72]">
                                    {Math.round(asset.analysis.bpm)} BPM
                                  </span>
                                )}
                                {asset.analysis.key && (
                                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-[rgba(91,138,114,0.12)] text-[#5B8A72]">
                                    {asset.analysis.key}
                                  </span>
                                )}
                              </div>
                            ) : (
                              <button
                                onClick={() => analyzeFile(asset.id)}
                                disabled={analyzing[asset.id]}
                                className="flex items-center gap-1 px-2.5 py-1 text-[12px] font-medium text-[#5B8A72] border border-[rgba(91,138,114,0.3)] rounded-lg hover:bg-[rgba(91,138,114,0.08)] transition-colors disabled:opacity-50"
                              >
                                <ChartBarIcon className="w-3.5 h-3.5" />
                                {analyzing[asset.id] ? 'Analyzing...' : 'Analyze'}
                              </button>
                            )}
                          </div>
                          <button
                            onClick={() => setShareTarget({ type: 'AUDIO', id: asset.id, name: asset.name || asset.filename })}
                            className="p-1.5 text-[#7A8580] hover:text-[#5A8A9A] rounded transition-colors"
                            title="Share audio file"
                          >
                            <LinkIcon className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => unlinkFile(asset.id)}
                            className="p-1.5 text-[#7A8580] hover:text-[#C47068] rounded transition-colors"
                            title="Unlink file"
                          >
                            <TrashIcon className="w-4 h-4" />
                          </button>
                        </div>

                        {asset.analysis && (
                          <div className="mt-2 ml-4 p-4 bg-white rounded-[12px] border border-[rgba(59,77,67,0.08)]">
                            <div className="flex items-center gap-6 mb-3">
                              {asset.analysis.bpm && (
                                <div>
                                  <span className="text-[12px] font-medium text-[#7A8580]">BPM</span>
                                  <p className="text-[18px] font-semibold text-[#3D4A44]">{Math.round(asset.analysis.bpm)}</p>
                                </div>
                              )}
                              {asset.analysis.key && (
                                <div>
                                  <span className="text-[12px] font-medium text-[#7A8580]">Key</span>
                                  <p className="text-[18px] font-semibold text-[#3D4A44]">{asset.analysis.key}</p>
                                </div>
                              )}
                              {asset.analysis.loudness != null && (
                                <div>
                                  <span className="text-[12px] font-medium text-[#7A8580]">Loudness</span>
                                  <p className="text-[18px] font-semibold text-[#3D4A44]">{asset.analysis.loudness.toFixed(1)} dB</p>
                                </div>
                              )}
                            </div>

                            {(asset.analysis.tags && asset.analysis.tags.length > 0) && (
                              <div className="flex flex-wrap gap-1.5 mb-2">
                                {asset.analysis.tags.map((tag) => (
                                  <span
                                    key={tag.id}
                                    className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[12px] font-medium border ${getTagColor(tag.tag_type)}`}
                                  >
                                    {tag.name}
                                    <button
                                      onClick={() => removeTag(asset.id, tag.id)}
                                      className="ml-0.5 hover:opacity-70"
                                    >
                                      <XMarkIcon className="w-3 h-3" />
                                    </button>
                                  </span>
                                ))}
                              </div>
                            )}

                            {showAddTag === asset.id ? (
                              <div className="flex items-center gap-2 mt-2">
                                <input
                                  type="text"
                                  value={newTagName}
                                  onChange={(e) => setNewTagName(e.target.value)}
                                  placeholder="Tag name"
                                  className="flex-1 border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-1.5 text-[13px] bg-white text-[#3D4A44] focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                                />
                                <select
                                  value={newTagType}
                                  onChange={(e) => setNewTagType(e.target.value)}
                                  className="border border-[rgba(59,77,67,0.12)] rounded-lg px-2 py-1.5 text-[13px] bg-white text-[#3D4A44] focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                                >
                                  <option value="MOOD">Mood</option>
                                  <option value="TEXTURE">Texture</option>
                                  <option value="SYNC">Sync</option>
                                  <option value="USER">User</option>
                                </select>
                                <button
                                  onClick={() => { if (newTagName.trim()) addTag(asset.id, newTagName.trim(), newTagType) }}
                                  className="px-3 py-1.5 text-[12px] font-medium bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] transition-colors"
                                >
                                  Add
                                </button>
                                <button
                                  onClick={() => { setShowAddTag(null); setNewTagName(''); setNewTagType('MOOD') }}
                                  className="px-2 py-1.5 text-[12px] text-[#7A8580] hover:text-[#3D4A44] transition-colors"
                                >
                                  Cancel
                                </button>
                              </div>
                            ) : (
                              <button
                                onClick={() => setShowAddTag(asset.id)}
                                className="flex items-center gap-1 mt-1 text-[12px] font-medium text-[#5B8A72] hover:text-[#4A7A62] transition-colors"
                              >
                                <PlusIcon className="w-3.5 h-3.5" />
                                Add Tag
                              </button>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 bg-[#F5F7F4] rounded-[12px] border-2 border-dashed border-[rgba(59,77,67,0.08)]">
                    <SpeakerWaveIcon className="w-12 h-12 text-[#7A8580] mx-auto mb-3" />
                    <p className="text-[#3D4A44] font-medium">No audio files linked yet</p>
                    <p className="text-[13px] text-[#7A8580] mt-1">
                      {dropboxConnected ? 'Click "Link from Dropbox" to attach audio files' : 'Connect Dropbox in Settings to link audio files'}
                    </p>
                  </div>
                )}
              </div>

              {showDropboxPicker && (
                <div className="fixed inset-0 bg-black/30 backdrop-blur-sm z-[60] flex items-center justify-center p-4" onClick={() => setShowDropboxPicker(false)}>
                  <div className="bg-white rounded-[18px] shadow-[0px_8px_24px_rgba(0,0,0,0.15)] w-full max-w-lg max-h-[70vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
                    <div className="p-4 border-b border-[rgba(59,77,67,0.08)] flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <FolderOpenIcon className="w-5 h-5 text-[#5B8A72]" />
                        <h4 className="text-[16px] font-semibold text-[#3D4A44]">Browse Dropbox</h4>
                      </div>
                      <button onClick={() => setShowDropboxPicker(false)} className="text-[#7A8580] hover:text-[#3D4A44]">
                        <XMarkIcon className="w-5 h-5" />
                      </button>
                    </div>

                    <div className="px-4 py-2 border-b border-[rgba(59,77,67,0.08)] flex items-center gap-2 text-[13px] text-[#7A8580]">
                      {dropboxPath && (
                        <button
                          onClick={() => {
                            const parentPath = dropboxPath.split('/').slice(0, -1).join('/')
                            browseDropbox(parentPath)
                          }}
                          className="flex items-center gap-1 text-[#5B8A72] hover:text-[#4A7A62] font-medium"
                        >
                          <ArrowLeftIcon className="w-4 h-4" />
                          Back
                        </button>
                      )}
                      <span className="truncate">/{dropboxPath}</span>
                    </div>

                    <div className="flex-1 overflow-y-auto p-2">
                      {dropboxLoading ? (
                        <div className="text-center py-8 text-[#7A8580]">Loading...</div>
                      ) : dropboxFiles.length > 0 ? (
                        <div className="space-y-1">
                          {dropboxFiles.map((file, idx) => {
                            const isFolder = file['.tag'] === 'folder' || file.is_folder || file.type === 'folder'
                            const isAudio = !isFolder && isAudioFile(file.name)
                            const isSelected = selectedFiles.some(f => (f.path_display || f.path) === (file.path_display || file.path))

                            if (!isFolder && !isAudio) return null

                            return (
                              <button
                                key={idx}
                                onClick={() => {
                                  if (isFolder) {
                                    browseDropbox(file.path_display || file.path_lower || file.path)
                                  } else if (isAudio) {
                                    handleSelectFile(file)
                                  }
                                }}
                                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-[10px] text-left transition-colors ${
                                  isSelected ? 'bg-[rgba(91,138,114,0.12)] border border-[#5B8A72]' : 'hover:bg-[#F5F7F4] border border-transparent'
                                }`}
                              >
                                {isFolder ? (
                                  <FolderIcon className="w-5 h-5 text-[#C4956B] flex-shrink-0" />
                                ) : (
                                  <SpeakerWaveIcon className="w-5 h-5 text-[#5B8A72] flex-shrink-0" />
                                )}
                                <div className="flex-1 min-w-0">
                                  <p className="text-[14px] font-medium text-[#3D4A44] truncate">{file.name}</p>
                                  {!isFolder && file.size && (
                                    <p className="text-[12px] text-[#7A8580]">{formatFileSize(file.size)}</p>
                                  )}
                                </div>
                                {isSelected && (
                                  <CheckCircleIcon className="w-5 h-5 text-[#5B8A72] flex-shrink-0" />
                                )}
                              </button>
                            )
                          })}
                        </div>
                      ) : (
                        <div className="text-center py-8 text-[#7A8580] text-[14px]">No files found in this folder</div>
                      )}
                    </div>

                    {selectedFiles.length > 0 && (
                      <div className="p-4 border-t border-[rgba(59,77,67,0.08)] flex items-center justify-between">
                        <span className="text-[13px] text-[#7A8580]">{selectedFiles.length} file{selectedFiles.length > 1 ? 's' : ''} selected</span>
                        <button
                          onClick={handleLinkSelected}
                          className="px-4 py-2 bg-[#5B8A72] text-white rounded-[12px] font-medium text-[14px] hover:bg-[#4A7A62] transition-colors"
                        >
                          Link Selected
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
      {shareTarget && (
        <ShareModal
          itemType={shareTarget.type}
          itemId={shareTarget.id}
          itemName={shareTarget.name}
          onClose={() => setShareTarget(null)}
        />
      )}
    </div>
  )
}
