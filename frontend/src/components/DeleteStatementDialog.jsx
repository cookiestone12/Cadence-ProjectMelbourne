import React, { useEffect, useState } from 'react'
import axios from 'axios'
import { XMarkIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline'

const formatDollars = (cents) => {
  if (cents == null) return '$0.00'
  const v = Number(cents) / 100
  return v.toLocaleString('en-US', { style: 'currency', currency: 'USD' })
}

export default function DeleteStatementDialog({ orgId, statementId, statementName, onClose, onDeleted }) {
  const [loading, setLoading] = useState(true)
  const [preview, setPreview] = useState(null)
  const [error, setError] = useState(null)
  const [confirmText, setConfirmText] = useState('')
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    if (!orgId || !statementId) return
    let cancelled = false
    setLoading(true)
    setError(null)
    axios.get(`/api/royalties/statements/${orgId}/${statementId}/delete-preview`)
      .then(res => { if (!cancelled) setPreview(res.data) })
      .catch(err => { if (!cancelled) setError(err.response?.data?.detail || 'Failed to load preview') })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [orgId, statementId])

  const canDelete = confirmText.trim().toUpperCase() === 'DELETE' && !deleting

  const handleDelete = async () => {
    if (!canDelete) return
    setDeleting(true)
    try {
      await axios.delete(`/api/royalties/statements/${orgId}/${statementId}`)
      if (onDeleted) onDeleted()
      onClose()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete statement.')
      setDeleting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm p-4">
      <div className="bg-white rounded-[18px] shadow-2xl w-full max-w-lg max-h-[90vh] overflow-hidden flex flex-col">
        <div className="flex items-center justify-between p-5 border-b border-[rgba(59,77,67,0.08)]">
          <div className="flex items-center gap-2">
            <ExclamationTriangleIcon className="w-5 h-5 text-red-500" />
            <h3 className="text-lg font-semibold text-red-600">Delete Statement</h3>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-[rgba(59,77,67,0.06)] rounded-full transition-colors">
            <XMarkIcon className="w-5 h-5 text-[#7A8580]" />
          </button>
        </div>

        <div className="p-5 space-y-4 overflow-y-auto">
          <p className="text-sm text-[#3D4A44]">
            You're about to permanently delete{' '}
            <span className="font-semibold">{statementName || preview?.source_name || 'this statement'}</span>.
            This action cannot be undone.
          </p>

          {loading && (
            <div className="flex items-center justify-center py-6">
              <div className="inline-block animate-spin rounded-full h-6 w-6 border-4 border-[#5B8A72] border-t-transparent"></div>
            </div>
          )}

          {error && !loading && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
              {error}
            </div>
          )}

          {preview && !loading && (
            <div className="space-y-3">
              <div className="bg-[rgba(91,138,114,0.04)] rounded-xl p-4 space-y-2">
                <p className="text-xs font-semibold text-[#3D4A44] uppercase tracking-wide">What will be removed</p>
                <ul className="text-sm text-[#3D4A44] space-y-1">
                  <li className="flex justify-between">
                    <span className="text-[#7A8580]">Transactions</span>
                    <span className="font-medium">{preview.transaction_count}</span>
                  </li>
                  <li className="flex justify-between">
                    <span className="text-[#7A8580]">Statement lines</span>
                    <span className="font-medium">{preview.line_count}</span>
                  </li>
                  <li className="flex justify-between">
                    <span className="text-[#7A8580]">Allocations</span>
                    <span className="font-medium">{preview.allocation_count}</span>
                  </li>
                  <li className="flex justify-between">
                    <span className="text-[#7A8580]">Ledger entries</span>
                    <span className="font-medium">{preview.ledger_entry_count}</span>
                  </li>
                  <li className="flex justify-between">
                    <span className="text-[#7A8580]">Processing runs</span>
                    <span className="font-medium">{preview.processing_run_count}</span>
                  </li>
                  <li className="flex justify-between">
                    <span className="text-[#7A8580]">Total revenue</span>
                    <span className="font-medium">{formatDollars(preview.total_revenue_cents)}</span>
                  </li>
                  <li className="flex justify-between">
                    <span className="text-[#7A8580]">Action items removed</span>
                    <span className="font-medium">{preview.action_items_to_remove}</span>
                  </li>
                  {preview.file_will_be_deleted && (
                    <li className="flex justify-between">
                      <span className="text-[#7A8580]">Uploaded file</span>
                      <span className="font-medium text-[#3D4A44]">Will be deleted from disk</span>
                    </li>
                  )}
                </ul>
              </div>

              {preview.advance_restores?.length > 0 && (
                <div className="bg-[rgba(91,138,114,0.06)] border border-[rgba(91,138,114,0.2)] rounded-xl p-4">
                  <p className="text-xs font-semibold text-[#3D4A44] uppercase tracking-wide mb-2">
                    Advance balances restored
                  </p>
                  <ul className="text-sm text-[#3D4A44] space-y-1">
                    {preview.advance_restores.map(a => (
                      <li key={a.advance_id} className="flex justify-between">
                        <span className="text-[#7A8580] truncate mr-2">{a.advance_name || `Advance #${a.advance_id}`}</span>
                        <span className="font-medium text-[#5B8A72]">+{formatDollars(a.restore_cents)}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {preview.payments_unwound?.length > 0 && (
                <div className="bg-[rgba(184,115,51,0.06)] border border-[rgba(184,115,51,0.2)] rounded-xl p-4">
                  <p className="text-xs font-semibold text-[#B87333] uppercase tracking-wide mb-2">
                    Payment links unwound ({preview.payments_unwound.length})
                  </p>
                  <p className="text-xs text-[#7A8580] mb-2">
                    These ledger entries link payouts to this statement. The actual payments stay recorded; only the link to this statement is removed and audit-logged.
                  </p>
                  <ul className="text-sm text-[#3D4A44] space-y-1 max-h-32 overflow-y-auto">
                    {preview.payments_unwound.map(p => (
                      <li key={p.ledger_entry_id} className="flex justify-between">
                        <span className="text-[#7A8580] truncate mr-2">{p.memo || `Entry #${p.ledger_entry_id}`}</span>
                        <span className="font-medium">{formatDollars(Math.abs(p.amount_cents || 0))}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">
                  Type <span className="font-mono font-semibold">DELETE</span> to confirm
                </label>
                <input
                  type="text"
                  value={confirmText}
                  onChange={e => setConfirmText(e.target.value)}
                  className="w-full border border-[rgba(59,77,67,0.15)] rounded-lg px-3 py-2 text-sm text-[#3D4A44] bg-white focus:outline-none focus:ring-2 focus:ring-red-400/30"
                  placeholder="DELETE"
                  autoFocus
                />
              </div>
            </div>
          )}
        </div>

        <div className="flex justify-end gap-3 px-5 py-4 border-t border-[rgba(59,77,67,0.08)] bg-[rgba(91,138,114,0.02)]">
          <button onClick={onClose} className="px-4 py-2 text-sm text-[#7A8580] hover:text-[#3D4A44] transition-colors">
            Cancel
          </button>
          <button
            onClick={handleDelete}
            disabled={!canDelete}
            className="px-5 py-2.5 bg-red-500 text-white rounded-xl hover:bg-red-600 transition-all text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {deleting ? 'Deleting...' : 'Delete Statement'}
          </button>
        </div>
      </div>
    </div>
  )
}
