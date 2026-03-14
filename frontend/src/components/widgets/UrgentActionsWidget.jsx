import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { ExclamationTriangleIcon, CheckCircleIcon } from '@heroicons/react/24/outline'
import { ExclamationCircleIcon } from '@heroicons/react/24/solid'
import axios from 'axios'

const PRIORITY_STYLES = {
  1: { label: 'High', color: '#C47068', bgColor: 'rgba(196, 112, 104, 0.15)' },
  2: { label: 'Medium', color: '#C4956B', bgColor: 'rgba(196, 149, 107, 0.15)' },
  3: { label: 'Low', color: '#5B9A6E', bgColor: 'rgba(91, 154, 110, 0.15)' }
}

const formatActionType = (type) => {
  const labels = {
    'MISSING_ISRC': 'Missing ISRC',
    'MISSING_ISWC': 'Missing ISWC',
    'CONTRACT_PENDING': 'Contract Pending',
    'PRO_INCOMPLETE': 'PRO Incomplete',
    'DSP_REGISTRATION': 'DSP Registration',
    'CUSTOM_DEADLINE': 'Custom Deadline',
    'GENERAL': 'General',
    'CONTRACT_EXPIRING': 'Contract Expiring',
    'RELEASE_INCOMPLETE': 'Release Incomplete',
    'UNMATCHED_ROYALTIES': 'Unmatched Royalties',
    'PLACEMENT_FOLLOWUP': 'Placement Follow-up',
    'PLACEMENT_NEEDS_CONTRACT': 'Needs Contract'
  }
  return labels[type] || type?.replace(/_/g, ' ') || type
}

export default function UrgentActionsWidget({ orgId }) {
  const [urgentActions, setUrgentActions] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!orgId) { setLoading(false); return }
    axios.get(`/api/actions/org/${orgId}?status=PENDING`)
      .then(res => {
        const actions = res.data
        const urgent = actions
          .filter(a => a.is_overdue || (a.days_until_deadline !== null && a.days_until_deadline <= 7))
          .sort((a, b) => {
            if (a.is_overdue && !b.is_overdue) return -1
            if (!a.is_overdue && b.is_overdue) return 1
            return a.priority - b.priority
          })
          .slice(0, 5)
        setUrgentActions(urgent)
      })
      .catch(e => console.error('UrgentActions: load failed:', e))
      .finally(() => setLoading(false))
  }, [orgId])

  const handleCompleteAction = async (actionId) => {
    try {
      await axios.post(`/api/actions/${actionId}/complete`)
      setUrgentActions(prev => prev.filter(a => a.id !== actionId))
    } catch (error) {
      console.error('Failed to complete action:', error)
    }
  }

  if (loading) {
    return (
      <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6 animate-pulse">
        <div className="h-4 bg-[#EEF1EC] rounded w-1/3 mb-3"></div>
        <div className="h-8 bg-[#EEF1EC] rounded w-1/4"></div>
      </div>
    )
  }

  if (urgentActions.length === 0) {
    return null
  }

  return (
    <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6 border-l-4 border-[#C47068]">
      <div className="flex justify-between items-center mb-4">
        <div className="flex items-center gap-2">
          <ExclamationTriangleIcon className="w-5 h-5 text-[#C47068]" />
          <h2 className="text-[22px] font-medium text-[#3D4A44]">Urgent Action Items</h2>
        </div>
        <Link to="/actions" className="text-[15px] text-[#5B8A72] hover:underline font-medium">
          View All →
        </Link>
      </div>

      <div className="space-y-2">
        {urgentActions.map(action => {
          const priorityStyle = PRIORITY_STYLES[action.priority] || PRIORITY_STYLES[2]
          return (
            <div key={action.id} className="flex items-center justify-between p-3 bg-[#FAFBF9] rounded-xl hover:bg-[#EEF1EC] transition-colors">
              <div className="flex items-center gap-3 flex-1 min-w-0">
                <button
                  onClick={() => handleCompleteAction(action.id)}
                  className="flex-shrink-0 w-6 h-6 rounded-full border-2 border-[#7A8580] hover:border-[#5B8A72] hover:bg-[rgba(91,138,114,0.1)] transition-colors flex items-center justify-center"
                >
                  <CheckCircleIcon className="w-4 h-4 text-transparent" />
                </button>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-[#3D4A44] text-sm truncate">{action.title}</p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span
                      className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium"
                      style={{ backgroundColor: priorityStyle.bgColor, color: priorityStyle.color }}
                    >
                      {priorityStyle.label}
                    </span>
                    <span className="text-[10px] text-[#7A8580]">{formatActionType(action.action_type)}</span>
                    {action.creator_name && (
                      <span className="text-[10px] text-[#5B8A72]">{action.creator_name}</span>
                    )}
                    {action.entity_type && action.entity_label && (
                      <span className="text-[10px] text-[#5A8A9A] capitalize">{action.entity_type}: {action.entity_label}</span>
                    )}
                  </div>
                </div>
              </div>
              <div className="flex-shrink-0 ml-3">
                {action.is_overdue ? (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-[rgba(196,112,104,0.15)] text-[#C47068]">
                    <ExclamationCircleIcon className="w-3 h-3" />
                    Overdue
                  </span>
                ) : action.days_until_deadline !== null ? (
                  <span className="text-[11px] text-[#C4956B] font-medium">
                    {action.days_until_deadline === 0 ? 'Due today' : `${action.days_until_deadline}d left`}
                  </span>
                ) : null}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
