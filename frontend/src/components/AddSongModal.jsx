import React, { useState, useEffect } from 'react'
import axios from 'axios'
import { XMarkIcon } from '@heroicons/react/24/outline'

export default function AddSongModal({ onClose, onSuccess, organizationId }) {
  const [creators, setCreators] = useState([])
  const [loadingCreators, setLoadingCreators] = useState(true)
  const [formData, setFormData] = useState({
    title: '',
    primary_artist: '',
    creator_id: '',
    creator_role: 'Writer',
    creator_split: '100',
    isrc: '',
    iswc: '',
    project_title: '',
    release_date: '',
    label: '',
    publishing_percentage: '',
    master_percentage: '',
    advance_amount: '',
    recording_code: '',
    master_paid: 'N/A',
    soundexchange_registered: 'N/A',
    payment_status: 'PENDING',
    contract_location: '',
    notes: '',
    media_url: '',
    has_contract_executed: false,
    is_registered_with_pro: false,
    is_registered_with_dsp: false
  })
  
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  
  useEffect(() => {
    fetchCreators()
  }, [organizationId])
  
  async function fetchCreators() {
    try {
      const token = localStorage.getItem('token')
      const response = await axios.get(`/api/creators/org/${organizationId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      setCreators(response.data)
    } catch (err) {
      console.error('Failed to fetch creators:', err)
    } finally {
      setLoadingCreators(false)
    }
  }
  
  const handleChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }))
  }
  
  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    
    if (!formData.creator_id) {
      setError('Please select a client. Every song must be assigned to a client in your roster.')
      setLoading(false)
      return
    }
    
    try {
      const token = localStorage.getItem('token')
      
      const payload = {
        title: formData.title,
        primary_artist: formData.primary_artist,
        isrc: formData.isrc || null,
        iswc: formData.iswc || null,
        project_title: formData.project_title || null,
        release_date: formData.release_date || null,
        label: formData.label || null,
        publishing_percentage: formData.publishing_percentage ? parseFloat(formData.publishing_percentage) : null,
        master_percentage: formData.master_percentage ? parseFloat(formData.master_percentage) : null,
        advance_amount: formData.advance_amount ? parseFloat(formData.advance_amount) * 100 : null,
        recording_code: formData.recording_code || null,
        master_paid: formData.master_paid,
        soundexchange_registered: formData.soundexchange_registered,
        payment_status: formData.payment_status,
        contract_location: formData.contract_location || null,
        notes: formData.notes || null,
        media_url: formData.media_url || null,
        has_contract_executed: formData.has_contract_executed,
        is_registered_with_pro: formData.is_registered_with_pro,
        is_registered_with_dsp: formData.is_registered_with_dsp
      }
      
      const songResponse = await axios.post(`/api/songs/org/${organizationId}`, payload, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      
      if (formData.creator_id) {
        const parsedSplit = parseFloat(formData.creator_split)
        const creditPayload = {
          creator_id: parseInt(formData.creator_id),
          role: formData.creator_role,
          split_percentage: Number.isNaN(parsedSplit) ? 100 : parsedSplit
        }
        
        await axios.post(`/api/credits/${songResponse.data.id}`, creditPayload, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
      }
      
      onSuccess()
      onClose()
    } catch (err) {
      console.error('Failed to create song:', err)
      setError(err.response?.data?.detail || 'Failed to create song. Please try again.')
    } finally {
      setLoading(false)
    }
  }
  
  return (
    <div className="fixed inset-0 bg-black/20 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div 
        className="bg-[#FFFFFF] rounded-[18px] shadow-[0px_4px_24px_rgba(0,0,0,0.12)] max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-6 border-b border-[rgba(0,0,0,0.07)] bg-[#FFFFFF]">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-semibold text-[#1D1D1F]">Add New Song</h2>
            <button
              onClick={onClose}
              className="text-[#86868B] hover:text-[#1D1D1F] transition-colors"
            >
              <XMarkIcon className="w-6 h-6" />
            </button>
          </div>
        </div>
        
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 bg-[#FFFFFF]">
          {error && (
            <div className="mb-6 p-4 bg-[rgba(255,59,48,0.1)] rounded-xl text-[#FF3B30]">
              {error}
            </div>
          )}
          
          <div className="mb-8">
            <h3 className="text-lg font-semibold text-[#1D1D1F] mb-4">Basic Information</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-[15px] font-medium text-[#1D1D1F] mb-1">
                  Song Title <span className="text-[#FF3B30]">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={formData.title}
                  onChange={(e) => handleChange('title', e.target.value)}
                  className="w-full px-4 py-3 bg-white border border-[rgba(0,0,0,0.1)] rounded-xl focus:ring-2 focus:ring-[#A020F0] focus:border-transparent text-[#1D1D1F] placeholder-[#86868B]"
                  placeholder="Enter song title"
                />
              </div>
              
              <div>
                <label className="block text-[15px] font-medium text-[#1D1D1F] mb-1">
                  Client / Creator <span className="text-[#FF3B30]">*</span>
                </label>
                {loadingCreators ? (
                  <div className="w-full px-4 py-3 border border-[rgba(0,0,0,0.1)] rounded-xl bg-[#F2F2F5] text-[#86868B]">
                    Loading clients...
                  </div>
                ) : creators.length > 0 ? (
                  <select
                    required
                    value={formData.creator_id}
                    onChange={(e) => handleChange('creator_id', e.target.value)}
                    className="w-full px-4 py-3 bg-white border border-[rgba(0,0,0,0.1)] rounded-xl focus:ring-2 focus:ring-[#A020F0] focus:border-transparent text-[#1D1D1F]"
                  >
                    <option value="">Select a client...</option>
                    {creators.map(creator => {
                      const roleDisplay = Array.isArray(creator.roles) && creator.roles.length > 0 
                        ? creator.roles[0] 
                        : (typeof creator.roles === 'string' && creator.roles ? creator.roles.split(',')[0].trim() : '')
                      return (
                        <option key={creator.id} value={creator.id}>
                          {creator.display_name}{roleDisplay ? ` (${roleDisplay})` : ''}
                        </option>
                      )
                    })}
                  </select>
                ) : (
                  <div className="w-full px-4 py-3 border border-[rgba(0,0,0,0.1)] rounded-xl bg-[rgba(255,149,0,0.1)] text-[#CC7700] text-sm">
                    No clients in roster. Add a client first.
                  </div>
                )}
              </div>
              
              <div>
                <label className="block text-[15px] font-medium text-[#1D1D1F] mb-1">
                  Primary Artist <span className="text-[#FF3B30]">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={formData.primary_artist}
                  onChange={(e) => handleChange('primary_artist', e.target.value)}
                  className="w-full px-4 py-3 bg-white border border-[rgba(0,0,0,0.1)] rounded-xl focus:ring-2 focus:ring-[#A020F0] focus:border-transparent text-[#1D1D1F] placeholder-[#86868B]"
                  placeholder="Enter artist name"
                />
              </div>
              
              <div>
                <label className="block text-[15px] font-medium text-[#1D1D1F] mb-1">Credit Role</label>
                <select
                  value={formData.creator_role}
                  onChange={(e) => handleChange('creator_role', e.target.value)}
                  className="w-full px-4 py-3 bg-white border border-[rgba(0,0,0,0.1)] rounded-xl focus:ring-2 focus:ring-[#A020F0] focus:border-transparent text-[#1D1D1F]"
                >
                  <option value="Writer">Writer</option>
                  <option value="Producer">Producer</option>
                  <option value="Performer">Performer</option>
                  <option value="Featured Artist">Featured Artist</option>
                  <option value="Composer">Composer</option>
                </select>
              </div>
              
              <div>
                <label className="block text-[15px] font-medium text-[#1D1D1F] mb-1">Split %</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  max="100"
                  value={formData.creator_split}
                  onChange={(e) => handleChange('creator_split', e.target.value)}
                  className="w-full px-4 py-3 bg-white border border-[rgba(0,0,0,0.1)] rounded-xl focus:ring-2 focus:ring-[#A020F0] focus:border-transparent text-[#1D1D1F] placeholder-[#86868B]"
                  placeholder="100"
                />
              </div>
              
              <div>
                <label className="block text-[15px] font-medium text-[#1D1D1F] mb-1">ISRC</label>
                <input
                  type="text"
                  value={formData.isrc}
                  onChange={(e) => handleChange('isrc', e.target.value)}
                  className="w-full px-4 py-3 bg-white border border-[rgba(0,0,0,0.1)] rounded-xl focus:ring-2 focus:ring-[#A020F0] focus:border-transparent text-[#1D1D1F] placeholder-[#86868B]"
                  placeholder="US-XXX-XX-XXXXX"
                />
              </div>
              
              <div>
                <label className="block text-[15px] font-medium text-[#1D1D1F] mb-1">ISWC</label>
                <input
                  type="text"
                  value={formData.iswc}
                  onChange={(e) => handleChange('iswc', e.target.value)}
                  className="w-full px-4 py-3 bg-white border border-[rgba(0,0,0,0.1)] rounded-xl focus:ring-2 focus:ring-[#A020F0] focus:border-transparent text-[#1D1D1F] placeholder-[#86868B]"
                  placeholder="T-XXX.XXX.XXX-X"
                />
              </div>
              
              <div>
                <label className="block text-[15px] font-medium text-[#1D1D1F] mb-1">Project/Album Title</label>
                <input
                  type="text"
                  value={formData.project_title}
                  onChange={(e) => handleChange('project_title', e.target.value)}
                  className="w-full px-4 py-3 bg-white border border-[rgba(0,0,0,0.1)] rounded-xl focus:ring-2 focus:ring-[#A020F0] focus:border-transparent text-[#1D1D1F] placeholder-[#86868B]"
                  placeholder="Enter project or album title"
                />
              </div>
              
              <div>
                <label className="block text-[15px] font-medium text-[#1D1D1F] mb-1">Release Date</label>
                <input
                  type="date"
                  value={formData.release_date}
                  onChange={(e) => handleChange('release_date', e.target.value)}
                  className="w-full px-4 py-3 bg-white border border-[rgba(0,0,0,0.1)] rounded-xl focus:ring-2 focus:ring-[#A020F0] focus:border-transparent text-[#1D1D1F]"
                />
              </div>
            </div>
          </div>
          
          <div className="mb-8">
            <h3 className="text-lg font-semibold text-[#1D1D1F] mb-4">Placement & Contract</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-[15px] font-medium text-[#1D1D1F] mb-1">Label</label>
                <input
                  type="text"
                  value={formData.label}
                  onChange={(e) => handleChange('label', e.target.value)}
                  className="w-full px-4 py-3 bg-white border border-[rgba(0,0,0,0.1)] rounded-xl focus:ring-2 focus:ring-[#A020F0] focus:border-transparent text-[#1D1D1F] placeholder-[#86868B]"
                  placeholder="Enter label name"
                />
              </div>
              
              <div>
                <label className="block text-[15px] font-medium text-[#1D1D1F] mb-1">Recording Code</label>
                <input
                  type="text"
                  value={formData.recording_code}
                  onChange={(e) => handleChange('recording_code', e.target.value)}
                  className="w-full px-4 py-3 bg-white border border-[rgba(0,0,0,0.1)] rounded-xl focus:ring-2 focus:ring-[#A020F0] focus:border-transparent text-[#1D1D1F] placeholder-[#86868B]"
                  placeholder="Enter recording code"
                />
              </div>
              
              <div>
                <label className="block text-[15px] font-medium text-[#1D1D1F] mb-1">Audio File URL</label>
                <input
                  type="url"
                  value={formData.media_url}
                  onChange={(e) => handleChange('media_url', e.target.value)}
                  className="w-full px-4 py-3 bg-white border border-[rgba(0,0,0,0.1)] rounded-xl focus:ring-2 focus:ring-[#A020F0] focus:border-transparent text-[#1D1D1F] placeholder-[#86868B]"
                  placeholder="Drive, Dropbox, or Disco link"
                />
              </div>
              
              <div>
                <label className="block text-[15px] font-medium text-[#1D1D1F] mb-1">Contract Location</label>
                <input
                  type="text"
                  value={formData.contract_location}
                  onChange={(e) => handleChange('contract_location', e.target.value)}
                  className="w-full px-4 py-3 bg-white border border-[rgba(0,0,0,0.1)] rounded-xl focus:ring-2 focus:ring-[#A020F0] focus:border-transparent text-[#1D1D1F] placeholder-[#86868B]"
                  placeholder="e.g., Dropbox/Contracts/2024"
                />
              </div>
              
              <div>
                <label className="block text-[15px] font-medium text-[#1D1D1F] mb-1">Payment Status</label>
                <select
                  value={formData.payment_status}
                  onChange={(e) => handleChange('payment_status', e.target.value)}
                  className="w-full px-4 py-3 bg-white border border-[rgba(0,0,0,0.1)] rounded-xl focus:ring-2 focus:ring-[#A020F0] focus:border-transparent text-[#1D1D1F]"
                >
                  <option value="PENDING">Pending</option>
                  <option value="PAID">Paid</option>
                  <option value="PARTIAL">Partial</option>
                  <option value="OVERDUE">Overdue</option>
                </select>
              </div>
              
              <div>
                <label className="block text-[15px] font-medium text-[#1D1D1F] mb-1">Master Paid</label>
                <select
                  value={formData.master_paid}
                  onChange={(e) => handleChange('master_paid', e.target.value)}
                  className="w-full px-4 py-3 bg-white border border-[rgba(0,0,0,0.1)] rounded-xl focus:ring-2 focus:ring-[#A020F0] focus:border-transparent text-[#1D1D1F]"
                >
                  <option value="Yes">Yes</option>
                  <option value="No">No</option>
                  <option value="N/A">N/A</option>
                </select>
              </div>
              
              <div>
                <label className="block text-[15px] font-medium text-[#1D1D1F] mb-1">SoundExchange Registered</label>
                <select
                  value={formData.soundexchange_registered}
                  onChange={(e) => handleChange('soundexchange_registered', e.target.value)}
                  className="w-full px-4 py-3 bg-white border border-[rgba(0,0,0,0.1)] rounded-xl focus:ring-2 focus:ring-[#A020F0] focus:border-transparent text-[#1D1D1F]"
                >
                  <option value="Yes">Yes</option>
                  <option value="No">No</option>
                  <option value="N/A">N/A</option>
                </select>
              </div>
            </div>
          </div>
          
          <div className="mb-8">
            <h3 className="text-lg font-semibold text-[#1D1D1F] mb-4">Ownership & Financial</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-[15px] font-medium text-[#1D1D1F] mb-1">Publishing %</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  max="100"
                  value={formData.publishing_percentage}
                  onChange={(e) => handleChange('publishing_percentage', e.target.value)}
                  className="w-full px-4 py-3 bg-white border border-[rgba(0,0,0,0.1)] rounded-xl focus:ring-2 focus:ring-[#A020F0] focus:border-transparent text-[#1D1D1F] placeholder-[#86868B]"
                  placeholder="0.00"
                />
              </div>
              
              <div>
                <label className="block text-[15px] font-medium text-[#1D1D1F] mb-1">Master %</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  max="100"
                  value={formData.master_percentage}
                  onChange={(e) => handleChange('master_percentage', e.target.value)}
                  className="w-full px-4 py-3 bg-white border border-[rgba(0,0,0,0.1)] rounded-xl focus:ring-2 focus:ring-[#A020F0] focus:border-transparent text-[#1D1D1F] placeholder-[#86868B]"
                  placeholder="0.00"
                />
              </div>
              
              <div>
                <label className="block text-[15px] font-medium text-[#1D1D1F] mb-1">Advance Amount ($)</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={formData.advance_amount}
                  onChange={(e) => handleChange('advance_amount', e.target.value)}
                  className="w-full px-4 py-3 bg-white border border-[rgba(0,0,0,0.1)] rounded-xl focus:ring-2 focus:ring-[#A020F0] focus:border-transparent text-[#1D1D1F] placeholder-[#86868B]"
                  placeholder="0.00"
                />
              </div>
            </div>
          </div>
          
          <div className="mb-8">
            <h3 className="text-lg font-semibold text-[#1D1D1F] mb-4">Registration Status</h3>
            <div className="space-y-3">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={formData.has_contract_executed}
                  onChange={(e) => handleChange('has_contract_executed', e.target.checked)}
                  className="w-4 h-4 text-[#A020F0] border-[rgba(0,0,0,0.1)] rounded focus:ring-[#A020F0]"
                />
                <span className="ml-2 text-[15px] text-[#1D1D1F]">Contract Executed</span>
              </label>
              
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={formData.is_registered_with_pro}
                  onChange={(e) => handleChange('is_registered_with_pro', e.target.checked)}
                  className="w-4 h-4 text-[#A020F0] border-[rgba(0,0,0,0.1)] rounded focus:ring-[#A020F0]"
                />
                <span className="ml-2 text-[15px] text-[#1D1D1F]">Registered with PRO</span>
              </label>
              
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={formData.is_registered_with_dsp}
                  onChange={(e) => handleChange('is_registered_with_dsp', e.target.checked)}
                  className="w-4 h-4 text-[#A020F0] border-[rgba(0,0,0,0.1)] rounded focus:ring-[#A020F0]"
                />
                <span className="ml-2 text-[15px] text-[#1D1D1F]">Registered with DSP</span>
              </label>
            </div>
          </div>
          
          <div className="mb-6">
            <label className="block text-[15px] font-medium text-[#1D1D1F] mb-1">Notes</label>
            <textarea
              value={formData.notes}
              onChange={(e) => handleChange('notes', e.target.value)}
              rows={3}
              className="w-full px-4 py-3 bg-white border border-[rgba(0,0,0,0.1)] rounded-xl focus:ring-2 focus:ring-[#A020F0] focus:border-transparent text-[#1D1D1F] placeholder-[#86868B]"
              placeholder="Add any additional notes..."
            />
          </div>
          
          <div className="flex justify-end space-x-3 pt-4 border-t border-[rgba(0,0,0,0.07)]">
            <button
              type="button"
              onClick={onClose}
              className="px-6 py-3 bg-[#F2F2F5] rounded-xl text-[#1D1D1F] font-medium hover:bg-[#E5E5EA] transition-colors"
              disabled={loading}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || (creators.length > 0 && !formData.creator_id)}
              className="px-6 py-3 bg-gradient-to-r from-[#A020F0] to-[#E540AC] text-white rounded-xl font-medium hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Creating...' : 'Create Song'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
