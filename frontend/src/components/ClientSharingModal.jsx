import React, { useState, useEffect, useCallback } from 'react'
import axios from 'axios'
import {
  ShareIcon,
  ClipboardIcon,
  CheckIcon,
  XMarkIcon,
  ArrowPathIcon,
  PaperAirplaneIcon,
  InboxArrowDownIcon,
  LinkIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline'

const ROLE_LABELS = {
  COPRIMARY: 'Co-Primary',
  SECONDARY: 'Secondary',
  READER: 'Reader',
}

const ROLE_DESCRIPTIONS = {
  COPRIMARY: 'Full management access, can grant further access',
  SECONDARY: 'Can make changes to catalog but cannot grant access',
  READER: 'View-only access to the catalog',
}

const ROLE_COLORS = {
  COPRIMARY: 'bg-purple-100 text-purple-700',
  SECONDARY: 'bg-blue-100 text-blue-700',
  READER: 'bg-gray-100 text-gray-600',
}

const STATUS_COLORS = {
  PENDING: 'bg-yellow-100 text-yellow-700',
  ACCEPTED: 'bg-green-100 text-green-700',
  REJECTED: 'bg-red-100 text-red-700',
  REVOKED: 'bg-gray-100 text-gray-500',
}

function generatePasscode() {
  return String(Math.floor(100000 + Math.random() * 900000))
}

export default function ClientSharingTab() {
  const [activeSubTab, setActiveSubTab] = useState('share')
  const [creators, setCreators] = useState([])
  const [sentShares, setSentShares] = useState([])
  const [receivedShares, setReceivedShares] = useState([])
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState(null)
  const [error, setError] = useState(null)

  const showMsg = (text, isError = false) => {
    if (isError) setError(text)
    else setMessage(text)
    setTimeout(() => { setError(null); setMessage(null) }, 4000)
  }

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const [creatorsRes, sentRes, receivedRes] = await Promise.all([
        axios.get('/api/tenant-admin/creators').catch(() => ({ data: [] })),
        axios.get('/api/client-sharing/sent').catch(() => ({ data: [] })),
        axios.get('/api/client-sharing/received').catch(() => ({ data: [] })),
      ])
      setCreators(creatorsRes.data)
      setSentShares(sentRes.data)
      setReceivedShares(receivedRes.data)
    } catch (err) {
      showMsg('Failed to load sharing data', true)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  const subTabs = [
    { id: 'share', label: 'Share Client', icon: PaperAirplaneIcon },
    { id: 'received', label: `Received (${receivedShares.length})`, icon: InboxArrowDownIcon },
    { id: 'active', label: 'Active Shares', icon: LinkIcon },
  ]

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[300px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#5B8A72]" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {(message || error) && (
        <div className={`p-3 rounded-lg flex items-center gap-2 ${error ? 'bg-red-50 text-red-700' : 'bg-green-50 text-green-700'}`}>
          {error ? <ExclamationTriangleIcon className="w-5 h-5" /> : <CheckCircleIcon className="w-5 h-5" />}
          <span className="text-sm">{message || error}</span>
        </div>
      )}

      <div className="flex gap-2 border-b border-[#E5E8E3]">
        {subTabs.map(tab => {
          const Icon = tab.icon
          return (
            <button
              key={tab.id}
              onClick={() => setActiveSubTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                activeSubTab === tab.id
                  ? 'border-[#5B8A72] text-[#5B8A72]'
                  : 'border-transparent text-[#7A8580] hover:text-[#3D4A44]'
              }`}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
            </button>
          )
        })}
      </div>

      {activeSubTab === 'share' && (
        <ShareForm creators={creators} onSuccess={() => { fetchData(); showMsg('Share invitation sent!') }} onError={(e) => showMsg(e, true)} />
      )}

      {activeSubTab === 'received' && (
        <ReceivedShares shares={receivedShares} onAction={() => { fetchData(); showMsg('Action completed') }} onError={(e) => showMsg(e, true)} />
      )}

      {activeSubTab === 'active' && (
        <ActiveShares shares={sentShares} onAction={() => { fetchData(); showMsg('Updated successfully') }} onError={(e) => showMsg(e, true)} />
      )}
    </div>
  )
}

function ShareForm({ creators, onSuccess, onError }) {
  const [form, setForm] = useState({
    creator_id: '',
    recipient_email: '',
    recipient_org_name: '',
    role: 'READER',
    passcode: generatePasscode(),
  })
  const [sending, setSending] = useState(false)
  const [copied, setCopied] = useState(false)

  const handleCopyPasscode = () => {
    navigator.clipboard.writeText(form.passcode)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleRegeneratePasscode = () => {
    setForm({ ...form, passcode: generatePasscode() })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.creator_id) { onError('Please select a creator'); return }
    if (!form.recipient_email) { onError('Please enter recipient email'); return }
    if (!form.recipient_org_name) { onError('Please enter recipient organization name'); return }

    setSending(true)
    try {
      await axios.post('/api/client-sharing/share', form)
      onSuccess()
      setForm({
        creator_id: '',
        recipient_email: '',
        recipient_org_name: '',
        role: 'READER',
        passcode: generatePasscode(),
      })
    } catch (err) {
      onError(err.response?.data?.detail || 'Failed to send share invitation')
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="bg-white rounded-xl shadow-sm p-6">
      <h3 className="text-lg font-semibold text-[#3D4A44] mb-1">Share a Client</h3>
      <p className="text-sm text-[#7A8580] mb-6">Grant another organization access to one of your clients</p>

      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div>
            <label className="block text-sm font-medium text-[#3D4A44] mb-1">Creator / Client</label>
            <select
              value={form.creator_id}
              onChange={(e) => setForm({ ...form, creator_id: e.target.value })}
              className="w-full px-3 py-2 border border-[#D1D5CE] rounded-lg text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
              required
            >
              <option value="">Select a creator...</option>
              {creators.map(c => (
                <option key={c.id} value={c.id}>{c.name || c.display_name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-[#3D4A44] mb-1">Recipient Email</label>
            <input
              type="email"
              value={form.recipient_email}
              onChange={(e) => setForm({ ...form, recipient_email: e.target.value })}
              className="w-full px-3 py-2 border border-[#D1D5CE] rounded-lg text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
              placeholder="user@organization.com"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-[#3D4A44] mb-1">Recipient Organization Name</label>
            <input
              type="text"
              value={form.recipient_org_name}
              onChange={(e) => setForm({ ...form, recipient_org_name: e.target.value })}
              className="w-full px-3 py-2 border border-[#D1D5CE] rounded-lg text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
              placeholder="Their organization name (for verification)"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-[#3D4A44] mb-1">Access Role</label>
            <select
              value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value })}
              className="w-full px-3 py-2 border border-[#D1D5CE] rounded-lg text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
            >
              {Object.entries(ROLE_LABELS).map(([key, label]) => (
                <option key={key} value={key}>{label}</option>
              ))}
            </select>
            <p className="text-xs text-[#7A8580] mt-1">{ROLE_DESCRIPTIONS[form.role]}</p>
          </div>
        </div>

        <div className="bg-[#F5F7F4] rounded-lg p-4">
          <label className="block text-sm font-medium text-[#3D4A44] mb-2">Security Passcode</label>
          <div className="flex items-center gap-3">
            <div className="flex-1 flex items-center gap-2 bg-white border-2 border-dashed border-[#5B8A72] rounded-lg px-4 py-3">
              <span className="text-2xl font-mono font-bold text-[#3D4A44] tracking-[0.3em] select-all">{form.passcode}</span>
            </div>
            <button
              type="button"
              onClick={handleCopyPasscode}
              className="flex items-center gap-1.5 px-3 py-2.5 bg-white border border-[#D1D5CE] rounded-lg text-sm text-[#3D4A44] hover:bg-[#EEF1EC] transition-colors"
            >
              {copied ? <CheckIcon className="w-4 h-4 text-green-600" /> : <ClipboardIcon className="w-4 h-4" />}
              {copied ? 'Copied!' : 'Copy'}
            </button>
            <button
              type="button"
              onClick={handleRegeneratePasscode}
              className="p-2.5 bg-white border border-[#D1D5CE] rounded-lg text-[#7A8580] hover:text-[#5B8A72] hover:bg-[#EEF1EC] transition-colors"
              title="Generate new passcode"
            >
              <ArrowPathIcon className="w-4 h-4" />
            </button>
          </div>
          <p className="text-xs text-[#7A8580] mt-2 flex items-center gap-1">
            <ExclamationTriangleIcon className="w-3.5 h-3.5" />
            Share this passcode separately with the recipient (e.g., via phone, text, or secure message)
          </p>
        </div>

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={sending}
            className="flex items-center gap-2 px-5 py-2.5 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] disabled:opacity-50 text-sm font-medium transition-colors"
          >
            <ShareIcon className="w-4 h-4" />
            {sending ? 'Sending...' : 'Share Client'}
          </button>
        </div>
      </form>
    </div>
  )
}

function ReceivedShares({ shares, onAction, onError }) {
  const [acceptingId, setAcceptingId] = useState(null)
  const [acceptForm, setAcceptForm] = useState({ passcode: '', org_name: '' })
  const [processing, setProcessing] = useState(false)

  const handleAccept = async (shareId) => {
    if (!acceptForm.passcode || !acceptForm.org_name) {
      onError('Please enter both passcode and organization name')
      return
    }
    setProcessing(true)
    try {
      await axios.post(`/api/client-sharing/accept/${shareId}`, acceptForm)
      setAcceptingId(null)
      setAcceptForm({ passcode: '', org_name: '' })
      onAction()
    } catch (err) {
      onError(err.response?.data?.detail || 'Failed to accept share')
    } finally {
      setProcessing(false)
    }
  }

  const handleReject = async (shareId) => {
    if (!confirm('Are you sure you want to reject this invitation?')) return
    setProcessing(true)
    try {
      await axios.post(`/api/client-sharing/reject/${shareId}`)
      onAction()
    } catch (err) {
      onError(err.response?.data?.detail || 'Failed to reject share')
    } finally {
      setProcessing(false)
    }
  }

  if (shares.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-sm p-8 text-center">
        <InboxArrowDownIcon className="w-12 h-12 mx-auto mb-3 text-[#7A8580] opacity-40" />
        <p className="text-sm text-[#7A8580]">No pending invitations</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {shares.map(share => (
        <div key={share.id} className="bg-white rounded-xl shadow-sm p-5">
          <div className="flex items-start justify-between">
            <div>
              <h4 className="text-sm font-semibold text-[#3D4A44]">{share.creator_name}</h4>
              <p className="text-xs text-[#7A8580] mt-0.5">
                Shared by <span className="font-medium">{share.shared_by_username}</span> from <span className="font-medium">{share.primary_org_name}</span>
              </p>
              <div className="flex items-center gap-2 mt-2">
                <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${ROLE_COLORS[share.role]}`}>
                  {ROLE_LABELS[share.role] || share.role}
                </span>
                <span className="text-xs text-[#A0A8A3]">
                  {share.created_at ? new Date(share.created_at).toLocaleDateString() : ''}
                </span>
              </div>
            </div>

            {acceptingId !== share.id && (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => { setAcceptingId(share.id); setAcceptForm({ passcode: '', org_name: '' }) }}
                  className="px-3 py-1.5 bg-[#5B8A72] text-white rounded-lg text-xs font-medium hover:bg-[#4A7A62] transition-colors"
                >
                  Accept
                </button>
                <button
                  onClick={() => handleReject(share.id)}
                  disabled={processing}
                  className="px-3 py-1.5 border border-red-300 text-red-600 rounded-lg text-xs font-medium hover:bg-red-50 transition-colors"
                >
                  Reject
                </button>
              </div>
            )}
          </div>

          {acceptingId === share.id && (
            <div className="mt-4 p-4 bg-[#F5F7F4] rounded-lg space-y-3">
              <p className="text-xs font-medium text-[#3D4A44]">Enter the passcode and confirm your organization name</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <input
                  type="text"
                  maxLength={6}
                  value={acceptForm.passcode}
                  onChange={(e) => setAcceptForm({ ...acceptForm, passcode: e.target.value.replace(/\D/g, '').slice(0, 6) })}
                  className="px-3 py-2 border border-[#D1D5CE] rounded-lg text-sm font-mono tracking-wider focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                  placeholder="6-digit passcode"
                />
                <input
                  type="text"
                  value={acceptForm.org_name}
                  onChange={(e) => setAcceptForm({ ...acceptForm, org_name: e.target.value })}
                  className="px-3 py-2 border border-[#D1D5CE] rounded-lg text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                  placeholder="Your organization name"
                />
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleAccept(share.id)}
                  disabled={processing}
                  className="px-3 py-1.5 bg-[#5B8A72] text-white rounded-lg text-xs font-medium hover:bg-[#4A7A62] disabled:opacity-50 transition-colors"
                >
                  {processing ? 'Accepting...' : 'Confirm Accept'}
                </button>
                <button
                  onClick={() => setAcceptingId(null)}
                  className="px-3 py-1.5 text-[#7A8580] hover:bg-white rounded-lg text-xs transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

function ActiveShares({ shares, onAction, onError }) {
  const [processing, setProcessing] = useState(false)

  const acceptedShares = shares.filter(s => s.status === 'ACCEPTED')
  const otherShares = shares.filter(s => s.status !== 'ACCEPTED')

  const handleRevoke = async (shareId) => {
    if (!confirm('Are you sure you want to revoke this share? The recipient will lose access.')) return
    setProcessing(true)
    try {
      await axios.post(`/api/client-sharing/revoke/${shareId}`)
      onAction()
    } catch (err) {
      onError(err.response?.data?.detail || 'Failed to revoke share')
    } finally {
      setProcessing(false)
    }
  }

  const handleRoleChange = async (shareId, newRole) => {
    setProcessing(true)
    try {
      await axios.put(`/api/client-sharing/${shareId}/role`, { role: newRole })
      onAction()
    } catch (err) {
      onError(err.response?.data?.detail || 'Failed to update role')
    } finally {
      setProcessing(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-sm font-semibold text-[#3D4A44] mb-3">Active Shares ({acceptedShares.length})</h3>
        {acceptedShares.length === 0 ? (
          <div className="bg-white rounded-xl shadow-sm p-8 text-center">
            <LinkIcon className="w-12 h-12 mx-auto mb-3 text-[#7A8580] opacity-40" />
            <p className="text-sm text-[#7A8580]">No active shares</p>
          </div>
        ) : (
          <div className="bg-white rounded-xl shadow-sm overflow-hidden">
            <table className="w-full">
              <thead className="bg-[#F5F7F4]">
                <tr>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-[#7A8580] uppercase tracking-wider">Creator</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-[#7A8580] uppercase tracking-wider">Shared With</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-[#7A8580] uppercase tracking-wider">Role</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-[#7A8580] uppercase tracking-wider hidden md:table-cell">Accepted</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-[#7A8580] uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E5E8E3]">
                {acceptedShares.map(share => (
                  <tr key={share.id} className="hover:bg-[#FAFBF9] transition-colors">
                    <td className="px-4 py-3">
                      <p className="text-sm font-medium text-[#3D4A44]">{share.creator_name}</p>
                    </td>
                    <td className="px-4 py-3">
                      <p className="text-sm text-[#3D4A44]">{share.recipient_org_name || share.recipient_user_email}</p>
                      <p className="text-xs text-[#7A8580]">{share.recipient_user_email}</p>
                    </td>
                    <td className="px-4 py-3">
                      <select
                        value={share.role}
                        onChange={(e) => handleRoleChange(share.id, e.target.value)}
                        disabled={processing}
                        className="px-2 py-1 text-xs border border-[#D1D5CE] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                      >
                        {Object.entries(ROLE_LABELS).map(([key, label]) => (
                          <option key={key} value={key}>{label}</option>
                        ))}
                      </select>
                    </td>
                    <td className="px-4 py-3 hidden md:table-cell">
                      <span className="text-xs text-[#7A8580]">
                        {share.accepted_at ? new Date(share.accepted_at).toLocaleDateString() : '—'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => handleRevoke(share.id)}
                        disabled={processing}
                        className="px-3 py-1.5 border border-red-300 text-red-600 rounded-lg text-xs font-medium hover:bg-red-50 disabled:opacity-50 transition-colors"
                      >
                        Revoke
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {otherShares.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-[#3D4A44] mb-3">Other Shares ({otherShares.length})</h3>
          <div className="bg-white rounded-xl shadow-sm overflow-hidden">
            <table className="w-full">
              <thead className="bg-[#F5F7F4]">
                <tr>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-[#7A8580] uppercase tracking-wider">Creator</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-[#7A8580] uppercase tracking-wider">Recipient</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-[#7A8580] uppercase tracking-wider">Status</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-[#7A8580] uppercase tracking-wider hidden md:table-cell">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E5E8E3]">
                {otherShares.map(share => (
                  <tr key={share.id} className="hover:bg-[#FAFBF9] transition-colors">
                    <td className="px-4 py-3">
                      <p className="text-sm font-medium text-[#3D4A44]">{share.creator_name}</p>
                    </td>
                    <td className="px-4 py-3">
                      <p className="text-sm text-[#3D4A44]">{share.recipient_user_email}</p>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${STATUS_COLORS[share.status]}`}>
                        {share.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 hidden md:table-cell">
                      <span className="text-xs text-[#7A8580]">
                        {share.created_at ? new Date(share.created_at).toLocaleDateString() : '—'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
