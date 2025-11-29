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
  const [activeTab, setActiveTab] = useState('all') // 'all', 'released', 'unreleased'
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
    if (value === 'Yes') return <CheckCircleIcon className="w-5 h-5 text-green-500" />
    if (value === 'No') return <XCircleIcon className="w-5 h-5 text-red-500" />
    return <MinusCircleIcon className="w-5 h-5 text-gray-400" />
  }
  
  const hasActiveFilters = Object.values(filters).some(v => v !== '')
  
  const releasedCount = songs.filter(s => s.is_released).length
  const unreleasedCount = songs.filter(s => !s.is_released).length
  
  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-400">Loading catalog...</div>
      </div>
    )
  }
  
  return (
    <div className="p-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold text-gray-900 mb-2">Catalog</h1>
          <p className="text-gray-600">{songs.length} total songs</p>
        </div>
        <div className="flex items-center space-x-3">
          <button 
            className="flex items-center space-x-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
            onClick={() => setShowAddModal(true)}
          >
            <PlusIcon className="w-5 h-5" />
            <span>Add Song</span>
          </button>
          <button 
            className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-lg hover:from-purple-700 hover:to-pink-700 transition-all"
            onClick={() => setShowUploadModal(true)}
          >
            <ArrowUpTrayIcon className="w-5 h-5" />
            <span>Upload Schedule A</span>
          </button>
        </div>
      </div>
      
      {/* Tabs */}
      <div className="mb-6 border-b border-gray-200">
        <div className="flex space-x-8">
          <button
            onClick={() => setActiveTab('all')}
            className={`pb-3 px-1 border-b-2 font-medium transition-colors ${
              activeTab === 'all'
                ? 'border-purple-600 text-purple-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            All Songs ({songs.length})
          </button>
          <button
            onClick={() => setActiveTab('released')}
            className={`pb-3 px-1 border-b-2 font-medium transition-colors ${
              activeTab === 'released'
                ? 'border-purple-600 text-purple-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            Released ({releasedCount})
          </button>
          <button
            onClick={() => setActiveTab('unreleased')}
            className={`pb-3 px-1 border-b-2 font-medium transition-colors ${
              activeTab === 'unreleased'
                ? 'border-purple-600 text-purple-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            Unreleased ({unreleasedCount})
          </button>
        </div>
      </div>
      
      {/* Search and Filters */}
      <div className="bg-white rounded-xl shadow-sm p-4 mb-6">
        <div className="flex items-center space-x-4">
          <div className="flex-1 relative">
            <MagnifyingGlassIcon className="w-5 h-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search songs, artists, or projects..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            />
          </div>
          
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-colors ${
              hasActiveFilters 
                ? 'bg-purple-600 text-white' 
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            <FunnelIcon className="w-5 h-5" />
            <span>Filters</span>
            {hasActiveFilters && (
              <span className="bg-white text-purple-600 px-2 py-0.5 rounded-full text-xs font-bold">
                {Object.values(filters).filter(v => v !== '').length}
              </span>
            )}
          </button>
        </div>
        
        {showFilters && (
          <div className="mt-4 pt-4 border-t border-gray-200 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Creator</label>
              <select
                value={filters.creator_id}
                onChange={(e) => handleFilterChange('creator_id', e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              >
                <option value="">All Creators</option>
                {creators.map(creator => (
                  <option key={creator.id} value={creator.id}>{creator.display_name}</option>
                ))}
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Min Health</label>
              <input
                type="number"
                value={filters.min_health}
                onChange={(e) => handleFilterChange('min_health', e.target.value)}
                placeholder="0"
                min="0"
                max="100"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Max Health</label>
              <input
                type="number"
                value={filters.max_health}
                onChange={(e) => handleFilterChange('max_health', e.target.value)}
                placeholder="100"
                min="0"
                max="100"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>
            
            <div className="flex items-end">
              <button
                onClick={clearFilters}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
              >
                Clear Filters
              </button>
            </div>
          </div>
        )}
      </div>
      
      {/* Catalog Table */}
      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-900">Song</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-900">Artist</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-900">Label</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-900">Pub %</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-900">Health</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-900">Contract</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-900">PRO</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-900">DSP</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-900">Paid</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {filteredSongs.map((song) => (
                <tr 
                  key={song.id} 
                  onClick={() => setSelectedSong(song)}
                  className="hover:bg-purple-50 cursor-pointer transition-colors"
                >
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900">{song.title}</div>
                    <div className="text-xs text-gray-500">{song.project_title || '-'}</div>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {song.primary_artist}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {song.label || '-'}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {song.publishing_percentage ? `${Math.min(song.publishing_percentage, 100).toFixed(1)}%` : '-'}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center space-x-2">
                      <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-gradient-to-r from-purple-500 to-pink-500"
                          style={{ width: `${song.status_health_score || 0}%` }}
                        ></div>
                      </div>
                      <span className="text-xs font-medium text-gray-600 w-10">
                        {Math.round(song.status_health_score || 0)}%
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3">{getStatusIcon(song.has_contract_executed ? 'Yes' : 'No')}</td>
                  <td className="px-4 py-3">{getStatusIcon(song.is_registered_with_pro ? 'Yes' : 'No')}</td>
                  <td className="px-4 py-3">{getStatusIcon(song.is_registered_with_dsp ? 'Yes' : 'No')}</td>
                  <td className="px-4 py-3">
                    {song.payment_status === 'PAID' ? (
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                        PAID
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
                        {song.payment_status || 'N/A'}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
              
              {filteredSongs.length === 0 && (
                <tr>
                  <td colSpan="9" className="px-6 py-12 text-center text-gray-400">
                    No songs found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
      
      {/* Song Detail Modal */}
      {selectedSong && (
        <SongDetailModal song={selectedSong} onClose={() => setSelectedSong(null)} />
      )}
      
      {/* Add Song Modal */}
      {showAddModal && organizationId && (
        <AddSongModal 
          onClose={() => setShowAddModal(false)}
          onSuccess={loadData}
          organizationId={organizationId}
        />
      )}
      
      {/* Schedule A Upload Modal */}
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
