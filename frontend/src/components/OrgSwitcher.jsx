import React, { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import { ChevronUpDownIcon, CheckIcon, BuildingOfficeIcon } from '@heroicons/react/24/outline'

export default function OrgSwitcher({ activeOrg, onSwitched }) {
  const [open, setOpen] = useState(false)
  const [orgs, setOrgs] = useState([])
  const [loading, setLoading] = useState(false)
  const [switching, setSwitching] = useState(false)
  const wrapRef = useRef(null)

  useEffect(() => {
    const onDocClick = (e) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', onDocClick)
    return () => document.removeEventListener('mousedown', onDocClick)
  }, [])

  // Eager-load on mount so the trigger label can show the active org's
  // name even before the parent's brand fetch resolves (a transient
  // backend hiccup would otherwise leave us stuck on the fallback).
  const loadOrgs = () => {
    setLoading(true)
    axios.get('/api/organizations/mine')
      .then(res => setOrgs(res.data?.organizations || []))
      .catch(() => setOrgs([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => { loadOrgs() }, [])

  useEffect(() => {
    if (open && orgs.length === 0 && !loading) loadOrgs()
  }, [open])

  const activeFromList = orgs.find(o => o.is_active)

  const handleSwitch = async (orgId) => {
    if (!orgId || switching) return
    if (activeOrg && orgId === activeOrg.id) {
      setOpen(false)
      return
    }
    setSwitching(true)
    setOpen(false)
    try {
      await axios.patch('/api/organizations/current', { organization_id: orgId })
      if (onSwitched) onSwitched(orgId)
      // Hard reload — every page caches its org-scoped data on first
      // mount, so a soft state update would leave widgets pointed at
      // the previous org's data until each one is revisited.
      window.location.reload()
    } catch (e) {
      setSwitching(false)
      alert(e?.response?.data?.detail || 'Failed to switch organization')
    }
  }

  const label =
    activeOrg?.display_name ||
    activeOrg?.name ||
    activeFromList?.display_name ||
    activeFromList?.name ||
    (loading ? 'Loading…' : 'Choose organization')

  return (
    <div ref={wrapRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        disabled={switching}
        className="w-full flex items-center justify-between gap-2 px-2 py-1 rounded-lg hover:bg-am-subtle text-left transition-all disabled:opacity-60"
        aria-label="Switch organization"
      >
        <span className="text-[12px] text-am-text-secondary truncate">
          {switching ? 'Switching…' : label}
        </span>
        <ChevronUpDownIcon className="w-4 h-4 text-am-text-secondary flex-shrink-0" />
      </button>

      {open && (
        <div className="absolute z-50 mt-1 left-0 right-0 bg-white rounded-xl border border-am-separator shadow-lg overflow-hidden">
          <div className="px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-am-text-secondary border-b border-am-separator">
            Switch organization
          </div>
          <div className="max-h-64 overflow-y-auto">
            {loading && (
              <div className="px-3 py-3 text-[13px] text-am-text-secondary">Loading…</div>
            )}
            {!loading && orgs.length === 0 && (
              <div className="px-3 py-3 text-[13px] text-am-text-secondary">No organizations</div>
            )}
            {!loading && orgs.map((o) => (
              <button
                key={o.id}
                type="button"
                onClick={() => handleSwitch(o.id)}
                disabled={switching}
                className={`w-full flex items-center gap-2 px-3 py-2 text-left text-[13px] hover:bg-am-subtle transition-colors disabled:opacity-50 ${o.is_active ? 'bg-am-subtle/60' : ''}`}
              >
                <BuildingOfficeIcon className="w-4 h-4 text-am-text-secondary flex-shrink-0" />
                <span className="flex-1 min-w-0 truncate font-medium text-am-text">
                  {o.display_name || o.name}
                </span>
                <span className="text-[11px] text-am-text-secondary uppercase tracking-wider flex-shrink-0">
                  {o.role}
                </span>
                {o.is_active && (
                  <CheckIcon className="w-4 h-4 text-am-accent flex-shrink-0" />
                )}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
