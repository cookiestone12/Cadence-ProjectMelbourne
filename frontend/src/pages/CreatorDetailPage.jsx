import React, { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import axios from 'axios'
import { ArrowLeftIcon, ArrowDownTrayIcon } from '@heroicons/react/24/outline'

export default function CreatorDetailPage() {
  const { id } = useParams()
  const [creator, setCreator] = useState(null)
  const [songs, setSongs] = useState([])
  const [activeTab, setActiveTab] = useState('overview')
  const [loading, setLoading] = useState(true)
  
  useEffect(() => {
    async function loadCreatorData() {
      try {
        const creatorResponse = await axios.get(`/api/creators/${id}`)
        setCreator(creatorResponse.data)
        
        const orgResponse = await axios.get('/api/organizations/current')
        const orgId = orgResponse.data.id
        
        const songsResponse = await axios.get(`/api/songs/org/${orgId}?creator_id=${id}&limit=1000`)
        setSongs(songsResponse.data)
      } catch (error) {
        console.error('Failed to load creator:', error)
      } finally {
        setLoading(false)
      }
    }
    
    loadCreatorData()
  }, [id])
  
  const handleScheduleAExport = async () => {
    try {
      const response = await axios.get(`/api/schedule-a/creator/${id}`, {
        responseType: 'blob'
      })
      
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `schedule-a-${creator.display_name}.csv`)
      document.body.appendChild(link)
      link.click()
      link.remove()
    } catch (error) {
      console.error('Failed to export Schedule A:', error)
    }
  }
  
  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-400">Loading creator...</div>
      </div>
    )
  }
  
  if (!creator) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-400">Creator not found</div>
      </div>
    )
  }
  
  const placedSongs = songs.filter(s => s.is_paid)
  
  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'songs', label: 'Songs' },
    { id: 'placements', label: 'Placements' },
    { id: 'schedule-a', label: 'Schedule A' }
  ]
  
  return (
    <div className="min-h-screen bg-gray-100">
      <div className="relative h-80 bg-gradient-to-br from-purple-600 to-pink-500">
        {creator.hero_image_url && (
          <img 
            src={creator.hero_image_url} 
            alt={creator.display_name}
            className="absolute inset-0 w-full h-full object-cover mix-blend-overlay opacity-50"
          />
        )}
        
        <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent"></div>
        
        <div className="relative h-full flex flex-col justify-end p-8">
          <Link 
            to="/roster" 
            className="inline-flex items-center space-x-2 text-white/80 hover:text-white mb-4 w-fit"
          >
            <ArrowLeftIcon className="w-5 h-5" />
            <span>Back to Roster</span>
          </Link>
          
          <h1 className="text-5xl font-bold text-white mb-2">{creator.display_name}</h1>
          <div className="flex items-center space-x-4 text-white/90">
            <span className="text-lg">{creator.roles.join(', ')}</span>
            <span>•</span>
            <span>{creator.song_count} songs</span>
            <span>•</span>
            <span>{placedSongs.length} placements</span>
          </div>
        </div>
      </div>
      
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="px-8">
          <div className="flex space-x-8">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`py-4 px-2 border-b-2 font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'border-purple-600 text-purple-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
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
              <div className="bg-white rounded-xl shadow-sm p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4">Performance</h2>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <p className="text-sm text-gray-500 mb-1">Total Songs</p>
                    <p className="text-2xl font-bold text-gray-900">{creator.song_count}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500 mb-1">Avg Health</p>
                    <p className="text-2xl font-bold text-gray-900">{creator.avg_health_score.toFixed(0)}%</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500 mb-1">Placements</p>
                    <p className="text-2xl font-bold text-gray-900">{creator.placement_count}</p>
                  </div>
                </div>
              </div>
              
              <div className="bg-white rounded-xl shadow-sm p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4">Recent Songs</h2>
                <div className="space-y-3">
                  {songs.slice(0, 5).map((song) => (
                    <div key={song.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-gray-900 truncate">{song.title}</p>
                        <p className="text-sm text-gray-500">{song.primary_artist}</p>
                      </div>
                      <div className="ml-4">
                        <div className={`px-3 py-1 rounded-full text-sm font-medium ${
                          song.status_health_score >= 75 ? 'bg-green-100 text-green-700' :
                          song.status_health_score >= 50 ? 'bg-blue-100 text-blue-700' :
                          song.status_health_score >= 25 ? 'bg-yellow-100 text-yellow-700' :
                          'bg-red-100 text-red-700'
                        }`}>
                          {song.status_health_score.toFixed(0)}%
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            
            <div className="space-y-6">
              <div className="bg-white rounded-xl shadow-sm p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4">Details</h2>
                <div className="space-y-3 text-sm">
                  {creator.legal_name && (
                    <div>
                      <p className="text-gray-500">Legal Name</p>
                      <p className="font-medium text-gray-900">{creator.legal_name}</p>
                    </div>
                  )}
                  {creator.primary_territory && (
                    <div>
                      <p className="text-gray-500">Territory</p>
                      <p className="font-medium text-gray-900">{creator.primary_territory}</p>
                    </div>
                  )}
                  {creator.primary_pro && (
                    <div>
                      <p className="text-gray-500">PRO</p>
                      <p className="font-medium text-gray-900">{creator.primary_pro}</p>
                    </div>
                  )}
                  {creator.primary_ipi && (
                    <div>
                      <p className="text-gray-500">IPI</p>
                      <p className="font-medium text-gray-900">{creator.primary_ipi}</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
        
        {activeTab === 'songs' && (
          <div className="bg-white rounded-xl shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">Title</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">Artist</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">Release Date</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">Health</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {songs.map((song) => (
                    <tr key={song.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4">
                        <div className="font-medium text-gray-900">{song.title}</div>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600">
                        {song.primary_artist}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600">
                        {song.release_date || '-'}
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center">
                          <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden mr-3">
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
                          <span className="text-sm font-medium text-gray-600">
                            {song.status_health_score.toFixed(0)}%
                          </span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
        
        {activeTab === 'placements' && (
          <div className="bg-white rounded-xl shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">Song</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">Project</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {placedSongs.map((song) => (
                    <tr key={song.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4">
                        <div className="font-medium text-gray-900">{song.title}</div>
                        <div className="text-sm text-gray-500">{song.primary_artist}</div>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600">
                        {song.project_title || '-'}
                      </td>
                      <td className="px-6 py-4">
                        <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium text-white bg-green-500">
                          Paid
                        </span>
                      </td>
                    </tr>
                  ))}
                  
                  {placedSongs.length === 0 && (
                    <tr>
                      <td colSpan="3" className="px-6 py-12 text-center text-gray-400">
                        No placements yet
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
        
        {activeTab === 'schedule-a' && (
          <div className="bg-white rounded-xl shadow-sm p-12 text-center">
            <h2 className="text-2xl font-bold text-gray-900 mb-3">Schedule A Export</h2>
            <p className="text-gray-600 mb-6 max-w-2xl mx-auto">
              Export a complete Schedule A document for {creator.display_name}'s catalog. 
              This includes all songs with credits, splits, and registration details.
            </p>
            
            <button
              onClick={handleScheduleAExport}
              className="inline-flex items-center space-x-2 bg-gradient-to-r from-purple-600 to-pink-500 text-white px-6 py-3 rounded-lg font-medium hover:from-purple-700 hover:to-pink-600 transition-all duration-200"
            >
              <ArrowDownTrayIcon className="w-5 h-5" />
              <span>Download Schedule A (CSV)</span>
            </button>
            
            <div className="mt-8 grid grid-cols-3 gap-4 max-w-2xl mx-auto">
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-sm text-gray-500 mb-1">Total Songs</p>
                <p className="text-2xl font-bold text-gray-900">{songs.length}</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-sm text-gray-500 mb-1">Placements</p>
                <p className="text-2xl font-bold text-gray-900">{placedSongs.length}</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-sm text-gray-500 mb-1">Avg Health</p>
                <p className="text-2xl font-bold text-gray-900">{creator.avg_health_score.toFixed(0)}%</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
