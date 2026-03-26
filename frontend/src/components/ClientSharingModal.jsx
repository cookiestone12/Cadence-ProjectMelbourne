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
  CANCELLED: 'bg-gray-100 text-gray-500',
}

function generatePasscode() {
  return String(Math.floor(100000 + Math.random() * 900000))
}

export default function ClientSharingTab() {
  const [activeSubTab, setActiveSubTab] = useState('share')
  const [creators, setCreators] = useState([])
  const [sentShares, setSentShares] = useState([])
  const [receivedShares, setReceivedShares] = useState([])
  const [receivedActiveShares, setReceivedActiveShares] = useState([])
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
      const [creatorsRes, sentRes, receivedRes, receivedActiveRes] = await Promise.all([
        axios.get('/api/tenant-admin/creators').catch(() => ({ data: [] })),
        axios.get('/api/client-sharing/sent').catch(() => ({ data: [] })),
        axios.get('/api/client-sharing/received').catch(() => ({ data: [] })),
        axios.get('/api/client-sharing/received-active').catch(() => ({ data: [] })),
      ])
      setCreators(creatorsRes.data)
      setSentShares(sentRes.data)
      setReceivedShares(receivedRes.data)
      setReceivedActiveShares(receivedActiveRes.data)
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
        <ActiveShares shares={sentShares} receivedActiveShares={receivedActiveShares} onAction={() => { fetchData(); showMsg('Updated successfully') }} onError={(e) => showMsg(e, true)} />
      )}
    </div>
  )
}

const SHARE_MODULES = [
  { key: 'catalog', label: 'Catalog', description: 'Songs, works, and releases' },
  { key: 'contracts', label: 'Contracts', description: 'Contracts, deals, and rights splits' },
  { key: 'placements', label: 'Placements', description: 'Sync placements and licensing' },
  { key: 'royalties', label: 'Royalties', description: 'Statements, transactions, and accounting' },
  { key: 'contacts', label: 'Contacts', description: 'Creative directory contacts' },
]

