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
      <div className="min-h-screen bg-[#F7F7F9] flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-[#A020F0] border-t-transparent"></div>
          <p className="mt-4 text-[#86868B]">Loading dashboard...</p>
        </div>
      </div>
    )
  }
  
  return (
    <div className="min-h-screen bg-[#F7F7F9] p-6 lg:p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-[34px] font-semibold text-[#1D1D1F] leading-tight">
            Welcome back, {org?.name}
          </h1>
          <p className="text-[17px] text-[#86868B] mt-1">Here's what's happening with your catalog</p>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
          <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6 relative overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-[#A020F0] to-[#E540AC]"></div>
            <p className="text-[13px] text-[#86868B] mb-1">Total Songs</p>
            <p className="text-[40px] font-semibold text-[#1D1D1F]">{org?.song_count || 0}</p>
          </div>
          
          <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6 relative overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-[#E540AC] to-[#FF2F71]"></div>
            <p className="text-[13px] text-[#86868B] mb-1">Active Creators</p>
            <p className="text-[40px] font-semibold text-[#1D1D1F]">{org?.creator_count || 0}</p>
          </div>
          
          <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6 relative overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-[#007AFF] to-[#5AC8FA]"></div>
            <p className="text-[13px] text-[#86868B] mb-1">Placements</p>
            <p className="text-[40px] font-semibold text-[#1D1D1F]">{recentSongs.filter(s => s.is_paid).length}</p>
          </div>
          
          <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6 relative overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-[#34C759] to-[#30D158]"></div>
            <p className="text-[13px] text-[#86868B] mb-1">Organization</p>
            <p className="text-[22px] font-semibold text-[#1D1D1F]">{org?.type || 'Label'}</p>
          </div>
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6">
            <div className="flex justify-between items-center mb-5">
              <h2 className="text-[22px] font-medium text-[#1D1D1F]">Needs Attention</h2>
              <Link to="/catalog" className="text-[15px] text-[#A020F0] hover:underline font-medium">
                View All →
              </Link>
            </div>
            
            <div className="space-y-3">
              {needsAttention.map((song) => (
                <div key={song.id} className="flex items-center justify-between p-4 bg-[#F2F2F5] rounded-xl">
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-[#1D1D1F] truncate">{song.title}</p>
                    <p className="text-[13px] text-[#86868B]">{song.primary_artist}</p>
                  </div>
                  <div className="ml-4">
                    <span className="px-3 py-1 bg-[rgba(255,59,48,0.15)] text-[#FF3B30] rounded-full text-[13px] font-medium">
                      {song.status_health_score.toFixed(0)}%
                    </span>
                  </div>
                </div>
              ))}
              
              {needsAttention.length === 0 && (
                <div className="text-center py-8">
                  <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-[rgba(52,199,89,0.15)] flex items-center justify-center">
                    <svg className="w-6 h-6 text-[#34C759]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <p className="text-[#86868B]">All songs in good health!</p>
                </div>
              )}
            </div>
          </div>
          
          <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6">
            <div className="flex justify-between items-center mb-5">
              <h2 className="text-[22px] font-medium text-[#1D1D1F]">Top Creators</h2>
              <Link to="/roster" className="text-[15px] text-[#A020F0] hover:underline font-medium">
                View All →
              </Link>
            </div>
            
            <div className="space-y-3">
              {topCreators.map((creator) => (
                <Link
                  key={creator.id}
                  to={`/roster/${creator.id}`}
                  className="flex items-center space-x-4 p-4 bg-[#F2F2F5] rounded-xl hover:bg-[#E5E5EA] transition-colors"
                >
                  <div className="w-12 h-12 rounded-full bg-gradient-to-r from-[#A020F0] to-[#E540AC] flex items-center justify-center text-white font-semibold shadow-md">
                    {creator.display_name.charAt(0).toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-[#1D1D1F] truncate">{creator.display_name}</p>
                    <p className="text-[13px] text-[#86868B]">{creator.song_count} songs</p>
                  </div>
                  <div className={`text-[15px] font-medium ${
                    creator.avg_health_score >= 80 ? 'text-[#34C759]' :
                    creator.avg_health_score >= 60 ? 'text-[#FF9500]' :
                    'text-[#FF3B30]'
                  }`}>
                    {creator.avg_health_score?.toFixed(0) || 0}%
                  </div>
                </Link>
              ))}
              
              {topCreators.length === 0 && (
                <div className="text-center py-8">
                  <p className="text-[#86868B]">No creators yet</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
