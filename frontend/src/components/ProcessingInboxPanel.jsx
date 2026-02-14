import React, { useState, useEffect } from 'react'
import axios from 'axios'
import {
  ExclamationTriangleIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  EyeIcon,
  DocumentTextIcon,
  InboxIcon,
} from '@heroicons/react/24/outline'

const INBOX_STATUSES = [
  { key: 'MAPPING_REQUIRED', label: 'Needs Mapping', bg: 'bg-amber-100', text: 'text-amber-700', icon: ExclamationTriangleIcon },
  { key: 'MATCHING', label: 'Matching in Progress', bg: 'bg-blue-100', text: 'text-blue-700', icon: ArrowPathIcon },
  { key: 'READY_TO_PROCESS', label: 'Ready to Process', bg: 'bg-green-100', text: 'text-green-700', icon: CheckCircleIcon },
  { key: 'PARTIALLY_MATCHED', label: 'Review Required', bg: 'bg-orange-100', text: 'text-orange-700', icon: EyeIcon },
  { key: 'PROCESSING', label: 'Processing', bg: 'bg-blue-100', text: 'text-blue-700', icon: ArrowPathIcon },
  { key: 'UPLOADED', label: 'Uploaded', bg: 'bg-gray-100', text: 'text-gray-700', icon: DocumentTextIcon },
  { key: 'REVIEW_REQUIRED', label: 'Review Required', bg: 'bg-orange-100', text: 'text-orange-700', icon: EyeIcon },
  { key: 'FULLY_MATCHED', label: 'Fully Matched', bg: 'bg-green-100', text: 'text-green-700', icon: CheckCircleIcon },
]

export default function ProcessingInboxPanel({ orgId, onSelectStatement }) {
  const [inbox, setInbox] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!orgId) return
    setLoading(true)
    axios.get(`/api/royalty-processing/${orgId}/inbox`)
      .then(res => setInbox(res.data))
      .catch(err => console.error('Inbox load error:', err))
      .finally(() => setLoading(false))
  }, [orgId])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-[#5B8A72] border-t-transparent"></div>
          <p className="mt-2 text-sm text-[#7A8580]">Loading inbox...</p>
        </div>
      </div>
    )
  }

  if (!inbox) return null

  const statusCards = INBOX_STATUSES
    .map(s => ({ ...s, count: inbox.by_status?.[s.key] || 0 }))
    .filter(s => s.count > 0)

  return (
    <div className="bg-white/80 backdrop-blur-xl rounded-[18px] shadow-am p-6 border border-[rgba(59,77,67,0.08)]">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] rounded-lg">
            <InboxIcon className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-[#3D4A44]">Processing Inbox</h3>
            <p className="text-sm text-[#7A8580]">{inbox.total_statements || 0} total statements</p>
          </div>
        </div>
      </div>

      {statusCards.length === 0 ? (
        <div className="text-center py-8">
          <InboxIcon className="w-12 h-12 text-[#7A8580] mx-auto mb-3 opacity-40" />
          <p className="text-sm text-[#7A8580]">No statements in processing queue</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {statusCards.map(card => {
            const Icon = card.icon
            return (
              <div key={card.key} className="bg-white/60 backdrop-blur-xl rounded-[14px] border border-[rgba(59,77,67,0.08)] p-4 hover:shadow-md transition-shadow">
                <div className="flex items-center justify-between mb-3">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${card.bg} ${card.text}`}>
                    {card.label}
                  </span>
                  <Icon className={`w-5 h-5 ${card.text}`} />
                </div>
                <div className="text-3xl font-bold text-[#3D4A44] mb-2">{card.count}</div>
                <button
                  onClick={() => onSelectStatement && onSelectStatement(card.key)}
                  className="w-full flex items-center justify-center gap-2 px-3 py-1.5 text-sm bg-[rgba(91,138,114,0.1)] text-[#5B8A72] rounded-xl hover:bg-[rgba(91,138,114,0.2)] transition-colors font-medium"
                >
                  <EyeIcon className="w-4 h-4" /> View
                </button>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
