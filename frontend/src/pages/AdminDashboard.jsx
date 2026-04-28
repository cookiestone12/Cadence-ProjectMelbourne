import React, { useState, useEffect } from 'react'
import axios from 'axios'
import {
  UsersIcon,
  BuildingOfficeIcon,
  MusicalNoteIcon,
  UserGroupIcon,
  PlusIcon,
  PencilIcon,
  TrashIcon,
  XMarkIcon,
  CheckIcon,
  EyeIcon,
  ChartBarIcon,
  Cog6ToothIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  KeyIcon,
  CurrencyDollarIcon,
  ArrowDownTrayIcon,
  CpuChipIcon,
  ServerIcon,
  CloudIcon,
  EnvelopeIcon,
  BoltIcon,
  GlobeAltIcon,
  BellAlertIcon,
  LifebuoyIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline'

export default function AdminDashboard() {
  const [activeTab, setActiveTab] = useState('overview')
  const [stats, setStats] = useState(null)
  const [users, setUsers] = useState([])
  const [organizations, setOrganizations] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  
  const [showUserModal, setShowUserModal] = useState(false)
  const [showOrgModal, setShowOrgModal] = useState(false)
  const [editingUser, setEditingUser] = useState(null)
  const [editingOrg, setEditingOrg] = useState(null)
  const [integrations, setIntegrations] = useState(null)
  const [showIntegrationModal, setShowIntegrationModal] = useState(false)
  const [configuringIntegration, setConfiguringIntegration] = useState(null)
  const [platformStats, setPlatformStats] = useState(null)
  const [resetPasswordUser, setResetPasswordUser] = useState(null)
  const [deletingOrg, setDeletingOrg] = useState(null)
  const [mergeRequests, setMergeRequests] = useState([])
  const [mergeFilter, setMergeFilter] = useState('all')
  const [approvingMerge, setApprovingMerge] = useState(null)
  const [rejectingMerge, setRejectingMerge] = useState(null)
  const [rejectNotes, setRejectNotes] = useState('')
  const [mergeActionLoading, setMergeActionLoading] = useState(false)
  const [aiUsage, setAiUsage] = useState(null)
  const [aiUsageLoading, setAiUsageLoading] = useState(false)
  const [costReportLoading, setCostReportLoading] = useState(false)
  const [supportTickets, setSupportTickets] = useState([])
  const [supportLoading, setSupportLoading] = useState(false)
  const [supportFilter, setSupportFilter] = useState('all')
  const [selectedSupportTicket, setSelectedSupportTicket] = useState(null)
  const [adminNotes, setAdminNotes] = useState('')
  const [savingNotes, setSavingNotes] = useState(false)
  const [updatingStatus, setUpdatingStatus] = useState(false)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      setError(null)
      const [statsRes, usersRes, orgsRes, integrationsRes, platformRes, mergeRes] = await Promise.all([
        axios.get('/api/admin/stats'),
        axios.get('/api/admin/users'),
        axios.get('/api/admin/organizations'),
        axios.get('/api/admin/integrations'),
        axios.get('/api/analytics/admin/platform-stats').catch(() => ({ data: null })),
        axios.get('/api/admin/merge-requests').catch(() => ({ data: [] }))
      ])
      setStats(statsRes.data)
      setUsers(usersRes.data)
      setOrganizations(orgsRes.data)
      setIntegrations(integrationsRes.data)
      if (platformRes.data) setPlatformStats(platformRes.data)
      setMergeRequests(mergeRes.data || [])
    } catch (err) {
      console.error('Failed to load admin data:', err)
      if (err.response?.status === 403) {
        setError('You do not have permission to access the admin dashboard.')
      } else {
        setError('Failed to load admin data. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  const loadAiUsage = async () => {
    setAiUsageLoading(true)
    try {
      const res = await axios.get('/api/admin/ai-usage')
      setAiUsage(res.data)
    } catch (err) {
      console.error('Failed to load AI usage:', err)
    } finally {
      setAiUsageLoading(false)
    }
  }

  const loadSupportTickets = async () => {
    setSupportLoading(true)
    try {
      const params = {}
      if (supportFilter !== 'all') params.status = supportFilter
      const res = await axios.get('/api/admin/support-tickets', { params })
      setSupportTickets(res.data.tickets || [])
    } catch (err) {
      console.error('Failed to load support tickets:', err)
    } finally {
      setSupportLoading(false)
    }
  }

  const handleUpdateTicketStatus = async (ticketId, newStatus) => {
    setUpdatingStatus(true)
    try {
      await axios.put(`/api/admin/support-tickets/${ticketId}/status`, { status: newStatus })
      loadSupportTickets()
      if (selectedSupportTicket?.id === ticketId) {
        setSelectedSupportTicket(prev => ({ ...prev, status: newStatus }))
      }
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to update status')
    } finally {
      setUpdatingStatus(false)
    }
  }

  const handleSaveAdminNotes = async (ticketId) => {
    setSavingNotes(true)
    try {
      await axios.put(`/api/admin/support-tickets/${ticketId}/notes`, { admin_notes: adminNotes })
      loadSupportTickets()
      if (selectedSupportTicket?.id === ticketId) {
        setSelectedSupportTicket(prev => ({ ...prev, admin_notes: adminNotes }))
      }
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to save notes')
    } finally {
      setSavingNotes(false)
    }
  }

  useEffect(() => {
    if (activeTab === 'costs' && !aiUsage) {
      loadAiUsage()
    }
    if (activeTab === 'support') {
      loadSupportTickets()
    }
  }, [activeTab, supportFilter])

  const handleDownloadCostReport = async () => {
    setCostReportLoading(true)
    try {
      const res = await axios.get('/api/admin/cost-report', { responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `cadence_cost_report_${new Date().toISOString().split('T')[0]}.pdf`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      alert('Failed to generate cost report')
      console.error(err)
    } finally {
      setCostReportLoading(false)
    }
  }

  const handleDeleteUser = async (userId) => {
    if (!confirm('Are you sure you want to delete this user?')) return
    try {
      await axios.delete(`/api/admin/users/${userId}`)
      setUsers(users.filter(u => u.id !== userId))
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to delete user')
    }
  }

  const handleDeleteOrg = async (orgId) => {
    try {
      await axios.delete(`/api/admin/organizations/${orgId}?confirm=true`)
      setOrganizations(organizations.filter(o => o.id !== orgId))
      setDeletingOrg(null)
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to delete organization')
    }
  }

  const handleToggleUserStatus = async (user) => {
    try {
      await axios.put(`/api/admin/users/${user.id}`, {
        is_active: !user.is_active
      })
      setUsers(users.map(u => 
        u.id === user.id ? { ...u, is_active: !u.is_active } : u
      ))
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to update user')
    }
  }

  const handleImpersonate = async (orgId) => {
    try {
      const res = await axios.post(`/api/admin/impersonate/${orgId}`)
      alert(res.data.message)
      window.location.href = '/'
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to impersonate')
    }
  }

  const handleApproveMerge = async (requestId) => {
    setMergeActionLoading(true)
    try {
      await axios.put(`/api/admin/merge-requests/${requestId}/approve`, { notes: '' })
      setApprovingMerge(null)
      loadData()
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to approve merge request')
    } finally {
      setMergeActionLoading(false)
    }
  }

  const handleRejectMerge = async (requestId) => {
    setMergeActionLoading(true)
    try {
      await axios.put(`/api/admin/merge-requests/${requestId}/reject`, { notes: rejectNotes })
      setRejectingMerge(null)
      setRejectNotes('')
      loadData()
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to reject merge request')
    } finally {
      setMergeActionLoading(false)
    }
  }

  const filteredMergeRequests = mergeRequests.filter(r => {
    if (mergeFilter === 'all') return true
    return r.status === mergeFilter.toUpperCase()
  })

  const getMergeStatusBadge = (status) => {
    const styles = {
      PENDING_VERIFICATION: 'bg-[rgba(196,149,107,0.12)] text-[#C4956B]',
      VERIFIED: 'bg-[rgba(90,138,154,0.12)] text-[#5A8A9A]',
      COMPLETED: 'bg-[rgba(91,154,110,0.12)] text-[#5B9A6E]',
      REJECTED: 'bg-[rgba(196,112,104,0.12)] text-[#C47068]',
      CANCELLED: 'bg-[rgba(59,77,67,0.08)] text-[#7A8580]',
      EXPIRED: 'bg-[rgba(59,77,67,0.08)] text-[#7A8580]',
    }
    const labels = {
      PENDING_VERIFICATION: 'Pending Verification',
      VERIFIED: 'Awaiting Approval',
      COMPLETED: 'Approved',
      REJECTED: 'Rejected',
      CANCELLED: 'Cancelled',
      EXPIRED: 'Expired',
    }
    return (
      <span className={`px-2 py-1 rounded text-xs font-medium ${styles[status] || styles.CANCELLED}`}>
        {labels[status] || status}
      </span>
    )
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full p-8">
        <div className="text-[#7A8580]">Loading admin dashboard...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full p-8">
        <div className="text-center">
          <div className="text-[#C47068] text-lg mb-4">{error}</div>
          <button
            onClick={loadData}
            className="px-4 py-2 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62]"
          >
            Try Again
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="p-4 sm:p-8">
      <div className="mb-8">
        <h1 className="text-2xl sm:text-4xl font-bold text-[#3D4A44] mb-2">Admin Dashboard</h1>
        <p className="text-[#7A8580]">Manage users, organizations, and system settings</p>
      </div>

      <div className="mb-6 border-b border-[rgba(59,77,67,0.08)] overflow-x-auto">
        <div className="flex space-x-4 sm:space-x-8 min-w-max">
          {['overview', 'users', 'organizations', 'merge-requests', 'api-config', 'costs', 'support', 'leads'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`pb-3 px-1 border-b-2 font-medium transition-colors capitalize ${
                activeTab === tab
                  ? 'border-[#5B8A72] text-[#5B8A72]'
                  : 'border-transparent text-[#7A8580] hover:text-[#3D4A44]'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      {activeTab === 'overview' && stats && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <StatCard
              icon={UsersIcon}
              title="Total Users"
              value={stats.total_users}
              subtitle={`${stats.active_users} active`}
              color="#5B8A72"
            />
            <StatCard
              icon={BuildingOfficeIcon}
              title="Organizations"
              value={stats.total_organizations}
              color="#5A8A9A"
            />
            <StatCard
              icon={MusicalNoteIcon}
              title="Total Songs"
              value={stats.total_songs.toLocaleString()}
              color="#7BA594"
            />
            <StatCard
              icon={UserGroupIcon}
              title="Total Creators"
              value={stats.total_creators}
              color="#C4956B"
            />
          </div>

          {platformStats && (
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
              {[
                { label: 'Works', value: platformStats.totals.works, color: '#5A8A9A' },
                { label: 'Releases', value: platformStats.totals.releases, color: '#8B6EAE' },
                { label: 'Contracts', value: platformStats.totals.contracts, color: '#5B9A6E' },
                { label: 'Placements', value: platformStats.totals.placements, color: '#C47068' },
              ].map(s => (
                <div key={s.label} className="bg-[#FAFBF9] rounded-xl shadow-sm p-4 text-center">
                  <p className="text-[24px] font-semibold text-[#3D4A44]">{(s.value || 0).toLocaleString()}</p>
                  <p className="text-[11px] text-[#7A8580] uppercase tracking-wider">{s.label}</p>
                </div>
              ))}
              <div className="bg-[#FAFBF9] rounded-xl shadow-sm p-4 text-center col-span-2 md:col-span-3">
                <p className="text-[24px] font-semibold text-[#5B9A6E]">
                  ${((platformStats.totals.total_revenue_cents || 0) / 100).toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: 0})}
                </p>
                <p className="text-[11px] text-[#7A8580] uppercase tracking-wider">Platform-wide Revenue</p>
              </div>
            </div>
          )}

          {platformStats?.top_orgs?.length > 0 && (
            <div className="bg-[#FAFBF9] rounded-xl shadow-sm p-6">
              <h3 className="text-lg font-bold text-[#3D4A44] mb-4">Top Organizations by Catalog Size</h3>
              <div className="space-y-2">
                {platformStats.top_orgs.map((org, i) => {
                  const maxCount = platformStats.top_orgs[0]?.song_count || 1
                  return (
                    <div key={org.id} className="flex items-center gap-3">
                      <span className="text-[12px] font-semibold text-[#7A8580] w-5">{i + 1}</span>
                      <div className="flex-1">
                        <div className="flex justify-between mb-1">
                          <span className="text-[13px] font-medium text-[#3D4A44]">{org.name || 'Unnamed Org'}</span>
                          <span className="text-[12px] text-[#7A8580]">{org.song_count} songs</span>
                        </div>
                        <div className="h-1.5 bg-[#EEF1EC] rounded-full overflow-hidden">
                          <div className="h-full bg-[#5B8A72] rounded-full transition-all" style={{ width: `${(org.song_count / maxCount) * 100}%` }}></div>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-[#FAFBF9] rounded-xl shadow-sm p-6">
              <h3 className="text-lg font-bold text-[#3D4A44] mb-4">Recent Users</h3>
              <div className="space-y-3">
                {users.slice(0, 5).map(user => (
                  <div key={user.id} className="flex items-center justify-between p-3 bg-[#EEF1EC] rounded-lg">
                    <div>
                      <div className="font-medium text-[#3D4A44]">{user.username}</div>
                      <div className="text-sm text-[#7A8580]">{user.email}</div>
                    </div>
                    <div className={`px-2 py-1 rounded text-xs font-medium ${
                      user.is_active 
                        ? 'bg-[rgba(91,154,110,0.12)] text-[#5B9A6E]' 
                        : 'bg-[rgba(196,112,104,0.12)] text-[#C47068]'
                    }`}>
                      {user.is_active ? 'Active' : 'Disabled'}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-[#FAFBF9] rounded-xl shadow-sm p-6">
              <h3 className="text-lg font-bold text-[#3D4A44] mb-4">Organizations</h3>
              <div className="space-y-3">
                {organizations.slice(0, 5).map(org => (
                  <div key={org.id} className="flex items-center justify-between p-3 bg-[#EEF1EC] rounded-lg">
                    <div>
                      <div className="font-medium text-[#3D4A44]">{org.display_name || org.name}</div>
                      <div className="text-sm text-[#7A8580]">{org.member_count} members, {org.song_count} songs</div>
                    </div>
                    <button
                      onClick={() => handleImpersonate(org.id)}
                      className="text-[#5B8A72] hover:text-[#4A7A62]"
                      title="View as this organization"
                    >
                      <EyeIcon className="w-5 h-5" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'users' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-bold text-[#3D4A44]">All Users ({users.length})</h2>
            <button
              onClick={() => {
                setEditingUser(null)
                setShowUserModal(true)
              }}
              className="flex items-center space-x-2 px-4 py-2 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62]"
            >
              <PlusIcon className="w-5 h-5" />
              <span>Add User</span>
            </button>
          </div>

          <div className="bg-[#FAFBF9] rounded-xl shadow-sm overflow-x-auto">
            <table className="w-full min-w-[700px]">
              <thead className="bg-[#EEF1EC]">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#3D4A44] uppercase">User</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#3D4A44] uppercase">Organizations</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#3D4A44] uppercase">Role</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#3D4A44] uppercase">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#3D4A44] uppercase">Last Login</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-[#3D4A44] uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[rgba(59,77,67,0.08)]">
                {users.map(user => (
                  <tr key={user.id} className="hover:bg-[#EEF1EC]">
                    <td className="px-6 py-4">
                      <div className="font-medium text-[#3D4A44]">{user.username}</div>
                      <div className="text-sm text-[#7A8580]">{user.email}</div>
                    </td>
                    <td className="px-6 py-4 text-sm text-[#7A8580]">
                      {user.organizations.length > 0 
                        ? user.organizations.map(o => o.name).join(', ')
                        : 'None'}
                    </td>
                    <td className="px-6 py-4">
                      {user.is_super_admin ? (
                        <span className="px-2 py-1 bg-[rgba(91,138,114,0.12)] text-[#5B8A72] rounded text-xs font-medium">
                          Super Admin
                        </span>
                      ) : user.is_admin ? (
                        <span className="px-2 py-1 bg-[rgba(90,138,154,0.12)] text-[#5A8A9A] rounded text-xs font-medium">
                          Admin
                        </span>
                      ) : (
                        <span className="px-2 py-1 bg-[rgba(59,77,67,0.08)] text-[#7A8580] rounded text-xs font-medium">
                          User
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <button
                        onClick={() => handleToggleUserStatus(user)}
                        disabled={user.is_super_admin}
                        className={`px-2 py-1 rounded text-xs font-medium ${
                          user.is_active 
                            ? 'bg-[rgba(91,154,110,0.12)] text-[#5B9A6E]' 
                            : 'bg-[rgba(196,112,104,0.12)] text-[#C47068]'
                        } ${user.is_super_admin ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                      >
                        {user.is_active ? 'Active' : 'Disabled'}
                      </button>
                    </td>
                    <td className="px-6 py-4 text-sm text-[#7A8580]">
                      {user.last_login_at 
                        ? new Date(user.last_login_at).toLocaleDateString()
                        : 'Never'}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex justify-end space-x-2">
                        {!user.is_super_admin && (
                          <button
                            onClick={() => setResetPasswordUser(user)}
                            className="p-1 text-amber-500 hover:text-amber-600"
                            title="Reset Password"
                          >
                            <KeyIcon className="w-5 h-5" />
                          </button>
                        )}
                        <button
                          onClick={() => {
                            setEditingUser(user)
                            setShowUserModal(true)
                          }}
                          className="p-1 text-[#5B8A72] hover:text-[#4A7A62]"
                        >
                          <PencilIcon className="w-5 h-5" />
                        </button>
                        {!user.is_super_admin && (
                          <button
                            onClick={() => handleDeleteUser(user.id)}
                            className="p-1 text-[#C47068] hover:text-[#A45850]"
                          >
                            <TrashIcon className="w-5 h-5" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'organizations' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-bold text-[#3D4A44]">All Organizations ({organizations.length})</h2>
            <button
              onClick={() => {
                setEditingOrg(null)
                setShowOrgModal(true)
              }}
              className="flex items-center space-x-2 px-4 py-2 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62]"
            >
              <PlusIcon className="w-5 h-5" />
              <span>Add Organization</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {organizations.map(org => (
              <div key={org.id} className="bg-[#FAFBF9] rounded-xl shadow-sm p-6">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center space-x-3">
                    {org.logo_url ? (
                      <img 
                        src={org.logo_url} 
                        alt={org.name}
                        className={`object-contain ${
                          org.logo_orientation === 'horizontal' ? 'h-10 w-auto' :
                          org.logo_orientation === 'vertical' ? 'h-16 w-auto' :
                          'h-12 w-12'
                        }`}
                      />
                    ) : (
                      <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-[#5B8A72] to-[#7BA594] flex items-center justify-center text-white font-bold text-lg">
                        {(org.display_name || org.name).charAt(0)}
                      </div>
                    )}
                    <div>
                      <h3 className="font-bold text-[#3D4A44]">{org.display_name || org.name}</h3>
                      <p className="text-sm text-[#7A8580]">{org.type}</p>
                    </div>
                  </div>
                  <div className="flex space-x-1">
                    <button
                      onClick={() => handleImpersonate(org.id)}
                      className="p-1 text-[#5B8A72] hover:text-[#4A7A62]"
                      title="View as this organization"
                    >
                      <EyeIcon className="w-5 h-5" />
                    </button>
                    <button
                      onClick={() => {
                        setEditingOrg(org)
                        setShowOrgModal(true)
                      }}
                      className="p-1 text-[#7A8580] hover:text-[#3D4A44]"
                      title="Edit organization"
                    >
                      <PencilIcon className="w-5 h-5" />
                    </button>
                    <button
                      onClick={() => setDeletingOrg(org)}
                      className="p-1 text-[#C47068] hover:text-[#A45850]"
                      title="Delete organization"
                    >
                      <TrashIcon className="w-5 h-5" />
                    </button>
                  </div>
                </div>
                
                <div className="grid grid-cols-3 gap-4 text-center">
                  <div className="bg-[#EEF1EC] rounded-lg p-3">
                    <div className="text-lg font-bold text-[#3D4A44]">{org.member_count}</div>
                    <div className="text-xs text-[#7A8580]">Members</div>
                  </div>
                  <div className="bg-[#EEF1EC] rounded-lg p-3">
                    <div className="text-lg font-bold text-[#3D4A44]">{org.song_count}</div>
                    <div className="text-xs text-[#7A8580]">Songs</div>
                  </div>
                  <div className="bg-[#EEF1EC] rounded-lg p-3">
                    <div className="text-lg font-bold text-[#3D4A44]">{org.creator_count}</div>
                    <div className="text-xs text-[#7A8580]">Creators</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'merge-requests' && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <h2 className="text-xl font-bold text-[#3D4A44]">
              Merge Requests ({mergeRequests.length})
            </h2>
            <div className="flex flex-wrap gap-2">
              {['all', 'verified', 'pending_verification', 'completed', 'rejected'].map(f => (
                <button
                  key={f}
                  onClick={() => setMergeFilter(f)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                    mergeFilter === f
                      ? 'bg-[#5B8A72] text-white'
                      : 'bg-[#EEF1EC] text-[#7A8580] hover:text-[#3D4A44]'
                  }`}
                >
                  {f === 'all' ? 'All' : f === 'verified' ? 'Awaiting Approval' : f === 'pending_verification' ? 'Pending Verification' : f === 'completed' ? 'Approved' : 'Rejected'}
                </button>
              ))}
            </div>
          </div>

          {filteredMergeRequests.length === 0 ? (
            <div className="bg-[#FAFBF9] rounded-xl shadow-sm p-12 text-center">
              <p className="text-[#7A8580]">No merge requests found.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {filteredMergeRequests.map(req => (
                <div key={req.id} className="bg-[#FAFBF9] rounded-xl shadow-sm p-6">
                  <div className="flex flex-col sm:flex-row justify-between gap-4">
                    <div className="flex-1 space-y-3">
                      <div className="flex items-center gap-3 flex-wrap">
                        <span className="text-sm font-medium text-[#7A8580]">#{req.id}</span>
                        {getMergeStatusBadge(req.status)}
                        {req.target_already_member && (
                          <span className="px-2 py-1 rounded text-xs font-medium bg-[rgba(196,112,104,0.12)] text-[#C47068]">
                            Target already member
                          </span>
                        )}
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                        <div>
                          <p className="text-xs text-[#7A8580] uppercase tracking-wider mb-1">Requesting Client</p>
                          <p className="text-sm font-medium text-[#3D4A44]">
                            {req.requesting_user?.username || 'Unknown'}
                          </p>
                          <p className="text-xs text-[#7A8580]">{req.requesting_user?.email}</p>
                        </div>
                        <div>
                          <p className="text-xs text-[#7A8580] uppercase tracking-wider mb-1">Target Account</p>
                          <p className="text-sm font-medium text-[#3D4A44]">
                            {req.target_user?.username || 'Unknown'}
                          </p>
                          <p className="text-xs text-[#7A8580]">{req.target_user?.email}</p>
                        </div>
                        <div>
                          <p className="text-xs text-[#7A8580] uppercase tracking-wider mb-1">Organization</p>
                          <p className="text-sm font-medium text-[#3D4A44]">
                            {req.organization?.name || 'Unknown'}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-[#7A8580] uppercase tracking-wider mb-1">Linked Creator</p>
                          <p className="text-sm font-medium text-[#3D4A44]">
                            {req.creator?.name || 'None'}
                          </p>
                        </div>
                      </div>

                      <div className="flex flex-wrap gap-4 text-xs text-[#7A8580]">
                        <span>Created: {req.created_at ? new Date(req.created_at).toLocaleString() : '—'}</span>
                        {req.verified_at && (
                          <span>Verified: {new Date(req.verified_at).toLocaleString()}</span>
                        )}
                        {req.resolved_at && (
                          <span>Resolved: {new Date(req.resolved_at).toLocaleString()}</span>
                        )}
                      </div>

                      {req.admin_notes && (
                        <div className="bg-[#EEF1EC] rounded-lg p-3">
                          <p className="text-xs text-[#7A8580] uppercase tracking-wider mb-1">Admin Notes</p>
                          <p className="text-sm text-[#3D4A44]">{req.admin_notes}</p>
                        </div>
                      )}
                    </div>

                    {req.status === 'VERIFIED' && (
                      <div className="flex sm:flex-col gap-2 sm:min-w-[120px]">
                        <button
                          onClick={() => setApprovingMerge(req)}
                          className="flex-1 sm:flex-none px-4 py-2 bg-[#5B8A72] text-white text-sm font-medium rounded-lg hover:bg-[#4A7A62] transition-colors"
                        >
                          Approve
                        </button>
                        <button
                          onClick={() => {
                            setRejectingMerge(req)
                            setRejectNotes('')
                          }}
                          className="flex-1 sm:flex-none px-4 py-2 border border-[#C47068] text-[#C47068] text-sm font-medium rounded-lg hover:bg-[rgba(196,112,104,0.08)] transition-colors"
                        >
                          Reject
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {approvingMerge && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4" onClick={() => setApprovingMerge(null)}>
          <div className="bg-[#FAFBF9] rounded-xl shadow-2xl max-w-md w-full" onClick={e => e.stopPropagation()}>
            <div className="p-6 border-b border-[rgba(59,77,67,0.08)]">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-bold text-[#3D4A44]">Approve Merge Request</h2>
                <button onClick={() => setApprovingMerge(null)} className="text-[#7A8580] hover:text-[#3D4A44]">
                  <XMarkIcon className="w-6 h-6" />
                </button>
              </div>
            </div>
            <div className="p-6 space-y-4">
              <div className="bg-[rgba(91,138,114,0.08)] border border-[rgba(91,138,114,0.2)] rounded-lg p-4">
                <p className="text-sm text-[#3D4A44] font-medium mb-2">This will:</p>
                <ul className="text-sm text-[#7A8580] space-y-1 list-disc list-inside">
                  <li>Transfer the CLIENT membership from <span className="font-medium text-[#3D4A44]">{approvingMerge.requesting_user?.username}</span> to <span className="font-medium text-[#3D4A44]">{approvingMerge.target_user?.username}</span></li>
                  <li>Update the linked creator to point to the target account</li>
                  <li>Deactivate the original client account if no other memberships remain</li>
                </ul>
              </div>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div className="bg-[#EEF1EC] rounded-lg p-3">
                  <p className="text-xs text-[#7A8580] mb-1">From (Client)</p>
                  <p className="font-medium text-[#3D4A44]">{approvingMerge.requesting_user?.username}</p>
                  <p className="text-xs text-[#7A8580]">{approvingMerge.requesting_user?.email}</p>
                </div>
                <div className="bg-[#EEF1EC] rounded-lg p-3">
                  <p className="text-xs text-[#7A8580] mb-1">To (Target)</p>
                  <p className="font-medium text-[#3D4A44]">{approvingMerge.target_user?.username}</p>
                  <p className="text-xs text-[#7A8580]">{approvingMerge.target_user?.email}</p>
                </div>
              </div>
              <div className="flex justify-end space-x-3 pt-2">
                <button
                  onClick={() => setApprovingMerge(null)}
                  className="px-4 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg text-[#3D4A44] hover:bg-[#EEF1EC]"
                >
                  Cancel
                </button>
                <button
                  onClick={() => handleApproveMerge(approvingMerge.id)}
                  disabled={mergeActionLoading}
                  className="px-4 py-2 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] disabled:opacity-50"
                >
                  {mergeActionLoading ? 'Approving...' : 'Confirm Approval'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {rejectingMerge && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4" onClick={() => setRejectingMerge(null)}>
          <div className="bg-[#FAFBF9] rounded-xl shadow-2xl max-w-md w-full" onClick={e => e.stopPropagation()}>
            <div className="p-6 border-b border-[rgba(59,77,67,0.08)]">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-bold text-[#C47068]">Reject Merge Request</h2>
                <button onClick={() => setRejectingMerge(null)} className="text-[#7A8580] hover:text-[#3D4A44]">
                  <XMarkIcon className="w-6 h-6" />
                </button>
              </div>
            </div>
            <div className="p-6 space-y-4">
              <div className="text-sm text-[#7A8580]">
                Rejecting merge request from <span className="font-medium text-[#3D4A44]">{rejectingMerge.requesting_user?.username}</span> to <span className="font-medium text-[#3D4A44]">{rejectingMerge.target_user?.username}</span>
              </div>
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Admin Notes (optional)</label>
                <textarea
                  value={rejectNotes}
                  onChange={e => setRejectNotes(e.target.value)}
                  rows={3}
                  className="w-full px-3 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg focus:ring-2 focus:ring-[#C47068] focus:border-transparent resize-none"
                  placeholder="Reason for rejection..."
                />
              </div>
              <div className="flex justify-end space-x-3 pt-2">
                <button
                  onClick={() => setRejectingMerge(null)}
                  className="px-4 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg text-[#3D4A44] hover:bg-[#EEF1EC]"
                >
                  Cancel
                </button>
                <button
                  onClick={() => handleRejectMerge(rejectingMerge.id)}
                  disabled={mergeActionLoading}
                  className="px-4 py-2 bg-[#C47068] text-white rounded-lg hover:bg-[#A45850] disabled:opacity-50"
                >
                  {mergeActionLoading ? 'Rejecting...' : 'Reject Request'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'api-config' && integrations && (
        <div className="space-y-6">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-xl font-bold text-[#3D4A44]">API Configuration</h2>
              <p className="text-[#7A8580] text-sm mt-1">
                Platform integrations are managed securely through Replit. No API keys are exposed in the UI.
              </p>
            </div>
            <div className="flex items-center gap-2 px-4 py-2 bg-[#5B8A72]/10 rounded-lg">
              <CheckCircleIcon className="w-5 h-5 text-[#5B8A72]" />
              <span className="text-[#5B8A72] font-medium">
                {integrations.connected}/{integrations.total} Connected
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {integrations.integrations.map((integration) => (
              <div key={integration.id} className="bg-[#FAFBF9] rounded-xl shadow-sm p-6">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${
                      integration.status === 'connected' 
                        ? 'bg-[#5B9A6E]/20' 
                        : 'bg-[#C47068]/20'
                    }`}>
                      <Cog6ToothIcon className={`w-6 h-6 ${
                        integration.status === 'connected'
                          ? 'text-[#5B9A6E]'
                          : 'text-[#C47068]'
                      }`} />
                    </div>
                    <div>
                      <h3 className="font-semibold text-[#3D4A44]">{integration.name}</h3>
                      <p className="text-sm text-[#7A8580]">{integration.description}</p>
                    </div>
                  </div>
                  <div className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${
                    integration.status === 'connected'
                      ? 'bg-[#5B9A6E]/20 text-[#5B9A6E]'
                      : 'bg-[#C47068]/20 text-[#C47068]'
                  }`}>
                    {integration.status === 'connected' ? (
                      <>
                        <CheckCircleIcon className="w-3.5 h-3.5" />
                        Connected
                      </>
                    ) : (
                      <>
                        <ExclamationCircleIcon className="w-3.5 h-3.5" />
                        Not Configured
                      </>
                    )}
                  </div>
                </div>

                <div className="border-t border-[rgba(59,77,67,0.08)] pt-4">
                  <p className="text-xs text-[#7A8580] mb-2">Features Enabled:</p>
                  <div className="flex flex-wrap gap-2">
                    {integration.features.map((feature, idx) => (
                      <span 
                        key={idx}
                        className="px-2 py-1 bg-[#EEF1EC] text-[#3D4A44] text-xs rounded-md"
                      >
                        {feature}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="mt-4 pt-4 border-t border-[rgba(59,77,67,0.08)] flex items-center justify-between">
                  <p className="text-xs text-[#7A8580]">
                    <span className="font-medium">Managed by:</span> {
                      integration.managed_by === 'replit_integration'
                        ? 'Replit Integration (Secure)'
                        : 'Platform Secrets'
                    }
                  </p>
                  {integration.configurable && (
                    <button
                      onClick={() => {
                        setConfiguringIntegration(integration)
                        setShowIntegrationModal(true)
                      }}
                      className="px-3 py-1.5 text-xs font-medium bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] transition-colors"
                    >
                      Configure
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>

          <div className="bg-[#5A8A9A]/10 rounded-xl p-6">
            <h3 className="font-semibold text-[#3D4A44] mb-2">Security Note</h3>
            <p className="text-sm text-[#7A8580]">
              API credentials are stored as platform-wide secrets. They apply to all users and organizations.
              For permanent storage, credentials should also be added to Replit Secrets.
            </p>
          </div>
        </div>
      )}

      {activeTab === 'costs' && (
        <InfrastructureCostsTab
          aiUsage={aiUsage}
          aiUsageLoading={aiUsageLoading}
          onRefresh={loadAiUsage}
          onDownloadReport={handleDownloadCostReport}
          costReportLoading={costReportLoading}
        />
      )}

      {activeTab === 'support' && (
        <SupportTicketsTab
          tickets={supportTickets}
          loading={supportLoading}
          filter={supportFilter}
          onFilterChange={setSupportFilter}
          onRefresh={loadSupportTickets}
          selectedTicket={selectedSupportTicket}
          onSelectTicket={(ticket) => { setSelectedSupportTicket(ticket); setAdminNotes(ticket?.admin_notes || '') }}
          onCloseTicket={() => setSelectedSupportTicket(null)}
          onUpdateStatus={handleUpdateTicketStatus}
          updatingStatus={updatingStatus}
          adminNotes={adminNotes}
          onAdminNotesChange={setAdminNotes}
          onSaveNotes={handleSaveAdminNotes}
          savingNotes={savingNotes}
        />
      )}

      {activeTab === 'leads' && (
        <LeadsTab />
      )}

      {showIntegrationModal && configuringIntegration && (
        <IntegrationModal
          integration={configuringIntegration}
          onClose={() => {
            setShowIntegrationModal(false)
            setConfiguringIntegration(null)
          }}
          onSave={() => {
            setShowIntegrationModal(false)
            setConfiguringIntegration(null)
            loadData()
          }}
        />
      )}

      {showUserModal && (
        <UserModal
          user={editingUser}
          organizations={organizations}
          onClose={() => setShowUserModal(false)}
          onSave={() => {
            setShowUserModal(false)
            loadData()
          }}
        />
      )}

      {showOrgModal && (
        <OrgModal
          org={editingOrg}
          onClose={() => setShowOrgModal(false)}
          onSave={() => {
            setShowOrgModal(false)
            loadData()
          }}
        />
      )}

      {deletingOrg && (
        <DeleteOrgModal
          org={deletingOrg}
          onClose={() => setDeletingOrg(null)}
          onConfirm={() => handleDeleteOrg(deletingOrg.id)}
        />
      )}

      {resetPasswordUser && (
        <AdminResetPasswordModal
          user={resetPasswordUser}
          onClose={() => setResetPasswordUser(null)}
          onSuccess={() => {
            setResetPasswordUser(null)
          }}
        />
      )}
    </div>
  )
}

function StatCard({ icon: Icon, title, value, subtitle, color }) {
  return (
    <div className="bg-[#FAFBF9] rounded-xl shadow-sm p-6">
      <div className="flex items-center space-x-3 mb-3">
        <div className="p-2 rounded-lg" style={{ backgroundColor: `${color}20` }}>
          <Icon className="w-6 h-6" style={{ color }} />
        </div>
        <h3 className="font-medium text-[#3D4A44]">{title}</h3>
      </div>
      <div className="text-3xl font-bold text-[#3D4A44]">{value}</div>
      {subtitle && <div className="text-sm text-[#7A8580] mt-1">{subtitle}</div>}
    </div>
  )
}

function UserModal({ user, organizations, onClose, onSave }) {
  const [formData, setFormData] = useState({
    username: user?.username || '',
    email: user?.email || '',
    password: '',
    is_admin: user?.is_admin || false,
    organization_id: user?.organizations?.[0]?.id || '',
    organization_role: 'OWNER'
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError(null)
    
    try {
      if (user) {
        const updateData = { ...formData }
        if (!updateData.password) delete updateData.password
        await axios.put(`/api/admin/users/${user.id}`, updateData)
      } else {
        await axios.post('/api/admin/users', formData)
      }
      onSave()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save user')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-[#FAFBF9] rounded-xl shadow-2xl max-w-lg w-full" onClick={e => e.stopPropagation()}>
        <div className="p-6 border-b border-[rgba(59,77,67,0.08)]">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-[#3D4A44]">
              {user ? 'Edit User' : 'Add User'}
            </h2>
            <button onClick={onClose} className="text-[#7A8580] hover:text-[#3D4A44]">
              <XMarkIcon className="w-6 h-6" />
            </button>
          </div>
        </div>
        
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-[rgba(196,112,104,0.12)] text-[#C47068] rounded-lg text-sm">
              {error}
            </div>
          )}
          
          <div>
            <label className="block text-sm font-medium text-[#3D4A44] mb-1">Username</label>
            <input
              type="text"
              value={formData.username}
              onChange={e => setFormData({...formData, username: e.target.value})}
              className="w-full px-3 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
              required
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-[#3D4A44] mb-1">Email</label>
            <input
              type="email"
              value={formData.email}
              onChange={e => setFormData({...formData, email: e.target.value})}
              className="w-full px-3 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
              required
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-[#3D4A44] mb-1">
              Password {user && '(leave blank to keep current)'}
            </label>
            <input
              type="password"
              value={formData.password}
              onChange={e => setFormData({...formData, password: e.target.value})}
              className="w-full px-3 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
              required={!user}
            />
          </div>
          
          {!user && (
            <div>
              <label className="block text-sm font-medium text-[#3D4A44] mb-1">Organization</label>
              <select
                value={formData.organization_id}
                onChange={e => setFormData({...formData, organization_id: e.target.value})}
                className="w-full px-3 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
              >
                <option value="">No organization</option>
                {organizations.map(org => (
                  <option key={org.id} value={org.id}>{org.name}</option>
                ))}
              </select>
            </div>
          )}
          
          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              id="is_admin"
              checked={formData.is_admin}
              onChange={e => setFormData({...formData, is_admin: e.target.checked})}
              className="rounded border-[rgba(59,77,67,0.12)] text-[#5B8A72] focus:ring-[#5B8A72]"
            />
            <label htmlFor="is_admin" className="text-sm text-[#3D4A44]">
              Organization Admin
            </label>
          </div>
          
          <div className="flex justify-end space-x-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg text-[#3D4A44] hover:bg-[#EEF1EC]"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function OrgModal({ org, onClose, onSave }) {
  const [formData, setFormData] = useState({
    name: org?.name || '',
    display_name: org?.display_name || '',
    type: org?.type || 'MANAGER',
    logo_url: org?.logo_url || '',
    logo_orientation: org?.logo_orientation || 'square',
    primary_color: org?.primary_color || ''
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError(null)
    
    try {
      if (org) {
        await axios.put(`/api/admin/organizations/${org.id}`, formData)
      } else {
        await axios.post('/api/admin/organizations', formData)
      }
      onSave()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save organization')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-[#FAFBF9] rounded-xl shadow-2xl max-w-lg w-full" onClick={e => e.stopPropagation()}>
        <div className="p-6 border-b border-[rgba(59,77,67,0.08)]">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-[#3D4A44]">
              {org ? 'Edit Organization' : 'Add Organization'}
            </h2>
            <button onClick={onClose} className="text-[#7A8580] hover:text-[#3D4A44]">
              <XMarkIcon className="w-6 h-6" />
            </button>
          </div>
        </div>
        
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-[rgba(196,112,104,0.12)] text-[#C47068] rounded-lg text-sm">
              {error}
            </div>
          )}
          
          <div>
            <label className="block text-sm font-medium text-[#3D4A44] mb-1">Name</label>
            <input
              type="text"
              value={formData.name}
              onChange={e => setFormData({...formData, name: e.target.value})}
              className="w-full px-3 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
              required
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-[#3D4A44] mb-1">Display Name</label>
            <input
              type="text"
              value={formData.display_name}
              onChange={e => setFormData({...formData, display_name: e.target.value})}
              className="w-full px-3 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
              placeholder="Company display name"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-[#3D4A44] mb-1">Type</label>
            <select
              value={formData.type}
              onChange={e => setFormData({...formData, type: e.target.value})}
              className="w-full px-3 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
            >
              <option value="MANAGER">Manager</option>
              <option value="LABEL">Label</option>
              <option value="PUBLISHER">Publisher</option>
              <option value="PRODUCTION_COMPANY">Production Company</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-[#3D4A44] mb-1">Logo URL</label>
            <input
              type="text"
              value={formData.logo_url}
              onChange={e => setFormData({...formData, logo_url: e.target.value})}
              className="w-full px-3 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
              placeholder="https://..."
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-[#3D4A44] mb-1">Logo Orientation</label>
            <select
              value={formData.logo_orientation}
              onChange={e => setFormData({...formData, logo_orientation: e.target.value})}
              className="w-full px-3 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
            >
              <option value="square">Square (1:1)</option>
              <option value="horizontal">Horizontal (landscape)</option>
              <option value="vertical">Vertical (portrait)</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-[#3D4A44] mb-1">Primary Color</label>
            <input
              type="text"
              value={formData.primary_color}
              onChange={e => setFormData({...formData, primary_color: e.target.value})}
              className="w-full px-3 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
              placeholder="#5B8A72"
            />
          </div>
          
          <div className="flex justify-end space-x-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg text-[#3D4A44] hover:bg-[#EEF1EC]"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function DeleteOrgModal({ org, onClose, onConfirm }) {
  const [confirmText, setConfirmText] = useState('')
  const [deleting, setDeleting] = useState(false)
  const orgName = org.display_name || org.name

  const handleDelete = async () => {
    setDeleting(true)
    await onConfirm()
    setDeleting(false)
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-[#FAFBF9] rounded-xl shadow-2xl max-w-md w-full" onClick={e => e.stopPropagation()}>
        <div className="p-6 border-b border-[rgba(59,77,67,0.08)]">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-[#C47068]">Delete Organization</h2>
            <button onClick={onClose} className="text-[#7A8580] hover:text-[#3D4A44]">
              <XMarkIcon className="w-6 h-6" />
            </button>
          </div>
        </div>
        <div className="p-6">
          <div className="bg-[rgba(196,112,104,0.08)] border border-[rgba(196,112,104,0.2)] rounded-lg p-4 mb-4">
            <p className="text-sm text-[#C47068] font-medium mb-1">This action is permanent and cannot be undone.</p>
            <p className="text-sm text-[#7A8580]">
              All data associated with <span className="font-semibold text-[#3D4A44]">{orgName}</span> will be permanently deleted, including members, creators, songs, works, releases, contracts, placements, royalty data, and all other records.
            </p>
          </div>
          <div className="mb-4">
            <label className="block text-sm font-medium text-[#3D4A44] mb-1">
              Type <span className="font-semibold">{orgName}</span> to confirm
            </label>
            <input
              type="text"
              value={confirmText}
              onChange={e => setConfirmText(e.target.value)}
              className="w-full px-3 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg focus:ring-2 focus:ring-[#C47068] focus:border-transparent"
              placeholder={orgName}
              autoFocus
            />
          </div>
          <div className="flex justify-end space-x-3">
            <button
              onClick={onClose}
              className="px-4 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg text-[#3D4A44] hover:bg-[#EEF1EC]"
            >
              Cancel
            </button>
            <button
              onClick={handleDelete}
              disabled={confirmText !== orgName || deleting}
              className="px-4 py-2 bg-[#C47068] text-white rounded-lg hover:bg-[#A45850] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {deleting ? 'Deleting...' : 'Delete Organization'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function IntegrationModal({ integration, onClose, onSave }) {
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState(null)
  const [oauthBusy, setOauthBusy] = useState(false)
  const [copied, setCopied] = useState(false)

  const handleTest = async () => {
    setTesting(true)
    setTestResult(null)
    try {
      const res = await axios.post(`/api/admin/integrations/${integration.id}/test`)
      setTestResult(res.data)
    } catch (err) {
      setTestResult({ success: false, message: err.response?.data?.detail || 'Test failed' })
    } finally {
      setTesting(false)
    }
  }

  const handleSpotifyConnect = async () => {
    setOauthBusy(true)
    setTestResult(null)
    let popup = null
    try {
      // Open the popup synchronously inside the click handler so popup
      // blockers don't kill it; navigate it to the OAuth start URL only
      // after we have a freshly-minted nonce in hand.
      popup = window.open('about:blank', 'spotify_oauth', 'width=560,height=720')
      const res = await axios.post('/api/spotify/oauth/start-nonce')
      const nonce = res.data?.nonce
      if (!nonce) throw new Error('No nonce returned')
      const url = `/api/spotify/oauth/start?nonce=${encodeURIComponent(nonce)}`
      if (popup && !popup.closed) {
        popup.location.replace(url)
      } else {
        window.open(url, 'spotify_oauth', 'width=560,height=720')
      }
    } catch (err) {
      if (popup && !popup.closed) popup.close()
      setTestResult({ success: false, message: err.response?.data?.detail || err.message || 'Could not start Spotify OAuth' })
    } finally {
      setOauthBusy(false)
    }
  }

  // Listen for the popup's completion postMessage and trigger a refresh.
  useEffect(() => {
    const handler = (ev) => {
      const msg = ev.data
      if (!msg || msg.type !== 'spotify_oauth_result') return
      if (msg.success) {
        setTestResult({ success: true, message: 'Spotify account connected.' })
        onSave && onSave()
      } else {
        setTestResult({ success: false, message: `Spotify connection failed: ${msg.reason || 'unknown'}` })
      }
    }
    window.addEventListener('message', handler)
    return () => window.removeEventListener('message', handler)
  }, [onSave])

  const handleSpotifyDisconnect = async () => {
    if (!window.confirm('Disconnect the Spotify account from Cadence? Authenticated Spotify calls will fall back to client-credentials only.')) return
    setOauthBusy(true)
    try {
      await axios.post('/api/spotify/oauth/disconnect')
      setTestResult({ success: true, message: 'Spotify disconnected.' })
      onSave && onSave()
    } catch (err) {
      setTestResult({ success: false, message: err.response?.data?.detail || 'Disconnect failed' })
    } finally {
      setOauthBusy(false)
    }
  }

  const copyRedirectUri = async () => {
    if (!integration.oauth?.redirect_uri) return
    try {
      await navigator.clipboard.writeText(integration.oauth.redirect_uri)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      setCopied(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-[#FAFBF9] rounded-xl shadow-xl w-full max-w-lg p-6 mx-4">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-xl font-bold text-[#3D4A44]">Configure {integration.name}</h2>
            <p className="text-sm text-[#7A8580] mt-1">{integration.description}</p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-[#EEF1EC] rounded-lg">
            <XMarkIcon className="w-5 h-5 text-[#7A8580]" />
          </button>
        </div>

        <div className="space-y-4">
          <div className="bg-[#5A8A9A]/10 rounded-lg p-4">
            <h3 className="font-medium text-[#3D4A44] mb-2">Setup Instructions</h3>
            <p className="text-sm text-[#7A8580] mb-3">
              Add the following secrets to the Replit Secrets panel (Tools &gt; Secrets):
            </p>
            <div className="space-y-2">
              {integration.fields?.map(field => (
                <div key={field.key} className="flex items-center justify-between bg-white rounded-lg p-3 border border-[rgba(59,77,67,0.12)]">
                  <div>
                    <code className="text-sm font-mono text-[#5B8A72]">{field.key}</code>
                    <p className="text-xs text-[#7A8580] mt-0.5">{field.label}</p>
                  </div>
                  {field.has_value ? (
                    <span className="flex items-center gap-1 text-xs text-[#5B9A6E]">
                      <CheckCircleIcon className="w-4 h-4" />
                      Configured
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-xs text-[#C47068]">
                      <ExclamationCircleIcon className="w-4 h-4" />
                      Missing
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>

          {integration.id === 'spotify' && integration.oauth && (
            <div className="bg-[#1DB954]/10 rounded-lg p-4 border border-[#1DB954]/20">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-medium text-[#3D4A44]">Listener Account (OAuth)</h3>
                {integration.oauth.connected ? (
                  <span className="flex items-center gap-1 text-xs font-medium text-[#5B9A6E]">
                    <CheckCircleIcon className="w-4 h-4" />
                    Connected
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-xs font-medium text-[#C47068]">
                    <ExclamationCircleIcon className="w-4 h-4" />
                    Not connected
                  </span>
                )}
              </div>
              {integration.oauth.connected ? (
                <div className="text-sm text-[#7A8580] space-y-1 mb-3">
                  <div>Connected as <span className="font-medium text-[#3D4A44]">{integration.oauth.connected_as || integration.oauth.connected_email || 'listener'}</span></div>
                  {integration.oauth.token_expires_at && (
                    <div className="text-xs">Access token refreshes automatically (current expiry: {new Date(integration.oauth.token_expires_at).toLocaleString()})</div>
                  )}
                </div>
              ) : (
                <p className="text-sm text-[#7A8580] mb-3">
                  Sign a Spotify listener account in to enable playlist import, release lookup, and pasted-URL track auto-fill.
                </p>
              )}
              {integration.oauth.redirect_uri && (
                <div className="bg-white rounded-lg p-3 border border-[rgba(59,77,67,0.12)] mb-3">
                  <div className="text-xs text-[#7A8580] mb-1">Add this Redirect URI to your Spotify Developer app first:</div>
                  <div className="flex items-center gap-2">
                    <code className="text-xs font-mono text-[#3D4A44] flex-1 break-all">{integration.oauth.redirect_uri}</code>
                    <button
                      type="button"
                      onClick={copyRedirectUri}
                      className="px-2 py-1 text-xs border border-[rgba(59,77,67,0.12)] rounded hover:bg-[#EEF1EC]"
                    >
                      {copied ? 'Copied' : 'Copy'}
                    </button>
                  </div>
                </div>
              )}
              <div className="flex gap-2">
                {integration.oauth.connected ? (
                  <button
                    type="button"
                    onClick={handleSpotifyDisconnect}
                    disabled={oauthBusy}
                    className="px-3 py-1.5 text-sm border border-[#C47068] text-[#C47068] rounded-lg hover:bg-[#C47068]/10 disabled:opacity-50"
                  >
                    {oauthBusy ? 'Disconnecting...' : 'Disconnect'}
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={handleSpotifyConnect}
                    disabled={!integration.oauth.configured}
                    className="px-3 py-1.5 text-sm bg-[#1DB954] text-white rounded-lg hover:bg-[#1aa84a] disabled:opacity-50"
                  >
                    Connect Spotify Account
                  </button>
                )}
                <button
                  type="button"
                  onClick={handleSpotifyConnect}
                  disabled={!integration.oauth.configured || !integration.oauth.connected}
                  className="px-3 py-1.5 text-sm border border-[rgba(59,77,67,0.12)] text-[#3D4A44] rounded-lg hover:bg-[#EEF1EC] disabled:opacity-50"
                  title="Re-authorize with a different Spotify account"
                >
                  Reconnect
                </button>
              </div>
              {!integration.oauth.configured && (
                <p className="text-xs text-[#C47068] mt-2">
                  Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET secrets first.
                </p>
              )}
            </div>
          )}

          {testResult && (
            <div className={`p-3 rounded-lg ${testResult.success ? 'bg-[#5B9A6E]/10 text-[#5B9A6E]' : 'bg-[#C47068]/10 text-[#C47068]'}`}>
              <div className="flex items-center gap-2">
                {testResult.success ? (
                  <CheckCircleIcon className="w-5 h-5" />
                ) : (
                  <ExclamationCircleIcon className="w-5 h-5" />
                )}
                <span className="text-sm font-medium">{testResult.message}</span>
              </div>
            </div>
          )}

          <div className="flex justify-between pt-4">
            <button
              type="button"
              onClick={handleTest}
              disabled={testing}
              className="px-4 py-2 border border-[#5B8A72] text-[#5B8A72] rounded-lg hover:bg-[#5B8A72]/10 disabled:opacity-50"
            >
              {testing ? 'Testing...' : 'Test Connection'}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg text-[#3D4A44] hover:bg-[#EEF1EC]"
            >
              Close
            </button>
          </div>
        </div>

        <div className="mt-4 pt-4 border-t border-[rgba(59,77,67,0.08)]">
          <p className="text-xs text-[#7A8580]">
            Secrets are stored securely in Replit and apply to all users across the platform.
            After adding secrets, restart the app for changes to take effect.
          </p>
        </div>
      </div>
    </div>
  )
}

const INFRASTRUCTURE_SERVICES = [
  {
    category: 'AI & Intelligence',
    icon: CpuChipIcon,
    color: '#8B6EAE',
    services: [
      {
        name: 'OpenAI (GPT-4o-mini)',
        tier: 'Pay-per-use',
        baseCost: '$0 base',
        notes: '~$0.015/1K input, $0.060/1K output tokens',
        features: ['Contract Parsing', 'Audio Analysis', 'Brief Builder', 'CSV Mapping', 'Royalty PDF Parsing'],
        scaling: { 10: '$5-15/mo', 100: '$25-75/mo', 1000: '$150-500/mo' },
      },
    ],
  },
  {
    category: 'Email & Communications',
    icon: EnvelopeIcon,
    color: '#5A8A9A',
    services: [
      {
        name: 'Google Workspace',
        tier: '$84/yr per mailbox',
        baseCost: '$7/mo',
        notes: 'Domain email hosting (communication@cadence-ci.com)',
        features: ['Domain Email', 'Email Routing', 'Workspace Admin'],
        scaling: { 10: '$7/mo', 100: '$7/mo', 1000: '$7/mo' },
      },
      {
        name: 'Resend',
        tier: 'Free tier (100 emails/day)',
        baseCost: '$0/mo',
        notes: 'Notifications, digests, sharing invitations, registration reports',
        features: ['Transactional Email', 'Branded Templates', 'Digest Notifications'],
        scaling: { 10: '$0/mo', 100: '$0-20/mo', 1000: '$20-50/mo' },
      },
    ],
  },
  {
    category: 'Cloud Storage',
    icon: CloudIcon,
    color: '#5B9A6E',
    services: [
      {
        name: 'Dropbox API',
        tier: 'App access (free)',
        baseCost: '$0/mo',
        notes: 'Audio file linking, org-wide scanning, creator folder linking',
        features: ['Audio File Linking', 'Org-wide Scan', 'Creator Storage'],
        scaling: { 10: '$0/mo', 100: '$0/mo', 1000: '$0/mo' },
      },
      {
        name: 'Google Drive API',
        tier: 'Free tier',
        baseCost: '$0/mo',
        notes: 'Audio file browsing and linking',
        features: ['File Browsing', 'Audio Linking'],
        scaling: { 10: '$0/mo', 100: '$0/mo', 1000: '$0/mo' },
      },
    ],
  },
  {
    category: 'Music APIs',
    icon: MusicalNoteIcon,
    color: '#C4956B',
    services: [
      {
        name: 'Spotify Web API',
        tier: 'Premium account (required)',
        baseCost: '~$10.99/mo',
        notes: 'Playlist import, track search, release metadata lookup',
        features: ['Playlist Import', 'Track Search', 'Release Lookup'],
        scaling: { 10: '~$10.99/mo', 100: '~$10.99/mo', 1000: '~$10.99/mo' },
      },
      {
        name: 'YouTube Data API',
        tier: 'Free tier (10K units/day)',
        baseCost: '$0/mo',
        notes: 'Streaming credits chart data ingestion',
        features: ['Chart Data'],
        scaling: { 10: '$0/mo', 100: '$0/mo', 1000: '$0/mo' },
      },
      {
        name: 'Last.fm API',
        tier: 'Free tier',
        baseCost: '$0/mo',
        notes: 'Streaming credits and chart data',
        features: ['Chart Data'],
        scaling: { 10: '$0/mo', 100: '$0/mo', 1000: '$0/mo' },
      },
    ],
  },
  {
    category: 'Infrastructure',
    icon: ServerIcon,
    color: '#5B8A72',
    services: [
      {
        name: 'PostgreSQL (Managed)',
        tier: 'Included with hosting plan',
        baseCost: 'Included',
        notes: 'Primary database for all application data',
        features: ['Data Storage', 'Full-text Search', 'Indexing'],
        scaling: { 10: 'Included', 100: 'Included', 1000: '$20-50/mo (dedicated)' },
      },
      {
        name: 'Cloud Hosting',
        tier: 'Managed Deployments',
        baseCost: '~$25/mo',
        notes: 'Application hosting with auto-scaling',
        features: ['App Hosting', 'SSL', 'Custom Domain'],
        scaling: { 10: '~$25/mo', 100: '~$25/mo', 1000: '$50-100/mo' },
      },
      {
        name: 'Domain (cadence-ci.com)',
        tier: 'Annual registration',
        baseCost: '~$12/yr',
        notes: 'Primary domain for the platform',
        features: ['Custom Domain', 'Email Routing'],
        scaling: { 10: '$12/yr', 100: '$12/yr', 1000: '$12/yr' },
      },
    ],
  },
  {
    category: 'Push Notifications',
    icon: BellAlertIcon,
    color: '#C47068',
    services: [
      {
        name: 'Web Push (VAPID)',
        tier: 'Free (self-hosted)',
        baseCost: '$0/mo',
        notes: 'Browser push notifications via pywebpush',
        features: ['Push Notifications', 'PWA Support'],
        scaling: { 10: '$0/mo', 100: '$0/mo', 1000: '$0/mo' },
      },
    ],
  },
]

const FEATURE_LABELS = {
  contract_parsing: 'AI Contract Parsing',
  audio_analysis: 'AI Audio Analysis',
  brief_builder: 'Brief Builder',
  csv_mapping: 'CSV Column Mapping',
  royalty_pdf_parsing: 'Royalty PDF Parsing',
}

function SupportTicketsTab({ tickets, loading, filter, onFilterChange, onRefresh, selectedTicket, onSelectTicket, onCloseTicket, onUpdateStatus, updatingStatus, adminNotes, onAdminNotesChange, onSaveNotes, savingNotes }) {
  const statusOptions = [
    { value: 'all', label: 'All' },
    { value: 'OPEN', label: 'Open', color: '#C47068' },
    { value: 'IN_PROGRESS', label: 'In Progress', color: '#C4956B' },
    { value: 'RESOLVED', label: 'Resolved', color: '#5B8A72' },
    { value: 'CLOSED', label: 'Closed', color: '#7A8580' },
  ]

  const categoryLabels = { BUG_REPORT: 'Bug Report', FEATURE_REQUEST: 'Feature Request', GENERAL_SUPPORT: 'General Support' }
  const categoryColors = { BUG_REPORT: '#C47068', FEATURE_REQUEST: '#5A8A9A', GENERAL_SUPPORT: '#5B8A72' }

  const statusColors = { OPEN: '#C47068', IN_PROGRESS: '#C4956B', RESOLVED: '#5B8A72', CLOSED: '#7A8580' }
  const statusLabels = { OPEN: 'Open', IN_PROGRESS: 'In Progress', RESOLVED: 'Resolved', CLOSED: 'Closed' }

  const formatDate = (iso) => {
    if (!iso) return ''
    return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' })
  }

  const openCount = tickets.filter(t => t.status === 'OPEN').length
  const inProgressCount = tickets.filter(t => t.status === 'IN_PROGRESS').length

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-4">
          <h3 className="text-lg font-bold text-[#3D4A44]">Support Tickets</h3>
          {openCount > 0 && (
            <span className="px-2.5 py-1 rounded-full text-xs font-medium" style={{ backgroundColor: '#C4706818', color: '#C47068' }}>
              {openCount} open
            </span>
          )}
          {inProgressCount > 0 && (
            <span className="px-2.5 py-1 rounded-full text-xs font-medium" style={{ backgroundColor: '#C4956B18', color: '#C4956B' }}>
              {inProgressCount} in progress
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <div className="flex rounded-lg overflow-hidden border border-[rgba(59,77,67,0.12)]">
            {statusOptions.map(opt => (
              <button
                key={opt.value}
                onClick={() => onFilterChange(opt.value)}
                className={`px-3 py-1.5 text-xs font-medium transition-colors ${
                  filter === opt.value
                    ? 'bg-[#5B8A72] text-white'
                    : 'bg-white text-[#7A8580] hover:bg-[#F5F7F4]'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
          <button onClick={onRefresh} className="p-2 hover:bg-[#F5F7F4] rounded-lg" title="Refresh">
            <ArrowPathIcon className={`w-4 h-4 text-[#7A8580] ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <ArrowPathIcon className="w-6 h-6 text-[#7A8580] animate-spin" />
        </div>
      ) : tickets.length === 0 ? (
        <div className="text-center py-16">
          <LifebuoyIcon className="w-12 h-12 text-[#B0B5B2] mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-[#3D4A44] mb-1">No tickets</h3>
          <p className="text-sm text-[#7A8580]">{filter !== 'all' ? `No ${statusLabels[filter]?.toLowerCase()} tickets found.` : 'No support tickets have been submitted yet.'}</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-[rgba(59,77,67,0.12)] overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-[#F5F7F4] border-b border-[rgba(59,77,67,0.08)]">
                  <th className="text-left text-xs font-semibold text-[#7A8580] uppercase tracking-wider px-4 py-3">ID</th>
                  <th className="text-left text-xs font-semibold text-[#7A8580] uppercase tracking-wider px-4 py-3">Subject</th>
                  <th className="text-left text-xs font-semibold text-[#7A8580] uppercase tracking-wider px-4 py-3">Category</th>
                  <th className="text-left text-xs font-semibold text-[#7A8580] uppercase tracking-wider px-4 py-3">User</th>
                  <th className="text-left text-xs font-semibold text-[#7A8580] uppercase tracking-wider px-4 py-3">Org</th>
                  <th className="text-left text-xs font-semibold text-[#7A8580] uppercase tracking-wider px-4 py-3">Status</th>
                  <th className="text-left text-xs font-semibold text-[#7A8580] uppercase tracking-wider px-4 py-3">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[rgba(59,77,67,0.06)]">
                {tickets.map(ticket => (
                  <tr
                    key={ticket.id}
                    onClick={() => onSelectTicket(ticket)}
                    className="hover:bg-[#F5F7F4]/50 cursor-pointer transition-colors"
                  >
                    <td className="px-4 py-3 text-sm text-[#7A8580]">#{ticket.id}</td>
                    <td className="px-4 py-3">
                      <p className="text-sm font-medium text-[#3D4A44] truncate max-w-[250px]">{ticket.subject}</p>
                      {ticket.attachments?.length > 0 && (
                        <span className="text-xs text-[#7A8580]">{ticket.attachments.length} attachment{ticket.attachments.length > 1 ? 's' : ''}</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
                        style={{ backgroundColor: `${categoryColors[ticket.category] || '#5B8A72'}18`, color: categoryColors[ticket.category] || '#5B8A72' }}
                      >
                        {categoryLabels[ticket.category] || ticket.category}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-[#3D4A44]">{ticket.user?.username || 'Unknown'}</td>
                    <td className="px-4 py-3 text-sm text-[#7A8580]">{ticket.organization?.name || '-'}</td>
                    <td className="px-4 py-3">
                      <span
                        className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium"
                        style={{ backgroundColor: `${statusColors[ticket.status] || '#7A8580'}18`, color: statusColors[ticket.status] || '#7A8580' }}
                      >
                        {statusLabels[ticket.status] || ticket.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-[#7A8580] whitespace-nowrap">{formatDate(ticket.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {selectedTicket && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={onCloseTicket}>
          <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[85vh] overflow-auto shadow-xl" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between p-5 border-b border-[rgba(59,77,67,0.08)]">
              <div>
                <h3 className="text-lg font-bold text-[#3D4A44]">Ticket #{selectedTicket.id}</h3>
                <p className="text-xs text-[#7A8580]">by {selectedTicket.user?.username} {selectedTicket.organization ? `(${selectedTicket.organization.name})` : ''}</p>
              </div>
              <button onClick={onCloseTicket} className="p-1 hover:bg-[#F5F7F4] rounded-lg">
                <XMarkIcon className="w-5 h-5 text-[#7A8580]" />
              </button>
            </div>
            <div className="p-5 space-y-5">
              <div className="flex items-center gap-2 flex-wrap">
                <span
                  className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium"
                  style={{ backgroundColor: `${statusColors[selectedTicket.status]}18`, color: statusColors[selectedTicket.status] }}
                >
                  {statusLabels[selectedTicket.status]}
                </span>
                <span
                  className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
                  style={{ backgroundColor: `${categoryColors[selectedTicket.category] || '#5B8A72'}18`, color: categoryColors[selectedTicket.category] || '#5B8A72' }}
                >
                  {categoryLabels[selectedTicket.category] || selectedTicket.category}
                </span>
                <span className="text-xs text-[#7A8580] ml-auto">{formatDate(selectedTicket.created_at)}</span>
              </div>

              <div>
                <h4 className="font-semibold text-[#3D4A44] mb-2">{selectedTicket.subject}</h4>
                <div className="bg-[#F5F7F4] rounded-xl p-4">
                  <p className="text-sm text-[#3D4A44] whitespace-pre-wrap">{selectedTicket.description}</p>
                </div>
              </div>

              {selectedTicket.attachments?.length > 0 && (
                <div>
                  <p className="text-sm font-medium text-[#3D4A44] mb-2">Attachments</p>
                  <div className="flex flex-wrap gap-3">
                    {selectedTicket.attachments.map(att => (
                      <a key={att.id} href={att.url} target="_blank" rel="noreferrer" className="block">
                        <img src={att.url} alt={att.file_name} className="w-40 h-40 object-cover rounded-xl border border-[rgba(59,77,67,0.12)] hover:border-[#5B8A72] transition-colors" />
                        <p className="text-[10px] text-[#7A8580] mt-1 max-w-[160px] truncate">{att.file_name}</p>
                      </a>
                    ))}
                  </div>
                </div>
              )}

              <div>
                <p className="text-sm font-medium text-[#3D4A44] mb-2">Update Status</p>
                <div className="flex flex-wrap gap-2">
                  {['OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED'].map(s => (
                    <button
                      key={s}
                      onClick={() => onUpdateStatus(selectedTicket.id, s)}
                      disabled={selectedTicket.status === s || updatingStatus}
                      className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                        selectedTicket.status === s
                          ? 'text-white'
                          : 'bg-[#F5F7F4] text-[#3D4A44] hover:bg-[#E8ECE6]'
                      } disabled:opacity-50`}
                      style={selectedTicket.status === s ? { backgroundColor: statusColors[s] } : {}}
                    >
                      {statusLabels[s]}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <p className="text-sm font-medium text-[#3D4A44] mb-2">Admin Notes</p>
                <textarea
                  value={adminNotes}
                  onChange={e => onAdminNotesChange(e.target.value)}
                  rows={3}
                  placeholder="Internal notes about this ticket..."
                  className="w-full px-4 py-2.5 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm text-[#3D4A44] placeholder-[#B0B5B2] focus:outline-none focus:ring-2 focus:ring-[#5B8A72]/20 focus:border-[#5B8A72] resize-none"
                />
                <div className="flex justify-end mt-2">
                  <button
                    onClick={() => onSaveNotes(selectedTicket.id)}
                    disabled={savingNotes}
                    className="px-4 py-2 text-sm font-medium bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] disabled:opacity-50"
                  >
                    {savingNotes ? 'Saving...' : 'Save Notes'}
                  </button>
                </div>
              </div>

              {selectedTicket.resolved_at && (
                <p className="text-xs text-[#5B8A72]">Resolved: {formatDate(selectedTicket.resolved_at)}</p>
              )}
              {selectedTicket.closed_at && (
                <p className="text-xs text-[#7A8580]">Closed: {formatDate(selectedTicket.closed_at)}</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function InfrastructureCostsTab({ aiUsage, aiUsageLoading, onRefresh, onDownloadReport, costReportLoading }) {
  const currentMonth = aiUsage?.current_month || { call_count: 0, total_tokens: 0, total_cost_cents: 0 }
  const totals = aiUsage?.totals || { call_count: 0, total_tokens: 0, total_cost_cents: 0 }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-xl font-bold text-[#3D4A44]">Infrastructure Costs</h2>
          <p className="text-[#7A8580] text-sm mt-1">
            Service costs, AI usage tracking, and scaling projections
          </p>
        </div>
        <button
          onClick={onDownloadReport}
          disabled={costReportLoading}
          className="flex items-center gap-2 px-4 py-2.5 bg-[#5B8A72] text-white rounded-xl hover:bg-[#4A7A62] transition-colors disabled:opacity-50 font-medium text-sm shadow-sm"
        >
          <ArrowDownTrayIcon className="w-4 h-4" />
          {costReportLoading ? 'Generating...' : 'Download Cost Report'}
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-[#FAFBF9] rounded-xl shadow-sm p-5">
          <div className="flex items-center gap-2 mb-2">
            <div className="p-1.5 rounded-lg bg-[#8B6EAE]/20">
              <BoltIcon className="w-4 h-4 text-[#8B6EAE]" />
            </div>
            <span className="text-xs text-[#7A8580] uppercase tracking-wider">AI Calls This Month</span>
          </div>
          <p className="text-2xl font-bold text-[#3D4A44]">{currentMonth.call_count.toLocaleString()}</p>
        </div>
        <div className="bg-[#FAFBF9] rounded-xl shadow-sm p-5">
          <div className="flex items-center gap-2 mb-2">
            <div className="p-1.5 rounded-lg bg-[#5A8A9A]/20">
              <CpuChipIcon className="w-4 h-4 text-[#5A8A9A]" />
            </div>
            <span className="text-xs text-[#7A8580] uppercase tracking-wider">Tokens This Month</span>
          </div>
          <p className="text-2xl font-bold text-[#3D4A44]">{currentMonth.total_tokens.toLocaleString()}</p>
        </div>
        <div className="bg-[#FAFBF9] rounded-xl shadow-sm p-5">
          <div className="flex items-center gap-2 mb-2">
            <div className="p-1.5 rounded-lg bg-[#5B9A6E]/20">
              <CurrencyDollarIcon className="w-4 h-4 text-[#5B9A6E]" />
            </div>
            <span className="text-xs text-[#7A8580] uppercase tracking-wider">AI Cost This Month</span>
          </div>
          <p className="text-2xl font-bold text-[#5B9A6E]">${(currentMonth.total_cost_cents / 100).toFixed(2)}</p>
        </div>
      </div>

      {aiUsage?.by_feature && aiUsage.by_feature.length > 0 && (
        <div className="bg-[#FAFBF9] rounded-xl shadow-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-[#3D4A44]">AI Usage by Feature</h3>
            <button
              onClick={onRefresh}
              disabled={aiUsageLoading}
              className="text-xs text-[#5B8A72] hover:text-[#4A7A62] font-medium"
            >
              {aiUsageLoading ? 'Loading...' : 'Refresh'}
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[rgba(59,77,67,0.08)]">
                  <th className="text-left py-2 text-[#7A8580] font-medium">Feature</th>
                  <th className="text-right py-2 text-[#7A8580] font-medium">Calls</th>
                  <th className="text-right py-2 text-[#7A8580] font-medium hidden sm:table-cell">Input Tokens</th>
                  <th className="text-right py-2 text-[#7A8580] font-medium hidden sm:table-cell">Output Tokens</th>
                  <th className="text-right py-2 text-[#7A8580] font-medium">Total Tokens</th>
                  <th className="text-right py-2 text-[#7A8580] font-medium">Est. Cost</th>
                </tr>
              </thead>
              <tbody>
                {aiUsage.by_feature.map((f) => (
                  <tr key={f.feature} className="border-b border-[rgba(59,77,67,0.04)]">
                    <td className="py-2.5 text-[#3D4A44] font-medium">{FEATURE_LABELS[f.feature] || f.feature}</td>
                    <td className="py-2.5 text-right text-[#3D4A44]">{f.call_count}</td>
                    <td className="py-2.5 text-right text-[#7A8580] hidden sm:table-cell">{f.total_input_tokens?.toLocaleString()}</td>
                    <td className="py-2.5 text-right text-[#7A8580] hidden sm:table-cell">{f.total_output_tokens?.toLocaleString()}</td>
                    <td className="py-2.5 text-right text-[#3D4A44]">{f.total_tokens.toLocaleString()}</td>
                    <td className="py-2.5 text-right text-[#5B9A6E] font-medium">${(f.total_cost_cents / 100).toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="border-t-2 border-[rgba(59,77,67,0.12)]">
                  <td className="py-2.5 font-semibold text-[#3D4A44]">Total</td>
                  <td className="py-2.5 text-right font-semibold text-[#3D4A44]">{totals.call_count}</td>
                  <td className="py-2.5 hidden sm:table-cell"></td>
                  <td className="py-2.5 hidden sm:table-cell"></td>
                  <td className="py-2.5 text-right font-semibold text-[#3D4A44]">{totals.total_tokens.toLocaleString()}</td>
                  <td className="py-2.5 text-right font-semibold text-[#5B9A6E]">${(totals.total_cost_cents / 100).toFixed(2)}</td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      )}

      {aiUsage?.recent_calls && aiUsage.recent_calls.length > 0 && (
        <div className="bg-[#FAFBF9] rounded-xl shadow-sm p-6">
          <h3 className="font-semibold text-[#3D4A44] mb-4">Recent AI Calls</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[rgba(59,77,67,0.08)]">
                  <th className="text-left py-2 text-[#7A8580] font-medium">Feature</th>
                  <th className="text-right py-2 text-[#7A8580] font-medium">Tokens</th>
                  <th className="text-right py-2 text-[#7A8580] font-medium">Cost</th>
                  <th className="text-right py-2 text-[#7A8580] font-medium">Time</th>
                </tr>
              </thead>
              <tbody>
                {aiUsage.recent_calls.slice(0, 10).map((call) => (
                  <tr key={call.id} className="border-b border-[rgba(59,77,67,0.04)]">
                    <td className="py-2 text-[#3D4A44]">{FEATURE_LABELS[call.feature] || call.feature}</td>
                    <td className="py-2 text-right text-[#7A8580]">{call.total_tokens.toLocaleString()}</td>
                    <td className="py-2 text-right text-[#5B9A6E]">${(call.estimated_cost_cents / 100).toFixed(3)}</td>
                    <td className="py-2 text-right text-[#7A8580] text-xs">
                      {call.created_at ? new Date(call.created_at).toLocaleString() : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div>
        <h3 className="text-lg font-semibold text-[#3D4A44] mb-4">Service Cost Breakdown</h3>
        <div className="space-y-6">
          {INFRASTRUCTURE_SERVICES.map((cat) => {
            const CatIcon = cat.icon
            return (
              <div key={cat.category}>
                <div className="flex items-center gap-2 mb-3">
                  <div className="p-1.5 rounded-lg" style={{ backgroundColor: `${cat.color}20` }}>
                    <CatIcon className="w-5 h-5" style={{ color: cat.color }} />
                  </div>
                  <h4 className="font-semibold text-[#3D4A44]">{cat.category}</h4>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {cat.services.map((svc) => (
                    <div key={svc.name} className="bg-[#FAFBF9] rounded-xl shadow-sm p-5">
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <h5 className="font-semibold text-[#3D4A44] text-sm">{svc.name}</h5>
                          <p className="text-xs text-[#7A8580] mt-0.5">{svc.tier}</p>
                        </div>
                        <span className="px-2 py-1 bg-[#5B9A6E]/10 text-[#5B9A6E] text-xs font-medium rounded-full">
                          {svc.baseCost}
                        </span>
                      </div>
                      <p className="text-xs text-[#7A8580] mb-3">{svc.notes}</p>
                      <div className="flex flex-wrap gap-1.5 mb-3">
                        {svc.features.map((f) => (
                          <span key={f} className="px-2 py-0.5 bg-[#EEF1EC] text-[#3D4A44] text-[10px] rounded-md">{f}</span>
                        ))}
                      </div>
                      <div className="border-t border-[rgba(59,77,67,0.06)] pt-3">
                        <p className="text-[10px] text-[#7A8580] uppercase tracking-wider mb-1.5">Scaling Projections</p>
                        <div className="grid grid-cols-3 gap-2 text-center">
                          {Object.entries(svc.scaling).map(([tier, cost]) => (
                            <div key={tier}>
                              <p className="text-[10px] text-[#7A8580]">{Number(tier).toLocaleString()} orgs</p>
                              <p className="text-xs font-medium text-[#3D4A44]">{cost}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      <div className="bg-[#5A8A9A]/10 rounded-xl p-6">
        <h3 className="font-semibold text-[#3D4A44] mb-2">Cost Summary</h3>
        <p className="text-sm text-[#7A8580]">
          Cadence's fixed monthly costs include Cloud Hosting (~$25/mo), Spotify Premium (~$10.99/mo), and Google Workspace ($7/mo).
          The primary variable cost is OpenAI API usage, which scales with catalog processing activity. At current usage levels,
          total monthly infrastructure cost is estimated around $44-50/mo. YouTube, Last.fm, Dropbox, and Web Push
          remain free regardless of scale.
        </p>
      </div>
    </div>
  )
}

function AdminResetPasswordModal({ user, onClose, onSuccess }) {
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(false)

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
      await axios.put(`/api/admin/users/${user.id}`, { password: newPassword })
      setSuccess(true)
      setTimeout(() => onSuccess(), 1500)
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
            <p className="text-sm text-[#7A8580]">User: {user.username} ({user.email})</p>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-[#EEF1EC] rounded-lg">
            <XMarkIcon className="w-5 h-5 text-[#7A8580]" />
          </button>
        </div>

        {error && <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">{error}</div>}
        {success && <div className="mb-4 p-3 bg-green-50 text-green-700 rounded-lg text-sm">Password reset successfully!</div>}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-[#3D4A44] mb-1">New Password</label>
            <input
              type="password" required value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full px-3 py-2 border border-[#D1D5CE] rounded-lg text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
              placeholder="Min 6 characters"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-[#3D4A44] mb-1">Confirm Password</label>
            <input
              type="password" required value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full px-3 py-2 border border-[#D1D5CE] rounded-lg text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
            />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-[#7A8580] hover:bg-[#EEF1EC] rounded-lg">Cancel</button>
            <button type="submit" disabled={saving || success} className="px-4 py-2 text-sm bg-amber-500 text-white rounded-lg hover:bg-amber-600 disabled:opacity-50">
              {saving ? 'Resetting...' : success ? 'Done!' : 'Reset Password'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function LeadsTab() {
  const [leads, setLeads] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')
  const [expandedLeadId, setExpandedLeadId] = useState(null)

  useEffect(() => {
    loadLeads()
  }, [filter])

  const loadLeads = async () => {
    setLoading(true)
    try {
      const params = {}
      if (filter !== 'all') params.lead_type = filter
      const res = await axios.get('/api/admin/leads', { params })
      setLeads(res.data.leads || [])
    } catch (err) {
      console.error('Failed to load leads:', err)
    } finally {
      setLoading(false)
    }
  }

  const waitlistCount = leads.filter(l => l.lead_type === 'WAITLIST').length
  const demoCount = leads.filter(l => l.lead_type === 'DEMO_REQUEST').length
  const investorCount = leads.filter(l => l.lead_type === 'INVESTOR_INQUIRY').length
  const applicationCount = leads.filter(l => l.lead_type === 'INTERN_APPLICATION').length

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-[#3D4A44]">Waitlist & Leads</h2>
          <p className="text-sm text-[#7A8580]">
            {filter === 'all' ? leads.length : leads.length} total
            {filter === 'all' && ` (${waitlistCount} waitlist, ${demoCount} demo, ${investorCount} investor, ${applicationCount} applications)`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {['all', 'WAITLIST', 'DEMO_REQUEST', 'INVESTOR_INQUIRY', 'INTERN_APPLICATION'].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                filter === f
                  ? 'bg-[#5B8A72] text-white'
                  : 'bg-[#EEF1EC] text-[#7A8580] hover:text-[#3D4A44]'
              }`}
            >
              {f === 'all' ? 'All' : f === 'WAITLIST' ? 'Waitlist' : f === 'DEMO_REQUEST' ? 'Demo Requests' : f === 'INVESTOR_INQUIRY' ? 'Investors' : 'Applications'}
            </button>
          ))}
          <button
            onClick={loadLeads}
            className="p-1.5 text-[#7A8580] hover:text-[#3D4A44] hover:bg-[#EEF1EC] rounded-lg"
          >
            <ArrowPathIcon className="w-4 h-4" />
          </button>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12 text-[#7A8580]">Loading leads...</div>
      ) : leads.length === 0 ? (
        <div className="text-center py-12">
          <EnvelopeIcon className="w-12 h-12 text-[#B0B8B3] mx-auto mb-3" />
          <p className="text-[#7A8580]">No leads yet</p>
        </div>
      ) : (
        <div className="bg-[#FAFBF9] rounded-xl shadow-sm overflow-x-auto">
          <table className="w-full min-w-[600px]">
            <thead className="bg-[#EEF1EC]">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-[#3D4A44] uppercase">Type</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-[#3D4A44] uppercase">Email</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-[#3D4A44] uppercase">Name</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-[#3D4A44] uppercase">Company / Role</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-[#3D4A44] uppercase">Details</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-[#3D4A44] uppercase">Date</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-[#3D4A44] uppercase">Resume</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[rgba(59,77,67,0.08)]">
              {leads.map(lead => {
                const isExpanded = expandedLeadId === lead.id;
                const detailLines = (lead.message || '').split('\n').filter(l => l.trim());
                return (
                <React.Fragment key={lead.id}>
                <tr
                  className={`cursor-pointer transition-colors ${isExpanded ? 'bg-[#EEF1EC]' : 'hover:bg-[#EEF1EC]'}`}
                  onClick={() => setExpandedLeadId(isExpanded ? null : lead.id)}
                >
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      lead.lead_type === 'WAITLIST'
                        ? 'bg-[rgba(91,138,114,0.12)] text-[#5B8A72]'
                        : lead.lead_type === 'INVESTOR_INQUIRY'
                        ? 'bg-[rgba(196,149,107,0.12)] text-[#C4956B]'
                        : lead.lead_type === 'INTERN_APPLICATION'
                        ? 'bg-[rgba(139,92,246,0.12)] text-[#8B5CF6]'
                        : 'bg-[rgba(90,138,154,0.12)] text-[#5A8A9A]'
                    }`}>
                      {lead.lead_type === 'WAITLIST' ? 'Waitlist' : lead.lead_type === 'INVESTOR_INQUIRY' ? 'Investor' : lead.lead_type === 'INTERN_APPLICATION' ? 'Application' : 'Demo'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-[#3D4A44] font-medium">{lead.email}</td>
                  <td className="px-6 py-4 text-sm text-[#7A8580]">{lead.name || '-'}</td>
                  <td className="px-6 py-4 text-sm text-[#7A8580]">{lead.company || '-'}</td>
                  <td className="px-6 py-4 text-sm text-[#7A8580] max-w-[200px] truncate" title={lead.message || ''}>{lead.message ? lead.message.substring(0, 80) + (lead.message.length > 80 ? '...' : '') : '-'}</td>
                  <td className="px-6 py-4 text-sm text-[#7A8580]">
                    {lead.created_at ? new Date(lead.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : '-'}
                  </td>
                  <td className="px-6 py-4 text-sm">
                    {lead.resume_path ? (
                      <button
                        onClick={async (e) => {
                          e.stopPropagation();
                          try {
                            const token = localStorage.getItem('token');
                            const res = await fetch(`/api/admin/leads/${lead.id}/resume`, {
                              headers: { 'Authorization': `Bearer ${token}` }
                            });
                            if (!res.ok) throw new Error('Download failed');
                            const blob = await res.blob();
                            const url = window.URL.createObjectURL(blob);
                            const a = document.createElement('a');
                            a.href = url;
                            const disposition = res.headers.get('content-disposition');
                            const filename = disposition ? disposition.split('filename=')[1]?.replace(/"/g, '') : 'resume.pdf';
                            a.download = filename;
                            document.body.appendChild(a);
                            a.click();
                            a.remove();
                            window.URL.revokeObjectURL(url);
                          } catch (err) {
                            console.error('Resume download failed:', err);
                            alert('Resume file is no longer available. It may have been lost during a deployment. New submissions will be preserved.');
                          }
                        }}
                        className="inline-flex items-center gap-1 px-2 py-1 bg-[rgba(91,138,114,0.1)] text-[#5B8A72] rounded text-xs font-medium hover:bg-[rgba(91,138,114,0.2)] transition-colors cursor-pointer"
                      >
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m.75 12l3 3m0 0l3-3m-3 3v-6m-1.5-9H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                        </svg>
                        Resume
                      </button>
                    ) : lead.lead_type === 'INTERN_APPLICATION' ? (
                      <span className="text-[#B0B8B3] text-xs">No resume</span>
                    ) : null}
                  </td>
                </tr>
                {isExpanded && (
                  <tr>
                    <td colSpan={7} className="px-0 py-0">
                      <div className="bg-white border-t border-b border-[rgba(59,77,67,0.1)] px-8 py-5">
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                          <div>
                            <p className="text-[11px] font-medium text-[#7A8580] uppercase tracking-wide mb-1">Name</p>
                            <p className="text-[14px] text-[#3D4A44] font-medium">{lead.name || 'N/A'}</p>
                          </div>
                          <div>
                            <p className="text-[11px] font-medium text-[#7A8580] uppercase tracking-wide mb-1">Email</p>
                            <p className="text-[14px] text-[#3D4A44]">
                              <a href={`mailto:${lead.email}`} className="text-[#5B8A72] hover:underline">{lead.email}</a>
                            </p>
                          </div>
                          <div>
                            <p className="text-[11px] font-medium text-[#7A8580] uppercase tracking-wide mb-1">
                              {lead.lead_type === 'INTERN_APPLICATION' ? 'Role Applied For' : 'Company'}
                            </p>
                            <p className="text-[14px] text-[#3D4A44]">{lead.company || 'N/A'}</p>
                          </div>
                          <div>
                            <p className="text-[11px] font-medium text-[#7A8580] uppercase tracking-wide mb-1">Type</p>
                            <p className="text-[14px] text-[#3D4A44]">
                              {lead.lead_type === 'WAITLIST' ? 'Waitlist Signup' : lead.lead_type === 'INVESTOR_INQUIRY' ? 'Investor Inquiry' : lead.lead_type === 'INTERN_APPLICATION' ? 'Intern Application' : 'Demo Request'}
                            </p>
                          </div>
                          <div>
                            <p className="text-[11px] font-medium text-[#7A8580] uppercase tracking-wide mb-1">Submitted</p>
                            <p className="text-[14px] text-[#3D4A44]">
                              {lead.created_at ? new Date(lead.created_at).toLocaleDateString('en-US', { weekday: 'short', month: 'long', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : 'N/A'}
                            </p>
                          </div>
                          <div>
                            <p className="text-[11px] font-medium text-[#7A8580] uppercase tracking-wide mb-1">Resume</p>
                            {lead.resume_path ? (
                              <button
                                onClick={async (e) => {
                                  e.stopPropagation();
                                  try {
                                    const token = localStorage.getItem('token');
                                    const res = await fetch(`/api/admin/leads/${lead.id}/resume`, {
                                      headers: { 'Authorization': `Bearer ${token}` }
                                    });
                                    if (!res.ok) throw new Error('Download failed');
                                    const blob = await res.blob();
                                    const url = window.URL.createObjectURL(blob);
                                    const a = document.createElement('a');
                                    a.href = url;
                                    const disposition = res.headers.get('content-disposition');
                                    const filename = disposition ? disposition.split('filename=')[1]?.replace(/"/g, '') : 'resume.pdf';
                                    a.download = filename;
                                    document.body.appendChild(a);
                                    a.click();
                                    a.remove();
                                    window.URL.revokeObjectURL(url);
                                  } catch (err) {
                                    console.error('Resume download failed:', err);
                                    alert('Resume file is no longer available. New submissions will be preserved.');
                                  }
                                }}
                                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[#5B8A72] text-white rounded-lg text-xs font-medium hover:bg-[#4A7862] transition-colors cursor-pointer"
                              >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m.75 12l3 3m0 0l3-3m-3 3v-6m-1.5-9H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                                </svg>
                                Download Resume
                              </button>
                            ) : (
                              <p className="text-[14px] text-[#B0B8B3]">No resume attached</p>
                            )}
                          </div>
                        </div>
                        {detailLines.length > 0 && (
                          <div className="mt-4 pt-4 border-t border-[rgba(59,77,67,0.08)]">
                            <p className="text-[11px] font-medium text-[#7A8580] uppercase tracking-wide mb-2">Application Details</p>
                            <div className="space-y-2">
                              {detailLines.map((line, i) => {
                                const colonIdx = line.indexOf(':');
                                if (colonIdx > 0 && colonIdx < 30) {
                                  const label = line.substring(0, colonIdx).trim();
                                  const value = line.substring(colonIdx + 1).trim();
                                  return (
                                    <div key={i}>
                                      <span className="text-[12px] font-medium text-[#7A8580]">{label}:</span>
                                      <span className="text-[13px] text-[#3D4A44] ml-1.5">{value}</span>
                                    </div>
                                  );
                                }
                                return <p key={i} className="text-[13px] text-[#3D4A44]">{line}</p>;
                              })}
                            </div>
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                )}
                </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
