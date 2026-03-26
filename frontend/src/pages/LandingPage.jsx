import React, { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'

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

export default function LandingPage() {
  const navigate = useNavigate()
  const [waitlistEmail, setWaitlistEmail] = useState('')
  const [waitlistStatus, setWaitlistStatus] = useState(null)
  const [waitlistLoading, setWaitlistLoading] = useState(false)
  const [showDemoModal, setShowDemoModal] = useState(false)
  const [demoForm, setDemoForm] = useState({ name: '', email: '', company: '', message: '' })
  const [demoStatus, setDemoStatus] = useState(null)
  const [demoLoading, setDemoLoading] = useState(false)

  const handleWaitlist = async (e) => {
    e.preventDefault()
    if (!waitlistEmail.trim()) return
    setWaitlistLoading(true)
    try {
      const res = await axios.post('/api/public/waitlist', { email: waitlistEmail })
      setWaitlistStatus(res.data.message)
      setWaitlistEmail('')
    } catch (err) {
      setWaitlistStatus(err.response?.data?.detail || 'Something went wrong. Please try again.')
    } finally {
      setWaitlistLoading(false)
    }
  }

  const handleDemo = async (e) => {
    e.preventDefault()
    if (!demoForm.name.trim() || !demoForm.email.trim()) return
    setDemoLoading(true)
    try {
      const res = await axios.post('/api/public/demo-request', demoForm)
      setDemoStatus(res.data.message)
      setDemoForm({ name: '', email: '', company: '', message: '' })
    } catch (err) {
      setDemoStatus(err.response?.data?.detail || 'Something went wrong. Please try again.')
    } finally {
      setDemoLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#FAFBF9] overflow-x-hidden">
      <nav className="fixed top-0 left-0 right-0 z-50 bg-[#FAFBF9]/80 backdrop-blur-xl border-b border-[rgba(59,77,67,0.06)]">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <img src="/cadence-icon-transparent.png" alt="Cadence" className="h-8 w-auto" />
            <span className="text-[18px] font-semibold text-[#3D4A44] tracking-tight">cadence</span>
          </div>
          <button
            onClick={() => navigate('/login')}
            className="text-[14px] font-medium text-[#5B8A72] hover:text-[#4A7A62] transition-colors px-4 py-2 rounded-full hover:bg-[#5B8A72]/8"
          >
            Sign In
          </button>
        </div>
      </nav>

      <section className="relative pt-32 pb-20 px-6 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-[#5B8A72]/5 via-transparent to-[#7BA594]/5" />
        <div className="absolute top-20 left-1/4 w-96 h-96 bg-[#5B8A72]/5 rounded-full blur-3xl" />
        <div className="absolute bottom-0 right-1/4 w-80 h-80 bg-[#7BA594]/5 rounded-full blur-3xl" />

        <div className="max-w-4xl mx-auto text-center relative z-10">
          <FadeIn>
            <div className="flex justify-center mb-8">
              <img
                src="/cadence-logo.png"
                alt="Cadence - Catalog Intelligence"
                className="h-[140px] sm:h-[180px] w-auto drop-shadow-md"
              />
            </div>
          </FadeIn>

          <FadeIn delay={150}>
            <h1 className="text-[36px] sm:text-[52px] lg:text-[64px] font-bold text-[#3D4A44] leading-[1.1] tracking-tight mb-6">
              Your catalog.<br />
              <span className="bg-gradient-to-r from-[#5B8A72] to-[#7BA594] bg-clip-text text-transparent">
                Fully understood.
              </span>
            </h1>
          </FadeIn>

          <FadeIn delay={300}>
            <p className="text-[17px] sm:text-[20px] text-[#7A8580] max-w-2xl mx-auto leading-relaxed mb-10">
              The intelligence layer for music catalogs. Know what you own, what it's worth, and where the opportunities are.
            </p>
          </FadeIn>

          <FadeIn delay={450}>
            {waitlistStatus ? (
              <div className="inline-flex items-center gap-2 px-6 py-3 bg-[#5B8A72]/10 rounded-full text-[#5B8A72] font-medium text-[15px]">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                {waitlistStatus}
              </div>
            ) : (
              <form onSubmit={handleWaitlist} className="flex flex-col sm:flex-row items-center justify-center gap-3 max-w-md mx-auto">
                <input
                  type="email"
                  value={waitlistEmail}
                  onChange={(e) => setWaitlistEmail(e.target.value)}
                  placeholder="Enter your email"
                  required
                  className="w-full sm:flex-1 px-5 py-3.5 bg-white border border-[rgba(59,77,67,0.12)] rounded-full text-[15px] text-[#3D4A44] placeholder-[#B0B8B3] focus:outline-none focus:border-[#5B8A72] focus:ring-2 focus:ring-[#5B8A72]/20 transition-all"
                />
                <button
                  type="submit"
                  disabled={waitlistLoading}
                  className="w-full sm:w-auto px-7 py-3.5 bg-gradient-to-r from-[#5B8A72] to-[#6B9A84] text-white font-semibold text-[15px] rounded-full hover:shadow-lg hover:shadow-[#5B8A72]/25 transition-all disabled:opacity-60 whitespace-nowrap"
                >
                  {waitlistLoading ? 'Joining...' : 'Join Waitlist'}
                </button>
              </form>
            )}
          </FadeIn>

          <FadeIn delay={550}>
            <button
              onClick={() => setShowDemoModal(true)}
              className="mt-4 text-[14px] font-medium text-[#7A8580] hover:text-[#5B8A72] transition-colors underline underline-offset-4 decoration-[#7A8580]/30 hover:decoration-[#5B8A72]/50"
            >
              Or request a demo
            </button>
          </FadeIn>
        </div>
      </section>

      <section className="py-16 sm:py-24 px-6">
        <div className="max-w-6xl mx-auto">
          <FadeIn>
            <p className="text-center text-[13px] font-semibold tracking-[0.2em] uppercase text-[#5B8A72]/60 mb-12">
              Built for the business of music
            </p>
          </FadeIn>

          <div className="relative flex flex-col lg:flex-row items-center justify-center gap-8 lg:gap-0">
            <FadeIn delay={100}>
              <div className="relative z-10 lg:mr-[-40px]">
                <div className="relative mx-auto" style={{ width: '280px' }}>
                  <div className="relative bg-[#1a1a1a] rounded-[40px] p-[10px] shadow-2xl shadow-black/20">
                    <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[120px] h-[28px] bg-[#1a1a1a] rounded-b-[14px] z-20" />
                    <div className="rounded-[30px] overflow-hidden bg-[#FAFBF9] aspect-[9/19.5]">
                      <img
                        src="/preview-mobile.jpg"
                        alt="Cadence on iPhone"
                        className="w-full h-full object-cover object-top"
                      />
                    </div>
                  </div>
                </div>
              </div>
            </FadeIn>

            <FadeIn delay={250}>
              <div className="relative z-0 lg:ml-[-40px]">
                <div className="relative mx-auto" style={{ width: '680px', maxWidth: '90vw' }}>
                  <div className="bg-[#e8e8e8] rounded-[12px] p-[8px] shadow-2xl shadow-black/15">
                    <div className="bg-[#2a2a2a] rounded-[8px] p-[3px]">
                      <div className="rounded-[6px] overflow-hidden bg-[#FAFBF9] aspect-[16/10]">
                        <img
                          src="/preview-desktop.jpg"
                          alt="Cadence dashboard"
                          className="w-full h-full object-cover object-top"
                        />
                      </div>
                    </div>
                    <div className="flex justify-center pt-2 pb-1">
                      <div className="w-[60px] h-[4px] bg-[#d0d0d0] rounded-full" />
                    </div>
                  </div>
                </div>
              </div>
            </FadeIn>
          </div>
        </div>
      </section>

      <section className="py-16 sm:py-24 px-6 bg-gradient-to-b from-transparent via-[#5B8A72]/[0.03] to-transparent">
        <div className="max-w-5xl mx-auto">
          <FadeIn>
            <h2 className="text-[28px] sm:text-[36px] font-bold text-[#3D4A44] text-center mb-4">
              Intelligence, not just information
            </h2>
            <p className="text-[16px] text-[#7A8580] text-center max-w-xl mx-auto mb-16">
              See your catalog through a lens that reveals value others can't find.
            </p>
          </FadeIn>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              {
                icon: (
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5M9 11.25v1.5M12 9v3.75m3-6v6" />
                  </svg>
                ),
                title: 'Catalog Valuation',
                desc: 'Understand the true worth of every asset in your portfolio.',
              },
              {
                icon: (
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
                  </svg>
                ),
                title: 'Rights Administration',
                desc: 'Track ownership, splits, and contracts across your entire roster.',
              },
              {
                icon: (
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M2.25 18.75a60.07 60.07 0 0115.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 013 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-.375m1.5-1.5H21a.75.75 0 00-.75.75v.75m0 0H3.75m0 0h-.375a1.125 1.125 0 01-1.125-1.125V15m1.5 1.5v-.75A.75.75 0 003 15h-.75M15 10.5a3 3 0 11-6 0 3 3 0 016 0zm3 0h.008v.008H18V10.5zm-12 0h.008v.008H6V10.5z" />
                  </svg>
                ),
                title: 'Revenue Intelligence',
                desc: 'Ingest statements, reconcile royalties, and see where every dollar flows.',
              },
              {
                icon: (
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
                  </svg>
                ),
                title: 'Creator Management',
                desc: 'One source of truth for every artist, writer, and producer you work with.',
              },
            ].map((item, i) => (
              <FadeIn key={i} delay={i * 100}>
                <div className="bg-white/80 backdrop-blur-sm rounded-[20px] p-6 border border-[rgba(59,77,67,0.06)] hover:border-[#5B8A72]/20 hover:shadow-lg hover:shadow-[#5B8A72]/5 transition-all duration-300 h-full">
                  <div className="w-12 h-12 rounded-[14px] bg-gradient-to-br from-[#5B8A72]/10 to-[#7BA594]/10 flex items-center justify-center text-[#5B8A72] mb-4">
                    {item.icon}
                  </div>
                  <h3 className="text-[16px] font-semibold text-[#3D4A44] mb-2">{item.title}</h3>
                  <p className="text-[14px] text-[#7A8580] leading-relaxed">{item.desc}</p>
                </div>
              </FadeIn>
            ))}
          </div>
        </div>
      </section>

      <section className="py-16 sm:py-24 px-6">
        <div className="max-w-3xl mx-auto text-center">
          <FadeIn>
            <h2 className="text-[28px] sm:text-[36px] font-bold text-[#3D4A44] mb-4">
              Ready to see your catalog differently?
            </h2>
            <p className="text-[16px] text-[#7A8580] mb-10">
              Join the waitlist for early access, or request a personalized demo.
            </p>
          </FadeIn>

          <FadeIn delay={150}>
            {waitlistStatus ? (
              <div className="inline-flex items-center gap-2 px-6 py-3 bg-[#5B8A72]/10 rounded-full text-[#5B8A72] font-medium text-[15px]">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                {waitlistStatus}
              </div>
            ) : (
              <form onSubmit={handleWaitlist} className="flex flex-col sm:flex-row items-center justify-center gap-3 max-w-md mx-auto">
                <input
                  type="email"
                  value={waitlistEmail}
                  onChange={(e) => setWaitlistEmail(e.target.value)}
                  placeholder="Enter your email"
                  required
                  className="w-full sm:flex-1 px-5 py-3.5 bg-white border border-[rgba(59,77,67,0.12)] rounded-full text-[15px] text-[#3D4A44] placeholder-[#B0B8B3] focus:outline-none focus:border-[#5B8A72] focus:ring-2 focus:ring-[#5B8A72]/20 transition-all"
                />
                <button
                  type="submit"
                  disabled={waitlistLoading}
                  className="w-full sm:w-auto px-7 py-3.5 bg-gradient-to-r from-[#5B8A72] to-[#6B9A84] text-white font-semibold text-[15px] rounded-full hover:shadow-lg hover:shadow-[#5B8A72]/25 transition-all disabled:opacity-60 whitespace-nowrap"
                >
                  {waitlistLoading ? 'Joining...' : 'Join Waitlist'}
                </button>
              </form>
            )}
          </FadeIn>

          <FadeIn delay={250}>
            <div className="mt-6 flex items-center justify-center gap-6">
              <button
                onClick={() => setShowDemoModal(true)}
                className="text-[14px] font-medium text-[#5B8A72] hover:text-[#4A7A62] transition-colors flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.91 11.672a.375.375 0 010 .656l-5.603 3.113a.375.375 0 01-.557-.328V8.887c0-.286.307-.466.557-.327l5.603 3.112z" />
                </svg>
                Request a Demo
              </button>
            </div>
          </FadeIn>
        </div>
      </section>

      <footer className="border-t border-[rgba(59,77,67,0.06)] py-8 px-6">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <img src="/cadence-icon-transparent.png" alt="Cadence" className="h-5 w-auto opacity-50" />
            <span className="text-[13px] text-[#B0B8B3]">Cadence Catalog Intelligence</span>
          </div>
          <p className="text-[12px] text-[#B0B8B3]">&copy; {new Date().getFullYear()} Cadence CI. All rights reserved.</p>
        </div>
      </footer>

      {showDemoModal && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm" onClick={() => setShowDemoModal(false)}>
          <div className="bg-white rounded-[24px] shadow-2xl w-full max-w-md p-8 animate-am-scale-in" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-[20px] font-bold text-[#3D4A44]">Request a Demo</h3>
              <button onClick={() => setShowDemoModal(false)} className="p-1 text-[#7A8580] hover:text-[#3D4A44] transition-colors">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {demoStatus ? (
              <div className="text-center py-8">
                <div className="w-14 h-14 rounded-full bg-[#5B8A72]/10 flex items-center justify-center mx-auto mb-4">
                  <svg className="w-7 h-7 text-[#5B8A72]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <p className="text-[16px] font-medium text-[#3D4A44] mb-2">{demoStatus}</p>
                <p className="text-[14px] text-[#7A8580]">We'll reach out to schedule your demo.</p>
              </div>
            ) : (
              <form onSubmit={handleDemo} className="space-y-4">
                <div>
                  <label className="block text-[13px] font-medium text-[#3D4A44] mb-1.5">Name *</label>
                  <input
                    type="text"
                    value={demoForm.name}
                    onChange={(e) => setDemoForm({ ...demoForm, name: e.target.value })}
                    required
                    className="w-full px-4 py-3 bg-[#FAFBF9] border border-[rgba(59,77,67,0.12)] rounded-xl text-[15px] text-[#3D4A44] focus:outline-none focus:border-[#5B8A72] focus:ring-2 focus:ring-[#5B8A72]/20 transition-all"
                    placeholder="Your full name"
                  />
                </div>
                <div>
                  <label className="block text-[13px] font-medium text-[#3D4A44] mb-1.5">Email *</label>
                  <input
                    type="email"
                    value={demoForm.email}
                    onChange={(e) => setDemoForm({ ...demoForm, email: e.target.value })}
                    required
                    className="w-full px-4 py-3 bg-[#FAFBF9] border border-[rgba(59,77,67,0.12)] rounded-xl text-[15px] text-[#3D4A44] focus:outline-none focus:border-[#5B8A72] focus:ring-2 focus:ring-[#5B8A72]/20 transition-all"
                    placeholder="you@company.com"
                  />
                </div>
                <div>
                  <label className="block text-[13px] font-medium text-[#3D4A44] mb-1.5">Company</label>
                  <input
                    type="text"
                    value={demoForm.company}
                    onChange={(e) => setDemoForm({ ...demoForm, company: e.target.value })}
                    className="w-full px-4 py-3 bg-[#FAFBF9] border border-[rgba(59,77,67,0.12)] rounded-xl text-[15px] text-[#3D4A44] focus:outline-none focus:border-[#5B8A72] focus:ring-2 focus:ring-[#5B8A72]/20 transition-all"
                    placeholder="Your company or label"
                  />
                </div>
                <div>
                  <label className="block text-[13px] font-medium text-[#3D4A44] mb-1.5">Message</label>
                  <textarea
                    value={demoForm.message}
                    onChange={(e) => setDemoForm({ ...demoForm, message: e.target.value })}
                    rows={3}
                    className="w-full px-4 py-3 bg-[#FAFBF9] border border-[rgba(59,77,67,0.12)] rounded-xl text-[15px] text-[#3D4A44] focus:outline-none focus:border-[#5B8A72] focus:ring-2 focus:ring-[#5B8A72]/20 transition-all resize-none"
                    placeholder="Tell us about your catalog..."
                  />
                </div>
                <button
                  type="submit"
                  disabled={demoLoading}
                  className="w-full px-6 py-3.5 bg-gradient-to-r from-[#5B8A72] to-[#6B9A84] text-white font-semibold text-[15px] rounded-xl hover:shadow-lg hover:shadow-[#5B8A72]/25 transition-all disabled:opacity-60"
                >
                  {demoLoading ? 'Submitting...' : 'Submit Request'}
                </button>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
