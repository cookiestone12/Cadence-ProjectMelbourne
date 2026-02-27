import React from 'react'
import { Link } from 'react-router-dom'

export default function Home() {
  const handleDownloadTemplate = () => {
    window.location.href = '/api/catalog/template/schedule-a'
  }

  return (
    <div className="min-h-screen bg-am-bg">
      {/* Hero Section */}
      <div className="bg-gradient-to-br from-am-accent to-am-accent-light text-white py-24 relative overflow-hidden">
        <div className="absolute inset-0 bg-[url('data:image/svg+xml,%3Csvg%20width%3D%2260%22%20height%3D%2260%22%20viewBox%3D%220%200%2060%2060%22%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%3E%3Cg%20fill%3D%22none%22%20fill-rule%3D%22evenodd%22%3E%3Cg%20fill%3D%22%23ffffff%22%20fill-opacity%3D%220.05%22%3E%3Cpath%20d%3D%22M36%2034v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6%2034v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6%204V0H4v4H0v2h4v4h2V6h4V4H6z%22%2F%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fsvg%3E')] opacity-50"></div>
        <div className="container mx-auto px-4 text-center relative z-10">
          <div className="flex justify-center mb-6">
            <img src="/cadence-logo.png" alt="Cadence" className="h-20 w-auto drop-shadow-lg" onError={(e) => e.target.style.display = 'none'} />
          </div>
          <h1 className="text-5xl font-bold mb-4 tracking-tight">Cadence</h1>
          <p className="text-xl mb-10 text-white/80 max-w-2xl mx-auto">Catalog Intelligence</p>
          <Link
            to="/login"
            className="bg-white text-am-accent px-8 py-3.5 rounded-full font-semibold shadow-am-lg hover:shadow-am-xl hover:scale-[1.02] active:scale-[0.98] transition-all duration-200 inline-block"
          >
            Get Started
          </Link>
        </div>
      </div>
      
      {/* How It Works */}
      <div className="container mx-auto px-4 py-20">
        <div className="max-w-4xl mx-auto">
          <h2 className="am-text-title-1 text-center mb-12">How It Works</h2>
          
          <div className="grid md:grid-cols-3 gap-8 mb-16">
            <div className="text-center">
              <div className="bg-gradient-to-br from-am-accent to-am-accent-light text-white rounded-2xl w-16 h-16 flex items-center justify-center mx-auto mb-5 text-2xl font-bold shadow-am-md">
                1
              </div>
              <h3 className="font-semibold mb-2 text-am-text text-[17px]">Add Your Creators</h3>
              <p className="text-am-text-secondary text-[15px]">Build your roster of songwriters, artists, and producers</p>
            </div>
            <div className="text-center">
              <div className="bg-gradient-to-br from-am-accent to-am-accent-light text-white rounded-2xl w-16 h-16 flex items-center justify-center mx-auto mb-5 text-2xl font-bold shadow-am-md">
                2
              </div>
              <h3 className="font-semibold mb-2 text-am-text text-[17px]">Import Catalogs</h3>
              <p className="text-am-text-secondary text-[15px]">Upload your catalog via CSV with AI-powered column mapping</p>
            </div>
            <div className="text-center">
              <div className="bg-gradient-to-br from-am-accent to-am-accent-light text-white rounded-2xl w-16 h-16 flex items-center justify-center mx-auto mb-5 text-2xl font-bold shadow-am-md">
                3
              </div>
              <h3 className="font-semibold mb-2 text-am-text text-[17px]">Track & Analyze</h3>
              <p className="text-am-text-secondary text-[15px]">Monitor health scores, placements, and catalog valuations</p>
            </div>
          </div>

          {/* Features Grid */}
          <div className="grid md:grid-cols-2 gap-5 mb-16">
            <div className="am-card am-card-interactive p-6">
              <h3 className="am-text-headline mb-2">Health Scoring</h3>
              <p className="text-am-text-secondary text-[15px]">Track catalog completeness with weighted health scores based on ISRC, ISWC, PRO registration, and more.</p>
            </div>
            <div className="am-card am-card-interactive p-6">
              <h3 className="am-text-headline mb-2">Catalog Valuation</h3>
              <p className="text-am-text-secondary text-[15px]">Advanced valuation tools using multiple methodologies including streaming multiples and market comparables.</p>
            </div>
            <div className="am-card am-card-interactive p-6">
              <h3 className="am-text-headline mb-2">Placement Tracking</h3>
              <p className="text-am-text-secondary text-[15px]">Visual pipeline from offer to payment with comprehensive placement management.</p>
            </div>
            <div className="am-card am-card-interactive p-6">
              <h3 className="am-text-headline mb-2">Action Items</h3>
              <p className="text-am-text-secondary text-[15px]">Proactive task management with deadline tracking and automated gap detection.</p>
            </div>
          </div>

          {/* Schedule A Download */}
          <div className="am-card p-10 text-center">
            <h3 className="am-text-title-2 mb-4">Schedule A Template</h3>
            <p className="text-am-text-secondary mb-8 max-w-lg mx-auto">
              Download our official Schedule A template to register your songs. Fill in songwriter details 
              and catalog information, then upload through the dashboard.
            </p>
            <button
              onClick={handleDownloadTemplate}
              className="am-btn am-btn-primary"
            >
              Download Template
            </button>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="bg-am-text py-10">
        <div className="container mx-auto px-4 text-center">
          <p className="text-white/50 text-[13px]">© 2026 Cadence. All rights reserved.</p>
        </div>
      </div>
    </div>
  )
}
