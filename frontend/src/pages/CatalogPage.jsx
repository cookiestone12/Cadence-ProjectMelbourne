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
        <div className="text-[#7A8580]">Loading catalog...</div>
      </div>
    )
  }
  
  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="text-4xl font-bold text-[#3D4A44] mb-2">Catalog</h1>
        <p className="text-[#7A8580]">{songs.length} songs in your catalog</p>
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
                className="w-full px-3 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
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
              <label className="block text-sm font-medium text-[#3D4A44] mb-1">Role</label>
              <select
                value={filters.role}
                onChange={(e) => handleFilterChange('role', e.target.value)}
                className="w-full px-3 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
              >
                <option value="">All Roles</option>
                <option value="WRITER">Writer</option>
                <option value="PRODUCER">Producer</option>
                <option value="PERFORMER">Performer</option>
                <option value="PUBLISHER">Publisher</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-[#3D4A44] mb-1">Health Score</label>
              <select
                value={filters.min_health}
                onChange={(e) => handleFilterChange('min_health', e.target.value)}
                className="w-full px-3 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
              >
                <option value="">Any Health</option>
                <option value="75">Excellent (75%+)</option>
                <option value="50">Good (50%+)</option>
                <option value="25">Fair (25%+)</option>
                <option value="0">All Songs</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-[#3D4A44] mb-1">Status</label>
              <select
                value={filters.status}
                onChange={(e) => handleFilterChange('status', e.target.value)}
                className="w-full px-3 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
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
                  className="w-full px-4 py-2 text-sm text-[#7A8580] hover:text-[#3D4A44] border border-[rgba(59,77,67,0.12)] rounded-lg hover:bg-[#EEF1EC] transition-colors"
                >
                  Clear Filters
                </button>
              </div>
            )}
          </div>
        )}
      </div>
      
      <div className="bg-[#FAFBF9] rounded-xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-[#EEF1EC] border-b border-[rgba(59,77,67,0.08)]">
              <tr>
                <th className="px-6 py-4 text-left text-sm font-semibold text-[#3D4A44]">Title</th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-[#3D4A44]">Artist</th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-[#3D4A44]">Project</th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-[#3D4A44]">ISRC</th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-[#3D4A44]">Release Date</th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-[#3D4A44]">Health</th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-[#3D4A44]">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[rgba(59,77,67,0.08)]">
              {filteredSongs.map((song) => (
                <tr key={song.id} className="hover:bg-[#EEF1EC] transition-colors cursor-pointer">
                  <td className="px-6 py-4">
                    <div className="font-medium text-[#3D4A44]">{song.title}</div>
                    <div className="text-sm text-[#7A8580]">{song.iswc || 'No ISWC'}</div>
                  </td>
                  <td className="px-6 py-4 text-sm text-[#7A8580]">
                    {song.primary_artist}
                  </td>
                  <td className="px-6 py-4 text-sm text-[#7A8580]">
                    {song.project_title || '-'}
                  </td>
                  <td className="px-6 py-4 text-sm text-[#7A8580] font-mono">
                    {song.isrc || '-'}
                  </td>
                  <td className="px-6 py-4 text-sm text-[#7A8580]">
                    {song.release_date || '-'}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center">
                      <div className="flex-1 h-2 bg-[#EEF1EC] rounded-full overflow-hidden mr-3 max-w-[100px]">
                        <div 
                          className={`h-full ${
                            song.status_health_score >= 75 ? 'bg-[#5B9A6E]' :
                            song.status_health_score >= 50 ? 'bg-[#5A8A9A]' :
                            song.status_health_score >= 25 ? 'bg-[#C4956B]' :
                            'bg-[#C47068]'
                          }`}
                          style={{ width: `${song.status_health_score}%` }}
                        ></div>
                      </div>
                      <span className="text-sm font-medium text-[#7A8580] w-12">
                        {song.status_health_score.toFixed(0)}%
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex flex-wrap gap-1">
                      {song.is_paid && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-[rgba(91,154,110,0.12)] text-[#5B9A6E]">
                          Paid
                        </span>
                      )}
                      {song.is_registered_with_pro && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-[rgba(90,138,154,0.12)] text-[#5A8A9A]">
                          PRO
                        </span>
                      )}
                      {song.is_registered_with_dsp && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-[rgba(91,138,114,0.12)] text-[#5B8A72]">
                          DSP
                        </span>
                      )}
                      {song.has_contract_executed && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-[rgba(107,154,132,0.12)] text-[#6B9A84]">
                          Contract
                        </span>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
              
              {filteredSongs.length === 0 && (
                <tr>
                  <td colSpan="7" className="px-6 py-12 text-center text-[#7A8580]">
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
