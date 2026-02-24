import React, { useState, useEffect } from 'react'
import axios from 'axios'
import { BellIcon, KeyIcon, EnvelopeIcon, BuildingOfficeIcon, LockClosedIcon, EyeIcon, EyeSlashIcon, CloudArrowUpIcon, CloudIcon, FolderIcon, CheckCircleIcon, XMarkIcon, DevicePhoneMobileIcon, ArrowDownTrayIcon } from '@heroicons/react/24/outline'
import FolderPicker from '../components/FolderPicker'

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
  const [activeTab, setActiveTab] = useState('notifications')
  const [apiStatus, setApiStatus] = useState({})
  const [preferences, setPreferences] = useState([])
  const [orgSettings, setOrgSettings] = useState([])
  const [organizationId, setOrganizationId] = useState(null)
  const [isOrgAdmin, setIsOrgAdmin] = useState(false)
  const [isSuperAdmin, setIsSuperAdmin] = useState(false)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [passwordForm, setPasswordForm] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  })
  const [passwordError, setPasswordError] = useState('')
  const [passwordSuccess, setPasswordSuccess] = useState('')
  const [changingPassword, setChangingPassword] = useState(false)
  const [emailDigest, setEmailDigest] = useState({
    email_digest_enabled: false,
    schedule_interval: 'weekly',
    min_priority_threshold: 3,
    preferred_hour: 9,
    last_email_sent_at: null,
  })
  const [sendingTest, setSendingTest] = useState(false)
  const [savingDigest, setSavingDigest] = useState(false)
  const [showCurrentPassword, setShowCurrentPassword] = useState(false)
  const [showNewPassword, setShowNewPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [integrations, setIntegrations] = useState({})
  const [connectingDropbox, setConnectingDropbox] = useState(false)
  const [folderPickerOpen, setFolderPickerOpen] = useState(false)
  const [testingConnection, setTestingConnection] = useState(false)
  const [pushSupported, setPushSupported] = useState(false)
  const [pushEnabled, setPushEnabled] = useState(false)
  const [pushLoading, setPushLoading] = useState(false)
  const [sendingTestPush, setSendingTestPush] = useState(false)
  const [installPrompt, setInstallPrompt] = useState(null)
  const [isInstalled, setIsInstalled] = useState(false)

  useEffect(() => {
    fetchUserInfo()
    fetchPreferences()
    fetchOrgData()
    fetchEmailDigest()
    fetchIntegrations()
    checkPushStatus()

    const installed = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone
    setIsInstalled(!!installed)

    const handleBeforeInstall = (e) => {
      e.preventDefault()
      setInstallPrompt(e)
    }
    window.addEventListener('beforeinstallprompt', handleBeforeInstall)

    const params = new URLSearchParams(window.location.search)
    if (params.get('tab') === 'integrations') setActiveTab('integrations')

    return () => window.removeEventListener('beforeinstallprompt', handleBeforeInstall)
  }, [])

  const fetchUserInfo = async () => {
    try {
      const response = await axios.get('/api/auth/me')
      setIsSuperAdmin(response.data.is_super_admin || false)
      if (response.data.is_super_admin) {
        fetchApiStatus()
      }
    } catch (error) {
      console.error('Error fetching user info:', error)
    }
  }

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

  const fetchOrgData = async () => {
    try {
      const orgResponse = await axios.get('/api/organizations/current')
      const orgId = orgResponse.data.id
      setOrganizationId(orgId)
      
      const memberResponse = await axios.get('/api/organizations/current/membership')
      const role = memberResponse.data.role
      setIsOrgAdmin(role === 'OWNER' || role === 'ADMIN')
      
      if (role === 'OWNER' || role === 'ADMIN') {
        const settingsResponse = await axios.get(`/api/notifications/org/${orgId}/settings`)
        setOrgSettings(settingsResponse.data)
      }
    } catch (error) {
      console.error('Error fetching org data:', error)
    }
  }

  const updateOrgSetting = async (type, updates) => {
    if (!organizationId) return
    
    const current = orgSettings.find(s => s.notification_type === type) || {
      notification_type: type,
      default_frequency: 'immediate',
      allow_user_override: true,
      rollup_digest_enabled: false,
      digest_frequency: 'weekly',
      digest_day: 1,
      digest_hour: 9
    }
    
    const updated = { ...current, ...updates }
    
    try {
      await axios.put(`/api/notifications/org/${organizationId}/settings`, updated)
      setOrgSettings(prev => {
        const existingIdx = prev.findIndex(s => s.notification_type === type)
        if (existingIdx >= 0) {
          return prev.map(s => s.notification_type === type ? { ...s, ...updates } : s)
        } else {
          return [...prev, { ...updated, id: 0 }]
        }
      })
      setMessage('Organization setting saved')
      setTimeout(() => setMessage(''), 2000)
    } catch (error) {
      console.error('Error updating org setting:', error)
      setMessage('Failed to save organization setting')
    }
  }

  const getOrgSetting = (type) => {
    return orgSettings.find(s => s.notification_type === type) || {
      notification_type: type,
      default_frequency: 'immediate',
      allow_user_override: true,
      rollup_digest_enabled: false,
      digest_frequency: 'weekly',
      digest_day: 1,
      digest_hour: 9
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
      const existingIdx = preferences.findIndex(p => p.notification_type === type)
      if (existingIdx >= 0) {
        setPreferences(prev => prev.map(p => 
          p.notification_type === type ? { ...p, [field]: value } : p
        ))
      } else {
        setPreferences(prev => [...prev, { ...updated, id: 0 }])
      }
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

  const fetchEmailDigest = async () => {
    try {
      const response = await axios.get('/api/notifications/email-digest')
      setEmailDigest(response.data)
    } catch (error) {
      console.error('Error fetching email digest preferences:', error)
    }
  }

  const updateEmailDigest = async (updates) => {
    const updated = { ...emailDigest, ...updates }
    setSavingDigest(true)
    try {
      await axios.put('/api/notifications/email-digest', {
        email_digest_enabled: updated.email_digest_enabled,
        schedule_interval: updated.schedule_interval,
        min_priority_threshold: updated.min_priority_threshold,
        preferred_hour: updated.preferred_hour,
      })
      setEmailDigest(updated)
      setMessage('Email digest settings saved')
      setTimeout(() => setMessage(''), 2000)
    } catch (error) {
      console.error('Error updating email digest:', error)
      setMessage('Failed to save email digest settings')
    } finally {
      setSavingDigest(false)
    }
  }

  const sendTestEmail = async () => {
    setSendingTest(true)
    try {
      const response = await axios.post('/api/notifications/email-digest/send-test')
      setMessage(response.data.message || 'Test email sent successfully')
      setTimeout(() => setMessage(''), 4000)
    } catch (error) {
      setMessage(error.response?.data?.detail || 'Failed to send test email')
    } finally {
      setSendingTest(false)
    }
  }

  const fetchIntegrations = async () => {
    try {
      const response = await axios.get('/api/integrations/status')
      const raw = response.data?.integrations || []
      const mapped = {}
      raw.forEach(i => {
        const key = (i.provider || '').toLowerCase()
        mapped[key] = {
          connected: true,
          account_email: i.account_email,
          display_name: i.account_display_name,
          default_folder: i.default_folder_path,
          connected_at: i.connected_at,
        }
      })
      setIntegrations(mapped)
    } catch (error) {
      console.error('Error fetching integrations:', error)
    }
  }

  const checkPushStatus = async () => {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
      setPushSupported(false)
      return
    }
    setPushSupported(true)
    try {
      const reg = await navigator.serviceWorker.ready
      const sub = await reg.pushManager.getSubscription()
      setPushEnabled(!!sub)
    } catch {
      setPushEnabled(false)
    }
  }

  const togglePush = async () => {
    setPushLoading(true)
    try {
      const reg = await navigator.serviceWorker.ready
      const existing = await reg.pushManager.getSubscription()

      if (existing) {
        await axios.post('/api/push/unsubscribe', { endpoint: existing.endpoint })
        await existing.unsubscribe()
        setPushEnabled(false)
        setMessage('Push notifications disabled')
      } else {
        const keyResponse = await axios.get('/api/push/vapid-public-key')
        const vapidKey = keyResponse.data.publicKey
        const applicationServerKey = urlBase64ToUint8Array(vapidKey)
        const sub = await reg.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey,
        })
        const subJSON = sub.toJSON()
        await axios.post('/api/push/subscribe', {
          endpoint: subJSON.endpoint,
          keys: {
            p256dh: subJSON.keys.p256dh,
            auth: subJSON.keys.auth,
          },
          userAgent: navigator.userAgent,
        })
        setPushEnabled(true)
        setMessage('Push notifications enabled')
      }
      setTimeout(() => setMessage(''), 3000)
    } catch (err) {
      console.error('Push toggle error:', err)
      setMessage('Failed to update push notifications. Make sure notifications are allowed in your browser.')
      setTimeout(() => setMessage(''), 5000)
    } finally {
      setPushLoading(false)
    }
  }

  const sendTestPush = async () => {
    setSendingTestPush(true)
    try {
      const res = await axios.post('/api/push/test')
      setMessage(`Test notification sent (${res.data.sent} device${res.data.sent !== 1 ? 's' : ''})`)
      setTimeout(() => setMessage(''), 4000)
    } catch (err) {
      setMessage(err.response?.data?.detail || 'Failed to send test notification')
      setTimeout(() => setMessage(''), 5000)
    } finally {
      setSendingTestPush(false)
    }
  }

  const handleInstall = async () => {
    if (!installPrompt) return
    installPrompt.prompt()
    const result = await installPrompt.userChoice
    if (result.outcome === 'accepted') {
      setIsInstalled(true)
      setInstallPrompt(null)
      setMessage('App installed successfully!')
      setTimeout(() => setMessage(''), 3000)
    }
  }

  const urlBase64ToUint8Array = (base64String) => {
    const padding = '='.repeat((4 - base64String.length % 4) % 4)
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
    const rawData = window.atob(base64)
    const outputArray = new Uint8Array(rawData.length)
    for (let i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i)
    }
    return outputArray
  }

  const [dropboxCodeInput, setDropboxCodeInput] = useState('')
  const [showCodeInput, setShowCodeInput] = useState(() => sessionStorage.getItem('dropbox_code_pending') === 'true')

  const connectDropbox = async () => {
    setConnectingDropbox(true)
    try {
      const response = await axios.get('/api/integrations/dropbox/auth-url')
      const authUrl = response.data.auth_url
      setShowCodeInput(true)
      sessionStorage.setItem('dropbox_code_pending', 'true')
      setConnectingDropbox(false)
      const authWindow = window.open(authUrl, '_blank')
      if (!authWindow || authWindow.closed) {
        window.location.href = authUrl
      }
    } catch (error) {
      console.error('Error getting Dropbox auth URL:', error)
      setMessage('Failed to start Dropbox connection')
      setTimeout(() => setMessage(''), 3000)
      setConnectingDropbox(false)
    }
  }

  const submitDropboxCode = async () => {
    if (!dropboxCodeInput.trim()) return
    setConnectingDropbox(true)
    try {
      await axios.post('/api/integrations/dropbox/callback', {
        code: dropboxCodeInput.trim(),
      })
      await fetchIntegrations()
      setMessage('Dropbox connected successfully!')
      setTimeout(() => setMessage(''), 3000)
      setShowCodeInput(false)
      sessionStorage.removeItem('dropbox_code_pending')
      setDropboxCodeInput('')
    } catch (err) {
      console.error('Error completing Dropbox OAuth:', err)
      setMessage('Failed to connect Dropbox. Please check the code and try again.')
      setTimeout(() => setMessage(''), 5000)
    } finally {
      setConnectingDropbox(false)
    }
  }

  const disconnectDropbox = async () => {
    try {
      await axios.delete('/api/integrations/dropbox')
      await fetchIntegrations()
      setMessage('Dropbox disconnected')
      setTimeout(() => setMessage(''), 3000)
    } catch (error) {
      console.error('Error disconnecting Dropbox:', error)
      setMessage('Failed to disconnect Dropbox')
    }
  }

  const handleFolderSelected = async (path) => {
    await setDefaultFolder(path)
  }

  const setDefaultFolder = async (path) => {
    try {
      await axios.put('/api/integrations/dropbox/default-folder', { path })
      await fetchIntegrations()
      setFolderPickerOpen(false)
      setMessage('Default folder updated')
      setTimeout(() => setMessage(''), 3000)
    } catch (error) {
      console.error('Error setting default folder:', error)
      setMessage('Failed to update default folder')
    }
  }

  const testDropboxConnection = async () => {
    setTestingConnection(true)
    try {
      const response = await axios.get('/api/integrations/dropbox/files?path=')
      setMessage('Dropbox connection is working!')
      setTimeout(() => setMessage(''), 3000)
    } catch (error) {
      setMessage('Dropbox connection test failed')
      setTimeout(() => setMessage(''), 3000)
    } finally {
      setTestingConnection(false)
    }
  }

  const handleChangePassword = async (e) => {
    e.preventDefault()
    setPasswordError('')
    setPasswordSuccess('')
    
    if (passwordForm.newPassword !== passwordForm.confirmPassword) {
      setPasswordError('New passwords do not match')
      return
    }
    
    if (passwordForm.newPassword.length < 6) {
      setPasswordError('New password must be at least 6 characters')
      return
    }
    
    setChangingPassword(true)
    try {
      await axios.put('/api/auth/change-password', {
        current_password: passwordForm.currentPassword,
        new_password: passwordForm.newPassword
      })
      setPasswordSuccess('Password changed successfully')
      setPasswordForm({ currentPassword: '', newPassword: '', confirmPassword: '' })
    } catch (error) {
      setPasswordError(error.response?.data?.detail || 'Failed to change password')
    } finally {
      setChangingPassword(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#F5F7F4] p-6 lg:p-8">
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-[34px] font-semibold text-[#3D4A44] leading-tight">Settings</h1>
          <p className="text-[17px] text-[#7A8580] mt-1">Manage your preferences and integrations</p>
        </div>

        <div className="mb-6 border-b border-[rgba(59,77,67,0.08)] overflow-x-auto">
          <div className="flex space-x-4 sm:space-x-8 min-w-max">
            {isSuperAdmin && (
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
            )}
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
            <button
              onClick={() => setActiveTab('password')}
              className={`flex items-center space-x-2 pb-3 px-1 border-b-2 font-medium transition-colors ${
                activeTab === 'password'
                  ? 'border-[#5B8A72] text-[#5B8A72]'
                  : 'border-transparent text-[#7A8580] hover:text-[#3D4A44]'
              }`}
            >
              <LockClosedIcon className="w-5 h-5" />
              <span>Password</span>
            </button>
            {isOrgAdmin && (
              <button
                onClick={() => setActiveTab('org-settings')}
                className={`flex items-center space-x-2 pb-3 px-1 border-b-2 font-medium transition-colors ${
                  activeTab === 'org-settings'
                    ? 'border-[#5B8A72] text-[#5B8A72]'
                    : 'border-transparent text-[#7A8580] hover:text-[#3D4A44]'
                }`}
              >
                <BuildingOfficeIcon className="w-5 h-5" />
                <span>Organization</span>
              </button>
            )}
            {isOrgAdmin && (
              <button
                onClick={() => setActiveTab('integrations')}
                className={`flex items-center space-x-2 pb-3 px-1 border-b-2 font-medium transition-colors ${
                  activeTab === 'integrations'
                    ? 'border-[#5B8A72] text-[#5B8A72]'
                    : 'border-transparent text-[#7A8580] hover:text-[#3D4A44]'
                }`}
              >
                <CloudArrowUpIcon className="w-5 h-5" />
                <span>Integrations</span>
              </button>
            )}
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

        {activeTab === 'api' && isSuperAdmin && (
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
          <div className="space-y-6">
            <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h2 className="text-[22px] font-medium text-[#3D4A44]">Notification Preferences</h2>
                  <p className="text-[15px] text-[#7A8580] mt-1">Choose how you want to be notified</p>
                </div>
              </div>

              <div className="space-y-1">
                <div className="hidden md:grid grid-cols-[1fr,80px,80px,110px] gap-3 px-4 py-2 text-[13px] font-medium text-[#7A8580] uppercase">
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
                      className="px-4 py-4 bg-[#FAFBF9] rounded-xl hover:bg-[#EEF1EC] transition-colors"
                    >
                      <div className="hidden md:grid grid-cols-[1fr,80px,80px,110px] gap-3 items-center">
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

                      <div className="md:hidden">
                        <div className="mb-3">
                          <div className="text-[15px] font-medium text-[#3D4A44]">{info.label}</div>
                          <div className="text-[13px] text-[#7A8580]">{info.description}</div>
                        </div>
                        <div className="flex items-center justify-between gap-3">
                          <div className="flex items-center gap-3">
                            <div className="flex items-center gap-1.5">
                              <span className="text-[12px] text-[#7A8580]">In-App</span>
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
                            <div className="flex items-center gap-1.5">
                              <span className="text-[12px] text-[#7A8580]">Email</span>
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
                          </div>
                          <select
                            value={pref.frequency}
                            onChange={(e) => updatePreference(type, 'frequency', e.target.value)}
                            className="text-[13px] px-2 py-1.5 border border-[rgba(59,77,67,0.12)] rounded-lg bg-white text-[#3D4A44] focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                          >
                            <option value="immediate">Immediate</option>
                            <option value="daily">Daily</option>
                            <option value="weekly">Weekly</option>
                          </select>
                        </div>
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

            <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-[18px] font-medium text-[#3D4A44]">Scheduled Email Digest</h3>
                  <p className="text-[14px] text-[#7A8580] mt-0.5">Receive periodic email summaries of your action items</p>
                </div>
                <button
                  onClick={() => updateEmailDigest({ email_digest_enabled: !emailDigest.email_digest_enabled })}
                  className={`w-14 h-8 rounded-full transition-colors relative flex-shrink-0 ${
                    emailDigest.email_digest_enabled ? 'bg-[#5B8A72]' : 'bg-[#D1D5DB]'
                  }`}
                >
                  <span className={`absolute top-1.5 w-5 h-5 bg-white rounded-full transition-transform ${
                    emailDigest.email_digest_enabled ? 'left-8' : 'left-1.5'
                  }`} />
                </button>
              </div>

              {emailDigest.email_digest_enabled && (
                <div className="mt-5 pt-5 border-t border-[rgba(59,77,67,0.08)] space-y-5">
                  <div>
                    <label className="block text-[14px] font-medium text-[#3D4A44] mb-3">Frequency</label>
                    <div className="flex flex-wrap gap-2">
                      {[
                        { value: 'daily', label: 'Daily' },
                        { value: 'every_3_days', label: 'Every 3 Days' },
                        { value: 'weekly', label: 'Weekly' },
                        { value: 'biweekly', label: 'Biweekly' },
                        { value: 'monthly', label: 'Monthly' }
                      ].map(({ value, label }) => (
                        <button
                          key={value}
                          onClick={() => updateEmailDigest({ schedule_interval: value })}
                          className={`px-3 py-2 rounded-lg text-[13px] font-medium transition-all ${
                            emailDigest.schedule_interval === value
                              ? 'bg-[#5B8A72] text-white'
                              : 'bg-[#FAFBF9] text-[#3D4A44] border border-[rgba(59,77,67,0.12)] hover:bg-[#EEF1EC]'
                          }`}
                        >
                          {label}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div>
                    <label className="block text-[14px] font-medium text-[#3D4A44] mb-2">Delivery Time (UTC)</label>
                    <select
                      value={emailDigest.preferred_hour}
                      onChange={(e) => updateEmailDigest({ preferred_hour: parseInt(e.target.value) })}
                      className="w-full sm:w-48 px-4 py-2 border border-[rgba(59,77,67,0.2)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent text-[14px] bg-white text-[#3D4A44]"
                    >
                      {[...Array(24)].map((_, i) => (
                        <option key={i} value={i}>
                          {i === 0 ? '12:00 AM' : i < 12 ? `${i}:00 AM` : i === 12 ? '12:00 PM' : `${i - 12}:00 PM`}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-[14px] font-medium text-[#3D4A44] mb-3">Priority Filter</label>
                    <div className="grid grid-cols-4 gap-2">
                      {[
                        { value: 1, label: 'Critical', color: 'bg-[rgba(196,112,104,0.15)] text-[#C47068] border-[#C47068]' },
                        { value: 2, label: 'High', color: 'bg-[rgba(196,149,107,0.15)] text-[#C4956B] border-[#C4956B]' },
                        { value: 3, label: 'Medium', color: 'bg-[rgba(91,138,114,0.15)] text-[#5B8A72] border-[#5B8A72]' },
                        { value: 4, label: 'All', color: 'bg-[rgba(122,133,128,0.15)] text-[#7A8580] border-[#7A8580]' },
                      ].map(({ value, label, color }) => (
                        <button
                          key={value}
                          onClick={() => updateEmailDigest({ min_priority_threshold: value })}
                          className={`py-2 px-3 rounded-lg text-[13px] font-medium border-2 transition-all ${
                            emailDigest.min_priority_threshold === value
                              ? `${color} border-opacity-100`
                              : 'bg-[#FAFBF9] text-[#7A8580] border-transparent hover:bg-[#EEF1EC]'
                          }`}
                        >
                          {label}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-3">
                    <div className="flex items-center space-x-2">
                      {emailDigest.last_email_sent_at && (
                        <span className="text-[12px] text-[#7A8580]">
                          Last sent: {new Date(emailDigest.last_email_sent_at).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                    <button
                      onClick={sendTestEmail}
                      disabled={sendingTest}
                      className="px-4 py-2 bg-[#5B8A72] text-white text-[13px] font-medium rounded-lg hover:bg-[#4A7862] transition-colors disabled:opacity-50"
                    >
                      {sendingTest ? 'Sending...' : 'Send Test'}
                    </button>
                  </div>
                </div>
              )}
            </div>

            {pushSupported && (
              <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 bg-[rgba(91,138,114,0.1)] rounded-xl flex items-center justify-center">
                      <DevicePhoneMobileIcon className="w-5 h-5 text-[#5B8A72]" />
                    </div>
                    <div>
                      <h3 className="text-[18px] font-medium text-[#3D4A44]">Push Notifications</h3>
                      <p className="text-[14px] text-[#7A8580] mt-0.5">Receive instant alerts on this device</p>
                    </div>
                  </div>
                  <button
                    onClick={togglePush}
                    disabled={pushLoading}
                    className={`w-14 h-8 rounded-full transition-colors relative flex-shrink-0 ${
                      pushEnabled ? 'bg-[#5B8A72]' : 'bg-[#D1D5DB]'
                    } ${pushLoading ? 'opacity-50' : ''}`}
                  >
                    <span className={`absolute top-1.5 w-5 h-5 bg-white rounded-full transition-transform ${
                      pushEnabled ? 'left-8' : 'left-1.5'
                    }`} />
                  </button>
                </div>

                {pushEnabled && (
                  <div className="mt-4 pt-4 border-t border-[rgba(59,77,67,0.08)]">
                    <div className="flex items-center justify-between">
                      <p className="text-[13px] text-[#7A8580]">
                        Push notifications are active on this device. You'll receive alerts even when the app isn't open.
                      </p>
                      <button
                        onClick={sendTestPush}
                        disabled={sendingTestPush}
                        className="px-4 py-2 bg-[#5B8A72] text-white text-[13px] font-medium rounded-lg hover:bg-[#4A7862] transition-colors disabled:opacity-50 flex-shrink-0 ml-4"
                      >
                        {sendingTestPush ? 'Sending...' : 'Send Test'}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {(installPrompt || isInstalled) && (
              <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 bg-[rgba(91,138,114,0.1)] rounded-xl flex items-center justify-center">
                      <ArrowDownTrayIcon className="w-5 h-5 text-[#5B8A72]" />
                    </div>
                    <div>
                      <h3 className="text-[18px] font-medium text-[#3D4A44]">Install App</h3>
                      <p className="text-[14px] text-[#7A8580] mt-0.5">
                        {isInstalled
                          ? 'Cadence is installed on this device'
                          : 'Add Cadence to your home screen for quick access'
                        }
                      </p>
                    </div>
                  </div>
                  {isInstalled ? (
                    <span className="inline-flex items-center space-x-1 px-3 py-1.5 rounded-full text-[13px] font-medium bg-[rgba(91,154,110,0.15)] text-[#5B9A6E]">
                      <CheckCircleIcon className="w-4 h-4" />
                      <span>Installed</span>
                    </span>
                  ) : installPrompt ? (
                    <button
                      onClick={handleInstall}
                      className="px-5 py-2.5 bg-[#5B8A72] text-white text-[14px] font-medium rounded-xl hover:bg-[#4A7862] transition-colors flex items-center space-x-2"
                    >
                      <ArrowDownTrayIcon className="w-4 h-4" />
                      <span>Install</span>
                    </button>
                  ) : null}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'password' && (
          <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6">
            <h2 className="text-[22px] font-medium text-[#3D4A44] mb-2">Change Password</h2>
            <p className="text-[15px] text-[#7A8580] mb-6">
              Update your password to keep your account secure
            </p>

            {passwordError && (
              <div className="mb-4 p-4 rounded-xl bg-[rgba(196,112,104,0.1)] text-[#C47068] text-[15px]">
                {passwordError}
              </div>
            )}

            {passwordSuccess && (
              <div className="mb-4 p-4 rounded-xl bg-[rgba(91,154,110,0.1)] text-[#5B9A6E] text-[15px]">
                {passwordSuccess}
              </div>
            )}

            <form onSubmit={handleChangePassword} className="max-w-md space-y-4">
              <div>
                <label className="block text-[15px] font-medium text-[#3D4A44] mb-2">
                  Current Password
                </label>
                <div className="relative">
                  <input
                    type={showCurrentPassword ? "text" : "password"}
                    value={passwordForm.currentPassword}
                    onChange={(e) => setPasswordForm({...passwordForm, currentPassword: e.target.value})}
                    required
                    className="w-full px-4 py-3 pr-12 border border-[rgba(59,77,67,0.2)] rounded-xl focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent text-[15px]"
                    placeholder="Enter current password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-[#7A8580] hover:text-[#5B8A72] transition-colors"
                  >
                    {showCurrentPassword ? <EyeSlashIcon className="w-5 h-5" /> : <EyeIcon className="w-5 h-5" />}
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-[15px] font-medium text-[#3D4A44] mb-2">
                  New Password
                </label>
                <div className="relative">
                  <input
                    type={showNewPassword ? "text" : "password"}
                    value={passwordForm.newPassword}
                    onChange={(e) => setPasswordForm({...passwordForm, newPassword: e.target.value})}
                    required
                    minLength={6}
                    className="w-full px-4 py-3 pr-12 border border-[rgba(59,77,67,0.2)] rounded-xl focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent text-[15px]"
                    placeholder="Enter new password (min 6 characters)"
                  />
                  <button
                    type="button"
                    onClick={() => setShowNewPassword(!showNewPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-[#7A8580] hover:text-[#5B8A72] transition-colors"
                  >
                    {showNewPassword ? <EyeSlashIcon className="w-5 h-5" /> : <EyeIcon className="w-5 h-5" />}
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-[15px] font-medium text-[#3D4A44] mb-2">
                  Confirm New Password
                </label>
                <div className="relative">
                  <input
                    type={showConfirmPassword ? "text" : "password"}
                    value={passwordForm.confirmPassword}
                    onChange={(e) => setPasswordForm({...passwordForm, confirmPassword: e.target.value})}
                    required
                    className="w-full px-4 py-3 pr-12 border border-[rgba(59,77,67,0.2)] rounded-xl focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent text-[15px]"
                    placeholder="Confirm new password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-[#7A8580] hover:text-[#5B8A72] transition-colors"
                  >
                    {showConfirmPassword ? <EyeSlashIcon className="w-5 h-5" /> : <EyeIcon className="w-5 h-5" />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={changingPassword}
                className="w-full px-6 py-3 bg-[#5B8A72] text-white rounded-xl font-medium hover:bg-[#4A7862] transition-colors disabled:opacity-50"
              >
                {changingPassword ? 'Changing Password...' : 'Change Password'}
              </button>
            </form>

            <div className="mt-6 p-4 bg-gradient-to-br from-[rgba(91,138,114,0.08)] to-[rgba(123,165,148,0.08)] rounded-xl border-l-4 border-[#5B8A72]">
              <div className="flex items-start space-x-3">
                <LockClosedIcon className="w-5 h-5 text-[#5B8A72] mt-0.5" />
                <div>
                  <h4 className="text-[15px] font-medium text-[#3D4A44]">Password Security Tips</h4>
                  <ul className="text-[13px] text-[#7A8580] mt-1 list-disc list-inside space-y-1">
                    <li>Use at least 6 characters</li>
                    <li>Include a mix of letters, numbers, and symbols</li>
                    <li>Avoid using easily guessable information</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        )}


        {activeTab === 'org-settings' && isOrgAdmin && (
          <div className="space-y-6">
            <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6">
              <h2 className="text-[22px] font-medium text-[#3D4A44] mb-2">Organization Notification Defaults</h2>
              <p className="text-[15px] text-[#7A8580] mb-6">
                Configure default notification settings for all team members. These can be overridden by individual users if allowed.
              </p>

              <div className="space-y-4">
                {Object.entries(NOTIFICATION_TYPES).map(([type, info]) => {
                  const setting = getOrgSetting(type)
                  return (
                    <div key={type} className="p-4 bg-[#FAFBF9] rounded-xl">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="text-[15px] font-medium text-[#3D4A44]">{info.label}</div>
                          <div className="text-[13px] text-[#7A8580]">{info.description}</div>
                        </div>
                        <div className="flex items-center space-x-4 ml-4">
                          <div className="flex flex-col items-center">
                            <span className="text-[11px] text-[#7A8580] mb-1">Allow Override</span>
                            <button
                              onClick={() => updateOrgSetting(type, { allow_user_override: !setting.allow_user_override })}
                              className={`w-10 h-6 rounded-full transition-colors relative ${
                                setting.allow_user_override ? 'bg-[#5B8A72]' : 'bg-[#D1D5DB]'
                              }`}
                            >
                              <span className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${
                                setting.allow_user_override ? 'left-5' : 'left-1'
                              }`} />
                            </button>
                          </div>
                          <div className="flex flex-col items-center">
                            <span className="text-[11px] text-[#7A8580] mb-1">Default</span>
                            <select
                              value={setting.default_frequency}
                              onChange={(e) => updateOrgSetting(type, { default_frequency: e.target.value })}
                              className="text-[13px] px-2 py-1 border border-[rgba(59,77,67,0.12)] rounded-lg bg-white text-[#3D4A44] focus:ring-2 focus:ring-[#5B8A72]"
                            >
                              <option value="immediate">Immediate</option>
                              <option value="daily">Daily</option>
                              <option value="weekly">Weekly</option>
                            </select>
                          </div>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6">
              <h2 className="text-[22px] font-medium text-[#3D4A44] mb-2">Organization Digest</h2>
              <p className="text-[15px] text-[#7A8580] mb-6">
                Enable a consolidated digest that summarizes all action items across the organization.
              </p>

              <div className="p-4 bg-[#FAFBF9] rounded-xl">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <div className="text-[15px] font-medium text-[#3D4A44]">Weekly Rollup Digest</div>
                    <div className="text-[13px] text-[#7A8580]">Receive a summary of all pending, overdue, and high-priority action items</div>
                  </div>
                  <button
                    onClick={() => {
                      const setting = getOrgSetting('WEEKLY_HEALTH_SUMMARY')
                      updateOrgSetting('WEEKLY_HEALTH_SUMMARY', { rollup_digest_enabled: !setting.rollup_digest_enabled })
                    }}
                    className={`w-12 h-7 rounded-full transition-colors relative ${
                      getOrgSetting('WEEKLY_HEALTH_SUMMARY').rollup_digest_enabled ? 'bg-[#5B8A72]' : 'bg-[#D1D5DB]'
                    }`}
                  >
                    <span className={`absolute top-1 w-5 h-5 bg-white rounded-full transition-transform ${
                      getOrgSetting('WEEKLY_HEALTH_SUMMARY').rollup_digest_enabled ? 'left-6' : 'left-1'
                    }`} />
                  </button>
                </div>

                {getOrgSetting('WEEKLY_HEALTH_SUMMARY').rollup_digest_enabled && (
                  <div className="grid grid-cols-3 gap-4 pt-4 border-t border-[rgba(59,77,67,0.08)]">
                    <div>
                      <label className="block text-[13px] font-medium text-[#3D4A44] mb-1">Frequency</label>
                      <select
                        value={getOrgSetting('WEEKLY_HEALTH_SUMMARY').digest_frequency}
                        onChange={(e) => updateOrgSetting('WEEKLY_HEALTH_SUMMARY', { digest_frequency: e.target.value })}
                        className="w-full text-[13px] px-3 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg bg-white"
                      >
                        <option value="daily">Daily</option>
                        <option value="weekly">Weekly</option>
                        <option value="monthly">Monthly</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-[13px] font-medium text-[#3D4A44] mb-1">Day</label>
                      <select
                        value={getOrgSetting('WEEKLY_HEALTH_SUMMARY').digest_day}
                        onChange={(e) => updateOrgSetting('WEEKLY_HEALTH_SUMMARY', { digest_day: parseInt(e.target.value) })}
                        className="w-full text-[13px] px-3 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg bg-white"
                      >
                        <option value={0}>Sunday</option>
                        <option value={1}>Monday</option>
                        <option value={2}>Tuesday</option>
                        <option value={3}>Wednesday</option>
                        <option value={4}>Thursday</option>
                        <option value={5}>Friday</option>
                        <option value={6}>Saturday</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-[13px] font-medium text-[#3D4A44] mb-1">Time</label>
                      <select
                        value={getOrgSetting('WEEKLY_HEALTH_SUMMARY').digest_hour}
                        onChange={(e) => updateOrgSetting('WEEKLY_HEALTH_SUMMARY', { digest_hour: parseInt(e.target.value) })}
                        className="w-full text-[13px] px-3 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg bg-white"
                      >
                        {[...Array(24)].map((_, i) => (
                          <option key={i} value={i}>{i === 0 ? '12:00 AM' : i < 12 ? `${i}:00 AM` : i === 12 ? '12:00 PM' : `${i-12}:00 PM`}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                )}
              </div>
            </div>

            <div className="bg-gradient-to-br from-[rgba(91,138,114,0.08)] to-[rgba(123,165,148,0.08)] rounded-[18px] p-6 border-l-4 border-[#5B8A72]">
              <h3 className="text-[17px] font-semibold text-[#3D4A44] mb-3">About Organization Settings</h3>
              <ul className="space-y-2 text-[15px] text-[#7A8580]">
                <li>• Default settings apply to new team members and users who haven't customized their preferences</li>
                <li>• When "Allow Override" is disabled, team members cannot change that notification type's settings</li>
                <li>• The rollup digest provides a consolidated view of all action items across your organization</li>
              </ul>
            </div>
          </div>
        )}

        {activeTab === 'integrations' && isOrgAdmin && (
          <div className="space-y-6">
            <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6">
              <div className="flex items-center justify-between mb-5">
                <div className="flex items-center space-x-3">
                  <div className="w-12 h-12 bg-[rgba(91,138,114,0.1)] rounded-xl flex items-center justify-center">
                    <CloudIcon className="w-7 h-7 text-[#5B8A72]" />
                  </div>
                  <div>
                    <h2 className="text-[22px] font-medium text-[#3D4A44]">Dropbox</h2>
                    {integrations.dropbox?.connected && (
                      <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[12px] font-medium bg-[rgba(91,154,110,0.15)] text-[#5B9A6E]">
                        <CheckCircleIcon className="w-3.5 h-3.5" />
                        <span>Connected</span>
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {!integrations.dropbox?.connected ? (
                <div>
                  <p className="text-[15px] text-[#7A8580] mb-6">
                    Connect your Dropbox account to link audio files to songs and releases for AI analysis.
                  </p>
                  {!showCodeInput ? (
                    <button
                      onClick={connectDropbox}
                      disabled={connectingDropbox}
                      className="px-6 py-3 bg-[#5B8A72] text-white rounded-xl font-medium hover:bg-[#4A7862] transition-colors disabled:opacity-50 flex items-center space-x-2"
                    >
                      <CloudArrowUpIcon className="w-5 h-5" />
                      <span>{connectingDropbox ? 'Connecting...' : 'Connect Dropbox'}</span>
                    </button>
                  ) : (
                    <div className="space-y-4">
                      <div className="p-4 bg-[#F0F4F1] rounded-xl border border-[#D1DDD5]">
                        <p className="text-[14px] text-[#3D4A44] mb-3">
                          A Dropbox authorization page has opened. After you approve access, Dropbox will show you an authorization code. Copy and paste that code below:
                        </p>
                        <div className="flex items-center space-x-3">
                          <input
                            type="text"
                            value={dropboxCodeInput}
                            onChange={(e) => setDropboxCodeInput(e.target.value)}
                            placeholder="Paste your authorization code here"
                            className="flex-1 px-4 py-2.5 border border-[#D1DDD5] rounded-lg text-[14px] text-[#3D4A44] focus:outline-none focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                            onKeyDown={(e) => e.key === 'Enter' && submitDropboxCode()}
                          />
                          <button
                            onClick={submitDropboxCode}
                            disabled={connectingDropbox || !dropboxCodeInput.trim()}
                            className="px-5 py-2.5 bg-[#5B8A72] text-white rounded-lg font-medium hover:bg-[#4A7862] transition-colors disabled:opacity-50 text-[14px]"
                          >
                            {connectingDropbox ? 'Connecting...' : 'Submit'}
                          </button>
                        </div>
                      </div>
                      <button
                        onClick={() => { setShowCodeInput(false); setDropboxCodeInput(''); sessionStorage.removeItem('dropbox_code_pending'); }}
                        className="text-[13px] text-[#7A8580] hover:text-[#3D4A44] transition-colors"
                      >
                        Cancel
                      </button>
                    </div>
                  )}
                </div>
              ) : (
                <div className="space-y-5">
                  <div className="p-4 bg-[#FAFBF9] rounded-xl">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      {integrations.dropbox?.account_email && (
                        <div className="min-w-0">
                          <div className="text-[13px] text-[#7A8580] mb-1">Email</div>
                          <div className="text-[15px] font-medium text-[#3D4A44] truncate">{integrations.dropbox.account_email}</div>
                        </div>
                      )}
                      {integrations.dropbox?.display_name && (
                        <div className="min-w-0">
                          <div className="text-[13px] text-[#7A8580] mb-1">Account</div>
                          <div className="text-[15px] font-medium text-[#3D4A44] truncate">{integrations.dropbox.display_name}</div>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="p-4 bg-[#FAFBF9] rounded-xl">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-[13px] text-[#7A8580] mb-1">Default Folder</div>
                        <div className="text-[15px] font-medium text-[#3D4A44] flex items-center space-x-2">
                          <FolderIcon className="w-4 h-4 text-[#5B8A72]" />
                          <span>{integrations.dropbox?.default_folder || '/ (root)'}</span>
                        </div>
                      </div>
                      <button
                        onClick={() => setFolderPickerOpen(true)}
                        className="px-3 py-1.5 text-[13px] font-medium text-[#5B8A72] border border-[#5B8A72] rounded-lg hover:bg-[rgba(91,138,114,0.08)] transition-colors"
                      >
                        Change
                      </button>
                    </div>
                  </div>

                  <div className="flex items-center space-x-3">
                    <button
                      onClick={testDropboxConnection}
                      disabled={testingConnection}
                      className="px-4 py-2 bg-[#5B8A72] text-white text-[13px] font-medium rounded-lg hover:bg-[#4A7862] transition-colors disabled:opacity-50"
                    >
                      {testingConnection ? 'Testing...' : 'Test Connection'}
                    </button>
                    <button
                      onClick={disconnectDropbox}
                      className="px-4 py-2 bg-white text-[#C47068] text-[13px] font-medium rounded-lg border border-[#C47068] hover:bg-[rgba(196,112,104,0.08)] transition-colors"
                    >
                      Disconnect
                    </button>
                  </div>
                </div>
              )}
            </div>

            <div>
              <h3 className="text-[17px] font-semibold text-[#3D4A44] mb-4">Coming Soon</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6 opacity-50 cursor-not-allowed">
                  <div className="flex items-center space-x-3 mb-3">
                    <div className="w-10 h-10 bg-[rgba(122,133,128,0.1)] rounded-xl flex items-center justify-center">
                      <CloudIcon className="w-6 h-6 text-[#7A8580]" />
                    </div>
                    <div>
                      <h4 className="text-[17px] font-medium text-[#3D4A44]">Box</h4>
                      <span className="text-[12px] text-[#7A8580]">Coming Soon</span>
                    </div>
                  </div>
                  <p className="text-[13px] text-[#7A8580]">
                    Connect your Box account for cloud file storage integration.
                  </p>
                </div>
                <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6 opacity-50 cursor-not-allowed">
                  <div className="flex items-center space-x-3 mb-3">
                    <div className="w-10 h-10 bg-[rgba(122,133,128,0.1)] rounded-xl flex items-center justify-center">
                      <CloudIcon className="w-6 h-6 text-[#7A8580]" />
                    </div>
                    <div>
                      <h4 className="text-[17px] font-medium text-[#3D4A44]">Google Drive</h4>
                      <span className="text-[12px] text-[#7A8580]">Coming Soon</span>
                    </div>
                  </div>
                  <p className="text-[13px] text-[#7A8580]">
                    Connect your Google Drive for seamless file access and sharing.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        <FolderPicker
          isOpen={folderPickerOpen}
          onClose={() => setFolderPickerOpen(false)}
          onSelect={handleFolderSelected}
          provider="DROPBOX"
          orgId={organizationId}
          initialPath={integrations.dropbox?.default_folder || ''}
        />
      </div>
    </div>
  )
}
