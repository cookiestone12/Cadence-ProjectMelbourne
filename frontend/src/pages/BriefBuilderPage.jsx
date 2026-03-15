import React, { useState } from 'react'
import axios from 'axios'
import {
  MagnifyingGlassIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  PlayIcon,
  DocumentArrowDownIcon,
  TableCellsIcon,
  QueueListIcon,
  SparklesIcon
} from '@heroicons/react/24/outline'

const MOODS = ['uplifting', 'melancholic', 'tense', 'dreamy', 'energetic', 'calm', 'dark', 'hopeful', 'nostalgic', 'epic']
const TEXTURES = ['acoustic', 'electronic', 'gritty', 'lush', 'intimate', 'ambient', 'orchestral', 'minimal']
const KEYS = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

const MOOD_COLORS = {
  uplifting: 'bg-amber-100 text-amber-800',
  melancholic: 'bg-blue-100 text-blue-800',
  tense: 'bg-red-100 text-red-800',
  dreamy: 'bg-purple-100 text-purple-800',
  energetic: 'bg-orange-100 text-orange-800',
  calm: 'bg-teal-100 text-teal-800',
  dark: 'bg-gray-200 text-gray-800',
  hopeful: 'bg-emerald-100 text-emerald-800',
  nostalgic: 'bg-rose-100 text-rose-800',
  epic: 'bg-indigo-100 text-indigo-800'
}

const TEXTURE_COLORS = {
  acoustic: 'bg-yellow-100 text-yellow-800',
  electronic: 'bg-cyan-100 text-cyan-800',
  gritty: 'bg-stone-200 text-stone-800',
  lush: 'bg-green-100 text-green-800',
  intimate: 'bg-pink-100 text-pink-800',
  ambient: 'bg-sky-100 text-sky-800',
  orchestral: 'bg-violet-100 text-violet-800',
  minimal: 'bg-neutral-100 text-neutral-800'
}

