import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import axios from 'axios'
import {
  UserGroupIcon, PlusIcon, MagnifyingGlassIcon, XMarkIcon,
  PencilIcon, TrashIcon, ArrowDownTrayIcon, ArrowPathIcon, LinkIcon
} from '@heroicons/react/24/outline'

const PRO_OPTIONS = ['BMI', 'ASCAP', 'SESAC', 'SOCAN', 'PRS', 'GEMA', 'SACEM', 'SIAE', 'JASRAC', 'Other']
const ROLE_OPTIONS = ['Songwriter', 'Producer', 'Artist', 'Musician', 'Engineer', 'Featured Artist', 'Composer', 'Lyricist', 'Arranger']

const ROLE_COLORS = {
  Songwriter: 'bg-blue-100 text-blue-700',
  Producer: 'bg-purple-100 text-purple-700',
  Artist: 'bg-green-100 text-green-700',
  Musician: 'bg-orange-100 text-orange-700',
  Engineer: 'bg-teal-100 text-teal-700',
  'Featured Artist': 'bg-pink-100 text-pink-700',
  Composer: 'bg-indigo-100 text-indigo-700',
  Lyricist: 'bg-yellow-100 text-yellow-700',
  Arranger: 'bg-red-100 text-red-700',
}

const emptyForm = {
  display_name: '', legal_name: '', email: '', phone: '',
  pro: '', ipi: '', isni: '',
  publisher_name: '', publisher_ipi: '', publisher_pro: '',
  roles: [],
  representation_name: '', representation_email: '', representation_phone: '',
  territory: '', notes: ''
}

