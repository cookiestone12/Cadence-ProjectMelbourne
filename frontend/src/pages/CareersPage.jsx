import React, { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import PublicFooter from '../components/PublicFooter'
import SEO from '../components/SEO'

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

const ROLE_OPTIONS = [
  'Software Engineering Intern',
  'Product / UX Design Intern',
  'Marketing & Content Intern',
  'Business Development & Sales Intern',
]

const roles = [
  {
    title: 'Software Engineering Intern',
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5" />
      </svg>
    ),
    about: 'Contribute directly to the Cadence platform — building features, fixing bugs, and helping architect systems that handle complex music rights data. You\'ll ship code to production.',
    responsibilities: [
      'Build and ship frontend and/or backend features',
      'Collaborate on database schema design for royalty accounting',
      'Develop and test API endpoints for catalog workflows',
      'Contribute to the publisher PDF parser and data ingestion pipeline',
      'Participate in code reviews and technical planning',
    ],
    qualifications: [
      'Proficiency in JavaScript/TypeScript, Python, or similar',
      'Familiarity with web frameworks (React, Next.js, Node.js, Django)',
      'Basic understanding of databases (SQL or NoSQL)',
      'Comfortable in a fast-paced startup environment',
    ],
  },
  {
    title: 'Product / UX Design Intern',
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.53 16.122a3 3 0 00-5.78 1.128 2.25 2.25 0 01-2.4 2.245 4.5 4.5 0 008.4-2.245c0-.399-.078-.78-.22-1.128zm0 0a15.998 15.998 0 003.388-1.62m-5.043-.025a15.994 15.994 0 011.622-3.395m3.42 3.42a15.995 15.995 0 004.764-4.648l3.876-5.814a1.151 1.151 0 00-1.597-1.597L14.146 6.32a15.996 15.996 0 00-4.649 4.763m3.42 3.42a6.776 6.776 0 00-3.42-3.42" />
      </svg>
    ),
    about: 'Help define how music professionals interact with their data. Conduct user research, design interfaces, prototype flows, and contribute to the design system that makes Cadence intuitive.',
    responsibilities: [
      'Design UI/UX for core platform features',
      'Conduct user research interviews with music professionals',
      'Create wireframes, prototypes, and high-fidelity mockups in Figma',
      'Contribute to the Cadence design system and component library',
      'Map user journeys for key personas',
    ],
    qualifications: [
      'Proficiency in Figma or similar design tools',
      'Understanding of user-centered design principles',
      'Ability to translate complex data into clean interfaces',
      'Strong portfolio demonstrating process-oriented design thinking',
    ],
  },
  {
    title: 'Marketing & Content Intern',
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10.34 15.84c-.688-.06-1.386-.09-2.09-.09H7.5a4.5 4.5 0 110-9h.75c.704 0 1.402-.03 2.09-.09m0 9.18c.253.962.584 1.892.985 2.783.247.55.06 1.21-.463 1.511l-.657.38c-.551.318-1.26.117-1.527-.461a20.845 20.845 0 01-1.44-4.282m3.102.069a18.03 18.03 0 01-.59-4.59c0-1.586.205-3.124.59-4.59m0 9.18a23.848 23.848 0 018.835 2.535M10.34 6.66a23.847 23.847 0 008.835-2.535m0 0A23.74 23.74 0 0018.795 3m.38 1.125a23.91 23.91 0 011.014 5.395m-1.014 8.855c-.118.38-.245.754-.38 1.125m.38-1.125a23.91 23.91 0 001.014-5.395m0-3.46c.495.413.811 1.035.811 1.73 0 .695-.316 1.317-.811 1.73m0-3.46a24.347 24.347 0 010 3.46" />
      </svg>
    ),
    about: 'Build the voice and visibility of Cadence across channels. From social media to thought leadership, email campaigns to event collateral — help position Cadence as the go-to platform for catalog intelligence.',
    responsibilities: [
      'Develop and execute social media content calendars',
      'Write blog posts, case studies, and thought leadership pieces',
      'Create email marketing campaigns for beta launch',
      'Design marketing collateral (one-pagers, pitch assets)',
      'Track and report on content performance metrics',
    ],
    qualifications: [
      'Strong writing skills across platforms and audiences',
      'Experience with social media management tools',
      'Basic graphic design skills (Canva, Adobe Creative Suite)',
      'Self-starter who can manage multiple content streams',
    ],
  },
  {
    title: 'Business Development & Sales Intern',
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20.25 14.15v4.25c0 1.094-.787 2.036-1.872 2.18-2.087.277-4.216.42-6.378.42s-4.291-.143-6.378-.42c-1.085-.144-1.872-1.086-1.872-2.18v-4.25m16.5 0a2.18 2.18 0 00.75-1.661V8.706c0-1.081-.768-2.015-1.837-2.175a48.114 48.114 0 00-3.413-.387m4.5 8.006c-.194.165-.42.295-.673.38A23.978 23.978 0 0112 15.75c-2.648 0-5.195-.429-7.577-1.22a2.016 2.016 0 01-.673-.38m0 0A2.18 2.18 0 013 12.489V8.706c0-1.081.768-2.015 1.837-2.175a48.111 48.111 0 013.413-.387m7.5 0V5.25A2.25 2.25 0 0013.5 3h-3a2.25 2.25 0 00-2.25 2.25v.894m7.5 0a48.667 48.667 0 00-7.5 0M12 12.75h.008v.008H12v-.008z" />
      </svg>
    ),
    about: 'Research target markets, build prospect lists, support outreach campaigns, and help refine Cadence\'s go-to-market strategy. Get exposure to the full sales cycle in early-stage B2B SaaS.',
    responsibilities: [
      'Research and build prospect lists across key verticals',
      'Support outreach campaigns via email, LinkedIn, and industry channels',
      'Help develop sales collateral (pitch decks, one-pagers)',
      'Track outreach metrics and maintain CRM data',
      'Contribute to competitive analysis and market positioning',
    ],
    qualifications: [
      'Strong communication skills (written and verbal)',
      'Comfortable with cold outreach and relationship building',
      'Organized, detail-oriented, and able to manage a pipeline',
      'Genuine interest in the music industry and/or B2B technology',
    ],
  },
]

