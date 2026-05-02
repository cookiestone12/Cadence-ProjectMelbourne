import React, { useState, useEffect, useCallback, useRef } from 'react'
import axios from 'axios'
import {
  BanknotesIcon,
  ArrowUpTrayIcon,
  DocumentTextIcon,
  ChartBarIcon,
  CurrencyDollarIcon,
  XMarkIcon,
  TrashIcon,
  EyeIcon,
  ArrowPathIcon,
  CalculatorIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  ClockIcon,
  PlusIcon,
  MagnifyingGlassIcon,
  ChevronRightIcon,
  ArrowLeftIcon,
  UserGroupIcon,
  MusicalNoteIcon,
  DocumentDuplicateIcon,
  ShareIcon,
  PencilSquareIcon
} from '@heroicons/react/24/outline'
import { CheckCircleIcon as CheckCircleSolid } from '@heroicons/react/24/solid'
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell
} from 'recharts'
import ShareModal from '../components/ShareModal'
import ProcessingInboxPanel from '../components/ProcessingInboxPanel'
import StatementDetailView from '../components/StatementDetailView'
import PayablesTab from '../components/PayablesTab'
import RoyaltyAnalyticsDashboard from '../components/RoyaltyAnalyticsDashboard'
import DeleteStatementDialog from '../components/DeleteStatementDialog'

const TABS = [
  { key: 'dashboard', label: 'Dashboard', icon: ChartBarIcon },
  { key: 'processing', label: 'Processing', icon: ArrowPathIcon },
  { key: 'statements', label: 'Statements', icon: DocumentTextIcon },
  { key: 'earnings', label: 'Earnings', icon: CurrencyDollarIcon },
  { key: 'analytics', label: 'Analytics', icon: ChartBarIcon },
  { key: 'money_out', label: 'Money Out', icon: ArrowUpTrayIcon },
  { key: 'fees', label: 'Fees & Advances', icon: CalculatorIcon },
  { key: 'payables', label: 'Payables', icon: BanknotesIcon },
]

const STATEMENT_STATUS_COLORS = {
  PENDING: { bg: 'bg-amber-100', text: 'text-amber-700' },
  PROCESSING: { bg: 'bg-blue-100', text: 'text-blue-700' },
  PROCESSED: { bg: 'bg-green-100', text: 'text-green-700' },
  FAILED: { bg: 'bg-red-100', text: 'text-red-700' },
  PARTIALLY_MATCHED: { bg: 'bg-orange-100', text: 'text-orange-700' },
}

const PAYMENT_STATUS_COLORS = {
  PENDING: { bg: 'bg-amber-100', text: 'text-amber-700' },
  APPROVED: { bg: 'bg-blue-100', text: 'text-blue-700' },
  PAID: { bg: 'bg-green-100', text: 'text-green-700' },
  CANCELLED: { bg: 'bg-red-100', text: 'text-red-700' },
}

const CURRENCIES = ['USD', 'EUR', 'GBP', 'CAD', 'AUD', 'JPY']

const TARGET_FIELDS = [
  { value: '', label: '— Skip —' },
  { value: 'track_title', label: 'Track / Work Title' },
  { value: 'artist', label: 'Artist / Writer' },
  { value: 'isrc', label: 'ISRC' },
  { value: 'upc', label: 'UPC' },
  { value: 'iswc', label: 'ISWC' },
  { value: 'revenue', label: 'Revenue / Amount' },
  { value: 'quantity', label: 'Quantity / Performances' },
  { value: 'territory', label: 'Territory' },
  { value: 'platform', label: 'Platform / Licensee' },
  { value: 'revenue_type', label: 'Revenue / Rights Type' },
  { value: 'publisher', label: 'Publisher' },
  { value: 'work_id', label: 'Work ID / Song Code' },
  { value: 'share_percentage', label: 'Share %' },
]

// Aligned with backend/config/statement_formats.py StatementSourceType
// + DROPDOWN_ORDER. Add new source types in the backend registry first,
// then mirror them here.
const SOURCE_TYPE_OPTIONS = [
  { value: '', label: 'Auto-detect' },
  { value: 'DSP', label: 'DSP / Distributor (Spotify, Apple Music, DistroKid, etc.)' },
  { value: 'BMI', label: 'BMI' },
  { value: 'ASCAP', label: 'ASCAP' },
  { value: 'SESAC', label: 'SESAC' },
  { value: 'MLC', label: 'MLC (Mechanical Licensing Collective)' },
  { value: 'HARRY_FOX', label: 'Harry Fox Agency' },
  { value: 'LABEL', label: 'Label / Publisher Statement' },
  { value: 'SOUNDEXCHANGE', label: 'SoundExchange' },
  { value: 'SOCAN', label: 'SOCAN' },
  { value: 'PRS', label: 'PRS for Music' },
  { value: 'OTHER_PRO', label: 'Other PRO' },
  { value: 'OTHER', label: 'Other' },
]

const CHART_COLORS = ['#5B8A72', '#7BA594', '#9BBFAA', '#A8C4B8', '#C4D9CE', '#5A8A9A', '#8BB0BE']

const formatCents = (cents) => {
  if (cents == null) return '$0.00'
  return (cents / 100).toLocaleString('en-US', { style: 'currency', currency: 'USD' })
}

const formatDollars = (val) => {
  if (val == null) return '$0.00'
  return Number(val).toLocaleString('en-US', { style: 'currency', currency: 'USD' })
}

