import React, { useState } from 'react'
import axios from 'axios'
import SEO from '../components/SEO'

const ROLE_OPTIONS = [
  'Label', 'Publisher', 'Artist/Songwriter', 'Manager',
  'Distributor', 'Catalog investor/fund', 'Rights administrator', 'Other',
]
const CATALOG_COVERAGE_OPTIONS = ['Masters', 'Publishing', 'Both', 'Still exploring']
const CATALOG_SIZE_OPTIONS = [
  'Under 100', '100-1,000', '1,000-10,000', '10,000-100,000', '100,000+',
]
const CURRENT_MANAGEMENT_OPTIONS = [
  'Spreadsheets', 'Distributor/admin dashboard', 'Dedicated platform',
  'Outsourced', 'No system yet',
]
const GOALS_OPTIONS = [
  'Royalty processing', 'Rights tracking', 'Catalog valuation',
  'Statement parsing', 'Stakeholder reporting', 'Acquisition due diligence', 'Other',
]
const TIMELINE_OPTIONS = ['Immediately', '1-3 months', '3-6 months', 'Just researching']

const SECTION = 'mb-6'
const LABEL = 'block text-sm font-semibold mb-1.5'
const INPUT = 'w-full px-3.5 py-2.5 rounded-md border border-[#d4ddd8] text-sm text-[#1D1D1F] bg-white focus:outline-none focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent transition'
const SELECT = INPUT
const TEXTAREA = `${INPUT} resize-none`
const ERROR_CLS = 'mt-1 text-xs text-red-600'

function MultiSelect({ options, value, onChange, name }) {
  const toggle = (opt) => {
    if (value.includes(opt)) onChange(value.filter(v => v !== opt))
    else onChange([...value, opt])
  }
  return (
    <div className="flex flex-wrap gap-2 mt-1">
      {options.map(opt => (
        <button
          key={opt}
          type="button"
          onClick={() => toggle(opt)}
          className={`px-3 py-1.5 rounded-md border text-sm transition-all ${
            value.includes(opt)
              ? 'bg-[#5B8A72] border-[#5B8A72] text-white font-medium'
              : 'bg-white border-[#d4ddd8] text-[#3D4A44] hover:border-[#5B8A72]'
          }`}
        >
          {opt}
        </button>
      ))}
    </div>
  )
}

