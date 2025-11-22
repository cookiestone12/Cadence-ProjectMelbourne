import React from 'react'
import { Link } from 'react-router-dom'

export default function Home() {
  const handleDownloadTemplate = () => {
    alert('Ampersound Schedule A template coming soon. Please contact support for template access.')
  }

  return (
    <div className="min-h-screen bg-void-black">
      <div className="bg-surface-black text-white py-20 border-b-4 border-signal-red">
        <div className="container mx-auto px-4 text-center">
          <h1 className="text-5xl font-bold font-heading mb-4 uppercase tracking-wide">Ampersound Catalog Intelligence</h1>
          <p className="text-xl mb-8 text-tech-grey">Music Publishing Analytics & Valuation Platform</p>
          <Link
            to="/login"
            className="bg-signal-red text-white px-8 py-3 rounded font-bold shadow-red-glow hover:shadow-red-glow-intense hover:scale-105 transition-all duration-200 inline-block uppercase tracking-wide"
          >
            Get Started
          </Link>
        </div>
      </div>
      
      <div className="container mx-auto px-4 py-16">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold font-heading mb-8 text-center uppercase tracking-wide">How It Works</h2>
          
          <div className="grid md:grid-cols-3 gap-8 mb-12">
            <div className="text-center">
              <div className="bg-signal-red text-white rounded w-16 h-16 flex items-center justify-center mx-auto mb-4 text-2xl font-bold shadow-red-glow">
                1
              </div>
              <h3 className="font-semibold font-heading mb-2 text-white uppercase text-sm tracking-wide">Download Template</h3>
              <p className="text-tech-grey text-sm">Get the Schedule A template and fill in your catalog information</p>
            </div>
            <div className="text-center">
              <div className="bg-signal-red text-white rounded w-16 h-16 flex items-center justify-center mx-auto mb-4 text-2xl font-bold shadow-red-glow">
                2
              </div>
              <h3 className="font-semibold font-heading mb-2 text-white uppercase text-sm tracking-wide">Upload</h3>
              <p className="text-tech-grey text-sm">Upload your completed template through our secure platform</p>
            </div>
            <div className="text-center">
              <div className="bg-signal-red text-white rounded w-16 h-16 flex items-center justify-center mx-auto mb-4 text-2xl font-bold shadow-red-glow">
                3
              </div>
              <h3 className="font-semibold font-heading mb-2 text-white uppercase text-sm tracking-wide">Analyze</h3>
              <p className="text-tech-grey text-sm">View valuations, scores, and analytics for your entire catalog</p>
            </div>
          </div>

          <div className="bg-surface-black rounded border border-border-grey shadow-lg p-8 text-center hover:border-signal-red transition-colors duration-200">
            <h3 className="text-2xl font-bold font-heading mb-4 uppercase tracking-wide">Schedule A Template</h3>
            <p className="text-tech-grey mb-6">
              Download our official Schedule A template to register your songs. Fill in songwriter details 
              and catalog information, then upload through the dashboard.
            </p>
            <button
              onClick={handleDownloadTemplate}
              className="bg-signal-red text-white px-8 py-3 rounded font-bold shadow-red-glow hover:shadow-red-glow-intense hover:scale-105 transition-all duration-200 uppercase tracking-wide"
            >
              Download Template
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
