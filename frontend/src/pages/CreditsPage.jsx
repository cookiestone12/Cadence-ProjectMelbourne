import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import {
  MusicalNoteIcon, MagnifyingGlassIcon, ArrowPathIcon,
  ChevronUpDownIcon, UserGroupIcon, ArrowDownTrayIcon, ChevronDownIcon
} from '@heroicons/react/24/outline'
import RosterSocialCard from '../components/RosterSocialCard'
import ViewToggle, { getStoredViewMode, setStoredViewMode } from '../components/ViewToggle'

const ROLE_COLORS = {
  ARTIST: 'bg-green-100 text-green-700',
  FEATURED_ARTIST: 'bg-pink-100 text-pink-700',
  SONGWRITER: 'bg-blue-100 text-blue-700',
  PRODUCER: 'bg-purple-100 text-purple-700',
  MIX_ENGINEER: 'bg-teal-100 text-teal-700',
  OTHER: 'bg-gray-100 text-gray-600',
}

function formatNumber(num) {
  if (!num) return '0'
  if (num >= 1_000_000_000) return (num / 1_000_000_000).toFixed(1) + 'B'
  if (num >= 1_000_000) return (num / 1_000_000).toFixed(1) + 'M'
  if (num >= 1_000) return (num / 1_000).toFixed(1) + 'K'
  return num.toLocaleString()
}

