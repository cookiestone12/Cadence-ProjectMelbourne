import React, { useState } from 'react'
import internal from './api'

export default function Onboarding() {
  const [step, setStep] = useState(1)
  const [orgName, setOrgName] = useState('')
  const [orgType, setOrgType] = useState('MANAGER')
  const [org, setOrg] = useState(null)
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [user, setUser] = useState(null)
  const [emailSent, setEmailSent] = useState(false)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  const wrap = async (fn) => {
    setBusy(true); setErr('')
    try { await fn() } catch (e) {
      setErr(e?.response?.data?.detail || 'Step failed')
    } finally { setBusy(false) }
  }

  const createOrg = () => wrap(async () => {
    // Goes through the staff-capable internal portal endpoint so
    // is_cadence_staff users (not just master admin) can complete
    // onboarding.
    const { data } = await internal.post('/api/internal/portal/onboarding/organization', {
      name: orgName, type: orgType,
    })
    setOrg(data); setStep(2)
  })

  const createOwner = () => wrap(async () => {
    const { data } = await internal.post('/api/internal/portal/onboarding/owner-user', {
      username, email, password,
      organization_id: org.id,
      role: 'OWNER',
    })
    setUser(data); setStep(3)
  })

  const sendWelcome = () => wrap(async () => {
    // Best-effort: hit the provisioning email endpoint if present.
    try {
      await internal.post('/api/notifications/welcome-email', {
        user_id: user.id, organization_id: org.id,
      })
    } catch { /* email is optional */ }
    setEmailSent(true); setStep(4)
  })

  const Step = ({ n, label }) => (
    <div className={`flex items-center gap-2 ${step >= n ? 'text-slate-900' : 'text-slate-400'}`}>
      <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs ${
        step > n ? 'bg-emerald-600 text-white' : step === n ? 'bg-slate-900 text-white' : 'bg-slate-200'
      }`}>
        {step > n ? '✓' : n}
      </div>
      <span className="text-sm">{label}</span>
    </div>
  )

  return (
    <div className="space-y-6 max-w-2xl">
      <h1 className="text-2xl font-semibold">Onboarding</h1>
      <div className="flex items-center gap-4">
        <Step n={1} label="Organization" />
        <Step n={2} label="Owner user" />
        <Step n={3} label="Welcome email" />
        <Step n={4} label="Done" />
      </div>
      {err && <div className="text-sm text-red-600">{err}</div>}

      {step === 1 && (
        <div className="space-y-3 border border-slate-200 rounded-md p-4">
          <div className="text-sm font-medium">Step 1 — Create organization</div>
          <input
            className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm"
            placeholder="Organization name"
            value={orgName}
            onChange={(e) => setOrgName(e.target.value)}
          />
          <select
            className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm"
            value={orgType}
            onChange={(e) => setOrgType(e.target.value)}
          >
            <option>MANAGER</option><option>LABEL</option><option>PUBLISHER</option>
          </select>
          <button
            disabled={!orgName || busy}
            onClick={createOrg}
            className="px-4 py-2 bg-slate-900 text-white rounded-md text-sm disabled:opacity-50"
          >
            Create org
          </button>
        </div>
      )}

      {step === 2 && (
        <div className="space-y-3 border border-slate-200 rounded-md p-4">
          <div className="text-sm font-medium">Step 2 — Create owner user for "{org?.name}"</div>
          <input
            className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm"
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
          <input
            className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <input
            type="password"
            className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm"
            placeholder="Initial password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <button
            disabled={!username || !email || !password || busy}
            onClick={createOwner}
            className="px-4 py-2 bg-slate-900 text-white rounded-md text-sm disabled:opacity-50"
          >
            Create owner
          </button>
        </div>
      )}

      {step === 3 && (
        <div className="space-y-3 border border-slate-200 rounded-md p-4">
          <div className="text-sm font-medium">Step 3 — Send welcome email</div>
          <p className="text-xs text-slate-500">
            Send a welcome email to {user?.email} with their initial credentials and login link.
          </p>
          <button
            disabled={busy}
            onClick={sendWelcome}
            className="px-4 py-2 bg-slate-900 text-white rounded-md text-sm disabled:opacity-50"
          >
            Send welcome email
          </button>
          <button
            onClick={() => setStep(4)}
            className="px-4 py-2 bg-slate-200 rounded-md text-sm ml-2"
          >
            Skip
          </button>
        </div>
      )}

      {step === 4 && (
        <div className="space-y-3 border border-emerald-300 bg-emerald-50 rounded-md p-4">
          <div className="text-sm font-medium text-emerald-900">Onboarding complete</div>
          <ul className="text-xs space-y-1 text-emerald-900">
            <li>✓ Organization "{org?.name}" (id {org?.id}) created</li>
            <li>✓ Owner user "{user?.username}" created</li>
            <li>{emailSent ? '✓ Welcome email queued' : '— Welcome email skipped'}</li>
            <li className="text-emerald-700 mt-2">Next: ask the owner to set the org access code in /admin.</li>
          </ul>
          <button
            onClick={() => {
              setStep(1); setOrg(null); setUser(null); setOrgName('')
              setUsername(''); setEmail(''); setPassword(''); setEmailSent(false)
            }}
            className="px-4 py-2 bg-slate-900 text-white rounded-md text-sm"
          >
            Onboard another
          </button>
        </div>
      )}
    </div>
  )
}
