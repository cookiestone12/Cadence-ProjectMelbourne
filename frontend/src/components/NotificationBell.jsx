import React, { useState, useEffect, useRef, useCallback } from 'react'
import axios from 'axios'
import { BellIcon, CheckIcon, TrashIcon } from '@heroicons/react/24/outline'
import { BellAlertIcon } from '@heroicons/react/24/solid'

function requestDesktopNotificationPermission() {
  if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission()
  }
}

function sendDesktopNotification(title, body, onClick) {
  if ('Notification' in window && Notification.permission === 'granted') {
    try {
      const notification = new Notification(title, {
        body: body || '',
        icon: '/favicon-192.png',
        badge: '/favicon-192.png',
        tag: 'rythm-notification-' + Date.now(),
        requireInteraction: false,
      })
      if (onClick) {
        notification.onclick = () => {
          window.focus()
          onClick()
          notification.close()
        }
      }
      setTimeout(() => notification.close(), 8000)
    } catch (e) {
      // Silent fail for environments that don't support Notification constructor
    }
  }
}

export default function NotificationBell() {
  const [isOpen, setIsOpen] = useState(false)
  const [notifications, setNotifications] = useState([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [loading, setLoading] = useState(false)
  const dropdownRef = useRef(null)
  const prevUnreadCountRef = useRef(-1)
  const initialLoadRef = useRef(true)

  const fetchUnreadCount = useCallback(async () => {
    try {
      const res = await axios.get('/api/notifications/unread-count')
      const newCount = res.data.unread_count
      const prevCount = prevUnreadCountRef.current

      if (!initialLoadRef.current && newCount > prevCount && prevCount >= 0) {
        try {
          const notifRes = await axios.get('/api/notifications?limit=5&unread=true')
          const newNotifs = notifRes.data || []
          if (newNotifs.length > 0) {
            const latest = newNotifs[0]
            sendDesktopNotification(
              latest.title || 'Rythm — New Notification',
              latest.message || `You have ${newCount - prevCount} new notification${(newCount - prevCount) > 1 ? 's' : ''}`,
              () => window.location.href = '/actions'
            )
          }
        } catch {
          sendDesktopNotification(
            'Rythm — New Notification',
            `You have ${newCount - prevCount} new notification${(newCount - prevCount) > 1 ? 's' : ''}`,
            () => window.location.href = '/actions'
          )
        }
      }

      initialLoadRef.current = false
      prevUnreadCountRef.current = newCount
      setUnreadCount(newCount)
    } catch (err) {
      console.error('Failed to fetch unread count:', err)
    }
  }, [])

  useEffect(() => {
    fetchUnreadCount()
    const interval = setInterval(fetchUnreadCount, 30000)
    return () => clearInterval(interval)
  }, [fetchUnreadCount])

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const fetchNotifications = async () => {
    setLoading(true)
    try {
      const res = await axios.get('/api/notifications?limit=10')
      setNotifications(res.data)
    } catch (err) {
      console.error('Failed to fetch notifications:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleOpen = () => {
    setIsOpen(!isOpen)
    if (!isOpen) {
      fetchNotifications()
    }
  }

  const markAsRead = async (id) => {
    try {
      await axios.put(`/api/notifications/${id}/read`)
      setNotifications(prev => prev.map(n => 
        n.id === id ? { ...n, is_read: true } : n
      ))
      setUnreadCount(prev => Math.max(0, prev - 1))
    } catch (err) {
      console.error('Failed to mark as read:', err)
    }
  }

  const markAllAsRead = async () => {
    try {
      await axios.put('/api/notifications/read-all')
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })))
      setUnreadCount(0)
    } catch (err) {
      console.error('Failed to mark all as read:', err)
    }
  }

  const deleteNotification = async (id) => {
    try {
      await axios.delete(`/api/notifications/${id}`)
      setNotifications(prev => prev.filter(n => n.id !== id))
      const wasUnread = notifications.find(n => n.id === id && !n.is_read)
      if (wasUnread) {
        setUnreadCount(prev => Math.max(0, prev - 1))
      }
    } catch (err) {
      console.error('Failed to delete notification:', err)
    }
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

  const getTypeColor = (type) => {
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

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={handleOpen}
        className="relative p-2 rounded-lg text-[#7A8580] hover:bg-[#EEF1EC] hover:text-[#3D4A44] transition-colors"
      >
        {unreadCount > 0 ? (
          <BellAlertIcon className="w-5 h-5 text-[#5B8A72]" />
        ) : (
          <BellIcon className="w-5 h-5" />
        )}
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 w-5 h-5 bg-[#C47068] text-white text-[10px] font-bold rounded-full flex items-center justify-center">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 bg-white rounded-xl shadow-lg border border-[rgba(59,77,67,0.08)] z-50 overflow-hidden">
          <div className="flex items-center justify-between p-4 border-b border-[rgba(59,77,67,0.08)]">
            <h3 className="font-semibold text-[#3D4A44]">Notifications</h3>
            {unreadCount > 0 && (
              <button
                onClick={markAllAsRead}
                className="text-xs text-[#5B8A72] hover:text-[#4A7A62] font-medium"
              >
                Mark all read
              </button>
            )}
          </div>

          <div className="max-h-96 overflow-y-auto">
            {loading ? (
              <div className="p-8 text-center text-[#7A8580]">Loading...</div>
            ) : notifications.length === 0 ? (
              <div className="p-8 text-center">
                <BellIcon className="w-12 h-12 mx-auto text-[#D1D5DB] mb-3" />
                <p className="text-[#7A8580]">No notifications yet</p>
              </div>
            ) : (
              notifications.map(notification => (
                <div
                  key={notification.id}
                  className={`p-4 border-b border-[rgba(59,77,67,0.04)] hover:bg-[#FAFBF9] transition-colors ${
                    !notification.is_read ? 'bg-[rgba(91,138,114,0.04)]' : ''
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2">
                        <span 
                          className="w-2 h-2 rounded-full flex-shrink-0"
                          style={{ backgroundColor: getTypeColor(notification.notification_type) }}
                        />
                        <span className="text-sm font-medium text-[#3D4A44] truncate">
                          {notification.title}
                        </span>
                      </div>
                      <p className="text-xs text-[#7A8580] mt-1 line-clamp-2">
                        {notification.message}
                      </p>
                      <p className="text-xs text-[#A0A5A2] mt-2">
                        {getTimeAgo(notification.created_at)}
                      </p>
                    </div>
                    
                    <div className="flex items-center space-x-1 ml-2">
                      {!notification.is_read && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            markAsRead(notification.id)
                          }}
                          className="p-1 text-[#5B8A72] hover:bg-[#EEF1EC] rounded"
                          title="Mark as read"
                        >
                          <CheckIcon className="w-4 h-4" />
                        </button>
                      )}
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          deleteNotification(notification.id)
                        }}
                        className="p-1 text-[#C47068] hover:bg-[rgba(196,112,104,0.1)] rounded"
                        title="Delete"
                      >
                        <TrashIcon className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>

          {notifications.length > 0 && (
            <div className="p-3 border-t border-[rgba(59,77,67,0.08)] bg-[#FAFBF9]">
              <a
                href="/settings"
                className="block text-center text-xs text-[#5B8A72] hover:text-[#4A7A62] font-medium"
                onClick={() => setIsOpen(false)}
              >
                Manage notification preferences
              </a>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