function ContactFormModal({ isOpen, onClose, onSubmit, initialData, title, loading }) {
  const [form, setForm] = useState({ ...emptyForm })

  useEffect(() => {
    if (isOpen) {
      setForm(initialData ? { ...emptyForm, ...initialData, roles: initialData.roles || [] } : { ...emptyForm })
    }
  }, [isOpen, initialData])

  const handleRoleToggle = (role) => {
    setForm(prev => ({
      ...prev,
      roles: prev.roles.includes(role)
        ? prev.roles.filter(r => r !== role)
        : [...prev.roles, role]
    }))
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!form.display_name.trim()) return
    onSubmit(form)
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b border-[rgba(59,77,67,0.12)]">
          <h2 className="text-xl font-bold text-[#3D4A44]">{title}</h2>
          <button onClick={onClose} className="w-9 h-9 flex items-center justify-center rounded-full text-[#7A8580] hover:text-[#3D4A44] hover:bg-[#EEF1EC] transition-colors">
            <XMarkIcon className="w-5 h-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-[#3D4A44] mb-1">Display Name *</label>
              <input type="text" required value={form.display_name} onChange={e => setForm(p => ({ ...p, display_name: e.target.value }))} className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]" />
            </div>
            <div>
              <label className="block text-sm font-medium text-[#3D4A44] mb-1">Legal Name</label>
              <input type="text" value={form.legal_name} onChange={e => setForm(p => ({ ...p, legal_name: e.target.value }))} className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]" />
            </div>
            <div>
              <label className="block text-sm font-medium text-[#3D4A44] mb-1">Email</label>
              <input type="email" value={form.email} onChange={e => setForm(p => ({ ...p, email: e.target.value }))} className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]" />
            </div>
            <div>
              <label className="block text-sm font-medium text-[#3D4A44] mb-1">Phone</label>
              <input type="text" value={form.phone} onChange={e => setForm(p => ({ ...p, phone: e.target.value }))} className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]" />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-[#3D4A44] mb-1">PRO</label>
              <select value={form.pro} onChange={e => setForm(p => ({ ...p, pro: e.target.value }))} className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]">
                <option value="">Select PRO</option>
                {PRO_OPTIONS.map(o => <option key={o} value={o}>{o}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-[#3D4A44] mb-1">IPI</label>
              <input type="text" value={form.ipi} onChange={e => setForm(p => ({ ...p, ipi: e.target.value }))} className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]" />
            </div>
            <div>
              <label className="block text-sm font-medium text-[#3D4A44] mb-1">ISNI</label>
              <input type="text" value={form.isni} onChange={e => setForm(p => ({ ...p, isni: e.target.value }))} className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]" />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-[#3D4A44] mb-1">Publisher Name</label>
              <input type="text" value={form.publisher_name} onChange={e => setForm(p => ({ ...p, publisher_name: e.target.value }))} className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]" />
            </div>
            <div>
              <label className="block text-sm font-medium text-[#3D4A44] mb-1">Publisher IPI</label>
              <input type="text" value={form.publisher_ipi} onChange={e => setForm(p => ({ ...p, publisher_ipi: e.target.value }))} className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]" />
            </div>
            <div>
              <label className="block text-sm font-medium text-[#3D4A44] mb-1">Publisher PRO</label>
              <select value={form.publisher_pro} onChange={e => setForm(p => ({ ...p, publisher_pro: e.target.value }))} className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]">
                <option value="">Select PRO</option>
                {PRO_OPTIONS.map(o => <option key={o} value={o}>{o}</option>)}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-[#3D4A44] mb-2">Roles</label>
            <div className="flex flex-wrap gap-2">
              {ROLE_OPTIONS.map(role => (
                <button
                  key={role}
                  type="button"
                  onClick={() => handleRoleToggle(role)}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors border ${
                    form.roles.includes(role)
                      ? 'bg-[#5B8A72] text-white border-[#5B8A72]'
                      : 'bg-white text-[#7A8580] border-[rgba(59,77,67,0.12)] hover:border-[#5B8A72] hover:text-[#5B8A72]'
                  }`}
                >
                  {role}
                </button>
              ))}
            </div>
          </div>

          <div className="border-t border-[rgba(59,77,67,0.12)] pt-4">
            <h3 className="text-sm font-semibold text-[#3D4A44] mb-3">Representation</h3>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Name</label>
                <input type="text" value={form.representation_name} onChange={e => setForm(p => ({ ...p, representation_name: e.target.value }))} className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]" />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Email</label>
                <input type="email" value={form.representation_email} onChange={e => setForm(p => ({ ...p, representation_email: e.target.value }))} className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]" />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Phone</label>
                <input type="text" value={form.representation_phone} onChange={e => setForm(p => ({ ...p, representation_phone: e.target.value }))} className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]" />
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-[#3D4A44] mb-1">Territory</label>
              <input type="text" value={form.territory} onChange={e => setForm(p => ({ ...p, territory: e.target.value }))} className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]" placeholder="e.g. United States" />
            </div>
            <div>
              <label className="block text-sm font-medium text-[#3D4A44] mb-1">Notes</label>
              <input type="text" value={form.notes} onChange={e => setForm(p => ({ ...p, notes: e.target.value }))} className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]" />
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm font-medium text-[#7A8580] hover:text-[#3D4A44] transition-colors">Cancel</button>
            <button type="submit" disabled={loading || !form.display_name.trim()} className="px-5 py-2 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] transition-colors text-sm font-medium disabled:opacity-50">
              {loading ? 'Saving...' : 'Save Contact'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function CreativeDirectoryPage() {
  const [contacts, setContacts] = useState([])
  const [loading, setLoading] = useState(true)
  const [organizationId, setOrganizationId] = useState(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [roleFilter, setRoleFilter] = useState('')
  const [showAddModal, setShowAddModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [editingContact, setEditingContact] = useState(null)
  const [saving, setSaving] = useState(false)
  const [syncing, setSyncing] = useState(false)

  useEffect(() => {
    loadData()
  }, [])

  async function loadData() {
    try {
      const orgRes = await axios.get('/api/organizations/current')
      const orgId = orgRes.data?.id
      if (!orgId) { setLoading(false); return }
      setOrganizationId(orgId)
      await loadContacts(orgId)
    } catch (error) {
      console.error('Failed to load directory:', error)
    } finally {
      setLoading(false)
    }
  }

  async function loadContacts(orgId, search) {
    try {
      const params = search ? `?search=${encodeURIComponent(search)}` : ''
      const res = await axios.get(`/api/creative-directory/org/${orgId || organizationId}${params}`)
      setContacts(Array.isArray(res.data) ? res.data : res.data.contacts || [])
    } catch (error) {
      console.error('Failed to load contacts:', error)
    }
  }

  async function handleCreate(form) {
    if (!organizationId) return
    setSaving(true)
    try {
      await axios.post(`/api/creative-directory/org/${organizationId}`, form)
      setShowAddModal(false)
      await loadContacts(organizationId)
    } catch (error) {
      console.error('Failed to create contact:', error)
      alert(error.response?.data?.detail || 'Failed to create contact')
    } finally {
      setSaving(false)
    }
  }

  async function handleUpdate(form) {
    if (!editingContact) return
    setSaving(true)
    try {
      await axios.put(`/api/creative-directory/${editingContact.id}`, form)
      setShowEditModal(false)
      setEditingContact(null)
      await loadContacts(organizationId)
    } catch (error) {
      console.error('Failed to update contact:', error)
      alert(error.response?.data?.detail || 'Failed to update contact')
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(contact) {
    if (!window.confirm(`Delete "${contact.display_name}" from your directory?`)) return
    try {
      await axios.delete(`/api/creative-directory/${contact.id}`)
      await loadContacts(organizationId)
    } catch (error) {
      console.error('Failed to delete contact:', error)
    }
  }

  async function handleSync() {
    if (!organizationId) return
    setSyncing(true)
    try {
      const res = await axios.get(`/api/creative-directory/org/${organizationId}/sync-creators`)
      const count = res.data?.synced || res.data?.created || 0
      alert(`Synced ${count} creator(s) from your roster.`)
      await loadContacts(organizationId)
    } catch (error) {
      console.error('Failed to sync from roster:', error)
      alert(error.response?.data?.detail || 'Failed to sync from roster')
    } finally {
      setSyncing(false)
    }
  }

  function openEdit(contact) {
    setEditingContact(contact)
    setShowEditModal(true)
  }

  useEffect(() => {
    if (!organizationId) return
    const timer = setTimeout(() => {
      loadContacts(organizationId, searchTerm)
    }, 300)
    return () => clearTimeout(timer)
  }, [searchTerm, organizationId])

  const filteredContacts = roleFilter
    ? contacts.filter(c => c.roles && c.roles.includes(roleFilter))
    : contacts

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-[#7A8580]">Loading directory...</div>
      </div>
    )
  }

  return (
    <div className="p-4 sm:p-8">
      <div className="bg-gradient-to-r from-[#5B8A72] to-[#7A8580] rounded-2xl p-6 sm:p-8 mb-6 text-white">
        <div className="flex items-center gap-3 mb-2">
          <UserGroupIcon className="w-8 h-8" />
          <h1 className="text-2xl sm:text-3xl font-bold">Creative Directory</h1>
        </div>
        <p className="text-white/80 text-sm sm:text-base">Your collaborator contact cards</p>
      </div>

      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <div className="relative flex-1">
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-[#7A8580]" />
          <input
            type="text"
            placeholder="Search by name..."
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 border border-[rgba(59,77,67,0.12)] rounded-xl bg-white text-[#3D4A44] focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
          />
        </div>
        <select
          value={roleFilter}
          onChange={e => setRoleFilter(e.target.value)}
          className="border border-[rgba(59,77,67,0.12)] rounded-xl px-3 py-2.5 bg-white text-[#3D4A44] focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
        >
          <option value="">All Roles</option>
          {ROLE_OPTIONS.map(r => <option key={r} value={r}>{r}</option>)}
        </select>
        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 px-4 py-2.5 bg-[#5B8A72] text-white rounded-xl hover:bg-[#4A7A62] transition-colors font-medium text-sm"
        >
          <PlusIcon className="w-5 h-5" />
          Add Contact
        </button>
        <button
          onClick={handleSync}
          disabled={syncing}
          className="flex items-center gap-2 px-4 py-2.5 bg-white border border-[rgba(59,77,67,0.12)] text-[#3D4A44] rounded-xl hover:bg-[#EEF1EC] transition-colors font-medium text-sm disabled:opacity-50"
        >
          <ArrowPathIcon className={`w-5 h-5 ${syncing ? 'animate-spin' : ''}`} />
          {syncing ? 'Syncing...' : 'Sync from Roster'}
        </button>
      </div>

      {filteredContacts.length === 0 ? (
        <div className="bg-white rounded-2xl border border-[rgba(59,77,67,0.12)] p-12 text-center">
          <UserGroupIcon className="w-12 h-12 text-[#B0BDB4] mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-[#3D4A44] mb-1">No contacts found</h3>
          <p className="text-sm text-[#7A8580]">Add your first collaborator or sync from your roster.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filteredContacts.map(contact => (
            <div key={contact.id} className="bg-white rounded-2xl border border-[rgba(59,77,67,0.12)] p-5 hover:shadow-md transition-shadow flex flex-col">
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1 min-w-0">
                  <h3 className="text-lg font-bold text-[#3D4A44] truncate">{contact.display_name}</h3>
                  {contact.legal_name && (
                    <p className="text-sm text-[#7A8580] truncate">{contact.legal_name}</p>
                  )}
                </div>
                {contact.creator_id && (
                  <Link
                    to={`/roster/${contact.creator_id}`}
                    className="flex items-center gap-1 px-2 py-1 bg-[#5B8A72]/10 text-[#5B8A72] rounded-full text-xs font-medium hover:bg-[#5B8A72]/20 transition-colors flex-shrink-0 ml-2"
                  >
                    <LinkIcon className="w-3 h-3" />
                    Roster
                  </Link>
                )}
              </div>

              {contact.roles && contact.roles.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mb-3">
                  {contact.roles.map(role => (
                    <span key={role} className={`px-2 py-0.5 rounded-full text-xs font-medium ${ROLE_COLORS[role] || 'bg-gray-100 text-gray-700'}`}>
                      {role}
                    </span>
                  ))}
                </div>
              )}

              <div className="space-y-1.5 text-sm flex-1">
                {(contact.pro || contact.ipi) && (
                  <p className="text-[#3D4A44]">
                    {contact.pro && <span className="font-medium">{contact.pro}</span>}
                    {contact.pro && contact.ipi && <span className="text-[#B0BDB4] mx-1">·</span>}
                    {contact.ipi && <span className="text-[#7A8580]">IPI: {contact.ipi}</span>}
                  </p>
                )}
                {contact.publisher_name && (
                  <p className="text-[#7A8580]">Publisher: <span className="text-[#3D4A44]">{contact.publisher_name}</span></p>
                )}
                {contact.email && (
                  <p className="text-[#7A8580] truncate">
                    <a href={`mailto:${contact.email}`} className="hover:text-[#5B8A72] transition-colors">{contact.email}</a>
                  </p>
                )}
                {contact.representation_name && (
                  <p className="text-[#7A8580]">Rep: <span className="text-[#3D4A44]">{contact.representation_name}</span></p>
                )}
                {contact.territory && (
                  <p className="text-[#7A8580]">Territory: <span className="text-[#3D4A44]">{contact.territory}</span></p>
                )}
              </div>

              <div className="flex items-center gap-2 mt-4 pt-3 border-t border-[rgba(59,77,67,0.08)]">
                <button
                  onClick={() => openEdit(contact)}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-[#5B8A72] hover:bg-[#5B8A72]/10 rounded-lg transition-colors"
                >
                  <PencilIcon className="w-3.5 h-3.5" />
                  Edit
                </button>
                <button
                  onClick={() => handleDelete(contact)}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                >
                  <TrashIcon className="w-3.5 h-3.5" />
                  Delete
                </button>
                <button
                  onClick={async () => {
                    try {
                      const res = await axios.get(`/api/creative-directory/${contact.id}/pdf`, { responseType: 'blob' })
                      const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
                      const link = document.createElement('a')
                      link.href = url
                      link.setAttribute('download', `Creative_Card_${contact.display_name.replace(/\s+/g, '_')}.pdf`)
                      document.body.appendChild(link)
                      link.click()
                      link.remove()
                      window.URL.revokeObjectURL(url)
                    } catch (err) {
                      console.error('Failed to download PDF:', err)
                      alert('Failed to download creative card PDF')
                    }
                  }}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-[#7A8580] hover:bg-[#EEF1EC] rounded-lg transition-colors ml-auto"
                >
                  <ArrowDownTrayIcon className="w-3.5 h-3.5" />
                  PDF
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <ContactFormModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onSubmit={handleCreate}
        initialData={null}
        title="Add Contact"
        loading={saving}
      />

      <ContactFormModal
        isOpen={showEditModal}
        onClose={() => { setShowEditModal(false); setEditingContact(null) }}
        onSubmit={handleUpdate}
        initialData={editingContact}
        title="Edit Contact"
        loading={saving}
      />
    </div>
  )
}
