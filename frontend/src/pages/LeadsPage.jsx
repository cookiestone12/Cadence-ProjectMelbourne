import React, { useState, useEffect, useMemo } from 'react'
import axios from 'axios'
import { EnvelopeIcon, ArrowPathIcon } from '@heroicons/react/24/outline'

const TYPE_LABELS = {
  WAITLIST: 'Waitlist',
  DEMO_REQUEST: 'Demo Request',
  INVESTOR_INQUIRY: 'Investor',
  INTERN_APPLICATION: 'Intern',
}

const TYPE_PILL_CLASSES = {
  WAITLIST: 'bg-amber-50 text-amber-700',
  DEMO_REQUEST: 'bg-[#EAF1EC] text-[#5B8A72]',
  INVESTOR_INQUIRY: 'bg-indigo-50 text-indigo-700',
  INTERN_APPLICATION: 'bg-slate-100 text-slate-600',
}

const TABS = [
  { key: 'all', label: 'All' },
  { key: 'WAITLIST', label: 'Waitlist' },
  { key: 'DEMO_REQUEST', label: 'Demo Requests' },
  { key: 'other', label: 'Other' },
]

const STATUS_TABS = [
  { key: 'all', label: 'All' },
  { key: 'new', label: 'New' },
  { key: 'contacted', label: 'Contacted' },
]

const EMAIL_TYPE_LABELS = {
  qualify: 'Qualifier email',
  demo_schedule: 'Demo scheduling email',
}

function typeLabel(t) {
  return TYPE_LABELS[t] || t || 'Unknown'
}

function emailTypeLabel(t) {
  if (!t) return 'Outreach email'
  return EMAIL_TYPE_LABELS[t] || t
}

function formatDate(iso) {
  if (!iso) return '-'
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  } catch {
    return '-'
  }
}

function emailTypeForLead(lead) {
  if (lead.lead_type === 'DEMO_REQUEST') return 'demo_schedule'
  if (lead.lead_type === 'WAITLIST') return 'qualify'
  return null
}

