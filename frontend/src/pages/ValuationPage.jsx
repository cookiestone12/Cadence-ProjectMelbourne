import React, { useState, useEffect, useMemo, useRef } from 'react'
import axios from 'axios'
import ExportButton from '../components/ExportButton'
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, AreaChart, Area } from 'recharts'
import {
  CurrencyDollarIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  MusicalNoteIcon,
  ArrowDownTrayIcon,
  XMarkIcon,
  ChartBarIcon,
  PlayIcon,
  ClockIcon,
  AdjustmentsHorizontalIcon,
  SparklesIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  InformationCircleIcon,
  TableCellsIcon,
  ChartPieIcon,
} from '@heroicons/react/24/outline'

export default function ValuationPage() {
  const [loading, setLoading] = useState(true)
  const [catalogData, setCatalogData] = useState(null)
  const [uwData, setUwData] = useState(null)
  const [uwLoading, setUwLoading] = useState(false)
  const [runs, setRuns] = useState([])
  const [activeTab, setActiveTab] = useState('overview')
  const [runModalOpen, setRunModalOpen] = useState(false)
  const [runConfig, setRunConfig] = useState({
    periodization_mode: 'activity',
    granularity: 'half',
    include_sync: true,
    use_gross: false,
    exclude_right_types: [],
    exclude_flags: [],
  })
  const [running, setRunning] = useState(false)
  const [selectedSong, setSelectedSong] = useState(null)
  const [songDetail, setSongDetail] = useState(null)
  const [loadingDetail, setLoadingDetail] = useState(false)

  // Per-creator scope (Task #105)
  const [creators, setCreators] = useState([])
  const [scopeCreatorId, setScopeCreatorId] = useState(() => {
    try {
      const params = new URLSearchParams(window.location.search)
      const v = params.get('creatorId')
      return v ? parseInt(v, 10) : null
    } catch { return null }
  })

  // Source-typed valuation (Task #162)
  const [sourceTyped, setSourceTyped] = useState(null)
  const [sourceTypedRunning, setSourceTypedRunning] = useState(false)

  // Phase 5 — Blended valuation (Task #172)
  const [fullVal, setFullVal] = useState(null)
  const [fullValRunning, setFullValRunning] = useState(false)
  const [methodology, setMethodology] = useState('blended') // income | market_comparable | dcf | blended
  const [trend, setTrend] = useState([])
  const [pdfDownloading, setPdfDownloading] = useState(false)
  // Org id is needed for the spec'd Phase 5 routes mounted under
  // /api/v1/organizations/{org_id}/valuation/{catalog,report/pdf}.
  const [orgId, setOrgId] = useState(null)

  // Load creator list once. Org id comes from /current.
  useEffect(() => {
    let alive = true
    ;(async () => {
      try {
        const orgRes = await axios.get('/api/organizations/current')
        if (!alive) return
        const orgId = orgRes.data?.id
        if (!orgId) return
        setOrgId(orgId)
        // /api/creators/{creator_id} is the single-creator detail route — what
        // we want here is the org-roster endpoint that the Roster page uses.
        // The previous URL silently 404'd (or returned a single-object
        // payload), so the Scope dropdown was always empty no matter how
        // many creators the org had.
        const creatorsRes = await axios.get(`/api/creators/org/${orgId}`)
        if (!alive) return
        const list = Array.isArray(creatorsRes.data) ? creatorsRes.data : []
        list.sort((a, b) => (a.display_name || a.name || '').localeCompare(b.display_name || b.name || ''))
        setCreators(list)
      } catch (e) {
        if (alive) console.error('Failed to load creators for scope dropdown:', e)
      }
    })()
    return () => { alive = false }
  }, [])

  // When the user clicks a row in Run History we need to set the scope
  // *and* show the historical run's payload, but the scope-change effect
  // would race against that and overwrite uwData with whatever
  // /underwriting/latest returns. Setting this ref to true tells the
  // scope effect to skip its loadAll for exactly one tick.
  const skipNextLoadRef = useRef(false)

  useEffect(() => {
    if (skipNextLoadRef.current) {
      skipNextLoadRef.current = false
      return
    }
    loadAll(scopeCreatorId)
  }, [scopeCreatorId])

  // Keep URL in sync so the page is shareable / refresh-safe.
  useEffect(() => {
    try {
      const url = new URL(window.location.href)
      if (scopeCreatorId) url.searchParams.set('creatorId', String(scopeCreatorId))
      else url.searchParams.delete('creatorId')
      window.history.replaceState({}, '', url.toString())
    } catch {}
  }, [scopeCreatorId])

  const loadAll = async (creatorId = null) => {
    setLoading(true)
    try {
      const scopeQs = creatorId ? `?scope_creator_id=${creatorId}` : ''
      const latestUrl = `/api/valuation/underwriting/latest${scopeQs}`
      const catalogUrl = `/api/valuation/catalog/summary${scopeQs}`
      const sourceTypedUrl = `/api/valuation/source-typed/summary${scopeQs}`
      const fullSummaryUrl = `/api/valuation/full/summary${scopeQs}${scopeQs ? '&' : '?'}method=blended`
      const trendUrl = `/api/valuation/full/trend${scopeQs}${scopeQs ? '&' : '?'}months=12`
      const [catRes, uwRes, runsRes, stRes, fvRes, trRes] = await Promise.allSettled([
        axios.get(catalogUrl),
        axios.get(latestUrl),
        axios.get('/api/valuation/underwriting/runs'),
        axios.get(sourceTypedUrl),
        axios.get(fullSummaryUrl),
        axios.get(trendUrl),
      ])
      if (catRes.status === 'fulfilled') setCatalogData(catRes.value.data)
      const latestData = uwRes.status === 'fulfilled' ? uwRes.value.data : null
      if (latestData?.has_data) setUwData(latestData)
      else setUwData(null)
      if (runsRes.status === 'fulfilled') setRuns(runsRes.value.data)
      if (stRes.status === 'fulfilled') setSourceTyped(stRes.value.data)
      else setSourceTyped(null)
      if (fvRes.status === 'fulfilled') setFullVal(fvRes.value.data)
      else setFullVal(null)
      if (trRes.status === 'fulfilled') setTrend(trRes.value.data?.trend || [])
      else setTrend([])

      // Switching scope to a creator must re-fire underwriting for that
      // creator (per-creator scope is meaningless if it just shows a stale
      // prior run). Org-wide loads do NOT auto-fire — the explicit "Run"
      // button stays the gesture there to avoid surprise cost on first
      // page mount.
      if (creatorId && !running) {
        try {
          setRunning(true)
          await axios.post('/api/valuation/underwriting/run', {
            ...runConfig,
            scope_creator_id: creatorId,
          })
          const [uwRes2, runsRes2] = await Promise.allSettled([
            axios.get(latestUrl),
            axios.get('/api/valuation/underwriting/runs'),
          ])
          if (uwRes2.status === 'fulfilled' && uwRes2.value.data?.has_data) {
            setUwData(uwRes2.value.data)
          }
          if (runsRes2.status === 'fulfilled') setRuns(runsRes2.value.data)
        } catch (e) {
          // Don't crash the page; the user can still hit "Run" manually.
          console.warn('Auto-run for scoped creator failed:', e?.response?.data || e?.message)
        } finally {
          setRunning(false)
        }
      }
    } catch (e) {
      console.error('Error loading data:', e)
    } finally {
      setLoading(false)
    }
  }

  const triggerSourceTypedRun = async () => {
    setSourceTypedRunning(true)
    try {
      const res = await axios.post('/api/valuation/source-typed/run', {
        scope_creator_id: scopeCreatorId || null,
      })
      setSourceTyped(res.data)
    } catch (e) {
      console.error('Source-typed valuation run failed:', e)
      alert('Source-typed valuation failed. Check that you have matched royalty statement lines for this scope.')
    } finally {
      setSourceTypedRunning(false)
    }
  }

  const triggerFullValRun = async () => {
    setFullValRunning(true)
    try {
      const res = await axios.post('/api/valuation/full/run', {
        scope_creator_id: scopeCreatorId || null,
      })
      setFullVal(res.data)
      // Trend extends with this fresh row — refetch.
      try {
        const scopeQs = scopeCreatorId ? `?scope_creator_id=${scopeCreatorId}` : ''
        const trRes = await axios.get(`/api/valuation/full/trend${scopeQs}${scopeQs ? '&' : '?'}months=12`)
        setTrend(trRes.data?.trend || [])
      } catch {}
    } catch (e) {
      console.error('Full valuation run failed:', e)
      alert('Full valuation failed. Make sure you have at least some matched royalty statements or streaming metrics.')
    } finally {
      setFullValRunning(false)
    }
  }

  const handleDownloadPdf = async () => {
    setPdfDownloading(true)
    try {
      // Prefer the spec'd Phase 5 contract route mounted under
      // /api/v1/organizations/{org_id}/valuation/report/pdf when the
      // org id is loaded; fall back to the legacy /api/valuation/report
      // route on first paint (before /current resolves) so the button
      // never deadlocks on the org fetch.
      const pdfUrl = orgId
        ? `/api/v1/organizations/${orgId}/valuation/report/pdf${scopeCreatorId ? `?creator_id=${scopeCreatorId}` : ''}`
        : `/api/valuation/report/pdf${scopeCreatorId ? `?scope_creator_id=${scopeCreatorId}` : ''}`
      const res = await axios.get(pdfUrl, { responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
      const link = document.createElement('a')
      link.href = url
      const today = new Date().toISOString().split('T')[0]
      const scopeLabel = scopeCreatorName ? scopeCreatorName.replace(/\s+/g, '_').toLowerCase() : 'catalog'
      link.setAttribute('download', `cadence_valuation_${scopeLabel}_${today}.pdf`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (e) {
      console.error('PDF download failed:', e)
      alert('Could not generate PDF. Run a Full Valuation first.')
    } finally {
      setPdfDownloading(false)
    }
  }

  const triggerRun = async () => {
    setRunning(true)
    try {
      await axios.post('/api/valuation/underwriting/run', {
        ...runConfig,
        scope_creator_id: scopeCreatorId || null,
      })
      setRunModalOpen(false)
      await loadAll(scopeCreatorId)
    } catch (e) {
      console.error('Underwriting run failed:', e)
      alert('Underwriting run failed. Check that you have processed royalty statements with matched assets.')
    } finally {
      setRunning(false)
    }
  }

  const scopeCreatorName = useMemo(() => {
    if (!scopeCreatorId) return null
    const c = creators.find(x => x.id === scopeCreatorId)
    return c?.display_name || c?.name || `Creator #${scopeCreatorId}`
  }, [scopeCreatorId, creators])

  const loadSongDetail = async (songId) => {
    setLoadingDetail(true)
    try {
      const res = await axios.get(`/api/valuation/song/${songId}/detail`)
      setSongDetail(res.data)
    } catch (e) {
      console.error('Error loading song detail:', e)
    } finally {
      setLoadingDetail(false)
    }
  }

  const handleDownloadReport = async () => {
    try {
      const res = await axios.get('/api/valuation/catalog/download/excel', { responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `cadence_catalog_report_${new Date().toISOString().split('T')[0]}.xlsx`)
      document.body.appendChild(link)
      link.click()
      link.remove()
    } catch (e) {
      console.error('Error downloading report:', e)
    }
  }

  const fmt = (v) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(v || 0)
  const fmtDec = (v) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(v || 0)
  const fmtPct = (v) => `${((v || 0) * 100).toFixed(1)}%`
  const fmtNum = (v) => (v || 0).toLocaleString()

  const ps = uwData?.portfolio_summary || {}
  const val = uwData?.valuation || {}
  const decay = uwData?.decay || {}
  const conc = uwData?.concentration || {}
  const spine = uwData?.spine?.entries || []
  const projections = uwData?.projections || {}
  const exceptions = uwData?.exceptions || []

  const periods = useMemo(() => ps.periods || [], [ps.periods])

  const concentrationChartData = useMemo(() => {
    if (!conc || !periods.length) return []
    return periods.map(p => ({
      period: p,
      'Top 1': (conc[p]?.top_1 || 0) * 100,
      'Top 3': (conc[p]?.top_3 || 0) * 100,
      'Top 5': (conc[p]?.top_5 || 0) * 100,
      'HHI': (conc[p]?.hhi || 0) * 100,
    }))
  }, [conc, periods])

  const projectionChartData = useMemo(() => {
    if (!projections.base) return []
    return (projections.base || []).map((b, i) => ({
      year: `Y${b.year}`,
      Downside: projections.downside?.[i]?.projected_net || 0,
      Base: b.projected_net,
      Upside: projections.upside?.[i]?.projected_net || 0,
    }))
  }, [projections])

  const halfLifeChartData = useMemo(() => {
    if (!decay.half_life_distribution) return []
    return Object.entries(decay.half_life_distribution).map(([bin, count]) => ({
      bin,
      count,
    }))
  }, [decay])

  const spineByPeriod = useMemo(() => {
    const songMap = {}
    spine.forEach(e => {
      const key = e.song_id || `w${e.work_id}`
      if (!songMap[key]) songMap[key] = { song_id: e.song_id, title: e.song_title || `Song ${e.song_id}`, isrc: e.isrc, periods: {}, total: 0 }
      songMap[key].periods[e.period] = e.total_net
      songMap[key].total += e.total_net
    })
    return Object.values(songMap).sort((a, b) => b.total - a.total).slice(0, 25)
  }, [spine])

  if (loading) {
    return (
      <div className="p-4 sm:p-8">
        <div className="animate-pulse">
          <div className="h-8 bg-[#EEF1EC] rounded w-1/4 mb-4"></div>
          <div className="h-4 bg-[#EEF1EC] rounded w-1/3 mb-8"></div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            {[1, 2, 3, 4].map(i => <div key={i} className="h-28 bg-[#EEF1EC] rounded-xl"></div>)}
          </div>
        </div>
      </div>
    )
  }

  const hasUW = !!uwData

  return (
    <div className="p-4 sm:p-8">
      <div className="mb-6 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center space-x-3">
            <h1 className="text-2xl sm:text-3xl font-bold text-[#3D4A44]">Catalog Valuation</h1>
            <span className="px-1.5 py-0.5 text-[9px] font-semibold tracking-wide uppercase bg-[#5B8A72]/10 text-[#5B8A72] rounded-md">Beta</span>
          </div>
          <p className="text-[#7A8580] text-sm mt-1">
            {catalogData?.organization_name || 'Your Organization'}
            {scopeCreatorName && (
              <> · <span className="text-[#5B8A72] font-medium">Scoped to {scopeCreatorName}</span></>
            )}
          </p>
        </div>
        <div className="w-full lg:w-auto flex flex-wrap items-center gap-2 sm:gap-3">
          <div className="flex items-center gap-2 w-full sm:w-auto">
            <label className="text-xs font-medium text-[#7A8580] hidden sm:inline">Scope:</label>
            <select
              value={scopeCreatorId || ''}
              onChange={e => setScopeCreatorId(e.target.value ? parseInt(e.target.value, 10) : null)}
              className="flex-1 sm:flex-none border border-[rgba(59,77,67,0.15)] bg-white text-[#3D4A44] rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent sm:min-w-[180px]"
              title="Limit valuation to a single client's catalog"
            >
              <option value="">All clients (org-wide)</option>
              {creators.map(c => (
                <option key={c.id} value={c.id}>{c.display_name || c.name || `Creator #${c.id}`}</option>
              ))}
            </select>
          </div>
          <button
            onClick={triggerFullValRun}
            disabled={fullValRunning}
            className="flex items-center space-x-2 px-4 py-2.5 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] transition-all text-sm font-medium shadow-sm disabled:opacity-60"
            title="Run the blended (Income + Market-Comparable + DCF) valuation engine"
          >
            {fullValRunning ? <ArrowPathIcon className="w-4 h-4 animate-spin" /> : <SparklesIcon className="w-4 h-4" />}
            <span>{fullValRunning ? 'Running…' : 'Run Full Valuation'}</span>
          </button>
          <button
            onClick={triggerSourceTypedRun}
            disabled={sourceTypedRunning}
            className="flex items-center space-x-2 px-4 py-2.5 border border-[#5B8A72] text-[#5B8A72] rounded-lg hover:bg-[#5B8A72]/5 transition-all text-sm font-medium disabled:opacity-60"
            title="Income engine only — bucket matched royalty statements by source type"
          >
            {sourceTypedRunning ? <ArrowPathIcon className="w-4 h-4 animate-spin" /> : <ChartPieIcon className="w-4 h-4" />}
            <span>{sourceTypedRunning ? 'Running…' : 'Income Only'}</span>
          </button>
          <button onClick={() => setRunModalOpen(true)} className="flex items-center space-x-2 px-4 py-2.5 border border-[rgba(59,77,67,0.15)] text-[#3D4A44] rounded-lg hover:bg-[#EEF1EC] transition-all text-sm font-medium">
            <SparklesIcon className="w-4 h-4" />
            <span>Underwriting</span>
          </button>
          {orgId && fullVal && (fullVal?.song_count || 0) > 0 ? (
            <ExportButton
              baseUrl={
                scopeCreatorId
                  ? `/api/v1/organizations/${orgId}/valuation/report/pdf?creator_id=${scopeCreatorId}`
                  : `/api/v1/organizations/${orgId}/valuation/report/pdf`
              }
              filename={`cadence_valuation_${scopeCreatorId ? `creator_${scopeCreatorId}` : 'catalog'}_${new Date().toISOString().slice(0, 10)}`}
              formats={['pdf', 'xlsx']}
              formatStrategy={(fmt) =>
                fmt === 'pdf'
                  ? (scopeCreatorId
                      ? `/api/v1/organizations/${orgId}/valuation/report/pdf?creator_id=${scopeCreatorId}`
                      : `/api/v1/organizations/${orgId}/valuation/report/pdf`)
                  : '/api/valuation/catalog/download/excel'
              }
              variant="secondary"
              label="Export"
            />
          ) : (
            <button
              disabled
              className="flex items-center space-x-2 px-4 py-2.5 border border-[rgba(59,77,67,0.15)] text-[#3D4A44] rounded-lg opacity-50 text-sm"
              title="Run Full Valuation first to enable export"
            >
              <ArrowDownTrayIcon className="w-4 h-4" />
              <span>Export</span>
            </button>
          )}
        </div>
      </div>

      {fullVal && (fullVal.song_count || 0) > 0 && (() => {
        const methods = [
          { key: 'income', label: 'Income' },
          { key: 'market_comparable', label: 'Market Comparable' },
          { key: 'dcf', label: 'DCF' },
          { key: 'blended', label: 'Blended (40/30/30)' },
        ]
        const bm = fullVal.by_methodology || {}
        const sel = bm[methodology] || bm.blended || { low: 0, base: 0, high: 0 }
        const dq = fullVal.data_quality || {}
        const confColor = dq.confidence_label === 'high' ? 'bg-[#5B9A6E]/15 text-[#3F7A52]' : dq.confidence_label === 'medium' ? 'bg-amber-100 text-amber-700' : 'bg-rose-100 text-rose-700'
        const confDot = dq.confidence_label === 'high' ? 'bg-[#5B9A6E]' : dq.confidence_label === 'medium' ? 'bg-amber-500' : 'bg-rose-500'
        const perCreator = fullVal.per_creator_share || []
        const isOrgScope = !scopeCreatorId
        return (
          <>
            {/* Methodology toggle */}
            <div className="mb-4 flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold text-[#7A8580] uppercase tracking-wide mr-1">Methodology:</span>
              {methods.map(m => (
                <button
                  key={m.key}
                  onClick={() => setMethodology(m.key)}
                  className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-all ${methodology === m.key ? 'bg-[#5B8A72] text-white shadow-sm' : 'bg-white border border-[rgba(59,77,67,0.15)] text-[#5C6660] hover:bg-[#EEF1EC]'}`}
                >
                  {m.label}
                </button>
              ))}
            </div>

            {/* Blended hero card + methodology breakdown */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
              <div className="lg:col-span-2 bg-gradient-to-br from-[#5B8A72] to-[#4A7A62] rounded-2xl p-6 text-white shadow-md">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="text-xs font-medium uppercase tracking-wide text-white/80">{methods.find(m => m.key === methodology)?.label} Catalog Value</div>
                    <div className="text-4xl font-bold mt-2">{fmt(sel.base)}</div>
                    <div className="text-sm text-white/80 mt-1">Range: {fmt(sel.low)} – {fmt(sel.high)}</div>
                  </div>
                  <div className={`px-2 py-1 rounded-full text-[10px] font-semibold uppercase tracking-wide flex items-center gap-1.5 bg-white/15 text-white`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${confDot}`}></span>
                    {dq.confidence_label || 'low'} confidence
                  </div>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mt-5 pt-4 border-t border-white/15">
                  <div>
                    <div className="text-[10px] text-white/70 uppercase tracking-wide">Annual Revenue</div>
                    <div className="text-base font-semibold mt-0.5">{fmt((fullVal.annual_revenue_cents || 0) / 100)}</div>
                  </div>
                  <div>
                    <div className="text-[10px] text-white/70 uppercase tracking-wide">Songs (with data)</div>
                    <div className="text-base font-semibold mt-0.5">{dq.songs_with_statements || 0} / {dq.song_count || 0}</div>
                  </div>
                  <div>
                    <div className="text-[10px] text-white/70 uppercase tracking-wide">Computed</div>
                    <div className="text-base font-semibold mt-0.5">{fullVal.computed_at ? new Date(fullVal.computed_at).toLocaleDateString() : '—'}</div>
                  </div>
                </div>
              </div>

              <div className="bg-white border border-[rgba(59,77,67,0.10)] rounded-2xl p-5">
                <div className="text-xs font-semibold text-[#7A8580] uppercase tracking-wide mb-3">Methodology Breakdown</div>
                <div className="space-y-2.5">
                  {methods.map(m => {
                    const v = bm[m.key] || { base: 0 }
                    const isSel = m.key === methodology
                    return (
                      <div key={m.key} className={`flex items-center justify-between px-3 py-2 rounded-lg ${isSel ? 'bg-[#EEF1EC]' : ''}`}>
                        <span className={`text-sm ${isSel ? 'font-semibold text-[#3D4A44]' : 'text-[#5C6660]'}`}>{m.label}</span>
                        <span className={`text-sm tabular-nums ${isSel ? 'font-bold text-[#5B8A72]' : 'text-[#3D4A44]'}`}>{fmt(v.base)}</span>
                      </div>
                    )
                  })}
                </div>
                <div className="mt-3 pt-3 border-t border-[rgba(59,77,67,0.08)]">
                  <div className="flex items-center justify-between text-[11px] text-[#7A8580]">
                    <span>Data coverage</span>
                    <span className="font-medium">{(dq.pct_with_statements || 0).toFixed(1)}% statements</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Trend + per-creator share */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
              <div className={`bg-white border border-[rgba(59,77,67,0.10)] rounded-2xl p-5 ${isOrgScope && perCreator.length ? 'lg:col-span-2' : 'lg:col-span-3'}`}>
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h3 className="text-base font-bold text-[#3D4A44]">Historical Trend</h3>
                    <p className="text-xs text-[#7A8580] mt-0.5">Last 12 months — {methods.find(m => m.key === methodology)?.label}</p>
                  </div>
                </div>
                {trend.length > 0 ? (
                  <ResponsiveContainer width="100%" height={220}>
                    <LineChart data={trend} margin={{ top: 5, right: 10, bottom: 0, left: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#EEF1EC" />
                      <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#7A8580' }} tickFormatter={(d) => { try { return new Date(d).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) } catch { return d } }} />
                      <YAxis tick={{ fontSize: 10, fill: '#7A8580' }} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
                      <Tooltip formatter={(v) => fmt(v)} labelFormatter={(d) => { try { return new Date(d).toLocaleDateString() } catch { return d } }} />
                      <Line type="monotone" dataKey={methodology} stroke="#5B8A72" strokeWidth={2.5} dot={{ r: 3, fill: '#5B8A72' }} name={methods.find(m => m.key === methodology)?.label} />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-[220px] flex items-center justify-center text-sm text-[#7A8580]">Run Full Valuation a few times to build a trend.</div>
                )}
              </div>

              {isOrgScope && perCreator.length > 0 && (
                <div className="bg-white border border-[rgba(59,77,67,0.10)] rounded-2xl p-5">
                  <h3 className="text-base font-bold text-[#3D4A44] mb-1">Per-Creator Share</h3>
                  <p className="text-xs text-[#7A8580] mb-3">Top contributors by blended value</p>
                  <div className="space-y-2 max-h-[180px] overflow-y-auto">
                    {perCreator.slice(0, 8).map(c => (
                      <div key={c.creator_id} className="flex items-center justify-between text-sm">
                        <span className="text-[#3D4A44] truncate mr-2">{c.creator_name}</span>
                        <div className="text-right shrink-0">
                          <div className="font-semibold text-[#3D4A44] tabular-nums">{fmt(c.blended_base)}</div>
                          <div className="text-[10px] text-[#7A8580]">{(c.share_pct || 0).toFixed(1)}%</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Data quality strip */}
            <div className="mb-6 px-4 py-3 bg-[#EEF1EC]/60 border border-[rgba(91,138,114,0.15)] rounded-xl flex flex-wrap items-center gap-x-6 gap-y-2 text-xs text-[#5C6660]">
              <div className="flex items-center gap-2">
                <span className={`px-2 py-0.5 rounded-full font-semibold uppercase ${confColor}`}>{dq.confidence_label || 'low'}</span>
                <span className="text-[#7A8580]">data confidence</span>
              </div>
              <div><span className="font-semibold text-[#3D4A44]">{(dq.pct_with_statements || 0).toFixed(1)}%</span> of songs have matched royalty statements</div>
              <div><span className="font-semibold text-[#3D4A44]">{(dq.pct_with_streaming || 0).toFixed(1)}%</span> of songs have streaming metrics</div>
              <div className="text-[#7A8580]">Average per-song confidence: {((dq.average_confidence || 0) * 100).toFixed(1)}%</div>
            </div>
          </>
        )
      })()}

      {hasUW && (
        <div className="flex space-x-1 mb-6 bg-[#EEF1EC] rounded-lg p-1 overflow-x-auto whitespace-nowrap">
          {[
            { key: 'overview', label: 'Overview', icon: ChartBarIcon },
            { key: 'spine', label: 'Revenue Spine', icon: TableCellsIcon },
            { key: 'decay', label: 'Decay Analytics', icon: ArrowTrendingDownIcon },
            { key: 'concentration', label: 'Concentration', icon: ChartPieIcon },
            { key: 'projections', label: 'Projections', icon: ArrowTrendingUpIcon },
            { key: 'history', label: 'Run History', icon: ClockIcon },
          ].map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex items-center space-x-1.5 px-3 py-2 rounded-md text-xs font-medium transition-all flex-shrink-0 ${activeTab === tab.key ? 'bg-white text-[#3D4A44] shadow-sm' : 'text-[#7A8580] hover:text-[#3D4A44]'}`}
            >
              <tab.icon className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">{tab.label}</span>
            </button>
          ))}
        </div>
      )}

      {(!hasUW || activeTab === 'overview') && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <div className="bg-gradient-to-br from-[rgba(91,138,114,0.08)] to-[rgba(123,165,148,0.08)] rounded-xl p-5 border border-[rgba(91,138,114,0.15)]">
              <div className="flex items-center space-x-2 mb-2">
                <div className="p-1.5 bg-[#5B8A72] rounded-lg"><CurrencyDollarIcon className="w-4 h-4 text-white" /></div>
                <span className="text-xs font-medium text-[#7A8580]">Catalog Value</span>
              </div>
              {hasUW ? (
                <>
                  <div className="text-2xl font-bold text-[#5B8A72]">{fmt(val.blended?.base)}</div>
                  <div className="flex items-center space-x-2 mt-1">
                    <span className="text-[10px] text-[#7A8580]">{fmt(val.blended?.low)}</span>
                    <span className="text-[10px] text-[#7A8580]">—</span>
                    <span className="text-[10px] text-[#7A8580]">{fmt(val.blended?.high)}</span>
                  </div>
                </>
              ) : (
                <>
                  <div className="text-2xl font-bold text-[#5B8A72]">{fmt(catalogData?.total_catalog_value)}</div>
                  <p className="text-xs text-[#7A8580] mt-1">{catalogData?.total_songs} songs</p>
                </>
              )}
            </div>

            <div className="bg-[#FAFBF9] rounded-xl p-5 border border-[rgba(59,77,67,0.08)]">
              <div className="flex items-center space-x-2 mb-2">
                <div className="p-1.5 bg-[rgba(91,154,110,0.12)] rounded-lg"><ArrowTrendingUpIcon className="w-4 h-4 text-[#5B9A6E]" /></div>
                <span className="text-xs font-medium text-[#7A8580]">Annual Revenue</span>
              </div>
              <div className="text-2xl font-bold text-[#3D4A44]">{fmt(hasUW ? ps.annual_revenue : catalogData?.total_annual_revenue)}</div>
              {hasUW && (
                <div className="flex items-center space-x-3 mt-1">
                  <span className="text-[10px] text-[#5B8A72]">Pub: {fmt(ps.publisher_annual)}</span>
                  <span className="text-[10px] text-[#7A8580]">Master: {fmt(ps.master_annual)}</span>
                </div>
              )}
              {!hasUW && <p className="text-xs text-[#5B9A6E] mt-1">+{fmtPct(catalogData?.avg_growth_rate)} avg growth</p>}
            </div>

            <div className="bg-[#FAFBF9] rounded-xl p-5 border border-[rgba(59,77,67,0.08)]">
              <div className="flex items-center space-x-2 mb-2">
                <div className="p-1.5 bg-[rgba(90,138,154,0.12)] rounded-lg"><ClockIcon className="w-4 h-4 text-[#5A8A9A]" /></div>
                <span className="text-xs font-medium text-[#7A8580]">{hasUW ? 'Portfolio Half-Life' : '30-Day Revenue'}</span>
              </div>
              {hasUW ? (
                <>
                  <div className="text-2xl font-bold text-[#3D4A44]">{decay.portfolio_half_life ? `${decay.portfolio_half_life} periods` : 'N/A'}</div>
                  <p className="text-xs text-[#7A8580] mt-1">Avg decay rate: {decay.portfolio_k ? decay.portfolio_k.toFixed(3) : 'N/A'}</p>
                </>
              ) : (
                <>
                  <div className="text-2xl font-bold text-[#3D4A44]">{fmt(catalogData?.total_thirty_day_revenue)}</div>
                  <p className="text-xs text-[#7A8580] mt-1">Last month projection</p>
                </>
              )}
            </div>

            <div className="bg-[#FAFBF9] rounded-xl p-5 border border-[rgba(59,77,67,0.08)]">
              <div className="flex items-center space-x-2 mb-2">
                <div className="p-1.5 bg-[rgba(196,149,107,0.12)] rounded-lg"><ChartPieIcon className="w-4 h-4 text-[#C4956B]" /></div>
                <span className="text-xs font-medium text-[#7A8580]">{hasUW ? 'HHI Concentration' : 'Songs'}</span>
              </div>
              {hasUW && periods.length ? (
                <>
                  <div className="text-2xl font-bold text-[#3D4A44]">{((conc[periods[periods.length - 1]]?.hhi || 0) * 100).toFixed(1)}%</div>
                  <p className="text-xs text-[#7A8580] mt-1">Top-1: {fmtPct(conc[periods[periods.length - 1]]?.top_1)}</p>
                </>
              ) : (
                <>
                  <div className="text-2xl font-bold text-[#3D4A44]">{catalogData?.total_songs || 0}</div>
                  <p className="text-xs text-[#7A8580] mt-1">In catalog</p>
                </>
              )}
            </div>
          </div>

          {hasUW && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
              <div className="bg-[#FAFBF9] rounded-xl border border-[rgba(59,77,67,0.08)] p-5">
                <h3 className="text-sm font-bold text-[#3D4A44] mb-4">Multiplier Valuation</h3>
                <div className="space-y-3">
                  {[
                    { label: 'Publishing (NPS)', data: val.multiplier?.publishing },
                    { label: 'Masters (Net)', data: val.multiplier?.masters },
                    { label: 'Combined', data: val.multiplier?.combined },
                  ].map(row => (
                    <div key={row.label} className="flex items-center justify-between">
                      <span className="text-xs text-[#7A8580]">{row.label}</span>
                      <div className="flex items-center space-x-3 text-xs">
                        <span className="text-[#C47068]">{fmt(row.data?.low)}</span>
                        <span className="font-semibold text-[#3D4A44]">{fmt(row.data?.base)}</span>
                        <span className="text-[#5B9A6E]">{fmt(row.data?.high)}</span>
                      </div>
                    </div>
                  ))}
                  <div className="border-t border-[rgba(59,77,67,0.08)] pt-2 mt-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-[#7A8580]">Adjustment factor</span>
                      <span className={`font-medium ${(val.multiplier?.adjustment_factor || 0) < 0 ? 'text-[#C47068]' : 'text-[#5B9A6E]'}`}>
                        {((val.multiplier?.adjustment_factor || 0) * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-[#FAFBF9] rounded-xl border border-[rgba(59,77,67,0.08)] p-5">
                <h3 className="text-sm font-bold text-[#3D4A44] mb-4">DCF Valuation</h3>
                <div className="space-y-3">
                  {[
                    { label: 'Conservative', value: val.dcf?.low },
                    { label: 'Base Case', value: val.dcf?.base },
                    { label: 'Optimistic', value: val.dcf?.high },
                  ].map(row => (
                    <div key={row.label} className="flex items-center justify-between">
                      <span className="text-xs text-[#7A8580]">{row.label}</span>
                      <span className={`text-xs font-semibold ${row.label === 'Base Case' ? 'text-[#3D4A44]' : 'text-[#7A8580]'}`}>{fmt(row.value)}</span>
                    </div>
                  ))}
                  <div className="border-t border-[rgba(59,77,67,0.08)] pt-2 mt-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-[#3D4A44]">Blended (Avg)</span>
                      <span className="text-sm font-bold text-[#5B8A72]">{fmt(val.blended?.base)}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {hasUW && ps.stability_signals && (
            <div className="bg-[#FAFBF9] rounded-xl border border-[rgba(59,77,67,0.08)] p-5 mb-6">
              <h3 className="text-sm font-bold text-[#3D4A44] mb-3">Stability Signals</h3>
              <div className="flex flex-wrap gap-2">
                {Object.entries(ps.stability_signals).map(([key, value]) => (
                  <div key={key} className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${value ? 'bg-[#C47068]/10 text-[#C47068]' : 'bg-[#5B9A6E]/10 text-[#5B9A6E]'}`}>
                    {value ? <ExclamationTriangleIcon className="w-3 h-3" /> : <CheckCircleIcon className="w-3 h-3" />}
                    <span>{key.replace(/_/g, ' ')}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Source-typed Revenue-by-Source panel: gated to the Income
              methodology view so the toggle drives every panel below the
              hero. The data here (PROs / mechanical / sync / streaming
              buckets at industry multipliers) IS the Income engine's
              breakdown, so it would be misleading under Market-Comp / DCF /
              Blended views. */}
          {methodology === 'income' && sourceTyped && sourceTyped.song_count > 0 && (() => {
            const buckets = sourceTyped.by_bucket || {}
            const totalValue = sourceTyped.total_value_cents / 100
            const totalRevenue = sourceTyped.total_annual_revenue_cents / 100
            const artist = sourceTyped.artist_total_value_cents / 100
            const publisher = sourceTyped.publisher_total_value_cents / 100
            const artistPct = totalValue > 0 ? (artist / totalValue) * 100 : 50
            const publisherPct = totalValue > 0 ? (publisher / totalValue) * 100 : 50
            const bucketRows = [
              { key: 'performance', label: 'Performance', sub: 'PROs · neighboring rights', tone: 'text-[#5B8A72]' },
              { key: 'mechanical', label: 'Mechanical', sub: 'MLC · HFA', tone: 'text-[#5A8A9A]' },
              { key: 'sync', label: 'Sync', sub: 'Sync licensing fees', tone: 'text-[#C4956B]' },
              { key: 'streaming', label: 'Streaming', sub: 'DSP · digital interactive', tone: 'text-[#7BA594]' },
              { key: 'other', label: 'Other', sub: 'Unclassified income (no multiplier)', tone: 'text-[#7A8580]' },
            ]
            return (
              <div className="bg-[#FAFBF9] rounded-xl border border-[rgba(59,77,67,0.08)] mb-6">
                <div className="p-5 border-b border-[rgba(59,77,67,0.08)] flex items-start justify-between">
                  <div>
                    <div className="flex items-center space-x-2">
                      <h2 className="text-base font-bold text-[#3D4A44]">Revenue by Source</h2>
                      <span className="px-1.5 py-0.5 text-[9px] font-semibold tracking-wide uppercase bg-[#5B8A72]/10 text-[#5B8A72] rounded-md">Source-Typed</span>
                      {sourceTyped.fresh && (
                        <span className="px-1.5 py-0.5 text-[9px] font-semibold tracking-wide uppercase bg-[#5B9A6E]/10 text-[#5B9A6E] rounded-md">Just computed</span>
                      )}
                    </div>
                    <p className="text-xs text-[#7A8580] mt-1">
                      Annualized from {sourceTyped.songs_with_revenue} of {sourceTyped.song_count} songs · {sourceTyped.computed_at ? `last run ${new Date(sourceTyped.computed_at).toLocaleString()}` : 'not yet computed'}
                    </p>
                  </div>
                  <div className="text-right">
                    <div className="text-[10px] text-[#7A8580] uppercase">Catalog Value</div>
                    <div className="text-2xl font-bold text-[#5B8A72]">{fmt(totalValue)}</div>
                    <div className="text-[10px] text-[#7A8580] mt-0.5">on {fmt(totalRevenue)} annual revenue</div>
                  </div>
                </div>
                <div className="p-5">
                  <div className="overflow-x-auto -mx-5 px-5">
                  <table className="w-full min-w-[480px]">
                    <thead>
                      <tr className="text-[10px] font-medium text-[#7A8580] uppercase border-b border-[rgba(59,77,67,0.08)]">
                        <th className="text-left pb-2">Source</th>
                        <th className="text-right pb-2">Annual Revenue</th>
                        <th className="text-right pb-2">Multiplier</th>
                        <th className="text-right pb-2">Contribution to Value</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[rgba(59,77,67,0.06)]">
                      {bucketRows.map(row => {
                        const b = buckets[row.key] || {}
                        const rev = (b.revenue_cents || 0) / 100
                        const val = (b.value_cents || 0) / 100
                        const pct = totalValue > 0 ? (val / totalValue) * 100 : 0
                        return (
                          <tr key={row.key} className="text-sm">
                            <td className="py-2.5">
                              <div className={`font-medium ${row.tone}`}>{row.label}</div>
                              <div className="text-[10px] text-[#7A8580]">{row.sub}</div>
                            </td>
                            <td className="py-2.5 text-right text-[#3D4A44]">{fmt(rev)}</td>
                            <td className="py-2.5 text-right text-[#7A8580]">{b.multiplier ? `${b.multiplier}×` : '—'}</td>
                            <td className="py-2.5 text-right">
                              <div className="font-semibold text-[#3D4A44]">{fmt(val)}</div>
                              <div className="text-[10px] text-[#7A8580]">{pct.toFixed(1)}% of total</div>
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                  </div>

                  <div className="mt-6 pt-5 border-t border-[rgba(59,77,67,0.08)]">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-xs font-bold text-[#3D4A44] uppercase tracking-wide">Artist vs Publisher Split</h3>
                      <span className="text-[10px] text-[#7A8580]">Derived from RightsSplit (MASTER vs PUBLISHING)</span>
                    </div>
                    <div className="flex h-8 rounded-lg overflow-hidden border border-[rgba(59,77,67,0.08)]">
                      <div
                        className="bg-[#5B8A72] flex items-center justify-center text-[10px] font-semibold text-white"
                        style={{ width: `${artistPct}%`, minWidth: artistPct > 0 ? '60px' : 0 }}
                      >
                        {artistPct.toFixed(0)}%
                      </div>
                      <div
                        className="bg-[#5A8A9A] flex items-center justify-center text-[10px] font-semibold text-white"
                        style={{ width: `${publisherPct}%`, minWidth: publisherPct > 0 ? '60px' : 0 }}
                      >
                        {publisherPct.toFixed(0)}%
                      </div>
                    </div>
                    <div className="flex justify-between mt-2 text-xs">
                      <div>
                        <span className="inline-block w-2 h-2 rounded-full bg-[#5B8A72] mr-1.5"></span>
                        <span className="text-[#7A8580]">Artist (Master):</span>
                        <span className="ml-1.5 font-semibold text-[#3D4A44]">{fmt(artist)}</span>
                      </div>
                      <div>
                        <span className="inline-block w-2 h-2 rounded-full bg-[#5A8A9A] mr-1.5"></span>
                        <span className="text-[#7A8580]">Publisher:</span>
                        <span className="ml-1.5 font-semibold text-[#3D4A44]">{fmt(publisher)}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )
          })()}

          {methodology === 'income' && sourceTyped && sourceTyped.song_count === 0 && !hasUW && (
            <div className="bg-[#FAFBF9] rounded-xl border border-dashed border-[rgba(91,138,114,0.25)] p-6 mb-6 text-center">
              <ChartPieIcon className="w-8 h-8 text-[#5B8A72] mx-auto mb-2" />
              <h3 className="text-sm font-semibold text-[#3D4A44]">No source-typed valuation yet</h3>
              <p className="text-xs text-[#7A8580] mt-1 max-w-md mx-auto">
                Click <strong>Source-Typed Valuation</strong> above to bucket your matched royalty statements by source (performance / mechanical / sync / streaming) and apply industry multipliers.
              </p>
            </div>
          )}

          {(!hasUW && catalogData?.top_songs?.length > 0) && (
            <div className="bg-[#FAFBF9] rounded-xl shadow-sm mb-6">
              <div className="p-5 border-b border-[rgba(59,77,67,0.08)]">
                <h2 className="text-base font-bold text-[#3D4A44]">Top Valued Songs</h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-[#EEF1EC]">
                    <tr>
                      <th className="px-4 py-2.5 text-left text-[10px] font-medium text-[#7A8580] uppercase">Song</th>
                      <th className="px-4 py-2.5 text-right text-[10px] font-medium text-[#7A8580] uppercase">Streams</th>
                      <th className="px-4 py-2.5 text-right text-[10px] font-medium text-[#7A8580] uppercase">Valuation</th>
                      <th className="px-4 py-2.5 text-right text-[10px] font-medium text-[#7A8580] uppercase">Annual Rev</th>
                      <th className="px-4 py-2.5 text-right text-[10px] font-medium text-[#7A8580] uppercase">Growth</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[rgba(59,77,67,0.06)]">
                    {catalogData.top_songs.map(song => (
                      <tr key={song.song_id} onClick={() => { setSelectedSong(song); loadSongDetail(song.song_id) }} className="hover:bg-[#EEF1EC] cursor-pointer text-sm">
                        <td className="px-4 py-3">
                          <div className="font-medium text-[#3D4A44]">{song.title}</div>
                          <div className="text-[10px] text-[#7A8580]">{song.primary_artist} {song.isrc ? `· ${song.isrc}` : ''}</div>
                        </td>
                        <td className="px-4 py-3 text-right text-[#3D4A44]">{fmtNum(song.total_streams)}</td>
                        <td className="px-4 py-3 text-right font-semibold text-[#5B8A72]">{fmt(song.final_valuation)}</td>
                        <td className="px-4 py-3 text-right text-[#3D4A44]">{fmt(song.annual_revenue)}</td>
                        <td className="px-4 py-3 text-right">
                          <span className={song.growth_rate >= 0 ? 'text-[#5B9A6E]' : 'text-[#C47068]'}>
                            {song.growth_rate >= 0 ? '+' : ''}{fmtPct(song.growth_rate)}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {!hasUW && (
            <div className="bg-gradient-to-br from-[rgba(91,138,114,0.04)] to-[rgba(123,165,148,0.04)] rounded-xl border border-dashed border-[rgba(91,138,114,0.25)] p-8 text-center mb-6">
              <SparklesIcon className="w-10 h-10 text-[#5B8A72] mx-auto mb-3" />
              <h3 className="text-lg font-semibold text-[#3D4A44] mb-2">Institutional Underwriting Engine</h3>
              <p className="text-sm text-[#7A8580] max-w-xl mx-auto mb-4">
                Run an underwriting analysis to generate statement-driven valuations with decay analytics, concentration metrics, DCF projections, and multiplier bands powered by your ingested royalty data.
              </p>
              <button onClick={() => setRunModalOpen(true)} className="inline-flex items-center space-x-2 px-5 py-2.5 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] transition-all text-sm font-medium">
                <SparklesIcon className="w-4 h-4" />
                <span>Run First Analysis</span>
              </button>
            </div>
          )}
        </>
      )}

      {hasUW && activeTab === 'spine' && (
        <div className="bg-[#FAFBF9] rounded-xl border border-[rgba(59,77,67,0.08)] mb-6">
          <div className="p-5 border-b border-[rgba(59,77,67,0.08)] flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-[#3D4A44]">Song-by-Period Revenue Spine</h2>
              <p className="text-xs text-[#7A8580] mt-0.5">{spine.length} entries across {periods.length} periods</p>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="bg-[#EEF1EC]">
                <tr>
                  <th className="px-3 py-2 text-left font-medium text-[#7A8580] uppercase text-[10px] sticky left-0 bg-[#EEF1EC] z-10 min-w-[180px]">Song</th>
                  {periods.map(p => (
                    <th key={p} className="px-3 py-2 text-right font-medium text-[#7A8580] uppercase text-[10px] min-w-[90px]">{p}</th>
                  ))}
                  <th className="px-3 py-2 text-right font-medium text-[#7A8580] uppercase text-[10px] min-w-[100px]">Total</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[rgba(59,77,67,0.06)]">
                {spineByPeriod.map((song, i) => (
                  <tr key={i} className="hover:bg-[#EEF1EC]">
                    <td className="px-3 py-2 sticky left-0 bg-[#FAFBF9] z-10">
                      <div className="font-medium text-[#3D4A44] truncate max-w-[170px]">{song.title}</div>
                      {song.isrc && <div className="text-[9px] text-[#7A8580]">{song.isrc}</div>}
                    </td>
                    {periods.map(p => {
                      const val = song.periods[p]
                      return (
                        <td key={p} className={`px-3 py-2 text-right ${val ? 'text-[#3D4A44]' : 'text-[#D1D5D3]'}`}>
                          {val ? fmtDec(val) : '—'}
                        </td>
                      )
                    })}
                    <td className="px-3 py-2 text-right font-semibold text-[#5B8A72]">{fmtDec(song.total)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {hasUW && activeTab === 'decay' && (() => {
        const awaitingData = Array.isArray(decay.awaiting_data) ? decay.awaiting_data : []
        const fitCount = Object.keys(decay.per_song || {}).length
        const hasSpine = decay.has_revenue_spine !== false && (
          (decay.has_revenue_spine === true) || fitCount > 0 || awaitingData.length > 0
        )
        const minPoints = decay.min_data_points || 3
        const reasonLabel = (r) => {
          if (r === 'insufficient_data') return 'Not enough periods yet'
          if (r === 'no_post_peak_data') return 'No post-peak periods yet'
          if (r === 'fit_failed') return 'Curve fit failed'
          return r || '—'
        }

        if (!hasSpine && fitCount === 0 && awaitingData.length === 0) {
          return (
            <div className="space-y-6 mb-6">
              <div className="bg-[#FAFBF9] rounded-xl border border-[rgba(59,77,67,0.08)] p-10 text-center">
                <ArrowTrendingDownIcon className="h-10 w-10 text-[#B5C0B8] mx-auto mb-3" />
                <h3 className="text-base font-semibold text-[#3D4A44] mb-1">No revenue data yet</h3>
                <p className="text-sm text-[#7A8580] max-w-md mx-auto">
                  Upload more royalty statements to enable decay analytics. We need at least {minPoints} periods of post-peak revenue per song before a curve can be fit.
                </p>
              </div>
            </div>
          )
        }

        return (
        <div className="space-y-6 mb-6">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-[#FAFBF9] rounded-xl border border-[rgba(59,77,67,0.08)] p-5">
              <div className="text-xs text-[#7A8580] mb-1">Portfolio Decay Rate (k)</div>
              {decay.portfolio_k != null ? (
                <div className="text-2xl font-bold text-[#3D4A44]">{decay.portfolio_k.toFixed(4)}</div>
              ) : (
                <div>
                  <div className="text-2xl font-bold text-[#B5C0B8]">—</div>
                  <span className="inline-block mt-1 text-[10px] font-medium text-[#C4956B] bg-[#FAF1E6] px-2 py-0.5 rounded-full uppercase tracking-wide">Insufficient data</span>
                </div>
              )}
            </div>
            <div className="bg-[#FAFBF9] rounded-xl border border-[rgba(59,77,67,0.08)] p-5">
              <div className="text-xs text-[#7A8580] mb-1">Portfolio Half-Life</div>
              {decay.portfolio_half_life != null ? (
                <div className="text-2xl font-bold text-[#3D4A44]">{decay.portfolio_half_life} periods</div>
              ) : (
                <div>
                  <div className="text-2xl font-bold text-[#B5C0B8]">—</div>
                  <span className="inline-block mt-1 text-[10px] font-medium text-[#C4956B] bg-[#FAF1E6] px-2 py-0.5 rounded-full uppercase tracking-wide">Insufficient data</span>
                </div>
              )}
            </div>
            <div className="bg-[#FAFBF9] rounded-xl border border-[rgba(59,77,67,0.08)] p-5">
              <div className="text-xs text-[#7A8580] mb-1">Songs with Decay Fit</div>
              <div className="text-2xl font-bold text-[#3D4A44]">{fitCount}</div>
              {awaitingData.length > 0 && (
                <p className="text-[11px] text-[#7A8580] mt-1">{awaitingData.length} awaiting more data</p>
              )}
            </div>
          </div>

          {halfLifeChartData.length > 0 && (
            <div className="bg-[#FAFBF9] rounded-xl border border-[rgba(59,77,67,0.08)] p-5">
              <h3 className="text-sm font-bold text-[#3D4A44] mb-4">Half-Life Distribution</h3>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={halfLifeChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(59,77,67,0.08)" />
                  <XAxis dataKey="bin" tick={{ fontSize: 11, fill: '#7A8580' }} />
                  <YAxis tick={{ fontSize: 11, fill: '#7A8580' }} />
                  <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid rgba(59,77,67,0.12)' }} />
                  <Bar dataKey="count" fill="#5B8A72" radius={[4, 4, 0, 0]} name="Songs" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {decay.per_song && Object.keys(decay.per_song).length > 0 && (
            <div className="bg-[#FAFBF9] rounded-xl border border-[rgba(59,77,67,0.08)]">
              <div className="p-5 border-b border-[rgba(59,77,67,0.08)]">
                <h3 className="text-sm font-bold text-[#3D4A44]">Per-Song Decay Parameters</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead className="bg-[#EEF1EC]">
                    <tr>
                      <th className="px-3 py-2 text-left font-medium text-[#7A8580] uppercase text-[10px]">Song ID</th>
                      <th className="px-3 py-2 text-right font-medium text-[#7A8580] uppercase text-[10px]">k</th>
                      <th className="px-3 py-2 text-right font-medium text-[#7A8580] uppercase text-[10px]">Half-Life</th>
                      <th className="px-3 py-2 text-right font-medium text-[#7A8580] uppercase text-[10px]">R²</th>
                      <th className="px-3 py-2 text-right font-medium text-[#7A8580] uppercase text-[10px]">Volatility</th>
                      <th className="px-3 py-2 text-right font-medium text-[#7A8580] uppercase text-[10px]">CAGR</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[rgba(59,77,67,0.06)]">
                    {Object.entries(decay.per_song).slice(0, 30).map(([sid, d]) => (
                      <tr key={sid} className="hover:bg-[#EEF1EC]">
                        <td className="px-3 py-2 font-medium text-[#3D4A44]">{sid}</td>
                        <td className="px-3 py-2 text-right text-[#3D4A44]">{d.k?.toFixed(4)}</td>
                        <td className="px-3 py-2 text-right text-[#3D4A44]">{d.half_life_periods?.toFixed(1) || '—'}</td>
                        <td className="px-3 py-2 text-right">
                          <span className={d.r2 >= 0.7 ? 'text-[#5B9A6E]' : d.r2 >= 0.4 ? 'text-[#C4956B]' : 'text-[#C47068]'}>
                            {d.r2?.toFixed(3)}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-right text-[#3D4A44]">{d.volatility?.toFixed(3) || '—'}</td>
                        <td className="px-3 py-2 text-right">
                          <span className={(d.cagr || 0) >= 0 ? 'text-[#5B9A6E]' : 'text-[#C47068]'}>
                            {d.cagr != null ? fmtPct(d.cagr) : '—'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {awaitingData.length > 0 && (
            <div className="bg-[#FAFBF9] rounded-xl border border-[rgba(59,77,67,0.08)]">
              <div className="p-5 border-b border-[rgba(59,77,67,0.08)]">
                <h3 className="text-sm font-bold text-[#3D4A44]">Songs Awaiting More Data ({awaitingData.length})</h3>
                <p className="text-xs text-[#7A8580] mt-1">
                  These songs have revenue but not yet enough post-peak periods (need {minPoints}) to fit a decay curve. Sorted by closest to fitting.
                </p>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead className="bg-[#EEF1EC]">
                    <tr>
                      <th className="px-3 py-2 text-left font-medium text-[#7A8580] uppercase text-[10px]">Song</th>
                      <th className="px-3 py-2 text-right font-medium text-[#7A8580] uppercase text-[10px]">Periods on file</th>
                      <th className="px-3 py-2 text-right font-medium text-[#7A8580] uppercase text-[10px]">Periods needed</th>
                      <th className="px-3 py-2 text-left font-medium text-[#7A8580] uppercase text-[10px]">Reason</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[rgba(59,77,67,0.06)]">
                    {awaitingData.slice(0, 100).map((row) => (
                      <tr key={row.spine_key} className="hover:bg-[#EEF1EC]">
                        <td className="px-3 py-2 font-medium text-[#3D4A44]">{row.title}</td>
                        <td className="px-3 py-2 text-right text-[#3D4A44]">{row.periods_present}</td>
                        <td className="px-3 py-2 text-right text-[#3D4A44]">
                          {row.periods_needed > 0 ? `${row.periods_needed} more` : '—'}
                        </td>
                        <td className="px-3 py-2 text-[#7A8580]">{reasonLabel(row.reason)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {awaitingData.length > 100 && (
                  <div className="px-5 py-3 text-[11px] text-[#7A8580] border-t border-[rgba(59,77,67,0.06)]">
                    Showing first 100 of {awaitingData.length}.
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
        )
      })()}

      {hasUW && activeTab === 'concentration' && (
        <div className="space-y-6 mb-6">
          {concentrationChartData.length > 0 && (
            <div className="bg-[#FAFBF9] rounded-xl border border-[rgba(59,77,67,0.08)] p-5">
              <h3 className="text-sm font-bold text-[#3D4A44] mb-4">Concentration Trends</h3>
              <ResponsiveContainer width="100%" height={280}>
                <LineChart data={concentrationChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(59,77,67,0.08)" />
                  <XAxis dataKey="period" tick={{ fontSize: 11, fill: '#7A8580' }} />
                  <YAxis tick={{ fontSize: 11, fill: '#7A8580' }} unit="%" />
                  <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid rgba(59,77,67,0.12)' }} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Line type="monotone" dataKey="Top 1" stroke="#C47068" strokeWidth={2} dot={{ r: 3 }} />
                  <Line type="monotone" dataKey="Top 3" stroke="#C4956B" strokeWidth={2} dot={{ r: 3 }} />
                  <Line type="monotone" dataKey="Top 5" stroke="#5B8A72" strokeWidth={2} dot={{ r: 3 }} />
                  <Line type="monotone" dataKey="HHI" stroke="#5A8A9A" strokeWidth={2} dot={{ r: 3 }} strokeDasharray="5 5" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          <div className="bg-[#FAFBF9] rounded-xl border border-[rgba(59,77,67,0.08)]">
            <div className="p-5 border-b border-[rgba(59,77,67,0.08)]">
              <h3 className="text-sm font-bold text-[#3D4A44]">Concentration by Period</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead className="bg-[#EEF1EC]">
                  <tr>
                    <th className="px-3 py-2 text-left font-medium text-[#7A8580] uppercase text-[10px]">Period</th>
                    <th className="px-3 py-2 text-right font-medium text-[#7A8580] uppercase text-[10px]">Top 1</th>
                    <th className="px-3 py-2 text-right font-medium text-[#7A8580] uppercase text-[10px]">Top 3</th>
                    <th className="px-3 py-2 text-right font-medium text-[#7A8580] uppercase text-[10px]">Top 5</th>
                    <th className="px-3 py-2 text-right font-medium text-[#7A8580] uppercase text-[10px]">Top 10</th>
                    <th className="px-3 py-2 text-right font-medium text-[#7A8580] uppercase text-[10px]">HHI</th>
                    <th className="px-3 py-2 text-right font-medium text-[#7A8580] uppercase text-[10px]">Songs</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[rgba(59,77,67,0.06)]">
                  {periods.map(p => {
                    const c = conc[p] || {}
                    return (
                      <tr key={p} className="hover:bg-[#EEF1EC]">
                        <td className="px-3 py-2 font-medium text-[#3D4A44]">{p}</td>
                        <td className="px-3 py-2 text-right">{fmtPct(c.top_1)}</td>
                        <td className="px-3 py-2 text-right">{fmtPct(c.top_3)}</td>
                        <td className="px-3 py-2 text-right">{fmtPct(c.top_5)}</td>
                        <td className="px-3 py-2 text-right">{fmtPct(c.top_10)}</td>
                        <td className="px-3 py-2 text-right">
                          <span className={(c.hhi || 0) > 0.25 ? 'text-[#C47068] font-semibold' : 'text-[#3D4A44]'}>{(c.hhi || 0).toFixed(4)}</span>
                        </td>
                        <td className="px-3 py-2 text-right text-[#7A8580]">{c.song_count || 0}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {hasUW && activeTab === 'projections' && (
        <div className="space-y-6 mb-6">
          {projectionChartData.length > 0 && (
            <div className="bg-[#FAFBF9] rounded-xl border border-[rgba(59,77,67,0.08)] p-5">
              <h3 className="text-sm font-bold text-[#3D4A44] mb-4">Revenue Projections (Scenario Bands)</h3>
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={projectionChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(59,77,67,0.08)" />
                  <XAxis dataKey="year" tick={{ fontSize: 11, fill: '#7A8580' }} />
                  <YAxis tick={{ fontSize: 11, fill: '#7A8580' }} tickFormatter={v => `$${(v / 1000).toFixed(0)}k`} />
                  <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid rgba(59,77,67,0.12)' }} formatter={v => fmt(v)} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Area type="monotone" dataKey="Upside" stroke="#5B9A6E" fill="#5B9A6E" fillOpacity={0.1} strokeWidth={1.5} />
                  <Area type="monotone" dataKey="Base" stroke="#5B8A72" fill="#5B8A72" fillOpacity={0.15} strokeWidth={2} />
                  <Area type="monotone" dataKey="Downside" stroke="#C47068" fill="#C47068" fillOpacity={0.1} strokeWidth={1.5} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}

          <div className="bg-[#FAFBF9] rounded-xl border border-[rgba(59,77,67,0.08)]">
            <div className="p-5 border-b border-[rgba(59,77,67,0.08)]">
              <h3 className="text-sm font-bold text-[#3D4A44]">Projected Revenue by Year</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead className="bg-[#EEF1EC]">
                  <tr>
                    <th className="px-3 py-2 text-left font-medium text-[#7A8580] uppercase text-[10px]">Year</th>
                    <th className="px-3 py-2 text-right font-medium text-[#C47068] uppercase text-[10px]">Downside</th>
                    <th className="px-3 py-2 text-right font-medium text-[#3D4A44] uppercase text-[10px]">Base</th>
                    <th className="px-3 py-2 text-right font-medium text-[#5B9A6E] uppercase text-[10px]">Upside</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[rgba(59,77,67,0.06)]">
                  {projectionChartData.map(row => (
                    <tr key={row.year} className="hover:bg-[#EEF1EC]">
                      <td className="px-3 py-2 font-medium text-[#3D4A44]">{row.year}</td>
                      <td className="px-3 py-2 text-right text-[#C47068]">{fmt(row.Downside)}</td>
                      <td className="px-3 py-2 text-right font-semibold text-[#3D4A44]">{fmt(row.Base)}</td>
                      <td className="px-3 py-2 text-right text-[#5B9A6E]">{fmt(row.Upside)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {hasUW && activeTab === 'history' && (
        <div className="bg-[#FAFBF9] rounded-xl border border-[rgba(59,77,67,0.08)] mb-6">
          <div className="p-5 border-b border-[rgba(59,77,67,0.08)]">
            <h2 className="text-base font-bold text-[#3D4A44]">Underwriting Run History</h2>
          </div>
          {runs.length === 0 ? (
            <div className="p-8 text-center text-sm text-[#7A8580]">No runs yet</div>
          ) : (
            <div className="divide-y divide-[rgba(59,77,67,0.06)]">
              {runs.map(run => (
                <div key={run.id} className="p-4 hover:bg-[#EEF1EC] cursor-pointer" onClick={async () => {
                  try {
                    // Restore the scope the run was executed under so the URL
                    // and surrounding panels match. We fetch the run + catalog
                    // summary FIRST, then suppress the scope-effect's loadAll
                    // (via skipNextLoadRef) so it can't race-overwrite uwData
                    // with /underwriting/latest for the new scope.
                    const runScopeId = run.scope_creator_id ?? null
                    const scopeQs = runScopeId ? `?scope_creator_id=${runScopeId}` : ''
                    const [runRes, catRes] = await Promise.allSettled([
                      axios.get(`/api/valuation/underwriting/runs/${run.id}`),
                      axios.get(`/api/valuation/catalog/summary${scopeQs}`),
                    ])
                    if (runScopeId !== scopeCreatorId) {
                      skipNextLoadRef.current = true
                      setScopeCreatorId(runScopeId)
                    }
                    if (runRes.status === 'fulfilled') setUwData({ ...runRes.value.data, has_data: true })
                    if (catRes.status === 'fulfilled') setCatalogData(catRes.value.data)
                    setActiveTab('overview')
                  } catch (e) { console.error(e) }
                }}>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 min-w-0">
                      <div className={`w-2 h-2 rounded-full flex-shrink-0 ${run.status === 'COMPLETED' ? 'bg-[#5B9A6E]' : run.status === 'FAILED' ? 'bg-[#C47068]' : 'bg-[#C4956B]'}`} />
                      <span className="text-sm font-medium text-[#3D4A44]">Run #{run.id}</span>
                      <span className="text-xs text-[#7A8580]">{run.status}</span>
                      <span className={`text-[10px] px-2 py-0.5 rounded-full max-w-[180px] truncate ${run.scope_creator_id ? 'bg-[#E5EEDF] text-[#5B8A72]' : 'bg-[rgba(59,77,67,0.08)] text-[#7A8580]'}`}>
                        {run.scope_creator_id ? (run.scope_creator_name || `Creator #${run.scope_creator_id}`) : 'Org-wide'}
                      </span>
                    </div>
                    <div className="text-right ml-auto">
                      {run.valuation && <span className="text-sm font-semibold text-[#5B8A72] mr-4">{fmt(run.valuation.base)}</span>}
                      <span className="text-xs text-[#7A8580]">{run.created_at ? new Date(run.created_at).toLocaleString() : ''}</span>
                    </div>
                  </div>
                  <div className="mt-1 flex flex-wrap gap-2 text-[10px] text-[#7A8580]">
                    <span>KB: {run.kb_version}</span>
                    {run.inputs?.periodization_mode && <span>Mode: {run.inputs.periodization_mode}</span>}
                    {run.portfolio_summary?.total_songs_in_spine != null && <span>Songs: {run.portfolio_summary.total_songs_in_spine}</span>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {runModalOpen && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md mx-4">
            <div className="flex items-center justify-between p-5 border-b border-[rgba(59,77,67,0.08)]">
              <div className="flex items-center space-x-2">
                <SparklesIcon className="w-5 h-5 text-[#5B8A72]" />
                <h3 className="text-base font-semibold text-[#3D4A44]">Run Underwriting Analysis</h3>
              </div>
              <button onClick={() => setRunModalOpen(false)} className="text-[#7A8580] hover:text-[#3D4A44]"><XMarkIcon className="w-5 h-5" /></button>
            </div>
            <div className="p-5 space-y-4">
              <div>
                <label className="block text-xs font-medium text-[#3D4A44] mb-1">Periodization Mode</label>
                <select value={runConfig.periodization_mode} onChange={e => setRunConfig(c => ({ ...c, periodization_mode: e.target.value }))} className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent">
                  <option value="activity">Activity Period (Earned)</option>
                  <option value="statement">Statement Period (Settlement)</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-[#3D4A44] mb-1">Granularity</label>
                <select value={runConfig.granularity} onChange={e => setRunConfig(c => ({ ...c, granularity: e.target.value }))} className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent">
                  <option value="half">Semi-Annual (H1/H2)</option>
                  <option value="quarter">Quarterly (Q1-Q4)</option>
                </select>
              </div>
              <div className="flex items-center justify-between">
                <label className="text-xs font-medium text-[#3D4A44]">Include Sync & Print Revenue</label>
                <button onClick={() => setRunConfig(c => ({ ...c, include_sync: !c.include_sync }))} className={`relative w-10 h-5 rounded-full transition-colors ${runConfig.include_sync ? 'bg-[#5B8A72]' : 'bg-[#D1D5D3]'}`}>
                  <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${runConfig.include_sync ? 'translate-x-5' : 'translate-x-0.5'}`} />
                </button>
              </div>
              <div className="flex items-center justify-between">
                <label className="text-xs font-medium text-[#3D4A44]">Use Gross (vs Net)</label>
                <button onClick={() => setRunConfig(c => ({ ...c, use_gross: !c.use_gross }))} className={`relative w-10 h-5 rounded-full transition-colors ${runConfig.use_gross ? 'bg-[#5B8A72]' : 'bg-[#D1D5D3]'}`}>
                  <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${runConfig.use_gross ? 'translate-x-5' : 'translate-x-0.5'}`} />
                </button>
              </div>
            </div>
            <div className="flex justify-end space-x-3 p-5 border-t border-[rgba(59,77,67,0.08)]">
              <button onClick={() => setRunModalOpen(false)} className="px-4 py-2 text-sm border border-[rgba(59,77,67,0.12)] rounded-lg text-[#3D4A44] hover:bg-[#EEF1EC]">Cancel</button>
              <button onClick={triggerRun} disabled={running} className="flex items-center space-x-2 px-4 py-2 text-sm bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] disabled:opacity-50">
                {running ? <ArrowPathIcon className="w-4 h-4 animate-spin" /> : <SparklesIcon className="w-4 h-4" />}
                <span>{running ? 'Running...' : 'Run Analysis'}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {selectedSong && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#FAFBF9] rounded-xl shadow-2xl max-w-3xl w-full max-h-[85vh] overflow-hidden flex flex-col">
            <div className="p-5 border-b border-[rgba(59,77,67,0.08)] flex items-center justify-between bg-gradient-to-r from-[rgba(91,138,114,0.06)] to-transparent">
              <div>
                <h2 className="text-lg font-bold text-[#3D4A44]">{selectedSong.title}</h2>
                <p className="text-xs text-[#7A8580]">{selectedSong.primary_artist}</p>
              </div>
              <button onClick={() => { setSelectedSong(null); setSongDetail(null) }} className="text-[#7A8580] hover:text-[#3D4A44]">
                <XMarkIcon className="w-5 h-5" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-5">
              {loadingDetail ? (
                <div className="flex items-center justify-center h-48">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#5B8A72]"></div>
                </div>
              ) : songDetail ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <div className="bg-[rgba(91,138,114,0.06)] rounded-lg p-3">
                      <div className="text-[10px] text-[#7A8580] mb-0.5">Valuation</div>
                      <div className="text-lg font-bold text-[#5B8A72]">{fmt(songDetail.valuation?.final_valuation)}</div>
                    </div>
                    <div className="bg-[rgba(91,154,110,0.06)] rounded-lg p-3">
                      <div className="text-[10px] text-[#7A8580] mb-0.5">Annual Revenue</div>
                      <div className="text-lg font-bold text-[#5B9A6E]">{fmt(songDetail.valuation?.annual_revenue)}</div>
                    </div>
                    <div className="bg-[rgba(90,138,154,0.06)] rounded-lg p-3">
                      <div className="text-[10px] text-[#7A8580] mb-0.5">Total Streams</div>
                      <div className="text-lg font-bold text-[#5A8A9A]">{fmtNum(songDetail.streaming_metrics?.total_streams)}</div>
                    </div>
                    <div className="bg-[rgba(196,149,107,0.06)] rounded-lg p-3">
                      <div className="text-[10px] text-[#7A8580] mb-0.5">Growth Rate</div>
                      <div className="text-lg font-bold text-[#C4956B]">{fmtPct(songDetail.valuation?.growth_rate)}</div>
                    </div>
                  </div>
                  {songDetail.valuation && (
                    <div className="bg-[#EEF1EC] rounded-lg p-4">
                      <h3 className="text-xs font-bold text-[#3D4A44] mb-3">Valuation Breakdown</h3>
                      <div className="grid grid-cols-2 gap-3 text-xs">
                        <div><span className="text-[#7A8580]">Streaming Multiple</span><div className="font-semibold">{fmt(songDetail.valuation.streaming_multiple_value)}</div></div>
                        <div><span className="text-[#7A8580]">Revenue Multiple</span><div className="font-semibold">{fmt(songDetail.valuation.revenue_multiple_value)}</div></div>
                        <div><span className="text-[#7A8580]">Market Comp</span><div className="font-semibold">{fmt(songDetail.valuation.market_comp_value)}</div></div>
                        <div><span className="text-[#7A8580]">Black Box</span><div className="font-semibold text-[#5B8A72]">{fmt(songDetail.valuation.black_box_value)}</div></div>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center text-sm text-[#7A8580]">No detail available</div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
