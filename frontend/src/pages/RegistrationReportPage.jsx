import React, { useState, useEffect } from 'react'
import axios from 'axios'
import {
  ArrowDownTrayIcon,
  DocumentTextIcon,
  ExclamationTriangleIcon,
  ChevronDownIcon,
  ChevronUpIcon
} from '@heroicons/react/24/outline'
import { CheckCircleIcon } from '@heroicons/react/24/solid'

export default function RegistrationReportPage() {
  const [loading, setLoading] = useState(true)
  const [assetType, setAssetType] = useState('works')
  const [reportData, setReportData] = useState([])
  const [selectedCreatorId, setSelectedCreatorId] = useState('')
  const [creators, setCreators] = useState([])
  const [expandedItems, setExpandedItems] = useState(new Set())

  const orgId = JSON.parse(localStorage.getItem('organization'))?.id

  useEffect(() => {
    if (orgId) {
      axios.get(`/api/creators/org/${orgId}`)
        .then(res => setCreators(Array.isArray(res.data) ? res.data : res.data.creators || []))
        .catch(() => {})
    }
  }, [orgId])

  useEffect(() => {
    if (!orgId) { setLoading(false); return }
    setLoading(true)
    const params = selectedCreatorId ? `?creator_id=${selectedCreatorId}` : ''
    axios.get(`/api/registration-reports/org/${orgId}/${assetType}${params}`)
      .then(res => setReportData(Array.isArray(res.data) ? res.data : res.data.items || []))
      .catch(() => setReportData([]))
      .finally(() => setLoading(false))
  }, [orgId, assetType, selectedCreatorId])

  const toggleExpanded = (id) => {
    setExpandedItems(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const readyCount = reportData.filter(i => i.is_valid).length
  const needsAttentionCount = reportData.filter(i => !i.is_valid).length

  async function handleExport(format) {
    if (!orgId) return
    try {
      const params = new URLSearchParams({ asset_type: assetType })
      if (selectedCreatorId) params.append('creator_id', selectedCreatorId)
      const res = await axios.get(`/api/registration-reports/org/${orgId}/export/${format}?${params}`, { responseType: 'blob' })
      const ext = format === 'csv' ? 'csv' : 'pdf'
      const mime = format === 'csv' ? 'text/csv' : 'application/pdf'
      const url = window.URL.createObjectURL(new Blob([res.data], { type: mime }))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `Registration_Report_${assetType}.${ext}`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      console.error(`Failed to export ${format}:`, err)
      alert(`Failed to export ${format.toUpperCase()}`)
    }
  }

  return (
    <div className="p-4 sm:p-8">
      <div className="bg-gradient-to-r from-[#5B8A72] to-[#7A8580] rounded-2xl p-6 sm:p-8 mb-6 text-white">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <DocumentTextIcon className="w-8 h-8" />
              <h1 className="text-2xl sm:text-3xl font-bold">Registration Reports</h1>
            </div>
            <p className="text-white/80 text-sm sm:text-base">PRO registration readiness for your catalog</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => handleExport('csv')}
              className="flex items-center gap-2 px-4 py-2 bg-white/20 hover:bg-white/30 rounded-xl text-sm font-medium transition-colors"
            >
              <ArrowDownTrayIcon className="w-4 h-4" />
              CSV
            </button>
            <button
              onClick={() => handleExport('pdf')}
              className="flex items-center gap-2 px-4 py-2 bg-white/20 hover:bg-white/30 rounded-xl text-sm font-medium transition-colors"
            >
              <ArrowDownTrayIcon className="w-4 h-4" />
              PDF
            </button>
          </div>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <div className="flex bg-white rounded-xl border border-[rgba(59,77,67,0.12)] p-1">
          <button
            onClick={() => setAssetType('works')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              assetType === 'works'
                ? 'bg-[#5B8A72] text-white shadow-sm'
                : 'text-[#7A8580] hover:text-[#3D4A44]'
            }`}
          >
            Works
          </button>
          <button
            onClick={() => setAssetType('songs')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              assetType === 'songs'
                ? 'bg-[#5B8A72] text-white shadow-sm'
                : 'text-[#7A8580] hover:text-[#3D4A44]'
            }`}
          >
            Songs
          </button>
        </div>

        {creators.length > 0 && (
          <select
            value={selectedCreatorId}
            onChange={e => setSelectedCreatorId(e.target.value)}
            className="border border-[rgba(59,77,67,0.12)] rounded-xl px-3 py-2.5 bg-white text-[#3D4A44] focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent text-sm"
          >
            <option value="">All Creators</option>
            {creators.map(c => (
              <option key={c.id} value={c.id}>{c.name || c.display_name || c.legal_name}</option>
            ))}
          </select>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <div className="bg-white rounded-2xl border border-[rgba(59,77,67,0.12)] p-5">
          <p className="text-sm text-[#7A8580] mb-1">Total {assetType === 'works' ? 'Works' : 'Songs'}</p>
          <p className="text-3xl font-bold text-[#3D4A44]">{reportData.length}</p>
        </div>
        <div className="bg-white rounded-2xl border border-[rgba(59,77,67,0.12)] p-5">
          <div className="flex items-center gap-2 mb-1">
            <CheckCircleIcon className="w-4 h-4 text-emerald-500" />
            <p className="text-sm text-[#7A8580]">Ready</p>
          </div>
          <p className="text-3xl font-bold text-emerald-600">{readyCount}</p>
        </div>
        <div className="bg-white rounded-2xl border border-[rgba(59,77,67,0.12)] p-5">
          <div className="flex items-center gap-2 mb-1">
            <ExclamationTriangleIcon className="w-4 h-4 text-amber-500" />
            <p className="text-sm text-[#7A8580]">Needs Attention</p>
          </div>
          <p className="text-3xl font-bold text-amber-600">{needsAttentionCount}</p>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="text-[#7A8580]">Loading report...</div>
        </div>
      ) : reportData.length === 0 ? (
        <div className="bg-white rounded-2xl border border-[rgba(59,77,67,0.12)] p-12 text-center">
          <DocumentTextIcon className="w-12 h-12 text-[#B0BDB4] mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-[#3D4A44] mb-1">No {assetType} found</h3>
          <p className="text-sm text-[#7A8580]">Add {assetType} to your catalog to generate registration reports.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {reportData.map(item => {
            const isExpanded = expandedItems.has(item.id)
            return (
              <div key={item.id} className="bg-white rounded-2xl border border-[rgba(59,77,67,0.12)] overflow-hidden hover:shadow-md transition-shadow">
                <button
                  onClick={() => toggleExpanded(item.id)}
                  className="w-full flex items-center justify-between p-5 text-left"
                >
                  <div className="flex items-center gap-4 flex-1 min-w-0">
                    <div className="flex-1 min-w-0">
                      <h3 className="text-base font-semibold text-[#3D4A44] truncate">{item.title}</h3>
                      {(item.iswc || item.isrc) && (
                        <p className="text-sm text-[#7A8580] mt-0.5">{item.iswc || item.isrc}</p>
                      )}
                    </div>
                    <div className="flex-shrink-0">
                      {item.is_valid ? (
                        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700">
                          <CheckCircleIcon className="w-3.5 h-3.5" />
                          Ready
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-amber-50 text-amber-700">
                          <ExclamationTriangleIcon className="w-3.5 h-3.5" />
                          Needs Attention
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="ml-3 flex-shrink-0 text-[#7A8580]">
                    {isExpanded ? (
                      <ChevronUpIcon className="w-5 h-5" />
                    ) : (
                      <ChevronDownIcon className="w-5 h-5" />
                    )}
                  </div>
                </button>

                {isExpanded && (
                  <div className="px-5 pb-5 border-t border-[rgba(59,77,67,0.08)]">
                    {item.writers && item.writers.length > 0 && (
                      <div className="mt-4">
                        <h4 className="text-sm font-semibold text-[#3D4A44] mb-3">Writers</h4>
                        <div className="space-y-2">
                          {item.writers.map((writer, idx) => (
                            <div key={idx} className="flex flex-wrap items-center gap-x-4 gap-y-1 py-2 px-3 bg-[#F5F7F4] rounded-lg text-sm">
                              <span className="font-medium text-[#3D4A44]">{writer.name}</span>
                              {writer.pro && <span className="text-[#7A8580]">PRO: <span className="text-[#3D4A44]">{writer.pro}</span></span>}
                              {writer.ipi && <span className="text-[#7A8580]">IPI: <span className="text-[#3D4A44]">{writer.ipi}</span></span>}
                              {writer.share != null && <span className="text-[#7A8580]">Share: <span className="text-[#3D4A44]">{writer.share}%</span></span>}
                              {writer.publisher && <span className="text-[#7A8580]">Publisher: <span className="text-[#3D4A44]">{writer.publisher}</span></span>}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {item.validation_issues && item.validation_issues.length > 0 && (
                      <div className="mt-4">
                        <h4 className="text-sm font-semibold text-[#3D4A44] mb-2">Validation Issues</h4>
                        <ul className="space-y-1">
                          {item.validation_issues.map((issue, idx) => (
                            <li key={idx} className="flex items-start gap-2 text-sm text-amber-600">
                              <ExclamationTriangleIcon className="w-4 h-4 flex-shrink-0 mt-0.5" />
                              {issue}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {(!item.writers || item.writers.length === 0) && (!item.validation_issues || item.validation_issues.length === 0) && (
                      <p className="mt-4 text-sm text-[#7A8580]">No additional details available.</p>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}