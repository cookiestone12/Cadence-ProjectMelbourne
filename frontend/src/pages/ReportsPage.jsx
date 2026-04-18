import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import axios from 'axios'
import {
  BarChart, Bar, PieChart, Pie, Cell, ResponsiveContainer, XAxis, YAxis,
  Tooltip, Legend, LineChart, Line, AreaChart, Area, CartesianGrid,
  RadialBarChart, RadialBar
} from 'recharts'
import {
  ChartBarIcon, CurrencyDollarIcon, UsersIcon, HeartIcon,
  FilmIcon, ShieldCheckIcon, MusicalNoteIcon, DocumentTextIcon,
  RectangleStackIcon, ExclamationTriangleIcon, ArrowTrendingUpIcon,
  CheckCircleIcon, ArrowDownTrayIcon, ArrowRightIcon
} from '@heroicons/react/24/outline'

const TABS = [
  { key: 'overview', label: 'Overview', icon: ChartBarIcon },
  { key: 'health', label: 'Catalog Health', icon: HeartIcon },
  { key: 'revenue', label: 'Revenue', icon: CurrencyDollarIcon },
  { key: 'creators', label: 'Creators', icon: UsersIcon },
  { key: 'placements', label: 'Placements', icon: FilmIcon },
  { key: 'rights', label: 'Rights Coverage', icon: ShieldCheckIcon },
]

const DATE_RANGES = [
  { key: '30d', label: '30d' },
  { key: '90d', label: '90d' },
  { key: '1y', label: '1y' },
  { key: 'all', label: 'All' },
]

const DATE_RANGE_MONTHS = { '30d': 1, '90d': 3, '1y': 12, 'all': 120 }

const EXPORT_MAP = {
  overview: 'catalog-summary',
  health: 'catalog-summary',
  revenue: 'revenue-summary',
  creators: 'creators-summary',
  placements: 'placements-summary',
  rights: 'contracts-summary',
}

const CHART_COLORS = ['#5B8A72', '#5A8A9A', '#C4956B', '#C47068', '#7BA594', '#8B6EAE', '#5B9A6E', '#D4A57B']

const formatCents = (cents) => {
  if (!cents) return '$0'
  const val = cents / 100
  if (val >= 1000000) return `$${(val / 1000000).toFixed(1)}M`
  if (val >= 1000) return `$${(val / 1000).toFixed(1)}K`
  return `$${val.toFixed(2)}`
}

const formatDollars = (val) => {
  if (!val) return '$0'
  if (val >= 1000000) return `$${(val / 1000000).toFixed(1)}M`
  if (val >= 1000) return `$${(val / 1000).toFixed(1)}K`
  return `$${val.toFixed(0)}`
}

