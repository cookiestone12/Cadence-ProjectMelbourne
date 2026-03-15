import React, { useState, useEffect } from 'react'
import axios from 'axios'
import {
  ShareIcon, DocumentTextIcon, MusicalNoteIcon,
  BanknotesIcon, UserGroupIcon, ClockIcon, XMarkIcon
} from '@heroicons/react/24/outline'

export default function SharedWithMePage() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('received')
  const [sentItems, setSentItems] = useState([])

  useEffect(() => {
    loadItems()
  }, [])

  async function loadItems() {
    setLoading(true)
    try {
      const [received, sent] = await Promise.all([
        axios.get('/api/sharing/shared-with-me'),
        axios.get('/api/sharing/shared-by-me'),
      ])
      setItems(received.data || [])
      setSentItems(sent.data || [])
    } catch (error) {
      console.error('Failed to load shared items:', error)
    } finally {
      setLoading(false)
    }
  }

  async function handleRevoke(shareId) {
    if (!confirm('Revoke this share?')) return
    try {
      await axios.post(`/api/sharing/${shareId}/revoke`)
      setSentItems(prev => prev.map(i => i.id === shareId ? { ...i, status: 'REVOKED' } : i))
    } catch (error) {
      console.error('Failed to revoke:', error)
      alert('Failed to revoke share')
    }
  }

  const typeIcons = {
    DOCUMENT: DocumentTextIcon,
    AUDIO: MusicalNoteIcon,
    STATEMENT: BanknotesIcon,
    CONTACT_CARD: UserGroupIcon,
  }
  const typeLabels = {
    DOCUMENT: 'Document',
    AUDIO: 'Audio File',
    STATEMENT: 'Statement',
    CONTACT_CARD: 'Contact Card',
  }
  const typeColors = {
    DOCUMENT: 'bg-blue-50 text-blue-600',
    AUDIO: 'bg-purple-50 text-purple-600',
    STATEMENT: 'bg-amber-50 text-amber-600',
    CONTACT_CARD: 'bg-teal-50 text-teal-600',
  }

  function formatDate(dateStr) {
    if (!dateStr) return ''
    const d = new Date(dateStr)
    const now = new Date()
    const diff = now - d
    if (diff < 60000) return 'Just now'
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`
    if (diff < 604800000) return `${Math.floor(diff / 86400000)}d ago`
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  }

  const displayItems = activeTab === 'received' ? items : sentItems

  return (
    <div className="min-h-screen bg-[#F5F5F0]">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 bg-[rgba(91,138,114,0.1)] rounded-xl flex items-center justify-center">
            <ShareIcon className="w-5 h-5 text-[#5B8A72]" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-[#3D4A44]">Shared With Me</h1>
            <p className="text-sm text-[#7A8580]">Documents and contacts shared with you</p>
          </div>
        </div>

        <div className="flex gap-2 mb-6">
          <button
            onClick={() => setActiveTab('received')}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
              activeTab === 'received'
                ? 'bg-[#5B8A72] text-white'
                : 'bg-white text-[#7A8580] hover:bg-[#F8F8FB]'
            }`}
          >
            Received ({items.length})
          </button>
          <button
            onClick={() => setActiveTab('sent')}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
              activeTab === 'sent'
                ? 'bg-[#5B8A72] text-white'
                : 'bg-white text-[#7A8580] hover:bg-[#F8F8FB]'
            }`}
          >
            Sent ({sentItems.length})
          </button>
        </div>

        {loading ? (
          <div className="text-center py-16">
            <div className="w-8 h-8 border-2 border-[#5B8A72] border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-sm text-[#7A8580] mt-3">Loading...</p>
          </div>
        ) : displayItems.length === 0 ? (
          <div className="bg-white rounded-2xl border border-[rgba(59,77,67,0.08)] p-12 text-center">
            <ShareIcon className="w-12 h-12 text-[#9CA8A3] mx-auto mb-4" />
            <p className="text-lg font-medium text-[#3D4A44]">
              {activeTab === 'received' ? 'Nothing shared with you yet' : 'You haven\'t shared anything yet'}
            </p>
            <p className="text-sm text-[#7A8580] mt-1">
              {activeTab === 'received' ? 'Shared documents and contacts will appear here' : 'Items you share will be tracked here'}
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {displayItems.map(item => {
              const Icon = typeIcons[item.item_type] || DocumentTextIcon
              const colorClass = typeColors[item.item_type] || 'bg-gray-50 text-gray-600'
              return (
                <div key={item.id} className="bg-white rounded-2xl border border-[rgba(59,77,67,0.08)] p-4 hover:shadow-sm transition-shadow">
                  <div className="flex items-start gap-4">
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${colorClass}`}>
                      <Icon className="w-5 h-5" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="text-sm font-semibold text-[#3D4A44] truncate">{item.item_name || 'Unnamed Item'}</h3>
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${colorClass}`}>
                          {typeLabels[item.item_type] || item.item_type}
                        </span>
                        {item.status === 'REVOKED' && (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-red-50 text-red-500">Revoked</span>
                        )}
                      </div>
                      <div className="flex items-center gap-3 text-xs text-[#7A8580]">
                        {activeTab === 'received' ? (
                          <>
                            <span>From: <strong className="text-[#3D4A44]">{item.shared_by?.username || 'Unknown'}</strong></span>
                            {item.shared_by_org && <span>· {item.shared_by_org}</span>}
                          </>
                        ) : (
                          <>
                            <span>To: <strong className="text-[#3D4A44]">
                              {item.shared_with?.username || item.shared_with?.email || 'Unknown'}
                            </strong></span>
                          </>
                        )}
                        <span className="flex items-center gap-1">
                          <ClockIcon className="w-3 h-3" />
                          {formatDate(item.created_at)}
                        </span>
                      </div>
                      {item.message && (
                        <p className="mt-2 text-xs text-[#7A8580] bg-[#F8F8FB] rounded-lg px-3 py-2 italic">
                          "{item.message}"
                        </p>
                      )}
                    </div>
                    {activeTab === 'sent' && item.status === 'ACTIVE' && (
                      <button
                        onClick={() => handleRevoke(item.id)}
                        className="text-xs text-[#C47068] hover:bg-red-50 px-3 py-1.5 rounded-lg transition-colors flex-shrink-0"
                      >
                        Revoke
                      </button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
