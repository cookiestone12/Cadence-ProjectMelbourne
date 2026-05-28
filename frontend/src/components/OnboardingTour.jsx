import React, { useEffect, useLayoutEffect, useState, useRef } from 'react'
import axios from 'axios'
import { XMarkIcon } from '@heroicons/react/24/outline'

/**
 * Task #206 — One-time post-login onboarding tour.
 *
 * Renders a dismissible step-by-step overlay that walks new users through
 * the core areas of Cadence: Catalog, Royalties, Settings, and — for
 * admins — the Team tab (called out because the welcome email tells admins
 * to invite their team from there).
 *
 * Each step "anchors" to a sidebar item via a `data-tour` attribute and
 * positions a tooltip card next to it. On small screens (where the
 * sidebar is off-canvas) the card falls back to a centered modal.
 *
 * Completion (and Skip) call `POST /api/auth/onboarding-complete` so the
 * tour never appears again for this user. We also write the timestamp
 * into the local `user` blob so the same browser tab doesn't reopen the
 * tour after the API call resolves.
 */
export default function OnboardingTour({ user, onDismiss }) {
  const isAdmin = !!(user?.is_admin || user?.role === 'OWNER' || user?.role === 'ADMIN')

  const steps = [
    {
      key: 'welcome',
      target: null,
      title: `Welcome to Cadence, ${user?.username || 'there'}!`,
      body:
        "Let's take a quick 30-second tour of the areas you'll use most. " +
        "You can skip at any time — we won't show this again.",
    },
    {
      key: 'catalog',
      target: 'catalog',
      title: 'Your Catalog',
      body:
        'Browse and manage every song, release, and master recording in ' +
        'your organization. This is your single source of truth for ' +
        'metadata, rights splits, and registrations.',
    },
    {
      key: 'royalties',
      target: 'royalties',
      title: 'Royalties',
      body:
        'Upload royalty statements from PROs, MLC, distributors and labels. ' +
        'Cadence parses, matches, and reconciles them automatically so you ' +
        'always know who earned what.',
    },
    ...(isAdmin
      ? [
          {
            key: 'team',
            target: 'team',
            title: 'Your Team',
            body:
              "As an admin, you can invite teammates and manage roles here. " +
              "The welcome email we sent points new users to this same flow.",
          },
        ]
      : []),
    {
      key: 'settings',
      target: 'settings',
      title: 'Settings',
      body:
        'Notification preferences, integrations (Dropbox, Spotify), ' +
        'security, and your organization profile all live in Settings.',
    },
  ]

  const [stepIdx, setStepIdx] = useState(0)
  const [anchorRect, setAnchorRect] = useState(null)
  const [saving, setSaving] = useState(false)
  const cardRef = useRef(null)

  const step = steps[stepIdx]
  const isLast = stepIdx === steps.length - 1

  // Recompute anchor position whenever the active step changes or the
  // window resizes (e.g. orientation flip on tablet).
  useLayoutEffect(() => {
    const compute = () => {
      if (!step?.target) {
        setAnchorRect(null)
        return
      }
      const el = document.querySelector(`[data-tour="${step.target}"]`)
      if (!el) {
        setAnchorRect(null)
        return
      }
      // Make sure the anchor is visible (sidebar section collapsed, etc).
      try {
        el.scrollIntoView({ block: 'center', behavior: 'auto' })
      } catch {
        /* older browsers */
      }
      const r = el.getBoundingClientRect()
      setAnchorRect({ top: r.top, left: r.left, width: r.width, height: r.height })
    }
    compute()
    window.addEventListener('resize', compute)
    return () => window.removeEventListener('resize', compute)
  }, [stepIdx, step?.target])

  const persistCompletion = async () => {
    setSaving(true)
    try {
      await axios.post('/api/auth/onboarding-complete')
    } catch (e) {
      console.error('Failed to mark onboarding complete', e)
    } finally {
      setSaving(false)
      // Update the cached user blob so a tab refresh doesn't reopen the tour
      try {
        const raw = localStorage.getItem('user')
        if (raw) {
          const u = JSON.parse(raw)
          u.onboarding_completed_at = new Date().toISOString()
          localStorage.setItem('user', JSON.stringify(u))
        }
      } catch {
        /* ignore */
      }
      if (onDismiss) onDismiss()
    }
  }

  const handleNext = () => {
    if (isLast) {
      persistCompletion()
    } else {
      setStepIdx((i) => i + 1)
    }
  }

  const handleBack = () => {
    if (stepIdx > 0) setStepIdx((i) => i - 1)
  }

  // Position the card next to the anchor on desktop, or center it when
  // there's no anchor (welcome step) or on small viewports.
  const isSmallScreen = typeof window !== 'undefined' && window.innerWidth < 1024
  const cardPos = (() => {
    if (!anchorRect || isSmallScreen) {
      return {
        position: 'fixed',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
      }
    }
    const gap = 16
    const cardWidth = 360
    const top = Math.max(16, Math.min(anchorRect.top, window.innerHeight - 280))
    const left = Math.min(
      window.innerWidth - cardWidth - 16,
      anchorRect.left + anchorRect.width + gap,
    )
    return { position: 'fixed', top: `${top}px`, left: `${left}px` }
  })()

  // Highlight ring around the anchor element.
  const ringStyle = anchorRect && !isSmallScreen
    ? {
        position: 'fixed',
        top: `${anchorRect.top - 6}px`,
        left: `${anchorRect.left - 6}px`,
        width: `${anchorRect.width + 12}px`,
        height: `${anchorRect.height + 12}px`,
        borderRadius: '12px',
        boxShadow: '0 0 0 3px #5B8A72, 0 0 0 9999px rgba(0,0,0,0.45)',
        pointerEvents: 'none',
        transition: 'all 200ms ease',
        zIndex: 9998,
      }
    : null

  return (
    <div className="fixed inset-0 z-[9999]" aria-modal="true" role="dialog">
      {/* Backdrop — when no anchor, we use a plain dim layer. When an
          anchor is present, the ring's giant outer box-shadow already
          dims everything else, so we skip the backdrop to avoid stacking. */}
      {(!ringStyle) && (
        <div className="absolute inset-0 bg-black/55" />
      )}
      {ringStyle && <div style={ringStyle} />}

      <div
        ref={cardRef}
        style={{ ...cardPos, width: '360px', maxWidth: 'calc(100vw - 32px)', zIndex: 9999 }}
        className="bg-white rounded-2xl shadow-2xl border border-[rgba(59,77,67,0.12)] p-6"
      >
        <div className="flex items-start justify-between gap-3 mb-3">
          <div>
            <div className="text-[11px] uppercase tracking-wide font-semibold text-[#5B8A72] mb-1">
              Step {stepIdx + 1} of {steps.length}
            </div>
            <h3 className="text-lg font-bold text-[#3D4A44]">{step.title}</h3>
          </div>
          <button
            onClick={persistCompletion}
            disabled={saving}
            aria-label="Skip tour"
            className="text-[#7A8580] hover:text-[#3D4A44] -m-1 p-1 rounded-full hover:bg-[rgba(59,77,67,0.06)] disabled:opacity-50"
          >
            <XMarkIcon className="w-5 h-5" />
          </button>
        </div>

        <p className="text-sm text-[#5A6660] leading-relaxed">{step.body}</p>

        <div className="mt-5 flex items-center justify-between">
          <button
            onClick={persistCompletion}
            disabled={saving}
            className="text-xs font-medium text-[#7A8580] hover:text-[#3D4A44] underline-offset-2 hover:underline disabled:opacity-50"
          >
            Skip tour
          </button>
          <div className="flex items-center gap-2">
            {stepIdx > 0 && (
              <button
                onClick={handleBack}
                disabled={saving}
                className="px-3 py-1.5 text-sm font-medium rounded-lg text-[#3D4A44] hover:bg-[rgba(59,77,67,0.06)] disabled:opacity-50"
              >
                Back
              </button>
            )}
            <button
              onClick={handleNext}
              disabled={saving}
              className="px-4 py-1.5 text-sm font-semibold rounded-lg bg-[#5B8A72] text-white hover:bg-[#4A7A62] disabled:opacity-60"
            >
              {isLast ? (saving ? 'Saving…' : 'Got it') : 'Next'}
            </button>
          </div>
        </div>

        {/* Dot indicators */}
        <div className="mt-4 flex items-center justify-center gap-1.5">
          {steps.map((s, i) => (
            <span
              key={s.key}
              className={`w-1.5 h-1.5 rounded-full transition-colors ${
                i === stepIdx ? 'bg-[#5B8A72]' : 'bg-[rgba(59,77,67,0.18)]'
              }`}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
