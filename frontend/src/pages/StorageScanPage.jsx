import React, { useState, useEffect, useCallback } from 'react'
import axios from 'axios'
import {
  FolderIcon, CloudArrowUpIcon, MagnifyingGlassIcon, PlusIcon,
  TrashIcon, PencilSquareIcon, CheckCircleIcon, XCircleIcon,
  ArrowPathIcon, FunnelIcon, SparklesIcon, LinkIcon,
  ChevronDownIcon, XMarkIcon, FolderOpenIcon, GlobeAltIcon,
  ChartBarIcon, MusicalNoteIcon, ExclamationTriangleIcon
} from '@heroicons/react/24/outline'
import FolderPicker from '../components/FolderPicker'

const CONFIDENCE_COLORS = {
  HIGH: 'bg-green-100 text-green-800',
  MEDIUM: 'bg-yellow-100 text-yellow-800',
  LOW: 'bg-orange-100 text-orange-800',
  NONE: 'bg-red-100 text-red-800'
}

const PROVIDER_LABELS = {
  DROPBOX: 'Dropbox',
  GOOGLE_DRIVE: 'Google Drive'
}

function formatFileSize(bytes) {
  if (!bytes) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1048576).toFixed(1)} MB`
}

function formatDate(dateStr) {
  if (!dateStr) return 'Never'
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit'
  })
}

function getAuthHeaders() {
  return { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } }
}

function ProviderIcon({ provider, className = 'w-5 h-5' }) {
  if (provider === 'DROPBOX') {
    return (
      <svg className={className} viewBox="0 0 24 24" fill="#0061FF">
        <path d="M6 2l6 3.75L6 9.5 0 5.75zM18 2l6 3.75-6 3.75-6-3.75zM0 13.25L6 9.5l6 3.75L6 17zM18 9.5l6 3.75L18 17l-6-3.75zM6 18.25l6-3.75 6 3.75-6 3.75z"/>
      </svg>
    )
  }
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none">
      <path d="M4.5 9.5l7-4.5 7 4.5M4.5 9.5v5l7 4.5m-7-9.5l7 4.5m7-4.5v5l-7 4.5m7-9.5l-7 4.5" stroke="#34A853" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}

function CoverageBar({ label, value, total, color = 'bg-[#5B8A72]' }) {
  const pct = total > 0 ? Math.round((value / total) * 100) : 0
  return (
    <div>
      <div className="flex justify-between text-[13px] mb-1">
        <span className="text-[#3D4A44] font-medium">{label}</span>
        <span className="text-[#7A8580]">{value} / {total} ({pct}%)</span>
      </div>
      <div className="h-2 bg-[#E0E5DE] rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all duration-500`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

