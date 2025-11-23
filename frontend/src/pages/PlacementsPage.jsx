import React, { useState, useEffect } from 'react'
import axios from 'axios'

export default function PlacementsPage() {
  const [songs, setSongs] = useState([])
  const [loading, setLoading] = useState(true)
  
  useEffect(() => {
    async function loadPlacements() {
      try {
        const orgResponse = await axios.get('/api/organizations/current')
        const orgId = orgResponse.data.id
        
        const response = await axios.get(`/api/songs/org/${orgId}`)
        const placedSongs = response.data.filter(song => 
          song.has_contract_sent || song.has_contract_executed || 
          song.is_registered_with_pro || song.is_paid
        )
        setSongs(placedSongs)
      } catch (error) {
        console.error('Failed to load placements:', error)
      } finally {
        setLoading(false)
      }
    }
    
    loadPlacements()
  }, [])
  
  const getPlacementStage = (song) => {
    if (song.is_paid) return { label: 'Paid', color: 'bg-green-500', progress: 100 }
    if (song.is_registered_with_pro || song.is_registered_with_dsp) return { label: 'Registered', color: 'bg-blue-500', progress: 75 }
    if (song.has_contract_executed) return { label: 'Executed', color: 'bg-purple-500', progress: 50 }
    if (song.has_contract_sent) return { label: 'Contract Sent', color: 'bg-yellow-500', progress: 25 }
    return { label: 'Offer', color: 'bg-gray-400', progress: 10 }
  }
  
  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-400">Loading placements...</div>
      </div>
    )
  }
  
  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-gray-900 mb-2">Placements</h1>
        <p className="text-gray-600">Track your placement pipeline from offer to payment</p>
      </div>
      
      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">Song</th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">Artist</th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">Project</th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">Release Date</th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">Stage</th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">Progress</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {songs.map((song) => {
                const stage = getPlacementStage(song)
                
                return (
                  <tr key={song.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4">
                      <div className="font-medium text-gray-900">{song.title}</div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {song.primary_artist}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {song.project_title || '-'}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {song.release_date || '-'}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium text-white ${stage.color}`}>
                        {stage.label}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center space-x-3">
                        <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                          <div 
                            className={`h-full ${stage.color}`}
                            style={{ width: `${stage.progress}%` }}
                          ></div>
                        </div>
                        <span className="text-sm font-medium text-gray-600">{stage.progress}%</span>
                      </div>
                    </td>
                  </tr>
                )
              })}
              
              {songs.length === 0 && (
                <tr>
                  <td colSpan="6" className="px-6 py-12 text-center text-gray-400">
                    No placements found
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
