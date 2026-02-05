import React from 'react'
import { Link } from 'react-router-dom'

export default function Home() {
  const handleDownloadTemplate = () => {
    window.location.href = '/api/catalog/template/schedule-a'
  }

  return (
    <div className="min-h-screen bg-[#F5F7F4]">
      {/* Hero Section */}
      <div className="bg-gradient-to-br from-[#5B8A72] to-[#7BA594] text-white py-24">
        <div className="container mx-auto px-4 text-center">
          <div className="flex justify-center mb-6">
            <img src="/ampersound-logo.png" alt="Ampersound" className="h-16 w-auto" onError={(e) => e.target.style.display = 'none'} />
          </div>
          <h1 className="text-5xl font-bold mb-4">Ampersound Intelligence</h1>
          <p className="text-xl mb-8 text-white/80">Catalog Manager - Multi-Tenant Rights & Catalog Administration</p>
          <Link
            to="/login"
            className="bg-white text-[#5B8A72] px-8 py-3 rounded-lg font-semibold shadow-lg hover:shadow-xl hover:scale-105 transition-all duration-200 inline-block"
          >
            Get Started
          </Link>
        </div>
      </div>
      
      {/* How It Works */}
      <div className="container mx-auto px-4 py-16">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold mb-8 text-center text-[#3D4A44]">How It Works</h2>
          
          <div className="grid md:grid-cols-3 gap-8 mb-12">
            <div className="text-center">
              <div className="bg-[#5B8A72] text-white rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4 text-2xl font-bold shadow-lg">
                1
              </div>
              <h3 className="font-semibold mb-2 text-[#3D4A44]">Add Your Creators</h3>
              <p className="text-[#7A8580] text-sm">Build your roster of songwriters, artists, and producers</p>
            </div>
            <div className="text-center">
              <div className="bg-[#5B8A72] text-white rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4 text-2xl font-bold shadow-lg">
                2
              </div>
              <h3 className="font-semibold mb-2 text-[#3D4A44]">Import Catalogs</h3>
              <p className="text-[#7A8580] text-sm">Upload your catalog via CSV with AI-powered column mapping</p>
            </div>
            <div className="text-center">
              <div className="bg-[#5B8A72] text-white rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4 text-2xl font-bold shadow-lg">
                3
              </div>
              <h3 className="font-semibold mb-2 text-[#3D4A44]">Track & Analyze</h3>
              <p className="text-[#7A8580] text-sm">Monitor health scores, placements, and catalog valuations</p>
            </div>
          </div>

          {/* Features Grid */}
          <div className="grid md:grid-cols-2 gap-6 mb-12">
            <div className="bg-[#FAFBF9] rounded-xl border border-[rgba(59,77,67,0.12)] p-6">
              <h3 className="text-lg font-semibold text-[#3D4A44] mb-2">Health Scoring</h3>
              <p className="text-[#7A8580] text-sm">Track catalog completeness with weighted health scores based on ISRC, ISWC, PRO registration, and more.</p>
            </div>
            <div className="bg-[#FAFBF9] rounded-xl border border-[rgba(59,77,67,0.12)] p-6">
              <h3 className="text-lg font-semibold text-[#3D4A44] mb-2">Catalog Valuation</h3>
              <p className="text-[#7A8580] text-sm">Advanced valuation tools using multiple methodologies including streaming multiples and market comparables.</p>
            </div>
            <div className="bg-[#FAFBF9] rounded-xl border border-[rgba(59,77,67,0.12)] p-6">
              <h3 className="text-lg font-semibold text-[#3D4A44] mb-2">Placement Tracking</h3>
              <p className="text-[#7A8580] text-sm">Visual pipeline from offer to payment with comprehensive placement management.</p>
            </div>
            <div className="bg-[#FAFBF9] rounded-xl border border-[rgba(59,77,67,0.12)] p-6">
              <h3 className="text-lg font-semibold text-[#3D4A44] mb-2">Action Items</h3>
              <p className="text-[#7A8580] text-sm">Proactive task management with deadline tracking and automated gap detection.</p>
            </div>
          </div>

          {/* Schedule A Download */}
          <div className="bg-[#FAFBF9] rounded-xl border border-[rgba(59,77,67,0.12)] shadow-lg p-8 text-center">
            <h3 className="text-2xl font-bold mb-4 text-[#3D4A44]">Schedule A Template</h3>
            <p className="text-[#7A8580] mb-6">
              Download our official Schedule A template to register your songs. Fill in songwriter details 
              and catalog information, then upload through the dashboard.
            </p>
            <button
              onClick={handleDownloadTemplate}
              className="bg-[#5B8A72] text-white px-8 py-3 rounded-lg font-semibold shadow-lg hover:bg-[#4A7A62] hover:shadow-xl transition-all duration-200"
            >
              Download Template
            </button>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="bg-[#3D4A44] text-white py-8">
        <div className="container mx-auto px-4 text-center">
          <p className="text-white/60 text-sm">© 2026 Ampersound Intelligence. All rights reserved.</p>
        </div>
      </div>
    </div>
  )
}
