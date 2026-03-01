import React, { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import {
  UserCircleIcon,
  MusicalNoteIcon,
  FilmIcon,
  ClipboardDocumentListIcon,
  BanknotesIcon,
  ShareIcon,
  PencilIcon,
  CheckIcon,
  XMarkIcon,
  UserGroupIcon,
  UsersIcon,
  MagnifyingGlassIcon,
  EnvelopeIcon,
  ArrowDownTrayIcon,
  PlusIcon,
  CloudArrowUpIcon,
  SparklesIcon,
  DocumentTextIcon,
  PaperClipIcon,
  TrashIcon,
  ArrowUpTrayIcon,
  ArrowLeftIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  StarIcon,
  LinkIcon,
} from '@heroicons/react/24/outline'
import PlatformIcon from '../components/PlatformIcon'
import AddSongModal from '../components/AddSongModal'
import ScheduleAUploadModal from '../components/ScheduleAUploadModal'
import SongDetailModal from '../components/SongDetailModal'

const TARGET_FIELDS = [
  { value: '', label: '— Skip —' },
  { value: 'track_title', label: 'Track / Work Title' },
  { value: 'artist', label: 'Artist / Writer' },
  { value: 'isrc', label: 'ISRC' },
  { value: 'upc', label: 'UPC' },
  { value: 'iswc', label: 'ISWC' },
  { value: 'revenue', label: 'Revenue / Amount' },
  { value: 'quantity', label: 'Quantity / Performances' },
  { value: 'territory', label: 'Territory' },
  { value: 'platform', label: 'Platform / Licensee' },
  { value: 'revenue_type', label: 'Revenue / Rights Type' },
  { value: 'publisher', label: 'Publisher' },
  { value: 'work_id', label: 'Work ID / Song Code' },
  { value: 'share_percentage', label: 'Share %' },
]

const SOURCE_TYPE_OPTIONS = [
  { value: '', label: 'Auto-detect' },
  { value: 'DSP', label: 'DSP / Distributor (Spotify, Apple Music, DistroKid, etc.)' },
  { value: 'BMI', label: 'BMI' },
  { value: 'ASCAP', label: 'ASCAP' },
  { value: 'SESAC', label: 'SESAC' },
  { value: 'SoundExchange', label: 'SoundExchange' },
  { value: 'SOCAN', label: 'SOCAN' },
  { value: 'PRS', label: 'PRS for Music' },
  { value: 'OTHER_PRO', label: 'Other PRO' },
]

const STATEMENT_STATUS_COLORS = {
  PENDING: 'bg-amber-100 text-amber-700',
  PROCESSING: 'bg-blue-100 text-blue-700',
  PROCESSED: 'bg-green-100 text-green-700',
  FAILED: 'bg-red-100 text-red-700',
  PARTIALLY_MATCHED: 'bg-orange-100 text-orange-700',
}

const CURRENCIES = ['USD', 'EUR', 'GBP', 'CAD', 'AUD', 'JPY']

const BASE_TABS = [
  { key: 'profile', label: 'Profile', icon: UserCircleIcon },
  { key: 'catalog', label: 'Catalog', icon: MusicalNoteIcon },
  { key: 'placements', label: 'Placements', icon: FilmIcon },
  { key: 'contracts', label: 'Contracts', icon: ClipboardDocumentListIcon },
  { key: 'accounting', label: 'Accounting', icon: BanknotesIcon },
  { key: 'credits', label: 'My Credits', icon: StarIcon },
  { key: 'directory', label: 'Directory', icon: UserGroupIcon },
  { key: 'access', label: 'Access', icon: ShareIcon },
]

export default function ClientPortalPage() {
  const [activeTab, setActiveTab] = useState('profile')
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    axios.get('/api/client-portal/me').then(res => {
      setProfile(res.data)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-[#5B8A72] border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (!profile) {
    return (
      <div className="max-w-2xl mx-auto p-8 text-center">
        <UserCircleIcon className="w-16 h-16 mx-auto text-[#A0A8A3] mb-4" />
        <h2 className="text-xl font-semibold text-[#3D4A44] mb-2">No Profile Found</h2>
        <p className="text-[#7A8580]">Your account is not linked to a creator profile. Please contact your administrator.</p>
      </div>
    )
  }

  const tabs = profile.client_access_scope === 'ALL'
    ? [...BASE_TABS.slice(0, 7), { key: 'clients', label: 'Clients', icon: UsersIcon }, BASE_TABS[7]]
    : BASE_TABS

  return (
    <div className="max-w-6xl mx-auto p-4 md:p-6 space-y-6">
      <div className="bg-gradient-to-r from-[#5B8A72] to-[#7BAF9E] rounded-2xl p-6 text-white shadow-sm">
        <div className="flex items-center gap-4">
          {profile.creator.hero_image_url ? (
            <img src={profile.creator.hero_image_url} alt="" className="w-16 h-16 rounded-full object-cover border-2 border-white/30" />
          ) : (
            <div className="w-16 h-16 rounded-full bg-white/20 flex items-center justify-center text-2xl font-bold">
              {profile.creator.display_name?.charAt(0) || '?'}
            </div>
          )}
          <div>
            <h1 className="text-2xl font-bold">{profile.creator.display_name}</h1>
            <p className="text-white/80 text-sm">{profile.organization_name}</p>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-[rgba(59,77,67,0.08)]">
        <div className="flex overflow-x-auto no-scrollbar border-b border-[#E5E8E3]">
          {tabs.map(tab => {
            const Icon = tab.icon
            const active = activeTab === tab.key
            return (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`flex items-center gap-2 px-4 py-3 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
                  active ? 'border-[#5B8A72] text-[#5B8A72]' : 'border-transparent text-[#7A8580] hover:text-[#3D4A44]'
                }`}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            )
          })}
        </div>
      </div>

      {activeTab === 'profile' && <ProfileTab creator={profile.creator} onUpdate={setProfile} />}
      {activeTab === 'catalog' && <CatalogTab organizationId={profile.organization_id} creatorId={profile.creator_id} />}
      {activeTab === 'placements' && <PlacementsTab />}
      {activeTab === 'contracts' && <ContractsTab />}
      {activeTab === 'accounting' && <AccountingTab orgId={profile.organization_id} />}
      {activeTab === 'credits' && <CreditsTab organizationId={profile.organization_id} creatorId={profile.creator_id} creatorName={profile.creator.display_name} />}
      {activeTab === 'directory' && <DirectoryTab />}
      {activeTab === 'clients' && profile.client_access_scope === 'ALL' && <ClientsTab />}
      {activeTab === 'access' && <AccessTab />}
    </div>
  )
}

function ProfileTab({ creator, onUpdate }) {
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({ ...creator })
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState(null)

  const handleSave = async () => {
    setSaving(true)
    try {
      await axios.put('/api/client-portal/profile', form)
      const res = await axios.get('/api/client-portal/me')
      onUpdate(res.data)
      setForm({ ...res.data.creator })
      setEditing(false)
      setMsg('Profile updated')
      setTimeout(() => setMsg(null), 3000)
    } catch (err) {
      setMsg(err.response?.data?.detail || 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  const Field = ({ label, field, type = 'text' }) => (
    <div>
      <label className="block text-xs font-medium text-[#7A8580] mb-1">{label}</label>
      {editing ? (
        type === 'textarea' ? (
          <textarea
            value={form[field] || ''}
            onChange={(e) => setForm({ ...form, [field]: e.target.value })}
            rows={3}
            className="w-full px-3 py-2 border border-[#D1D5CE] rounded-lg text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
          />
        ) : (
          <input
            type={type}
            value={form[field] || ''}
            onChange={(e) => setForm({ ...form, [field]: e.target.value })}
            className="w-full px-3 py-2 border border-[#D1D5CE] rounded-lg text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
          />
        )
      ) : (
        <p className="text-sm text-[#3D4A44]">{creator[field] || <span className="text-[#A0A8A3] italic">Not set</span>}</p>
      )}
    </div>
  )

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl shadow-sm border border-[rgba(59,77,67,0.08)] p-6 space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-[#3D4A44]">Creator Profile</h2>
          <div className="flex items-center gap-2">
            {msg && <span className="text-sm text-[#5B8A72] font-medium">{msg}</span>}
            {editing ? (
              <>
                <button onClick={() => { setEditing(false); setForm({ ...creator }) }} className="px-3 py-1.5 text-sm text-[#7A8580] hover:bg-[#EEF1EC] rounded-lg">Cancel</button>
                <button onClick={handleSave} disabled={saving} className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] disabled:opacity-50">
                  <CheckIcon className="w-4 h-4" />
                  {saving ? 'Saving...' : 'Save'}
                </button>
              </>
            ) : (
              <button onClick={() => setEditing(true)} className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-[#5B8A72] hover:bg-[#EEF1EC] rounded-lg border border-[#5B8A72]/30">
                <PencilIcon className="w-4 h-4" />
                Edit
              </button>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Field label="Display Name" field="display_name" />
          <Field label="Legal Name" field="legal_name" />
          <Field label="Email" field="email" type="email" />
          <Field label="Phone" field="phone" />
          <Field label="Territory" field="primary_territory" />
          <Field label="PRO" field="primary_pro" />
          <Field label="IPI Number" field="primary_ipi" />
          <div>
            <label className="block text-xs font-medium text-[#7A8580] mb-1">Publisher</label>
            <p className="text-sm text-[#3D4A44]">
              {creator.publisher_contact
                ? <>{creator.publisher_contact.display_name}{creator.publisher_contact.company ? <span className="text-[#7A8580]"> ({creator.publisher_contact.company})</span> : ''}</>
                : creator.publisher_name
                  ? creator.publisher_name
                  : <span className="text-[#A0A8A3] italic">Not set</span>
              }
            </p>
          </div>
          <div>
            <label className="block text-xs font-medium text-[#7A8580] mb-1">Administrator</label>
            <p className="text-sm text-[#3D4A44]">
              {creator.admin_contact
                ? <>{creator.admin_contact.display_name}{creator.admin_contact.company ? <span className="text-[#7A8580]"> ({creator.admin_contact.company})</span> : ''}</>
                : <span className="text-[#A0A8A3] italic">Not set</span>
              }
            </p>
          </div>
          <Field label="Label Affiliation" field="label_affiliation" />
          <Field label="Website" field="website_url" type="url" />
        </div>

        <div>
          <Field label="Bio" field="bio" type="textarea" />
        </div>

        <div>
          <h3 className="text-sm font-semibold text-[#3D4A44] mb-3">Social Links</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Field label="Spotify" field="spotify_url" type="url" />
            <Field label="Apple Music" field="apple_music_url" type="url" />
            <Field label="YouTube" field="youtube_url" type="url" />
            <Field label="Instagram" field="instagram_url" type="url" />
            <Field label="Twitter / X" field="twitter_url" type="url" />
          </div>
        </div>
      </div>

      <MergeAccountSection />
    </div>
  )
}

function MergeAccountSection() {
  const [step, setStep] = useState('idle')
  const [targetEmail, setTargetEmail] = useState('')
  const [verificationCode, setVerificationCode] = useState('')
  const [requestId, setRequestId] = useState(null)
  const [maskedEmail, setMaskedEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [successMsg, setSuccessMsg] = useState('')
  const [mergeRequests, setMergeRequests] = useState([])
  const [requestsLoading, setRequestsLoading] = useState(true)

  const loadRequests = () => {
    setRequestsLoading(true)
    axios.get('/api/account-merge/my-requests')
      .then(res => setMergeRequests(res.data))
      .catch(() => {})
      .finally(() => setRequestsLoading(false))
  }

  useEffect(() => { loadRequests() }, [])

  const handleSubmitRequest = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    setSuccessMsg('')
    try {
      const res = await axios.post('/api/account-merge/request', { target_email: targetEmail })
      setRequestId(res.data.id)
      setMaskedEmail(res.data.target_email_masked || targetEmail)
      setStep('verify')
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create merge request')
    } finally {
      setLoading(false)
    }
  }

  const handleVerify = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      await axios.post('/api/account-merge/verify', {
        request_id: requestId,
        code: verificationCode,
      })
      setSuccessMsg('Identity verified! Your merge request has been submitted for admin review.')
      setStep('idle')
      setTargetEmail('')
      setVerificationCode('')
      setRequestId(null)
      loadRequests()
    } catch (err) {
      setError(err.response?.data?.detail || 'Verification failed')
    } finally {
      setLoading(false)
    }
  }

  const handleCancel = async (reqId) => {
    try {
      await axios.delete(`/api/account-merge/${reqId}`)
      loadRequests()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to cancel request')
    }
  }

  const statusColors = {
    PENDING_VERIFICATION: 'bg-amber-100 text-amber-700',
    VERIFIED: 'bg-blue-100 text-blue-700',
    COMPLETED: 'bg-green-100 text-green-700',
    REJECTED: 'bg-red-100 text-red-600',
    CANCELLED: 'bg-gray-100 text-gray-600',
    EXPIRED: 'bg-gray-100 text-gray-500',
  }

  const statusLabels = {
    PENDING_VERIFICATION: 'Pending Verification',
    VERIFIED: 'Awaiting Admin Approval',
    COMPLETED: 'Completed',
    REJECTED: 'Rejected',
    CANCELLED: 'Cancelled',
    EXPIRED: 'Expired',
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-[rgba(59,77,67,0.08)] p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-[#3D4A44]">Merge Account</h2>
          <p className="text-sm text-[#7A8580] mt-0.5">Link this client profile to your own independent user account.</p>
        </div>
        {step === 'idle' && (
          <button
            onClick={() => setStep('enter_email')}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] transition-colors"
          >
            <ShareIcon className="w-4 h-4" />
            Merge Account
          </button>
        )}
      </div>

      {successMsg && (
        <div className="flex items-center gap-2 p-3 bg-green-50 text-green-700 rounded-lg text-sm">
          <CheckCircleIcon className="w-5 h-5 flex-shrink-0" />
          {successMsg}
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-50 text-red-700 rounded-lg text-sm">
          <ExclamationCircleIcon className="w-5 h-5 flex-shrink-0" />
          {error}
        </div>
      )}

      {step === 'enter_email' && (
        <form onSubmit={handleSubmitRequest} className="space-y-3 border border-[#E5E8E3] rounded-xl p-4">
          <div>
            <label className="block text-sm font-medium text-[#3D4A44] mb-1">Target Account Email</label>
            <p className="text-xs text-[#7A8580] mb-2">Enter the email address of the independent account you want to merge into. A verification code will be sent to that email.</p>
            <input
              type="email"
              required
              value={targetEmail}
              onChange={(e) => setTargetEmail(e.target.value)}
              placeholder="your-account@example.com"
              className="w-full px-3 py-2 border border-[#D1D5CE] rounded-lg text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
            />
          </div>
          <div className="flex items-center gap-2 justify-end">
            <button
              type="button"
              onClick={() => { setStep('idle'); setTargetEmail(''); setError('') }}
              className="px-3 py-1.5 text-sm text-[#7A8580] hover:bg-[#EEF1EC] rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex items-center gap-1.5 px-4 py-2 text-sm bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] disabled:opacity-50"
            >
              {loading ? 'Sending...' : 'Send Verification Code'}
            </button>
          </div>
        </form>
      )}

      {step === 'verify' && (
        <form onSubmit={handleVerify} className="space-y-3 border border-[#E5E8E3] rounded-xl p-4">
          <div className="bg-[#F5F7F4] rounded-lg p-3 text-sm text-[#3D4A44]">
            A 6-digit verification code has been sent to <strong>{maskedEmail}</strong>. Enter it below to verify your identity.
          </div>
          <div>
            <label className="block text-sm font-medium text-[#3D4A44] mb-1">Verification Code</label>
            <input
              type="text"
              required
              value={verificationCode}
              onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
              placeholder="000000"
              maxLength={6}
              className="w-full px-3 py-2 border border-[#D1D5CE] rounded-lg text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent font-mono tracking-widest text-center text-lg"
            />
          </div>
          <div className="flex items-center gap-2 justify-end">
            <button
              type="button"
              onClick={() => { setStep('idle'); setVerificationCode(''); setError('') }}
              className="px-3 py-1.5 text-sm text-[#7A8580] hover:bg-[#EEF1EC] rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || verificationCode.length < 6}
              className="flex items-center gap-1.5 px-4 py-2 text-sm bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] disabled:opacity-50"
            >
              {loading ? 'Verifying...' : 'Verify & Submit'}
            </button>
          </div>
        </form>
      )}

      {requestsLoading ? (
        <LoadingSpinner />
      ) : mergeRequests.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-[#3D4A44]">Merge Requests</h3>
          {mergeRequests.map(req => (
            <div key={req.id} className="flex items-center justify-between p-3 border border-[#E5E8E3] rounded-xl">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-[#3D4A44]">
                    {req.target_username ? `@${req.target_username}` : req.target_email_masked}
                  </span>
                  <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${statusColors[req.status] || 'bg-gray-100 text-gray-600'}`}>
                    {statusLabels[req.status] || req.status}
                  </span>
                </div>
                <div className="flex items-center gap-3 text-xs text-[#7A8580]">
                  {req.organization_name && <span>{req.organization_name}</span>}
                  {req.creator_name && <span>{req.creator_name}</span>}
                  {req.created_at && <span>{new Date(req.created_at).toLocaleDateString()}</span>}
                </div>
                {req.admin_notes && (
                  <p className="text-xs text-[#7A8580] italic mt-1">Admin: {req.admin_notes}</p>
                )}
              </div>
              {(req.status === 'PENDING_VERIFICATION' || req.status === 'VERIFIED') && (
                <button
                  onClick={() => handleCancel(req.id)}
                  className="px-3 py-1.5 text-xs text-red-600 hover:bg-red-50 rounded-lg border border-red-200 transition-colors"
                >
                  Cancel
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function CatalogTab({ organizationId, creatorId }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [view, setView] = useState('songs')
  const [showAddSong, setShowAddSong] = useState(false)
  const [showImport, setShowImport] = useState(false)
  const [selectedSong, setSelectedSong] = useState(null)

  const loadCatalog = () => {
    axios.get('/api/client-portal/catalog').then(res => {
      setData(res.data)
      setLoading(false)
    }).catch(() => setLoading(false))
  }

  useEffect(() => {
    loadCatalog()
  }, [])

  if (loading) return <LoadingSpinner />
  if (!data) return <EmptyState text="Could not load catalog" />

  return (
    <div className="bg-white rounded-xl shadow-sm border border-[rgba(59,77,67,0.08)] p-6 space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h2 className="text-lg font-semibold text-[#3D4A44]">My Catalog</h2>
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => setShowImport(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-[#5B8A72] hover:bg-[#EEF1EC] rounded-lg border border-[#5B8A72]/30 transition-colors"
          >
            <CloudArrowUpIcon className="w-4 h-4" />
            Import Catalog
          </button>
          <button
            onClick={() => setShowAddSong(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] transition-colors"
          >
            <PlusIcon className="w-4 h-4" />
            Add Song
          </button>
          <div className="flex bg-[#F5F7F4] rounded-lg p-0.5">
            <button onClick={() => setView('songs')} className={`px-3 py-1.5 text-sm rounded-md transition-colors ${view === 'songs' ? 'bg-white text-[#3D4A44] shadow-sm font-medium' : 'text-[#7A8580]'}`}>
              Songs ({data.songs?.length || 0})
            </button>
            <button onClick={() => setView('works')} className={`px-3 py-1.5 text-sm rounded-md transition-colors ${view === 'works' ? 'bg-white text-[#3D4A44] shadow-sm font-medium' : 'text-[#7A8580]'}`}>
              Works ({data.works?.length || 0})
            </button>
          </div>
        </div>
      </div>

      {view === 'songs' && (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[500px]">
            <thead className="bg-[#F5F7F4]">
              <tr>
                <th className="text-left px-4 py-2 text-xs font-semibold text-[#7A8580] uppercase">Title</th>
                <th className="text-left px-4 py-2 text-xs font-semibold text-[#7A8580] uppercase">Artist</th>
                <th className="text-left px-4 py-2 text-xs font-semibold text-[#7A8580] uppercase">ISRC</th>
                <th className="text-left px-4 py-2 text-xs font-semibold text-[#7A8580] uppercase">Release Date</th>
                <th className="text-left px-4 py-2 text-xs font-semibold text-[#7A8580] uppercase">Credits</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E5E8E3]">
              {data.songs.map(s => (
                <tr
                  key={s.id}
                  className="hover:bg-[#FAFBF9] cursor-pointer"
                  onClick={() => setSelectedSong({ id: s.id, title: s.title, primary_artist: s.artist })}
                >
                  <td className="px-4 py-3 text-sm font-medium text-[#3D4A44]">{s.title}</td>
                  <td className="px-4 py-3 text-sm text-[#7A8580]">{s.artist}</td>
                  <td className="px-4 py-3 text-sm text-[#7A8580] font-mono">{s.isrc || '-'}</td>
                  <td className="px-4 py-3 text-sm text-[#7A8580]">{s.release_date || '-'}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {s.credits?.map((c, i) => (
                        <span key={i} className="inline-flex px-1.5 py-0.5 text-xs bg-[#EEF1EC] text-[#5B8A72] rounded">
                          {c.creator_name} ({c.role}{c.share_percentage ? ` ${c.share_percentage}%` : ''})
                        </span>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {data.songs.length === 0 && <EmptyState text="No songs in your catalog" />}
        </div>
      )}

      {view === 'works' && (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[400px]">
            <thead className="bg-[#F5F7F4]">
              <tr>
                <th className="text-left px-4 py-2 text-xs font-semibold text-[#7A8580] uppercase">Title</th>
                <th className="text-left px-4 py-2 text-xs font-semibold text-[#7A8580] uppercase">Type</th>
                <th className="text-left px-4 py-2 text-xs font-semibold text-[#7A8580] uppercase">ISWC</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E5E8E3]">
              {data.works.map(w => (
                <tr key={w.id} className="hover:bg-[#FAFBF9]">
                  <td className="px-4 py-3 text-sm font-medium text-[#3D4A44]">{w.title}</td>
                  <td className="px-4 py-3 text-sm text-[#7A8580]">{w.work_type || '-'}</td>
                  <td className="px-4 py-3 text-sm text-[#7A8580] font-mono">{w.iswc || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {data.works.length === 0 && <EmptyState text="No works in your catalog" />}
        </div>
      )}

      {showAddSong && (
        <AddSongModal
          onClose={() => setShowAddSong(false)}
          onSuccess={() => loadCatalog()}
          organizationId={organizationId}
        />
      )}

      {showImport && (
        <ScheduleAUploadModal
          onClose={() => setShowImport(false)}
          onSuccess={() => loadCatalog()}
          organizationId={organizationId}
        />
      )}

      {selectedSong && (
        <SongDetailModal
          song={selectedSong}
          onClose={() => setSelectedSong(null)}
          onSongUpdated={() => loadCatalog()}
        />
      )}
    </div>
  )
}

function PlacementsTab() {
  const [placements, setPlacements] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    axios.get('/api/client-portal/placements').then(res => {
      setPlacements(res.data)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  const statusColors = {
    PITCHED: 'bg-blue-100 text-blue-700',
    INTERESTED: 'bg-amber-100 text-amber-700',
    NEGOTIATING: 'bg-purple-100 text-purple-700',
    CONFIRMED: 'bg-green-100 text-green-700',
    PLACED: 'bg-emerald-100 text-emerald-700',
    PAID: 'bg-teal-100 text-teal-700',
    DECLINED: 'bg-red-100 text-red-600',
  }

  if (loading) return <LoadingSpinner />

  return (
    <div className="bg-white rounded-xl shadow-sm border border-[rgba(59,77,67,0.08)] p-6 space-y-4">
      <h2 className="text-lg font-semibold text-[#3D4A44]">Sync Placements ({placements.length})</h2>
      {placements.length === 0 ? (
        <EmptyState text="No placements yet" />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {placements.map(p => (
            <div key={p.id} className="border border-[#E5E8E3] rounded-xl p-4 hover:shadow-sm transition-shadow">
              <div className="flex items-start justify-between mb-2">
                <h3 className="text-sm font-semibold text-[#3D4A44]">{p.title}</h3>
                <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${statusColors[p.status] || 'bg-gray-100 text-gray-600'}`}>
                  {p.status}
                </span>
              </div>
              <div className="space-y-1 text-xs text-[#7A8580]">
                {p.client_name && <p>Client: {p.client_name}</p>}
                {p.project_name && <p>Project: {p.project_name}</p>}
                {p.media_type && <p>Media: {p.media_type}</p>}
                {p.license_fee > 0 && (
                  <p className="text-[#5B8A72] font-medium">
                    Fee: {p.license_currency || 'USD'} {p.license_fee.toLocaleString()}
                  </p>
                )}
                {p.created_at && <p className="text-[#A0A8A3]">Added: {new Date(p.created_at).toLocaleDateString()}</p>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

const CONTRACT_TYPES = [
  { value: 'MASTER', label: 'Master' },
  { value: 'PUBLISHING', label: 'Publishing' },
  { value: 'SYNC_LICENSE', label: 'Sync License' },
  { value: 'DISTRIBUTION', label: 'Distribution' },
  { value: 'MECHANICAL', label: 'Mechanical' },
  { value: 'PERFORMANCE', label: 'Performance' },
  { value: 'OTHER', label: 'Other' },
]

const CONTRACT_STATUSES = ['DRAFT', 'ACTIVE', 'EXPIRED', 'TERMINATED']
const CONTRACT_CURRENCIES = ['USD', 'EUR', 'GBP', 'CAD', 'AUD', 'JPY']

const emptyContractForm = {
  title: '', contract_type: 'MASTER', payment_direction: 'INCOMING', status: 'DRAFT',
  reference_number: '', start_date: '', end_date: '', territory: '',
  advance_amount: '', advance_currency: 'USD', notes: '', terms_summary: '',
}

function ContractsTab() {
  const [contracts, setContracts] = useState([])
  const [loading, setLoading] = useState(true)
  const [orgId, setOrgId] = useState(null)
  const [creatorId, setCreatorId] = useState(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [createForm, setCreateForm] = useState({ ...emptyContractForm })
  const [createLoading, setCreateLoading] = useState(false)
  const [createError, setCreateError] = useState('')
  const [parseFile, setParseFile] = useState(null)
  const [parsing, setParsing] = useState(false)
  const [parseSuccess, setParseSuccess] = useState(false)
  const [selectedContract, setSelectedContract] = useState(null)
  const [contractDocuments, setContractDocuments] = useState([])
  const [docUploading, setDocUploading] = useState(false)
  const [showUploadDoc, setShowUploadDoc] = useState(false)
  const parseFileRef = useRef(null)
  const docFileRef = useRef(null)

  useEffect(() => {
    axios.get('/api/client-portal/me').then(res => {
      setOrgId(res.data.organization_id)
      setCreatorId(res.data.creator_id)
    })
  }, [])

  useEffect(() => {
    loadContracts()
  }, [])

  function loadContracts() {
    axios.get('/api/client-portal/contracts').then(res => {
      setContracts(res.data)
      setLoading(false)
    }).catch(() => setLoading(false))
  }

  async function loadDocuments(contractId) {
    try {
      const res = await axios.get(`/api/rights/contracts/${contractId}/documents`)
      setContractDocuments(Array.isArray(res.data) ? res.data : [])
    } catch {
      setContractDocuments([])
    }
  }

  async function handleParseContract() {
    if (!parseFile) return
    setParsing(true)
    setCreateError('')
    setParseSuccess(false)
    try {
      const formData = new FormData()
      formData.append('file', parseFile)
      const res = await axios.post('/api/rights/contracts/parse-document', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      const fields = res.data.parsed_fields
      if (fields) {
        setCreateForm(prev => ({
          ...prev,
          title: fields.title || prev.title,
          contract_type: fields.contract_type || prev.contract_type,
          payment_direction: fields.payment_direction || prev.payment_direction,
          status: fields.status || prev.status,
          reference_number: fields.reference_number || prev.reference_number,
          start_date: fields.start_date || prev.start_date,
          end_date: fields.end_date || prev.end_date,
          territory: Array.isArray(fields.territory) ? fields.territory.join(', ') : (fields.territory || prev.territory),
          advance_amount: fields.advance_amount != null ? String(fields.advance_amount) : prev.advance_amount,
          advance_currency: fields.advance_currency || prev.advance_currency,
          notes: fields.notes || prev.notes,
          terms_summary: fields.terms_summary || prev.terms_summary,
        }))
        setParseSuccess(true)
        setTimeout(() => setParseSuccess(false), 5000)
      }
    } catch (error) {
      const detail = error.response?.data?.detail
      setCreateError(typeof detail === 'string' ? detail : 'Failed to parse document. Please try again or enter details manually.')
    } finally {
      setParsing(false)
    }
  }

  async function handleCreateContract() {
    if (!createForm.title.trim()) {
      setCreateError('Please enter a contract title.')
      return
    }
    if (!orgId) {
      setCreateError('Organization not found.')
      return
    }
    setCreateError('')
    setCreateLoading(true)
    try {
      const payload = { ...createForm }
      payload.creator_id = creatorId
      if (payload.advance_amount) payload.advance_amount = parseFloat(payload.advance_amount)
      else delete payload.advance_amount
      if (!payload.start_date) delete payload.start_date
      if (!payload.end_date) delete payload.end_date
      if (!payload.reference_number) delete payload.reference_number
      if (payload.territory && typeof payload.territory === 'string') {
        payload.territory = payload.territory.split(',').map(t => t.trim()).filter(Boolean)
      } else if (!payload.territory) {
        payload.territory = []
      }

      const res = await axios.post(`/api/rights/contracts/org/${orgId}`, payload)
      const newContractId = res.data?.id

      if (parseFile && newContractId) {
        try {
          const docForm = new FormData()
          docForm.append('file', parseFile)
          docForm.append('description', parseFile.name)
          await axios.post(`/api/rights/contracts/${newContractId}/documents`, docForm, {
            headers: { 'Content-Type': 'multipart/form-data' }
          })
        } catch {}
      }

      setShowCreateModal(false)
      setCreateForm({ ...emptyContractForm })
      setCreateError('')
      setParseFile(null)
      setParseSuccess(false)
      loadContracts()
    } catch (error) {
      const detail = error.response?.data?.detail
      setCreateError(typeof detail === 'string' ? detail : 'Failed to create contract. Please try again.')
    } finally {
      setCreateLoading(false)
    }
  }

  async function handleUploadDocument(file) {
    if (!selectedContract) return
    setDocUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('description', file.name)
      await axios.post(`/api/rights/contracts/${selectedContract.id}/documents`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      loadDocuments(selectedContract.id)
      setShowUploadDoc(false)
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to upload document')
    } finally {
      setDocUploading(false)
    }
  }

  async function handleDownloadDocument(doc) {
    try {
      const res = await axios.get(`/api/rights/contracts/documents/${doc.id}/download`, {
        responseType: 'blob'
      })
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', doc.file_name)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch {
      alert('Failed to download document')
    }
  }

  const statusColors = {
    DRAFT: 'bg-gray-100 text-gray-600',
    ACTIVE: 'bg-green-100 text-green-700',
    EXPIRED: 'bg-red-100 text-red-600',
    TERMINATED: 'bg-red-100 text-red-600',
  }

  const typeLabels = {
    MASTER: 'Master', PUBLISHING: 'Publishing', SYNC_LICENSE: 'Sync License',
    DISTRIBUTION: 'Distribution', MECHANICAL: 'Mechanical', PERFORMANCE: 'Performance', OTHER: 'Other',
  }

  if (loading) return <LoadingSpinner />

  if (selectedContract) {
    return (
      <div className="space-y-4">
        <div className="bg-white rounded-xl shadow-sm border border-[rgba(59,77,67,0.08)] p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <button
                onClick={() => { setSelectedContract(null); setContractDocuments([]) }}
                className="text-sm text-[#7A8580] hover:text-[#3D4A44]"
              >
                &larr; Back
              </button>
              <h2 className="text-lg font-semibold text-[#3D4A44]">{selectedContract.title}</h2>
              <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${statusColors[selectedContract.status] || 'bg-gray-100 text-gray-600'}`}>
                {selectedContract.status}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-[#7A8580] mb-1">Type</label>
              <p className="text-sm text-[#3D4A44]">{typeLabels[selectedContract.contract_type] || selectedContract.contract_type}</p>
            </div>
            {selectedContract.start_date && (
              <div>
                <label className="block text-xs font-medium text-[#7A8580] mb-1">Start Date</label>
                <p className="text-sm text-[#3D4A44]">{selectedContract.start_date}</p>
              </div>
            )}
            {selectedContract.end_date && (
              <div>
                <label className="block text-xs font-medium text-[#7A8580] mb-1">End Date</label>
                <p className="text-sm text-[#3D4A44]">{selectedContract.end_date}</p>
              </div>
            )}
            {selectedContract.advance_amount > 0 && (
              <div>
                <label className="block text-xs font-medium text-[#7A8580] mb-1">Advance</label>
                <p className="text-sm text-[#3D4A44]">
                  {selectedContract.advance_currency} {selectedContract.advance_amount?.toLocaleString()}
                </p>
                <div className="mt-1">
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-[#7A8580]">Recouped</span>
                    <span className="font-medium text-[#3D4A44]">
                      {(selectedContract.advance_recouped || 0).toLocaleString()} / {selectedContract.advance_amount.toLocaleString()}
                    </span>
                  </div>
                  <div className="w-full bg-[#E5E8E3] rounded-full h-2">
                    <div
                      className="bg-[#5B8A72] h-2 rounded-full transition-all"
                      style={{ width: `${Math.min(100, ((selectedContract.advance_recouped || 0) / selectedContract.advance_amount) * 100)}%` }}
                    />
                  </div>
                </div>
              </div>
            )}
            {selectedContract.notes && (
              <div className="md:col-span-2">
                <label className="block text-xs font-medium text-[#7A8580] mb-1">Notes</label>
                <p className="text-sm text-[#3D4A44] whitespace-pre-wrap">{selectedContract.notes}</p>
              </div>
            )}
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-[rgba(59,77,67,0.08)] p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-[#3D4A44]">Documents ({contractDocuments.length})</h3>
            <button
              onClick={() => { setShowUploadDoc(true) }}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62]"
            >
              <CloudArrowUpIcon className="w-4 h-4" />
              Upload Document
            </button>
          </div>

          {showUploadDoc && (
            <div className="border border-dashed border-[#5B8A72] rounded-lg p-4 bg-[#F0F5F2]">
              <input
                ref={docFileRef}
                type="file"
                accept=".pdf,.doc,.docx"
                onChange={(e) => {
                  if (e.target.files?.[0]) handleUploadDocument(e.target.files[0])
                }}
                className="text-sm"
              />
              {docUploading && <p className="text-xs text-[#5B8A72] mt-2">Uploading...</p>}
              <button
                onClick={() => setShowUploadDoc(false)}
                className="mt-2 text-xs text-[#7A8580] hover:text-[#3D4A44]"
              >
                Cancel
              </button>
            </div>
          )}

          {contractDocuments.length === 0 ? (
            <p className="text-sm text-[#7A8580] text-center py-4">No documents attached</p>
          ) : (
            <div className="space-y-2">
              {contractDocuments.map(doc => (
                <div key={doc.id} className="flex items-center justify-between p-3 border border-[#E5E8E3] rounded-lg">
                  <div className="flex items-center gap-2 min-w-0">
                    <PaperClipIcon className="w-4 h-4 text-[#7A8580] flex-shrink-0" />
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-[#3D4A44] truncate">{doc.file_name}</p>
                      {doc.description && <p className="text-xs text-[#7A8580] truncate">{doc.description}</p>}
                    </div>
                  </div>
                  <button
                    onClick={() => handleDownloadDocument(doc)}
                    className="flex items-center gap-1 px-2 py-1 text-xs text-[#5B8A72] hover:bg-[#EEF1EC] rounded-lg flex-shrink-0"
                  >
                    <ArrowDownTrayIcon className="w-3.5 h-3.5" />
                    Download
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-xl shadow-sm border border-[rgba(59,77,67,0.08)] p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-[#3D4A44]">Contracts ({contracts.length})</h2>
          <button
            onClick={() => { setShowCreateModal(true); setCreateForm({ ...emptyContractForm }); setParseFile(null); setCreateError(''); setParseSuccess(false) }}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62]"
          >
            <PlusIcon className="w-4 h-4" />
            New Contract
          </button>
        </div>
        {contracts.length === 0 ? (
          <EmptyState text="No contracts linked to your profile" />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {contracts.map(c => (
              <div
                key={c.id}
                onClick={() => { setSelectedContract(c); loadDocuments(c.id) }}
                className="border border-[#E5E8E3] rounded-xl p-4 hover:shadow-sm transition-shadow cursor-pointer"
              >
                <div className="flex items-start justify-between mb-2">
                  <h3 className="text-sm font-semibold text-[#3D4A44]">{c.title}</h3>
                  <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${statusColors[c.status] || 'bg-gray-100 text-gray-600'}`}>
                    {c.status}
                  </span>
                </div>
                <div className="space-y-1 text-xs text-[#7A8580]">
                  <p>Type: {typeLabels[c.contract_type] || c.contract_type}</p>
                  {c.start_date && <p>Start: {c.start_date}</p>}
                  {c.end_date && <p>End: {c.end_date}</p>}
                  {c.advance_amount > 0 && (
                    <div className="mt-2">
                      <div className="flex justify-between text-xs mb-1">
                        <span>Advance Recoupment</span>
                        <span className="font-medium text-[#3D4A44]">
                          {c.advance_currency} {(c.advance_recouped || 0).toLocaleString()} / {c.advance_amount.toLocaleString()}
                        </span>
                      </div>
                      <div className="w-full bg-[#E5E8E3] rounded-full h-2">
                        <div
                          className="bg-[#5B8A72] h-2 rounded-full transition-all"
                          style={{ width: `${Math.min(100, ((c.advance_recouped || 0) / c.advance_amount) * 100)}%` }}
                        />
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {showCreateModal && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-6 border-b border-[#E5E8E3]">
              <h2 className="text-lg font-semibold text-[#3D4A44]">New Contract</h2>
              <button onClick={() => setShowCreateModal(false)} className="text-[#7A8580] hover:text-[#3D4A44]">
                <XMarkIcon className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-5">
              <div className="border border-dashed border-[#5B8A72] rounded-xl p-4 bg-[#F0F5F2] space-y-3">
                <div className="flex items-center gap-2 text-sm font-medium text-[#5B8A72]">
                  <SparklesIcon className="w-4 h-4" />
                  AI Contract Parser
                </div>
                <p className="text-xs text-[#7A8580]">Upload a contract document (PDF or Word) to auto-fill form fields using AI.</p>
                <div className="flex items-center gap-3">
                  <input
                    ref={parseFileRef}
                    type="file"
                    accept=".pdf,.docx"
                    onChange={(e) => setParseFile(e.target.files?.[0] || null)}
                    className="text-sm flex-1"
                  />
                  <button
                    onClick={handleParseContract}
                    disabled={!parseFile || parsing}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] disabled:opacity-50"
                  >
                    <SparklesIcon className="w-4 h-4" />
                    {parsing ? 'Parsing...' : 'Parse'}
                  </button>
                </div>
                {parseSuccess && (
                  <p className="text-xs text-green-600 font-medium">Fields populated from document</p>
                )}
              </div>

              {createError && (
                <div className="p-3 bg-red-50 text-red-700 rounded-lg text-sm">{createError}</div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="md:col-span-2">
                  <label className="block text-xs font-medium text-[#7A8580] mb-1">Title *</label>
                  <input
                    type="text"
                    value={createForm.title}
                    onChange={(e) => setCreateForm({ ...createForm, title: e.target.value })}
                    className="w-full px-3 py-2 border border-[#D1D5CE] rounded-lg text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                    placeholder="Contract title"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-[#7A8580] mb-1">Type</label>
                  <select
                    value={createForm.contract_type}
                    onChange={(e) => setCreateForm({ ...createForm, contract_type: e.target.value })}
                    className="w-full px-3 py-2 border border-[#D1D5CE] rounded-lg text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                  >
                    {CONTRACT_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-[#7A8580] mb-1">Status</label>
                  <select
                    value={createForm.status}
                    onChange={(e) => setCreateForm({ ...createForm, status: e.target.value })}
                    className="w-full px-3 py-2 border border-[#D1D5CE] rounded-lg text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                  >
                    {CONTRACT_STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-[#7A8580] mb-1">Payment Direction</label>
                  <select
                    value={createForm.payment_direction}
                    onChange={(e) => setCreateForm({ ...createForm, payment_direction: e.target.value })}
                    className="w-full px-3 py-2 border border-[#D1D5CE] rounded-lg text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                  >
                    <option value="INCOMING">Incoming</option>
                    <option value="OUTGOING">Outgoing</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-[#7A8580] mb-1">Reference Number</label>
                  <input
                    type="text"
                    value={createForm.reference_number}
                    onChange={(e) => setCreateForm({ ...createForm, reference_number: e.target.value })}
                    className="w-full px-3 py-2 border border-[#D1D5CE] rounded-lg text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                    placeholder="Optional"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-[#7A8580] mb-1">Start Date</label>
                  <input
                    type="date"
                    value={createForm.start_date}
                    onChange={(e) => setCreateForm({ ...createForm, start_date: e.target.value })}
                    className="w-full px-3 py-2 border border-[#D1D5CE] rounded-lg text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-[#7A8580] mb-1">End Date</label>
                  <input
                    type="date"
                    value={createForm.end_date}
                    onChange={(e) => setCreateForm({ ...createForm, end_date: e.target.value })}
                    className="w-full px-3 py-2 border border-[#D1D5CE] rounded-lg text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-[#7A8580] mb-1">Territory</label>
                  <input
                    type="text"
                    value={createForm.territory}
                    onChange={(e) => setCreateForm({ ...createForm, territory: e.target.value })}
                    className="w-full px-3 py-2 border border-[#D1D5CE] rounded-lg text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                    placeholder="e.g. US, UK, Worldwide"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-[#7A8580] mb-1">Advance Amount</label>
                  <div className="flex gap-2">
                    <select
                      value={createForm.advance_currency}
                      onChange={(e) => setCreateForm({ ...createForm, advance_currency: e.target.value })}
                      className="px-2 py-2 border border-[#D1D5CE] rounded-lg text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent w-20"
                    >
                      {CONTRACT_CURRENCIES.map(c => <option key={c} value={c}>{c}</option>)}
                    </select>
                    <input
                      type="number"
                      value={createForm.advance_amount}
                      onChange={(e) => setCreateForm({ ...createForm, advance_amount: e.target.value })}
                      className="flex-1 px-3 py-2 border border-[#D1D5CE] rounded-lg text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                      placeholder="0.00"
                      min="0"
                      step="0.01"
                    />
                  </div>
                </div>

                <div className="md:col-span-2">
                  <label className="block text-xs font-medium text-[#7A8580] mb-1">Terms Summary</label>
                  <textarea
                    value={createForm.terms_summary}
                    onChange={(e) => setCreateForm({ ...createForm, terms_summary: e.target.value })}
                    rows={2}
                    className="w-full px-3 py-2 border border-[#D1D5CE] rounded-lg text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                    placeholder="Key terms..."
                  />
                </div>

                <div className="md:col-span-2">
                  <label className="block text-xs font-medium text-[#7A8580] mb-1">Notes</label>
                  <textarea
                    value={createForm.notes}
                    onChange={(e) => setCreateForm({ ...createForm, notes: e.target.value })}
                    rows={2}
                    className="w-full px-3 py-2 border border-[#D1D5CE] rounded-lg text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                    placeholder="Additional notes..."
                  />
                </div>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 p-6 border-t border-[#E5E8E3]">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 text-sm text-[#7A8580] hover:bg-[#EEF1EC] rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateContract}
                disabled={createLoading}
                className="flex items-center gap-1.5 px-4 py-2 text-sm bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] disabled:opacity-50"
              >
                {createLoading ? 'Creating...' : 'Create Contract'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function AccountingTab({ orgId }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [statements, setStatements] = useState([])
  const [statementsLoading, setStatementsLoading] = useState(true)
  const [showUpload, setShowUpload] = useState(false)
  const [uploadStep, setUploadStep] = useState(1)
  const [uploadFile, setUploadFile] = useState(null)
  const [uploadSource, setUploadSource] = useState('')
  const [uploadSourceType, setUploadSourceType] = useState('')
  const [detectedSourceType, setDetectedSourceType] = useState(null)
  const [uploadPeriodStart, setUploadPeriodStart] = useState('')
  const [uploadPeriodEnd, setUploadPeriodEnd] = useState('')
  const [uploadCurrency, setUploadCurrency] = useState('USD')
  const [previewData, setPreviewData] = useState(null)
  const [columnMappings, setColumnMappings] = useState({})
  const [uploading, setUploading] = useState(false)
  const [uploadResult, setUploadResult] = useState(null)

  useEffect(() => {
    axios.get('/api/client-portal/accounting').then(res => {
      setData(res.data)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  const loadStatements = () => {
    if (!orgId) return
    setStatementsLoading(true)
    axios.get(`/api/royalties/statements/${orgId}`)
      .then(res => {
        setStatements(Array.isArray(res.data) ? res.data : res.data.statements || [])
      })
      .catch(() => {})
      .finally(() => setStatementsLoading(false))
  }

  useEffect(() => { loadStatements() }, [orgId])

  const handlePreview = async () => {
    if (!uploadFile) return
    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', uploadFile)
      formData.append('source_name', uploadSourceType || uploadSource)
      const res = await axios.post(`/api/royalties/statements/${orgId}/preview`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      setPreviewData(res.data)
      if (res.data.detected_source_type) {
        setDetectedSourceType(res.data.detected_source_type)
      }
      const rawMapping = res.data.mapping || res.data.suggested_mappings || res.data.mappings || {}
      const inverted = {}
      Object.entries(rawMapping).forEach(([field, header]) => {
        if (header) inverted[header] = field
      })
      setColumnMappings(inverted)
      setUploadStep(2)
    } catch (err) {
      alert('Failed to preview file. Please check the format.')
    } finally {
      setUploading(false)
    }
  }

  const handleUpload = async () => {
    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', uploadFile)
      formData.append('source_name', uploadSource || uploadSourceType)
      formData.append('source_type', detectedSourceType || uploadSourceType || '')
      formData.append('period_start', uploadPeriodStart)
      formData.append('period_end', uploadPeriodEnd)
      formData.append('currency', uploadCurrency)
      const backendMapping = {}
      Object.entries(columnMappings).forEach(([header, field]) => {
        if (field) backendMapping[field] = header
      })
      formData.append('column_mapping', JSON.stringify(backendMapping))
      const res = await axios.post(`/api/royalties/statements/${orgId}/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      setUploadResult(res.data)
      setUploadStep(3)
      loadStatements()
      axios.get('/api/client-portal/accounting').then(r => setData(r.data)).catch(() => {})
    } catch (err) {
      alert('Failed to upload statement.')
    } finally {
      setUploading(false)
    }
  }

  const resetUpload = () => {
    setShowUpload(false)
    setUploadStep(1)
    setUploadFile(null)
    setUploadSource('')
    setUploadSourceType('')
    setDetectedSourceType(null)
    setUploadPeriodStart('')
    setUploadPeriodEnd('')
    setUploadCurrency('USD')
    setPreviewData(null)
    setColumnMappings({})
    setUploadResult(null)
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return '—'
    return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  }

  if (loading) return <LoadingSpinner />
  if (!data) return <EmptyState text="Could not load accounting data" />

  const totalRevenue = (data.total_revenue_cents || 0) / 100

  return (
    <div className="space-y-6">
      <div className="bg-gradient-to-r from-[#5B8A72] to-[#7BAF9E] rounded-xl p-6 text-white shadow-sm">
        <p className="text-white/80 text-sm mb-1">Total Revenue</p>
        <p className="text-3xl font-bold">${totalRevenue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
        <p className="text-white/60 text-xs mt-1">{data.transactions?.length || 0} transactions</p>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-[rgba(59,77,67,0.08)] p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-[#3D4A44]">Statements</h3>
          <button
            onClick={() => setShowUpload(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] font-medium"
          >
            <ArrowUpTrayIcon className="w-4 h-4" />
            Upload Statement
          </button>
        </div>

        {statementsLoading ? (
          <LoadingSpinner />
        ) : statements.length === 0 ? (
          <EmptyState text="No statements uploaded yet" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[600px]">
              <thead className="bg-[#F5F7F4]">
                <tr>
                  <th className="text-left px-4 py-2 text-xs font-semibold text-[#7A8580] uppercase">Source</th>
                  <th className="text-left px-4 py-2 text-xs font-semibold text-[#7A8580] uppercase">Period</th>
                  <th className="text-left px-4 py-2 text-xs font-semibold text-[#7A8580] uppercase">Status</th>
                  <th className="text-right px-4 py-2 text-xs font-semibold text-[#7A8580] uppercase">Revenue</th>
                  <th className="text-right px-4 py-2 text-xs font-semibold text-[#7A8580] uppercase">Matched</th>
                  <th className="text-left px-4 py-2 text-xs font-semibold text-[#7A8580] uppercase">Uploaded</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E5E8E3]">
                {statements.map(s => (
                  <tr key={s.id} className="hover:bg-[#FAFBF9]">
                    <td className="px-4 py-3 text-sm font-medium text-[#3D4A44]">{s.source_name || s.file_name || '—'}</td>
                    <td className="px-4 py-3 text-sm text-[#7A8580]">
                      {s.period_start ? `${formatDate(s.period_start)} – ${formatDate(s.period_end)}` : '—'}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex px-2 py-0.5 text-xs rounded-full font-medium ${STATEMENT_STATUS_COLORS[s.status] || 'bg-gray-100 text-gray-600'}`}>
                        {s.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-right font-medium text-[#3D4A44]">
                      ${((s.total_revenue_cents || 0) / 100).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td className="px-4 py-3 text-sm text-right text-[#7A8580]">
                      {s.matched_transactions || 0}/{s.total_transactions || 0}
                    </td>
                    <td className="px-4 py-3 text-sm text-[#7A8580]">{formatDate(s.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showUpload && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-6 border-b border-[#E5E8E3]">
              <h2 className="text-lg font-semibold text-[#3D4A44]">
                {uploadStep === 1 && 'Upload Statement'}
                {uploadStep === 2 && 'Map Columns'}
                {uploadStep === 3 && 'Upload Complete'}
              </h2>
              <button onClick={resetUpload} className="text-[#7A8580] hover:text-[#3D4A44]">
                <XMarkIcon className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-4">
              {uploadStep === 1 && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-[#3D4A44] mb-1">Statement File</label>
                    <input
                      type="file"
                      accept=".csv,.xlsx,.xls"
                      onChange={e => setUploadFile(e.target.files?.[0] || null)}
                      className="w-full text-sm border border-[#D1D5CE] rounded-lg px-3 py-2 file:mr-3 file:py-1 file:px-3 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-[#5B8A72] file:text-white hover:file:bg-[#4A7A62]"
                    />
                    <p className="text-xs text-[#7A8580] mt-1">CSV or Excel (.xlsx) files supported</p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-[#3D4A44] mb-1">Source Type</label>
                    <select
                      value={uploadSourceType}
                      onChange={e => setUploadSourceType(e.target.value)}
                      className="w-full border border-[#D1D5CE] rounded-lg px-3 py-2 text-sm"
                    >
                      {SOURCE_TYPE_OPTIONS.map(o => (
                        <option key={o.value} value={o.value}>{o.label}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-[#3D4A44] mb-1">Source Name</label>
                    <input
                      type="text"
                      value={uploadSource}
                      onChange={e => setUploadSource(e.target.value)}
                      placeholder="e.g., DistroKid Q1 2025"
                      className="w-full border border-[#D1D5CE] rounded-lg px-3 py-2 text-sm"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-sm font-medium text-[#3D4A44] mb-1">Period Start</label>
                      <input
                        type="date"
                        value={uploadPeriodStart}
                        onChange={e => setUploadPeriodStart(e.target.value)}
                        className="w-full border border-[#D1D5CE] rounded-lg px-3 py-2 text-sm"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-[#3D4A44] mb-1">Period End</label>
                      <input
                        type="date"
                        value={uploadPeriodEnd}
                        onChange={e => setUploadPeriodEnd(e.target.value)}
                        className="w-full border border-[#D1D5CE] rounded-lg px-3 py-2 text-sm"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-[#3D4A44] mb-1">Currency</label>
                    <select
                      value={uploadCurrency}
                      onChange={e => setUploadCurrency(e.target.value)}
                      className="w-full border border-[#D1D5CE] rounded-lg px-3 py-2 text-sm"
                    >
                      {CURRENCIES.map(c => <option key={c} value={c}>{c}</option>)}
                    </select>
                  </div>
                  <div className="flex justify-end gap-3 pt-2">
                    <button onClick={resetUpload} className="px-4 py-2 text-sm text-[#7A8580] hover:bg-[#EEF1EC] rounded-lg">
                      Cancel
                    </button>
                    <button
                      onClick={handlePreview}
                      disabled={!uploadFile || uploading}
                      className="px-4 py-2 text-sm bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] font-medium disabled:opacity-50"
                    >
                      {uploading ? 'Analyzing...' : 'Preview & Map Columns'}
                    </button>
                  </div>
                </>
              )}

              {uploadStep === 2 && previewData && (
                <>
                  <div className="bg-[#F5F7F4] rounded-lg p-3 text-sm text-[#3D4A44]">
                    <p><strong>{previewData.row_count}</strong> rows detected</p>
                    {detectedSourceType && (
                      <p className="text-[#5B8A72] mt-1">Detected source: <strong>{detectedSourceType}</strong></p>
                    )}
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-[#3D4A44] mb-2">Column Mapping</h4>
                    <p className="text-xs text-[#7A8580] mb-3">Map your file columns to the correct fields. Auto-detected mappings are pre-selected.</p>
                    <div className="space-y-2 max-h-60 overflow-y-auto">
                      {(previewData.headers || []).map(header => (
                        <div key={header} className="flex items-center gap-3">
                          <span className="text-sm text-[#3D4A44] w-40 truncate font-mono" title={header}>{header}</span>
                          <span className="text-[#7A8580]">→</span>
                          <select
                            value={columnMappings[header] || ''}
                            onChange={e => setColumnMappings(prev => ({ ...prev, [header]: e.target.value }))}
                            className="flex-1 border border-[#D1D5CE] rounded-lg px-2 py-1.5 text-sm"
                          >
                            {TARGET_FIELDS.map(f => (
                              <option key={f.value} value={f.value}>{f.label}</option>
                            ))}
                          </select>
                        </div>
                      ))}
                    </div>
                  </div>
                  {previewData.preview_rows?.length > 0 && (
                    <div>
                      <h4 className="text-sm font-semibold text-[#3D4A44] mb-2">Preview (first {previewData.preview_rows.length} rows)</h4>
                      <div className="overflow-x-auto border border-[#E5E8E3] rounded-lg">
                        <table className="w-full text-xs">
                          <thead className="bg-[#F5F7F4]">
                            <tr>
                              {(previewData.headers || []).slice(0, 6).map(h => (
                                <th key={h} className="px-2 py-1.5 text-left font-medium text-[#7A8580] whitespace-nowrap">{h}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-[#E5E8E3]">
                            {previewData.preview_rows.slice(0, 5).map((row, i) => (
                              <tr key={i}>
                                {(previewData.headers || []).slice(0, 6).map(h => (
                                  <td key={h} className="px-2 py-1.5 text-[#3D4A44] whitespace-nowrap max-w-[150px] truncate">{row[h] || ''}</td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                  <div className="flex justify-between pt-2">
                    <button onClick={() => setUploadStep(1)} className="px-4 py-2 text-sm text-[#7A8580] hover:bg-[#EEF1EC] rounded-lg">
                      Back
                    </button>
                    <button
                      onClick={handleUpload}
                      disabled={uploading}
                      className="px-4 py-2 text-sm bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] font-medium disabled:opacity-50"
                    >
                      {uploading ? 'Uploading...' : 'Confirm & Upload'}
                    </button>
                  </div>
                </>
              )}

              {uploadStep === 3 && uploadResult && (
                <div className="text-center space-y-4">
                  <CheckCircleIcon className="w-16 h-16 text-[#5B8A72] mx-auto" />
                  <h3 className="text-lg font-semibold text-[#3D4A44]">Statement Uploaded</h3>
                  <div className="bg-[#F5F7F4] rounded-lg p-4 text-sm space-y-1">
                    <p className="text-[#3D4A44]"><strong>{uploadResult.total_transactions}</strong> transactions processed</p>
                    <p className="text-green-700"><strong>{uploadResult.matched_transactions}</strong> matched</p>
                    {uploadResult.unmatched_transactions > 0 && (
                      <p className="text-amber-700"><strong>{uploadResult.unmatched_transactions}</strong> unmatched</p>
                    )}
                    <p className="text-[#3D4A44] font-medium mt-2">
                      Total Revenue: ${((uploadResult.total_revenue_cents || 0) / 100).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </p>
                  </div>
                  <button
                    onClick={resetUpload}
                    className="px-4 py-2 text-sm bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] font-medium"
                  >
                    Done
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {data.advances?.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-[rgba(59,77,67,0.08)] p-6 space-y-4">
          <h3 className="text-sm font-semibold text-[#3D4A44]">Advance Recoupment</h3>
          {data.advances.map(a => (
            <div key={a.contract_id} className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-[#3D4A44] font-medium">{a.contract_title}</span>
                <span className="text-[#7A8580]">
                  {a.currency} {a.advance_recouped.toLocaleString()} / {a.advance_amount.toLocaleString()}
                </span>
              </div>
              <div className="w-full bg-[#E5E8E3] rounded-full h-2.5">
                <div
                  className="bg-[#5B8A72] h-2.5 rounded-full transition-all"
                  style={{ width: `${Math.min(100, (a.advance_recouped / a.advance_amount) * 100)}%` }}
                />
              </div>
              <p className="text-xs text-[#7A8580]">Remaining: {a.currency} {a.remaining.toLocaleString()}</p>
            </div>
          ))}
        </div>
      )}

      <div className="bg-white rounded-xl shadow-sm border border-[rgba(59,77,67,0.08)] p-6 space-y-4">
        <h3 className="text-sm font-semibold text-[#3D4A44]">Transactions ({data.transactions?.length || 0})</h3>
        {data.transactions?.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[500px]">
              <thead className="bg-[#F5F7F4]">
                <tr>
                  <th className="text-left px-4 py-2 text-xs font-semibold text-[#7A8580] uppercase">Track</th>
                  <th className="text-left px-4 py-2 text-xs font-semibold text-[#7A8580] uppercase">Artist</th>
                  <th className="text-left px-4 py-2 text-xs font-semibold text-[#7A8580] uppercase">Platform</th>
                  <th className="text-left px-4 py-2 text-xs font-semibold text-[#7A8580] uppercase">Status</th>
                  <th className="text-right px-4 py-2 text-xs font-semibold text-[#7A8580] uppercase">Amount</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E5E8E3]">
                {data.transactions.slice(0, 50).map(tx => (
                  <tr key={tx.id} className="hover:bg-[#FAFBF9]">
                    <td className="px-4 py-2 text-sm text-[#3D4A44]">{tx.original_track_title || '-'}</td>
                    <td className="px-4 py-2 text-sm text-[#7A8580]">{tx.original_artist || '-'}</td>
                    <td className="px-4 py-2 text-sm text-[#7A8580]">{tx.platform || '-'}</td>
                    <td className="px-4 py-2">
                      <span className={`inline-flex px-2 py-0.5 text-xs rounded-full font-medium ${
                        tx.match_status === 'MATCHED' ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'
                      }`}>{tx.match_status}</span>
                    </td>
                    <td className="px-4 py-2 text-sm text-right text-[#3D4A44] font-medium">
                      ${((tx.revenue_amount_cents || 0) / 100).toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState text="No transactions yet" />
        )}
      </div>
    </div>
  )
}

function AccessTab() {
  const [links, setLinks] = useState([])
  const [loading, setLoading] = useState(true)
  const [accessCode, setAccessCode] = useState('')
  const [permission, setPermission] = useState('VIEW_ONLY')
  const [granting, setGranting] = useState(false)
  const [msg, setMsg] = useState(null)

  const fetchAccess = () => {
    axios.get('/api/client-portal/managed-access').then(res => {
      setLinks(res.data)
      setLoading(false)
    }).catch(() => setLoading(false))
  }

  useEffect(() => { fetchAccess() }, [])

  const handleGrant = async (e) => {
    e.preventDefault()
    setGranting(true)
    setMsg(null)
    try {
      await axios.post('/api/client-portal/grant-access', {
        access_code: accessCode,
        permission_level: permission,
      })
      setAccessCode('')
      setPermission('VIEW_ONLY')
      fetchAccess()
      setMsg({ type: 'success', text: 'Access granted successfully' })
    } catch (err) {
      setMsg({ type: 'error', text: err.response?.data?.detail || 'Failed to grant access' })
    } finally {
      setGranting(false)
    }
  }

  const handleRevoke = async (linkId) => {
    try {
      await axios.put(`/api/client-portal/revoke-access/${linkId}`)
      fetchAccess()
      setMsg({ type: 'success', text: 'Access revoked' })
    } catch {
      setMsg({ type: 'error', text: 'Failed to revoke access' })
    }
  }

  const permissionLabels = {
    VIEW_ONLY: 'View Only',
    EDIT: 'Edit Access',
    FULL_ACCESS: 'Full Access',
  }

  const permissionColors = {
    VIEW_ONLY: 'bg-gray-100 text-gray-600',
    EDIT: 'bg-blue-100 text-blue-700',
    FULL_ACCESS: 'bg-purple-100 text-purple-700',
  }

  if (loading) return <LoadingSpinner />

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl shadow-sm border border-[rgba(59,77,67,0.08)] p-6 space-y-4">
        <h2 className="text-lg font-semibold text-[#3D4A44]">Grant Company Access</h2>
        <p className="text-sm text-[#7A8580]">Allow a management company or label to access your catalog by entering their access code.</p>

        {msg && (
          <div className={`p-3 rounded-lg text-sm ${msg.type === 'error' ? 'bg-red-50 text-red-700' : 'bg-green-50 text-green-700'}`}>
            {msg.text}
          </div>
        )}

        <form onSubmit={handleGrant} className="flex flex-col sm:flex-row gap-3">
          <input
            type="text"
            required
            value={accessCode}
            onChange={(e) => setAccessCode(e.target.value.toUpperCase())}
            placeholder="Enter access code (e.g. AB12CD34)"
            className="flex-1 px-3 py-2 border border-[#D1D5CE] rounded-lg text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent font-mono tracking-wider"
          />
          <select
            value={permission}
            onChange={(e) => setPermission(e.target.value)}
            className="px-3 py-2 border border-[#D1D5CE] rounded-lg text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
          >
            <option value="VIEW_ONLY">View Only</option>
            <option value="EDIT">Edit Access</option>
            <option value="FULL_ACCESS">Full Access</option>
          </select>
          <button
            type="submit"
            disabled={granting}
            className="px-4 py-2 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] text-sm font-medium disabled:opacity-50 whitespace-nowrap"
          >
            {granting ? 'Granting...' : 'Grant Access'}
          </button>
        </form>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-[rgba(59,77,67,0.08)] p-6 space-y-4">
        <h2 className="text-lg font-semibold text-[#3D4A44]">Companies with Access ({links.length})</h2>
        {links.length === 0 ? (
          <EmptyState text="No companies have access to your catalog" />
        ) : (
          <div className="space-y-3">
            {links.map(link => (
              <div key={link.id} className="flex items-center justify-between p-4 border border-[#E5E8E3] rounded-xl">
                <div>
                  <p className="text-sm font-medium text-[#3D4A44]">{link.enterprise_org_name}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${permissionColors[link.permission_level] || 'bg-gray-100 text-gray-600'}`}>
                      {permissionLabels[link.permission_level] || link.permission_level}
                    </span>
                    <span className="text-xs text-[#A0A8A3]">{link.status}</span>
                  </div>
                </div>
                <button
                  onClick={() => handleRevoke(link.id)}
                  className="px-3 py-1.5 text-xs text-red-600 hover:bg-red-50 rounded-lg border border-red-200 transition-colors"
                >
                  Revoke
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

const DIR_ROLE_OPTIONS = ['Songwriter', 'Producer', 'Artist', 'Musician', 'Engineer', 'Featured Artist', 'Composer', 'Lyricist', 'Arranger', 'Manager', 'Lawyer', 'Publisher', 'A&R', 'Agent']

const DIR_ROLE_COLORS = {
  Songwriter: 'bg-blue-100 text-blue-700',
  Producer: 'bg-purple-100 text-purple-700',
  Artist: 'bg-green-100 text-green-700',
  Musician: 'bg-orange-100 text-orange-700',
  Engineer: 'bg-teal-100 text-teal-700',
  'Featured Artist': 'bg-pink-100 text-pink-700',
  Composer: 'bg-indigo-100 text-indigo-700',
  Lyricist: 'bg-yellow-100 text-yellow-700',
  Arranger: 'bg-red-100 text-red-700',
  Manager: 'bg-emerald-100 text-emerald-700',
  Lawyer: 'bg-slate-100 text-slate-700',
  Publisher: 'bg-cyan-100 text-cyan-700',
  'A&R': 'bg-violet-100 text-violet-700',
  Agent: 'bg-amber-100 text-amber-700',
}


function ClientsTab() {
  const [clients, setClients] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    axios.get('/api/client-portal/clients')
      .then(res => setClients(res.data.clients || []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-32">
        <div className="w-6 h-6 border-2 border-[#5B8A72] border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (clients.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-[rgba(59,77,67,0.08)] p-8 text-center">
        <UsersIcon className="w-12 h-12 text-[#B0BDB4] mx-auto mb-3" />
        <h3 className="text-lg font-semibold text-[#3D4A44] mb-1">No Other Clients</h3>
        <p className="text-sm text-[#7A8580]">There are no other client profiles to display.</p>
      </div>
    )
  }

  const ROLE_COLORS = {
    Songwriter: 'bg-blue-100 text-blue-700',
    Producer: 'bg-purple-100 text-purple-700',
    Artist: 'bg-green-100 text-green-700',
    Musician: 'bg-orange-100 text-orange-700',
    Engineer: 'bg-teal-100 text-teal-700',
    'Featured Artist': 'bg-pink-100 text-pink-700',
    Composer: 'bg-indigo-100 text-indigo-700',
    Lyricist: 'bg-yellow-100 text-yellow-700',
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      {clients.map(client => (
        <div key={client.id} className="bg-white rounded-xl shadow-sm border border-[rgba(59,77,67,0.08)] p-5 flex flex-col">
          <div className="flex items-center gap-3 mb-3">
            {client.hero_image_url ? (
              <img src={client.hero_image_url} alt="" className="w-12 h-12 rounded-full object-cover" />
            ) : (
              <div className="w-12 h-12 rounded-full bg-[#5B8A72]/10 flex items-center justify-center text-lg font-bold text-[#5B8A72]">
                {client.display_name?.charAt(0) || '?'}
              </div>
            )}
            <div className="flex-1 min-w-0">
              <h3 className="text-base font-semibold text-[#3D4A44] truncate">{client.display_name}</h3>
              {client.primary_territory && (
                <p className="text-xs text-[#7A8580]">{client.primary_territory}</p>
              )}
            </div>
          </div>
          {client.roles && client.roles.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-3">
              {client.roles.map(role => (
                <span key={role} className={`px-2 py-0.5 rounded-full text-xs font-medium ${ROLE_COLORS[role] || 'bg-gray-100 text-gray-700'}`}>
                  {role}
                </span>
              ))}
            </div>
          )}
          <div className="space-y-1 text-sm flex-1">
            {client.email && (
              <p className="text-[#7A8580] truncate">
                <a href={`mailto:${client.email}`} className="hover:text-[#5B8A72] transition-colors">{client.email}</a>
              </p>
            )}
            {client.primary_pro && (
              <p className="text-[#7A8580]">PRO: <span className="text-[#3D4A44]">{client.primary_pro}</span></p>
            )}
            {client.publisher_name && (
              <p className="text-[#7A8580]">Publisher: <span className="text-[#3D4A44]">{client.publisher_name}</span></p>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

function DirectoryTab() {
  const [contacts, setContacts] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [roleFilter, setRoleFilter] = useState('')

  useEffect(() => {
    loadContacts()
  }, [])

  async function loadContacts() {
    try {
      const res = await axios.get('/api/client-portal/shared-contacts')
      setContacts(res.data.contacts || [])
    } catch (err) {
      console.error('Failed to load shared contacts:', err)
    } finally {
      setLoading(false)
    }
  }

  const searched = searchTerm
    ? contacts.filter(c => {
        const term = searchTerm.toLowerCase()
        return (
          (c.display_name || '').toLowerCase().includes(term) ||
          (c.legal_name || '').toLowerCase().includes(term) ||
          (c.email || '').toLowerCase().includes(term) ||
          (c.publisher_name || '').toLowerCase().includes(term) ||
          (c.pro || '').toLowerCase().includes(term)
        )
      })
    : contacts
  const filtered = roleFilter ? searched.filter(c => c.roles && c.roles.includes(roleFilter)) : searched

  if (loading) return <LoadingSpinner />

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-xl shadow-sm border border-[rgba(59,77,67,0.08)] p-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-4">
          <h2 className="text-lg font-semibold text-[#3D4A44]">Shared Contacts ({contacts.length})</h2>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 mb-4">
          <div className="relative flex-1">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#7A8580]" />
            <input
              type="text"
              placeholder="Search contacts..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-4 py-2 border border-[#D1D5CE] rounded-lg text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
            />
          </div>
          <select
            value={roleFilter}
            onChange={e => setRoleFilter(e.target.value)}
            className="border border-[#D1D5CE] rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
          >
            <option value="">All Roles</option>
            {DIR_ROLE_OPTIONS.map(r => <option key={r} value={r}>{r}</option>)}
          </select>
        </div>

        {filtered.length === 0 ? (
          <EmptyState text={contacts.length === 0 ? "No contacts have been shared with you yet." : "No contacts match your filter."} />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filtered.map(contact => (
              <div key={contact.id} className="border border-[#E5E8E3] rounded-xl p-4 hover:shadow-sm transition-shadow flex flex-col">
                <div className="flex-1 min-w-0 mb-2">
                  <h3 className="text-sm font-semibold text-[#3D4A44] truncate">{contact.display_name}</h3>
                  {contact.legal_name && <p className="text-xs text-[#7A8580] truncate">{contact.legal_name}</p>}
                </div>

                {contact.roles && contact.roles.length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-2">
                    {contact.roles.map(role => (
                      <span key={role} className={`px-2 py-0.5 rounded-full text-xs font-medium ${DIR_ROLE_COLORS[role] || 'bg-gray-100 text-gray-700'}`}>
                        {role}
                      </span>
                    ))}
                  </div>
                )}

                <div className="space-y-1 text-xs text-[#7A8580] flex-1">
                  {contact.email && <p className="truncate">{contact.email}</p>}
                  {contact.phone && <p>{contact.phone}</p>}
                  {contact.pro && <p>PRO: <span className="text-[#3D4A44] font-medium">{contact.pro}</span>{contact.ipi ? ` · IPI: ${contact.ipi}` : ''}</p>}
                  {contact.publisher_name && <p>Publisher: <span className="text-[#3D4A44]">{contact.publisher_name}</span></p>}
                  {contact.representation_name && <p>Rep: <span className="text-[#3D4A44]">{contact.representation_name}</span></p>}
                  {contact.territory && <p>Territory: {contact.territory}</p>}
                </div>

                <div className="flex items-center gap-2 mt-3 pt-2 border-t border-[rgba(59,77,67,0.08)]">
                  <button
                    onClick={async () => {
                      try {
                        const res = await axios.get(`/api/creative-directory/${contact.id}/pdf`, { responseType: 'blob' })
                        const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
                        const link = document.createElement('a')
                        link.href = url
                        link.setAttribute('download', `Contact_Card_${contact.display_name.replace(/\s+/g, '_')}.pdf`)
                        document.body.appendChild(link)
                        link.click()
                        link.remove()
                        window.URL.revokeObjectURL(url)
                      } catch (err) {
                        alert('Failed to download contact card')
                      }
                    }}
                    className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-[#7A8580] hover:bg-[#EEF1EC] rounded-lg transition-colors ml-auto"
                  >
                    <ArrowDownTrayIcon className="w-3.5 h-3.5" />
                    PDF
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function CreditsTab({ organizationId, creatorId, creatorName }) {
  const [creditsData, setCreditsData] = useState(null)
  const [creditsLoading, setCreditsLoading] = useState(true)
  const [creditsSongs, setCreditsSongs] = useState([])
  const [creditsSongsLoading, setCreditsSongsLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [showShareModal, setShowShareModal] = useState(false)
  const [shareSettings, setShareSettings] = useState({ is_public: true, passcode: '' })
  const [shareResult, setShareResult] = useState(null)
  const [savingShare, setSavingShare] = useState(false)
  const [linkCopied, setLinkCopied] = useState(false)

  const PLATFORM_ICONS = {
    SPOTIFY: { color: '#1DB954', label: 'Spotify' },
    APPLE_MUSIC: { color: '#FA233B', label: 'Apple Music' },
    YOUTUBE_MUSIC: { color: '#FF0000', label: 'YouTube Music' },
    AMAZON_MUSIC: { color: '#FF9900', label: 'Amazon Music' },
    TIDAL: { color: '#000000', label: 'Tidal' },
    DEEZER: { color: '#A238FF', label: 'Deezer' },
  }

  const formatStreamCount = (num) => {
    if (!num || num === 0) return '0'
    if (num >= 1000000000) return (num / 1000000000).toFixed(1) + 'B'
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K'
    return num.toLocaleString()
  }

  const loadCreditsData = async () => {
    if (!organizationId) return
    setCreditsLoading(true)
    try {
      const res = await axios.get(`/api/streaming-credits/org/${organizationId}/creator/${creatorId}`)
      setCreditsData(res.data)
    } catch (err) {
      console.error('Failed to load credits:', err)
    } finally {
      setCreditsLoading(false)
    }
  }

  const loadCreditsSongs = async () => {
    if (!organizationId) return
    setCreditsSongsLoading(true)
    try {
      const res = await axios.get(`/api/streaming-credits/org/${organizationId}/creator/${creatorId}/songs?per_page=100`)
      setCreditsSongs(res.data.songs || [])
    } catch (err) {
      console.error('Failed to load credits songs:', err)
    } finally {
      setCreditsSongsLoading(false)
    }
  }

  useEffect(() => {
    loadCreditsData()
    loadCreditsSongs()
  }, [organizationId, creatorId])

  const handleRefresh = async () => {
    if (!organizationId) return
    setRefreshing(true)
    try {
      await axios.post(`/api/streaming-credits/org/${organizationId}/creator/${creatorId}/refresh`)
      await loadCreditsData()
      await loadCreditsSongs()
    } catch (err) {
      console.error('Failed to refresh credits:', err)
    } finally {
      setRefreshing(false)
    }
  }

  const handleShareCredits = async () => {
    if (!organizationId) return
    setSavingShare(true)
    try {
      const res = await axios.post(`/api/streaming-credits/org/${organizationId}/creator/${creatorId}/share`, {
        is_public: shareSettings.is_public,
        passcode: shareSettings.passcode || ''
      })
      setShareResult(res.data)
    } catch (err) {
      console.error('Failed to manage share link:', err)
    } finally {
      setSavingShare(false)
    }
  }

  const handleRevokeShare = async () => {
    if (!organizationId) return
    try {
      await axios.delete(`/api/streaming-credits/org/${organizationId}/creator/${creatorId}/share`)
      setShareResult(null)
      setShowShareModal(false)
    } catch (err) {
      console.error('Failed to revoke share link:', err)
    }
  }

  const handleCopyLink = () => {
    if (shareResult?.share_url) {
      navigator.clipboard.writeText(`${window.location.origin}${shareResult.share_url}`)
      setLinkCopied(true)
      setTimeout(() => setLinkCopied(false), 2000)
    }
  }

  if (creditsLoading) return <LoadingSpinner />

  const roleColors = {
    PRODUCER: { bg: 'rgba(91, 138, 114, 0.12)', text: '#5B8A72', border: 'rgba(91, 138, 114, 0.2)' },
    SONGWRITER: { bg: 'rgba(90, 138, 154, 0.12)', text: '#5A8A9A', border: 'rgba(90, 138, 154, 0.2)' },
    ARTIST: { bg: 'rgba(196, 149, 107, 0.12)', text: '#C4956B', border: 'rgba(196, 149, 107, 0.2)' },
    FEATURED_ARTIST: { bg: 'rgba(160, 32, 240, 0.12)', text: '#8B5CF6', border: 'rgba(160, 32, 240, 0.2)' },
    MIX_ENGINEER: { bg: 'rgba(123, 165, 148, 0.12)', text: '#7BA594', border: 'rgba(123, 165, 148, 0.2)' },
    OTHER: { bg: 'rgba(122, 133, 128, 0.12)', text: '#7A8580', border: 'rgba(122, 133, 128, 0.2)' },
  }

  return (
    <div className="space-y-4">
      <div className="bg-gradient-to-r from-[#5B8A72] to-[#3D6B4F] rounded-xl p-6 text-white shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold mb-1">Streaming Credits</h2>
            <p className="text-white/70 text-sm">Streaming intelligence & credit profile for {creatorName}</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-white/20 text-white rounded-lg hover:bg-white/30 transition-colors border border-white/30 disabled:opacity-50"
            >
              <svg className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              {refreshing ? 'Refreshing...' : 'Refresh'}
            </button>
            <button
              onClick={() => setShowShareModal(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-white text-[#5B8A72] rounded-lg hover:bg-white/90 transition-colors font-medium"
            >
              <ShareIcon className="w-4 h-4" />
              Share
            </button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-white rounded-xl shadow-sm border border-[rgba(59,77,67,0.08)] p-4">
          <p className="text-xs text-[#7A8580] mb-1">Total Credits</p>
          <p className="text-2xl font-bold text-[#3D4A44]">{creditsData?.total_credits || 0}</p>
        </div>
        <div className="bg-white rounded-xl shadow-sm border border-[rgba(59,77,67,0.08)] p-4">
          <p className="text-xs text-[#7A8580] mb-1">Total Estimated Streams</p>
          <p className="text-2xl font-bold text-[#5B8A72]">{formatStreamCount(creditsData?.total_estimated_streams || 0)}</p>
        </div>
        <div className="bg-white rounded-xl shadow-sm border border-[rgba(59,77,67,0.08)] p-4">
          <p className="text-xs text-[#7A8580] mb-1">Album Units (RIAA)</p>
          <p className="text-2xl font-bold text-[#5A8A9A]">{formatStreamCount(creditsData?.riaa_equivalents?.album_units || Math.floor((creditsData?.total_estimated_streams || 0) / 1500))}</p>
        </div>
        <div className="bg-white rounded-xl shadow-sm border border-[rgba(59,77,67,0.08)] p-4">
          <p className="text-xs text-[#7A8580] mb-1">Single Units (RIAA)</p>
          <p className="text-2xl font-bold text-[#7BA594]">{formatStreamCount(creditsData?.riaa_equivalents?.single_units || Math.floor((creditsData?.total_estimated_streams || 0) / 150))}</p>
        </div>
      </div>

      {creditsData?.platform_breakdown && Object.keys(creditsData.platform_breakdown).length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-[rgba(59,77,67,0.08)] p-6">
          <h3 className="text-sm font-semibold text-[#3D4A44] mb-3">Platform Breakdown</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            {Object.entries(creditsData.platform_breakdown).map(([platform, streamData]) => {
              const pInfo = PLATFORM_ICONS[platform] || { color: '#7A8580', label: platform }
              const streamCount = typeof streamData === 'object' && streamData !== null ? (streamData.streams || 0) : (streamData || 0)
              return (
                <div key={platform} className="flex items-center gap-2 p-3 rounded-lg bg-[#F5F7F4]">
                  <PlatformIcon platform={platform} size={24} />
                  <div className="min-w-0">
                    <p className="text-[10px] text-[#7A8580] truncate">{pInfo.label}</p>
                    <p className="text-xs font-semibold text-[#3D4A44]">{formatStreamCount(streamCount)}</p>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {creditsData?.role_breakdown && Object.keys(creditsData.role_breakdown).length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-[rgba(59,77,67,0.08)] p-6">
          <h3 className="text-sm font-semibold text-[#3D4A44] mb-3">Role Breakdown</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {Object.entries(creditsData.role_breakdown).map(([role, count]) => {
              const rc = roleColors[role] || roleColors.OTHER
              return (
                <div key={role} className="rounded-xl p-4 border" style={{ background: rc.bg, borderColor: rc.border }}>
                  <p className="text-2xl font-bold mb-0.5" style={{ color: rc.text }}>{count}</p>
                  <p className="text-xs font-medium" style={{ color: rc.text }}>{role.replace(/_/g, ' ')}</p>
                </div>
              )
            })}
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl shadow-sm border border-[rgba(59,77,67,0.08)] overflow-hidden">
        <div className="p-5 border-b border-[#E5E8E3]">
          <h3 className="text-sm font-semibold text-[#3D4A44]">Credited Songs</h3>
          <p className="text-xs text-[#7A8580] mt-0.5">Songs ranked by estimated total streams</p>
        </div>
        {creditsSongsLoading ? (
          <div className="p-8 text-center text-[#7A8580] text-sm">Loading songs...</div>
        ) : creditsSongs.length > 0 ? (
          <div className="divide-y divide-[#E5E8E3]">
            {creditsSongs.map((song, idx) => (
              <div key={song.song_id} className="flex items-center gap-3 px-5 py-3 hover:bg-[#FAFBF9] transition-colors">
                <span className="text-sm font-bold text-[#B0BDB4] w-6 text-right flex-shrink-0">{idx + 1}</span>
                <div className="w-9 h-9 rounded-lg bg-[#EEF1EC] flex items-center justify-center flex-shrink-0 overflow-hidden">
                  {song.artwork_url ? (
                    <img src={song.artwork_url} alt="" className="w-full h-full object-cover" />
                  ) : (
                    <MusicalNoteIcon className="w-4 h-4 text-[#7A8580]" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-[#3D4A44] truncate">{song.title}</p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <p className="text-xs text-[#7A8580] truncate">{song.artist}</p>
                    {song.role && (
                      <span className="px-1.5 py-0.5 rounded-full text-[10px] font-semibold bg-[#EEF1EC] text-[#5B8A72]">
                        {song.role.replace(/_/g, ' ')}
                      </span>
                    )}
                    {song.share_percentage && (
                      <span className="text-[10px] text-[#7A8580]">{song.share_percentage}%</span>
                    )}
                  </div>
                </div>
                <div className="text-right flex-shrink-0">
                  <p className="text-sm font-semibold text-[#3D4A44]">{formatStreamCount(song.total_streams)}</p>
                  <p className="text-[10px] text-[#7A8580]">streams</p>
                </div>
                {song.platforms && Object.keys(song.platforms).length > 0 && (
                  <div className="hidden md:flex items-center gap-1 flex-shrink-0 ml-1">
                    {Object.entries(song.platforms).map(([plat, platData]) => {
                      const pInfo = PLATFORM_ICONS[plat] || { color: '#7A8580', label: plat }
                      const platStreams = typeof platData === 'object' && platData !== null ? (platData.streams || 0) : (platData || 0)
                      return (
                        <div key={plat} className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-[#F5F7F4]" title={`${pInfo.label}: ${formatStreamCount(platStreams)}`}>
                          <PlatformIcon platform={plat} size={14} />
                          <span className="text-[10px] text-[#7A8580]">{formatStreamCount(platStreams)}</span>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="p-10 text-center">
            <MusicalNoteIcon className="w-10 h-10 text-[#C7C7CC] mx-auto mb-3" />
            <h3 className="text-sm font-medium text-[#3D4A44] mb-1">No credits data yet</h3>
            <p className="text-xs text-[#7A8580]">Credits are computed from song credits and streaming data. Click "Refresh" to generate.</p>
          </div>
        )}
      </div>

      <p className="text-[10px] text-[#B0BDB4] text-center italic">
        Stream estimates are derived from chart data, market-share ratios, and available platform data. Actual numbers may vary.
      </p>

      {showShareModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md">
            <div className="flex items-center justify-between p-6 border-b border-[#E5E8E3]">
              <h2 className="text-lg font-semibold text-[#3D4A44]">Share Credits Profile</h2>
              <button onClick={() => setShowShareModal(false)} className="text-[#7A8580] hover:text-[#3D4A44]">
                <XMarkIcon className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-[#3D4A44]">Public Access</p>
                  <p className="text-xs text-[#7A8580]">Allow anyone with the link to view</p>
                </div>
                <button
                  onClick={() => setShareSettings(prev => ({ ...prev, is_public: !prev.is_public }))}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${shareSettings.is_public ? 'bg-[#5B8A72]' : 'bg-[#D1D5DB]'}`}
                >
                  <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${shareSettings.is_public ? 'translate-x-6' : 'translate-x-1'}`} />
                </button>
              </div>
              <div>
                <label className="block text-xs font-medium text-[#7A8580] mb-1">Passcode (optional)</label>
                <input
                  type="text"
                  value={shareSettings.passcode}
                  onChange={(e) => setShareSettings(prev => ({ ...prev, passcode: e.target.value }))}
                  placeholder="Leave empty for no passcode"
                  className="w-full px-3 py-2 border border-[#D1D5CE] rounded-lg text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                />
              </div>
              {shareResult && (
                <div className="bg-[#F5F7F4] rounded-xl p-4">
                  <p className="text-xs text-[#7A8580] mb-2">Share Link</p>
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      readOnly
                      value={`${window.location.origin}${shareResult.share_url}`}
                      className="flex-1 px-3 py-2 bg-white border border-[#E5E8E3] rounded-lg text-sm text-[#3D4A44]"
                    />
                    <button
                      onClick={handleCopyLink}
                      className="px-3 py-2 bg-[#5B8A72] text-white rounded-lg text-sm font-medium hover:bg-[#4A7A62] transition-colors"
                    >
                      {linkCopied ? 'Copied!' : 'Copy'}
                    </button>
                  </div>
                  {shareResult.has_passcode && (
                    <p className="text-xs text-[#7A8580] mt-2">Passcode protected</p>
                  )}
                </div>
              )}
            </div>
            <div className="flex items-center justify-between p-6 border-t border-[#E5E8E3]">
              {shareResult ? (
                <button
                  onClick={handleRevokeShare}
                  className="text-sm text-red-600 hover:text-red-700 font-medium"
                >
                  Revoke Link
                </button>
              ) : <div />}
              <div className="flex gap-2">
                <button onClick={() => setShowShareModal(false)} className="px-3 py-1.5 text-sm text-[#7A8580] hover:bg-[#EEF1EC] rounded-lg">
                  Cancel
                </button>
                <button
                  onClick={handleShareCredits}
                  disabled={savingShare}
                  className="px-4 py-2 text-sm bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] disabled:opacity-50 font-medium"
                >
                  {savingShare ? 'Saving...' : shareResult ? 'Update' : 'Generate Link'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center h-32">
      <div className="w-6 h-6 border-2 border-[#5B8A72] border-t-transparent rounded-full animate-spin" />
    </div>
  )
}

function EmptyState({ text }) {
  return (
    <div className="text-center py-12 text-[#7A8580]">
      <p className="text-sm">{text}</p>
    </div>
  )
}
