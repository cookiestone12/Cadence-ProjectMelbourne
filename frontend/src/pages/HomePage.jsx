import React, { useState, useEffect, useCallback } from 'react'
import axios from 'axios'
import { Cog6ToothIcon } from '@heroicons/react/24/outline'
import StatsRowWidget from '../components/widgets/StatsRowWidget'
import PlacementPipelineWidget from '../components/widgets/PlacementPipelineWidget'
import TaskBreakdownWidget from '../components/widgets/TaskBreakdownWidget'
import UrgentActionsWidget from '../components/widgets/UrgentActionsWidget'
import NeedsAttentionWidget from '../components/widgets/NeedsAttentionWidget'
import NotificationsWidget from '../components/widgets/NotificationsWidget'
import TopCreatorsWidget from '../components/widgets/TopCreatorsWidget'
import CustomizeDashboard from '../components/widgets/CustomizeDashboard'

const STORAGE_KEY = 'dashboard_widget_prefs'

const DEFAULT_ORDER = [
  'stats',
  'placements',
  'taskBreakdown',
  'urgentActions',
  'needsAttention',
  'notifications',
  'topCreators'
]

const DEFAULT_VISIBILITY = {
  stats: true,
  placements: true,
  taskBreakdown: true,
  urgentActions: true,
  needsAttention: true,
  notifications: true,
  topCreators: true
}

function loadPreferences() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      const parsed = JSON.parse(stored)
      const validIds = new Set(DEFAULT_ORDER)
      const storedOrder = parsed.order
      const order = Array.isArray(storedOrder)
        && storedOrder.length === DEFAULT_ORDER.length
        && storedOrder.every(id => validIds.has(id))
        && new Set(storedOrder).size === storedOrder.length
        ? storedOrder
        : DEFAULT_ORDER
      const visibility = parsed.visibility && typeof parsed.visibility === 'object'
        ? { ...DEFAULT_VISIBILITY, ...parsed.visibility }
        : DEFAULT_VISIBILITY
      return { order, visibility }
    }
  } catch {}
  return { order: DEFAULT_ORDER, visibility: DEFAULT_VISIBILITY }
}

function savePreferences(order, visibility) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ order, visibility }))
  } catch {}
}

const SectionSkeleton = ({ height = 'h-32' }) => (
  <div className={`bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6 ${height} animate-pulse`}>
    <div className="h-4 bg-[#EEF1EC] rounded w-1/3 mb-3"></div>
    <div className="h-8 bg-[#EEF1EC] rounded w-1/4"></div>
  </div>
)

