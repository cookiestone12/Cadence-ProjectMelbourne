import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import axios from 'axios'

export default function Dashboard() {
  const [songs, setSongs] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchSongs()
  }, [])

  const fetchSongs = async () => {
    try {
      const token = localStorage.getItem('token')
      const response = await axios.get('/api/catalog/songs', {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      setSongs(response.data)
    } catch (error) {
      console.error('Error fetching songs:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#F7F7F9] flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-[#A020F0] border-t-transparent"></div>
          <p className="mt-4 text-[#86868B]">Loading catalog...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#F7F7F9] p-6 lg:p-8">
      <div className="max-w-7xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-[34px] font-semibold text-[#1D1D1F] leading-tight">Catalog Dashboard</h1>
            <p className="text-[17px] text-[#86868B] mt-1">Manage and track your music catalog</p>
          </div>
          <Link
            to="/upload"
            className="bg-gradient-to-r from-[#A020F0] to-[#E540AC] text-white px-6 py-3 rounded-xl font-semibold hover:shadow-lg hover:shadow-purple-500/30 transition-all duration-200"
          >
            Upload Songs
          </Link>
        </div>

        {songs.length === 0 ? (
          <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-12 text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[#F2F2F5] flex items-center justify-center">
              <svg className="w-8 h-8 text-[#86868B]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
              </svg>
            </div>
            <p className="text-[#86868B] mb-4 text-[17px]">No songs in your catalog yet</p>
            <Link to="/upload" className="text-[#A020F0] hover:underline font-medium">
              Upload your first Schedule A
            </Link>
          </div>
        ) : (
          <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] overflow-hidden">
            <table className="min-w-full">
              <thead>
                <tr className="border-b border-[rgba(0,0,0,0.07)]">
                  <th className="px-6 py-4 text-left text-[13px] font-medium text-[#86868B] uppercase tracking-wider">Title</th>
                  <th className="px-6 py-4 text-left text-[13px] font-medium text-[#86868B] uppercase tracking-wider">Artist</th>
                  <th className="px-6 py-4 text-left text-[13px] font-medium text-[#86868B] uppercase tracking-wider">Publishing %</th>
                  <th className="px-6 py-4 text-left text-[13px] font-medium text-[#86868B] uppercase tracking-wider">Valuation</th>
                  <th className="px-6 py-4 text-left text-[13px] font-medium text-[#86868B] uppercase tracking-wider">Score</th>
                  <th className="px-6 py-4 text-left text-[13px] font-medium text-[#86868B] uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody>
                {songs.map((song, index) => (
                  <tr 
                    key={song.id} 
                    className={`hover:bg-[#F2F2F5] transition-colors ${index % 2 === 0 ? 'bg-white' : 'bg-[#F8F8FB]'}`}
                  >
                    <td className="px-6 py-4 whitespace-nowrap font-medium text-[#1D1D1F]">{song.title}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-[#86868B]">{song.artist_name}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-[#1D1D1F]">{song.publishing_percentage}%</td>
                    <td className="px-6 py-4 whitespace-nowrap text-[#34C759] font-semibold">
                      ${song.valuation?.toLocaleString() || '0'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-3 py-1 rounded-full text-[13px] font-medium ${
                        song.score >= 80 ? 'bg-[rgba(52,199,89,0.15)] text-[#34C759]' :
                        song.score >= 60 ? 'bg-[rgba(255,149,0,0.15)] text-[#CC7700]' :
                        'bg-[rgba(255,59,48,0.15)] text-[#FF3B30]'
                      }`}>
                        {song.score}/100
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <Link
                        to={`/song/${song.id}`}
                        className="text-[#A020F0] hover:underline font-medium"
                      >
                        View Details
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
