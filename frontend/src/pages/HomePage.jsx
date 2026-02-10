import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import axios from 'axios'
import {
  ExclamationTriangleIcon,
  ClockIcon,
  CalendarIcon,
  FlagIcon,
  BellIcon,
  ClipboardDocumentCheckIcon,
  CheckCircleIcon,
  FilmIcon,
  CurrencyDollarIcon
} from '@heroicons/react/24/outline'
import { ExclamationCircleIcon } from '@heroicons/react/24/solid'

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

const getTimeAgo = (dateStr) => {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now - date
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)
  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return date.toLocaleDateString()
}

const getNotificationTypeColor = (type) => {
  const colors = {
    MISSING_ISRC: '#C4956B',
    MISSING_ISWC: '#C4956B',
    CONTRACT_PENDING: '#C47068',
    PRO_INCOMPLETE: '#C4956B',
    WEEKLY_HEALTH_SUMMARY: '#5A8A9A',
    SYSTEM_ANNOUNCEMENT: '#5B8A72',
    CATALOG_UPDATE: '#7BA594',
    PLACEMENT_UPDATE: '#5B9A6E'
  }
  return colors[type] || '#7A8580'
}

export default function HomePage() {
  const [org, setOrg] = useState(null)
  const [recentSongs, setRecentSongs] = useState([])
  const [needsAttention, setNeedsAttention] = useState([])
  const [topCreators, setTopCreators] = useState([])
  const [actionSummary, setActionSummary] = useState(null)
  const [urgentActions, setUrgentActions] = useState([])
  const [recentNotifications, setRecentNotifications] = useState([])
  const [placementSummary, setPlacementSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  
  useEffect(() => {
    async function loadDashboard() {
      try {
        const orgResponse = await axios.get('/api/organizations/current')
        const orgId = orgResponse.data?.id
        if (!orgId) { setLoading(false); return }
        setOrg(orgResponse.data)
        
        const [songsResponse, creatorsResponse, summaryResponse, actionsResponse, notificationsResponse, placementRes] = await Promise.allSettled([
          axios.get(`/api/songs/org/${orgId}`),
          axios.get(`/api/creators/org/${orgId}`),
          axios.get(`/api/actions/summary/org/${orgId}`),
          axios.get(`/api/actions/org/${orgId}?status=PENDING`),
          axios.get('/api/notifications?limit=5'),
          axios.get(`/api/placements/org/${orgId}/summary`)
        ])
        
        if (songsResponse.status === 'fulfilled') {
          const songs = songsResponse.value.data
          setRecentSongs(songs.slice(0, 5))
          const lowHealth = songs
            .filter(s => s.status_health_score < 50)
            .sort((a, b) => a.status_health_score - b.status_health_score)
            .slice(0, 5)
          setNeedsAttention(lowHealth)
        }
        
        if (creatorsResponse.status === 'fulfilled') {
          const creators = creatorsResponse.value.data
            .sort((a, b) => b.song_count - a.song_count)
            .slice(0, 4)
          setTopCreators(creators)
        }
        
        if (summaryResponse.status === 'fulfilled') {
          setActionSummary(summaryResponse.value.data)
        }
        
        if (actionsResponse.status === 'fulfilled') {
          const actions = actionsResponse.value.data
          const urgent = actions
            .filter(a => a.is_overdue || (a.days_until_deadline !== null && a.days_until_deadline <= 7))
            .sort((a, b) => {
              if (a.is_overdue && !b.is_overdue) return -1
              if (!a.is_overdue && b.is_overdue) return 1
              return a.priority - b.priority
            })
            .slice(0, 5)
          setUrgentActions(urgent)
        }
        
        if (notificationsResponse.status === 'fulfilled') {
          setRecentNotifications(notificationsResponse.value.data)
        }

        if (placementRes.status === 'fulfilled') {
          setPlacementSummary(placementRes.value.data)
        }
      } catch (error) {
        console.error('Failed to load dashboard:', error)
      } finally {
        setLoading(false)
      }
    }
    
    loadDashboard()
  }, [])

  const handleCompleteAction = async (actionId) => {
    try {
      await axios.post(`/api/actions/${actionId}/complete`)
      setUrgentActions(prev => prev.filter(a => a.id !== actionId))
      if (actionSummary) {
        setActionSummary(prev => ({
          ...prev,
          total_pending: Math.max(0, prev.total_pending - 1)
        }))
      }
    } catch (error) {
      console.error('Failed to complete action:', error)
    }
  }
  
  if (loading) {
    return (
      <div className="min-h-screen bg-[#F5F7F4] flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-[#5B8A72] border-t-transparent"></div>
          <p className="mt-4 text-[#7A8580]">Loading dashboard...</p>
        </div>
      </div>
    )
  }
  
  return (
    <div className="min-h-screen bg-[#F5F7F4] p-6 lg:p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <div className="flex items-center gap-4">
            {org?.logo_url && (
              <img src={org.logo_url} alt={org.display_name || org.name} className="w-12 h-12 rounded-xl object-contain shadow-sm" />
            )}
            <div>
              <h1 className="text-[34px] font-semibold text-[#3D4A44] leading-tight">
                Welcome back, {org?.display_name || org?.name}
              </h1>
              <p className="text-[17px] text-[#7A8580] mt-1">Here's what's happening with your catalog</p>
            </div>
          </div>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
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
              <p className="text-[40px] font-semibold text-[#3D4A44]">{actionSummary?.total_pending || 0}</p>
              {actionSummary?.overdue > 0 && (
                <span className="mb-2 px-2 py-0.5 bg-[rgba(196,112,104,0.15)] text-[#C47068] rounded-full text-[12px] font-medium">
                  {actionSummary.overdue} overdue
                </span>
              )}
            </div>
          </Link>
          
          <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6 relative overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-[#5B9A6E] to-[#6BAA7E]"></div>
            <p className="text-[13px] text-[#7A8580] mb-1">Due This Week</p>
            <div className="flex items-end justify-between">
              <p className="text-[40px] font-semibold text-[#3D4A44]">{actionSummary?.due_this_week || 0}</p>
              {actionSummary?.high_priority > 0 && (
                <span className="mb-2 px-2 py-0.5 bg-[rgba(196,112,104,0.15)] text-[#C47068] rounded-full text-[12px] font-medium">
                  {actionSummary.high_priority} high priority
                </span>
              )}
            </div>
          </div>
        </div>

        {(placementSummary && placementSummary.total_placements > 0) && (
          <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6 mb-6">
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
        )}

        {actionSummary?.by_entity_type && Object.keys(actionSummary.by_entity_type).length > 0 && (
          <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6 mb-6">
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
        )}

        {urgentActions.length > 0 && (
          <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6 mb-6 border-l-4 border-[#C47068]">
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
        )}
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6">
            <div className="flex justify-between items-center mb-5">
              <h2 className="text-[22px] font-medium text-[#3D4A44]">Needs Attention</h2>
              <Link to="/catalog" className="text-[15px] text-[#5B8A72] hover:underline font-medium">
                View All →
              </Link>
            </div>
            
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
          </div>

          <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6">
            <div className="flex justify-between items-center mb-5">
              <div className="flex items-center gap-2">
                <BellIcon className="w-5 h-5 text-[#5B8A72]" />
                <h2 className="text-[22px] font-medium text-[#3D4A44]">Recent Notifications</h2>
              </div>
              <Link to="/settings" className="text-[15px] text-[#5B8A72] hover:underline font-medium">
                Settings →
              </Link>
            </div>
            
            <div className="space-y-2">
              {recentNotifications.length > 0 ? (
                recentNotifications.map(n => (
                  <div
                    key={n.id}
                    className={`p-3 rounded-xl transition-colors ${!n.is_read ? 'bg-[rgba(91,138,114,0.06)]' : 'bg-[#FAFBF9]'}`}
                  >
                    <div className="flex items-start gap-2">
                      <span
                        className="w-2 h-2 rounded-full mt-1.5 flex-shrink-0"
                        style={{ backgroundColor: getNotificationTypeColor(n.notification_type) }}
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-[#3D4A44] truncate">{n.title}</p>
                        <p className="text-xs text-[#7A8580] mt-0.5 line-clamp-1">{n.message}</p>
                        <p className="text-xs text-[#A0A5A2] mt-1">{getTimeAgo(n.created_at)}</p>
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center py-8">
                  <BellIcon className="w-12 h-12 mx-auto text-[#D1D5DB] mb-3" />
                  <p className="text-[#7A8580]">No notifications yet</p>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6">
          <div className="flex justify-between items-center mb-5">
            <h2 className="text-[22px] font-medium text-[#3D4A44]">Top Creators</h2>
            <Link to="/roster" className="text-[15px] text-[#5B8A72] hover:underline font-medium">
              View All →
            </Link>
          </div>
          
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
        </div>
      </div>
    </div>
  )
}
