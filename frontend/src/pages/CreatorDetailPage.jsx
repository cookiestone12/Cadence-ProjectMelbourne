import React, { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import axios from 'axios'
import { ArrowLeftIcon, ArrowDownTrayIcon, CheckIcon, XMarkIcon, PencilIcon } from '@heroicons/react/24/outline'
import { CheckCircleIcon, XCircleIcon, MinusCircleIcon } from '@heroicons/react/24/solid'

export default function CreatorDetailPage() {
  const { id } = useParams()
  const [creator, setCreator] = useState(null)
  const [songs, setSongs] = useState([])
  const [activeTab, setActiveTab] = useState('overview')
  const [loading, setLoading] = useState(true)
  const [editingSong, setEditingSong] = useState(null)
  const [editForm, setEditForm] = useState({})
  const [saving, setSaving] = useState(false)
  
  const loadSongs = async (orgId) => {
    const songsResponse = await axios.get(`/api/songs/org/${orgId}?creator_id=${id}&limit=1000`)
    setSongs(songsResponse.data)
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
  
  const handleScheduleAExport = async () => {
    try {
      const response = await axios.get(`/api/schedule-a/creator/${id}`, {
        responseType: 'blob'
      })
      
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `schedule-a-${creator.display_name}.csv`)
      document.body.appendChild(link)
      link.click()
      link.remove()
    } catch (error) {
      console.error('Failed to export Schedule A:', error)
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
        publishing_percentage: editForm.publishing_percentage === '' ? null : parseFloat(editForm.publishing_percentage),
        master_percentage: editForm.master_percentage === '' ? null : parseFloat(editForm.master_percentage),
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
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">
          <CheckCircleIcon className="w-3 h-3" />
          {label || 'Yes'}
        </span>
      )
    } else if (value === false || value === 'No') {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700">
          <XCircleIcon className="w-3 h-3" />
          {label || 'No'}
        </span>
      )
    } else {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
          <MinusCircleIcon className="w-3 h-3" />
          N/A
        </span>
      )
    }
  }
  
  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-400">Loading creator...</div>
      </div>
    )
  }
  
  if (!creator) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-400">Creator not found</div>
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
    <div className="min-h-screen bg-gray-100">
      <div className="relative h-80 bg-gradient-to-br from-purple-600 to-pink-500">
        {creator.hero_image_url && (
          <img 
            src={creator.hero_image_url} 
            alt={creator.display_name}
            className="absolute inset-0 w-full h-full object-cover mix-blend-overlay opacity-50"
          />
        )}
        
        <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent"></div>
        
        <div className="relative h-full flex flex-col justify-end p-8">
          <Link 
            to="/roster" 
            className="inline-flex items-center space-x-2 text-white/80 hover:text-white mb-4 w-fit"
          >
            <ArrowLeftIcon className="w-5 h-5" />
            <span>Back to Roster</span>
          </Link>
          
          <h1 className="text-5xl font-bold text-white mb-2">{creator.display_name}</h1>
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
      
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="px-8">
          <div className="flex space-x-8">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`py-4 px-2 border-b-2 font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'border-purple-600 text-purple-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
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
              <div className="bg-white rounded-xl shadow-sm p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4">Performance</h2>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <p className="text-sm text-gray-500 mb-1">Total Songs</p>
                    <p className="text-2xl font-bold text-gray-900">{songs.length}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500 mb-1">Paid Placements</p>
                    <p className="text-2xl font-bold text-green-600">{placedSongs.length}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500 mb-1">PRO Registered</p>
                    <p className="text-2xl font-bold text-blue-600">{registeredPro}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500 mb-1">DSP Registered</p>
                    <p className="text-2xl font-bold text-purple-600">{registeredDsp}</p>
                  </div>
                </div>
              </div>
              
              <div className="bg-white rounded-xl shadow-sm p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4">Financials</h2>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <div>
                    <p className="text-sm text-gray-500 mb-1">Total Advances</p>
                    <p className="text-2xl font-bold text-green-600">${totalAdvance.toLocaleString()}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500 mb-1">Avg Publishing %</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {songs.filter(s => s.publishing_percentage).length > 0 
                        ? (songs.reduce((sum, s) => sum + (s.publishing_percentage || 0), 0) / songs.filter(s => s.publishing_percentage).length).toFixed(1)
                        : 0}%
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500 mb-1">Avg Health Score</p>
                    <p className="text-2xl font-bold text-gray-900">{creator.avg_health_score?.toFixed(0) || 0}%</p>
                  </div>
                </div>
              </div>
              
              <div className="bg-white rounded-xl shadow-sm p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4">Recent Songs</h2>
                <div className="space-y-3">
                  {songs.slice(0, 5).map((song) => (
                    <div key={song.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-gray-900 truncate">{song.title}</p>
                        <p className="text-sm text-gray-500">{song.primary_artist}</p>
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
              <div className="bg-white rounded-xl shadow-sm p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4">Details</h2>
                <div className="space-y-3 text-sm">
                  {creator.legal_name && (
                    <div>
                      <p className="text-gray-500">Legal Name</p>
                      <p className="font-medium text-gray-900">{creator.legal_name}</p>
                    </div>
                  )}
                  {creator.primary_territory && (
                    <div>
                      <p className="text-gray-500">Territory</p>
                      <p className="font-medium text-gray-900">{creator.primary_territory}</p>
                    </div>
                  )}
                  {creator.primary_pro && (
                    <div>
                      <p className="text-gray-500">PRO</p>
                      <p className="font-medium text-gray-900">{creator.primary_pro}</p>
                    </div>
                  )}
                  {creator.primary_ipi && (
                    <div>
                      <p className="text-gray-500">IPI</p>
                      <p className="font-medium text-gray-900">{creator.primary_ipi}</p>
                    </div>
                  )}
                </div>
              </div>
              
              <div className="bg-white rounded-xl shadow-sm p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4">Registration Status</h2>
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">PRO Registered</span>
                    <span className="font-medium">{registeredPro} / {songs.length}</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div 
                      className="bg-blue-600 h-2 rounded-full" 
                      style={{ width: `${songs.length > 0 ? (registeredPro / songs.length) * 100 : 0}%` }}
                    />
                  </div>
                  
                  <div className="flex justify-between items-center mt-4">
                    <span className="text-gray-600">DSP Registered</span>
                    <span className="font-medium">{registeredDsp} / {songs.length}</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div 
                      className="bg-purple-600 h-2 rounded-full" 
                      style={{ width: `${songs.length > 0 ? (registeredDsp / songs.length) * 100 : 0}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
        
        {activeTab === 'songs' && (
          <div className="bg-white rounded-xl shadow-sm overflow-hidden">
            <div className="p-4 border-b border-gray-200 bg-gray-50">
              <p className="text-sm text-gray-600">
                Showing all {songs.length} songs. Click the edit button to update placement status.
              </p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="px-4 py-3 text-left font-semibold text-gray-900 sticky left-0 bg-gray-50">Title / Artist</th>
                    <th className="px-4 py-3 text-left font-semibold text-gray-900">Label</th>
                    <th className="px-4 py-3 text-center font-semibold text-gray-900">Pub %</th>
                    <th className="px-4 py-3 text-right font-semibold text-gray-900">Advance</th>
                    <th className="px-4 py-3 text-center font-semibold text-gray-900">PRO</th>
                    <th className="px-4 py-3 text-center font-semibold text-gray-900">DSP</th>
                    <th className="px-4 py-3 text-center font-semibold text-gray-900">Sound Ex.</th>
                    <th className="px-4 py-3 text-center font-semibold text-gray-900">Contract</th>
                    <th className="px-4 py-3 text-center font-semibold text-gray-900">Paid</th>
                    <th className="px-4 py-3 text-center font-semibold text-gray-900">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {songs.map((song) => (
                    <tr key={song.id} className="hover:bg-gray-50 transition-colors">
                      {editingSong === song.id ? (
                        <>
                          <td className="px-4 py-3 sticky left-0 bg-white">
                            <div className="font-medium text-gray-900">{song.title}</div>
                            <div className="text-xs text-gray-500">{song.primary_artist}</div>
                          </td>
                          <td className="px-4 py-2">
                            <input 
                              type="text" 
                              value={editForm.label}
                              onChange={(e) => setEditForm({...editForm, label: e.target.value})}
                              className="w-full px-2 py-1 border rounded text-sm"
                              placeholder="Label"
                            />
                          </td>
                          <td className="px-4 py-2">
                            <input 
                              type="number" 
                              value={editForm.publishing_percentage}
                              onChange={(e) => setEditForm({...editForm, publishing_percentage: e.target.value})}
                              className="w-16 px-2 py-1 border rounded text-sm text-center"
                              placeholder="%"
                              step="0.01"
                            />
                          </td>
                          <td className="px-4 py-2">
                            <input 
                              type="number" 
                              value={editForm.advance_amount}
                              onChange={(e) => setEditForm({...editForm, advance_amount: e.target.value})}
                              className="w-24 px-2 py-1 border rounded text-sm text-right"
                              placeholder="$"
                              step="0.01"
                            />
                          </td>
                          <td className="px-4 py-2 text-center">
                            <input 
                              type="checkbox" 
                              checked={editForm.is_registered_with_pro}
                              onChange={(e) => setEditForm({...editForm, is_registered_with_pro: e.target.checked})}
                              className="w-4 h-4 text-purple-600 rounded"
                            />
                          </td>
                          <td className="px-4 py-2 text-center">
                            <input 
                              type="checkbox" 
                              checked={editForm.is_registered_with_dsp}
                              onChange={(e) => setEditForm({...editForm, is_registered_with_dsp: e.target.checked})}
                              className="w-4 h-4 text-purple-600 rounded"
                            />
                          </td>
                          <td className="px-4 py-2 text-center">
                            <select 
                              value={editForm.soundexchange_registered}
                              onChange={(e) => setEditForm({...editForm, soundexchange_registered: e.target.value})}
                              className="px-2 py-1 border rounded text-sm"
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
                              className="w-4 h-4 text-purple-600 rounded"
                            />
                          </td>
                          <td className="px-4 py-2 text-center">
                            <input 
                              type="checkbox" 
                              checked={editForm.is_paid}
                              onChange={(e) => setEditForm({...editForm, is_paid: e.target.checked})}
                              className="w-4 h-4 text-purple-600 rounded"
                            />
                          </td>
                          <td className="px-4 py-2">
                            <div className="flex items-center gap-2 justify-center">
                              <button 
                                onClick={() => saveEdit(song.id)}
                                disabled={saving}
                                className="p-1 text-green-600 hover:bg-green-100 rounded"
                              >
                                <CheckIcon className="w-5 h-5" />
                              </button>
                              <button 
                                onClick={cancelEdit}
                                disabled={saving}
                                className="p-1 text-red-600 hover:bg-red-100 rounded"
                              >
                                <XMarkIcon className="w-5 h-5" />
                              </button>
                            </div>
                          </td>
                        </>
                      ) : (
                        <>
                          <td className="px-4 py-3 sticky left-0 bg-white">
                            <div className="font-medium text-gray-900">{song.title}</div>
                            <div className="text-xs text-gray-500">{song.primary_artist}</div>
                          </td>
                          <td className="px-4 py-3 text-gray-600 max-w-32 truncate" title={song.label}>
                            {song.label || '-'}
                          </td>
                          <td className="px-4 py-3 text-center text-gray-600">
                            {song.publishing_percentage ? `${song.publishing_percentage.toFixed(1)}%` : '-'}
                          </td>
                          <td className="px-4 py-3 text-right text-gray-600">
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
                              className="p-1 text-gray-400 hover:text-purple-600 hover:bg-purple-50 rounded"
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
          <div className="bg-white rounded-xl shadow-sm overflow-hidden">
            <div className="p-4 border-b border-gray-200 bg-gray-50">
              <p className="text-sm text-gray-600">
                {placedSongs.length} paid placements totaling ${totalAdvance.toLocaleString()} in advances
              </p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="px-4 py-3 text-left font-semibold text-gray-900">Song</th>
                    <th className="px-4 py-3 text-left font-semibold text-gray-900">Artist</th>
                    <th className="px-4 py-3 text-left font-semibold text-gray-900">Label</th>
                    <th className="px-4 py-3 text-center font-semibold text-gray-900">Pub %</th>
                    <th className="px-4 py-3 text-right font-semibold text-gray-900">Advance</th>
                    <th className="px-4 py-3 text-center font-semibold text-gray-900">PRO</th>
                    <th className="px-4 py-3 text-center font-semibold text-gray-900">DSP</th>
                    <th className="px-4 py-3 text-left font-semibold text-gray-900">Release</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {placedSongs.map((song) => (
                    <tr key={song.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3">
                        <div className="font-medium text-gray-900">{song.title}</div>
                      </td>
                      <td className="px-4 py-3 text-gray-600">
                        {song.primary_artist}
                      </td>
                      <td className="px-4 py-3 text-gray-600 max-w-40 truncate" title={song.label}>
                        {song.label || '-'}
                      </td>
                      <td className="px-4 py-3 text-center text-gray-600">
                        {song.publishing_percentage ? `${song.publishing_percentage.toFixed(1)}%` : '-'}
                      </td>
                      <td className="px-4 py-3 text-right font-medium text-green-600">
                        ${song.advance_amount ? (song.advance_amount / 100).toLocaleString() : 0}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <StatusBadge value={song.is_registered_with_pro} />
                      </td>
                      <td className="px-4 py-3 text-center">
                        <StatusBadge value={song.is_registered_with_dsp} />
                      </td>
                      <td className="px-4 py-3 text-gray-600">
                        {song.release_date || '-'}
                      </td>
                    </tr>
                  ))}
                  
                  {placedSongs.length === 0 && (
                    <tr>
                      <td colSpan="8" className="px-6 py-12 text-center text-gray-400">
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
          <div className="bg-white rounded-xl shadow-sm p-12 text-center">
            <h2 className="text-2xl font-bold text-gray-900 mb-3">Schedule A Export</h2>
            <p className="text-gray-600 mb-6 max-w-2xl mx-auto">
              Export a complete Schedule A document for {creator.display_name}'s catalog. 
              This includes all songs with credits, splits, and registration details.
            </p>
            
            <button
              onClick={handleScheduleAExport}
              className="inline-flex items-center space-x-2 bg-gradient-to-r from-purple-600 to-pink-500 text-white px-6 py-3 rounded-lg font-medium hover:from-purple-700 hover:to-pink-600 transition-all duration-200"
            >
              <ArrowDownTrayIcon className="w-5 h-5" />
              <span>Download Schedule A (CSV)</span>
            </button>
            
            <div className="mt-8 grid grid-cols-2 md:grid-cols-4 gap-4 max-w-3xl mx-auto">
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-sm text-gray-500 mb-1">Total Songs</p>
                <p className="text-2xl font-bold text-gray-900">{songs.length}</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-sm text-gray-500 mb-1">Paid Placements</p>
                <p className="text-2xl font-bold text-green-600">{placedSongs.length}</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-sm text-gray-500 mb-1">Total Advances</p>
                <p className="text-2xl font-bold text-green-600">${totalAdvance.toLocaleString()}</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-sm text-gray-500 mb-1">Avg Health</p>
                <p className="text-2xl font-bold text-gray-900">{creator.avg_health_score?.toFixed(0) || 0}%</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
