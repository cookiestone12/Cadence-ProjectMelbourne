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
    <div className="container mx-auto px-4 py-8 bg-void-black min-h-screen">
      <h1 className="text-3xl font-bold font-heading mb-8 uppercase tracking-wide">Admin Settings</h1>

      <div className="max-w-2xl bg-surface-black border border-border-grey rounded shadow-lg p-6 mb-6 hover:border-signal-red transition-colors duration-200">
        <h2 className="text-xl font-bold font-heading mb-4 uppercase tracking-wide">API Configuration Status</h2>
        <div className="space-y-3">
          {Object.entries(apiStatus).map(([key, configured]) => (
            <div key={key} className="flex items-center justify-between py-2 border-b border-border-grey">
              <span className="font-medium text-tech-grey uppercase text-sm tracking-wide">{key}</span>
              <span className={`px-3 py-1 rounded text-sm font-bold border ${
                configured 
                  ? 'bg-green-500 bg-opacity-20 text-green-400 border-green-500' 
                  : 'bg-orange-500 bg-opacity-20 text-orange-400 border-orange-500'
              }`}>
                {configured ? 'Configured' : 'Using Mock Data'}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="max-w-2xl bg-signal-red bg-opacity-10 border-l-4 border-signal-red p-4 rounded">
        <h3 className="font-semibold mb-2 uppercase tracking-wide">How to Configure API Keys:</h3>
        <ol className="list-decimal list-inside space-y-2 text-sm text-tech-grey">
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
        <div className="max-w-2xl mt-4 p-4 bg-signal-red bg-opacity-20 border border-signal-red text-signal-red rounded">
          {message}
        </div>
      )}
    </div>
  )
}
