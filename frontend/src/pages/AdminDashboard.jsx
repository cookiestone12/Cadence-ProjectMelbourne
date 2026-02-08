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
  KeyIcon
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

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      setError(null)
      const [statsRes, usersRes, orgsRes, integrationsRes, platformRes] = await Promise.all([
        axios.get('/api/admin/stats'),
        axios.get('/api/admin/users'),
        axios.get('/api/admin/organizations'),
        axios.get('/api/admin/integrations'),
        axios.get('/api/analytics/admin/platform-stats').catch(() => ({ data: null }))
      ])
      setStats(statsRes.data)
      setUsers(usersRes.data)
      setOrganizations(orgsRes.data)
      setIntegrations(integrationsRes.data)
      if (platformRes.data) setPlatformStats(platformRes.data)
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

  const handleDeleteUser = async (userId) => {
    if (!confirm('Are you sure you want to delete this user?')) return
    try {
      await axios.delete(`/api/admin/users/${userId}`)
      setUsers(users.filter(u => u.id !== userId))
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to delete user')
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
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-[#3D4A44] mb-2">Admin Dashboard</h1>
        <p className="text-[#7A8580]">Manage users, organizations, and system settings</p>
      </div>

      <div className="mb-6 border-b border-[rgba(59,77,67,0.08)]">
        <div className="flex space-x-8">
          {['overview', 'users', 'organizations', 'api-config'].map((tab) => (
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

          <div className="bg-[#FAFBF9] rounded-xl shadow-sm overflow-hidden">
            <table className="w-full">
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
                    >
                      <PencilIcon className="w-5 h-5" />
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

function IntegrationModal({ integration, onClose, onSave }) {
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState(null)

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