export default function StorageScanPage() {
  const [orgId, setOrgId] = useState(null)

  const [activeTab, setActiveTab] = useState('overview')
  const [toast, setToast] = useState(null)

  const [coverage, setCoverage] = useState(null)
  const [coverageLoading, setCoverageLoading] = useState(false)

  const [links, setLinks] = useState([])
  const [linksLoading, setLinksLoading] = useState(false)
  const [creators, setCreators] = useState([])
  const [providers, setProviders] = useState([])
  const [showLinkModal, setShowLinkModal] = useState(false)
  const [editingLink, setEditingLink] = useState(null)
  const [linkForm, setLinkForm] = useState({ creator_id: '', provider: 'DROPBOX', folder_path: '', scan_recursive: true })
  const [linkSaving, setLinkSaving] = useState(false)
  const [folderPickerOpen, setFolderPickerOpen] = useState(false)
  const [scanningId, setScanningId] = useState(null)
  const [scanningAll, setScanningAll] = useState(false)

  const [batches, setBatches] = useState([])
  const [selectedBatch, setSelectedBatch] = useState('')
  const [results, setResults] = useState([])
  const [resultsLoading, setResultsLoading] = useState(false)
  const [confidenceFilter, setConfidenceFilter] = useState('')
  const [creatorFilter, setCreatorFilter] = useState('')
  const [showReassignModal, setShowReassignModal] = useState(null)
  const [songSearch, setSongSearch] = useState('')
  const [songSearchResults, setSongSearchResults] = useState([])
  const [songSearchLoading, setSongSearchLoading] = useState(false)
  const [bulkApproving, setBulkApproving] = useState(false)

  const [analyzeLoading, setAnalyzeLoading] = useState(false)
  const [analyzeStatus, setAnalyzeStatus] = useState(null)

  const [orgScanFolder, setOrgScanFolder] = useState('/')
  const [orgScanRunning, setOrgScanRunning] = useState(false)
  const [orgScanResult, setOrgScanResult] = useState(null)
  const [orgScanFolderPickerOpen, setOrgScanFolderPickerOpen] = useState(false)

  useEffect(() => {
    const fetchOrg = async () => {
      try {
        const res = await axios.get('/api/organizations/current', getAuthHeaders())
        setOrgId(res.data?.id)
      } catch (err) {
        console.error('Failed to fetch org:', err)
      }
    }
    fetchOrg()
  }, [])

  const showToast = useCallback((message, type = 'success') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 3000)
  }, [])

  const loadCoverage = useCallback(async () => {
    if (!orgId) return
    setCoverageLoading(true)
    try {
      const res = await axios.get(`/api/storage-scan/org/${orgId}/coverage`, getAuthHeaders())
      setCoverage(res.data)
    } catch (err) {
      console.error('Failed to load coverage:', err)
    } finally {
      setCoverageLoading(false)
    }
  }, [orgId])

  const loadLinks = useCallback(async () => {
    if (!orgId) {
      setLinksLoading(false)
      return
    }
    setLinksLoading(true)
    try {
      const linksRes = await axios.get(`/api/storage-scan/org/${orgId}/links`, getAuthHeaders())
      setLinks(linksRes.data || [])
    } catch (err) {
      console.error('Failed to load links:', err)
    }
    try {
      const creatorsRes = await axios.get(`/api/creators/org/${orgId}`, getAuthHeaders())
      setCreators(creatorsRes.data || [])
    } catch (err) {
      console.error('Failed to load creators:', err)
    }
    try {
      const providersRes = await axios.get(`/api/storage-scan/org/${orgId}/providers`, getAuthHeaders())
      setProviders(providersRes.data || [])
    } catch (err) {
      console.error('Failed to load providers:', err)
    }
    setLinksLoading(false)
  }, [orgId])

  const loadBatches = useCallback(async () => {
    if (!orgId) return
    try {
      const res = await axios.get(`/api/storage-scan/org/${orgId}/batches`, getAuthHeaders())
      setBatches(res.data || [])
    } catch (err) {
      console.error('Failed to load batches:', err)
    }
  }, [orgId])

  const loadResults = useCallback(async () => {
    if (!orgId) return
    setResultsLoading(true)
    try {
      const params = new URLSearchParams()
      if (selectedBatch) params.append('scan_batch_id', selectedBatch)
      params.append('reviewed', 'false')
      const res = await axios.get(`/api/storage-scan/org/${orgId}/results?${params}`, getAuthHeaders())
      setResults(res.data || [])
    } catch (err) {
      console.error('Failed to load results:', err)
    } finally {
      setResultsLoading(false)
    }
  }, [orgId, selectedBatch])

  useEffect(() => {
    if (!orgId) return
    if (activeTab === 'overview') loadCoverage()
    if (activeTab === 'links') loadLinks()
    if (activeTab === 'results') { loadBatches(); loadResults() }
    if (activeTab === 'analyze') loadBatches()
  }, [orgId, activeTab, loadLinks, loadBatches, loadResults, loadCoverage])

  useEffect(() => {
    if (activeTab === 'results') loadResults()
  }, [selectedBatch, loadResults, activeTab])

  const handleSaveLink = async () => {
    if (!orgId || !linkForm.creator_id || !linkForm.folder_path) return
    setLinkSaving(true)
    try {
      const payload = {
        creator_id: parseInt(linkForm.creator_id),
        provider: linkForm.provider,
        folder_path: linkForm.folder_path,
        scan_recursive: linkForm.scan_recursive,
      }
      if (editingLink) {
        await axios.put(`/api/storage-scan/org/${orgId}/links/${editingLink.id}`, payload, getAuthHeaders())
        showToast('Link updated')
      } else {
        await axios.post(`/api/storage-scan/org/${orgId}/links`, payload, getAuthHeaders())
        showToast('Link created')
      }
      setShowLinkModal(false)
      setEditingLink(null)
      setLinkForm({ creator_id: '', provider: 'DROPBOX', folder_path: '', scan_recursive: true })
      loadLinks()
    } catch (err) {
      showToast(err.response?.data?.detail || 'Failed to save link', 'error')
    } finally {
      setLinkSaving(false)
    }
  }

  const handleDeleteLink = async (linkId) => {
    if (!window.confirm('Delete this storage link?')) return
    try {
      await axios.delete(`/api/storage-scan/org/${orgId}/links/${linkId}`, getAuthHeaders())
      setLinks(prev => prev.filter(l => l.id !== linkId))
      showToast('Link deleted')
    } catch (err) {
      showToast('Failed to delete link', 'error')
    }
  }

  const handleScanSingle = async (linkId) => {
    setScanningId(linkId)
    try {
      await axios.post(`/api/storage-scan/org/${orgId}/scan/${linkId}`, {}, getAuthHeaders())
      showToast('Scan started')
      loadLinks()
    } catch (err) {
      showToast(err.response?.data?.detail || 'Scan failed', 'error')
    } finally {
      setScanningId(null)
    }
  }

  const handleScanAll = async () => {
    setScanningAll(true)
    try {
      await axios.post(`/api/storage-scan/org/${orgId}/scan-all`, {}, getAuthHeaders())
      showToast('Scanning all links...')
      loadLinks()
    } catch (err) {
      showToast(err.response?.data?.detail || 'Scan failed', 'error')
    } finally {
      setScanningAll(false)
    }
  }

  const handleApprove = async (resultId, songId) => {
    try {
      await axios.post(`/api/storage-scan/org/${orgId}/results/${resultId}/approve`, { song_id: songId }, getAuthHeaders())
      setResults(prev => prev.filter(r => r.id !== resultId))
      showToast('Approved')
    } catch (err) {
      showToast('Approve failed', 'error')
    }
  }

  const handleReject = async (resultId) => {
    try {
      await axios.post(`/api/storage-scan/org/${orgId}/results/${resultId}/reject`, {}, getAuthHeaders())
      setResults(prev => prev.filter(r => r.id !== resultId))
      showToast('Rejected')
    } catch (err) {
      showToast('Reject failed', 'error')
    }
  }

  const handleReassign = async (resultId, songId) => {
    try {
      await axios.post(`/api/storage-scan/org/${orgId}/results/${resultId}/reassign`, { song_id: songId }, getAuthHeaders())
      setResults(prev => prev.filter(r => r.id !== resultId))
      setShowReassignModal(null)
      showToast('Reassigned')
    } catch (err) {
      showToast('Reassign failed', 'error')
    }
  }

  const handleBulkApprove = async () => {
    if (!selectedBatch) { showToast('Select a scan batch first', 'error'); return }
    setBulkApproving(true)
    try {
      const res = await axios.post(`/api/storage-scan/org/${orgId}/bulk-approve`, {
        scan_batch_id: selectedBatch, min_confidence: 'HIGH'
      }, getAuthHeaders())
      showToast(`Approved ${res.data?.approved_count || res.data?.approved || 0} results`)
      loadResults()
    } catch (err) {
      showToast('Bulk approve failed', 'error')
    } finally {
      setBulkApproving(false)
    }
  }

  const handleSongSearch = async (query) => {
    setSongSearch(query)
    if (query.length < 2) { setSongSearchResults([]); return }
    setSongSearchLoading(true)
    try {
      const res = await axios.get(`/api/songs/org/${orgId}?search=${encodeURIComponent(query)}&limit=10`, getAuthHeaders())
      setSongSearchResults(res.data || [])
    } catch { setSongSearchResults([]) }
    finally { setSongSearchLoading(false) }
  }

  const handleAnalyzeLinked = async () => {
    if (!selectedBatch && batches.length === 0) { showToast('No scan batch available', 'error'); return }
    setAnalyzeLoading(true)
    try {
      const batchId = selectedBatch || (batches[0]?.id)
      const res = await axios.post(`/api/storage-scan/org/${orgId}/analyze-linked`, { scan_batch_id: batchId }, getAuthHeaders())
      setAnalyzeStatus(res.data)
      showToast('Analysis started')
    } catch (err) {
      showToast(err.response?.data?.detail || 'Analysis failed', 'error')
    } finally {
      setAnalyzeLoading(false)
    }
  }

  const handleAnalyzeAllUnanalyzed = async () => {
    setAnalyzeLoading(true)
    try {
      const res = await axios.post(`/api/storage-scan/org/${orgId}/analyze-all-unanalyzed`, {}, getAuthHeaders())
      setAnalyzeStatus(res.data)
      showToast(`Queued ${res.data?.queued || 0} assets for analysis`)
      loadCoverage()
    } catch (err) {
      showToast(err.response?.data?.detail || 'Analysis failed', 'error')
    } finally {
      setAnalyzeLoading(false)
    }
  }

  const handleOrgWideScan = async () => {
    setOrgScanRunning(true)
    setOrgScanResult(null)
    try {
      const res = await axios.post(`/api/storage-scan/org/${orgId}/org-scan`, {
        folder_path: orgScanFolder || '/'
      }, getAuthHeaders())
      setOrgScanResult(res.data)
      showToast(`Scan complete: ${res.data.auto_linked} auto-linked, ${res.data.needs_review} need review`)
      loadCoverage()
    } catch (err) {
      showToast(err.response?.data?.detail || 'Org-wide scan failed', 'error')
    } finally {
      setOrgScanRunning(false)
    }
  }

  const openEditLink = (link) => {
    setEditingLink(link)
    setLinkForm({
      creator_id: link.creator_id || '',
      provider: link.provider || 'DROPBOX',
      folder_path: link.folder_path || '',
      scan_recursive: link.scan_recursive !== false
    })
    setShowLinkModal(true)
  }

  const openAddLink = () => {
    setEditingLink(null)
    setLinkForm({ creator_id: '', provider: 'DROPBOX', folder_path: '', scan_recursive: true })
    setShowLinkModal(true)
  }

  const filteredResults = results.filter(r => {
    if (confidenceFilter && r.match_confidence !== confidenceFilter) return false
    if (creatorFilter && r.creator_id !== parseInt(creatorFilter)) return false
    return true
  })

  const tabs = [
    { key: 'overview', label: 'Overview', icon: ChartBarIcon },
    { key: 'org-scan', label: 'Org-Wide Scan', icon: GlobeAltIcon },
    { key: 'links', label: 'Storage Links', icon: LinkIcon },
    { key: 'results', label: 'Scan Results', icon: MagnifyingGlassIcon },
    { key: 'analyze', label: 'Analyze', icon: SparklesIcon }
  ]

  return (
    <div className="min-h-screen bg-[#F5F7F4] p-4 sm:p-6 lg:p-8">
      <div className="max-w-6xl mx-auto">
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-2">
            <CloudArrowUpIcon className="w-8 h-8 text-[#5B8A72]" />
            <h1 className="text-2xl sm:text-4xl font-bold text-[#3D4A44]">Storage Scan & Link</h1>
          </div>
          <p className="text-[#7A8580] text-lg">Connect cloud storage folders and match files to your catalog</p>
        </div>

        <div className="mb-6 border-b border-[rgba(59,77,67,0.08)] overflow-x-auto">
          <div className="flex space-x-4 sm:space-x-8 min-w-max">
            {tabs.map(tab => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`pb-3 px-1 border-b-2 font-medium transition-colors flex items-center gap-2 ${
                  activeTab === tab.key
                    ? 'border-[#5B8A72] text-[#5B8A72]'
                    : 'border-transparent text-[#7A8580] hover:text-[#3D4A44]'
                }`}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {activeTab === 'overview' && (
          <div>
            {coverageLoading ? (
              <div className="flex items-center justify-center py-16">
                <div className="flex items-center gap-3 text-[#7A8580]">
                  <ArrowPathIcon className="w-5 h-5 animate-spin" />
                  <span>Loading coverage data...</span>
                </div>
              </div>
            ) : coverage ? (
              <div className="space-y-6">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-5 text-center">
                    <div className="text-3xl font-bold text-[#3D4A44]">{coverage.total_songs}</div>
                    <div className="text-[13px] text-[#7A8580] mt-1">Total Songs</div>
                  </div>
                  <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-5 text-center">
                    <div className="text-3xl font-bold text-[#5B8A72]">{coverage.songs_with_audio}</div>
                    <div className="text-[13px] text-[#7A8580] mt-1">Audio Linked</div>
                  </div>
                  <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-5 text-center">
                    <div className="text-3xl font-bold text-[#6B4FA0]">{coverage.songs_analyzed}</div>
                    <div className="text-[13px] text-[#7A8580] mt-1">Analyzed</div>
                  </div>
                  <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-5 text-center">
                    <div className="text-3xl font-bold text-[#C47068]">{coverage.songs_unlinked}</div>
                    <div className="text-[13px] text-[#7A8580] mt-1">Unlinked</div>
                  </div>
                </div>

                <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6">
                  <h2 className="text-lg font-semibold text-[#3D4A44] mb-4">Audio Coverage</h2>
                  <div className="space-y-4">
                    <CoverageBar label="Audio Linked" value={coverage.songs_with_audio} total={coverage.total_songs} />
                    <CoverageBar label="AI Analyzed" value={coverage.songs_analyzed} total={coverage.total_songs} color="bg-[#6B4FA0]" />
                    {coverage.songs_queued > 0 && (
                      <CoverageBar label="Analysis In Progress" value={coverage.songs_queued} total={coverage.total_songs} color="bg-amber-500" />
                    )}
                    {coverage.songs_failed > 0 && (
                      <CoverageBar label="Analysis Failed" value={coverage.songs_failed} total={coverage.total_songs} color="bg-[#C47068]" />
                    )}
                  </div>
                </div>

                <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6">
                  <h2 className="text-lg font-semibold text-[#3D4A44] mb-3">Quick Actions</h2>
                  <div className="flex flex-wrap gap-3">
                    {coverage.songs_unlinked > 0 && (
                      <button
                        onClick={() => setActiveTab('org-scan')}
                        className="flex items-center gap-2 px-4 py-2.5 bg-[#5B8A72] text-white rounded-xl text-sm font-medium hover:bg-[#4A7A62] transition-colors"
                      >
                        <GlobeAltIcon className="w-4 h-4" />
                        Run Org-Wide Scan ({coverage.songs_unlinked} unlinked)
                      </button>
                    )}
                    {coverage.songs_with_audio > coverage.songs_analyzed && (
                      <button
                        onClick={handleAnalyzeAllUnanalyzed}
                        disabled={analyzeLoading}
                        className="flex items-center gap-2 px-4 py-2.5 bg-[#6B4FA0] text-white rounded-xl text-sm font-medium hover:bg-[#5A3F8A] transition-colors disabled:opacity-50"
                      >
                        {analyzeLoading ? <ArrowPathIcon className="w-4 h-4 animate-spin" /> : <SparklesIcon className="w-4 h-4" />}
                        Analyze All Unanalyzed ({coverage.songs_with_audio - coverage.songs_analyzed})
                      </button>
                    )}
                    <button
                      onClick={loadCoverage}
                      className="flex items-center gap-2 px-4 py-2.5 bg-[#EEF1EC] text-[#3D4A44] rounded-xl text-sm font-medium hover:bg-[#D8DDD6] transition-colors"
                    >
                      <ArrowPathIcon className="w-4 h-4" />
                      Refresh
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <ChartBarIcon className="w-12 h-12 text-[#7A8580] opacity-40 mb-4" />
                <p className="text-[#7A8580] text-lg">No coverage data available</p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'org-scan' && (
          <div>
            <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6 mb-6">
              <div className="flex items-center gap-3 mb-4">
                <GlobeAltIcon className="w-6 h-6 text-[#5B8A72]" />
                <h2 className="text-lg font-semibold text-[#3D4A44]">Org-Wide Dropbox Scan</h2>
              </div>
              <p className="text-[#7A8580] text-sm mb-6">
                Scan your entire Dropbox (or a specific folder) to find audio files and automatically match them
                to songs in your catalog. High-confidence matches are auto-linked and queued for AI analysis.
              </p>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Root Folder to Scan</label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={orgScanFolder}
                      onChange={(e) => setOrgScanFolder(e.target.value)}
                      placeholder="/ (entire Dropbox)"
                      className="flex-1 border border-[rgba(59,77,67,0.12)] rounded-xl px-3 py-2.5 text-sm bg-white text-[#3D4A44] focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent placeholder-[#7A8580]"
                    />
                    <button
                      type="button"
                      onClick={() => setOrgScanFolderPickerOpen(true)}
                      className="flex items-center gap-1.5 px-3 py-2.5 border border-[#5B8A72] text-[#5B8A72] rounded-xl text-sm font-medium hover:bg-[rgba(91,138,114,0.08)] transition-colors shrink-0"
                    >
                      <FolderOpenIcon className="w-4 h-4" />
                      Browse
                    </button>
                  </div>
                </div>

                <button
                  onClick={handleOrgWideScan}
                  disabled={orgScanRunning}
                  className="flex items-center gap-2 px-6 py-3 bg-[#5B8A72] text-white rounded-xl text-sm font-medium hover:bg-[#4A7A62] transition-colors disabled:opacity-50"
                >
                  {orgScanRunning ? (
                    <>
                      <ArrowPathIcon className="w-5 h-5 animate-spin" />
                      Scanning Dropbox...
                    </>
                  ) : (
                    <>
                      <MagnifyingGlassIcon className="w-5 h-5" />
                      Start Org-Wide Scan
                    </>
                  )}
                </button>
              </div>
            </div>

            {orgScanResult && (
              <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6">
                <h3 className="text-lg font-semibold text-[#3D4A44] mb-4">Scan Results</h3>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4">
                  <div className="p-3 bg-[#F5F7F4] rounded-xl text-center">
                    <div className="text-2xl font-bold text-[#3D4A44]">{orgScanResult.total_files_found}</div>
                    <div className="text-[12px] text-[#7A8580]">Audio Files Found</div>
                  </div>
                  <div className="p-3 bg-green-50 rounded-xl text-center">
                    <div className="text-2xl font-bold text-green-700">{orgScanResult.auto_linked}</div>
                    <div className="text-[12px] text-green-600">Auto-Linked</div>
                  </div>
                  <div className="p-3 bg-amber-50 rounded-xl text-center">
                    <div className="text-2xl font-bold text-amber-700">{orgScanResult.needs_review}</div>
                    <div className="text-[12px] text-amber-600">Need Review</div>
                  </div>
                  <div className="p-3 bg-gray-50 rounded-xl text-center">
                    <div className="text-2xl font-bold text-gray-600">{orgScanResult.no_match}</div>
                    <div className="text-[12px] text-gray-500">No Match</div>
                  </div>
                </div>
                {orgScanResult.already_linked > 0 && (
                  <p className="text-[13px] text-[#7A8580]">{orgScanResult.already_linked} files were already linked</p>
                )}
                {orgScanResult.analysis_queued > 0 && (
                  <p className="text-[13px] text-[#5B8A72] mt-1">{orgScanResult.analysis_queued} assets queued for AI analysis</p>
                )}
                {orgScanResult.needs_review > 0 && (
                  <button
                    onClick={() => setActiveTab('results')}
                    className="mt-4 flex items-center gap-2 px-4 py-2 bg-[#EEF1EC] text-[#3D4A44] rounded-xl text-sm font-medium hover:bg-[#D8DDD6] transition-colors"
                  >
                    <MagnifyingGlassIcon className="w-4 h-4" />
                    Review Pending Matches
                  </button>
                )}
              </div>
            )}

            {!orgScanResult && !orgScanRunning && (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <GlobeAltIcon className="w-12 h-12 text-[#7A8580] opacity-40 mb-4" />
                <p className="text-[#7A8580] text-lg">Ready to scan</p>
                <p className="text-[#7A8580] text-sm mt-1">Choose a folder and start scanning to match audio files to your catalog</p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'links' && (
          <div>
            <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
              <p className="text-sm text-[#7A8580] font-medium">{links.length} storage link{links.length !== 1 ? 's' : ''}</p>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleScanAll}
                  disabled={scanningAll || links.length === 0}
                  className="flex items-center gap-2 px-4 py-2 bg-[#EEF1EC] text-[#3D4A44] rounded-xl text-sm font-medium hover:bg-[#D8DDD6] transition-colors disabled:opacity-50"
                >
                  <ArrowPathIcon className={`w-4 h-4 ${scanningAll ? 'animate-spin' : ''}`} />
                  Scan All
                </button>
                <button
                  onClick={openAddLink}
                  className="flex items-center gap-2 px-4 py-2 bg-[#5B8A72] text-white rounded-xl text-sm font-medium hover:bg-[#4A7A62] transition-colors"
                >
                  <PlusIcon className="w-4 h-4" />
                  Add Link
                </button>
              </div>
            </div>

            {linksLoading ? (
              <div className="flex items-center justify-center py-16">
                <div className="flex items-center gap-3 text-[#7A8580]">
                  <ArrowPathIcon className="w-5 h-5 animate-spin" />
                  <span>Loading links...</span>
                </div>
              </div>
            ) : links.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <FolderIcon className="w-12 h-12 text-[#7A8580] opacity-40 mb-4" />
                <p className="text-[#7A8580] text-lg">No storage links yet</p>
                <p className="text-[#7A8580] text-sm mt-1">Connect a cloud storage folder to get started</p>
              </div>
            ) : (
              <div className="space-y-3">
                {links.map(link => {
                  const creator = creators.find(c => c.id === link.creator_id)
                  return (
                    <div key={link.id} className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-5 transition-all hover:shadow-[0px_6px_16px_rgba(0,0,0,0.12)]">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex items-start gap-3 min-w-0 flex-1">
                          <ProviderIcon provider={link.provider} className="w-6 h-6 flex-shrink-0 mt-0.5" />
                          <div className="min-w-0">
                            <h3 className="text-[16px] font-semibold text-[#3D4A44] truncate">{creator?.display_name || `Creator #${link.creator_id}`}</h3>
                            <p className="text-[14px] text-[#7A8580] truncate">{link.folder_path}</p>
                            <div className="flex flex-wrap items-center gap-3 mt-2">
                              <span className="rounded-full px-3 py-1 text-[13px] font-medium bg-[#EEF1EC] text-[#3D4A44]">
                                {PROVIDER_LABELS[link.provider] || link.provider}
                              </span>
                              {link.last_scan_file_count != null && (
                                <span className="text-[13px] text-[#7A8580]">{link.last_scan_file_count} files</span>
                              )}
                              <span className="text-[13px] text-[#7A8580]">
                                Scanned: {formatDate(link.last_scanned_at)}
                              </span>
                              {link.scan_recursive && (
                                <span className="text-[13px] text-[#7A8580]">Recursive</span>
                              )}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2 flex-shrink-0">
                          <button
                            onClick={() => handleScanSingle(link.id)}
                            disabled={scanningId === link.id}
                            className="p-2 text-[#5B8A72] hover:bg-[#EEF1EC] rounded-lg transition-colors disabled:opacity-50"
                            title="Scan"
                          >
                            <ArrowPathIcon className={`w-4 h-4 ${scanningId === link.id ? 'animate-spin' : ''}`} />
                          </button>
                          <button
                            onClick={() => openEditLink(link)}
                            className="p-2 text-[#7A8580] hover:bg-[#EEF1EC] rounded-lg transition-colors"
                            title="Edit"
                          >
                            <PencilSquareIcon className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleDeleteLink(link.id)}
                            className="p-2 text-[#C47068] hover:bg-red-50 rounded-lg transition-colors"
                            title="Delete"
                          >
                            <TrashIcon className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )}

        {activeTab === 'results' && (
          <div>
            <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
              <div className="flex items-center gap-3 flex-wrap">
                <select
                  value={selectedBatch}
                  onChange={(e) => setSelectedBatch(e.target.value)}
                  className="border border-[rgba(59,77,67,0.12)] rounded-xl px-3 py-2 text-sm bg-white text-[#3D4A44] focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                >
                  <option value="">All Batches</option>
                  {batches.map(b => (
                    <option key={b.scan_batch_id} value={b.scan_batch_id}>{formatDate(b.created_at)} — {b.total || 0} files</option>
                  ))}
                </select>
                <select
                  value={confidenceFilter}
                  onChange={(e) => setConfidenceFilter(e.target.value)}
                  className="border border-[rgba(59,77,67,0.12)] rounded-xl px-3 py-2 text-sm bg-white text-[#3D4A44] focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                >
                  <option value="">All Confidence</option>
                  <option value="HIGH">High</option>
                  <option value="MEDIUM">Medium</option>
                  <option value="LOW">Low</option>
                  <option value="NONE">None</option>
                </select>
                <select
                  value={creatorFilter}
                  onChange={(e) => setCreatorFilter(e.target.value)}
                  className="border border-[rgba(59,77,67,0.12)] rounded-xl px-3 py-2 text-sm bg-white text-[#3D4A44] focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                >
                  <option value="">All Creators</option>
                  {creators.map(c => (
                    <option key={c.id} value={c.id}>{c.display_name}</option>
                  ))}
                </select>
              </div>
              <button
                onClick={handleBulkApprove}
                disabled={bulkApproving}
                className="flex items-center gap-2 px-4 py-2 bg-[#5B8A72] text-white rounded-xl text-sm font-medium hover:bg-[#4A7A62] transition-colors disabled:opacity-50"
              >
                {bulkApproving ? <ArrowPathIcon className="w-4 h-4 animate-spin" /> : <CheckCircleIcon className="w-4 h-4" />}
                Approve All High Confidence
              </button>
            </div>

            {resultsLoading ? (
              <div className="flex items-center justify-center py-16">
                <div className="flex items-center gap-3 text-[#7A8580]">
                  <ArrowPathIcon className="w-5 h-5 animate-spin" />
                  <span>Loading results...</span>
                </div>
              </div>
            ) : filteredResults.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <MagnifyingGlassIcon className="w-12 h-12 text-[#7A8580] opacity-40 mb-4" />
                <p className="text-[#7A8580] text-lg">No scan results to review</p>
                <p className="text-[#7A8580] text-sm mt-1">Run a scan from the Org-Wide Scan or Storage Links tab</p>
              </div>
            ) : (
              <div className="space-y-3">
                <p className="text-sm text-[#7A8580] font-medium">{filteredResults.length} result{filteredResults.length !== 1 ? 's' : ''} to review</p>
                {filteredResults.map(result => (
                  <div key={result.id} className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-5 transition-all hover:shadow-[0px_6px_16px_rgba(0,0,0,0.12)]">
                    <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="text-[16px] font-semibold text-[#3D4A44] truncate">{result.file_name}</h3>
                          {result.match_confidence && (
                            <span className={`rounded-full px-2.5 py-0.5 text-[12px] font-bold ${CONFIDENCE_COLORS[result.match_confidence] || CONFIDENCE_COLORS.NONE}`}>
                              {result.match_confidence}
                            </span>
                          )}
                        </div>
                        <p className="text-[13px] text-[#7A8580] truncate">{result.file_path}</p>
                        <p className="text-[13px] text-[#7A8580]">{formatFileSize(result.file_size)}</p>

                        {(result.matched_song_title || result.suggested_title) && (
                          <div className="mt-3 p-3 bg-[#F5F7F4] rounded-xl">
                            <p className="text-[13px] font-medium text-[#3D4A44]">
                              Suggested: {result.matched_song_title || result.suggested_title}
                              {(result.matched_song_artist || result.suggested_artist) && (
                                <span className="text-[#7A8580]"> — {result.matched_song_artist || result.suggested_artist}</span>
                              )}
                            </p>
                            {result.match_score != null && (
                              <div className="flex items-center gap-2 mt-1">
                                <div className="flex-1 h-1.5 bg-[#E0E5DE] rounded-full overflow-hidden">
                                  <div
                                    className="h-full bg-[#5B8A72] rounded-full transition-all"
                                    style={{ width: `${Math.min(result.match_score * 100, 100)}%` }}
                                  />
                                </div>
                                <span className="text-[12px] font-bold text-[#3D4A44]">{Math.round(result.match_score * 100)}%</span>
                              </div>
                            )}
                          </div>
                        )}
                      </div>

                      <div className="flex items-center gap-2 flex-shrink-0">
                        <button
                          onClick={() => handleApprove(result.id, result.matched_song_id)}
                          disabled={!result.matched_song_id}
                          className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-white bg-[#5B8A72] rounded-lg hover:bg-[#4A7A62] transition-colors disabled:opacity-50"
                        >
                          <CheckCircleIcon className="w-4 h-4" />
                          Approve
                        </button>
                        <button
                          onClick={() => handleReject(result.id)}
                          className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-[#C47068] bg-red-50 rounded-lg hover:bg-red-100 transition-colors"
                        >
                          <XCircleIcon className="w-4 h-4" />
                          Reject
                        </button>
                        <button
                          onClick={() => { setShowReassignModal(result); setSongSearch(''); setSongSearchResults([]) }}
                          className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-[#3D4A44] bg-[#EEF1EC] rounded-lg hover:bg-[#D8DDD6] transition-colors"
                        >
                          <MagnifyingGlassIcon className="w-4 h-4" />
                          Reassign
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'analyze' && (
          <div>
            <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6 mb-6">
              <div className="flex items-center gap-3 mb-4">
                <SparklesIcon className="w-6 h-6 text-[#5B8A72]" />
                <h2 className="text-lg font-semibold text-[#3D4A44]">AI Audio Analysis</h2>
              </div>
              <p className="text-[#7A8580] text-sm mb-6">
                Analyze linked audio files with AI to extract BPM, key, mood, and other metadata for your catalog.
              </p>

              <div className="flex flex-wrap items-center gap-3 mb-6">
                <button
                  onClick={handleAnalyzeAllUnanalyzed}
                  disabled={analyzeLoading}
                  className="flex items-center gap-2 px-5 py-2.5 bg-[#5B8A72] text-white rounded-xl text-sm font-medium hover:bg-[#4A7A62] transition-colors disabled:opacity-50"
                >
                  {analyzeLoading ? (
                    <>
                      <ArrowPathIcon className="w-4 h-4 animate-spin" />
                      Analyzing...
                    </>
                  ) : (
                    <>
                      <SparklesIcon className="w-4 h-4" />
                      Analyze All Unanalyzed
                    </>
                  )}
                </button>

                <div className="flex items-center gap-2 border-l border-[rgba(59,77,67,0.12)] pl-3">
                  <select
                    value={selectedBatch}
                    onChange={(e) => setSelectedBatch(e.target.value)}
                    className="border border-[rgba(59,77,67,0.12)] rounded-xl px-3 py-2 text-sm bg-white text-[#3D4A44] focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                  >
                    <option value="">Select Batch</option>
                    {batches.map(b => (
                      <option key={b.scan_batch_id} value={b.scan_batch_id}>{formatDate(b.created_at)} — {b.total || 0} files</option>
                    ))}
                  </select>
                  <button
                    onClick={handleAnalyzeLinked}
                    disabled={analyzeLoading || !selectedBatch}
                    className="flex items-center gap-2 px-4 py-2.5 bg-[#EEF1EC] text-[#3D4A44] rounded-xl text-sm font-medium hover:bg-[#D8DDD6] transition-colors disabled:opacity-50"
                  >
                    <SparklesIcon className="w-4 h-4" />
                    Analyze Batch
                  </button>
                </div>
              </div>

              {analyzeStatus && (
                <div className="p-4 bg-[#F5F7F4] rounded-xl">
                  <h3 className="text-sm font-semibold text-[#3D4A44] mb-2">Analysis Status</h3>
                  {analyzeStatus.message && <p className="text-sm text-[#7A8580]">{analyzeStatus.message}</p>}
                  {analyzeStatus.queued != null && (
                    <p className="text-sm text-[#5B8A72]">{analyzeStatus.queued} assets queued for analysis</p>
                  )}
                  {analyzeStatus.total != null && (
                    <div className="mt-2">
                      <div className="flex justify-between text-[13px] text-[#7A8580] mb-1">
                        <span>{analyzeStatus.completed || 0} of {analyzeStatus.total} completed</span>
                        <span>{analyzeStatus.total > 0 ? Math.round(((analyzeStatus.completed || 0) / analyzeStatus.total) * 100) : 0}%</span>
                      </div>
                      <div className="h-2 bg-[#E0E5DE] rounded-full overflow-hidden">
                        <div
                          className="h-full bg-[#5B8A72] rounded-full transition-all"
                          style={{ width: `${analyzeStatus.total > 0 ? ((analyzeStatus.completed || 0) / analyzeStatus.total) * 100 : 0}%` }}
                        />
                      </div>
                    </div>
                  )}
                  {analyzeStatus.failed > 0 && (
                    <p className="text-sm text-[#C47068] mt-2">{analyzeStatus.failed} failed</p>
                  )}
                </div>
              )}
            </div>

            {!analyzeStatus && (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <SparklesIcon className="w-12 h-12 text-[#7A8580] opacity-40 mb-4" />
                <p className="text-[#7A8580] text-lg">Ready to analyze</p>
                <p className="text-[#7A8580] text-sm mt-1">Click "Analyze All Unanalyzed" to process all linked audio</p>
              </div>
            )}
          </div>
        )}
      </div>

      {showLinkModal && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={() => setShowLinkModal(false)}>
          <div className="bg-white rounded-[20px] shadow-xl w-full max-w-md p-6" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-bold text-[#3D4A44]">{editingLink ? 'Edit Link' : 'Add Storage Link'}</h2>
              <button onClick={() => setShowLinkModal(false)} className="p-1 hover:bg-[#EEF1EC] rounded-lg transition-colors">
                <XMarkIcon className="w-5 h-5 text-[#7A8580]" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Creator</label>
                <select
                  value={linkForm.creator_id}
                  onChange={(e) => setLinkForm(prev => ({ ...prev, creator_id: e.target.value }))}
                  className="w-full border border-[rgba(59,77,67,0.12)] rounded-xl px-3 py-2.5 text-sm bg-white text-[#3D4A44] focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                >
                  <option value="">Select creator...</option>
                  {creators.map(c => (
                    <option key={c.id} value={c.id}>{c.display_name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Provider</label>
                <div className="flex rounded-xl border border-[rgba(59,77,67,0.12)] overflow-hidden">
                  {Object.entries(PROVIDER_LABELS).map(([key, label]) => (
                    <button
                      key={key}
                      onClick={() => setLinkForm(prev => ({ ...prev, provider: key }))}
                      className={`flex-1 px-4 py-2.5 text-sm font-medium transition-colors flex items-center justify-center gap-2 ${
                        linkForm.provider === key
                          ? 'bg-[#5B8A72] text-white'
                          : 'bg-white text-[#7A8580] hover:bg-[#EEF1EC]'
                      }`}
                    >
                      <ProviderIcon provider={key} className="w-4 h-4" />
                      {label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Folder Path</label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={linkForm.folder_path}
                    onChange={(e) => setLinkForm(prev => ({ ...prev, folder_path: e.target.value }))}
                    placeholder="/Music/Artist Name"
                    className="flex-1 border border-[rgba(59,77,67,0.12)] rounded-xl px-3 py-2.5 text-sm bg-white text-[#3D4A44] focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent placeholder-[#7A8580]"
                  />
                  <button
                    type="button"
                    onClick={() => setFolderPickerOpen(true)}
                    disabled={!providers.some(p => p.provider === linkForm.provider)}
                    className="flex items-center gap-1.5 px-3 py-2.5 border border-[#5B8A72] text-[#5B8A72] rounded-xl text-sm font-medium hover:bg-[rgba(91,138,114,0.08)] transition-colors disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
                    title={providers.some(p => p.provider === linkForm.provider) ? 'Browse folders' : `Connect ${PROVIDER_LABELS[linkForm.provider]} first`}
                  >
                    <FolderOpenIcon className="w-4 h-4" />
                    Browse
                  </button>
                </div>
                {!providers.some(p => p.provider === linkForm.provider) && (
                  <p className="text-[12px] text-amber-600 mt-1">Connect {PROVIDER_LABELS[linkForm.provider]} in Settings first to browse folders</p>
                )}
              </div>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={linkForm.scan_recursive}
                  onChange={(e) => setLinkForm(prev => ({ ...prev, scan_recursive: e.target.checked }))}
                  className="w-4 h-4 rounded border-[rgba(59,77,67,0.2)] text-[#5B8A72] focus:ring-[#5B8A72]"
                />
                <span className="text-sm text-[#3D4A44]">Scan subfolders recursively</span>
              </label>
            </div>

            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowLinkModal(false)}
                className="px-4 py-2 text-sm font-medium text-[#7A8580] hover:text-[#3D4A44] transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveLink}
                disabled={linkSaving || !linkForm.creator_id || !linkForm.folder_path}
                className="flex items-center gap-2 px-5 py-2 bg-[#5B8A72] text-white rounded-xl text-sm font-medium hover:bg-[#4A7A62] transition-colors disabled:opacity-50"
              >
                {linkSaving && <ArrowPathIcon className="w-4 h-4 animate-spin" />}
                {editingLink ? 'Update' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}

      <FolderPicker
        isOpen={folderPickerOpen}
        onClose={() => setFolderPickerOpen(false)}
        onSelect={(path, displayPath) => {
          setLinkForm(prev => ({ ...prev, folder_path: displayPath || path }))
        }}
        provider={linkForm.provider}
        orgId={orgId}
        initialPath={linkForm.folder_path}
      />

      <FolderPicker
        isOpen={orgScanFolderPickerOpen}
        onClose={() => setOrgScanFolderPickerOpen(false)}
        onSelect={(path) => {
          setOrgScanFolder(path)
        }}
        provider="DROPBOX"
        orgId={orgId}
        initialPath={orgScanFolder}
      />

      {showReassignModal && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={() => setShowReassignModal(null)}>
          <div className="bg-white rounded-[20px] shadow-xl w-full max-w-md p-6" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-[#3D4A44]">Reassign to Song</h2>
              <button onClick={() => setShowReassignModal(null)} className="p-1 hover:bg-[#EEF1EC] rounded-lg transition-colors">
                <XMarkIcon className="w-5 h-5 text-[#7A8580]" />
              </button>
            </div>
            <p className="text-sm text-[#7A8580] mb-3">Reassigning: {showReassignModal.file_name}</p>

            <input
              type="text"
              value={songSearch}
              onChange={(e) => handleSongSearch(e.target.value)}
              placeholder="Search songs..."
              className="w-full border border-[rgba(59,77,67,0.12)] rounded-xl px-3 py-2.5 text-sm bg-white text-[#3D4A44] focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent placeholder-[#7A8580] mb-3"
            />

            <div className="max-h-60 overflow-y-auto space-y-1">
              {songSearchLoading && <p className="text-sm text-[#7A8580] p-2">Searching...</p>}
              {songSearchResults.map(song => (
                <button
                  key={song.id}
                  onClick={() => handleReassign(showReassignModal.id, song.id)}
                  className="w-full text-left p-3 rounded-xl hover:bg-[#EEF1EC] transition-colors"
                >
                  <p className="text-sm font-medium text-[#3D4A44]">{song.title}</p>
                  <p className="text-[13px] text-[#7A8580]">{song.primary_artist}</p>
                </button>
              ))}
              {!songSearchLoading && songSearch.length >= 2 && songSearchResults.length === 0 && (
                <p className="text-sm text-[#7A8580] p-2">No songs found</p>
              )}
            </div>
          </div>
        </div>
      )}

      {toast && (
        <div className={`fixed bottom-6 right-6 z-50 px-5 py-3 rounded-xl shadow-lg text-sm font-medium transition-all ${
          toast.type === 'error' ? 'bg-red-600 text-white' : 'bg-[#3D4A44] text-white'
        }`}>
          {toast.message}
        </div>
      )}
    </div>
  )
}
