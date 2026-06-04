import React, { useState, useEffect, useCallback } from 'react'
import axios from 'axios'
import {
  ArrowLeftIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  MagnifyingGlassIcon,
  ArrowDownTrayIcon,
  PlayIcon,
  XMarkIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  EyeIcon,
  DocumentTextIcon,
  ClockIcon,
  CurrencyDollarIcon,
  MusicalNoteIcon,
  LinkIcon,
  XCircleIcon,
  HandThumbUpIcon,
  HandThumbDownIcon,
  NoSymbolIcon,
  ShieldCheckIcon,
  ChartBarIcon,
  TrashIcon,
} from '@heroicons/react/24/outline'
import DeleteStatementDialog from './DeleteStatementDialog'
import BMIIntelligencePanel from './BMIIntelligencePanel'

const MATCH_STATUS_COLORS = {
  MATCHED: { bg: 'bg-green-100', text: 'text-green-700' },
  UNMATCHED: { bg: 'bg-red-100', text: 'text-red-700' },
  REVIEW_REQUIRED: { bg: 'bg-orange-100', text: 'text-orange-700' },
  IGNORED: { bg: 'bg-gray-100', text: 'text-gray-700' },
  CONFIRMED: { bg: 'bg-green-100', text: 'text-green-700' },
}

const STATEMENT_STATUS_COLORS = {
  PENDING: { bg: 'bg-amber-100', text: 'text-amber-700' },
  PROCESSING: { bg: 'bg-blue-100', text: 'text-blue-700' },
  PROCESSED: { bg: 'bg-green-100', text: 'text-green-700' },
  FAILED: { bg: 'bg-red-100', text: 'text-red-700' },
  PARTIALLY_MATCHED: { bg: 'bg-orange-100', text: 'text-orange-700' },
  UPLOADED: { bg: 'bg-gray-100', text: 'text-gray-700' },
  REVIEW_REQUIRED: { bg: 'bg-orange-100', text: 'text-orange-700' },
  FULLY_MATCHED: { bg: 'bg-green-100', text: 'text-green-700' },
  MAPPING_REQUIRED: { bg: 'bg-amber-100', text: 'text-amber-700' },
  MATCHING: { bg: 'bg-blue-100', text: 'text-blue-700' },
  READY_TO_PROCESS: { bg: 'bg-green-100', text: 'text-green-700' },
}

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

const DETAIL_TABS = [
  { key: 'overview', label: 'Overview', icon: EyeIcon },
  { key: 'lines', label: 'Lines', icon: DocumentTextIcon },
  { key: 'matching', label: 'Matching', icon: LinkIcon },
  { key: 'reconciliation', label: 'Reconciliation', icon: ShieldCheckIcon },
  { key: 'bmi_intel', label: 'BMI Intelligence', icon: ChartBarIcon },
  { key: 'classification', label: 'Classification', icon: ChartBarIcon },
  { key: 'allocation', label: 'Allocation Preview', icon: CurrencyDollarIcon },
  { key: 'runs', label: 'Run History', icon: ClockIcon },
  { key: 'exports', label: 'Exports', icon: ArrowDownTrayIcon },
]

const LINE_FILTERS = [
  { key: '', label: 'All' },
  { key: 'UNMATCHED', label: 'Unmatched' },
  { key: 'REVIEW_REQUIRED', label: 'Review Required' },
  { key: 'MATCHED', label: 'Matched' },
  { key: 'CONFIRMED', label: 'Confirmed' },
  { key: 'IGNORED', label: 'Ignored' },
]

