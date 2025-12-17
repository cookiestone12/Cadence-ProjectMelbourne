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
      <div className="min-h-screen bg-[#F5F7F4] flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-[#5B8A72] border-t-transparent"></div>
          <p className="mt-4 text-[#7A8580]">Loading catalog...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#F5F7F4] p-6 lg:p-8">
      <div className="max-w-7xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-[34px] font-semibold text-[#3D4A44] leading-tight">Catalog Dashboard</h1>
            <p className="text-[17px] text-[#7A8580] mt-1">Manage and track your music catalog</p>
          </div>
          <Link
            to="/upload"
            className="bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white px-6 py-3 rounded-xl font-semibold hover:shadow-lg hover:shadow-[rgba(91,138,114,0.25)] transition-all duration-200"
          >
            Upload Songs
          </Link>
        </div>

        {songs.length === 0 ? (
          <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-12 text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[#EEF1EC] flex items-center justify-center">
              <svg className="w-8 h-8 text-[#7A8580]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
              </svg>
            </div>
            <p className="text-[#7A8580] mb-4 text-[17px]">No songs in your catalog yet</p>
            <Link to="/upload" className="text-[#5B8A72] hover:underline font-medium">
              Upload your first Schedule A
            </Link>
          </div>
        ) : (
          <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] overflow-hidden">
            <table className="min-w-full">
              <thead>
                <tr className="border-b border-[rgba(59,77,67,0.08)]">
                  <th className="px-6 py-4 text-left text-[13px] font-medium text-[#7A8580] uppercase tracking-wider">Title</th>
                  <th className="px-6 py-4 text-left text-[13px] font-medium text-[#7A8580] uppercase tracking-wider">Artist</th>
                  <th className="px-6 py-4 text-left text-[13px] font-medium text-[#7A8580] uppercase tracking-wider">Publishing %</th>
                  <th className="px-6 py-4 text-left text-[13px] font-medium text-[#7A8580] uppercase tracking-wider">Valuation</th>
                  <th className="px-6 py-4 text-left text-[13px] font-medium text-[#7A8580] uppercase tracking-wider">Score</th>
                  <th className="px-6 py-4 text-left text-[13px] font-medium text-[#7A8580] uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody>
                {songs.map((song, index) => (
                  <tr 
                    key={song.id} 
                    className={`hover:bg-[#EEF1EC] transition-colors ${index % 2 === 0 ? 'bg-white' : 'bg-[#F8F8FB]'}`}
                  >
                    <td className="px-6 py-4 whitespace-nowrap font-medium text-[#3D4A44]">{song.title}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-[#7A8580]">{song.artist_name}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-[#3D4A44]">{song.publishing_percentage}%</td>
                    <td className="px-6 py-4 whitespace-nowrap text-[#5B9A6E] font-semibold">
                      ${song.valuation?.toLocaleString() || '0'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-3 py-1 rounded-full text-[13px] font-medium ${
                        song.score >= 80 ? 'bg-[rgba(91,154,110,0.15)] text-[#5B9A6E]' :
                        song.score >= 60 ? 'bg-[rgba(196,149,107,0.15)] text-[#C4956B]' :
                        'bg-[rgba(196,112,104,0.15)] text-[#C47068]'
                      }`}>
                        {song.score}/100
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <Link
                        to={`/song/${song.id}`}
                        className="text-[#5B8A72] hover:underline font-medium"
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
