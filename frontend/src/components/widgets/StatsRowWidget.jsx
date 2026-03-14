import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import axios from 'axios'

export default function StatsRowWidget({ org, orgId }) {
  const [actionSummary, setActionSummary] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!orgId) { setLoading(false); return }
    axios.get(`/api/actions/summary/org/${orgId}`)
      .then(res => setActionSummary(res.data))
      .catch(e => console.error('StatsRow: action summary load failed:', e))
      .finally(() => setLoading(false))
  }, [orgId])

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
      <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6 relative overflow-hidden">
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-[#5B8A72] to-[#7BA594]"></div>
        <p className="text-[13px] text-[#7A8580] mb-1">Total Songs</p>
        <p className="text-[40px] font-semibold text-[#3D4A44]">{org?.song_count || 0}</p>
      </div>

      <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6 relative overflow-hidden">
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-[#7BA594] to-[#4A7A62]"></div>
        <p className="text-[13px] text-[#7A8580] mb-1">Active Creators</p>
        <p className="text-[40px] font-semibold text-[#3D4A44]">{org?.creator_count || 0}</p>
      </div>

      <Link to="/actions" className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6 relative overflow-hidden hover:shadow-[0px_6px_16px_rgba(0,0,0,0.12)] transition-shadow">
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-[#C47068] to-[#C4956B]"></div>
        <p className="text-[13px] text-[#7A8580] mb-1">Pending Actions</p>
        <div className="flex items-end justify-between">
          {!loading ? (
            <>
              <p className="text-[40px] font-semibold text-[#3D4A44]">{actionSummary?.total_pending || 0}</p>
              {actionSummary?.overdue > 0 && (
                <span className="mb-2 px-2 py-0.5 bg-[rgba(196,112,104,0.15)] text-[#C47068] rounded-full text-[12px] font-medium">
                  {actionSummary.overdue} overdue
                </span>
              )}
            </>
          ) : (
            <div className="h-12 w-16 bg-[#EEF1EC] rounded animate-pulse"></div>
          )}
        </div>
      </Link>

      <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6 relative overflow-hidden">
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-[#5B9A6E] to-[#6BAA7E]"></div>
        <p className="text-[13px] text-[#7A8580] mb-1">Due This Week</p>
        <div className="flex items-end justify-between">
          {!loading ? (
            <>
              <p className="text-[40px] font-semibold text-[#3D4A44]">{actionSummary?.due_this_week || 0}</p>
              {actionSummary?.high_priority > 0 && (
                <span className="mb-2 px-2 py-0.5 bg-[rgba(196,112,104,0.15)] text-[#C47068] rounded-full text-[12px] font-medium">
                  {actionSummary.high_priority} high priority
                </span>
              )}
            </>
          ) : (
            <div className="h-12 w-16 bg-[#EEF1EC] rounded animate-pulse"></div>
          )}
        </div>
      </div>
    </div>
  )
}
