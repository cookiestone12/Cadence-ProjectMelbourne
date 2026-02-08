import React, { useState, useEffect } from 'react'
import axios from 'axios'
import {
  PlusIcon,
  CheckIcon,
  TrashIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  CalendarIcon,
  FlagIcon,
  XMarkIcon,
  SparklesIcon,
  ArrowPathIcon,
  FunnelIcon,
  ArrowsUpDownIcon
} from '@heroicons/react/24/outline'
import { ExclamationCircleIcon } from '@heroicons/react/24/solid'

const PRIORITY_OPTIONS = [
  { value: 1, label: 'High', color: '#C47068', bgColor: 'rgba(196, 112, 104, 0.15)' },
  { value: 2, label: 'Medium', color: '#C4956B', bgColor: 'rgba(196, 149, 107, 0.15)' },
  { value: 3, label: 'Low', color: '#5B9A6E', bgColor: 'rgba(91, 154, 110, 0.15)' }
]

const ACTION_TYPES = [
  'MISSING_ISRC',
  'MISSING_ISWC',
  'CONTRACT_PENDING',
  'PRO_INCOMPLETE',
  'DSP_REGISTRATION',
  'CUSTOM_DEADLINE',
  'GENERAL'
]

const formatActionType = (type) => {
  const labels = {
    'MISSING_ISRC': 'Missing ISRC',
    'MISSING_ISWC': 'Missing ISWC',
    'CONTRACT_PENDING': 'Contract Pending',
    'PRO_INCOMPLETE': 'PRO Incomplete',
    'DSP_REGISTRATION': 'DSP Registration',
    'CUSTOM_DEADLINE': 'Custom Deadline',
    'GENERAL': 'General'
  }
  return labels[type] || type
}

const getPriorityStyle = (priority) => {
  const opt = PRIORITY_OPTIONS.find(p => p.value === priority)
  return opt || PRIORITY_OPTIONS[1]
}

