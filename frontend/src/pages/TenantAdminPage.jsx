import React, { useState, useEffect, useCallback } from 'react'
import axios from 'axios'
import {
  UsersIcon,
  PlusIcon,
  PencilIcon,
  TrashIcon,
  KeyIcon,
  XMarkIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  PhotoIcon,
  SwatchIcon,
  UserGroupIcon,
  BuildingOfficeIcon,
  EyeIcon,
  EyeSlashIcon,
  ClipboardDocumentListIcon,
  ShareIcon,
  EnvelopeIcon,
} from '@heroicons/react/24/outline'
import ClientSharingTab from '../components/ClientSharingModal'
import EmailSendModal from '../components/EmailSendModal'

export default function TenantAdminPage() {
  const [activeTab, setActiveTab] = useState('members')
  const [members, setMembers] = useState([])
  const [creators, setCreators] = useState([])
  const [branding, setBranding] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [message, setMessage] = useState(null)

  const [showAddModal, setShowAddModal] = useState(false)
  const [showClientModal, setShowClientModal] = useState(false)
  const [editingMember, setEditingMember] = useState(null)
  const [resetPasswordUser, setResetPasswordUser] = useState(null)
  const [assignCreatorsUser, setAssignCreatorsUser] = useState(null)
  const [showInviteModal, setShowInviteModal] = useState(false)
  const [inviteSending, setInviteSending] = useState(false)
  const [inviteResult, setInviteResult] = useState(null)
  const [orgId, setOrgId] = useState(null)

  const showMsg = (text, isError = false) => {
    if (isError) setError(text)
    else setMessage(text)
    setTimeout(() => { setError(null); setMessage(null) }, 3000)
  }

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const [membersRes, brandingRes] = await Promise.all([
        axios.get('/api/tenant-admin/members'),
        axios.get('/api/tenant-admin/branding')
      ])
      setMembers(membersRes.data)
      setBranding(brandingRes.data)

      try {
        const orgRes = await axios.get('/api/organizations/current')
        if (orgRes.data?.id) setOrgId(orgRes.data.id)
      } catch {}

      try {
        const creatorsRes = await axios.get('/api/tenant-admin/creators')
        setCreators(creatorsRes.data)
      } catch { setCreators([]) }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  const handleToggleRoster = async (userId, value) => {
    try {
      await axios.patch(`/api/tenant-admin/members/${userId}/permissions`, { can_manage_roster: value })
      setMembers(prev => prev.map(m => m.id === userId ? { ...m, can_manage_roster: value } : m))
      showMsg(value ? 'Roster access granted' : 'Roster access revoked')
    } catch (err) {
      showMsg(err.response?.data?.detail || 'Failed to update permissions', true)
    }
  }

  const handleInviteUser = async ({ to, subject, message }) => {
    if (!orgId) return
    setInviteSending(true)
    setInviteResult(null)
    try {
      await axios.post(`/api/tenant-admin/org/${orgId}/invite`, {
        email: to,
        subject,
        message
      })
      setInviteResult({ success: true, message: 'Invitation sent successfully!' })
    } catch (err) {
      setInviteResult({ success: false, message: err.response?.data?.detail || 'Failed to send invitation' })
    } finally {
      setInviteSending(false)
    }
  }

  const handleDeleteMember = async (userId, username) => {
    if (!confirm(`Remove ${username} from this organization?`)) return
    try {
      await axios.delete(`/api/tenant-admin/members/${userId}`)
      showMsg(`${username} removed`)
      fetchData()
    } catch (err) {
      showMsg(err.response?.data?.detail || 'Failed to remove member', true)
    }
  }

  const tabs = [
    { id: 'members', label: 'Team Members', icon: UsersIcon },
    { id: 'branding', label: 'Organization Branding', icon: BuildingOfficeIcon },
    { id: 'sharing', label: 'Client Sharing', icon: ShareIcon },
    { id: 'audit', label: 'Activity Log', icon: ClipboardDocumentListIcon },
  ]

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#5B8A72]" />
      </div>
    )
  }

  return (
    <div className="p-4 lg:p-8 max-w-7xl mx-auto overflow-hidden">
      <div className="mb-8">
        <h1 className="text-[28px] font-bold text-[#3D4A44] truncate">Organization Admin</h1>
        <p className="text-[15px] text-[#7A8580] mt-1">Manage your team, branding, and client assignments</p>
      </div>

      {(message || error) && (
        <div className={`mb-4 p-3 rounded-lg flex items-center gap-2 ${error ? 'bg-red-50 text-red-700' : 'bg-green-50 text-green-700'}`}>
          {error ? <ExclamationTriangleIcon className="w-5 h-5" /> : <CheckCircleIcon className="w-5 h-5" />}
          <span className="text-sm">{message || error}</span>
        </div>
      )}

      <div className="flex gap-2 mb-6 border-b border-[#E5E8E3] overflow-x-auto -mx-4 px-4 lg:mx-0 lg:px-0">
        {tabs.map(tab => {
          const Icon = tab.icon
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap flex-shrink-0 ${
                activeTab === tab.id
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

      {activeTab === 'members' && (
        <MembersTab
          members={members}
          creators={creators}
          onAdd={() => { setEditingMember(null); setShowAddModal(true) }}
          onEdit={(m) => { setEditingMember(m); setShowAddModal(true) }}
          onDelete={handleDeleteMember}
          onResetPassword={setResetPasswordUser}
          onAssignCreators={setAssignCreatorsUser}
          onToggleRoster={handleToggleRoster}
          onInvite={() => { setShowInviteModal(true); setInviteResult(null) }}
          onAddClient={() => setShowClientModal(true)}
        />
      )}

      {activeTab === 'branding' && (
        <BrandingTab branding={branding} onSave={(b) => { setBranding(b); showMsg('Branding updated') }} onError={(e) => showMsg(e, true)} />
      )}

      {activeTab === 'sharing' && <ClientSharingTab />}

      {activeTab === 'audit' && <AuditLogTab />}

      {showAddModal && (
        <AddEditMemberModal
          member={editingMember}
          onClose={() => { setShowAddModal(false); setEditingMember(null) }}
          onSave={() => { setShowAddModal(false); setEditingMember(null); fetchData(); showMsg(editingMember ? 'Member updated' : 'Member added') }}
        />
      )}

      {showClientModal && (
        <CreateClientLoginModal
          creators={creators}
          existingMembers={members}
          onClose={() => setShowClientModal(false)}
          onSave={() => { setShowClientModal(false); fetchData(); showMsg('Client login created') }}
        />
      )}

      {resetPasswordUser && (
        <ResetPasswordModal
          user={resetPasswordUser}
          onClose={() => setResetPasswordUser(null)}
          onSuccess={() => { setResetPasswordUser(null); showMsg('Password reset successfully') }}
        />
      )}

      {assignCreatorsUser && (
        <AssignCreatorsModal
          user={assignCreatorsUser}
          creators={creators}
          onClose={() => setAssignCreatorsUser(null)}
          onSave={() => { setAssignCreatorsUser(null); fetchData(); showMsg('Client assignments updated') }}
        />
      )}

      <EmailSendModal
        isOpen={showInviteModal}
        onClose={() => { setShowInviteModal(false); setInviteResult(null) }}
        onSend={handleInviteUser}
        title="Invite User"
        subtitle="Send a welcome email invitation to join your organization"
        defaultSubject="You're invited to join our organization"
        defaultMessage="You've been invited to join our team. Click the link in this email to set up your account and get started."
        sending={inviteSending}
        result={inviteResult}
      />
    </div>
  )
}

function MembersTab({ members, creators, onAdd, onEdit, onDelete, onResetPassword, onAssignCreators, onToggleRoster, onInvite, onAddClient }) {
  const roleColors = {
    OWNER: 'bg-purple-100 text-purple-700',
    ADMIN: 'bg-blue-100 text-blue-700',
    MEMBER: 'bg-gray-100 text-gray-600',
    CLIENT: 'bg-teal-100 text-teal-700',
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-semibold text-[#3D4A44]">Team Members ({members.length})</h2>
        <div className="flex items-center gap-2 flex-wrap">
          <button onClick={onInvite} className="flex items-center gap-2 px-4 py-2 bg-white border border-[#5B8A72] text-[#5B8A72] rounded-lg hover:bg-[#5B8A72]/5 text-sm font-medium">
            <EnvelopeIcon className="w-4 h-4" />
            Invite User
          </button>
          <button onClick={onAddClient} className="flex items-center gap-2 px-4 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 text-sm font-medium">
            <UserGroupIcon className="w-4 h-4" />
            Create Client Login
          </button>
          <button onClick={onAdd} className="flex items-center gap-2 px-4 py-2 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] text-sm font-medium">
            <PlusIcon className="w-4 h-4" />
            Add Member
          </button>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm overflow-x-auto">
        <table className="w-full min-w-[600px]">
          <thead className="bg-[#F5F7F4]">
            <tr>
              <th className="text-left px-4 py-3 text-xs font-semibold text-[#7A8580] uppercase tracking-wider">User</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-[#7A8580] uppercase tracking-wider">Role</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-[#7A8580] uppercase tracking-wider">Status</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-[#7A8580] uppercase tracking-wider hidden md:table-cell">Roster Access</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-[#7A8580] uppercase tracking-wider hidden md:table-cell">Assigned Clients</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-[#7A8580] uppercase tracking-wider hidden lg:table-cell">Last Login</th>
              <th className="text-right px-4 py-3 text-xs font-semibold text-[#7A8580] uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#E5E8E3]">
            {members.map(member => (
              <tr key={member.id} className="hover:bg-[#FAFBF9] transition-colors">
                <td className="px-4 py-3">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-full bg-gradient-to-br from-[#5B8A72] to-[#7BA897] flex items-center justify-center text-sm font-semibold text-white">
                      {member.username?.charAt(0).toUpperCase() || 'U'}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-[#3D4A44]">{member.username}</p>
                      <p className="text-xs text-[#7A8580]">{member.email}</p>
                    </div>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <div className="flex flex-col gap-1">
                    <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full w-fit ${roleColors[member.role] || roleColors.MEMBER}`}>
                      {member.role}
                    </span>
                    {member.role === 'CLIENT' && member.linked_creator_name && (
                      <span className="text-xs text-teal-600 font-medium">{member.linked_creator_name}</span>
                    )}
                    {member.role === 'CLIENT' && member.client_access_scope === 'ALL' && (
                      <span className="text-[10px] text-[#7A8580] bg-[#EEF1EC] px-1.5 py-0.5 rounded">All Clients</span>
                    )}
                  </div>
                </td>
                <td className="px-4 py-3">
                  <span className={`inline-flex items-center gap-1 text-xs font-medium ${member.is_active ? 'text-green-600' : 'text-red-500'}`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${member.is_active ? 'bg-green-500' : 'bg-red-400'}`} />
                    {member.is_active ? 'Active' : 'Disabled'}
                  </span>
                </td>
                <td className="px-4 py-3 hidden md:table-cell">
                  {member.role === 'OWNER' || member.role === 'ADMIN' ? (
                    <span className="inline-flex items-center gap-1 text-xs font-medium text-green-600">
                      <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
                      Always
                    </span>
                  ) : (
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={member.can_manage_roster || false}
                        onChange={() => onToggleRoster(member.id, !member.can_manage_roster)}
                        className="sr-only peer"
                      />
                      <div className="w-9 h-5 bg-gray-200 peer-focus:ring-2 peer-focus:ring-[#5B8A72] rounded-full peer peer-checked:bg-[#5B8A72] after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:after:translate-x-full"></div>
                    </label>
                  )}
                </td>
                <td className="px-4 py-3 hidden md:table-cell">
                  {member.assigned_creators?.length > 0 ? (
                    <div className="flex flex-wrap gap-1">
                      {member.assigned_creators.slice(0, 3).map(c => (
                        <span key={c.id} className="inline-flex px-2 py-0.5 text-xs bg-[#EEF1EC] text-[#5B8A72] rounded-full">{c.name}</span>
                      ))}
                      {member.assigned_creators.length > 3 && (
                        <span className="text-xs text-[#7A8580]">+{member.assigned_creators.length - 3}</span>
                      )}
                    </div>
                  ) : (
                    <span className="text-xs text-[#A0A8A3]">None</span>
                  )}
                </td>
                <td className="px-4 py-3 hidden lg:table-cell">
                  <span className="text-xs text-[#7A8580]">
                    {member.last_login_at ? new Date(member.last_login_at).toLocaleDateString() : 'Never'}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-end gap-1">
                    <button onClick={() => onAssignCreators(member)} className="p-1.5 text-[#7A8580] hover:text-[#5B8A72] hover:bg-[#EEF1EC] rounded-lg transition-colors" title="Assign Clients">
                      <UserGroupIcon className="w-4 h-4" />
                    </button>
                    <button onClick={() => onResetPassword(member)} className="p-1.5 text-[#7A8580] hover:text-amber-600 hover:bg-amber-50 rounded-lg transition-colors" title="Reset Password">
                      <KeyIcon className="w-4 h-4" />
                    </button>
                    <button onClick={() => onEdit(member)} className="p-1.5 text-[#7A8580] hover:text-[#5B8A72] hover:bg-[#EEF1EC] rounded-lg transition-colors" title="Edit">
                      <PencilIcon className="w-4 h-4" />
                    </button>
                    <button onClick={() => onDelete(member.id, member.username)} className="p-1.5 text-[#7A8580] hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors" title="Remove">
                      <TrashIcon className="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {members.length === 0 && (
          <div className="text-center py-12 text-[#7A8580]">
            <UsersIcon className="w-12 h-12 mx-auto mb-3 opacity-40" />
            <p className="text-sm">No team members yet</p>
          </div>
        )}
      </div>
    </div>
  )
}

function AddEditMemberModal({ member, onClose, onSave }) {
  const [form, setForm] = useState({
    username: member?.username || '',
    email: member?.email || '',
    password: '',
    role: member?.role || 'MEMBER',
    is_active: member?.is_active !== false,
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      if (member) {
        const data = { role: form.role, is_active: form.is_active }
        if (form.username !== member.username) data.username = form.username
        if (form.email !== member.email) data.email = form.email
        await axios.put(`/api/tenant-admin/members/${member.id}`, data)
      } else {
        if (!form.password || form.password.length < 6) {
          setError('Password must be at least 6 characters')
          setSaving(false)
          return
        }
        await axios.post('/api/tenant-admin/members', form)
      }
      onSave()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 mx-4">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold text-[#3D4A44]">{member ? 'Edit Member' : 'Add New Member'}</h3>
          <button onClick={onClose} className="p-1 hover:bg-[#EEF1EC] rounded-lg"><XMarkIcon className="w-5 h-5 text-[#7A8580]" /></button>
        </div>

        {error && <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">{error}</div>}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-[#3D4A44] mb-1">Username</label>
            <input
              type="text" required value={form.username}
              onChange={(e) => setForm({...form, username: e.target.value})}
              className="w-full px-3 py-2 border border-[#D1D5CE] rounded-lg text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-[#3D4A44] mb-1">Email</label>
            <input
              type="email" required value={form.email}
              onChange={(e) => setForm({...form, email: e.target.value})}
              className="w-full px-3 py-2 border border-[#D1D5CE] rounded-lg text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
            />
          </div>
          {!member && (
            <div>
              <label className="block text-sm font-medium text-[#3D4A44] mb-1">Password</label>
              <input
                type="password" required value={form.password}
                onChange={(e) => setForm({...form, password: e.target.value})}
                className="w-full px-3 py-2 border border-[#D1D5CE] rounded-lg text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                placeholder="Min 6 characters"
              />
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-[#3D4A44] mb-1">Role</label>
            <select
              value={form.role}
              onChange={(e) => setForm({...form, role: e.target.value})}
              className="w-full px-3 py-2 border border-[#D1D5CE] rounded-lg text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
            >
              <option value="MEMBER">Member</option>
              <option value="ADMIN">Admin</option>
              <option value="OWNER">Owner</option>
            </select>
            <p className="text-xs text-[#7A8580] mt-1">Admins and Owners can manage team members and settings</p>
          </div>
          {member && (
            <div className="flex items-center gap-3">
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox" checked={form.is_active}
                  onChange={(e) => setForm({...form, is_active: e.target.checked})}
                  className="sr-only peer"
                />
                <div className="w-9 h-5 bg-gray-200 peer-focus:ring-2 peer-focus:ring-[#5B8A72] rounded-full peer peer-checked:bg-[#5B8A72] after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:after:translate-x-full"></div>
              </label>
              <span className="text-sm text-[#3D4A44]">Account Active</span>
            </div>
          )}
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-[#7A8580] hover:bg-[#EEF1EC] rounded-lg">Cancel</button>
            <button type="submit" disabled={saving} className="px-4 py-2 text-sm bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] disabled:opacity-50">
              {saving ? 'Saving...' : member ? 'Update' : 'Create Member'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function CreateClientLoginModal({ creators, existingMembers, onClose, onSave }) {
  const [form, setForm] = useState({
    username: '',
    email: '',
    password: '',
    creator_id: '',
    client_access_scope: 'OWN',
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  const linkedCreatorIds = new Set(
    existingMembers.filter(m => m.linked_creator_id && m.role === 'CLIENT').map(m => m.linked_creator_id)
  )
  const availableCreators = creators.filter(c => !linkedCreatorIds.has(c.id))

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.creator_id) {
      setError('Please select a creator to link')
      return
    }
    if (!form.password || form.password.length < 6) {
      setError('Password must be at least 6 characters')
      return
    }
    setSaving(true)
    setError(null)
    try {
      await axios.post('/api/tenant-admin/members', {
        username: form.username,
        email: form.email,
        password: form.password,
        role: 'CLIENT',
        creator_id: parseInt(form.creator_id),
        client_access_scope: form.client_access_scope,
      })
      onSave()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create client login')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 mx-4">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-lg font-semibold text-[#3D4A44]">Create Client Login</h3>
          <button onClick={onClose} className="p-1 hover:bg-[#EEF1EC] rounded-lg"><XMarkIcon className="w-5 h-5 text-[#7A8580]" /></button>
        </div>
        <p className="text-sm text-[#7A8580] mb-5">Create a login for a creator on your roster. They will be able to view and edit their own profile, catalog, and related data.</p>

        {error && <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">{error}</div>}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-[#3D4A44] mb-1">Link to Creator</label>
            <select
              required value={form.creator_id}
              onChange={(e) => setForm({...form, creator_id: e.target.value})}
              className="w-full px-3 py-2 border border-[#D1D5CE] rounded-lg text-sm focus:ring-2 focus:ring-teal-500 focus:border-transparent"
            >
              <option value="">Select a creator...</option>
              {availableCreators.map(c => (
                <option key={c.id} value={c.id}>{c.display_name || c.name}</option>
              ))}
            </select>
            {availableCreators.length === 0 && (
              <p className="text-xs text-amber-600 mt-1">All creators already have linked accounts</p>
            )}
          </div>
          <div>
            <label className="block text-sm font-medium text-[#3D4A44] mb-1">Username</label>
            <input
              type="text" required value={form.username}
              onChange={(e) => setForm({...form, username: e.target.value})}
              className="w-full px-3 py-2 border border-[#D1D5CE] rounded-lg text-sm focus:ring-2 focus:ring-teal-500 focus:border-transparent"
              placeholder="e.g. artist_john"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-[#3D4A44] mb-1">Email</label>
            <input
              type="email" required value={form.email}
              onChange={(e) => setForm({...form, email: e.target.value})}
              className="w-full px-3 py-2 border border-[#D1D5CE] rounded-lg text-sm focus:ring-2 focus:ring-teal-500 focus:border-transparent"
              placeholder="client@email.com"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-[#3D4A44] mb-1">Password</label>
            <input
              type="password" required value={form.password}
              onChange={(e) => setForm({...form, password: e.target.value})}
              className="w-full px-3 py-2 border border-[#D1D5CE] rounded-lg text-sm focus:ring-2 focus:ring-teal-500 focus:border-transparent"
              placeholder="Min 6 characters"
            />
          </div>
          <div>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={form.client_access_scope === 'ALL'}
                onChange={(e) => setForm({...form, client_access_scope: e.target.checked ? 'ALL' : 'OWN'})}
                className="w-4 h-4 text-[#5B8A72] border-[#D1D5CE] rounded focus:ring-[#5B8A72]"
              />
              <span className="text-sm text-[#3D4A44]">Can view other client profiles</span>
            </label>
            <p className="text-xs text-[#7A8580] mt-1 ml-6">When enabled, this client can see other creators on your roster who also have client logins.</p>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-[#7A8580] hover:bg-[#EEF1EC] rounded-lg">Cancel</button>
            <button type="submit" disabled={saving || availableCreators.length === 0} className="px-4 py-2 text-sm bg-teal-600 text-white rounded-lg hover:bg-teal-700 disabled:opacity-50">
              {saving ? 'Creating...' : 'Create Client Login'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function ResetPasswordModal({ user, onClose, onSuccess }) {
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showNewPw, setShowNewPw] = useState(false)
  const [showConfirmPw, setShowConfirmPw] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match')
      return
    }
    if (newPassword.length < 6) {
      setError('Password must be at least 6 characters')
      return
    }
    setSaving(true)
    setError(null)
    try {
      await axios.post(`/api/tenant-admin/members/${user.id}/reset-password`, { new_password: newPassword })
      onSuccess()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to reset password')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 mx-4">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-lg font-semibold text-[#3D4A44]">Reset Password</h3>
            <p className="text-sm text-[#7A8580]">For: {user.username}</p>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-[#EEF1EC] rounded-lg"><XMarkIcon className="w-5 h-5 text-[#7A8580]" /></button>
        </div>
        {error && <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">{error}</div>}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-[#3D4A44] mb-1">New Password</label>
            <div className="relative">
              <input type={showNewPw ? "text" : "password"} required value={newPassword} onChange={(e) => setNewPassword(e.target.value)} className="w-full px-3 py-2 pr-10 border border-[#D1D5CE] rounded-lg text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent" placeholder="Min 6 characters" />
              <button type="button" onClick={() => setShowNewPw(!showNewPw)} className="absolute right-2.5 top-1/2 -translate-y-1/2 p-0.5 text-[#7A8580] hover:text-[#5B8A72] transition-colors">
                {showNewPw ? <EyeSlashIcon className="w-4 h-4" /> : <EyeIcon className="w-4 h-4" />}
              </button>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-[#3D4A44] mb-1">Confirm Password</label>
            <div className="relative">
              <input type={showConfirmPw ? "text" : "password"} required value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} className="w-full px-3 py-2 pr-10 border border-[#D1D5CE] rounded-lg text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent" />
              <button type="button" onClick={() => setShowConfirmPw(!showConfirmPw)} className="absolute right-2.5 top-1/2 -translate-y-1/2 p-0.5 text-[#7A8580] hover:text-[#5B8A72] transition-colors">
                {showConfirmPw ? <EyeSlashIcon className="w-4 h-4" /> : <EyeIcon className="w-4 h-4" />}
              </button>
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-[#7A8580] hover:bg-[#EEF1EC] rounded-lg">Cancel</button>
            <button type="submit" disabled={saving} className="px-4 py-2 text-sm bg-amber-500 text-white rounded-lg hover:bg-amber-600 disabled:opacity-50">
              {saving ? 'Resetting...' : 'Reset Password'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function AssignCreatorsModal({ user, creators, onClose, onSave }) {
  const [selectedIds, setSelectedIds] = useState(
    (user.assigned_creators || []).map(c => c.id)
  )
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')

  const toggleCreator = (id) => {
    setSelectedIds(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id])
  }

  const filteredCreators = creators.filter(c =>
    c.name.toLowerCase().includes(search.toLowerCase())
  )

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    try {
      await axios.post(`/api/tenant-admin/members/${user.id}/assign-creators`, { creator_ids: selectedIds })
      onSave()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to assign clients')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6 mx-4 max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-[#3D4A44]">Assign Clients</h3>
            <p className="text-sm text-[#7A8580]">Assign clients/creators to {user.username}</p>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-[#EEF1EC] rounded-lg"><XMarkIcon className="w-5 h-5 text-[#7A8580]" /></button>
        </div>

        {error && <div className="mb-3 p-3 bg-red-50 text-red-700 rounded-lg text-sm">{error}</div>}

        <input
          type="text" placeholder="Search creators..."
          value={search} onChange={(e) => setSearch(e.target.value)}
          className="w-full px-3 py-2 border border-[#D1D5CE] rounded-lg text-sm mb-3 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
        />

        <div className="flex-1 overflow-y-auto space-y-1 mb-4 min-h-0">
          {filteredCreators.length === 0 ? (
            <p className="text-center text-sm text-[#7A8580] py-8">No creators found in this organization</p>
          ) : (
            filteredCreators.map(creator => (
              <label key={creator.id} className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-[#F5F7F4] cursor-pointer">
                <input
                  type="checkbox"
                  checked={selectedIds.includes(creator.id)}
                  onChange={() => toggleCreator(creator.id)}
                  className="w-4 h-4 text-[#5B8A72] border-[#D1D5CE] rounded focus:ring-[#5B8A72]"
                />
                <span className="text-sm text-[#3D4A44]">{creator.name}</span>
                {creator.assigned_to_user_id && creator.assigned_to_user_id !== user.id && (
                  <span className="text-xs text-amber-600 ml-auto">(assigned elsewhere)</span>
                )}
              </label>
            ))
          )}
        </div>

        <div className="flex items-center justify-between pt-3 border-t border-[#E5E8E3]">
          <span className="text-xs text-[#7A8580]">{selectedIds.length} selected</span>
          <div className="flex gap-3">
            <button onClick={onClose} className="px-4 py-2 text-sm text-[#7A8580] hover:bg-[#EEF1EC] rounded-lg">Cancel</button>
            <button onClick={handleSave} disabled={saving} className="px-4 py-2 text-sm bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] disabled:opacity-50">
              {saving ? 'Saving...' : 'Save Assignments'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function BrandingTab({ branding, onSave, onError }) {
  const [form, setForm] = useState({
    display_name: branding?.display_name || '',
    primary_color: branding?.primary_color || '#5B8A72',
    logo_orientation: branding?.logo_orientation || 'square',
  })
  const [saving, setSaving] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [logoPreview, setLogoPreview] = useState(branding?.logo_url || null)

  const handleSaveBranding = async () => {
    setSaving(true)
    try {
      const res = await axios.put('/api/tenant-admin/branding', form)
      onSave({ ...branding, ...res.data.branding })
    } catch (err) {
      onError(err.response?.data?.detail || 'Failed to update branding')
    } finally {
      setSaving(false)
    }
  }

  const handleLogoUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return

    if (!file.type.startsWith('image/')) {
      onError('Please upload an image file')
      return
    }
    if (file.size > 2 * 1024 * 1024) {
      onError('Image must be under 2MB')
      return
    }

    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const res = await axios.post('/api/tenant-admin/branding/logo', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      setLogoPreview(res.data.logo_url)
      onSave({ ...branding, logo_url: res.data.logo_url })
    } catch (err) {
      onError(err.response?.data?.detail || 'Failed to upload logo')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="bg-white rounded-xl shadow-sm p-6">
        <h3 className="text-lg font-semibold text-[#3D4A44] mb-4">Company Logo</h3>
        <div className="flex items-start gap-6">
          <div className="w-24 h-24 bg-[#F5F7F4] rounded-xl border-2 border-dashed border-[#D1D5CE] flex items-center justify-center overflow-hidden flex-shrink-0">
            {logoPreview ? (
              <img src={logoPreview} alt="Logo" className="w-full h-full object-contain" />
            ) : (
              <PhotoIcon className="w-10 h-10 text-[#A0A8A3]" />
            )}
          </div>
          <div className="space-y-3">
            <p className="text-sm text-[#7A8580]">Upload your company logo. It will appear on the sidebar and dashboard for all users in your organization.</p>
            <div className="flex items-center gap-3">
              <label className="px-4 py-2 text-sm bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] cursor-pointer inline-flex items-center gap-2">
                <PhotoIcon className="w-4 h-4" />
                {uploading ? 'Uploading...' : 'Upload Logo'}
                <input type="file" accept="image/*" onChange={handleLogoUpload} className="hidden" disabled={uploading} />
              </label>
              <select
                value={form.logo_orientation}
                onChange={(e) => setForm({...form, logo_orientation: e.target.value})}
                className="px-3 py-2 border border-[#D1D5CE] rounded-lg text-sm"
              >
                <option value="square">Square</option>
                <option value="horizontal">Horizontal</option>
                <option value="vertical">Vertical</option>
              </select>
            </div>
            <p className="text-xs text-[#A0A8A3]">Max 2MB. PNG or JPG recommended.</p>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm p-6">
        <h3 className="text-lg font-semibold text-[#3D4A44] mb-4">Display Settings</h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-[#3D4A44] mb-1">Display Name</label>
            <input
              type="text" value={form.display_name}
              onChange={(e) => setForm({...form, display_name: e.target.value})}
              className="w-full px-3 py-2 border border-[#D1D5CE] rounded-lg text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
              placeholder="Your company name as shown in the app"
            />
            <p className="text-xs text-[#A0A8A3] mt-1">This name is shown on the dashboard and sidebar for your team</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-[#3D4A44] mb-1">Brand Color</label>
            <div className="flex items-center gap-3">
              <input
                type="color" value={form.primary_color}
                onChange={(e) => setForm({...form, primary_color: e.target.value})}
                className="w-10 h-10 rounded-lg border border-[#D1D5CE] cursor-pointer"
              />
              <input
                type="text" value={form.primary_color}
                onChange={(e) => setForm({...form, primary_color: e.target.value})}
                className="w-28 px-3 py-2 border border-[#D1D5CE] rounded-lg text-sm font-mono"
                placeholder="#5B8A72"
              />
              <div className="flex gap-2">
                {['#5B8A72', '#4A6FA5', '#8B5CF6', '#DC2626', '#D97706', '#0D9488'].map(color => (
                  <button
                    key={color}
                    onClick={() => setForm({...form, primary_color: color})}
                    className="w-7 h-7 rounded-full border-2 border-white shadow-sm hover:scale-110 transition-transform"
                    style={{ backgroundColor: color }}
                  />
                ))}
              </div>
            </div>
          </div>
        </div>
        <div className="mt-6 flex justify-end">
          <button onClick={handleSaveBranding} disabled={saving} className="px-5 py-2 text-sm bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] disabled:opacity-50 font-medium">
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm p-6">
        <h3 className="text-lg font-semibold text-[#3D4A44] mb-3">Preview</h3>
        <div className="border border-[#E5E8E3] rounded-xl p-4 bg-[#FAFBF9]">
          <div className="flex items-center gap-3">
            {logoPreview ? (
              <img src={logoPreview} alt="Preview" className="w-10 h-10 rounded-xl object-contain" />
            ) : (
              <div className="w-10 h-10 rounded-xl flex items-center justify-center text-white font-bold text-sm" style={{ backgroundColor: form.primary_color }}>
                {(form.display_name || branding?.name || 'R').charAt(0).toUpperCase()}
              </div>
            )}
            <div>
              <p className="text-[15px] font-semibold" style={{ color: '#3D4A44' }}>{form.display_name || branding?.name || 'Organization'}</p>
              <p className="text-[12px] text-[#7A8580]">Catalog Intelligence</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function AuditLogTab() {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [filterAction, setFilterAction] = useState('')
  const [filterEntity, setFilterEntity] = useState('')
  const limit = 50

  useEffect(() => {
    loadLogs()
  }, [offset, filterAction, filterEntity])

  const loadLogs = async () => {
    setLoading(true)
    try {
      const orgRes = await axios.get('/api/organizations/current')
      const orgId = orgRes.data?.id
      if (!orgId) return
      const params = new URLSearchParams()
      params.append('limit', limit)
      params.append('offset', offset)
      if (filterAction) params.append('action', filterAction)
      if (filterEntity) params.append('entity_type', filterEntity)
      const res = await axios.get(`/api/audit-log/org/${orgId}?${params}`)
      setLogs(res.data.logs || [])
      setTotal(res.data.total || 0)
    } catch (err) {
      console.error('Failed to load audit logs:', err)
    } finally {
      setLoading(false)
    }
  }

  const actionColors = {
    CREATE: 'bg-[#D4EDDA] text-[#155724]',
    DELETE: 'bg-[#FFE0DE] text-[#9B2C2C]',
    UPDATE: 'bg-[#D6EAF8] text-[#1B4F72]',
    IMPORT: 'bg-[#FFF3CD] text-[#856404]',
  }

  const formatDate = (iso) => {
    if (!iso) return '-'
    const d = new Date(iso)
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) + ' ' + d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
  }

  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <select
          value={filterAction}
          onChange={(e) => { setFilterAction(e.target.value); setOffset(0) }}
          className="px-3 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg text-sm bg-white text-[#3D4A44]"
        >
          <option value="">All Actions</option>
          <option value="CREATE">Create</option>
          <option value="UPDATE">Update</option>
          <option value="DELETE">Delete</option>
          <option value="IMPORT">Import</option>
        </select>
        <select
          value={filterEntity}
          onChange={(e) => { setFilterEntity(e.target.value); setOffset(0) }}
          className="px-3 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg text-sm bg-white text-[#3D4A44]"
        >
          <option value="">All Types</option>
          <option value="SONG">Song</option>
          <option value="CREATOR">Creator</option>
          <option value="PLACEMENT">Placement</option>
          <option value="CONTRACT">Contract</option>
        </select>
        <span className="text-sm text-[#7A8580] ml-auto">{total} total entries</span>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-2 border-[#5B8A72] border-t-transparent"></div>
        </div>
      ) : logs.length === 0 ? (
        <div className="text-center py-12 text-[#7A8580]">
          <ClipboardDocumentListIcon className="w-12 h-12 mx-auto mb-3 opacity-40" />
          <p className="font-medium">No activity recorded yet</p>
          <p className="text-sm mt-1">Actions like creating, editing, or deleting items will appear here.</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm overflow-hidden">
          <table className="w-full">
            <thead className="bg-[#EEF1EC]">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-[#3D4A44]">When</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-[#3D4A44]">User</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-[#3D4A44]">Action</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-[#3D4A44]">Type</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-[#3D4A44]">Item</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-[#3D4A44]">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[rgba(59,77,67,0.08)]">
              {logs.map((log) => (
                <tr key={log.id} className="hover:bg-[#FAFBF9]">
                  <td className="px-4 py-3 text-xs text-[#7A8580] whitespace-nowrap">{formatDate(log.created_at)}</td>
                  <td className="px-4 py-3 text-sm text-[#3D4A44]">{log.user_name}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${actionColors[log.action] || 'bg-[#EEF1EC] text-[#3D4A44]'}`}>
                      {log.action}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-[#7A8580]">{log.entity_type}</td>
                  <td className="px-4 py-3 text-sm text-[#3D4A44] truncate max-w-[200px]">{log.entity_name || '-'}</td>
                  <td className="px-4 py-3 text-xs text-[#7A8580] truncate max-w-[200px]">
                    {log.details ? JSON.stringify(log.details) : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {total > limit && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-[rgba(59,77,67,0.08)]">
              <button onClick={() => setOffset(Math.max(0, offset - limit))} disabled={offset === 0} className="px-3 py-1.5 text-sm border border-[rgba(59,77,67,0.12)] rounded-lg disabled:opacity-40 hover:bg-[#EEF1EC] transition-colors">Previous</button>
              <span className="text-sm text-[#7A8580]">{offset + 1}–{Math.min(offset + limit, total)} of {total}</span>
              <button onClick={() => setOffset(offset + limit)} disabled={offset + limit >= total} className="px-3 py-1.5 text-sm border border-[rgba(59,77,67,0.12)] rounded-lg disabled:opacity-40 hover:bg-[#EEF1EC] transition-colors">Next</button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
