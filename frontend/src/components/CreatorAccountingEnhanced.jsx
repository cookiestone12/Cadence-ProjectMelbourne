import React, { useState, useEffect, useCallback } from 'react'
import axios from 'axios'
import {
  ArrowUpTrayIcon, DocumentTextIcon, CurrencyDollarIcon,
  ArrowPathIcon, BanknotesIcon, ChartBarIcon, TrashIcon,
  EyeIcon, XMarkIcon
} from '@heroicons/react/24/outline'
import StatementDetailView from './StatementDetailView'
import ProcessingInboxPanel from './ProcessingInboxPanel'
import RoyaltyAnalyticsDashboard from './RoyaltyAnalyticsDashboard'

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

const ENTRY_TYPES = ['ALL', 'EARNING', 'FEE', 'RECOUPMENT_APPLIED', 'PAYABLE_CREATED', 'PAYMENT', 'REVERSAL']

const ENTRY_TYPE_COLORS = {
  EARNING: 'bg-green-100 text-green-700',
  FEE: 'bg-amber-100 text-amber-700',
  RECOUPMENT_APPLIED: 'bg-purple-100 text-purple-700',
  PAYABLE_CREATED: 'bg-blue-100 text-blue-700',
  PAYMENT: 'bg-teal-100 text-teal-700',
  REVERSAL: 'bg-red-100 text-red-700',
}

const POOL_COLORS = {
  MASTER: 'bg-purple-100 text-purple-700',
  PUBLISHING: 'bg-blue-100 text-blue-700',
  BOTH: 'bg-teal-100 text-teal-700',
  CUSTOM: 'bg-orange-100 text-orange-700',
}

const STATEMENT_STATUS_COLORS = {
  PENDING: { bg: 'bg-amber-100', text: 'text-amber-700' },
  UPLOADED: { bg: 'bg-blue-100', text: 'text-blue-700' },
  PROCESSING: { bg: 'bg-blue-100', text: 'text-blue-700' },
  PROCESSED: { bg: 'bg-green-100', text: 'text-green-700' },
  FAILED: { bg: 'bg-red-100', text: 'text-red-700' },
  PARTIALLY_MATCHED: { bg: 'bg-orange-100', text: 'text-orange-700' },
  FULLY_MATCHED: { bg: 'bg-green-100', text: 'text-green-700' },
  REVIEW_REQUIRED: { bg: 'bg-amber-100', text: 'text-amber-700' },
}

const SOURCE_TYPE_OPTIONS = [
  { value: '', label: 'Auto-detect' },
  { value: 'DSP', label: 'DSP / Distributor' },
  { value: 'BMI', label: 'BMI' },
  { value: 'ASCAP', label: 'ASCAP' },
  { value: 'SESAC', label: 'SESAC' },
  { value: 'SoundExchange', label: 'SoundExchange' },
  { value: 'OTHER_PRO', label: 'Other PRO' },
]