export default function StatementDetailView({ orgId, statementId, onBack, initialTab = 'overview' }) {
  const [activeTab, setActiveTab] = useState(initialTab)
  const [statement, setStatement] = useState(null)
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  const [lines, setLines] = useState([])
  const [linesTotal, setLinesTotal] = useState(0)
  const [linesLoading, setLinesLoading] = useState(false)
  const [lineFilter, setLineFilter] = useState('')
  const [lineSearch, setLineSearch] = useState('')
  const [lineOffset, setLineOffset] = useState(0)
  const lineLimit = 50

  const [selectedLine, setSelectedLine] = useState(null)
  const [suggestions, setSuggestions] = useState([])
  const [suggestionsLoading, setSuggestionsLoading] = useState(false)
  const [matchQueue, setMatchQueue] = useState([])
  const [matchQueueLoading, setMatchQueueLoading] = useState(false)

  const [allocations, setAllocations] = useState([])
  const [allocLoading, setAllocLoading] = useState(false)
  const [allocIsProcessed, setAllocIsProcessed] = useState(false)

  const [runs, setRuns] = useState([])
  const [runsLoading, setRunsLoading] = useState(false)
  const [showReprocess, setShowReprocess] = useState(false)
  const [reprocessReason, setReprocessReason] = useState('')
  const [reprocessing, setReprocessing] = useState(false)

  const [showProcessModal, setShowProcessModal] = useState(false)
  const [processing, setProcessing] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

  const [bulkThreshold, setBulkThreshold] = useState(85)
  const [bulkConfirming, setBulkConfirming] = useState(false)
  const [autoMatching, setAutoMatching] = useState(false)

  const [propagation, setPropagation] = useState(null)
  const [propagationBusy, setPropagationBusy] = useState(false)

  const loadStatement = useCallback(async () => {
    if (!orgId || !statementId) return
    try {
      const [stmtRes, statsRes] = await Promise.all([
        axios.get(`/api/royalties/statements/${orgId}`),
        axios.get(`/api/royalty-processing/${orgId}/statements/${statementId}/lines/stats`),
      ])
      const stmts = Array.isArray(stmtRes.data) ? stmtRes.data : stmtRes.data.statements || []
      const stmt = stmts.find(s => s.id === statementId)
      setStatement(stmt || null)
      setStats(statsRes.data)
    } catch (err) {
      console.error('Failed to load statement:', err)
    } finally {
      setLoading(false)
    }
  }, [orgId, statementId])

  useEffect(() => { loadStatement() }, [loadStatement])

  const loadLines = useCallback(async () => {
    if (!orgId || !statementId) return
    setLinesLoading(true)
    try {
      const params = { offset: lineOffset, limit: lineLimit }
      if (lineFilter) params.match_status = lineFilter
      if (lineSearch) params.search = lineSearch
      const res = await axios.get(`/api/royalty-processing/${orgId}/statements/${statementId}/lines`, { params })
      setLines(res.data.lines || [])
      setLinesTotal(res.data.total || 0)
    } catch (err) {
      console.error('Failed to load lines:', err)
    } finally {
      setLinesLoading(false)
    }
  }, [orgId, statementId, lineOffset, lineFilter, lineSearch])

  useEffect(() => {
    if (activeTab === 'lines') loadLines()
  }, [activeTab, loadLines])

  const loadMatchQueue = useCallback(async () => {
    if (!orgId || !statementId) return
    setMatchQueueLoading(true)
    try {
      const res = await axios.get(`/api/royalty-processing/${orgId}/statements/${statementId}/lines`, {
        params: { match_status: 'UNMATCHED', limit: 200 }
      })
      const unmatchedLines = res.data.lines || []
      const res2 = await axios.get(`/api/royalty-processing/${orgId}/statements/${statementId}/lines`, {
        params: { match_status: 'REVIEW_REQUIRED', limit: 200 }
      })
      const reviewLines = res2.data.lines || []
      setMatchQueue([...reviewLines, ...unmatchedLines])
    } catch (err) {
      console.error('Failed to load match queue:', err)
    } finally {
      setMatchQueueLoading(false)
    }
  }, [orgId, statementId])

  useEffect(() => {
    if (activeTab === 'matching') loadMatchQueue()
  }, [activeTab, loadMatchQueue])

  const loadSuggestions = async (lineId) => {
    setSuggestionsLoading(true)
    try {
      const res = await axios.get(`/api/royalty-processing/${orgId}/lines/${lineId}/suggestions`)
      setSuggestions(res.data.suggestions || [])
    } catch (err) {
      console.error('Failed to load suggestions:', err)
    } finally {
      setSuggestionsLoading(false)
    }
  }

  const handleSelectLine = (line) => {
    setSelectedLine(line)
    loadSuggestions(line.id)
  }

  const handleConfirmMatch = async (songId) => {
    if (!selectedLine) return
    const lineId = selectedLine.id
    try {
      const res = await axios.post(`/api/royalty-processing/${orgId}/lines/${lineId}/confirm-match`, { song_id: songId })
      setSelectedLine(null)
      setSuggestions([])
      const prop = res.data?.propagation
      if (prop && prop.tier) {
        setPropagation({ ...prop, sourceLineId: lineId, songId })
      } else {
        setPropagation(null)
      }
      loadMatchQueue()
      loadStatement()
    } catch (err) {
      console.error('Confirm match failed:', err)
    }
  }

  const handleApplyTitleArtist = async () => {
    if (!propagation?.sourceLineId) return
    setPropagationBusy(true)
    try {
      const res = await axios.post(
        `/api/royalty-processing/${orgId}/lines/${propagation.sourceLineId}/propagate-match`,
        { song_id: propagation.songId },
      )
      const prop = res.data?.propagation
      setPropagation(prop && prop.tier ? { ...prop, sourceLineId: propagation.sourceLineId, songId: propagation.songId } : null)
      loadMatchQueue()
      loadStatement()
    } catch (err) {
      console.error('Apply propagation failed:', err)
    } finally {
      setPropagationBusy(false)
    }
  }

  const handleUndoPropagation = async () => {
    if (!propagation?.batch_id) return
    setPropagationBusy(true)
    try {
      await axios.post(`/api/royalty-processing/${orgId}/propagation/${propagation.batch_id}/undo`)
      setPropagation(null)
      loadMatchQueue()
      loadStatement()
    } catch (err) {
      console.error('Undo propagation failed:', err)
    } finally {
      setPropagationBusy(false)
    }
  }

  const dismissPropagation = () => setPropagation(null)

  const handleRejectMatch = async () => {
    if (!selectedLine) return
    try {
      await axios.post(`/api/royalty-processing/${orgId}/lines/${selectedLine.id}/reject-match`)
      setSelectedLine(null)
      setSuggestions([])
      loadMatchQueue()
      loadStatement()
    } catch (err) {
      console.error('Reject match failed:', err)
    }
  }

  const handleIgnoreLine = async (lineId) => {
    try {
      await axios.post(`/api/royalty-processing/${orgId}/lines/${lineId || selectedLine?.id}/ignore`)
      setSelectedLine(null)
      setSuggestions([])
      loadMatchQueue()
      loadStatement()
    } catch (err) {
      console.error('Ignore line failed:', err)
    }
  }

  const handleBulkConfirm = async () => {
    setBulkConfirming(true)
    try {
      const res = await axios.post(`/api/royalty-processing/${orgId}/statements/${statementId}/bulk-confirm`, { threshold: bulkThreshold })
      alert(`${res.data.confirmed_count} lines confirmed.`)
      loadMatchQueue()
      loadStatement()
    } catch (err) {
      console.error('Bulk confirm failed:', err)
    } finally {
      setBulkConfirming(false)
    }
  }

  const loadAllocations = useCallback(async () => {
    if (!orgId || !statementId) return
    setAllocLoading(true)
    try {
      const res = await axios.get(`/api/royalty-processing/${orgId}/statements/${statementId}/allocation-preview`)
      setAllocations(res.data.allocations || [])
      setAllocIsProcessed(res.data.is_processed || false)
    } catch (err) {
      console.error('Failed to load allocations:', err)
    } finally {
      setAllocLoading(false)
    }
  }, [orgId, statementId])

  useEffect(() => {
    if (activeTab === 'allocation') loadAllocations()
  }, [activeTab, loadAllocations])

  const loadRuns = useCallback(async () => {
    if (!orgId || !statementId) return
    setRunsLoading(true)
    try {
      const res = await axios.get(`/api/royalty-processing/${orgId}/statements/${statementId}/runs`)
      setRuns(res.data.runs || [])
    } catch (err) {
      console.error('Failed to load runs:', err)
    } finally {
      setRunsLoading(false)
    }
  }, [orgId, statementId])

  useEffect(() => {
    if (activeTab === 'runs') loadRuns()
  }, [activeTab, loadRuns])

  const handleProcess = async () => {
    setProcessing(true)
    try {
      await axios.post(`/api/royalty-processing/${orgId}/statements/${statementId}/process`)
      setShowProcessModal(false)
      loadStatement()
      loadRuns()
    } catch (err) {
      console.error('Process failed:', err)
      alert(err.response?.data?.detail || 'Processing failed.')
    } finally {
      setProcessing(false)
    }
  }

  const handleReprocess = async () => {
    if (!reprocessReason.trim()) return
    setReprocessing(true)
    try {
      await axios.post(`/api/royalty-processing/${orgId}/statements/${statementId}/reprocess`, { reason: reprocessReason })
      setShowReprocess(false)
      setReprocessReason('')
      loadStatement()
      loadRuns()
    } catch (err) {
      console.error('Reprocess failed:', err)
      alert(err.response?.data?.detail || 'Reprocessing failed.')
    } finally {
      setReprocessing(false)
    }
  }

  const handleAutoMatch = async () => {
    setAutoMatching(true)
    try {
      const res = await axios.post(`/api/royalty-processing/${orgId}/statements/${statementId}/auto-match`)
      loadStatement()
      if (activeTab === 'matching') {
        loadMatchQueue()
      }
      if (activeTab === 'lines') {
        loadLines()
      }
      const s = res.data.stats || {}
      const a = s.auto_matched || 0
      const r2 = s.review_required || 0
      const u = s.unmatched || 0
      alert(`Auto-match complete. ${a} auto-matched, ${r2} need review, ${u} unmatched.`)
    } catch (err) {
      console.error('Auto-match failed:', err)
      alert(err.response?.data?.detail || 'Auto-match failed.')
    } finally {
      setAutoMatching(false)
    }
  }

  const handleExport = (type) => {
    window.open(`/api/royalty-processing/${orgId}/statements/${statementId}/export/${type}`, '_blank')
  }


  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-10 w-10 border-4 border-[#5B8A72] border-t-transparent"></div>
          <p className="mt-3 text-sm text-[#7A8580]">Loading statement...</p>
        </div>
      </div>
    )
  }

  if (!statement) {
    return (
      <div className="space-y-4">
        <button onClick={onBack} className="flex items-center gap-2 text-[#5B8A72] hover:text-[#4a7a62] text-sm font-medium transition-colors">
          <ArrowLeftIcon className="w-4 h-4" /> Back
        </button>
        <div className="flex items-center justify-center py-16">
          <div className="text-center">
            <ExclamationCircleIcon className="w-12 h-12 text-[#7A8580] mx-auto mb-3" />
            <p className="text-sm text-[#7A8580]">Statement not found</p>
          </div>
        </div>
      </div>
    )
  }

  const statusColors = STATEMENT_STATUS_COLORS[statement.status] || { bg: 'bg-gray-100', text: 'text-gray-700' }
  const totalLines = stats?.total_lines || 0
  const matchedCount = (stats?.by_status?.MATCHED?.count || 0) + (stats?.by_status?.CONFIRMED?.count || 0) + (stats?.by_status?.AUTO_MATCHED?.count || 0)
  const ignoredCount = stats?.by_status?.IGNORED?.count || 0
  const reviewCount = stats?.by_status?.REVIEW_REQUIRED?.count || 0
  const unmatchedCount = stats?.by_status?.UNMATCHED?.count || 0
  const matchPct = totalLines > 0 ? (matchedCount / totalLines) * 100 : 0

  return (
    <div className="space-y-4">
      <button onClick={onBack} className="flex items-center gap-2 text-[#5B8A72] hover:text-[#4a7a62] text-sm font-medium transition-colors">
        <ArrowLeftIcon className="w-4 h-4" /> Back to Processing
      </button>

      <div className="bg-white/80 backdrop-blur-xl rounded-[18px] shadow-am p-6 border border-[rgba(59,77,67,0.08)]">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold text-[#3D4A44]">{statement.source_name || 'Statement'}</h2>
            <p className="text-sm text-[#7A8580] mt-1">
              {formatDate(statement.period_start)} — {formatDate(statement.period_end)}
            </p>
          </div>
          <div className="flex items-center gap-3 flex-wrap">
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusColors.bg} ${statusColors.text}`}>
              {statement.status}
            </span>
            <button
              onClick={handleAutoMatch}
              disabled={autoMatching}
              className="flex items-center gap-2 px-4 py-2 border border-[#5B8A72] text-[#5B8A72] rounded-xl hover:bg-[rgba(91,138,114,0.06)] transition-all text-sm font-medium disabled:opacity-50"
            >
              <LinkIcon className="w-4 h-4" /> {autoMatching ? 'Matching...' : 'Run Auto-Match'}
            </button>
            <button
              onClick={() => setShowProcessModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-xl hover:shadow-[0px_4px_12px_rgba(91,138,114,0.3)] transition-all text-sm font-medium"
            >
              <PlayIcon className="w-4 h-4" /> Process Statement
            </button>
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className="flex items-center gap-2 px-3 py-2 border border-red-300 text-red-500 rounded-xl hover:bg-red-50 transition-all text-sm font-medium"
              title="Delete Statement"
            >
              <TrashIcon className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-1 bg-white/60 backdrop-blur-xl rounded-[14px] p-1 border border-[rgba(59,77,67,0.08)] overflow-x-auto">
        {DETAIL_TABS.map(tab => {
          const Icon = tab.icon
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium transition-all whitespace-nowrap ${
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

      {activeTab === 'overview' && (
        <OverviewPane statement={statement} stats={stats} totalLines={totalLines} matchedCount={matchedCount} matchPct={matchPct} />
      )}
      {activeTab === 'lines' && (
        <LinesPane
          lines={lines} total={linesTotal} loading={linesLoading}
          filter={lineFilter} setFilter={(f) => { setLineFilter(f); setLineOffset(0) }}
          search={lineSearch} setSearch={(s) => { setLineSearch(s); setLineOffset(0) }}
          offset={lineOffset} setOffset={setLineOffset} limit={lineLimit}
        />
      )}
      {activeTab === 'matching' && (
        <MatchingPane
          queue={matchQueue} queueLoading={matchQueueLoading}
          selectedLine={selectedLine} onSelectLine={handleSelectLine}
          suggestions={suggestions} suggestionsLoading={suggestionsLoading}
          onConfirm={handleConfirmMatch} onReject={handleRejectMatch} onIgnore={handleIgnoreLine}
          bulkThreshold={bulkThreshold} setBulkThreshold={setBulkThreshold}
          onBulkConfirm={handleBulkConfirm} bulkConfirming={bulkConfirming}
          propagation={propagation} propagationBusy={propagationBusy}
          onApplyTitleArtist={handleApplyTitleArtist} onUndoPropagation={handleUndoPropagation}
          onDismissPropagation={dismissPropagation}
        />
      )}
      {activeTab === 'reconciliation' && (
        <ReconciliationPane orgId={orgId} statementId={statementId} />
      )}
      {activeTab === 'bmi_intel' && (
        <BMIIntelligencePanel orgId={orgId} statementId={statementId} />
      )}
      {activeTab === 'classification' && (
        <ClassificationPane orgId={orgId} statementId={statementId} />
      )}
      {activeTab === 'allocation' && (
        <AllocationPane allocations={allocations} loading={allocLoading} isProcessed={allocIsProcessed} />
      )}
      {activeTab === 'runs' && (
        <RunsPane
          runs={runs} loading={runsLoading}
          showReprocess={showReprocess} setShowReprocess={setShowReprocess}
          reprocessReason={reprocessReason} setReprocessReason={setReprocessReason}
          onReprocess={handleReprocess} reprocessing={reprocessing}
        />
      )}
      {activeTab === 'exports' && (
        <ExportsPane onExport={handleExport} />
      )}

      {showProcessModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm p-4">
          <div className="bg-white rounded-[18px] shadow-2xl w-full max-w-md">
            <div className="flex items-center justify-between p-6 border-b border-[rgba(59,77,67,0.08)]">
              <h3 className="text-lg font-semibold text-[#3D4A44]">Process Statement</h3>
              <button onClick={() => setShowProcessModal(false)} className="p-2 hover:bg-[rgba(59,77,67,0.06)] rounded-full transition-colors">
                <XMarkIcon className="w-5 h-5 text-[#7A8580]" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <p className="text-sm text-[#7A8580]">
                This will create ledger entries for all statement lines. Matched (and confirmed) lines are allocated to payees based on contract splits with recoupment applied. Lines awaiting review and unmatched lines are booked as unallocated org revenue until they're confirmed.
              </p>
              <div className="bg-[rgba(91,138,114,0.06)] rounded-xl p-4">
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-[#7A8580]">Total Lines</span>
                  <span className="font-medium text-[#3D4A44]">{totalLines}</span>
                </div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-[#7A8580]">Matched</span>
                  <span className="font-medium text-[#5B8A72]">{matchedCount}</span>
                </div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-[#7A8580]">Needs Review</span>
                  <span className="font-medium text-orange-600">{reviewCount}</span>
                </div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-[#7A8580]">Unmatched</span>
                  <span className="font-medium text-[#B87333]">{unmatchedCount}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-[#7A8580]">Match Rate</span>
                  <span className="font-medium text-[#3D4A44]">{matchPct.toFixed(1)}%</span>
                </div>
              </div>
              {reviewCount > 0 && (
                <div className="bg-orange-50 rounded-xl p-3 space-y-2">
                  <p className="text-xs text-orange-700">
                    {reviewCount} line{reviewCount !== 1 ? 's have' : ' has'} a suggested match awaiting confirmation. {reviewCount !== 1 ? 'They' : 'It'} won't be allocated to a payee until confirmed.
                  </p>
                  <button
                    onClick={async () => {
                      try {
                        const res = await axios.post(`/api/royalty-processing/${orgId}/statements/${statementId}/bulk-confirm`, { threshold: bulkThreshold })
                        await loadStatement()
                        alert(`Confirmed ${res.data.confirmed_count || 0} suggestion${(res.data.confirmed_count || 0) === 1 ? '' : 's'} at or above ${bulkThreshold}% confidence.`)
                      } catch (err) {
                        alert(err.response?.data?.detail || 'Bulk confirm failed.')
                      }
                    }}
                    className="text-xs px-3 py-1.5 bg-white border border-orange-300 text-orange-700 rounded-lg hover:bg-orange-100 font-medium"
                  >
                    Confirm all suggestions ≥ {bulkThreshold}%
                  </button>
                </div>
              )}
              {unmatchedCount > 0 && (
                <div className="bg-[rgba(184,115,51,0.06)] rounded-xl p-3">
                  <p className="text-xs text-[#B87333]">
                    {unmatchedCount} unmatched line{unmatchedCount !== 1 ? 's' : ''} will be booked as unallocated revenue. You can run auto-match afterwards and reprocess to allocate them.
                  </p>
                </div>
              )}
              <div className="flex justify-end gap-3 pt-2">
                <button onClick={() => setShowProcessModal(false)} className="px-4 py-2 text-sm text-[#7A8580] hover:text-[#3D4A44] transition-colors">Cancel</button>
                <button
                  onClick={handleProcess}
                  disabled={processing}
                  className="px-5 py-2.5 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-xl hover:shadow-[0px_4px_12px_rgba(91,138,114,0.3)] transition-all text-sm font-medium disabled:opacity-50"
                >
                  {processing ? 'Processing...' : 'Confirm & Process'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {showDeleteConfirm && (
        <DeleteStatementDialog
          orgId={orgId}
          statementId={statementId}
          statementName={statement.source_name}
          onClose={() => setShowDeleteConfirm(false)}
          onDeleted={() => onBack()}
        />
      )}
    </div>
  )
}

function OverviewPane({ statement, stats, totalLines, matchedCount, matchPct }) {
  const byStatus = stats?.by_status || {}
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Total Lines', value: totalLines, icon: DocumentTextIcon },
          { label: 'Matched', value: matchedCount, icon: CheckCircleIcon },
          { label: 'Unmatched', value: byStatus.UNMATCHED?.count || 0, icon: ExclamationCircleIcon },
          { label: 'Total Amount', value: formatDollars(stats?.total_amount), icon: CurrencyDollarIcon, isAmount: true },
        ].map((card, i) => (
          <div key={i} className="bg-white/80 backdrop-blur-xl rounded-[18px] shadow-am p-5 border border-[rgba(59,77,67,0.08)]">
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 bg-[rgba(91,138,114,0.1)] rounded-lg">
                <card.icon className="w-5 h-5 text-[#5B8A72]" />
              </div>
              <span className="text-sm font-medium text-[#7A8580]">{card.label}</span>
            </div>
            <div className="text-2xl font-bold text-[#3D4A44]">{card.value}</div>
          </div>
        ))}
      </div>

      <div className="bg-white/80 backdrop-blur-xl rounded-[18px] shadow-am p-6 border border-[rgba(59,77,67,0.08)]">
        <h3 className="text-lg font-semibold text-[#3D4A44] mb-4">Matching Progress</h3>
        <div className="w-full bg-[#EEF1EC] rounded-full h-4 mb-2">
          <div
            className="h-4 rounded-full bg-gradient-to-r from-[#5B8A72] to-[#7BA594] transition-all"
            style={{ width: `${matchPct}%` }}
          />
        </div>
        <div className="flex justify-between text-sm text-[#7A8580]">
          <span>{matchPct.toFixed(1)}% matched</span>
          <span>{matchedCount} / {totalLines} lines</span>
        </div>

        <div className="mt-6 grid grid-cols-2 sm:grid-cols-4 gap-3">
          {Object.entries(byStatus).map(([status, data]) => {
            const colors = MATCH_STATUS_COLORS[status] || { bg: 'bg-gray-100', text: 'text-gray-700' }
            return (
              <div key={status} className="border border-[rgba(59,77,67,0.08)] rounded-xl p-3 text-center">
                <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${colors.bg} ${colors.text} mb-1`}>
                  {status}
                </span>
                <div className="text-lg font-bold text-[#3D4A44]">{data.count}</div>
                <div className="text-xs text-[#7A8580]">{formatDollars(data.total_amount)}</div>
              </div>
            )
          })}
        </div>
      </div>

      <div className="bg-white/80 backdrop-blur-xl rounded-[18px] shadow-am p-6 border border-[rgba(59,77,67,0.08)]">
        <h3 className="text-lg font-semibold text-[#3D4A44] mb-4">Statement Info</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {[
            { label: 'Source', value: statement.source_name || '—' },
            { label: 'Source Type', value: statement.source_type || '—' },
            { label: 'Period', value: `${formatDate(statement.period_start)} — ${formatDate(statement.period_end)}` },
            { label: 'Currency', value: statement.currency || 'USD' },
            { label: 'File', value: statement.file_name || '—' },
            { label: 'Status', value: statement.status || '—' },
          ].map((item, i) => (
            <div key={i}>
              <span className="text-xs font-medium text-[#7A8580] uppercase">{item.label}</span>
              <p className="text-sm text-[#3D4A44] mt-0.5">{item.value}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function LinesPane({ lines, total, loading, filter, setFilter, search, setSearch, offset, setOffset, limit }) {
  const totalPages = Math.ceil(total / limit)
  const currentPage = Math.floor(offset / limit) + 1

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
        <div className="flex items-center gap-1 bg-white/60 backdrop-blur-xl rounded-[14px] p-1 border border-[rgba(59,77,67,0.08)] overflow-x-auto">
          {LINE_FILTERS.map(f => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all whitespace-nowrap ${
                filter === f.key
                  ? 'bg-[#5B8A72] text-white'
                  : 'text-[#7A8580] hover:text-[#3D4A44] hover:bg-[rgba(91,138,114,0.06)]'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
        <div className="relative flex-1 max-w-xs">
          <MagnifyingGlassIcon className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#7A8580]" />
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search tracks, artists, ISRCs..."
            className="w-full pl-9 pr-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm text-[#3D4A44] bg-white focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent outline-none"
          />
        </div>
        <span className="text-xs text-[#7A8580]">{total} lines</span>
      </div>

      <div className="bg-white/80 backdrop-blur-xl rounded-[18px] shadow-am border border-[rgba(59,77,67,0.08)]">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-[#5B8A72] border-t-transparent"></div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-[#EEF1EC]">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[#7A8580] uppercase tracking-wider">Track</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[#7A8580] uppercase tracking-wider">Artist</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[#7A8580] uppercase tracking-wider">Source</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[#7A8580] uppercase tracking-wider">ISRC</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-[#7A8580] uppercase tracking-wider">Net Amount</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-[#7A8580] uppercase tracking-wider">Qty</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[#7A8580] uppercase tracking-wider">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[#7A8580] uppercase tracking-wider">Matched Song</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-[#7A8580] uppercase tracking-wider">Confidence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[rgba(59,77,67,0.05)]">
                {lines.map(line => {
                  const colors = MATCH_STATUS_COLORS[line.match_status] || { bg: 'bg-gray-100', text: 'text-gray-700' }
                  return (
                    <tr key={line.id} className="hover:bg-[rgba(91,138,114,0.04)]">
                      <td className="px-4 py-3 text-sm text-[#3D4A44]">{line.track_title_raw || '—'}</td>
                      <td className="px-4 py-3 text-sm text-[#7A8580]">{line.artist_name_raw || '—'}</td>
                      <td className="px-4 py-3 text-sm text-[#7A8580]">{line.store || '—'}</td>
                      <td className="px-4 py-3 text-sm text-[#7A8580] font-mono text-xs">{line.isrc || '—'}</td>
                      <td className="px-4 py-3 text-sm text-right font-medium text-[#3D4A44]">{formatDollars(line.net_amount)}</td>
                      <td className="px-4 py-3 text-sm text-right text-[#7A8580]">{(line.unit_count || 0).toLocaleString()}</td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${colors.bg} ${colors.text}`}>
                          {line.match_status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-[#5B8A72]">{line.matched_song_title || '—'}</td>
                      <td className="px-4 py-3 text-sm text-right text-[#7A8580]">
                        {line.match_confidence != null ? `${line.match_confidence.toFixed(0)}%` : '—'}
                      </td>
                    </tr>
                  )
                })}
                {lines.length === 0 && (
                  <tr><td colSpan={8} className="px-6 py-12 text-center text-sm text-[#7A8580]">No statement lines or transactions found for this statement.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}

        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-[rgba(59,77,67,0.08)]">
            <button
              onClick={() => setOffset(Math.max(0, offset - limit))}
              disabled={offset === 0}
              className="flex items-center gap-1 px-3 py-1.5 text-sm text-[#5B8A72] hover:bg-[rgba(91,138,114,0.06)] rounded-lg disabled:opacity-40 transition-colors"
            >
              <ChevronLeftIcon className="w-4 h-4" /> Previous
            </button>
            <span className="text-sm text-[#7A8580]">Page {currentPage} of {totalPages}</span>
            <button
              onClick={() => setOffset(offset + limit)}
              disabled={offset + limit >= total}
              className="flex items-center gap-1 px-3 py-1.5 text-sm text-[#5B8A72] hover:bg-[rgba(91,138,114,0.06)] rounded-lg disabled:opacity-40 transition-colors"
            >
              Next <ChevronRightIcon className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

const PROPAGATION_TIER_LABELS = {
  ISRC: 'ISRC',
  ISWC: 'ISWC',
  TITLE_ARTIST: 'title and artist',
}

function PropagationBanner({ propagation, busy, onApplyTitleArtist, onUndo, onDismiss }) {
  if (!propagation || !propagation.tier) return null

  const tierLabel = PROPAGATION_TIER_LABELS[propagation.tier] || propagation.tier
  const lines = propagation.affected_count || 0
  const stmts = propagation.statements_count || 0
  const lineWord = lines === 1 ? 'line' : 'lines'
  const stmtWord = stmts === 1 ? 'statement' : 'statements'

  if (!propagation.applied) {
    if (lines === 0) return null
    return (
      <div className="rounded-[14px] border border-[rgba(91,138,114,0.3)] bg-[rgba(91,138,114,0.06)] p-4">
        <div className="flex items-start justify-between gap-3 flex-wrap">
          <div className="flex items-start gap-3">
            <LinkIcon className="w-5 h-5 text-[#5B8A72] mt-0.5 shrink-0" />
            <div>
              <p className="text-sm font-medium text-[#3D4A44]">
                {lines} other {lineWord} across {stmts} {stmtWord} look like this song, matched by {tierLabel}.
              </p>
              <p className="text-xs text-[#7A8580] mt-1">
                This is a lower-confidence match. Review before applying it to every line.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={onApplyTitleArtist}
              disabled={busy}
              className="flex items-center gap-1 px-3 py-1.5 text-xs bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-lg hover:shadow-[0px_4px_12px_rgba(91,138,114,0.3)] transition-all font-medium disabled:opacity-50"
            >
              <CheckCircleIcon className="w-3.5 h-3.5" /> {busy ? 'Applying...' : `Apply to all ${lines} ${lineWord}`}
            </button>
            <button
              onClick={onDismiss}
              disabled={busy}
              className="px-3 py-1.5 text-xs text-[#7A8580] hover:text-[#3D4A44] rounded-lg transition-colors font-medium disabled:opacity-50"
            >
              Dismiss
            </button>
          </div>
        </div>
      </div>
    )
  }

  if (lines === 0) {
    return (
      <div className="rounded-[14px] border border-[rgba(59,77,67,0.12)] bg-white/60 p-4">
        <div className="flex items-center justify-between gap-3">
          <p className="text-sm text-[#7A8580]">No other lines in this catalog matched this song by {tierLabel}.</p>
          <button onClick={onDismiss} className="text-[#7A8580] hover:text-[#3D4A44] transition-colors">
            <XMarkIcon className="w-4 h-4" />
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="rounded-[14px] border border-[rgba(91,138,114,0.3)] bg-[rgba(91,138,114,0.08)] p-4">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="flex items-start gap-3">
          <CheckCircleIcon className="w-5 h-5 text-[#5B8A72] mt-0.5 shrink-0" />
          <div>
            <p className="text-sm font-medium text-[#3D4A44]">
              Linked {lines} more {lineWord} across {stmts} {stmtWord}, matched by {tierLabel}.
            </p>
            <p className="text-xs text-[#7A8580] mt-1">
              Existing confirmed and ignored lines were left unchanged.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {propagation.batch_id && (
            <button
              onClick={onUndo}
              disabled={busy}
              className="flex items-center gap-1 px-3 py-1.5 text-xs border border-[#5B8A72] text-[#5B8A72] rounded-lg hover:bg-[rgba(91,138,114,0.06)] transition-all font-medium disabled:opacity-50"
            >
              <ArrowPathIcon className="w-3.5 h-3.5" /> {busy ? 'Undoing...' : 'Undo'}
            </button>
          )}
          <button
            onClick={onDismiss}
            disabled={busy}
            className="px-2 py-1.5 text-[#7A8580] hover:text-[#3D4A44] rounded-lg transition-colors disabled:opacity-50"
          >
            <XMarkIcon className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )
}

function MatchingPane({ queue, queueLoading, selectedLine, onSelectLine, suggestions, suggestionsLoading, onConfirm, onReject, onIgnore, bulkThreshold, setBulkThreshold, onBulkConfirm, bulkConfirming, propagation, propagationBusy, onApplyTitleArtist, onUndoPropagation, onDismissPropagation }) {
  return (
    <div className="space-y-4">
      <PropagationBanner
        propagation={propagation}
        busy={propagationBusy}
        onApplyTitleArtist={onApplyTitleArtist}
        onUndo={onUndoPropagation}
        onDismiss={onDismissPropagation}
      />
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h3 className="text-lg font-semibold text-[#3D4A44]">Matching Console</h3>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <label className="text-xs text-[#7A8580]">Threshold:</label>
            <input
              type="number"
              value={bulkThreshold}
              onChange={e => setBulkThreshold(Number(e.target.value))}
              min={50}
              max={100}
              className="w-16 px-2 py-1 border border-[rgba(59,77,67,0.15)] rounded-lg text-xs text-[#3D4A44] bg-white focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent outline-none"
            />
            <span className="text-xs text-[#7A8580]">%</span>
          </div>
          <button
            onClick={onBulkConfirm}
            disabled={bulkConfirming}
            className="flex items-center gap-2 px-3 py-1.5 text-sm bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-xl hover:shadow-[0px_4px_12px_rgba(91,138,114,0.3)] transition-all font-medium disabled:opacity-50"
          >
            <CheckCircleIcon className="w-4 h-4" /> {bulkConfirming ? 'Confirming...' : 'Bulk Confirm High-Confidence'}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white/60 backdrop-blur-xl rounded-[14px] border border-[rgba(59,77,67,0.08)] overflow-hidden">
          <div className="p-4 border-b border-[rgba(59,77,67,0.08)]">
            <h4 className="text-sm font-semibold text-[#3D4A44]">Queue ({queue.length} lines)</h4>
          </div>
          {queueLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-[#5B8A72] border-t-transparent"></div>
            </div>
          ) : queue.length === 0 ? (
            <div className="text-center py-12">
              <CheckCircleIcon className="w-12 h-12 text-green-400 mx-auto mb-3" />
              <p className="text-sm text-[#7A8580]">All lines matched or ignored</p>
            </div>
          ) : (
            <div className="max-h-[500px] overflow-y-auto divide-y divide-[rgba(59,77,67,0.05)]">
              {queue.map(line => {
                const colors = MATCH_STATUS_COLORS[line.match_status] || { bg: 'bg-gray-100', text: 'text-gray-700' }
                const isSelected = selectedLine?.id === line.id
                return (
                  <button
                    key={line.id}
                    onClick={() => onSelectLine(line)}
                    className={`w-full text-left px-4 py-3 hover:bg-[rgba(91,138,114,0.04)] transition-colors ${isSelected ? 'bg-[rgba(91,138,114,0.08)]' : ''}`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-[#3D4A44] truncate">{line.track_title_raw || 'Unknown Track'}</p>
                        <p className="text-xs text-[#7A8580] truncate">{line.artist_name_raw || 'Unknown Artist'}</p>
                      </div>
                      <div className="flex items-center gap-2 ml-3">
                        <span className="text-xs font-medium text-[#3D4A44]">{formatDollars(line.net_amount)}</span>
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium ${colors.bg} ${colors.text}`}>
                          {line.match_status}
                        </span>
                      </div>
                    </div>
                  </button>
                )
              })}
            </div>
          )}
        </div>

        <div className="bg-white/60 backdrop-blur-xl rounded-[14px] border border-[rgba(59,77,67,0.08)] overflow-hidden">
          <div className="p-4 border-b border-[rgba(59,77,67,0.08)]">
            <h4 className="text-sm font-semibold text-[#3D4A44]">Suggestions & Actions</h4>
          </div>
          {!selectedLine ? (
            <div className="text-center py-12">
              <MusicalNoteIcon className="w-12 h-12 text-[#7A8580] mx-auto mb-3 opacity-40" />
              <p className="text-sm text-[#7A8580]">Select a line to see match suggestions</p>
            </div>
          ) : (
            <div className="p-4 space-y-4">
              <div className="bg-[rgba(91,138,114,0.06)] rounded-xl p-4">
                <p className="text-sm font-medium text-[#3D4A44]">{selectedLine.track_title_raw}</p>
                <p className="text-xs text-[#7A8580]">{selectedLine.artist_name_raw}</p>
                {selectedLine.store && <p className="text-xs text-[#7A8580] mt-1">Source: {selectedLine.store}</p>}
                {selectedLine.isrc && <p className="text-xs text-[#7A8580] font-mono mt-1">ISRC: {selectedLine.isrc}</p>}
                <p className="text-xs text-[#7A8580] mt-1">Amount: {formatDollars(selectedLine.net_amount)}</p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={onReject}
                  className="flex items-center gap-1 px-3 py-1.5 text-xs bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors font-medium"
                >
                  <HandThumbDownIcon className="w-3.5 h-3.5" /> Reject
                </button>
                <button
                  onClick={() => onIgnore()}
                  className="flex items-center gap-1 px-3 py-1.5 text-xs bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors font-medium"
                >
                  <NoSymbolIcon className="w-3.5 h-3.5" /> Ignore
                </button>
              </div>

              <div>
                <h5 className="text-xs font-semibold text-[#7A8580] uppercase mb-2">Suggested Matches</h5>
                {suggestionsLoading ? (
                  <div className="flex items-center justify-center py-6">
                    <div className="inline-block animate-spin rounded-full h-6 w-6 border-3 border-[#5B8A72] border-t-transparent"></div>
                  </div>
                ) : suggestions.length === 0 ? (
                  <p className="text-sm text-[#7A8580] text-center py-4">No suggestions found</p>
                ) : (
                  <div className="space-y-2 max-h-[300px] overflow-y-auto">
                    {suggestions.map(s => (
                      <div key={s.song_id} className="border border-[rgba(59,77,67,0.08)] rounded-xl p-3 hover:bg-[rgba(91,138,114,0.04)] transition-colors">
                        <div className="flex items-center justify-between">
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-[#3D4A44] truncate">{s.title}</p>
                            <p className="text-xs text-[#7A8580]">{s.primary_artist || '—'}</p>
                            {s.isrc && <p className="text-xs text-[#7A8580] font-mono">ISRC: {s.isrc}</p>}
                          </div>
                          <div className="flex items-center gap-2 ml-3">
                            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                              s.confidence >= 85 ? 'bg-green-100 text-green-700' : s.confidence >= 60 ? 'bg-amber-100 text-amber-700' : 'bg-red-100 text-red-700'
                            }`}>
                              {s.confidence.toFixed(0)}%
                            </span>
                            <button
                              onClick={() => onConfirm(s.song_id)}
                              className="flex items-center gap-1 px-2 py-1 text-xs bg-[#5B8A72] text-white rounded-lg hover:bg-[#4a7a62] transition-colors font-medium"
                            >
                              <HandThumbUpIcon className="w-3.5 h-3.5" /> Confirm
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function AllocationPane({ allocations, loading, isProcessed }) {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="inline-block animate-spin rounded-full h-10 w-10 border-4 border-[#5B8A72] border-t-transparent"></div>
      </div>
    )
  }

  return (
    <div className="bg-white/80 backdrop-blur-xl rounded-[18px] shadow-am border border-[rgba(59,77,67,0.08)]">
      <div className="p-6 border-b border-[rgba(59,77,67,0.08)]">
        <h3 className="text-lg font-semibold text-[#3D4A44]">{isProcessed ? 'Allocation Summary' : 'Allocation Preview'}</h3>
        <p className="text-sm text-[#7A8580] mt-1">{isProcessed ? 'Actual earnings distribution from the latest processing run' : 'Preview how earnings will be distributed to payees'}</p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-[#EEF1EC]">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-[#7A8580] uppercase tracking-wider">Payee Name</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-[#7A8580] uppercase tracking-wider">Type</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-[#7A8580] uppercase tracking-wider">Earnings</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-[#7A8580] uppercase tracking-wider">Fees</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-[#7A8580] uppercase tracking-wider">Recoupment</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-[#7A8580] uppercase tracking-wider">Net Payable</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[rgba(59,77,67,0.05)]">
            {allocations.map((a, i) => (
              <tr key={i} className="hover:bg-[rgba(91,138,114,0.04)]">
                <td className="px-4 py-3 text-sm font-medium text-[#3D4A44]">{a.payee_name || '—'}</td>
                <td className="px-4 py-3">
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-[rgba(91,138,114,0.1)] text-[#5B8A72]">
                    {a.payee_type || '—'}
                  </span>
                </td>
                <td className="px-4 py-3 text-sm text-right font-medium text-[#3D4A44]">{formatCents(a.earnings_cents)}</td>
                <td className="px-4 py-3 text-sm text-right text-[#7A8580]">{formatCents(a.fees_cents)}</td>
                <td className="px-4 py-3 text-sm text-right text-[#7A8580]">{formatCents(a.recoupment_cents)}</td>
                <td className="px-4 py-3 text-sm text-right font-semibold text-[#3D4A44]">{formatCents(a.payable_cents)}</td>
              </tr>
            ))}
            {allocations.length === 0 && (
              <tr><td colSpan={6} className="px-6 py-12 text-center text-sm text-[#7A8580]">{isProcessed ? 'No allocations were recorded during processing.' : 'No allocation data available. Match statement lines and process the statement to see allocations.'}</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function RunsPane({ runs, loading, showReprocess, setShowReprocess, reprocessReason, setReprocessReason, onReprocess, reprocessing }) {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="inline-block animate-spin rounded-full h-10 w-10 border-4 border-[#5B8A72] border-t-transparent"></div>
      </div>
    )
  }

  const RUN_STATUS_COLORS = {
    COMPLETED: { bg: 'bg-green-100', text: 'text-green-700' },
    RUNNING: { bg: 'bg-blue-100', text: 'text-blue-700' },
    FAILED: { bg: 'bg-red-100', text: 'text-red-700' },
    PENDING: { bg: 'bg-amber-100', text: 'text-amber-700' },
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-[#3D4A44]">Run History</h3>
        <button
          onClick={() => setShowReprocess(true)}
          className="flex items-center gap-2 px-4 py-2 bg-[rgba(91,138,114,0.1)] text-[#5B8A72] rounded-xl hover:bg-[rgba(91,138,114,0.2)] transition-colors text-sm font-medium"
        >
          <ArrowPathIcon className="w-4 h-4" /> Reprocess
        </button>
      </div>

      <div className="bg-white/80 backdrop-blur-xl rounded-[18px] shadow-am border border-[rgba(59,77,67,0.08)]">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-[#EEF1EC]">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-[#7A8580] uppercase tracking-wider">Version</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[#7A8580] uppercase tracking-wider">Status</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[#7A8580] uppercase tracking-wider">Started</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[#7A8580] uppercase tracking-wider">Completed</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[#7A8580] uppercase tracking-wider">Notes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[rgba(59,77,67,0.05)]">
              {runs.map(run => {
                const colors = RUN_STATUS_COLORS[run.status] || { bg: 'bg-gray-100', text: 'text-gray-700' }
                return (
                  <tr key={run.id} className="hover:bg-[rgba(91,138,114,0.04)]">
                    <td className="px-4 py-3 text-sm font-medium text-[#3D4A44]">v{run.run_version}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${colors.bg} ${colors.text}`}>
                        {run.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-[#7A8580]">{formatDate(run.started_at)}</td>
                    <td className="px-4 py-3 text-sm text-[#7A8580]">{formatDate(run.completed_at)}</td>
                    <td className="px-4 py-3 text-sm text-[#7A8580]">{run.notes || '—'}</td>
                  </tr>
                )
              })}
              {runs.length === 0 && (
                <tr><td colSpan={5} className="px-6 py-12 text-center text-sm text-[#7A8580]">No processing runs yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {showReprocess && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm p-4">
          <div className="bg-white rounded-[18px] shadow-2xl w-full max-w-md">
            <div className="flex items-center justify-between p-6 border-b border-[rgba(59,77,67,0.08)]">
              <h3 className="text-lg font-semibold text-[#3D4A44]">Reprocess Statement</h3>
              <button onClick={() => setShowReprocess(false)} className="p-2 hover:bg-[rgba(59,77,67,0.06)] rounded-full transition-colors">
                <XMarkIcon className="w-5 h-5 text-[#7A8580]" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Reason for reprocessing</label>
                <textarea
                  value={reprocessReason}
                  onChange={e => setReprocessReason(e.target.value)}
                  rows={3}
                  placeholder="Describe why this statement needs reprocessing..."
                  className="w-full px-4 py-2.5 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm text-[#3D4A44] bg-white focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent outline-none resize-none"
                />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button onClick={() => setShowReprocess(false)} className="px-4 py-2 text-sm text-[#7A8580] hover:text-[#3D4A44] transition-colors">Cancel</button>
                <button
                  onClick={onReprocess}
                  disabled={!reprocessReason.trim() || reprocessing}
                  className="px-5 py-2.5 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-xl hover:shadow-[0px_4px_12px_rgba(91,138,114,0.3)] transition-all text-sm font-medium disabled:opacity-50"
                >
                  {reprocessing ? 'Reprocessing...' : 'Reprocess'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function ReconciliationPane({ orgId, statementId }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [reportedGross, setReportedGross] = useState('')
  const [reportedWithholding, setReportedWithholding] = useState('')
  const [reportedNet, setReportedNet] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!orgId || !statementId) return
    setLoading(true)
    axios.get(`/api/royalty-processing/${orgId}/statements/${statementId}/reconciliation`)
      .then(res => setData(res.data))
      .catch(err => console.error('Failed to load reconciliation:', err))
      .finally(() => setLoading(false))
  }, [orgId, statementId])

  const handleSetTotals = async () => {
    setSaving(true)
    try {
      const params = new URLSearchParams()
      if (reportedGross) params.set('gross', reportedGross)
      if (reportedWithholding) params.set('withholding', reportedWithholding)
      if (reportedNet) params.set('net', reportedNet)
      await axios.post(`/api/royalty-processing/${orgId}/statements/${statementId}/set-reported-totals?${params}`)
      const res = await axios.get(`/api/royalty-processing/${orgId}/statements/${statementId}/reconciliation`)
      setData(res.data)
      setReportedGross('')
      setReportedWithholding('')
      setReportedNet('')
    } catch (err) {
      console.error('Failed to set totals:', err)
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div className="flex justify-center py-12"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#5B8A72]" /></div>

  const statusColor = {
    PASS: 'bg-green-100 text-green-700 border-green-200',
    WARN: 'bg-amber-100 text-amber-700 border-amber-200',
    FAIL: 'bg-red-100 text-red-700 border-red-200',
  }

  return (
    <div className="space-y-6">
      {data?.overall_status && (
        <div className={`flex items-center gap-3 p-4 rounded-xl border ${statusColor[data.overall_status] || 'bg-gray-100 text-gray-700 border-gray-200'}`}>
          {data.overall_status === 'PASS' ? <CheckCircleIcon className="w-6 h-6" /> : <ExclamationCircleIcon className="w-6 h-6" />}
          <div>
            <p className="font-semibold text-sm">Reconciliation: {data.overall_status}</p>
            <p className="text-xs opacity-75">{data.line_count} lines analyzed</p>
          </div>
        </div>
      )}

      {data?.computed_totals && (
        <div className="bg-white/80 backdrop-blur-xl rounded-[18px] shadow-am border border-[rgba(59,77,67,0.08)] p-6">
          <h4 className="text-sm font-semibold text-[#3D4A44] mb-4">Computed Totals</h4>
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center p-3 bg-[rgba(91,138,114,0.06)] rounded-xl">
              <p className="text-xs text-[#7A8580] mb-1">Gross</p>
              <p className="text-lg font-bold text-[#3D4A44]">{formatDollars(data.computed_totals.gross)}</p>
            </div>
            <div className="text-center p-3 bg-[rgba(91,138,114,0.06)] rounded-xl">
              <p className="text-xs text-[#7A8580] mb-1">Deductions</p>
              <p className="text-lg font-bold text-[#3D4A44]">{formatDollars(data.computed_totals.deductions)}</p>
            </div>
            <div className="text-center p-3 bg-[rgba(91,138,114,0.06)] rounded-xl">
              <p className="text-xs text-[#7A8580] mb-1">Net</p>
              <p className="text-lg font-bold text-[#5B8A72]">{formatDollars(data.computed_totals.net)}</p>
            </div>
          </div>
        </div>
      )}

      {data?.checks?.length > 0 && (
        <div className="bg-white/80 backdrop-blur-xl rounded-[18px] shadow-am border border-[rgba(59,77,67,0.08)] p-6">
          <h4 className="text-sm font-semibold text-[#3D4A44] mb-4">Control Checks</h4>
          <div className="space-y-3">
            {data.checks.map((check, i) => (
              <div key={i} className={`flex items-center justify-between p-3 rounded-xl border ${statusColor[check.status] || 'bg-gray-50 border-gray-200'}`}>
                <div>
                  <p className="text-sm font-medium capitalize">{(check.check || '').replace(/_/g, ' ')}</p>
                  {check.reported != null && <p className="text-xs opacity-75">Reported: {formatDollars(check.reported)}</p>}
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold">{check.status}</p>
                  {check.difference != null && <p className="text-xs opacity-75">Diff: {formatDollars(check.difference)}</p>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="bg-white/80 backdrop-blur-xl rounded-[18px] shadow-am border border-[rgba(59,77,67,0.08)] p-6">
        <h4 className="text-sm font-semibold text-[#3D4A44] mb-4">Set Reported Totals</h4>
        <p className="text-xs text-[#7A8580] mb-4">Enter the totals from the original statement to compare against computed values.</p>
        <div className="grid grid-cols-3 gap-3 mb-4">
          <div>
            <label className="block text-xs text-[#7A8580] mb-1">Gross</label>
            <input type="number" step="0.01" value={reportedGross} onChange={e => setReportedGross(e.target.value)} placeholder="0.00" className="w-full px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm focus:ring-2 focus:ring-[#5B8A72] outline-none" />
          </div>
          <div>
            <label className="block text-xs text-[#7A8580] mb-1">Withholding</label>
            <input type="number" step="0.01" value={reportedWithholding} onChange={e => setReportedWithholding(e.target.value)} placeholder="0.00" className="w-full px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm focus:ring-2 focus:ring-[#5B8A72] outline-none" />
          </div>
          <div>
            <label className="block text-xs text-[#7A8580] mb-1">Net</label>
            <input type="number" step="0.01" value={reportedNet} onChange={e => setReportedNet(e.target.value)} placeholder="0.00" className="w-full px-3 py-2 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm focus:ring-2 focus:ring-[#5B8A72] outline-none" />
          </div>
        </div>
        <button onClick={handleSetTotals} disabled={saving || (!reportedGross && !reportedWithholding && !reportedNet)} className="px-5 py-2.5 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-xl hover:shadow-[0px_4px_12px_rgba(91,138,114,0.3)] transition-all text-sm font-medium disabled:opacity-50">
          {saving ? 'Saving...' : 'Save & Reconcile'}
        </button>
      </div>
    </div>
  )
}


function ClassificationPane({ orgId, statementId }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!orgId || !statementId) return
    setLoading(true)
    axios.get(`/api/royalty-processing/${orgId}/statements/${statementId}/classification`)
      .then(res => setData(res.data))
      .catch(err => console.error('Failed to load classification:', err))
      .finally(() => setLoading(false))
  }, [orgId, statementId])

  if (loading) return <div className="flex justify-center py-12"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#5B8A72]" /></div>

  const rightColors = {
    mechanical: 'bg-blue-100 text-blue-700',
    performance: 'bg-purple-100 text-purple-700',
    sync: 'bg-amber-100 text-amber-700',
    print_lyrics: 'bg-pink-100 text-pink-700',
    neighboring_rights: 'bg-teal-100 text-teal-700',
    other: 'bg-gray-100 text-gray-600',
    unclassified: 'bg-gray-100 text-gray-500',
  }

  const channelColors = {
    streaming: 'bg-green-100 text-green-700',
    download: 'bg-blue-100 text-blue-700',
    broadcast: 'bg-orange-100 text-orange-700',
    live: 'bg-red-100 text-red-700',
    ugc: 'bg-yellow-100 text-yellow-700',
    social: 'bg-pink-100 text-pink-700',
    physical: 'bg-gray-100 text-gray-700',
    other: 'bg-gray-100 text-gray-600',
    unclassified: 'bg-gray-100 text-gray-500',
  }

  const renderBar = (items, colorMap, label) => {
    const total = items.reduce((sum, i) => sum + Math.abs(i.net_total), 0)
    if (total === 0) return null
    return (
      <div className="bg-white/80 backdrop-blur-xl rounded-[18px] shadow-am border border-[rgba(59,77,67,0.08)] p-6">
        <h4 className="text-sm font-semibold text-[#3D4A44] mb-4">{label}</h4>
        <div className="space-y-3">
          {items.sort((a, b) => Math.abs(b.net_total) - Math.abs(a.net_total)).map((item, i) => {
            const pct = total > 0 ? (Math.abs(item.net_total) / total * 100) : 0
            const key = item.category || item.channel || item.territory || 'unknown'
            return (
              <div key={i}>
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full capitalize ${colorMap[key] || 'bg-gray-100 text-gray-600'}`}>
                      {key.replace(/_/g, ' ')}
                    </span>
                    <span className="text-xs text-[#7A8580]">{item.line_count} lines</span>
                  </div>
                  <span className="text-sm font-semibold text-[#3D4A44]">{formatDollars(item.net_total)}</span>
                </div>
                <div className="h-2 bg-[rgba(59,77,67,0.06)] rounded-full overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-[#5B8A72] to-[#7BA594] rounded-full transition-all" style={{ width: `${pct}%` }} />
                </div>
              </div>
            )
          })}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {data?.by_right_category && renderBar(data.by_right_category, rightColors, 'By Right Category')}
      {data?.by_channel && renderBar(data.by_channel, channelColors, 'By Channel')}
      {data?.by_territory && (
        <div className="bg-white/80 backdrop-blur-xl rounded-[18px] shadow-am border border-[rgba(59,77,67,0.08)] p-6">
          <h4 className="text-sm font-semibold text-[#3D4A44] mb-4">Top Territories</h4>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {data.by_territory.map((t, i) => (
              <div key={i} className="text-center p-3 bg-[rgba(91,138,114,0.06)] rounded-xl">
                <p className="text-lg font-bold text-[#3D4A44]">{t.territory}</p>
                <p className="text-xs text-[#7A8580]">{formatDollars(t.net_total)}</p>
                <p className="text-xs text-[#A0A8A3]">{t.line_count} lines</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}


function ExportsPane({ onExport }) {
  const exports = [
    { key: 'unmatched', label: 'Unmatched Lines', description: 'Download CSV of all unmatched statement lines', icon: ExclamationCircleIcon },
    { key: 'allocation', label: 'Allocation Preview', description: 'Download CSV of allocation preview per payee', icon: CurrencyDollarIcon },
    { key: 'payables', label: 'Payables Report', description: 'Download CSV of payable ledger entries', icon: DocumentTextIcon },
  ]

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      {exports.map(exp => (
        <div key={exp.key} className="bg-white/80 backdrop-blur-xl rounded-[18px] shadow-am p-6 border border-[rgba(59,77,67,0.08)]">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-[rgba(91,138,114,0.1)] rounded-lg">
              <exp.icon className="w-5 h-5 text-[#5B8A72]" />
            </div>
            <h4 className="text-sm font-semibold text-[#3D4A44]">{exp.label}</h4>
          </div>
          <p className="text-xs text-[#7A8580] mb-4">{exp.description}</p>
          <button
            onClick={() => onExport(exp.key)}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 text-sm bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-xl hover:shadow-[0px_4px_12px_rgba(91,138,114,0.3)] transition-all font-medium"
          >
            <ArrowDownTrayIcon className="w-4 h-4" /> Download CSV
          </button>
        </div>
      ))}
    </div>
  )
}
