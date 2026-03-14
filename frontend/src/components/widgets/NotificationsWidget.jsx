import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { BellIcon } from '@heroicons/react/24/outline'
import axios from 'axios'

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

export default function NotificationsWidget() {
  const [recentNotifications, setRecentNotifications] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    axios.get('/api/notifications?limit=5')
      .then(res => setRecentNotifications(res.data))
      .catch(e => console.error('Notifications: load failed:', e))
      .finally(() => setLoading(false))
  }, [])

  return (
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

      {loading ? (
        <div className="space-y-2">
          {[1,2,3].map(i => (
            <div key={i} className="p-3 rounded-xl bg-[#FAFBF9] animate-pulse">
              <div className="h-4 bg-[#D1D5DB] rounded w-3/4 mb-2"></div>
              <div className="h-3 bg-[#D1D5DB] rounded w-1/2"></div>
            </div>
          ))}
        </div>
      ) : (
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
      )}
    </div>
  )
}
