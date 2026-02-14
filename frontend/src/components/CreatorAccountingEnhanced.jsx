import React, { useState, useEffect, useCallback } from 'react'
import axios from 'axios'

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

export default function CreatorAccountingEnhanced({ orgId, creatorId, existingAccountingData, accountingLoading }) {
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
      const match = payees.find(p => p.creator_id === creatorId)
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
    { key: 'ledger', label: 'Ledger' },
    { key: 'recoupment', label: 'Recoupment' },
  ]

  return (
    <div className="space-y-6">
      <div className="flex space-x-1 bg-[#F5F7F4] rounded-xl p-1">
        {subTabs.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveSubTab(tab.key)}
            className={`flex-1 px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
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
        <SummarySubTab data={existingAccountingData} loading={accountingLoading} />
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

function SummarySubTab({ data, loading }) {
  if (loading) {
    return <div className="text-center py-12 text-[#7A8580]">Loading accounting data...</div>
  }
  if (!data) {
    return <div className="text-center py-12 text-[#7A8580]">No accounting data available</div>
  }

  const summary = data.summary || {}
  const cards = [
    { label: 'Total Royalties', value: formatDollars(summary.total_royalties_dollars), color: 'text-[#5B8A72]' },
    { label: 'Outstanding Advances', value: formatDollars(summary.outstanding_advances_dollars), color: 'text-[#C4956B]' },
    { label: 'Net Payable', value: formatDollars(summary.net_balance_dollars), color: summary.net_balance_cents >= 0 ? 'text-[#5B8A72]' : 'text-[#C47068]' },
  ]

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
