import React from 'react'
import PublicPageLayout from '../components/PublicPageLayout'

export default function AboutPage() {
  return (
    <PublicPageLayout>
      <div className="space-y-10">
        <div className="text-center mb-12">
          <h1 className="text-[32px] sm:text-[44px] font-bold text-[#3D4A44] leading-tight mb-4">
            Treat your catalog like the financial asset it is.
          </h1>
          <p className="text-[17px] sm:text-[19px] text-[#7A8580] leading-relaxed max-w-2xl mx-auto">
            Cadence is the operating system for modern music catalogs — built for labels, publishers, managers, and rights holders who are tired of running a multi-million-dollar business on spreadsheets.
          </p>
        </div>

        <section>
          <h2 className="text-[22px] font-bold text-[#3D4A44] mb-4">The Problem We Solve</h2>
          <div className="text-[15px] text-[#5A6660] leading-relaxed space-y-4">
            <p>
              The music industry generates billions of dollars a year in recorded music and publishing revenue, yet the people who own those catalogs still manage them with tools built for a different era. Royalty statements arrive as 500-page PDFs. Splits live in email threads. Schedule A documents take weeks to assemble. Catalog valuations are guesswork. And when it's time to sell, refinance, or audit a catalog, the data is scattered across a dozen systems that were never designed to talk to each other.
            </p>
            <p>Cadence exists to change that.</p>
          </div>
        </section>

        <section>
          <h2 className="text-[22px] font-bold text-[#3D4A44] mb-4">What Cadence Does</h2>
          <p className="text-[15px] text-[#5A6660] leading-relaxed mb-5">
            Cadence is a multi-tenant SaaS platform that brings catalog management, rights intelligence, royalty processing, and valuation into a single system. We built it around one idea: every song in your catalog is a financial asset, and it deserves to be tracked, analyzed, and valued like one.
          </p>
          <p className="text-[15px] text-[#5A6660] leading-relaxed mb-4">With Cadence, you can:</p>
          <ul className="space-y-3">
            {[
              { title: 'Manage your catalog end-to-end', desc: 'from unreleased demos to fully commercialized recordings, with automated release triggers and date-stamped edit history for every work.' },
              { title: 'Process royalty statements intelligently', desc: 'upload statements from BMI, ASCAP, the MLC, distributors, and sub-publishers, and let the royalty engine normalize line items down to the individual song and client.' },
              { title: 'Value your catalog with real data', desc: 'combine years of statement history with streaming consumption data to generate defensible catalog valuations.' },
              { title: 'Audit your earnings', desc: 'cross-reference what you were paid against what you should have been paid, and catch missing streams before they disappear.' },
              { title: 'Pitch for sync with AI', desc: 'match your catalog to sync briefs automatically using metadata-driven search.' },
              { title: 'Give clients their own portal', desc: 'let the creators you represent log in, review their catalog, upload contracts, and see their earnings without a phone call.' },
            ].map((item, i) => (
              <li key={i} className="flex items-start gap-3 text-[15px] text-[#5A6660]">
                <span className="w-1.5 h-1.5 rounded-full bg-[#5B8A72] mt-2 flex-shrink-0" />
                <span><strong className="text-[#3D4A44]">{item.title}</strong> — {item.desc}</span>
              </li>
            ))}
          </ul>
        </section>

        <section>
          <h2 className="text-[22px] font-bold text-[#3D4A44] mb-4">Who We Built It For</h2>
          <p className="text-[15px] text-[#5A6660] leading-relaxed">
            Cadence serves independent labels, music publishers, production companies, artist managers, catalog investors, and the administrators who support them. Whether you manage ten songs or ten thousand, the platform scales with you.
          </p>
        </section>

        <section>
          <h2 className="text-[22px] font-bold text-[#3D4A44] mb-4">Our Philosophy</h2>
          <p className="text-[15px] text-[#5A6660] leading-relaxed mb-5">
            Software in the music industry is too often designed for accountants or engineers, not for the creative people whose livelihoods depend on it. Cadence is built on three principles:
          </p>
          <ol className="space-y-4">
            {[
              { title: 'Simplicity over jargon.', desc: "If a kindergartener couldn't figure out the core workflow, we haven't finished designing it." },
              { title: 'The catalog is the asset.', desc: 'Every feature should help you understand, grow, or defend the value of your catalog.' },
              { title: 'Your data is yours.', desc: 'We give you the tools, but you own everything you put into the platform. Export at any time. No lock-in.' },
            ].map((item, i) => (
              <li key={i} className="flex items-start gap-3 text-[15px] text-[#5A6660]">
                <span className="w-6 h-6 rounded-full bg-[#5B8A72]/10 text-[#5B8A72] flex items-center justify-center flex-shrink-0 text-[13px] font-bold mt-0.5">{i + 1}</span>
                <span><strong className="text-[#3D4A44]">{item.title}</strong> {item.desc}</span>
              </li>
            ))}
          </ol>
        </section>

        <section>
          <h2 className="text-[22px] font-bold text-[#3D4A44] mb-4">Where We Are</h2>
          <p className="text-[15px] text-[#5A6660] leading-relaxed">
            Cadence Catalog Intelligence Co. is a Delaware C-Corporation headquartered in Atlanta, Georgia, with team members across the United States and the Caribbean.
          </p>
        </section>

        <section className="bg-gradient-to-br from-[#5B8A72]/5 to-[#7BA594]/5 rounded-2xl p-8 text-center">
          <h2 className="text-[22px] font-bold text-[#3D4A44] mb-3">Get In Touch</h2>
          <p className="text-[15px] text-[#5A6660] leading-relaxed">
            To request a demo, partner with us, or learn more about Cadence, reach out at{' '}
            <a href="mailto:communication@cadence-ci.com" className="text-[#5B8A72] font-medium hover:underline">
              communication@cadence-ci.com
            </a>.
          </p>
        </section>
      </div>
    </PublicPageLayout>
  )
}