export default function CareersPage() {
  const navigate = useNavigate()
  const [expandedRole, setExpandedRole] = useState(null)
  const [showApplyModal, setShowApplyModal] = useState(false)
  const [appForm, setAppForm] = useState({ name: '', email: '', role: '', location: '', linkedin: '', portfolio: '', experience: '', why_cadence: '' })
  const [resumeFile, setResumeFile] = useState(null)
  const [appStatus, setAppStatus] = useState(null)
  const [appStatusType, setAppStatusType] = useState(null)
  const [appLoading, setAppLoading] = useState(false)

  const openApplyModal = (role = '') => {
    setAppForm({ name: '', email: '', role: role, location: '', linkedin: '', portfolio: '', experience: '', why_cadence: '' })
    setResumeFile(null)
    setAppStatus(null)
    setAppStatusType(null)
    setShowApplyModal(true)
  }

  const handleApply = async (e) => {
    e.preventDefault()
    if (!appForm.name.trim() || !appForm.email.trim() || !appForm.role) return
    setAppLoading(true)
    try {
      const formData = new FormData()
      Object.entries(appForm).forEach(([key, val]) => { if (val) formData.append(key, val) })
      if (resumeFile) formData.append('resume', resumeFile)
      const res = await axios.post('/api/public/intern-application', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
      setAppStatus(res.data.message)
      setAppStatusType('success')
    } catch (err) {
      setAppStatus(err.response?.data?.detail || 'Something went wrong. Please try again.')
      setAppStatusType('error')
    } finally {
      setAppLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#FAFBF9] overflow-x-hidden">
      <SEO
        path="/careers"
        title="Careers"
        description="Join the founding team at Cadence Catalog Intelligence and help reshape how the music industry thinks about catalog data, royalties, and rights. 2026 internship program now open."
        image="https://cadence-ci.com/careers-og.png"
      />
      <nav className="fixed top-0 left-0 right-0 z-50 bg-[#FAFBF9]/80 backdrop-blur-xl border-b border-[rgba(59,77,67,0.06)]">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center cursor-pointer" onClick={() => navigate('/')}>
            <img src="/cadence-logo-full.png" alt="Cadence - Catalog Intelligence" className="h-12 w-auto" />
          </div>
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/investors')}
              className="hidden sm:inline-flex text-[14px] font-medium text-[#7A8580] hover:text-[#5B8A72] transition-colors"
            >
              Investors
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
              2026 Internship Program
            </p>
          </FadeIn>

          <FadeIn delay={100}>
            <h1 className="text-[36px] sm:text-[52px] lg:text-[64px] font-bold text-[#3D4A44] leading-[1.1] tracking-tight mb-6">
              Build the future of{' '}
              <span className="bg-gradient-to-r from-[#5B8A72] to-[#7BA594] bg-clip-text text-transparent">
                music intelligence.
              </span>
            </h1>
          </FadeIn>

          <FadeIn delay={200}>
            <p className="text-[17px] sm:text-[20px] text-[#7A8580] max-w-2xl mx-auto leading-relaxed mb-8">
              Join the founding team at Cadence and help reshape how the music industry thinks about catalog data, royalties, and rights.
            </p>
          </FadeIn>

          <FadeIn delay={300}>
            <button
              onClick={() => openApplyModal()}
              className="inline-flex items-center gap-2 px-8 py-4 bg-gradient-to-r from-[#5B8A72] to-[#6B9A84] text-white font-semibold text-[16px] rounded-full hover:shadow-lg hover:shadow-[#5B8A72]/25 transition-all"
            >
              Apply Now
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
              </svg>
            </button>
          </FadeIn>
        </div>
      </section>

      <section className="py-16 px-6">
        <div className="max-w-5xl mx-auto">
          <FadeIn>
            <h2 className="text-[28px] sm:text-[36px] font-bold text-[#3D4A44] text-center mb-4">
              Program Overview
            </h2>
            <p className="text-[16px] text-[#7A8580] text-center max-w-2xl mx-auto mb-12">
              A 12-week program designed for people who want to ship real work at the intersection of music and technology.
            </p>
          </FadeIn>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {[
              {
                label: 'Duration',
                value: '12 Weeks',
                sub: 'Summer 2026',
                icon: (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5" />
                  </svg>
                ),
              },
              {
                label: 'Location',
                value: 'Hybrid',
                sub: 'Atlanta or LA (remote considered)',
                icon: (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z" />
                  </svg>
                ),
              },
              {
                label: 'Eligibility',
                value: 'Open to All',
                sub: 'Students, grads & career changers',
                icon: (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4.26 10.147a60.436 60.436 0 00-.491 6.347A48.627 48.627 0 0112 20.904a48.627 48.627 0 018.232-4.41 60.46 60.46 0 00-.491-6.347m-15.482 0a50.57 50.57 0 00-2.658-.813A59.905 59.905 0 0112 3.493a59.902 59.902 0 0110.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.697 50.697 0 0112 13.489a50.702 50.702 0 017.74-3.342M6.75 15a.75.75 0 100-1.5.75.75 0 000 1.5zm0 0v-3.675A55.378 55.378 0 0112 8.443m-7.007 11.55A5.981 5.981 0 006.75 15.75v-1.5" />
                  </svg>
                ),
              },
              {
                label: 'Credit',
                value: 'Available',
                sub: 'College credit where applicable',
                icon: (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M11.48 3.499a.562.562 0 011.04 0l2.125 5.111a.563.563 0 00.475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 00-.182.557l1.285 5.385a.562.562 0 01-.84.61l-4.725-2.885a.563.563 0 00-.586 0L6.982 20.54a.562.562 0 01-.84-.61l1.285-5.386a.562.562 0 00-.182-.557l-4.204-3.602a.563.563 0 01.321-.988l5.518-.442a.563.563 0 00.475-.345L11.48 3.5z" />
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
                  <p className="text-[18px] font-bold text-[#3D4A44] mb-1">{item.value}</p>
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
              What you'll get
            </h2>
            <p className="text-[16px] text-[#7A8580] text-center max-w-xl mx-auto mb-12">
              This isn't a shadow role. You'll own real work from day one.
            </p>
          </FadeIn>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {[
              { title: 'Real Ownership', desc: 'Work on production features, campaigns, and strategy — not busywork.' },
              { title: 'Founding Team Access', desc: 'Weekly 1:1s with a founder and bi-weekly all-hands syncs.' },
              { title: 'Music Industry Network', desc: 'Access to a network spanning Grammy-winning studios and enterprise tech.' },
              { title: 'Portfolio-Ready Work', desc: 'Leave with tangible deliverables and a letter of recommendation.' },
              { title: 'Startup Exposure', desc: 'See how a SaaS company is built from scratch, from product to pitch decks.' },
              { title: 'Culture That Fits', desc: 'We move fast with intention. Quality over speed. Honesty over hierarchy.' },
            ].map((item, i) => (
              <FadeIn key={i} delay={i * 80}>
                <div className="bg-white/60 backdrop-blur-sm rounded-[16px] p-5 border border-[rgba(59,77,67,0.06)]">
                  <div className="w-8 h-8 rounded-lg bg-[#5B8A72]/10 flex items-center justify-center text-[#5B8A72] mb-3">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <h3 className="text-[15px] font-semibold text-[#3D4A44] mb-1">{item.title}</h3>
                  <p className="text-[13px] text-[#7A8580] leading-relaxed">{item.desc}</p>
                </div>
              </FadeIn>
            ))}
          </div>
        </div>
      </section>

      <section className="py-16 px-6">
        <div className="max-w-4xl mx-auto">
          <FadeIn>
            <h2 className="text-[28px] sm:text-[36px] font-bold text-[#3D4A44] text-center mb-4">
              Open Roles
            </h2>
            <p className="text-[16px] text-[#7A8580] text-center max-w-xl mx-auto mb-12">
              We're hiring across four disciplines. No degree required — we care about what you can do.
            </p>
          </FadeIn>

          <div className="space-y-4">
            {roles.map((role, i) => (
              <FadeIn key={i} delay={i * 80}>
                <div className="bg-white/80 backdrop-blur-sm rounded-[20px] border border-[rgba(59,77,67,0.06)] overflow-hidden hover:border-[#5B8A72]/20 transition-colors">
                  <button
                    onClick={() => setExpandedRole(expandedRole === i ? null : i)}
                    className="w-full flex items-center gap-4 p-6 text-left"
                  >
                    <div className="w-12 h-12 rounded-[14px] bg-gradient-to-br from-[#5B8A72]/10 to-[#7BA594]/10 flex items-center justify-center text-[#5B8A72] flex-shrink-0">
                      {role.icon}
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="text-[17px] font-semibold text-[#3D4A44]">{role.title}</h3>
                      <p className="text-[13px] text-[#7A8580] mt-0.5">12 weeks | Hybrid (ATL or LA) | Remote considered</p>
                    </div>
                    <svg
                      className={`w-5 h-5 text-[#7A8580] flex-shrink-0 transition-transform duration-300 ${expandedRole === i ? 'rotate-180' : ''}`}
                      fill="none" stroke="currentColor" viewBox="0 0 24 24"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
                    </svg>
                  </button>

                  <div className={`transition-all duration-300 ease-in-out overflow-hidden ${expandedRole === i ? 'max-h-[1000px] opacity-100' : 'max-h-0 opacity-0'}`}>
                    <div className="px-6 pb-6 pt-0">
                      <div className="border-t border-[rgba(59,77,67,0.06)] pt-5">
                        <p className="text-[14px] text-[#7A8580] leading-relaxed mb-5">{role.about}</p>

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                          <div>
                            <h4 className="text-[13px] font-semibold text-[#3D4A44] uppercase tracking-wider mb-3">Responsibilities</h4>
                            <ul className="space-y-2">
                              {role.responsibilities.map((r, ri) => (
                                <li key={ri} className="flex items-start gap-2 text-[13px] text-[#7A8580]">
                                  <span className="w-1.5 h-1.5 rounded-full bg-[#5B8A72] mt-1.5 flex-shrink-0" />
                                  {r}
                                </li>
                              ))}
                            </ul>
                          </div>
                          <div>
                            <h4 className="text-[13px] font-semibold text-[#3D4A44] uppercase tracking-wider mb-3">Qualifications</h4>
                            <ul className="space-y-2">
                              {role.qualifications.map((q, qi) => (
                                <li key={qi} className="flex items-start gap-2 text-[13px] text-[#7A8580]">
                                  <span className="w-1.5 h-1.5 rounded-full bg-[#7BA594] mt-1.5 flex-shrink-0" />
                                  {q}
                                </li>
                              ))}
                            </ul>
                          </div>
                        </div>

                        <div className="mt-5">
                          <button
                            onClick={() => openApplyModal(role.title)}
                            className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-[#5B8A72] to-[#6B9A84] text-white font-medium text-[14px] rounded-full hover:shadow-lg hover:shadow-[#5B8A72]/25 transition-all"
                          >
                            Apply for this role
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                            </svg>
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </FadeIn>
            ))}
          </div>
        </div>
      </section>

      <section className="py-16 sm:py-20 px-6 bg-gradient-to-b from-transparent via-[#5B8A72]/[0.03] to-transparent">
        <div className="max-w-3xl mx-auto text-center">
          <FadeIn>
            <h2 className="text-[24px] sm:text-[32px] font-bold text-[#3D4A44] mb-4">
              About Cadence
            </h2>
            <p className="text-[15px] text-[#7A8580] leading-relaxed mb-6 max-w-2xl mx-auto">
              Cadence (Catalog Intelligence) is a SaaS platform built for the modern music industry. We help rights holders, publishers, distributors, and independent artists manage their catalogs, track royalties, understand their rights, and value their assets.
            </p>
            <p className="text-[15px] text-[#7A8580] leading-relaxed max-w-2xl mx-auto">
              Founded by a team of music industry veterans and technologists, our founding team has credits spanning Beyoncé, Ariana Grande, Usher, and Tyla, and brings 13+ years of enterprise IT infrastructure experience from one of the world's largest financial institutions.
            </p>
          </FadeIn>
        </div>
      </section>

      <section className="py-16 sm:py-20 px-6">
        <div className="max-w-3xl mx-auto text-center">
          <FadeIn>
            <h2 className="text-[28px] sm:text-[36px] font-bold text-[#3D4A44] mb-4">
              Ready to apply?
            </h2>
            <p className="text-[16px] text-[#7A8580] mb-8">
              The music industry still runs on spreadsheets and PDFs. We're replacing that with real intelligence.
            </p>
          </FadeIn>
          <FadeIn delay={150}>
            <button
              onClick={() => openApplyModal()}
              className="inline-flex items-center gap-2 px-8 py-4 bg-gradient-to-r from-[#5B8A72] to-[#6B9A84] text-white font-semibold text-[16px] rounded-full hover:shadow-lg hover:shadow-[#5B8A72]/25 transition-all"
            >
              Start Your Application
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
              </svg>
            </button>
          </FadeIn>
        </div>
      </section>

      <PublicFooter />

      {showApplyModal && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm" onClick={() => setShowApplyModal(false)}>
          <div className="bg-white rounded-[24px] shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto p-8 animate-am-scale-in" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-[20px] font-bold text-[#3D4A44]">Apply for Internship</h3>
              <button onClick={() => setShowApplyModal(false)} className="p-1 text-[#7A8580] hover:text-[#3D4A44] transition-colors">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {appStatus && appStatusType === 'success' ? (
              <div className="text-center py-8">
                <div className="w-14 h-14 rounded-full bg-[#5B8A72]/10 flex items-center justify-center mx-auto mb-4">
                  <svg className="w-7 h-7 text-[#5B8A72]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <p className="text-[16px] font-medium text-[#3D4A44] mb-2">{appStatus}</p>
                <p className="text-[14px] text-[#7A8580]">We review applications on a rolling basis and will reach out within 2 weeks if there's a fit.</p>
              </div>
            ) : (
              <form onSubmit={handleApply} className="space-y-4">
                {appStatusType === 'error' && appStatus && (
                  <div className="px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-[14px] text-red-600">
                    {appStatus}
                  </div>
                )}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-[13px] font-medium text-[#3D4A44] mb-1.5">Full Name *</label>
                    <input
                      type="text"
                      value={appForm.name}
                      onChange={(e) => setAppForm({ ...appForm, name: e.target.value })}
                      required
                      className="w-full px-4 py-3 bg-[#FAFBF9] border border-[rgba(59,77,67,0.12)] rounded-xl text-[15px] text-[#3D4A44] focus:outline-none focus:border-[#5B8A72] focus:ring-2 focus:ring-[#5B8A72]/20 transition-all"
                      placeholder="Your name"
                    />
                  </div>
                  <div>
                    <label className="block text-[13px] font-medium text-[#3D4A44] mb-1.5">Email *</label>
                    <input
                      type="email"
                      value={appForm.email}
                      onChange={(e) => setAppForm({ ...appForm, email: e.target.value })}
                      required
                      className="w-full px-4 py-3 bg-[#FAFBF9] border border-[rgba(59,77,67,0.12)] rounded-xl text-[15px] text-[#3D4A44] focus:outline-none focus:border-[#5B8A72] focus:ring-2 focus:ring-[#5B8A72]/20 transition-all"
                      placeholder="you@email.com"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-[13px] font-medium text-[#3D4A44] mb-1.5">Role *</label>
                  <select
                    value={appForm.role}
                    onChange={(e) => setAppForm({ ...appForm, role: e.target.value })}
                    required
                    className="w-full px-4 py-3 bg-[#FAFBF9] border border-[rgba(59,77,67,0.12)] rounded-xl text-[15px] text-[#3D4A44] focus:outline-none focus:border-[#5B8A72] focus:ring-2 focus:ring-[#5B8A72]/20 transition-all"
                  >
                    <option value="">Select a role</option>
                    {ROLE_OPTIONS.map((r) => (
                      <option key={r} value={r}>{r}</option>
                    ))}
                  </select>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-[13px] font-medium text-[#3D4A44] mb-1.5">Location Preference</label>
                    <select
                      value={appForm.location}
                      onChange={(e) => setAppForm({ ...appForm, location: e.target.value })}
                      className="w-full px-4 py-3 bg-[#FAFBF9] border border-[rgba(59,77,67,0.12)] rounded-xl text-[15px] text-[#3D4A44] focus:outline-none focus:border-[#5B8A72] focus:ring-2 focus:ring-[#5B8A72]/20 transition-all"
                    >
                      <option value="">Select preference</option>
                      <option value="Hybrid - Atlanta, GA">Hybrid - Atlanta, GA</option>
                      <option value="Hybrid - Los Angeles, CA">Hybrid - Los Angeles, CA</option>
                      <option value="Remote">Remote</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-[13px] font-medium text-[#3D4A44] mb-1.5">LinkedIn URL</label>
                    <input
                      type="url"
                      value={appForm.linkedin}
                      onChange={(e) => setAppForm({ ...appForm, linkedin: e.target.value })}
                      className="w-full px-4 py-3 bg-[#FAFBF9] border border-[rgba(59,77,67,0.12)] rounded-xl text-[15px] text-[#3D4A44] focus:outline-none focus:border-[#5B8A72] focus:ring-2 focus:ring-[#5B8A72]/20 transition-all"
                      placeholder="linkedin.com/in/..."
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-[13px] font-medium text-[#3D4A44] mb-1.5">Portfolio / GitHub / Website</label>
                  <input
                    type="url"
                    value={appForm.portfolio}
                    onChange={(e) => setAppForm({ ...appForm, portfolio: e.target.value })}
                    className="w-full px-4 py-3 bg-[#FAFBF9] border border-[rgba(59,77,67,0.12)] rounded-xl text-[15px] text-[#3D4A44] focus:outline-none focus:border-[#5B8A72] focus:ring-2 focus:ring-[#5B8A72]/20 transition-all"
                    placeholder="Your portfolio or GitHub link"
                  />
                </div>
                <div>
                  <label className="block text-[13px] font-medium text-[#3D4A44] mb-1.5">Relevant Experience</label>
                  <textarea
                    value={appForm.experience}
                    onChange={(e) => setAppForm({ ...appForm, experience: e.target.value })}
                    rows={3}
                    className="w-full px-4 py-3 bg-[#FAFBF9] border border-[rgba(59,77,67,0.12)] rounded-xl text-[15px] text-[#3D4A44] focus:outline-none focus:border-[#5B8A72] focus:ring-2 focus:ring-[#5B8A72]/20 transition-all resize-none"
                    placeholder="Tell us about your relevant experience..."
                  />
                </div>
                <div>
                  <label className="block text-[13px] font-medium text-[#3D4A44] mb-1.5">Why Cadence?</label>
                  <textarea
                    value={appForm.why_cadence}
                    onChange={(e) => setAppForm({ ...appForm, why_cadence: e.target.value })}
                    rows={3}
                    className="w-full px-4 py-3 bg-[#FAFBF9] border border-[rgba(59,77,67,0.12)] rounded-xl text-[15px] text-[#3D4A44] focus:outline-none focus:border-[#5B8A72] focus:ring-2 focus:ring-[#5B8A72]/20 transition-all resize-none"
                    placeholder="What excites you about working at an early-stage music tech company?"
                  />
                </div>
                <div>
                  <label className="block text-[13px] font-medium text-[#3D4A44] mb-1.5">Resume (PDF or Word)</label>
                  <div className="relative">
                    <input
                      type="file"
                      accept=".pdf,.doc,.docx,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                      onChange={(e) => setResumeFile(e.target.files[0] || null)}
                      className="hidden"
                      id="resume-upload"
                    />
                    <label
                      htmlFor="resume-upload"
                      className="flex items-center gap-3 w-full px-4 py-3 bg-[#FAFBF9] border border-[rgba(59,77,67,0.12)] rounded-xl text-[15px] cursor-pointer hover:border-[#5B8A72] transition-all"
                    >
                      <svg className="w-5 h-5 text-[#7A8580] shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
                      </svg>
                      <span className={resumeFile ? 'text-[#3D4A44]' : 'text-[#7A8580]'}>
                        {resumeFile ? resumeFile.name : 'Upload your resume'}
                      </span>
                      {resumeFile && (
                        <button
                          type="button"
                          onClick={(e) => { e.preventDefault(); setResumeFile(null); document.getElementById('resume-upload').value = '' }}
                          className="ml-auto text-[#7A8580] hover:text-red-500 transition-colors"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      )}
                    </label>
                  </div>
                  <p className="text-[11px] text-[#B0B8B3] mt-1">Max 10MB. PDF or Word format.</p>
                </div>
                <button
                  type="submit"
                  disabled={appLoading}
                  className="w-full px-6 py-3.5 bg-gradient-to-r from-[#5B8A72] to-[#6B9A84] text-white font-semibold text-[15px] rounded-xl hover:shadow-lg hover:shadow-[#5B8A72]/25 transition-all disabled:opacity-60"
                >
                  {appLoading ? 'Submitting...' : 'Submit Application'}
                </button>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
