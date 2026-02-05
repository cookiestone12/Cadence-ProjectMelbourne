import React, { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import axios from 'axios'
import { ArrowLeftIcon, ArrowDownTrayIcon, CheckIcon, XMarkIcon, PencilIcon, DocumentTextIcon, DocumentArrowDownIcon, PlusIcon, MusicalNoteIcon } from '@heroicons/react/24/outline'
import { CheckCircleIcon, XCircleIcon, MinusCircleIcon } from '@heroicons/react/24/solid'
import ActionsTab from '../components/ActionsTab'

export default function CreatorDetailPage() {
  const { id } = useParams()
  const [creator, setCreator] = useState(null)
  const [songs, setSongs] = useState([])
  const [scheduleAData, setScheduleAData] = useState(null)
  const [activeTab, setActiveTab] = useState('overview')
  const [loading, setLoading] = useState(true)
  const [editingSong, setEditingSong] = useState(null)
  const [editForm, setEditForm] = useState({})
  const [saving, setSaving] = useState(false)
  const [organizationId, setOrganizationId] = useState(null)
  const [showAddSongModal, setShowAddSongModal] = useState(false)
  const [addingSong, setAddingSong] = useState(false)
  const [newSong, setNewSong] = useState({
    title: '',
    primary_artist: '',
    isrc: '',
    iswc: '',
    project_title: '',
    release_date: '',
    label: '',
    publishing_percentage: '',
    master_percentage: '',
    advance_amount: '',
    notes: ''
  })
  const [showEditCreatorModal, setShowEditCreatorModal] = useState(false)
  const [editingCreator, setEditingCreator] = useState(false)
  const [showSpotifyModal, setShowSpotifyModal] = useState(false)
  const [spotifyModalSong, setSpotifyModalSong] = useState(null)
  const [spotifyLinkInput, setSpotifyLinkInput] = useState('')
  const [savingSpotifyLink, setSavingSpotifyLink] = useState(false)
  const [creatorForm, setCreatorForm] = useState({
    display_name: '',
    legal_name: '',
    email: '',
    roles: [],
    primary_territory: '',
    primary_pro: '',
    primary_ipi: ''
  })
  
  const loadSongs = async (orgId) => {
    const songsResponse = await axios.get(`/api/songs/org/${orgId}?creator_id=${id}&limit=1000`)
    setSongs(songsResponse.data)
  }
  
  const loadScheduleAData = async () => {
    try {
      const response = await axios.get(`/api/schedule-a/creator/${id}/data`)
      setScheduleAData(response.data)
    } catch (error) {
      console.error('Failed to load Schedule A data:', error)
    }
  }
  
  useEffect(() => {
    async function loadCreatorData() {
      try {
        const creatorResponse = await axios.get(`/api/creators/${id}`)
        setCreator(creatorResponse.data)
        
        const orgResponse = await axios.get('/api/organizations/current')
        const orgId = orgResponse.data.id
        setOrganizationId(orgId)
        
        await loadSongs(orgId)
      } catch (error) {
        console.error('Failed to load creator:', error)
      } finally {
        setLoading(false)
      }
    }
    
    loadCreatorData()
  }, [id])
  
  useEffect(() => {
    if (activeTab === 'schedule-a') {
      loadScheduleAData()
    }
  }, [activeTab, id])
  
  const handleScheduleAExportCSV = async () => {
    try {
      const response = await axios.get(`/api/schedule-a/creator/${id}/csv`, {
        responseType: 'blob'
      })
      
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `Schedule_A_${creator.display_name.replace(/ /g, '_')}.csv`)
      document.body.appendChild(link)
      link.click()
      link.remove()
    } catch (error) {
      console.error('Failed to export Schedule A CSV:', error)
    }
  }
  
  const handleScheduleAExportPDF = async () => {
    try {
      const response = await axios.get(`/api/schedule-a/creator/${id}/pdf`, {
        responseType: 'blob'
      })
      
      const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `Schedule_A_${creator.display_name.replace(/ /g, '_')}.pdf`)
      document.body.appendChild(link)
      link.click()
      link.remove()
    } catch (error) {
      console.error('Failed to export Schedule A PDF:', error)
    }
  }
  
  const startEdit = (song) => {
    setEditingSong(song.id)
    setEditForm({
      publishing_percentage: song.publishing_percentage || '',
      master_percentage: song.master_percentage || '',
      advance_amount: song.advance_amount ? (song.advance_amount / 100) : '',
      label: song.label || '',
      is_registered_with_pro: song.is_registered_with_pro || false,
      is_registered_with_dsp: song.is_registered_with_dsp || false,
      soundexchange_registered: song.soundexchange_registered || 'N/A',
      is_paid: song.is_paid || false,
      is_invoiced: song.is_invoiced || false,
      has_contract_executed: song.has_contract_executed || false,
      is_released: song.is_released || false,
      spotify_link: song.spotify_link || '',
      notes: song.notes || ''
    })
  }
  
  const cancelEdit = () => {
    setEditingSong(null)
    setEditForm({})
  }
  
  const saveEdit = async (songId) => {
    setSaving(true)
    try {
      const payload = {
        publishing_percentage: editForm.publishing_percentage === '' ? null : Math.min(parseFloat(editForm.publishing_percentage), 100),
        master_percentage: editForm.master_percentage === '' ? null : Math.min(parseFloat(editForm.master_percentage), 100),
        advance_amount: editForm.advance_amount === '' ? null : Math.round(parseFloat(editForm.advance_amount) * 100),
        label: editForm.label || null,
        is_registered_with_pro: editForm.is_registered_with_pro,
        is_registered_with_dsp: editForm.is_registered_with_dsp,
        soundexchange_registered: editForm.soundexchange_registered,
        is_paid: editForm.is_paid,
        is_invoiced: editForm.is_invoiced,
        has_contract_executed: editForm.has_contract_executed,
        is_released: editForm.is_released,
        spotify_link: editForm.spotify_link || null,
        notes: editForm.notes || null
      }
      
      await axios.patch(`/api/songs/${songId}`, payload)
      
      const orgResponse = await axios.get('/api/organizations/current')
      await loadSongs(orgResponse.data.id)
      
      setEditingSong(null)
      setEditForm({})
    } catch (error) {
      console.error('Failed to update song:', error)
      alert('Failed to save changes')
    } finally {
      setSaving(false)
    }
  }

  const handleReleasedToggle = async (song) => {
    const newReleasedStatus = !song.is_released
    if (newReleasedStatus && !song.spotify_link) {
      setSpotifyModalSong(song)
      setSpotifyLinkInput('')
      setShowSpotifyModal(true)
    } else {
      try {
        await axios.patch(`/api/songs/${song.id}`, { is_released: newReleasedStatus })
        const orgResponse = await axios.get('/api/organizations/current')
        await loadSongs(orgResponse.data.id)
      } catch (error) {
        console.error('Failed to update released status:', error)
      }
    }
  }

  const handleSpotifyModalSave = async () => {
    if (!spotifyModalSong) return
    setSavingSpotifyLink(true)
    try {
      await axios.patch(`/api/songs/${spotifyModalSong.id}`, { 
        is_released: true,
        spotify_link: spotifyLinkInput || null
      })
      const orgResponse = await axios.get('/api/organizations/current')
      await loadSongs(orgResponse.data.id)
      setShowSpotifyModal(false)
      setSpotifyModalSong(null)
      setSpotifyLinkInput('')
    } catch (error) {
      console.error('Failed to save Spotify link:', error)
    } finally {
      setSavingSpotifyLink(false)
    }
  }

  const handleAddSong = async (e) => {
    e.preventDefault()
    if (!newSong.title.trim()) return
    
    setAddingSong(true)
    try {
      const payload = {
        title: newSong.title,
        primary_artist: newSong.primary_artist || creator.display_name,
        isrc: newSong.isrc || null,
        iswc: newSong.iswc || null,
        project_title: newSong.project_title || null,
        release_date: newSong.release_date || null,
        label: newSong.label || null,
        publishing_percentage: newSong.publishing_percentage ? parseFloat(newSong.publishing_percentage) : null,
        master_percentage: newSong.master_percentage ? parseFloat(newSong.master_percentage) : null,
        advance_amount: newSong.advance_amount ? parseFloat(newSong.advance_amount) : null,
        notes: newSong.notes || null
      }
      
      const response = await axios.post(`/api/songs/org/${organizationId}`, payload)
      
      await axios.post(`/api/credits/song/${response.data.id}`, {
        creator_id: parseInt(id),
        role: 'ARTIST',
        share_percentage: newSong.publishing_percentage ? parseFloat(newSong.publishing_percentage) : 100
      })
      
      await loadSongs(organizationId)
      
      setShowAddSongModal(false)
      setNewSong({
        title: '',
        primary_artist: '',
        isrc: '',
        iswc: '',
        project_title: '',
        release_date: '',
        label: '',
        publishing_percentage: '',
        master_percentage: '',
        advance_amount: '',
        notes: ''
      })
    } catch (error) {
      console.error('Failed to add song:', error)
      alert(error.response?.data?.detail || 'Failed to add song')
    } finally {
      setAddingSong(false)
    }
  }

  const ROLE_OPTIONS = ['ARTIST', 'SONGWRITER', 'PRODUCER']
  const PRO_OPTIONS = ['ASCAP', 'BMI', 'PRS', 'SESAC', 'OTHER']

  const openEditCreatorModal = () => {
    setCreatorForm({
      display_name: creator.display_name || '',
      legal_name: creator.legal_name || '',
      email: creator.email || '',
      roles: creator.roles || [],
      primary_territory: creator.primary_territory || '',
      primary_pro: creator.primary_pro || '',
      primary_ipi: creator.primary_ipi || ''
    })
    setShowEditCreatorModal(true)
  }

  const handleCreatorRoleToggle = (role) => {
    setCreatorForm(prev => ({
      ...prev,
      roles: prev.roles.includes(role)
        ? prev.roles.filter(r => r !== role)
        : [...prev.roles, role]
    }))
  }

  const handleUpdateCreator = async (e) => {
    e.preventDefault()
    if (!creatorForm.display_name.trim()) return
    
    setEditingCreator(true)
    try {
      const response = await axios.put(`/api/creators/${id}`, creatorForm)
      setCreator(prev => ({ ...prev, ...response.data }))
      setShowEditCreatorModal(false)
    } catch (error) {
      console.error('Failed to update creator:', error)
      alert(error.response?.data?.detail || 'Failed to update creator')
    } finally {
      setEditingCreator(false)
    }
  }
  
  const StatusBadge = ({ value, label }) => {
    if (value === true || value === 'Yes') {
      return (
        <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium" style={{ background: 'rgba(52, 199, 89, 0.15)', color: '#5B9A6E' }}>
          <CheckCircleIcon className="w-3 h-3" />
          {label || 'Yes'}
        </span>
      )
    } else if (value === false || value === 'No') {
      return (
        <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium" style={{ background: 'rgba(255, 59, 48, 0.15)', color: '#C47068' }}>
          <XCircleIcon className="w-3 h-3" />
          {label || 'No'}
        </span>
      )
    } else {
      return (
        <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium" style={{ background: 'rgba(0, 0, 0, 0.05)', color: '#7A8580' }}>
          <MinusCircleIcon className="w-3 h-3" />
          N/A
        </span>
      )
    }
  }
  
  const PlacementStatusBadge = ({ status }) => {
    const colors = {
      'Paid': { bg: 'rgba(52, 199, 89, 0.15)', color: '#5B9A6E' },
      'Invoiced': { bg: 'rgba(0, 122, 255, 0.15)', color: '#5A8A9A' },
      'Contracted': { bg: 'rgba(160, 32, 240, 0.15)', color: '#5B8A72' },
      'Contract Sent': { bg: 'rgba(88, 86, 214, 0.15)', color: '#6B9A84' },
      'Released - Awaiting Contract': { bg: 'rgba(255, 149, 0, 0.15)', color: '#C4956B' },
      'In Pipeline': { bg: 'rgba(0, 0, 0, 0.05)', color: '#7A8580' }
    }
    const style = colors[status] || colors['In Pipeline']
    return (
      <span 
        className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium"
        style={{ background: style.bg, color: style.color }}
      >
        {status}
      </span>
    )
  }
  
  if (loading) {
    return (
      <div className="flex items-center justify-center h-full bg-[#F5F7F4]">
        <div className="text-[#7A8580]">Loading creator...</div>
      </div>
    )
  }
  
  if (!creator) {
    return (
      <div className="flex items-center justify-center h-full bg-[#F5F7F4]">
        <div className="text-[#7A8580]">Creator not found</div>
      </div>
    )
  }
  
  const placedSongs = songs.filter(s => s.is_paid)
  const registeredPro = songs.filter(s => s.is_registered_with_pro).length
  const registeredDsp = songs.filter(s => s.is_registered_with_dsp).length
  const totalAdvance = songs.reduce((sum, s) => sum + (s.advance_amount || 0), 0) / 100
  
  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'records', label: `Records (${songs.length})` },
    { id: 'actions', label: 'Actions' },
    { id: 'schedule-a', label: 'Schedule A' }
  ]
  
  return (
    <div className="min-h-screen bg-[#F5F7F4]">
      <div className="relative h-80" style={{ background: 'linear-gradient(135deg, #5B8A72 0%, #7BA594 100%)' }}>
        {creator.hero_image_url && (
          <img 
            src={creator.hero_image_url} 
            alt={creator.display_name}
            className="absolute inset-0 w-full h-full object-cover mix-blend-overlay opacity-40"
          />
        )}
        
        <div className="absolute inset-0 bg-gradient-to-t from-black/40 to-transparent"></div>
        
        <div className="relative h-full flex flex-col justify-end p-8">
          <Link 
            to="/roster" 
            className="inline-flex items-center space-x-2 text-white/90 hover:text-white mb-4 w-fit transition-colors"
          >
            <ArrowLeftIcon className="w-5 h-5" />
            <span>Back to Roster</span>
          </Link>
          
          <div className="flex items-center gap-4 mb-2">
            <h1 className="text-5xl font-semibold text-white">{creator.display_name}</h1>
            <button
              onClick={openEditCreatorModal}
              className="p-2 rounded-full bg-white/20 hover:bg-white/30 transition-colors"
              title="Edit Creator"
            >
              <PencilIcon className="w-5 h-5 text-white" />
            </button>
          </div>
          <div className="flex items-center space-x-4 text-white/90">
            <span className="text-lg">{creator.roles?.join(', ') || 'Producer'}</span>
            <span>•</span>
            <span>{songs.length} songs</span>
            <span>•</span>
            <span>{placedSongs.length} paid placements</span>
            <span>•</span>
            <span>${totalAdvance.toLocaleString()} advances</span>
          </div>
        </div>
      </div>
      
      <div className="bg-white border-b border-[rgba(59,77,67,0.08)] sticky top-0 z-10">
        <div className="px-8">
          <div className="flex space-x-8">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`py-4 px-2 border-b-2 font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'border-[#5B8A72] text-[#5B8A72]'
                    : 'border-transparent text-[#7A8580] hover:text-[#3D4A44]'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>
      
      <div className="p-8">
        {activeTab === 'overview' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              <div className="bg-white rounded-[18px] p-7" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                <h2 className="text-xl font-semibold text-[#3D4A44] mb-5">Performance</h2>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <p className="text-sm text-[#7A8580] mb-1">Total Songs</p>
                    <p className="text-2xl font-semibold text-[#3D4A44]">{songs.length}</p>
                  </div>
                  <div>
                    <p className="text-sm text-[#7A8580] mb-1">Paid Placements</p>
                    <p className="text-2xl font-semibold text-[#5B9A6E]">{placedSongs.length}</p>
                  </div>
                  <div>
                    <p className="text-sm text-[#7A8580] mb-1">PRO Registered</p>
                    <p className="text-2xl font-semibold text-[#5A8A9A]">{registeredPro}</p>
                  </div>
                  <div>
                    <p className="text-sm text-[#7A8580] mb-1">DSP Registered</p>
                    <p className="text-2xl font-semibold text-[#5B8A72]">{registeredDsp}</p>
                  </div>
                </div>
              </div>
              
              <div className="bg-white rounded-[18px] p-7" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                <h2 className="text-xl font-semibold text-[#3D4A44] mb-5">Financials</h2>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <div>
                    <p className="text-sm text-[#7A8580] mb-1">Total Advances</p>
                    <p className="text-2xl font-semibold text-[#5B9A6E]">${totalAdvance.toLocaleString()}</p>
                  </div>
                  <div>
                    <p className="text-sm text-[#7A8580] mb-1">Avg Publishing %</p>
                    <p className="text-2xl font-semibold text-[#3D4A44]">
                      {songs.filter(s => s.publishing_percentage).length > 0 
                        ? (songs.reduce((sum, s) => sum + (s.publishing_percentage || 0), 0) / songs.filter(s => s.publishing_percentage).length).toFixed(1)
                        : 0}%
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-[#7A8580] mb-1">Avg Health Score</p>
                    <p className="text-2xl font-semibold text-[#3D4A44]">{creator.avg_health_score?.toFixed(0) || 0}%</p>
                  </div>
                </div>
              </div>
              
              <div className="bg-white rounded-[18px] p-7" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                <h2 className="text-xl font-semibold text-[#3D4A44] mb-5">Recent Songs</h2>
                <div className="space-y-3">
                  {songs.slice(0, 5).map((song) => (
                    <div key={song.id} className="flex items-center justify-between p-4 bg-[#F8F8FB] rounded-xl">
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-[#3D4A44] truncate">{song.title}</p>
                        <p className="text-sm text-[#7A8580]">{song.primary_artist}</p>
                      </div>
                      <div className="flex items-center gap-2 ml-4">
                        <StatusBadge value={song.is_paid} label="Paid" />
                        <StatusBadge value={song.is_registered_with_pro} label="PRO" />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            
            <div className="space-y-6">
              <div className="bg-white rounded-[18px] p-7" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                <h2 className="text-xl font-semibold text-[#3D4A44] mb-5">Details</h2>
                <div className="space-y-4 text-sm">
                  {creator.legal_name && (
                    <div>
                      <p className="text-[#7A8580]">Legal Name</p>
                      <p className="font-medium text-[#3D4A44]">{creator.legal_name}</p>
                    </div>
                  )}
                  {creator.primary_territory && (
                    <div>
                      <p className="text-[#7A8580]">Territory</p>
                      <p className="font-medium text-[#3D4A44]">{creator.primary_territory}</p>
                    </div>
                  )}
                  {creator.primary_pro && (
                    <div>
                      <p className="text-[#7A8580]">PRO</p>
                      <p className="font-medium text-[#3D4A44]">{creator.primary_pro}</p>
                    </div>
                  )}
                  {creator.primary_ipi && (
                    <div>
                      <p className="text-[#7A8580]">IPI</p>
                      <p className="font-medium text-[#3D4A44]">{creator.primary_ipi}</p>
                    </div>
                  )}
                </div>
              </div>
              
              <div className="bg-white rounded-[18px] p-7" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                <h2 className="text-xl font-semibold text-[#3D4A44] mb-5">Registration Status</h2>
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <span className="text-[#7A8580]">PRO Registered</span>
                    <span className="font-medium text-[#3D4A44]">{registeredPro} / {songs.length}</span>
                  </div>
                  <div className="w-full bg-[#EEF1EC] rounded-full h-2">
                    <div 
                      className="h-2 rounded-full" 
                      style={{ width: `${songs.length > 0 ? (registeredPro / songs.length) * 100 : 0}%`, background: '#5A8A9A' }}
                    />
                  </div>
                  
                  <div className="flex justify-between items-center mt-4">
                    <span className="text-[#7A8580]">DSP Registered</span>
                    <span className="font-medium text-[#3D4A44]">{registeredDsp} / {songs.length}</span>
                  </div>
                  <div className="w-full bg-[#EEF1EC] rounded-full h-2">
                    <div 
                      className="h-2 rounded-full" 
                      style={{ width: `${songs.length > 0 ? (registeredDsp / songs.length) * 100 : 0}%`, background: '#5B8A72' }}
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
        
        {activeTab === 'records' && (
          <div className="bg-white rounded-[18px] overflow-hidden" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
            <div className="p-5 border-b border-[rgba(59,77,67,0.08)] bg-[#F8F8FB] flex items-center justify-between">
              <p className="text-sm text-[#7A8580]">
                Showing all {songs.length} records. Click the edit button to update details.
              </p>
              <button
                onClick={() => setShowAddSongModal(true)}
                className="flex items-center gap-2 px-4 py-2 bg-[#5B8A72] text-white rounded-xl font-medium hover:bg-[#4A7862] transition-colors text-sm"
              >
                <PlusIcon className="w-4 h-4" />
                Add Song
              </button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-[#F8F8FB] border-b border-[rgba(59,77,67,0.08)]">
                  <tr>
                    <th className="px-4 py-3 text-left font-semibold text-[#3D4A44] sticky left-0 bg-[#F8F8FB]">Title / Artist</th>
                    <th className="px-4 py-3 text-left font-semibold text-[#3D4A44]">Label</th>
                    <th className="px-4 py-3 text-center font-semibold text-[#3D4A44]">Pub %</th>
                    <th className="px-4 py-3 text-right font-semibold text-[#3D4A44]">Advance</th>
                    <th className="px-4 py-3 text-center font-semibold text-[#3D4A44]">PRO</th>
                    <th className="px-4 py-3 text-center font-semibold text-[#3D4A44]">DSP</th>
                    <th className="px-4 py-3 text-center font-semibold text-[#3D4A44]">Sound Ex.</th>
                    <th className="px-4 py-3 text-center font-semibold text-[#3D4A44]">Contract</th>
                    <th className="px-4 py-3 text-center font-semibold text-[#3D4A44]">Paid</th>
                    <th className="px-4 py-3 text-center font-semibold text-[#3D4A44]">Released</th>
                    <th className="px-4 py-3 text-center font-semibold text-[#3D4A44]">Spotify</th>
                    <th className="px-4 py-3 text-center font-semibold text-[#3D4A44]">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {songs.map((song, index) => (
                    <tr key={song.id} className={`hover:bg-[#F8F8FB] transition-colors border-b border-[rgba(0,0,0,0.05)] ${index % 2 === 0 ? 'bg-white' : 'bg-[#F8F8FB]'}`}>
                      {editingSong === song.id ? (
                        <>
                          <td className={`px-4 py-3 sticky left-0 ${index % 2 === 0 ? 'bg-white' : 'bg-[#F8F8FB]'}`}>
                            <div className="font-medium text-[#3D4A44]">{song.title}</div>
                            <div className="text-xs text-[#7A8580]">{song.primary_artist}</div>
                          </td>
                          <td className="px-4 py-2">
                            <input 
                              type="text" 
                              value={editForm.label}
                              onChange={(e) => setEditForm({...editForm, label: e.target.value})}
                              className="w-full px-3 py-2 border border-[rgba(0,0,0,0.1)] rounded-xl text-sm bg-white focus:outline-none focus:border-[#5B8A72] focus:ring-2 focus:ring-[rgba(160,32,240,0.1)]"
                              placeholder="Label"
                            />
                          </td>
                          <td className="px-4 py-2">
                            <input 
                              type="number" 
                              value={editForm.publishing_percentage}
                              onChange={(e) => setEditForm({...editForm, publishing_percentage: e.target.value})}
                              className="w-16 px-3 py-2 border border-[rgba(0,0,0,0.1)] rounded-xl text-sm text-center bg-white focus:outline-none focus:border-[#5B8A72] focus:ring-2 focus:ring-[rgba(160,32,240,0.1)]"
                              placeholder="%"
                              step="0.01"
                              max="100"
                            />
                          </td>
                          <td className="px-4 py-2">
                            <input 
                              type="number" 
                              value={editForm.advance_amount}
                              onChange={(e) => setEditForm({...editForm, advance_amount: e.target.value})}
                              className="w-24 px-3 py-2 border border-[rgba(0,0,0,0.1)] rounded-xl text-sm text-right bg-white focus:outline-none focus:border-[#5B8A72] focus:ring-2 focus:ring-[rgba(160,32,240,0.1)]"
                              placeholder="$"
                              step="0.01"
                            />
                          </td>
                          <td className="px-4 py-2 text-center">
                            <input 
                              type="checkbox" 
                              checked={editForm.is_registered_with_pro}
                              onChange={(e) => setEditForm({...editForm, is_registered_with_pro: e.target.checked})}
                              className="w-4 h-4 text-[#5B8A72] rounded accent-[#5B8A72]"
                            />
                          </td>
                          <td className="px-4 py-2 text-center">
                            <input 
                              type="checkbox" 
                              checked={editForm.is_registered_with_dsp}
                              onChange={(e) => setEditForm({...editForm, is_registered_with_dsp: e.target.checked})}
                              className="w-4 h-4 text-[#5B8A72] rounded accent-[#5B8A72]"
                            />
                          </td>
                          <td className="px-4 py-2 text-center">
                            <select 
                              value={editForm.soundexchange_registered}
                              onChange={(e) => setEditForm({...editForm, soundexchange_registered: e.target.value})}
                              className="px-3 py-2 border border-[rgba(0,0,0,0.1)] rounded-xl text-sm bg-white focus:outline-none focus:border-[#5B8A72]"
                            >
                              <option value="N/A">N/A</option>
                              <option value="Yes">Yes</option>
                              <option value="No">No</option>
                            </select>
                          </td>
                          <td className="px-4 py-2 text-center">
                            <input 
                              type="checkbox" 
                              checked={editForm.has_contract_executed}
                              onChange={(e) => setEditForm({...editForm, has_contract_executed: e.target.checked})}
                              className="w-4 h-4 text-[#5B8A72] rounded accent-[#5B8A72]"
                            />
                          </td>
                          <td className="px-4 py-2 text-center">
                            <input 
                              type="checkbox" 
                              checked={editForm.is_paid}
                              onChange={(e) => setEditForm({...editForm, is_paid: e.target.checked})}
                              className="w-4 h-4 text-[#5B8A72] rounded accent-[#5B8A72]"
                            />
                          </td>
                          <td className="px-4 py-2 text-center">
                            <input 
                              type="checkbox" 
                              checked={editForm.is_released}
                              onChange={(e) => setEditForm({...editForm, is_released: e.target.checked})}
                              className="w-4 h-4 text-[#5B8A72] rounded accent-[#5B8A72]"
                            />
                          </td>
                          <td className="px-4 py-2">
                            <input 
                              type="text" 
                              value={editForm.spotify_link}
                              onChange={(e) => setEditForm({...editForm, spotify_link: e.target.value})}
                              disabled={!editForm.is_released}
                              placeholder={editForm.is_released ? "Spotify URL" : "-"}
                              className={`w-24 px-2 py-1 border border-[rgba(0,0,0,0.1)] rounded-lg text-xs ${!editForm.is_released ? 'bg-gray-100 text-gray-400 cursor-not-allowed' : 'bg-white focus:outline-none focus:border-[#5B8A72]'}`}
                            />
                          </td>
                          <td className="px-4 py-2">
                            <div className="flex items-center gap-2 justify-center">
                              <button 
                                onClick={() => saveEdit(song.id)}
                                disabled={saving}
                                className="p-2 rounded-lg transition-colors" style={{ background: 'rgba(52, 199, 89, 0.15)', color: '#5B9A6E' }}
                              >
                                <CheckIcon className="w-5 h-5" />
                              </button>
                              <button 
                                onClick={cancelEdit}
                                disabled={saving}
                                className="p-2 rounded-lg transition-colors" style={{ background: 'rgba(255, 59, 48, 0.15)', color: '#C47068' }}
                              >
                                <XMarkIcon className="w-5 h-5" />
                              </button>
                            </div>
                          </td>
                        </>
                      ) : (
                        <>
                          <td className={`px-4 py-3 sticky left-0 ${index % 2 === 0 ? 'bg-white' : 'bg-[#F8F8FB]'}`}>
                            <div className="font-medium text-[#3D4A44]">{song.title}</div>
                            <div className="text-xs text-[#7A8580]">{song.primary_artist}</div>
                          </td>
                          <td className="px-4 py-3 text-[#7A8580] max-w-32 truncate" title={song.label}>
                            {song.label || '-'}
                          </td>
                          <td className="px-4 py-3 text-center text-[#7A8580]">
                            {song.publishing_percentage ? `${Math.min(song.publishing_percentage, 100).toFixed(1)}%` : '-'}
                          </td>
                          <td className="px-4 py-3 text-right text-[#7A8580]">
                            {song.advance_amount ? `$${(song.advance_amount / 100).toLocaleString()}` : '-'}
                          </td>
                          <td className="px-4 py-3 text-center">
                            <StatusBadge value={song.is_registered_with_pro} />
                          </td>
                          <td className="px-4 py-3 text-center">
                            <StatusBadge value={song.is_registered_with_dsp} />
                          </td>
                          <td className="px-4 py-3 text-center">
                            <StatusBadge value={song.soundexchange_registered} />
                          </td>
                          <td className="px-4 py-3 text-center">
                            <StatusBadge value={song.has_contract_executed} />
                          </td>
                          <td className="px-4 py-3 text-center">
                            <StatusBadge value={song.is_paid} />
                          </td>
                          <td className="px-4 py-3 text-center">
                            <input 
                              type="checkbox" 
                              checked={song.is_released || false}
                              onChange={() => handleReleasedToggle(song)}
                              className="w-4 h-4 text-[#5B8A72] rounded accent-[#5B8A72] cursor-pointer"
                            />
                          </td>
                          <td className="px-4 py-3 text-center">
                            {song.is_released && song.spotify_link ? (
                              <a
                                href={song.spotify_link}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="px-2 py-1 text-xs font-medium rounded-lg transition-colors"
                                style={{ background: 'rgba(30, 215, 96, 0.15)', color: '#1DB954' }}
                              >
                                Open
                              </a>
                            ) : (
                              <span className={`text-xs ${song.is_released ? 'text-[#7A8580]' : 'text-gray-300'}`}>
                                {song.is_released ? 'Add link' : '-'}
                              </span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-center">
                            <button 
                              onClick={() => startEdit(song)}
                              className="p-2 text-[#7A8580] hover:text-[#5B8A72] rounded-lg transition-colors" style={{ background: 'rgba(0,0,0,0.03)' }}
                            >
                              <PencilIcon className="w-4 h-4" />
                            </button>
                          </td>
                        </>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
        
        {activeTab === 'actions' && organizationId && (
          <ActionsTab 
            creatorId={parseInt(id)} 
            organizationId={organizationId}
            creatorName={creator.display_name}
          />
        )}
        
        {activeTab === 'schedule-a' && (
          <div className="space-y-6">
            <div className="rounded-[18px] p-8 text-white" style={{ background: 'linear-gradient(135deg, #5B8A72 0%, #7BA594 100%)', boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                <div>
                  <h2 className="text-2xl font-semibold mb-2">Schedule A - Catalog of Compositions</h2>
                  <p className="text-white/80">
                    Official export document for {creator.display_name}'s catalog with industry-standard fields.
                  </p>
                </div>
                <div className="flex gap-3">
                  <button
                    onClick={handleScheduleAExportPDF}
                    className="inline-flex items-center space-x-2 bg-white text-[#5B8A72] px-5 py-2.5 rounded-xl font-medium hover:bg-white/90 transition-all duration-200"
                    style={{ boxShadow: '0px 2px 8px rgba(0,0,0,0.1)' }}
                  >
                    <DocumentTextIcon className="w-5 h-5" />
                    <span>Download PDF</span>
                  </button>
                  <button
                    onClick={handleScheduleAExportCSV}
                    className="inline-flex items-center space-x-2 bg-white/20 text-white px-5 py-2.5 rounded-xl font-medium hover:bg-white/30 transition-all duration-200 border border-white/30"
                  >
                    <DocumentArrowDownIcon className="w-5 h-5" />
                    <span>Download CSV</span>
                  </button>
                </div>
              </div>
            </div>
            
            {scheduleAData && (
              <>
                <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
                  <div className="bg-white rounded-[18px] p-5" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                    <p className="text-sm text-[#7A8580] mb-1">Total Compositions</p>
                    <p className="text-2xl font-semibold text-[#3D4A44]">{scheduleAData.summary.total_songs}</p>
                  </div>
                  <div className="bg-white rounded-[18px] p-5" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                    <p className="text-sm text-[#7A8580] mb-1">Released</p>
                    <p className="text-2xl font-semibold text-[#5B8A72]">{scheduleAData.summary.released_count}</p>
                  </div>
                  <div className="bg-white rounded-[18px] p-5" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                    <p className="text-sm text-[#7A8580] mb-1">Pipeline</p>
                    <p className="text-2xl font-semibold text-[#7BA594]">{scheduleAData.summary.pipeline_count}</p>
                  </div>
                  <div className="bg-white rounded-[18px] p-5" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                    <p className="text-sm text-[#7A8580] mb-1">Paid</p>
                    <p className="text-2xl font-semibold text-[#5B9A6E]">{scheduleAData.summary.paid_count}</p>
                  </div>
                  <div className="bg-white rounded-[18px] p-5" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                    <p className="text-sm text-[#7A8580] mb-1">Contracted</p>
                    <p className="text-2xl font-semibold text-[#5A8A9A]">{scheduleAData.summary.contracted_count}</p>
                  </div>
                  <div className="bg-white rounded-[18px] p-5" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                    <p className="text-sm text-[#7A8580] mb-1">Total Advances</p>
                    <p className="text-2xl font-semibold text-[#5B9A6E]">{scheduleAData.summary.total_advance_display}</p>
                  </div>
                </div>
                
                {scheduleAData.released.length > 0 && (
                  <div className="bg-white rounded-[18px] overflow-hidden" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                    <div className="p-5 border-b border-[rgba(59,77,67,0.08)]" style={{ background: 'rgba(160, 32, 240, 0.08)' }}>
                      <h3 className="text-lg font-semibold text-[#5B8A72]">Released Catalog ({scheduleAData.released.length})</h3>
                      <p className="text-sm text-[#7A8580]">Songs that have been officially released</p>
                    </div>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead className="bg-[#F8F8FB] border-b border-[rgba(59,77,67,0.08)]">
                          <tr>
                            <th className="px-4 py-3 text-left font-semibold text-[#3D4A44]">Title</th>
                            <th className="px-4 py-3 text-left font-semibold text-[#3D4A44]">Artist</th>
                            <th className="px-4 py-3 text-left font-semibold text-[#3D4A44]">Release</th>
                            <th className="px-4 py-3 text-left font-semibold text-[#3D4A44]">Label</th>
                            <th className="px-4 py-3 text-center font-semibold text-[#3D4A44]">Pub %</th>
                            <th className="px-4 py-3 text-right font-semibold text-[#3D4A44]">Advance</th>
                            <th className="px-4 py-3 text-center font-semibold text-[#3D4A44]">Status</th>
                            <th className="px-4 py-3 text-center font-semibold text-[#3D4A44]">PRO</th>
                            <th className="px-4 py-3 text-center font-semibold text-[#3D4A44]">DSP</th>
                          </tr>
                        </thead>
                        <tbody>
                          {scheduleAData.released.map((song, index) => (
                            <tr key={song.id} className={`hover:bg-[#F8F8FB] border-b border-[rgba(0,0,0,0.05)] ${index % 2 === 0 ? 'bg-white' : 'bg-[#F8F8FB]'}`}>
                              <td className="px-4 py-3 font-medium text-[#3D4A44]">{song.title}</td>
                              <td className="px-4 py-3 text-[#7A8580]">{song.primary_artist}</td>
                              <td className="px-4 py-3 text-[#7A8580]">{song.release_date || '-'}</td>
                              <td className="px-4 py-3 text-[#7A8580] max-w-32 truncate">{song.label || '-'}</td>
                              <td className="px-4 py-3 text-center text-[#7A8580]">
                                {song.publishing_percentage ? `${Math.min(song.publishing_percentage, 100).toFixed(1)}%` : '-'}
                              </td>
                              <td className="px-4 py-3 text-right text-[#7A8580]">{song.advance_display || '-'}</td>
                              <td className="px-4 py-3 text-center">
                                <PlacementStatusBadge status={song.status} />
                              </td>
                              <td className="px-4 py-3 text-center">
                                <StatusBadge value={song.is_registered_with_pro} />
                              </td>
                              <td className="px-4 py-3 text-center">
                                <StatusBadge value={song.is_registered_with_dsp} />
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
                
                {scheduleAData.pipeline.length > 0 && (
                  <div className="bg-white rounded-[18px] overflow-hidden" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                    <div className="p-5 border-b border-[rgba(59,77,67,0.08)]" style={{ background: 'rgba(229, 64, 172, 0.08)' }}>
                      <h3 className="text-lg font-semibold text-[#7BA594]">Pipeline ({scheduleAData.pipeline.length})</h3>
                      <p className="text-sm text-[#7A8580]">Unreleased songs in various stages of the placement process</p>
                    </div>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead className="bg-[#F8F8FB] border-b border-[rgba(59,77,67,0.08)]">
                          <tr>
                            <th className="px-4 py-3 text-left font-semibold text-[#3D4A44]">Title</th>
                            <th className="px-4 py-3 text-left font-semibold text-[#3D4A44]">Artist</th>
                            <th className="px-4 py-3 text-left font-semibold text-[#3D4A44]">Label</th>
                            <th className="px-4 py-3 text-center font-semibold text-[#3D4A44]">Pub %</th>
                            <th className="px-4 py-3 text-right font-semibold text-[#3D4A44]">Advance</th>
                            <th className="px-4 py-3 text-center font-semibold text-[#3D4A44]">Status</th>
                            <th className="px-4 py-3 text-center font-semibold text-[#3D4A44]">Contract</th>
                            <th className="px-4 py-3 text-center font-semibold text-[#3D4A44]">Paid</th>
                          </tr>
                        </thead>
                        <tbody>
                          {scheduleAData.pipeline.map((song, index) => (
                            <tr key={song.id} className={`hover:bg-[#F8F8FB] border-b border-[rgba(0,0,0,0.05)] ${index % 2 === 0 ? 'bg-white' : 'bg-[#F8F8FB]'}`}>
                              <td className="px-4 py-3 font-medium text-[#3D4A44]">{song.title}</td>
                              <td className="px-4 py-3 text-[#7A8580]">{song.primary_artist}</td>
                              <td className="px-4 py-3 text-[#7A8580] max-w-32 truncate">{song.label || '-'}</td>
                              <td className="px-4 py-3 text-center text-[#7A8580]">
                                {song.publishing_percentage ? `${Math.min(song.publishing_percentage, 100).toFixed(1)}%` : '-'}
                              </td>
                              <td className="px-4 py-3 text-right text-[#7A8580]">{song.advance_display || '-'}</td>
                              <td className="px-4 py-3 text-center">
                                <PlacementStatusBadge status={song.status} />
                              </td>
                              <td className="px-4 py-3 text-center">
                                <StatusBadge value={song.has_contract_executed} />
                              </td>
                              <td className="px-4 py-3 text-center">
                                <StatusBadge value={song.is_paid} />
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
                
                {scheduleAData.released.length === 0 && scheduleAData.pipeline.length === 0 && (
                  <div className="bg-white rounded-[18px] p-12 text-center" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                    <DocumentTextIcon className="w-12 h-12 text-[#C7C7CC] mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-[#3D4A44] mb-2">No compositions yet</h3>
                    <p className="text-[#7A8580]">Add songs to this creator's catalog to generate a Schedule A.</p>
                  </div>
                )}
              </>
            )}
            
            {!scheduleAData && (
              <div className="bg-white rounded-[18px] p-12 text-center" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                <div className="text-[#7A8580]">Loading Schedule A data...</div>
              </div>
            )}
          </div>
        )}
      </div>

      {showSpotifyModal && spotifyModalSong && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-[18px] w-full max-w-md">
            <div className="p-6 border-b border-[rgba(59,77,67,0.12)]">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full flex items-center justify-center" style={{ background: 'rgba(30, 215, 96, 0.15)' }}>
                    <svg className="w-5 h-5" style={{ color: '#1DB954' }} viewBox="0 0 24 24" fill="currentColor">
                      <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
                    </svg>
                  </div>
                  <h2 className="text-[22px] font-semibold text-[#3D4A44]">Add Spotify Link</h2>
                </div>
                <button
                  onClick={() => {
                    setShowSpotifyModal(false)
                    setSpotifyModalSong(null)
                  }}
                  className="p-2 hover:bg-[#EEF1EC] rounded-lg transition-colors"
                >
                  <XMarkIcon className="w-5 h-5 text-[#7A8580]" />
                </button>
              </div>
            </div>
            <div className="p-6">
              <p className="text-sm text-[#7A8580] mb-4">
                Add a Spotify link for <span className="font-medium text-[#3D4A44]">{spotifyModalSong.title}</span>
              </p>
              <input
                type="text"
                value={spotifyLinkInput}
                onChange={(e) => setSpotifyLinkInput(e.target.value)}
                placeholder="https://open.spotify.com/track/..."
                className="w-full px-4 py-3 border border-[rgba(0,0,0,0.1)] rounded-xl text-sm bg-white focus:outline-none focus:border-[#5B8A72] focus:ring-2 focus:ring-[rgba(91,138,114,0.1)]"
              />
              <p className="text-xs text-[#7A8580] mt-2">Optional - you can skip this and add the link later</p>
            </div>
            <div className="p-6 border-t border-[rgba(59,77,67,0.08)] flex justify-end gap-3">
              <button
                onClick={() => {
                  setShowSpotifyModal(false)
                  setSpotifyModalSong(null)
                }}
                className="px-4 py-2 text-[#7A8580] hover:bg-[#EEF1EC] rounded-xl transition-colors text-sm font-medium"
              >
                Cancel
              </button>
              <button
                onClick={handleSpotifyModalSave}
                disabled={savingSpotifyLink}
                className="px-4 py-2 bg-[#5B8A72] text-white rounded-xl font-medium hover:bg-[#4A7862] transition-colors text-sm disabled:opacity-50"
              >
                {savingSpotifyLink ? 'Saving...' : 'Mark as Released'}
              </button>
            </div>
          </div>
        </div>
      )}

      {showAddSongModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-[18px] w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-[rgba(59,77,67,0.12)]">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-[#EEF1EC] flex items-center justify-center">
                    <MusicalNoteIcon className="w-5 h-5 text-[#5B8A72]" />
                  </div>
                  <h2 className="text-[22px] font-semibold text-[#3D4A44]">Add New Song</h2>
                </div>
                <button
                  onClick={() => setShowAddSongModal(false)}
                  className="p-2 hover:bg-[#EEF1EC] rounded-lg transition-colors"
                >
                  <XMarkIcon className="w-5 h-5 text-[#7A8580]" />
                </button>
              </div>
              <p className="text-[15px] text-[#7A8580] mt-2">Add a song to {creator?.display_name}'s catalog</p>
            </div>
            
            <form onSubmit={handleAddSong} className="p-6 space-y-4">
              <div>
                <label className="block text-[15px] font-medium text-[#3D4A44] mb-2">
                  Song Title <span className="text-[#C47068]">*</span>
                </label>
                <input
                  type="text"
                  value={newSong.title}
                  onChange={(e) => setNewSong({...newSong, title: e.target.value})}
                  required
                  className="w-full px-4 py-3 border border-[rgba(59,77,67,0.2)] rounded-xl focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                  placeholder="Enter song title"
                />
              </div>

              <div>
                <label className="block text-[15px] font-medium text-[#3D4A44] mb-2">
                  Primary Artist
                </label>
                <input
                  type="text"
                  value={newSong.primary_artist}
                  onChange={(e) => setNewSong({...newSong, primary_artist: e.target.value})}
                  className="w-full px-4 py-3 border border-[rgba(59,77,67,0.2)] rounded-xl focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                  placeholder={creator?.display_name || "Artist name"}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-[15px] font-medium text-[#3D4A44] mb-2">ISRC</label>
                  <input
                    type="text"
                    value={newSong.isrc}
                    onChange={(e) => setNewSong({...newSong, isrc: e.target.value})}
                    className="w-full px-4 py-3 border border-[rgba(59,77,67,0.2)] rounded-xl focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                    placeholder="XX-XXX-00-00000"
                  />
                </div>
                <div>
                  <label className="block text-[15px] font-medium text-[#3D4A44] mb-2">ISWC</label>
                  <input
                    type="text"
                    value={newSong.iswc}
                    onChange={(e) => setNewSong({...newSong, iswc: e.target.value})}
                    className="w-full px-4 py-3 border border-[rgba(59,77,67,0.2)] rounded-xl focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                    placeholder="T-000000000-0"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-[15px] font-medium text-[#3D4A44] mb-2">Project/Album</label>
                  <input
                    type="text"
                    value={newSong.project_title}
                    onChange={(e) => setNewSong({...newSong, project_title: e.target.value})}
                    className="w-full px-4 py-3 border border-[rgba(59,77,67,0.2)] rounded-xl focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                    placeholder="Album name"
                  />
                </div>
                <div>
                  <label className="block text-[15px] font-medium text-[#3D4A44] mb-2">Release Date</label>
                  <input
                    type="date"
                    value={newSong.release_date}
                    onChange={(e) => setNewSong({...newSong, release_date: e.target.value})}
                    className="w-full px-4 py-3 border border-[rgba(59,77,67,0.2)] rounded-xl focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[15px] font-medium text-[#3D4A44] mb-2">Label</label>
                <input
                  type="text"
                  value={newSong.label}
                  onChange={(e) => setNewSong({...newSong, label: e.target.value})}
                  className="w-full px-4 py-3 border border-[rgba(59,77,67,0.2)] rounded-xl focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                  placeholder="Record label"
                />
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-[15px] font-medium text-[#3D4A44] mb-2">Pub %</label>
                  <input
                    type="number"
                    value={newSong.publishing_percentage}
                    onChange={(e) => setNewSong({...newSong, publishing_percentage: e.target.value})}
                    className="w-full px-4 py-3 border border-[rgba(59,77,67,0.2)] rounded-xl focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                    placeholder="0-100"
                    min="0"
                    max="100"
                    step="0.01"
                  />
                </div>
                <div>
                  <label className="block text-[15px] font-medium text-[#3D4A44] mb-2">Master %</label>
                  <input
                    type="number"
                    value={newSong.master_percentage}
                    onChange={(e) => setNewSong({...newSong, master_percentage: e.target.value})}
                    className="w-full px-4 py-3 border border-[rgba(59,77,67,0.2)] rounded-xl focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                    placeholder="0-100"
                    min="0"
                    max="100"
                    step="0.01"
                  />
                </div>
                <div>
                  <label className="block text-[15px] font-medium text-[#3D4A44] mb-2">Advance</label>
                  <input
                    type="number"
                    value={newSong.advance_amount}
                    onChange={(e) => setNewSong({...newSong, advance_amount: e.target.value})}
                    className="w-full px-4 py-3 border border-[rgba(59,77,67,0.2)] rounded-xl focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                    placeholder="$"
                    min="0"
                    step="0.01"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[15px] font-medium text-[#3D4A44] mb-2">Notes</label>
                <textarea
                  value={newSong.notes}
                  onChange={(e) => setNewSong({...newSong, notes: e.target.value})}
                  className="w-full px-4 py-3 border border-[rgba(59,77,67,0.2)] rounded-xl focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent resize-none"
                  placeholder="Additional notes..."
                  rows={3}
                />
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowAddSongModal(false)}
                  className="flex-1 px-4 py-3 border border-[rgba(59,77,67,0.2)] text-[#3D4A44] rounded-xl font-medium hover:bg-[#EEF1EC] transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={addingSong || !newSong.title.trim()}
                  className="flex-1 px-4 py-3 bg-[#5B8A72] text-white rounded-xl font-medium hover:bg-[#4A7862] transition-colors disabled:opacity-50"
                >
                  {addingSong ? 'Adding...' : 'Add Song'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showEditCreatorModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6 mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-semibold text-[#3D4A44]">Edit Creator</h2>
              <button onClick={() => setShowEditCreatorModal(false)} className="p-2 hover:bg-[#EEF1EC] rounded-lg">
                <XMarkIcon className="w-5 h-5 text-[#7A8580]" />
              </button>
            </div>

            <form onSubmit={handleUpdateCreator} className="space-y-4">
              <div>
                <label className="block text-[15px] font-medium text-[#3D4A44] mb-2">Display Name *</label>
                <input
                  type="text"
                  value={creatorForm.display_name}
                  onChange={(e) => setCreatorForm({...creatorForm, display_name: e.target.value})}
                  required
                  className="w-full px-4 py-3 border border-[rgba(59,77,67,0.2)] rounded-xl focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                  placeholder="Stage name or brand"
                />
              </div>

              <div>
                <label className="block text-[15px] font-medium text-[#3D4A44] mb-2">Legal Name</label>
                <input
                  type="text"
                  value={creatorForm.legal_name}
                  onChange={(e) => setCreatorForm({...creatorForm, legal_name: e.target.value})}
                  className="w-full px-4 py-3 border border-[rgba(59,77,67,0.2)] rounded-xl focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                  placeholder="Full legal name"
                />
              </div>

              <div>
                <label className="block text-[15px] font-medium text-[#3D4A44] mb-2">Email</label>
                <input
                  type="email"
                  value={creatorForm.email}
                  onChange={(e) => setCreatorForm({...creatorForm, email: e.target.value})}
                  className="w-full px-4 py-3 border border-[rgba(59,77,67,0.2)] rounded-xl focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                  placeholder="creator@example.com"
                />
              </div>

              <div>
                <label className="block text-[15px] font-medium text-[#3D4A44] mb-2">Roles</label>
                <div className="flex flex-wrap gap-2">
                  {ROLE_OPTIONS.map(role => (
                    <button
                      key={role}
                      type="button"
                      onClick={() => handleCreatorRoleToggle(role)}
                      className={`px-4 py-2 rounded-lg border font-medium transition-colors ${
                        creatorForm.roles.includes(role)
                          ? 'bg-[#5B8A72] text-white border-[#5B8A72]'
                          : 'border-[rgba(59,77,67,0.2)] text-[#3D4A44] hover:bg-[#EEF1EC]'
                      }`}
                    >
                      {role}
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-[15px] font-medium text-[#3D4A44] mb-2">Primary Territory</label>
                  <input
                    type="text"
                    value={creatorForm.primary_territory}
                    onChange={(e) => setCreatorForm({...creatorForm, primary_territory: e.target.value})}
                    className="w-full px-4 py-3 border border-[rgba(59,77,67,0.2)] rounded-xl focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                    placeholder="e.g., US, UK, WW"
                  />
                </div>
                <div>
                  <label className="block text-[15px] font-medium text-[#3D4A44] mb-2">Primary PRO</label>
                  <select
                    value={creatorForm.primary_pro}
                    onChange={(e) => setCreatorForm({...creatorForm, primary_pro: e.target.value})}
                    className="w-full px-4 py-3 border border-[rgba(59,77,67,0.2)] rounded-xl focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                  >
                    <option value="">Select PRO</option>
                    {PRO_OPTIONS.map(pro => (
                      <option key={pro} value={pro}>{pro}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-[15px] font-medium text-[#3D4A44] mb-2">IPI Number</label>
                <input
                  type="text"
                  value={creatorForm.primary_ipi}
                  onChange={(e) => setCreatorForm({...creatorForm, primary_ipi: e.target.value})}
                  className="w-full px-4 py-3 border border-[rgba(59,77,67,0.2)] rounded-xl focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                  placeholder="IPI/CAE Number"
                />
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowEditCreatorModal(false)}
                  className="flex-1 px-4 py-3 border border-[rgba(59,77,67,0.2)] text-[#3D4A44] rounded-xl font-medium hover:bg-[#EEF1EC] transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={editingCreator || !creatorForm.display_name.trim()}
                  className="flex-1 px-4 py-3 bg-[#5B8A72] text-white rounded-xl font-medium hover:bg-[#4A7862] transition-colors disabled:opacity-50"
                >
                  {editingCreator ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
