import React, { useState, useEffect } from 'react'
import axios from 'axios'

export default function Settings() {
  const [apiStatus, setApiStatus] = useState({})
  const [settings, setSettings] = useState({
    CHARTMETRIC_API_KEY: '',
    SPOTIFY_CLIENT_ID: '',
    SPOTIFY_CLIENT_SECRET: '',
    LUMINATE_API_KEY: '',
    CLAUDE_API_KEY: ''
  })
  const [message, setMessage] = useState('')

  useEffect(() => {
    fetchApiStatus()
  }, [])

  const fetchApiStatus = async () => {
    try {
      const response = await axios.get('/api/settings/api-status')
      setApiStatus(response.data)
    } catch (error) {
      console.error('Error fetching API status:', error)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setMessage('API keys should be set in Replit Secrets. This interface is for display only.')
  }

  return (
    <div className="min-h-screen bg-[#F5F7F4] p-6 lg:p-8">
      <div className="max-w-3xl mx-auto">
        <div className="mb-8">
          <h1 className="text-[34px] font-semibold text-[#3D4A44] leading-tight">Admin Settings</h1>
          <p className="text-[17px] text-[#7A8580] mt-1">Manage API integrations and configurations</p>
        </div>

        <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6 mb-6">
          <h2 className="text-[22px] font-medium text-[#3D4A44] mb-5">API Configuration Status</h2>
          <div className="space-y-3">
            {Object.entries(apiStatus).map(([key, configured]) => (
              <div key={key} className="flex items-center justify-between py-3 border-b border-[rgba(59,77,67,0.08)] last:border-0">
                <span className="text-[15px] font-medium text-[#3D4A44]">{key}</span>
                <span className={`px-3 py-1.5 rounded-full text-[13px] font-medium ${
                  configured 
                    ? 'bg-[rgba(91,154,110,0.15)] text-[#5B9A6E]' 
                    : 'bg-[rgba(196,149,107,0.15)] text-[#C4956B]'
                }`}>
                  {configured ? 'Configured' : 'Using Mock Data'}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-gradient-to-br from-[rgba(91,138,114,0.08)] to-[rgba(123,165,148,0.08)] rounded-[18px] p-6 border-l-4 border-[#5B8A72]">
          <h3 className="text-[17px] font-semibold text-[#3D4A44] mb-3">How to Configure API Keys</h3>
          <ol className="list-decimal list-inside space-y-2 text-[15px] text-[#7A8580]">
            <li>Go to the Replit Secrets panel (Tools → Secrets or the lock icon)</li>
            <li>Add the following environment variables:
              <ul className="ml-6 mt-2 space-y-1 list-disc">
                <li>CHARTMETRIC_API_KEY</li>
                <li>SPOTIFY_CLIENT_ID</li>
                <li>SPOTIFY_CLIENT_SECRET</li>
                <li>LUMINATE_API_KEY</li>
                <li>CLAUDE_API_KEY (for future AI features)</li>
              </ul>
            </li>
            <li>Restart the application after adding secrets</li>
            <li>The system will automatically switch from mock data to real API calls</li>
          </ol>
        </div>

        {message && (
          <div className="mt-6 p-4 bg-[rgba(196,112,104,0.1)] border border-[rgba(196,112,104,0.3)] text-[#C47068] rounded-[14px] text-[15px]">
            {message}
          </div>
        )}
      </div>
    </div>
  )
}
