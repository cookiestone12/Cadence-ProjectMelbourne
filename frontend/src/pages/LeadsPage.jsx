import React, { useState, useEffect, useMemo } from 'react'
import axios from 'axios'
import {
  EnvelopeIcon,
  ArrowPathIcon,
  PencilSquareIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline'

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
  const [showTemplates, setShowTemplates] = useState(false)

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
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowTemplates(true)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-white text-[#3D4A44] text-sm font-medium border border-[#E2E8E3] hover:bg-[#EAF1EC] transition-colors"
            >
              <PencilSquareIcon className="w-4 h-4" />
              Edit email templates
            </button>
            <button
              onClick={fetchLeads}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-white text-[#3D4A44] text-sm font-medium border border-[#E2E8E3] hover:bg-[#EAF1EC] transition-colors"
            >
              <ArrowPathIcon className="w-4 h-4" />
              Refresh
            </button>
          </div>
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

      {showTemplates && (
        <TemplateEditorModal onClose={() => setShowTemplates(false)} />
      )}
    </div>
  )
}

function TemplateEditorModal({ onClose }) {
  const [templates, setTemplates] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedKey, setSelectedKey] = useState(null)
  const [draft, setDraft] = useState(null)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState(null)
  const [savedNote, setSavedNote] = useState(null)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await axios.get('/api/admin/email-templates')
      const list = res.data.templates || []
      setTemplates(list)
      if (list.length > 0) {
        setSelectedKey((prev) => prev || list[0].template_key)
      }
    } catch (e) {
      setError('Could not load templates. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  useEffect(() => {
    const t = templates.find((x) => x.template_key === selectedKey)
    if (t) {
      setDraft({ subject: t.subject, header: t.header, body: t.body })
      setSaveError(null)
      setSavedNote(null)
    }
  }, [selectedKey, templates])

  const selected = templates.find((x) => x.template_key === selectedKey)

  const handleSave = async () => {
    if (!selected || !draft) return
    setSaving(true)
    setSaveError(null)
    setSavedNote(null)
    try {
      const res = await axios.put(
        `/api/admin/email-templates/${selected.template_key}`,
        {
          subject: draft.subject,
          header: draft.header,
          body: draft.body,
        }
      )
      const updated = res.data
      setTemplates((prev) =>
        prev.map((t) => (t.template_key === updated.template_key ? updated : t))
      )
      setSavedNote('Saved. New emails will use this wording.')
    } catch (e) {
      setSaveError(
        e?.response?.data?.detail || 'Could not save. Please try again.'
      )
    } finally {
      setSaving(false)
    }
  }

  const isDirty =
    selected &&
    draft &&
    (draft.subject !== selected.subject ||
      draft.header !== selected.header ||
      draft.body !== selected.body)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white rounded-2xl w-full max-w-3xl max-h-[90vh] flex flex-col overflow-hidden shadow-xl">
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#E2E8E3]">
          <div>
            <h2 className="text-lg font-semibold text-[#3D4A44]">
              Email templates
            </h2>
            <p className="text-xs text-[#7A8580] mt-0.5">
              Edit the wording of the outreach emails. Use{' '}
              <code className="px-1 py-0.5 bg-[#F0F3F0] rounded text-[#5B8A72]">
                {'{first_name}'}
              </code>{' '}
              to insert the recipient's first name.
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-[#7A8580] hover:bg-[#F0F3F0] hover:text-[#3D4A44]"
          >
            <XMarkIcon className="w-5 h-5" />
          </button>
        </div>

        {loading ? (
          <div className="p-10 text-center text-[#7A8580]">
            Loading templates...
          </div>
        ) : error ? (
          <div className="p-10 text-center">
            <p className="text-[#3D4A44] mb-3">{error}</p>
            <button
              onClick={load}
              className="px-4 py-2 rounded-xl bg-[#5B8A72] text-white text-sm font-medium hover:opacity-90"
            >
              Retry
            </button>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto">
            <div className="px-6 pt-4 flex flex-wrap gap-2">
              {templates.map((t) => (
                <button
                  key={t.template_key}
                  onClick={() => setSelectedKey(t.template_key)}
                  className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                    selectedKey === t.template_key
                      ? 'bg-[#5B8A72] text-white'
                      : 'bg-white text-[#3D4A44] border border-[#E2E8E3] hover:bg-[#EAF1EC]'
                  }`}
                >
                  {t.name}
                </button>
              ))}
            </div>

            {selected && draft && (
              <div className="px-6 py-5 space-y-4">
                <div className="text-xs text-[#7A8580]">
                  {selected.lead_type
                    ? `Sent to ${typeLabel(selected.lead_type)} leads`
                    : 'Not mapped to a lead type'}
                </div>

                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">
                    Subject line
                  </label>
                  <input
                    type="text"
                    value={draft.subject}
                    onChange={(e) =>
                      setDraft((d) => ({ ...d, subject: e.target.value }))
                    }
                    className="w-full px-3 py-2 rounded-lg border border-[#E2E8E3] text-sm text-[#3D4A44] focus:outline-none focus:ring-2 focus:ring-[#5B8A72]/40"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">
                    Header (banner title)
                  </label>
                  <input
                    type="text"
                    value={draft.header}
                    onChange={(e) =>
                      setDraft((d) => ({ ...d, header: e.target.value }))
                    }
                    className="w-full px-3 py-2 rounded-lg border border-[#E2E8E3] text-sm text-[#3D4A44] focus:outline-none focus:ring-2 focus:ring-[#5B8A72]/40"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">
                    Body
                  </label>
                  <textarea
                    value={draft.body}
                    onChange={(e) =>
                      setDraft((d) => ({ ...d, body: e.target.value }))
                    }
                    rows={14}
                    className="w-full px-3 py-2 rounded-lg border border-[#E2E8E3] text-sm text-[#3D4A44] font-mono leading-relaxed focus:outline-none focus:ring-2 focus:ring-[#5B8A72]/40"
                  />
                  <p className="text-xs text-[#7A8580] mt-1">
                    Leave a blank line between paragraphs. Plain text only — no
                    HTML needed.
                  </p>
                </div>

                {saveError && (
                  <div className="px-4 py-2.5 rounded-lg bg-red-50 text-red-700 text-sm">
                    {saveError}
                  </div>
                )}
                {savedNote && (
                  <div className="px-4 py-2.5 rounded-lg bg-[#EAF1EC] text-[#5B8A72] text-sm">
                    {savedNote}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        <div className="flex items-center justify-end gap-2 px-6 py-4 border-t border-[#E2E8E3]">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-white text-[#3D4A44] text-sm font-medium border border-[#E2E8E3] hover:bg-[#F0F3F0]"
          >
            Close
          </button>
          <button
            onClick={handleSave}
            disabled={saving || !isDirty}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
              saving || !isDirty
                ? 'bg-[#5B8A72]/50 text-white cursor-not-allowed'
                : 'bg-[#5B8A72] text-white hover:opacity-90'
            }`}
          >
            {saving ? 'Saving...' : 'Save changes'}
          </button>
        </div>
      </div>
    </div>
  )
}