export default function ReportsPage() {
  const [activeTab, setActiveTab] = useState('overview')
  const [orgId, setOrgId] = useState(null)
  const [loading, setLoading] = useState(true)
  const [overview, setOverview] = useState(null)
  const [healthData, setHealthData] = useState(null)
  const [revenueData, setRevenueData] = useState(null)
  const [creatorsData, setCreatorsData] = useState(null)
  const [placementsData, setPlacementsData] = useState(null)
  const [rightsData, setRightsData] = useState(null)
  const [growthData, setGrowthData] = useState(null)
  const [valuationData, setValuationData] = useState(null)
  const [expiringContracts, setExpiringContracts] = useState(null)
  const [dateRange, setDateRange] = useState('all')
  const [reconciliation, setReconciliation] = useState(null)

  useEffect(() => {
    async function init() {
      try {
        const orgRes = await axios.get('/api/organizations/current')
        const id = orgRes.data?.id
        if (id) setOrgId(id)
        else setLoading(false)
      } catch (e) {
        console.error('Failed to load org:', e)
        setLoading(false)
      }
    }
    init()
  }, [])

  useEffect(() => {
    if (!orgId) return
    loadTabData(activeTab)
  }, [orgId, activeTab, dateRange])

  useEffect(() => {
    if (!orgId) return
    axios
      .get(`/api/royalty-processing/${orgId}/reconciliation`)
      .then(res => setReconciliation(res.data))
      .catch(e => console.error('Failed to load reconciliation:', e))
  }, [orgId])

  function handleExport(reportType) {
    window.open(`/api/analytics/org/${orgId}/export/${reportType}`, '_blank')
  }

  async function loadTabData(tab) {
    setLoading(true)
    const months = DATE_RANGE_MONTHS[dateRange] || 120
    try {
      switch (tab) {
        case 'overview': {
          const [overviewRes, growthRes, healthRes, valuationRes] = await Promise.all([
            axios.get(`/api/analytics/org/${orgId}/overview`),
            axios.get(`/api/analytics/org/${orgId}/catalog-growth`, { params: { months } }),
            axios.get(`/api/analytics/org/${orgId}/health-distribution`),
            axios.get(`/api/analytics/org/${orgId}/valuation`).catch(() => ({ data: null })),
          ])
          setOverview(overviewRes.data)
          setGrowthData(growthRes.data)
          setHealthData(healthRes.data)
          setValuationData(valuationRes.data)
          break
        }
        case 'health': {
          const [healthRes, growthRes] = await Promise.all([
            axios.get(`/api/analytics/org/${orgId}/health-distribution`),
            axios.get(`/api/analytics/org/${orgId}/catalog-growth`, { params: { months } }),
          ])
          setHealthData(healthRes.data)
          setGrowthData(growthRes.data)
          break
        }
        case 'revenue': {
          const res = await axios.get(`/api/analytics/org/${orgId}/revenue`)
          setRevenueData(res.data)
          break
        }
        case 'creators': {
          const res = await axios.get(`/api/analytics/org/${orgId}/creators`)
          setCreatorsData(res.data)
          break
        }
        case 'placements': {
          const res = await axios.get(`/api/analytics/org/${orgId}/placements`)
          setPlacementsData(res.data)
          break
        }
        case 'rights': {
          const [rightsRes, expiringRes] = await Promise.all([
            axios.get(`/api/analytics/org/${orgId}/rights-coverage`),
            axios.get(`/api/analytics/org/${orgId}/expiring-contracts`).catch(() => ({ data: null })),
          ])
          setRightsData(rightsRes.data)
          setExpiringContracts(expiringRes.data)
          break
        }
      }
    } catch (e) {
      console.error('Failed to load analytics:', e)
    } finally {
      setLoading(false)
    }
  }

  if (!orgId) {
    return (
      <div className="min-h-screen bg-[#F5F7F4] flex items-center justify-center">
        <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-[#5B8A72] border-t-transparent"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#F5F7F4] p-6 lg:p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-6 flex items-start justify-between">
          <div>
            <h1 className="text-[34px] font-semibold text-[#3D4A44] leading-tight">Reports & Analytics</h1>
            <p className="text-[17px] text-[#7A8580] mt-1">Comprehensive insights into your catalog performance</p>
          </div>
          <button
            onClick={() => handleExport(EXPORT_MAP[activeTab])}
            className="flex items-center gap-2 px-4 py-2.5 bg-white rounded-[12px] shadow-[0px_2px_8px_rgba(0,0,0,0.06)] text-[14px] font-medium text-[#3D4A44] hover:bg-[#EEF1EC] transition-all"
          >
            <ArrowDownTrayIcon className="w-4 h-4" />
            Export
          </button>
        </div>

        {reconciliation && reconciliation.totals && reconciliation.totals.flagged_count > 0 && (
          <div className="mb-4 rounded-[14px] border border-[#E0B062] bg-[#FFF8E8] p-4 flex items-start gap-3 shadow-[0px_2px_8px_rgba(0,0,0,0.06)]">
            <ExclamationTriangleIcon className="w-5 h-5 text-[#B07A1F] flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-[14px] font-semibold text-[#7A5410]">
                {reconciliation.totals.flagged_count} royalty {reconciliation.totals.flagged_count === 1 ? 'statement needs' : 'statements need'} attention
              </p>
              <p className="text-[13px] text-[#8A6520] mt-0.5">
                {reconciliation.totals.duplicate_group_count > 0 && (
                  <span>{reconciliation.totals.duplicate_group_count} duplicate {reconciliation.totals.duplicate_group_count === 1 ? 'file' : 'files'} detected. </span>
                )}
                Reports totals may differ from Royalties until these are resolved.
              </p>
              {reconciliation.generated_at && (
                <p className="text-[11px] text-[#A98A4A] mt-1">
                  As of last reconciliation: {new Date(reconciliation.generated_at).toLocaleString()}
                </p>
              )}
            </div>
            <Link
              to="/royalties"
              className="flex items-center gap-1.5 px-3 py-1.5 bg-white rounded-[10px] text-[13px] font-medium text-[#7A5410] hover:bg-[#FFF1D0] border border-[#E0B062] transition-all whitespace-nowrap"
            >
              Review in Royalties
              <ArrowRightIcon className="w-3.5 h-3.5" />
            </Link>
          </div>
        )}

        <div className="flex gap-1 mb-3 bg-white rounded-[14px] p-1.5 shadow-[0px_2px_8px_rgba(0,0,0,0.06)] overflow-x-auto">
          {TABS.map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-[10px] text-[14px] font-medium transition-all whitespace-nowrap ${
                activeTab === tab.key
                  ? 'bg-[#5B8A72] text-white shadow-sm'
                  : 'text-[#7A8580] hover:bg-[#EEF1EC]'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        <div className="flex gap-1.5 mb-6">
          {DATE_RANGES.map(dr => (
            <button
              key={dr.key}
              onClick={() => setDateRange(dr.key)}
              className={`px-4 py-1.5 rounded-full text-[13px] font-medium transition-all ${
                dateRange === dr.key
                  ? 'bg-[#5B8A72] text-white shadow-sm'
                  : 'bg-white text-[#7A8580] hover:bg-[#EEF1EC] shadow-[0px_1px_4px_rgba(0,0,0,0.06)]'
              }`}
            >
              {dr.label}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="text-center">
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-[#5B8A72] border-t-transparent"></div>
              <p className="mt-4 text-[#7A8580]">Loading analytics...</p>
            </div>
          </div>
        ) : (
          <>
            {activeTab === 'overview' && <OverviewTab overview={overview} growthData={growthData} healthData={healthData} valuationData={valuationData} />}
            {activeTab === 'health' && <HealthTab data={healthData} growthData={growthData} />}
            {activeTab === 'revenue' && <RevenueTab data={revenueData} />}
            {activeTab === 'creators' && <CreatorsTab data={creatorsData} />}
            {activeTab === 'placements' && <PlacementsTab data={placementsData} />}
            {activeTab === 'rights' && <RightsTab data={rightsData} expiringContracts={expiringContracts} />}
          </>
        )}
      </div>
    </div>
  )
}

function StatCard({ label, value, subtitle, icon: Icon, color = '#5B8A72', gradient }) {
  return (
    <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-5 relative overflow-hidden">
      <div className={`absolute top-0 left-0 right-0 h-1 ${gradient || 'bg-gradient-to-r from-[#5B8A72] to-[#7BA594]'}`}></div>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-[12px] text-[#7A8580] uppercase tracking-wider mb-1">{label}</p>
          <p className="text-[32px] font-semibold text-[#3D4A44] leading-tight">{value}</p>
          {subtitle && <p className="text-[12px] text-[#7A8580] mt-1">{subtitle}</p>}
        </div>
        {Icon && (
          <div className="p-2 rounded-xl" style={{ backgroundColor: `${color}15` }}>
            <Icon className="w-5 h-5" style={{ color }} />
          </div>
        )}
      </div>
    </div>
  )
}

function ChartCard({ title, children, className = '' }) {
  return (
    <div className={`bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6 ${className}`}>
      <h3 className="text-[18px] font-medium text-[#3D4A44] mb-4">{title}</h3>
      {children}
    </div>
  )
}

function OverviewTab({ overview, growthData, healthData, valuationData }) {
  if (!overview) return null
  const { totals, health, financial, tasks } = overview

  const methodologyData = valuationData?.methodology_breakdown
    ? Object.entries(valuationData.methodology_breakdown)
        .filter(([_, v]) => v > 0)
        .map(([key, value]) => ({
          name: key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
          value,
        }))
    : []

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <StatCard label="Songs" value={totals.songs} icon={MusicalNoteIcon} color="#5B8A72" gradient="bg-gradient-to-r from-[#5B8A72] to-[#7BA594]" />
        <StatCard label="Works" value={totals.works} icon={DocumentTextIcon} color="#5A8A9A" gradient="bg-gradient-to-r from-[#5A8A9A] to-[#7BA5B4]" />
        <StatCard label="Releases" value={totals.releases} icon={RectangleStackIcon} color="#8B6EAE" gradient="bg-gradient-to-r from-[#8B6EAE] to-[#A88EC6]" />
        <StatCard label="Creators" value={totals.creators} icon={UsersIcon} color="#C4956B" gradient="bg-gradient-to-r from-[#C4956B] to-[#D4A57B]" />
        <StatCard label="Contracts" value={totals.contracts} subtitle={`${financial.active_contracts} active`} icon={ShieldCheckIcon} color="#5B9A6E" gradient="bg-gradient-to-r from-[#5B9A6E] to-[#6BAA7E]" />
        <StatCard label="Placements" value={totals.placements} icon={FilmIcon} color="#C47068" gradient="bg-gradient-to-r from-[#C47068] to-[#D4A57B]" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard label="Avg Health Score" value={`${health.avg_score}%`} subtitle={`${health.release_rate}% released`} icon={HeartIcon} color="#5B8A72" />
        <StatCard label="Total Royalty Revenue" value={formatCents(financial.total_royalty_revenue)} icon={CurrencyDollarIcon} color="#5B9A6E" gradient="bg-gradient-to-r from-[#5B9A6E] to-[#6BAA7E]" />
        <StatCard label="Placement Value" value={formatDollars(financial.total_placement_value)} subtitle={`${tasks.pending_actions} pending tasks`} icon={FilmIcon} color="#C4956B" gradient="bg-gradient-to-r from-[#C4956B] to-[#D4A57B]" />
      </div>

      {valuationData && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <StatCard label="Total Catalog Valuation" value={formatCents(valuationData.total_valuation_cents)} icon={CurrencyDollarIcon} color="#8B6EAE" gradient="bg-gradient-to-r from-[#8B6EAE] to-[#A88EC6]" />
          <StatCard label="Songs Valued" value={valuationData.songs_valued || 0} icon={MusicalNoteIcon} color="#5B8A72" gradient="bg-gradient-to-r from-[#5B8A72] to-[#7BA594]" />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {growthData?.timeline?.length > 0 && (
          <ChartCard title="Catalog Growth">
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={growthData.timeline}>
                <CartesianGrid strokeDasharray="3 3" stroke="#EEF1EC" />
                <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#7A8580' }} />
                <YAxis tick={{ fontSize: 11, fill: '#7A8580' }} />
                <Tooltip contentStyle={{ borderRadius: 12, border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }} />
                <Legend />
                <Area type="monotone" dataKey="songs" stackId="1" stroke="#5B8A72" fill="#5B8A72" fillOpacity={0.3} name="Songs" />
                <Area type="monotone" dataKey="works" stackId="1" stroke="#5A8A9A" fill="#5A8A9A" fillOpacity={0.3} name="Works" />
                <Area type="monotone" dataKey="releases" stackId="1" stroke="#8B6EAE" fill="#8B6EAE" fillOpacity={0.3} name="Releases" />
              </AreaChart>
            </ResponsiveContainer>
          </ChartCard>
        )}

        {healthData?.distribution && (
          <ChartCard title="Health Score Distribution">
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie
                  data={healthData.distribution.filter(d => d.value > 0)}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {healthData.distribution.filter(d => d.value > 0).map((entry, i) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ borderRadius: 12, border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }} />
                <Legend formatter={(value) => <span className="text-[12px] text-[#3D4A44]">{value}</span>} />
              </PieChart>
            </ResponsiveContainer>
          </ChartCard>
        )}
      </div>

      {methodologyData.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ChartCard title="Valuation Methodology">
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie
                  data={methodologyData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {methodologyData.map((_, i) => (
                    <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ borderRadius: 12, border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }} />
                <Legend formatter={(value) => <span className="text-[12px] text-[#3D4A44]">{value}</span>} />
              </PieChart>
            </ResponsiveContainer>
          </ChartCard>
          <div className="flex items-center justify-center">
            <Link
              to="/valuation"
              className="inline-flex items-center gap-2 px-6 py-3 bg-[#5B8A72] text-white rounded-[14px] text-[15px] font-medium hover:bg-[#4A7A62] transition-all shadow-sm"
            >
              View Full Valuation
              <ArrowTrendingUpIcon className="w-5 h-5" />
            </Link>
          </div>
        </div>
      )}

      {valuationData && methodologyData.length === 0 && (
        <div className="flex justify-center">
          <Link
            to="/valuation"
            className="inline-flex items-center gap-2 px-6 py-3 bg-[#5B8A72] text-white rounded-[14px] text-[15px] font-medium hover:bg-[#4A7A62] transition-all shadow-sm"
          >
            View Full Valuation
            <ArrowTrendingUpIcon className="w-5 h-5" />
          </Link>
        </div>
      )}
    </div>
  )
}

function HealthTab({ data, growthData }) {
  if (!data) return null

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Missing ISRC" value={data.gaps.missing_isrc} icon={ExclamationTriangleIcon} color="#C47068" gradient="bg-gradient-to-r from-[#C47068] to-[#D48078]" />
        <StatCard label="Missing ISWC" value={data.gaps.missing_iswc} icon={ExclamationTriangleIcon} color="#C4956B" gradient="bg-gradient-to-r from-[#C4956B] to-[#D4A57B]" />
        <StatCard label="No Contract" value={data.gaps.no_contract} icon={ShieldCheckIcon} color="#C47068" gradient="bg-gradient-to-r from-[#C47068] to-[#D48078]" />
        <StatCard label="Not Registered (PRO)" value={data.gaps.not_registered_pro} icon={ExclamationTriangleIcon} color="#C4956B" gradient="bg-gradient-to-r from-[#C4956B] to-[#D4A57B]" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartCard title="Health Score Distribution">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={data.distribution} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#EEF1EC" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 11, fill: '#7A8580' }} />
              <YAxis dataKey="name" type="category" width={130} tick={{ fontSize: 11, fill: '#7A8580' }} />
              <Tooltip contentStyle={{ borderRadius: 12, border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }} />
              <Bar dataKey="value" name="Songs" radius={[0, 6, 6, 0]}>
                {data.distribution.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Catalog Gaps Overview">
          <div className="space-y-4 mt-2">
            {[
              { label: 'Missing ISRC', value: data.gaps.missing_isrc, color: '#C47068' },
              { label: 'Missing ISWC', value: data.gaps.missing_iswc, color: '#C4956B' },
              { label: 'No Executed Contract', value: data.gaps.no_contract, color: '#C47068' },
              { label: 'Not Registered with PRO', value: data.gaps.not_registered_pro, color: '#C4956B' },
            ].map(gap => {
              const total = data.distribution.reduce((s, d) => s + d.value, 0)
              const pct = total > 0 ? (gap.value / total * 100) : 0
              return (
                <div key={gap.label}>
                  <div className="flex justify-between mb-1">
                    <span className="text-[13px] text-[#3D4A44]">{gap.label}</span>
                    <span className="text-[13px] font-medium text-[#3D4A44]">{gap.value} ({pct.toFixed(0)}%)</span>
                  </div>
                  <div className="h-2 bg-[#EEF1EC] rounded-full overflow-hidden">
                    <div className="h-full rounded-full transition-all" style={{ width: `${Math.min(pct, 100)}%`, backgroundColor: gap.color }}></div>
                  </div>
                </div>
              )
            })}
          </div>
        </ChartCard>
      </div>

      {growthData?.timeline?.length > 0 && (
        <ChartCard title="Catalog Growth Over Time">
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={growthData.timeline}>
              <CartesianGrid strokeDasharray="3 3" stroke="#EEF1EC" />
              <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#7A8580' }} />
              <YAxis tick={{ fontSize: 11, fill: '#7A8580' }} />
              <Tooltip contentStyle={{ borderRadius: 12, border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }} />
              <Legend />
              <Line type="monotone" dataKey="songs" stroke="#5B8A72" strokeWidth={2} dot={{ r: 4 }} name="Songs" />
              <Line type="monotone" dataKey="works" stroke="#5A8A9A" strokeWidth={2} dot={{ r: 4 }} name="Works" />
              <Line type="monotone" dataKey="releases" stroke="#8B6EAE" strokeWidth={2} dot={{ r: 4 }} name="Releases" />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>
      )}
    </div>
  )
}

function RevenueTab({ data }) {
  if (!data) return null

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard label="Total Revenue" value={formatCents(data.totals.total_revenue)} icon={CurrencyDollarIcon} color="#5B9A6E" gradient="bg-gradient-to-r from-[#5B9A6E] to-[#6BAA7E]" />
        <StatCard label="Total Paid Out" value={formatCents(data.totals.total_paid)} icon={CheckCircleIcon} color="#5B8A72" gradient="bg-gradient-to-r from-[#5B8A72] to-[#7BA594]" />
        <StatCard label="Unpaid Balance" value={formatCents(data.totals.unpaid)} icon={CurrencyDollarIcon} color="#C4956B" gradient="bg-gradient-to-r from-[#C4956B] to-[#D4A57B]" />
      </div>

      {data.monthly_revenue.length > 0 && (
        <ChartCard title="Monthly Revenue Trend">
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={data.monthly_revenue}>
              <CartesianGrid strokeDasharray="3 3" stroke="#EEF1EC" />
              <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#7A8580' }} />
              <YAxis tick={{ fontSize: 11, fill: '#7A8580' }} tickFormatter={(v) => formatCents(v)} />
              <Tooltip contentStyle={{ borderRadius: 12, border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }} formatter={(v) => formatCents(v)} />
              <Area type="monotone" dataKey="revenue" stroke="#5B9A6E" fill="#5B9A6E" fillOpacity={0.2} strokeWidth={2} name="Revenue" />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {data.top_tracks.length > 0 && (
          <ChartCard title="Top Earning Tracks">
            <div className="space-y-3">
              {data.top_tracks.map((track, i) => (
                <div key={i} className="flex items-center justify-between py-2 border-b border-[#EEF1EC] last:border-0">
                  <div className="flex items-center gap-3">
                    <span className="text-[12px] font-semibold text-[#7A8580] w-6">{i + 1}</span>
                    <div>
                      <p className="text-[14px] font-medium text-[#3D4A44]">{track.title}</p>
                      <p className="text-[12px] text-[#7A8580]">{track.artist}</p>
                    </div>
                  </div>
                  <span className="text-[14px] font-semibold text-[#5B9A6E]">{formatCents(track.revenue)}</span>
                </div>
              ))}
            </div>
          </ChartCard>
        )}

        <div className="space-y-6">
          {data.by_platform.length > 0 && (
            <ChartCard title="Revenue by Platform">
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={data.by_platform}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#EEF1EC" />
                  <XAxis dataKey="platform" tick={{ fontSize: 10, fill: '#7A8580' }} interval={0} angle={-20} textAnchor="end" height={50} />
                  <YAxis tick={{ fontSize: 11, fill: '#7A8580' }} tickFormatter={(v) => formatCents(v)} />
                  <Tooltip contentStyle={{ borderRadius: 12, border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }} formatter={(v) => formatCents(v)} />
                  <Bar dataKey="revenue" fill="#5B8A72" radius={[6, 6, 0, 0]} name="Revenue" />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
          )}

          {data.by_territory.length > 0 && (
            <ChartCard title="Revenue by Territory">
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={data.by_territory}
                    cx="50%"
                    cy="50%"
                    innerRadius={40}
                    outerRadius={75}
                    paddingAngle={2}
                    dataKey="revenue"
                    nameKey="territory"
                  >
                    {data.by_territory.map((_, i) => (
                      <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ borderRadius: 12, border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }} formatter={(v) => formatCents(v)} />
                  <Legend formatter={(value) => <span className="text-[11px] text-[#3D4A44]">{value}</span>} />
                </PieChart>
              </ResponsiveContainer>
            </ChartCard>
          )}
        </div>
      </div>

      {data.monthly_revenue.length === 0 && data.top_tracks.length === 0 && (
        <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-12 text-center">
          <CurrencyDollarIcon className="w-12 h-12 text-[#7A8580] mx-auto mb-3" />
          <p className="text-[17px] text-[#3D4A44] font-medium">No Revenue Data Yet</p>
          <p className="text-[14px] text-[#7A8580] mt-1">Upload royalty statements to see revenue analytics</p>
        </div>
      )}
    </div>
  )
}

function CreatorsTab({ data }) {
  if (!data) return null

  const roleData = Object.entries(data.by_role).map(([role, count]) => ({ name: role, value: count }))
  const proData = Object.entries(data.by_pro).map(([pro, count]) => ({ name: pro, value: count }))

  return (
    <div className="space-y-6">
      <StatCard label="Total Creators" value={data.total_creators} icon={UsersIcon} color="#5B8A72" />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {roleData.length > 0 && (
          <ChartCard title="Creators by Role">
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={roleData}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={85}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {roleData.map((_, i) => (
                    <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ borderRadius: 12, border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }} />
                <Legend formatter={(value) => <span className="text-[12px] text-[#3D4A44]">{value}</span>} />
              </PieChart>
            </ResponsiveContainer>
          </ChartCard>
        )}

        {proData.length > 0 && (
          <ChartCard title="PRO Distribution">
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={proData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#EEF1EC" />
                <XAxis dataKey="name" tick={{ fontSize: 12, fill: '#7A8580' }} />
                <YAxis tick={{ fontSize: 11, fill: '#7A8580' }} />
                <Tooltip contentStyle={{ borderRadius: 12, border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }} />
                <Bar dataKey="value" fill="#5A8A9A" radius={[6, 6, 0, 0]} name="Creators" />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        )}
      </div>

      {data.creators.length > 0 && (
        <ChartCard title="Top Creators">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-[#EEF1EC]">
                  <th className="text-left py-3 px-2 text-[12px] uppercase tracking-wider text-[#7A8580] font-medium">#</th>
                  <th className="text-left py-3 px-2 text-[12px] uppercase tracking-wider text-[#7A8580] font-medium">Creator</th>
                  <th className="text-left py-3 px-2 text-[12px] uppercase tracking-wider text-[#7A8580] font-medium">Roles</th>
                  <th className="text-right py-3 px-2 text-[12px] uppercase tracking-wider text-[#7A8580] font-medium">Songs</th>
                  <th className="text-right py-3 px-2 text-[12px] uppercase tracking-wider text-[#7A8580] font-medium">Works</th>
                  <th className="text-right py-3 px-2 text-[12px] uppercase tracking-wider text-[#7A8580] font-medium">Avg Health</th>
                  <th className="text-right py-3 px-2 text-[12px] uppercase tracking-wider text-[#7A8580] font-medium">Revenue</th>
                </tr>
              </thead>
              <tbody>
                {data.creators.map((c, i) => (
                  <tr key={c.id} className="border-b border-[#EEF1EC] last:border-0 hover:bg-[#FAFBF9] transition-colors">
                    <td className="py-3 px-2 text-[13px] text-[#7A8580]">{i + 1}</td>
                    <td className="py-3 px-2 text-[14px] font-medium text-[#3D4A44]">{c.name}</td>
                    <td className="py-3 px-2">
                      <div className="flex gap-1 flex-wrap">
                        {(c.roles || []).map(r => (
                          <span key={r} className="px-2 py-0.5 bg-[#EEF1EC] rounded-full text-[10px] font-medium text-[#3D4A44]">{r}</span>
                        ))}
                      </div>
                    </td>
                    <td className="py-3 px-2 text-[14px] text-[#3D4A44] text-right">{c.song_count}</td>
                    <td className="py-3 px-2 text-[14px] text-[#3D4A44] text-right">{c.work_count}</td>
                    <td className="py-3 px-2 text-right">
                      <span className={`text-[14px] font-medium ${c.avg_health >= 75 ? 'text-[#5B9A6E]' : c.avg_health >= 50 ? 'text-[#5A8A9A]' : c.avg_health >= 25 ? 'text-[#C4956B]' : 'text-[#C47068]'}`}>
                        {c.avg_health}%
                      </span>
                    </td>
                    <td className="py-3 px-2 text-[14px] font-medium text-[#5B9A6E] text-right">{formatCents(c.total_revenue)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </ChartCard>
      )}

      {data.creators.length === 0 && (
        <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-12 text-center">
          <UsersIcon className="w-12 h-12 text-[#7A8580] mx-auto mb-3" />
          <p className="text-[17px] text-[#3D4A44] font-medium">No Creator Data Yet</p>
          <p className="text-[14px] text-[#7A8580] mt-1">Add creators to your roster to see analytics</p>
        </div>
      )}
    </div>
  )
}

function PlacementsTab({ data }) {
  if (!data) return null

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Total Placements" value={data.totals.total} icon={FilmIcon} color="#5B8A72" />
        <StatCard label="Total Value" value={formatDollars(data.totals.total_value)} icon={CurrencyDollarIcon} color="#5B9A6E" gradient="bg-gradient-to-r from-[#5B9A6E] to-[#6BAA7E]" />
        <StatCard label="Conversion Rate" value={`${data.totals.conversion_rate}%`} icon={ArrowTrendingUpIcon} color="#5A8A9A" gradient="bg-gradient-to-r from-[#5A8A9A] to-[#7BA5B4]" />
        <StatCard label="Paid Value" value={formatDollars(data.totals.paid_value)} icon={CheckCircleIcon} color="#5B8A72" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {data.funnel.length > 0 && (
          <ChartCard title="Placement Pipeline Funnel">
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={data.funnel} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#EEF1EC" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 11, fill: '#7A8580' }} />
                <YAxis dataKey="stage" type="category" width={120} tick={{ fontSize: 11, fill: '#7A8580' }} />
                <Tooltip contentStyle={{ borderRadius: 12, border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }} />
                <Bar dataKey="count" name="Placements" radius={[0, 6, 6, 0]}>
                  {data.funnel.map((_, i) => (
                    <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        )}

        {data.by_type.length > 0 && (
          <ChartCard title="Revenue by Placement Type">
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={data.by_type}>
                <CartesianGrid strokeDasharray="3 3" stroke="#EEF1EC" />
                <XAxis dataKey="type" tick={{ fontSize: 10, fill: '#7A8580' }} interval={0} angle={-15} textAnchor="end" height={50} />
                <YAxis tick={{ fontSize: 11, fill: '#7A8580' }} tickFormatter={(v) => formatDollars(v)} />
                <Tooltip contentStyle={{ borderRadius: 12, border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }} formatter={(v) => formatDollars(v)} />
                <Bar dataKey="value" fill="#C4956B" radius={[6, 6, 0, 0]} name="Value" />
                <Bar dataKey="count" fill="#5B8A72" radius={[6, 6, 0, 0]} name="Count" />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        )}
      </div>

      {data.monthly_activity.length > 0 && (
        <ChartCard title="Placement Activity Over Time">
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={data.monthly_activity}>
              <CartesianGrid strokeDasharray="3 3" stroke="#EEF1EC" />
              <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#7A8580' }} />
              <YAxis tick={{ fontSize: 11, fill: '#7A8580' }} />
              <Tooltip contentStyle={{ borderRadius: 12, border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }} />
              <Line type="monotone" dataKey="count" stroke="#5B8A72" strokeWidth={2} dot={{ r: 4 }} name="Placements" />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>
      )}

      {data.totals.total === 0 && (
        <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-12 text-center">
          <FilmIcon className="w-12 h-12 text-[#7A8580] mx-auto mb-3" />
          <p className="text-[17px] text-[#3D4A44] font-medium">No Placements Yet</p>
          <p className="text-[14px] text-[#7A8580] mt-1">Create placements to track your sync licensing pipeline</p>
        </div>
      )}
    </div>
  )
}

function RightsTab({ data, expiringContracts }) {
  if (!data) return null

  const statusData = Object.entries(data.contracts_by_status).map(([s, c]) => ({ name: s, value: c }))
  const typeData = Object.entries(data.contracts_by_type).map(([t, c]) => ({ name: t, value: c }))

  const coverageMetrics = [
    { label: 'Contract Coverage', value: data.coverage.contract_coverage_rate, count: data.coverage.songs_with_contracts, total: data.coverage.total_songs, color: '#5B8A72' },
    { label: 'Rights Splits Defined', value: data.coverage.splits_coverage_rate, count: data.coverage.songs_with_splits, total: data.coverage.total_songs, color: '#5A8A9A' },
  ]

  const getDaysColor = (days) => {
    if (days < 30) return 'text-[#C47068]'
    if (days < 60) return 'text-[#C4956B]'
    if (days < 90) return 'text-[#B5A642]'
    return 'text-[#3D4A44]'
  }

  const contracts = expiringContracts?.contracts || expiringContracts || []

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard label="Total Songs" value={data.coverage.total_songs} icon={MusicalNoteIcon} color="#5B8A72" />
        <StatCard label="Songs with Contracts" value={data.coverage.songs_with_contracts} subtitle={`${data.coverage.contract_coverage_rate}% coverage`} icon={ShieldCheckIcon} color="#5B9A6E" gradient="bg-gradient-to-r from-[#5B9A6E] to-[#6BAA7E]" />
        <StatCard label="Expiring Soon" value={data.expiring_soon} subtitle="Within 90 days" icon={ExclamationTriangleIcon} color="#C47068" gradient="bg-gradient-to-r from-[#C47068] to-[#D48078]" />
      </div>

      <ChartCard title="Rights Coverage">
        <div className="space-y-6">
          {coverageMetrics.map(metric => (
            <div key={metric.label}>
              <div className="flex justify-between mb-2">
                <span className="text-[14px] text-[#3D4A44] font-medium">{metric.label}</span>
                <span className="text-[14px] text-[#7A8580]">{metric.count} / {metric.total} songs ({metric.value}%)</span>
              </div>
              <div className="h-3 bg-[#EEF1EC] rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{ width: `${Math.min(metric.value, 100)}%`, backgroundColor: metric.color }}
                ></div>
              </div>
            </div>
          ))}
        </div>
      </ChartCard>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {statusData.length > 0 && (
          <ChartCard title="Contracts by Status">
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={statusData}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={85}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {statusData.map((_, i) => (
                    <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ borderRadius: 12, border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }} />
                <Legend formatter={(value) => <span className="text-[12px] text-[#3D4A44]">{value}</span>} />
              </PieChart>
            </ResponsiveContainer>
          </ChartCard>
        )}

        {typeData.length > 0 && (
          <ChartCard title="Contracts by Type">
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={typeData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#EEF1EC" />
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#7A8580' }} />
                <YAxis tick={{ fontSize: 11, fill: '#7A8580' }} />
                <Tooltip contentStyle={{ borderRadius: 12, border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }} />
                <Bar dataKey="value" fill="#5B8A72" radius={[6, 6, 0, 0]} name="Contracts" />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        )}
      </div>

      <ChartCard title="Contracts Expiring Soon">
        {Array.isArray(contracts) && contracts.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-[#EEF1EC]">
                  <th className="text-left py-3 px-2 text-[12px] uppercase tracking-wider text-[#7A8580] font-medium">Contract</th>
                  <th className="text-left py-3 px-2 text-[12px] uppercase tracking-wider text-[#7A8580] font-medium">Type</th>
                  <th className="text-left py-3 px-2 text-[12px] uppercase tracking-wider text-[#7A8580] font-medium">End Date</th>
                  <th className="text-right py-3 px-2 text-[12px] uppercase tracking-wider text-[#7A8580] font-medium">Days Remaining</th>
                  <th className="text-right py-3 px-2 text-[12px] uppercase tracking-wider text-[#7A8580] font-medium">Assets</th>
                </tr>
              </thead>
              <tbody>
                {contracts.map((contract, i) => (
                  <tr key={contract.id || i} className="border-b border-[#EEF1EC] last:border-0 hover:bg-[#FAFBF9] transition-colors">
                    <td className="py-3 px-2 text-[14px] font-medium text-[#3D4A44]">{contract.name || contract.contract_name || 'Untitled'}</td>
                    <td className="py-3 px-2 text-[13px] text-[#7A8580]">{contract.type || contract.contract_type || '—'}</td>
                    <td className="py-3 px-2 text-[13px] text-[#3D4A44]">{contract.end_date ? new Date(contract.end_date).toLocaleDateString() : '—'}</td>
                    <td className={`py-3 px-2 text-[14px] font-semibold text-right ${getDaysColor(contract.days_remaining)}`}>
                      {contract.days_remaining != null ? contract.days_remaining : '—'}
                    </td>
                    <td className="py-3 px-2 text-[14px] text-[#3D4A44] text-right">{contract.asset_count ?? contract.assets ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-8 text-center">
            <ShieldCheckIcon className="w-10 h-10 text-[#7A8580] mx-auto mb-2" />
            <p className="text-[15px] text-[#3D4A44] font-medium">No Contracts Expiring Soon</p>
            <p className="text-[13px] text-[#7A8580] mt-1">All contracts are in good standing</p>
          </div>
        )}
      </ChartCard>
    </div>
  )
}
