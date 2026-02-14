import React, { useState, useEffect, useCallback } from 'react'
import axios from 'axios'
import { PlusIcon, XMarkIcon } from '@heroicons/react/24/outline'

const formatDollars = (val) => {
  if (val == null) return '$0.00'
  return Number(val).toLocaleString('en-US', { style: 'currency', currency: 'USD' })
}

const formatDate = (dateStr) => {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

const POOL_COLORS = {
  MASTER: 'bg-purple-100 text-purple-700',
  PUBLISHING: 'bg-blue-100 text-blue-700',
  BOTH: 'bg-teal-100 text-teal-700',
  CUSTOM: 'bg-orange-100 text-orange-700',
}

const POOL_OPTIONS = ['MASTER', 'PUBLISHING', 'BOTH', 'CUSTOM']
const CURRENCY_OPTIONS = ['USD', 'EUR', 'GBP', 'CAD', 'AUD', 'JPY']

const emptyForm = {
  advance_name: '',
  advance_date: '',
  principal_amount: '',
  currency: 'USD',
  recoupment_pool: 'MASTER',
  recoupment_priority: 1,
  cross_collateralize: false,
  payee_id: '',
  start_recouping_on: '',
  end_recouping_on: '',
  notes: '',
}

export default function ContractAdvancesSection({ orgId, contractId }) {
  const [advances, setAdvances] = useState([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [form, setForm] = useState({ ...emptyForm })
  const [payees, setPayees] = useState([])
  const [payeesLoaded, setPayeesLoaded] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const loadAdvances = useCallback(async () => {
    if (!orgId || !contractId) return
    setLoading(true)
    try {
      const res = await axios.get(`/api/royalty-processing/${orgId}/advances`, { params: { contract_id: contractId } })
      setAdvances(Array.isArray(res.data) ? res.data : res.data.advances || [])
    } catch (err) {
      console.error('Failed to load advances:', err)
      setAdvances([])
    } finally {
      setLoading(false)
    }
  }, [orgId, contractId])

  useEffect(() => {
    loadAdvances()
  }, [loadAdvances])

  const loadPayees = async () => {
    if (payeesLoaded) return
    try {
      const res = await axios.get(`/api/royalty-processing/${orgId}/payees`)
      setPayees(Array.isArray(res.data) ? res.data : res.data.payees || [])
    } catch (err) {
      console.error('Failed to load payees:', err)
    } finally {
      setPayeesLoaded(true)
    }
  }

  const openModal = () => {
    setForm({ ...emptyForm })
    setError('')
    loadPayees()
    setShowModal(true)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.advance_name.trim()) {
      setError('Please enter an advance name.')
      return
    }
    if (!form.principal_amount || parseFloat(form.principal_amount) <= 0) {
      setError('Please enter a valid principal amount.')
      return
    }
    setError('')
    setSubmitting(true)
    try {
      const payload = {
        advance_name: form.advance_name,
        principal_amount_cents: Math.round(parseFloat(form.principal_amount) * 100),
        currency: form.currency,
        recoupment_pool: form.recoupment_pool,
        recoupment_priority: parseInt(form.recoupment_priority) || 1,
        cross_collateralize: form.cross_collateralize,
        contract_id: contractId,
        notes: form.notes || null,
      }
      if (form.advance_date) payload.advance_date = form.advance_date
      if (form.payee_id) payload.payee_id = parseInt(form.payee_id)
      if (form.start_recouping_on) payload.start_recouping_on = form.start_recouping_on
      if (form.end_recouping_on) payload.end_recouping_on = form.end_recouping_on
      await axios.post(`/api/royalty-processing/${orgId}/advances`, payload)
      setShowModal(false)
      setForm({ ...emptyForm })
      loadAdvances()
    } catch (err) {
      console.error('Failed to create advance:', err)
      const detail = err.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Failed to create advance. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="mt-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-[#3D4A44]">Advances</h3>
        <button
          onClick={openModal}
          className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-medium bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white hover:shadow-[0px_4px_12px_rgba(91,138,114,0.3)] transition-all"
        >
          <PlusIcon className="w-4 h-4" />
          Add Advance
        </button>
      </div>

      {loading ? (
        <div className="text-center py-8 text-[#7A8580]">Loading advances...</div>
      ) : advances.length === 0 ? (
        <div className="bg-white/60 backdrop-blur-xl rounded-[14px] border border-[rgba(59,77,67,0.08)] p-8 text-center">
          <p className="text-[#7A8580]">No advances found for this contract.</p>
        </div>
      ) : (
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
                    <p className="text-xs text-[#7A8580] mt-0.5">{formatDate(adv.advance_date || adv.created_at)}</p>
                  </div>
                  <div className="flex items-center gap-2 flex-wrap justify-end">
                    {adv.recoupment_pool && (
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${POOL_COLORS[adv.recoupment_pool] || 'bg-gray-100 text-gray-700'}`}>
                        {adv.recoupment_pool}
                      </span>
                    )}
                    {adv.recoupment_priority != null && (
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
                        Priority: {adv.recoupment_priority}
                      </span>
                    )}
                    {adv.cross_collateralize && (
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700">
                        Cross-Collateralized
                      </span>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-3">
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
                  {adv.payee_name && (
                    <div>
                      <p className="text-xs text-[#7A8580]">Payee</p>
                      <p className="text-sm font-medium text-[#3D4A44]">{adv.payee_name}</p>
                    </div>
                  )}
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
      )}

      {showModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg mx-4 max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between p-6 border-b border-[rgba(59,77,67,0.08)]">
              <h3 className="text-lg font-semibold text-[#3D4A44]">Add Advance</h3>
              <button onClick={() => setShowModal(false)} className="text-[#7A8580] hover:text-[#3D4A44]">
                <XMarkIcon className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-4">
              {error && (
                <div className="px-4 py-2 bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl">{error}</div>
              )}
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Advance Name *</label>
                <input
                  type="text"
                  value={form.advance_name}
                  onChange={(e) => setForm(p => ({ ...p, advance_name: e.target.value }))}
                  className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  placeholder="e.g. Recording Advance Q1"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Advance Date</label>
                  <input
                    type="date"
                    value={form.advance_date}
                    onChange={(e) => setForm(p => ({ ...p, advance_date: e.target.value }))}
                    className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Principal Amount ($) *</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={form.principal_amount}
                    onChange={(e) => setForm(p => ({ ...p, principal_amount: e.target.value }))}
                    className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                    placeholder="10000.00"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Currency</label>
                  <select
                    value={form.currency}
                    onChange={(e) => setForm(p => ({ ...p, currency: e.target.value }))}
                    className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  >
                    {CURRENCY_OPTIONS.map(c => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Recoupment Pool</label>
                  <select
                    value={form.recoupment_pool}
                    onChange={(e) => setForm(p => ({ ...p, recoupment_pool: e.target.value }))}
                    className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  >
                    {POOL_OPTIONS.map(p => <option key={p} value={p}>{p}</option>)}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Priority</label>
                  <input
                    type="number"
                    min="1"
                    value={form.recoupment_priority}
                    onChange={(e) => setForm(p => ({ ...p, recoupment_priority: e.target.value }))}
                    className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Payee</label>
                  <select
                    value={form.payee_id}
                    onChange={(e) => setForm(p => ({ ...p, payee_id: e.target.value }))}
                    className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  >
                    <option value="">Select payee...</option>
                    {payees.map(p => (
                      <option key={p.id} value={p.id}>{p.payee_name || p.name || `Payee #${p.id}`}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Start Recouping On</label>
                  <input
                    type="date"
                    value={form.start_recouping_on}
                    onChange={(e) => setForm(p => ({ ...p, start_recouping_on: e.target.value }))}
                    className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">End Recouping On</label>
                  <input
                    type="date"
                    value={form.end_recouping_on}
                    onChange={(e) => setForm(p => ({ ...p, end_recouping_on: e.target.value }))}
                    className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  />
                </div>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="cross_collateralize"
                  checked={form.cross_collateralize}
                  onChange={(e) => setForm(p => ({ ...p, cross_collateralize: e.target.checked }))}
                  className="w-4 h-4 rounded border-[rgba(59,77,67,0.2)] text-[#5B8A72] focus:ring-[#5B8A72]"
                />
                <label htmlFor="cross_collateralize" className="text-sm font-medium text-[#3D4A44]">Cross-Collateralize</label>
              </div>
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Notes</label>
                <textarea
                  value={form.notes}
                  onChange={(e) => setForm(p => ({ ...p, notes: e.target.value }))}
                  rows={3}
                  className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  placeholder="Optional notes..."
                />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 rounded-xl text-sm font-medium border border-[rgba(59,77,67,0.12)] text-[#3D4A44] hover:bg-[#F5F7F4] transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 rounded-xl text-sm font-medium bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white hover:shadow-[0px_4px_12px_rgba(91,138,114,0.3)] transition-all disabled:opacity-50"
                >
                  {submitting ? 'Creating...' : 'Create Advance'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
