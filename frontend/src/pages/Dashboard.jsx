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
      <div className="bg-void-black min-h-screen">
        <div className="container mx-auto px-4 py-8 text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-signal-red"></div>
          <p className="mt-4 text-white">Loading catalog...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-void-black min-h-screen">
      <div className="container mx-auto px-4 py-8">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold font-heading text-white uppercase tracking-wide">Catalog Dashboard</h1>
          <Link
            to="/upload"
            className="bg-signal-red text-white px-6 py-2 rounded hover:bg-opacity-90 shadow-red-glow"
          >
            Upload Songs
          </Link>
        </div>

        {songs.length === 0 ? (
          <div className="text-center py-12 bg-surface-black border border-border-grey rounded-lg shadow">
            <p className="text-tech-grey mb-4">No songs in your catalog yet</p>
            <Link to="/upload" className="text-signal-red hover:underline">
              Upload your first Schedule A
            </Link>
          </div>
        ) : (
          <div className="bg-surface-black border border-border-grey rounded-lg shadow overflow-hidden">
            <table className="min-w-full divide-y divide-border-grey">
              <thead className="bg-black bg-opacity-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-tech-grey uppercase tracking-wider">Title</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-tech-grey uppercase tracking-wider">Artist</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-tech-grey uppercase tracking-wider">Publishing %</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-tech-grey uppercase tracking-wider">Valuation</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-tech-grey uppercase tracking-wider">Score</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-tech-grey uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-surface-black divide-y divide-border-grey">
                {songs.map((song) => (
                  <tr key={song.id} className="hover:bg-black hover:bg-opacity-30">
                    <td className="px-6 py-4 whitespace-nowrap font-medium text-white">{song.title}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-tech-grey">{song.artist_name}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-tech-grey">{song.publishing_percentage}%</td>
                    <td className="px-6 py-4 whitespace-nowrap text-green-400 font-semibold">
                      ${song.valuation.toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 rounded text-sm border ${
                        song.score >= 80 ? 'bg-black bg-opacity-50 border-green-500 text-green-400' :
                        song.score >= 60 ? 'bg-black bg-opacity-50 border-yellow-500 text-yellow-400' :
                        'bg-black bg-opacity-50 border-red-500 text-red-400'
                      }`}>
                        {song.score}/100
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <Link
                        to={`/song/${song.id}`}
                        className="text-signal-red hover:underline"
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
