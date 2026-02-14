import React, { useState, useEffect, useCallback } from 'react'
import axios from 'axios'
import {
  BanknotesIcon,
  PlusIcon,
  EyeIcon,
  XMarkIcon,
  ArrowLeftIcon,
  ChevronRightIcon,
  UserGroupIcon,
  CurrencyDollarIcon,
  CheckCircleIcon,
  ClockIcon,
  DocumentTextIcon,
} from '@heroicons/react/24/outline'

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

const BATCH_STATUS_COLORS = {
  DRAFT: { bg: 'bg-gray-100', text: 'text-gray-700' },
  APPROVED: { bg: 'bg-blue-100', text: 'text-blue-700' },
  PAID: { bg: 'bg-green-100', text: 'text-green-700' },
}

export default function PayablesTab({ orgId }) {
  const [payables, setPayables] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedPayee, setSelectedPayee] = useState(null)
  const [ledger, setLedger] = useState([])
  const [ledgerLoading, setLedgerLoading] = useState(false)

  const [batches, setBatches] = useState([])
  const [batchesLoading, setBatchesLoading] = useState(true)
  const [showCreateBatch, setShowCreateBatch] = useState(false)
  const [batchName, setBatchName] = useState('')
  const [batchCurrency, setBatchCurrency] = useState('USD')
  const [creatingBatch, setCreatingBatch] = useState(false)

  const [showAddItem, setShowAddItem] = useState(null)
  const [itemAmount, setItemAmount] = useState('')
  const [itemMemo, setItemMemo] = useState('')
  const [addingItem, setAddingItem] = useState(false)

  const loadPayables = useCallback(async () => {
    if (!orgId) return
    try {
      const res = await axios.get(`/api/royalty-processing/${orgId}/payables`)
      setPayables(res.data.payables || [])
    } catch (err) {
      console.error('Failed to load payables:', err)
    } finally {
      setLoading(false)
    }
  }, [orgId])

  const loadBatches = useCallback(async () => {
    if (!orgId) return
    try {
      const res = await axios.get(`/api/royalty-processing/${orgId}/payout-batches`)
      setBatches(res.data.batches || [])
    } catch (err) {
      console.error('Failed to load batches:', err)
    } finally {
      setBatchesLoading(false)
    }
  }, [orgId])

  useEffect(() => { loadPayables(); loadBatches() }, [loadPayables, loadBatches])

  const loadLedger = async (payeeId) => {
    setLedgerLoading(true)
    try {
      const res = await axios.get(`/api/royalty-processing/${orgId}/payees/${payeeId}/ledger`)
      setLedger(res.data.entries || [])
    } catch (err) {
      console.error('Failed to load ledger:', err)
    } finally {
      setLedgerLoading(false)
    }
  }

  const handleViewLedger = (payee) => {
    setSelectedPayee(payee)
    loadLedger(payee.payee_id)
  }

  const handleCreateBatch = async () => {
    if (!batchName.trim()) return
    setCreatingBatch(true)
    try {
      await axios.post(`/api/royalty-processing/${orgId}/payout-batches`, { name: batchName, currency: batchCurrency })
      setShowCreateBatch(false)
      setBatchName('')
      loadBatches()
    } catch (err) {
      console.error('Failed to create batch:', err)
    } finally {
      setCreatingBatch(false)
    }
  }

  const handleUpdateBatchStatus = async (batchId, newStatus) => {
    try {
      await axios.put(`/api/royalty-processing/${orgId}/payout-batches/${batchId}/status`, { status: newStatus })
      loadBatches()
    } catch (err) {
      console.error('Failed to update batch status:', err)
      alert(err.response?.data?.detail || 'Failed to update status.')
    }
  }

  const handleAddItem = async (batchId, payeeId) => {
    if (!itemAmount) return
    setAddingItem(true)
    try {
      await axios.post(`/api/royalty-processing/${orgId}/payout-batches/${batchId}/items`, {
        payee_id: payeeId,
        amount_cents: Math.round(parseFloat(itemAmount) * 100),
        memo: itemMemo || null,
      })
      setShowAddItem(null)
      setItemAmount('')
      setItemMemo('')
      loadBatches()
    } catch (err) {
      console.error('Failed to add item:', err)
      alert(err.response?.data?.detail || 'Failed to add item.')
    } finally {
      setAddingItem(false)
    }
  }

  if (selectedPayee) {
    return (
      <div className="space-y-4">
        <button onClick={() => setSelectedPayee(null)} className="flex items-center gap-2 text-[#5B8A72] hover:text-[#4a7a62] text-sm font-medium transition-colors">
          <ArrowLeftIcon className="w-4 h-4" /> Back to Payables
        </button>
        <div className="bg-white/80 backdrop-blur-xl rounded-[18px] shadow-am p-6 border border-[rgba(59,77,67,0.08)]">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] rounded-lg">
              <UserGroupIcon className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-[#3D4A44]">
                {selectedPayee.creator_name || selectedPayee.company_name || 'Payee'}
              </h3>
              <p className="text-sm text-[#7A8580]">{selectedPayee.payee_type} — Balance: {formatCents(selectedPayee.balance?.current_balance_cents)}</p>
            </div>
          </div>
        </div>

        <div className="bg-white/80 backdrop-blur-xl rounded-[18px] shadow-am border border-[rgba(59,77,67,0.08)]">
          <div className="p-6 border-b border-[rgba(59,77,67,0.08)]">
            <h3 className="text-lg font-semibold text-[#3D4A44]">Ledger Entries</h3>
          </div>
          {ledgerLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-[#5B8A72] border-t-transparent"></div>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-[#EEF1EC]">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-[#7A8580] uppercase tracking-wider">Date</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-[#7A8580] uppercase tracking-wider">Type</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-[#7A8580] uppercase tracking-wider">Source</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-[#7A8580] uppercase tracking-wider">Amount</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-[#7A8580] uppercase tracking-wider">Memo</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[rgba(59,77,67,0.05)]">
                  {ledger.map(e => (
                    <tr key={e.id} className="hover:bg-[rgba(91,138,114,0.04)]">
                      <td className="px-4 py-3 text-sm text-[#7A8580]">{formatDate(e.created_at)}</td>
                      <td className="px-4 py-3">
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-[rgba(91,138,114,0.1)] text-[#5B8A72]">
                          {e.entry_type}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-[#7A8580]">{e.source || '—'}</td>
                      <td className="px-4 py-3 text-sm text-right font-medium text-[#3D4A44]">{formatCents(e.amount_cents)}</td>
                      <td className="px-4 py-3 text-sm text-[#7A8580]">{e.memo || '—'}</td>
                    </tr>
                  ))}
                  {ledger.length === 0 && (
                    <tr><td colSpan={5} className="px-6 py-12 text-center text-sm text-[#7A8580]">No ledger entries found.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-10 w-10 border-4 border-[#5B8A72] border-t-transparent"></div>
          <p className="mt-3 text-sm text-[#7A8580]">Loading payables...</p>
        </div>
      </div>
    )
  }

  const draftBatches = batches.filter(b => b.status === 'DRAFT')

  return (
    <div className="space-y-6">
      <div className="bg-white/80 backdrop-blur-xl rounded-[18px] shadow-am border border-[rgba(59,77,67,0.08)]">
        <div className="p-6 border-b border-[rgba(59,77,67,0.08)]">
          <h3 className="text-lg font-semibold text-[#3D4A44]">Payables</h3>
          <p className="text-sm text-[#7A8580] mt-1">Payees with outstanding balances</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-[#EEF1EC]">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-[#7A8580] uppercase tracking-wider">Payee Name</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[#7A8580] uppercase tracking-wider">Type</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-[#7A8580] uppercase tracking-wider">Payable Balance</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[#7A8580] uppercase tracking-wider">Outstanding Advances</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[#7A8580] uppercase tracking-wider">Last Statement</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-[#7A8580] uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[rgba(59,77,67,0.05)]">
              {payables.map(p => (
                <tr key={p.payee_id} className="hover:bg-[rgba(91,138,114,0.04)]">
                  <td className="px-4 py-3 text-sm font-medium text-[#3D4A44]">
                    {p.creator_name || p.company_name || 'Unknown'}
                  </td>
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-[rgba(91,138,114,0.1)] text-[#5B8A72]">
                      {p.payee_type}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-right font-semibold text-[#3D4A44]">
                    {formatCents(p.balance?.current_balance_cents)}
                  </td>
                  <td className="px-4 py-3">
                    {(p.outstanding_advances || []).length > 0 ? (
                      <div className="space-y-1">
                        {p.outstanding_advances.map(a => (
                          <div key={a.id} className="text-xs text-[#7A8580]">
                            {a.advance_name}: {formatCents(a.outstanding_balance_cents)}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <span className="text-xs text-[#7A8580]">None</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-sm text-[#7A8580]">
                    {p.last_statement ? `${p.last_statement.source_name} (${formatDate(p.last_statement.period_end)})` : '—'}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => handleViewLedger(p)}
                        className="flex items-center gap-1 px-3 py-1.5 text-xs bg-[rgba(91,138,114,0.1)] text-[#5B8A72] rounded-lg hover:bg-[rgba(91,138,114,0.2)] transition-colors font-medium"
                      >
                        <EyeIcon className="w-3.5 h-3.5" /> View Ledger
                      </button>
                      {draftBatches.length > 0 && (
                        <button
                          onClick={() => setShowAddItem({ payeeId: p.payee_id, payeeName: p.creator_name || p.company_name })}
                          className="flex items-center gap-1 px-3 py-1.5 text-xs bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-lg hover:shadow-[0px_4px_12px_rgba(91,138,114,0.3)] transition-all font-medium"
                        >
                          <PlusIcon className="w-3.5 h-3.5" /> Add to Payout
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
              {payables.length === 0 && (
                <tr><td colSpan={6} className="px-6 py-12 text-center text-sm text-[#7A8580]">No payables outstanding.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="bg-white/80 backdrop-blur-xl rounded-[18px] shadow-am border border-[rgba(59,77,67,0.08)]">
        <div className="flex items-center justify-between p-6 border-b border-[rgba(59,77,67,0.08)]">
          <div>
            <h3 className="text-lg font-semibold text-[#3D4A44]">Payout Batches</h3>
            <p className="text-sm text-[#7A8580] mt-1">Manage payout batches for bulk payments</p>
          </div>
          <button
            onClick={() => setShowCreateBatch(true)}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-xl hover:shadow-[0px_4px_12px_rgba(91,138,114,0.3)] transition-all text-sm font-medium"
          >
            <PlusIcon className="w-4 h-4" /> Create Batch
          </button>
        </div>
        {batchesLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-[#5B8A72] border-t-transparent"></div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-[#EEF1EC]">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[#7A8580] uppercase tracking-wider">Batch Name</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[#7A8580] uppercase tracking-wider">Status</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-[#7A8580] uppercase tracking-wider">Items</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-[#7A8580] uppercase tracking-wider">Total</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[#7A8580] uppercase tracking-wider">Created</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-[#7A8580] uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[rgba(59,77,67,0.05)]">
                {batches.map(b => {
                  const colors = BATCH_STATUS_COLORS[b.status] || { bg: 'bg-gray-100', text: 'text-gray-700' }
                  return (
                    <tr key={b.id} className="hover:bg-[rgba(91,138,114,0.04)]">
                      <td className="px-4 py-3 text-sm font-medium text-[#3D4A44]">{b.name}</td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colors.bg} ${colors.text}`}>
                          {b.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-right text-[#7A8580]">{b.item_count}</td>
                      <td className="px-4 py-3 text-sm text-right font-medium text-[#3D4A44]">{formatDollars(b.total_dollars)}</td>
                      <td className="px-4 py-3 text-sm text-[#7A8580]">{formatDate(b.created_at)}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-end gap-1">
                          {b.status === 'DRAFT' && (
                            <button
                              onClick={() => handleUpdateBatchStatus(b.id, 'APPROVED')}
                              className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 transition-colors font-medium"
                            >
                              Approve
                            </button>
                          )}
                          {b.status === 'APPROVED' && (
                            <button
                              onClick={() => handleUpdateBatchStatus(b.id, 'PAID')}
                              className="px-2 py-1 text-xs bg-green-100 text-green-700 rounded-lg hover:bg-green-200 transition-colors font-medium"
                            >
                              Mark Paid
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  )
                })}
                {batches.length === 0 && (
                  <tr><td colSpan={6} className="px-6 py-12 text-center text-sm text-[#7A8580]">No payout batches created yet.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showCreateBatch && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm p-4">
          <div className="bg-white rounded-[18px] shadow-2xl w-full max-w-md">
            <div className="flex items-center justify-between p-6 border-b border-[rgba(59,77,67,0.08)]">
              <h3 className="text-lg font-semibold text-[#3D4A44]">Create Payout Batch</h3>
              <button onClick={() => setShowCreateBatch(false)} className="p-2 hover:bg-[rgba(59,77,67,0.06)] rounded-full transition-colors">
                <XMarkIcon className="w-5 h-5 text-[#7A8580]" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Batch Name</label>
                <input
                  type="text"
                  value={batchName}
                  onChange={e => setBatchName(e.target.value)}
                  placeholder="e.g., Q4 2025 Payouts"
                  className="w-full px-4 py-2.5 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm text-[#3D4A44] bg-white focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Currency</label>
                <select
                  value={batchCurrency}
                  onChange={e => setBatchCurrency(e.target.value)}
                  className="w-full px-4 py-2.5 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm text-[#3D4A44] bg-white focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent outline-none"
                >
                  <option value="USD">USD</option>
                  <option value="EUR">EUR</option>
                  <option value="GBP">GBP</option>
                </select>
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button onClick={() => setShowCreateBatch(false)} className="px-4 py-2 text-sm text-[#7A8580] hover:text-[#3D4A44] transition-colors">Cancel</button>
                <button
                  onClick={handleCreateBatch}
                  disabled={!batchName.trim() || creatingBatch}
                  className="px-5 py-2.5 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-xl hover:shadow-[0px_4px_12px_rgba(91,138,114,0.3)] transition-all text-sm font-medium disabled:opacity-50"
                >
                  {creatingBatch ? 'Creating...' : 'Create Batch'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {showAddItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm p-4">
          <div className="bg-white rounded-[18px] shadow-2xl w-full max-w-md">
            <div className="flex items-center justify-between p-6 border-b border-[rgba(59,77,67,0.08)]">
              <h3 className="text-lg font-semibold text-[#3D4A44]">Add to Payout Batch</h3>
              <button onClick={() => setShowAddItem(null)} className="p-2 hover:bg-[rgba(59,77,67,0.06)] rounded-full transition-colors">
                <XMarkIcon className="w-5 h-5 text-[#7A8580]" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <p className="text-sm text-[#7A8580]">
                Adding payout for <span className="font-medium text-[#3D4A44]">{showAddItem.payeeName}</span>
              </p>
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Batch</label>
                <select
                  id="batch-select"
                  className="w-full px-4 py-2.5 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm text-[#3D4A44] bg-white focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent outline-none"
                >
                  {draftBatches.map(b => (
                    <option key={b.id} value={b.id}>{b.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Amount ($)</label>
                <input
                  type="number"
                  step="0.01"
                  value={itemAmount}
                  onChange={e => setItemAmount(e.target.value)}
                  placeholder="0.00"
                  className="w-full px-4 py-2.5 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm text-[#3D4A44] bg-white focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Memo (optional)</label>
                <input
                  type="text"
                  value={itemMemo}
                  onChange={e => setItemMemo(e.target.value)}
                  placeholder="Payment memo..."
                  className="w-full px-4 py-2.5 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm text-[#3D4A44] bg-white focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent outline-none"
                />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button onClick={() => setShowAddItem(null)} className="px-4 py-2 text-sm text-[#7A8580] hover:text-[#3D4A44] transition-colors">Cancel</button>
                <button
                  onClick={() => {
                    const batchId = document.getElementById('batch-select')?.value
                    if (batchId) handleAddItem(parseInt(batchId), showAddItem.payeeId)
                  }}
                  disabled={!itemAmount || addingItem}
                  className="px-5 py-2.5 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-xl hover:shadow-[0px_4px_12px_rgba(91,138,114,0.3)] transition-all text-sm font-medium disabled:opacity-50"
                >
                  {addingItem ? 'Adding...' : 'Add to Batch'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
