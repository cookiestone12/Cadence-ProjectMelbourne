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
    if (song.is_paid) return { label: 'Paid', color: 'bg-[#5B9A6E]', progress: 100 }
    if (song.is_registered_with_pro || song.is_registered_with_dsp) return { label: 'Registered', color: 'bg-[#5A8A9A]', progress: 75 }
    if (song.has_contract_executed) return { label: 'Executed', color: 'bg-[#5B8A72]', progress: 50 }
    if (song.has_contract_sent) return { label: 'Contract Sent', color: 'bg-[#C4956B]', progress: 25 }
    return { label: 'Offer', color: 'bg-[#7A8580]', progress: 10 }
  }
  
  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-[#7A8580]">Loading placements...</div>
      </div>
    )
  }
  
  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-[#3D4A44] mb-2">Placements</h1>
        <p className="text-[#7A8580]">Track your placement pipeline from offer to payment</p>
      </div>
      
      <div className="bg-[#FAFBF9] rounded-xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-[#EEF1EC] border-b border-[rgba(59,77,67,0.08)]">
              <tr>
                <th className="px-6 py-4 text-left text-sm font-semibold text-[#3D4A44]">Song</th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-[#3D4A44]">Artist</th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-[#3D4A44]">Project</th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-[#3D4A44]">Release Date</th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-[#3D4A44]">Stage</th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-[#3D4A44]">Progress</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[rgba(59,77,67,0.08)]">
              {songs.map((song) => {
                const stage = getPlacementStage(song)
                
                return (
                  <tr key={song.id} className="hover:bg-[#EEF1EC] transition-colors">
                    <td className="px-6 py-4">
                      <div className="font-medium text-[#3D4A44]">{song.title}</div>
                    </td>
                    <td className="px-6 py-4 text-sm text-[#7A8580]">
                      {song.primary_artist}
                    </td>
                    <td className="px-6 py-4 text-sm text-[#7A8580]">
                      {song.project_title || '-'}
                    </td>
                    <td className="px-6 py-4 text-sm text-[#7A8580]">
                      {song.release_date || '-'}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium text-white ${stage.color}`}>
                        {stage.label}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center space-x-3">
                        <div className="flex-1 h-2 bg-[#EEF1EC] rounded-full overflow-hidden">
                          <div 
                            className={`h-full ${stage.color}`}
                            style={{ width: `${stage.progress}%` }}
                          ></div>
                        </div>
                        <span className="text-sm font-medium text-[#7A8580]">{stage.progress}%</span>
                      </div>
                    </td>
                  </tr>
                )
              })}
              
              {songs.length === 0 && (
                <tr>
                  <td colSpan="6" className="px-6 py-12 text-center text-[#7A8580]">
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
