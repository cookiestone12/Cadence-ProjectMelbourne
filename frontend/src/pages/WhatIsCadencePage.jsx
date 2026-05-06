import React from 'react'
import PublicNav from '../components/PublicNav'
import PublicFooter from '../components/PublicFooter'
import SEO from '../components/SEO'

export default function WhatIsCadencePage() {
  return (
    <div className="min-h-screen bg-[#FAFBF9] flex flex-col">
      <SEO
        path="/what-is-cadence"
        title="What Is Cadence Catalog Intelligence"
        description="Cadence Catalog Intelligence is the SaaS platform for music publishers, labels, managers, and rights holders. End-to-end music catalog management software, defensible catalog valuation, royalty processing, rights administration, sync placements, creator portals, and streaming intelligence — purpose-built as a publisher analytics platform and rights management for music solution. Not affiliated with Cadence Design Systems."
      />
      <PublicNav />
      <main className="flex-1 pt-28 pb-16 px-6">
        <div className="max-w-4xl mx-auto">
          <header className="text-center mb-14">
            <h1 className="text-[32px] sm:text-[44px] font-bold text-[#3D4A44] leading-tight mb-4">
              The intelligence layer for music catalogs
            </h1>
            <p className="text-[16px] text-[#7A8580] max-w-2xl mx-auto leading-relaxed">
              Cadence Catalog Intelligence is purpose-built for the people who own, administer, and finance music rights — independent publishers, labels, managers, and catalog investors who need a modern operating system instead of a spreadsheet.
            </p>
          </header>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div className="bg-white/80 backdrop-blur-sm rounded-[20px] p-6 border border-[rgba(59,77,67,0.06)]">
              <h2 className="text-[17px] font-semibold text-[#3D4A44] mb-3">Music catalog management, end to end</h2>
              <p className="text-[14px] text-[#7A8580] leading-relaxed">
                Manage your entire catalog from a single workspace — unreleased demos through fully commercialized recordings. Cadence tracks every song, split, contract, and contributor with date-stamped edit history, so the provenance of every work is verifiable. Import directly from Spotify, scan Dropbox or Google Drive folders, or upload Schedule A documents and let our AI map the columns for you.
              </p>
            </div>

            <div className="bg-white/80 backdrop-blur-sm rounded-[20px] p-6 border border-[rgba(59,77,67,0.06)]">
              <h2 className="text-[17px] font-semibold text-[#3D4A44] mb-3">Defensible catalog valuation</h2>
              <p className="text-[14px] text-[#7A8580] leading-relaxed">
                Cadence's catalog valuation engine combines years of royalty history with streaming consumption data to produce defensible numbers. Compare Income, Market Comparable, DCF, and Blended methodologies side by side, apply your own multiples, run scenarios, and export PDF reports your buyers, lenders, and underwriters will actually trust. Whether you're refinancing, selling, or simply forecasting, you'll know what every asset in your portfolio is worth.
              </p>
            </div>

            <div className="bg-white/80 backdrop-blur-sm rounded-[20px] p-6 border border-[rgba(59,77,67,0.06)]">
              <h2 className="text-[17px] font-semibold text-[#3D4A44] mb-3">Royalty processing without the spreadsheets</h2>
              <p className="text-[14px] text-[#7A8580] leading-relaxed">
                Upload royalty statements from BMI, ASCAP, the MLC, distributors, and sub-publishers. Cadence's royalty engine normalizes line items down to the song and client, calculates what each creator is owed under their splits, runs a four-check audit (cross-statement, rate, missing-period, decay-anomaly), and surfaces unmatched transactions before they cost you money. Multi-currency, multi-source, fully reconciled.
              </p>
            </div>

            <div className="bg-white/80 backdrop-blur-sm rounded-[20px] p-6 border border-[rgba(59,77,67,0.06)]">
              <h2 className="text-[17px] font-semibold text-[#3D4A44] mb-3">Rights administration and contract intelligence</h2>
              <p className="text-[14px] text-[#7A8580] leading-relaxed">
                Track deal-level contracts, asset-level rights splits, advances, and recoupment in one place. Upload a contract PDF and let our AI extract the key terms — title, parties, territory, term, advance — for review. Link contracts to the songs they govern, share documents securely with co-administrators, and keep a complete audit trail of every rights change.
              </p>
            </div>

            <div className="bg-white/80 backdrop-blur-sm rounded-[20px] p-6 border border-[rgba(59,77,67,0.06)]">
              <h2 className="text-[17px] font-semibold text-[#3D4A44] mb-3">Sync placements and creator portals</h2>
              <p className="text-[14px] text-[#7A8580] leading-relaxed">
                Pitch for sync with AI-driven brief matching, track every placement through a status pipeline from pitch to paid, and give the creators you represent their own organization-managed portal. Clients log in to see their catalog, statements, contracts, and earnings — without ever seeing another client's data. Cross-organization sharing lets co-publishers and administrators collaborate with granular permissions.
              </p>
            </div>

            <div className="bg-white/80 backdrop-blur-sm rounded-[20px] p-6 border border-[rgba(59,77,67,0.06)]">
              <h2 className="text-[17px] font-semibold text-[#3D4A44] mb-3">Streaming intelligence and chart data</h2>
              <p className="text-[14px] text-[#7A8580] leading-relaxed">
                Cadence integrates Spotify popularity, Last.fm, YouTube, and Luminate-ready streaming metrics, then cross-references them against your statements to flag missing periods, decay anomalies, and underpaid streams. The result is a real, data-driven picture of how your catalog is performing across every platform — and where the next opportunity is hiding.
              </p>
            </div>
          </div>

          <p className="text-[14px] text-[#7A8580] text-center max-w-3xl mx-auto mt-12 leading-relaxed">
            Cadence is music catalog management software, a publisher analytics platform, and a rights management for music solution rolled into one. Built by Cadence Catalog Intelligence Co. — a Delaware C-Corporation headquartered in Atlanta, Georgia — for the modern music industry. Your catalog is a financial asset. Treat it like one. (Cadence Catalog Intelligence is not affiliated with Cadence Design Systems.)
          </p>
        </div>
      </main>
      <PublicFooter />
    </div>
  )
}
