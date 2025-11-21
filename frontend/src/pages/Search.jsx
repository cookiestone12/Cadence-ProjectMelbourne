import React, { useState } from 'react'
import axios from 'axios'

export default function Search() {
  const [searchQuery, setSearchQuery] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!searchQuery.trim()) return

    setLoading(true)
    setSearched(true)
    
    try {
      const token = localStorage.getItem('token')
      const response = await axios.get('/api/catalog/search', {
        params: { q: searchQuery },
        headers: { 'Authorization': `Bearer ${token}` }
      })
      setResults(response.data.results || [])
    } catch (error) {
      console.error('Error searching:', error)
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  const formatNumber = (num) => {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K'
    return num.toString()
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">Search Songs & Artists</h1>
        
        <form onSubmit={handleSearch} className="mb-8">
          <div className="flex gap-2">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by song title or artist name..."
              className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-ampersound-red focus:border-transparent"
            />
            <button
              type="submit"
              disabled={loading}
              className="bg-ampersound-red text-white px-8 py-3 rounded-lg hover:bg-opacity-90 disabled:bg-gray-400"
            >
              {loading ? 'Searching...' : 'Search'}
            </button>
          </div>
        </form>

        {loading && (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-ampersound-red"></div>
            <p className="mt-4">Searching...</p>
          </div>
        )}

        {!loading && searched && results.length === 0 && (
          <div className="text-center py-12 bg-white rounded-lg shadow">
            <p className="text-gray-600">No results found for "{searchQuery}"</p>
          </div>
        )}

        {!loading && results.length > 0 && (
          <div className="space-y-6">
            <p className="text-gray-600">Found {results.length} result(s)</p>
            
            {results.map((result, index) => (
              <div key={index} className="bg-white rounded-lg shadow-lg p-6">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h2 className="text-2xl font-bold">{result.title}</h2>
                    <p className="text-lg text-gray-600">by {result.artist_name}</p>
                  </div>
                  <div className="text-right">
                    {result.in_catalog ? (
                      <span className="inline-block bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm font-semibold">
                        In Catalog: {result.catalog_name}
                      </span>
                    ) : (
                      <span className="inline-block bg-gray-100 text-gray-800 px-3 py-1 rounded-full text-sm font-semibold">
                        External Data Only
                      </span>
                    )}
                  </div>
                </div>

                <div className="border-t pt-4 mb-4">
                  <h3 className="font-semibold text-gray-700 mb-3">Valuation</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <p className="text-xs text-gray-500 mb-1">Estimated Revenue</p>
                      <p className="text-xl font-bold text-ampersound-red">
                        ${formatNumber(result.valuation.estimated_revenue || result.valuation.valuation_base * 0.05)}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500 mb-1">Low</p>
                      <p className="text-lg font-semibold text-gray-700">
                        ${formatNumber(result.valuation.low || result.valuation.valuation_low)}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500 mb-1">Base</p>
                      <p className="text-lg font-semibold text-gray-700">
                        ${formatNumber(result.valuation.base || result.valuation.valuation_base)}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500 mb-1">High</p>
                      <p className="text-lg font-semibold text-gray-700">
                        ${formatNumber(result.valuation.high || result.valuation.valuation_high)}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="border-t pt-4 mb-4">
                  <h3 className="font-semibold text-gray-700 mb-3">Track Metrics</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <p className="text-xs text-gray-500 mb-1">Total Streams</p>
                      <p className="text-lg font-semibold">{formatNumber(result.metrics?.total_streams || 0)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500 mb-1">Playlists</p>
                      <p className="text-lg font-semibold">{result.metrics?.playlist_count || 0}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500 mb-1">3-Month Growth</p>
                      <p className={`text-lg font-semibold ${(result.metrics?.growth_3_month || 0) > 0 ? 'text-green-600' : 'text-gray-700'}`}>
                        {(result.metrics?.growth_3_month || 0) > 0 ? '+' : ''}{(result.metrics?.growth_3_month || 0).toFixed(1)}%
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500 mb-1">Score</p>
                      <p className="text-lg font-semibold text-ampersound-red">{result.score?.toFixed(1) || 0}/100</p>
                    </div>
                  </div>
                  
                  {result.metrics?.top_playlist && (
                    <div className="mt-3 p-3 bg-gray-50 rounded">
                      <p className="text-xs text-gray-500">Top Playlist</p>
                      <p className="font-semibold">{result.metrics.top_playlist}</p>
                      <p className="text-sm text-gray-600">{formatNumber(result.metrics.top_playlist_followers || 0)} followers</p>
                    </div>
                  )}
                </div>

                {result.metrics?.top_territories && result.metrics.top_territories.length > 0 && (
                  <div className="border-t pt-4 mb-4">
                    <h3 className="font-semibold text-gray-700 mb-3">Top Territories</h3>
                    <div className="grid grid-cols-3 gap-3">
                      {result.metrics.top_territories.slice(0, 3).map((territory, idx) => (
                        <div key={idx} className="text-center p-2 bg-gray-50 rounded">
                          <p className="font-semibold">{territory.country}</p>
                          <p className="text-sm text-gray-600">{formatNumber(territory.streams)} streams</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {result.artist_metrics && (
                  <div className="border-t pt-4">
                    <h3 className="font-semibold text-gray-700 mb-3">Artist Metrics</h3>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                      <div>
                        <p className="text-xs text-gray-500 mb-1">Monthly Listeners</p>
                        <p className="text-lg font-semibold">{formatNumber(result.artist_metrics.monthly_listeners || 0)}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-500 mb-1">Followers</p>
                        <p className="text-lg font-semibold">{formatNumber(result.artist_metrics.followers || 0)}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-500 mb-1">3-Month Growth</p>
                        <p className={`text-lg font-semibold ${(result.artist_metrics.follower_growth_3_month || 0) > 0 ? 'text-green-600' : 'text-gray-700'}`}>
                          {(result.artist_metrics.follower_growth_3_month || 0) > 0 ? '+' : ''}{(result.artist_metrics.follower_growth_3_month || 0).toFixed(1)}%
                        </p>
                      </div>
                    </div>
                    {result.artist_metrics.genre_tags && result.artist_metrics.genre_tags.length > 0 && (
                      <div className="mt-3">
                        <p className="text-xs text-gray-500 mb-2">Genres</p>
                        <div className="flex flex-wrap gap-2">
                          {result.artist_metrics.genre_tags.map((tag, idx) => (
                            <span key={idx} className="px-3 py-1 bg-ampersound-red bg-opacity-10 text-ampersound-red rounded-full text-sm">
                              {tag}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {result.in_catalog && result.spotify_link && (
                  <div className="mt-4 pt-4 border-t">
                    <a
                      href={result.spotify_link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-ampersound-red hover:underline"
                    >
                      View on Spotify →
                    </a>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