export default function QualifyPage() {
  const [form, setForm] = useState({
    full_name: '', work_email: '', company: '', role: '',
    catalog_coverage: [], catalog_size: '', current_management: '',
    goals: [], reason_now: '', timeline: '', demo_notes: '',
    honeypot: '',
  })
  const [errors, setErrors] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [done, setDone] = useState(false)

  const set = (field, val) => setForm(f => ({ ...f, [field]: val }))

  const validate = () => {
    const e = {}
    if (!form.full_name.trim()) e.full_name = 'Full name is required.'
    if (!form.work_email.trim() || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.work_email))
      e.work_email = 'A valid work email is required.'
    if (!form.company.trim()) e.company = 'Company name is required.'
    if (!form.role) e.role = 'Please select your role.'
    return e
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    const e2 = validate()
    if (Object.keys(e2).length) { setErrors(e2); return }
    setErrors({})
    setSubmitting(true)
    try {
      await axios.post('/api/qualify', form)
      setDone(true)
    } catch (err) {
      const detail = err.response?.data?.detail
      if (Array.isArray(detail)) {
        const mapped = {}
        detail.forEach(d => {
          const field = d.loc?.[d.loc.length - 1]
          if (field) mapped[field] = d.msg
        })
        setErrors(mapped)
      } else {
        setErrors({ _general: detail || 'Something went wrong. Please try again.' })
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div style={{ fontFamily: '-apple-system, Inter, sans-serif', background: '#F8F9F7', minHeight: '100vh' }}>
      <SEO
        title="Request a Demo"
        description="Tell us about your catalog — we'll tailor the walkthrough to your rights, royalties, and revenue goals."
        path="/qualify"
        image="https://cadence-ci.com/qualify-og.png"
      />
      <div style={{ background: 'linear-gradient(135deg,#5B8A72 0%,#7BA594 100%)', padding: '20px 32px' }}>
        <img
          src="/assets/email/cadence-logo-white.png"
          alt="Cadence Catalog Intelligence"
          style={{ height: 36, display: 'block' }}
        />
      </div>

      <div style={{ maxWidth: 620, margin: '0 auto', padding: '40px 16px 64px' }}>
        {done ? (
          <div style={{ background: '#fff', borderRadius: 8, padding: '48px 40px', textAlign: 'center', border: '1px solid #d4ddd8' }}>
            <div style={{ width: 48, height: 48, background: '#5B8A72', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px' }}>
              <svg width="22" height="22" viewBox="0 0 20 20" fill="none">
                <path d="M4 10l4.5 4.5L16 6" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <h2 style={{ margin: '0 0 12px', color: '#1D1D1F', fontSize: 22, fontWeight: 700 }}>
              You are all set
            </h2>
            <p style={{ margin: 0, color: '#3D4A44', fontSize: 15, lineHeight: 1.6 }}>
              Thanks — we will review your responses and reach out to confirm next steps.
            </p>
          </div>
        ) : (
          <div style={{ background: '#fff', borderRadius: 8, padding: '40px 40px 36px', border: '1px solid #d4ddd8' }}>
            <h1 style={{ margin: '0 0 6px', color: '#1D1D1F', fontSize: 24, fontWeight: 700 }}>
              Tell us about your catalog
            </h1>
            <p style={{ margin: '0 0 32px', color: '#3D4A44', fontSize: 14, lineHeight: 1.6 }}>
              A couple of quick questions so we can tailor your demo. Takes about two minutes.
            </p>

            <form onSubmit={handleSubmit} noValidate>
              {/* Honeypot — hidden from real users */}
              <input
                type="text"
                name="honeypot"
                value={form.honeypot}
                onChange={e => set('honeypot', e.target.value)}
                style={{ display: 'none' }}
                tabIndex={-1}
                autoComplete="off"
              />

              <div className={SECTION}>
                <label className={LABEL} style={{ color: '#1D1D1F' }}>Full name <span style={{ color: '#e05252' }}>*</span></label>
                <input
                  className={INPUT}
                  type="text"
                  value={form.full_name}
                  onChange={e => set('full_name', e.target.value)}
                  placeholder="Jane Smith"
                />
                {errors.full_name && <p className={ERROR_CLS}>{errors.full_name}</p>}
              </div>

              <div className={SECTION}>
                <label className={LABEL} style={{ color: '#1D1D1F' }}>Work email <span style={{ color: '#e05252' }}>*</span></label>
                <input
                  className={INPUT}
                  type="email"
                  value={form.work_email}
                  onChange={e => set('work_email', e.target.value)}
                  placeholder="jane@label.com"
                />
                {errors.work_email && <p className={ERROR_CLS}>{errors.work_email}</p>}
              </div>

              <div className={SECTION}>
                <label className={LABEL} style={{ color: '#1D1D1F' }}>Company <span style={{ color: '#e05252' }}>*</span></label>
                <input
                  className={INPUT}
                  type="text"
                  value={form.company}
                  onChange={e => set('company', e.target.value)}
                  placeholder="Acme Music Group"
                />
                {errors.company && <p className={ERROR_CLS}>{errors.company}</p>}
              </div>

              <div className={SECTION}>
                <label className={LABEL} style={{ color: '#1D1D1F' }}>Your role <span style={{ color: '#e05252' }}>*</span></label>
                <select
                  className={SELECT}
                  value={form.role}
                  onChange={e => set('role', e.target.value)}
                >
                  <option value="">Select one</option>
                  {ROLE_OPTIONS.map(r => <option key={r} value={r}>{r}</option>)}
                </select>
                {errors.role && <p className={ERROR_CLS}>{errors.role}</p>}
              </div>

              <div className={SECTION}>
                <label className={LABEL} style={{ color: '#1D1D1F' }}>What does your catalog cover?</label>
                <MultiSelect
                  options={CATALOG_COVERAGE_OPTIONS}
                  value={form.catalog_coverage}
                  onChange={v => set('catalog_coverage', v)}
                />
              </div>

              <div className={SECTION}>
                <label className={LABEL} style={{ color: '#1D1D1F' }}>Catalog size (number of assets)</label>
                <select
                  className={SELECT}
                  value={form.catalog_size}
                  onChange={e => set('catalog_size', e.target.value)}
                >
                  <option value="">Select one</option>
                  {CATALOG_SIZE_OPTIONS.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>

              <div className={SECTION}>
                <label className={LABEL} style={{ color: '#1D1D1F' }}>How do you manage your catalog today?</label>
                <select
                  className={SELECT}
                  value={form.current_management}
                  onChange={e => set('current_management', e.target.value)}
                >
                  <option value="">Select one</option>
                  {CURRENT_MANAGEMENT_OPTIONS.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>

              <div className={SECTION}>
                <label className={LABEL} style={{ color: '#1D1D1F' }}>What are you hoping to solve?</label>
                <MultiSelect
                  options={GOALS_OPTIONS}
                  value={form.goals}
                  onChange={v => set('goals', v)}
                />
              </div>

              <div className={SECTION}>
                <label className={LABEL} style={{ color: '#1D1D1F' }}>What is prompting you to look now? <span style={{ color: '#7A8580', fontWeight: 400 }}>(optional)</span></label>
                <textarea
                  className={TEXTAREA}
                  rows={3}
                  value={form.reason_now}
                  onChange={e => set('reason_now', e.target.value)}
                  placeholder="A contract renewal, a fund raise, new hires..."
                />
              </div>

              <div className={SECTION}>
                <label className={LABEL} style={{ color: '#1D1D1F' }}>How soon are you looking to get started?</label>
                <select
                  className={SELECT}
                  value={form.timeline}
                  onChange={e => set('timeline', e.target.value)}
                >
                  <option value="">Select one</option>
                  {TIMELINE_OPTIONS.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>

              <div className={SECTION}>
                <label className={LABEL} style={{ color: '#1D1D1F' }}>Anything specific you want us to cover in the demo? <span style={{ color: '#7A8580', fontWeight: 400 }}>(optional)</span></label>
                <textarea
                  className={TEXTAREA}
                  rows={3}
                  value={form.demo_notes}
                  onChange={e => set('demo_notes', e.target.value)}
                  placeholder="Particular workflows, integrations, or questions..."
                />
              </div>

              {errors._general && (
                <div className="mb-4 px-4 py-3 rounded-md bg-red-50 border border-red-200 text-sm text-red-700">
                  {errors._general}
                </div>
              )}

              <button
                type="submit"
                disabled={submitting}
                style={{
                  width: '100%', padding: '12px 0', borderRadius: 6,
                  background: submitting ? '#7BA594' : '#5B8A72',
                  color: '#fff', fontWeight: 600, fontSize: 15,
                  border: 'none', cursor: submitting ? 'not-allowed' : 'pointer',
                  transition: 'background 0.15s',
                }}
              >
                {submitting ? 'Submitting...' : 'Request a demo'}
              </button>
            </form>
          </div>
        )}

        <p style={{ textAlign: 'center', marginTop: 24, color: '#7A8580', fontSize: 12 }}>
          Cadence Catalog Intelligence — your information is used only to schedule and tailor your demo.
        </p>
      </div>
    </div>
  )
}
