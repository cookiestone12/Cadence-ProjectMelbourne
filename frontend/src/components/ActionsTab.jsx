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
  ArrowPathIcon
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

export default function ActionsTab({ creatorId, organizationId, creatorName }) {
  const [actions, setActions] = useState([])
  const [loading, setLoading] = useState(true)
  const [showAddForm, setShowAddForm] = useState(false)
  const [includeCompleted, setIncludeCompleted] = useState(false)
  const [newAction, setNewAction] = useState({
    action_type: 'GENERAL',
    title: '',
    description: '',
    priority: 2,
    deadline: '',
    reminder_days_before: 3
  })
  const [saving, setSaving] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [gapsCount, setGapsCount] = useState(0)

  const loadActions = async () => {
    try {
      const response = await axios.get(`/api/actions/creator/${creatorId}?include_completed=${includeCompleted}`)
      setActions(response.data)
    } catch (error) {
      console.error('Failed to load actions:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadGapsCount = async () => {
    try {
      const response = await axios.get(`/api/actions/gaps/${creatorId}`)
      setGapsCount(response.data.total_gaps || 0)
    } catch (error) {
      console.error('Failed to load gaps:', error)
    }
  }

  useEffect(() => {
    loadActions()
    loadGapsCount()
  }, [creatorId, includeCompleted])

  const handleAddAction = async () => {
    if (!newAction.title.trim()) return
    
    setSaving(true)
    try {
      await axios.post(`/api/actions/org/${organizationId}`, {
        ...newAction,
        creator_id: creatorId,
        deadline: newAction.deadline || null
      })
      setShowAddForm(false)
      setNewAction({
        action_type: 'GENERAL',
        title: '',
        description: '',
        priority: 2,
        deadline: '',
        reminder_days_before: 3
      })
      loadActions()
    } catch (error) {
      console.error('Failed to add action:', error)
    } finally {
      setSaving(false)
    }
  }

  const handleCompleteAction = async (actionId) => {
    try {
      await axios.post(`/api/actions/${actionId}/complete`)
      loadActions()
    } catch (error) {
      console.error('Failed to complete action:', error)
    }
  }

  const handleDeleteAction = async (actionId) => {
    try {
      await axios.delete(`/api/actions/${actionId}`)
      loadActions()
    } catch (error) {
      console.error('Failed to delete action:', error)
    }
  }

  const handleUpdateDeadline = async (actionId, newDeadline) => {
    try {
      await axios.put(`/api/actions/${actionId}`, { deadline: newDeadline || null })
      loadActions()
    } catch (error) {
      console.error('Failed to update deadline:', error)
    }
  }

  const handleGenerateActions = async () => {
    setGenerating(true)
    try {
      const response = await axios.post(`/api/actions/generate/${creatorId}`)
      loadActions()
      loadGapsCount()
    } catch (error) {
      console.error('Failed to generate actions:', error)
    } finally {
      setGenerating(false)
    }
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

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-[#7A8580]">Loading actions...</div>
      </div>
    )
  }

  const pendingActions = actions.filter(a => a.status !== 'COMPLETED')
  const overdueActions = pendingActions.filter(a => a.is_overdue)
  const upcomingActions = pendingActions.filter(a => !a.is_overdue && a.days_until_deadline !== null && a.days_until_deadline <= 7)

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl p-6 border border-[rgba(59,77,67,0.08)]">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-lg" style={{ backgroundColor: 'rgba(91, 138, 114, 0.15)' }}>
              <ClockIcon className="w-5 h-5 text-[#5B8A72]" />
            </div>
            <div>
              <p className="text-sm text-[#7A8580]">Pending Actions</p>
              <p className="text-2xl font-semibold text-[#3D4A44]">{pendingActions.length}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-xl p-6 border border-[rgba(59,77,67,0.08)]">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-lg" style={{ backgroundColor: 'rgba(196, 112, 104, 0.15)' }}>
              <ExclamationTriangleIcon className="w-5 h-5 text-[#C47068]" />
            </div>
            <div>
              <p className="text-sm text-[#7A8580]">Overdue</p>
              <p className="text-2xl font-semibold text-[#C47068]">{overdueActions.length}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-xl p-6 border border-[rgba(59,77,67,0.08)]">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-lg" style={{ backgroundColor: 'rgba(196, 149, 107, 0.15)' }}>
              <CalendarIcon className="w-5 h-5 text-[#C4956B]" />
            </div>
            <div>
              <p className="text-sm text-[#7A8580]">Due This Week</p>
              <p className="text-2xl font-semibold text-[#C4956B]">{upcomingActions.length}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <h3 className="text-lg font-semibold text-[#3D4A44]">Action Items for {creatorName}</h3>
          <label className="flex items-center space-x-2 text-sm text-[#7A8580]">
            <input
              type="checkbox"
              checked={includeCompleted}
              onChange={(e) => setIncludeCompleted(e.target.checked)}
              className="rounded border-[#7A8580] text-[#5B8A72] focus:ring-[#5B8A72]"
            />
            <span>Show Completed</span>
          </label>
        </div>
        <div className="flex items-center space-x-2">
          {gapsCount > 0 && (
            <button
              onClick={handleGenerateActions}
              disabled={generating}
              className="inline-flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-lg hover:from-[#4A7862] hover:to-[#6A9484] transition-all disabled:opacity-50"
            >
              {generating ? (
                <ArrowPathIcon className="w-4 h-4 animate-spin" />
              ) : (
                <SparklesIcon className="w-4 h-4" />
              )}
              <span>{generating ? 'Generating...' : `Generate Actions (${gapsCount})`}</span>
            </button>
          )}
          <button
            onClick={() => setShowAddForm(true)}
            className="inline-flex items-center space-x-2 px-4 py-2 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7862] transition-colors"
          >
            <PlusIcon className="w-4 h-4" />
            <span>Add Action</span>
          </button>
        </div>
      </div>

      {showAddForm && (
        <div className="bg-white rounded-xl p-6 border border-[#5B8A72] shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h4 className="font-semibold text-[#3D4A44]">New Action Item</h4>
            <button onClick={() => setShowAddForm(false)} className="text-[#7A8580] hover:text-[#3D4A44]">
              <XMarkIcon className="w-5 h-5" />
            </button>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-[#3D4A44] mb-1">Title *</label>
              <input
                type="text"
                value={newAction.title}
                onChange={(e) => setNewAction({...newAction, title: e.target.value})}
                placeholder="e.g., Submit ISRC registration"
                className="w-full px-3 py-2 border border-[rgba(59,77,67,0.2)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-[#3D4A44] mb-1">Type</label>
              <select
                value={newAction.action_type}
                onChange={(e) => setNewAction({...newAction, action_type: e.target.value})}
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
                onChange={(e) => setNewAction({...newAction, priority: parseInt(e.target.value)})}
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
                onChange={(e) => setNewAction({...newAction, deadline: e.target.value})}
                className="w-full px-3 py-2 border border-[rgba(59,77,67,0.2)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-[#3D4A44] mb-1">Remind Days Before</label>
              <input
                type="number"
                min="0"
                value={newAction.reminder_days_before}
                onChange={(e) => setNewAction({...newAction, reminder_days_before: parseInt(e.target.value) || 0})}
                className="w-full px-3 py-2 border border-[rgba(59,77,67,0.2)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
              />
            </div>
            
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-[#3D4A44] mb-1">Description</label>
              <textarea
                value={newAction.description}
                onChange={(e) => setNewAction({...newAction, description: e.target.value})}
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
        {actions.length === 0 ? (
          <div className="bg-white rounded-xl p-12 text-center border border-[rgba(59,77,67,0.08)]">
            <ClockIcon className="w-12 h-12 text-[#7A8580] mx-auto mb-4" />
            <p className="text-[#7A8580]">No action items yet</p>
            <p className="text-sm text-[#7A8580] mt-1">Click "Add Action" to create your first action item</p>
          </div>
        ) : (
          actions.map((action) => {
            const priorityStyle = getPriorityStyle(action.priority)
            const isCompleted = action.status === 'COMPLETED'
            
            return (
              <div 
                key={action.id}
                className={`bg-white rounded-xl p-4 border transition-all ${
                  action.is_overdue 
                    ? 'border-[#C47068] shadow-sm' 
                    : isCompleted 
                      ? 'border-[rgba(59,77,67,0.08)] opacity-60' 
                      : 'border-[rgba(59,77,67,0.08)]'
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
                        
                        {action.is_auto_generated && (
                          <span className="inline-flex items-center px-2 py-1 rounded-full bg-[rgba(123,165,148,0.15)] text-[#7BA594] text-xs">
                            <SparklesIcon className="w-3 h-3 mr-1" />
                            Auto
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
                  
                  <div className="flex items-center space-x-2 ml-4">
                    <input
                      type="date"
                      value={action.deadline ? action.deadline.split('T')[0] : ''}
                      onChange={(e) => handleUpdateDeadline(action.id, e.target.value)}
                      disabled={isCompleted}
                      className="text-xs px-2 py-1 border border-[rgba(59,77,67,0.2)] rounded-lg focus:ring-1 focus:ring-[#5B8A72]"
                      title="Update deadline"
                    />
                    <button
                      onClick={() => handleDeleteAction(action.id)}
                      className="p-1 text-[#7A8580] hover:text-[#C47068] transition-colors"
                      title="Delete action"
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
  )
}
