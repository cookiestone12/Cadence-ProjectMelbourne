import React, { useState, useEffect, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import axios from 'axios'
import { 
  FunnelIcon, MagnifyingGlassIcon, PlusIcon, ArrowUpTrayIcon,
  CheckCircleIcon, XCircleIcon, MinusCircleIcon, LinkIcon, TrashIcon,
  SpeakerWaveIcon, ChevronDownIcon, ChevronUpIcon, ArrowPathIcon,
  DocumentDuplicateIcon, AdjustmentsHorizontalIcon, XMarkIcon,
  ArrowUpIcon, ArrowDownIcon, ArrowsUpDownIcon,
  DocumentTextIcon, MusicalNoteIcon
} from '@heroicons/react/24/outline'
import SongDetailModal from '../components/SongDetailModal'
import AddSongModal from '../components/AddSongModal'
import ScheduleAUploadModal from '../components/ScheduleAUploadModal'

export default function NewCatalogPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [songs, setSongs] = useState([])
  const [works, setWorks] = useState([])
  const [creators, setCreators] = useState([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [activeTab, setActiveTab] = useState('all')
  const [recordingsSubFilter, setRecordingsSubFilter] = useState('all')
  const [selectedSong, setSelectedSong] = useState(null)
  const [showAddModal, setShowAddModal] = useState(false)
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [organizationId, setOrganizationId] = useState(null)
  const [spotifyModal, setSpotifyModal] = useState({ open: false, song: null, link: '' })
  const [filters, setFilters] = useState({
    creator_id: '',
    role: '',
    min_health: '',
    max_health: '',
    status: ''
  })
  const [showFilters, setShowFilters] = useState(false)
  const [sortField, setSortField] = useState('title')
  const [sortDirection, setSortDirection] = useState('asc')

  const [selectedSongIds, setSelectedSongIds] = useState(new Set())
  const [showBulkEditModal, setShowBulkEditModal] = useState(false)
  const [bulkEditFields, setBulkEditFields] = useState({})
  const [bulkEditLoading, setBulkEditLoading] = useState(false)

  const [showSpotifyImportModal, setShowSpotifyImportModal] = useState(false)
  const [spotifyPlaylistUrl, setSpotifyPlaylistUrl] = useState('')
  const [spotifyCreatorId, setSpotifyCreatorId] = useState('')
  const [spotifyPreviewTracks, setSpotifyPreviewTracks] = useState(null)
  const [spotifySelectedTracks, setSpotifySelectedTracks] = useState(new Set())
  const [spotifyPreviewLoading, setSpotifyPreviewLoading] = useState(false)
  const [spotifyImportLoading, setSpotifyImportLoading] = useState(false)
  const [spotifyImportResult, setSpotifyImportResult] = useState(null)
  const [showQuickCreator, setShowQuickCreator] = useState(false)
  const [quickCreatorName, setQuickCreatorName] = useState('')
  const [showDuplicateModal, setShowDuplicateModal] = useState(false)
  const [duplicateGroups, setDuplicateGroups] = useState([])
  const [showMergeModal, setShowMergeModal] = useState(false)
  const [mergeGroupSongs, setMergeGroupSongs] = useState([])
  const [mergePrimaryId, setMergePrimaryId] = useState(null)
  const [merging, setMerging] = useState(false)
  const [duplicateLoading, setDuplicateLoading] = useState(false)

  const [entryTypeFilter, setEntryTypeFilter] = useState('')

  const [audioData, setAudioData] = useState({})
  const [audioColumnsEnabled, setAudioColumnsEnabled] = useState(false)
  const [audioDataLoading, setAudioDataLoading] = useState(false)
  const [showAudioFilters, setShowAudioFilters] = useState(false)
  const [audioFilters, setAudioFilters] = useState({
    audioLinked: '',
    analyzed: '',
    bpmMin: '',
    bpmMax: '',
    musicalKey: '',
    mood: [],
    vocal: ''
  })

  const MUSICAL_KEYS = [
    'C major', 'C minor', 'C# major', 'C# minor',
    'D major', 'D minor', 'D# major', 'D# minor',
    'E major', 'E minor',
    'F major', 'F minor', 'F# major', 'F# minor',
    'G major', 'G minor', 'G# major', 'G# minor',
    'A major', 'A minor', 'A# major', 'A# minor',
    'B major', 'B minor'
  ]
  const MOOD_OPTIONS = ['uplifting', 'melancholic', 'tense', 'dreamy', 'energetic', 'calm']
  const MOOD_COLORS = {
    uplifting: 'bg-amber-100 text-amber-800',
    melancholic: 'bg-blue-100 text-blue-800',
    tense: 'bg-red-100 text-red-800',
    dreamy: 'bg-purple-100 text-purple-800',
    energetic: 'bg-orange-100 text-orange-800',
    calm: 'bg-teal-100 text-teal-800'
  }

  const ALL_COLUMNS = [
    { key: 'title', label: 'Song', sortable: true, required: true },
    { key: 'primary_artist', label: 'Artist', sortable: true },
    { key: 'client_name', label: 'Client', sortable: true },
    { key: 'label', label: 'Label', sortable: true },
    { key: 'publishing_percentage', label: 'Pub %', sortable: true },
    { key: 'status_health_score', label: 'Health', sortable: true },
    { key: 'is_released', label: 'Released', sortable: true, align: 'center' },
    { key: 'spotify_link', label: 'Spotify', sortable: true },
    { key: 'has_contract_executed', label: 'Contract', sortable: true },
    { key: 'is_registered_with_pro', label: 'PRO', sortable: true },
    { key: 'isrc', label: 'ISRC', sortable: true },
    { key: 'release_date', label: 'Release Date', sortable: true },
    { key: 'project_title', label: 'Project', sortable: true },
    { key: 'iswc', label: 'ISWC', sortable: true },
  ]

  const DEFAULT_VISIBLE = ['title', 'primary_artist', 'label', 'publishing_percentage', 'status_health_score', 'is_released', 'spotify_link', 'has_contract_executed', 'is_registered_with_pro']

  const [visibleColumns, setVisibleColumns] = useState(() => {
    try {
      const stored = localStorage.getItem('cadence_catalog_columns')
      if (stored) {
        const parsed = JSON.parse(stored)
        const validKeys = ALL_COLUMNS.map(c => c.key)
        if (Array.isArray(parsed) && parsed.length > 0) {
          const cleaned = [...new Set(parsed.filter(k => validKeys.includes(k)))]
          if (!cleaned.includes('title')) cleaned.unshift('title')
          if (cleaned.length > 0) return cleaned
        }
      }
    } catch {}
    return DEFAULT_VISIBLE
  })
  const [showColumnConfig, setShowColumnConfig] = useState(false)
  const columnConfigRef = useRef(null)

  const [columnWidths, setColumnWidths] = useState(() => {
    try {
      const stored = localStorage.getItem('cadence_catalog_col_widths')
      if (stored) {
        const parsed = JSON.parse(stored)
        if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
          const cleaned = {}
          for (const [k, v] of Object.entries(parsed)) {
            if (typeof v === 'number' && v > 0 && isFinite(v)) cleaned[k] = v
          }
          return cleaned
        }
      }
    } catch {}
    return {}
  })
  const deepLinkHandled = useRef(false)
  useEffect(() => {
    if (deepLinkHandled.current) return
    const songIdParam = searchParams.get('songId')
    if (songIdParam && songs.length > 0) {
      const match = songs.find(s => String(s.id) === songIdParam)
      if (match) {
        setSelectedSong(match)
        deepLinkHandled.current = true
        setSearchParams({}, { replace: true })
      }
    }
  }, [searchParams, songs])

  useEffect(() => {
    localStorage.setItem('cadence_catalog_columns', JSON.stringify(visibleColumns))
  }, [visibleColumns])

  useEffect(() => {
    if (Object.keys(columnWidths).length > 0) {
      localStorage.setItem('cadence_catalog_col_widths', JSON.stringify(columnWidths))
    } else {
      localStorage.removeItem('cadence_catalog_col_widths')
    }
  }, [columnWidths])

  const handleResizeStart = (e, colKey) => {
    if (e.type === 'touchstart') return
    e.preventDefault()
    e.stopPropagation()
    const startX = e.clientX
    const th = e.currentTarget.parentElement
    if (!th) return
    const startWidth = th.offsetWidth
    const savedColKey = colKey

    const handleMove = (moveEvent) => {
      moveEvent.preventDefault()
      const diff = moveEvent.clientX - startX
      const newWidth = Math.max(60, startWidth + diff)
      setColumnWidths(prev => ({ ...prev, [savedColKey]: newWidth }))
    }

    const handleEnd = () => {
      document.removeEventListener('mousemove', handleMove)
      document.removeEventListener('mouseup', handleEnd)
    }

    document.addEventListener('mousemove', handleMove)
    document.addEventListener('mouseup', handleEnd)
  }

  const toggleColumn = (key) => {
    setVisibleColumns(prev => {
      if (prev.includes(key)) return prev.filter(k => k !== key)
      return [...prev, key]
    })
  }

  const moveColumn = (fromIdx, toIdx) => {
    setVisibleColumns(prev => {
      const updated = [...prev]
      const [moved] = updated.splice(fromIdx, 1)
      updated.splice(toIdx, 0, moved)
      return updated
    })
  }

  const activeColumns = visibleColumns
    .map(key => ALL_COLUMNS.find(c => c.key === key))
    .filter(Boolean)

  const SortArrow = ({ field }) => {
    if (sortField === field) {
      return sortDirection === 'asc'
        ? <ArrowUpIcon className="w-3.5 h-3.5 text-[#5B8A72]" />
        : <ArrowDownIcon className="w-3.5 h-3.5 text-[#5B8A72]" />
    }
    return <ArrowsUpDownIcon className="w-3.5 h-3.5 text-[#B0BDB4]" />
  }

  useEffect(() => {
    loadData()
  }, [filters])
  
  async function loadData() {
    try {
      const orgResponse = await axios.get('/api/organizations/current')
      const orgId = orgResponse.data?.id
      setOrganizationId(orgId)
      if (!orgId) { setLoading(false); return }
      
      const params = new URLSearchParams()
      if (filters.creator_id) params.append('creator_id', filters.creator_id)
      if (filters.role) params.append('role', filters.role)
      if (filters.min_health) params.append('min_health', filters.min_health)
      if (filters.max_health) params.append('max_health', filters.max_health)
      if (filters.status) params.append('status', filters.status)
      params.append('limit', '1000')
      
      axios.get(`/api/songs/org/${orgId}?${params}`)
        .then(res => setSongs(res.data || []))
        .catch(err => console.error('Failed to load songs:', err))
        .finally(() => setLoading(false))

      axios.get(`/api/works/org/${orgId}?limit=500`)
        .then(res => setWorks(res.data?.works || []))
        .catch(err => console.error('Failed to load works:', err))

      axios.get(`/api/creators/org/${orgId}`)
        .then(res => setCreators(res.data || []))
        .catch(err => console.error('Failed to load creators:', err))
    } catch (error) {
      console.error('Failed to load catalog:', error)
      setLoading(false)
    }
  }

  const loadAudioData = async (songIds) => {
    if (!songIds || songIds.length === 0) return
    setAudioDataLoading(true)
    const data = {}
    const batchSize = 10
    for (let i = 0; i < songIds.length; i += batchSize) {
      const batch = songIds.slice(i, i + batchSize)
      await Promise.all(batch.map(async (id) => {
        try {
          const res = await axios.get(`/api/audio/song/${id}`)
          data[id] = res.data?.assets || res.data || []
        } catch (e) {
          data[id] = []
        }
      }))
    }
    setAudioData(data)
    setAudioDataLoading(false)
  }

  useEffect(() => {
    if (audioColumnsEnabled && songs.length > 0) {
      const songIds = songs.map(s => s.id)
      loadAudioData(songIds)
    }
  }, [audioColumnsEnabled, songs])

  const hasActiveAudioFilters = audioFilters.audioLinked !== '' || audioFilters.analyzed !== '' ||
    audioFilters.bpmMin !== '' || audioFilters.bpmMax !== '' || audioFilters.musicalKey !== '' ||
    audioFilters.mood.length > 0 || audioFilters.vocal !== ''

  const clearAudioFilters = () => {
    setAudioFilters({ audioLinked: '', analyzed: '', bpmMin: '', bpmMax: '', musicalKey: '', mood: [], vocal: '' })
  }

  const toggleMoodFilter = (mood) => {
    setAudioFilters(prev => ({
      ...prev,
      mood: prev.mood.includes(mood) ? prev.mood.filter(m => m !== mood) : [...prev.mood, mood]
    }))
  }
  
  const filteredSongs = songs.filter(song => {
    const matchesSearch = !searchTerm || (
      song.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      song.primary_artist.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (song.client_name && song.client_name.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (song.project_title && song.project_title.toLowerCase().includes(searchTerm.toLowerCase()))
    )
    
    const matchesTab = activeTab === 'all' || activeTab === 'released' || activeTab === 'unreleased'
    
    let matchesSubFilter = true
    if (activeTab === 'released') {
      matchesSubFilter = (song.release_status || (song.is_released ? 'released' : 'unreleased')) === 'released'
    } else if (activeTab === 'unreleased') {
      matchesSubFilter = (song.release_status || (song.is_released ? 'released' : 'unreleased')) === 'unreleased'
      if (matchesSubFilter && entryTypeFilter) {
        matchesSubFilter = (song.entry_type || 'Song') === entryTypeFilter
      }
    }

    let matchesAudio = true
    if (hasActiveAudioFilters && audioColumnsEnabled) {
      const songAudio = audioData[song.id] || []
      const hasAudio = songAudio.length > 0
      const analysis = songAudio[0]?.analysis || null
      const hasAnalysis = !!analysis

      if (audioFilters.audioLinked === 'yes' && !hasAudio) matchesAudio = false
      if (audioFilters.audioLinked === 'no' && hasAudio) matchesAudio = false
      if (audioFilters.analyzed === 'yes' && !hasAnalysis) matchesAudio = false
      if (audioFilters.analyzed === 'no' && hasAnalysis) matchesAudio = false
      if (audioFilters.bpmMin && analysis?.bpm && parseFloat(analysis.bpm) < parseFloat(audioFilters.bpmMin)) matchesAudio = false
      if (audioFilters.bpmMax && analysis?.bpm && parseFloat(analysis.bpm) > parseFloat(audioFilters.bpmMax)) matchesAudio = false
      if (audioFilters.bpmMin && !analysis?.bpm) matchesAudio = false
      if (audioFilters.bpmMax && !analysis?.bpm) matchesAudio = false
      if (audioFilters.musicalKey && analysis?.musical_key !== audioFilters.musicalKey) matchesAudio = false
      if (audioFilters.mood.length > 0) {
        const songMoods = analysis?.mood_tags || []
        if (!audioFilters.mood.some(m => songMoods.includes(m))) matchesAudio = false
      }
      if (audioFilters.vocal === 'vocal' && analysis?.has_vocals !== true) matchesAudio = false
      if (audioFilters.vocal === 'instrumental' && analysis?.has_vocals !== false) matchesAudio = false
    }
    
    return matchesSearch && matchesTab && matchesSubFilter && matchesAudio
  })

  const sortedSongs = [...filteredSongs].sort((a, b) => {
    const dir = sortDirection === 'asc' ? 1 : -1
    const valA = a[sortField]
    const valB = b[sortField]
    if (valA == null && valB == null) return 0
    if (valA == null) return 1
    if (valB == null) return -1
    if (typeof valA === 'string') return valA.localeCompare(valB) * dir
    if (typeof valA === 'boolean') return ((valA ? 1 : 0) - (valB ? 1 : 0)) * dir
    return (valA - valB) * dir
  })
  
  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }))
  }
  
  const clearFilters = () => {
    setFilters({
      creator_id: '',
      role: '',
      min_health: '',
      max_health: '',
      status: ''
    })
  }

  const handleSort = (field) => {
    if (sortField === field) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('asc')
    }
  }
  
  const getStatusIcon = (value) => {
    if (value === 'Yes') return <CheckCircleIcon className="w-5 h-5 text-[#5B9A6E]" />
    if (value === 'No') return <XCircleIcon className="w-5 h-5 text-[#C47068]" />
    return <MinusCircleIcon className="w-5 h-5 text-[#7A8580]" />
  }
  
  const filteredWorks = works.filter(work => {
    if (!searchTerm) return true
    const term = searchTerm.toLowerCase()
    return work.title.toLowerCase().includes(term) ||
      (work.iswc && work.iswc.toLowerCase().includes(term))
  })

  const [unifiedSortField, setUnifiedSortField] = useState('title')
  const [unifiedSortDir, setUnifiedSortDir] = useState('asc')

  const handleUnifiedSort = (field) => {
    if (unifiedSortField === field) {
      setUnifiedSortDir(prev => prev === 'asc' ? 'desc' : 'asc')
    } else {
      setUnifiedSortField(field)
      setUnifiedSortDir('asc')
    }
  }

  const unifiedItems = activeTab === 'all' ? [
    ...filteredSongs.map(s => ({ ...s, _itemType: 'recording', _sortTitle: s.title, _sortType: 'Recording' })),
    ...filteredWorks.map(w => ({
      _itemType: 'composition',
      _sortTitle: w.title,
      _sortType: 'Composition',
      id: w.id,
      title: w.title,
      primary_artist: '-',
      work_type: w.work_type,
      iswc: w.iswc,
      isrc: null,
      genre: w.genre,
      status: w.status || 'PENDING',
      track_count: w.track_count || 0,
      credit_count: w.credit_count || 0,
      folder_name: w.folder_name,
      created_at: w.created_at,
      is_released: null,
    }))
  ].sort((a, b) => {
    const dir = unifiedSortDir === 'asc' ? 1 : -1
    let valA, valB
    switch (unifiedSortField) {
      case 'title': valA = a._sortTitle; valB = b._sortTitle; break
      case '_sortType': valA = a._sortType; valB = b._sortType; break
      default: valA = a[unifiedSortField]; valB = b[unifiedSortField]
    }
    if (valA == null && valB == null) return 0
    if (valA == null) return 1
    if (valB == null) return -1
    if (typeof valA === 'string') return valA.localeCompare(valB) * dir
    return 0
  }) : []

  const hasActiveFilters = Object.values(filters).some(v => v !== '')
  
  const releasedCount = songs.filter(s => (s.release_status || (s.is_released ? 'released' : 'unreleased')) === 'released').length
  const unreleasedCount = songs.filter(s => (s.release_status || (s.is_released ? 'released' : 'unreleased')) === 'unreleased').length

  
  const handleReleasedToggle = async (e, song) => {
    e.stopPropagation()
    const newReleasedState = !song.is_released
    
    if (newReleasedState && !song.spotify_link) {
      setSpotifyModal({ open: true, song, link: '' })
    } else {
      try {
        await axios.put(`/api/songs/${song.id}`, { is_released: newReleasedState })
        setSongs(prev => prev.map(s => 
          s.id === song.id ? { ...s, is_released: newReleasedState } : s
        ))
      } catch (error) {
        console.error('Failed to update released status:', error)
      }
    }
  }
  
  const handleSpotifyLinkSave = async () => {
    if (!spotifyModal.song) return
    
    try {
      await axios.put(`/api/songs/${spotifyModal.song.id}`, { 
        is_released: true,
        spotify_link: spotifyModal.link || null 
      })
      setSongs(prev => prev.map(s => 
        s.id === spotifyModal.song.id 
          ? { ...s, is_released: true, spotify_link: spotifyModal.link || null } 
          : s
      ))
      setSpotifyModal({ open: false, song: null, link: '' })
    } catch (error) {
      console.error('Failed to save Spotify link:', error)
    }
  }
  
  const openSpotifyLink = (e, link) => {
    e.stopPropagation()
    if (link) {
      window.open(link, '_blank')
    }
  }

  const toggleSongSelection = (e, songId) => {
    e.stopPropagation()
    setSelectedSongIds(prev => {
      const next = new Set(prev)
      if (next.has(songId)) {
        next.delete(songId)
      } else {
        next.add(songId)
      }
      return next
    })
  }

  const selectAllSongs = () => {
    setSelectedSongIds(new Set(filteredSongs.map(s => s.id)))
  }

  const clearSelection = () => {
    setSelectedSongIds(new Set())
  }

  const openBulkEditModal = () => {
    setBulkEditFields({})
    setShowBulkEditModal(true)
  }

  const handleBulkEditFieldChange = (field, value) => {
    setBulkEditFields(prev => ({ ...prev, [field]: value }))
  }

  const handleBulkEditSubmit = async () => {
    if (!organizationId || selectedSongIds.size === 0) return
    const updates = {}
    Object.entries(bulkEditFields).forEach(([key, val]) => {
      if (val !== '' && val !== undefined && val !== null) {
        if (key === 'publishing_percentage' || key === 'master_percentage') {
          updates[key] = parseFloat(val)
        } else {
          updates[key] = val
        }
      }
    })
    if (Object.keys(updates).length === 0) return
    setBulkEditLoading(true)
    try {
      await axios.put(`/api/bulk/songs/${organizationId}`, {
        song_ids: Array.from(selectedSongIds),
        updates
      })
      setShowBulkEditModal(false)
      setSelectedSongIds(new Set())
      setLoading(true)
      await loadData()
    } catch (error) {
      console.error('Bulk edit failed:', error)
    } finally {
      setBulkEditLoading(false)
    }
  }

  const handleDuplicateSong = async (songId, e) => {
    if (e) e.stopPropagation()
    try {
      const res = await axios.post(`/api/songs/${songId}/duplicate`)
      const newSong = res.data
      setSongs(prev => [newSong, ...prev])
      setSelectedSong(newSong)
    } catch (error) {
      console.error('Failed to duplicate song:', error)
      alert(error.response?.data?.detail || 'Failed to duplicate song')
    }
  }

  const handleDeleteSong = async (songId, songTitle) => {
    if (!window.confirm(`Are you sure you want to delete "${songTitle}"? This cannot be undone.`)) return
    setSongs(prev => prev.filter(s => s.id !== songId))
    try {
      await axios.delete(`/api/songs/${songId}`)
    } catch (error) {
      console.error('Failed to delete song:', error)
      alert(error.response?.data?.detail || 'Failed to delete song')
      loadData()
    }
  }

  const handleBulkDelete = async () => {
    const count = selectedSongIds.size
    if (!window.confirm(`Are you sure you want to delete ${count} song${count !== 1 ? 's' : ''}? This cannot be undone.`)) return
    const idsToDelete = new Set(selectedSongIds)
    setSongs(prev => prev.filter(s => !idsToDelete.has(s.id)))
    setSelectedSongIds(new Set())
    try {
      await axios.post('/api/songs/bulk-delete', { song_ids: Array.from(idsToDelete) })
    } catch (error) {
      console.error('Failed to delete songs:', error)
      alert(error.response?.data?.detail || 'Failed to delete songs')
      loadData()
    }
  }

  const handleFindDuplicates = async () => {
    if (!organizationId) return
    setDuplicateLoading(true)
    setShowDuplicateModal(true)
    try {
      const res = await axios.get(`/api/songs/org/${organizationId}/duplicates`)
      setDuplicateGroups(res.data.groups || [])
    } catch (error) {
      console.error('Failed to find duplicates:', error)
    } finally {
      setDuplicateLoading(false)
    }
  }

  const handleDeleteDuplicate = async (songId, songTitle) => {
    if (!window.confirm(`Delete "${songTitle}"?`)) return
    setSongs(prev => prev.filter(s => s.id !== songId))
    setDuplicateGroups(prev => 
      prev.map(group => group.filter(s => s.id !== songId)).filter(g => g.length > 1)
    )
    try {
      await axios.delete(`/api/songs/${songId}`)
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to delete')
      loadData()
    }
  }

  const openMergeForGroup = (group) => {
    setMergeGroupSongs(group)
    setMergePrimaryId(group[0]?.id || null)
    setShowMergeModal(true)
  }

  const handleMergeSongs = async () => {
    if (!mergePrimaryId || mergeGroupSongs.length < 2 || !organizationId) return
    setMerging(true)
    try {
      const mergeIds = mergeGroupSongs.filter(s => s.id !== mergePrimaryId).map(s => s.id)
      await axios.post(`/api/songs/org/${organizationId}/merge`, {
        primary_song_id: mergePrimaryId,
        merge_song_ids: mergeIds,
      })
      setShowMergeModal(false)
      setMergeGroupSongs([])
      setMergePrimaryId(null)
      setSelectedSongIds(new Set())
      setDuplicateGroups(prev =>
        prev.filter(group => {
          const groupIds = new Set(group.map(s => s.id))
          return !mergeGroupSongs.some(s => groupIds.has(s.id))
        })
      )
      loadData()
    } catch (err) {
      alert('Failed to merge songs: ' + (err.response?.data?.detail || err.message))
    } finally {
      setMerging(false)
    }
  }

  const handleSpotifyPreview = async () => {
    if (!organizationId || !spotifyPlaylistUrl) return
    setSpotifyPreviewLoading(true)
    setSpotifyImportResult(null)
    try {
      const res = await axios.post(`/api/spotify/playlist/preview/${organizationId}`, {
        playlist_url: spotifyPlaylistUrl
      })
      setSpotifyPreviewTracks(res.data.tracks)
      setSpotifySelectedTracks(new Set(res.data.tracks.map((t, i) => (!t.already_exists && !t.potential_duplicate) ? i : null).filter(i => i !== null)))
    } catch (error) {
      console.error('Spotify preview failed:', error)
      const message = error?.response?.data?.detail || error?.message || 'Failed to load playlist. Please check the URL and try again.'
      setSpotifyImportResult({ error: true, message })
    } finally {
      setSpotifyPreviewLoading(false)
    }
  }

  const toggleSpotifyTrack = (index) => {
    setSpotifySelectedTracks(prev => {
      const next = new Set(prev)
      if (next.has(index)) {
        next.delete(index)
      } else {
        next.add(index)
      }
      return next
    })
  }

  const handleSpotifyImport = async () => {
    if (!organizationId || !spotifyPreviewTracks || spotifySelectedTracks.size === 0) return
    setSpotifyImportLoading(true)
    try {
      const tracks = Array.from(spotifySelectedTracks).map(i => {
        const t = spotifyPreviewTracks[i]
        return {
          title: t.title || t.name,
          primary_artist: t.primary_artist || t.artist || (t.all_artists && t.all_artists[0]) || '',
          all_artists: t.all_artists || [],
          isrc: t.isrc || null,
          release_date: t.release_date || null,
          spotify_url: t.spotify_url || t.external_url || null,
          album_name: t.album_name || t.album || null,
          explicit: t.explicit || false,
          track_number: t.track_number || null,
          duration_ms: t.duration_ms || null,
          popularity: t.popularity || null
        }
      })
      const res = await axios.post(`/api/spotify/playlist/import/${organizationId}`, {
        tracks,
        creator_id: spotifyCreatorId ? parseInt(spotifyCreatorId) : null
      })
      setSpotifyImportResult(res.data)
      setSpotifyPreviewTracks(null)
      setLoading(true)
      await loadData()
    } catch (error) {
      console.error('Spotify import failed:', error)
      const message = error?.response?.data?.detail || error?.message || 'Import failed. Please try again.'
      setSpotifyImportResult({ error: true, message })
    } finally {
      setSpotifyImportLoading(false)
    }
  }

  const closeSpotifyImportModal = () => {
    setShowSpotifyImportModal(false)
    setSpotifyPlaylistUrl('')
    setSpotifyCreatorId('')
    setSpotifyPreviewTracks(null)
    setSpotifySelectedTracks(new Set())
    setSpotifyImportResult(null)
    setShowQuickCreator(false)
    setQuickCreatorName('')
  }

  const handleQuickCreatorCreate = async () => {
    if (!organizationId || !quickCreatorName.trim()) return
    try {
      const res = await axios.post(`/api/creators/org/${organizationId}`, {
        display_name: quickCreatorName.trim(),
        roles: ['ARTIST']
      })
      const newCreator = res.data
      const creatorsRes = await axios.get(`/api/creators/org/${organizationId}`)
      setCreators(creatorsRes.data || [])
      setSpotifyCreatorId(String(newCreator.id))
      setShowQuickCreator(false)
      setQuickCreatorName('')
    } catch (error) {
      console.error('Failed to create creator:', error)
    }
  }
  
  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-[#7A8580]">Loading catalog...</div>
      </div>
    )
  }
  
  return (
    <div className="p-4 sm:p-8 pb-24">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl sm:text-4xl font-bold text-[#3D4A44] mb-2">Catalog</h1>
          <p className="text-[#7A8580]">{songs.length} recordings, {works.length} compositions</p>
        </div>
        <div className="flex items-center gap-2 sm:gap-3 flex-wrap justify-end">
          <button
            className="p-1.5 sm:p-2 text-[#7A8580] hover:text-[#5B8A72] hover:bg-[#E8F0EB] rounded-lg transition-colors"
            onClick={async () => { setRefreshing(true); try { await loadData(); } finally { setRefreshing(false); } }}
            title="Refresh catalog"
          >
            <ArrowPathIcon className={`w-5 h-5 ${refreshing ? 'animate-spin' : ''}`} />
          </button>
          <button 
            className="flex items-center space-x-1.5 px-2.5 py-1.5 sm:px-4 sm:py-2 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] transition-colors text-xs sm:text-sm whitespace-nowrap"
            onClick={() => setShowAddModal(true)}
          >
            <PlusIcon className="w-4 h-4 sm:w-5 sm:h-5" />
            <span>Add Song</span>
          </button>
          <button 
            className="flex items-center space-x-1.5 px-2.5 py-1.5 sm:px-4 sm:py-2 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-lg hover:shadow-[0px_4px_12px_rgba(91,138,114,0.3)] transition-all text-xs sm:text-sm whitespace-nowrap"
            onClick={() => setShowUploadModal(true)}
          >
            <ArrowUpTrayIcon className="w-4 h-4 sm:w-5 sm:h-5" />
            <span>Schedule A</span>
          </button>
          <button
            onClick={handleFindDuplicates}
            className="px-4 py-2.5 bg-[#EEF1EC] text-[#3D4A44] rounded-xl text-sm font-medium hover:bg-[#D8DDD6] transition-colors flex items-center space-x-2"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 17.25v3.375c0 .621-.504 1.125-1.125 1.125h-9.75a1.125 1.125 0 01-1.125-1.125V7.875c0-.621.504-1.125 1.125-1.125H6.75a9.06 9.06 0 011.5.124m7.5 10.376h3.375c.621 0 1.125-.504 1.125-1.125V11.25c0-4.46-3.243-8.161-7.5-8.876a9.06 9.06 0 00-1.5-.124H9.375c-.621 0-1.125.504-1.125 1.125v3.5m7.5 10.375H9.375a1.125 1.125 0 01-1.125-1.125v-9.25m12 6.625v-1.875a3.375 3.375 0 00-3.375-3.375h-1.5a1.125 1.125 0 01-1.125-1.125v-1.5a3.375 3.375 0 00-3.375-3.375H9.75" />
            </svg>
            <span>Duplicates</span>
          </button>
          <button 
            className="flex items-center space-x-1.5 px-2.5 py-1.5 sm:px-4 sm:py-2 bg-[#1DB954] text-white rounded-lg hover:bg-[#1aa34a] transition-colors text-xs sm:text-sm whitespace-nowrap"
            onClick={() => setShowSpotifyImportModal(true)}
          >
            <svg className="w-4 h-4 sm:w-5 sm:h-5" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
            </svg>
            <span>Spotify</span>
          </button>
        </div>
      </div>
      
      <div className="mb-6 border-b border-[rgba(59,77,67,0.08)] overflow-x-auto">
        <div className="flex space-x-4 sm:space-x-8 min-w-max">
          <button
            onClick={() => { setActiveTab('all'); setEntryTypeFilter('') }}
            className={`pb-3 px-1 border-b-2 font-medium transition-colors ${
              activeTab === 'all'
                ? 'border-[#5B8A72] text-[#5B8A72]'
                : 'border-transparent text-[#7A8580] hover:text-[#3D4A44]'
            }`}
          >
            All ({songs.length})
          </button>
          <button
            onClick={() => { setActiveTab('released'); setEntryTypeFilter('') }}
            className={`pb-3 px-1 border-b-2 font-medium transition-colors ${
              activeTab === 'released'
                ? 'border-[#5B8A72] text-[#5B8A72]'
                : 'border-transparent text-[#7A8580] hover:text-[#3D4A44]'
            }`}
          >
            Released ({releasedCount})
          </button>
          <button
            onClick={() => setActiveTab('unreleased')}
            className={`pb-3 px-1 border-b-2 font-medium transition-colors ${
              activeTab === 'unreleased'
                ? 'border-[#5B8A72] text-[#5B8A72]'
                : 'border-transparent text-[#7A8580] hover:text-[#3D4A44]'
            }`}
          >
            Unreleased ({unreleasedCount})
          </button>
        </div>
      </div>

      {activeTab === 'unreleased' && (
        <div className="mb-4 flex items-center gap-2 flex-wrap">
          {['', 'Song', 'Instrumental', 'Remix', 'Sample', 'Demo'].map(type => (
            <button
              key={type}
              onClick={() => setEntryTypeFilter(type)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                entryTypeFilter === type
                  ? 'bg-[#5B8A72] text-white'
                  : 'bg-[#EEF1EC] text-[#3D4A44] hover:bg-[#E4E8E2]'
              }`}
            >
              {type || 'All Types'}
            </button>
          ))}
        </div>
      )}
      
      {activeTab === 'all' && (
        <div className="bg-[#FAFBF9] rounded-xl shadow-sm overflow-hidden">
          <div className="p-4">
            <div className="flex-1 relative">
              <MagnifyingGlassIcon className="w-5 h-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-[#7A8580]" />
              <input
                type="text"
                placeholder="Search recordings and compositions..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
              />
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[700px]">
              <thead className="bg-[#EEF1EC] border-b border-[rgba(59,77,67,0.08)]">
                <tr>
                  {[
                    { key: '_sortType', label: 'Type', align: 'left', w: 'w-24' },
                    { key: 'title', label: 'Title', align: 'left' },
                    { key: null, label: 'Artist / Info', align: 'left' },
                    { key: null, label: 'ISRC / ISWC', align: 'left' },
                    { key: null, label: 'Status', align: 'center' },
                  ].map((col, i) => (
                    <th
                      key={i}
                      className={`px-4 py-3 text-${col.align} text-xs font-semibold text-[#3D4A44] ${col.w || ''} ${col.key ? 'cursor-pointer select-none hover:bg-[rgba(59,77,67,0.08)]' : ''} transition-colors`}
                      onClick={() => col.key && handleUnifiedSort(col.key)}
                    >
                      <div className={`flex items-center ${col.align === 'center' ? 'justify-center' : ''} space-x-1`}>
                        <span>{col.label}</span>
                        {col.key && (
                          unifiedSortField === col.key
                            ? (unifiedSortDir === 'asc' ? <ArrowUpIcon className="w-3.5 h-3.5 text-[#5B8A72]" /> : <ArrowDownIcon className="w-3.5 h-3.5 text-[#5B8A72]" />)
                            : <ArrowsUpDownIcon className="w-3.5 h-3.5 text-[#B0BDB4]" />
                        )}
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-[rgba(59,77,67,0.08)]">
                {unifiedItems.map(item => (
                  <tr
                    key={`${item._itemType}-${item.id}`}
                    onClick={() => {
                      if (item._itemType === 'recording') {
                        setSelectedSong(item)
                      } else {
                        navigate(`/catalog/unreleased?workId=${item.id}`)
                      }
                    }}
                    className="group hover:bg-[rgba(91,138,114,0.06)] cursor-pointer transition-colors"
                  >
                    <td className="px-4 py-3">
                      {item._itemType === 'recording' ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700">
                          <MusicalNoteIcon className="w-3 h-3 mr-1" />
                          Recording
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-purple-50 text-purple-700">
                          <DocumentTextIcon className="w-3 h-3 mr-1" />
                          Composition
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-medium text-[#3D4A44] truncate">{item.title}</div>
                      {item._itemType === 'composition' && item.folder_name && (
                        <div className="text-xs text-[#7A8580] truncate">{item.folder_name}</div>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm text-[#7A8580]">
                      {item._itemType === 'recording' ? (
                        <span className="truncate block">{item.primary_artist}</span>
                      ) : (
                        <span className="truncate block">{item.track_count} track{item.track_count !== 1 ? 's' : ''}, {item.credit_count} credit{item.credit_count !== 1 ? 's' : ''}</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm text-[#7A8580] font-mono">
                      {item._itemType === 'recording' ? (item.isrc || '-') : (item.iswc || '-')}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {item._itemType === 'recording' ? (
                        item.is_released ? (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-50 text-green-700">Released</span>
                        ) : (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">Unreleased</span>
                        )
                      ) : (
                        item.status === 'APPROVED' ? (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-50 text-green-700">Approved</span>
                        ) : item.status === 'REJECTED' ? (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-50 text-red-700">Rejected</span>
                        ) : (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-700">Pending</span>
                        )
                      )}
                    </td>
                  </tr>
                ))}
                {unifiedItems.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-6 py-12 text-center text-[#7A8580]">
                      No catalog items found
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {(activeTab === 'released' || activeTab === 'unreleased') && (<>
      <div className="bg-[#FAFBF9] rounded-xl shadow-sm p-4 mb-6">
        <div className="flex items-center space-x-4 mb-3 sm:mb-0">
          <div className="flex-1 relative">
            <MagnifyingGlassIcon className="w-5 h-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-[#7A8580]" />
            <input
              type="text"
              placeholder="Search songs, artists, or projects..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
            />
          </div>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`flex items-center space-x-2 px-3 sm:px-4 py-2 rounded-lg transition-colors text-sm ${
              hasActiveFilters 
                ? 'bg-[#5B8A72] text-white' 
                : 'bg-[#EEF1EC] text-[#3D4A44] hover:bg-[#E4E8E2]'
            }`}
          >
            <FunnelIcon className="w-4 h-4 sm:w-5 sm:h-5" />
            <span>Filters</span>
            {hasActiveFilters && (
              <span className="bg-white text-[#5B8A72] px-2 py-0.5 rounded-full text-xs font-bold">
                {Object.values(filters).filter(v => v !== '').length}
              </span>
            )}
          </button>

          <button
            onClick={() => setAudioColumnsEnabled(!audioColumnsEnabled)}
            className={`flex items-center space-x-2 px-3 sm:px-4 py-2 rounded-lg transition-colors text-sm ${
              audioColumnsEnabled
                ? 'bg-[#5B8A72] text-white'
                : 'bg-[#EEF1EC] text-[#3D4A44] hover:bg-[#E4E8E2]'
            }`}
            title={audioColumnsEnabled ? 'Hide audio columns' : 'Show audio columns'}
          >
            <SpeakerWaveIcon className="w-4 h-4 sm:w-5 sm:h-5" />
            <span>Audio</span>
            {audioDataLoading && (
              <span className="w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin"></span>
            )}
          </button>

          <div className="relative" ref={columnConfigRef}>
            <button
              onClick={() => setShowColumnConfig(!showColumnConfig)}
              className={`flex items-center space-x-2 px-3 sm:px-4 py-2 rounded-lg transition-colors text-sm ${
                showColumnConfig
                  ? 'bg-[#5B8A72] text-white'
                  : 'bg-[#EEF1EC] text-[#3D4A44] hover:bg-[#E4E8E2]'
              }`}
              title="Configure columns"
            >
              <AdjustmentsHorizontalIcon className="w-4 h-4 sm:w-5 sm:h-5" />
              <span>Columns</span>
            </button>

            {showColumnConfig && (
              <div className="fixed inset-0 bg-black/30 backdrop-blur-sm z-50 flex items-end sm:items-center justify-center" onClick={() => setShowColumnConfig(false)}>
                <div className="bg-white w-full sm:w-80 sm:rounded-2xl rounded-t-2xl shadow-xl max-h-[80vh] flex flex-col" onClick={e => e.stopPropagation()}>
                  <div className="px-4 py-3 border-b border-[rgba(59,77,67,0.08)] flex items-center justify-between flex-shrink-0">
                    <span className="text-sm font-semibold text-[#3D4A44]">Table Columns</span>
                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => { setVisibleColumns(DEFAULT_VISIBLE); setColumnWidths({}) }}
                        className="text-xs text-[#5B8A72] hover:underline"
                      >
                        Reset
                      </button>
                      <button onClick={() => setShowColumnConfig(false)} className="text-[#7A8580] hover:text-[#3D4A44]">
                        <XMarkIcon className="w-5 h-5" />
                      </button>
                    </div>
                  </div>
                  <div className="overflow-y-auto py-1 flex-1">
                    {visibleColumns.map((key, idx) => {
                      const col = ALL_COLUMNS.find(c => c.key === key)
                      if (!col) return null
                      return (
                        <div
                          key={key}
                          className="flex items-center gap-1.5 px-3 py-2 hover:bg-[#F5F7F4] transition-colors"
                        >
                          <div className="flex flex-col flex-shrink-0">
                            <button
                              onClick={() => { if (idx > 0 && !col.required) moveColumn(idx, idx - 1) }}
                              disabled={idx === 0 || col.required}
                              className="p-0.5 text-[#B0BDB4] hover:text-[#5B8A72] disabled:opacity-30 disabled:cursor-default transition-colors"
                            >
                              <ChevronUpIcon className="w-3 h-3" />
                            </button>
                            <button
                              onClick={() => { if (idx < visibleColumns.length - 1 && !col.required) moveColumn(idx, idx + 1) }}
                              disabled={idx === visibleColumns.length - 1 || col.required}
                              className="p-0.5 text-[#B0BDB4] hover:text-[#5B8A72] disabled:opacity-30 disabled:cursor-default transition-colors"
                            >
                              <ChevronDownIcon className="w-3 h-3" />
                            </button>
                          </div>
                          <span className="flex-1 text-sm text-[#3D4A44]">{col.label}</span>
                          <button
                            onClick={() => !col.required && toggleColumn(key)}
                            disabled={col.required}
                            className="relative inline-flex h-5 w-9 items-center rounded-full transition-colors flex-shrink-0"
                            style={{ backgroundColor: '#5B8A72', opacity: col.required ? 0.5 : 1 }}
                          >
                            <span className="inline-block h-3.5 w-3.5 rounded-full bg-white transition-transform shadow-sm" style={{ transform: 'translateX(18px)' }} />
                          </button>
                        </div>
                      )
                    })}

                    {ALL_COLUMNS.filter(c => !visibleColumns.includes(c.key)).map(col => (
                      <div
                        key={col.key}
                        className="flex items-center gap-1.5 px-3 py-2 hover:bg-[#F5F7F4] transition-colors"
                      >
                        <div className="w-[18px] flex-shrink-0" />
                        <span className="flex-1 text-sm text-[#7A8580]">{col.label}</span>
                        <button
                          onClick={() => toggleColumn(col.key)}
                          className="relative inline-flex h-5 w-9 items-center rounded-full transition-colors flex-shrink-0"
                          style={{ backgroundColor: '#D1D5DB' }}
                        >
                          <span className="inline-block h-3.5 w-3.5 rounded-full bg-white transition-transform shadow-sm" style={{ transform: 'translateX(3px)' }} />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
        
        {showFilters && (
          <div className="mt-4 pt-4 border-t border-[rgba(59,77,67,0.08)] grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-[#3D4A44] mb-1">Creator</label>
              <select
                value={filters.creator_id}
                onChange={(e) => handleFilterChange('creator_id', e.target.value)}
                className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
              >
                <option value="">All Creators</option>
                {creators.map(creator => (
                  <option key={creator.id} value={creator.id}>{creator.display_name}</option>
                ))}
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-[#3D4A44] mb-1">Min Health</label>
              <input
                type="number"
                value={filters.min_health}
                onChange={(e) => handleFilterChange('min_health', e.target.value)}
                placeholder="0"
                min="0"
                max="100"
                className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-[#3D4A44] mb-1">Max Health</label>
              <input
                type="number"
                value={filters.max_health}
                onChange={(e) => handleFilterChange('max_health', e.target.value)}
                placeholder="100"
                min="0"
                max="100"
                className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
              />
            </div>
            
            <div className="flex items-end">
              <button
                onClick={clearFilters}
                className="w-full px-4 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg text-[#3D4A44] hover:bg-[#EEF1EC] transition-colors"
              >
                Clear Filters
              </button>
            </div>
          </div>
        )}

        {audioColumnsEnabled && (
          <div className="mt-4 pt-4 border-t border-[rgba(59,77,67,0.08)]">
            <button
              onClick={() => setShowAudioFilters(!showAudioFilters)}
              className="flex items-center space-x-2 text-sm font-medium text-[#3D4A44] hover:text-[#5B8A72] transition-colors"
            >
              <SpeakerWaveIcon className="w-4 h-4" />
              <span>Audio & Analysis</span>
              {hasActiveAudioFilters && (
                <span className="bg-[#5B8A72] text-white px-2 py-0.5 rounded-full text-xs font-bold ml-1">
                  {[audioFilters.audioLinked, audioFilters.analyzed, audioFilters.bpmMin, audioFilters.bpmMax, audioFilters.musicalKey, audioFilters.vocal].filter(v => v !== '').length + (audioFilters.mood.length > 0 ? 1 : 0)}
                </span>
              )}
              {showAudioFilters ? <ChevronUpIcon className="w-4 h-4" /> : <ChevronDownIcon className="w-4 h-4" />}
            </button>

            {showAudioFilters && (
              <div className="mt-3 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Audio Linked</label>
                  <select
                    value={audioFilters.audioLinked}
                    onChange={(e) => setAudioFilters(prev => ({ ...prev, audioLinked: e.target.value }))}
                    className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  >
                    <option value="">All</option>
                    <option value="yes">Yes</option>
                    <option value="no">No</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Analyzed</label>
                  <select
                    value={audioFilters.analyzed}
                    onChange={(e) => setAudioFilters(prev => ({ ...prev, analyzed: e.target.value }))}
                    className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  >
                    <option value="">All</option>
                    <option value="yes">Yes</option>
                    <option value="no">No</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">BPM Range</label>
                  <div className="flex items-center space-x-2">
                    <input
                      type="number"
                      value={audioFilters.bpmMin}
                      onChange={(e) => setAudioFilters(prev => ({ ...prev, bpmMin: e.target.value }))}
                      placeholder="Min"
                      min="0"
                      max="300"
                      className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                    />
                    <span className="text-[#7A8580]">–</span>
                    <input
                      type="number"
                      value={audioFilters.bpmMax}
                      onChange={(e) => setAudioFilters(prev => ({ ...prev, bpmMax: e.target.value }))}
                      placeholder="Max"
                      min="0"
                      max="300"
                      className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Key</label>
                  <select
                    value={audioFilters.musicalKey}
                    onChange={(e) => setAudioFilters(prev => ({ ...prev, musicalKey: e.target.value }))}
                    className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  >
                    <option value="">All Keys</option>
                    {MUSICAL_KEYS.map(k => (
                      <option key={k} value={k}>{k}</option>
                    ))}
                  </select>
                </div>

                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Mood</label>
                  <div className="flex flex-wrap gap-2">
                    {MOOD_OPTIONS.map(mood => (
                      <button
                        key={mood}
                        onClick={() => toggleMoodFilter(mood)}
                        className={`px-3 py-1 rounded-full text-xs font-medium transition-colors capitalize ${
                          audioFilters.mood.includes(mood)
                            ? MOOD_COLORS[mood] || 'bg-[#5B8A72] text-white'
                            : 'bg-[#EEF1EC] text-[#7A8580] hover:bg-[#E4E8E2]'
                        }`}
                      >
                        {mood}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Vocal</label>
                  <select
                    value={audioFilters.vocal}
                    onChange={(e) => setAudioFilters(prev => ({ ...prev, vocal: e.target.value }))}
                    className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  >
                    <option value="">All</option>
                    <option value="vocal">Vocal</option>
                    <option value="instrumental">Instrumental</option>
                  </select>
                </div>

                <div className="flex items-end">
                  <button
                    onClick={clearAudioFilters}
                    className="w-full px-4 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg text-[#3D4A44] hover:bg-[#EEF1EC] transition-colors"
                  >
                    Clear Audio Filters
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
      
      <div className="bg-[#FAFBF9] rounded-xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[700px]">
            <thead className="bg-[#EEF1EC] border-b border-[rgba(59,77,67,0.08)]">
              <tr>
                <th className="px-2 sm:px-3 py-3 text-center w-10">
                  <input
                    type="checkbox"
                    checked={filteredSongs.length > 0 && filteredSongs.every(s => selectedSongIds.has(s.id))}
                    onChange={(e) => {
                      if (e.target.checked) {
                        selectAllSongs()
                      } else {
                        clearSelection()
                      }
                    }}
                    className="w-4 h-4 rounded border-[#7A8580] text-[#5B8A72] focus:ring-[#5B8A72]"
                  />
                </th>
                {activeColumns.map(col => (
                  <th
                    key={col.key}
                    className={`relative px-2 sm:px-4 py-3 ${col.align === 'center' ? 'text-center' : 'text-left'} text-xs font-semibold text-[#3D4A44] whitespace-nowrap ${col.sortable ? 'cursor-pointer select-none hover:bg-[rgba(59,77,67,0.08)]' : ''} transition-colors`}
                    style={columnWidths[col.key] ? { width: columnWidths[col.key], minWidth: 60 } : undefined}
                    onClick={() => col.sortable && handleSort(col.key)}
                  >
                    <div className={`flex items-center ${col.align === 'center' ? 'justify-center' : ''} space-x-1`}>
                      <span>{col.label}</span>
                      {col.sortable && <SortArrow field={col.key} />}
                    </div>
                    <div
                      className="absolute right-0 top-0 bottom-0 w-1.5 cursor-col-resize hover:bg-[#5B8A72]/30 active:bg-[#5B8A72]/50 z-10 hidden sm:block"
                      onMouseDown={(e) => handleResizeStart(e, col.key)}
                      onClick={(e) => e.stopPropagation()}
                    />
                  </th>
                ))}
                {audioColumnsEnabled && (
                  <>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-[#3D4A44]">Audio</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-[#3D4A44]">BPM</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-[#3D4A44]">Key</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-[#3D4A44]">Mood</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-[#3D4A44]">Analyzed</th>
                  </>
                )}
                <th className="px-3 py-4 text-center text-sm font-semibold text-[#3D4A44] w-10"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[rgba(59,77,67,0.08)]">
              {sortedSongs.map((song) => (
                <tr 
                  key={song.id} 
                  onClick={() => setSelectedSong(song)}
                  className={`group hover:bg-[rgba(91,138,114,0.06)] cursor-pointer transition-colors ${
                    selectedSongIds.has(song.id) ? 'bg-[rgba(91,138,114,0.08)]' : ''
                  }`}
                >
                  <td className="px-2 sm:px-3 py-3 text-center">
                    <input
                      type="checkbox"
                      checked={selectedSongIds.has(song.id)}
                      onChange={(e) => toggleSongSelection(e, song.id)}
                      onClick={(e) => e.stopPropagation()}
                      className="w-4 h-4 rounded border-[#7A8580] text-[#5B8A72] focus:ring-[#5B8A72]"
                    />
                  </td>
                  {activeColumns.map(col => {
                    const cellAlign = col.align === 'center' ? 'text-center' : ''
                    switch (col.key) {
                      case 'title':
                        return (
                          <td key={col.key} className="px-2 sm:px-4 py-3 overflow-hidden">
                            <div className="font-medium text-[#3D4A44] truncate">{song.title}</div>
                            {!visibleColumns.includes('project_title') && (
                              <div className="text-xs text-[#7A8580] truncate">{song.project_title || '-'}</div>
                            )}
                          </td>
                        )
                      case 'primary_artist':
                        return <td key={col.key} className="px-2 sm:px-4 py-3 text-sm text-[#7A8580] overflow-hidden"><span className="block truncate">{song.primary_artist}</span></td>
                      case 'client_name':
                        return <td key={col.key} className="px-2 sm:px-4 py-3 text-sm text-[#7A8580] overflow-hidden"><span className="block truncate">{song.client_name || '-'}</span></td>
                      case 'label':
                        return <td key={col.key} className="px-2 sm:px-4 py-3 text-sm text-[#7A8580] overflow-hidden"><span className="block truncate">{song.label || '-'}</span></td>
                      case 'publishing_percentage':
                        return <td key={col.key} className="px-2 sm:px-4 py-3 text-sm text-[#7A8580] whitespace-nowrap">{song.publishing_percentage ? `${Math.min(song.publishing_percentage, 100).toFixed(1)}%` : '-'}</td>
                      case 'status_health_score':
                        return (
                          <td key={col.key} className="px-2 sm:px-4 py-3 min-w-[120px]">
                            <div className="flex items-center space-x-2">
                              <div className="flex-1 h-2 bg-[#EEF1EC] rounded-full overflow-hidden">
                                <div className="h-full bg-gradient-to-r from-[#5B8A72] to-[#7BA594]" style={{ width: `${song.status_health_score || 0}%` }}></div>
                              </div>
                              <span className="text-xs font-medium text-[#7A8580] w-10">{Math.round(song.status_health_score || 0)}%</span>
                            </div>
                          </td>
                        )
                      case 'is_released':
                        return (
                          <td key={col.key} className="px-2 sm:px-4 py-3 text-center">
                            <button
                              onClick={(e) => handleReleasedToggle(e, song)}
                              className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-all mx-auto ${
                                song.is_released ? 'bg-[#5B8A72] border-[#5B8A72] text-white' : 'border-[#7A8580] hover:border-[#5B8A72]'
                              }`}
                            >
                              {song.is_released && (
                                <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                </svg>
                              )}
                            </button>
                          </td>
                        )
                      case 'spotify_link':
                        return (
                          <td key={col.key} className="px-2 sm:px-4 py-3 whitespace-nowrap">
                            {song.spotify_link ? (
                              <button onClick={(e) => openSpotifyLink(e, song.spotify_link)} className="flex items-center space-x-1 text-[#1DB954] hover:underline text-sm">
                                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                                  <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
                                </svg>
                                <span>Open</span>
                              </button>
                            ) : song.is_released ? (
                              <button onClick={(e) => { e.stopPropagation(); setSpotifyModal({ open: true, song, link: '' }) }} className="flex items-center space-x-1 text-[#7A8580] hover:text-[#5B8A72] text-sm">
                                <LinkIcon className="w-4 h-4" />
                                <span>Add Link</span>
                              </button>
                            ) : (
                              <span className="text-xs text-[#7A8580]">-</span>
                            )}
                          </td>
                        )
                      case 'has_contract_executed':
                        return <td key={col.key} className="px-2 sm:px-4 py-3">{getStatusIcon(song.has_contract_executed ? 'Yes' : 'No')}</td>
                      case 'is_registered_with_pro':
                        return <td key={col.key} className="px-2 sm:px-4 py-3">{getStatusIcon(song.is_registered_with_pro ? 'Yes' : 'No')}</td>
                      case 'isrc':
                        return <td key={col.key} className="px-2 sm:px-4 py-3 text-sm text-[#7A8580] whitespace-nowrap">{song.isrc || '-'}</td>
                      case 'release_date':
                        return <td key={col.key} className="px-2 sm:px-4 py-3 text-sm text-[#7A8580] whitespace-nowrap">{song.release_date || '-'}</td>
                      case 'project_title':
                        return <td key={col.key} className="px-2 sm:px-4 py-3 text-sm text-[#7A8580]">{song.project_title || '-'}</td>
                      case 'iswc':
                        return <td key={col.key} className="px-2 sm:px-4 py-3 text-sm text-[#7A8580] whitespace-nowrap">{song.iswc || '-'}</td>
                      default:
                        return <td key={col.key} className="px-2 sm:px-4 py-3 text-sm text-[#7A8580]">{song[col.key] || '-'}</td>
                    }
                  })}
                  {audioColumnsEnabled && (() => {
                    const songAudio = audioData[song.id] || []
                    const hasAudio = songAudio.length > 0
                    const analysis = songAudio[0]?.analysis || null
                    const firstMood = analysis?.mood_tags?.[0] || null
                    return (
                      <>
                        <td className="px-4 py-3 text-center">
                          {hasAudio ? (
                            <SpeakerWaveIcon className="w-5 h-5 text-[#5B8A72] mx-auto" />
                          ) : (
                            <span className="text-[#7A8580]">-</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-sm text-[#7A8580]">
                          {analysis?.bpm ? Math.round(analysis.bpm) : '-'}
                        </td>
                        <td className="px-4 py-3 text-sm text-[#7A8580]">
                          {analysis?.musical_key || '-'}
                        </td>
                        <td className="px-4 py-3">
                          {firstMood ? (
                            <span className={`px-2 py-0.5 rounded-full text-xs font-medium capitalize ${MOOD_COLORS[firstMood] || 'bg-gray-100 text-gray-800'}`}>
                              {firstMood}
                            </span>
                          ) : (
                            <span className="text-sm text-[#7A8580]">-</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-center">
                          {analysis ? (
                            <CheckCircleIcon className="w-5 h-5 text-[#5B9A6E] mx-auto" />
                          ) : (
                            <span className="text-[#7A8580]">-</span>
                          )}
                        </td>
                      </>
                    )
                  })()}
                  <td className="px-3 py-3 text-center">
                    <div className="flex items-center justify-center gap-1">
                      <button
                        onClick={(e) => handleDuplicateSong(song.id, e)}
                        className="p-1.5 rounded-lg text-[#9CA8A3] hover:text-[#5B8A72] hover:bg-[rgba(91,138,114,0.08)] transition-colors opacity-0 group-hover:opacity-100"
                        title="Duplicate song"
                      >
                        <DocumentDuplicateIcon className="w-4 h-4" />
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); handleDeleteSong(song.id, song.title) }}
                        className="p-1.5 rounded-lg text-[#9CA8A3] hover:text-[#C47068] hover:bg-red-50 transition-colors opacity-0 group-hover:opacity-100"
                        title="Delete song"
                      >
                        <TrashIcon className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              
              {filteredSongs.length === 0 && (
                <tr>
                  <td colSpan={activeColumns.length + (audioColumnsEnabled ? 7 : 2)} className="px-6 py-12 text-center text-[#7A8580]">
                    No songs found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
      </>)}

      {activeTab === 'compositions' && (
        <div className="bg-[#FAFBF9] rounded-xl shadow-sm p-4 mb-6">
          <div className="flex items-center space-x-4 mb-4">
            <div className="flex-1 relative">
              <MagnifyingGlassIcon className="w-5 h-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-[#7A8580]" />
              <input
                type="text"
                placeholder="Search compositions by title or ISWC..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
              />
            </div>
          </div>
        </div>
      )}

      {activeTab === 'compositions' && (
        <div className="bg-[#FAFBF9] rounded-xl shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[600px]">
              <thead className="bg-[#EEF1EC] border-b border-[rgba(59,77,67,0.08)]">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-[#3D4A44]">Title</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-[#3D4A44]">Type</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-[#3D4A44]">Folder</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-[#3D4A44]">ISWC</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-[#3D4A44]">Tracks</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-[#3D4A44]">Credits</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-[#3D4A44]">Genre</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-[#3D4A44]">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[rgba(59,77,67,0.08)]">
                {filteredWorks.map(work => (
                  <tr
                    key={work.id}
                    onClick={() => navigate(`/catalog/unreleased?workId=${work.id}`)}
                    className="group hover:bg-[rgba(91,138,114,0.06)] cursor-pointer transition-colors"
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center space-x-2">
                        <DocumentTextIcon className="w-4 h-4 text-[#7A8580] flex-shrink-0" />
                        <span className="font-medium text-[#3D4A44] truncate">{work.title}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-[#7A8580]">{work.work_type || 'TRACK'}</td>
                    <td className="px-4 py-3 text-sm text-[#7A8580]">{work.folder_name || '-'}</td>
                    <td className="px-4 py-3 text-sm text-[#7A8580] font-mono">{work.iswc || '-'}</td>
                    <td className="px-4 py-3 text-center">
                      <span className="inline-flex items-center space-x-1 text-sm text-[#7A8580]">
                        <MusicalNoteIcon className="w-3.5 h-3.5" />
                        <span>{work.track_count || 0}</span>
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center text-sm text-[#7A8580]">{work.credit_count || 0}</td>
                    <td className="px-4 py-3 text-sm text-[#7A8580]">{work.genre || '-'}</td>
                    <td className="px-4 py-3 text-center">
                      {(work.status || 'PENDING') === 'APPROVED' ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-50 text-green-700">Approved</span>
                      ) : (work.status || 'PENDING') === 'REJECTED' ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-50 text-red-700">Rejected</span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-700">Pending</span>
                      )}
                    </td>
                  </tr>
                ))}
                {filteredWorks.length === 0 && (
                  <tr>
                    <td colSpan={8} className="px-6 py-12 text-center text-[#7A8580]">
                      No compositions found
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}


      {selectedSongIds.size > 0 && (
        <div className="fixed bottom-4 left-2 right-2 sm:left-1/2 sm:right-auto sm:transform sm:-translate-x-1/2 z-40">
          <div className="bg-[#3D4A44] text-white px-3 py-2.5 sm:px-6 sm:py-3 rounded-2xl shadow-[0_8px_32px_rgba(61,74,68,0.3)] flex items-center justify-between sm:justify-start gap-2 sm:gap-4">
            <span className="text-xs sm:text-sm font-medium whitespace-nowrap">{selectedSongIds.size} selected</span>
            <div className="hidden sm:block w-px h-5 bg-[#7A8580]"></div>
            <div className="flex items-center gap-1.5 sm:gap-3">
              <button
                onClick={openBulkEditModal}
                className="px-2.5 sm:px-4 py-1.5 bg-[#5B8A72] text-white rounded-lg text-xs sm:text-sm font-medium hover:bg-[#4A7A62] transition-colors whitespace-nowrap"
              >
                Edit
              </button>
              {selectedSongIds.size >= 2 && (
                <button
                  onClick={() => {
                    const selected = songs.filter(s => selectedSongIds.has(s.id))
                    openMergeForGroup(selected)
                  }}
                  className="px-2.5 sm:px-4 py-1.5 bg-[#5A8A9A] text-white rounded-lg text-xs sm:text-sm font-medium hover:bg-[#4A7A8A] transition-colors whitespace-nowrap"
                >
                  Merge
                </button>
              )}
              <button
                onClick={handleBulkDelete}
                className="px-2.5 sm:px-4 py-1.5 bg-[#C47068] text-white rounded-lg text-xs sm:text-sm font-medium hover:bg-[#B45F58] transition-colors whitespace-nowrap"
              >
                Delete
              </button>
              <button
                onClick={selectAllSongs}
                className="px-2.5 sm:px-4 py-1.5 bg-[#EEF1EC] text-[#3D4A44] rounded-lg text-xs sm:text-sm font-medium hover:bg-white transition-colors whitespace-nowrap"
              >
                All
              </button>
              <button
                onClick={clearSelection}
                className="px-2.5 sm:px-4 py-1.5 border border-[#7A8580] text-white rounded-lg text-xs sm:text-sm font-medium hover:bg-[#4A5550] transition-colors whitespace-nowrap"
              >
                Clear
              </button>
            </div>
          </div>
        </div>
      )}
      
      {selectedSong && (
        <SongDetailModal song={selectedSong} onClose={() => setSelectedSong(null)} onSongUpdated={(data, action) => {
          if (action === 'duplicate' && data) {
            setSongs(prev => [data, ...prev])
            setTimeout(() => setSelectedSong(data), 100)
          }
          loadData()
        }} />
      )}
      
      {showAddModal && organizationId && (
        <AddSongModal 
          onClose={() => setShowAddModal(false)}
          onSuccess={loadData}
          organizationId={organizationId}
        />
      )}
      
      {showUploadModal && organizationId && (
        <ScheduleAUploadModal 
          onClose={() => setShowUploadModal(false)}
          onSuccess={loadData}
          organizationId={organizationId}
        />
      )}
      
      {spotifyModal.open && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-md mx-4">
            <h3 className="text-lg font-semibold text-[#3D4A44] mb-2">Add Spotify Link</h3>
            <p className="text-sm text-[#7A8580] mb-4">
              Add the Spotify link for "<span className="font-medium text-[#3D4A44]">{spotifyModal.song?.title}</span>"
            </p>
            
            <div className="mb-4">
              <label className="block text-sm font-medium text-[#3D4A44] mb-1">Spotify URL</label>
              <input
                type="url"
                value={spotifyModal.link}
                onChange={(e) => setSpotifyModal(prev => ({ ...prev, link: e.target.value }))}
                placeholder="https://open.spotify.com/track/..."
                className="w-full px-4 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent text-[#3D4A44]"
              />
            </div>
            
            <div className="flex items-center justify-end space-x-3">
              <button
                onClick={() => setSpotifyModal({ open: false, song: null, link: '' })}
                className="px-4 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg text-[#3D4A44] hover:bg-[#EEF1EC] transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSpotifyLinkSave}
                className="px-4 py-2 bg-[#1DB954] text-white rounded-lg hover:bg-[#1aa34a] transition-colors flex items-center space-x-2"
              >
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
                </svg>
                <span>Save & Mark Released</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {showBulkEditModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-lg mx-4">
            <h3 className="text-lg font-semibold text-[#3D4A44] mb-2">Bulk Edit</h3>
            <p className="text-sm text-[#7A8580] mb-4">
              Update {selectedSongIds.size} selected song{selectedSongIds.size !== 1 ? 's' : ''}. Only changed fields will be applied.
            </p>

            <div className="space-y-4 max-h-[60vh] overflow-y-auto">
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Label</label>
                <input
                  type="text"
                  value={bulkEditFields.label || ''}
                  onChange={(e) => handleBulkEditFieldChange('label', e.target.value)}
                  placeholder="Enter label..."
                  className="w-full px-4 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent text-[#3D4A44]"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Publishing %</label>
                  <input
                    type="number"
                    value={bulkEditFields.publishing_percentage ?? ''}
                    onChange={(e) => handleBulkEditFieldChange('publishing_percentage', e.target.value)}
                    placeholder="0-100"
                    min="0"
                    max="100"
                    className="w-full px-4 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent text-[#3D4A44]"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Master %</label>
                  <input
                    type="number"
                    value={bulkEditFields.master_percentage ?? ''}
                    onChange={(e) => handleBulkEditFieldChange('master_percentage', e.target.value)}
                    placeholder="0-100"
                    min="0"
                    max="100"
                    className="w-full px-4 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent text-[#3D4A44]"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Notes</label>
                <textarea
                  value={bulkEditFields.notes || ''}
                  onChange={(e) => handleBulkEditFieldChange('notes', e.target.value)}
                  placeholder="Enter notes..."
                  rows={3}
                  className="w-full px-4 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent text-[#3D4A44] resize-none"
                />
              </div>

              <div className="flex flex-wrap gap-6 pt-2">
                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={bulkEditFields.is_released === true}
                    onChange={(e) => handleBulkEditFieldChange('is_released', e.target.checked ? true : undefined)}
                    className="w-4 h-4 rounded border-[#7A8580] text-[#5B8A72] focus:ring-[#5B8A72]"
                  />
                  <span className="text-sm text-[#3D4A44]">Is Released</span>
                </label>
                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={bulkEditFields.has_contract_executed === true}
                    onChange={(e) => handleBulkEditFieldChange('has_contract_executed', e.target.checked ? true : undefined)}
                    className="w-4 h-4 rounded border-[#7A8580] text-[#5B8A72] focus:ring-[#5B8A72]"
                  />
                  <span className="text-sm text-[#3D4A44]">Has Contract</span>
                </label>
                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={bulkEditFields.is_registered_with_pro === true}
                    onChange={(e) => handleBulkEditFieldChange('is_registered_with_pro', e.target.checked ? true : undefined)}
                    className="w-4 h-4 rounded border-[#7A8580] text-[#5B8A72] focus:ring-[#5B8A72]"
                  />
                  <span className="text-sm text-[#3D4A44]">PRO Registered</span>
                </label>
              </div>
            </div>

            <div className="flex items-center justify-end space-x-3 mt-6 pt-4 border-t border-[rgba(59,77,67,0.08)]">
              <button
                onClick={() => setShowBulkEditModal(false)}
                className="px-4 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg text-[#3D4A44] hover:bg-[#EEF1EC] transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleBulkEditSubmit}
                disabled={bulkEditLoading}
                className="px-4 py-2 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] transition-colors disabled:opacity-50"
              >
                {bulkEditLoading ? 'Updating...' : 'Apply Changes'}
              </button>
            </div>
          </div>
        </div>
      )}

      {showSpotifyImportModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-3xl mx-4 max-h-[85vh] flex flex-col">
            <h3 className="text-lg font-semibold text-[#3D4A44] mb-2 flex items-center space-x-2">
              <svg className="w-6 h-6 text-[#1DB954]" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
              </svg>
              <span>Import from Spotify</span>
            </h3>
            <p className="text-sm text-[#7A8580] mb-4">Import tracks from a Spotify playlist, artist, or album into your catalog.</p>

            {spotifyImportResult ? (
              <div className="flex-1 flex flex-col items-center justify-center py-8">
                {spotifyImportResult.error ? (
                  <>
                    <div className="w-16 h-16 bg-red-50 rounded-full flex items-center justify-center mb-4">
                      <svg className="w-8 h-8 text-red-500" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
                      </svg>
                    </div>
                    <h4 className="text-lg font-semibold text-[#3D4A44] mb-2">Spotify Error</h4>
                    <p className="text-sm text-[#7A8580] text-center max-w-md mb-4">{spotifyImportResult.message}</p>
                    <button
                      onClick={() => setSpotifyImportResult(null)}
                      className="mt-2 px-6 py-2 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] transition-colors"
                    >
                      Try Again
                    </button>
                  </>
                ) : (
                  <>
                    <div className="w-16 h-16 bg-[#EEF1EC] rounded-full flex items-center justify-center mb-4">
                      <CheckCircleIcon className="w-8 h-8 text-[#5B8A72]" />
                    </div>
                    <h4 className="text-lg font-semibold text-[#3D4A44] mb-2">Import Complete</h4>
                    <p className="text-sm text-[#7A8580] mb-1">{spotifyImportResult.imported} track{spotifyImportResult.imported !== 1 ? 's' : ''} imported</p>
                    {spotifyImportResult.skipped > 0 && (
                      <p className="text-sm text-[#7A8580] mb-1">{spotifyImportResult.skipped} skipped (already exist)</p>
                    )}
                    {spotifyImportResult.credits_created > 0 && (
                      <p className="text-sm text-[#7A8580] mb-1">{spotifyImportResult.credits_created} credit{spotifyImportResult.credits_created !== 1 ? 's' : ''} linked</p>
                    )}
                    {spotifyImportResult.creators_created > 0 && (
                      <p className="text-sm text-[#9CA8A3]">{spotifyImportResult.creators_created} new creator profile{spotifyImportResult.creators_created !== 1 ? 's' : ''} auto-created</p>
                    )}
                    <button
                      onClick={closeSpotifyImportModal}
                      className="mt-6 px-6 py-2 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] transition-colors"
                    >
                      Done
                    </button>
                  </>
                )}
              </div>
            ) : (
              <>
                <div className="space-y-4 mb-4">
                  <div>
                    <label className="block text-sm font-medium text-[#3D4A44] mb-1">Spotify URL</label>
                    <input
                      type="url"
                      value={spotifyPlaylistUrl}
                      onChange={(e) => setSpotifyPlaylistUrl(e.target.value)}
                      placeholder="https://open.spotify.com/playlist/... or artist/... or album/..."
                      className="w-full px-4 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent text-[#3D4A44]"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-[#3D4A44] mb-1">Assign to Creator <span className="text-red-500">*</span></label>
                    <select
                      value={spotifyCreatorId}
                      onChange={(e) => {
                        if (e.target.value === 'new') {
                          setShowQuickCreator(true)
                          setSpotifyCreatorId('')
                        } else {
                          setSpotifyCreatorId(e.target.value)
                          setShowQuickCreator(false)
                        }
                      }}
                      className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                    >
                      <option value="">Select a creator...</option>
                      {creators.map(creator => (
                        <option key={creator.id} value={creator.id}>{creator.display_name}</option>
                      ))}
                      <option value="new">+ Create New Creator</option>
                    </select>
                    {showQuickCreator && (
                      <div className="mt-2 flex items-center space-x-2">
                        <input
                          type="text"
                          value={quickCreatorName}
                          onChange={(e) => setQuickCreatorName(e.target.value)}
                          placeholder="Creator name..."
                          className="flex-1 px-3 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent text-[#3D4A44] text-sm"
                          onKeyDown={(e) => { if (e.key === 'Enter') handleQuickCreatorCreate() }}
                        />
                        <button
                          onClick={handleQuickCreatorCreate}
                          disabled={!quickCreatorName.trim()}
                          className="px-3 py-2 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] transition-colors text-sm disabled:opacity-50"
                        >
                          Create
                        </button>
                        <button
                          onClick={() => { setShowQuickCreator(false); setQuickCreatorName('') }}
                          className="px-3 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg text-[#3D4A44] hover:bg-[#EEF1EC] transition-colors text-sm"
                        >
                          Cancel
                        </button>
                      </div>
                    )}
                  </div>

                  <button
                    onClick={handleSpotifyPreview}
                    disabled={spotifyPreviewLoading || !spotifyPlaylistUrl || !spotifyCreatorId}
                    className="px-4 py-2 bg-[#1DB954] text-white rounded-lg hover:bg-[#1aa34a] transition-colors disabled:opacity-50 flex items-center space-x-2"
                  >
                    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
                    </svg>
                    <span>{spotifyPreviewLoading ? 'Loading...' : 'Preview'}</span>
                  </button>
                </div>

                {spotifyPreviewTracks && (
                  <div className="flex-1 overflow-hidden flex flex-col">
                    <div className="text-sm text-[#7A8580] mb-2">
                      {spotifyPreviewTracks.length} tracks found — {spotifySelectedTracks.size} selected for import
                    </div>
                    <div className="flex-1 overflow-y-auto border border-[rgba(59,77,67,0.08)] rounded-lg">
                      <table className="w-full">
                        <thead className="bg-[#EEF1EC] sticky top-0">
                          <tr>
                            <th className="px-3 py-2 text-center w-10">
                              <input
                                type="checkbox"
                                checked={spotifyPreviewTracks.length > 0 && spotifySelectedTracks.size === spotifyPreviewTracks.length}
                                onChange={(e) => {
                                  if (e.target.checked) {
                                    setSpotifySelectedTracks(new Set(spotifyPreviewTracks.map((_, i) => i)))
                                  } else {
                                    setSpotifySelectedTracks(new Set())
                                  }
                                }}
                                className="w-4 h-4 rounded border-[#7A8580] text-[#5B8A72] focus:ring-[#5B8A72]"
                              />
                            </th>
                            <th className="px-3 py-2 text-left text-xs font-semibold text-[#3D4A44]">Title</th>
                            <th className="px-3 py-2 text-left text-xs font-semibold text-[#3D4A44]">Artist(s)</th>
                            <th className="px-3 py-2 text-left text-xs font-semibold text-[#3D4A44]">Album</th>
                            <th className="px-3 py-2 text-left text-xs font-semibold text-[#3D4A44]">ISRC</th>
                            <th className="px-3 py-2 text-left text-xs font-semibold text-[#3D4A44]">Status</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-[rgba(59,77,67,0.08)]">
                          {spotifyPreviewTracks.map((track, index) => (
                            <tr key={index} className="hover:bg-[rgba(91,138,114,0.04)]">
                              <td className="px-3 py-2 text-center">
                                <input
                                  type="checkbox"
                                  checked={spotifySelectedTracks.has(index)}
                                  onChange={() => toggleSpotifyTrack(index)}
                                  className="w-4 h-4 rounded border-[#7A8580] text-[#5B8A72] focus:ring-[#5B8A72]"
                                />
                              </td>
                              <td className="px-3 py-2 text-sm text-[#3D4A44] font-medium">{track.title || track.name}</td>
                              <td className="px-3 py-2 text-sm text-[#7A8580]">
                                {track.all_artists && track.all_artists.length > 1
                                  ? <span>{track.all_artists[0]} <span className="text-xs text-[#9CA8A3]">+{track.all_artists.length - 1} more</span></span>
                                  : track.primary_artist || track.artist || '-'
                                }
                              </td>
                              <td className="px-3 py-2 text-xs text-[#7A8580] truncate max-w-[120px]">{track.album_name || '-'}</td>
                              <td className="px-3 py-2 text-xs text-[#7A8580] font-mono">{track.isrc || '-'}</td>
                              <td className="px-3 py-2">
                                {track.already_exists ? (
                                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-[#FFF3CD] text-[#856404]">
                                    Exact match
                                  </span>
                                ) : track.potential_duplicate ? (
                                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-[#FFE0DE] text-[#9B2C2C]" title={track.duplicate_matches?.[0] ? `Similar to: ${track.duplicate_matches[0].existing_title} by ${track.duplicate_matches[0].existing_artist} (${Math.round(track.duplicate_matches[0].similarity * 100)}%)` : ''}>
                                    Possible duplicate
                                  </span>
                                ) : (
                                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-[#D4EDDA] text-[#155724]">
                                    New
                                  </span>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                <div className="flex items-center justify-end space-x-3 mt-4 pt-4 border-t border-[rgba(59,77,67,0.08)]">
                  <button
                    onClick={closeSpotifyImportModal}
                    className="px-4 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg text-[#3D4A44] hover:bg-[#EEF1EC] transition-colors"
                  >
                    Cancel
                  </button>
                  {spotifyPreviewTracks && (
                    <button
                      onClick={handleSpotifyImport}
                      disabled={spotifyImportLoading || spotifySelectedTracks.size === 0 || !spotifyCreatorId}
                      className="px-4 py-2 bg-[#1DB954] text-white rounded-lg hover:bg-[#1aa34a] transition-colors disabled:opacity-50 flex items-center space-x-2"
                    >
                      <span>{spotifyImportLoading ? 'Importing...' : `Import Selected (${spotifySelectedTracks.size})`}</span>
                    </button>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {showDuplicateModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-3xl mx-4 max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-lg font-semibold text-[#3D4A44]">Duplicate Review</h3>
                <p className="text-sm text-[#7A8580]">
                  {duplicateLoading ? 'Scanning...' : `${duplicateGroups.length} potential duplicate group${duplicateGroups.length !== 1 ? 's' : ''} found`}
                </p>
              </div>
              <button onClick={() => setShowDuplicateModal(false)} className="p-2 hover:bg-[#EEF1EC] rounded-lg transition-colors">
                <XCircleIcon className="w-5 h-5 text-[#7A8580]" />
              </button>
            </div>
            
            {duplicateLoading ? (
              <div className="flex-1 flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-2 border-[#5B8A72] border-t-transparent"></div>
              </div>
            ) : duplicateGroups.length === 0 ? (
              <div className="flex-1 flex flex-col items-center justify-center py-12">
                <CheckCircleIcon className="w-12 h-12 text-[#5B8A72] mb-3" />
                <p className="text-[#3D4A44] font-medium">No duplicates found</p>
                <p className="text-sm text-[#7A8580]">Your catalog is clean!</p>
              </div>
            ) : (
              <div className="flex-1 overflow-y-auto space-y-4">
                {duplicateGroups.map((group, gi) => (
                  <div key={gi} className="border border-[rgba(59,77,67,0.12)] rounded-xl overflow-hidden">
                    <div className="bg-[#FFF8F0] px-4 py-2 flex items-center justify-between">
                      <span className="text-xs font-medium text-[#856404]">Duplicate group — {group.length} matching songs</span>
                      <button
                        onClick={() => openMergeForGroup(group)}
                        className="flex items-center gap-1 px-2.5 py-1 bg-[#5A8A9A] text-white rounded-lg text-xs font-medium hover:bg-[#4A7A8A] transition-colors"
                      >
                        <LinkIcon className="w-3.5 h-3.5" />
                        Merge
                      </button>
                    </div>
                    {group.map((song, si) => (
                      <div key={song.id} className={`px-4 py-3 flex items-center justify-between ${si > 0 ? 'border-t border-[rgba(59,77,67,0.08)]' : ''}`}>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-sm text-[#3D4A44] truncate">{song.title}</span>
                            {song.isrc && <span className="text-xs text-[#7A8580] font-mono">{song.isrc}</span>}
                            {song.similarity && <span className="text-xs text-[#9CA8A3]">{Math.round(song.similarity * 100)}% match</span>}
                          </div>
                          <div className="flex items-center gap-3 mt-0.5">
                            <span className="text-xs text-[#7A8580]">{song.primary_artist}</span>
                            {song.is_released && <span className="text-xs text-[#5B9A6E]">Released</span>}
                            {song.has_contract_executed && <span className="text-xs text-[#5A8A9A]">Contract</span>}
                            {song.is_registered_with_pro && <span className="text-xs text-[#5B8A72]">PRO</span>}
                            <span className="text-xs text-[#7A8580]">Health: {song.status_health_score?.toFixed(0) || 0}%</span>
                          </div>
                        </div>
                        <button
                          onClick={() => handleDeleteDuplicate(song.id, song.title)}
                          className="ml-3 p-1.5 rounded-lg text-[#9CA8A3] hover:text-[#C47068] hover:bg-red-50 transition-colors flex-shrink-0"
                          title="Delete this version"
                        >
                          <TrashIcon className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
      {showMergeModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between p-6 border-b border-[rgba(59,77,67,0.08)]">
              <div>
                <h3 className="text-lg font-semibold text-[#3D4A44]">Merge Songs</h3>
                <p className="text-sm text-[#7A8580] mt-0.5">Select which song to keep as the primary. All data from the others will be merged into it.</p>
              </div>
              <button onClick={() => { setShowMergeModal(false); setMergePrimaryId(null); setMergeGroupSongs([]) }} className="text-[#7A8580] hover:text-[#3D4A44]">
                <XCircleIcon className="w-5 h-5" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-6 space-y-3">
              {mergeGroupSongs.map(song => (
                <div
                  key={song.id}
                  onClick={() => setMergePrimaryId(song.id)}
                  className={`p-4 rounded-xl border-2 cursor-pointer transition-all ${
                    mergePrimaryId === song.id
                      ? 'border-[#5B8A72] bg-[#EDF5F0]'
                      : 'border-[rgba(59,77,67,0.1)] hover:border-[rgba(59,77,67,0.2)]'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-[#3D4A44] text-sm truncate">{song.title}</p>
                      <p className="text-xs text-[#7A8580]">{song.primary_artist || 'No artist'}</p>
                      <div className="flex items-center gap-3 mt-1 text-xs text-[#A0A8A3]">
                        {song.isrc && <span>ISRC: {song.isrc}</span>}
                        {song.is_released && <span className="text-[#5B9A6E]">Released</span>}
                        {song.has_contract_executed && <span className="text-[#5A8A9A]">Contract</span>}
                        {song.is_registered_with_pro && <span className="text-[#5B8A72]">PRO</span>}
                        <span>Health: {song.status_health_score?.toFixed(0) || 0}%</span>
                      </div>
                    </div>
                    {mergePrimaryId === song.id && (
                      <span className="px-2.5 py-1 bg-[#5B8A72] text-white text-xs font-semibold rounded-full ml-3 whitespace-nowrap">Primary</span>
                    )}
                  </div>
                </div>
              ))}
              <div className="bg-[#FAFBF9] rounded-xl p-3 text-xs text-[#7A8580]">
                <p className="font-medium text-[#3D4A44] mb-1">What happens when you merge:</p>
                <ul className="list-disc pl-4 space-y-0.5">
                  <li>All credits from merged songs are combined onto the primary</li>
                  <li>Placements, contracts, and accounting data are transferred</li>
                  <li>Missing metadata on the primary is filled from merged songs</li>
                  <li>Merged songs are permanently deleted</li>
                </ul>
              </div>
            </div>
            <div className="flex gap-3 p-6 border-t border-[rgba(59,77,67,0.08)]">
              <button
                onClick={() => { setShowMergeModal(false); setMergePrimaryId(null); setMergeGroupSongs([]) }}
                disabled={merging}
                className="flex-1 px-4 py-3 border border-[rgba(59,77,67,0.2)] rounded-xl text-[#3D4A44] font-medium hover:bg-[#F5F7F4] transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleMergeSongs}
                disabled={merging || !mergePrimaryId}
                className="flex-1 px-4 py-3 bg-[#5A8A9A] text-white rounded-xl font-medium hover:bg-[#4A7A8A] transition-colors disabled:opacity-50"
              >
                {merging ? 'Merging...' : 'Merge into Primary'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
