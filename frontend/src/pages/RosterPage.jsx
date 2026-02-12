import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import axios from 'axios'
import { PlusIcon, XMarkIcon, ArrowUpTrayIcon, UserPlusIcon, CameraIcon } from '@heroicons/react/24/outline'

const ROLE_OPTIONS = ['ARTIST', 'SONGWRITER', 'PRODUCER']
const PRO_OPTIONS = ['ASCAP', 'BMI', 'PRS', 'SESAC', 'OTHER']

export default function RosterPage() {
  const [creators, setCreators] = useState([])
  const [loading, setLoading] = useState(true)
  const [orgId, setOrgId] = useState(null)
  const [showNewCreatorModal, setShowNewCreatorModal] = useState(false)
  const [showCSVModal, setShowCSVModal] = useState(false)
  const [creating, setCreating] = useState(false)
  const [newCreator, setNewCreator] = useState({
    display_name: '',
    legal_name: '',
    email: '',
    roles: ['ARTIST'],
    primary_territory: '',
    primary_pro: '',
    primary_ipi: ''
  })

  const [uploadingImageId, setUploadingImageId] = useState(null)

  const handleImageUpload = async (creatorId, file) => {
    if (!file) return
    setUploadingImageId(creatorId)
    try {
      const formData = new FormData()
      formData.append('file', file)
      await axios.post(`/api/creators/${creatorId}/image`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      await loadData()
    } catch (error) {
      console.error('Failed to upload image:', error)
      alert(error.response?.data?.detail || 'Failed to upload image')
    } finally {
      setUploadingImageId(null)
    }
  }

  const [csvFile, setCsvFile] = useState(null)
  const [csvPreview, setCsvPreview] = useState(null)
  const [csvMapping, setCsvMapping] = useState({})
  const [csvAllRows, setCsvAllRows] = useState([])
  const [importing, setImporting] = useState(false)
  const [selectedCreatorId, setSelectedCreatorId] = useState('')
  const [createNewCreatorForCSV, setCreateNewCreatorForCSV] = useState(false)
  const [newCreatorNameForCSV, setNewCreatorNameForCSV] = useState('')
  
  useEffect(() => {
    loadData()
  }, [])

  async function loadData() {
    try {
      const orgResponse = await axios.get('/api/organizations/current')
      const currentOrgId = orgResponse.data?.id
      if (!currentOrgId) { setLoading(false); return }
      setOrgId(currentOrgId)
      
      axios.get(`/api/creators/org/${currentOrgId}`)
        .then(res => setCreators(res.data || []))
        .catch(err => console.error('Failed to load creators:', err))
        .finally(() => setLoading(false))
    } catch (error) {
      console.error('Failed to load roster:', error)
      setLoading(false)
    }
  }

  const handleCreateCreator = async (e) => {
    e.preventDefault()
    if (!newCreator.display_name.trim()) return
    
    setCreating(true)
    try {
      await axios.post(`/api/creators/org/${orgId}`, newCreator)
      setShowNewCreatorModal(false)
      setNewCreator({
        display_name: '',
        legal_name: '',
        email: '',
        roles: ['ARTIST'],
        primary_territory: '',
        primary_pro: '',
        primary_ipi: ''
      })
      await loadData()
    } catch (error) {
      console.error('Failed to create creator:', error)
      alert(error.response?.data?.detail || 'Failed to create creator')
    } finally {
      setCreating(false)
    }
  }

  const handleRoleToggle = (role) => {
    setNewCreator(prev => ({
      ...prev,
      roles: prev.roles.includes(role)
        ? prev.roles.filter(r => r !== role)
        : [...prev.roles, role]
    }))
  }

  const parseCSVLocally = (text) => {
    const lines = text.split('\n').filter(line => line.trim())
    if (lines.length === 0) return { headers: [], rows: [] }
    
    const parseCSVLine = (line) => {
      const result = []
      let current = ''
      let inQuotes = false
      for (let i = 0; i < line.length; i++) {
        const char = line[i]
        if (char === '"') {
          inQuotes = !inQuotes
        } else if (char === ',' && !inQuotes) {
          result.push(current.trim())
          current = ''
        } else {
          current += char
        }
      }
      result.push(current.trim())
      return result
    }
    
    const headers = parseCSVLine(lines[0])
    const rows = []
    for (let i = 1; i < lines.length; i++) {
      const values = parseCSVLine(lines[i])
      const row = {}
      headers.forEach((header, idx) => {
        row[header] = values[idx] || ''
      })
      rows.push(row)
    }
    return { headers, rows }
  }

  const handleCSVUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    
    setCsvFile(file)
    
    const text = await file.text()
    const { headers, rows } = parseCSVLocally(text)
    setCsvAllRows(rows)
    
    const formData = new FormData()
    formData.append('file', file)
    
    try {
      const response = await axios.post(`/api/csv/preview/${orgId}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      setCsvPreview({ ...response.data, row_count: rows.length })
      setCsvMapping(response.data.mapping || {})
    } catch (error) {
      console.error('Failed to preview CSV:', error)
      alert(error.response?.data?.detail || 'Failed to parse CSV file')
      setCsvFile(null)
      setCsvAllRows([])
    }
  }

  const handleCSVImport = async () => {
    if (!csvPreview || csvAllRows.length === 0) return
    
    if (!selectedCreatorId && !createNewCreatorForCSV) {
      alert('Please select a creator or create a new one')
      return
    }
    
    if (createNewCreatorForCSV && !newCreatorNameForCSV.trim()) {
      alert('Please enter a name for the new creator')
      return
    }
    
    setImporting(true)
    try {
      const response = await axios.post(`/api/csv/import/${orgId}`, {
        mapping: csvMapping,
        rows: csvAllRows,
        creator_id: selectedCreatorId ? parseInt(selectedCreatorId) : null,
        create_new_creator: createNewCreatorForCSV,
        new_creator_name: newCreatorNameForCSV
      })
      
      alert(`Successfully imported ${response.data.songs_created} songs`)
      setShowCSVModal(false)
      setCsvFile(null)
      setCsvPreview(null)
      setCsvMapping({})
      setCsvAllRows([])
      setSelectedCreatorId('')
      setCreateNewCreatorForCSV(false)
      setNewCreatorNameForCSV('')
      await loadData()
    } catch (error) {
      console.error('Failed to import CSV:', error)
      alert(error.response?.data?.detail || 'Failed to import CSV')
    } finally {
      setImporting(false)
    }
  }

  const FIELD_OPTIONS = [
    { value: null, label: '-- Skip --' },
    { value: 'title', label: 'Song Title' },
    { value: 'primary_artist', label: 'Primary Artist' },
    { value: 'isrc', label: 'ISRC' },
    { value: 'iswc', label: 'ISWC' },
    { value: 'project_title', label: 'Project/Album' },
    { value: 'release_date', label: 'Release Date' },
    { value: 'label', label: 'Label' },
    { value: 'publishing_percentage', label: 'Publishing %' },
    { value: 'master_percentage', label: 'Master %' },
    { value: 'advance_amount', label: 'Advance Amount' },
    { value: 'recording_code', label: 'Recording Code' },
    { value: 'notes', label: 'Notes' }
  ]
  
  if (loading) {
    return (
      <div className="min-h-screen bg-[#F5F7F4] flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-[#5B8A72] border-t-transparent"></div>
          <p className="mt-4 text-[#7A8580]">Loading roster...</p>
        </div>
      </div>
    )
  }
  
  return (
    <div className="min-h-screen bg-[#F5F7F4] p-6 lg:p-8">
      <div className="max-w-7xl mx-auto">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-8 gap-4">
          <div>
            <h1 className="text-[34px] font-semibold text-[#3D4A44] leading-tight">Roster</h1>
            <p className="text-[17px] text-[#7A8580] mt-1">Manage your creators and view their catalog performance</p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => setShowCSVModal(true)}
              className="flex items-center gap-2 px-4 py-2.5 bg-white border border-[rgba(59,77,67,0.2)] text-[#3D4A44] rounded-xl font-medium hover:bg-[#EEF1EC] transition-colors"
            >
              <ArrowUpTrayIcon className="w-5 h-5" />
              <span>Upload CSV</span>
            </button>
            <button
              onClick={() => setShowNewCreatorModal(true)}
              className="flex items-center gap-2 px-4 py-2.5 bg-[#5B8A72] text-white rounded-xl font-medium hover:bg-[#4A7862] transition-colors"
            >
              <UserPlusIcon className="w-5 h-5" />
              <span>Add Creator</span>
            </button>
          </div>
        </div>
        
        {creators.length === 0 ? (
          <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-12 text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[#EEF1EC] flex items-center justify-center">
              <svg className="w-8 h-8 text-[#7A8580]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
            </div>
            <p className="text-[#7A8580] mb-4 text-[17px]">No creators in your roster yet</p>
            <div className="flex justify-center gap-3">
              <button
                onClick={() => setShowCSVModal(true)}
                className="flex items-center gap-2 px-4 py-2.5 bg-white border border-[rgba(59,77,67,0.2)] text-[#3D4A44] rounded-xl font-medium hover:bg-[#EEF1EC] transition-colors"
              >
                <ArrowUpTrayIcon className="w-5 h-5" />
                Upload CSV
              </button>
              <button
                onClick={() => setShowNewCreatorModal(true)}
                className="flex items-center gap-2 px-4 py-2.5 bg-[#5B8A72] text-white rounded-xl font-medium hover:bg-[#4A7862] transition-colors"
              >
                <UserPlusIcon className="w-5 h-5" />
                Add Creator
              </button>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
            {creators.map((creator) => (
              <div key={creator.id} className="bg-white rounded-xl shadow-[0px_2px_8px_rgba(0,0,0,0.07)] hover:shadow-[0px_6px_16px_rgba(0,0,0,0.1)] transition-all duration-200 overflow-hidden group">
                <div className="aspect-square bg-gradient-to-br from-[#5B8A72] to-[#7BA594] relative overflow-hidden">
                  <Link to={`/roster/${creator.id}`} className="block w-full h-full">
                    {creator.hero_image_url ? (
                      <img 
                        src={`/api/creators/${creator.id}/image`} 
                        alt={creator.display_name}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <div className="text-white text-3xl font-bold opacity-90">
                          {creator.display_name.charAt(0).toUpperCase()}
                        </div>
                      </div>
                    )}
                  </Link>
                  <input
                    type="file"
                    accept="image/jpeg,image/png,image/webp,image/gif"
                    className="hidden"
                    id={`creator-image-${creator.id}`}
                    onChange={(e) => {
                      handleImageUpload(creator.id, e.target.files[0])
                      e.target.value = ''
                    }}
                  />
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      document.getElementById(`creator-image-${creator.id}`).click()
                    }}
                    className="absolute bottom-2 right-2 w-7 h-7 bg-white/90 backdrop-blur-sm rounded-full flex items-center justify-center shadow-md opacity-0 group-hover:opacity-100 transition-opacity duration-150 hover:bg-white z-10"
                    title="Upload photo"
                  >
                    {uploadingImageId === creator.id ? (
                      <div className="w-3.5 h-3.5 border-2 border-[#5B8A72] border-t-transparent rounded-full animate-spin"></div>
                    ) : (
                      <CameraIcon className="w-3.5 h-3.5 text-[#3D4A44]" />
                    )}
                  </button>
                </div>
                
                <Link to={`/roster/${creator.id}`} className="block p-3">
                  <h3 className="font-semibold text-[14px] text-[#3D4A44] mb-0.5 truncate">
                    {creator.display_name}
                  </h3>
                  <p className="text-[11px] text-[#7A8580] mb-2 truncate">
                    {Array.isArray(creator.roles) ? creator.roles.join(', ') : creator.roles}
                  </p>
                  
                  <div className="flex justify-between items-center">
                    <div>
                      <p className="text-[11px] text-[#7A8580]">Songs</p>
                      <p className="font-semibold text-[14px] text-[#3D4A44]">{creator.song_count}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-[11px] text-[#7A8580]">Health</p>
                      <p className={`font-semibold text-[14px] ${
                        creator.avg_health_score >= 80 ? 'text-[#5B9A6E]' :
                        creator.avg_health_score >= 60 ? 'text-[#C4956B]' :
                        'text-[#C47068]'
                      }`}>
                        {creator.avg_health_score?.toFixed(0) || 0}%
                      </p>
                    </div>
                  </div>
                </Link>
              </div>
            ))}
          </div>
        )}
      </div>

      {showNewCreatorModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-[18px] w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-[rgba(59,77,67,0.12)]">
              <div className="flex items-center justify-between">
                <h2 className="text-[22px] font-semibold text-[#3D4A44]">Add New Creator</h2>
                <button
                  onClick={() => setShowNewCreatorModal(false)}
                  className="p-2 hover:bg-[#EEF1EC] rounded-lg transition-colors"
                >
                  <XMarkIcon className="w-5 h-5 text-[#7A8580]" />
                </button>
              </div>
            </div>
            
            <form onSubmit={handleCreateCreator} className="p-6 space-y-4">
              <div>
                <label className="block text-[15px] font-medium text-[#3D4A44] mb-2">
                  Display Name <span className="text-[#C47068]">*</span>
                </label>
                <input
                  type="text"
                  value={newCreator.display_name}
                  onChange={(e) => setNewCreator({...newCreator, display_name: e.target.value})}
                  required
                  className="w-full px-4 py-3 border border-[rgba(59,77,67,0.2)] rounded-xl focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                  placeholder="Artist or creator name"
                />
              </div>

              <div>
                <label className="block text-[15px] font-medium text-[#3D4A44] mb-2">
                  Legal Name
                </label>
                <input
                  type="text"
                  value={newCreator.legal_name}
                  onChange={(e) => setNewCreator({...newCreator, legal_name: e.target.value})}
                  className="w-full px-4 py-3 border border-[rgba(59,77,67,0.2)] rounded-xl focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                  placeholder="Full legal name"
                />
              </div>

              <div>
                <label className="block text-[15px] font-medium text-[#3D4A44] mb-2">
                  Email
                </label>
                <input
                  type="email"
                  value={newCreator.email}
                  onChange={(e) => setNewCreator({...newCreator, email: e.target.value})}
                  className="w-full px-4 py-3 border border-[rgba(59,77,67,0.2)] rounded-xl focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                  placeholder="contact@example.com"
                />
              </div>

              <div>
                <label className="block text-[15px] font-medium text-[#3D4A44] mb-2">
                  Roles
                </label>
                <div className="flex flex-wrap gap-2">
                  {ROLE_OPTIONS.map(role => (
                    <button
                      key={role}
                      type="button"
                      onClick={() => handleRoleToggle(role)}
                      className={`px-4 py-2 rounded-lg text-[14px] font-medium transition-colors ${
                        newCreator.roles.includes(role)
                          ? 'bg-[#5B8A72] text-white'
                          : 'bg-[#EEF1EC] text-[#3D4A44] hover:bg-[#D8DDD6]'
                      }`}
                    >
                      {role}
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-[15px] font-medium text-[#3D4A44] mb-2">
                    Territory
                  </label>
                  <input
                    type="text"
                    value={newCreator.primary_territory}
                    onChange={(e) => setNewCreator({...newCreator, primary_territory: e.target.value})}
                    className="w-full px-4 py-3 border border-[rgba(59,77,67,0.2)] rounded-xl focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                    placeholder="e.g., US"
                  />
                </div>
                <div>
                  <label className="block text-[15px] font-medium text-[#3D4A44] mb-2">
                    PRO
                  </label>
                  <select
                    value={newCreator.primary_pro}
                    onChange={(e) => setNewCreator({...newCreator, primary_pro: e.target.value})}
                    className="w-full px-4 py-3 border border-[rgba(59,77,67,0.2)] rounded-xl focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white"
                  >
                    <option value="">Select PRO</option>
                    {PRO_OPTIONS.map(pro => (
                      <option key={pro} value={pro}>{pro}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-[15px] font-medium text-[#3D4A44] mb-2">
                  IPI Number
                </label>
                <input
                  type="text"
                  value={newCreator.primary_ipi}
                  onChange={(e) => setNewCreator({...newCreator, primary_ipi: e.target.value})}
                  className="w-full px-4 py-3 border border-[rgba(59,77,67,0.2)] rounded-xl focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                  placeholder="IPI/CAE number"
                />
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowNewCreatorModal(false)}
                  className="flex-1 px-4 py-3 border border-[rgba(59,77,67,0.2)] text-[#3D4A44] rounded-xl font-medium hover:bg-[#EEF1EC] transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating || !newCreator.display_name.trim()}
                  className="flex-1 px-4 py-3 bg-[#5B8A72] text-white rounded-xl font-medium hover:bg-[#4A7862] transition-colors disabled:opacity-50"
                >
                  {creating ? 'Creating...' : 'Create Creator'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showCSVModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-[18px] w-full max-w-3xl max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-[rgba(59,77,67,0.12)]">
              <div className="flex items-center justify-between">
                <h2 className="text-[22px] font-semibold text-[#3D4A44]">Upload Catalog CSV</h2>
                <button
                  onClick={() => {
                    setShowCSVModal(false)
                    setCsvFile(null)
                    setCsvPreview(null)
                    setCsvMapping({})
                    setCsvAllRows([])
                  }}
                  className="p-2 hover:bg-[#EEF1EC] rounded-lg transition-colors"
                >
                  <XMarkIcon className="w-5 h-5 text-[#7A8580]" />
                </button>
              </div>
              <p className="text-[15px] text-[#7A8580] mt-1">
                Upload a CSV file to bulk import songs. AI will automatically detect and map columns.
              </p>
            </div>
            
            <div className="p-6 space-y-6">
              {!csvFile ? (
                <div className="border-2 border-dashed border-[rgba(59,77,67,0.2)] rounded-xl p-8 text-center">
                  <ArrowUpTrayIcon className="w-12 h-12 text-[#7A8580] mx-auto mb-4" />
                  <p className="text-[15px] text-[#3D4A44] mb-2">Drop your CSV file here or click to browse</p>
                  <p className="text-[13px] text-[#7A8580] mb-4">Supports CSV files with headers</p>
                  <input
                    type="file"
                    accept=".csv"
                    onChange={handleCSVUpload}
                    className="hidden"
                    id="csv-upload"
                  />
                  <label
                    htmlFor="csv-upload"
                    className="inline-flex items-center gap-2 px-4 py-2.5 bg-[#5B8A72] text-white rounded-xl font-medium hover:bg-[#4A7862] transition-colors cursor-pointer"
                  >
                    <ArrowUpTrayIcon className="w-5 h-5" />
                    Select CSV File
                  </label>
                </div>
              ) : (
                <>
                  <div className="bg-[#EEF1EC] rounded-xl p-4 flex items-center justify-between">
                    <div>
                      <p className="text-[15px] font-medium text-[#3D4A44]">{csvFile.name}</p>
                      <p className="text-[13px] text-[#7A8580]">{csvPreview?.row_count || 0} rows detected</p>
                    </div>
                    <button
                      onClick={() => {
                        setCsvFile(null)
                        setCsvPreview(null)
                        setCsvMapping({})
                        setCsvAllRows([])
                      }}
                      className="p-2 hover:bg-[#D8DDD6] rounded-lg transition-colors"
                    >
                      <XMarkIcon className="w-5 h-5 text-[#7A8580]" />
                    </button>
                  </div>

                  {csvPreview && (
                    <>
                      <div>
                        <h3 className="text-[17px] font-medium text-[#3D4A44] mb-3">Column Mapping</h3>
                        <p className="text-[13px] text-[#7A8580] mb-4">
                          AI has suggested mappings below. Adjust if needed.
                        </p>
                        <div className="space-y-2 max-h-48 overflow-y-auto">
                          {csvPreview.headers.map(header => (
                            <div key={header} className="flex items-center gap-4 bg-[#FAFBF9] rounded-lg p-3">
                              <span className="text-[14px] text-[#3D4A44] font-medium w-1/3 truncate">{header}</span>
                              <span className="text-[#7A8580]">→</span>
                              <select
                                value={csvMapping[header] || ''}
                                onChange={(e) => setCsvMapping({
                                  ...csvMapping,
                                  [header]: e.target.value || null
                                })}
                                className="flex-1 px-3 py-2 border border-[rgba(59,77,67,0.2)] rounded-lg text-[14px] bg-white"
                              >
                                {FIELD_OPTIONS.map(opt => (
                                  <option key={opt.value || 'skip'} value={opt.value || ''}>
                                    {opt.label}
                                  </option>
                                ))}
                              </select>
                            </div>
                          ))}
                        </div>
                      </div>

                      <div>
                        <h3 className="text-[17px] font-medium text-[#3D4A44] mb-3">Assign to Creator</h3>
                        <div className="space-y-3">
                          <div className="flex items-center gap-3">
                            <input
                              type="radio"
                              id="existing-creator"
                              checked={!createNewCreatorForCSV}
                              onChange={() => setCreateNewCreatorForCSV(false)}
                              className="w-4 h-4 text-[#5B8A72]"
                            />
                            <label htmlFor="existing-creator" className="text-[15px] text-[#3D4A44]">
                              Select existing creator
                            </label>
                          </div>
                          {!createNewCreatorForCSV && (
                            <select
                              value={selectedCreatorId}
                              onChange={(e) => setSelectedCreatorId(e.target.value)}
                              className="w-full px-4 py-3 border border-[rgba(59,77,67,0.2)] rounded-xl bg-white"
                            >
                              <option value="">Select a creator...</option>
                              {creators.map(c => (
                                <option key={c.id} value={c.id}>{c.display_name}</option>
                              ))}
                            </select>
                          )}

                          <div className="flex items-center gap-3">
                            <input
                              type="radio"
                              id="new-creator"
                              checked={createNewCreatorForCSV}
                              onChange={() => setCreateNewCreatorForCSV(true)}
                              className="w-4 h-4 text-[#5B8A72]"
                            />
                            <label htmlFor="new-creator" className="text-[15px] text-[#3D4A44]">
                              Create new creator
                            </label>
                          </div>
                          {createNewCreatorForCSV && (
                            <input
                              type="text"
                              value={newCreatorNameForCSV}
                              onChange={(e) => setNewCreatorNameForCSV(e.target.value)}
                              className="w-full px-4 py-3 border border-[rgba(59,77,67,0.2)] rounded-xl"
                              placeholder="Enter creator name"
                            />
                          )}
                        </div>
                      </div>

                      <div className="flex gap-3 pt-4">
                        <button
                          onClick={() => {
                            setShowCSVModal(false)
                            setCsvFile(null)
                            setCsvPreview(null)
                            setCsvMapping({})
                            setCsvAllRows([])
                          }}
                          className="flex-1 px-4 py-3 border border-[rgba(59,77,67,0.2)] text-[#3D4A44] rounded-xl font-medium hover:bg-[#EEF1EC] transition-colors"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={handleCSVImport}
                          disabled={importing || (!selectedCreatorId && !createNewCreatorForCSV)}
                          className="flex-1 px-4 py-3 bg-[#5B8A72] text-white rounded-xl font-medium hover:bg-[#4A7862] transition-colors disabled:opacity-50"
                        >
                          {importing ? 'Importing...' : `Import ${csvPreview.row_count} Songs`}
                        </button>
                      </div>
                    </>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
