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
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-400">Loading dashboard...</div>
      </div>
    )
  }
  
  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-gray-900 mb-2">
          Welcome back, {org?.name}
        </h1>
        <p className="text-gray-600">Here's what's happening with your catalog</p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl shadow-sm p-6 text-white">
          <p className="text-purple-100 text-sm mb-1">Total Songs</p>
          <p className="text-4xl font-bold">{org?.song_count || 0}</p>
        </div>
        
        <div className="bg-gradient-to-br from-pink-500 to-pink-600 rounded-xl shadow-sm p-6 text-white">
          <p className="text-pink-100 text-sm mb-1">Active Creators</p>
          <p className="text-4xl font-bold">{org?.creator_count || 0}</p>
        </div>
        
        <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl shadow-sm p-6 text-white">
          <p className="text-blue-100 text-sm mb-1">Placements</p>
          <p className="text-4xl font-bold">{recentSongs.filter(s => s.is_paid).length}</p>
        </div>
        
        <div className="bg-gradient-to-br from-green-500 to-green-600 rounded-xl shadow-sm p-6 text-white">
          <p className="text-green-100 text-sm mb-1">Organization</p>
          <p className="text-xl font-bold">{org?.type || 'Label'}</p>
        </div>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <div className="bg-white rounded-xl shadow-sm p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-bold text-gray-900">Needs Attention</h2>
            <Link to="/catalog" className="text-sm text-purple-600 hover:text-purple-700">
              View All →
            </Link>
          </div>
          
          <div className="space-y-3">
            {needsAttention.map((song) => (
              <div key={song.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-gray-900 truncate">{song.title}</p>
                  <p className="text-sm text-gray-500">{song.primary_artist}</p>
                </div>
                <div className="ml-4">
                  <div className="px-3 py-1 bg-red-100 text-red-700 rounded-full text-sm font-medium">
                    {song.status_health_score.toFixed(0)}%
                  </div>
                </div>
              </div>
            ))}
            
            {needsAttention.length === 0 && (
              <p className="text-center text-gray-400 py-8">All songs in good health!</p>
            )}
          </div>
        </div>
        
        <div className="bg-white rounded-xl shadow-sm p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-bold text-gray-900">Top Creators</h2>
            <Link to="/roster" className="text-sm text-purple-600 hover:text-purple-700">
              View All →
            </Link>
          </div>
          
          <div className="space-y-3">
            {topCreators.map((creator) => (
              <Link
                key={creator.id}
                to={`/roster/${creator.id}`}
                className="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <div className="w-12 h-12 rounded-full bg-gradient-to-r from-purple-400 to-pink-500 flex items-center justify-center text-white font-bold">
                  {creator.display_name.charAt(0).toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-gray-900 truncate">{creator.display_name}</p>
                  <p className="text-sm text-gray-500">{creator.song_count} songs</p>
                </div>
                <div className="text-sm font-medium text-gray-600">
                  {creator.avg_health_score.toFixed(0)}%
                </div>
              </Link>
            ))}
            
            {topCreators.length === 0 && (
              <p className="text-center text-gray-400 py-8">No creators yet</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
