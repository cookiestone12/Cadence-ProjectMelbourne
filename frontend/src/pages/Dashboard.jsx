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
      <div className="container mx-auto px-4 py-8 text-center">
        <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-mime-purple"></div>
        <p className="mt-4">Loading catalog...</p>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">Catalog Dashboard</h1>
        <Link
          to="/upload"
          className="bg-mime-purple text-white px-6 py-2 rounded hover:bg-opacity-90"
        >
          Upload Songs
        </Link>
      </div>

      {songs.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg shadow">
          <p className="text-gray-600 mb-4">No songs in your catalog yet</p>
          <Link to="/upload" className="text-mime-purple hover:underline">
            Upload your first Schedule A
          </Link>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Title</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Artist</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Publishing %</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Valuation</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Score</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {songs.map((song) => (
                <tr key={song.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap font-medium">{song.title}</td>
                  <td className="px-6 py-4 whitespace-nowrap">{song.artist_name}</td>
                  <td className="px-6 py-4 whitespace-nowrap">{song.publishing_percentage}%</td>
                  <td className="px-6 py-4 whitespace-nowrap text-green-600 font-semibold">
                    ${song.valuation.toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 py-1 rounded text-sm ${
                      song.score >= 80 ? 'bg-green-100 text-green-800' :
                      song.score >= 60 ? 'bg-yellow-100 text-yellow-800' :
                      'bg-red-100 text-red-800'
                    }`}>
                      {song.score}/100
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <Link
                      to={`/song/${song.id}`}
                      className="text-mime-purple hover:underline"
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
  )
}
