import React, { useState, useEffect } from 'react'
import axios from 'axios'
import { 
  FunnelIcon, MagnifyingGlassIcon, PlusIcon, ArrowUpTrayIcon,
  CheckCircleIcon, XCircleIcon, MinusCircleIcon
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
                <th className="px-4 py-3 text-left text-xs font-semibold text-[#3D4A44]">Contract</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-[#3D4A44]">PRO</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-[#3D4A44]">DSP</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-[#3D4A44]">Paid</th>
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
                  <td className="px-4 py-3">{getStatusIcon(song.has_contract_executed ? 'Yes' : 'No')}</td>
                  <td className="px-4 py-3">{getStatusIcon(song.is_registered_with_pro ? 'Yes' : 'No')}</td>
                  <td className="px-4 py-3">{getStatusIcon(song.is_registered_with_dsp ? 'Yes' : 'No')}</td>
                  <td className="px-4 py-3">
                    {song.payment_status === 'PAID' ? (
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-[rgba(91,154,110,0.12)] text-[#5B9A6E]">
                        PAID
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-[rgba(59,77,67,0.06)] text-[#7A8580]">
                        {song.payment_status || 'N/A'}
                      </span>
                    )}
                  </td>
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
    </div>
  )
}
