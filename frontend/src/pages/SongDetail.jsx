import React, { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import axios from 'axios'

export default function SongDetail() {
  const { id } = useParams()
  const [song, setSong] = useState(null)
  const [loading, setLoading] = useState(true)
  const [registrations, setRegistrations] = useState([])

  useEffect(() => {
    fetchSongDetail()
    fetchRegistrations()
  }, [id])

  const fetchRegistrations = async () => {
    try {
      const token = localStorage.getItem('token')
      const response = await axios.get(`/api/v1/songs/${id}/registrations`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      setRegistrations(response.data?.registrations || [])
    } catch (error) {
      console.error('Error fetching registrations:', error)
    }
  }

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
      <div className="bg-void-black min-h-screen">
        <div className="container mx-auto px-4 py-8 text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-signal-red"></div>
        </div>
      </div>
    )
  }

  if (!song) {
    return (
      <div className="bg-void-black min-h-screen">
        <div className="container mx-auto px-4 py-8">
          <p className="text-white">Song not found</p>
        </div>
      </div>
    )
  }

  const analytics = song.analytics || {}
  const scoreBreakdown = song.score_breakdown || {}
  const writerSplits = song.writer_splits || []

  return (
    <div className="bg-void-black min-h-screen">
      <div className="container mx-auto px-4 py-8">
        <Link to="/catalog" className="text-signal-red hover:underline mb-4 inline-block">
          &larr; Back to Catalog
        </Link>

        <div className="bg-surface-black border border-border-grey rounded-lg shadow-lg p-8 mb-6">
          <h1 className="text-4xl font-bold font-heading mb-2 text-white uppercase tracking-wide">{song.title}</h1>
          <p className="text-xl text-tech-grey mb-6">by {song.artist_name}</p>

          <div className="grid md:grid-cols-4 gap-6 mb-6">
            <div>
              <h3 className="text-sm font-medium font-heading text-tech-grey mb-1 uppercase tracking-wide">Estimated Revenue</h3>
              <p className="text-2xl font-bold text-signal-red shadow-red-glow">${formatNumber(song.estimated_revenue)}</p>
            </div>
            <div>
              <h3 className="text-sm font-medium font-heading text-tech-grey mb-1 uppercase tracking-wide">Overall Score</h3>
              <p className="text-2xl font-bold text-white">{song.score}/100</p>
            </div>
            <div>
              <h3 className="text-sm font-medium font-heading text-tech-grey mb-1 uppercase tracking-wide">Publishing %</h3>
              <p className="text-2xl font-semibold text-white">{song.publishing_percentage}%</p>
            </div>
            <div>
              <h3 className="text-sm font-medium font-heading text-tech-grey mb-1 uppercase tracking-wide">Master %</h3>
              <p className="text-2xl font-semibold text-white">{song.master_percentage}%</p>
            </div>
          </div>

          <div className="border-t border-border-grey pt-4">
            <h3 className="font-semibold font-heading mb-3 text-white uppercase tracking-wide">Valuation Range</h3>
            <div className="grid md:grid-cols-3 gap-4">
              <div className="bg-black bg-opacity-50 border border-border-grey p-4 rounded">
                <p className="text-xs text-tech-grey mb-1 uppercase tracking-wide">Conservative (Low)</p>
                <p className="text-xl font-bold text-white">${formatNumber(song.valuation_low)}</p>
              </div>
              <div className="bg-black bg-opacity-50 p-4 rounded border-2 border-green-500">
                <p className="text-xs text-tech-grey mb-1 uppercase tracking-wide">Base Valuation</p>
                <p className="text-2xl font-bold text-green-400">${formatNumber(song.valuation_base)}</p>
              </div>
              <div className="bg-black bg-opacity-50 border border-border-grey p-4 rounded">
                <p className="text-xs text-tech-grey mb-1 uppercase tracking-wide">Optimistic (High)</p>
                <p className="text-xl font-bold text-white">${formatNumber(song.valuation_high)}</p>
              </div>
            </div>
          </div>
        </div>

        <div className="grid md:grid-cols-2 gap-6 mb-6">
          <div className="bg-surface-black border border-border-grey rounded-lg shadow p-6">
            <h2 className="text-xl font-bold font-heading mb-4 text-white uppercase tracking-wide">Score Breakdown</h2>
            <div className="space-y-4">
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-sm font-medium text-white">Catalog Value</span>
                  <span className="text-sm font-semibold text-tech-grey">{scoreBreakdown.catalog_value || 0}/25</span>
                </div>
                <div className="w-full bg-border-grey rounded-full h-2">
                  <div
                    className="bg-signal-red h-2 rounded-full shadow-red-glow"
                    style={{ width: `${((scoreBreakdown.catalog_value || 0) / 25) * 100}%` }}
                  ></div>
                </div>
              </div>
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-sm font-medium text-white">Growth Momentum</span>
                  <span className="text-sm font-semibold text-tech-grey">{scoreBreakdown.growth_momentum || 0}/25</span>
                </div>
                <div className="w-full bg-border-grey rounded-full h-2">
                  <div
                    className="bg-green-500 h-2 rounded-full"
                    style={{ width: `${((scoreBreakdown.growth_momentum || 0) / 25) * 100}%` }}
                  ></div>
                </div>
              </div>
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-sm font-medium text-white">Metadata Health</span>
                  <span className="text-sm font-semibold text-tech-grey">{scoreBreakdown.metadata_health || 0}/25</span>
                </div>
                <div className="w-full bg-border-grey rounded-full h-2">
                  <div
                    className="bg-blue-500 h-2 rounded-full"
                    style={{ width: `${((scoreBreakdown.metadata_health || 0) / 25) * 100}%` }}
                  ></div>
                </div>
              </div>
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-sm font-medium text-white">Exploitation Potential</span>
                  <span className="text-sm font-semibold text-tech-grey">{scoreBreakdown.exploitation_potential || 0}/25</span>
                </div>
                <div className="w-full bg-border-grey rounded-full h-2">
                  <div
                    className="bg-yellow-500 h-2 rounded-full"
                    style={{ width: `${((scoreBreakdown.exploitation_potential || 0) / 25) * 100}%` }}
                  ></div>
                </div>
              </div>
            </div>
          </div>

          {writerSplits && writerSplits.length > 0 && (
            <div className="bg-surface-black border border-border-grey rounded-lg shadow p-6">
              <h2 className="text-xl font-bold font-heading mb-4 text-white uppercase tracking-wide">Writer Splits</h2>
              <div className="space-y-3">
                {writerSplits.map((writer, index) => (
                  <div key={index} className="flex justify-between items-center border-b border-border-grey pb-2">
                    <span className="font-medium text-white">{writer.name}</span>
                    <span className="text-signal-red font-semibold">{writer.share}%</span>
                  </div>
                ))}
              </div>
              {song.isrc && (
                <div className="mt-4 pt-4 border-t border-border-grey">
                  <p className="text-sm text-tech-grey">ISRC: {song.isrc}</p>
                  {song.iswc && <p className="text-sm text-tech-grey">ISWC: {song.iswc}</p>}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          <div className="bg-surface-black border border-border-grey rounded-lg shadow p-6">
            <h2 className="text-xl font-bold font-heading mb-4 text-white uppercase tracking-wide">Track Performance</h2>
            <div className="space-y-4">
              <div>
                <p className="text-sm text-tech-grey">Total Spotify Streams</p>
                <p className="text-2xl font-semibold text-white">{formatNumber(analytics.spotify_streams || 0)}</p>
              </div>
              <div>
                <p className="text-sm text-tech-grey">Monthly Listeners</p>
                <p className="text-2xl font-semibold text-white">{formatNumber(analytics.spotify_monthly_listeners || 0)}</p>
              </div>
              <div>
                <p className="text-sm text-tech-grey">Chartmetric Score</p>
                <p className="text-2xl font-semibold text-white">{analytics.chartmetric_score || 0}</p>
              </div>
              {analytics.trend_data?.growth_3_month !== undefined && (
                <div>
                  <p className="text-sm text-tech-grey">3-Month Growth</p>
                  <p className={`text-2xl font-semibold ${analytics.trend_data.growth_3_month > 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {analytics.trend_data.growth_3_month > 0 ? '+' : ''}{analytics.trend_data.growth_3_month}%
                  </p>
                </div>
              )}
            </div>
          </div>

          <div className="bg-surface-black border border-border-grey rounded-lg shadow p-6">
            <h2 className="text-xl font-bold font-heading mb-4 text-white uppercase tracking-wide">Playlist Performance</h2>
            <div className="mb-4">
              <p className="text-sm text-tech-grey">Total Playlists</p>
              <p className="text-2xl font-semibold text-white">{analytics.playlist_count || 0}</p>
            </div>
            <div>
              <p className="text-sm font-medium mb-2 text-white">Top Playlists</p>
              <div className="space-y-2">
                {analytics.top_playlists?.slice(0, 5).map((playlist, index) => (
                  <div key={index} className="border-l-4 border-signal-red pl-3 py-2 bg-black bg-opacity-50 border border-border-grey rounded">
                    <p className="font-semibold text-sm text-white">{playlist.name}</p>
                    <div className="flex justify-between text-xs text-tech-grey mt-1">
                      <span>{formatNumber(playlist.followers)} followers</span>
                      <span>Position #{playlist.position}</span>
                    </div>
                  </div>
                )) || <p className="text-tech-grey text-sm">No playlist data available</p>}
              </div>
            </div>
          </div>
        </div>

        {analytics.regional_data && Object.keys(analytics.regional_data).length > 0 && (
          <div className="bg-surface-black border border-border-grey rounded-lg shadow p-6 mt-6">
            <h2 className="text-xl font-bold font-heading mb-4 text-white uppercase tracking-wide">Regional Performance</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {Object.entries(analytics.regional_data).slice(0, 8).map(([region, data]) => (
                <div key={region} className="text-center p-3 bg-black bg-opacity-50 border border-border-grey rounded">
                  <p className="font-semibold text-lg text-white">{region}</p>
                  <p className="text-sm text-tech-grey">{formatNumber(data.streams)} streams</p>
                  {data.percentage && (
                    <p className="text-xs text-tech-grey">{data.percentage}%</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="bg-surface-black border border-border-grey rounded-lg shadow p-6 mt-6">
          <h2 className="text-xl font-bold font-heading mb-4 text-white uppercase tracking-wide">Registrations</h2>
          {registrations.length === 0 ? (
            <p className="text-tech-grey text-sm">No registrations on file.</p>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {registrations.map((reg) => {
                const ok = reg.registration_status === 'REGISTERED'
                return (
                  <div
                    key={reg.registry_type}
                    className={`p-3 rounded border ${ok ? 'border-green-500 bg-green-500 bg-opacity-10' : 'border-border-grey bg-black bg-opacity-50'}`}
                  >
                    <div className="flex justify-between items-center mb-1">
                      <span className="font-semibold text-white text-sm">{reg.registry_type}</span>
                      <span className={`text-xs ${ok ? 'text-green-400' : 'text-tech-grey'}`}>
                        {ok ? '✓' : '—'}
                      </span>
                    </div>
                    <p className="text-xs text-tech-grey capitalize">{(reg.registration_status || 'not_started').toLowerCase().replace(/_/g, ' ')}</p>
                    {reg.registration_id && (
                      <p className="text-xs text-tech-grey mt-1 truncate" title={reg.registration_id}>{reg.registration_id}</p>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {song.spotify_link && (
          <div className="mt-6 text-center">
            <a
              href={song.spotify_link}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-block bg-signal-red text-white px-6 py-3 rounded-lg hover:bg-opacity-90 shadow-red-glow"
            >
              Open in Spotify →
            </a>
          </div>
        )}
      </div>
    </div>
  )
}
