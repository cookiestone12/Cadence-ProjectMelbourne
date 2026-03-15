import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
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
  ArrowsUpDownIcon,
  MusicalNoteIcon,
  DocumentTextIcon,
  FolderIcon,
  CurrencyDollarIcon,
  FilmIcon,
  LinkIcon,
  BoltIcon,
  EnvelopeIcon,
  ArrowDownTrayIcon,
  UserIcon,
  ArrowUpIcon,
  ChevronDownIcon
} from '@heroicons/react/24/outline'
import { ExclamationCircleIcon } from '@heroicons/react/24/solid'
import useBodyScrollLock from '../hooks/useBodyScrollLock'

const PRIORITY_OPTIONS = [
  { value: 1, label: 'High', color: '#C47068', bgColor: 'rgba(196, 112, 104, 0.15)' },
  { value: 2, label: 'Medium', color: '#C4956B', bgColor: 'rgba(196, 149, 107, 0.15)' },
  { value: 3, label: 'Low', color: '#5B9A6E', bgColor: 'rgba(91, 154, 110, 0.15)' }
]

const ACTION_TYPES = [
  'GENERAL',
  'CUSTOM_DEADLINE',
  'SEND_BULK_REGISTRATION',
  'CLIENT_FOLLOWUP',
  'REMINDER',
  'MISSING_ISRC',
  'MISSING_ISWC',
  'CONTRACT_PENDING',
  'PRO_INCOMPLETE',
  'DSP_REGISTRATION',
  'CONTRACT_EXPIRING',
  'RELEASE_INCOMPLETE',
  'UNMATCHED_ROYALTIES',
  'PLACEMENT_FOLLOWUP',
  'PLACEMENT_NEEDS_CONTRACT'
]

const formatActionType = (type) => {
  const labels = {
    'GENERAL': 'General',
    'CUSTOM_DEADLINE': 'Custom Deadline',
    'SEND_BULK_REGISTRATION': 'Send Bulk Registration',
    'CLIENT_FOLLOWUP': 'Client Follow-up',
    'REMINDER': 'Reminder',
    'MISSING_ISRC': 'Missing ISRC',
    'MISSING_ISWC': 'Missing ISWC',
    'CONTRACT_PENDING': 'Contract Pending',
    'PRO_INCOMPLETE': 'PRO Incomplete',
    'DSP_REGISTRATION': 'DSP Registration',
    'CONTRACT_EXPIRING': 'Contract Expiring',
    'RELEASE_INCOMPLETE': 'Release Incomplete',
    'UNMATCHED_ROYALTIES': 'Unmatched Royalties',
    'PLACEMENT_FOLLOWUP': 'Placement Follow-up',
    'PLACEMENT_NEEDS_CONTRACT': 'Placement Needs Contract'
  }
  return labels[type] || type
}

const ENTITY_TYPE_PILLS = [
  { value: '', label: 'All' },
  { value: 'song', label: 'Songs' },
  { value: 'work', label: 'Works' },
  { value: 'release', label: 'Releases' },
  { value: 'contract', label: 'Contracts' },
  { value: 'placement', label: 'Placements' },
  { value: 'royalty', label: 'Royalty' }
]

const ENTITY_TYPE_OPTIONS = [
  { value: '', label: 'None' },
  { value: 'song', label: 'Song' },
  { value: 'work', label: 'Work' },
  { value: 'release', label: 'Release' },
  { value: 'contract', label: 'Contract' },
  { value: 'placement', label: 'Placement' },
  { value: 'royalty', label: 'Royalty' }
]

const getPriorityStyle = (priority) => {
  const opt = PRIORITY_OPTIONS.find(p => p.value === priority)
  return opt || PRIORITY_OPTIONS[1]
}

