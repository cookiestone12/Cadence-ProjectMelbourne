import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import axios from 'axios'

export default function HomePage() {
  const [org, setOrg] = useState(null)
  const [recentSongs, setRecentSongs] = useState([])
  const [needsAttention, setNeedsAttention] = useState([])
  const [topCreators, setTopCreators] = useState([])
  const [loading, setLoading] = useState(true)
  
  useEffect(() => {
    async function loadDashboard() {
      try {
        const orgResponse = await axios.get('/api/organizations/current')
        setOrg(orgResponse.data)
        const orgId = orgResponse.data.id
        
        const [songsResponse, creatorsResponse] = await Promise.all([
          axios.get(`/api/songs/org/${orgId}`),
          axios.get(`/api/creators/org/${orgId}`)
        ])
        
        const songs = songsResponse.data
        setRecentSongs(songs.slice(0, 5))
        
        const lowHealth = songs
          .filter(s => s.status_health_score < 50)
          .sort((a, b) => a.status_health_score - b.status_health_score)
          .slice(0, 5)
        setNeedsAttention(lowHealth)
        
        const creators = creatorsResponse.data
          .sort((a, b) => b.song_count - a.song_count)
          .slice(0, 4)
        setTopCreators(creators)
      } catch (error) {
        console.error('Failed to load dashboard:', error)
      } finally {
        setLoading(false)
      }
    }
    
    loadDashboard()
  }, [])
  
  if (loading) {
    return (
      <div className="min-h-screen bg-[#F5F7F4] flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-[#5B8A72] border-t-transparent"></div>
          <p className="mt-4 text-[#7A8580]">Loading dashboard...</p>
        </div>
      </div>
    )
  }
  
  return (
    <div className="min-h-screen bg-[#F5F7F4] p-6 lg:p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-[34px] font-semibold text-[#3D4A44] leading-tight">
            Welcome back, {org?.name}
          </h1>
          <p className="text-[17px] text-[#7A8580] mt-1">Here's what's happening with your catalog</p>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
          <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6 relative overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-[#5B8A72] to-[#7BA594]"></div>
            <p className="text-[13px] text-[#7A8580] mb-1">Total Songs</p>
            <p className="text-[40px] font-semibold text-[#3D4A44]">{org?.song_count || 0}</p>
          </div>
          
          <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6 relative overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-[#7BA594] to-[#4A7A62]"></div>
            <p className="text-[13px] text-[#7A8580] mb-1">Active Creators</p>
            <p className="text-[40px] font-semibold text-[#3D4A44]">{org?.creator_count || 0}</p>
          </div>
          
          <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6 relative overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-[#5A8A9A] to-[#7BA5B4]"></div>
            <p className="text-[13px] text-[#7A8580] mb-1">Placements</p>
            <p className="text-[40px] font-semibold text-[#3D4A44]">{recentSongs.filter(s => s.is_paid).length}</p>
          </div>
          
          <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6 relative overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-[#5B9A6E] to-[#6BAA7E]"></div>
            <p className="text-[13px] text-[#7A8580] mb-1">Organization</p>
            <p className="text-[22px] font-semibold text-[#3D4A44]">{org?.type || 'Label'}</p>
          </div>
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6">
            <div className="flex justify-between items-center mb-5">
              <h2 className="text-[22px] font-medium text-[#3D4A44]">Needs Attention</h2>
              <Link to="/catalog" className="text-[15px] text-[#5B8A72] hover:underline font-medium">
                View All →
              </Link>
            </div>
            
            <div className="space-y-3">
              {needsAttention.map((song) => (
                <div key={song.id} className="flex items-center justify-between p-4 bg-[#EEF1EC] rounded-xl">
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-[#3D4A44] truncate">{song.title}</p>
                    <p className="text-[13px] text-[#7A8580]">{song.primary_artist}</p>
                  </div>
                  <div className="ml-4">
                    <span className="px-3 py-1 bg-[rgba(196,112,104,0.15)] text-[#C47068] rounded-full text-[13px] font-medium">
                      {song.status_health_score.toFixed(0)}%
                    </span>
                  </div>
                </div>
              ))}
              
              {needsAttention.length === 0 && (
                <div className="text-center py-8">
                  <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-[rgba(91,154,110,0.15)] flex items-center justify-center">
                    <svg className="w-6 h-6 text-[#5B9A6E]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <p className="text-[#7A8580]">All songs in good health!</p>
                </div>
              )}
            </div>
          </div>
          
          <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6">
            <div className="flex justify-between items-center mb-5">
              <h2 className="text-[22px] font-medium text-[#3D4A44]">Top Creators</h2>
              <Link to="/roster" className="text-[15px] text-[#5B8A72] hover:underline font-medium">
                View All →
              </Link>
            </div>
            
            <div className="space-y-3">
              {topCreators.map((creator) => (
                <Link
                  key={creator.id}
                  to={`/roster/${creator.id}`}
                  className="flex items-center space-x-4 p-4 bg-[#EEF1EC] rounded-xl hover:bg-[#E5E5EA] transition-colors"
                >
                  <div className="w-12 h-12 rounded-full bg-gradient-to-r from-[#5B8A72] to-[#7BA594] flex items-center justify-center text-white font-semibold shadow-md">
                    {creator.display_name.charAt(0).toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-[#3D4A44] truncate">{creator.display_name}</p>
                    <p className="text-[13px] text-[#7A8580]">{creator.song_count} songs</p>
                  </div>
                  <div className={`text-[15px] font-medium ${
                    creator.avg_health_score >= 80 ? 'text-[#5B9A6E]' :
                    creator.avg_health_score >= 60 ? 'text-[#C4956B]' :
                    'text-[#C47068]'
                  }`}>
                    {creator.avg_health_score?.toFixed(0) || 0}%
                  </div>
                </Link>
              ))}
              
              {topCreators.length === 0 && (
                <div className="text-center py-8">
                  <p className="text-[#7A8580]">No creators yet</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
