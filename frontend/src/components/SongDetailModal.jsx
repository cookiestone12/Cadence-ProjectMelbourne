import React, { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import axios from 'axios'
import {
  XMarkIcon, CheckCircleIcon, XCircleIcon, MinusCircleIcon,
  MusicalNoteIcon, ChartBarIcon, DocumentTextIcon, LinkIcon,
  DocumentArrowUpIcon, ArrowDownTrayIcon, TrashIcon, PlayIcon, UserIcon
} from '@heroicons/react/24/outline'

export default function SongDetailModal({ song, onClose }) {
  const [activeTab, setActiveTab] = useState('overview')
  const [songDetails, setSongDetails] = useState(null)
  const [loading, setLoading] = useState(true)
  const [contracts, setContracts] = useState([])
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef(null)
  
  useEffect(() => {
    loadSongDetails()
    loadContracts()
  }, [song.id])
  
  async function loadSongDetails() {
    try {
      const token = localStorage.getItem('token')
      const response = await axios.get(`/api/songs/${song.id}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      setSongDetails(response.data)
    } catch (error) {
      console.error('Failed to load song details:', error)
    } finally {
      setLoading(false)
    }
  }
  
  async function loadContracts() {
    try {
      const token = localStorage.getItem('token')
      const response = await axios.get(`/api/contracts/song/${song.id}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      setContracts(response.data)
    } catch (error) {
      console.error('Failed to load contracts:', error)
    }
  }
  
  async function handleContractUpload(event) {
    const file = event.target.files[0]
    if (!file) return
    
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      alert('Only PDF files are allowed')
      return
    }
    
    setUploading(true)
    try {
      const token = localStorage.getItem('token')
      const formData = new FormData()
      formData.append('file', file)
      formData.append('contract_type', 'Agreement')
      
      await axios.post(`/api/contracts/upload/${song.id}`, formData, {
        headers: { 
          'Content-Type': 'multipart/form-data',
          'Authorization': `Bearer ${token}`
        }
      })
      
      await loadContracts()
      await loadSongDetails()
    } catch (error) {
      console.error('Failed to upload contract:', error)
      alert('Failed to upload contract')
    } finally {
      setUploading(false)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }
  
  async function handleDeleteContract(contractId) {
    if (!confirm('Are you sure you want to delete this contract?')) return
    
    try {
      const token = localStorage.getItem('token')
      await axios.delete(`/api/contracts/${contractId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      await loadContracts()
      await loadSongDetails()
    } catch (error) {
      console.error('Failed to delete contract:', error)
    }
  }
  
  function downloadContract(contractId) {
    const token = localStorage.getItem('token')
    window.open(`/api/contracts/download/${contractId}?token=${token}`, '_blank')
  }
  
  const getStatusIcon = (value) => {
    if (value === 'Yes' || value === true) return <CheckCircleIcon className="w-5 h-5 text-green-500" />
    if (value === 'No' || value === false) return <XCircleIcon className="w-5 h-5 text-red-500" />
    return <MinusCircleIcon className="w-5 h-5 text-gray-400" />
  }
  
  const formatCurrency = (cents) => {
    if (!cents) return '$0.00'
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(cents / 100)
  }
  
  const formatNumber = (num) => {
    if (!num) return '0'
    return new Intl.NumberFormat('en-US').format(num)
  }
  
  if (loading || !songDetails) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-xl p-8">
          <div className="text-gray-500">Loading song details...</div>
        </div>
      </div>
    )
  }
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div 
        className="bg-white rounded-xl shadow-2xl max-w-6xl w-full max-h-[90vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-6 border-b border-gray-200 bg-gradient-to-r from-purple-50 to-pink-50">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <h2 className="text-3xl font-bold text-gray-900 mb-2">{songDetails.title}</h2>
              <p className="text-lg text-gray-600 mb-3">{songDetails.primary_artist}</p>
              <div className="flex flex-wrap gap-2">
                {songDetails.is_released && (
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    Released
                  </span>
                )}
                {!songDetails.is_released && (
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
                    Unreleased
                  </span>
                )}
                {songDetails.payment_status === 'PAID' && (
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                    Paid
                  </span>
                )}
                {songDetails.label && (
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                    {songDetails.label}
                  </span>
                )}
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <XMarkIcon className="w-8 h-8" />
            </button>
          </div>
        </div>
        
        {/* Tabs */}
        <div className="border-b border-gray-200 px-6">
          <div className="flex space-x-8">
            {[
              { id: 'overview', label: 'Overview', icon: MusicalNoteIcon },
              { id: 'placement', label: 'Placement Status', icon: DocumentTextIcon },
              { id: 'streaming', label: 'Streaming & Valuation', icon: ChartBarIcon },
              { id: 'links', label: 'Credits & Links', icon: LinkIcon }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center space-x-2 py-4 px-1 border-b-2 font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'border-purple-600 text-purple-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                <tab.icon className="w-5 h-5" />
                <span>{tab.label}</span>
              </button>
            ))}
          </div>
        </div>
        
        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {activeTab === 'overview' && (
            <div className="grid grid-cols-2 gap-6">
              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Basic Information</h3>
                <div>
                  <label className="text-sm font-medium text-gray-500">Title</label>
                  <p className="text-gray-900">{songDetails.title}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">Primary Artist</label>
                  <p className="text-gray-900">{songDetails.primary_artist}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">Client</label>
                  {songDetails.client_name ? (
                    <Link 
                      to={`/creators/${songDetails.client_id}`}
                      onClick={onClose}
                      className="flex items-center space-x-2 text-purple-600 hover:text-purple-800"
                    >
                      <UserIcon className="w-4 h-4" />
                      <span className="font-medium">{songDetails.client_name}</span>
                    </Link>
                  ) : (
                    <p className="text-gray-400">Not assigned</p>
                  )}
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">Project/Album</label>
                  <p className="text-gray-900">{songDetails.project_title || 'N/A'}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">Label</label>
                  <p className="text-gray-900">{songDetails.label || 'N/A'}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">Release Date</label>
                  <p className="text-gray-900">{songDetails.release_date || 'N/A'}</p>
                </div>
                {songDetails.media_url && (
                  <div>
                    <label className="text-sm font-medium text-gray-500">Audio File</label>
                    <a 
                      href={songDetails.media_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center space-x-2 text-purple-600 hover:text-purple-800 mt-1"
                    >
                      <PlayIcon className="w-5 h-5" />
                      <span className="underline">Listen / Download</span>
                    </a>
                  </div>
                )}
              </div>
              
              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Metadata</h3>
                <div>
                  <label className="text-sm font-medium text-gray-500">ISRC</label>
                  <p className="text-gray-900 font-mono">{songDetails.isrc || 'N/A'}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">ISWC</label>
                  <p className="text-gray-900 font-mono">{songDetails.iswc || 'N/A'}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">Recording Code</label>
                  <p className="text-gray-900 font-mono">{songDetails.recording_code || 'N/A'}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">Health Score</label>
                  <div className="flex items-center space-x-3">
                    <div className="flex-1 h-3 bg-gray-200 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-purple-500 to-pink-500"
                        style={{ width: `${songDetails.status_health_score || 0}%` }}
                      ></div>
                    </div>
                    <span className="text-sm font-bold text-gray-700">
                      {Math.round(songDetails.status_health_score || 0)}%
                    </span>
                  </div>
                </div>
              </div>
              
              {songDetails.notes && (
                <div className="col-span-2">
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">Notes</h3>
                  <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                    <p className="text-sm text-gray-700 whitespace-pre-wrap">{songDetails.notes}</p>
                  </div>
                </div>
              )}
            </div>
          )}
          
          {activeTab === 'placement' && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Ownership</h3>
                  <div className="space-y-3">
                    <div>
                      <label className="text-sm font-medium text-gray-500">Publishing %</label>
                      <p className="text-2xl font-bold text-gray-900">
                        {songDetails.publishing_percentage 
                          ? `${Math.min(songDetails.publishing_percentage, 100).toFixed(2)}%`
                          : 'N/A'
                        }
                      </p>
                    </div>
                    <div>
                      <label className="text-sm font-medium text-gray-500">Master %</label>
                      <p className="text-2xl font-bold text-gray-900">
                        {songDetails.master_percentage 
                          ? `${Math.min(songDetails.master_percentage, 100).toFixed(2)}%`
                          : 'N/A'
                        }
                      </p>
                    </div>
                    <div>
                      <label className="text-sm font-medium text-gray-500">Advance</label>
                      <p className="text-2xl font-bold text-gray-900">
                        {songDetails.advance_amount 
                          ? `$${songDetails.advance_amount.toLocaleString()}`
                          : 'N/A'
                        }
                      </p>
                    </div>
                  </div>
                </div>
                
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Status Checklist</h3>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-700">Contract Executed</span>
                      {getStatusIcon(songDetails.has_contract_executed)}
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-700">Contract Location</span>
                      <span className="text-sm font-medium text-gray-900">{songDetails.contract_location || 'N/A'}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-700">PRO Registered</span>
                      {getStatusIcon(songDetails.is_registered_with_pro)}
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-700">DSP Registered</span>
                      {getStatusIcon(songDetails.is_registered_with_dsp)}
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-700">SoundExchange Registered</span>
                      {getStatusIcon(songDetails.soundexchange_registered)}
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-700">Master Paid</span>
                      {getStatusIcon(songDetails.master_paid)}
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-700">Payment Status</span>
                      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                        songDetails.payment_status === 'PAID' 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-gray-100 text-gray-600'
                      }`}>
                        {songDetails.payment_status || 'N/A'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Contracts Section */}
              <div className="mt-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-gray-900">Contracts & Agreements</h3>
                  <div>
                    <input
                      type="file"
                      ref={fileInputRef}
                      onChange={handleContractUpload}
                      accept=".pdf"
                      className="hidden"
                    />
                    <button
                      onClick={() => fileInputRef.current?.click()}
                      disabled={uploading}
                      className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-lg hover:from-purple-700 hover:to-pink-700 transition-all disabled:opacity-50"
                    >
                      <DocumentArrowUpIcon className="w-5 h-5" />
                      <span>{uploading ? 'Uploading...' : 'Upload Contract'}</span>
                    </button>
                  </div>
                </div>
                
                {contracts.length > 0 ? (
                  <div className="space-y-2">
                    {contracts.map((contract) => (
                      <div key={contract.id} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg border border-gray-200">
                        <div className="flex items-center space-x-3">
                          <DocumentTextIcon className="w-8 h-8 text-purple-500" />
                          <div>
                            <p className="font-medium text-gray-900">{contract.file_name}</p>
                            <p className="text-sm text-gray-500">
                              {contract.contract_type || 'Contract'} • {new Date(contract.created_at).toLocaleDateString()}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center space-x-2">
                          <button
                            onClick={() => downloadContract(contract.id)}
                            className="p-2 text-gray-600 hover:text-purple-600 hover:bg-purple-50 rounded-lg transition-colors"
                            title="Download"
                          >
                            <ArrowDownTrayIcon className="w-5 h-5" />
                          </button>
                          <button
                            onClick={() => handleDeleteContract(contract.id)}
                            className="p-2 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                            title="Delete"
                          >
                            <TrashIcon className="w-5 h-5" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 bg-gray-50 rounded-lg border-2 border-dashed border-gray-200">
                    <DocumentTextIcon className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                    <p className="text-gray-500">No contracts uploaded yet</p>
                    <p className="text-sm text-gray-400">Upload a PDF to attach it to this song</p>
                  </div>
                )}
              </div>
            </div>
          )}
          
          {activeTab === 'streaming' && (
            <div className="text-center text-gray-500 py-12">
              Streaming metrics and valuation data will be displayed here
            </div>
          )}
          
          {activeTab === 'links' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Credits</h3>
                {songDetails.credits && songDetails.credits.length > 0 ? (
                  <div className="space-y-2">
                    {songDetails.credits.map((credit, idx) => (
                      <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                        <div>
                          <p className="font-medium text-gray-900">{credit.creator?.display_name || 'Unknown'}</p>
                          <p className="text-sm text-gray-500">{credit.role}</p>
                        </div>
                        <span className="text-sm font-medium text-gray-700">
                          {credit.share_percentage ? `${credit.share_percentage}%` : '-'}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-500">No credits added yet</p>
                )}
              </div>
              
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4">DSP Links</h3>
                {songDetails.dsp_links && songDetails.dsp_links.length > 0 ? (
                  <div className="space-y-2">
                    {songDetails.dsp_links.map((link, idx) => (
                      <a
                        key={idx}
                        href={link.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                      >
                        <span className="font-medium text-gray-900">{link.platform}</span>
                        <LinkIcon className="w-5 h-5 text-gray-400" />
                      </a>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-500">No DSP links added yet</p>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
