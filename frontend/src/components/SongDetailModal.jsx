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
    if (value === 'Yes' || value === true) return <CheckCircleIcon className="w-5 h-5 text-[#5B9A6E]" />
    if (value === 'No' || value === false) return <XCircleIcon className="w-5 h-5 text-[#C47068]" />
    return <MinusCircleIcon className="w-5 h-5 text-[#7A8580]" />
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
      <div className="fixed inset-0 bg-black/20 backdrop-blur-sm z-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-[18px] p-8 shadow-[0px_4px_12px_rgba(0,0,0,0.08)]">
          <div className="text-[#7A8580]">Loading song details...</div>
        </div>
      </div>
    )
  }
  
  return (
    <div className="fixed inset-0 bg-black/20 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div 
        className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] max-w-6xl w-full max-h-[90vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-6 border-b border-[rgba(59,77,67,0.08)] bg-white">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <h2 className="text-[28px] font-semibold text-[#3D4A44] mb-2 leading-tight">{songDetails.title}</h2>
              <p className="text-[17px] text-[#7A8580] mb-3">{songDetails.primary_artist}</p>
              <div className="flex flex-wrap gap-2">
                {songDetails.is_released && (
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-[13px] font-medium bg-[rgba(91,154,110,0.15)] text-[#5B9A6E]">
                    Released
                  </span>
                )}
                {!songDetails.is_released && (
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-[13px] font-medium bg-[rgba(196,149,107,0.15)] text-[#C4956B]">
                    Unreleased
                  </span>
                )}
                {songDetails.payment_status === 'PAID' && (
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-[13px] font-medium bg-[rgba(90,138,154,0.15)] text-[#5A8A9A]">
                    Paid
                  </span>
                )}
                {songDetails.label && (
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-[13px] font-medium bg-[rgba(91,138,114,0.15)] text-[#5B8A72]">
                    {songDetails.label}
                  </span>
                )}
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-[#7A8580] hover:text-[#3D4A44] transition-colors"
            >
              <XMarkIcon className="w-7 h-7" />
            </button>
          </div>
        </div>
        
        <div className="border-b border-[rgba(59,77,67,0.08)] px-6 bg-white">
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
                className={`flex items-center space-x-2 py-4 px-1 border-b-2 font-medium text-[15px] transition-colors ${
                  activeTab === tab.id
                    ? 'border-[#5B8A72] text-[#5B8A72]'
                    : 'border-transparent text-[#7A8580] hover:text-[#3D4A44]'
                }`}
              >
                <tab.icon className="w-5 h-5" />
                <span>{tab.label}</span>
              </button>
            ))}
          </div>
        </div>
        
        <div className="flex-1 overflow-y-auto p-6 bg-[#F5F7F4]">
          {activeTab === 'overview' && (
            <div className="grid grid-cols-2 gap-6">
              <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-5 space-y-4">
                <h3 className="text-[17px] font-semibold text-[#3D4A44] mb-4">Basic Information</h3>
                <div>
                  <label className="text-[13px] font-medium text-[#7A8580]">Title</label>
                  <p className="text-[#3D4A44]">{songDetails.title}</p>
                </div>
                <div>
                  <label className="text-[13px] font-medium text-[#7A8580]">Primary Artist</label>
                  <p className="text-[#3D4A44]">{songDetails.primary_artist}</p>
                </div>
                <div>
                  <label className="text-[13px] font-medium text-[#7A8580]">Client</label>
                  {songDetails.client_name ? (
                    <Link 
                      to={`/creators/${songDetails.client_id}`}
                      onClick={onClose}
                      className="flex items-center space-x-2 text-[#5B8A72] hover:text-[#7BA594]"
                    >
                      <UserIcon className="w-4 h-4" />
                      <span className="font-medium">{songDetails.client_name}</span>
                    </Link>
                  ) : (
                    <p className="text-[#7A8580]">Not assigned</p>
                  )}
                </div>
                <div>
                  <label className="text-[13px] font-medium text-[#7A8580]">Project/Album</label>
                  <p className="text-[#3D4A44]">{songDetails.project_title || 'N/A'}</p>
                </div>
                <div>
                  <label className="text-[13px] font-medium text-[#7A8580]">Label</label>
                  <p className="text-[#3D4A44]">{songDetails.label || 'N/A'}</p>
                </div>
                <div>
                  <label className="text-[13px] font-medium text-[#7A8580]">Release Date</label>
                  <p className="text-[#3D4A44]">{songDetails.release_date || 'N/A'}</p>
                </div>
                {songDetails.media_url && (
                  <div>
                    <label className="text-[13px] font-medium text-[#7A8580]">Audio File</label>
                    <a 
                      href={songDetails.media_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center space-x-2 text-[#5B8A72] hover:text-[#7BA594] mt-1"
                    >
                      <PlayIcon className="w-5 h-5" />
                      <span>Listen / Download</span>
                    </a>
                  </div>
                )}
              </div>
              
              <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-5 space-y-4">
                <h3 className="text-[17px] font-semibold text-[#3D4A44] mb-4">Metadata</h3>
                <div>
                  <label className="text-[13px] font-medium text-[#7A8580]">ISRC</label>
                  <p className="text-[#3D4A44] font-mono">{songDetails.isrc || 'N/A'}</p>
                </div>
                <div>
                  <label className="text-[13px] font-medium text-[#7A8580]">ISWC</label>
                  <p className="text-[#3D4A44] font-mono">{songDetails.iswc || 'N/A'}</p>
                </div>
                <div>
                  <label className="text-[13px] font-medium text-[#7A8580]">Recording Code</label>
                  <p className="text-[#3D4A44] font-mono">{songDetails.recording_code || 'N/A'}</p>
                </div>
                <div>
                  <label className="text-[13px] font-medium text-[#7A8580]">Health Score</label>
                  <div className="flex items-center space-x-3 mt-1">
                    <div className="flex-1 h-2 bg-[#EEF1EC] rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-[#5B8A72] to-[#7BA594]"
                        style={{ width: `${songDetails.status_health_score || 0}%` }}
                      ></div>
                    </div>
                    <span className="text-[13px] font-semibold text-[#3D4A44]">
                      {Math.round(songDetails.status_health_score || 0)}%
                    </span>
                  </div>
                </div>
              </div>
              
              {songDetails.notes && (
                <div className="col-span-2 bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-5">
                  <h3 className="text-[17px] font-semibold text-[#3D4A44] mb-2">Notes</h3>
                  <div className="bg-[rgba(196,149,107,0.08)] border border-[rgba(196,149,107,0.15)] rounded-[12px] p-4">
                    <p className="text-[15px] text-[#3D4A44] whitespace-pre-wrap">{songDetails.notes}</p>
                  </div>
                </div>
              )}
            </div>
          )}
          
          {activeTab === 'placement' && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-6">
                <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-5">
                  <h3 className="text-[17px] font-semibold text-[#3D4A44] mb-4">Ownership</h3>
                  <div className="space-y-4">
                    <div>
                      <label className="text-[13px] font-medium text-[#7A8580]">Publishing %</label>
                      <p className="text-[28px] font-semibold text-[#3D4A44]">
                        {songDetails.publishing_percentage 
                          ? `${Math.min(songDetails.publishing_percentage, 100).toFixed(2)}%`
                          : 'N/A'
                        }
                      </p>
                    </div>
                    <div>
                      <label className="text-[13px] font-medium text-[#7A8580]">Master %</label>
                      <p className="text-[28px] font-semibold text-[#3D4A44]">
                        {songDetails.master_percentage 
                          ? `${Math.min(songDetails.master_percentage, 100).toFixed(2)}%`
                          : 'N/A'
                        }
                      </p>
                    </div>
                    <div>
                      <label className="text-[13px] font-medium text-[#7A8580]">Advance</label>
                      <p className="text-[28px] font-semibold text-[#3D4A44]">
                        {songDetails.advance_amount 
                          ? `$${songDetails.advance_amount.toLocaleString()}`
                          : 'N/A'
                        }
                      </p>
                    </div>
                  </div>
                </div>
                
                <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-5">
                  <h3 className="text-[17px] font-semibold text-[#3D4A44] mb-4">Status Checklist</h3>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-[15px] text-[#3D4A44]">Contract Executed</span>
                      {getStatusIcon(songDetails.has_contract_executed)}
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-[15px] text-[#3D4A44]">Contract Location</span>
                      <span className="text-[15px] font-medium text-[#3D4A44]">{songDetails.contract_location || 'N/A'}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-[15px] text-[#3D4A44]">PRO Registered</span>
                      {getStatusIcon(songDetails.is_registered_with_pro)}
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-[15px] text-[#3D4A44]">DSP Registered</span>
                      {getStatusIcon(songDetails.is_registered_with_dsp)}
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-[15px] text-[#3D4A44]">SoundExchange Registered</span>
                      {getStatusIcon(songDetails.soundexchange_registered)}
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-[15px] text-[#3D4A44]">Master Paid</span>
                      {getStatusIcon(songDetails.master_paid)}
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-[15px] text-[#3D4A44]">Payment Status</span>
                      <span className={`inline-flex items-center px-3 py-1 rounded-full text-[13px] font-medium ${
                        songDetails.payment_status === 'PAID' 
                          ? 'bg-[rgba(91,154,110,0.15)] text-[#5B9A6E]' 
                          : 'bg-[rgba(0,0,0,0.05)] text-[#7A8580]'
                      }`}>
                        {songDetails.payment_status || 'N/A'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
              
              <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-5">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-[17px] font-semibold text-[#3D4A44]">Contracts & Agreements</h3>
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
                      className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-[12px] font-medium text-[15px] hover:shadow-[0px_4px_12px_rgba(91,138,114,0.3)] transition-all disabled:opacity-50"
                    >
                      <DocumentArrowUpIcon className="w-5 h-5" />
                      <span>{uploading ? 'Uploading...' : 'Upload Contract'}</span>
                    </button>
                  </div>
                </div>
                
                {contracts.length > 0 ? (
                  <div className="space-y-2">
                    {contracts.map((contract) => (
                      <div key={contract.id} className="flex items-center justify-between p-4 bg-[#F5F7F4] rounded-[12px] border border-[rgba(59,77,67,0.08)]">
                        <div className="flex items-center space-x-3">
                          <DocumentTextIcon className="w-8 h-8 text-[#5B8A72]" />
                          <div>
                            <p className="font-medium text-[#3D4A44]">{contract.file_name}</p>
                            <p className="text-[13px] text-[#7A8580]">
                              {contract.contract_type || 'Contract'} • {new Date(contract.created_at).toLocaleDateString()}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center space-x-2">
                          <button
                            onClick={() => downloadContract(contract.id)}
                            className="p-2 text-[#7A8580] hover:text-[#5B8A72] hover:bg-[rgba(91,138,114,0.1)] rounded-[8px] transition-colors"
                            title="Download"
                          >
                            <ArrowDownTrayIcon className="w-5 h-5" />
                          </button>
                          <button
                            onClick={() => handleDeleteContract(contract.id)}
                            className="p-2 text-[#7A8580] hover:text-[#C47068] hover:bg-[rgba(196,112,104,0.1)] rounded-[8px] transition-colors"
                            title="Delete"
                          >
                            <TrashIcon className="w-5 h-5" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 bg-[#F5F7F4] rounded-[12px] border-2 border-dashed border-[rgba(59,77,67,0.08)]">
                    <DocumentTextIcon className="w-12 h-12 text-[#7A8580] mx-auto mb-3" />
                    <p className="text-[#3D4A44]">No contracts uploaded yet</p>
                    <p className="text-[13px] text-[#7A8580]">Upload a PDF to attach it to this song</p>
                  </div>
                )}
              </div>
            </div>
          )}
          
          {activeTab === 'streaming' && (
            <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-5">
              <div className="text-center text-[#7A8580] py-12">
                Streaming metrics and valuation data will be displayed here
              </div>
            </div>
          )}
          
          {activeTab === 'links' && (
            <div className="space-y-6">
              <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-5">
                <h3 className="text-[17px] font-semibold text-[#3D4A44] mb-4">Credits</h3>
                {songDetails.credits && songDetails.credits.length > 0 ? (
                  <div className="space-y-2">
                    {songDetails.credits.map((credit, idx) => (
                      <div key={idx} className="flex items-center justify-between p-3 bg-[#F5F7F4] rounded-[12px]">
                        <div>
                          <p className="font-medium text-[#3D4A44]">{credit.creator?.display_name || 'Unknown'}</p>
                          <p className="text-[13px] text-[#7A8580]">{credit.role}</p>
                        </div>
                        <span className="text-[15px] font-medium text-[#3D4A44]">
                          {credit.share_percentage ? `${credit.share_percentage}%` : '-'}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-[#7A8580]">No credits added yet</p>
                )}
              </div>
              
              <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-5">
                <h3 className="text-[17px] font-semibold text-[#3D4A44] mb-4">DSP Links</h3>
                {songDetails.dsp_links && songDetails.dsp_links.length > 0 ? (
                  <div className="space-y-2">
                    {songDetails.dsp_links.map((link, idx) => (
                      <a
                        key={idx}
                        href={link.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center justify-between p-3 bg-[#F5F7F4] rounded-[12px] hover:bg-[#EEF1EC] transition-colors"
                      >
                        <span className="font-medium text-[#3D4A44]">{link.platform}</span>
                        <LinkIcon className="w-5 h-5 text-[#7A8580]" />
                      </a>
                    ))}
                  </div>
                ) : (
                  <p className="text-[#7A8580]">No DSP links added yet</p>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
