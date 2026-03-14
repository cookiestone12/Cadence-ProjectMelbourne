import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import axios from 'axios'

export default function TopCreatorsWidget({ orgId }) {
  const [topCreators, setTopCreators] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!orgId) { setLoading(false); return }
    axios.get(`/api/creators/org/${orgId}`)
      .then(res => {
        const creators = res.data
          .sort((a, b) => b.song_count - a.song_count)
          .slice(0, 4)
        setTopCreators(creators)
      })
      .catch(e => console.error('TopCreators: load failed:', e))
      .finally(() => setLoading(false))
  }, [orgId])

  return (
    <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6">
      <div className="flex justify-between items-center mb-5">
        <h2 className="text-[22px] font-medium text-[#3D4A44]">Top Creators</h2>
        <Link to="/roster" className="text-[15px] text-[#5B8A72] hover:underline font-medium">
          View All →
        </Link>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1,2,3,4].map(i => (
            <div key={i} className="flex items-center space-x-4 p-4 bg-[#EEF1EC] rounded-xl animate-pulse">
              <div className="w-12 h-12 rounded-full bg-[#D1D5DB]"></div>
              <div className="flex-1"><div className="h-4 bg-[#D1D5DB] rounded w-2/3 mb-2"></div><div className="h-3 bg-[#D1D5DB] rounded w-1/3"></div></div>
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {topCreators.map((creator) => (
            <Link
              key={creator.id}
              to={`/roster/${creator.id}`}
              className="flex items-center space-x-4 p-4 bg-[#EEF1EC] rounded-xl hover:bg-[#E5E5EA] transition-colors"
            >
              <div className="w-12 h-12 rounded-full bg-gradient-to-r from-[#5B8A72] to-[#7BA594] flex items-center justify-center text-white font-semibold shadow-md">
                {creator.display_name.charAt(0).toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium text-[#3D4A44] truncate">{creator.display_name}</p>
                <p className="text-[13px] text-[#7A8580]">{creator.song_count} songs</p>
              </div>
              <div className={`text-[15px] font-medium ${
                creator.avg_health_score >= 80 ? 'text-[#5B9A6E]' :
                creator.avg_health_score >= 60 ? 'text-[#C4956B]' :
                'text-[#C47068]'
              }`}>
                {creator.avg_health_score?.toFixed(0) || 0}%
              </div>
            </Link>
          ))}

          {topCreators.length === 0 && (
            <div className="text-center py-8 col-span-full">
              <p className="text-[#7A8580]">No creators yet</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