const formatDate = (dateStr) => {
  if (!dateStr) return 'No deadline'
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

const formatEntityType = (type) => {
  if (!type) return type
  return type.charAt(0).toUpperCase() + type.slice(1)
}

export default function ActionItemsPage() {
  const navigate = useNavigate()
  const [orgId, setOrgId] = useState(null)
  const [actions, setActions] = useState([])
  const [creators, setCreators] = useState([])
  const [members, setMembers] = useState([])
  const [songs, setSongs] = useState([])
  const [summary, setSummary] = useState({ total_pending: 0, overdue: 0, due_this_week: 0, high_priority: 0, by_entity_type: {}, by_action_type: {} })
  const [loading, setLoading] = useState(true)
  const [showAddForm, setShowAddForm] = useState(false)
  useBodyScrollLock(showAddForm)
  const [filterStatus, setFilterStatus] = useState('')
  const [filterPriority, setFilterPriority] = useState('')
  const [filterCreator, setFilterCreator] = useState('')
  const [filterType, setFilterType] = useState('')
  const [filterEntityType, setFilterEntityType] = useState('')
  const [sortBy, setSortBy] = useState('priority')
  const [generating, setGenerating] = useState(false)
  const [generatingCrossModule, setGeneratingCrossModule] = useState(false)
  const [saving, setSaving] = useState(false)
  const [feedback, setFeedback] = useState(null)
  const [pushingEmail, setPushingEmail] = useState(false)
  const [downloadingPdf, setDownloadingPdf] = useState(false)
  const [showEmailModal, setShowEmailModal] = useState(false)
  const [emailForm, setEmailForm] = useState({
    creator_id: '',
    send_to: 'me',
    custom_email: ''
  })
  const [newAction, setNewAction] = useState({
    action_type: 'GENERAL',
    title: '',
    description: '',
    priority: 2,
    deadline: '',
    reminder_days_before: 3,
    creator_id: '',
    song_id: '',
    entity_type: '',
    work_id: '',
    release_id: '',
    contract_id: '',
    placement_id: '',
    assigned_to_user_id: ''
  })
  const [showScrollTop, setShowScrollTop] = useState(false)
  const [filterAssignedTo, setFilterAssignedTo] = useState('')

  useEffect(() => {
    loadInitialData()
  }, [])

  useEffect(() => {
    const handleScroll = () => setShowScrollTop(window.scrollY > 400)
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  const loadInitialData = async () => {
    try {
      const orgResponse = await axios.get('/api/organizations/current')
      const id = orgResponse.data?.id
      if (!id) { setLoading(false); return }
      setOrgId(id)

      const [creatorsRes, songsRes, membersRes] = await Promise.all([
        axios.get(`/api/creators/org/${id}`),
        axios.get(`/api/songs/org/${id}?limit=1000`),
        axios.get(`/api/organizations/${id}/members`)
      ])

      setCreators(creatorsRes.data)
      setSongs(Array.isArray(songsRes.data) ? songsRes.data : [])
      setMembers(membersRes.data.members || membersRes.data || [])

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
      if (filterEntityType) params.append('entity_type', filterEntityType)
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
  }, [filterStatus, filterCreator, filterPriority, filterEntityType])

  const handleAddAction = async () => {
    if (!newAction.title.trim()) return
    setSaving(true)
    try {
      await axios.post(`/api/actions/org/${orgId}`, {
        ...newAction,
        creator_id: newAction.creator_id ? parseInt(newAction.creator_id) : null,
        song_id: newAction.song_id ? parseInt(newAction.song_id) : null,
        work_id: newAction.work_id ? parseInt(newAction.work_id) : null,
        release_id: newAction.release_id ? parseInt(newAction.release_id) : null,
        contract_id: newAction.contract_id ? parseInt(newAction.contract_id) : null,
        placement_id: newAction.placement_id ? parseInt(newAction.placement_id) : null,
        entity_type: newAction.entity_type || null,
        deadline: newAction.deadline || null,
        assigned_to_user_id: newAction.assigned_to_user_id ? parseInt(newAction.assigned_to_user_id) : null
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
        song_id: '',
        entity_type: '',
        work_id: '',
        release_id: '',
        contract_id: '',
        placement_id: '',
        assigned_to_user_id: ''
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

  const handleAssignAction = async (actionId, userId) => {
    try {
      await axios.put(`/api/actions/${actionId}`, {
        assigned_to_user_id: userId ? parseInt(userId) : null
      })
      await loadActions()
    } catch (error) {
      console.error('Failed to assign action:', error)
    }
  }

  const showFeedback = (msg, type = 'success') => {
    setFeedback({ msg, type })
    setTimeout(() => setFeedback(null), 4000)
  }

  const handleGenerateActions = async () => {
    setGenerating(true)
    try {
      const response = await axios.post(`/api/actions/generate-org/${orgId}`)
      await Promise.all([loadActions(), loadSummary()])
      const count = response.data?.created_count || 0
      if (count > 0) {
        showFeedback(`Generated ${count} action items from catalog gaps`)
      } else {
        showFeedback('No new catalog gaps found — your catalog looks good!', 'info')
      }
    } catch (error) {
      console.error('Failed to generate actions:', error)
      showFeedback('Failed to generate actions. Please try again.', 'error')
    } finally {
      setGenerating(false)
    }
  }

  const handleGenerateCrossModule = async () => {
    setGeneratingCrossModule(true)
    try {
      const response = await axios.post(`/api/actions/generate-cross-module/${orgId}`)
      await Promise.all([loadActions(), loadSummary()])
      const count = response.data?.created_count || 0
      if (count > 0) {
        showFeedback(`Generated ${count} cross-module tasks`)
      } else {
        showFeedback('No new cross-module tasks found — everything is up to date!', 'info')
      }
    } catch (error) {
      console.error('Failed to generate cross-module actions:', error)
      showFeedback('Failed to scan modules. Please try again.', 'error')
    } finally {
      setGeneratingCrossModule(false)
    }
  }

  const filteredActions = actions.filter(action => {
    if (filterType && action.action_type !== filterType) return false
    if (filterAssignedTo && String(action.assigned_to_user_id) !== filterAssignedTo) return false
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

  const hasActiveFilters = filterStatus || filterPriority || filterCreator || filterType || filterEntityType || filterAssignedTo

  const clearFilters = () => {
    setFilterStatus('')
    setFilterPriority('')
    setFilterCreator('')
    setFilterType('')
    setFilterEntityType('')
    setFilterAssignedTo('')
  }

  const uniqueTypes = [...new Set(actions.map(a => a.action_type))]

  const openEmailModal = () => {
    setEmailForm({
      creator_id: filterCreator || '',
      send_to: 'me',
      custom_email: ''
    })
    setShowEmailModal(true)
  }

  const handleSendEmail = async () => {
    if (!emailForm.creator_id) {
      setFeedback({ type: 'error', msg: 'Please select a creator' })
      setTimeout(() => setFeedback(null), 4000)
      return
    }
    if (emailForm.send_to === 'custom' && !emailForm.custom_email) {
      setFeedback({ type: 'error', msg: 'Please enter an email address' })
      setTimeout(() => setFeedback(null), 4000)
      return
    }
    setPushingEmail(true)
    try {
      const response = await axios.post('/api/notifications/push-email', {
        creator_id: parseInt(emailForm.creator_id),
        send_to: emailForm.send_to,
        custom_email: emailForm.send_to === 'custom' ? emailForm.custom_email : undefined
      })
      setFeedback({ type: 'success', msg: response.data.message })
      setShowEmailModal(false)
      setTimeout(() => setFeedback(null), 4000)
    } catch (error) {
      setFeedback({ type: 'error', msg: error.response?.data?.detail || 'Failed to send email' })
      setTimeout(() => setFeedback(null), 4000)
    } finally {
      setPushingEmail(false)
    }
  }

  const handleDownloadPdf = async () => {
    setDownloadingPdf(true)
    try {
      const params = filterCreator ? `?creator_id=${filterCreator}` : ''
      const response = await axios.get(`/api/notifications/digest-pdf${params}`, { responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([response.data], { type: 'text/html' }))
      const link = document.createElement('a')
      link.href = url
      const creatorName = filterCreator ? creators.find(c => c.id === parseInt(filterCreator))?.display_name?.replace(/\s+/g, '-').toLowerCase() : null
      link.download = creatorName ? `cadence-action-items-${creatorName}.html` : 'cadence-action-items.html'
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
      setFeedback({ type: 'success', msg: 'Report downloaded — open the file and use Print > Save as PDF' })
      setTimeout(() => setFeedback(null), 5000)
    } catch (error) {
      setFeedback({ type: 'error', msg: 'Failed to download report' })
      setTimeout(() => setFeedback(null), 4000)
    } finally {
      setDownloadingPdf(false)
    }
  }

  const getEntityLink = (action) => {
    const links = []
    if (action.song_id && action.song_title) {
      links.push({ label: `Song: ${action.song_title}`, path: '/catalog', icon: MusicalNoteIcon })
    }
    if (action.work_id && action.work_title) {
      links.push({ label: `Work: ${action.work_title}`, path: '/works', icon: DocumentTextIcon })
    }
    if (action.release_id && action.release_title) {
      links.push({ label: `Release: ${action.release_title}`, path: '/releases', icon: FolderIcon })
    }
    if (action.contract_id && action.contract_title) {
      links.push({ label: `Contract: ${action.contract_title}`, path: '/contracts', icon: DocumentTextIcon })
    }
    if (action.placement_id && action.placement_title) {
      links.push({ label: `Placement: ${action.placement_title}`, path: '/placements', icon: FilmIcon })
    }
    return links
  }

  const byEntityType = summary.by_entity_type || {}
  const byActionType = summary.by_action_type || {}

  if (loading) {
    return (
      <div className="min-h-screen bg-[#F5F7F4] flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-[#5B8A72] border-t-transparent"></div>
          <p className="mt-4 text-[#7A8580]">Loading task inbox...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#F5F7F4] p-6 lg:p-8">
      {feedback && (
        <div className={`fixed top-4 right-4 z-50 px-5 py-3 rounded-xl shadow-lg text-sm font-medium transition-all animate-fade-in ${
          feedback.type === 'error' ? 'bg-[#C47068] text-white' :
          feedback.type === 'info' ? 'bg-[#5A8A9A] text-white' :
          'bg-[#5B9A6E] text-white'
        }`}>
          {feedback.msg}
        </div>
      )}
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-[34px] font-semibold text-[#3D4A44] leading-tight">Task Inbox</h1>
            <p className="text-[17px] text-[#7A8580] mt-1">Unified tasks across all modules</p>
          </div>
          <div className="flex items-center space-x-3 flex-wrap gap-y-2">
            <button
              onClick={handleDownloadPdf}
              disabled={downloadingPdf}
              className="inline-flex items-center space-x-2 px-4 py-2.5 bg-white border border-[rgba(59,77,67,0.2)] text-[#3D4A44] rounded-xl hover:bg-[#EEF1EC] transition-colors disabled:opacity-50 shadow-sm"
              title="Download action items as a printable report"
            >
              <ArrowDownTrayIcon className="w-5 h-5" />
              <span>{downloadingPdf ? 'Downloading...' : 'Download Report'}</span>
            </button>
            <button
              onClick={openEmailModal}
              className="inline-flex items-center space-x-2 px-4 py-2.5 bg-white border border-[rgba(59,77,67,0.2)] text-[#3D4A44] rounded-xl hover:bg-[#EEF1EC] transition-colors shadow-sm"
              title="Email action items report"
            >
              <EnvelopeIcon className="w-5 h-5" />
              <span>Email Report</span>
            </button>
            <button
              onClick={handleGenerateCrossModule}
              disabled={generatingCrossModule}
              className="inline-flex items-center space-x-2 px-4 py-2.5 bg-gradient-to-r from-[#4A7A62] to-[#5B8A72] text-white rounded-xl hover:from-[#3A6A52] hover:to-[#4A7A62] transition-all disabled:opacity-50 shadow-sm"
            >
              {generatingCrossModule ? (
                <ArrowPathIcon className="w-5 h-5 animate-spin" />
              ) : (
                <BoltIcon className="w-5 h-5" />
              )}
              <span>{generatingCrossModule ? 'Scanning...' : 'Scan All Modules'}</span>
            </button>
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
              <span>{generating ? 'Scanning...' : 'Generate from Catalog'}</span>
            </button>
            <button
              onClick={() => setShowAddForm(true)}
              className="inline-flex items-center space-x-2 px-4 py-2.5 bg-[#5B8A72] text-white rounded-xl hover:bg-[#4A7862] transition-colors shadow-sm"
            >
              <PlusIcon className="w-5 h-5" />
              <span>Add Task</span>
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 mb-6">
          <div className="bg-white rounded-[18px] border border-[rgba(59,77,67,0.08)] shadow-sm p-6 relative overflow-hidden">
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

          <div className="bg-white rounded-[18px] border border-[rgba(59,77,67,0.08)] shadow-sm p-6 relative overflow-hidden">
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

          <div className="bg-white rounded-[18px] border border-[rgba(59,77,67,0.08)] shadow-sm p-6 relative overflow-hidden">
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

          <div className="bg-white rounded-[18px] border border-[rgba(59,77,67,0.08)] shadow-sm p-6 relative overflow-hidden">
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

        {(Object.keys(byEntityType).length > 0 || Object.keys(byActionType).length > 0) && (
          <div className="bg-white rounded-[18px] border border-[rgba(59,77,67,0.08)] shadow-sm p-4 mb-6">
            <div className="flex flex-wrap gap-4">
              {Object.keys(byEntityType).length > 0 && (
                <div className="flex-1 min-w-[200px]">
                  <p className="text-[11px] font-medium text-[#7A8580] uppercase tracking-wider mb-2">By Module</p>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(byEntityType).map(([type, count]) => (
                      <span
                        key={type}
                        className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-[rgba(91,138,114,0.1)] text-[#5B8A72]"
                      >
                        {formatEntityType(type)}: {count}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {Object.keys(byActionType).length > 0 && (
                <div className="flex-1 min-w-[200px]">
                  <p className="text-[11px] font-medium text-[#7A8580] uppercase tracking-wider mb-2">By Type</p>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(byActionType).map(([type, count]) => (
                      <span
                        key={type}
                        className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-[rgba(196,149,107,0.1)] text-[#C4956B]"
                      >
                        {formatActionType(type)}: {count}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        <div className="flex flex-wrap gap-2 mb-6">
          {ENTITY_TYPE_PILLS.map(pill => (
            <button
              key={pill.value}
              onClick={() => setFilterEntityType(pill.value)}
              className={`px-4 py-1.5 rounded-full text-sm font-medium transition-all ${
                filterEntityType === pill.value
                  ? 'bg-[#5B8A72] text-white shadow-sm'
                  : 'bg-white text-[#3D4A44] border border-[rgba(59,77,67,0.15)] hover:border-[#5B8A72] hover:text-[#5B8A72]'
              }`}
            >
              {pill.label}
            </button>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-3 bg-white rounded-[18px] border border-[rgba(59,77,67,0.08)] shadow-sm p-4 mb-6">
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

          <select
            value={filterAssignedTo}
            onChange={(e) => setFilterAssignedTo(e.target.value)}
            className="text-sm px-3 py-1.5 border border-[rgba(59,77,67,0.2)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44] max-w-[200px]"
          >
            <option value="">All Assignees</option>
            {members.map(m => (
              <option key={m.user_id || m.id} value={m.user_id || m.id}>{m.username || m.email || m.name}</option>
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

        {showEmailModal && (
          <div className="fixed inset-0 bg-black/30 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md">
              <div className="p-6 border-b border-[rgba(59,77,67,0.1)]">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold text-[#3D4A44]">Email Action Items</h3>
                  <button onClick={() => setShowEmailModal(false)} className="text-[#7A8580] hover:text-[#3D4A44]">
                    <XMarkIcon className="w-5 h-5" />
                  </button>
                </div>
              </div>
              <div className="p-6 space-y-5">
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1.5">Creator</label>
                  <select
                    value={emailForm.creator_id}
                    onChange={(e) => setEmailForm({...emailForm, creator_id: e.target.value})}
                    className="w-full px-3 py-2.5 border border-[rgba(59,77,67,0.2)] rounded-xl text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  >
                    <option value="">Select a creator...</option>
                    {creators.map(c => (
                      <option key={c.id} value={c.id}>{c.display_name}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-2">Send To</label>
                  <div className="space-y-2">
                    <label className="flex items-center gap-3 p-3 rounded-xl border border-[rgba(59,77,67,0.15)] hover:bg-[#F5F7F4] cursor-pointer transition-colors">
                      <input type="radio" name="send_to" value="me" checked={emailForm.send_to === 'me'} onChange={(e) => setEmailForm({...emailForm, send_to: e.target.value})} className="accent-[#5B8A72]" />
                      <div>
                        <p className="text-sm font-medium text-[#3D4A44]">Send to me (manager)</p>
                        <p className="text-xs text-[#7A8580]">Receive the report at your account email</p>
                      </div>
                    </label>
                    {emailForm.creator_id && creators.find(c => c.id === parseInt(emailForm.creator_id))?.email && (
                      <label className="flex items-center gap-3 p-3 rounded-xl border border-[rgba(59,77,67,0.15)] hover:bg-[#F5F7F4] cursor-pointer transition-colors">
                        <input type="radio" name="send_to" value="creator" checked={emailForm.send_to === 'creator'} onChange={(e) => setEmailForm({...emailForm, send_to: e.target.value})} className="accent-[#5B8A72]" />
                        <div>
                          <p className="text-sm font-medium text-[#3D4A44]">Send to creator</p>
                          <p className="text-xs text-[#7A8580]">{creators.find(c => c.id === parseInt(emailForm.creator_id))?.email}</p>
                        </div>
                      </label>
                    )}
                    <label className="flex items-center gap-3 p-3 rounded-xl border border-[rgba(59,77,67,0.15)] hover:bg-[#F5F7F4] cursor-pointer transition-colors">
                      <input type="radio" name="send_to" value="custom" checked={emailForm.send_to === 'custom'} onChange={(e) => setEmailForm({...emailForm, send_to: e.target.value})} className="accent-[#5B8A72]" />
                      <div className="flex-1">
                        <p className="text-sm font-medium text-[#3D4A44]">Send to custom email</p>
                        {emailForm.send_to === 'custom' && (
                          <input
                            type="email"
                            placeholder="email@example.com"
                            value={emailForm.custom_email}
                            onChange={(e) => setEmailForm({...emailForm, custom_email: e.target.value})}
                            className="mt-2 w-full px-3 py-2 border border-[rgba(59,77,67,0.2)] rounded-lg text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                            onClick={(e) => e.stopPropagation()}
                          />
                        )}
                      </div>
                    </label>
                  </div>
                </div>
              </div>
              <div className="p-6 border-t border-[rgba(59,77,67,0.1)] flex justify-end gap-3">
                <button onClick={() => setShowEmailModal(false)} className="px-4 py-2.5 text-sm text-[#7A8580] hover:text-[#3D4A44] transition-colors">Cancel</button>
                <button
                  onClick={handleSendEmail}
                  disabled={pushingEmail || !emailForm.creator_id}
                  className="inline-flex items-center space-x-2 px-5 py-2.5 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-xl hover:from-[#4A7862] hover:to-[#6A9484] transition-all disabled:opacity-50 shadow-sm text-sm font-medium"
                >
                  <EnvelopeIcon className="w-4 h-4" />
                  <span>{pushingEmail ? 'Sending...' : 'Send Email'}</span>
                </button>
              </div>
            </div>
          </div>
        )}

        {showAddForm && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4" onClick={() => setShowAddForm(false)}>
            <div className="bg-white rounded-2xl shadow-xl w-full max-w-xl max-h-[90vh] flex flex-col" onClick={e => e.stopPropagation()}>
              <div className="flex items-center justify-between px-6 py-4 border-b border-[rgba(59,77,67,0.08)]">
                <h4 className="text-lg font-semibold text-[#3D4A44]">New Task</h4>
                <button onClick={() => setShowAddForm(false)} className="text-[#7A8580] hover:text-[#3D4A44]">
                  <XMarkIcon className="w-5 h-5" />
                </button>
              </div>

              <div className="overflow-y-auto px-6 py-5 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Title *</label>
                  <input
                    type="text"
                    value={newAction.title}
                    onChange={(e) => setNewAction({ ...newAction, title: e.target.value })}
                    placeholder="e.g., Follow up with client, Submit registration..."
                    className="w-full px-3 py-2.5 border border-[rgba(59,77,67,0.2)] rounded-xl text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-[#3D4A44] mb-1">Type</label>
                    <select
                      value={newAction.action_type}
                      onChange={(e) => setNewAction({ ...newAction, action_type: e.target.value })}
                      className="w-full px-3 py-2.5 border border-[rgba(59,77,67,0.2)] rounded-xl text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
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
                      className="w-full px-3 py-2.5 border border-[rgba(59,77,67,0.2)] rounded-xl text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                    >
                      {PRIORITY_OPTIONS.map(opt => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="min-w-0">
                    <label className="block text-sm font-medium text-[#3D4A44] mb-1">Deadline</label>
                    <input
                      type="date"
                      value={newAction.deadline}
                      onChange={(e) => setNewAction({ ...newAction, deadline: e.target.value })}
                      className="w-full min-w-0 px-3 py-2.5 border border-[rgba(59,77,67,0.2)] rounded-xl text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent appearance-none"
                      style={{ WebkitAppearance: 'none' }}
                    />
                  </div>

                  <div className="min-w-0">
                    <label className="block text-sm font-medium text-[#3D4A44] mb-1 truncate">Remind Before (days)</label>
                    <input
                      type="number"
                      min="0"
                      value={newAction.reminder_days_before}
                      onChange={(e) => setNewAction({ ...newAction, reminder_days_before: parseInt(e.target.value) || 0 })}
                      className="w-full min-w-0 px-3 py-2.5 border border-[rgba(59,77,67,0.2)] rounded-xl text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Assign To</label>
                  <select
                    value={newAction.assigned_to_user_id}
                    onChange={(e) => setNewAction(prev => ({...prev, assigned_to_user_id: e.target.value}))}
                    className="w-full px-3 py-2.5 border border-[rgba(59,77,67,0.2)] rounded-xl text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                  >
                    <option value="">Unassigned</option>
                    {members.map(m => (
                      <option key={m.user_id || m.id} value={m.user_id || m.id}>{m.username || m.email || m.name}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Description</label>
                  <textarea
                    value={newAction.description}
                    onChange={(e) => setNewAction({ ...newAction, description: e.target.value })}
                    placeholder="Add details, instructions, or notes..."
                    rows={3}
                    className="w-full px-3 py-2.5 border border-[rgba(59,77,67,0.2)] rounded-xl text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent resize-none"
                  />
                </div>

                <details className="group">
                  <summary className="text-sm font-medium text-[#7A8580] cursor-pointer hover:text-[#5B8A72] transition-colors flex items-center gap-1.5">
                    <ChevronDownIcon className="w-4 h-4 group-open:rotate-180 transition-transform" />
                    Link to Entity (optional)
                  </summary>
                  <div className="mt-3 space-y-3">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-xs font-medium text-[#7A8580] mb-1">Module</label>
                        <select
                          value={newAction.entity_type}
                          onChange={(e) => setNewAction({ ...newAction, entity_type: e.target.value })}
                          className="w-full px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                        >
                          {ENTITY_TYPE_OPTIONS.map(opt => (
                            <option key={opt.value} value={opt.value}>{opt.label}</option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-[#7A8580] mb-1">Creator</label>
                        <select
                          value={newAction.creator_id}
                          onChange={(e) => setNewAction({ ...newAction, creator_id: e.target.value })}
                          className="w-full px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                        >
                          <option value="">None</option>
                          {creators.map(c => (
                            <option key={c.id} value={c.id}>{c.display_name}</option>
                          ))}
                        </select>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-xs font-medium text-[#7A8580] mb-1">Song</label>
                        <select
                          value={newAction.song_id}
                          onChange={(e) => setNewAction({ ...newAction, song_id: e.target.value })}
                          className="w-full px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                        >
                          <option value="">None</option>
                          {songs.map(s => (
                            <option key={s.id} value={s.id}>{s.title}</option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-[#7A8580] mb-1">Contract ID</label>
                        <input
                          type="number"
                          value={newAction.contract_id}
                          onChange={(e) => setNewAction({ ...newAction, contract_id: e.target.value })}
                          placeholder="Optional"
                          className="w-full px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-3 gap-4">
                      <div>
                        <label className="block text-xs font-medium text-[#7A8580] mb-1">Work ID</label>
                        <input
                          type="number"
                          value={newAction.work_id}
                          onChange={(e) => setNewAction({ ...newAction, work_id: e.target.value })}
                          placeholder="Optional"
                          className="w-full px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-[#7A8580] mb-1">Release ID</label>
                        <input
                          type="number"
                          value={newAction.release_id}
                          onChange={(e) => setNewAction({ ...newAction, release_id: e.target.value })}
                          placeholder="Optional"
                          className="w-full px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-[#7A8580] mb-1">Placement ID</label>
                        <input
                          type="number"
                          value={newAction.placement_id}
                          onChange={(e) => setNewAction({ ...newAction, placement_id: e.target.value })}
                          placeholder="Optional"
                          className="w-full px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                        />
                      </div>
                    </div>
                  </div>
                </details>
              </div>

              <div className="px-6 py-4 border-t border-[rgba(59,77,67,0.08)] flex justify-end gap-3">
                <button
                  onClick={() => setShowAddForm(false)}
                  className="px-5 py-2.5 text-[#7A8580] hover:text-[#3D4A44] font-medium text-sm transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleAddAction}
                  disabled={saving || !newAction.title.trim()}
                  className="px-5 py-2.5 bg-[#5B8A72] text-white rounded-xl font-medium text-sm hover:bg-[#4A7862] transition-colors disabled:opacity-50"
                >
                  {saving ? 'Adding...' : 'Add Task'}
                </button>
              </div>
            </div>
          </div>
        )}

        <div className="space-y-3">
          {sortedActions.length === 0 ? (
            <div className="bg-white rounded-[18px] border border-[rgba(59,77,67,0.08)] shadow-sm p-12 text-center">
              <ClockIcon className="w-12 h-12 text-[#7A8580] mx-auto mb-4" />
              {hasActiveFilters ? (
                <>
                  <p className="text-[#7A8580]">No tasks match your filters</p>
                  <button onClick={clearFilters} className="text-sm text-[#5B8A72] hover:underline mt-2">
                    Clear filters
                  </button>
                </>
              ) : (
                <>
                  <p className="text-[#7A8580]">No tasks yet</p>
                  <p className="text-sm text-[#7A8580] mt-1">Click "Add Task", "Scan All Modules", or "Generate from Catalog" to get started</p>
                </>
              )}
            </div>
          ) : (
            sortedActions.map((action) => {
              const priorityStyle = getPriorityStyle(action.priority)
              const isCompleted = action.status === 'COMPLETED'
              const entityLinks = getEntityLink(action)

              return (
                <div
                  key={action.id}
                  className={`bg-white rounded-[18px] border border-[rgba(59,77,67,0.08)] shadow-sm p-4 transition-all ${
                    action.is_overdue
                      ? 'border-[#C47068]'
                      : isCompleted
                        ? 'opacity-60'
                        : ''
                  }`}
                >
                  <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                    <div className="flex items-start space-x-4 flex-1 min-w-0">
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
                          {action.is_auto_generated && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-[rgba(91,138,114,0.08)] text-[#7A8580]">
                              Auto
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

                          {action.entity_type && (
                            <span className="inline-flex items-center px-2 py-1 rounded-full bg-[rgba(90,138,154,0.1)] text-[#5A8A9A] font-medium">
                              {formatEntityType(action.entity_type)}
                            </span>
                          )}

                          {action.creator_name && (
                            <span className="inline-flex items-center px-2 py-1 rounded-full bg-[#EEF1EC] text-[#3D4A44] font-medium">
                              {action.creator_name}
                            </span>
                          )}

                          {action.assigned_to_name && (
                            <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-[rgba(91,138,114,0.08)] text-[#5B8A72] font-medium">
                              <UserIcon className="w-3 h-3" />
                              {action.assigned_to_name}
                            </span>
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

                        {entityLinks.length > 0 && (
                          <div className="flex flex-wrap items-center gap-2 mt-2">
                            {entityLinks.map((link, idx) => {
                              const IconComp = link.icon
                              return (
                                <button
                                  key={idx}
                                  onClick={() => navigate(link.path)}
                                  className="inline-flex items-center space-x-1 px-2 py-1 rounded-lg text-xs font-medium text-[#5B8A72] bg-[rgba(91,138,114,0.06)] hover:bg-[rgba(91,138,114,0.15)] transition-colors"
                                >
                                  <IconComp className="w-3 h-3" />
                                  <span>{link.label}</span>
                                  <LinkIcon className="w-2.5 h-2.5 opacity-50" />
                                </button>
                              )
                            })}
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center space-x-1 sm:ml-4 ml-10 shrink-0">
                      {!isCompleted && (
                        <select
                          value={action.assigned_to_user_id || ''}
                          onChange={(e) => handleAssignAction(action.id, e.target.value)}
                          className="text-xs px-2 py-1.5 border border-[rgba(59,77,67,0.15)] rounded-lg bg-white text-[#3D4A44] focus:ring-1 focus:ring-[#5B8A72] focus:border-transparent max-w-[120px]"
                          title="Assign to"
                        >
                          <option value="">Assign...</option>
                          {members.map(m => (
                            <option key={m.user_id || m.id} value={m.user_id || m.id}>{m.username || m.email || m.name}</option>
                          ))}
                        </select>
                      )}
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

      {showScrollTop && (
        <button
          onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
          className="fixed bottom-6 right-6 z-50 p-3 bg-[#5B8A72] text-white rounded-full shadow-lg hover:bg-[#4A7A62] transition-all"
        >
          <ArrowUpIcon className="w-5 h-5" />
        </button>
      )}
    </div>
  )
}
