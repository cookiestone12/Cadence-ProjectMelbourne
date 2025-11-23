import React, { useState, useEffect } from 'react'
import axios from 'axios'
import { FunnelIcon, MagnifyingGlassIcon } from '@heroicons/react/24/outline'

export default function CatalogPage() {
  const [songs, setSongs] = useState([])
  const [creators, setCreators] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
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
    if (!searchTerm) return true
    const term = searchTerm.toLowerCase()
    return (
      song.title.toLowerCase().includes(term) ||
      song.primary_artist.toLowerCase().includes(term) ||
      (song.project_title && song.project_title.toLowerCase().includes(term))
    )
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
  
  const hasActiveFilters = Object.values(filters).some(v => v !== '')
  
  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-400">Loading catalog...</div>
      </div>
    )
  }
  
  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="text-4xl font-bold text-gray-900 mb-2">Catalog</h1>
        <p className="text-gray-600">{songs.length} songs in your catalog</p>
      </div>
      
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
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              >
                <option value="">All Creators</option>
                {creators.map((creator) => (
                  <option key={creator.id} value={creator.id}>
                    {creator.display_name}
                  </option>
                ))}
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Role</label>
              <select
                value={filters.role}
                onChange={(e) => handleFilterChange('role', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              >
                <option value="">All Roles</option>
                <option value="WRITER">Writer</option>
                <option value="PRODUCER">Producer</option>
                <option value="PERFORMER">Performer</option>
                <option value="PUBLISHER">Publisher</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Health Score</label>
              <select
                value={filters.min_health}
                onChange={(e) => handleFilterChange('min_health', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              >
                <option value="">Any Health</option>
                <option value="75">Excellent (75%+)</option>
                <option value="50">Good (50%+)</option>
                <option value="25">Fair (25%+)</option>
                <option value="0">All Songs</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
              <select
                value={filters.status}
                onChange={(e) => handleFilterChange('status', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              >
                <option value="">All Statuses</option>
                <option value="paid">Paid</option>
                <option value="invoiced">Invoiced</option>
                <option value="registered">Registered</option>
                <option value="contract_executed">Contract Executed</option>
                <option value="contract_sent">Contract Sent</option>
              </select>
            </div>
            
            {hasActiveFilters && (
              <div className="flex items-end">
                <button
                  onClick={clearFilters}
                  className="w-full px-4 py-2 text-sm text-gray-600 hover:text-gray-900 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  Clear Filters
                </button>
              </div>
            )}
          </div>
        )}
      </div>
      
      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">Title</th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">Artist</th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">Project</th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">ISRC</th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">Release Date</th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">Health</th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {filteredSongs.map((song) => (
                <tr key={song.id} className="hover:bg-gray-50 transition-colors cursor-pointer">
                  <td className="px-6 py-4">
                    <div className="font-medium text-gray-900">{song.title}</div>
                    <div className="text-sm text-gray-500">{song.iswc || 'No ISWC'}</div>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600">
                    {song.primary_artist}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600">
                    {song.project_title || '-'}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600 font-mono">
                    {song.isrc || '-'}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600">
                    {song.release_date || '-'}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center">
                      <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden mr-3 max-w-[100px]">
                        <div 
                          className={`h-full ${
                            song.status_health_score >= 75 ? 'bg-green-500' :
                            song.status_health_score >= 50 ? 'bg-blue-500' :
                            song.status_health_score >= 25 ? 'bg-yellow-500' :
                            'bg-red-500'
                          }`}
                          style={{ width: `${song.status_health_score}%` }}
                        ></div>
                      </div>
                      <span className="text-sm font-medium text-gray-600 w-12">
                        {song.status_health_score.toFixed(0)}%
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex flex-wrap gap-1">
                      {song.is_paid && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700">
                          Paid
                        </span>
                      )}
                      {song.is_registered_with_pro && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-700">
                          PRO
                        </span>
                      )}
                      {song.is_registered_with_dsp && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-700">
                          DSP
                        </span>
                      )}
                      {song.has_contract_executed && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-indigo-100 text-indigo-700">
                          Contract
                        </span>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
              
              {filteredSongs.length === 0 && (
                <tr>
                  <td colSpan="7" className="px-6 py-12 text-center text-gray-400">
                    No songs found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