export default function HomePage() {
  const [org, setOrg] = useState(null)
  const [orgId, setOrgId] = useState(null)
  const [orgLoading, setOrgLoading] = useState(true)

  const [customizeOpen, setCustomizeOpen] = useState(false)
  const [widgetOrder, setWidgetOrder] = useState(() => loadPreferences().order)
  const [widgetVisibility, setWidgetVisibility] = useState(() => loadPreferences().visibility)

  const storedUser = localStorage.getItem('user')
  let userName = 'User'
  try {
    const parsed = JSON.parse(storedUser)
    userName = parsed?.display_name || parsed?.username || 'User'
  } catch {}

  useEffect(() => {
    savePreferences(widgetOrder, widgetVisibility)
  }, [widgetOrder, widgetVisibility])

  useEffect(() => {
    async function loadOrg() {
      try {
        const orgResponse = await axios.get('/api/organizations/current')
        const id = orgResponse.data?.id
        if (!id) { setOrgLoading(false); return }
        setOrg(orgResponse.data)
        setOrgId(id)
      } catch (error) {
        console.error('Failed to load organization:', error)
      } finally {
        setOrgLoading(false)
      }
    }
    loadOrg()
  }, [])

  const handleReorder = useCallback((newOrder) => {
    setWidgetOrder(newOrder)
  }, [])

  const handleToggleVisibility = useCallback((widgetId) => {
    setWidgetVisibility(prev => ({
      ...prev,
      [widgetId]: !prev[widgetId]
    }))
  }, [])

  const handleReset = useCallback(() => {
    setWidgetOrder(DEFAULT_ORDER)
    setWidgetVisibility(DEFAULT_VISIBILITY)
  }, [])

  const renderWidget = (widgetId) => {
    const widgets = {
      stats: <StatsRowWidget org={org} orgId={orgId} />,
      placements: <PlacementPipelineWidget orgId={orgId} />,
      taskBreakdown: <TaskBreakdownWidget orgId={orgId} />,
      urgentActions: <UrgentActionsWidget orgId={orgId} />,
      needsAttention: <NeedsAttentionWidget orgId={orgId} />,
      notifications: <NotificationsWidget />,
      topCreators: <TopCreatorsWidget orgId={orgId} />
    }
    return widgets[widgetId] || null
  }

  const isDoubleColumnWidget = (widgetId) => {
    return widgetId === 'needsAttention' || widgetId === 'notifications'
  }

  if (orgLoading) {
    return (
      <div className="min-h-screen bg-[#F5F7F4] p-6 lg:p-8">
        <div className="max-w-7xl mx-auto">
          <div className="mb-8 animate-pulse">
            <div className="h-8 bg-[#EEF1EC] rounded w-72 mb-2"></div>
            <div className="h-5 bg-[#EEF1EC] rounded w-64"></div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
            {[1,2,3,4].map(i => <SectionSkeleton key={i} />)}
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <SectionSkeleton height="h-64" />
            <SectionSkeleton height="h-64" />
          </div>
        </div>
      </div>
    )
  }

  const visibleWidgets = widgetOrder.filter(id => widgetVisibility[id])

  const renderWidgetLayout = () => {
    const elements = []
    let i = 0
    while (i < visibleWidgets.length) {
      const current = visibleWidgets[i]
      const next = visibleWidgets[i + 1]

      if (isDoubleColumnWidget(current) && next && isDoubleColumnWidget(next)) {
        elements.push(
          <div key={`pair-${current}-${next}`} className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div>{renderWidget(current)}</div>
            <div>{renderWidget(next)}</div>
          </div>
        )
        i += 2
      } else {
        elements.push(
          <div key={current}>
            {renderWidget(current)}
          </div>
        )
        i++
      }
    }
    return elements
  }

  return (
    <div className="min-h-screen bg-[#F5F7F4] p-6 lg:p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              {org?.logo_url && (
                <img src={org.logo_url} alt={org.display_name || org.name} className="w-12 h-12 rounded-xl object-contain shadow-sm" />
              )}
              <div>
                <h1 className="text-[34px] font-semibold text-[#3D4A44] leading-tight">
                  Welcome back, {userName}
                </h1>
                <p className="text-[17px] text-[#7A8580] mt-1">Here's what's happening with your catalog</p>
              </div>
            </div>
            <button
              onClick={() => setCustomizeOpen(true)}
              className="flex items-center gap-2 px-4 py-2.5 bg-white rounded-xl shadow-[0px_2px_8px_rgba(0,0,0,0.08)] hover:shadow-[0px_4px_12px_rgba(0,0,0,0.12)] transition-all text-[#5B8A72] hover:text-[#4A7A62] text-sm font-medium"
            >
              <Cog6ToothIcon className="w-4 h-4" />
              <span className="hidden sm:inline">Customize</span>
            </button>
          </div>
        </div>

        <div className="space-y-6">
          {renderWidgetLayout()}
        </div>
      </div>

      <CustomizeDashboard
        isOpen={customizeOpen}
        onClose={() => setCustomizeOpen(false)}
        widgetOrder={widgetOrder}
        widgetVisibility={widgetVisibility}
        onReorder={handleReorder}
        onToggleVisibility={handleToggleVisibility}
        onReset={handleReset}
      />
    </div>
  )
}
