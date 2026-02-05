import React, { useState, useEffect } from 'react'
import axios from 'axios'
import { BellIcon, KeyIcon, EnvelopeIcon } from '@heroicons/react/24/outline'

const NOTIFICATION_TYPES = {
  MISSING_ISRC: { label: 'Missing ISRC', description: 'Alert when songs are missing ISRC codes' },
  MISSING_ISWC: { label: 'Missing ISWC', description: 'Alert when songs are missing ISWC codes' },
  CONTRACT_PENDING: { label: 'Contract Pending', description: 'Reminder for pending contract uploads' },
  PRO_INCOMPLETE: { label: 'PRO Incomplete', description: 'Alert for incomplete PRO registrations' },
  WEEKLY_HEALTH_SUMMARY: { label: 'Weekly Health Summary', description: 'Weekly catalog health report' },
  CUSTOM_DEADLINE: { label: 'Custom Deadlines', description: 'Reminders for custom-set deadlines' },
  SYSTEM_ANNOUNCEMENT: { label: 'System Announcements', description: 'Platform updates and news' },
  CATALOG_UPDATE: { label: 'Catalog Updates', description: 'Changes to your catalog' },
  PLACEMENT_UPDATE: { label: 'Placement Updates', description: 'Placement status changes' }
}

export default function Settings() {
  const [activeTab, setActiveTab] = useState('api')
  const [apiStatus, setApiStatus] = useState({})
  const [preferences, setPreferences] = useState([])
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')

  useEffect(() => {
    fetchApiStatus()
    fetchPreferences()
  }, [])

  const fetchApiStatus = async () => {
    try {
      const response = await axios.get('/api/settings/api-status')
      setApiStatus(response.data)
    } catch (error) {
      console.error('Error fetching API status:', error)
    }
  }

  const fetchPreferences = async () => {
    try {
      const response = await axios.get('/api/notifications/preferences')
      setPreferences(response.data)
    } catch (error) {
      console.error('Error fetching preferences:', error)
    }
  }

  const updatePreference = async (type, field, value) => {
    const current = preferences.find(p => p.notification_type === type) || {
      notification_type: type,
      in_app_enabled: true,
      email_enabled: false,
      frequency: 'immediate'
    }
    
    const updated = { ...current, [field]: value }
    
    try {
      await axios.put('/api/notifications/preferences', updated)
      setPreferences(prev => prev.map(p => 
        p.notification_type === type ? { ...p, [field]: value } : p
      ))
      setMessage('Preference saved')
      setTimeout(() => setMessage(''), 2000)
    } catch (error) {
      console.error('Error updating preference:', error)
      setMessage('Failed to save preference')
    }
  }

  const getPref = (type) => {
    return preferences.find(p => p.notification_type === type) || {
      notification_type: type,
      in_app_enabled: true,
      email_enabled: false,
      frequency: 'immediate'
    }
  }

  return (
    <div className="min-h-screen bg-[#F5F7F4] p-6 lg:p-8">
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-[34px] font-semibold text-[#3D4A44] leading-tight">Settings</h1>
          <p className="text-[17px] text-[#7A8580] mt-1">Manage your preferences and integrations</p>
        </div>

        <div className="mb-6 border-b border-[rgba(59,77,67,0.08)]">
          <div className="flex space-x-8">
            <button
              onClick={() => setActiveTab('api')}
              className={`flex items-center space-x-2 pb-3 px-1 border-b-2 font-medium transition-colors ${
                activeTab === 'api'
                  ? 'border-[#5B8A72] text-[#5B8A72]'
                  : 'border-transparent text-[#7A8580] hover:text-[#3D4A44]'
              }`}
            >
              <KeyIcon className="w-5 h-5" />
              <span>API Integrations</span>
            </button>
            <button
              onClick={() => setActiveTab('notifications')}
              className={`flex items-center space-x-2 pb-3 px-1 border-b-2 font-medium transition-colors ${
                activeTab === 'notifications'
                  ? 'border-[#5B8A72] text-[#5B8A72]'
                  : 'border-transparent text-[#7A8580] hover:text-[#3D4A44]'
              }`}
            >
              <BellIcon className="w-5 h-5" />
              <span>Notifications</span>
            </button>
          </div>
        </div>

        {message && (
          <div className={`mb-6 p-4 rounded-[14px] text-[15px] ${
            message.includes('Failed') 
              ? 'bg-[rgba(196,112,104,0.1)] text-[#C47068]'
              : 'bg-[rgba(91,154,110,0.1)] text-[#5B9A6E]'
          }`}>
            {message}
          </div>
        )}

        {activeTab === 'api' && (
          <>
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
          </>
        )}

        {activeTab === 'notifications' && (
          <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-[22px] font-medium text-[#3D4A44]">Notification Preferences</h2>
                <p className="text-[15px] text-[#7A8580] mt-1">Choose how you want to be notified</p>
              </div>
            </div>

            <div className="space-y-1">
              <div className="grid grid-cols-[1fr,100px,100px,120px] gap-4 px-4 py-2 text-[13px] font-medium text-[#7A8580] uppercase">
                <span>Notification Type</span>
                <span className="text-center">In-App</span>
                <span className="text-center">Email</span>
                <span className="text-center">Frequency</span>
              </div>
              
              {Object.entries(NOTIFICATION_TYPES).map(([type, info]) => {
                const pref = getPref(type)
                return (
                  <div 
                    key={type} 
                    className="grid grid-cols-[1fr,100px,100px,120px] gap-4 items-center px-4 py-4 bg-[#FAFBF9] rounded-xl hover:bg-[#EEF1EC] transition-colors"
                  >
                    <div>
                      <div className="text-[15px] font-medium text-[#3D4A44]">{info.label}</div>
                      <div className="text-[13px] text-[#7A8580]">{info.description}</div>
                    </div>
                    
                    <div className="flex justify-center">
                      <button
                        onClick={() => updatePreference(type, 'in_app_enabled', !pref.in_app_enabled)}
                        className={`w-10 h-6 rounded-full transition-colors relative ${
                          pref.in_app_enabled ? 'bg-[#5B8A72]' : 'bg-[#D1D5DB]'
                        }`}
                      >
                        <span className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${
                          pref.in_app_enabled ? 'left-5' : 'left-1'
                        }`} />
                      </button>
                    </div>
                    
                    <div className="flex justify-center">
                      <button
                        onClick={() => updatePreference(type, 'email_enabled', !pref.email_enabled)}
                        className={`w-10 h-6 rounded-full transition-colors relative ${
                          pref.email_enabled ? 'bg-[#5B8A72]' : 'bg-[#D1D5DB]'
                        }`}
                      >
                        <span className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${
                          pref.email_enabled ? 'left-5' : 'left-1'
                        }`} />
                      </button>
                    </div>
                    
                    <div className="flex justify-center">
                      <select
                        value={pref.frequency}
                        onChange={(e) => updatePreference(type, 'frequency', e.target.value)}
                        className="text-[13px] px-2 py-1 border border-[rgba(59,77,67,0.12)] rounded-lg bg-white text-[#3D4A44] focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                      >
                        <option value="immediate">Immediate</option>
                        <option value="daily">Daily</option>
                        <option value="weekly">Weekly</option>
                      </select>
                    </div>
                  </div>
                )
              })}
            </div>

            <div className="mt-6 p-4 bg-gradient-to-br from-[rgba(91,138,114,0.08)] to-[rgba(123,165,148,0.08)] rounded-xl border-l-4 border-[#5B8A72]">
              <div className="flex items-start space-x-3">
                <EnvelopeIcon className="w-5 h-5 text-[#5B8A72] mt-0.5" />
                <div>
                  <h4 className="text-[15px] font-medium text-[#3D4A44]">Email Notifications</h4>
                  <p className="text-[13px] text-[#7A8580] mt-1">
                    Email notifications will be sent to your registered email address. 
                    Make sure your email is verified in your account settings.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
