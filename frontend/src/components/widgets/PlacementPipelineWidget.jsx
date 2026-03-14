import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { FilmIcon } from '@heroicons/react/24/outline'
import axios from 'axios'

export default function PlacementPipelineWidget({ orgId }) {
  const [placementSummary, setPlacementSummary] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!orgId) { setLoading(false); return }
    axios.get(`/api/placements/org/${orgId}/summary`)
      .then(res => setPlacementSummary(res.data))
      .catch(e => console.error('PlacementPipeline: load failed:', e))
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

  if (!placementSummary || placementSummary.total_placements === 0) {
    return null
  }

  return (
    <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6">
      <div className="flex justify-between items-center mb-4">
        <div className="flex items-center gap-2">
          <FilmIcon className="w-5 h-5 text-[#5B8A72]" />
          <h2 className="text-[22px] font-medium text-[#3D4A44]">Placement Pipeline</h2>
        </div>
        <Link to="/placements" className="text-[15px] text-[#5B8A72] hover:underline font-medium">
          View All →
        </Link>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        <div className="bg-[#FAFBF9] rounded-xl p-3 text-center">
          <p className="text-[24px] font-semibold text-[#3D4A44]">{placementSummary.total_placements}</p>
          <p className="text-[12px] text-[#7A8580]">Total</p>
        </div>
        <div className="bg-[#FAFBF9] rounded-xl p-3 text-center">
          <p className="text-[24px] font-semibold text-[#5B8A72]">
            ${(placementSummary.total_pipeline_value || 0).toLocaleString()}
          </p>
          <p className="text-[12px] text-[#7A8580]">Pipeline Value</p>
        </div>
        <div className="bg-[#FAFBF9] rounded-xl p-3 text-center">
          <p className="text-[24px] font-semibold text-[#5B9A6E]">
            ${(placementSummary.total_paid || 0).toLocaleString()}
          </p>
          <p className="text-[12px] text-[#7A8580]">Paid</p>
        </div>
        <div className="bg-[#FAFBF9] rounded-xl p-3 text-center">
          <p className="text-[24px] font-semibold text-[#C4956B]">
            {(placementSummary.status_counts?.['IN_NEGOTIATION'] || 0) + (placementSummary.status_counts?.['PITCHED'] || 0)}
          </p>
          <p className="text-[12px] text-[#7A8580]">Active Pitches</p>
        </div>
      </div>
      {Object.keys(placementSummary.status_counts || {}).length > 0 && (
        <div className="flex flex-wrap gap-2">
          {Object.entries(placementSummary.status_counts).map(([status, count]) => (
            <span key={status} className="px-2.5 py-1 bg-[#EEF1EC] rounded-full text-[11px] font-medium text-[#3D4A44]">
              {status.replace(/_/g, ' ')}: {count}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
