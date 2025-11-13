import React, { useEffect, useState } from 'react'
import axios from 'axios'

export default function SongDetailModal({ songId, onClose }) {
  const [song, setSong] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchSongDetails()
  }, [songId])

  const fetchSongDetails = async () => {
    try {
      const token = localStorage.getItem('token')
      const response = await axios.get(`/api/catalog/songs/${songId}`, {
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

  const calculateAge = (releaseDate) => {
    if (!releaseDate) return 'N/A'
    const now = new Date()
    const release = new Date(releaseDate)
    const years = (now - release) / (1000 * 60 * 60 * 24 * 365.25)
    return `${years.toFixed(1)} years`
  }

  const getCollectionWindow = (releaseDate) => {
    if (!releaseDate) return { decay: 100, label: 'Full collectibility' }
    const now = new Date()
    const release = new Date(releaseDate)
    const years = (now - release) / (1000 * 60 * 60 * 24 * 365.25)
    
    if (years <= 3) return { decay: 100, label: '100% collectible (0-3 years)' }
    if (years <= 5) return { decay: 50, label: '50% collectible (3-5 years)' }
    return { decay: 10, label: '10% collectible (5+ years)' }
  }

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-8 max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
          <div className="text-center">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-mime-purple mb-4"></div>
            <p>Loading song details...</p>
          </div>
        </div>
      </div>
    )
  }

  if (!song) {
    return null
  }

  const collectionWindow = getCollectionWindow(song.release_date)

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded-lg p-8 max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex justify-between items-start mb-6">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">{song.title}</h2>
            <p className="text-lg text-gray-600">{song.artist_name}</p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl font-bold"
          >
            ×
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-purple-50 rounded-lg p-4">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Basic Information</h3>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Release Date</span>
                <span className="text-sm font-semibold">{song.release_date || 'N/A'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Song Age</span>
                <span className="text-sm font-semibold">{calculateAge(song.release_date)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">ISRC</span>
                <span className="text-sm font-semibold">{song.isrc || 'N/A'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">ISWC</span>
                <span className="text-sm font-semibold">{song.iswc || 'N/A'}</span>
              </div>
            </div>
          </div>

          <div className="bg-blue-50 rounded-lg p-4">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Ownership</h3>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Publishing %</span>
                <span className="text-sm font-semibold text-mime-purple">{song.publishing_percentage}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Master %</span>
                <span className="text-sm font-semibold text-blue-600">{song.master_percentage}%</span>
              </div>
            </div>
          </div>

          <div className="bg-green-50 rounded-lg p-4">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Streaming Performance</h3>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Total Streams</span>
                <span className="text-sm font-semibold">{formatNumber(song.spotify_streams)}</span>
              </div>
              {song.premium_streams !== undefined && song.premium_streams !== null && (
                <>
                  <div className="flex justify-between pl-4">
                    <span className="text-xs text-gray-500">Premium (70%)</span>
                    <span className="text-sm text-gray-700">{formatNumber(song.premium_streams)}</span>
                  </div>
                  <div className="flex justify-between pl-4">
                    <span className="text-xs text-gray-500">Ad-Supported (30%)</span>
                    <span className="text-sm text-gray-700">{formatNumber(song.ad_supported_streams)}</span>
                  </div>
                </>
              )}
            </div>
          </div>

          <div className="bg-orange-50 rounded-lg p-4">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Black Box Tracking</h3>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Collection Window</span>
                <span className="text-sm font-semibold">{collectionWindow.label}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Collectible Value</span>
                <span className="text-sm font-semibold text-green-600">${formatNumber(song.collectible_publishing_value)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Black Box Loss</span>
                <span className="text-sm font-semibold text-red-600">${formatNumber(song.black_box_loss)}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-6 bg-gray-50 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Revenue Breakdown</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-gray-500 mb-1">Publishing Revenue</p>
              <p className="text-lg font-bold text-mime-purple">${formatNumber(song.publishing_revenue)}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 mb-1">Master Revenue</p>
              <p className="text-lg font-bold text-blue-600">${formatNumber(song.master_revenue)}</p>
            </div>
          </div>
        </div>

        <div className="mt-6 bg-gray-50 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Valuations</h3>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <p className="text-xs text-gray-500 mb-1">Low (8× multiplier)</p>
              <p className="text-lg font-semibold text-gray-700">${formatNumber(song.valuation_low)}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 mb-1">Base (12× multiplier)</p>
              <p className="text-lg font-semibold text-green-600">${formatNumber(song.valuation_base)}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 mb-1">High (18× multiplier)</p>
              <p className="text-lg font-semibold text-gray-700">${formatNumber(song.valuation_high)}</p>
            </div>
          </div>
        </div>

        <div className="mt-6 bg-gray-50 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Score Breakdown</h3>
          <div className="flex justify-between items-center mb-3">
            <span className="text-lg font-bold">Total Score</span>
            <span className={`px-3 py-1 rounded text-lg font-bold ${
              song.score >= 80 ? 'bg-green-100 text-green-800' :
              song.score >= 60 ? 'bg-yellow-100 text-yellow-800' :
              'bg-red-100 text-red-800'
            }`}>
              {song.score}/100
            </span>
          </div>
          {song.score_breakdown && (
            <div className="space-y-3">
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-sm text-gray-600">Catalog Value</span>
                  <span className="text-sm font-semibold">{song.score_breakdown.catalog_value}/25</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-mime-purple h-2 rounded-full"
                    style={{ width: `${(song.score_breakdown.catalog_value / 25) * 100}%` }}
                  ></div>
                </div>
              </div>
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-sm text-gray-600">Growth Momentum</span>
                  <span className="text-sm font-semibold">{song.score_breakdown.growth_momentum}/25</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-green-500 h-2 rounded-full"
                    style={{ width: `${(song.score_breakdown.growth_momentum / 25) * 100}%` }}
                  ></div>
                </div>
              </div>
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-sm text-gray-600">Metadata Health</span>
                  <span className="text-sm font-semibold">{song.score_breakdown.metadata_health}/25</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-500 h-2 rounded-full"
                    style={{ width: `${(song.score_breakdown.metadata_health / 25) * 100}%` }}
                  ></div>
                </div>
              </div>
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-sm text-gray-600">Exploitation Potential</span>
                  <span className="text-sm font-semibold">{song.score_breakdown.exploitation_potential}/25</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-yellow-500 h-2 rounded-full"
                    style={{ width: `${(song.score_breakdown.exploitation_potential / 25) * 100}%` }}
                  ></div>
                </div>
              </div>
            </div>
          )}
        </div>

        {song.territory_streams && Object.keys(song.territory_streams).length > 0 && (
          <div className="mt-6 bg-gray-50 rounded-lg p-4">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Top 3 Territories</h3>
            <div className="space-y-2">
              {Object.entries(song.territory_streams)
                .map(([territory, data]) => {
                  const totalStreams = typeof data === 'number' ? data : 
                    (data.premium || 0) + (data.ad_supported || 0);
                  return [territory, totalStreams];
                })
                .sort(([, a], [, b]) => b - a)
                .slice(0, 3)
                .map(([territory, streams], index) => (
                  <div key={territory} className="flex justify-between items-center">
                    <span className="text-sm font-medium">
                      {index + 1}. {territory}
                    </span>
                    <span className="text-sm font-semibold text-gray-700">{formatNumber(streams)} streams</span>
                  </div>
                ))}
            </div>
          </div>
        )}

        <div className="mt-6 flex justify-end">
          <button
            onClick={onClose}
            className="bg-mime-purple text-white px-6 py-2 rounded-lg hover:bg-opacity-90 transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