export default function CreatorAccountingEnhanced({ orgId, creatorId, existingAccountingData, accountingLoading, onRefresh }) {
  const [activeSubTab, setActiveSubTab] = useState('summary')
  const [payeeId, setPayeeId] = useState(null)
  const [payeeResolved, setPayeeResolved] = useState(false)

  const [ledgerEntries, setLedgerEntries] = useState([])
  const [ledgerLoading, setLedgerLoading] = useState(false)
  const [ledgerTotal, setLedgerTotal] = useState(0)
  const [ledgerOffset, setLedgerOffset] = useState(0)
  const [ledgerLimit] = useState(25)
  const [entryTypeFilter, setEntryTypeFilter] = useState('ALL')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  const [advances, setAdvances] = useState([])
  const [advancesLoading, setAdvancesLoading] = useState(false)

  useEffect(() => {
    if (!orgId || !creatorId) return
    resolvePayee()
  }, [orgId, creatorId])

  const resolvePayee = async () => {
    try {
      const res = await axios.get(`/api/royalty-processing/${orgId}/payees`)
      const payees = Array.isArray(res.data) ? res.data : res.data.payees || []
      const match = payees.find(p => Number(p.creator_id) === Number(creatorId))
      if (match) {
        setPayeeId(match.id)
      }
    } catch (err) {
      console.error('Failed to resolve payee:', err)
    } finally {
      setPayeeResolved(true)
    }
  }

  const loadLedger = useCallback(async () => {
    if (!payeeId) return
    setLedgerLoading(true)
    try {
      const params = { offset: ledgerOffset, limit: ledgerLimit }
      if (entryTypeFilter !== 'ALL') params.entry_type = entryTypeFilter
      if (dateFrom) params.date_from = dateFrom
      if (dateTo) params.date_to = dateTo
      const res = await axios.get(`/api/royalty-processing/${orgId}/payees/${payeeId}/ledger`, { params })
      const data = res.data
      setLedgerEntries(Array.isArray(data) ? data : data.entries || data.items || [])
      setLedgerTotal(data.total || data.count || (Array.isArray(data) ? data.length : 0))
    } catch (err) {
      console.error('Failed to load ledger:', err)
      setLedgerEntries([])
    } finally {
      setLedgerLoading(false)
    }
  }, [orgId, payeeId, ledgerOffset, ledgerLimit, entryTypeFilter, dateFrom, dateTo])

  const loadAdvances = useCallback(async () => {
    if (!payeeId) return
    setAdvancesLoading(true)
    try {
      const res = await axios.get(`/api/royalty-processing/${orgId}/advances`, { params: { payee_id: payeeId } })
      setAdvances(Array.isArray(res.data) ? res.data : res.data.advances || [])
    } catch (err) {
      console.error('Failed to load advances:', err)
      setAdvances([])
    } finally {
      setAdvancesLoading(false)
    }
  }, [orgId, payeeId])

  useEffect(() => {
    if (activeSubTab === 'ledger' && payeeId) {
      loadLedger()
    }
  }, [activeSubTab, payeeId, loadLedger])

  useEffect(() => {
    if (activeSubTab === 'recoupment' && payeeId) {
      loadAdvances()
    }
  }, [activeSubTab, payeeId, loadAdvances])

  useEffect(() => {
    setLedgerOffset(0)
  }, [entryTypeFilter, dateFrom, dateTo])

  const subTabs = [
    { key: 'summary', label: 'Summary' },
    { key: 'processing', label: 'Processing' },
    { key: 'statements', label: 'Statements' },
    { key: 'earnings', label: 'Earnings' },
    { key: 'ledger', label: 'Ledger' },
    { key: 'money_out', label: 'Money Out' },
    { key: 'payables', label: 'Payables' },
    { key: 'fees', label: 'Fees & Advances' },
    { key: 'analytics', label: 'Analytics' },
    { key: 'recoupment', label: 'Recoupment' },
  ]

  return (
    <div className="space-y-6">
      <div className="flex space-x-1 bg-[#F5F7F4] rounded-xl p-1 overflow-x-auto">
        {subTabs.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveSubTab(tab.key)}
            className={`flex-1 px-3 py-2 rounded-xl text-sm font-medium transition-colors whitespace-nowrap ${
              activeSubTab === tab.key
                ? 'bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white shadow-sm'
                : 'text-[#7A8580] hover:text-[#3D4A44]'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeSubTab === 'summary' && (
        <SummarySubTab data={existingAccountingData} loading={accountingLoading} orgId={orgId} onRefresh={onRefresh} />
      )}

      {activeSubTab === 'processing' && (
        <CreatorProcessingSubTab orgId={orgId} creatorId={creatorId} />
      )}

      {activeSubTab === 'statements' && (
        <StatementsSubTab orgId={orgId} creatorId={creatorId} />
      )}

      {activeSubTab === 'earnings' && (
        <EarningsSubTab orgId={orgId} creatorId={creatorId} />
      )}

      {activeSubTab === 'ledger' && (
        !payeeResolved ? (
          <div className="text-center py-12 text-[#7A8580]">Resolving payee...</div>
        ) : !payeeId ? (
          <div className="bg-white/60 backdrop-blur-xl rounded-[14px] border border-[rgba(59,77,67,0.08)] p-8 text-center">
            <p className="text-[#7A8580]">No ledger data available. This creator does not have a payee profile yet.</p>
          </div>
        ) : (
          <LedgerSubTab
            entries={ledgerEntries}
            loading={ledgerLoading}
            total={ledgerTotal}
            offset={ledgerOffset}
            limit={ledgerLimit}
            entryTypeFilter={entryTypeFilter}
            dateFrom={dateFrom}
            dateTo={dateTo}
            onEntryTypeChange={setEntryTypeFilter}
            onDateFromChange={setDateFrom}
            onDateToChange={setDateTo}
            onOffsetChange={setLedgerOffset}
          />
        )
      )}

      {activeSubTab === 'money_out' && (
        <MoneyOutSubTab orgId={orgId} creatorId={creatorId} />
      )}

      {activeSubTab === 'payables' && (
        !payeeResolved ? (
          <div className="text-center py-12 text-[#7A8580]">Resolving payee...</div>
        ) : !payeeId ? (
          <div className="bg-white/60 backdrop-blur-xl rounded-[14px] border border-[rgba(59,77,67,0.08)] p-8 text-center">
            <p className="text-[#7A8580]">No payables data available. This creator does not have a payee profile yet.</p>
          </div>
        ) : (
          <CreatorPayablesSubTab orgId={orgId} payeeId={payeeId} />
        )
      )}

      {activeSubTab === 'fees' && (
        <FeesAdvancesSubTab orgId={orgId} creatorId={creatorId} />
      )}

      {activeSubTab === 'analytics' && (
        <div className="space-y-3">
          <div className="flex items-center gap-2 px-4 py-2 bg-[rgba(91,138,114,0.06)] rounded-xl border border-[rgba(91,138,114,0.1)]">
            <ChartBarIcon className="w-4 h-4 text-[#5B8A72]" />
            <span className="text-xs text-[#7A8580]">Showing organization-wide royalty analytics</span>
          </div>
          <RoyaltyAnalyticsDashboard orgId={orgId} />
        </div>
      )}

      {activeSubTab === 'recoupment' && (
        !payeeResolved ? (
          <div className="text-center py-12 text-[#7A8580]">Resolving payee...</div>
        ) : !payeeId ? (
          <div className="bg-white/60 backdrop-blur-xl rounded-[14px] border border-[rgba(59,77,67,0.08)] p-8 text-center">
            <p className="text-[#7A8580]">No recoupment data available. This creator does not have a payee profile yet.</p>
          </div>
        ) : (
          <RecoupmentSubTab advances={advances} loading={advancesLoading} />
        )
      )}
    </div>
  )
}

function SummarySubTab({ data, loading, orgId, onRefresh }) {
  const [confirmingId, setConfirmingId] = useState(null)

  if (loading) {
    return <div className="text-center py-12 text-[#7A8580]">Loading accounting data...</div>
  }
  if (!data) {
    return <div className="text-center py-12 text-[#7A8580]">No accounting data available</div>
  }

  const summary = data.summary || {}
  const contracts = data.contracts || []
  const cards = [
    { label: 'Total Royalties', value: formatDollars(summary.total_royalties_dollars), color: 'text-[#5B8A72]' },
    { label: 'Outstanding Advances', value: formatDollars(summary.outstanding_advances_dollars), color: 'text-[#C4956B]' },
    { label: 'Net Payable', value: formatDollars(summary.net_balance_dollars), color: summary.net_balance_cents >= 0 ? 'text-[#5B8A72]' : 'text-[#C47068]' },
  ]

  const hasContractFinancials = (summary.contract_incoming_pending_cents > 0 || summary.contract_outgoing_pending_cents > 0 ||
    summary.contract_incoming_confirmed_cents > 0 || summary.contract_outgoing_confirmed_cents > 0)

  const handleConfirmPayment = async (contractId) => {
    setConfirmingId(contractId)
    try {
      const token = localStorage.getItem('token')
      await axios.post(`/api/royalties/confirm-contract-payment/${orgId}/${contractId}`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (onRefresh) onRefresh()
    } catch (err) {
      console.error('Failed to confirm payment:', err)
    } finally {
      setConfirmingId(null)
    }
  }

  const recentTransactions = data.recent_transactions || data.payments || []

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {cards.map((card, i) => (
          <div key={i} className="bg-white/60 backdrop-blur-xl rounded-[14px] border border-[rgba(59,77,67,0.08)] p-5">
            <p className="text-xs text-[#7A8580] mb-1">{card.label}</p>
            <p className={`text-2xl font-bold ${card.color}`}>{card.value}</p>
          </div>
        ))}
      </div>

      {hasContractFinancials && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {summary.contract_incoming_pending_cents > 0 && (
            <div className="bg-white/60 backdrop-blur-xl rounded-[14px] border border-[rgba(59,77,67,0.08)] p-5">
              <p className="text-xs text-[#7A8580] mb-1">Pending Incoming (Contracts)</p>
              <p className="text-xl font-bold text-[#C4956B]">{formatDollars(summary.contract_incoming_pending_dollars)}</p>
            </div>
          )}
          {summary.contract_outgoing_pending_cents > 0 && (
            <div className="bg-white/60 backdrop-blur-xl rounded-[14px] border border-[rgba(59,77,67,0.08)] p-5">
              <p className="text-xs text-[#7A8580] mb-1">Pending Outgoing (Contracts)</p>
              <p className="text-xl font-bold text-[#C47068]">{formatDollars(summary.contract_outgoing_pending_dollars)}</p>
            </div>
          )}
          {summary.contract_incoming_confirmed_cents > 0 && (
            <div className="bg-white/60 backdrop-blur-xl rounded-[14px] border border-[rgba(59,77,67,0.08)] p-5">
              <p className="text-xs text-[#7A8580] mb-1">Confirmed Incoming (Contracts)</p>
              <p className="text-xl font-bold text-[#5B8A72]">{formatDollars(summary.contract_incoming_confirmed_dollars)}</p>
            </div>
          )}
          {summary.contract_outgoing_confirmed_cents > 0 && (
            <div className="bg-white/60 backdrop-blur-xl rounded-[14px] border border-[rgba(59,77,67,0.08)] p-5">
              <p className="text-xs text-[#7A8580] mb-1">Confirmed Outgoing (Contracts)</p>
              <p className="text-xl font-bold text-[#5B8A72]">{formatDollars(summary.contract_outgoing_confirmed_dollars)}</p>
            </div>
          )}
        </div>
      )}

      {contracts.length > 0 && (
        <div className="bg-white/60 backdrop-blur-xl rounded-[14px] border border-[rgba(59,77,67,0.08)]">
          <div className="px-6 py-4 border-b border-[rgba(59,77,67,0.08)]">
            <h3 className="font-semibold text-[#3D4A44]">Contract Obligations</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="border-b border-[rgba(59,77,67,0.08)]">
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Contract</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Type</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Direction</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-[#7A8580] uppercase">Advance</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-[#7A8580] uppercase">Recouped</th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-[#7A8580] uppercase">Status</th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-[#7A8580] uppercase">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[rgba(59,77,67,0.06)]">
                {contracts.map((c) => {
                  const isPending = c.advance_amount > 0 && !c.is_confirmed
                  return (
                    <tr key={c.id} className="hover:bg-[rgba(91,138,114,0.04)]">
                      <td className="px-6 py-3 text-sm font-medium text-[#3D4A44]">{c.title}</td>
                      <td className="px-6 py-3 text-sm text-[#7A8580]">{c.contract_type || '—'}</td>
                      <td className="px-6 py-3 text-sm">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                          c.payment_direction === 'OUTGOING' ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
                        }`}>
                          {c.payment_direction === 'OUTGOING' ? 'We Pay' : 'We Receive'}
                        </span>
                      </td>
                      <td className="px-6 py-3 text-sm text-right font-medium text-[#3D4A44]">
                        {formatDollars(c.advance_amount)}
                      </td>
                      <td className="px-6 py-3 text-sm text-right text-[#7A8580]">
                        {formatDollars(c.advance_recouped)}
                      </td>
                      <td className="px-6 py-3 text-center">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          isPending ? 'bg-amber-100 text-amber-700' : 'bg-green-100 text-green-700'
                        }`}>
                          {isPending ? 'Pending' : 'Confirmed'}
                        </span>
                      </td>
                      <td className="px-6 py-3 text-center">
                        {isPending ? (
                          <button
                            onClick={() => handleConfirmPayment(c.id)}
                            disabled={confirmingId === c.id}
                            className="px-3 py-1 text-xs font-medium rounded-lg bg-[#5B8A72] text-white hover:bg-[#4A7A62] disabled:opacity-50 transition-colors"
                          >
                            {confirmingId === c.id ? 'Confirming...' : 'Confirm Payment'}
                          </button>
                        ) : (
                          <span className="text-xs text-[#7A8580]">—</span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {recentTransactions.length > 0 && (
        <div className="bg-white/60 backdrop-blur-xl rounded-[14px] border border-[rgba(59,77,67,0.08)]">
          <div className="px-6 py-4 border-b border-[rgba(59,77,67,0.08)]">
            <h3 className="font-semibold text-[#3D4A44]">Recent Transactions</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="border-b border-[rgba(59,77,67,0.08)]">
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Date</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Description</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-[#7A8580] uppercase">Amount</th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-[#7A8580] uppercase">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[rgba(59,77,67,0.06)]">
                {recentTransactions.map((tx, i) => (
                  <tr key={tx.id || i} className="hover:bg-[rgba(91,138,114,0.04)]">
                    <td className="px-6 py-3 text-sm text-[#7A8580]">
                      {formatDate(tx.payment_date || tx.created_at || tx.date)}
                    </td>
                    <td className="px-6 py-3 text-sm text-[#3D4A44]">
                      {tx.description || tx.notes || tx.payment_method || '—'}
                    </td>
                    <td className="px-6 py-3 text-sm text-right font-medium text-[#3D4A44]">
                      {formatDollars(tx.amount_dollars || (tx.amount_cents ? tx.amount_cents / 100 : 0))}
                    </td>
                    <td className="px-6 py-3 text-center">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        tx.status === 'PAID' ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'
                      }`}>
                        {tx.status || 'PENDING'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

function StatementsSubTab({ orgId, creatorId }) {
  const [statements, setStatements] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedStatementId, setSelectedStatementId] = useState(null)
  const [showUpload, setShowUpload] = useState(false)
  const [uploadFile, setUploadFile] = useState(null)
  const [uploadSource, setUploadSource] = useState('')
  const [uploadSourceType, setUploadSourceType] = useState('')
  const [uploadPeriodStart, setUploadPeriodStart] = useState('')
  const [uploadPeriodEnd, setUploadPeriodEnd] = useState('')
  const [uploadCurrency, setUploadCurrency] = useState('USD')
  const [uploading, setUploading] = useState(false)

  const loadStatements = useCallback(async () => {
    if (!orgId) return
    try {
      let url = `/api/royalties/statements/${orgId}`
      if (creatorId) url += `?creator_id=${creatorId}`
      const res = await axios.get(url)
      setStatements(Array.isArray(res.data) ? res.data : res.data.statements || [])
    } catch (err) {
      console.error('Failed to load statements:', err)
    } finally {
      setLoading(false)
    }
  }, [orgId, creatorId])

  useEffect(() => { loadStatements() }, [loadStatements])

  const handleUpload = async () => {
    if (!uploadFile || !uploadSource) return
    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', uploadFile)
      formData.append('source_name', uploadSource)
      if (uploadSourceType) formData.append('source_type', uploadSourceType)
      if (uploadPeriodStart) formData.append('period_start', uploadPeriodStart)
      if (uploadPeriodEnd) formData.append('period_end', uploadPeriodEnd)
      formData.append('currency', uploadCurrency)
      if (creatorId) formData.append('creator_id', creatorId)
      await axios.post(`/api/royalty-processing/${orgId}/statements/upload`, formData)
      setShowUpload(false)
      setUploadFile(null)
      setUploadSource('')
      setUploadSourceType('')
      setUploadPeriodStart('')
      setUploadPeriodEnd('')
      setUploadCurrency('USD')
      loadStatements()
    } catch (err) {
      console.error('Upload failed:', err)
      alert('Upload failed: ' + (err.response?.data?.detail || err.message))
    } finally {
      setUploading(false)
    }
  }

  const handleDelete = async (stmtId) => {
    if (!window.confirm('Delete this statement? This cannot be undone.')) return
    try {
      await axios.delete(`/api/royalties/statements/${orgId}/${stmtId}`)
      loadStatements()
    } catch (err) {
      console.error('Delete failed:', err)
    }
  }

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
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-[#3D4A44]">Royalty Statements</h3>
        <button
          onClick={() => setShowUpload(!showUpload)}
          className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-xl hover:shadow-[0px_4px_12px_rgba(91,138,114,0.3)] transition-all text-sm font-medium"
        >
          <ArrowUpTrayIcon className="w-4 h-4" /> Upload Statement
        </button>
      </div>

      {showUpload && (
        <div className="bg-white/60 backdrop-blur-xl rounded-[14px] border border-[rgba(59,77,67,0.08)] p-5 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-[#7A8580] mb-1">Source Name *</label>
              <input type="text" value={uploadSource} onChange={(e) => setUploadSource(e.target.value)} className={inputClass} placeholder="e.g., DistroKid, BMI" />
            </div>
            <div>
              <label className="block text-xs text-[#7A8580] mb-1">Source Type</label>
              <select value={uploadSourceType} onChange={(e) => setUploadSourceType(e.target.value)} className={inputClass}>
                {SOURCE_TYPE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-[#7A8580] mb-1">Period Start</label>
              <input type="date" value={uploadPeriodStart} onChange={(e) => setUploadPeriodStart(e.target.value)} className={inputClass} />
            </div>
            <div>
              <label className="block text-xs text-[#7A8580] mb-1">Period End</label>
              <input type="date" value={uploadPeriodEnd} onChange={(e) => setUploadPeriodEnd(e.target.value)} className={inputClass} />
            </div>
            <div>
              <label className="block text-xs text-[#7A8580] mb-1">Currency</label>
              <select value={uploadCurrency} onChange={(e) => setUploadCurrency(e.target.value)} className={inputClass}>
                {['USD', 'EUR', 'GBP', 'CAD', 'AUD', 'JPY'].map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-[#7A8580] mb-1">File *</label>
              <input type="file" accept=".csv,.xlsx,.xls,.pdf" onChange={(e) => setUploadFile(e.target.files[0])} className={inputClass} />
            </div>
          </div>
          <div className="flex items-center gap-3 pt-2">
            <button onClick={handleUpload} disabled={!uploadFile || !uploadSource || uploading} className="px-4 py-2 bg-[#5B8A72] text-white rounded-lg text-sm font-medium hover:bg-[#4A7A62] disabled:opacity-50 transition-colors">
              {uploading ? 'Uploading...' : 'Upload & Auto-Match'}
            </button>
            <button onClick={() => setShowUpload(false)} className="px-4 py-2 text-[#7A8580] hover:text-[#3D4A44] text-sm transition-colors">Cancel</button>
          </div>
        </div>
      )}

      <div className="bg-white/60 backdrop-blur-xl rounded-[14px] border border-[rgba(59,77,67,0.08)]">
        {loading ? (
          <div className="text-center py-12 text-[#7A8580]">Loading statements...</div>
        ) : statements.length === 0 ? (
          <div className="text-center py-12">
            <DocumentTextIcon className="w-12 h-12 text-[#7A8580] mx-auto mb-3" />
            <p className="text-[#7A8580]">No statements found for this client</p>
            <p className="text-xs text-[#7A8580] mt-1">Upload a royalty statement to get started</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="border-b border-[rgba(59,77,67,0.08)]">
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Source</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Period</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-[#7A8580] uppercase">Revenue</th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-[#7A8580] uppercase">Lines</th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-[#7A8580] uppercase">Matched</th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-[#7A8580] uppercase">Status</th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-[#7A8580] uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[rgba(59,77,67,0.06)]">
                {statements.map(stmt => {
                  const colors = STATEMENT_STATUS_COLORS[stmt.status] || { bg: 'bg-gray-100', text: 'text-gray-700' }
                  return (
                    <tr key={stmt.id} className="hover:bg-[rgba(91,138,114,0.04)]">
                      <td className="px-6 py-3 text-sm font-medium text-[#3D4A44]">{stmt.source_name || stmt.source || '—'}</td>
                      <td className="px-6 py-3 text-sm text-[#7A8580]">
                        {stmt.period_start ? `${formatDate(stmt.period_start)} – ${formatDate(stmt.period_end)}` : formatDate(stmt.created_at)}
                      </td>
                      <td className="px-6 py-3 text-sm text-right font-medium text-[#3D4A44]">
                        {formatCents(stmt.total_revenue_cents)}
                      </td>
                      <td className="px-6 py-3 text-sm text-center text-[#7A8580]">{stmt.total_lines || stmt.transaction_count || 0}</td>
                      <td className="px-6 py-3 text-sm text-center text-[#7A8580]">{stmt.matched_lines || stmt.matched_count || 0}</td>
                      <td className="px-6 py-3 text-center">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colors.bg} ${colors.text}`}>
                          {(stmt.status || '').replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td className="px-6 py-3 text-center">
                        <div className="flex items-center justify-center gap-2">
                          <button onClick={() => setSelectedStatementId(stmt.id)} className="p-1.5 text-[#5B8A72] hover:bg-[rgba(91,138,114,0.1)] rounded-lg transition-colors" title="View Details">
                            <EyeIcon className="w-4 h-4" />
                          </button>
                          <button onClick={() => handleDelete(stmt.id)} className="p-1.5 text-[#C47068] hover:bg-[rgba(196,112,104,0.1)] rounded-lg transition-colors" title="Delete">
                            <TrashIcon className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

function EarningsSubTab({ orgId, creatorId }) {
  const [earnings, setEarnings] = useState([])
  const [loading, setLoading] = useState(true)
  const [summary, setSummary] = useState(null)

  useEffect(() => {
    if (!orgId) return
    loadEarnings()
  }, [orgId, creatorId])

  const loadEarnings = async () => {
    try {
      const params = {}
      if (creatorId) params.creator_id = creatorId
      const res = await axios.get(`/api/royalties/earnings/${orgId}`, { params })
      const data = res.data
      if (Array.isArray(data)) {
        setEarnings(data)
      } else {
        setEarnings(data.earnings || data.items || [])
        if (data.summary) setSummary(data.summary)
      }
    } catch (err) {
      console.error('Failed to load earnings:', err)
      setEarnings([])
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <div className="text-center py-12 text-[#7A8580]">Loading earnings...</div>

  return (
    <div className="space-y-4">
      {summary && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-white/60 backdrop-blur-xl rounded-[14px] border border-[rgba(59,77,67,0.08)] p-5">
            <p className="text-xs text-[#7A8580] mb-1">Total Earnings</p>
            <p className="text-2xl font-bold text-[#5B8A72]">{formatCents(summary.total_cents)}</p>
          </div>
          <div className="bg-white/60 backdrop-blur-xl rounded-[14px] border border-[rgba(59,77,67,0.08)] p-5">
            <p className="text-xs text-[#7A8580] mb-1">Allocated</p>
            <p className="text-2xl font-bold text-[#3D4A44]">{formatCents(summary.allocated_cents)}</p>
          </div>
          <div className="bg-white/60 backdrop-blur-xl rounded-[14px] border border-[rgba(59,77,67,0.08)] p-5">
            <p className="text-xs text-[#7A8580] mb-1">Unallocated</p>
            <p className="text-2xl font-bold text-[#C4956B]">{formatCents(summary.unallocated_cents)}</p>
          </div>
        </div>
      )}

      <div className="bg-white/60 backdrop-blur-xl rounded-[14px] border border-[rgba(59,77,67,0.08)]">
        {earnings.length === 0 ? (
          <div className="text-center py-12">
            <CurrencyDollarIcon className="w-12 h-12 text-[#7A8580] mx-auto mb-3" />
            <p className="text-[#7A8580]">No earnings data found for this client</p>
            <p className="text-xs text-[#7A8580] mt-1">Earnings appear after statements are processed</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="border-b border-[rgba(59,77,67,0.08)]">
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Song</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Source</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Period</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-[#7A8580] uppercase">Revenue</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-[#7A8580] uppercase">Quantity</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[rgba(59,77,67,0.06)]">
                {earnings.slice(0, 100).map((e, i) => (
                  <tr key={e.id || i} className="hover:bg-[rgba(91,138,114,0.04)]">
                    <td className="px-6 py-3 text-sm font-medium text-[#3D4A44]">{e.track_title || e.song_title || '—'}</td>
                    <td className="px-6 py-3 text-sm text-[#7A8580]">{e.source_name || e.platform || '—'}</td>
                    <td className="px-6 py-3 text-sm text-[#7A8580]">{e.period || formatDate(e.period_start)}</td>
                    <td className="px-6 py-3 text-sm text-right font-medium text-[#5B8A72]">{e.revenue_cents != null ? formatCents(e.revenue_cents) : formatDollars(e.revenue)}</td>
                    <td className="px-6 py-3 text-sm text-right text-[#7A8580]">{(e.quantity || 0).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

function LedgerSubTab({ entries, loading, total, offset, limit, entryTypeFilter, dateFrom, dateTo, onEntryTypeChange, onDateFromChange, onDateToChange, onOffsetChange }) {
  return (
    <div className="space-y-4">
      <div className="bg-white/60 backdrop-blur-xl rounded-[14px] border border-[rgba(59,77,67,0.08)] p-4">
        <div className="flex flex-wrap items-center gap-3">
          <div>
            <label className="block text-xs text-[#7A8580] mb-1">Entry Type</label>
            <select
              value={entryTypeFilter}
              onChange={(e) => onEntryTypeChange(e.target.value)}
              className="border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 bg-white text-[#3D4A44] text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
            >
              {ENTRY_TYPES.map(t => (
                <option key={t} value={t}>{t === 'ALL' ? 'All Types' : t.replace(/_/g, ' ')}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-[#7A8580] mb-1">From</label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => onDateFromChange(e.target.value)}
              className="border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 bg-white text-[#3D4A44] text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-xs text-[#7A8580] mb-1">To</label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => onDateToChange(e.target.value)}
              className="border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 bg-white text-[#3D4A44] text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
            />
          </div>
        </div>
      </div>

      <div className="bg-white/60 backdrop-blur-xl rounded-[14px] border border-[rgba(59,77,67,0.08)]">
        {loading ? (
          <div className="text-center py-12 text-[#7A8580]">Loading ledger...</div>
        ) : entries.length === 0 ? (
          <div className="text-center py-12 text-[#7A8580]">No ledger entries found</div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="min-w-full">
                <thead>
                  <tr className="border-b border-[rgba(59,77,67,0.08)]">
                    <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Date</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Type</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Source</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Song</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-[#7A8580] uppercase">Amount</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Memo</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[rgba(59,77,67,0.06)]">
                  {entries.map((entry, i) => {
                    const amountCents = entry.amount_cents || entry.amount || 0
                    const amountDollars = entry.amount_dollars != null ? entry.amount_dollars : amountCents / 100
                    const isPositive = amountDollars >= 0
                    return (
                      <tr key={entry.id || i} className="hover:bg-[rgba(91,138,114,0.04)]">
                        <td className="px-6 py-3 text-sm text-[#7A8580]">{formatDate(entry.entry_date || entry.created_at)}</td>
                        <td className="px-6 py-3">
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${ENTRY_TYPE_COLORS[entry.entry_type] || 'bg-gray-100 text-gray-700'}`}>
                            {(entry.entry_type || '').replace(/_/g, ' ')}
                          </span>
                        </td>
                        <td className="px-6 py-3 text-sm text-[#3D4A44]">{entry.source_name || entry.source || '—'}</td>
                        <td className="px-6 py-3 text-sm text-[#3D4A44]">{entry.song_title || entry.song_name || '—'}</td>
                        <td className={`px-6 py-3 text-sm text-right font-medium ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
                          {isPositive ? '+' : ''}{formatDollars(amountDollars)}
                        </td>
                        <td className="px-6 py-3 text-sm text-[#7A8580] max-w-[200px] truncate">{entry.memo || entry.notes || '—'}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
            <div className="px-6 py-4 border-t border-[rgba(59,77,67,0.08)] flex items-center justify-between">
              <span className="text-sm text-[#7A8580]">
                Showing {offset + 1}–{Math.min(offset + limit, total || entries.length)} of {total || entries.length}
              </span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => onOffsetChange(Math.max(0, offset - limit))}
                  disabled={offset === 0}
                  className="px-4 py-2 rounded-xl text-sm font-medium border border-[rgba(59,77,67,0.12)] text-[#3D4A44] disabled:opacity-40 hover:bg-[#F5F7F4] transition-colors"
                >
                  Previous
                </button>
                <button
                  onClick={() => onOffsetChange(offset + limit)}
                  disabled={offset + limit >= (total || entries.length)}
                  className="px-4 py-2 rounded-xl text-sm font-medium border border-[rgba(59,77,67,0.12)] text-[#3D4A44] disabled:opacity-40 hover:bg-[#F5F7F4] transition-colors"
                >
                  Next
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

function RecoupmentSubTab({ advances, loading }) {
  if (loading) {
    return <div className="text-center py-12 text-[#7A8580]">Loading recoupment data...</div>
  }
  if (advances.length === 0) {
    return (
      <div className="bg-white/60 backdrop-blur-xl rounded-[14px] border border-[rgba(59,77,67,0.08)] p-8 text-center">
        <p className="text-[#7A8580]">No advances found for this creator.</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {advances.map((adv, i) => {
        const principal = adv.principal_amount_cents ? adv.principal_amount_cents / 100 : (adv.principal_amount || 0)
        const outstanding = adv.outstanding_balance_cents ? adv.outstanding_balance_cents / 100 : (adv.outstanding_balance || 0)
        const recouped = principal - outstanding
        const pct = principal > 0 ? Math.min((recouped / principal) * 100, 100) : 0

        return (
          <div key={adv.id || i} className="bg-white/60 backdrop-blur-xl rounded-[14px] border border-[rgba(59,77,67,0.08)] p-5">
            <div className="flex items-start justify-between mb-3">
              <div>
                <h4 className="font-semibold text-[#3D4A44]">{adv.advance_name || adv.name || 'Advance'}</h4>
                {adv.contract_name && (
                  <p className="text-xs text-[#7A8580] mt-0.5">Contract: {adv.contract_name}</p>
                )}
              </div>
              <div className="flex items-center gap-2">
                {adv.recoupment_pool && (
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${POOL_COLORS[adv.recoupment_pool] || 'bg-gray-100 text-gray-700'}`}>
                    {adv.recoupment_pool}
                  </span>
                )}
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4 mb-3">
              <div>
                <p className="text-xs text-[#7A8580]">Principal</p>
                <p className="text-sm font-semibold text-[#3D4A44]">{formatDollars(principal)}</p>
              </div>
              <div>
                <p className="text-xs text-[#7A8580]">Recouped</p>
                <p className="text-sm font-semibold text-[#5B8A72]">{formatDollars(recouped)}</p>
              </div>
              <div>
                <p className="text-xs text-[#7A8580]">Outstanding</p>
                <p className="text-sm font-semibold text-[#C4956B]">{formatDollars(outstanding)}</p>
              </div>
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
  )
}

function CreatorPayablesSubTab({ orgId, payeeId }) {
  const [payableData, setPayableData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!orgId || !payeeId) return
    loadPayableData()
  }, [orgId, payeeId])

  const loadPayableData = async () => {
    try {
      const res = await axios.get(`/api/royalty-processing/${orgId}/payables`)
      const allPayables = Array.isArray(res.data) ? res.data : res.data.payables || []
      const match = allPayables.find(p => Number(p.payee_id) === Number(payeeId) || Number(p.id) === Number(payeeId))
      setPayableData(match || null)
    } catch (err) {
      console.error('Failed to load payables:', err)
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <div className="text-center py-12 text-[#7A8580]">Loading payables...</div>

  if (!payableData) {
    return (
      <div className="bg-white/60 backdrop-blur-xl rounded-[14px] border border-[rgba(59,77,67,0.08)] p-8 text-center">
        <BanknotesIcon className="w-12 h-12 text-[#7A8580] mx-auto mb-3" />
        <p className="text-[#7A8580]">No payable balance found for this client</p>
        <p className="text-xs text-[#7A8580] mt-1">Payables are created after royalty statements are processed</p>
      </div>
    )
  }

  const balance = payableData.balance || {}
  const cards = [
    { label: 'Total Earned', value: formatCents(balance.total_earned_cents || payableData.total_earned_cents), color: 'text-[#5B8A72]' },
    { label: 'Total Paid', value: formatCents(balance.total_paid_cents || payableData.total_paid_cents), color: 'text-[#3D4A44]' },
    { label: 'Current Balance', value: formatCents(balance.current_balance_cents || payableData.current_balance_cents), color: 'text-[#C4956B]' },
  ]

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {cards.map((card, i) => (
          <div key={i} className="bg-white/60 backdrop-blur-xl rounded-[14px] border border-[rgba(59,77,67,0.08)] p-5">
            <p className="text-xs text-[#7A8580] mb-1">{card.label}</p>
            <p className={`text-2xl font-bold ${card.color}`}>{card.value}</p>
          </div>
        ))}
      </div>

      <div className="bg-white/60 backdrop-blur-xl rounded-[14px] border border-[rgba(59,77,67,0.08)] p-5">
        <h4 className="font-semibold text-[#3D4A44] mb-3">Payee Details</h4>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-xs text-[#7A8580]">Name</p>
            <p className="text-[#3D4A44] font-medium">{payableData.creator_name || payableData.company_name || '—'}</p>
          </div>
          <div>
            <p className="text-xs text-[#7A8580]">Type</p>
            <p className="text-[#3D4A44]">{payableData.payee_type || '—'}</p>
          </div>
          {payableData.payment_method && (
            <div>
              <p className="text-xs text-[#7A8580]">Payment Method</p>
              <p className="text-[#3D4A44]">{payableData.payment_method}</p>
            </div>
          )}
          {payableData.payment_details && (
            <div>
              <p className="text-xs text-[#7A8580]">Payment Details</p>
              <p className="text-[#3D4A44]">{payableData.payment_details}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function CreatorProcessingSubTab({ orgId, creatorId }) {
  const [statements, setStatements] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedStatementId, setSelectedStatementId] = useState(null)
  const [showUpload, setShowUpload] = useState(false)
  const [uploadFile, setUploadFile] = useState(null)
  const [uploadForm, setUploadForm] = useState({ source_name: '', source_type: '', period_start: '', period_end: '', currency: 'USD' })
  const [uploading, setUploading] = useState(false)
  const [statusFilter, setStatusFilter] = useState('')

  const loadStatements = useCallback(async () => {
    if (!orgId) return
    try {
      let url = `/api/royalties/statements/${orgId}`
      if (creatorId) url += `?creator_id=${creatorId}`
      const res = await axios.get(url)
      setStatements(Array.isArray(res.data) ? res.data : res.data.statements || [])
    } catch (err) {
      console.error('Failed to load statements:', err)
    } finally {
      setLoading(false)
    }
  }, [orgId, creatorId])

  useEffect(() => { loadStatements() }, [loadStatements])

  const handleUpload = async () => {
    if (!uploadFile || !uploadForm.source_name) return
    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', uploadFile)
      formData.append('source_name', uploadForm.source_name)
      if (uploadForm.source_type) formData.append('source_type', uploadForm.source_type)
      if (uploadForm.period_start) formData.append('period_start', uploadForm.period_start)
      if (uploadForm.period_end) formData.append('period_end', uploadForm.period_end)
      formData.append('currency', uploadForm.currency)
      if (creatorId) formData.append('creator_id', creatorId)
      await axios.post(`/api/royalty-processing/${orgId}/statements/upload`, formData)
      setShowUpload(false)
      setUploadFile(null)
      setUploadForm({ source_name: '', source_type: '', period_start: '', period_end: '', currency: 'USD' })
      loadStatements()
    } catch (err) {
      console.error('Upload failed:', err)
      alert('Upload failed: ' + (err.response?.data?.detail || err.message))
    } finally {
      setUploading(false)
    }
  }

  const handleRematch = async (stmtId) => {
    try {
      await axios.post(`/api/royalties/statements/${orgId}/${stmtId}/rematch`)
      loadStatements()
    } catch (err) {
      console.error('Rematch failed:', err)
    }
  }

  const handleCalculate = async (stmtId) => {
    try {
      await axios.post(`/api/royalties/calculate/${orgId}/${stmtId}`)
      loadStatements()
    } catch (err) {
      console.error('Calculate failed:', err)
    }
  }

  if (selectedStatementId) {
    return (
      <StatementDetailView
        orgId={orgId}
        statementId={selectedStatementId}
        onBack={() => { setSelectedStatementId(null); loadStatements() }}
      />
    )
  }

  const STATUS_OPTIONS = [
    { key: '', label: 'All' },
    { key: 'UPLOADED', label: 'Uploaded' },
    { key: 'PARTIALLY_MATCHED', label: 'Partially Matched' },
    { key: 'REVIEW_REQUIRED', label: 'Review Required' },
    { key: 'FULLY_MATCHED', label: 'Fully Matched' },
    { key: 'PROCESSED', label: 'Processed' },
  ]

  const filteredStatements = statusFilter
    ? statements.filter(s => s.status === statusFilter)
    : statements

  const inputClass = "w-full border border-[rgba(59,77,67,0.15)] rounded-lg px-3 py-2 text-sm text-[#3D4A44] bg-white focus:outline-none focus:ring-2 focus:ring-[#5B8A72]/30"

  return (
    <div className="space-y-6">
      <ProcessingInboxPanel orgId={orgId} onSelectStatement={(status) => setStatusFilter(status)} />

      <div className="bg-white/80 backdrop-blur-xl rounded-[18px] shadow-am p-6 border border-[rgba(59,77,67,0.08)]">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-[#3D4A44]">Upload & Auto-Match</h3>
          <button
            onClick={() => setShowUpload(!showUpload)}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-xl hover:shadow-[0px_4px_12px_rgba(91,138,114,0.3)] transition-all text-sm font-medium"
          >
            <ArrowUpTrayIcon className="w-4 h-4" /> Upload & Auto-Match
          </button>
        </div>

        {showUpload && (
          <div className="mt-4 space-y-4 border-t border-[rgba(59,77,67,0.08)] pt-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-[#7A8580] mb-1">Source Name *</label>
                <input type="text" value={uploadForm.source_name} onChange={(e) => setUploadForm(prev => ({ ...prev, source_name: e.target.value }))} className={inputClass} placeholder="e.g., DistroKid, BMI" />
              </div>
              <div>
                <label className="block text-xs text-[#7A8580] mb-1">Source Type</label>
                <select value={uploadForm.source_type} onChange={(e) => setUploadForm(prev => ({ ...prev, source_type: e.target.value }))} className={inputClass}>
                  {SOURCE_TYPE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs text-[#7A8580] mb-1">Period Start</label>
                <input type="date" value={uploadForm.period_start} onChange={(e) => setUploadForm(prev => ({ ...prev, period_start: e.target.value }))} className={inputClass} />
              </div>
              <div>
                <label className="block text-xs text-[#7A8580] mb-1">Period End</label>
                <input type="date" value={uploadForm.period_end} onChange={(e) => setUploadForm(prev => ({ ...prev, period_end: e.target.value }))} className={inputClass} />
              </div>
              <div>
                <label className="block text-xs text-[#7A8580] mb-1">Currency</label>
                <select value={uploadForm.currency} onChange={(e) => setUploadForm(prev => ({ ...prev, currency: e.target.value }))} className={inputClass}>
                  {['USD', 'EUR', 'GBP', 'CAD', 'AUD', 'JPY'].map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs text-[#7A8580] mb-1">File *</label>
                <input type="file" accept=".csv,.xlsx,.xls,.pdf" onChange={(e) => setUploadFile(e.target.files[0])} className={inputClass} />
              </div>
            </div>
            <div className="flex items-center gap-3 pt-2">
              <button onClick={handleUpload} disabled={!uploadFile || !uploadForm.source_name || uploading} className="px-4 py-2 bg-[#5B8A72] text-white rounded-lg text-sm font-medium hover:bg-[#4A7A62] disabled:opacity-50 transition-colors">
                {uploading ? 'Uploading...' : 'Upload & Process'}
              </button>
              <button onClick={() => setShowUpload(false)} className="px-4 py-2 text-[#7A8580] hover:text-[#3D4A44] text-sm transition-colors">Cancel</button>
            </div>
          </div>
        )}
      </div>

      <div className="flex items-center gap-2 flex-wrap">
        {STATUS_OPTIONS.map(opt => (
          <button
            key={opt.key}
            onClick={() => setStatusFilter(opt.key)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              statusFilter === opt.key
                ? 'bg-[rgba(91,138,114,0.15)] text-[#5B8A72] border border-[rgba(91,138,114,0.3)]'
                : 'text-[#7A8580] hover:bg-[rgba(91,138,114,0.06)] border border-transparent'
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>

      <div className="bg-white/60 backdrop-blur-xl rounded-[14px] border border-[rgba(59,77,67,0.08)]">
        {loading ? (
          <div className="text-center py-12 text-[#7A8580]">Loading processing pipeline...</div>
        ) : filteredStatements.length === 0 ? (
          <div className="text-center py-12">
            <ArrowPathIcon className="w-12 h-12 text-[#7A8580] mx-auto mb-3" />
            <p className="text-[#7A8580]">No statements in the processing pipeline</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="border-b border-[rgba(59,77,67,0.08)]">
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Source</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Period</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-[#7A8580] uppercase">Revenue</th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-[#7A8580] uppercase">Matched</th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-[#7A8580] uppercase">Status</th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-[#7A8580] uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[rgba(59,77,67,0.06)]">
                {filteredStatements.map(stmt => {
                  const colors = STATEMENT_STATUS_COLORS[stmt.status] || { bg: 'bg-gray-100', text: 'text-gray-700' }
                  const matchRate = stmt.total_lines > 0 ? Math.round(((stmt.matched_lines || 0) / stmt.total_lines) * 100) : 0
                  return (
                    <tr key={stmt.id} className="hover:bg-[rgba(91,138,114,0.04)]">
                      <td className="px-6 py-3 text-sm font-medium text-[#3D4A44]">{stmt.source_name || '—'}</td>
                      <td className="px-6 py-3 text-sm text-[#7A8580]">
                        {stmt.period_start ? `${formatDate(stmt.period_start)} – ${formatDate(stmt.period_end)}` : formatDate(stmt.created_at)}
                      </td>
                      <td className="px-6 py-3 text-sm text-right font-medium text-[#3D4A44]">{formatCents(stmt.total_revenue_cents)}</td>
                      <td className="px-6 py-3 text-center">
                        <div className="flex items-center justify-center gap-2">
                          <div className="w-16 bg-[#EEF1EC] rounded-full h-1.5">
                            <div className="h-1.5 rounded-full bg-[#5B8A72]" style={{ width: `${matchRate}%` }} />
                          </div>
                          <span className="text-xs text-[#7A8580]">{matchRate}%</span>
                        </div>
                      </td>
                      <td className="px-6 py-3 text-center">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colors.bg} ${colors.text}`}>
                          {(stmt.status || '').replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td className="px-6 py-3 text-center">
                        <div className="flex items-center justify-center gap-1">
                          <button onClick={() => setSelectedStatementId(stmt.id)} className="p-1.5 text-[#5B8A72] hover:bg-[rgba(91,138,114,0.1)] rounded-lg transition-colors" title="Review">
                            <EyeIcon className="w-4 h-4" />
                          </button>
                          <button onClick={() => handleRematch(stmt.id)} className="p-1.5 text-[#5A8A9A] hover:bg-[rgba(90,138,154,0.1)] rounded-lg transition-colors" title="Re-match">
                            <ArrowPathIcon className="w-4 h-4" />
                          </button>
                          <button onClick={() => handleCalculate(stmt.id)} className="p-1.5 text-[#C4956B] hover:bg-[rgba(196,149,107,0.1)] rounded-lg transition-colors" title="Calculate Royalties">
                            <CurrencyDollarIcon className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

function MoneyOutSubTab({ orgId, creatorId }) {
  const [expenses, setExpenses] = useState([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [creating, setCreating] = useState(false)
  const [form, setForm] = useState({
    category: 'OTHER', description: '', amount: '', expense_date: '', payment_method: '', notes: ''
  })

  const EXPENSE_CATEGORIES = ['RECORDING', 'MARKETING', 'DISTRIBUTION', 'LEGAL', 'MANAGEMENT_FEE', 'ADVANCE', 'SYNC_FEE', 'OTHER']
  const EXPENSE_STATUS_COLORS = {
    PENDING: 'bg-amber-100 text-amber-700',
    APPROVED: 'bg-blue-100 text-blue-700',
    PAID: 'bg-green-100 text-green-700',
    CANCELLED: 'bg-red-100 text-red-700',
  }

  const loadExpenses = useCallback(async () => {
    if (!orgId) return
    try {
      const res = await axios.get(`/api/expenses/org/${orgId}`)
      const allExpenses = Array.isArray(res.data) ? res.data : []
      setExpenses(creatorId ? allExpenses.filter(e => Number(e.creator_id) === Number(creatorId)) : allExpenses)
    } catch (err) {
      console.error('Failed to load expenses:', err)
    } finally {
      setLoading(false)
    }
  }, [orgId, creatorId])

  useEffect(() => { loadExpenses() }, [loadExpenses])

  const handleCreate = async () => {
    if (!form.description || !form.amount) return
    setCreating(true)
    try {
      await axios.post(`/api/expenses/org/${orgId}`, {
        category: form.category,
        description: form.description,
        amount_cents: Math.round(parseFloat(form.amount) * 100),
        creator_id: creatorId ? Number(creatorId) : null,
        expense_date: form.expense_date || null,
        payment_method: form.payment_method || null,
        notes: form.notes || null,
      })
      setShowCreate(false)
      setForm({ category: 'OTHER', description: '', amount: '', expense_date: '', payment_method: '', notes: '' })
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
    if (!window.confirm('Delete this expense?')) return
    try {
      await axios.delete(`/api/expenses/${expenseId}`)
      loadExpenses()
    } catch (err) {
      console.error('Failed to delete expense:', err)
    }
  }

  const totalExpenses = expenses.reduce((sum, e) => sum + (e.amount_cents || 0), 0)
  const inputClass = "w-full border border-[rgba(59,77,67,0.15)] rounded-lg px-3 py-2 text-sm text-[#3D4A44] bg-white focus:outline-none focus:ring-2 focus:ring-[#5B8A72]/30"

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h3 className="text-lg font-semibold text-[#3D4A44]">Expenses</h3>
          <span className="text-sm text-[#7A8580]">Total: {formatCents(totalExpenses)}</span>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-xl text-sm font-medium hover:shadow-md transition-all"
        >
          <ArrowUpTrayIcon className="w-4 h-4" /> Add Expense
        </button>
      </div>

      {showCreate && (
        <div className="bg-white/60 backdrop-blur-xl rounded-[14px] border border-[rgba(59,77,67,0.08)] p-5 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-[#7A8580] mb-1">Category</label>
              <select value={form.category} onChange={(e) => setForm(prev => ({ ...prev, category: e.target.value }))} className={inputClass}>
                {EXPENSE_CATEGORIES.map(c => <option key={c} value={c}>{c.replace(/_/g, ' ')}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-[#7A8580] mb-1">Amount ($) *</label>
              <input type="number" step="0.01" value={form.amount} onChange={(e) => setForm(prev => ({ ...prev, amount: e.target.value }))} className={inputClass} placeholder="0.00" />
            </div>
            <div className="sm:col-span-2">
              <label className="block text-xs text-[#7A8580] mb-1">Description *</label>
              <input type="text" value={form.description} onChange={(e) => setForm(prev => ({ ...prev, description: e.target.value }))} className={inputClass} placeholder="Expense description" />
            </div>
            <div>
              <label className="block text-xs text-[#7A8580] mb-1">Date</label>
              <input type="date" value={form.expense_date} onChange={(e) => setForm(prev => ({ ...prev, expense_date: e.target.value }))} className={inputClass} />
            </div>
            <div>
              <label className="block text-xs text-[#7A8580] mb-1">Payment Method</label>
              <input type="text" value={form.payment_method} onChange={(e) => setForm(prev => ({ ...prev, payment_method: e.target.value }))} className={inputClass} placeholder="e.g., Wire, Check" />
            </div>
          </div>
          <div className="flex gap-3">
            <button onClick={handleCreate} disabled={!form.description || !form.amount || creating} className="px-4 py-2 bg-[#5B8A72] text-white rounded-lg text-sm font-medium hover:bg-[#4A7A62] disabled:opacity-50 transition-colors">
              {creating ? 'Creating...' : 'Create Expense'}
            </button>
            <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-[#7A8580] hover:text-[#3D4A44] text-sm transition-colors">Cancel</button>
          </div>
        </div>
      )}

      <div className="bg-white/60 backdrop-blur-xl rounded-[14px] border border-[rgba(59,77,67,0.08)]">
        {loading ? (
          <div className="text-center py-12 text-[#7A8580]">Loading expenses...</div>
        ) : expenses.length === 0 ? (
          <div className="text-center py-12">
            <ArrowUpTrayIcon className="w-12 h-12 text-[#7A8580] mx-auto mb-3" />
            <p className="text-[#7A8580]">No expenses recorded for this client</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="border-b border-[rgba(59,77,67,0.08)]">
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Date</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Category</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Description</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-[#7A8580] uppercase">Amount</th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-[#7A8580] uppercase">Status</th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-[#7A8580] uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[rgba(59,77,67,0.06)]">
                {expenses.map(exp => (
                  <tr key={exp.id} className="hover:bg-[rgba(91,138,114,0.04)]">
                    <td className="px-6 py-3 text-sm text-[#7A8580]">{formatDate(exp.expense_date || exp.created_at)}</td>
                    <td className="px-6 py-3 text-sm text-[#3D4A44]">{(exp.category || '').replace(/_/g, ' ')}</td>
                    <td className="px-6 py-3 text-sm text-[#3D4A44] max-w-[200px] truncate">{exp.description}</td>
                    <td className="px-6 py-3 text-sm text-right font-medium text-[#3D4A44]">{formatCents(exp.amount_cents)}</td>
                    <td className="px-6 py-3 text-center">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${EXPENSE_STATUS_COLORS[exp.status] || 'bg-gray-100 text-gray-700'}`}>
                        {exp.status || 'PENDING'}
                      </span>
                    </td>
                    <td className="px-6 py-3 text-center">
                      <div className="flex items-center justify-center gap-1">
                        {exp.status === 'PENDING' && (
                          <button onClick={() => handleUpdateStatus(exp.id, 'APPROVED')} className="px-2 py-1 text-xs text-[#5B8A72] hover:bg-[rgba(91,138,114,0.1)] rounded transition-colors">Approve</button>
                        )}
                        {exp.status === 'APPROVED' && (
                          <button onClick={() => handleUpdateStatus(exp.id, 'PAID')} className="px-2 py-1 text-xs text-[#5B8A72] hover:bg-[rgba(91,138,114,0.1)] rounded transition-colors">Mark Paid</button>
                        )}
                        <button onClick={() => handleDelete(exp.id)} className="p-1 text-[#C47068] hover:bg-[rgba(196,112,104,0.1)] rounded transition-colors">
                          <TrashIcon className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

function FeesAdvancesSubTab({ orgId, creatorId }) {
  const [fees, setFees] = useState([])
  const [advances, setAdvances] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeSection, setActiveSection] = useState('fees')
  const [showAddFee, setShowAddFee] = useState(false)
  const [showAddAdvance, setShowAddAdvance] = useState(false)
  const [feeForm, setFeeForm] = useState({ fee_type: 'MANAGEMENT_FEE', description: '', amount: '', fee_date: '', notes: '' })
  const [advanceForm, setAdvanceForm] = useState({ description: '', amount: '', advance_date: '', notes: '' })
  const [savingFee, setSavingFee] = useState(false)
  const [savingAdvance, setSavingAdvance] = useState(false)

  const FEE_TYPES = ['MANAGEMENT_FEE', 'DISTRIBUTION_FEE', 'ADMIN_FEE', 'SYNC_FEE', 'MECHANICAL_FEE', 'OTHER']

  const loadData = useCallback(async () => {
    if (!orgId) return
    try {
      const [feesRes, advancesRes] = await Promise.all([
        axios.get(`/api/royalties/fees/${orgId}`),
        axios.get(`/api/royalties/advances/${orgId}`)
      ])
      const allFees = Array.isArray(feesRes.data) ? feesRes.data : feesRes.data.fees || []
      const allAdvances = Array.isArray(advancesRes.data) ? advancesRes.data : advancesRes.data.advances || []
      setFees(creatorId ? allFees.filter(f => Number(f.creator_id) === Number(creatorId)) : allFees)
      setAdvances(creatorId ? allAdvances.filter(a => Number(a.creator_id) === Number(creatorId)) : allAdvances)
    } catch (err) {
      console.error('Failed to load fees/advances:', err)
    } finally {
      setLoading(false)
    }
  }, [orgId, creatorId])

  useEffect(() => { loadData() }, [loadData])

  const handleAddFee = async () => {
    if (!feeForm.description || !feeForm.amount) return
    setSavingFee(true)
    try {
      await axios.post(`/api/royalties/fees/${orgId}`, {
        fee_type: feeForm.fee_type,
        description: feeForm.description,
        amount_cents: Math.round(parseFloat(feeForm.amount) * 100),
        creator_id: creatorId ? Number(creatorId) : null,
        fee_date: feeForm.fee_date || null,
        notes: feeForm.notes || null,
      })
      setShowAddFee(false)
      setFeeForm({ fee_type: 'MANAGEMENT_FEE', description: '', amount: '', fee_date: '', notes: '' })
      loadData()
    } catch (err) {
      console.error('Failed to add fee:', err)
    } finally {
      setSavingFee(false)
    }
  }

  const handleAddAdvance = async () => {
    if (!advanceForm.description || !advanceForm.amount) return
    setSavingAdvance(true)
    try {
      await axios.post(`/api/royalties/advances/${orgId}`, {
        description: advanceForm.description,
        amount_cents: Math.round(parseFloat(advanceForm.amount) * 100),
        creator_id: creatorId ? Number(creatorId) : null,
        advance_date: advanceForm.advance_date || null,
        notes: advanceForm.notes || null,
      })
      setShowAddAdvance(false)
      setAdvanceForm({ description: '', amount: '', advance_date: '', notes: '' })
      loadData()
    } catch (err) {
      console.error('Failed to add advance:', err)
    } finally {
      setSavingAdvance(false)
    }
  }

  const inputClass = "w-full border border-[rgba(59,77,67,0.15)] rounded-lg px-3 py-2 text-sm text-[#3D4A44] bg-white focus:outline-none focus:ring-2 focus:ring-[#5B8A72]/30"

  if (loading) return <div className="text-center py-12 text-[#7A8580]">Loading fees & advances...</div>

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <button onClick={() => setActiveSection('fees')} className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${activeSection === 'fees' ? 'bg-[rgba(91,138,114,0.12)] text-[#5B8A72] border border-[rgba(91,138,114,0.2)]' : 'text-[#7A8580] hover:text-[#3D4A44]'}`}>
          Fees ({fees.length})
        </button>
        <button onClick={() => setActiveSection('advances')} className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${activeSection === 'advances' ? 'bg-[rgba(91,138,114,0.12)] text-[#5B8A72] border border-[rgba(91,138,114,0.2)]' : 'text-[#7A8580] hover:text-[#3D4A44]'}`}>
          Advances ({advances.length})
        </button>
      </div>

      {activeSection === 'fees' && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <button onClick={() => setShowAddFee(!showAddFee)} className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-xl text-sm font-medium hover:shadow-md transition-all">
              <ArrowUpTrayIcon className="w-4 h-4" /> Add Fee
            </button>
          </div>

          {showAddFee && (
            <div className="bg-white/60 backdrop-blur-xl rounded-[14px] border border-[rgba(59,77,67,0.08)] p-5 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs text-[#7A8580] mb-1">Fee Type</label>
                  <select value={feeForm.fee_type} onChange={(e) => setFeeForm(prev => ({ ...prev, fee_type: e.target.value }))} className={inputClass}>
                    {FEE_TYPES.map(t => <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-[#7A8580] mb-1">Amount ($) *</label>
                  <input type="number" step="0.01" value={feeForm.amount} onChange={(e) => setFeeForm(prev => ({ ...prev, amount: e.target.value }))} className={inputClass} />
                </div>
                <div className="sm:col-span-2">
                  <label className="block text-xs text-[#7A8580] mb-1">Description *</label>
                  <input type="text" value={feeForm.description} onChange={(e) => setFeeForm(prev => ({ ...prev, description: e.target.value }))} className={inputClass} />
                </div>
                <div>
                  <label className="block text-xs text-[#7A8580] mb-1">Date</label>
                  <input type="date" value={feeForm.fee_date} onChange={(e) => setFeeForm(prev => ({ ...prev, fee_date: e.target.value }))} className={inputClass} />
                </div>
              </div>
              <div className="flex gap-3">
                <button onClick={handleAddFee} disabled={!feeForm.description || !feeForm.amount || savingFee} className="px-4 py-2 bg-[#5B8A72] text-white rounded-lg text-sm font-medium hover:bg-[#4A7A62] disabled:opacity-50 transition-colors">
                  {savingFee ? 'Adding...' : 'Add Fee'}
                </button>
                <button onClick={() => setShowAddFee(false)} className="px-4 py-2 text-[#7A8580] text-sm">Cancel</button>
              </div>
            </div>
          )}

          <div className="bg-white/60 backdrop-blur-xl rounded-[14px] border border-[rgba(59,77,67,0.08)]">
            {fees.length === 0 ? (
              <div className="text-center py-12 text-[#7A8580]">No fees recorded</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full">
                  <thead>
                    <tr className="border-b border-[rgba(59,77,67,0.08)]">
                      <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Date</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Type</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Description</th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-[#7A8580] uppercase">Amount</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[rgba(59,77,67,0.06)]">
                    {fees.map((fee, i) => (
                      <tr key={fee.id || i} className="hover:bg-[rgba(91,138,114,0.04)]">
                        <td className="px-6 py-3 text-sm text-[#7A8580]">{formatDate(fee.fee_date || fee.created_at)}</td>
                        <td className="px-6 py-3 text-sm text-[#3D4A44]">{(fee.fee_type || '').replace(/_/g, ' ')}</td>
                        <td className="px-6 py-3 text-sm text-[#3D4A44]">{fee.description || '—'}</td>
                        <td className="px-6 py-3 text-sm text-right font-medium text-[#C47068]">{formatCents(fee.amount_cents)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {activeSection === 'advances' && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <button onClick={() => setShowAddAdvance(!showAddAdvance)} className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-xl text-sm font-medium hover:shadow-md transition-all">
              <ArrowUpTrayIcon className="w-4 h-4" /> Add Advance
            </button>
          </div>

          {showAddAdvance && (
            <div className="bg-white/60 backdrop-blur-xl rounded-[14px] border border-[rgba(59,77,67,0.08)] p-5 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs text-[#7A8580] mb-1">Amount ($) *</label>
                  <input type="number" step="0.01" value={advanceForm.amount} onChange={(e) => setAdvanceForm(prev => ({ ...prev, amount: e.target.value }))} className={inputClass} />
                </div>
                <div>
                  <label className="block text-xs text-[#7A8580] mb-1">Date</label>
                  <input type="date" value={advanceForm.advance_date} onChange={(e) => setAdvanceForm(prev => ({ ...prev, advance_date: e.target.value }))} className={inputClass} />
                </div>
                <div className="sm:col-span-2">
                  <label className="block text-xs text-[#7A8580] mb-1">Description *</label>
                  <input type="text" value={advanceForm.description} onChange={(e) => setAdvanceForm(prev => ({ ...prev, description: e.target.value }))} className={inputClass} />
                </div>
              </div>
              <div className="flex gap-3">
                <button onClick={handleAddAdvance} disabled={!advanceForm.description || !advanceForm.amount || savingAdvance} className="px-4 py-2 bg-[#5B8A72] text-white rounded-lg text-sm font-medium hover:bg-[#4A7A62] disabled:opacity-50 transition-colors">
                  {savingAdvance ? 'Adding...' : 'Add Advance'}
                </button>
                <button onClick={() => setShowAddAdvance(false)} className="px-4 py-2 text-[#7A8580] text-sm">Cancel</button>
              </div>
            </div>
          )}

          <div className="bg-white/60 backdrop-blur-xl rounded-[14px] border border-[rgba(59,77,67,0.08)]">
            {advances.length === 0 ? (
              <div className="text-center py-12 text-[#7A8580]">No advances recorded</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full">
                  <thead>
                    <tr className="border-b border-[rgba(59,77,67,0.08)]">
                      <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Date</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] uppercase">Description</th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-[#7A8580] uppercase">Amount</th>
                      <th className="px-6 py-3 text-center text-xs font-medium text-[#7A8580] uppercase">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[rgba(59,77,67,0.06)]">
                    {advances.map((adv, i) => (
                      <tr key={adv.id || i} className="hover:bg-[rgba(91,138,114,0.04)]">
                        <td className="px-6 py-3 text-sm text-[#7A8580]">{formatDate(adv.advance_date || adv.created_at)}</td>
                        <td className="px-6 py-3 text-sm text-[#3D4A44]">{adv.description || '—'}</td>
                        <td className="px-6 py-3 text-sm text-right font-medium text-[#3D4A44]">{formatCents(adv.amount_cents)}</td>
                        <td className="px-6 py-3 text-center">
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${adv.is_recouped ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'}`}>
                            {adv.is_recouped ? 'Recouped' : 'Active'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
