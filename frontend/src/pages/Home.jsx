import React from 'react'
import { Link } from 'react-router-dom'

export default function Home() {
  const handleDownloadTemplate = () => {
    window.open('/attached_assets/MIME_Song_Registration_Template_1762653175934.pdf', '_blank')
  }

  return (
    <div className="min-h-screen">
      <div className="bg-gradient-to-r from-mime-purple to-mime-orange text-white py-20">
        <div className="container mx-auto px-4 text-center">
          <h1 className="text-5xl font-bold mb-4">MIME Catalog Intelligence</h1>
          <p className="text-xl mb-8">Music Publishing Analytics & Valuation Platform</p>
          <Link
            to="/login"
            className="bg-white text-mime-purple px-8 py-3 rounded-lg font-semibold hover:bg-gray-100 inline-block"
          >
            Get Started
          </Link>
        </div>
      </div>
      
      <div className="container mx-auto px-4 py-16">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold mb-8 text-center">How It Works</h2>
          
          <div className="grid md:grid-cols-3 gap-8 mb-12">
            <div className="text-center">
              <div className="bg-mime-purple text-white rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4 text-2xl font-bold">
                1
              </div>
              <h3 className="font-semibold mb-2">Download Template</h3>
              <p className="text-gray-600">Get the Schedule A template and fill in your catalog information</p>
            </div>
            <div className="text-center">
              <div className="bg-mime-orange text-white rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4 text-2xl font-bold">
                2
              </div>
              <h3 className="font-semibold mb-2">Upload</h3>
              <p className="text-gray-600">Upload your completed template through our secure platform</p>
            </div>
            <div className="text-center">
              <div className="bg-mime-purple text-white rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4 text-2xl font-bold">
                3
              </div>
              <h3 className="font-semibold mb-2">Analyze</h3>
              <p className="text-gray-600">View valuations, scores, and analytics for your entire catalog</p>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-lg p-8 text-center">
            <h3 className="text-2xl font-bold mb-4">Schedule A Template</h3>
            <p className="text-gray-600 mb-6">
              Download our official Schedule A template to register your songs. Fill in songwriter details 
              and catalog information, then upload through the dashboard.
            </p>
            <button
              onClick={handleDownloadTemplate}
              className="bg-mime-purple text-white px-8 py-3 rounded-lg font-semibold hover:bg-opacity-90"
            >
              Download Template
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
