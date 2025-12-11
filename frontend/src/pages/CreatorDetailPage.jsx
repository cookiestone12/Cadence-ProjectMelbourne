import React, { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import axios from 'axios'
import { ArrowLeftIcon, ArrowDownTrayIcon, CheckIcon, XMarkIcon, PencilIcon, DocumentTextIcon, DocumentArrowDownIcon } from '@heroicons/react/24/outline'
import { CheckCircleIcon, XCircleIcon, MinusCircleIcon } from '@heroicons/react/24/solid'

export default function CreatorDetailPage() {
  const { id } = useParams()
  const [creator, setCreator] = useState(null)
  const [songs, setSongs] = useState([])
  const [scheduleAData, setScheduleAData] = useState(null)
  const [activeTab, setActiveTab] = useState('overview')
  const [loading, setLoading] = useState(true)
  const [editingSong, setEditingSong] = useState(null)
  const [editForm, setEditForm] = useState({})
  const [saving, setSaving] = useState(false)
  
  const loadSongs = async (orgId) => {
    const songsResponse = await axios.get(`/api/songs/org/${orgId}?creator_id=${id}&limit=1000`)
    setSongs(songsResponse.data)
  }
  
  const loadScheduleAData = async () => {
    try {
      const response = await axios.get(`/api/schedule-a/creator/${id}/data`)
      setScheduleAData(response.data)
    } catch (error) {
      console.error('Failed to load Schedule A data:', error)
    }
  }
  
  useEffect(() => {
    async function loadCreatorData() {
      try {
        const creatorResponse = await axios.get(`/api/creators/${id}`)
        setCreator(creatorResponse.data)
        
        const orgResponse = await axios.get('/api/organizations/current')
        const orgId = orgResponse.data.id
        
        await loadSongs(orgId)
      } catch (error) {
        console.error('Failed to load creator:', error)
      } finally {
        setLoading(false)
      }
    }
    
    loadCreatorData()
  }, [id])
  
  useEffect(() => {
    if (activeTab === 'schedule-a') {
      loadScheduleAData()
    }
  }, [activeTab, id])
  
  const handleScheduleAExportCSV = async () => {
    try {
      const response = await axios.get(`/api/schedule-a/creator/${id}/csv`, {
        responseType: 'blob'
      })
      
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `Schedule_A_${creator.display_name.replace(/ /g, '_')}.csv`)
      document.body.appendChild(link)
      link.click()
      link.remove()
    } catch (error) {
      console.error('Failed to export Schedule A CSV:', error)
    }
  }
  
  const handleScheduleAExportPDF = async () => {
    try {
      const response = await axios.get(`/api/schedule-a/creator/${id}/pdf`, {
        responseType: 'blob'
      })
      
      const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `Schedule_A_${creator.display_name.replace(/ /g, '_')}.pdf`)
      document.body.appendChild(link)
      link.click()
      link.remove()
    } catch (error) {
      console.error('Failed to export Schedule A PDF:', error)
    }
  }
  
  const startEdit = (song) => {
    setEditingSong(song.id)
    setEditForm({
      publishing_percentage: song.publishing_percentage || '',
      master_percentage: song.master_percentage || '',
      advance_amount: song.advance_amount ? (song.advance_amount / 100) : '',
      label: song.label || '',
      is_registered_with_pro: song.is_registered_with_pro || false,
      is_registered_with_dsp: song.is_registered_with_dsp || false,
      soundexchange_registered: song.soundexchange_registered || 'N/A',
      is_paid: song.is_paid || false,
      is_invoiced: song.is_invoiced || false,
      has_contract_executed: song.has_contract_executed || false,
      notes: song.notes || ''
    })
  }
  
  const cancelEdit = () => {
    setEditingSong(null)
    setEditForm({})
  }
  
  const saveEdit = async (songId) => {
    setSaving(true)
    try {
      const payload = {
        publishing_percentage: editForm.publishing_percentage === '' ? null : Math.min(parseFloat(editForm.publishing_percentage), 100),
        master_percentage: editForm.master_percentage === '' ? null : Math.min(parseFloat(editForm.master_percentage), 100),
        advance_amount: editForm.advance_amount === '' ? null : Math.round(parseFloat(editForm.advance_amount) * 100),
        label: editForm.label || null,
        is_registered_with_pro: editForm.is_registered_with_pro,
        is_registered_with_dsp: editForm.is_registered_with_dsp,
        soundexchange_registered: editForm.soundexchange_registered,
        is_paid: editForm.is_paid,
        is_invoiced: editForm.is_invoiced,
        has_contract_executed: editForm.has_contract_executed,
        notes: editForm.notes || null
      }
      
      await axios.patch(`/api/songs/${songId}`, payload)
      
      const orgResponse = await axios.get('/api/organizations/current')
      await loadSongs(orgResponse.data.id)
      
      setEditingSong(null)
      setEditForm({})
    } catch (error) {
      console.error('Failed to update song:', error)
      alert('Failed to save changes')
    } finally {
      setSaving(false)
    }
  }
  
  const StatusBadge = ({ value, label }) => {
    if (value === true || value === 'Yes') {
      return (
        <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium" style={{ background: 'rgba(52, 199, 89, 0.15)', color: '#34C759' }}>
          <CheckCircleIcon className="w-3 h-3" />
          {label || 'Yes'}
        </span>
      )
    } else if (value === false || value === 'No') {
      return (
        <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium" style={{ background: 'rgba(255, 59, 48, 0.15)', color: '#FF3B30' }}>
          <XCircleIcon className="w-3 h-3" />
          {label || 'No'}
        </span>
      )
    } else {
      return (
        <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium" style={{ background: 'rgba(0, 0, 0, 0.05)', color: '#86868B' }}>
          <MinusCircleIcon className="w-3 h-3" />
          N/A
        </span>
      )
    }
  }
  
  const PlacementStatusBadge = ({ status }) => {
    const colors = {
      'Paid': { bg: 'rgba(52, 199, 89, 0.15)', color: '#34C759' },
      'Invoiced': { bg: 'rgba(0, 122, 255, 0.15)', color: '#007AFF' },
      'Contracted': { bg: 'rgba(160, 32, 240, 0.15)', color: '#A020F0' },
      'Contract Sent': { bg: 'rgba(88, 86, 214, 0.15)', color: '#5856D6' },
      'Released - Awaiting Contract': { bg: 'rgba(255, 149, 0, 0.15)', color: '#FF9500' },
      'In Pipeline': { bg: 'rgba(0, 0, 0, 0.05)', color: '#86868B' }
    }
    const style = colors[status] || colors['In Pipeline']
    return (
      <span 
        className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium"
        style={{ background: style.bg, color: style.color }}
      >
        {status}
      </span>
    )
  }
  
  if (loading) {
    return (
      <div className="flex items-center justify-center h-full bg-[#F7F7F9]">
        <div className="text-[#86868B]">Loading creator...</div>
      </div>
    )
  }
  
  if (!creator) {
    return (
      <div className="flex items-center justify-center h-full bg-[#F7F7F9]">
        <div className="text-[#86868B]">Creator not found</div>
      </div>
    )
  }
  
  const placedSongs = songs.filter(s => s.is_paid)
  const registeredPro = songs.filter(s => s.is_registered_with_pro).length
  const registeredDsp = songs.filter(s => s.is_registered_with_dsp).length
  const totalAdvance = songs.reduce((sum, s) => sum + (s.advance_amount || 0), 0) / 100
  
  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'songs', label: `Songs (${songs.length})` },
    { id: 'placements', label: `Placements (${placedSongs.length})` },
    { id: 'schedule-a', label: 'Schedule A' }
  ]
  
  return (
    <div className="min-h-screen bg-[#F7F7F9]">
      <div className="relative h-80" style={{ background: 'linear-gradient(135deg, #A020F0 0%, #E540AC 100%)' }}>
        {creator.hero_image_url && (
          <img 
            src={creator.hero_image_url} 
            alt={creator.display_name}
            className="absolute inset-0 w-full h-full object-cover mix-blend-overlay opacity-40"
          />
        )}
        
        <div className="absolute inset-0 bg-gradient-to-t from-black/40 to-transparent"></div>
        
        <div className="relative h-full flex flex-col justify-end p-8">
          <Link 
            to="/roster" 
            className="inline-flex items-center space-x-2 text-white/90 hover:text-white mb-4 w-fit transition-colors"
          >
            <ArrowLeftIcon className="w-5 h-5" />
            <span>Back to Roster</span>
          </Link>
          
          <h1 className="text-5xl font-semibold text-white mb-2">{creator.display_name}</h1>
          <div className="flex items-center space-x-4 text-white/90">
            <span className="text-lg">{creator.roles?.join(', ') || 'Producer'}</span>
            <span>•</span>
            <span>{songs.length} songs</span>
            <span>•</span>
            <span>{placedSongs.length} paid placements</span>
            <span>•</span>
            <span>${totalAdvance.toLocaleString()} advances</span>
          </div>
        </div>
      </div>
      
      <div className="bg-white border-b border-[rgba(0,0,0,0.07)] sticky top-0 z-10">
        <div className="px-8">
          <div className="flex space-x-8">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`py-4 px-2 border-b-2 font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'border-[#A020F0] text-[#A020F0]'
                    : 'border-transparent text-[#86868B] hover:text-[#1D1D1F]'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>
      
      <div className="p-8">
        {activeTab === 'overview' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              <div className="bg-white rounded-[18px] p-7" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                <h2 className="text-xl font-semibold text-[#1D1D1F] mb-5">Performance</h2>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <p className="text-sm text-[#86868B] mb-1">Total Songs</p>
                    <p className="text-2xl font-semibold text-[#1D1D1F]">{songs.length}</p>
                  </div>
                  <div>
                    <p className="text-sm text-[#86868B] mb-1">Paid Placements</p>
                    <p className="text-2xl font-semibold text-[#34C759]">{placedSongs.length}</p>
                  </div>
                  <div>
                    <p className="text-sm text-[#86868B] mb-1">PRO Registered</p>
                    <p className="text-2xl font-semibold text-[#007AFF]">{registeredPro}</p>
                  </div>
                  <div>
                    <p className="text-sm text-[#86868B] mb-1">DSP Registered</p>
                    <p className="text-2xl font-semibold text-[#A020F0]">{registeredDsp}</p>
                  </div>
                </div>
              </div>
              
              <div className="bg-white rounded-[18px] p-7" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                <h2 className="text-xl font-semibold text-[#1D1D1F] mb-5">Financials</h2>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <div>
                    <p className="text-sm text-[#86868B] mb-1">Total Advances</p>
                    <p className="text-2xl font-semibold text-[#34C759]">${totalAdvance.toLocaleString()}</p>
                  </div>
                  <div>
                    <p className="text-sm text-[#86868B] mb-1">Avg Publishing %</p>
                    <p className="text-2xl font-semibold text-[#1D1D1F]">
                      {songs.filter(s => s.publishing_percentage).length > 0 
                        ? (songs.reduce((sum, s) => sum + (s.publishing_percentage || 0), 0) / songs.filter(s => s.publishing_percentage).length).toFixed(1)
                        : 0}%
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-[#86868B] mb-1">Avg Health Score</p>
                    <p className="text-2xl font-semibold text-[#1D1D1F]">{creator.avg_health_score?.toFixed(0) || 0}%</p>
                  </div>
                </div>
              </div>
              
              <div className="bg-white rounded-[18px] p-7" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                <h2 className="text-xl font-semibold text-[#1D1D1F] mb-5">Recent Songs</h2>
                <div className="space-y-3">
                  {songs.slice(0, 5).map((song) => (
                    <div key={song.id} className="flex items-center justify-between p-4 bg-[#F8F8FB] rounded-xl">
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-[#1D1D1F] truncate">{song.title}</p>
                        <p className="text-sm text-[#86868B]">{song.primary_artist}</p>
                      </div>
                      <div className="flex items-center gap-2 ml-4">
                        <StatusBadge value={song.is_paid} label="Paid" />
                        <StatusBadge value={song.is_registered_with_pro} label="PRO" />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            
            <div className="space-y-6">
              <div className="bg-white rounded-[18px] p-7" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                <h2 className="text-xl font-semibold text-[#1D1D1F] mb-5">Details</h2>
                <div className="space-y-4 text-sm">
                  {creator.legal_name && (
                    <div>
                      <p className="text-[#86868B]">Legal Name</p>
                      <p className="font-medium text-[#1D1D1F]">{creator.legal_name}</p>
                    </div>
                  )}
                  {creator.primary_territory && (
                    <div>
                      <p className="text-[#86868B]">Territory</p>
                      <p className="font-medium text-[#1D1D1F]">{creator.primary_territory}</p>
                    </div>
                  )}
                  {creator.primary_pro && (
                    <div>
                      <p className="text-[#86868B]">PRO</p>
                      <p className="font-medium text-[#1D1D1F]">{creator.primary_pro}</p>
                    </div>
                  )}
                  {creator.primary_ipi && (
                    <div>
                      <p className="text-[#86868B]">IPI</p>
                      <p className="font-medium text-[#1D1D1F]">{creator.primary_ipi}</p>
                    </div>
                  )}
                </div>
              </div>
              
              <div className="bg-white rounded-[18px] p-7" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                <h2 className="text-xl font-semibold text-[#1D1D1F] mb-5">Registration Status</h2>
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <span className="text-[#86868B]">PRO Registered</span>
                    <span className="font-medium text-[#1D1D1F]">{registeredPro} / {songs.length}</span>
                  </div>
                  <div className="w-full bg-[#F2F2F5] rounded-full h-2">
                    <div 
                      className="h-2 rounded-full" 
                      style={{ width: `${songs.length > 0 ? (registeredPro / songs.length) * 100 : 0}%`, background: '#007AFF' }}
                    />
                  </div>
                  
                  <div className="flex justify-between items-center mt-4">
                    <span className="text-[#86868B]">DSP Registered</span>
                    <span className="font-medium text-[#1D1D1F]">{registeredDsp} / {songs.length}</span>
                  </div>
                  <div className="w-full bg-[#F2F2F5] rounded-full h-2">
                    <div 
                      className="h-2 rounded-full" 
                      style={{ width: `${songs.length > 0 ? (registeredDsp / songs.length) * 100 : 0}%`, background: '#A020F0' }}
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
        
        {activeTab === 'songs' && (
          <div className="bg-white rounded-[18px] overflow-hidden" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
            <div className="p-5 border-b border-[rgba(0,0,0,0.07)] bg-[#F8F8FB]">
              <p className="text-sm text-[#86868B]">
                Showing all {songs.length} songs. Click the edit button to update placement status.
              </p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-[#F8F8FB] border-b border-[rgba(0,0,0,0.07)]">
                  <tr>
                    <th className="px-4 py-3 text-left font-semibold text-[#1D1D1F] sticky left-0 bg-[#F8F8FB]">Title / Artist</th>
                    <th className="px-4 py-3 text-left font-semibold text-[#1D1D1F]">Label</th>
                    <th className="px-4 py-3 text-center font-semibold text-[#1D1D1F]">Pub %</th>
                    <th className="px-4 py-3 text-right font-semibold text-[#1D1D1F]">Advance</th>
                    <th className="px-4 py-3 text-center font-semibold text-[#1D1D1F]">PRO</th>
                    <th className="px-4 py-3 text-center font-semibold text-[#1D1D1F]">DSP</th>
                    <th className="px-4 py-3 text-center font-semibold text-[#1D1D1F]">Sound Ex.</th>
                    <th className="px-4 py-3 text-center font-semibold text-[#1D1D1F]">Contract</th>
                    <th className="px-4 py-3 text-center font-semibold text-[#1D1D1F]">Paid</th>
                    <th className="px-4 py-3 text-center font-semibold text-[#1D1D1F]">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {songs.map((song, index) => (
                    <tr key={song.id} className={`hover:bg-[#F8F8FB] transition-colors border-b border-[rgba(0,0,0,0.05)] ${index % 2 === 0 ? 'bg-white' : 'bg-[#F8F8FB]'}`}>
                      {editingSong === song.id ? (
                        <>
                          <td className={`px-4 py-3 sticky left-0 ${index % 2 === 0 ? 'bg-white' : 'bg-[#F8F8FB]'}`}>
                            <div className="font-medium text-[#1D1D1F]">{song.title}</div>
                            <div className="text-xs text-[#86868B]">{song.primary_artist}</div>
                          </td>
                          <td className="px-4 py-2">
                            <input 
                              type="text" 
                              value={editForm.label}
                              onChange={(e) => setEditForm({...editForm, label: e.target.value})}
                              className="w-full px-3 py-2 border border-[rgba(0,0,0,0.1)] rounded-xl text-sm bg-white focus:outline-none focus:border-[#A020F0] focus:ring-2 focus:ring-[rgba(160,32,240,0.1)]"
                              placeholder="Label"
                            />
                          </td>
                          <td className="px-4 py-2">
                            <input 
                              type="number" 
                              value={editForm.publishing_percentage}
                              onChange={(e) => setEditForm({...editForm, publishing_percentage: e.target.value})}
                              className="w-16 px-3 py-2 border border-[rgba(0,0,0,0.1)] rounded-xl text-sm text-center bg-white focus:outline-none focus:border-[#A020F0] focus:ring-2 focus:ring-[rgba(160,32,240,0.1)]"
                              placeholder="%"
                              step="0.01"
                              max="100"
                            />
                          </td>
                          <td className="px-4 py-2">
                            <input 
                              type="number" 
                              value={editForm.advance_amount}
                              onChange={(e) => setEditForm({...editForm, advance_amount: e.target.value})}
                              className="w-24 px-3 py-2 border border-[rgba(0,0,0,0.1)] rounded-xl text-sm text-right bg-white focus:outline-none focus:border-[#A020F0] focus:ring-2 focus:ring-[rgba(160,32,240,0.1)]"
                              placeholder="$"
                              step="0.01"
                            />
                          </td>
                          <td className="px-4 py-2 text-center">
                            <input 
                              type="checkbox" 
                              checked={editForm.is_registered_with_pro}
                              onChange={(e) => setEditForm({...editForm, is_registered_with_pro: e.target.checked})}
                              className="w-4 h-4 text-[#A020F0] rounded accent-[#A020F0]"
                            />
                          </td>
                          <td className="px-4 py-2 text-center">
                            <input 
                              type="checkbox" 
                              checked={editForm.is_registered_with_dsp}
                              onChange={(e) => setEditForm({...editForm, is_registered_with_dsp: e.target.checked})}
                              className="w-4 h-4 text-[#A020F0] rounded accent-[#A020F0]"
                            />
                          </td>
                          <td className="px-4 py-2 text-center">
                            <select 
                              value={editForm.soundexchange_registered}
                              onChange={(e) => setEditForm({...editForm, soundexchange_registered: e.target.value})}
                              className="px-3 py-2 border border-[rgba(0,0,0,0.1)] rounded-xl text-sm bg-white focus:outline-none focus:border-[#A020F0]"
                            >
                              <option value="N/A">N/A</option>
                              <option value="Yes">Yes</option>
                              <option value="No">No</option>
                            </select>
                          </td>
                          <td className="px-4 py-2 text-center">
                            <input 
                              type="checkbox" 
                              checked={editForm.has_contract_executed}
                              onChange={(e) => setEditForm({...editForm, has_contract_executed: e.target.checked})}
                              className="w-4 h-4 text-[#A020F0] rounded accent-[#A020F0]"
                            />
                          </td>
                          <td className="px-4 py-2 text-center">
                            <input 
                              type="checkbox" 
                              checked={editForm.is_paid}
                              onChange={(e) => setEditForm({...editForm, is_paid: e.target.checked})}
                              className="w-4 h-4 text-[#A020F0] rounded accent-[#A020F0]"
                            />
                          </td>
                          <td className="px-4 py-2">
                            <div className="flex items-center gap-2 justify-center">
                              <button 
                                onClick={() => saveEdit(song.id)}
                                disabled={saving}
                                className="p-2 rounded-lg transition-colors" style={{ background: 'rgba(52, 199, 89, 0.15)', color: '#34C759' }}
                              >
                                <CheckIcon className="w-5 h-5" />
                              </button>
                              <button 
                                onClick={cancelEdit}
                                disabled={saving}
                                className="p-2 rounded-lg transition-colors" style={{ background: 'rgba(255, 59, 48, 0.15)', color: '#FF3B30' }}
                              >
                                <XMarkIcon className="w-5 h-5" />
                              </button>
                            </div>
                          </td>
                        </>
                      ) : (
                        <>
                          <td className={`px-4 py-3 sticky left-0 ${index % 2 === 0 ? 'bg-white' : 'bg-[#F8F8FB]'}`}>
                            <div className="font-medium text-[#1D1D1F]">{song.title}</div>
                            <div className="text-xs text-[#86868B]">{song.primary_artist}</div>
                          </td>
                          <td className="px-4 py-3 text-[#86868B] max-w-32 truncate" title={song.label}>
                            {song.label || '-'}
                          </td>
                          <td className="px-4 py-3 text-center text-[#86868B]">
                            {song.publishing_percentage ? `${Math.min(song.publishing_percentage, 100).toFixed(1)}%` : '-'}
                          </td>
                          <td className="px-4 py-3 text-right text-[#86868B]">
                            {song.advance_amount ? `$${(song.advance_amount / 100).toLocaleString()}` : '-'}
                          </td>
                          <td className="px-4 py-3 text-center">
                            <StatusBadge value={song.is_registered_with_pro} />
                          </td>
                          <td className="px-4 py-3 text-center">
                            <StatusBadge value={song.is_registered_with_dsp} />
                          </td>
                          <td className="px-4 py-3 text-center">
                            <StatusBadge value={song.soundexchange_registered} />
                          </td>
                          <td className="px-4 py-3 text-center">
                            <StatusBadge value={song.has_contract_executed} />
                          </td>
                          <td className="px-4 py-3 text-center">
                            <StatusBadge value={song.is_paid} />
                          </td>
                          <td className="px-4 py-3 text-center">
                            <button 
                              onClick={() => startEdit(song)}
                              className="p-2 text-[#86868B] hover:text-[#A020F0] rounded-lg transition-colors" style={{ background: 'rgba(0,0,0,0.03)' }}
                            >
                              <PencilIcon className="w-4 h-4" />
                            </button>
                          </td>
                        </>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
        
        {activeTab === 'placements' && (
          <div className="bg-white rounded-[18px] overflow-hidden" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
            <div className="p-5 border-b border-[rgba(0,0,0,0.07)] bg-[#F8F8FB]">
              <p className="text-sm text-[#86868B]">
                {placedSongs.length} paid placements totaling ${totalAdvance.toLocaleString()} in advances
              </p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-[#F8F8FB] border-b border-[rgba(0,0,0,0.07)]">
                  <tr>
                    <th className="px-4 py-3 text-left font-semibold text-[#1D1D1F]">Song</th>
                    <th className="px-4 py-3 text-left font-semibold text-[#1D1D1F]">Artist</th>
                    <th className="px-4 py-3 text-left font-semibold text-[#1D1D1F]">Label</th>
                    <th className="px-4 py-3 text-center font-semibold text-[#1D1D1F]">Pub %</th>
                    <th className="px-4 py-3 text-right font-semibold text-[#1D1D1F]">Advance</th>
                    <th className="px-4 py-3 text-center font-semibold text-[#1D1D1F]">PRO</th>
                    <th className="px-4 py-3 text-center font-semibold text-[#1D1D1F]">DSP</th>
                    <th className="px-4 py-3 text-left font-semibold text-[#1D1D1F]">Release</th>
                  </tr>
                </thead>
                <tbody>
                  {placedSongs.map((song, index) => (
                    <tr key={song.id} className={`hover:bg-[#F8F8FB] transition-colors border-b border-[rgba(0,0,0,0.05)] ${index % 2 === 0 ? 'bg-white' : 'bg-[#F8F8FB]'}`}>
                      <td className="px-4 py-3">
                        <div className="font-medium text-[#1D1D1F]">{song.title}</div>
                      </td>
                      <td className="px-4 py-3 text-[#86868B]">
                        {song.primary_artist}
                      </td>
                      <td className="px-4 py-3 text-[#86868B] max-w-40 truncate" title={song.label}>
                        {song.label || '-'}
                      </td>
                      <td className="px-4 py-3 text-center text-[#86868B]">
                        {song.publishing_percentage ? `${Math.min(song.publishing_percentage, 100).toFixed(1)}%` : '-'}
                      </td>
                      <td className="px-4 py-3 text-right font-medium text-[#34C759]">
                        ${song.advance_amount ? (song.advance_amount / 100).toLocaleString() : 0}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <StatusBadge value={song.is_registered_with_pro} />
                      </td>
                      <td className="px-4 py-3 text-center">
                        <StatusBadge value={song.is_registered_with_dsp} />
                      </td>
                      <td className="px-4 py-3 text-[#86868B]">
                        {song.release_date || '-'}
                      </td>
                    </tr>
                  ))}
                  
                  {placedSongs.length === 0 && (
                    <tr>
                      <td colSpan="8" className="px-6 py-12 text-center text-[#86868B]">
                        No paid placements yet
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
        
        {activeTab === 'schedule-a' && (
          <div className="space-y-6">
            <div className="rounded-[18px] p-8 text-white" style={{ background: 'linear-gradient(135deg, #A020F0 0%, #E540AC 100%)', boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                <div>
                  <h2 className="text-2xl font-semibold mb-2">Schedule A - Catalog of Compositions</h2>
                  <p className="text-white/80">
                    Official export document for {creator.display_name}'s catalog with industry-standard fields.
                  </p>
                </div>
                <div className="flex gap-3">
                  <button
                    onClick={handleScheduleAExportPDF}
                    className="inline-flex items-center space-x-2 bg-white text-[#A020F0] px-5 py-2.5 rounded-xl font-medium hover:bg-white/90 transition-all duration-200"
                    style={{ boxShadow: '0px 2px 8px rgba(0,0,0,0.1)' }}
                  >
                    <DocumentTextIcon className="w-5 h-5" />
                    <span>Download PDF</span>
                  </button>
                  <button
                    onClick={handleScheduleAExportCSV}
                    className="inline-flex items-center space-x-2 bg-white/20 text-white px-5 py-2.5 rounded-xl font-medium hover:bg-white/30 transition-all duration-200 border border-white/30"
                  >
                    <DocumentArrowDownIcon className="w-5 h-5" />
                    <span>Download CSV</span>
                  </button>
                </div>
              </div>
            </div>
            
            {scheduleAData && (
              <>
                <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
                  <div className="bg-white rounded-[18px] p-5" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                    <p className="text-sm text-[#86868B] mb-1">Total Compositions</p>
                    <p className="text-2xl font-semibold text-[#1D1D1F]">{scheduleAData.summary.total_songs}</p>
                  </div>
                  <div className="bg-white rounded-[18px] p-5" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                    <p className="text-sm text-[#86868B] mb-1">Released</p>
                    <p className="text-2xl font-semibold text-[#A020F0]">{scheduleAData.summary.released_count}</p>
                  </div>
                  <div className="bg-white rounded-[18px] p-5" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                    <p className="text-sm text-[#86868B] mb-1">Pipeline</p>
                    <p className="text-2xl font-semibold text-[#E540AC]">{scheduleAData.summary.pipeline_count}</p>
                  </div>
                  <div className="bg-white rounded-[18px] p-5" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                    <p className="text-sm text-[#86868B] mb-1">Paid</p>
                    <p className="text-2xl font-semibold text-[#34C759]">{scheduleAData.summary.paid_count}</p>
                  </div>
                  <div className="bg-white rounded-[18px] p-5" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                    <p className="text-sm text-[#86868B] mb-1">Contracted</p>
                    <p className="text-2xl font-semibold text-[#007AFF]">{scheduleAData.summary.contracted_count}</p>
                  </div>
                  <div className="bg-white rounded-[18px] p-5" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                    <p className="text-sm text-[#86868B] mb-1">Total Advances</p>
                    <p className="text-2xl font-semibold text-[#34C759]">{scheduleAData.summary.total_advance_display}</p>
                  </div>
                </div>
                
                {scheduleAData.released.length > 0 && (
                  <div className="bg-white rounded-[18px] overflow-hidden" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                    <div className="p-5 border-b border-[rgba(0,0,0,0.07)]" style={{ background: 'rgba(160, 32, 240, 0.08)' }}>
                      <h3 className="text-lg font-semibold text-[#A020F0]">Released Catalog ({scheduleAData.released.length})</h3>
                      <p className="text-sm text-[#86868B]">Songs that have been officially released</p>
                    </div>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead className="bg-[#F8F8FB] border-b border-[rgba(0,0,0,0.07)]">
                          <tr>
                            <th className="px-4 py-3 text-left font-semibold text-[#1D1D1F]">Title</th>
                            <th className="px-4 py-3 text-left font-semibold text-[#1D1D1F]">Artist</th>
                            <th className="px-4 py-3 text-left font-semibold text-[#1D1D1F]">Release</th>
                            <th className="px-4 py-3 text-left font-semibold text-[#1D1D1F]">Label</th>
                            <th className="px-4 py-3 text-center font-semibold text-[#1D1D1F]">Pub %</th>
                            <th className="px-4 py-3 text-right font-semibold text-[#1D1D1F]">Advance</th>
                            <th className="px-4 py-3 text-center font-semibold text-[#1D1D1F]">Status</th>
                            <th className="px-4 py-3 text-center font-semibold text-[#1D1D1F]">PRO</th>
                            <th className="px-4 py-3 text-center font-semibold text-[#1D1D1F]">DSP</th>
                          </tr>
                        </thead>
                        <tbody>
                          {scheduleAData.released.map((song, index) => (
                            <tr key={song.id} className={`hover:bg-[#F8F8FB] border-b border-[rgba(0,0,0,0.05)] ${index % 2 === 0 ? 'bg-white' : 'bg-[#F8F8FB]'}`}>
                              <td className="px-4 py-3 font-medium text-[#1D1D1F]">{song.title}</td>
                              <td className="px-4 py-3 text-[#86868B]">{song.primary_artist}</td>
                              <td className="px-4 py-3 text-[#86868B]">{song.release_date || '-'}</td>
                              <td className="px-4 py-3 text-[#86868B] max-w-32 truncate">{song.label || '-'}</td>
                              <td className="px-4 py-3 text-center text-[#86868B]">
                                {song.publishing_percentage ? `${Math.min(song.publishing_percentage, 100).toFixed(1)}%` : '-'}
                              </td>
                              <td className="px-4 py-3 text-right text-[#86868B]">{song.advance_display || '-'}</td>
                              <td className="px-4 py-3 text-center">
                                <PlacementStatusBadge status={song.status} />
                              </td>
                              <td className="px-4 py-3 text-center">
                                <StatusBadge value={song.is_registered_with_pro} />
                              </td>
                              <td className="px-4 py-3 text-center">
                                <StatusBadge value={song.is_registered_with_dsp} />
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
                
                {scheduleAData.pipeline.length > 0 && (
                  <div className="bg-white rounded-[18px] overflow-hidden" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                    <div className="p-5 border-b border-[rgba(0,0,0,0.07)]" style={{ background: 'rgba(229, 64, 172, 0.08)' }}>
                      <h3 className="text-lg font-semibold text-[#E540AC]">Pipeline ({scheduleAData.pipeline.length})</h3>
                      <p className="text-sm text-[#86868B]">Unreleased songs in various stages of the placement process</p>
                    </div>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead className="bg-[#F8F8FB] border-b border-[rgba(0,0,0,0.07)]">
                          <tr>
                            <th className="px-4 py-3 text-left font-semibold text-[#1D1D1F]">Title</th>
                            <th className="px-4 py-3 text-left font-semibold text-[#1D1D1F]">Artist</th>
                            <th className="px-4 py-3 text-left font-semibold text-[#1D1D1F]">Label</th>
                            <th className="px-4 py-3 text-center font-semibold text-[#1D1D1F]">Pub %</th>
                            <th className="px-4 py-3 text-right font-semibold text-[#1D1D1F]">Advance</th>
                            <th className="px-4 py-3 text-center font-semibold text-[#1D1D1F]">Status</th>
                            <th className="px-4 py-3 text-center font-semibold text-[#1D1D1F]">Contract</th>
                            <th className="px-4 py-3 text-center font-semibold text-[#1D1D1F]">Paid</th>
                          </tr>
                        </thead>
                        <tbody>
                          {scheduleAData.pipeline.map((song, index) => (
                            <tr key={song.id} className={`hover:bg-[#F8F8FB] border-b border-[rgba(0,0,0,0.05)] ${index % 2 === 0 ? 'bg-white' : 'bg-[#F8F8FB]'}`}>
                              <td className="px-4 py-3 font-medium text-[#1D1D1F]">{song.title}</td>
                              <td className="px-4 py-3 text-[#86868B]">{song.primary_artist}</td>
                              <td className="px-4 py-3 text-[#86868B] max-w-32 truncate">{song.label || '-'}</td>
                              <td className="px-4 py-3 text-center text-[#86868B]">
                                {song.publishing_percentage ? `${Math.min(song.publishing_percentage, 100).toFixed(1)}%` : '-'}
                              </td>
                              <td className="px-4 py-3 text-right text-[#86868B]">{song.advance_display || '-'}</td>
                              <td className="px-4 py-3 text-center">
                                <PlacementStatusBadge status={song.status} />
                              </td>
                              <td className="px-4 py-3 text-center">
                                <StatusBadge value={song.has_contract_executed} />
                              </td>
                              <td className="px-4 py-3 text-center">
                                <StatusBadge value={song.is_paid} />
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
                
                {scheduleAData.released.length === 0 && scheduleAData.pipeline.length === 0 && (
                  <div className="bg-white rounded-[18px] p-12 text-center" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                    <DocumentTextIcon className="w-12 h-12 text-[#C7C7CC] mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-[#1D1D1F] mb-2">No compositions yet</h3>
                    <p className="text-[#86868B]">Add songs to this creator's catalog to generate a Schedule A.</p>
                  </div>
                )}
              </>
            )}
            
            {!scheduleAData && (
              <div className="bg-white rounded-[18px] p-12 text-center" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                <div className="text-[#86868B]">Loading Schedule A data...</div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
