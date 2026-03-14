import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { ClipboardDocumentCheckIcon } from '@heroicons/react/24/outline'
import axios from 'axios'

export default function TaskBreakdownWidget({ orgId }) {
  const [actionSummary, setActionSummary] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!orgId) { setLoading(false); return }
    axios.get(`/api/actions/summary/org/${orgId}`)
      .then(res => setActionSummary(res.data))
      .catch(e => console.error('TaskBreakdown: load failed:', e))
      .finally(() => setLoading(false))
  }, [orgId])

  if (loading) {
    return (
      <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6 animate-pulse">
        <div className="h-4 bg-[#EEF1EC] rounded w-1/3 mb-3"></div>
        <div className="h-8 bg-[#EEF1EC] rounded w-1/4"></div>
      </div>
    )
  }

  if (!actionSummary?.by_entity_type || Object.keys(actionSummary.by_entity_type).length === 0) {
    return null
  }

  return (
    <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6">
      <div className="flex justify-between items-center mb-4">
        <div className="flex items-center gap-2">
          <ClipboardDocumentCheckIcon className="w-5 h-5 text-[#5B8A72]" />
          <h2 className="text-[22px] font-medium text-[#3D4A44]">Tasks by Module</h2>
        </div>
        <Link to="/actions" className="text-[15px] text-[#5B8A72] hover:underline font-medium">
          Task Inbox →
        </Link>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {Object.entries(actionSummary.by_entity_type).map(([type, count]) => {
          const icons = { song: '🎵', work: '📝', release: '💿', contract: '📋', placement: '🎬', royalty: '💰' }
          return (
            <div key={type} className="bg-[#FAFBF9] rounded-xl p-3 text-center">
              <p className="text-[20px] mb-1">{icons[type] || '📌'}</p>
              <p className="text-[20px] font-semibold text-[#3D4A44]">{count}</p>
              <p className="text-[11px] text-[#7A8580] capitalize">{type}</p>
            </div>
          )
        })}
      </div>
    </div>
  )
}
