import React, { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import PublicFooter from '../components/PublicFooter'

function useInView(ref, threshold = 0.15) {
  const [inView, setInView] = useState(false)
  useEffect(() => {
    if (!ref.current) return
    const obs = new IntersectionObserver(([e]) => { if (e.isIntersecting) setInView(true) }, { threshold })
    obs.observe(ref.current)
    return () => obs.disconnect()
  }, [ref, threshold])
  return inView
}

function FadeIn({ children, className = '', delay = 0 }) {
  const ref = useRef(null)
  const visible = useInView(ref)
  return (
    <div
      ref={ref}
      className={`transition-all duration-700 ease-out ${visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'} ${className}`}
      style={{ transitionDelay: `${delay}ms` }}
    >
      {children}
    </div>
  )
}

export default function InvestorsPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState({ name: '', email: '', firm: '', investment_focus: '', message: '' })
  const [status, setStatus] = useState(null)
  const [statusType, setStatusType] = useState(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.name.trim() || !form.email.trim() || !form.firm.trim()) return
    setLoading(true)
    try {
      const res = await axios.post('/api/public/investor-inquiry', form)
      setStatus(res.data.message)
      setStatusType('success')
      setForm({ name: '', email: '', firm: '', investment_focus: '', message: '' })
    } catch (err) {
      setStatus(err.response?.data?.detail || 'Something went wrong. Please try again.')
      setStatusType('error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#FAFBF9] overflow-x-hidden">
      <nav className="fixed top-0 left-0 right-0 z-50 bg-[#FAFBF9]/80 backdrop-blur-xl border-b border-[rgba(59,77,67,0.06)]">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center cursor-pointer" onClick={() => navigate('/')}>
            <img src="/cadence-logo-full.png" alt="Cadence - Catalog Intelligence" className="h-12 w-auto" />
          </div>
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/careers')}
              className="hidden sm:inline-flex text-[14px] font-medium text-[#7A8580] hover:text-[#5B8A72] transition-colors"
            >
              Careers
            </button>
            <button
              onClick={() => navigate('/login')}
              className="text-[14px] font-medium text-[#5B8A72] hover:text-[#4A7A62] transition-colors px-4 py-2 rounded-full hover:bg-[#5B8A72]/8"
            >
              Sign In
            </button>
          </div>
        </div>
      </nav>

      <section className="relative pt-32 pb-16 px-6 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-[#5B8A72]/5 via-transparent to-[#7BA594]/5" />
        <div className="absolute top-20 left-1/4 w-96 h-96 bg-[#5B8A72]/5 rounded-full blur-3xl" />
        <div className="absolute bottom-0 right-1/4 w-80 h-80 bg-[#7BA594]/5 rounded-full blur-3xl" />

        <div className="max-w-4xl mx-auto text-center relative z-10">
          <FadeIn>
            <p className="text-[13px] font-semibold tracking-[0.2em] uppercase text-[#5B8A72]/60 mb-4">
              Investor Relations
            </p>
          </FadeIn>

          <FadeIn delay={100}>
            <h1 className="text-[36px] sm:text-[52px] lg:text-[60px] font-bold text-[#3D4A44] leading-[1.1] tracking-tight mb-6">
              Invest in the intelligence layer for{' '}
              <span className="bg-gradient-to-r from-[#5B8A72] to-[#7BA594] bg-clip-text text-transparent">
                music catalogs.
              </span>
            </h1>
          </FadeIn>

          <FadeIn delay={200}>
            <p className="text-[17px] sm:text-[20px] text-[#7A8580] max-w-2xl mx-auto leading-relaxed">
              Cadence is building the operating system for music rights and royalties. We're raising to accelerate product development and go-to-market.
            </p>
          </FadeIn>
        </div>
      </section>

      <section className="py-12 px-6">
        <div className="max-w-5xl mx-auto">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {[
              {
                label: 'Market',
                value: '$43B+',
                sub: 'Global music rights market',
                icon: (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A11.953 11.953 0 0112 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0121 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0112 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 013 12c0-1.605.42-3.113 1.157-4.418" />
                  </svg>
                ),
              },
              {
                label: 'Model',
                value: 'B2B SaaS',
                sub: 'Recurring revenue platform',
                icon: (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
                  </svg>
                ),
              },
              {
                label: 'Stage',
                value: 'Pre-Seed',
                sub: 'Product built, approaching beta',
                icon: (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15.59 14.37a6 6 0 01-5.84 7.38v-4.8m5.84-2.58a14.98 14.98 0 006.16-12.12A14.98 14.98 0 009.631 8.41m5.96 5.96a14.926 14.926 0 01-5.841 2.58m-.119-8.54a6 6 0 00-7.381 5.84h4.8m2.581-5.84a14.927 14.927 0 00-2.58 5.84m2.699 2.7c-.103.021-.207.041-.311.06a15.09 15.09 0 01-2.448-2.448 14.9 14.9 0 01.06-.312m-2.24 2.39a4.493 4.493 0 00-1.757 4.306 4.493 4.493 0 004.306-1.758M16.5 9a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0z" />
                  </svg>
                ),
              },
              {
                label: 'Team',
                value: '3 Founders',
                sub: 'Industry + enterprise tech DNA',
                icon: (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M18 18.72a9.094 9.094 0 003.741-.479 3 3 0 00-4.682-2.72m.94 3.198l.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0112 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 016 18.719m12 0a5.971 5.971 0 00-.941-3.197m0 0A5.995 5.995 0 0012 12.75a5.995 5.995 0 00-5.058 2.772m0 0a3 3 0 00-4.681 2.72 8.986 8.986 0 003.74.477m.94-3.197a5.971 5.971 0 00-.94 3.197M15 6.75a3 3 0 11-6 0 3 3 0 016 0zm6 3a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0zm-13.5 0a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0z" />
                  </svg>
                ),
              },
            ].map((item, i) => (
              <FadeIn key={i} delay={i * 80}>
                <div className="bg-white/80 backdrop-blur-sm rounded-[20px] p-6 border border-[rgba(59,77,67,0.06)] h-full">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#5B8A72]/10 to-[#7BA594]/10 flex items-center justify-center text-[#5B8A72] mb-3">
                    {item.icon}
                  </div>
                  <p className="text-[11px] font-semibold tracking-wider uppercase text-[#7A8580] mb-1">{item.label}</p>
                  <p className="text-[20px] font-bold text-[#3D4A44] mb-1">{item.value}</p>
                  <p className="text-[13px] text-[#7A8580]">{item.sub}</p>
                </div>
              </FadeIn>
            ))}
          </div>
        </div>
      </section>

      <section className="py-16 px-6 bg-gradient-to-b from-transparent via-[#5B8A72]/[0.03] to-transparent">
        <div className="max-w-5xl mx-auto">
          <FadeIn>
            <h2 className="text-[28px] sm:text-[36px] font-bold text-[#3D4A44] text-center mb-4">
              The Opportunity
            </h2>
            <p className="text-[16px] text-[#7A8580] text-center max-w-2xl mx-auto mb-12">
              Music catalogs are the fastest-growing alternative asset class. The infrastructure to manage them hasn't kept up.
            </p>
          </FadeIn>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            {[
              {
                title: 'Fragmented Market',
                desc: 'Rights holders rely on spreadsheets, outdated software, and manual processes to manage billions in catalog assets. There is no modern, unified platform.',
              },
              {
                title: 'Surging Demand',
                desc: 'Catalog acquisitions exceeded $5B+ in recent years. Buyers, sellers, and administrators all need better tools for valuation, due diligence, and ongoing management.',
              },
              {
                title: 'Complex Problem',
                desc: 'Music rights involve multiple stakeholders, territories, revenue streams, and regulatory bodies. Cadence turns this complexity into a competitive moat.',
              },
              {
                title: 'Platform Play',
                desc: 'Starting with catalog management and royalty processing, Cadence is positioned to become the financial operating system for the entire music rights ecosystem.',
              },
            ].map((item, i) => (
              <FadeIn key={i} delay={i * 80}>
                <div className="bg-white/80 backdrop-blur-sm rounded-[20px] p-6 border border-[rgba(59,77,67,0.06)] h-full">
                  <h3 className="text-[17px] font-semibold text-[#3D4A44] mb-2">{item.title}</h3>
                  <p className="text-[14px] text-[#7A8580] leading-relaxed">{item.desc}</p>
                </div>
              </FadeIn>
            ))}
          </div>
        </div>
      </section>

      <section className="py-16 px-6">
        <div className="max-w-5xl mx-auto">
          <FadeIn>
            <h2 className="text-[28px] sm:text-[36px] font-bold text-[#3D4A44] text-center mb-4">
              What We've Built
            </h2>
            <p className="text-[16px] text-[#7A8580] text-center max-w-2xl mx-auto mb-12">
              Cadence is already a full-featured platform with production-grade capabilities.
            </p>
          </FadeIn>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[
              'Multi-tenant catalog management',
              'Royalty statement ingestion & processing',
              'AI-powered data extraction (PDF/CSV)',
              'Catalog valuation with underwriting engine',
              'Rights & contract administration',
              'Sync placement pipeline',
              'Creator & client portals',
              'Streaming credits & intelligence',
              'Cross-organization sharing',
            ].map((item, i) => (
              <FadeIn key={i} delay={i * 50}>
                <div className="flex items-center gap-3 bg-white/60 rounded-[12px] p-4 border border-[rgba(59,77,67,0.06)]">
                  <div className="w-6 h-6 rounded-full bg-[#5B8A72]/10 flex items-center justify-center flex-shrink-0">
                    <svg className="w-3.5 h-3.5 text-[#5B8A72]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <span className="text-[14px] text-[#3D4A44] font-medium">{item}</span>
                </div>
              </FadeIn>
            ))}
          </div>
        </div>
      </section>

      <section className="py-16 sm:py-20 px-6 bg-gradient-to-b from-transparent via-[#5B8A72]/[0.03] to-transparent">
        <div className="max-w-xl mx-auto">
          <FadeIn>
            <h2 className="text-[28px] sm:text-[36px] font-bold text-[#3D4A44] text-center mb-4">
              Request Information
            </h2>
            <p className="text-[16px] text-[#7A8580] text-center mb-10">
              Interested in learning more about the Cadence investment opportunity? Fill out the form below and our team will reach out.
            </p>
          </FadeIn>

          <FadeIn delay={150}>
            <div className="bg-white/80 backdrop-blur-sm rounded-[24px] border border-[rgba(59,77,67,0.08)] p-8">
              {status && statusType === 'success' ? (
                <div className="text-center py-8">
                  <div className="w-14 h-14 rounded-full bg-[#5B8A72]/10 flex items-center justify-center mx-auto mb-4">
                    <svg className="w-7 h-7 text-[#5B8A72]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <p className="text-[16px] font-medium text-[#3D4A44] mb-2">{status}</p>
                  <p className="text-[14px] text-[#7A8580]">We'll follow up with additional details about the opportunity.</p>
                </div>
              ) : (
                <form onSubmit={handleSubmit} className="space-y-4">
                  {statusType === 'error' && status && (
                    <div className="px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-[14px] text-red-600">
                      {status}
                    </div>
                  )}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-[13px] font-medium text-[#3D4A44] mb-1.5">Full Name *</label>
                      <input
                        type="text"
                        value={form.name}
                        onChange={(e) => setForm({ ...form, name: e.target.value })}
                        required
                        className="w-full px-4 py-3 bg-[#FAFBF9] border border-[rgba(59,77,67,0.12)] rounded-xl text-[15px] text-[#3D4A44] focus:outline-none focus:border-[#5B8A72] focus:ring-2 focus:ring-[#5B8A72]/20 transition-all"
                        placeholder="Your name"
                      />
                    </div>
                    <div>
                      <label className="block text-[13px] font-medium text-[#3D4A44] mb-1.5">Email *</label>
                      <input
                        type="email"
                        value={form.email}
                        onChange={(e) => setForm({ ...form, email: e.target.value })}
                        required
                        className="w-full px-4 py-3 bg-[#FAFBF9] border border-[rgba(59,77,67,0.12)] rounded-xl text-[15px] text-[#3D4A44] focus:outline-none focus:border-[#5B8A72] focus:ring-2 focus:ring-[#5B8A72]/20 transition-all"
                        placeholder="you@firm.com"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-[13px] font-medium text-[#3D4A44] mb-1.5">Firm / Fund Name *</label>
                    <input
                      type="text"
                      value={form.firm}
                      onChange={(e) => setForm({ ...form, firm: e.target.value })}
                      required
                      className="w-full px-4 py-3 bg-[#FAFBF9] border border-[rgba(59,77,67,0.12)] rounded-xl text-[15px] text-[#3D4A44] focus:outline-none focus:border-[#5B8A72] focus:ring-2 focus:ring-[#5B8A72]/20 transition-all"
                      placeholder="Your firm or fund"
                    />
                  </div>
                  <div>
                    <label className="block text-[13px] font-medium text-[#3D4A44] mb-1.5">Investment Focus</label>
                    <select
                      value={form.investment_focus}
                      onChange={(e) => setForm({ ...form, investment_focus: e.target.value })}
                      className="w-full px-4 py-3 bg-[#FAFBF9] border border-[rgba(59,77,67,0.12)] rounded-xl text-[15px] text-[#3D4A44] focus:outline-none focus:border-[#5B8A72] focus:ring-2 focus:ring-[#5B8A72]/20 transition-all"
                    >
                      <option value="">Select focus area</option>
                      <option value="Pre-Seed / Seed">Pre-Seed / Seed</option>
                      <option value="Series A">Series A</option>
                      <option value="Music / Entertainment">Music / Entertainment</option>
                      <option value="SaaS / Enterprise">SaaS / Enterprise</option>
                      <option value="Angel / Individual">Angel / Individual</option>
                      <option value="Strategic / Corporate">Strategic / Corporate</option>
                      <option value="Other">Other</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-[13px] font-medium text-[#3D4A44] mb-1.5">Message</label>
                    <textarea
                      value={form.message}
                      onChange={(e) => setForm({ ...form, message: e.target.value })}
                      rows={4}
                      className="w-full px-4 py-3 bg-[#FAFBF9] border border-[rgba(59,77,67,0.12)] rounded-xl text-[15px] text-[#3D4A44] focus:outline-none focus:border-[#5B8A72] focus:ring-2 focus:ring-[#5B8A72]/20 transition-all resize-none"
                      placeholder="Tell us about your interest in Cadence..."
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full px-6 py-3.5 bg-gradient-to-r from-[#5B8A72] to-[#6B9A84] text-white font-semibold text-[15px] rounded-xl hover:shadow-lg hover:shadow-[#5B8A72]/25 transition-all disabled:opacity-60"
                  >
                    {loading ? 'Submitting...' : 'Request Information'}
                  </button>
                  <p className="text-[12px] text-[#B0B8B3] text-center">
                    Your information is confidential and will only be used to facilitate communication about the investment opportunity.
                  </p>
                </form>
              )}
            </div>
          </FadeIn>
        </div>
      </section>

      <PublicFooter />
    </div>
  )
}
