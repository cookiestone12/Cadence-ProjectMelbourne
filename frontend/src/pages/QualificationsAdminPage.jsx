import React, { useState, useEffect } from 'react'
import axios from 'axios'
import {
  ArrowDownTrayIcon,
  ChevronLeftIcon,
  UserIcon,
  BuildingOfficeIcon,
  CalendarDaysIcon,
} from '@heroicons/react/24/outline'

function Badge({ children, color = 'sage' }) {
  const palette = {
    sage: 'bg-[rgba(91,138,114,0.1)] text-[#3D6E5A]',
    amber: 'bg-amber-50 text-amber-700',
    gray: 'bg-[#EEF1EC] text-[#7A8580]',
  }
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${palette[color] || palette.gray}`}>
      {children}
    </span>
  )
}

function DetailRow({ label, value }) {
  if (!value && value !== 0) return null
  const display = Array.isArray(value) ? value.join(', ') || '—' : value
  return (
    <div className="flex gap-3 py-2.5 border-b border-[rgba(59,77,67,0.06)] last:border-0">
      <dt className="w-44 shrink-0 text-xs font-semibold text-[#7A8580] uppercase tracking-wide pt-0.5">
        {label}
      </dt>
      <dd className="text-sm text-[#1D1D1F] min-w-0 break-words">{display || '—'}</dd>
    </div>
  )
}

function fmtDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
  })
}

export default function QualificationsAdminPage() {
  const [records, setRecords] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selected, setSelected] = useState(null)

  useEffect(() => {
    axios.get('/api/admin/qualifications')
      .then(r => setRecords(r.data))
      .catch(() => setError('Failed to load qualifications.'))
      .finally(() => setLoading(false))
  }, [])

  const downloadCSV = () => {
    window.open('/api/admin/qualifications/export', '_blank')
  }

  if (loading) {
    return (
      <div className="p-8 text-center text-sm text-[#7A8580]">Loading qualifications...</div>
    )
  }

  if (error) {
    return (
      <div className="p-8 text-center text-sm text-red-600">{error}</div>
    )
  }

  if (selected) {
    const r = selected
    return (
      <div className="p-4 sm:p-8 max-w-3xl mx-auto">
        <button
          onClick={() => setSelected(null)}
          className="flex items-center gap-1.5 text-sm text-[#5B8A72] hover:text-[#3D6E5A] mb-6"
        >
          <ChevronLeftIcon className="w-4 h-4" />
          Back to list
        </button>

        <div className="bg-white rounded-xl border border-[rgba(59,77,67,0.1)] overflow-hidden mb-4">
          <div className="p-5 border-b border-[rgba(59,77,67,0.08)] flex items-start justify-between gap-4">
            <div>
              <h2 className="text-lg font-bold text-[#1D1D1F]">{r.full_name}</h2>
              <div className="text-sm text-[#3D4A44] mt-0.5">{r.company}</div>
              <a href={`mailto:${r.work_email}`} className="text-xs text-[#5B8A72] hover:underline">
                {r.work_email}
              </a>
            </div>
            <div className="text-right shrink-0">
              <Badge color="sage">{r.role}</Badge>
              <div className="text-xs text-[#7A8580] mt-1">{fmtDate(r.created_at)}</div>
            </div>
          </div>
          <dl className="px-5 py-2">
            <DetailRow label="Catalog coverage" value={r.catalog_coverage} />
            <DetailRow label="Catalog size" value={r.catalog_size} />
            <DetailRow label="Current management" value={r.current_management} />
            <DetailRow label="Goals" value={r.goals} />
            <DetailRow label="Timeline" value={r.timeline} />
            <DetailRow label="Reason now" value={r.reason_now} />
            <DetailRow label="Demo notes" value={r.demo_notes} />
            <DetailRow label="Submitted" value={r.created_at ? new Date(r.created_at).toLocaleString() : '—'} />
          </dl>
        </div>

        <a
          href={`mailto:${r.work_email}?subject=Your%20Cadence%20demo%20request`}
          className="inline-block px-4 py-2 rounded-md bg-[#5B8A72] text-white text-sm font-semibold hover:bg-[#3D6E5A] transition-colors"
        >
          Reply to {r.full_name.split(' ')[0]}
        </a>
      </div>
    )
  }

  return (
    <div className="p-4 sm:p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-[#1D1D1F]">Demo Qualifications</h1>
          <p className="text-sm text-[#7A8580] mt-0.5">
            {records.length} submission{records.length !== 1 ? 's' : ''}, newest first
          </p>
        </div>
        <button
          onClick={downloadCSV}
          className="flex items-center gap-2 px-4 py-2 rounded-md bg-[#EEF1EC] text-[#3D4A44] text-sm font-medium hover:bg-[#dde5de] transition-colors"
        >
          <ArrowDownTrayIcon className="w-4 h-4" />
          Download CSV
        </button>
      </div>

      {records.length === 0 ? (
        <div className="bg-white rounded-xl border border-[rgba(59,77,67,0.08)] p-12 text-center">
          <UserIcon className="w-8 h-8 text-[#d4ddd8] mx-auto mb-3" />
          <p className="text-sm text-[#7A8580]">No submissions yet. Share the link to <strong>/qualify</strong> to get started.</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-[rgba(59,77,67,0.08)] overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-[#EEF1EC]">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-[#7A8580] uppercase tracking-wide">Name</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-[#7A8580] uppercase tracking-wide hidden sm:table-cell">Company</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-[#7A8580] uppercase tracking-wide hidden md:table-cell">Role</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-[#7A8580] uppercase tracking-wide hidden lg:table-cell">Catalog size</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-[#7A8580] uppercase tracking-wide hidden lg:table-cell">Timeline</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-[#7A8580] uppercase tracking-wide">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[rgba(59,77,67,0.06)]">
                {records.map(r => (
                  <tr
                    key={r.id}
                    className="hover:bg-[#F8F9F7] cursor-pointer"
                    onClick={() => setSelected(r)}
                  >
                    <td className="px-4 py-3">
                      <div className="font-medium text-[#1D1D1F]">{r.full_name}</div>
                      <div className="text-xs text-[#7A8580]">{r.work_email}</div>
                    </td>
                    <td className="px-4 py-3 text-[#3D4A44] hidden sm:table-cell">
                      <div className="flex items-center gap-1.5">
                        <BuildingOfficeIcon className="w-3.5 h-3.5 text-[#7A8580] shrink-0" />
                        {r.company}
                      </div>
                    </td>
                    <td className="px-4 py-3 hidden md:table-cell">
                      <Badge color="sage">{r.role}</Badge>
                    </td>
                    <td className="px-4 py-3 text-[#3D4A44] hidden lg:table-cell">{r.catalog_size || '—'}</td>
                    <td className="px-4 py-3 hidden lg:table-cell">
                      {r.timeline ? <Badge color="gray">{r.timeline}</Badge> : '—'}
                    </td>
                    <td className="px-4 py-3 text-[#7A8580] text-xs">
                      <div className="flex items-center gap-1">
                        <CalendarDaysIcon className="w-3.5 h-3.5 shrink-0" />
                        {fmtDate(r.created_at)}
                      </div>
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
