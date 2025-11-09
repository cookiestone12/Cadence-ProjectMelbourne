import React, { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import axios from 'axios'

export default function SongDetail() {
  const { id } = useParams()
  const [song, setSong] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchSongDetail()
  }, [id])

  const fetchSongDetail = async () => {
    try {
      const token = localStorage.getItem('token')
      const response = await axios.get(`/api/catalog/songs/${id}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      setSong(response.data)
    } catch (error) {
      console.error('Error fetching song details:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8 text-center">
        <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-mime-purple"></div>
      </div>
    )
  }

  if (!song) {
    return (
      <div className="container mx-auto px-4 py-8">
        <p>Song not found</p>
      </div>
    )
  }

  const analytics = song.analytics || {}

  return (
    <div className="container mx-auto px-4 py-8">
      <Link to="/dashboard" className="text-mime-purple hover:underline mb-4 inline-block">
        &larr; Back to Dashboard
      </Link>

      <div className="bg-white rounded-lg shadow-lg p-8 mb-6">
        <h1 className="text-4xl font-bold mb-2">{song.title}</h1>
        <p className="text-xl text-gray-600 mb-6">by {song.artist_name}</p>

        <div className="grid md:grid-cols-2 gap-6">
          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-1">Valuation</h3>
            <p className="text-3xl font-bold text-green-600">${song.valuation.toLocaleString()}</p>
          </div>
          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-1">Score</h3>
            <p className="text-3xl font-bold">{song.score}/100</p>
          </div>
          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-1">Publishing %</h3>
            <p className="text-2xl">{song.publishing_percentage}%</p>
          </div>
          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-1">Master %</h3>
            <p className="text-2xl">{song.master_percentage}%</p>
          </div>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold mb-4">Streaming Analytics</h2>
          <div className="space-y-4">
            <div>
              <p className="text-sm text-gray-500">Total Spotify Streams</p>
              <p className="text-2xl font-semibold">{analytics.spotify_streams?.toLocaleString() || 0}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Monthly Listeners</p>
              <p className="text-2xl font-semibold">{analytics.spotify_monthly_listeners?.toLocaleString() || 0}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Chartmetric Score</p>
              <p className="text-2xl font-semibold">{analytics.chartmetric_score || 0}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold mb-4">Playlist Performance</h2>
          <div className="mb-4">
            <p className="text-sm text-gray-500">Total Playlists</p>
            <p className="text-2xl font-semibold">{analytics.playlist_count || 0}</p>
          </div>
          <div>
            <p className="text-sm font-medium mb-2">Top Playlists</p>
            <div className="space-y-2">
              {analytics.top_playlists?.slice(0, 3).map((playlist, index) => (
                <div key={index} className="border-l-4 border-mime-purple pl-3 py-1">
                  <p className="font-medium">{playlist.name}</p>
                  <p className="text-sm text-gray-500">
                    {playlist.followers?.toLocaleString()} followers · Position #{playlist.position}
                  </p>
                </div>
              )) || <p className="text-gray-400">No playlist data available</p>}
            </div>
          </div>
        </div>

        {analytics.regional_data && Object.keys(analytics.regional_data).length > 0 && (
          <div className="bg-white rounded-lg shadow p-6 md:col-span-2">
            <h2 className="text-xl font-bold mb-4">Regional Performance</h2>
            <div className="grid md:grid-cols-3 gap-4">
              {Object.entries(analytics.regional_data).map(([region, data]) => (
                <div key={region} className="border rounded p-4">
                  <h3 className="font-semibold mb-2">{region}</h3>
                  <p className="text-sm text-gray-600">Streams: {data.streams?.toLocaleString()}</p>
                  <p className="text-sm text-gray-600">Radio Spins: {data.radio_spins?.toLocaleString()}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
