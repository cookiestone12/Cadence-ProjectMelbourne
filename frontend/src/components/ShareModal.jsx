import React, { useState, useEffect } from 'react'
import axios from 'axios'
import {
  XMarkIcon, PaperAirplaneIcon, UserGroupIcon,
  EnvelopeIcon, MagnifyingGlassIcon, CheckIcon
} from '@heroicons/react/24/outline'

export default function ShareModal({ itemType, itemId, itemIds, itemName, onClose, orgId }) {
  const [activeTab, setActiveTab] = useState('email')
  const [recipientEmails, setRecipientEmails] = useState('')
  const [message, setMessage] = useState('')
  const [sending, setSending] = useState(false)
  const [success, setSuccess] = useState(null)
  const [error, setError] = useState(null)

  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [selectedUsers, setSelectedUsers] = useState([])
  const [searching, setSearching] = useState(false)

  useEffect(() => {
    if (searchQuery.length < 2) {
      setSearchResults([])
      return
    }
    const timer = setTimeout(() => searchUsers(searchQuery), 300)
    return () => clearTimeout(timer)
  }, [searchQuery])

  async function searchUsers(q) {
    setSearching(true)
    try {
      const res = await axios.get(`/api/sharing/users/search?q=${encodeURIComponent(q)}`)
      setSearchResults(res.data || [])
    } catch (err) {
      console.error('User search failed:', err)
    } finally {
      setSearching(false)
    }
  }

  function toggleUser(user) {
    setSelectedUsers(prev => {
      const exists = prev.find(u => u.id === user.id)
      if (exists) return prev.filter(u => u.id !== user.id)
      return [...prev, user]
    })
  }

  const allItemIds = itemIds || [itemId]

  async function handleEmailShare() {
    const emails = recipientEmails.split(/[,;\s]+/).filter(e => e.includes('@'))
    if (emails.length === 0) {
      setError('Please enter at least one valid email address')
      return
    }
    setSending(true)
    setError(null)
    try {
      for (const id of allItemIds) {
        await axios.post('/api/sharing/email', {
          item_type: itemType,
          item_id: id,
          item_name: itemName,
          recipient_emails: emails,
          message,
        })
      }
      setSuccess(`Shared via email to ${emails.length} recipient${emails.length > 1 ? 's' : ''}`)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to send')
    } finally {
      setSending(false)
    }
  }

  async function handleAccountShare() {
    if (selectedUsers.length === 0) {
      setError('Please select at least one user')
      return
    }
    setSending(true)
    setError(null)
    try {
      for (const id of allItemIds) {
        await axios.post('/api/sharing/account', {
          item_type: itemType,
          item_id: id,
          item_name: itemName,
          recipient_user_ids: selectedUsers.map(u => u.id),
          message,
        })
      }
      setSuccess(`Shared with ${selectedUsers.length} account${selectedUsers.length > 1 ? 's' : ''}`)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to share')
    } finally {
      setSending(false)
    }
  }

  const typeLabels = {
    DOCUMENT: 'Document',
    AUDIO: 'Audio File',
    STATEMENT: 'Statement',
    CONTACT_CARD: 'Contact Card',
  }

  return (
    <div className="fixed inset-0 bg-black/20 backdrop-blur-sm z-[60] flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-[0_25px_60px_rgba(0,0,0,0.15)] w-full max-w-lg" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-[rgba(59,77,67,0.08)]">
          <div>
            <h3 className="text-lg font-semibold text-[#3D4A44]">Share {typeLabels[itemType] || 'Item'}</h3>
            <p className="text-sm text-[#7A8580] mt-0.5 truncate max-w-[300px]">{itemName}</p>
          </div>
          <button onClick={onClose} className="text-[#7A8580] hover:text-[#3D4A44] transition-colors">
            <XMarkIcon className="w-6 h-6" />
          </button>
        </div>

        {success ? (
          <div className="px-6 py-12 text-center">
            <div className="w-16 h-16 bg-[rgba(91,138,114,0.1)] rounded-full flex items-center justify-center mx-auto mb-4">
              <CheckIcon className="w-8 h-8 text-[#5B8A72]" />
            </div>
            <p className="text-lg font-medium text-[#3D4A44]">{success}</p>
            <button
              onClick={onClose}
              className="mt-6 px-6 py-2.5 bg-[#5B8A72] text-white rounded-xl font-medium hover:bg-[#4A7862] transition-colors"
            >
              Done
            </button>
          </div>
        ) : (
          <>
            <div className="flex border-b border-[rgba(59,77,67,0.08)]">
              <button
                onClick={() => { setActiveTab('email'); setError(null) }}
                className={`flex-1 flex items-center justify-center gap-2 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === 'email'
                    ? 'border-[#5B8A72] text-[#5B8A72]'
                    : 'border-transparent text-[#7A8580] hover:text-[#3D4A44]'
                }`}
              >
                <EnvelopeIcon className="w-4 h-4" />
                Email
              </button>
              <button
                onClick={() => { setActiveTab('account'); setError(null) }}
                className={`flex-1 flex items-center justify-center gap-2 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === 'account'
                    ? 'border-[#5B8A72] text-[#5B8A72]'
                    : 'border-transparent text-[#7A8580] hover:text-[#3D4A44]'
                }`}
              >
                <UserGroupIcon className="w-4 h-4" />
                Account
              </button>
            </div>

            <div className="px-6 py-5 space-y-4">
              {activeTab === 'email' ? (
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1.5">Recipient Emails</label>
                  <textarea
                    value={recipientEmails}
                    onChange={e => setRecipientEmails(e.target.value)}
                    placeholder="Enter email addresses (comma separated)"
                    rows={2}
                    className="w-full px-4 py-2.5 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm focus:outline-none focus:border-[#5B8A72] focus:ring-2 focus:ring-[rgba(91,138,114,0.15)] resize-none"
                  />
                </div>
              ) : (
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1.5">Search Users</label>
                  <div className="relative">
                    <MagnifyingGlassIcon className="w-4 h-4 text-[#9CA8A3] absolute left-3 top-1/2 -translate-y-1/2" />
                    <input
                      value={searchQuery}
                      onChange={e => setSearchQuery(e.target.value)}
                      placeholder="Search by name or email..."
                      className="w-full pl-10 pr-4 py-2.5 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm focus:outline-none focus:border-[#5B8A72] focus:ring-2 focus:ring-[rgba(91,138,114,0.15)]"
                    />
                  </div>
                  {searching && <p className="text-xs text-[#7A8580] mt-1">Searching...</p>}
                  {searchResults.length > 0 && (
                    <div className="mt-2 max-h-40 overflow-y-auto border border-[rgba(59,77,67,0.1)] rounded-xl">
                      {searchResults.map(user => {
                        const isSelected = selectedUsers.some(u => u.id === user.id)
                        return (
                          <button
                            key={user.id}
                            onClick={() => toggleUser(user)}
                            className={`w-full text-left px-4 py-2.5 flex items-center justify-between hover:bg-[#F8F8FB] transition-colors border-b border-[rgba(59,77,67,0.05)] last:border-0 ${
                              isSelected ? 'bg-[rgba(91,138,114,0.06)]' : ''
                            }`}
                          >
                            <div>
                              <p className="text-sm font-medium text-[#3D4A44]">{user.username}</p>
                              <p className="text-xs text-[#7A8580]">{user.email}{user.organization_name ? ` · ${user.organization_name}` : ''}</p>
                            </div>
                            {isSelected && <CheckIcon className="w-4 h-4 text-[#5B8A72]" />}
                          </button>
                        )
                      })}
                    </div>
                  )}
                  {selectedUsers.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {selectedUsers.map(user => (
                        <span key={user.id} className="inline-flex items-center gap-1.5 px-3 py-1 bg-[rgba(91,138,114,0.1)] text-[#5B8A72] rounded-full text-xs font-medium">
                          {user.username}
                          <button onClick={() => toggleUser(user)} className="hover:text-[#C47068]">
                            <XMarkIcon className="w-3 h-3" />
                          </button>
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1.5">Message (optional)</label>
                <textarea
                  value={message}
                  onChange={e => setMessage(e.target.value)}
                  placeholder="Add a note..."
                  rows={2}
                  className="w-full px-4 py-2.5 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm focus:outline-none focus:border-[#5B8A72] focus:ring-2 focus:ring-[rgba(91,138,114,0.15)] resize-none"
                />
              </div>

              {error && (
                <p className="text-sm text-[#C47068] bg-red-50 px-3 py-2 rounded-lg">{error}</p>
              )}
            </div>

            <div className="px-6 py-4 border-t border-[rgba(59,77,67,0.08)] flex justify-end gap-3">
              <button
                onClick={onClose}
                className="px-5 py-2.5 text-[#7A8580] hover:text-[#3D4A44] font-medium text-sm transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={activeTab === 'email' ? handleEmailShare : handleAccountShare}
                disabled={sending}
                className="flex items-center gap-2 px-5 py-2.5 bg-[#5B8A72] text-white rounded-xl font-medium text-sm hover:bg-[#4A7862] transition-colors disabled:opacity-50"
              >
                <PaperAirplaneIcon className="w-4 h-4" />
                {sending ? 'Sharing...' : activeTab === 'email' ? 'Send Email' : 'Share'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
