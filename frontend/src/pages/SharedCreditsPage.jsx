import React, { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import axios from 'axios'
import {
  MusicalNoteIcon,
  LockClosedIcon,
  UserCircleIcon,
  StarIcon,
} from '@heroicons/react/24/outline'

const ROLE_COLORS = {
  PRODUCER: 'bg-purple-100 text-purple-700 border-purple-200',
  SONGWRITER: 'bg-blue-100 text-blue-700 border-blue-200',
  ARTIST: 'bg-green-100 text-green-700 border-green-200',
  FEATURED_ARTIST: 'bg-pink-100 text-pink-700 border-pink-200',
  MIX_ENGINEER: 'bg-orange-100 text-orange-700 border-orange-200',
  OTHER: 'bg-gray-100 text-gray-700 border-gray-200',
}

const ROLE_LABELS = {
  PRODUCER: 'Producer',
  SONGWRITER: 'Songwriter',
  ARTIST: 'Artist',
  FEATURED_ARTIST: 'Featured Artist',
  MIX_ENGINEER: 'Mix Engineer',
  OTHER: 'Other',
}

const PLATFORM_ICONS = {
  SPOTIFY: { label: 'Spotify', color: 'text-green-500' },
  APPLE_MUSIC: { label: 'Apple Music', color: 'text-pink-500' },
  YOUTUBE_MUSIC: { label: 'YouTube Music', color: 'text-red-500' },
  AMAZON_MUSIC: { label: 'Amazon Music', color: 'text-blue-500' },
  TIDAL: { label: 'Tidal', color: 'text-cyan-600' },
  DEEZER: { label: 'Deezer', color: 'text-purple-500' },
}

function formatNumber(num) {
  if (!num) return '0'
  if (num >= 1_000_000_000) return (num / 1_000_000_000).toFixed(1) + 'B'
  if (num >= 1_000_000) return (num / 1_000_000).toFixed(1) + 'M'
  if (num >= 1_000) return (num / 1_000).toFixed(1) + 'K'
  return num.toLocaleString()
}

export default function SharedCreditsPage() {
  const { token } = useParams()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [needsPasscode, setNeedsPasscode] = useState(false)
  const [passcode, setPasscode] = useState('')
  const [passcodeError, setPasscodeError] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const fetchCredits = async (pc) => {
    try {
      setLoading(true)
      setError(null)
      const url = pc
        ? `/api/public/credits/${token}?passcode=${encodeURIComponent(pc)}`
        : `/api/public/credits/${token}`
      const res = await axios.get(url)

      if (res.data.requires_passcode) {
        setNeedsPasscode(true)
        setLoading(false)
        return
      }

      setData(res.data)
      setNeedsPasscode(false)
    } catch (err) {
      if (err.response?.status === 403) {
        if (needsPasscode) {
          setPasscodeError(true)
        } else {
          setError('Access denied.')
        }
      } else if (err.response?.status === 404) {
        setError('Credits profile not found.')
      } else {
        setError('Failed to load credits.')
      }
    } finally {
      setLoading(false)
      setSubmitting(false)
    }
  }

  useEffect(() => {
    fetchCredits()
  }, [token])

  const handlePasscodeSubmit = (e) => {
    e.preventDefault()
    setPasscodeError(false)
    setSubmitting(true)
    fetchCredits(passcode)
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#F8F9F7] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-[#5B8A72] border-t-transparent rounded-full animate-spin" />
          <p className="text-[#7A8580] text-sm">Loading credits...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#F8F9F7] flex items-center justify-center">
        <div className="bg-white rounded-2xl border border-[rgba(59,77,67,0.12)] p-12 text-center max-w-md shadow-sm">
          <MusicalNoteIcon className="w-12 h-12 text-[#B0BDB4] mx-auto mb-3" />
          <h2 className="text-lg font-semibold text-[#3D4A44] mb-2">Unavailable</h2>
          <p className="text-sm text-[#7A8580]">{error}</p>
        </div>
      </div>
    )
  }

  if (needsPasscode) {
    return (
      <div className="min-h-screen bg-[#F8F9F7] flex items-center justify-center px-4">
        <div className="bg-white rounded-2xl border border-[rgba(59,77,67,0.12)] p-8 sm:p-10 max-w-sm w-full shadow-sm text-center">
          <LockClosedIcon className="w-10 h-10 text-[#5B8A72] mx-auto mb-4" />
          <h2 className="text-xl font-bold text-[#3D4A44] mb-2">Protected Profile</h2>
          <p className="text-sm text-[#7A8580] mb-6">Enter the passcode to view this credits profile.</p>
          <form onSubmit={handlePasscodeSubmit}>
            <input
              type="password"
              value={passcode}
              onChange={(e) => { setPasscode(e.target.value); setPasscodeError(false) }}
              placeholder="Enter passcode"
              className={`w-full px-4 py-3 rounded-xl border text-center text-lg tracking-widest font-mono ${
                passcodeError ? 'border-red-400 bg-red-50' : 'border-[rgba(59,77,67,0.2)] bg-[#F8F9F7]'
              } focus:outline-none focus:ring-2 focus:ring-[#5B8A72]/30 focus:border-[#5B8A72]`}
              autoFocus
            />
            {passcodeError && (
              <p className="text-red-500 text-xs mt-2">Invalid passcode. Please try again.</p>
            )}
            <button
              type="submit"
              disabled={!passcode || submitting}
              className="w-full mt-4 py-3 bg-[#5B8A72] text-white rounded-xl font-medium hover:bg-[#4A7A62] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {submitting ? 'Verifying...' : 'View Credits'}
            </button>
          </form>
        </div>
      </div>
    )
  }

  if (!data) return null

  const roleBreakdown = data.role_breakdown || {}
  const topSongs = data.top_songs || []

  return (
    <div className="min-h-screen bg-[#F8F9F7]">
      <div className="max-w-4xl mx-auto p-4 sm:p-8">
        <div className="bg-gradient-to-br from-[#5B8A72] via-[#4A7A62] to-[#3D6B54] rounded-2xl p-6 sm:p-8 mb-6 text-white shadow-lg">
          <div className="flex items-start gap-4 sm:gap-5">
            {data.avatar_url ? (
              <img
                src={data.avatar_url}
                alt={data.creator_name}
                className="w-16 h-16 sm:w-20 sm:h-20 rounded-full object-cover border-2 border-white/30 flex-shrink-0"
              />
            ) : (
              <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-full bg-white/20 flex items-center justify-center flex-shrink-0">
                <UserCircleIcon className="w-10 h-10 sm:w-12 sm:h-12 text-white/60" />
              </div>
            )}
            <div className="flex-1 min-w-0">
              <h1 className="text-2xl sm:text-3xl font-bold truncate">{data.creator_name}</h1>
              {data.organization_name && (
                <p className="text-white/70 text-sm sm:text-base mt-1">{data.organization_name}</p>
              )}
              <div className="flex flex-wrap gap-3 sm:gap-5 mt-4">
                <div>
                  <p className="text-white/60 text-xs uppercase tracking-wider">Credits</p>
                  <p className="text-xl sm:text-2xl font-bold">{data.total_credits || 0}</p>
                </div>
                <div>
                  <p className="text-white/60 text-xs uppercase tracking-wider">Est. Streams</p>
                  <p className="text-xl sm:text-2xl font-bold">{formatNumber(data.total_estimated_streams)}</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {Object.keys(roleBreakdown).length > 0 && (
          <div className="mb-6">
            <h2 className="text-sm font-semibold text-[#7A8580] uppercase tracking-wider mb-3">Role Breakdown</h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {Object.entries(roleBreakdown).map(([role, count]) => (
                <div
                  key={role}
                  className={`rounded-xl border px-4 py-3 ${ROLE_COLORS[role] || ROLE_COLORS.OTHER}`}
                >
                  <p className="text-2xl font-bold">{count}</p>
                  <p className="text-xs font-medium opacity-80">{ROLE_LABELS[role] || role}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {data.platforms && Object.keys(data.platforms).length > 0 && (
          <div className="mb-6">
            <h2 className="text-sm font-semibold text-[#7A8580] uppercase tracking-wider mb-3">Platform Breakdown</h2>
            <div className="bg-white rounded-2xl border border-[rgba(59,77,67,0.12)] p-4 sm:p-5">
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {Object.entries(data.platforms).map(([platform, streamData]) => {
                  const info = PLATFORM_ICONS[platform] || { label: platform, color: 'text-gray-500' }
                  const streamCount = typeof streamData === 'object' && streamData !== null ? (streamData.streams || 0) : (streamData || 0)
                  return (
                    <div key={platform} className="flex items-center gap-2">
                      <span className={`text-sm font-medium ${info.color}`}>{info.label}</span>
                      <span className="text-sm text-[#3D4A44] font-semibold">{formatNumber(streamCount)}</span>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        )}

        {data.riaa && (
          <div className="mb-6">
            <h2 className="text-sm font-semibold text-[#7A8580] uppercase tracking-wider mb-3">RIAA Equivalents</h2>
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-white rounded-xl border border-[rgba(59,77,67,0.12)] p-4 text-center">
                <p className="text-2xl font-bold text-[#3D4A44]">{formatNumber(data.riaa.single_units)}</p>
                <p className="text-xs text-[#7A8580] mt-1">Single Units</p>
              </div>
              <div className="bg-white rounded-xl border border-[rgba(59,77,67,0.12)] p-4 text-center">
                <p className="text-2xl font-bold text-[#3D4A44]">{formatNumber(data.riaa.album_units)}</p>
                <p className="text-xs text-[#7A8580] mt-1">Album Units</p>
              </div>
            </div>
          </div>
        )}

        {topSongs.length > 0 && (
          <div className="mb-6">
            <h2 className="text-sm font-semibold text-[#7A8580] uppercase tracking-wider mb-3">Top Songs</h2>
            <div className="bg-white rounded-2xl border border-[rgba(59,77,67,0.12)] overflow-hidden">
              {topSongs.map((song, idx) => (
                <div
                  key={song.song_id || idx}
                  className={`flex items-center gap-3 sm:gap-4 px-4 sm:px-5 py-3 ${
                    idx !== topSongs.length - 1 ? 'border-b border-[rgba(59,77,67,0.08)]' : ''
                  }`}
                >
                  <span className="text-sm font-bold text-[#B0BDB4] w-6 text-right flex-shrink-0">
                    {idx + 1}
                  </span>
                  {song.artwork_url ? (
                    <img
                      src={song.artwork_url}
                      alt={song.title}
                      className="w-10 h-10 rounded-lg object-cover flex-shrink-0"
                    />
                  ) : (
                    <div className="w-10 h-10 rounded-lg bg-[#F0F3EE] flex items-center justify-center flex-shrink-0">
                      <MusicalNoteIcon className="w-5 h-5 text-[#B0BDB4]" />
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-[#3D4A44] truncate">{song.title}</p>
                    <p className="text-xs text-[#7A8580] truncate">{song.artist}</p>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <p className="text-sm font-bold text-[#3D4A44]">{formatNumber(song.total_streams)}</p>
                    <p className="text-[10px] text-[#B0BDB4]">streams</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <p className="text-center text-[10px] text-[#B0BDB4] mt-4 mb-2">
          Stream estimates are approximations and may vary from actual figures.
        </p>

        <div className="text-center mt-6 mb-4 text-xs text-[#B0BDB4]">
          Powered by Cadence &mdash; Catalog Intelligence
        </div>
      </div>
    </div>
  )
}
