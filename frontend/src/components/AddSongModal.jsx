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
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div 
        className="bg-white rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-6 border-b border-gray-200 bg-gradient-to-r from-purple-50 to-pink-50">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold text-gray-900">Add New Song</h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <XMarkIcon className="w-6 h-6" />
            </button>
          </div>
        </div>
        
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6">
          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
              {error}
            </div>
          )}
          
          <div className="mb-8">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Basic Information</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Song Title <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={formData.title}
                  onChange={(e) => handleChange('title', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  placeholder="Enter song title"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Client / Creator <span className="text-red-500">*</span>
                </label>
                {loadingCreators ? (
                  <div className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-500">
                    Loading clients...
                  </div>
                ) : creators.length > 0 ? (
                  <select
                    required
                    value={formData.creator_id}
                    onChange={(e) => handleChange('creator_id', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  >
                    <option value="">Select a client...</option>
                    {creators.map(creator => (
                      <option key={creator.id} value={creator.id}>
                        {creator.name} ({creator.role})
                      </option>
                    ))}
                  </select>
                ) : (
                  <div className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-yellow-50 text-yellow-700 text-sm">
                    No clients in roster. Add a client first.
                  </div>
                )}
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Primary Artist <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={formData.primary_artist}
                  onChange={(e) => handleChange('primary_artist', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  placeholder="Enter artist name"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Credit Role</label>
                <select
                  value={formData.creator_role}
                  onChange={(e) => handleChange('creator_role', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                >
                  <option value="Writer">Writer</option>
                  <option value="Producer">Producer</option>
                  <option value="Performer">Performer</option>
                  <option value="Featured Artist">Featured Artist</option>
                  <option value="Composer">Composer</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Split %</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  max="100"
                  value={formData.creator_split}
                  onChange={(e) => handleChange('creator_split', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  placeholder="100"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">ISRC</label>
                <input
                  type="text"
                  value={formData.isrc}
                  onChange={(e) => handleChange('isrc', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  placeholder="US-XXX-XX-XXXXX"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">ISWC</label>
                <input
                  type="text"
                  value={formData.iswc}
                  onChange={(e) => handleChange('iswc', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  placeholder="T-XXX.XXX.XXX-X"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Project/Album Title</label>
                <input
                  type="text"
                  value={formData.project_title}
                  onChange={(e) => handleChange('project_title', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  placeholder="Enter project or album title"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Release Date</label>
                <input
                  type="date"
                  value={formData.release_date}
                  onChange={(e) => handleChange('release_date', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                />
              </div>
            </div>
          </div>
          
          <div className="mb-8">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Placement & Contract</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Label</label>
                <input
                  type="text"
                  value={formData.label}
                  onChange={(e) => handleChange('label', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  placeholder="Enter label name"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Recording Code</label>
                <input
                  type="text"
                  value={formData.recording_code}
                  onChange={(e) => handleChange('recording_code', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  placeholder="Enter recording code"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Audio File URL</label>
                <input
                  type="url"
                  value={formData.media_url}
                  onChange={(e) => handleChange('media_url', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  placeholder="Drive, Dropbox, or Disco link"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Contract Location</label>
                <input
                  type="text"
                  value={formData.contract_location}
                  onChange={(e) => handleChange('contract_location', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  placeholder="e.g., Dropbox/Contracts/2024"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Payment Status</label>
                <select
                  value={formData.payment_status}
                  onChange={(e) => handleChange('payment_status', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                >
                  <option value="PENDING">Pending</option>
                  <option value="PAID">Paid</option>
                  <option value="PARTIAL">Partial</option>
                  <option value="OVERDUE">Overdue</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Master Paid</label>
                <select
                  value={formData.master_paid}
                  onChange={(e) => handleChange('master_paid', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                >
                  <option value="Yes">Yes</option>
                  <option value="No">No</option>
                  <option value="N/A">N/A</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">SoundExchange Registered</label>
                <select
                  value={formData.soundexchange_registered}
                  onChange={(e) => handleChange('soundexchange_registered', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                >
                  <option value="Yes">Yes</option>
                  <option value="No">No</option>
                  <option value="N/A">N/A</option>
                </select>
              </div>
            </div>
          </div>
          
          <div className="mb-8">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Ownership & Financial</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Publishing %</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  max="100"
                  value={formData.publishing_percentage}
                  onChange={(e) => handleChange('publishing_percentage', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  placeholder="0.00"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Master %</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  max="100"
                  value={formData.master_percentage}
                  onChange={(e) => handleChange('master_percentage', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  placeholder="0.00"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Advance Amount ($)</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={formData.advance_amount}
                  onChange={(e) => handleChange('advance_amount', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  placeholder="0.00"
                />
              </div>
            </div>
          </div>
          
          <div className="mb-8">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Registration Status</h3>
            <div className="space-y-3">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={formData.has_contract_executed}
                  onChange={(e) => handleChange('has_contract_executed', e.target.checked)}
                  className="w-4 h-4 text-purple-600 border-gray-300 rounded focus:ring-purple-500"
                />
                <span className="ml-2 text-sm text-gray-700">Contract Executed</span>
              </label>
              
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={formData.is_registered_with_pro}
                  onChange={(e) => handleChange('is_registered_with_pro', e.target.checked)}
                  className="w-4 h-4 text-purple-600 border-gray-300 rounded focus:ring-purple-500"
                />
                <span className="ml-2 text-sm text-gray-700">Registered with PRO</span>
              </label>
              
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={formData.is_registered_with_dsp}
                  onChange={(e) => handleChange('is_registered_with_dsp', e.target.checked)}
                  className="w-4 h-4 text-purple-600 border-gray-300 rounded focus:ring-purple-500"
                />
                <span className="ml-2 text-sm text-gray-700">Registered with DSP</span>
              </label>
            </div>
          </div>
          
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
            <textarea
              value={formData.notes}
              onChange={(e) => handleChange('notes', e.target.value)}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              placeholder="Add any additional notes..."
            />
          </div>
          
          <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200">
            <button
              type="button"
              onClick={onClose}
              className="px-6 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
              disabled={loading}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || (creators.length > 0 && !formData.creator_id)}
              className="px-6 py-2 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-lg hover:from-purple-700 hover:to-pink-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Creating...' : 'Create Song'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
