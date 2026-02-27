import React, { useState, useEffect } from 'react'
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
} from '@heroicons/react/24/outline'

const TABS = [
  { key: 'profile', label: 'Profile', icon: UserCircleIcon },
  { key: 'catalog', label: 'Catalog', icon: MusicalNoteIcon },
  { key: 'placements', label: 'Placements', icon: FilmIcon },
  { key: 'contracts', label: 'Contracts', icon: ClipboardDocumentListIcon },
  { key: 'accounting', label: 'Accounting', icon: BanknotesIcon },
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
          {TABS.map(tab => {
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
      {activeTab === 'catalog' && <CatalogTab />}
      {activeTab === 'placements' && <PlacementsTab />}
      {activeTab === 'contracts' && <ContractsTab />}
      {activeTab === 'accounting' && <AccountingTab />}
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
        <Field label="Publisher" field="publisher_name" />
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
  )
}

function CatalogTab() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [view, setView] = useState('songs')

  useEffect(() => {
    axios.get('/api/client-portal/catalog').then(res => {
      setData(res.data)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  if (loading) return <LoadingSpinner />
  if (!data) return <EmptyState text="Could not load catalog" />

  return (
    <div className="bg-white rounded-xl shadow-sm border border-[rgba(59,77,67,0.08)] p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-[#3D4A44]">My Catalog</h2>
        <div className="flex bg-[#F5F7F4] rounded-lg p-0.5">
          <button onClick={() => setView('songs')} className={`px-3 py-1.5 text-sm rounded-md transition-colors ${view === 'songs' ? 'bg-white text-[#3D4A44] shadow-sm font-medium' : 'text-[#7A8580]'}`}>
            Songs ({data.songs?.length || 0})
          </button>
          <button onClick={() => setView('works')} className={`px-3 py-1.5 text-sm rounded-md transition-colors ${view === 'works' ? 'bg-white text-[#3D4A44] shadow-sm font-medium' : 'text-[#7A8580]'}`}>
            Works ({data.works?.length || 0})
          </button>
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
                <tr key={s.id} className="hover:bg-[#FAFBF9]">
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

function ContractsTab() {
  const [contracts, setContracts] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    axios.get('/api/client-portal/contracts').then(res => {
      setContracts(res.data)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  const statusColors = {
    DRAFT: 'bg-gray-100 text-gray-600',
    ACTIVE: 'bg-green-100 text-green-700',
    EXPIRED: 'bg-red-100 text-red-600',
    TERMINATED: 'bg-red-100 text-red-600',
  }

  if (loading) return <LoadingSpinner />

  return (
    <div className="bg-white rounded-xl shadow-sm border border-[rgba(59,77,67,0.08)] p-6 space-y-4">
      <h2 className="text-lg font-semibold text-[#3D4A44]">Contracts ({contracts.length})</h2>
      {contracts.length === 0 ? (
        <EmptyState text="No contracts linked to your profile" />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {contracts.map(c => (
            <div key={c.id} className="border border-[#E5E8E3] rounded-xl p-4 hover:shadow-sm transition-shadow">
              <div className="flex items-start justify-between mb-2">
                <h3 className="text-sm font-semibold text-[#3D4A44]">{c.title}</h3>
                <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${statusColors[c.status] || 'bg-gray-100 text-gray-600'}`}>
                  {c.status}
                </span>
              </div>
              <div className="space-y-1 text-xs text-[#7A8580]">
                <p>Type: {c.contract_type}</p>
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
  )
}

function AccountingTab() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    axios.get('/api/client-portal/accounting').then(res => {
      setData(res.data)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

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
  const [orgName, setOrgName] = useState('')
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
        organization_name: orgName,
        permission_level: permission,
      })
      setOrgName('')
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
        <p className="text-sm text-[#7A8580]">Allow a management company or label to access your catalog by entering their organization name.</p>

        {msg && (
          <div className={`p-3 rounded-lg text-sm ${msg.type === 'error' ? 'bg-red-50 text-red-700' : 'bg-green-50 text-green-700'}`}>
            {msg.text}
          </div>
        )}

        <form onSubmit={handleGrant} className="flex flex-col sm:flex-row gap-3">
          <input
            type="text"
            required
            value={orgName}
            onChange={(e) => setOrgName(e.target.value)}
            placeholder="Organization name"
            className="flex-1 px-3 py-2 border border-[#D1D5CE] rounded-lg text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
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