function ShareForm({ creators, onSuccess, onError }) {
  const [form, setForm] = useState({
    creator_id: '',
    recipient_email: '',
    recipient_org_name: '',
    role: 'READER',
    passcode: generatePasscode(),
    shared_modules: SHARE_MODULES.map(m => m.key),
  })
  const [sending, setSending] = useState(false)
  const [copied, setCopied] = useState(false)

  const toggleModule = (key) => {
    setForm(prev => {
      const current = prev.shared_modules || []
      const updated = current.includes(key)
        ? current.filter(m => m !== key)
        : [...current, key]
      return { ...prev, shared_modules: updated }
    })
  }

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
    if (!form.shared_modules || form.shared_modules.length === 0) { onError('Please select at least one section to share'); return }

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
        shared_modules: SHARE_MODULES.map(m => m.key),
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

        <div>
          <label className="block text-sm font-medium text-[#3D4A44] mb-2">Shared Access</label>
          <p className="text-xs text-[#7A8580] mb-3">Choose which sections the recipient can access</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
            {SHARE_MODULES.map(mod => {
              const isSelected = (form.shared_modules || []).includes(mod.key)
              return (
                <button
                  key={mod.key}
                  type="button"
                  onClick={() => toggleModule(mod.key)}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg border text-left transition-all ${
                    isSelected
                      ? 'border-[#5B8A72] bg-[rgba(91,138,114,0.06)]'
                      : 'border-[#D1D5CE] bg-white hover:border-[#7A8580]'
                  }`}
                >
                  <div className={`w-4 h-4 rounded border-2 flex items-center justify-center flex-shrink-0 ${
                    isSelected ? 'border-[#5B8A72] bg-[#5B8A72]' : 'border-[#D1D5CE]'
                  }`}>
                    {isSelected && <CheckIcon className="w-3 h-3 text-white" />}
                  </div>
                  <div>
                    <div className="text-sm font-medium text-[#3D4A44]">{mod.label}</div>
                    <div className="text-xs text-[#7A8580]">{mod.description}</div>
                  </div>
                </button>
              )
            })}
          </div>
          {(form.shared_modules || []).length === 0 && (
            <p className="text-xs text-red-500 mt-1">At least one section must be selected</p>
          )}
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

function ActiveShares({ shares, receivedActiveShares = [], onAction, onError }) {
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

  const handleCancel = async (shareId) => {
    if (!confirm('Cancel this share invitation?')) return
    setProcessing(true)
    try {
      await axios.post(`/api/client-sharing/revoke/${shareId}`)
      onAction()
    } catch (err) {
      onError(err.response?.data?.detail || 'Failed to cancel share')
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

  const handleModuleToggle = async (share, moduleKey) => {
    const currentModules = share.shared_modules || SHARE_MODULES.map(m => m.key)
    const updated = currentModules.includes(moduleKey)
      ? currentModules.filter(m => m !== moduleKey)
      : [...currentModules, moduleKey]
    if (updated.length === 0) { onError('At least one section must remain selected'); return }
    setProcessing(true)
    try {
      await axios.put(`/api/client-sharing/${share.id}/modules`, { shared_modules: updated })
      onAction()
    } catch (err) {
      onError(err.response?.data?.detail || 'Failed to update shared modules')
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
                  <th className="text-left px-4 py-3 text-xs font-semibold text-[#7A8580] uppercase tracking-wider hidden lg:table-cell">Modules</th>
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
                    <td className="px-4 py-3 hidden lg:table-cell">
                      <div className="flex flex-wrap gap-1">
                        {SHARE_MODULES.map(mod => {
                          const active = (share.shared_modules || SHARE_MODULES.map(m => m.key)).includes(mod.key)
                          return (
                            <button
                              key={mod.key}
                              onClick={() => handleModuleToggle(share, mod.key)}
                              disabled={processing}
                              className={`px-2 py-0.5 text-xs rounded-full border transition-colors ${
                                active
                                  ? 'bg-[#5B8A72] text-white border-[#5B8A72]'
                                  : 'bg-white text-[#7A8580] border-[#D1D5CE] hover:border-[#5B8A72]'
                              } disabled:opacity-50`}
                              title={`${active ? 'Remove' : 'Add'} ${mod.label} access`}
                            >
                              {mod.label}
                            </button>
                          )
                        })}
                      </div>
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
                  <th className="text-left px-4 py-3 text-xs font-semibold text-[#7A8580] uppercase tracking-wider">Passcode</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-[#7A8580] uppercase tracking-wider">Status</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-[#7A8580] uppercase tracking-wider hidden md:table-cell">Date</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-[#7A8580] uppercase tracking-wider">Actions</th>
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
                      {share.passcode && share.status === 'PENDING' ? (
                        <button
                          onClick={() => navigator.clipboard.writeText(share.passcode)}
                          className="inline-flex items-center gap-1.5 font-mono text-sm font-bold text-[#3D4A44] tracking-wider hover:text-[#5B8A72] transition-colors"
                          title="Click to copy passcode"
                        >
                          {share.passcode}
                          <svg className="w-3.5 h-3.5 text-[#7A8580]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9.75a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184" />
                          </svg>
                        </button>
                      ) : (
                        <span className="text-xs text-[#7A8580]">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${STATUS_COLORS[share.status] || 'bg-gray-100 text-gray-500'}`}>
                        {share.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 hidden md:table-cell">
                      <span className="text-xs text-[#7A8580]">
                        {share.created_at ? new Date(share.created_at).toLocaleDateString() : '—'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      {share.status === 'PENDING' && (
                        <button
                          onClick={() => handleCancel(share.id)}
                          disabled={processing}
                          className="px-3 py-1.5 border border-red-300 text-red-600 rounded-lg text-xs font-medium hover:bg-red-50 disabled:opacity-50 transition-colors"
                        >
                          Cancel
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {receivedActiveShares.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-[#3D4A44] mb-3">Shared With You ({receivedActiveShares.length})</h3>
          <div className="bg-white rounded-xl shadow-sm overflow-hidden">
            <table className="w-full">
              <thead className="bg-[#F5F7F4]">
                <tr>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-[#7A8580] uppercase tracking-wider">Creator</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-[#7A8580] uppercase tracking-wider">Shared By</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-[#7A8580] uppercase tracking-wider">Role</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-[#7A8580] uppercase tracking-wider hidden lg:table-cell">Access</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-[#7A8580] uppercase tracking-wider hidden md:table-cell">Accepted</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E5E8E3]">
                {receivedActiveShares.map(share => (
                  <tr key={share.id} className="hover:bg-[#FAFBF9] transition-colors">
                    <td className="px-4 py-3">
                      <p className="text-sm font-medium text-[#3D4A44]">{share.creator_name}</p>
                    </td>
                    <td className="px-4 py-3">
                      <p className="text-sm text-[#3D4A44]">{share.primary_org_name}</p>
                      <p className="text-xs text-[#7A8580]">{share.shared_by_username}</p>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${ROLE_COLORS[share.role] || 'bg-gray-100 text-gray-600'}`}>
                        {ROLE_LABELS[share.role] || share.role}
                      </span>
                    </td>
                    <td className="px-4 py-3 hidden lg:table-cell">
                      <div className="flex flex-wrap gap-1">
                        {SHARE_MODULES.filter(m => (share.shared_modules || SHARE_MODULES.map(s => s.key)).includes(m.key)).map(mod => (
                          <span key={mod.key} className="px-2 py-0.5 text-xs rounded-full bg-[#5B8A72] text-white">
                            {mod.label}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-3 hidden md:table-cell">
                      <span className="text-xs text-[#7A8580]">
                        {share.accepted_at ? new Date(share.accepted_at).toLocaleDateString() : '—'}
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