const formatDate = (dateStr) => {
  if (!dateStr) return 'No deadline'
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

export default function ActionItemsPage() {
  const [orgId, setOrgId] = useState(null)
  const [actions, setActions] = useState([])
  const [creators, setCreators] = useState([])
  const [songs, setSongs] = useState([])
  const [summary, setSummary] = useState({ total_pending: 0, overdue: 0, due_this_week: 0, high_priority: 0 })
  const [loading, setLoading] = useState(true)
  const [showAddForm, setShowAddForm] = useState(false)
  const [filterStatus, setFilterStatus] = useState('')
  const [filterPriority, setFilterPriority] = useState('')
  const [filterCreator, setFilterCreator] = useState('')
  const [filterType, setFilterType] = useState('')
  const [sortBy, setSortBy] = useState('priority')
  const [generating, setGenerating] = useState(false)
  const [saving, setSaving] = useState(false)
  const [newAction, setNewAction] = useState({
    action_type: 'GENERAL',
    title: '',
    description: '',
    priority: 2,
    deadline: '',
    reminder_days_before: 3,
    creator_id: '',
    song_id: ''
  })

  useEffect(() => {
    loadInitialData()
  }, [])

  const loadInitialData = async () => {
    try {
      const orgResponse = await axios.get('/api/organizations/current')
      const id = orgResponse.data.id
      setOrgId(id)

      const [creatorsRes, songsRes] = await Promise.all([
        axios.get(`/api/creators/org/${id}`),
        axios.get(`/api/songs/org/${id}?limit=1000`)
      ])

      setCreators(creatorsRes.data)
      setSongs(Array.isArray(songsRes.data) ? songsRes.data : [])

      await Promise.all([
        loadActions(id),
        loadSummary(id)
      ])
    } catch (error) {
      console.error('Failed to load data:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadActions = async (id) => {
    const oid = id || orgId
    if (!oid) return
    try {
      const params = new URLSearchParams()
      if (filterStatus) params.append('status', filterStatus)
      if (filterCreator) params.append('creator_id', filterCreator)
      if (filterPriority) params.append('priority', filterPriority)
      const response = await axios.get(`/api/actions/org/${oid}?${params.toString()}`)
      setActions(response.data)
    } catch (error) {
      console.error('Failed to load actions:', error)
    }
  }

  const loadSummary = async (id) => {
    const oid = id || orgId
    if (!oid) return
    try {
      const response = await axios.get(`/api/actions/summary/org/${oid}`)
      setSummary(response.data)
    } catch (error) {
      console.error('Failed to load summary:', error)
    }
  }

  useEffect(() => {
    if (orgId) {
      loadActions()
    }
  }, [filterStatus, filterCreator, filterPriority])

  const handleAddAction = async () => {
    if (!newAction.title.trim()) return
    setSaving(true)
    try {
      await axios.post(`/api/actions/org/${orgId}`, {
        ...newAction,
        creator_id: newAction.creator_id ? parseInt(newAction.creator_id) : null,
        song_id: newAction.song_id ? parseInt(newAction.song_id) : null,
        deadline: newAction.deadline || null
      })
      setShowAddForm(false)
      setNewAction({
        action_type: 'GENERAL',
        title: '',
        description: '',
        priority: 2,
        deadline: '',
        reminder_days_before: 3,
        creator_id: '',
        song_id: ''
      })
      await Promise.all([loadActions(), loadSummary()])
    } catch (error) {
      console.error('Failed to add action:', error)
    } finally {
      setSaving(false)
    }
  }

  const handleCompleteAction = async (actionId) => {
    try {
      await axios.post(`/api/actions/${actionId}/complete`)
      await Promise.all([loadActions(), loadSummary()])
    } catch (error) {
      console.error('Failed to complete action:', error)
    }
  }

  const handleDeleteAction = async (actionId) => {
    try {
      await axios.delete(`/api/actions/${actionId}`)
      await Promise.all([loadActions(), loadSummary()])
    } catch (error) {
      console.error('Failed to delete action:', error)
    }
  }

  const handleGenerateActions = async () => {
    setGenerating(true)
    try {
      await axios.post(`/api/actions/generate-org/${orgId}`)
      await Promise.all([loadActions(), loadSummary()])
    } catch (error) {
      console.error('Failed to generate actions:', error)
    } finally {
      setGenerating(false)
    }
  }

  const filteredActions = actions.filter(action => {
    if (filterType && action.action_type !== filterType) return false
    return true
  })

  const sortedActions = [...filteredActions].sort((a, b) => {
    switch (sortBy) {
      case 'priority':
        return a.priority - b.priority
      case 'deadline':
        if (!a.deadline && !b.deadline) return 0
        if (!a.deadline) return 1
        if (!b.deadline) return -1
        return new Date(a.deadline) - new Date(b.deadline)
      case 'created':
        return new Date(b.created_at) - new Date(a.created_at)
      case 'creator':
        return (a.creator_name || '').localeCompare(b.creator_name || '')
      default:
        return 0
    }
  })

  const hasActiveFilters = filterStatus || filterPriority || filterCreator || filterType

  const clearFilters = () => {
    setFilterStatus('')
    setFilterPriority('')
    setFilterCreator('')
    setFilterType('')
  }

  const uniqueTypes = [...new Set(actions.map(a => a.action_type))]

  if (loading) {
    return (
      <div className="min-h-screen bg-[#F5F7F4] flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-[#5B8A72] border-t-transparent"></div>
          <p className="mt-4 text-[#7A8580]">Loading action items...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#F5F7F4] p-6 lg:p-8">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-[34px] font-semibold text-[#3D4A44] leading-tight">Action Items</h1>
            <p className="text-[17px] text-[#7A8580] mt-1">Organization-wide action items and tasks</p>
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={handleGenerateActions}
              disabled={generating}
              className="inline-flex items-center space-x-2 px-4 py-2.5 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-xl hover:from-[#4A7862] hover:to-[#6A9484] transition-all disabled:opacity-50 shadow-sm"
            >
              {generating ? (
                <ArrowPathIcon className="w-5 h-5 animate-spin" />
              ) : (
                <SparklesIcon className="w-5 h-5" />
              )}
              <span>{generating ? 'Scanning...' : 'Auto-Generate'}</span>
            </button>
            <button
              onClick={() => setShowAddForm(true)}
              className="inline-flex items-center space-x-2 px-4 py-2.5 bg-[#5B8A72] text-white rounded-xl hover:bg-[#4A7862] transition-colors shadow-sm"
            >
              <PlusIcon className="w-5 h-5" />
              <span>Add Action</span>
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
          <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6 relative overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-[#5B8A72] to-[#7BA594]"></div>
            <div className="flex items-center space-x-3">
              <div className="p-2 rounded-lg" style={{ backgroundColor: 'rgba(91, 138, 114, 0.15)' }}>
                <ClockIcon className="w-5 h-5 text-[#5B8A72]" />
              </div>
              <div>
                <p className="text-[13px] text-[#7A8580]">Total Pending</p>
                <p className="text-[40px] font-semibold text-[#3D4A44] leading-tight">{summary.total_pending}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6 relative overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-[#C47068] to-[#D4908A]"></div>
            <div className="flex items-center space-x-3">
              <div className="p-2 rounded-lg" style={{ backgroundColor: 'rgba(196, 112, 104, 0.15)' }}>
                <ExclamationTriangleIcon className="w-5 h-5 text-[#C47068]" />
              </div>
              <div>
                <p className="text-[13px] text-[#7A8580]">Overdue</p>
                <p className="text-[40px] font-semibold text-[#C47068] leading-tight">{summary.overdue}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6 relative overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-[#C4956B] to-[#D4B59B]"></div>
            <div className="flex items-center space-x-3">
              <div className="p-2 rounded-lg" style={{ backgroundColor: 'rgba(196, 149, 107, 0.15)' }}>
                <CalendarIcon className="w-5 h-5 text-[#C4956B]" />
              </div>
              <div>
                <p className="text-[13px] text-[#7A8580]">Due This Week</p>
                <p className="text-[40px] font-semibold text-[#C4956B] leading-tight">{summary.due_this_week}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6 relative overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-[#C47068] to-[#C4956B]"></div>
            <div className="flex items-center space-x-3">
              <div className="p-2 rounded-lg" style={{ backgroundColor: 'rgba(196, 112, 104, 0.15)' }}>
                <FlagIcon className="w-5 h-5 text-[#C47068]" />
              </div>
              <div>
                <p className="text-[13px] text-[#7A8580]">High Priority</p>
                <p className="text-[40px] font-semibold text-[#3D4A44] leading-tight">{summary.high_priority}</p>
              </div>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3 bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-4 mb-6">
          <div className="flex items-center space-x-2 text-[#7A8580]">
            <FunnelIcon className="w-4 h-4" />
            <span className="text-sm font-medium">Filter:</span>
          </div>

          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="text-sm px-3 py-1.5 border border-[rgba(59,77,67,0.2)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
          >
            <option value="">All Statuses</option>
            <option value="PENDING">Pending</option>
            <option value="IN_PROGRESS">In Progress</option>
            <option value="COMPLETED">Completed</option>
          </select>

          <select
            value={filterPriority}
            onChange={(e) => setFilterPriority(e.target.value)}
            className="text-sm px-3 py-1.5 border border-[rgba(59,77,67,0.2)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
          >
            <option value="">All Priorities</option>
            {PRIORITY_OPTIONS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>

          <select
            value={filterCreator}
            onChange={(e) => setFilterCreator(e.target.value)}
            className="text-sm px-3 py-1.5 border border-[rgba(59,77,67,0.2)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44] max-w-[200px]"
          >
            <option value="">All Creators</option>
            {creators.map(c => (
              <option key={c.id} value={c.id}>{c.display_name}</option>
            ))}
          </select>

          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="text-sm px-3 py-1.5 border border-[rgba(59,77,67,0.2)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
          >
            <option value="">All Types</option>
            {uniqueTypes.map(type => (
              <option key={type} value={type}>{formatActionType(type)}</option>
            ))}
          </select>

          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="text-sm px-3 py-1.5 text-[#C47068] hover:bg-[rgba(196,112,104,0.1)] rounded-lg transition-colors"
            >
              Clear Filters
            </button>
          )}

          <div className="flex-1" />

          <div className="flex items-center space-x-2 text-[#7A8580]">
            <ArrowsUpDownIcon className="w-4 h-4" />
            <span className="text-sm font-medium">Sort:</span>
          </div>

          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="text-sm px-3 py-1.5 border border-[rgba(59,77,67,0.2)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
          >
            <option value="priority">Priority</option>
            <option value="deadline">Deadline</option>
            <option value="created">Recently Added</option>
            <option value="creator">Creator</option>
          </select>

          {hasActiveFilters && (
            <span className="text-sm text-[#7A8580]">
              Showing {sortedActions.length} of {actions.length}
            </span>
          )}
        </div>

        {showAddForm && (
          <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6 mb-6 border border-[#5B8A72]">
            <div className="flex items-center justify-between mb-4">
              <h4 className="text-lg font-semibold text-[#3D4A44]">New Action Item</h4>
              <button onClick={() => setShowAddForm(false)} className="text-[#7A8580] hover:text-[#3D4A44]">
                <XMarkIcon className="w-5 h-5" />
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Title *</label>
                <input
                  type="text"
                  value={newAction.title}
                  onChange={(e) => setNewAction({ ...newAction, title: e.target.value })}
                  placeholder="e.g., Submit ISRC registration"
                  className="w-full px-3 py-2 border border-[rgba(59,77,67,0.2)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Type</label>
                <select
                  value={newAction.action_type}
                  onChange={(e) => setNewAction({ ...newAction, action_type: e.target.value })}
                  className="w-full px-3 py-2 border border-[rgba(59,77,67,0.2)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                >
                  {ACTION_TYPES.map(type => (
                    <option key={type} value={type}>{formatActionType(type)}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Priority</label>
                <select
                  value={newAction.priority}
                  onChange={(e) => setNewAction({ ...newAction, priority: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 border border-[rgba(59,77,67,0.2)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                >
                  {PRIORITY_OPTIONS.map(opt => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Deadline</label>
                <input
                  type="date"
                  value={newAction.deadline}
                  onChange={(e) => setNewAction({ ...newAction, deadline: e.target.value })}
                  className="w-full px-3 py-2 border border-[rgba(59,77,67,0.2)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Remind Days Before</label>
                <input
                  type="number"
                  min="0"
                  value={newAction.reminder_days_before}
                  onChange={(e) => setNewAction({ ...newAction, reminder_days_before: parseInt(e.target.value) || 0 })}
                  className="w-full px-3 py-2 border border-[rgba(59,77,67,0.2)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Creator (optional)</label>
                <select
                  value={newAction.creator_id}
                  onChange={(e) => setNewAction({ ...newAction, creator_id: e.target.value })}
                  className="w-full px-3 py-2 border border-[rgba(59,77,67,0.2)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                >
                  <option value="">None</option>
                  {creators.map(c => (
                    <option key={c.id} value={c.id}>{c.display_name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Song (optional)</label>
                <select
                  value={newAction.song_id}
                  onChange={(e) => setNewAction({ ...newAction, song_id: e.target.value })}
                  className="w-full px-3 py-2 border border-[rgba(59,77,67,0.2)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                >
                  <option value="">None</option>
                  {songs.map(s => (
                    <option key={s.id} value={s.id}>{s.title}</option>
                  ))}
                </select>
              </div>

              <div className="md:col-span-2 lg:col-span-2">
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Description</label>
                <textarea
                  value={newAction.description}
                  onChange={(e) => setNewAction({ ...newAction, description: e.target.value })}
                  placeholder="Optional details..."
                  rows={2}
                  className="w-full px-3 py-2 border border-[rgba(59,77,67,0.2)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                />
              </div>
            </div>

            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setShowAddForm(false)}
                className="px-4 py-2 text-[#7A8580] hover:text-[#3D4A44] transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleAddAction}
                disabled={saving || !newAction.title.trim()}
                className="px-4 py-2 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7862] transition-colors disabled:opacity-50"
              >
                {saving ? 'Adding...' : 'Add Action'}
              </button>
            </div>
          </div>
        )}

        <div className="space-y-3">
          {sortedActions.length === 0 ? (
            <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-12 text-center">
              <ClockIcon className="w-12 h-12 text-[#7A8580] mx-auto mb-4" />
              {hasActiveFilters ? (
                <>
                  <p className="text-[#7A8580]">No actions match your filters</p>
                  <button onClick={clearFilters} className="text-sm text-[#5B8A72] hover:underline mt-2">
                    Clear filters
                  </button>
                </>
              ) : (
                <>
                  <p className="text-[#7A8580]">No action items yet</p>
                  <p className="text-sm text-[#7A8580] mt-1">Click "Add Action" or "Auto-Generate" to get started</p>
                </>
              )}
            </div>
          ) : (
            sortedActions.map((action) => {
              const priorityStyle = getPriorityStyle(action.priority)
              const isCompleted = action.status === 'COMPLETED'

              return (
                <div
                  key={action.id}
                  className={`bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-4 transition-all ${
                    action.is_overdue
                      ? 'border border-[#C47068]'
                      : isCompleted
                        ? 'opacity-60'
                        : ''
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-start space-x-4 flex-1">
                      <button
                        onClick={() => !isCompleted && handleCompleteAction(action.id)}
                        disabled={isCompleted}
                        className={`mt-1 p-1 rounded-full transition-colors ${
                          isCompleted
                            ? 'bg-[#5B9A6E] text-white cursor-default'
                            : 'border-2 border-[#7A8580] hover:border-[#5B8A72] hover:bg-[rgba(91,138,114,0.1)]'
                        }`}
                      >
                        <CheckIcon className={`w-4 h-4 ${isCompleted ? '' : 'text-transparent'}`} />
                      </button>

                      <div className="flex-1">
                        <div className="flex items-center space-x-2 mb-1">
                          <h4 className={`font-medium ${isCompleted ? 'line-through text-[#7A8580]' : 'text-[#3D4A44]'}`}>
                            {action.title}
                          </h4>
                          {action.is_overdue && (
                            <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-xs font-medium bg-[rgba(196,112,104,0.15)] text-[#C47068]">
                              <ExclamationCircleIcon className="w-3 h-3" />
                              <span>Overdue</span>
                            </span>
                          )}
                        </div>

                        {action.description && (
                          <p className="text-sm text-[#7A8580] mb-2">{action.description}</p>
                        )}

                        <div className="flex flex-wrap items-center gap-2 text-xs">
                          <span
                            className="inline-flex items-center px-2 py-1 rounded-full font-medium"
                            style={{ backgroundColor: priorityStyle.bgColor, color: priorityStyle.color }}
                          >
                            <FlagIcon className="w-3 h-3 mr-1" />
                            {priorityStyle.label}
                          </span>

                          <span className="inline-flex items-center px-2 py-1 rounded-full bg-[rgba(91,138,114,0.1)] text-[#5B8A72] font-medium">
                            {formatActionType(action.action_type)}
                          </span>

                          {action.creator_name && (
                            <span className="inline-flex items-center px-2 py-1 rounded-full bg-[#EEF1EC] text-[#3D4A44] font-medium">
                              {action.creator_name}
                            </span>
                          )}

                          {action.song_title && (
                            <span className="text-[#7A8580]">Song: {action.song_title}</span>
                          )}

                          <span className="inline-flex items-center text-[#7A8580]">
                            <CalendarIcon className="w-3 h-3 mr-1" />
                            {action.deadline ? (
                              <>
                                {formatDate(action.deadline)}
                                {action.days_until_deadline !== null && action.days_until_deadline >= 0 && !isCompleted && (
                                  <span className="ml-1 text-[#C4956B]">
                                    ({action.days_until_deadline === 0 ? 'Today' : `${action.days_until_deadline} days`})
                                  </span>
                                )}
                              </>
                            ) : (
                              'No deadline'
                            )}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center space-x-1 ml-4">
                      {!isCompleted && (
                        <button
                          onClick={() => handleCompleteAction(action.id)}
                          className="p-2 text-[#5B8A72] hover:bg-[rgba(91,138,114,0.1)] rounded-lg transition-colors"
                          title="Complete"
                        >
                          <CheckIcon className="w-4 h-4" />
                        </button>
                      )}
                      <button
                        onClick={() => handleDeleteAction(action.id)}
                        className="p-2 text-[#C47068] hover:bg-[rgba(196,112,104,0.1)] rounded-lg transition-colors"
                        title="Delete"
                      >
                        <TrashIcon className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              )
            })
          )}
        </div>
      </div>
    </div>
  )
}