export default function CreditsPage() {
  const navigate = useNavigate()
  const [creators, setCreators] = useState([])
  const [loading, setLoading] = useState(true)
  const [orgId, setOrgId] = useState(null)
  const [orgName, setOrgName] = useState('')
  const [search, setSearch] = useState('')
  const [sortBy, setSortBy] = useState('streams')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [allCreators, setAllCreators] = useState([])
  const [showFormatMenu, setShowFormatMenu] = useState(false)
  const [socialCardFormat, setSocialCardFormat] = useState('story')
  const [showSocialCard, setShowSocialCard] = useState(false)
  const [generatingSocialCard, setGeneratingSocialCard] = useState(false)
  const [viewMode, setViewMode] = useState(() => getStoredViewMode('credits'))

  const handleViewModeChange = (mode) => {
    setViewMode(mode)
    setStoredViewMode('credits', mode)
  }
  const socialCardRef = useRef(null)
  const formatMenuRef = useRef(null)

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), 300)
    return () => clearTimeout(timer)
  }, [search])

  useEffect(() => {
    loadData()
  }, [])

  useEffect(() => {
    if (orgId) fetchCredits()
  }, [orgId, debouncedSearch, sortBy])

  useEffect(() => {
    function handleClickOutside(e) {
      if (formatMenuRef.current && !formatMenuRef.current.contains(e.target)) {
        setShowFormatMenu(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  async function loadData() {
    try {
      const orgRes = await axios.get('/api/organizations/current')
      const currentOrgId = orgRes.data?.id
      const currentOrgName = orgRes.data?.name || ''
      if (!currentOrgId) { setLoading(false); return }
      setOrgId(currentOrgId)
      setOrgName(currentOrgName)
      try {
        const allRes = await axios.get(`/api/streaming-credits/org/${currentOrgId}/overview`, { params: { sort_by: 'streams' } })
        setAllCreators(allRes.data?.creators || [])
      } catch {}
    } catch (error) {
      console.error('Failed to load org:', error)
      setLoading(false)
    }
  }

  async function fetchCredits() {
    setLoading(true)
    try {
      const params = { sort_by: sortBy }
      if (debouncedSearch) params.search = debouncedSearch
      const res = await axios.get(`/api/streaming-credits/org/${orgId}/overview`, { params })
      setCreators(res.data?.creators || [])
    } catch (error) {
      console.error('Failed to load credits:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleDownloadSocialCard = useCallback(async (fmt) => {
    const chosenFormat = fmt || socialCardFormat
    setSocialCardFormat(chosenFormat)
    setGeneratingSocialCard(true)
    setShowSocialCard(true)
    setShowFormatMenu(false)
    try {
      await new Promise(r => setTimeout(r, 500))
      const html2canvas = (await import('html2canvas')).default
      const node = socialCardRef.current
      if (!node) return
      const h = chosenFormat === 'square' ? 1080 : 1350
      const canvas = await html2canvas(node, {
        scale: 1,
        useCORS: true,
        allowTaint: true,
        backgroundColor: null,
        width: 1080,
        height: h,
        logging: false,
      })
      let url
      try {
        const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/png'))
        if (blob) {
          url = URL.createObjectURL(blob)
        } else {
          url = canvas.toDataURL('image/png')
        }
      } catch {
        url = canvas.toDataURL('image/png')
      }
      const a = document.createElement('a')
      a.href = url
      const safeName = (orgName || 'roster').replace(/[^a-zA-Z0-9]/g, '_')
      const suffix = chosenFormat === 'square' ? '_roster_credits_square' : '_roster_credits'
      a.download = `${safeName}${suffix}.png`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      if (url.startsWith('blob:')) URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Social card generation failed:', err)
    } finally {
      setGeneratingSocialCard(false)
      setShowSocialCard(false)
    }
  }, [socialCardFormat, orgName])

  const totalCredits = creators.reduce((sum, c) => sum + (c.total_credits || 0), 0)
  const totalStreams = creators.reduce((sum, c) => sum + (c.total_estimated_streams || 0), 0)
  const activeCreators = creators.filter(c => c.total_credits > 0).length
  const avgStreams = activeCreators > 0 ? Math.round(totalStreams / totalCredits || 0) : 0

  const cardCreators = allCreators.length > 0 ? allCreators : creators
  const cardTotalCredits = cardCreators.reduce((sum, c) => sum + (c.total_credits || 0), 0)
  const cardTotalStreams = cardCreators.reduce((sum, c) => sum + (c.total_estimated_streams || 0), 0)
  const cardActiveCreators = cardCreators.filter(c => c.total_credits > 0).length
  const sortedForCard = [...cardCreators].sort((a, b) => (b.total_estimated_streams || 0) - (a.total_estimated_streams || 0))

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-[#3D4A44]">Credits</h1>
          <p className="text-sm text-[#7A8580] mt-1">Streaming intelligence & creator credits overview</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative" ref={formatMenuRef}>
            <button
              onClick={() => setShowFormatMenu(!showFormatMenu)}
              disabled={generatingSocialCard || (creators.length === 0 && allCreators.length === 0)}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-[#5B8A72] hover:bg-[#4A7A62] rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {generatingSocialCard ? (
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <ArrowDownTrayIcon className="w-4 h-4" />
              )}
              Download for Social
              <ChevronDownIcon className="w-3 h-3" />
            </button>
            {showFormatMenu && (
              <div className="absolute right-0 mt-1 w-44 bg-white rounded-xl shadow-lg border border-[rgba(59,77,67,0.12)] py-1 z-50">
                <button
                  onClick={() => handleDownloadSocialCard('story')}
                  className="w-full text-left px-4 py-2.5 text-sm text-[#3D4A44] hover:bg-[#5B8A72]/10 transition-colors"
                >
                  Story (1080 x 1350)
                </button>
                <button
                  onClick={() => handleDownloadSocialCard('square')}
                  className="w-full text-left px-4 py-2.5 text-sm text-[#3D4A44] hover:bg-[#5B8A72]/10 transition-colors"
                >
                  Square (1080 x 1080)
                </button>
              </div>
            )}
          </div>
          <button
            onClick={() => orgId && fetchCredits()}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-[#5B8A72] bg-[#5B8A72]/10 hover:bg-[#5B8A72]/20 rounded-xl transition-colors"
          >
            <ArrowPathIcon className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-2xl border border-[rgba(59,77,67,0.08)] p-5 shadow-sm">
          <p className="text-xs font-medium text-[#7A8580] uppercase tracking-wide">Total Credits</p>
          <p className="text-2xl font-bold text-[#3D4A44] mt-1">{formatNumber(totalCredits)}</p>
        </div>
        <div className="bg-white rounded-2xl border border-[rgba(59,77,67,0.08)] p-5 shadow-sm">
          <p className="text-xs font-medium text-[#7A8580] uppercase tracking-wide">Est. Streams</p>
          <p className="text-2xl font-bold text-[#3D4A44] mt-1">{formatNumber(totalStreams)}</p>
        </div>
        <div className="bg-white rounded-2xl border border-[rgba(59,77,67,0.08)] p-5 shadow-sm">
          <p className="text-xs font-medium text-[#7A8580] uppercase tracking-wide">Active Creators</p>
          <p className="text-2xl font-bold text-[#3D4A44] mt-1">{activeCreators}</p>
        </div>
        <div className="bg-white rounded-2xl border border-[rgba(59,77,67,0.08)] p-5 shadow-sm">
          <p className="text-xs font-medium text-[#7A8580] uppercase tracking-wide">Avg Streams/Song</p>
          <p className="text-2xl font-bold text-[#3D4A44] mt-1">{formatNumber(avgStreams)}</p>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <div className="relative flex-1">
          <MagnifyingGlassIcon className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#7A8580]" />
          <input
            type="text"
            placeholder="Search creators..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2.5 border border-[rgba(59,77,67,0.12)] rounded-xl bg-white text-sm text-[#3D4A44] placeholder-[#7A8580] focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
          />
        </div>
        <div className="relative">
          <select
            value={sortBy}
            onChange={e => setSortBy(e.target.value)}
            className="appearance-none pl-3 pr-8 py-2.5 border border-[rgba(59,77,67,0.12)] rounded-xl bg-white text-sm text-[#3D4A44] focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent cursor-pointer"
          >
            <option value="streams">Sort by Streams</option>
            <option value="credits">Sort by Credits</option>
            <option value="name">Sort by Name</option>
          </select>
          <ChevronUpDownIcon className="w-4 h-4 absolute right-2.5 top-1/2 -translate-y-1/2 text-[#7A8580] pointer-events-none" />
        </div>
        <ViewToggle viewMode={viewMode} onViewModeChange={handleViewModeChange} />
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="w-8 h-8 border-2 border-[#5B8A72] border-t-transparent rounded-full animate-spin" />
        </div>
      ) : creators.length === 0 ? (
        <div className="bg-white rounded-2xl border border-[rgba(59,77,67,0.08)] p-12 text-center shadow-sm">
          <UserGroupIcon className="w-12 h-12 text-[#7A8580]/40 mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-[#3D4A44] mb-1">No credits data yet</h3>
          <p className="text-sm text-[#7A8580]">Credits will appear here once creators have song credits and streaming data.</p>
        </div>
      ) : viewMode === 'grid' ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {creators.map(creator => (
            <button
              key={creator.creator_id}
              onClick={() => navigate(`/roster/${creator.creator_id}?tab=credits`)}
              className="bg-white rounded-2xl border border-[rgba(59,77,67,0.08)] p-5 shadow-sm hover:shadow-md hover:border-[#5B8A72]/30 transition-all duration-200 text-left group"
            >
              <div className="flex items-start gap-3">
                {creator.hero_image_url ? (
                  <img
                    src={creator.hero_image_url}
                    alt={creator.display_name}
                    className="w-12 h-12 rounded-full object-cover flex-shrink-0"
                  />
                ) : (
                  <div className="w-12 h-12 rounded-full bg-gradient-to-br from-[#5B8A72] to-[#4A7A62] flex items-center justify-center text-white font-semibold text-lg flex-shrink-0">
                    {(creator.display_name || '?').charAt(0).toUpperCase()}
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <h3 className="text-[15px] font-semibold text-[#3D4A44] truncate group-hover:text-[#5B8A72] transition-colors">
                    {creator.display_name}
                  </h3>
                  {creator.top_role && (
                    <span className={`inline-block mt-1 px-2 py-0.5 text-[11px] font-medium rounded-full ${ROLE_COLORS[creator.top_role] || ROLE_COLORS.OTHER}`}>
                      {creator.top_role.replace('_', ' ')}
                    </span>
                  )}
                </div>
              </div>

              <div className="mt-4 flex items-end justify-between">
                <div>
                  <p className="text-xs text-[#7A8580]">Est. Streams</p>
                  <p className="text-lg font-bold text-[#3D4A44]">{formatNumber(creator.total_estimated_streams)}</p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-[#7A8580]">Credits</p>
                  <p className="text-lg font-bold text-[#3D4A44]">{creator.total_credits}</p>
                </div>
              </div>

              {Object.keys(creator.role_breakdown || {}).length > 1 && (
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {Object.entries(creator.role_breakdown).map(([role, count]) => (
                    <span
                      key={role}
                      className={`px-1.5 py-0.5 text-[10px] font-medium rounded ${ROLE_COLORS[role] || ROLE_COLORS.OTHER}`}
                    >
                      {role.replace('_', ' ')} ({count})
                    </span>
                  ))}
                </div>
              )}
            </button>
          ))}
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-[rgba(59,77,67,0.08)] overflow-hidden shadow-sm">
          <table className="w-full">
            <thead className="bg-[#EEF1EC] border-b border-[rgba(59,77,67,0.08)]">
              <tr>
                <th className="px-6 py-3 text-left text-sm font-semibold text-[#3D4A44]">Creator</th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-[#3D4A44]">Role</th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-[#3D4A44]">Est. Streams</th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-[#3D4A44]">Credits</th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-[#3D4A44] hidden lg:table-cell">Breakdown</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[rgba(59,77,67,0.08)]">
              {creators.map(creator => (
                <tr
                  key={creator.creator_id}
                  onClick={() => navigate(`/roster/${creator.creator_id}?tab=credits`)}
                  className="hover:bg-[#FAFBF9] transition-colors cursor-pointer"
                >
                  <td className="px-6 py-3">
                    <div className="flex items-center gap-3">
                      {creator.hero_image_url ? (
                        <img src={creator.hero_image_url} alt={creator.display_name} className="w-10 h-10 rounded-full object-cover flex-shrink-0" />
                      ) : (
                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#5B8A72] to-[#4A7A62] flex items-center justify-center text-white font-semibold text-sm flex-shrink-0">
                          {(creator.display_name || '?').charAt(0).toUpperCase()}
                        </div>
                      )}
                      <p className="font-semibold text-[#3D4A44] truncate">{creator.display_name}</p>
                    </div>
                  </td>
                  <td className="px-6 py-3">
                    {creator.top_role && (
                      <span className={`px-2 py-0.5 text-[11px] font-medium rounded-full ${ROLE_COLORS[creator.top_role] || ROLE_COLORS.OTHER}`}>
                        {creator.top_role.replace('_', ' ')}
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-3 text-sm font-bold text-[#3D4A44]">{formatNumber(creator.total_estimated_streams)}</td>
                  <td className="px-6 py-3 text-sm font-bold text-[#3D4A44]">{creator.total_credits}</td>
                  <td className="px-6 py-3 hidden lg:table-cell">
                    <div className="flex flex-wrap gap-1">
                      {Object.entries(creator.role_breakdown || {}).map(([role, count]) => (
                        <span key={role} className={`px-1.5 py-0.5 text-[10px] font-medium rounded ${ROLE_COLORS[role] || ROLE_COLORS.OTHER}`}>
                          {role.replace('_', ' ')} ({count})
                        </span>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showSocialCard && (
        <div style={{ position: 'fixed', top: 0, left: '-9999px', opacity: 0, pointerEvents: 'none' }}>
          <RosterSocialCard
            ref={socialCardRef}
            orgName={orgName}
            totalCredits={cardTotalCredits}
            totalStreams={cardTotalStreams}
            activeCreators={cardActiveCreators}
            topCreators={sortedForCard}
            format={socialCardFormat}
          />
        </div>
      )}
    </div>
  )
}
