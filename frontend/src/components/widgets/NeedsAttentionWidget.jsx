import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import axios from 'axios'

export default function NeedsAttentionWidget({ orgId }) {
  const [needsAttention, setNeedsAttention] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!orgId) { setLoading(false); return }
    axios.get(`/api/songs/org/${orgId}`)
      .then(res => {
        const lowHealth = res.data
          .filter(s => s.status_health_score < 50)
          .sort((a, b) => a.status_health_score - b.status_health_score)
          .slice(0, 5)
        setNeedsAttention(lowHealth)
      })
      .catch(e => console.error('NeedsAttention: load failed:', e))
      .finally(() => setLoading(false))
  }, [orgId])

  return (
    <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6">
      <div className="flex justify-between items-center mb-5">
        <h2 className="text-[22px] font-medium text-[#3D4A44]">Needs Attention</h2>
        <Link to="/catalog" className="text-[15px] text-[#5B8A72] hover:underline font-medium">
          View All →
        </Link>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1,2,3].map(i => (
            <div key={i} className="flex items-center justify-between p-4 bg-[#EEF1EC] rounded-xl animate-pulse">
              <div className="flex-1"><div className="h-4 bg-[#D1D5DB] rounded w-2/3 mb-2"></div><div className="h-3 bg-[#D1D5DB] rounded w-1/3"></div></div>
              <div className="h-6 w-12 bg-[#D1D5DB] rounded-full"></div>
            </div>
          ))}
        </div>
      ) : (
        <div className="space-y-3">
          {needsAttention.map((song) => (
            <div key={song.id} className="flex items-center justify-between p-4 bg-[#EEF1EC] rounded-xl">
              <div className="flex-1 min-w-0">
                <p className="font-medium text-[#3D4A44] truncate">{song.title}</p>
                <p className="text-[13px] text-[#7A8580]">{song.primary_artist}</p>
              </div>
              <div className="ml-4">
                <span className="px-3 py-1 bg-[rgba(196,112,104,0.15)] text-[#C47068] rounded-full text-[13px] font-medium">
                  {song.status_health_score.toFixed(0)}%
                </span>
              </div>
            </div>
          ))}

          {needsAttention.length === 0 && (
            <div className="text-center py-8">
              <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-[rgba(91,154,110,0.15)] flex items-center justify-center">
                <svg className="w-6 h-6 text-[#5B9A6E]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <p className="text-[#7A8580]">All songs in good health!</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