export default function BriefBuilderPage() {
  const [query, setQuery] = useState('')
  const [filters, setFilters] = useState({
    bpm_min: '', bpm_max: '', key: '', moods: [], textures: [],
    vocal_present: null, has_stems: false, analyzed_only: false
  })
  const [results, setResults] = useState([])
  const [searching, setSearching] = useState(false)
  const [selectedResults, setSelectedResults] = useState([])
  const [expandedResult, setExpandedResult] = useState(null)
  const [filtersOpen, setFiltersOpen] = useState(true)
  const [keyMode, setKeyMode] = useState('major')

  const handleSearch = async () => {
    setSearching(true)
    try {
      const token = localStorage.getItem('token')
      const filterPayload = {
        ...filters,
        key: filters.key ? `${filters.key} ${keyMode}` : ''
      }
      const response = await axios.post('/api/brief-builder/search', {
        query,
        ...filterPayload,
        limit: 50
      }, { headers: { Authorization: `Bearer ${token}` } })
      setResults(response.data.results || [])
      setSelectedResults([])
    } catch (error) {
      console.error('Search failed:', error)
    } finally {
      setSearching(false)
    }
  }

  const toggleMood = (mood) => {
    setFilters(prev => ({
      ...prev,
      moods: prev.moods.includes(mood)
        ? prev.moods.filter(m => m !== mood)
        : [...prev.moods, mood]
    }))
  }

  const toggleTexture = (texture) => {
    setFilters(prev => ({
      ...prev,
      textures: prev.textures.includes(texture)
        ? prev.textures.filter(t => t !== texture)
        : [...prev.textures, texture]
    }))
  }

  const toggleResultSelection = (resultId) => {
    setSelectedResults(prev =>
      prev.includes(resultId)
        ? prev.filter(id => id !== resultId)
        : [...prev, resultId]
    )
  }

  const getMatchScoreColor = (score) => {
    if (score >= 80) return 'text-emerald-600 bg-emerald-50 border-emerald-200'
    if (score >= 60) return 'text-amber-600 bg-amber-50 border-amber-200'
    return 'text-gray-600 bg-gray-50 border-gray-200'
  }

  return (
    <div className="min-h-screen bg-[#F5F7F4] p-6 lg:p-8">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <SparklesIcon className="w-8 h-8 text-[#5B8A72]" />
            <h1 className="text-2xl sm:text-4xl font-bold text-[#3D4A44]">Brief Builder</h1>
          </div>
          <p className="text-[#7A8580] text-lg">Find the perfect tracks for your sync brief</p>
        </div>

        <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6 mb-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-semibold text-[#3D4A44] mb-2">Describe Your Brief</label>
              <textarea
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Describe what you're looking for... e.g., 'Uplifting indie folk track, female vocals, warm acoustic feel, 90-110 BPM, good for a car commercial'"
                rows={6}
                className="w-full border border-[rgba(59,77,67,0.12)] rounded-xl px-4 py-3 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44] placeholder-[#7A8580] resize-none text-[15px]"
              />
              <button
                onClick={handleSearch}
                disabled={searching}
                className="mt-3 flex items-center gap-2 px-6 py-2.5 bg-[#5B8A72] text-white rounded-xl hover:bg-[#4A7A62] transition-colors text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {searching ? (
                  <>
                    <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    <span>Searching...</span>
                  </>
                ) : (
                  <>
                    <MagnifyingGlassIcon className="w-4 h-4" />
                    <span>Search</span>
                  </>
                )}
              </button>
            </div>

            <div>
              <button
                onClick={() => setFiltersOpen(!filtersOpen)}
                className="flex items-center gap-2 text-sm font-semibold text-[#3D4A44] mb-3"
              >
                <span>Structured Filters</span>
                {filtersOpen ? <ChevronUpIcon className="w-4 h-4" /> : <ChevronDownIcon className="w-4 h-4" />}
              </button>

              {filtersOpen && (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-medium text-[#7A8580] mb-1">BPM Min</label>
                      <input
                        type="number"
                        value={filters.bpm_min}
                        onChange={(e) => setFilters(prev => ({ ...prev, bpm_min: e.target.value }))}
                        placeholder="60"
                        className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-[#7A8580] mb-1">BPM Max</label>
                      <input
                        type="number"
                        value={filters.bpm_max}
                        onChange={(e) => setFilters(prev => ({ ...prev, bpm_max: e.target.value }))}
                        placeholder="180"
                        className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-[#7A8580] mb-1">Key</label>
                    <div className="flex gap-2">
                      <select
                        value={filters.key}
                        onChange={(e) => setFilters(prev => ({ ...prev, key: e.target.value }))}
                        className="flex-1 border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                      >
                        <option value="">Any Key</option>
                        {KEYS.map(k => <option key={k} value={k}>{k}</option>)}
                      </select>
                      <div className="flex rounded-lg border border-[rgba(59,77,67,0.12)] overflow-hidden">
                        <button
                          onClick={() => setKeyMode('major')}
                          className={`px-3 py-2 text-xs font-medium transition-colors ${keyMode === 'major' ? 'bg-[#5B8A72] text-white' : 'bg-white text-[#7A8580] hover:bg-[#EEF1EC]'}`}
                        >
                          Major
                        </button>
                        <button
                          onClick={() => setKeyMode('minor')}
                          className={`px-3 py-2 text-xs font-medium transition-colors ${keyMode === 'minor' ? 'bg-[#5B8A72] text-white' : 'bg-white text-[#7A8580] hover:bg-[#EEF1EC]'}`}
                        >
                          Minor
                        </button>
                      </div>
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-[#7A8580] mb-2">Moods</label>
                    <div className="flex flex-wrap gap-2">
                      {MOODS.map(mood => (
                        <button
                          key={mood}
                          onClick={() => toggleMood(mood)}
                          className={`rounded-full px-3 py-1 text-[13px] font-medium transition-all ${
                            filters.moods.includes(mood)
                              ? 'bg-[#5B8A72] text-white shadow-sm'
                              : 'bg-[#EEF1EC] text-[#3D4A44] hover:bg-[#D8DDD6]'
                          }`}
                        >
                          {mood}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-[#7A8580] mb-2">Textures</label>
                    <div className="flex flex-wrap gap-2">
                      {TEXTURES.map(texture => (
                        <button
                          key={texture}
                          onClick={() => toggleTexture(texture)}
                          className={`rounded-full px-3 py-1 text-[13px] font-medium transition-all ${
                            filters.textures.includes(texture)
                              ? 'bg-[#5B8A72] text-white shadow-sm'
                              : 'bg-[#EEF1EC] text-[#3D4A44] hover:bg-[#D8DDD6]'
                          }`}
                        >
                          {texture}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-[#7A8580] mb-2">Vocal</label>
                    <div className="flex rounded-lg border border-[rgba(59,77,67,0.12)] overflow-hidden w-fit">
                      {[{ label: 'Any', value: null }, { label: 'Vocal', value: true }, { label: 'Instrumental', value: false }].map(opt => (
                        <button
                          key={opt.label}
                          onClick={() => setFilters(prev => ({ ...prev, vocal_present: opt.value }))}
                          className={`px-4 py-2 text-xs font-medium transition-colors ${
                            filters.vocal_present === opt.value
                              ? 'bg-[#5B8A72] text-white'
                              : 'bg-white text-[#7A8580] hover:bg-[#EEF1EC]'
                          }`}
                        >
                          {opt.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="flex items-center gap-6">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={filters.has_stems}
                        onChange={(e) => setFilters(prev => ({ ...prev, has_stems: e.target.checked }))}
                        className="w-4 h-4 rounded border-[rgba(59,77,67,0.2)] text-[#5B8A72] focus:ring-[#5B8A72]"
                      />
                      <span className="text-sm text-[#3D4A44]">Stems Available</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={filters.analyzed_only}
                        onChange={(e) => setFilters(prev => ({ ...prev, analyzed_only: e.target.checked }))}
                        className="w-4 h-4 rounded border-[rgba(59,77,67,0.2)] text-[#5B8A72] focus:ring-[#5B8A72]"
                      />
                      <span className="text-sm text-[#3D4A44]">Only analyzed songs</span>
                    </label>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {results.length > 0 && (
          <div className="mb-4">
            <p className="text-sm text-[#7A8580] font-medium">{results.length} result{results.length !== 1 ? 's' : ''} found</p>
          </div>
        )}

        <div className="space-y-3 pb-24">
          {searching && (
            <div className="flex items-center justify-center py-16">
              <div className="flex items-center gap-3 text-[#7A8580]">
                <svg className="animate-spin w-5 h-5" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                <span>Searching your catalog...</span>
              </div>
            </div>
          )}

          {!searching && results.map((result, idx) => {
            const resultKey = result.song_id || result.id || idx
            return (
              <div
                key={resultKey}
                className={`bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6 transition-all hover:shadow-[0px_6px_16px_rgba(0,0,0,0.12)] ${result.is_analyzed === false ? 'opacity-75' : ''}`}
              >
                <div className="flex items-start gap-4">
                  <input
                    type="checkbox"
                    checked={selectedResults.includes(resultKey)}
                    onChange={() => toggleResultSelection(resultKey)}
                    className="mt-1 w-4 h-4 rounded border-[rgba(59,77,67,0.2)] text-[#5B8A72] focus:ring-[#5B8A72]"
                  />

                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex items-center gap-2">
                        <div>
                          <h3 className="text-[16px] font-semibold text-[#3D4A44]">{result.title || 'Untitled'}</h3>
                          <p className="text-[14px] text-[#7A8580]">{result.artist || result.primary_artist || 'Unknown Artist'}</p>
                        </div>
                        {result.is_analyzed === false && (
                          <span className="rounded-full px-2.5 py-0.5 text-[11px] font-bold bg-amber-100 text-amber-700 whitespace-nowrap">
                            Not Analyzed
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        {result.score != null && result.score > 0 && (
                          <span className={`text-sm font-bold px-3 py-1 rounded-full border ${getMatchScoreColor(result.score)}`}>
                            {Math.round(result.score)} pts
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-2 mt-3">
                      {result.bpm && (
                        <span className="rounded-full px-3 py-1 text-[13px] font-medium bg-[#EEF1EC] text-[#3D4A44]">
                          {Math.round(result.bpm)} BPM
                        </span>
                      )}
                      {(result.musical_key || result.key) && (
                        <span className="rounded-full px-3 py-1 text-[13px] font-medium bg-[#EEF1EC] text-[#3D4A44]">
                          {result.musical_key || result.key}
                        </span>
                      )}
                      {result.energy_level && (
                        <span className="rounded-full px-3 py-1 text-[13px] font-medium bg-[#EEF1EC] text-[#3D4A44]">
                          {result.energy_level} energy
                        </span>
                      )}
                      {result.vocal_present != null && (
                        <span className="rounded-full px-3 py-1 text-[13px] font-medium bg-[#EEF1EC] text-[#3D4A44]">
                          {result.vocal_present ? 'Vocal' : 'Instrumental'}
                        </span>
                      )}
                      {result.moods && result.moods.map(mood => (
                        <span key={mood} className={`rounded-full px-3 py-1 text-[13px] font-medium ${MOOD_COLORS[mood.toLowerCase()] || 'bg-gray-100 text-gray-700'}`}>
                          {mood}
                        </span>
                      ))}
                      {result.textures && result.textures.map(texture => (
                        <span key={texture} className={`rounded-full px-3 py-1 text-[13px] font-medium ${TEXTURE_COLORS[texture.toLowerCase()] || 'bg-gray-100 text-gray-700'}`}>
                          {texture}
                        </span>
                      ))}
                      {result.sync_tags && result.sync_tags.map(tag => (
                        <span key={tag} className="rounded-full px-3 py-1 text-[13px] font-medium bg-[#F0EBF8] text-[#6B4FA0]">
                          {tag}
                        </span>
                      ))}
                    </div>

                    <div className="flex items-center gap-3 mt-3">
                      {(result.dropbox_link || result.audio_url) && (
                        <button
                          onClick={() => window.open(result.dropbox_link || result.audio_url, '_blank')}
                          className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-[#5B8A72] bg-[#EEF1EC] rounded-lg hover:bg-[#D8DDD6] transition-colors font-medium"
                        >
                          <PlayIcon className="w-4 h-4" />
                          <span>Play</span>
                        </button>
                      )}
                      <button
                        onClick={() => setExpandedResult(expandedResult === resultKey ? null : resultKey)}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-[#7A8580] hover:text-[#3D4A44] transition-colors font-medium"
                      >
                        <span>Why it matched</span>
                        {expandedResult === resultKey
                          ? <ChevronUpIcon className="w-3.5 h-3.5" />
                          : <ChevronDownIcon className="w-3.5 h-3.5" />
                        }
                      </button>
                    </div>

                    {expandedResult === resultKey && (
                      <div className="mt-3 pt-3 border-t border-[rgba(59,77,67,0.08)]">
                        <p className="text-sm text-[#7A8580]">
                          {result.match_reasons
                            ? (Array.isArray(result.match_reasons)
                                ? result.match_reasons.join(' \u2022 ')
                                : result.match_reasons)
                            : 'Match criteria details not available for this result.'}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )
          })}

          {!searching && results.length === 0 && query && (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <MagnifyingGlassIcon className="w-12 h-12 text-[#7A8580] opacity-40 mb-4" />
              <p className="text-[#7A8580] text-lg">No results found</p>
              <p className="text-[#7A8580] text-sm mt-1">Try adjusting your search criteria</p>
            </div>
          )}
        </div>

        {results.length > 0 && (
          <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-[rgba(59,77,67,0.12)] shadow-[0px_-4px_12px_rgba(0,0,0,0.08)] px-6 py-4 z-40">
            <div className="max-w-6xl mx-auto flex items-center justify-between">
              <p className="text-sm font-medium text-[#3D4A44]">
                {selectedResults.length} track{selectedResults.length !== 1 ? 's' : ''} selected
              </p>
              <div className="flex items-center gap-3">
                <button
                  disabled
                  className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-[#7A8580] bg-[#EEF1EC] rounded-xl cursor-not-allowed opacity-50"
                >
                  <DocumentArrowDownIcon className="w-4 h-4" />
                  <span>Export PDF</span>
                </button>
                <button
                  disabled
                  className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-[#7A8580] bg-[#EEF1EC] rounded-xl cursor-not-allowed opacity-50"
                >
                  <TableCellsIcon className="w-4 h-4" />
                  <span>Export CSV</span>
                </button>
                <button
                  disabled
                  className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-[#7A8580] bg-[#EEF1EC] rounded-xl cursor-not-allowed opacity-50"
                >
                  <QueueListIcon className="w-4 h-4" />
                  <span>Create Playlist</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}