export default function LeadsPage() {
  const [leads, setLeads] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('all')
  const [statusTab, setStatusTab] = useState('all')
  const [sendingId, setSendingId] = useState(null)
  const [actionError, setActionError] = useState(null)

  const fetchLeads = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await axios.get('/api/admin/leads')
      setLeads(res.data.leads || [])
    } catch (e) {
      setError('Could not load leads. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchLeads()
  }, [])

  const counts = useMemo(() => {
    const c = { all: leads.length, WAITLIST: 0, DEMO_REQUEST: 0, other: 0 }
    for (const l of leads) {
      if (l.lead_type === 'WAITLIST') c.WAITLIST += 1
      else if (l.lead_type === 'DEMO_REQUEST') c.DEMO_REQUEST += 1
      else c.other += 1
    }
    return c
  }, [leads])

  const statusCounts = useMemo(() => {
    const c = { all: leads.length, new: 0, contacted: 0 }
    for (const l of leads) {
      if (l.status === 'contacted') c.contacted += 1
      else c.new += 1
    }
    return c
  }, [leads])

  const visibleLeads = useMemo(() => {
    let rows = leads
    if (activeTab === 'other') {
      rows = rows.filter(
        (l) => l.lead_type !== 'WAITLIST' && l.lead_type !== 'DEMO_REQUEST'
      )
    } else if (activeTab !== 'all') {
      rows = rows.filter((l) => l.lead_type === activeTab)
    }
    if (statusTab === 'contacted') {
      rows = rows.filter((l) => l.status === 'contacted')
    } else if (statusTab === 'new') {
      rows = rows.filter((l) => l.status !== 'contacted')
    }
    return rows
  }, [leads, activeTab, statusTab])

  const handleContact = async (lead) => {
    const emailType = emailTypeForLead(lead)
    if (!emailType) return
    setSendingId(lead.id)
    setActionError(null)
    try {
      const res = await axios.post(`/api/admin/leads/${lead.id}/contact`, {
        email_type: emailType,
      })
      const contactedAt = res?.data?.contacted_at || new Date().toISOString()
      const contactedType = res?.data?.contacted_email_type || emailType
      setLeads((prev) =>
        prev.map((l) =>
          l.id === lead.id
            ? {
                ...l,
                status: 'contacted',
                contacted_at: contactedAt,
                contacted_email_type: contactedType,
              }
            : l
        )
      )
    } catch (e) {
      setActionError(
        `Could not send the email to ${lead.email}. Please try again.`
      )
    } finally {
      setSendingId(null)
    }
  }

  return (
    <div className="min-h-screen bg-[#F5F7F4] p-6">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-semibold text-[#3D4A44]">Leads</h1>
            <p className="text-sm text-[#7A8580] mt-1">
              Outreach to waitlist signups and demo requests.
            </p>
          </div>
          <button
            onClick={fetchLeads}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-white text-[#3D4A44] text-sm font-medium border border-[#E2E8E3] hover:bg-[#EAF1EC] transition-colors"
          >
            <ArrowPathIcon className="w-4 h-4" />
            Refresh
          </button>
        </div>

        <div className="flex flex-wrap gap-2 mb-5">
          {TABS.map((tab) => {
            const isActive = activeTab === tab.key
            return (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-[#5B8A72] text-white'
                    : 'bg-white text-[#3D4A44] border border-[#E2E8E3] hover:bg-[#EAF1EC]'
                }`}
              >
                {tab.label}
                <span
                  className={`text-xs px-2 py-0.5 rounded-full ${
                    isActive ? 'bg-white/25 text-white' : 'bg-[#F5F7F4] text-[#7A8580]'
                  }`}
                >
                  {counts[tab.key]}
                </span>
              </button>
            )
          })}
        </div>

        <div className="flex flex-wrap items-center gap-2 mb-5">
          <span className="text-xs font-medium text-[#7A8580] mr-1">Status</span>
          {STATUS_TABS.map((tab) => {
            const isActive = statusTab === tab.key
            return (
              <button
                key={tab.key}
                onClick={() => setStatusTab(tab.key)}
                className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                  isActive
                    ? 'bg-[#3D4A44] text-white'
                    : 'bg-white text-[#3D4A44] border border-[#E2E8E3] hover:bg-[#EAF1EC]'
                }`}
              >
                {tab.label}
                <span
                  className={`text-xs px-2 py-0.5 rounded-full ${
                    isActive ? 'bg-white/25 text-white' : 'bg-[#F5F7F4] text-[#7A8580]'
                  }`}
                >
                  {statusCounts[tab.key]}
                </span>
              </button>
            )
          })}
        </div>

        {actionError && (
          <div className="mb-4 px-4 py-3 rounded-xl bg-red-50 text-red-700 text-sm">
            {actionError}
          </div>
        )}

        <div className="bg-white rounded-2xl border border-[#E2E8E3] overflow-hidden">
          {loading ? (
            <div className="p-10 text-center text-[#7A8580]">Loading leads...</div>
          ) : error ? (
            <div className="p-10 text-center">
              <p className="text-[#3D4A44] mb-3">{error}</p>
              <button
                onClick={fetchLeads}
                className="px-4 py-2 rounded-xl bg-[#5B8A72] text-white text-sm font-medium hover:opacity-90"
              >
                Retry
              </button>
            </div>
          ) : visibleLeads.length === 0 ? (
            <div className="p-10 text-center text-[#7A8580]">
              No leads in this view yet.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-[#7A8580] border-b border-[#E2E8E3]">
                    <th className="px-4 py-3 font-medium">Name</th>
                    <th className="px-4 py-3 font-medium">Email</th>
                    <th className="px-4 py-3 font-medium">Company</th>
                    <th className="px-4 py-3 font-medium">Type</th>
                    <th className="px-4 py-3 font-medium">Status</th>
                    <th className="px-4 py-3 font-medium">Received</th>
                    <th className="px-4 py-3 font-medium">Outreach</th>
                    <th className="px-4 py-3 font-medium text-right">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleLeads.map((lead) => {
                    const emailType = emailTypeForLead(lead)
                    const isContacted = lead.status === 'contacted'
                    const isSending = sendingId === lead.id
                    return (
                      <tr
                        key={lead.id}
                        className="border-b border-[#F0F3F0] last:border-0 hover:bg-[#FAFBFA]"
                      >
                        <td className="px-4 py-3 text-[#3D4A44]">
                          {lead.name || '-'}
                        </td>
                        <td className="px-4 py-3 text-[#3D4A44]">{lead.email}</td>
                        <td className="px-4 py-3 text-[#7A8580]">
                          {lead.company || '-'}
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={`inline-block px-2.5 py-1 rounded-full text-xs font-medium ${
                              TYPE_PILL_CLASSES[lead.lead_type] ||
                              'bg-slate-100 text-slate-600'
                            }`}
                          >
                            {typeLabel(lead.lead_type)}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          {isContacted ? (
                            <span className="inline-block px-2.5 py-1 rounded-full text-xs font-medium bg-[#EAF1EC] text-[#5B8A72]">
                              Contacted
                            </span>
                          ) : (
                            <span className="inline-block px-2.5 py-1 rounded-full text-xs font-medium bg-amber-50 text-amber-700">
                              New
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-[#7A8580]">
                          {formatDate(lead.created_at)}
                        </td>
                        <td className="px-4 py-3 text-[#7A8580]">
                          {isContacted ? (
                            <div className="leading-tight">
                              <div className="text-[#3D4A44]">
                                {emailTypeLabel(lead.contacted_email_type)}
                              </div>
                              <div className="text-xs text-[#7A8580]">
                                Sent {formatDate(lead.contacted_at)}
                              </div>
                            </div>
                          ) : (
                            <span className="text-[#A6AFA9]">Not contacted</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right">
                          {emailType ? (
                            <button
                              onClick={() => handleContact(lead)}
                              disabled={isSending || isContacted}
                              className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                                isContacted
                                  ? 'bg-[#F0F3F0] text-[#7A8580] cursor-default'
                                  : isSending
                                  ? 'bg-[#5B8A72]/60 text-white cursor-wait'
                                  : 'bg-[#5B8A72] text-white hover:opacity-90'
                              }`}
                            >
                              <EnvelopeIcon className="w-4 h-4" />
                              {isContacted
                                ? 'Sent'
                                : isSending
                                ? 'Sending...'
                                : lead.lead_type === 'DEMO_REQUEST'
                                ? 'Send demo email'
                                : 'Send qualifier'}
                            </button>
                          ) : (
                            <span className="text-xs text-[#A6AFA9]">No action</span>
                          )}
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
    </div>
  )
}
