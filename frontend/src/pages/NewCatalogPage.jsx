import React, { useState, useEffect } from 'react'
import axios from 'axios'
import { 
  FunnelIcon, MagnifyingGlassIcon, PlusIcon, ArrowUpTrayIcon,
  CheckCircleIcon, XCircleIcon, MinusCircleIcon, LinkIcon
} from '@heroicons/react/24/outline'
import SongDetailModal from '../components/SongDetailModal'
import AddSongModal from '../components/AddSongModal'
import ScheduleAUploadModal from '../components/ScheduleAUploadModal'

export default function NewCatalogPage() {
  const [songs, setSongs] = useState([])
  const [creators, setCreators] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [activeTab, setActiveTab] = useState('all')
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
  
  useEffect(() => {
    loadData()
  }, [filters])
  
  async function loadData() {
    try {
      const orgResponse = await axios.get('/api/organizations/current')
      const orgId = orgResponse.data.id
      setOrganizationId(orgId)
      
      const params = new URLSearchParams()
      if (filters.creator_id) params.append('creator_id', filters.creator_id)
      if (filters.role) params.append('role', filters.role)
      if (filters.min_health) params.append('min_health', filters.min_health)
      if (filters.max_health) params.append('max_health', filters.max_health)
      if (filters.status) params.append('status', filters.status)
      params.append('limit', '1000')
      
      const [songsResponse, creatorsResponse] = await Promise.all([
        axios.get(`/api/songs/org/${orgId}?${params}`),
        axios.get(`/api/creators/org/${orgId}`)
      ])
      
      setSongs(songsResponse.data)
      setCreators(creatorsResponse.data)
    } catch (error) {
      console.error('Failed to load catalog:', error)
    } finally {
      setLoading(false)
    }
  }
  
  const filteredSongs = songs.filter(song => {
    const matchesSearch = !searchTerm || (
      song.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      song.primary_artist.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (song.project_title && song.project_title.toLowerCase().includes(searchTerm.toLowerCase()))
    )
    
    const matchesTab = activeTab === 'all' || 
      (activeTab === 'released' && song.is_released) ||
      (activeTab === 'unreleased' && !song.is_released)
    
    return matchesSearch && matchesTab
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
  
  const getStatusIcon = (value) => {
    if (value === 'Yes') return <CheckCircleIcon className="w-5 h-5 text-[#5B9A6E]" />
    if (value === 'No') return <XCircleIcon className="w-5 h-5 text-[#C47068]" />
    return <MinusCircleIcon className="w-5 h-5 text-[#7A8580]" />
  }
  
  const hasActiveFilters = Object.values(filters).some(v => v !== '')
  
  const releasedCount = songs.filter(s => s.is_released).length
  const unreleasedCount = songs.filter(s => !s.is_released).length
  
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
  
  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-[#7A8580]">Loading catalog...</div>
      </div>
    )
  }
  
  return (
    <div className="p-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold text-[#3D4A44] mb-2">Catalog</h1>
          <p className="text-[#7A8580]">{songs.length} total songs</p>
        </div>
        <div className="flex items-center space-x-3">
          <button 
            className="flex items-center space-x-2 px-4 py-2 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] transition-colors"
            onClick={() => setShowAddModal(true)}
          >
            <PlusIcon className="w-5 h-5" />
            <span>Add Song</span>
          </button>
          <button 
            className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-lg hover:shadow-[0px_4px_12px_rgba(91,138,114,0.3)] transition-all"
            onClick={() => setShowUploadModal(true)}
          >
            <ArrowUpTrayIcon className="w-5 h-5" />
            <span>Upload Schedule A</span>
          </button>
        </div>
      </div>
      
      <div className="mb-6 border-b border-[rgba(59,77,67,0.08)]">
        <div className="flex space-x-8">
          <button
            onClick={() => setActiveTab('all')}
            className={`pb-3 px-1 border-b-2 font-medium transition-colors ${
              activeTab === 'all'
                ? 'border-[#5B8A72] text-[#5B8A72]'
                : 'border-transparent text-[#7A8580] hover:text-[#3D4A44]'
            }`}
          >
            All Songs ({songs.length})
          </button>
          <button
            onClick={() => setActiveTab('released')}
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
      
      <div className="bg-[#FAFBF9] rounded-xl shadow-sm p-4 mb-6">
        <div className="flex items-center space-x-4">
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
            {hasActiveFilters && (
              <span className="bg-white text-[#5B8A72] px-2 py-0.5 rounded-full text-xs font-bold">
                {Object.values(filters).filter(v => v !== '').length}
              </span>
            )}
          </button>
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
      </div>
      
      <div className="bg-[#FAFBF9] rounded-xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-[#EEF1EC] border-b border-[rgba(59,77,67,0.08)]">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-[#3D4A44]">Song</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-[#3D4A44]">Artist</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-[#3D4A44]">Label</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-[#3D4A44]">Pub %</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-[#3D4A44]">Health</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-[#3D4A44]">Released</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-[#3D4A44]">Spotify</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-[#3D4A44]">Contract</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-[#3D4A44]">PRO</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[rgba(59,77,67,0.08)]">
              {filteredSongs.map((song) => (
                <tr 
                  key={song.id} 
                  onClick={() => setSelectedSong(song)}
                  className="hover:bg-[rgba(91,138,114,0.06)] cursor-pointer transition-colors"
                >
                  <td className="px-4 py-3">
                    <div className="font-medium text-[#3D4A44]">{song.title}</div>
                    <div className="text-xs text-[#7A8580]">{song.project_title || '-'}</div>
                  </td>
                  <td className="px-4 py-3 text-sm text-[#7A8580]">
                    {song.primary_artist}
                  </td>
                  <td className="px-4 py-3 text-sm text-[#7A8580]">
                    {song.label || '-'}
                  </td>
                  <td className="px-4 py-3 text-sm text-[#7A8580]">
                    {song.publishing_percentage ? `${Math.min(song.publishing_percentage, 100).toFixed(1)}%` : '-'}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center space-x-2">
                      <div className="flex-1 h-2 bg-[#EEF1EC] rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-gradient-to-r from-[#5B8A72] to-[#7BA594]"
                          style={{ width: `${song.status_health_score || 0}%` }}
                        ></div>
                      </div>
                      <span className="text-xs font-medium text-[#7A8580] w-10">
                        {Math.round(song.status_health_score || 0)}%
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <button
                      onClick={(e) => handleReleasedToggle(e, song)}
                      className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-all ${
                        song.is_released 
                          ? 'bg-[#5B8A72] border-[#5B8A72] text-white' 
                          : 'border-[#7A8580] hover:border-[#5B8A72]'
                      }`}
                    >
                      {song.is_released && (
                        <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      )}
                    </button>
                  </td>
                  <td className="px-4 py-3">
                    {song.spotify_link ? (
                      <button
                        onClick={(e) => openSpotifyLink(e, song.spotify_link)}
                        className="flex items-center space-x-1 text-[#1DB954] hover:underline text-sm"
                      >
                        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                          <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
                        </svg>
                        <span>Open</span>
                      </button>
                    ) : song.is_released ? (
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          setSpotifyModal({ open: true, song, link: '' })
                        }}
                        className="flex items-center space-x-1 text-[#7A8580] hover:text-[#5B8A72] text-sm"
                      >
                        <LinkIcon className="w-4 h-4" />
                        <span>Add Link</span>
                      </button>
                    ) : (
                      <span className="text-xs text-[#7A8580]">-</span>
                    )}
                  </td>
                  <td className="px-4 py-3">{getStatusIcon(song.has_contract_executed ? 'Yes' : 'No')}</td>
                  <td className="px-4 py-3">{getStatusIcon(song.is_registered_with_pro ? 'Yes' : 'No')}</td>
                </tr>
              ))}
              
              {filteredSongs.length === 0 && (
                <tr>
                  <td colSpan="9" className="px-6 py-12 text-center text-[#7A8580]">
                    No songs found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
      
      {selectedSong && (
        <SongDetailModal song={selectedSong} onClose={() => setSelectedSong(null)} />
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
    </div>
  )
}
