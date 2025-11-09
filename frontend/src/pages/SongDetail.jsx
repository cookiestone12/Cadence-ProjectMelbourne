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

  const formatNumber = (num) => {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'
    if (num >= 1000) return (num / 1000).toFixed(0) + 'K'
    return num?.toString() || '0'
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
  const scoreBreakdown = song.score_breakdown || {}
  const writerSplits = song.writer_splits || []

  return (
    <div className="container mx-auto px-4 py-8">
      <Link to="/catalog" className="text-mime-purple hover:underline mb-4 inline-block">
        &larr; Back to Catalog
      </Link>

      <div className="bg-white rounded-lg shadow-lg p-8 mb-6">
        <h1 className="text-4xl font-bold mb-2">{song.title}</h1>
        <p className="text-xl text-gray-600 mb-6">by {song.artist_name}</p>

        <div className="grid md:grid-cols-4 gap-6 mb-6">
          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-1">Estimated Revenue</h3>
            <p className="text-2xl font-bold text-mime-purple">${formatNumber(song.estimated_revenue)}</p>
          </div>
          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-1">Overall Score</h3>
            <p className="text-2xl font-bold">{song.score}/100</p>
          </div>
          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-1">Publishing %</h3>
            <p className="text-2xl font-semibold">{song.publishing_percentage}%</p>
          </div>
          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-1">Master %</h3>
            <p className="text-2xl font-semibold">{song.master_percentage}%</p>
          </div>
        </div>

        <div className="border-t pt-4">
          <h3 className="font-semibold mb-3">Valuation Range</h3>
          <div className="grid md:grid-cols-3 gap-4">
            <div className="bg-gray-50 p-4 rounded">
              <p className="text-xs text-gray-500 mb-1">Conservative (Low)</p>
              <p className="text-xl font-bold text-gray-700">${formatNumber(song.valuation_low)}</p>
            </div>
            <div className="bg-green-50 p-4 rounded border-2 border-green-500">
              <p className="text-xs text-gray-500 mb-1">Base Valuation</p>
              <p className="text-2xl font-bold text-green-600">${formatNumber(song.valuation_base)}</p>
            </div>
            <div className="bg-gray-50 p-4 rounded">
              <p className="text-xs text-gray-500 mb-1">Optimistic (High)</p>
              <p className="text-xl font-bold text-gray-700">${formatNumber(song.valuation_high)}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6 mb-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold mb-4">Score Breakdown</h2>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between mb-1">
                <span className="text-sm font-medium">Catalog Value</span>
                <span className="text-sm font-semibold">{scoreBreakdown.catalog_value || 0}/25</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-mime-purple h-2 rounded-full"
                  style={{ width: `${((scoreBreakdown.catalog_value || 0) / 25) * 100}%` }}
                ></div>
              </div>
            </div>
            <div>
              <div className="flex justify-between mb-1">
                <span className="text-sm font-medium">Growth Momentum</span>
                <span className="text-sm font-semibold">{scoreBreakdown.growth_momentum || 0}/25</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-green-500 h-2 rounded-full"
                  style={{ width: `${((scoreBreakdown.growth_momentum || 0) / 25) * 100}%` }}
                ></div>
              </div>
            </div>
            <div>
              <div className="flex justify-between mb-1">
                <span className="text-sm font-medium">Metadata Health</span>
                <span className="text-sm font-semibold">{scoreBreakdown.metadata_health || 0}/25</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-500 h-2 rounded-full"
                  style={{ width: `${((scoreBreakdown.metadata_health || 0) / 25) * 100}%` }}
                ></div>
              </div>
            </div>
            <div>
              <div className="flex justify-between mb-1">
                <span className="text-sm font-medium">Exploitation Potential</span>
                <span className="text-sm font-semibold">{scoreBreakdown.exploitation_potential || 0}/25</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-yellow-500 h-2 rounded-full"
                  style={{ width: `${((scoreBreakdown.exploitation_potential || 0) / 25) * 100}%` }}
                ></div>
              </div>
            </div>
          </div>
        </div>

        {writerSplits && writerSplits.length > 0 && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold mb-4">Writer Splits</h2>
            <div className="space-y-3">
              {writerSplits.map((writer, index) => (
                <div key={index} className="flex justify-between items-center border-b pb-2">
                  <span className="font-medium">{writer.name}</span>
                  <span className="text-mime-purple font-semibold">{writer.share}%</span>
                </div>
              ))}
            </div>
            {song.isrc && (
              <div className="mt-4 pt-4 border-t">
                <p className="text-sm text-gray-500">ISRC: {song.isrc}</p>
                {song.iswc && <p className="text-sm text-gray-500">ISWC: {song.iswc}</p>}
              </div>
            )}
          </div>
        )}
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold mb-4">Track Performance</h2>
          <div className="space-y-4">
            <div>
              <p className="text-sm text-gray-500">Total Spotify Streams</p>
              <p className="text-2xl font-semibold">{formatNumber(analytics.spotify_streams || 0)}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Monthly Listeners</p>
              <p className="text-2xl font-semibold">{formatNumber(analytics.spotify_monthly_listeners || 0)}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Chartmetric Score</p>
              <p className="text-2xl font-semibold">{analytics.chartmetric_score || 0}</p>
            </div>
            {analytics.trend_data?.growth_3_month !== undefined && (
              <div>
                <p className="text-sm text-gray-500">3-Month Growth</p>
                <p className={`text-2xl font-semibold ${analytics.trend_data.growth_3_month > 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {analytics.trend_data.growth_3_month > 0 ? '+' : ''}{analytics.trend_data.growth_3_month}%
                </p>
              </div>
            )}
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
              {analytics.top_playlists?.slice(0, 5).map((playlist, index) => (
                <div key={index} className="border-l-4 border-mime-purple pl-3 py-2 bg-gray-50 rounded">
                  <p className="font-semibold text-sm">{playlist.name}</p>
                  <div className="flex justify-between text-xs text-gray-600 mt-1">
                    <span>{formatNumber(playlist.followers)} followers</span>
                    <span>Position #{playlist.position}</span>
                  </div>
                </div>
              )) || <p className="text-gray-500 text-sm">No playlist data available</p>}
            </div>
          </div>
        </div>
      </div>

      {analytics.regional_data && Object.keys(analytics.regional_data).length > 0 && (
        <div className="bg-white rounded-lg shadow p-6 mt-6">
          <h2 className="text-xl font-bold mb-4">Regional Performance</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(analytics.regional_data).slice(0, 8).map(([region, data]) => (
              <div key={region} className="text-center p-3 bg-gray-50 rounded">
                <p className="font-semibold text-lg">{region}</p>
                <p className="text-sm text-gray-600">{formatNumber(data.streams)} streams</p>
                {data.percentage && (
                  <p className="text-xs text-gray-500">{data.percentage}%</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {song.spotify_link && (
        <div className="mt-6 text-center">
          <a
            href={song.spotify_link}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block bg-mime-purple text-white px-6 py-3 rounded-lg hover:bg-opacity-90"
          >
            Open in Spotify →
          </a>
        </div>
      )}
    </div>
  )
}
