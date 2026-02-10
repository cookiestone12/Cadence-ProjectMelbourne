import React, { useState, useEffect, useCallback } from 'react'
import axios from 'axios'
import {
  MagnifyingGlassIcon,
  MusicalNoteIcon,
  DocumentTextIcon,
  RectangleStackIcon,
  UsersIcon
} from '@heroicons/react/24/outline'

const ENTITY_TYPES = [
  { key: 'songs', label: 'Songs', icon: MusicalNoteIcon },
  { key: 'works', label: 'Works', icon: DocumentTextIcon },
  { key: 'releases', label: 'Releases', icon: RectangleStackIcon },
  { key: 'creators', label: 'Creators', icon: UsersIcon },
]

export default function SearchPage() {
  const [searchTerm, setSearchTerm] = useState('')
  const [debouncedTerm, setDebouncedTerm] = useState('')
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [orgId, setOrgId] = useState(null)
  const [activeTypes, setActiveTypes] = useState(new Set(['songs', 'works', 'releases', 'creators']))

  useEffect(() => {
    axios.get('/api/organizations/current').then(res => {
      const id = res.data?.id
      if (id) setOrgId(id)
    }).catch(err => console.error('Failed to load organization:', err))
  }, [])

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedTerm(searchTerm)
    }, 300)
    return () => clearTimeout(timer)
  }, [searchTerm])

  useEffect(() => {
    if (!debouncedTerm || !orgId || activeTypes.size === 0) {
      if (!debouncedTerm) setResults(null)
      return
    }

    setLoading(true)
    const params = new URLSearchParams()
    params.append('q', debouncedTerm)
    params.append('entity_types', Array.from(activeTypes).join(','))

    axios.get(`/api/bulk/search/${orgId}?${params}`)
      .then(res => setResults(res.data))
      .catch(err => console.error('Search failed:', err))
      .finally(() => setLoading(false))
  }, [debouncedTerm, orgId, activeTypes])

  const toggleType = useCallback((type) => {
    setActiveTypes(prev => {
      const next = new Set(prev)
      if (next.has(type)) {
        if (next.size > 1) next.delete(type)
      } else {
        next.add(type)
      }
      return next
    })
  }, [])

  const handleResultClick = useCallback((item) => {
    console.log('Selected result:', item)
  }, [])

  const totalResults = results
    ? Object.values(results).reduce((sum, arr) => sum + (arr?.length || 0), 0)
    : 0

  const hasResults = results && totalResults > 0
  const hasSearched = results !== null

  return (
    <div className="p-8 pb-24 min-h-screen" style={{ backgroundColor: '#F5F7F4' }}>
      <div className="max-w-4xl mx-auto">
        <div className="mb-8 text-center">
          <h1 className="text-4xl font-bold text-[#3D4A44] mb-2">Search</h1>
          <p className="text-[#7A8580]">Find songs, works, releases, and creators across your catalog</p>
        </div>

        <div className="relative mb-6">
          <MagnifyingGlassIcon className="w-6 h-6 absolute left-5 top-1/2 transform -translate-y-1/2 text-[#7A8580]" />
          <input
            type="text"
            placeholder="Search by title, artist, ISRC, UPC, name..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            autoFocus
            className="w-full pl-14 pr-6 py-4 text-lg border border-[rgba(59,77,67,0.12)] rounded-2xl focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-[#FAFBF9] text-[#3D4A44] shadow-sm placeholder-[#7A8580]"
          />
          {loading && (
            <div className="absolute right-5 top-1/2 transform -translate-y-1/2">
              <div className="w-5 h-5 border-2 border-[#5B8A72] border-t-transparent rounded-full animate-spin" />
            </div>
          )}
        </div>

        <div className="flex items-center gap-2 mb-8 flex-wrap">
          {ENTITY_TYPES.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => toggleType(key)}
              className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all duration-150 ${
                activeTypes.has(key)
                  ? 'bg-[#5B8A72] text-white shadow-sm'
                  : 'bg-[#FAFBF9] text-[#7A8580] border border-[rgba(59,77,67,0.12)] hover:bg-[#EEF1EC] hover:text-[#3D4A44]'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{label}</span>
            </button>
          ))}
        </div>

        {!searchTerm && !hasSearched && (
          <div className="text-center py-20">
            <MagnifyingGlassIcon className="w-16 h-16 mx-auto text-[rgba(59,77,67,0.12)] mb-4" />
            <p className="text-[#7A8580] text-lg">Start typing to search your catalog</p>
          </div>
        )}

        {hasSearched && !hasResults && !loading && (
          <div className="text-center py-20">
            <MagnifyingGlassIcon className="w-16 h-16 mx-auto text-[rgba(59,77,67,0.12)] mb-4" />
            <p className="text-[#3D4A44] text-lg font-medium mb-1">No results found</p>
            <p className="text-[#7A8580]">Try adjusting your search term or filters</p>
          </div>
        )}

        {hasResults && (
          <div className="space-y-6">
            <p className="text-sm text-[#7A8580]">{totalResults} result{totalResults !== 1 ? 's' : ''} found</p>

            {results.songs?.length > 0 && (
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <MusicalNoteIcon className="w-5 h-5 text-[#5B8A72]" />
                  <h2 className="text-lg font-semibold text-[#3D4A44]">Songs</h2>
                  <span className="text-sm text-[#7A8580]">({results.songs.length})</span>
                </div>
                <div className="bg-[#FAFBF9] rounded-xl border border-[rgba(59,77,67,0.08)] overflow-hidden">
                  {results.songs.map((song, i) => (
                    <div
                      key={song.id}
                      onClick={() => handleResultClick(song)}
                      className={`flex items-center justify-between px-5 py-3.5 cursor-pointer hover:bg-[#EEF1EC] transition-colors duration-150 ${
                        i > 0 ? 'border-t border-[rgba(59,77,67,0.08)]' : ''
                      }`}
                    >
                      <div className="min-w-0 flex-1">
                        <p className="text-[15px] font-medium text-[#3D4A44] truncate">{song.title}</p>
                        <p className="text-[13px] text-[#7A8580] truncate">{song.primary_artist}</p>
                      </div>
                      {song.isrc && (
                        <span className="text-[12px] text-[#7A8580] bg-[#EEF1EC] px-2.5 py-1 rounded-md font-mono ml-3 shrink-0">
                          {song.isrc}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {results.works?.length > 0 && (
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <DocumentTextIcon className="w-5 h-5 text-[#5B8A72]" />
                  <h2 className="text-lg font-semibold text-[#3D4A44]">Works</h2>
                  <span className="text-sm text-[#7A8580]">({results.works.length})</span>
                </div>
                <div className="bg-[#FAFBF9] rounded-xl border border-[rgba(59,77,67,0.08)] overflow-hidden">
                  {results.works.map((work, i) => (
                    <div
                      key={work.id}
                      onClick={() => handleResultClick(work)}
                      className={`flex items-center justify-between px-5 py-3.5 cursor-pointer hover:bg-[#EEF1EC] transition-colors duration-150 ${
                        i > 0 ? 'border-t border-[rgba(59,77,67,0.08)]' : ''
                      }`}
                    >
                      <div className="min-w-0 flex-1">
                        <p className="text-[15px] font-medium text-[#3D4A44] truncate">{work.title}</p>
                      </div>
                      {work.iswc && (
                        <span className="text-[12px] text-[#7A8580] bg-[#EEF1EC] px-2.5 py-1 rounded-md font-mono ml-3 shrink-0">
                          {work.iswc}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {results.releases?.length > 0 && (
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <RectangleStackIcon className="w-5 h-5 text-[#5B8A72]" />
                  <h2 className="text-lg font-semibold text-[#3D4A44]">Releases</h2>
                  <span className="text-sm text-[#7A8580]">({results.releases.length})</span>
                </div>
                <div className="bg-[#FAFBF9] rounded-xl border border-[rgba(59,77,67,0.08)] overflow-hidden">
                  {results.releases.map((release, i) => (
                    <div
                      key={release.id}
                      onClick={() => handleResultClick(release)}
                      className={`flex items-center justify-between px-5 py-3.5 cursor-pointer hover:bg-[#EEF1EC] transition-colors duration-150 ${
                        i > 0 ? 'border-t border-[rgba(59,77,67,0.08)]' : ''
                      }`}
                    >
                      <div className="min-w-0 flex-1">
                        <p className="text-[15px] font-medium text-[#3D4A44] truncate">{release.title}</p>
                        <p className="text-[13px] text-[#7A8580] truncate">{release.primary_artist}</p>
                      </div>
                      {release.upc && (
                        <span className="text-[12px] text-[#7A8580] bg-[#EEF1EC] px-2.5 py-1 rounded-md font-mono ml-3 shrink-0">
                          {release.upc}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {results.creators?.length > 0 && (
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <UsersIcon className="w-5 h-5 text-[#5B8A72]" />
                  <h2 className="text-lg font-semibold text-[#3D4A44]">Creators</h2>
                  <span className="text-sm text-[#7A8580]">({results.creators.length})</span>
                </div>
                <div className="bg-[#FAFBF9] rounded-xl border border-[rgba(59,77,67,0.08)] overflow-hidden">
                  {results.creators.map((creator, i) => (
                    <div
                      key={creator.id}
                      onClick={() => handleResultClick(creator)}
                      className={`flex items-center justify-between px-5 py-3.5 cursor-pointer hover:bg-[#EEF1EC] transition-colors duration-150 ${
                        i > 0 ? 'border-t border-[rgba(59,77,67,0.08)]' : ''
                      }`}
                    >
                      <div className="min-w-0 flex-1">
                        <p className="text-[15px] font-medium text-[#3D4A44] truncate">{creator.display_name}</p>
                        <p className="text-[13px] text-[#7A8580] truncate">
                          {[creator.email, creator.roles].filter(Boolean).join(' · ')}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}