const formatDate = (dateStr) => {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

const StatusBadge = ({ status, colorMap }) => {
  const colors = colorMap[status] || { bg: 'bg-gray-100', text: 'text-gray-700' }
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colors.bg} ${colors.text}`}>
      {status}
    </span>
  )
}

function DashboardTab({ orgId, creatorId }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [expenseSummary, setExpenseSummary] = useState(null)

  useEffect(() => {
    if (!orgId) return
    setLoading(true)
    const url = creatorId ? `/api/royalties/dashboard/${orgId}?creator_id=${creatorId}` : `/api/royalties/dashboard/${orgId}`
    axios.get(url)
      .then(res => setData(res.data))
      .catch(err => console.error('Dashboard load error:', err))
      .finally(() => setLoading(false))
    axios.get(`/api/expenses/org/${orgId}/summary`)
      .then(res => setExpenseSummary(res.data))
      .catch(err => console.error('Expense summary load error:', err))
  }, [orgId, creatorId])

  if (loading) return <LoadingSpinner message="Loading dashboard..." />
  if (!data) return <EmptyState icon={ChartBarIcon} title="No Dashboard Data" message="Upload royalty statements to see your dashboard." />

  const revenueBySource = (data.revenue_by_source || []).map(s => ({
    name: s.source || s.name || 'Unknown',
    revenue: s.total_dollars || (s.total_cents || 0) / 100
  }))
  const topTracks = data.top_earning_tracks || data.top_tracks || []
  const revenueOverTime = (data.revenue_by_period || []).map(r => ({
    period: r.period_start || r.period || '',
    revenue: r.total_dollars || (r.total_cents || 0) / 100,
    source: r.source || ''
  }))
  const advances = data.recoupment_status || data.contracts_with_advances || []

  const statementsCount = (data.recent_statements || []).length
  const sourcesCount = (data.revenue_by_source || []).length

  const summaryCards = [
    { label: 'Total Revenue', value: formatCents(data.total_revenue_cents), icon: CurrencyDollarIcon, accent: true },
    { label: 'Statements', value: String(statementsCount), icon: DocumentDuplicateIcon },
    { label: 'Sources', value: String(sourcesCount), icon: CheckCircleIcon },
    { label: 'Money Out', value: formatCents(expenseSummary?.total_amount_cents || 0), icon: ArrowUpTrayIcon },
  ]

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {summaryCards.map((card, i) => (
          <div key={i} className={`${card.accent ? 'bg-gradient-to-br from-[rgba(91,138,114,0.08)] to-[rgba(123,165,148,0.08)] border-[rgba(91,138,114,0.15)]' : 'bg-white/80 border-[rgba(59,77,67,0.08)]'} backdrop-blur-xl rounded-[18px] shadow-am p-5 border`}>
            <div className="flex items-center gap-3 mb-3">
              <div className={`p-2 ${card.accent ? 'bg-gradient-to-r from-[#5B8A72] to-[#7BA594]' : 'bg-[rgba(91,138,114,0.1)]'} rounded-lg`}>
                <card.icon className={`w-5 h-5 ${card.accent ? 'text-white' : 'text-[#5B8A72]'}`} />
              </div>
              <span className="text-sm font-medium text-[#7A8580]">{card.label}</span>
            </div>
            <div className={`text-2xl font-bold ${card.accent ? 'bg-gradient-to-r from-[#5B8A72] to-[#7BA594] bg-clip-text text-transparent' : 'text-[#3D4A44]'}`}>
              {card.value}
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {revenueBySource.length > 0 && (
          <div className="bg-white/80 backdrop-blur-xl rounded-[18px] shadow-am p-6 border border-[rgba(59,77,67,0.08)]">
            <h3 className="text-lg font-semibold text-[#3D4A44] mb-4">Revenue by Source</h3>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={revenueBySource}>
                <CartesianGrid strokeDasharray="3 3" stroke="#EEF1EC" />
                <XAxis dataKey="name" tick={{ fontSize: 12, fill: '#7A8580' }} />
                <YAxis tick={{ fontSize: 12, fill: '#7A8580' }} tickFormatter={v => `$${v.toLocaleString()}`} />
                <Tooltip formatter={(v) => formatDollars(v)} />
                <Bar dataKey="revenue" radius={[6, 6, 0, 0]}>
                  {revenueBySource.map((_, idx) => (
                    <Cell key={idx} fill={CHART_COLORS[idx % CHART_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {revenueOverTime.length > 0 && (
          <div className="bg-white/80 backdrop-blur-xl rounded-[18px] shadow-am p-6 border border-[rgba(59,77,67,0.08)]">
            <h3 className="text-lg font-semibold text-[#3D4A44] mb-4">Revenue Over Time</h3>
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={revenueOverTime}>
                <CartesianGrid strokeDasharray="3 3" stroke="#EEF1EC" />
                <XAxis dataKey="period" tick={{ fontSize: 12, fill: '#7A8580' }} />
                <YAxis tick={{ fontSize: 12, fill: '#7A8580' }} tickFormatter={v => `$${v.toLocaleString()}`} />
                <Tooltip formatter={(v) => formatDollars(v)} />
                <Line type="monotone" dataKey="revenue" stroke="#5B8A72" strokeWidth={2} dot={{ fill: '#5B8A72', r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {topTracks.length > 0 && (
        <div className="bg-white/80 backdrop-blur-xl rounded-[18px] shadow-am border border-[rgba(59,77,67,0.08)]">
          <div className="p-6 border-b border-[rgba(59,77,67,0.08)]">
            <h3 className="text-lg font-semibold text-[#3D4A44]">Top Earning Tracks</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-[#EEF1EC]">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">#</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Track</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Artist</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-[#7A8580] uppercase">Revenue</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-[#7A8580] uppercase">Streams</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[rgba(59,77,67,0.06)]">
                {topTracks.slice(0, 10).map((track, i) => (
                  <tr key={i} className="hover:bg-[rgba(91,138,114,0.04)]">
                    <td className="px-6 py-3 text-sm text-[#7A8580]">{i + 1}</td>
                    <td className="px-6 py-3 text-sm font-medium text-[#3D4A44]">
                      {track.title}
                      {track.unmatched && <span className="ml-2 px-1.5 py-0.5 text-[10px] font-medium bg-[#F5E6D3] text-[#C4956B] rounded">Unmatched</span>}
                    </td>
                    <td className="px-6 py-3 text-sm text-[#7A8580]">{track.artist}</td>
                    <td className="px-6 py-3 text-sm text-right font-medium text-[#3D4A44]">{formatCents(track.total_revenue_cents)}</td>
                    <td className="px-6 py-3 text-sm text-right text-[#7A8580]">{(track.total_quantity || 0).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {advances.length > 0 && (
        <div className="bg-white/80 backdrop-blur-xl rounded-[18px] shadow-am p-6 border border-[rgba(59,77,67,0.08)]">
          <h3 className="text-lg font-semibold text-[#3D4A44] mb-4">Contracts with Advances</h3>
          <div className="space-y-4">
            {advances.map((adv, i) => {
              const advance = adv.advance_amount || 0
              const recouped = adv.advance_recouped || 0
              const pct = adv.percentage_recouped || (advance > 0 ? Math.min((recouped / advance) * 100, 100) : 0)
              return (
                <div key={i} className="border border-[rgba(59,77,67,0.08)] rounded-xl p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-[#3D4A44]">{adv.title || adv.contract_title}</span>
                    <span className="text-xs text-[#7A8580]">{formatDollars(recouped)} / {formatDollars(advance)}</span>
                  </div>
                  <div className="w-full bg-[#EEF1EC] rounded-full h-2.5">
                    <div
                      className="h-2.5 rounded-full bg-gradient-to-r from-[#5B8A72] to-[#7BA594] transition-all"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <div className="text-right mt-1">
                    <span className="text-xs text-[#7A8580]">{pct.toFixed(1)}% recouped</span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

function StatementsTab({ orgId, songs, selectedCreatorId }) {
  const [statements, setStatements] = useState([])
  const [loading, setLoading] = useState(true)
  const [showUpload, setShowUpload] = useState(false)
  const [shareStatement, setShareStatement] = useState(null)
  const [selectedStatement, setSelectedStatement] = useState(null)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [selectedIds, setSelectedIds] = useState(() => new Set())
  const [bulkDeleteOpen, setBulkDeleteOpen] = useState(false)
  const [transactions, setTransactions] = useState([])
  const [txLoading, setTxLoading] = useState(false)
  const [uploadStep, setUploadStep] = useState(1)
  const [uploadFile, setUploadFile] = useState(null)
  const [uploadSource, setUploadSource] = useState('')
  const [uploadPeriodStart, setUploadPeriodStart] = useState('')
  const [uploadPeriodEnd, setUploadPeriodEnd] = useState('')
  const [uploadCurrency, setUploadCurrency] = useState('USD')
  const [uploadSourceType, setUploadSourceType] = useState('')
  const [detectedSourceType, setDetectedSourceType] = useState(null)
  const [previewData, setPreviewData] = useState(null)
  const [columnMappings, setColumnMappings] = useState({})
  const [uploading, setUploading] = useState(false)
  const [uploadResult, setUploadResult] = useState(null)
  const [matchingSongId, setMatchingSongId] = useState({})
  const [songSearchTerm, setSongSearchTerm] = useState({})
  const [songDropdownOpen, setSongDropdownOpen] = useState({})
  const [calculating, setCalculating] = useState({})
  const [txPage, setTxPage] = useState(0)
  const [txTotal, setTxTotal] = useState(0)
  const txPerPage = 50

  const [showBulkUpload, setShowBulkUpload] = useState(false)
  // Task #191 — per-file rows with overrides + per-file preview/mapping.
  // Each row: { id, file, source_type, source_name, period_start,
  // period_end, creator_id, preview, previewLoading, previewError,
  // mapping (canonical_field -> header), unmappedHeaders, mappingConfident,
  // mappingReviewed, status, error, result, duplicate }
  const [bulkRows, setBulkRows] = useState([])
  const [bulkSource, setBulkSource] = useState('')
  const [bulkSourceType, setBulkSourceType] = useState('')
  const [bulkPeriodStart, setBulkPeriodStart] = useState('')
  const [bulkPeriodEnd, setBulkPeriodEnd] = useState('')
  const [bulkCurrency, setBulkCurrency] = useState('USD')
  const [bulkCreatorId, setBulkCreatorId] = useState('')
  const [bulkCreatorOptions, setBulkCreatorOptions] = useState([])
  const [bulkStep, setBulkStep] = useState(1)
  const [bulkProcessing, setBulkProcessing] = useState(false)
  const [bulkCurrentIndex, setBulkCurrentIndex] = useState(-1)
  const [bulkMappingReviewIdx, setBulkMappingReviewIdx] = useState(-1)
  const [bulkDuplicatePrompt, setBulkDuplicatePrompt] = useState(null)
  const bulkDuplicateResolver = useRef(null)
  const bulkApplyChoiceRef = useRef(null) // 'skip' | 'overwrite' | null
  const bulkCancelRef = useRef(false)

  const [editStmt, setEditStmt] = useState(null)
  const [editForm, setEditForm] = useState({ source_name: '', source_type: '', period_start: '', period_end: '', currency: 'USD', creator_id: '' })
  const [editSaving, setEditSaving] = useState(false)
  const [editError, setEditError] = useState(null)
  const [editCreatorOptions, setEditCreatorOptions] = useState([])
  const [canEditStatements, setCanEditStatements] = useState(false)

  useEffect(() => {
    let alive = true
    axios.get('/api/organizations/current/membership')
      .then(res => {
        if (!alive) return
        const role = res.data?.role
        setCanEditStatements(role === 'OWNER' || role === 'ADMIN' || role === 'MEMBER')
      })
      .catch(() => { if (alive) setCanEditStatements(false) })
    return () => { alive = false }
  }, [])

  const openEditStatement = (stmt) => {
    setEditStmt(stmt)
    setEditForm({
      source_name: stmt.source_name || '',
      source_type: stmt.source_type || '',
      period_start: stmt.period_start || '',
      period_end: stmt.period_end || '',
      currency: stmt.currency || 'USD',
      creator_id: stmt.creator_id != null ? String(stmt.creator_id) : '',
    })
    setEditError(null)
    // Lazy-load creator options for the assignee dropdown.
    if (orgId && editCreatorOptions.length === 0) {
      axios.get(`/api/creators/org/${orgId}`)
        .then(res => setEditCreatorOptions(Array.isArray(res.data) ? res.data : []))
        .catch(() => setEditCreatorOptions([]))
    }
  }

  const closeEditStatement = () => {
    if (editSaving) return
    setEditStmt(null)
    setEditError(null)
  }

  const submitEditStatement = async () => {
    if (!editStmt) return
    if (editForm.period_start && editForm.period_end && editForm.period_start > editForm.period_end) {
      setEditError('Period start must be on or before period end.')
      return
    }
    setEditSaving(true)
    setEditError(null)
    try {
      const body = {
        source_name: editForm.source_name || null,
        source_type: editForm.source_type || null,
        period_start: editForm.period_start || null,
        period_end: editForm.period_end || null,
        currency: editForm.currency || null,
        creator_id: editForm.creator_id === '' ? null : Number(editForm.creator_id),
      }
      await axios.patch(`/api/royalties/statements/${orgId}/${editStmt.id}`, body)
      setEditStmt(null)
      loadStatements()
    } catch (err) {
      setEditError(err.response?.data?.detail || err.message || 'Failed to save changes.')
    } finally {
      setEditSaving(false)
    }
  }

  const loadStatements = useCallback(async () => {
    if (!orgId) return
    try {
      const params = new URLSearchParams()
      if (selectedCreatorId) params.append('creator_id', selectedCreatorId)
      const qs = params.toString()
      const res = await axios.get(`/api/royalties/statements/${orgId}${qs ? `?${qs}` : ''}`)
      setStatements(Array.isArray(res.data) ? res.data : res.data.statements || [])
    } catch (err) {
      console.error('Failed to load statements:', err)
    } finally {
      setLoading(false)
    }
  }, [orgId, selectedCreatorId])

  useEffect(() => { loadStatements() }, [loadStatements])

  useEffect(() => {
    if (statements.length === 0) return
    const present = new Set(statements.map(s => s.id))
    setSelectedIds(prev => {
      let changed = false
      const next = new Set()
      prev.forEach(id => { if (present.has(id)) next.add(id); else changed = true })
      return changed ? next : prev
    })
  }, [statements])

  const loadTransactions = async (stmt, page = 0) => {
    setSelectedStatement(stmt)
    setTxLoading(true)
    setTxPage(page)
    try {
      const skip = page * txPerPage
      const res = await axios.get(`/api/royalties/statements/${orgId}/${stmt.id}/transactions?skip=${skip}&limit=${txPerPage}`)
      setTransactions(Array.isArray(res.data) ? res.data : res.data.transactions || [])
      setTxTotal(res.data.total || 0)
    } catch (err) {
      console.error('Failed to load transactions:', err)
    } finally {
      setTxLoading(false)
    }
  }

  const handlePreview = async () => {
    if (!uploadFile) return
    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', uploadFile)
      formData.append('source_name', uploadSourceType || uploadSource)
      const res = await axios.post(`/api/royalties/statements/${orgId}/preview`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      setPreviewData(res.data)
      if (res.data.detected_source_type) {
        setDetectedSourceType(res.data.detected_source_type)
      }
      const rawMapping = res.data.mapping || res.data.suggested_mappings || res.data.mappings || {}
      const inverted = {}
      Object.entries(rawMapping).forEach(([field, header]) => {
        if (header) inverted[header] = field
      })
      setColumnMappings(inverted)
      setUploadStep(2)
    } catch (err) {
      console.error('Preview failed:', err)
      alert(err.response?.data?.detail || 'Failed to preview file. Please check the format.')
    } finally {
      setUploading(false)
    }
  }

  const handleUpload = async () => {
    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', uploadFile)
      formData.append('source_name', uploadSource || uploadSourceType)
      formData.append('source_type', detectedSourceType || uploadSourceType || '')
      formData.append('period_start', uploadPeriodStart)
      formData.append('period_end', uploadPeriodEnd)
      formData.append('currency', uploadCurrency)
      const backendMapping = {}
      Object.entries(columnMappings).forEach(([header, field]) => {
        if (field) backendMapping[field] = header
      })
      formData.append('column_mapping', JSON.stringify(backendMapping))
      const res = await axios.post(`/api/royalties/statements/${orgId}/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      setUploadResult(res.data)
      setUploadStep(3)
      loadStatements()
    } catch (err) {
      console.error('Upload failed:', err)
      alert('Failed to upload statement.')
    } finally {
      setUploading(false)
    }
  }

  const handleDelete = (stmt) => {
    setDeleteTarget(stmt)
  }

  const handleDeleted = () => {
    const removedId = deleteTarget?.id
    loadStatements()
    if (removedId && selectedStatement?.id === removedId) setSelectedStatement(null)
    if (removedId) {
      setSelectedIds(prev => {
        if (!prev.has(removedId)) return prev
        const next = new Set(prev)
        next.delete(removedId)
        return next
      })
    }
  }

  const toggleSelected = (id) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id); else next.add(id)
      return next
    })
  }

  const visibleStatementIds = statements.map(s => s.id)
  const allVisibleSelected = visibleStatementIds.length > 0 && visibleStatementIds.every(id => selectedIds.has(id))
  const someVisibleSelected = visibleStatementIds.some(id => selectedIds.has(id)) && !allVisibleSelected

  const toggleSelectAllVisible = () => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (allVisibleSelected) {
        visibleStatementIds.forEach(id => next.delete(id))
      } else {
        visibleStatementIds.forEach(id => next.add(id))
      }
      return next
    })
  }

  const handleBulkDeleted = () => {
    setSelectedIds(new Set())
    setBulkDeleteOpen(false)
    loadStatements()
    if (selectedStatement && selectedIds.has(selectedStatement.id)) setSelectedStatement(null)
  }

  const handleManualMatch = async (txId) => {
    const songId = matchingSongId[txId]
    if (!songId) return
    try {
      await axios.post(`/api/royalties/statements/${orgId}/${selectedStatement.id}/match/${txId}`, { song_id: parseInt(songId) })
      loadTransactions(selectedStatement)
    } catch (err) {
      console.error('Match failed:', err)
    }
  }

  const handleRematch = async (stmtId) => {
    try {
      await axios.post(`/api/royalties/statements/${orgId}/${stmtId}/rematch`)
      if (selectedStatement?.id === stmtId) loadTransactions(selectedStatement)
      loadStatements()
    } catch (err) {
      console.error('Rematch failed:', err)
    }
  }

  const handleCalculate = async (stmtId) => {
    setCalculating(prev => ({ ...prev, [stmtId]: true }))
    try {
      await axios.post(`/api/royalties/calculate/${orgId}/${stmtId}`)
      loadStatements()
    } catch (err) {
      console.error('Calculate failed:', err)
    } finally {
      setCalculating(prev => ({ ...prev, [stmtId]: false }))
    }
  }

  const resetUpload = () => {
    setShowUpload(false)
    setUploadStep(1)
    setUploadFile(null)
    setUploadSource('')
    setUploadSourceType('')
    setDetectedSourceType(null)
    setUploadPeriodStart('')
    setUploadPeriodEnd('')
    setUploadCurrency('USD')
    setPreviewData(null)
    setColumnMappings({})
    setUploadResult(null)
  }

  const resetBulkUpload = () => {
    setShowBulkUpload(false)
    setBulkStep(1)
    setBulkRows([])
    setBulkSource('')
    setBulkSourceType('')
    setBulkPeriodStart('')
    setBulkPeriodEnd('')
    setBulkCurrency('USD')
    setBulkCreatorId('')
    setBulkProcessing(false)
    setBulkCurrentIndex(-1)
    setBulkMappingReviewIdx(-1)
    setBulkDuplicatePrompt(null)
    bulkDuplicateResolver.current = null
    bulkApplyChoiceRef.current = null
    bulkCancelRef.current = false
  }

  // Task #191 — fetch preview for a single bulk row so we can pre-fill
  // detected source type / source name / mapping confidence without making
  // the user babysit each file. Mirrors the single-flow handlePreview but
  // writes its results into a single row of bulkRows.
  const previewBulkRow = useCallback(async (rowId, file, sourceName) => {
    setBulkRows(prev => prev.map(r => r.id === rowId ? { ...r, previewLoading: true, previewError: null } : r))
    try {
      const fd = new FormData()
      fd.append('file', file)
      if (sourceName) fd.append('source_name', sourceName)
      const res = await axios.post(`/api/royalties/statements/${orgId}/preview`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      const data = res.data || {}
      // Backend returns mapping as {canonical_field: header}
      const mapping = data.mapping || data.suggested_mappings || data.mappings || {}
      const filtered = {}
      Object.entries(mapping).forEach(([field, header]) => { if (header) filtered[field] = header })
      const detected = data.detected_source_type || null
      const confident = data.mapping_confident !== false  // treat undefined as confident
      const unmapped = Array.isArray(data.unmapped_headers) ? data.unmapped_headers : []
      const detectedStart = data.detected_period_start || ''
      const detectedEnd = data.detected_period_end || ''
      setBulkRows(prev => prev.map(r => {
        if (r.id !== rowId) return r
        return {
          ...r,
          previewLoading: false,
          preview: data,
          mapping: filtered,
          mappingConfident: confident,
          unmappedHeaders: unmapped,
          // Pre-fill source_type / period from detector when the row hasn't set it.
          // Period precedence: row override (operator typed) > PDF/filename detected
          // > batch default. Mirrors how the single-flow upload prefills the
          // operator's editable period field.
          source_type: r.source_type || detected || '',
          source_name: r.source_name || detected || sourceName || '',
          period_start: r.period_start || detectedStart || '',
          period_end: r.period_end || detectedEnd || '',
          // Reflect the new mapping confidence in the row's progress
          // status so the UI can render an explicit `needs_review` chip
          // before the operator hits Upload (vs. silently auto-confirming).
          status: confident ? (r.status === 'needs_review' ? 'pending' : r.status) : 'needs_review',
        }
      }))
    } catch (err) {
      setBulkRows(prev => prev.map(r => r.id === rowId
        ? { ...r, previewLoading: false, previewError: err.response?.data?.detail || err.message || 'Preview failed' }
        : r))
    }
  }, [orgId])

  // Add files to the row table and kick off previews in parallel.
  const handleBulkFilesChange = (files) => {
    const arr = Array.from(files || [])
    if (arr.length === 0) return
    const next = arr.map((file, idx) => ({
      id: `${Date.now()}_${idx}_${file.name}`,
      file,
      source_type: bulkSourceType || '',
      source_name: bulkSource || '',
      period_start: bulkPeriodStart || '',
      period_end: bulkPeriodEnd || '',
      creator_id: bulkCreatorId || '',
      preview: null,
      previewLoading: false,
      previewError: null,
      mapping: null,
      unmappedHeaders: [],
      mappingConfident: true,
      mappingReviewed: false,
      status: 'pending',
      error: null,
      result: null,
      duplicate: null,
    }))
    setBulkRows(prev => [...prev, ...next])
    next.forEach(row => previewBulkRow(row.id, row.file, row.source_name || row.source_type || bulkSource || bulkSourceType))
  }

  const removeBulkRow = (rowId) => {
    setBulkRows(prev => prev.filter(r => r.id !== rowId))
  }

  const updateBulkRow = (rowId, patch) => {
    setBulkRows(prev => prev.map(r => r.id === rowId ? { ...r, ...patch } : r))
  }

  // Lazy-load creator options for the bulk creator dropdown.
  useEffect(() => {
    if (!showBulkUpload || !orgId || bulkCreatorOptions.length > 0) return
    axios.get(`/api/creators/org/${orgId}`)
      .then(res => setBulkCreatorOptions(Array.isArray(res.data) ? res.data : []))
      .catch(() => setBulkCreatorOptions([]))
  }, [showBulkUpload, orgId, bulkCreatorOptions.length])

  // Wait for the user to choose Skip / Overwrite / Cancel on a duplicate.
  // Marks the row as `duplicate_pending` for the progress list so the
  // operator can see at a glance which file is blocking the batch.
  const promptDuplicate = (rowIndex, info) => new Promise(resolve => {
    bulkDuplicateResolver.current = resolve
    if (info.rowId) updateBulkRow(info.rowId, { status: 'duplicate_pending', duplicate: { existing_statement_id: info.existing_statement_id, existing_status: info.existing_status } })
    setBulkDuplicatePrompt({ rowIndex, ...info })
  })

  const resolveDuplicatePrompt = (choice, applyToAll) => {
    if (applyToAll && (choice === 'skip' || choice === 'overwrite')) {
      bulkApplyChoiceRef.current = choice
    }
    if (choice === 'cancel') bulkCancelRef.current = true
    const fn = bulkDuplicateResolver.current
    bulkDuplicateResolver.current = null
    setBulkDuplicatePrompt(null)
    if (fn) fn(choice)
  }

  const handleBulkProcess = async () => {
    if (bulkRows.length === 0) return
    // Block when any row still needs review and isn't reviewed.
    const needsReview = bulkRows.find(r => r.status === 'needs_review' || (r.mappingConfident === false && !r.mappingReviewed))
    if (needsReview) {
      alert(`"${needsReview.file.name}" has a low-confidence column mapping. Please review it before continuing.`)
      return
    }
    bulkApplyChoiceRef.current = null
    bulkCancelRef.current = false
    setBulkStep(2)
    setBulkProcessing(true)

    for (let i = 0; i < bulkRows.length; i++) {
      if (bulkCancelRef.current) break
      const row = bulkRows[i]
      setBulkCurrentIndex(i)
      // Reset duplicate metadata on a fresh attempt so the row's
      // status pill flips back from any prior `duplicate_pending`.
      updateBulkRow(row.id, { status: 'uploading', error: null, duplicate: null })

      const sourceName = row.source_name || row.source_type || bulkSource || bulkSourceType || ''
      const sourceType = row.source_type || bulkSourceType || ''

      // Convert mapping {canonical_field: header} → JSON form param.
      const mappingPayload = {}
      Object.entries(row.mapping || {}).forEach(([field, header]) => {
        if (header) mappingPayload[field] = header
      })

      let force = false
      let attemptResult = null
      let attemptError = null
      // up to one re-attempt with force=true after a 409 prompt
      for (let attempt = 0; attempt < 2; attempt++) {
        const fd = new FormData()
        fd.append('file', row.file)
        fd.append('source_name', sourceName)
        if (sourceType) fd.append('source_type', sourceType)
        if (row.period_start) fd.append('period_start', row.period_start)
        if (row.period_end) fd.append('period_end', row.period_end)
        fd.append('currency', bulkCurrency)
        if (row.creator_id) fd.append('creator_id', String(row.creator_id))
        if (Object.keys(mappingPayload).length > 0) {
          fd.append('column_mapping', JSON.stringify(mappingPayload))
        }
        if (force) fd.append('force', 'true')
        try {
          const res = await axios.post(
            `/api/royalty-processing/${orgId}/statements/upload`,
            fd,
            { headers: { 'Content-Type': 'multipart/form-data' } }
          )
          attemptResult = res.data
          break
        } catch (err) {
          const status = err.response?.status
          const detail = err.response?.data?.detail
          if (status === 409 && detail && typeof detail === 'object' && detail.error === 'duplicate_statement') {
            // Decide what to do — Skip / Overwrite / Cancel.
            let choice = bulkApplyChoiceRef.current
            if (choice) {
              // Apply-to-all in effect — mirror the duplicate metadata
              // onto the row so the progress list can still show what
              // it collided with, even without a per-row prompt.
              updateBulkRow(row.id, { duplicate: { existing_statement_id: detail.existing_statement_id, existing_status: detail.existing_status } })
            } else {
              choice = await promptDuplicate(i, {
                rowId: row.id,
                fileName: row.file.name,
                existing_statement_id: detail.existing_statement_id,
                existing_status: detail.existing_status,
              })
            }
            if (choice === 'cancel') {
              bulkCancelRef.current = true
              attemptError = 'Batch cancelled.'
              break
            }
            if (choice === 'skip') {
              updateBulkRow(row.id, {
                status: 'skipped',
                duplicate: { existing_statement_id: detail.existing_statement_id, existing_status: detail.existing_status },
              })
              attemptError = null
              attemptResult = null
              break
            }
            if (choice === 'overwrite') {
              force = true
              continue
            }
          }
          attemptError = (typeof detail === 'string' ? detail : null) || err.message || 'Upload failed'
          break
        }
      }

      if (bulkCancelRef.current && !attemptResult && !attemptError) break

      if (attemptResult) {
        const matchStats = attemptResult.match_stats || {}
        updateBulkRow(row.id, {
          status: force ? 'overwritten' : 'done',
          result: {
            id: attemptResult.id,
            total_lines: attemptResult.total_lines || 0,
            matched: matchStats.matched_count || 0,
            unmatched: matchStats.unmatched_count || 0,
            review_required: matchStats.review_required_count || 0,
            statement_status: attemptResult.status,
          },
        })
      } else if (attemptError) {
        updateBulkRow(row.id, { status: 'error', error: attemptError })
      } else {
        // skipped (already updated above) — nothing to do
      }
    }

    setBulkProcessing(false)
    setBulkCurrentIndex(-1)
    setBulkStep(3)
    loadStatements()
  }

  if (loading) return <LoadingSpinner message="Loading statements..." />

  if (selectedStatement) {
    return (
      <div className="space-y-3">
        <div className="flex items-center justify-end gap-2">
          <button
            onClick={() => handleRematch(selectedStatement.id)}
            className="px-3 py-1.5 text-sm bg-[rgba(91,138,114,0.1)] text-[#5B8A72] rounded-xl hover:bg-[rgba(91,138,114,0.2)] transition-colors font-medium"
          >
            <ArrowPathIcon className="w-4 h-4 inline mr-1" /> Re-match
          </button>
          <button
            onClick={() => handleCalculate(selectedStatement.id)}
            disabled={calculating[selectedStatement.id]}
            className="px-3 py-1.5 text-sm bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-xl hover:shadow-[0px_4px_12px_rgba(91,138,114,0.3)] transition-all font-medium disabled:opacity-50"
          >
            <CalculatorIcon className="w-4 h-4 inline mr-1" />
            {calculating[selectedStatement.id] ? 'Calculating...' : 'Calculate Royalties'}
          </button>
        </div>
        <StatementDetailView
          orgId={orgId}
          statementId={selectedStatement.id}
          onBack={() => { setSelectedStatement(null); loadStatements() }}
          initialTab="lines"
        />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-[#3D4A44]">Royalty Statements</h3>
        <div className="flex items-center gap-2">
          {selectedIds.size > 0 && (
            <button
              onClick={() => setBulkDeleteOpen(true)}
              className="flex items-center gap-2 px-4 py-2 bg-red-500 text-white rounded-xl hover:bg-red-600 transition-all text-sm font-medium"
            >
              <TrashIcon className="w-4 h-4" /> Delete selected ({selectedIds.size})
            </button>
          )}
          <button onClick={() => setShowBulkUpload(true)} className="flex items-center gap-2 px-4 py-2 border border-[#5B8A72] text-[#5B8A72] rounded-xl hover:bg-[rgba(91,138,114,0.06)] transition-all text-sm font-medium">
            <DocumentDuplicateIcon className="w-4 h-4" /> Bulk Upload
          </button>
          <button onClick={() => setShowUpload(true)} className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-xl hover:shadow-[0px_4px_12px_rgba(91,138,114,0.3)] transition-all text-sm font-medium">
            <ArrowUpTrayIcon className="w-4 h-4" /> Upload Statement
          </button>
        </div>
      </div>

      <div className="bg-white/80 backdrop-blur-xl rounded-[18px] shadow-am border border-[rgba(59,77,67,0.08)]">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-[#EEF1EC]">
              <tr>
                <th className="pl-4 pr-2 py-3 w-8">
                  <input
                    type="checkbox"
                    aria-label="Select all statements"
                    checked={allVisibleSelected}
                    ref={el => { if (el) el.indeterminate = someVisibleSelected }}
                    onChange={toggleSelectAllVisible}
                    className="h-4 w-4 rounded border-[rgba(59,77,67,0.3)] text-[#5B8A72] focus:ring-[#5B8A72]"
                  />
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Source</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Period</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Currency</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-[#7A8580] uppercase">Total Revenue</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Status</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-[#7A8580] uppercase">Matched</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-[#7A8580] uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[rgba(59,77,67,0.06)]">
              {statements.map(stmt => (
                <tr key={stmt.id} className="hover:bg-[rgba(91,138,114,0.04)]">
                  <td className="pl-4 pr-2 py-4 w-8">
                    <input
                      type="checkbox"
                      aria-label={`Select statement ${stmt.source_name || stmt.id}`}
                      checked={selectedIds.has(stmt.id)}
                      onChange={() => toggleSelected(stmt.id)}
                      className="h-4 w-4 rounded border-[rgba(59,77,67,0.3)] text-[#5B8A72] focus:ring-[#5B8A72]"
                    />
                  </td>
                  <td className="px-6 py-4 text-sm font-medium text-[#3D4A44]">{stmt.source_name || '—'}</td>
                  <td className="px-6 py-4 text-sm text-[#7A8580]">
                    {stmt.period_start || stmt.period_end ? (
                      <>{formatDate(stmt.period_start)} — {formatDate(stmt.period_end)}</>
                    ) : (
                      canEditStatements ? (
                        <button
                          onClick={() => openEditStatement(stmt)}
                          className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-amber-100 text-amber-800 hover:bg-amber-200 transition-colors"
                          title="Decay analytics can't bucket this statement until a period is set"
                        >
                          Period missing — fix
                        </button>
                      ) : (
                        <span className="inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full bg-amber-100 text-amber-800">
                          Period missing
                        </span>
                      )
                    )}
                  </td>
                  <td className="px-6 py-4 text-sm text-[#7A8580]">{stmt.currency || 'USD'}</td>
                  <td className="px-6 py-4 text-sm text-right font-medium text-[#3D4A44]">{formatCents(stmt.total_revenue_cents)}</td>
                  <td className="px-6 py-4"><StatusBadge status={stmt.status || 'PENDING'} colorMap={STATEMENT_STATUS_COLORS} /></td>
                  <td className="px-6 py-4 text-sm text-right text-[#7A8580]">{stmt.matched_percentage != null ? `${stmt.matched_percentage}%` : '—'}</td>
                  <td className="px-6 py-4">
                    <div className="flex items-center justify-end gap-1">
                      <button onClick={() => loadTransactions(stmt)} className="p-1.5 text-[#5B8A72] hover:bg-[rgba(91,138,114,0.1)] rounded-lg transition-colors" title="View">
                        <EyeIcon className="w-4 h-4" />
                      </button>
                      <button onClick={() => handleCalculate(stmt.id)} disabled={calculating[stmt.id]} className="p-1.5 text-[#5B8A72] hover:bg-[rgba(91,138,114,0.1)] rounded-lg transition-colors disabled:opacity-40" title="Calculate">
                        <CalculatorIcon className="w-4 h-4" />
                      </button>
                      {canEditStatements && (
                        <button onClick={() => openEditStatement(stmt)} className="p-1.5 text-[#5B8A72] hover:bg-[rgba(91,138,114,0.1)] rounded-lg transition-colors" title="Edit period & metadata">
                          <PencilSquareIcon className="w-4 h-4" />
                        </button>
                      )}
                      <button onClick={() => setShareStatement(stmt)} className="p-1.5 text-[#5B8A72] hover:bg-[rgba(91,138,114,0.1)] rounded-lg transition-colors" title="Share">
                        <ShareIcon className="w-4 h-4" />
                      </button>
                      <button onClick={() => handleDelete(stmt)} className="p-1.5 text-red-500 hover:bg-red-50 rounded-lg transition-colors" title="Delete">
                        <TrashIcon className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {statements.length === 0 && (
                <tr><td colSpan={8} className="px-6 py-12 text-center text-sm text-[#7A8580]">{selectedCreatorId ? 'No statements for this client yet.' : 'No statements uploaded yet.'}</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {showUpload && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm p-4">
          <div className="bg-white rounded-[18px] shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-6 border-b border-[rgba(59,77,67,0.08)]">
              <h3 className="text-lg font-semibold text-[#3D4A44]">
                {uploadStep === 1 && 'Upload Statement'}
                {uploadStep === 2 && 'Map Columns'}
                {uploadStep === 3 && 'Upload Complete'}
              </h3>
              <button onClick={resetUpload} className="p-2 hover:bg-[rgba(59,77,67,0.06)] rounded-full transition-colors">
                <XMarkIcon className="w-5 h-5 text-[#7A8580]" />
              </button>
            </div>

            <div className="p-6">
              {uploadStep === 1 && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-[#3D4A44] mb-1">Statement Source</label>
                    <select
                      value={uploadSourceType}
                      onChange={e => {
                        setUploadSourceType(e.target.value)
                        if (e.target.value && e.target.value !== 'DSP') setUploadSource(e.target.value)
                      }}
                      className="w-full px-4 py-2.5 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm text-[#3D4A44] bg-white focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent outline-none"
                    >
                      {SOURCE_TYPE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                    </select>
                    <p className="text-xs text-[#7A8580] mt-1">Pick the source first so we can detect columns automatically</p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-[#3D4A44] mb-1">File (CSV/Excel/PDF)</label>
                    <input
                      type="file"
                      accept=".csv,.xlsx,.xls,.pdf,application/pdf,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel"
                      onChange={e => setUploadFile(e.target.files?.[0] || null)}
                      className="w-full text-sm text-[#3D4A44] file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-medium file:bg-[rgba(91,138,114,0.1)] file:text-[#5B8A72] hover:file:bg-[rgba(91,138,114,0.2)]"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-[#3D4A44] mb-1">Source Name</label>
                    <input
                      type="text"
                      value={uploadSource}
                      onChange={e => setUploadSource(e.target.value)}
                      placeholder={uploadSourceType === 'DSP' ? 'e.g. Spotify, Apple Music, DistroKid' : uploadSourceType ? `e.g. ${uploadSourceType} Q4 2025` : 'e.g. Spotify, BMI, ASCAP'}
                      className="w-full px-4 py-2.5 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm text-[#3D4A44] bg-white focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent outline-none"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-[#3D4A44] mb-1">Period Start</label>
                      <input type="date" value={uploadPeriodStart} onChange={e => setUploadPeriodStart(e.target.value)} className="w-full px-4 py-2.5 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm text-[#3D4A44] bg-white focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent outline-none" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-[#3D4A44] mb-1">Period End</label>
                      <input type="date" value={uploadPeriodEnd} onChange={e => setUploadPeriodEnd(e.target.value)} className="w-full px-4 py-2.5 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm text-[#3D4A44] bg-white focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent outline-none" />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-[#3D4A44] mb-1">Currency</label>
                    <select value={uploadCurrency} onChange={e => setUploadCurrency(e.target.value)} className="w-full px-4 py-2.5 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm text-[#3D4A44] bg-white focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent outline-none">
                      {CURRENCIES.map(c => <option key={c} value={c}>{c}</option>)}
                    </select>
                  </div>
                  <div className="flex justify-end pt-2">
                    <button
                      onClick={handlePreview}
                      disabled={!uploadFile || uploading}
                      className="px-5 py-2.5 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-xl hover:shadow-[0px_4px_12px_rgba(91,138,114,0.3)] transition-all text-sm font-medium disabled:opacity-50"
                    >
                      {uploading ? 'Previewing...' : 'Preview & Map Columns'}
                    </button>
                  </div>
                </div>
              )}

              {uploadStep === 2 && previewData && (
                <div className="space-y-4">
                  {detectedSourceType && (
                    <div className="flex items-center gap-2 px-4 py-3 bg-[rgba(91,138,114,0.08)] border border-[rgba(91,138,114,0.15)] rounded-xl">
                      <CheckCircleSolid className="w-5 h-5 text-[#5B8A72] flex-shrink-0" />
                      <p className="text-sm text-[#3D4A44]">
                        Detected as <span className="font-semibold">{detectedSourceType}</span> statement — columns mapped accordingly
                      </p>
                    </div>
                  )}
                  {previewData.mapping_confident === false && (
                    <div className="flex items-start gap-2 px-4 py-3 bg-amber-50 border border-amber-200 rounded-xl">
                      <ExclamationCircleIcon className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                      <div className="text-sm text-[#3D4A44]">
                        <p className="font-medium">
                          Low-confidence column mapping{typeof previewData.mapping_confidence === 'number' ? ` (${Math.round(previewData.mapping_confidence * 100)}%)` : ''} — review carefully.
                        </p>
                        {Array.isArray(previewData.unmapped_headers) && previewData.unmapped_headers.length > 0 && (
                          <p className="text-xs text-[#7A8580] mt-1">
                            Unmatched headers: <span className="font-mono">{previewData.unmapped_headers.join(', ')}</span>
                          </p>
                        )}
                      </div>
                    </div>
                  )}
                  <p className="text-sm text-[#7A8580]">
                    Detected {previewData.columns?.length || 0} columns and {previewData.row_count || previewData.rows?.length || 0} rows. Adjust the mappings below:
                  </p>
                  <div className="space-y-3">
                    {(previewData.columns || []).map((col) => (
                      <div key={col} className="flex items-center gap-4">
                        <span className="text-sm font-medium text-[#3D4A44] w-40 truncate" title={col}>{col}</span>
                        <ChevronRightIcon className="w-4 h-4 text-[#7A8580] flex-shrink-0" />
                        <select
                          value={columnMappings[col] || ''}
                          onChange={e => setColumnMappings(prev => ({ ...prev, [col]: e.target.value }))}
                          className="flex-1 px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm text-[#3D4A44] bg-white focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent outline-none"
                        >
                          {TARGET_FIELDS.map(f => <option key={f.value} value={f.value}>{f.label}</option>)}
                        </select>
                      </div>
                    ))}
                  </div>
                  {previewData.preview_rows && previewData.preview_rows.length > 0 && (
                    <div className="mt-4">
                      <p className="text-xs font-medium text-[#7A8580] mb-2">Preview (first rows):</p>
                      <div className="overflow-x-auto border border-[rgba(59,77,67,0.1)] rounded-xl">
                        <table className="w-full text-xs">
                          <thead className="bg-[#EEF1EC]">
                            <tr>
                              {(previewData.columns || []).map(c => <th key={c} className="px-3 py-2 text-left text-[#7A8580] font-medium">{c}</th>)}
                            </tr>
                          </thead>
                          <tbody>
                            {previewData.preview_rows.slice(0, 3).map((row, i) => (
                              <tr key={i} className="border-t border-[rgba(59,77,67,0.06)]">
                                {(previewData.columns || []).map(c => <td key={c} className="px-3 py-2 text-[#3D4A44]">{row[c] ?? '—'}</td>)}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                  <div className="flex justify-between pt-2">
                    <button onClick={() => setUploadStep(1)} className="px-4 py-2 text-sm text-[#7A8580] hover:text-[#3D4A44] transition-colors">Back</button>
                    <button
                      onClick={handleUpload}
                      disabled={uploading}
                      className="px-5 py-2.5 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-xl hover:shadow-[0px_4px_12px_rgba(91,138,114,0.3)] transition-all text-sm font-medium disabled:opacity-50"
                    >
                      {uploading ? 'Uploading...' : 'Confirm & Upload'}
                    </button>
                  </div>
                </div>
              )}

              {uploadStep === 3 && (
                <div className="text-center py-6">
                  <CheckCircleSolid className="w-16 h-16 text-[#5B8A72] mx-auto mb-4" />
                  <h4 className="text-lg font-semibold text-[#3D4A44] mb-2">Upload Successful</h4>
                  {(() => {
                    const total = uploadResult?.total_transactions ?? uploadResult?.transactions_count ?? uploadResult?.rows_imported ?? 0
                    const matched = uploadResult?.matched_transactions ?? uploadResult?.matched_count
                    const unmatched = uploadResult?.unmatched_transactions ?? uploadResult?.unmatched_count ?? 0
                    const totalRevenue = uploadResult?.total_revenue_dollars ?? (uploadResult?.total_revenue_cents != null ? uploadResult.total_revenue_cents / 100 : null)
                    return (
                      <>
                        <p className="text-sm text-[#7A8580] mb-1">
                          {total} transactions imported
                        </p>
                        {matched != null && (
                          <p className="text-sm text-[#7A8580]">
                            {matched} matched, {unmatched} unmatched
                          </p>
                        )}
                        {totalRevenue != null && (
                          <p className="text-sm text-[#7A8580] mt-1">
                            Total revenue: ${totalRevenue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                          </p>
                        )}
                      </>
                    )
                  })()}
                  <button onClick={resetUpload} className="mt-6 px-5 py-2.5 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-xl hover:shadow-[0px_4px_12px_rgba(91,138,114,0.3)] transition-all text-sm font-medium">
                    Done
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {showBulkUpload && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm p-4">
          <div className="bg-white rounded-[18px] shadow-2xl w-full max-w-5xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-6 border-b border-[rgba(59,77,67,0.08)]">
              <h3 className="text-lg font-semibold text-[#3D4A44]">
                {bulkStep === 1 && 'Bulk Upload Statements'}
                {bulkStep === 2 && 'Processing Files'}
                {bulkStep === 3 && 'Bulk Upload Complete'}
              </h3>
              <button onClick={resetBulkUpload} disabled={bulkProcessing} className="p-2 hover:bg-[rgba(59,77,67,0.06)] rounded-full transition-colors disabled:opacity-40">
                <XMarkIcon className="w-5 h-5 text-[#7A8580]" />
              </button>
            </div>

            <div className="p-6">
              {bulkStep === 1 && (
                <div className="space-y-4">
                  <p className="text-xs text-[#7A8580]">
                    Bulk uploads run through the same Enhanced pipeline as a single upload — auto-detected source type, full match status, and audit log on every file. Adjust per-file overrides in the table below.
                  </p>
                  <div>
                    <label className="block text-sm font-medium text-[#3D4A44] mb-1">Add Files (CSV/Excel/PDF)</label>
                    <input
                      type="file"
                      multiple
                      accept=".csv,.xlsx,.xls,.pdf,application/pdf,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel"
                      onChange={e => { handleBulkFilesChange(e.target.files); e.target.value = '' }}
                      className="w-full text-sm text-[#3D4A44] file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-medium file:bg-[rgba(91,138,114,0.1)] file:text-[#5B8A72] hover:file:bg-[rgba(91,138,114,0.2)]"
                    />
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-6 gap-3 p-3 bg-[#F5F7F4] rounded-xl">
                    <div className="col-span-2 md:col-span-6 text-xs font-medium text-[#7A8580]">Batch defaults (applied to new rows you add — per-row values from PDF auto-detection still take precedence):</div>
                    <div>
                      <label className="block text-xs text-[#7A8580] mb-1">Source type</label>
                      <select value={bulkSourceType} onChange={e => setBulkSourceType(e.target.value)} className="w-full px-2 py-1.5 border border-[rgba(59,77,67,0.15)] rounded-lg text-xs bg-white">
                        {SOURCE_TYPE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.value || 'Auto'}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs text-[#7A8580] mb-1">Source name</label>
                      <input type="text" value={bulkSource} onChange={e => setBulkSource(e.target.value)} placeholder="(optional)" className="w-full px-2 py-1.5 border border-[rgba(59,77,67,0.15)] rounded-lg text-xs bg-white" />
                    </div>
                    <div>
                      <label className="block text-xs text-[#7A8580] mb-1">Period start</label>
                      <input type="date" value={bulkPeriodStart} onChange={e => setBulkPeriodStart(e.target.value)} className="w-full px-2 py-1.5 border border-[rgba(59,77,67,0.15)] rounded-lg text-xs bg-white" />
                    </div>
                    <div>
                      <label className="block text-xs text-[#7A8580] mb-1">Period end</label>
                      <input type="date" value={bulkPeriodEnd} onChange={e => setBulkPeriodEnd(e.target.value)} className="w-full px-2 py-1.5 border border-[rgba(59,77,67,0.15)] rounded-lg text-xs bg-white" />
                    </div>
                    <div>
                      <label className="block text-xs text-[#7A8580] mb-1">Currency</label>
                      <select value={bulkCurrency} onChange={e => setBulkCurrency(e.target.value)} className="w-full px-2 py-1.5 border border-[rgba(59,77,67,0.15)] rounded-lg text-xs bg-white">
                        {CURRENCIES.map(c => <option key={c} value={c}>{c}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs text-[#7A8580] mb-1">Creator (optional)</label>
                      <select value={bulkCreatorId} onChange={e => setBulkCreatorId(e.target.value)} className="w-full px-2 py-1.5 border border-[rgba(59,77,67,0.15)] rounded-lg text-xs bg-white">
                        <option value="">— None —</option>
                        {bulkCreatorOptions.map(c => <option key={c.id} value={c.id}>{c.display_name || c.name}</option>)}
                      </select>
                    </div>
                  </div>

                  {bulkRows.length === 0 ? (
                    <div className="text-center py-8 text-sm text-[#7A8580]">
                      Pick one or more statement files above. Each file gets its own row you can edit.
                    </div>
                  ) : (
                    <div className="overflow-x-auto border border-[rgba(59,77,67,0.08)] rounded-xl">
                      <table className="w-full text-xs">
                        <thead className="bg-[#EEF1EC] text-[#7A8580]">
                          <tr>
                            <th className="px-3 py-2 text-left font-medium min-w-[200px]">File</th>
                            <th className="px-2 py-2 text-left font-medium">Source type</th>
                            <th className="px-2 py-2 text-left font-medium">Source name</th>
                            <th className="px-2 py-2 text-left font-medium">Period start</th>
                            <th className="px-2 py-2 text-left font-medium">Period end</th>
                            <th className="px-2 py-2 text-left font-medium">Creator</th>
                            <th className="px-2 py-2 text-left font-medium">Mapping</th>
                            <th className="px-2 py-2"></th>
                          </tr>
                        </thead>
                        <tbody>
                          {bulkRows.map((row) => {
                            const needsReview = row.mappingConfident === false && !row.mappingReviewed
                            return (
                              <tr key={row.id} className="border-t border-[rgba(59,77,67,0.06)]">
                                <td className="px-3 py-2 align-top">
                                  <div className="flex items-center gap-2">
                                    <DocumentTextIcon className="w-4 h-4 text-[#7A8580] flex-shrink-0" />
                                    <div className="min-w-0">
                                      <p className="text-[#3D4A44] truncate" title={row.file.name}>{row.file.name}</p>
                                      <p className="text-[10px] text-[#7A8580]">{(row.file.size / 1024).toFixed(0)} KB</p>
                                      {row.previewLoading && <p className="text-[10px] text-blue-600">Detecting…</p>}
                                      {row.previewError && <p className="text-[10px] text-red-600 truncate" title={row.previewError}>Preview error</p>}
                                    </div>
                                  </div>
                                </td>
                                <td className="px-2 py-2 align-top">
                                  <select value={row.source_type} onChange={e => updateBulkRow(row.id, { source_type: e.target.value })} className="w-full px-2 py-1.5 border border-[rgba(59,77,67,0.15)] rounded-lg bg-white">
                                    {SOURCE_TYPE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.value || 'Auto'}</option>)}
                                  </select>
                                </td>
                                <td className="px-2 py-2 align-top">
                                  <input type="text" value={row.source_name} onChange={e => updateBulkRow(row.id, { source_name: e.target.value })} placeholder="(detected)" className="w-32 px-2 py-1.5 border border-[rgba(59,77,67,0.15)] rounded-lg bg-white" />
                                </td>
                                <td className="px-2 py-2 align-top">
                                  <input type="date" value={row.period_start} onChange={e => updateBulkRow(row.id, { period_start: e.target.value })} className="w-32 px-2 py-1.5 border border-[rgba(59,77,67,0.15)] rounded-lg bg-white" />
                                </td>
                                <td className="px-2 py-2 align-top">
                                  <input type="date" value={row.period_end} onChange={e => updateBulkRow(row.id, { period_end: e.target.value })} className="w-32 px-2 py-1.5 border border-[rgba(59,77,67,0.15)] rounded-lg bg-white" />
                                </td>
                                <td className="px-2 py-2 align-top">
                                  <select value={row.creator_id} onChange={e => updateBulkRow(row.id, { creator_id: e.target.value })} className="w-full px-2 py-1.5 border border-[rgba(59,77,67,0.15)] rounded-lg bg-white">
                                    <option value="">—</option>
                                    {bulkCreatorOptions.map(c => <option key={c.id} value={c.id}>{c.display_name || c.name}</option>)}
                                  </select>
                                </td>
                                <td className="px-2 py-2 align-top">
                                  {row.previewLoading ? (
                                    <span className="text-[#7A8580]">…</span>
                                  ) : needsReview ? (
                                    <button onClick={() => setBulkMappingReviewIdx(bulkRows.findIndex(r => r.id === row.id))} className="inline-flex items-center gap-1 px-2 py-1 bg-amber-100 text-amber-700 rounded-lg font-medium hover:bg-amber-200">
                                      <ExclamationCircleIcon className="w-3.5 h-3.5" /> Review
                                    </button>
                                  ) : row.mappingReviewed ? (
                                    <button onClick={() => setBulkMappingReviewIdx(bulkRows.findIndex(r => r.id === row.id))} className="inline-flex items-center gap-1 px-2 py-1 bg-[rgba(91,138,114,0.1)] text-[#5B8A72] rounded-lg font-medium hover:bg-[rgba(91,138,114,0.2)]">
                                      <CheckCircleIcon className="w-3.5 h-3.5" /> Reviewed
                                    </button>
                                  ) : (
                                    <button onClick={() => setBulkMappingReviewIdx(bulkRows.findIndex(r => r.id === row.id))} className="inline-flex items-center gap-1 px-2 py-1 text-[#5B8A72] hover:underline">
                                      View
                                    </button>
                                  )}
                                </td>
                                <td className="px-2 py-2 align-top text-right">
                                  <button onClick={() => removeBulkRow(row.id)} className="p-1 text-[#7A8580] hover:text-red-500" title="Remove">
                                    <TrashIcon className="w-4 h-4" />
                                  </button>
                                </td>
                              </tr>
                            )
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {bulkRows.some(r => r.status === 'needs_review' || (r.mappingConfident === false && !r.mappingReviewed)) && (
                    <div className="flex items-start gap-2 px-4 py-3 bg-amber-50 border border-amber-200 rounded-xl">
                      <ExclamationCircleIcon className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                      <p className="text-sm text-[#3D4A44]">
                        One or more files have low-confidence column mappings. Click <span className="font-medium">Review</span> on each before uploading.
                      </p>
                    </div>
                  )}

                  <div className="flex justify-between pt-2">
                    <p className="text-xs text-[#7A8580] self-center">
                      {bulkRows.length} file{bulkRows.length === 1 ? '' : 's'} ready
                    </p>
                    <button
                      onClick={handleBulkProcess}
                      disabled={bulkRows.length === 0 || bulkRows.some(r => r.previewLoading) || bulkRows.some(r => r.status === 'needs_review' || (r.mappingConfident === false && !r.mappingReviewed))}
                      className="px-5 py-2.5 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-xl hover:shadow-[0px_4px_12px_rgba(91,138,114,0.3)] transition-all text-sm font-medium disabled:opacity-50"
                    >
                      Upload {bulkRows.length} File{bulkRows.length === 1 ? '' : 's'}
                    </button>
                  </div>
                </div>
              )}

              {bulkStep === 2 && (
                <div className="space-y-3">
                  {(() => {
                    const total = bulkRows.length
                    const finished = bulkRows.filter(r => r.status !== 'pending' && r.status !== 'uploading').length
                    return (
                      <div className="flex items-center gap-3 mb-4">
                        <div className="w-full bg-[#EEF1EC] rounded-full h-2">
                          <div
                            className="bg-gradient-to-r from-[#5B8A72] to-[#7BA594] h-2 rounded-full transition-all duration-500"
                            style={{ width: `${total > 0 ? (finished / total) * 100 : 0}%` }}
                          />
                        </div>
                        <span className="text-sm text-[#7A8580] flex-shrink-0 min-w-[60px] text-right">{finished}/{total}</span>
                      </div>
                    )
                  })()}
                  {bulkRows.map(row => {
                    const tone =
                      row.status === 'uploading' ? 'border-blue-200 bg-blue-50' :
                      row.status === 'done' ? 'border-green-200 bg-green-50' :
                      row.status === 'overwritten' ? 'border-green-200 bg-green-50' :
                      row.status === 'skipped' ? 'border-[rgba(59,77,67,0.15)] bg-[#F5F7F4]' :
                      row.status === 'error' ? 'border-red-200 bg-red-50' :
                      row.status === 'needs_review' ? 'border-amber-200 bg-amber-50' :
                      row.status === 'duplicate_pending' ? 'border-amber-200 bg-amber-50' :
                      'border-[rgba(59,77,67,0.08)] bg-[#F5F7F4]'
                    return (
                      <div key={row.id} className={`flex items-center gap-3 px-4 py-3 rounded-xl border ${tone}`}>
                        <div className="flex-shrink-0">
                          {row.status === 'uploading' ? <ArrowPathIcon className="w-5 h-5 text-blue-500 animate-spin" /> :
                           row.status === 'done' || row.status === 'overwritten' ? <CheckCircleSolid className="w-5 h-5 text-green-600" /> :
                           row.status === 'skipped' ? <XMarkIcon className="w-5 h-5 text-[#7A8580]" /> :
                           row.status === 'error' ? <ExclamationCircleIcon className="w-5 h-5 text-red-500" /> :
                           row.status === 'needs_review' ? <ExclamationCircleIcon className="w-5 h-5 text-amber-600" /> :
                           row.status === 'duplicate_pending' ? <ExclamationCircleIcon className="w-5 h-5 text-amber-600" /> :
                           <ClockIcon className="w-5 h-5 text-[#7A8580]" />}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-[#3D4A44] truncate">{row.file.name}</p>
                          {row.status === 'done' && row.result && (
                            <p className="text-xs text-[#7A8580]">
                              {row.result.total_lines} lines · {row.result.matched} matched · {row.result.unmatched} unmatched · status {row.result.statement_status}
                            </p>
                          )}
                          {row.status === 'overwritten' && row.result && (
                            <p className="text-xs text-[#5B8A72]">Overwrote duplicate · {row.result.total_lines} lines · status {row.result.statement_status}</p>
                          )}
                          {row.status === 'skipped' && (
                            <p className="text-xs text-[#7A8580]">Skipped — duplicate of statement #{row.duplicate?.existing_statement_id}</p>
                          )}
                          {row.status === 'needs_review' && (
                            <p className="text-xs text-amber-700">Needs mapping review (low confidence)</p>
                          )}
                          {row.status === 'duplicate_pending' && (
                            <p className="text-xs text-amber-700">
                              Duplicate of statement #{row.duplicate?.existing_statement_id} — awaiting your choice
                            </p>
                          )}
                          {row.status === 'error' && <p className="text-xs text-red-600 truncate">{row.error}</p>}
                          {row.status === 'uploading' && <p className="text-xs text-blue-600">Processing…</p>}
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}

              {bulkStep === 3 && (() => {
                const succeeded = bulkRows.filter(r => r.status === 'done' || r.status === 'overwritten').length
                const failed = bulkRows.filter(r => r.status === 'error').length
                const skipped = bulkRows.filter(r => r.status === 'skipped').length
                const overwritten = bulkRows.filter(r => r.status === 'overwritten').length
                const totalLines = bulkRows.reduce((s, r) => s + (r.result?.total_lines || 0), 0)
                return (
                  <div className="text-center py-6">
                    <CheckCircleSolid className="w-16 h-16 text-[#5B8A72] mx-auto mb-4" />
                    <h4 className="text-lg font-semibold text-[#3D4A44] mb-2">Bulk Upload Complete</h4>
                    <div className="flex flex-wrap items-center justify-center gap-6 mb-4">
                      <div className="text-center">
                        <p className="text-2xl font-bold text-[#5B8A72]">{succeeded}</p>
                        <p className="text-xs text-[#7A8580]">Succeeded</p>
                      </div>
                      {overwritten > 0 && (
                        <div className="text-center">
                          <p className="text-2xl font-bold text-[#5B8A72]">{overwritten}</p>
                          <p className="text-xs text-[#7A8580]">Overwritten</p>
                        </div>
                      )}
                      {skipped > 0 && (
                        <div className="text-center">
                          <p className="text-2xl font-bold text-[#7A8580]">{skipped}</p>
                          <p className="text-xs text-[#7A8580]">Skipped (duplicate)</p>
                        </div>
                      )}
                      {failed > 0 && (
                        <div className="text-center">
                          <p className="text-2xl font-bold text-red-500">{failed}</p>
                          <p className="text-xs text-[#7A8580]">Failed</p>
                        </div>
                      )}
                      <div className="text-center">
                        <p className="text-2xl font-bold text-[#3D4A44]">{totalLines}</p>
                        <p className="text-xs text-[#7A8580]">Total Lines</p>
                      </div>
                    </div>
                    {failed > 0 && (
                      <div className="mb-4 max-h-32 overflow-y-auto text-left">
                        {bulkRows.filter(r => r.status === 'error').map((r) => (
                          <div key={r.id} className="flex items-center gap-2 px-3 py-2 bg-red-50 rounded-lg mb-1">
                            <ExclamationCircleIcon className="w-4 h-4 text-red-500 flex-shrink-0" />
                            <span className="text-xs text-red-700 truncate">{r.file.name}: {r.error}</span>
                          </div>
                        ))}
                      </div>
                    )}
                    <button onClick={resetBulkUpload} className="mt-2 px-5 py-2.5 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-xl hover:shadow-[0px_4px_12px_rgba(91,138,114,0.3)] transition-all text-sm font-medium">
                      Done
                    </button>
                  </div>
                )
              })()}
            </div>
          </div>
        </div>
      )}

      {bulkMappingReviewIdx >= 0 && bulkRows[bulkMappingReviewIdx] && (() => {
        const row = bulkRows[bulkMappingReviewIdx]
        const columns = row.preview?.columns || []
        // Display: header → canonical_field. Mapping is stored canonical→header.
        const headerToField = {}
        Object.entries(row.mapping || {}).forEach(([field, header]) => { if (header) headerToField[header] = field })
        const setHeader = (header, field) => {
          const next = { ...(row.mapping || {}) }
          // Drop any existing field that mapped to this header
          Object.entries(next).forEach(([f, h]) => { if (h === header) delete next[f] })
          if (field) next[field] = header
          updateBulkRow(row.id, { mapping: next })
        }
        return (
          <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
            <div className="bg-white rounded-[18px] shadow-2xl w-full max-w-2xl max-h-[85vh] overflow-y-auto">
              <div className="flex items-center justify-between p-5 border-b border-[rgba(59,77,67,0.08)]">
                <h3 className="text-base font-semibold text-[#3D4A44]">Review column mapping — {row.file.name}</h3>
                <button onClick={() => setBulkMappingReviewIdx(-1)} className="p-2 hover:bg-[rgba(59,77,67,0.06)] rounded-full">
                  <XMarkIcon className="w-5 h-5 text-[#7A8580]" />
                </button>
              </div>
              <div className="p-5 space-y-3">
                {row.preview?.detected_source_type && (
                  <div className="text-xs text-[#7A8580]">
                    Detected as <span className="font-semibold text-[#3D4A44]">{row.preview.detected_source_type}</span>
                    {typeof row.preview.mapping_confidence === 'number' && (
                      <> · mapping confidence <span className="font-semibold text-[#3D4A44]">{Math.round(row.preview.mapping_confidence * 100)}%</span></>
                    )}
                  </div>
                )}
                {row.unmappedHeaders && row.unmappedHeaders.length > 0 && (
                  <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
                    Unmatched headers: <span className="font-mono">{row.unmappedHeaders.join(', ')}</span>
                  </div>
                )}
                <div className="space-y-2">
                  {columns.map(col => (
                    <div key={col} className="flex items-center gap-3">
                      <span className="text-sm font-medium text-[#3D4A44] w-40 truncate" title={col}>{col}</span>
                      <ChevronRightIcon className="w-4 h-4 text-[#7A8580] flex-shrink-0" />
                      <select
                        value={headerToField[col] || ''}
                        onChange={e => setHeader(col, e.target.value)}
                        className="flex-1 px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm bg-white"
                      >
                        {TARGET_FIELDS.map(f => <option key={f.value} value={f.value}>{f.label}</option>)}
                      </select>
                    </div>
                  ))}
                </div>
                <div className="flex justify-end gap-2 pt-2">
                  <button onClick={() => setBulkMappingReviewIdx(-1)} className="px-4 py-2 text-sm text-[#7A8580] hover:text-[#3D4A44]">Cancel</button>
                  <button
                    onClick={() => {
                      // Reviewing a low-confidence mapping clears the
                      // needs_review block so the row joins the rest of
                      // the batch as `pending`.
                      updateBulkRow(row.id, {
                        mappingReviewed: true,
                        status: row.status === 'needs_review' ? 'pending' : row.status,
                      })
                      setBulkMappingReviewIdx(-1)
                    }}
                    className="px-4 py-2 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-xl text-sm font-medium"
                  >
                    Save mapping
                  </button>
                </div>
              </div>
            </div>
          </div>
        )
      })()}

      {bulkDuplicatePrompt && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-[18px] shadow-2xl w-full max-w-md">
            <div className="p-5 border-b border-[rgba(59,77,67,0.08)]">
              <h3 className="text-base font-semibold text-[#3D4A44]">Duplicate statement detected</h3>
            </div>
            <div className="p-5 space-y-3">
              <p className="text-sm text-[#3D4A44]">
                <span className="font-semibold">{bulkDuplicatePrompt.fileName}</span> looks like a duplicate of an existing statement
                {bulkDuplicatePrompt.existing_statement_id ? <> (#{bulkDuplicatePrompt.existing_statement_id}, status {bulkDuplicatePrompt.existing_status})</> : ''}.
              </p>
              <p className="text-xs text-[#7A8580]">
                <span className="font-medium">Skip</span> — keep the existing statement and move on.
                <br />
                <span className="font-medium">Overwrite</span> — force a fresh import alongside the existing statement (the old one stays and can be deleted from the Statements page; this is not a destructive in-place replace).
                <br />
                <span className="font-medium">Cancel batch</span> — stop the bulk upload here.
              </p>
              <div className="flex flex-col gap-2 pt-2">
                <div className="flex gap-2">
                  <button onClick={() => resolveDuplicatePrompt('skip', false)} className="flex-1 px-3 py-2 bg-[#F5F7F4] text-[#3D4A44] rounded-xl text-sm font-medium hover:bg-[#EEF1EC]">Skip</button>
                  <button onClick={() => resolveDuplicatePrompt('overwrite', false)} className="flex-1 px-3 py-2 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-xl text-sm font-medium">Overwrite</button>
                  <button onClick={() => resolveDuplicatePrompt('cancel', false)} className="flex-1 px-3 py-2 bg-red-50 text-red-600 rounded-xl text-sm font-medium hover:bg-red-100">Cancel batch</button>
                </div>
                <div className="flex gap-2 text-xs">
                  <button onClick={() => resolveDuplicatePrompt('skip', true)} className="flex-1 px-2 py-1.5 text-[#7A8580] hover:text-[#3D4A44] underline">Apply skip to all</button>
                  <button onClick={() => resolveDuplicatePrompt('overwrite', true)} className="flex-1 px-2 py-1.5 text-[#7A8580] hover:text-[#3D4A44] underline">Apply overwrite to all</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {editStmt && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm p-4" onClick={closeEditStatement}>
          <div className="bg-white rounded-[18px] shadow-2xl w-full max-w-md" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between p-6 border-b border-[rgba(59,77,67,0.08)]">
              <h3 className="text-lg font-semibold text-[#3D4A44]">Edit Statement</h3>
              <button onClick={closeEditStatement} disabled={editSaving} className="p-2 hover:bg-[rgba(59,77,67,0.06)] rounded-full transition-colors disabled:opacity-40">
                <XMarkIcon className="w-5 h-5 text-[#7A8580]" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <p className="text-xs text-[#7A8580]">
                Correct the statement period or label if it was misread from the PDF. This does not change the underlying file or any line amounts. The change is recorded in the audit log.
              </p>
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Source Name</label>
                <input
                  type="text"
                  value={editForm.source_name}
                  onChange={e => setEditForm(f => ({ ...f, source_name: e.target.value }))}
                  className="w-full px-4 py-2.5 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm text-[#3D4A44] bg-white focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Statement Source</label>
                <select
                  value={editForm.source_type}
                  onChange={e => setEditForm(f => ({ ...f, source_type: e.target.value }))}
                  className="w-full px-4 py-2.5 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm text-[#3D4A44] bg-white focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent outline-none"
                >
                  {SOURCE_TYPE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Period Start</label>
                  <input
                    type="date"
                    value={editForm.period_start || ''}
                    onChange={e => setEditForm(f => ({ ...f, period_start: e.target.value }))}
                    className="w-full px-4 py-2.5 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm text-[#3D4A44] bg-white focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Period End</label>
                  <input
                    type="date"
                    value={editForm.period_end || ''}
                    onChange={e => setEditForm(f => ({ ...f, period_end: e.target.value }))}
                    className="w-full px-4 py-2.5 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm text-[#3D4A44] bg-white focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent outline-none"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Currency</label>
                <select
                  value={editForm.currency}
                  onChange={e => setEditForm(f => ({ ...f, currency: e.target.value }))}
                  className="w-full px-4 py-2.5 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm text-[#3D4A44] bg-white focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent outline-none"
                >
                  {CURRENCIES.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Assigned Client</label>
                <select
                  value={editForm.creator_id}
                  onChange={e => setEditForm(f => ({ ...f, creator_id: e.target.value }))}
                  className="w-full px-4 py-2.5 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm text-[#3D4A44] bg-white focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent outline-none"
                >
                  <option value="">— Unassigned (org-wide) —</option>
                  {editCreatorOptions.map(c => (
                    <option key={c.id} value={c.id}>{c.name || c.display_name || `Creator #${c.id}`}</option>
                  ))}
                </select>
              </div>
              {editError && (
                <div className="px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
                  {typeof editError === 'string' ? editError : 'Failed to save changes.'}
                </div>
              )}
              <div className="flex justify-end gap-2 pt-2">
                <button onClick={closeEditStatement} disabled={editSaving} className="px-4 py-2 text-sm text-[#7A8580] hover:text-[#3D4A44] transition-colors disabled:opacity-40">Cancel</button>
                <button
                  onClick={submitEditStatement}
                  disabled={editSaving}
                  className="px-5 py-2.5 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-xl hover:shadow-[0px_4px_12px_rgba(91,138,114,0.3)] transition-all text-sm font-medium disabled:opacity-50"
                >
                  {editSaving ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {shareStatement && (
        <ShareModal
          itemType="STATEMENT"
          itemId={shareStatement.id}
          itemName={`${shareStatement.source_name || 'Statement'} (${formatDate(shareStatement.period_start)} — ${formatDate(shareStatement.period_end)})`}
          onClose={() => setShareStatement(null)}
        />
      )}

      {deleteTarget && (
        <DeleteStatementDialog
          orgId={orgId}
          statementId={deleteTarget.id}
          statementName={deleteTarget.source_name}
          onClose={() => setDeleteTarget(null)}
          onDeleted={handleDeleted}
        />
      )}

      {bulkDeleteOpen && selectedIds.size > 0 && (
        <DeleteStatementDialog
          orgId={orgId}
          statementIds={Array.from(selectedIds)}
          onClose={() => setBulkDeleteOpen(false)}
          onDeleted={handleBulkDeleted}
        />
      )}
    </div>
  )
}

function EarningsTab({ orgId, selectedCreatorId }) {
  const [view, setView] = useState('overview')
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)
  const [summary, setSummary] = useState(null)
  const [statements, setStatements] = useState([])

  useEffect(() => {
    if (!orgId) return
    const url = selectedCreatorId
      ? `/api/royalties/dashboard/${orgId}?creator_id=${selectedCreatorId}`
      : `/api/royalties/dashboard/${orgId}`
    axios.get(url).then(res => {
      setSummary(res.data)
      setStatements(res.data.recent_statements || [])
    }).catch(() => {})
  }, [orgId, selectedCreatorId])

  const loadData = useCallback(async () => {
    if (!orgId) return
    if (view === 'overview') { setLoading(false); return }
    setLoading(true)
    const endpoints = {
      holder: `/api/royalties/earnings/${orgId}/by-holder`,
      contract: `/api/royalties/earnings/${orgId}/by-contract`,
      track: `/api/royalties/earnings/${orgId}/by-track`,
    }
    try {
      const params = selectedCreatorId ? { creator_id: selectedCreatorId } : {}
      const res = await axios.get(endpoints[view], { params })
      setData(Array.isArray(res.data) ? res.data : res.data.earnings || res.data.data || [])
    } catch (err) {
      console.error('Failed to load earnings:', err)
      setData([])
    } finally {
      setLoading(false)
    }
  }, [orgId, view, selectedCreatorId])

  useEffect(() => { loadData() }, [loadData])

  const viewButtons = [
    { key: 'overview', label: 'Overview', icon: CurrencyDollarIcon },
    { key: 'track', label: 'By Track', icon: MusicalNoteIcon },
    { key: 'holder', label: 'By Rights Holder', icon: UserGroupIcon },
    { key: 'contract', label: 'By Contract', icon: DocumentDuplicateIcon },
  ]

  const totalEarnings = summary?.total_revenue_cents || 0
  const stmtCount = statements.length || (summary?.revenue_by_source?.length || 0)

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-gradient-to-br from-[rgba(91,138,114,0.08)] to-[rgba(123,165,148,0.08)] backdrop-blur-xl rounded-[18px] shadow-am p-5 border border-[rgba(91,138,114,0.15)]">
          <span className="text-sm font-medium text-[#7A8580]">Total Earnings</span>
          <p className="text-2xl font-bold text-[#5B8A72] mt-1">{formatCents(totalEarnings)}</p>
        </div>
        <div className="bg-white/80 backdrop-blur-xl rounded-[18px] shadow-am p-5 border border-[rgba(59,77,67,0.08)]">
          <span className="text-sm font-medium text-[#7A8580]">Statements Processed</span>
          <p className="text-2xl font-bold text-[#3D4A44] mt-1">{stmtCount}</p>
        </div>
        <div className="bg-white/80 backdrop-blur-xl rounded-[18px] shadow-am p-5 border border-[rgba(59,77,67,0.08)]">
          <span className="text-sm font-medium text-[#7A8580]">Sources</span>
          <p className="text-2xl font-bold text-[#3D4A44] mt-1">
            {(summary?.revenue_by_source || []).map(s => s.source).filter(Boolean).join(', ') || '—'}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2 flex-wrap">
        {viewButtons.map(btn => (
          <button
            key={btn.key}
            onClick={() => setView(btn.key)}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all ${
              view === btn.key
                ? 'bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white shadow-am-button'
                : 'bg-white/80 text-[#7A8580] hover:bg-[rgba(91,138,114,0.08)] border border-[rgba(59,77,67,0.08)]'
            }`}
          >
            <btn.icon className="w-4 h-4" /> {btn.label}
          </button>
        ))}
      </div>

      {view === 'overview' && (
        <div className="bg-white/80 backdrop-blur-xl rounded-[18px] shadow-am border border-[rgba(59,77,67,0.08)]">
          <div className="p-6 border-b border-[rgba(59,77,67,0.08)]">
            <h3 className="text-lg font-semibold text-[#3D4A44]">Earnings by Source</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-[#EEF1EC]">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Source</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-[#7A8580] uppercase">Revenue</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[rgba(59,77,67,0.06)]">
                {(summary?.revenue_by_source || []).map((src, i) => (
                  <tr key={i} className="hover:bg-[rgba(91,138,114,0.04)]">
                    <td className="px-6 py-4 text-sm font-medium text-[#3D4A44]">{src.source || 'Unknown'}</td>
                    <td className="px-6 py-4 text-sm text-right font-medium text-[#3D4A44]">{formatCents(src.total_cents)}</td>
                  </tr>
                ))}
                {(summary?.revenue_by_source || []).length === 0 && (
                  <tr><td colSpan={2} className="px-6 py-12 text-center text-sm text-[#7A8580]">No earnings yet. Upload royalty statements to see your earnings.</td></tr>
                )}
              </tbody>
              {(summary?.revenue_by_source || []).length > 0 && (
                <tfoot className="bg-[rgba(91,138,114,0.04)]">
                  <tr>
                    <td className="px-6 py-4 text-sm font-bold text-[#3D4A44]">Total</td>
                    <td className="px-6 py-4 text-sm text-right font-bold text-[#5B8A72]">{formatCents(totalEarnings)}</td>
                  </tr>
                </tfoot>
              )}
            </table>
          </div>

          {statements.length > 0 && (
            <>
              <div className="p-6 border-t border-[rgba(59,77,67,0.08)] border-b border-[rgba(59,77,67,0.08)]">
                <h3 className="text-lg font-semibold text-[#3D4A44]">Statement History</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-[#EEF1EC]">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Source</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Period</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Currency</th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-[#7A8580] uppercase">Revenue</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[rgba(59,77,67,0.06)]">
                    {statements.map((stmt, i) => (
                      <tr key={i} className="hover:bg-[rgba(91,138,114,0.04)]">
                        <td className="px-6 py-4 text-sm font-medium text-[#3D4A44]">{stmt.source || '—'}</td>
                        <td className="px-6 py-4 text-sm text-[#7A8580]">{stmt.period_start || '—'}</td>
                        <td className="px-6 py-4 text-sm text-[#7A8580]">{stmt.currency || 'USD'}</td>
                        <td className="px-6 py-4 text-sm text-right font-medium text-[#3D4A44]">{formatCents(stmt.total_cents)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      )}

      {view !== 'overview' && loading && <LoadingSpinner message="Loading earnings..." />}

      {view !== 'overview' && !loading && (
        <div className="bg-white/80 backdrop-blur-xl rounded-[18px] shadow-am border border-[rgba(59,77,67,0.08)]">
          <div className="overflow-x-auto">
            {view === 'holder' && (
              <table className="w-full">
                <thead className="bg-[#EEF1EC]">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Client</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-[#7A8580] uppercase">Total Revenue</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-[#7A8580] uppercase">Net Earned</th>
                    <th className="px-6 py-3 text-center text-xs font-medium text-[#7A8580] uppercase">Statements</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[rgba(59,77,67,0.06)]">
                  {data.map((row, i) => (
                    <tr key={i} className="hover:bg-[rgba(91,138,114,0.04)]">
                      <td className="px-6 py-4 text-sm font-medium text-[#3D4A44]">{row.rights_holder_name || '—'}</td>
                      <td className="px-6 py-4 text-sm text-right font-medium text-[#3D4A44]">{formatCents(row.total_revenue_cents)}</td>
                      <td className="px-6 py-4 text-sm text-right text-[#7A8580]">{formatCents(row.net_earned_cents)}</td>
                      <td className="px-6 py-4 text-sm text-center text-[#7A8580]">{row.statement_count || 0}</td>
                    </tr>
                  ))}
                  {data.length === 0 && (
                    <tr><td colSpan={4} className="px-6 py-12 text-center text-sm text-[#7A8580]">
                      No client earnings yet. Assign statements to clients to see their earnings here.
                    </td></tr>
                  )}
                </tbody>
              </table>
            )}

            {view === 'contract' && (
              <table className="w-full">
                <thead className="bg-[#EEF1EC]">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Contract</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Recoupment %</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-[#7A8580] uppercase">Total Allocated</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-[#7A8580] uppercase">Advance</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-[#7A8580] uppercase">Recouped</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-[#7A8580] uppercase">Balance</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[rgba(59,77,67,0.06)]">
                  {data.map((row, i) => (
                    <tr key={i} className="hover:bg-[rgba(91,138,114,0.04)]">
                      <td className="px-6 py-4 text-sm font-medium text-[#3D4A44]">{row.contract_title || '—'}</td>
                      <td className="px-6 py-4 text-sm text-[#7A8580]">{row.recoupment_percentage ? `${row.recoupment_percentage}%` : '—'}</td>
                      <td className="px-6 py-4 text-sm text-right font-medium text-[#3D4A44]">{formatCents(row.total_allocated_cents)}</td>
                      <td className="px-6 py-4 text-sm text-right text-[#7A8580]">{formatDollars(row.advance_amount)}</td>
                      <td className="px-6 py-4 text-sm text-right text-[#7A8580]">{formatDollars(row.advance_recouped)}</td>
                      <td className="px-6 py-4 text-sm text-right font-medium text-[#3D4A44]">{formatDollars(row.remaining_advance)}</td>
                    </tr>
                  ))}
                  {data.length === 0 && (
                    <tr><td colSpan={6} className="px-6 py-12 text-center text-sm text-[#7A8580]">No contract earnings data available.</td></tr>
                  )}
                </tbody>
              </table>
            )}

            {view === 'track' && (
              <table className="w-full">
                <thead className="bg-[#EEF1EC]">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Track</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Artist</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-[#7A8580] uppercase">Total Revenue</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-[#7A8580] uppercase">Streams</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[rgba(59,77,67,0.06)]">
                  {data.map((row, i) => (
                    <tr key={i} className="hover:bg-[rgba(91,138,114,0.04)]">
                      <td className="px-6 py-4 text-sm font-medium text-[#3D4A44]">
                        {row.title || '—'}
                        {row.unmatched && <span className="ml-2 px-1.5 py-0.5 text-[10px] font-medium bg-[#F5E6D3] text-[#C4956B] rounded">Unmatched</span>}
                      </td>
                      <td className="px-6 py-4 text-sm text-[#7A8580]">{row.artist || '—'}</td>
                      <td className="px-6 py-4 text-sm text-right font-medium text-[#3D4A44]">{formatCents(row.total_revenue_cents)}</td>
                      <td className="px-6 py-4 text-sm text-right text-[#7A8580]">{(row.total_quantity || 0).toLocaleString()}</td>
                    </tr>
                  ))}
                  {data.length === 0 && (
                    <tr><td colSpan={4} className="px-6 py-12 text-center text-sm text-[#7A8580]">No track earnings data available.</td></tr>
                  )}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

const EXPENSE_CATEGORIES = [
  { value: 'PRODUCER_FEE', label: 'Producer Fee' },
  { value: 'DAY_RATE', label: 'Day Rate' },
  { value: 'VIDEO_PRODUCTION', label: 'Video Production' },
  { value: 'CONTENT_CREATION', label: 'Content Creation' },
  { value: 'LEGAL', label: 'Legal' },
  { value: 'MARKETING', label: 'Marketing' },
  { value: 'TRAVEL', label: 'Travel' },
  { value: 'STUDIO', label: 'Studio' },
  { value: 'MIXING_MASTERING', label: 'Mixing/Mastering' },
  { value: 'OTHER', label: 'Other' },
]

const EXPENSE_STATUS_COLORS = {
  PENDING: { bg: 'bg-amber-100', text: 'text-amber-700' },
  APPROVED: { bg: 'bg-blue-100', text: 'text-blue-700' },
  PAID: { bg: 'bg-green-100', text: 'text-green-700' },
  CANCELLED: { bg: 'bg-red-100', text: 'text-red-700' },
}

const getCategoryLabel = (val) => {
  const cat = EXPENSE_CATEGORIES.find(c => c.value === val)
  return cat ? cat.label : val
}

function MoneyOutTab({ orgId, creators, contracts }) {
  const [subTab, setSubTab] = useState('expenses')

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 mb-2">
        <button
          onClick={() => setSubTab('expenses')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all ${
            subTab === 'expenses'
              ? 'bg-[rgba(91,138,114,0.12)] text-[#5B8A72] border border-[rgba(91,138,114,0.2)]'
              : 'text-[#7A8580] hover:text-[#3D4A44] hover:bg-[rgba(91,138,114,0.06)]'
          }`}
        >
          <ArrowUpTrayIcon className="w-4 h-4" /> Expenses
        </button>
        <button
          onClick={() => setSubTab('payments')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all ${
            subTab === 'payments'
              ? 'bg-[rgba(91,138,114,0.12)] text-[#5B8A72] border border-[rgba(91,138,114,0.2)]'
              : 'text-[#7A8580] hover:text-[#3D4A44] hover:bg-[rgba(91,138,114,0.06)]'
          }`}
        >
          <BanknotesIcon className="w-4 h-4" /> Payments
        </button>
      </div>

      {subTab === 'expenses' && <ExpensesSubTab orgId={orgId} creators={creators} contracts={contracts} />}
      {subTab === 'payments' && <PaymentsSubTab orgId={orgId} creators={creators} contracts={contracts} />}
    </div>
  )
}

function ExpensesSubTab({ orgId, creators, contracts }) {
  const [expenses, setExpenses] = useState([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [creating, setCreating] = useState(false)
  const [categoryFilter, setCategoryFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [form, setForm] = useState({
    category: 'OTHER',
    description: '',
    amount: '',
    payee_name: '',
    creator_id: '',
    contract_id: '',
    expense_date: '',
    payment_method: '',
    invoice_reference: '',
    budget_source: '',
    notes: '',
  })

  const loadExpenses = useCallback(async () => {
    if (!orgId) return
    try {
      let url = `/api/expenses/org/${orgId}`
      const params = new URLSearchParams()
      if (categoryFilter) params.append('category', categoryFilter)
      if (statusFilter) params.append('status', statusFilter)
      if (params.toString()) url += `?${params.toString()}`
      const res = await axios.get(url)
      setExpenses(Array.isArray(res.data) ? res.data : [])
    } catch (err) {
      console.error('Failed to load expenses:', err)
    } finally {
      setLoading(false)
    }
  }, [orgId, categoryFilter, statusFilter])

  useEffect(() => { loadExpenses() }, [loadExpenses])

  const handleCreate = async () => {
    if (!form.description || !form.amount) return
    setCreating(true)
    try {
      await axios.post(`/api/expenses/org/${orgId}`, {
        category: form.category,
        description: form.description,
        amount_cents: Math.round(parseFloat(form.amount) * 100),
        payee_name: form.payee_name || null,
        creator_id: form.creator_id ? parseInt(form.creator_id) : null,
        contract_id: form.contract_id ? parseInt(form.contract_id) : null,
        expense_date: form.expense_date || null,
        payment_method: form.payment_method || null,
        invoice_reference: form.invoice_reference || null,
        budget_source: form.budget_source || null,
        notes: form.notes || null,
      })
      setShowCreate(false)
      setForm({ category: 'OTHER', description: '', amount: '', payee_name: '', creator_id: '', contract_id: '', expense_date: '', payment_method: '', invoice_reference: '', budget_source: '', notes: '' })
      loadExpenses()
    } catch (err) {
      console.error('Failed to create expense:', err)
    } finally {
      setCreating(false)
    }
  }

  const handleUpdateStatus = async (expenseId, newStatus) => {
    try {
      await axios.patch(`/api/expenses/${expenseId}/status`, { status: newStatus })
      loadExpenses()
    } catch (err) {
      console.error('Failed to update expense status:', err)
    }
  }

  const handleDelete = async (expenseId) => {
    if (!window.confirm('Delete this expense? This cannot be undone.')) return
    try {
      await axios.delete(`/api/expenses/${expenseId}`)
      loadExpenses()
    } catch (err) {
      console.error('Failed to delete expense:', err)
    }
  }

  if (loading) return <LoadingSpinner message="Loading expenses..." />

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <select value={categoryFilter} onChange={e => setCategoryFilter(e.target.value)} className="px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm text-[#3D4A44] bg-white focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent outline-none">
            <option value="">All Categories</option>
            {EXPENSE_CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
          </select>
          <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm text-[#3D4A44] bg-white focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent outline-none">
            <option value="">All Statuses</option>
            <option value="PENDING">Pending</option>
            <option value="APPROVED">Approved</option>
            <option value="PAID">Paid</option>
            <option value="CANCELLED">Cancelled</option>
          </select>
        </div>
        <button onClick={() => setShowCreate(true)} className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-xl hover:shadow-[0px_4px_12px_rgba(91,138,114,0.3)] transition-all text-sm font-medium">
          <PlusIcon className="w-4 h-4" /> Add Expense
        </button>
      </div>

      <div className="bg-white/80 backdrop-blur-xl rounded-[18px] shadow-am border border-[rgba(59,77,67,0.08)]">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-[#EEF1EC]">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Date</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Category</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Description</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Payee</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-[#7A8580] uppercase">Amount</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Status</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-[#7A8580] uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[rgba(59,77,67,0.06)]">
              {expenses.map(e => (
                <tr key={e.id} className="hover:bg-[rgba(91,138,114,0.04)]">
                  <td className="px-6 py-4 text-sm text-[#7A8580]">{formatDate(e.expense_date)}</td>
                  <td className="px-6 py-4">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-[rgba(91,138,114,0.1)] text-[#5B8A72]">
                      {getCategoryLabel(e.category)}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-[#3D4A44]">{e.description || '—'}</td>
                  <td className="px-6 py-4 text-sm text-[#7A8580]">{e.payee_name || e.creator_name || '—'}</td>
                  <td className="px-6 py-4 text-sm text-right font-medium text-[#3D4A44]">{formatCents(e.amount_cents)}</td>
                  <td className="px-6 py-4"><StatusBadge status={e.status || 'PENDING'} colorMap={EXPENSE_STATUS_COLORS} /></td>
                  <td className="px-6 py-4">
                    <div className="flex items-center justify-end gap-1">
                      {e.status === 'PENDING' && (
                        <button onClick={() => handleUpdateStatus(e.id, 'APPROVED')} className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 transition-colors font-medium">
                          Approve
                        </button>
                      )}
                      {e.status === 'APPROVED' && (
                        <button onClick={() => handleUpdateStatus(e.id, 'PAID')} className="px-2 py-1 text-xs bg-green-100 text-green-700 rounded-lg hover:bg-green-200 transition-colors font-medium">
                          Mark Paid
                        </button>
                      )}
                      {(e.status === 'PENDING' || e.status === 'APPROVED') && (
                        <button onClick={() => handleUpdateStatus(e.id, 'CANCELLED')} className="px-2 py-1 text-xs bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors font-medium">
                          Cancel
                        </button>
                      )}
                      <button onClick={() => handleDelete(e.id)} className="p-1.5 text-[#7A8580] hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors">
                        <TrashIcon className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {expenses.length === 0 && (
                <tr><td colSpan={7} className="px-6 py-12 text-center text-sm text-[#7A8580]">No expenses recorded yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm p-4">
          <div className="bg-white rounded-[18px] shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-6 border-b border-[rgba(59,77,67,0.08)]">
              <h3 className="text-lg font-semibold text-[#3D4A44]">Add Expense</h3>
              <button onClick={() => setShowCreate(false)} className="p-2 hover:bg-[rgba(59,77,67,0.06)] rounded-full transition-colors">
                <XMarkIcon className="w-5 h-5 text-[#7A8580]" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Category</label>
                <select value={form.category} onChange={e => setForm(prev => ({ ...prev, category: e.target.value }))} className="w-full px-4 py-2.5 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm text-[#3D4A44] bg-white focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent outline-none">
                  {EXPENSE_CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Description</label>
                <input type="text" value={form.description} onChange={e => setForm(prev => ({ ...prev, description: e.target.value }))} placeholder="Expense description" className="w-full px-4 py-2.5 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm text-[#3D4A44] bg-white focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent outline-none" />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Amount ($)</label>
                <input type="number" step="0.01" value={form.amount} onChange={e => setForm(prev => ({ ...prev, amount: e.target.value }))} placeholder="0.00" className="w-full px-4 py-2.5 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm text-[#3D4A44] bg-white focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent outline-none" />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Payee Name</label>
                <input type="text" value={form.payee_name} onChange={e => setForm(prev => ({ ...prev, payee_name: e.target.value }))} placeholder="Who was paid" className="w-full px-4 py-2.5 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm text-[#3D4A44] bg-white focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent outline-none" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Creator (optional)</label>
                  <select value={form.creator_id} onChange={e => setForm(prev => ({ ...prev, creator_id: e.target.value }))} className="w-full px-4 py-2.5 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm text-[#3D4A44] bg-white focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent outline-none">
                    <option value="">None</option>
                    {(creators || []).map(c => <option key={c.id} value={c.id}>{c.display_name || c.name || c.artist_name}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Contract (optional)</label>
                  <select value={form.contract_id} onChange={e => setForm(prev => ({ ...prev, contract_id: e.target.value }))} className="w-full px-4 py-2.5 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm text-[#3D4A44] bg-white focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent outline-none">
                    <option value="">None</option>
                    {(contracts || []).map(c => <option key={c.id} value={c.id}>{c.title}</option>)}
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Expense Date</label>
                <input type="date" value={form.expense_date} onChange={e => setForm(prev => ({ ...prev, expense_date: e.target.value }))} className="w-full px-4 py-2.5 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm text-[#3D4A44] bg-white focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent outline-none" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Payment Method</label>
                  <input type="text" value={form.payment_method} onChange={e => setForm(prev => ({ ...prev, payment_method: e.target.value }))} placeholder="e.g. Wire, Check" className="w-full px-4 py-2.5 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm text-[#3D4A44] bg-white focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent outline-none" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Invoice Reference</label>
                  <input type="text" value={form.invoice_reference} onChange={e => setForm(prev => ({ ...prev, invoice_reference: e.target.value }))} placeholder="INV-001" className="w-full px-4 py-2.5 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm text-[#3D4A44] bg-white focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent outline-none" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Budget Source</label>
                <input type="text" value={form.budget_source} onChange={e => setForm(prev => ({ ...prev, budget_source: e.target.value }))} placeholder="e.g. Client Budget, Label Budget" className="w-full px-4 py-2.5 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm text-[#3D4A44] bg-white focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent outline-none" />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Notes</label>
                <textarea value={form.notes} onChange={e => setForm(prev => ({ ...prev, notes: e.target.value }))} rows={3} placeholder="Optional notes..." className="w-full px-4 py-2.5 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm text-[#3D4A44] bg-white focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent outline-none resize-none" />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-sm text-[#7A8580] hover:text-[#3D4A44] transition-colors">Cancel</button>
                <button
                  onClick={handleCreate}
                  disabled={!form.description || !form.amount || creating}
                  className="px-5 py-2.5 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-xl hover:shadow-[0px_4px_12px_rgba(91,138,114,0.3)] transition-all text-sm font-medium disabled:opacity-50"
                >
                  {creating ? 'Creating...' : 'Add Expense'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function PaymentsSubTab({ orgId, creators, contracts }) {
  const [payments, setPayments] = useState([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [creating, setCreating] = useState(false)
  const [form, setForm] = useState({
    payee_id: '',
    contract_id: '',
    amount: '',
    period_start: '',
    period_end: '',
    payment_method: '',
    notes: '',
  })

  const loadPayments = useCallback(async () => {
    if (!orgId) return
    try {
      const res = await axios.get(`/api/royalties/payments/${orgId}`)
      setPayments(Array.isArray(res.data) ? res.data : res.data.payments || [])
    } catch (err) {
      console.error('Failed to load payments:', err)
    } finally {
      setLoading(false)
    }
  }, [orgId])

  useEffect(() => { loadPayments() }, [loadPayments])

  const handleCreate = async () => {
    if (!form.payee_id || !form.amount) return
    setCreating(true)
    try {
      await axios.post(`/api/royalties/payments/${orgId}`, {
        ...form,
        payee_id: parseInt(form.payee_id),
        contract_id: form.contract_id ? parseInt(form.contract_id) : null,
        amount: Math.round(parseFloat(form.amount) * 100),
      })
      setShowCreate(false)
      setForm({ payee_id: '', contract_id: '', amount: '', period_start: '', period_end: '', payment_method: '', notes: '' })
      loadPayments()
    } catch (err) {
      console.error('Failed to create payment:', err)
    } finally {
      setCreating(false)
    }
  }

  const handleUpdateStatus = async (paymentId, newStatus) => {
    try {
      await axios.patch(`/api/royalties/payments/${orgId}/${paymentId}`, { status: newStatus })
      loadPayments()
    } catch (err) {
      console.error('Failed to update payment:', err)
    }
  }

  if (loading) return <LoadingSpinner message="Loading payments..." />

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-[#3D4A44]">Royalty Payments</h3>
        <button onClick={() => setShowCreate(true)} className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-xl hover:shadow-[0px_4px_12px_rgba(91,138,114,0.3)] transition-all text-sm font-medium">
          <PlusIcon className="w-4 h-4" /> Create Payment
        </button>
      </div>

      <div className="bg-white/80 backdrop-blur-xl rounded-[18px] shadow-am border border-[rgba(59,77,67,0.08)]">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-[#EEF1EC]">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Payee</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Contract</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-[#7A8580] uppercase">Amount</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Period</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Date</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-[#7A8580] uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[rgba(59,77,67,0.06)]">
              {payments.map(p => (
                <tr key={p.id} className="hover:bg-[rgba(91,138,114,0.04)]">
                  <td className="px-6 py-4 text-sm font-medium text-[#3D4A44]">{p.payee_name || p.payee || '—'}</td>
                  <td className="px-6 py-4 text-sm text-[#7A8580]">{p.contract_title || p.contract || '—'}</td>
                  <td className="px-6 py-4 text-sm text-right font-medium text-[#3D4A44]">{formatCents(p.amount)}</td>
                  <td className="px-6 py-4 text-sm text-[#7A8580]">{formatDate(p.period_start)} — {formatDate(p.period_end)}</td>
                  <td className="px-6 py-4"><StatusBadge status={p.status || 'PENDING'} colorMap={PAYMENT_STATUS_COLORS} /></td>
                  <td className="px-6 py-4 text-sm text-[#7A8580]">{formatDate(p.created_at || p.date)}</td>
                  <td className="px-6 py-4">
                    <div className="flex items-center justify-end gap-1">
                      {p.status === 'PENDING' && (
                        <button onClick={() => handleUpdateStatus(p.id, 'APPROVED')} className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 transition-colors font-medium">
                          Approve
                        </button>
                      )}
                      {p.status === 'APPROVED' && (
                        <button onClick={() => handleUpdateStatus(p.id, 'PAID')} className="px-2 py-1 text-xs bg-green-100 text-green-700 rounded-lg hover:bg-green-200 transition-colors font-medium">
                          Mark Paid
                        </button>
                      )}
                      {(p.status === 'PENDING' || p.status === 'APPROVED') && (
                        <button onClick={() => handleUpdateStatus(p.id, 'CANCELLED')} className="px-2 py-1 text-xs bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors font-medium">
                          Cancel
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
              {payments.length === 0 && (
                <tr><td colSpan={7} className="px-6 py-12 text-center text-sm text-[#7A8580]">No payments recorded yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm p-4">
          <div className="bg-white rounded-[18px] shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-6 border-b border-[rgba(59,77,67,0.08)]">
              <h3 className="text-lg font-semibold text-[#3D4A44]">Create Payment</h3>
              <button onClick={() => setShowCreate(false)} className="p-2 hover:bg-[rgba(59,77,67,0.06)] rounded-full transition-colors">
                <XMarkIcon className="w-5 h-5 text-[#7A8580]" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Payee</label>
                <select value={form.payee_id} onChange={e => setForm(prev => ({ ...prev, payee_id: e.target.value }))} className="w-full px-4 py-2.5 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm text-[#3D4A44] bg-white focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent outline-none">
                  <option value="">Select payee...</option>
                  {(creators || []).map(c => <option key={c.id} value={c.id}>{c.display_name || c.name || c.artist_name}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Contract (optional)</label>
                <select value={form.contract_id} onChange={e => setForm(prev => ({ ...prev, contract_id: e.target.value }))} className="w-full px-4 py-2.5 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm text-[#3D4A44] bg-white focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent outline-none">
                  <option value="">Select contract...</option>
                  {(contracts || []).map(c => <option key={c.id} value={c.id}>{c.title}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Amount ($)</label>
                <input type="number" step="0.01" value={form.amount} onChange={e => setForm(prev => ({ ...prev, amount: e.target.value }))} placeholder="0.00" className="w-full px-4 py-2.5 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm text-[#3D4A44] bg-white focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent outline-none" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Period Start</label>
                  <input type="date" value={form.period_start} onChange={e => setForm(prev => ({ ...prev, period_start: e.target.value }))} className="w-full px-4 py-2.5 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm text-[#3D4A44] bg-white focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent outline-none" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Period End</label>
                  <input type="date" value={form.period_end} onChange={e => setForm(prev => ({ ...prev, period_end: e.target.value }))} className="w-full px-4 py-2.5 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm text-[#3D4A44] bg-white focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent outline-none" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Payment Method</label>
                <input type="text" value={form.payment_method} onChange={e => setForm(prev => ({ ...prev, payment_method: e.target.value }))} placeholder="e.g. Wire Transfer, Check, PayPal" className="w-full px-4 py-2.5 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm text-[#3D4A44] bg-white focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent outline-none" />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Notes</label>
                <textarea value={form.notes} onChange={e => setForm(prev => ({ ...prev, notes: e.target.value }))} rows={3} placeholder="Optional notes..." className="w-full px-4 py-2.5 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm text-[#3D4A44] bg-white focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent outline-none resize-none" />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-sm text-[#7A8580] hover:text-[#3D4A44] transition-colors">Cancel</button>
                <button
                  onClick={handleCreate}
                  disabled={!form.payee_id || !form.amount || creating}
                  className="px-5 py-2.5 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-xl hover:shadow-[0px_4px_12px_rgba(91,138,114,0.3)] transition-all text-sm font-medium disabled:opacity-50"
                >
                  {creating ? 'Creating...' : 'Create Payment'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function LoadingSpinner({ message }) {
  return (
    <div className="flex items-center justify-center py-16">
      <div className="text-center">
        <div className="inline-block animate-spin rounded-full h-10 w-10 border-4 border-[#5B8A72] border-t-transparent"></div>
        <p className="mt-3 text-sm text-[#7A8580]">{message}</p>
      </div>
    </div>
  )
}

function EmptyState({ icon: Icon, title, message }) {
  return (
    <div className="flex items-center justify-center py-16">
      <div className="text-center">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] rounded-full mb-4">
          <Icon className="w-8 h-8 text-white" />
        </div>
        <h3 className="text-lg font-semibold text-[#3D4A44] mb-2">{title}</h3>
        <p className="text-sm text-[#7A8580] max-w-md">{message}</p>
      </div>
    </div>
  )
}

function FeesAdvancesTab({ orgId, creators }) {
  const [fees, setFees] = useState([])
  const [advances, setAdvances] = useState([])
  const [loadingFees, setLoadingFees] = useState(true)
  const [loadingAdvances, setLoadingAdvances] = useState(true)
  const [showAddFeeModal, setShowAddFeeModal] = useState(false)
  const [showAddAdvanceModal, setShowAddAdvanceModal] = useState(false)
  const [feeForm, setFeeForm] = useState({ creator_id: '', fee_type: 'MANAGEMENT_FEE', description: '', amount: '', fee_date: '', notes: '' })
  const [advanceForm, setAdvanceForm] = useState({ creator_id: '', description: '', amount: '', advance_date: '', notes: '' })
  const [savingFee, setSavingFee] = useState(false)
  const [savingAdvance, setSavingAdvance] = useState(false)

  const loadFees = useCallback(async () => {
    if (!orgId) return
    try {
      const res = await axios.get(`/api/royalties/fees/${orgId}`)
      setFees(Array.isArray(res.data) ? res.data : res.data.fees || [])
    } catch (err) {
      console.error('Failed to load fees:', err)
    } finally {
      setLoadingFees(false)
    }
  }, [orgId])

  const loadAdvances = useCallback(async () => {
    if (!orgId) return
    try {
      const res = await axios.get(`/api/royalties/advances/${orgId}`)
      setAdvances(Array.isArray(res.data) ? res.data : res.data.advances || [])
    } catch (err) {
      console.error('Failed to load advances:', err)
    } finally {
      setLoadingAdvances(false)
    }
  }, [orgId])

  useEffect(() => { loadFees(); loadAdvances() }, [loadFees, loadAdvances])

  const handleCreateFee = async () => {
    if (!feeForm.creator_id || !feeForm.amount) return
    setSavingFee(true)
    try {
      await axios.post(`/api/royalties/fees/${orgId}`, {
        creator_id: parseInt(feeForm.creator_id),
        fee_type: feeForm.fee_type,
        description: feeForm.description,
        amount_cents: Math.round(parseFloat(feeForm.amount) * 100),
        fee_date: feeForm.fee_date || null,
        notes: feeForm.notes || null
      })
      setShowAddFeeModal(false)
      setFeeForm({ creator_id: '', fee_type: 'MANAGEMENT_FEE', description: '', amount: '', fee_date: '', notes: '' })
      loadFees()
    } catch (err) {
      console.error('Failed to create fee:', err)
      alert('Failed to create fee.')
    } finally {
      setSavingFee(false)
    }
  }

  const handleCreateAdvance = async () => {
    if (!advanceForm.creator_id || !advanceForm.amount) return
    setSavingAdvance(true)
    try {
      await axios.post(`/api/royalties/advances/${orgId}`, {
        creator_id: parseInt(advanceForm.creator_id),
        description: advanceForm.description,
        amount_cents: Math.round(parseFloat(advanceForm.amount) * 100),
        advance_date: advanceForm.advance_date || null,
        notes: advanceForm.notes || null
      })
      setShowAddAdvanceModal(false)
      setAdvanceForm({ creator_id: '', description: '', amount: '', advance_date: '', notes: '' })
      loadAdvances()
    } catch (err) {
      console.error('Failed to create advance:', err)
      alert('Failed to create advance.')
    } finally {
      setSavingAdvance(false)
    }
  }

  const handleDeleteFee = async (feeId) => {
    if (!window.confirm('Delete this fee? This cannot be undone.')) return
    try {
      await axios.delete(`/api/royalties/fees/${orgId}/${feeId}`)
      loadFees()
    } catch (err) {
      console.error('Failed to delete fee:', err)
    }
  }

  const handleDeleteAdvance = async (advanceId) => {
    if (!window.confirm('Delete this advance? This cannot be undone.')) return
    try {
      await axios.delete(`/api/royalties/advances/${orgId}/${advanceId}`)
      loadAdvances()
    } catch (err) {
      console.error('Failed to delete advance:', err)
    }
  }

  const getCreatorName = (creatorId) => {
    const c = (creators || []).find(cr => cr.id === creatorId)
    return c ? (c.display_name || c.name || c.artist_name || 'Unknown') : 'Unknown'
  }

  const formatAmount = (dollars) => {
    if (dollars == null) return '$0.00'
    return `$${Number(dollars).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  }

  const inputClass = "w-full border border-[rgba(59,77,67,0.15)] rounded-lg px-3 py-2 text-sm text-[#3D4A44] bg-white focus:outline-none focus:ring-2 focus:ring-[#5B8A72]/30"

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="bg-white/80 backdrop-blur-xl rounded-[18px] shadow-am border border-[rgba(59,77,67,0.08)]">
        <div className="flex items-center justify-between p-6 border-b border-[rgba(59,77,67,0.08)]">
          <h3 className="text-lg font-semibold text-[#3D4A44]">Fees</h3>
          <button onClick={() => setShowAddFeeModal(true)} className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-xl hover:shadow-[0px_4px_12px_rgba(91,138,114,0.3)] transition-all text-sm font-medium">
            <PlusIcon className="w-4 h-4" /> Add Fee
          </button>
        </div>
        {loadingFees ? <LoadingSpinner message="Loading fees..." /> : fees.length === 0 ? (
          <EmptyState icon={CalculatorIcon} title="No Fees" message="No fees have been recorded yet." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-[#EEF1EC]">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Creator</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Type</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Description</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Date</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-[#7A8580] uppercase">Amount</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Status</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-[#7A8580] uppercase"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[rgba(59,77,67,0.06)]">
                {fees.map(fee => (
                  <tr key={fee.id} className="hover:bg-[rgba(91,138,114,0.04)]">
                    <td className="px-4 py-3 text-sm font-medium text-[#3D4A44]">{getCreatorName(fee.creator_id)}</td>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-[rgba(91,138,114,0.1)] text-[#5B8A72]">
                        {(fee.fee_type || '').replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-[#7A8580]">{fee.description || '—'}</td>
                    <td className="px-4 py-3 text-sm text-[#7A8580]">{formatDate(fee.fee_date)}</td>
                    <td className="px-4 py-3 text-sm text-right font-medium text-[#3D4A44]">{formatAmount(fee.amount_dollars != null ? fee.amount_dollars : (fee.amount_cents || 0) / 100)}</td>
                    <td className="px-4 py-3">
                      {fee.status === 'PAID' ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">PAID</span>
                      ) : (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-[rgba(196,149,107,0.15)] text-[#C4956B]">{fee.status || 'PENDING'}</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <button onClick={() => handleDeleteFee(fee.id)} className="p-1.5 text-[#7A8580] hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors">
                        <TrashIcon className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="bg-white/80 backdrop-blur-xl rounded-[18px] shadow-am border border-[rgba(59,77,67,0.08)]">
        <div className="flex items-center justify-between p-6 border-b border-[rgba(59,77,67,0.08)]">
          <h3 className="text-lg font-semibold text-[#3D4A44]">Advances</h3>
          <button onClick={() => setShowAddAdvanceModal(true)} className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-xl hover:shadow-[0px_4px_12px_rgba(91,138,114,0.3)] transition-all text-sm font-medium">
            <PlusIcon className="w-4 h-4" /> Add Advance
          </button>
        </div>
        {loadingAdvances ? <LoadingSpinner message="Loading advances..." /> : advances.length === 0 ? (
          <EmptyState icon={BanknotesIcon} title="No Advances" message="No advances have been recorded yet." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-[#EEF1EC]">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Creator</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Description</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Date</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-[#7A8580] uppercase">Amount</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-[#7A8580] uppercase">Recouped</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-[#7A8580] uppercase">Remaining</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Status</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-[#7A8580] uppercase"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[rgba(59,77,67,0.06)]">
                {advances.map(adv => {
                  const amountDollars = adv.amount_dollars != null ? adv.amount_dollars : (adv.amount_cents || 0) / 100
                  const recoupedDollars = adv.recouped_dollars != null ? adv.recouped_dollars : (adv.recouped_cents || 0) / 100
                  const remainingDollars = adv.remaining_dollars != null ? adv.remaining_dollars : amountDollars - recoupedDollars
                  const pct = adv.recoupment_pct != null ? adv.recoupment_pct : (amountDollars > 0 ? Math.min((recoupedDollars / amountDollars) * 100, 100) : 0)
                  return (
                    <tr key={adv.id} className="hover:bg-[rgba(91,138,114,0.04)]">
                      <td className="px-4 py-3 text-sm font-medium text-[#3D4A44]">{getCreatorName(adv.creator_id)}</td>
                      <td className="px-4 py-3 text-sm text-[#7A8580]">{adv.description || '—'}</td>
                      <td className="px-4 py-3 text-sm text-[#7A8580]">{formatDate(adv.advance_date)}</td>
                      <td className="px-4 py-3 text-sm text-right font-medium text-[#3D4A44]">{formatAmount(amountDollars)}</td>
                      <td className="px-4 py-3 text-sm text-right text-[#7A8580]">{formatAmount(recoupedDollars)}</td>
                      <td className="px-4 py-3 text-sm text-right text-[#7A8580]">{formatAmount(remainingDollars)}</td>
                      <td className="px-4 py-3">
                        <div>
                          {adv.fully_recouped ? (
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-[rgba(91,154,110,0.15)] text-[#3D7A4E]">RECOUPED</span>
                          ) : (
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-[rgba(196,149,107,0.15)] text-[#C4956B]">ACTIVE</span>
                          )}
                          <div className="mt-1.5 w-full bg-[#EEF1EC] rounded-full h-1.5">
                            <div className="h-1.5 rounded-full bg-gradient-to-r from-[#5B8A72] to-[#7BA594] transition-all" style={{ width: `${pct}%` }} />
                          </div>
                          <span className="text-[10px] text-[#7A8580]">{pct.toFixed(1)}%</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <button onClick={() => handleDeleteAdvance(adv.id)} className="p-1.5 text-[#7A8580] hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors">
                          <TrashIcon className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showAddFeeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-sm p-4">
          <div className="bg-white rounded-[18px] shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-6 border-b border-[rgba(59,77,67,0.08)]">
              <h3 className="text-lg font-semibold text-[#3D4A44]">Add Fee</h3>
              <button onClick={() => setShowAddFeeModal(false)} className="p-2 hover:bg-[rgba(59,77,67,0.06)] rounded-full transition-colors">
                <XMarkIcon className="w-5 h-5 text-[#7A8580]" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Creator</label>
                <select value={feeForm.creator_id} onChange={e => setFeeForm(prev => ({ ...prev, creator_id: e.target.value }))} className={inputClass}>
                  <option value="">Select creator...</option>
                  {(creators || []).map(c => <option key={c.id} value={c.id}>{c.display_name || c.name || c.artist_name}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Fee Type</label>
                <select value={feeForm.fee_type} onChange={e => setFeeForm(prev => ({ ...prev, fee_type: e.target.value }))} className={inputClass}>
                  <option value="MANAGEMENT_FEE">Management Fee</option>
                  <option value="ADMIN_FEE">Admin Fee</option>
                  <option value="DISTRIBUTION_FEE">Distribution Fee</option>
                  <option value="SYNC_FEE">Sync Fee</option>
                  <option value="LEGAL_FEE">Legal Fee</option>
                  <option value="OTHER">Other</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Description</label>
                <input type="text" value={feeForm.description} onChange={e => setFeeForm(prev => ({ ...prev, description: e.target.value }))} placeholder="Fee description" className={inputClass} />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Amount ($)</label>
                <input type="number" step="0.01" value={feeForm.amount} onChange={e => setFeeForm(prev => ({ ...prev, amount: e.target.value }))} placeholder="0.00" className={inputClass} />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Date</label>
                <input type="date" value={feeForm.fee_date} onChange={e => setFeeForm(prev => ({ ...prev, fee_date: e.target.value }))} className={inputClass} />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Notes</label>
                <textarea value={feeForm.notes} onChange={e => setFeeForm(prev => ({ ...prev, notes: e.target.value }))} rows={3} placeholder="Optional notes..." className={`${inputClass} resize-none`} />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button onClick={() => setShowAddFeeModal(false)} className="px-4 py-2 text-sm text-[#7A8580] hover:text-[#3D4A44] transition-colors">Cancel</button>
                <button
                  onClick={handleCreateFee}
                  disabled={!feeForm.creator_id || !feeForm.amount || savingFee}
                  className="px-5 py-2.5 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-xl hover:shadow-[0px_4px_12px_rgba(91,138,114,0.3)] transition-all text-sm font-medium disabled:opacity-50"
                >
                  {savingFee ? 'Saving...' : 'Add Fee'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {showAddAdvanceModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-sm p-4">
          <div className="bg-white rounded-[18px] shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-6 border-b border-[rgba(59,77,67,0.08)]">
              <h3 className="text-lg font-semibold text-[#3D4A44]">Add Advance</h3>
              <button onClick={() => setShowAddAdvanceModal(false)} className="p-2 hover:bg-[rgba(59,77,67,0.06)] rounded-full transition-colors">
                <XMarkIcon className="w-5 h-5 text-[#7A8580]" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Creator</label>
                <select value={advanceForm.creator_id} onChange={e => setAdvanceForm(prev => ({ ...prev, creator_id: e.target.value }))} className={inputClass}>
                  <option value="">Select creator...</option>
                  {(creators || []).map(c => <option key={c.id} value={c.id}>{c.display_name || c.name || c.artist_name}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Description</label>
                <input type="text" value={advanceForm.description} onChange={e => setAdvanceForm(prev => ({ ...prev, description: e.target.value }))} placeholder="Advance description" className={inputClass} />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Amount ($)</label>
                <input type="number" step="0.01" value={advanceForm.amount} onChange={e => setAdvanceForm(prev => ({ ...prev, amount: e.target.value }))} placeholder="0.00" className={inputClass} />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Date</label>
                <input type="date" value={advanceForm.advance_date} onChange={e => setAdvanceForm(prev => ({ ...prev, advance_date: e.target.value }))} className={inputClass} />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Notes</label>
                <textarea value={advanceForm.notes} onChange={e => setAdvanceForm(prev => ({ ...prev, notes: e.target.value }))} rows={3} placeholder="Optional notes..." className={`${inputClass} resize-none`} />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button onClick={() => setShowAddAdvanceModal(false)} className="px-4 py-2 text-sm text-[#7A8580] hover:text-[#3D4A44] transition-colors">Cancel</button>
                <button
                  onClick={handleCreateAdvance}
                  disabled={!advanceForm.creator_id || !advanceForm.amount || savingAdvance}
                  className="px-5 py-2.5 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-xl hover:shadow-[0px_4px_12px_rgba(91,138,114,0.3)] transition-all text-sm font-medium disabled:opacity-50"
                >
                  {savingAdvance ? 'Saving...' : 'Add Advance'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function ProcessingTab({ orgId, creators = [], selectedCreatorId }) {
  const [selectedStatementId, setSelectedStatementId] = useState(null)
  const [statements, setStatements] = useState([])
  const [statementsLoading, setStatementsLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('')
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [selectedIds, setSelectedIds] = useState(() => new Set())
  const [bulkDeleteOpen, setBulkDeleteOpen] = useState(false)
  const [statementsPage, setStatementsPage] = useState(1)
  const STATEMENTS_PAGE_SIZE = 20
  const [uploading, setUploading] = useState(false)
  const [showUpload, setShowUpload] = useState(false)
  const [uploadForm, setUploadForm] = useState({ source_name: '', source_type: '', period_start: '', period_end: '', currency: 'USD', creator_id: selectedCreatorId || '' })
  const [uploadFile, setUploadFile] = useState(null)

  useEffect(() => {
    if (selectedCreatorId) setUploadForm(prev => ({ ...prev, creator_id: selectedCreatorId }))
  }, [selectedCreatorId])

  const loadStatements = useCallback(async () => {
    if (!orgId) return
    try {
      const params = new URLSearchParams()
      if (selectedCreatorId) params.append('creator_id', selectedCreatorId)
      const qs = params.toString()
      const res = await axios.get(`/api/royalties/statements/${orgId}${qs ? `?${qs}` : ''}`)
      const data = Array.isArray(res.data) ? res.data : res.data.statements || []
      setStatements(data)
    } catch (err) {
      console.error('Failed to load statements:', err)
    } finally {
      setStatementsLoading(false)
    }
  }, [orgId, selectedCreatorId])

  useEffect(() => { loadStatements() }, [loadStatements])

  useEffect(() => {
    if (statements.length === 0) return
    const present = new Set(statements.map(s => s.id))
    setSelectedIds(prev => {
      let changed = false
      const next = new Set()
      prev.forEach(id => { if (present.has(id)) next.add(id); else changed = true })
      return changed ? next : prev
    })
  }, [statements])

  const handleEnhancedUpload = async () => {
    if (!uploadFile || !uploadForm.source_name || !uploadForm.creator_id) return
    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', uploadFile)
      formData.append('source_name', uploadForm.source_name)
      if (uploadForm.source_type) formData.append('source_type', uploadForm.source_type)
      if (uploadForm.period_start) formData.append('period_start', uploadForm.period_start)
      if (uploadForm.period_end) formData.append('period_end', uploadForm.period_end)
      formData.append('currency', uploadForm.currency)
      formData.append('creator_id', uploadForm.creator_id)
      await axios.post(`/api/royalty-processing/${orgId}/statements/upload`, formData)
      setShowUpload(false)
      setUploadFile(null)
      setUploadForm({ source_name: '', source_type: '', period_start: '', period_end: '', currency: 'USD', creator_id: selectedCreatorId || '' })
      loadStatements()
    } catch (err) {
      console.error('Enhanced upload failed:', err)
      alert('Upload failed: ' + (err.response?.data?.detail || err.message))
    } finally {
      setUploading(false)
    }
  }

  const filteredStatements = statusFilter
    ? statements.filter(s => s.status === statusFilter)
    : statements

  useEffect(() => { setStatementsPage(1) }, [statusFilter])

  const totalPages = Math.max(1, Math.ceil(filteredStatements.length / STATEMENTS_PAGE_SIZE))
  const safePage = Math.min(statementsPage, totalPages)
  const pagedStatements = filteredStatements.slice(
    (safePage - 1) * STATEMENTS_PAGE_SIZE,
    safePage * STATEMENTS_PAGE_SIZE,
  )
  const visibleProcessingIds = pagedStatements.map(s => s.id)
  const allVisibleSelected = visibleProcessingIds.length > 0 && visibleProcessingIds.every(id => selectedIds.has(id))
  const someVisibleSelected = visibleProcessingIds.some(id => selectedIds.has(id)) && !allVisibleSelected

  const toggleSelected = (id) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id); else next.add(id)
      return next
    })
  }

  const toggleSelectAllVisible = () => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (allVisibleSelected) {
        visibleProcessingIds.forEach(id => next.delete(id))
      } else {
        visibleProcessingIds.forEach(id => next.add(id))
      }
      return next
    })
  }

  const handleBulkDeleted = () => {
    setSelectedIds(new Set())
    setBulkDeleteOpen(false)
    loadStatements()
  }

  const STATUS_OPTIONS = [
    { key: '', label: 'Show all statuses' },
    { key: 'UPLOADED', label: 'Uploaded' },
    { key: 'PARTIALLY_MATCHED', label: 'Partially Matched' },
    { key: 'REVIEW_REQUIRED', label: 'Review Required' },
    { key: 'FULLY_MATCHED', label: 'Fully Matched' },
    { key: 'PROCESSED', label: 'Processed' },
  ]

  if (selectedStatementId) {
    return (
      <StatementDetailView
        orgId={orgId}
        statementId={selectedStatementId}
        onBack={() => { setSelectedStatementId(null); loadStatements() }}
      />
    )
  }

  const inputClass = "w-full border border-[rgba(59,77,67,0.15)] rounded-lg px-3 py-2 text-sm text-[#3D4A44] bg-white focus:outline-none focus:ring-2 focus:ring-[#5B8A72]/30"

  return (
    <div className="space-y-6">
      <ProcessingInboxPanel orgId={orgId} onSelectStatement={(status) => setStatusFilter(status)} />

      <div className="bg-white/80 backdrop-blur-xl rounded-[18px] shadow-am p-6 border border-[rgba(59,77,67,0.08)]">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-[#3D4A44]">Enhanced Upload</h3>
          <button
            onClick={() => setShowUpload(!showUpload)}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-xl hover:shadow-[0px_4px_12px_rgba(91,138,114,0.3)] transition-all text-sm font-medium"
          >
            <ArrowUpTrayIcon className="w-4 h-4" /> Upload & Auto-Match
          </button>
        </div>
        <p className="text-sm text-[#7A8580]">Upload a statement file to create statement lines and automatically run matching.</p>

        {showUpload && (
          <div className="mt-4 space-y-4 border-t border-[rgba(59,77,67,0.08)] pt-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Client / Creator *</label>
                <select value={uploadForm.creator_id} onChange={e => setUploadForm(prev => ({ ...prev, creator_id: e.target.value }))} className={inputClass} disabled={!!selectedCreatorId}>
                  <option value="">Select a client...</option>
                  {creators.map(c => (
                    <option key={c.id} value={c.id}>{c.display_name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Source Name *</label>
                <input type="text" value={uploadForm.source_name} onChange={e => setUploadForm(prev => ({ ...prev, source_name: e.target.value }))} placeholder="e.g., Spotify, Apple Music" className={inputClass} />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Source Type</label>
                <select
                  value={uploadForm.source_type}
                  onChange={e => setUploadForm(prev => ({ ...prev, source_type: e.target.value }))}
                  className={inputClass}
                >
                  <option value="">Auto-detect from file</option>
                  {SOURCE_TYPE_OPTIONS.filter(o => o.value).map(o => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Period Start</label>
                <input type="date" value={uploadForm.period_start} onChange={e => setUploadForm(prev => ({ ...prev, period_start: e.target.value }))} className={inputClass} />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Period End</label>
                <input type="date" value={uploadForm.period_end} onChange={e => setUploadForm(prev => ({ ...prev, period_end: e.target.value }))} className={inputClass} />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-[#3D4A44] mb-1">File *</label>
              <input type="file" accept=".csv,.xlsx,.xls,.tsv,.pdf,application/pdf,text/csv,text/tab-separated-values,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel" onChange={e => setUploadFile(e.target.files?.[0] || null)} className="text-sm text-[#3D4A44]" />
            </div>
            <div className="flex justify-end gap-3">
              <button onClick={() => setShowUpload(false)} className="px-4 py-2 text-sm text-[#7A8580] hover:text-[#3D4A44] transition-colors">Cancel</button>
              <button
                onClick={handleEnhancedUpload}
                disabled={!uploadFile || !uploadForm.source_name || !uploadForm.creator_id || uploading}
                className="px-5 py-2.5 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-xl hover:shadow-[0px_4px_12px_rgba(91,138,114,0.3)] transition-all text-sm font-medium disabled:opacity-50"
              >
                {uploading ? 'Uploading & Matching...' : 'Upload & Auto-Match'}
              </button>
            </div>
          </div>
        )}
      </div>

      <div className="bg-white/80 backdrop-blur-xl rounded-[18px] shadow-am border border-[rgba(59,77,67,0.08)]">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-6 border-b border-[rgba(59,77,67,0.08)]">
          <div className="flex items-center gap-3 shrink-0">
            <h3 className="text-lg font-semibold text-[#3D4A44]">Recent Statements</h3>
            {visibleProcessingIds.length > 0 && (
              <label className="flex items-center gap-2 text-xs text-[#7A8580] cursor-pointer">
                <input
                  type="checkbox"
                  aria-label="Select all visible statements"
                  checked={allVisibleSelected}
                  ref={el => { if (el) el.indeterminate = someVisibleSelected }}
                  onChange={toggleSelectAllVisible}
                  className="h-4 w-4 rounded border-[rgba(59,77,67,0.3)] text-[#5B8A72] focus:ring-[#5B8A72]"
                />
                Select all
              </label>
            )}
            {selectedIds.size > 0 && (
              <button
                onClick={() => setBulkDeleteOpen(true)}
                className="flex items-center gap-2 px-3 py-1.5 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-all text-xs font-medium"
              >
                <TrashIcon className="w-3.5 h-3.5" /> Delete selected ({selectedIds.size})
              </button>
            )}
          </div>
          <div className="flex items-center gap-1 bg-white/60 backdrop-blur-xl rounded-[14px] p-1 border border-[rgba(59,77,67,0.08)] overflow-x-auto max-w-full">
            {STATUS_OPTIONS.map(opt => (
              <button
                key={opt.key}
                onClick={() => setStatusFilter(opt.key)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all whitespace-nowrap ${
                  statusFilter === opt.key
                    ? 'bg-[#5B8A72] text-white'
                    : 'text-[#7A8580] hover:text-[#3D4A44] hover:bg-[rgba(91,138,114,0.06)]'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
        {statementsLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-[#5B8A72] border-t-transparent"></div>
          </div>
        ) : filteredStatements.length === 0 ? (
          <div className="text-center py-12">
            <DocumentTextIcon className="w-12 h-12 text-[#7A8580] mx-auto mb-3 opacity-40" />
            <p className="text-sm text-[#7A8580]">{selectedCreatorId ? 'No statements for this client yet' : 'No statements found'}</p>
          </div>
        ) : (
          <div className="divide-y divide-[rgba(59,77,67,0.05)]">
            {pagedStatements.map(stmt => {
              const colors = STATEMENT_STATUS_COLORS[stmt.status] || { bg: 'bg-gray-100', text: 'text-gray-700' }
              return (
                <div
                  key={stmt.id}
                  className="w-full px-6 py-4 hover:bg-[rgba(91,138,114,0.04)] transition-colors flex items-center justify-between gap-3"
                >
                  <input
                    type="checkbox"
                    aria-label={`Select statement ${stmt.source_name || stmt.id}`}
                    checked={selectedIds.has(stmt.id)}
                    onChange={() => toggleSelected(stmt.id)}
                    onClick={e => e.stopPropagation()}
                    className="h-4 w-4 rounded border-[rgba(59,77,67,0.3)] text-[#5B8A72] focus:ring-[#5B8A72] flex-shrink-0"
                  />
                  <button
                    onClick={() => setSelectedStatementId(stmt.id)}
                    className="flex-1 min-w-0 text-left"
                  >
                    <div className="flex items-center gap-3">
                      <p className="text-sm font-medium text-[#3D4A44] truncate">{stmt.source_name || 'Statement'}</p>
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${colors.bg} ${colors.text}`}>
                        {stmt.status}
                      </span>
                    </div>
                    <p className="text-xs text-[#7A8580] mt-1">
                      {stmt.period_start && stmt.period_end
                        ? `${new Date(stmt.period_start).toLocaleDateString()} — ${new Date(stmt.period_end).toLocaleDateString()}`
                        : stmt.file_name || '—'}
                    </p>
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); setDeleteTarget(stmt) }}
                    className="p-1.5 text-red-500 hover:bg-red-50 rounded-lg transition-colors flex-shrink-0"
                    title="Delete statement"
                  >
                    <TrashIcon className="w-4 h-4" />
                  </button>
                  <ChevronRightIcon className="w-4 h-4 text-[#7A8580] flex-shrink-0" />
                </div>
              )
            })}
          </div>
        )}
        {filteredStatements.length > STATEMENTS_PAGE_SIZE && (
          <div className="flex items-center justify-between px-6 py-3 border-t border-[rgba(59,77,67,0.05)] bg-white">
            <div className="text-sm text-[#7A8580]">
              Showing {(safePage - 1) * STATEMENTS_PAGE_SIZE + 1}–
              {Math.min(safePage * STATEMENTS_PAGE_SIZE, filteredStatements.length)} of {filteredStatements.length}
            </div>
            <div className="flex items-center space-x-2">
              <button
                className="px-3 py-1 rounded border border-[rgba(59,77,67,0.2)] text-sm disabled:opacity-40"
                disabled={safePage === 1}
                onClick={() => setStatementsPage(p => Math.max(1, p - 1))}
              >
                Previous
              </button>
              <span className="text-sm text-[#3D4A44]">
                Page {safePage} of {totalPages}
              </span>
              <button
                className="px-3 py-1 rounded border border-[rgba(59,77,67,0.2)] text-sm disabled:opacity-40"
                disabled={safePage >= totalPages}
                onClick={() => setStatementsPage(p => Math.min(totalPages, p + 1))}
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {deleteTarget && (
        <DeleteStatementDialog
          orgId={orgId}
          statementId={deleteTarget.id}
          statementName={deleteTarget.source_name}
          onClose={() => setDeleteTarget(null)}
          onDeleted={() => {
            const removedId = deleteTarget?.id
            if (removedId) {
              setSelectedIds(prev => {
                if (!prev.has(removedId)) return prev
                const next = new Set(prev)
                next.delete(removedId)
                return next
              })
            }
            loadStatements()
          }}
        />
      )}

      {bulkDeleteOpen && selectedIds.size > 0 && (
        <DeleteStatementDialog
          orgId={orgId}
          statementIds={Array.from(selectedIds)}
          onClose={() => setBulkDeleteOpen(false)}
          onDeleted={handleBulkDeleted}
        />
      )}
    </div>
  )
}

function CreatorRoyaltyLanding({ orgId, creators, onSelectCreator }) {
  const [summaryData, setSummaryData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [assigningCreator, setAssigningCreator] = useState('')
  const [assigning, setAssigning] = useState(false)

  const loadSummary = useCallback(() => {
    if (!orgId) return
    axios.get(`/api/royalties/creators-summary/${orgId}`)
      .then(res => setSummaryData(res.data))
      .catch(err => console.error('Failed to load creator royalty summary:', err))
      .finally(() => setLoading(false))
  }, [orgId])

  useEffect(() => { loadSummary() }, [loadSummary])

  const handleAssignAll = async () => {
    if (!assigningCreator) return
    setAssigning(true)
    try {
      await axios.post(`/api/royalties/statements/${orgId}/assign-unassigned`, { creator_id: parseInt(assigningCreator) })
      setAssigningCreator('')
      loadSummary()
    } catch (err) {
      console.error('Failed to assign statements:', err)
    } finally {
      setAssigning(false)
    }
  }

  if (loading) return <LoadingSpinner message="Loading clients..." />

  const creatorCards = summaryData?.creators || []
  const unassignedCount = summaryData?.unassigned_count || 0
  const unassignedRevenue = summaryData?.unassigned_revenue_dollars || 0

  const totalRevenue = creatorCards.reduce((sum, c) => sum + (c.total_revenue_dollars || 0), 0) + unassignedRevenue
  const totalStatements = creatorCards.reduce((sum, c) => sum + (c.statement_count || 0), 0) + unassignedCount

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white/80 backdrop-blur-xl rounded-[18px] shadow-am p-5 border border-[rgba(59,77,67,0.08)]">
          <p className="text-xs font-medium text-[#7A8580] uppercase tracking-wider">Total Revenue</p>
          <p className="text-2xl font-bold text-[#3D4A44] mt-1">{formatDollars(totalRevenue)}</p>
        </div>
        <div className="bg-white/80 backdrop-blur-xl rounded-[18px] shadow-am p-5 border border-[rgba(59,77,67,0.08)]">
          <p className="text-xs font-medium text-[#7A8580] uppercase tracking-wider">Total Statements</p>
          <p className="text-2xl font-bold text-[#3D4A44] mt-1">{totalStatements}</p>
        </div>
        <div className="bg-white/80 backdrop-blur-xl rounded-[18px] shadow-am p-5 border border-[rgba(59,77,67,0.08)]">
          <p className="text-xs font-medium text-[#7A8580] uppercase tracking-wider">Clients</p>
          <p className="text-2xl font-bold text-[#3D4A44] mt-1">{creatorCards.length}</p>
        </div>
      </div>

      {creatorCards.length === 0 ? (
        <EmptyState icon={UserGroupIcon} title="No Clients Yet" message="Add creators to your roster to start managing their royalties." />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {creatorCards.map(c => {
            const matchPct = c.total_lines > 0 ? Math.round((c.matched_lines / c.total_lines) * 100) : 0
            return (
              <button
                key={c.creator_id}
                onClick={() => onSelectCreator(c.creator_id, c.display_name)}
                className="bg-white/80 backdrop-blur-xl rounded-[18px] shadow-am border border-[rgba(59,77,67,0.08)] p-5 text-left hover:shadow-[0px_8px_24px_rgba(91,138,114,0.15)] hover:border-[rgba(91,138,114,0.2)] transition-all group"
              >
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-12 h-12 rounded-full bg-gradient-to-br from-[#5B8A72] to-[#7BA594] flex items-center justify-center overflow-hidden flex-shrink-0">
                    <img
                      src={`/api/creators/${c.creator_id}/image`}
                      alt=""
                      className="w-full h-full object-cover"
                      onError={e => { e.target.style.display = 'none'; e.target.parentElement.innerHTML = `<span class="text-white font-semibold text-lg">${(c.display_name || '?')[0].toUpperCase()}</span>` }}
                    />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-base font-semibold text-[#3D4A44] truncate group-hover:text-[#5B8A72] transition-colors">{c.display_name}</p>
                    <p className="text-xs text-[#7A8580]">{c.statement_count} statement{c.statement_count !== 1 ? 's' : ''}</p>
                  </div>
                  <ChevronRightIcon className="w-5 h-5 text-[#7A8580] group-hover:text-[#5B8A72] transition-colors flex-shrink-0" />
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-[#7A8580]">Total Revenue</span>
                    <span className="text-sm font-semibold text-[#3D4A44]">{formatDollars(c.total_revenue_dollars)}</span>
                  </div>
                  {c.statement_count > 0 && (
                    <>
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-[#7A8580]">Match Rate</span>
                        <span className="text-sm font-medium text-[#3D4A44]">{matchPct}%</span>
                      </div>
                      <div className="w-full bg-[#E8EDE9] rounded-full h-1.5">
                        <div className="bg-gradient-to-r from-[#5B8A72] to-[#7BA594] h-1.5 rounded-full transition-all" style={{ width: `${matchPct}%` }} />
                      </div>
                    </>
                  )}
                  {c.latest_statement && (
                    <p className="text-xs text-[#7A8580] pt-1">Latest: {formatDate(c.latest_statement)}</p>
                  )}
                </div>
              </button>
            )
          })}
        </div>
      )}

      {unassignedCount > 0 && (
        <div className="bg-amber-50/80 backdrop-blur-xl rounded-[18px] shadow-am border border-amber-200/50 p-5">
          <div className="flex items-start gap-3">
            <ExclamationCircleIcon className="w-5 h-5 text-amber-600 mt-0.5 flex-shrink-0" />
            <div className="flex-1 space-y-3">
              <div>
                <p className="text-sm font-medium text-amber-800">{unassignedCount} unassigned statement{unassignedCount !== 1 ? 's' : ''}</p>
                <p className="text-xs text-amber-600">{formatDollars(unassignedRevenue)} in revenue not attributed to any client</p>
              </div>
              <div className="flex items-center gap-2 flex-wrap">
                <select
                  value={assigningCreator}
                  onChange={e => setAssigningCreator(e.target.value)}
                  className="px-3 py-1.5 text-sm border border-amber-300 rounded-lg bg-white text-[#3D4A44] focus:ring-2 focus:ring-amber-400 outline-none"
                >
                  <option value="">Assign to client...</option>
                  {creators.map(c => (
                    <option key={c.id} value={c.id}>{c.display_name}</option>
                  ))}
                </select>
                <button
                  onClick={handleAssignAll}
                  disabled={!assigningCreator || assigning}
                  className="px-4 py-1.5 text-sm font-medium text-white bg-amber-600 rounded-lg hover:bg-amber-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  {assigning ? 'Assigning...' : 'Assign'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default function RoyaltiesPage() {
  const [orgId, setOrgId] = useState(null)
  const [activeTab, setActiveTab] = useState('dashboard')
  const [loading, setLoading] = useState(true)
  const [songs, setSongs] = useState([])
  const [creators, setCreators] = useState([])
  const [contracts, setContracts] = useState([])
  const [selectedCreatorId, setSelectedCreatorId] = useState(null)
  const [selectedCreatorName, setSelectedCreatorName] = useState('')

  useEffect(() => {
    const loadInitialData = async () => {
      try {
        const orgRes = await axios.get('/api/organizations/current')
        const id = orgRes.data?.id
        if (!id) { setLoading(false); return }
        setOrgId(id)

        axios.get(`/api/songs/org/${id}?limit=1000`)
          .then(res => {
            const songsData = res.data
            setSongs(Array.isArray(songsData) ? songsData : [])
          })
          .catch(err => console.error('Failed to load songs:', err))
          .finally(() => setLoading(false))

        axios.get(`/api/creators/org/${id}`)
          .then(res => setCreators(Array.isArray(res.data) ? res.data : []))
          .catch(err => console.error('Failed to load creators:', err))

        axios.get(`/api/rights/contracts/org/${id}`)
          .then(res => {
            const cData = res.data
            setContracts(Array.isArray(cData) ? cData : cData?.contracts || [])
          })
          .catch(err => console.error('Failed to load contracts:', err))
      } catch (err) {
        console.error('Failed to load initial data:', err)
        setLoading(false)
      }
    }
    loadInitialData()
  }, [])

  const handleSelectCreator = (creatorId, creatorName) => {
    setSelectedCreatorId(creatorId)
    setSelectedCreatorName(creatorName)
    setActiveTab('processing')
  }

  const handleBackToClients = () => {
    setSelectedCreatorId(null)
    setSelectedCreatorName('')
    setActiveTab('dashboard')
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#F5F7F4] flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-[#5B8A72] border-t-transparent"></div>
          <p className="mt-4 text-[#7A8580]">Loading royalties...</p>
        </div>
      </div>
    )
  }

  if (!selectedCreatorId) {
    return (
      <div className="min-h-screen bg-[#F5F7F4] p-4 sm:p-6 lg:p-8 overflow-x-hidden">
        <div className="max-w-7xl mx-auto">
          <div className="mb-6">
            <h1 className="text-[34px] font-semibold text-[#3D4A44] leading-tight">Royalties</h1>
            <p className="text-[17px] text-[#7A8580] mt-1">Select a client to manage their statements, earnings, and payments</p>
          </div>
          <CreatorRoyaltyLanding orgId={orgId} creators={creators} onSelectCreator={handleSelectCreator} />
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#F5F7F4] p-4 sm:p-6 lg:p-8 overflow-x-hidden">
      <div className="max-w-7xl mx-auto">
        <div className="mb-6">
          <button
            onClick={handleBackToClients}
            className="flex items-center gap-2 text-sm text-[#7A8580] hover:text-[#5B8A72] transition-colors mb-3"
          >
            <ArrowLeftIcon className="w-4 h-4" />
            All Clients
          </button>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#5B8A72] to-[#7BA594] flex items-center justify-center overflow-hidden flex-shrink-0">
              <img
                src={`/api/creators/${selectedCreatorId}/image`}
                alt=""
                className="w-full h-full object-cover"
                onError={e => { e.target.style.display = 'none'; e.target.parentElement.innerHTML = `<span class="text-white font-semibold text-base">${(selectedCreatorName || '?')[0].toUpperCase()}</span>` }}
              />
            </div>
            <div>
              <h1 className="text-[34px] font-semibold text-[#3D4A44] leading-tight">{selectedCreatorName}</h1>
              <p className="text-[17px] text-[#7A8580] mt-0">Royalties & Accounting</p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-1 mb-6 bg-white/60 backdrop-blur-xl rounded-[14px] p-1 border border-[rgba(59,77,67,0.08)] overflow-x-auto">
          {TABS.map(tab => {
            const Icon = tab.icon
            return (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all ${
                  activeTab === tab.key
                    ? 'bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white shadow-am-button'
                    : 'text-[#7A8580] hover:text-[#3D4A44] hover:bg-[rgba(91,138,114,0.06)]'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span className="hidden sm:inline">{tab.label}</span>
              </button>
            )
          })}
        </div>

        {activeTab === 'dashboard' && <DashboardTab orgId={orgId} creatorId={selectedCreatorId} />}
        {activeTab === 'processing' && <ProcessingTab orgId={orgId} creators={creators} selectedCreatorId={selectedCreatorId} />}
        {activeTab === 'statements' && <StatementsTab orgId={orgId} songs={songs} selectedCreatorId={selectedCreatorId} />}
        {activeTab === 'earnings' && <EarningsTab orgId={orgId} selectedCreatorId={selectedCreatorId} />}
        {activeTab === 'analytics' && <RoyaltyAnalyticsDashboard orgId={orgId} />}
        {activeTab === 'money_out' && <MoneyOutTab orgId={orgId} creators={creators} contracts={contracts} />}
        {activeTab === 'fees' && <FeesAdvancesTab orgId={orgId} creators={creators} />}
        {activeTab === 'payables' && <PayablesTab orgId={orgId} />}
      </div>
    </div>
  )
}
