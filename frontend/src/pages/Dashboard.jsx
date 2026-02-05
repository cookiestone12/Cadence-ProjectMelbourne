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
      <div className="min-h-screen bg-am-bg flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-10 w-10 border-[3px] border-am-accent border-t-transparent"></div>
          <p className="mt-4 text-am-text-secondary text-[15px]">Loading catalog...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-am-bg p-6 lg:p-8">
      <div className="max-w-7xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="am-text-large-title">Catalog Dashboard</h1>
            <p className="am-text-subhead text-am-text-secondary mt-1">Manage and track your music catalog</p>
          </div>
          <Link
            to="/upload"
            className="am-btn am-btn-primary"
          >
            Upload Songs
          </Link>
        </div>

        {songs.length === 0 ? (
          <div className="am-card p-12 text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-am-subtle flex items-center justify-center">
              <svg className="w-8 h-8 text-am-text-tertiary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
              </svg>
            </div>
            <p className="text-am-text-secondary mb-4 text-[17px]">No songs in your catalog yet</p>
            <Link to="/upload" className="text-am-accent hover:text-am-accent-hover font-medium transition-colors">
              Upload your first Schedule A
            </Link>
          </div>
        ) : (
          <div className="am-card p-0 overflow-hidden">
            <table className="min-w-full">
              <thead>
                <tr className="border-b border-am-separator bg-am-subtle/50">
                  <th className="px-6 py-3.5 text-left text-[12px] font-semibold text-am-text-secondary uppercase tracking-wider">Title</th>
                  <th className="px-6 py-3.5 text-left text-[12px] font-semibold text-am-text-secondary uppercase tracking-wider">Artist</th>
                  <th className="px-6 py-3.5 text-left text-[12px] font-semibold text-am-text-secondary uppercase tracking-wider">Publishing %</th>
                  <th className="px-6 py-3.5 text-left text-[12px] font-semibold text-am-text-secondary uppercase tracking-wider">Valuation</th>
                  <th className="px-6 py-3.5 text-left text-[12px] font-semibold text-am-text-secondary uppercase tracking-wider">Score</th>
                  <th className="px-6 py-3.5 text-left text-[12px] font-semibold text-am-text-secondary uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-am-separator">
                {songs.map((song) => (
                  <tr 
                    key={song.id} 
                    className="hover:bg-am-subtle/50 transition-colors duration-150"
                  >
                    <td className="px-6 py-4 whitespace-nowrap font-medium text-am-text text-[15px]">{song.title}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-am-text-secondary text-[15px]">{song.artist_name}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-am-text text-[15px]">{song.publishing_percentage}%</td>
                    <td className="px-6 py-4 whitespace-nowrap text-am-success font-semibold text-[15px]">
                      ${song.valuation?.toLocaleString() || '0'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`am-pill ${
                        song.score >= 80 ? 'am-pill-success' :
                        song.score >= 60 ? 'am-pill-warning' :
                        'am-pill-error'
                      }`}>
                        {song.score}/100
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <Link
                        to={`/song/${song.id}`}
                        className="text-am-accent hover:text-am-accent-hover font-medium text-[14px] transition-colors"
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
