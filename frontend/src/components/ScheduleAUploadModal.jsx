import React, { useState, useEffect } from 'react'
import axios from 'axios'
import { XMarkIcon, ArrowUpTrayIcon, CheckCircleIcon, XCircleIcon, ArrowRightIcon, ArrowLeftIcon, SparklesIcon, DocumentTextIcon } from '@heroicons/react/24/outline'

const STANDARD_FIELDS = [
  { value: 'title', label: 'Song Title', required: true },
  { value: 'primary_artist', label: 'Artist Name', required: true },
  { value: 'isrc', label: 'ISRC' },
  { value: 'iswc', label: 'ISWC' },
  { value: 'project_title', label: 'Album/Project' },
  { value: 'release_date', label: 'Release Date' },
  { value: 'label', label: 'Label' },
  { value: 'publishing_percentage', label: 'Publishing %' },
  { value: 'master_percentage', label: 'Master %' },
  { value: 'advance_amount', label: 'Advance ($)' },
  { value: 'recording_code', label: 'Recording Code' },
  { value: 'notes', label: 'Notes' },
]

const isDocumentFile = (filename) => {
  const lower = (filename || '').toLowerCase()
  return lower.endsWith('.pdf') || lower.endsWith('.docx') || lower.endsWith('.doc')
}

export default function ScheduleAUploadModal({ onClose, onSuccess, organizationId, creators = [] }) {
  const [step, setStep] = useState(1)
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [importing, setImporting] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [dragActive, setDragActive] = useState(false)
  
  const [previewData, setPreviewData] = useState(null)
  const [mapping, setMapping] = useState({})
  const [previewRows, setPreviewRows] = useState([])
  const [allRows, setAllRows] = useState([])
  const [totalRows, setTotalRows] = useState(0)
  const [isDocImport, setIsDocImport] = useState(false)
  const [documentInfo, setDocumentInfo] = useState(null)
  
  const [selectedCreatorId, setSelectedCreatorId] = useState('')
  const [createNewCreator, setCreateNewCreator] = useState(false)
  const [newCreatorName, setNewCreatorName] = useState('')
  const [creatorList, setCreatorList] = useState(creators)
  
  useEffect(() => {
    if (creators.length === 0 && organizationId) {
      loadCreators()
    }
  }, [organizationId])
  
  const loadCreators = async () => {
    try {
      const token = localStorage.getItem('token')
      const response = await axios.get(`/api/creators/org/${organizationId}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setCreatorList(response.data)
    } catch (err) {
      console.error('Failed to load creators:', err)
    }
  }
  
  const handleDrag = (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true)
    } else if (e.type === "dragleave") {
      setDragActive(false)
    }
  }
  
  const handleDrop = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0])
      setError(null)
      setResult(null)
    }
  }
  
  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
      setError(null)
      setResult(null)
    }
  }
  
  const analyzeFile = async () => {
    if (!file) return
    
    setAnalyzing(true)
    setError(null)
    
    try {
      const token = localStorage.getItem('token')
      const formData = new FormData()
      formData.append('file', file)
      
      const isDoc = isDocumentFile(file.name)
      const endpoint = isDoc 
        ? `/api/csv/document-preview/${organizationId}`
        : `/api/csv/preview/${organizationId}?all_rows=true`
      
      const response = await axios.post(
        endpoint,
        formData,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          }
        }
      )
      
      setPreviewData(response.data)
      setMapping(response.data.mapping || {})
      const allRowsData = response.data.preview_rows || []
      setAllRows(allRowsData)
      setPreviewRows(allRowsData.slice(0, 5))
      setTotalRows(response.data.row_count || 0)
      
      if (isDoc && response.data.is_document_import) {
        setIsDocImport(true)
        setDocumentInfo(response.data.document_info || null)
        if (response.data.document_info?.creator_name) {
          const matchingCreator = creatorList.find(
            c => c.display_name.toLowerCase() === response.data.document_info.creator_name.toLowerCase()
          )
          if (matchingCreator) {
            setSelectedCreatorId(String(matchingCreator.id))
            setCreateNewCreator(false)
          } else {
            setCreateNewCreator(true)
            setNewCreatorName(response.data.document_info.creator_name)
          }
        }
        setStep(2)
      } else {
        setIsDocImport(false)
        setDocumentInfo(null)
        setStep(2)
      }
    } catch (err) {
      console.error('Analysis failed:', err)
      setError(err.response?.data?.detail || 'Failed to analyze file. Please check the format.')
    } finally {
      setAnalyzing(false)
    }
  }
  
  const handleMappingChange = (csvHeader, newValue) => {
    setMapping(prev => ({
      ...prev,
      [csvHeader]: newValue || null
    }))
  }
  
  const getMappedFieldsCount = () => {
    return Object.values(mapping).filter(v => v).length
  }
  
  const hasRequiredMappings = () => {
    const mappedValues = Object.values(mapping)
    return mappedValues.includes('title')
  }
  
  const handleImport = async () => {
    if (!isDocImport && !hasRequiredMappings()) {
      setError('Song Title mapping is required')
      return
    }
    
    if (!createNewCreator && !selectedCreatorId) {
      setError('Please select a creator or choose to create a new one')
      return
    }
    
    if (createNewCreator && !newCreatorName.trim()) {
      setError('Please enter a name for the new creator')
      return
    }
    
    setImporting(true)
    setError(null)
    
    try {
      const token = localStorage.getItem('token')
      
      let importMapping = mapping
      let importRows = allRows.length > 0 ? allRows : previewRows
      
      if (isDocImport) {
        importMapping = {
          title: 'title',
          primary_artist: 'primary_artist',
          publishing_percentage: 'publishing_percentage',
          notes: 'notes',
        }
        importRows = importRows.map(row => ({
          title: row.title || '',
          primary_artist: row.primary_artist || '',
          publishing_percentage: row.publishing_percentage || '',
          notes: row.notes || '',
        }))
      }
      
      const response = await axios.post(
        `/api/csv/import/${organizationId}`,
        {
          mapping: importMapping,
          rows: importRows,
          creator_id: createNewCreator ? null : parseInt(selectedCreatorId),
          create_new_creator: createNewCreator,
          new_creator_name: createNewCreator ? newCreatorName.trim() : null
        },
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      )
      
      setResult(response.data)
      setStep(4)
      
      setTimeout(() => {
        onSuccess()
        onClose()
      }, 2500)
    } catch (err) {
      console.error('Import failed:', err)
      setError(err.response?.data?.detail || 'Failed to import songs. Please try again.')
    } finally {
      setImporting(false)
    }
  }
  
  const isValidFile = file && (
    file.name.endsWith('.csv') ||
    file.name.endsWith('.xlsx') ||
    file.name.endsWith('.xls') ||
    file.name.endsWith('.pdf') ||
    file.name.endsWith('.docx') ||
    file.name.endsWith('.doc')
  )
  
  const getAvailableFields = (currentHeader) => {
    const usedValues = Object.entries(mapping)
      .filter(([header, _]) => header !== currentHeader)
      .map(([_, value]) => value)
      .filter(Boolean)
    
    return STANDARD_FIELDS.filter(field => !usedValues.includes(field.value))
  }
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div 
        className="bg-[#FAFBF9] rounded-xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-6 border-b border-[rgba(59,77,67,0.08)] bg-gradient-to-r from-[rgba(91,138,114,0.08)] to-[rgba(123,165,148,0.08)]">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-[#3D4A44]">Import Catalog</h2>
              <p className="text-sm text-[#7A8580] mt-1">
                {step === 1 && 'Upload your CSV, Excel, PDF, or Word file'}
                {step === 2 && (isDocImport ? 'Review parsed songs from document' : 'Review AI-suggested column mapping')}
                {step === 3 && 'Select creator for imported songs'}
                {step === 4 && 'Import complete!'}
              </p>
            </div>
            <button
              onClick={onClose}
              className="text-[#7A8580] hover:text-[#3D4A44] transition-colors"
            >
              <XMarkIcon className="w-6 h-6" />
            </button>
          </div>
          
          <div className="flex items-center mt-4 space-x-2">
            {[1, 2, 3, 4].map((s) => (
              <React.Fragment key={s}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors ${
                  s < step ? 'bg-[#5B9A6E] text-white' :
                  s === step ? 'bg-[#5B8A72] text-white' :
                  'bg-[rgba(59,77,67,0.1)] text-[#7A8580]'
                }`}>
                  {s < step ? <CheckCircleIcon className="w-5 h-5" /> : s}
                </div>
                {s < 4 && <div className={`flex-1 h-0.5 ${s < step ? 'bg-[#5B9A6E]' : 'bg-[rgba(59,77,67,0.1)]'}`} />}
              </React.Fragment>
            ))}
          </div>
        </div>
        
        <div className="flex-1 overflow-y-auto p-6">
          {step === 1 && (
            <>
              <div
                className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                  dragActive
                    ? 'border-[#5B8A72] bg-[rgba(91,138,114,0.08)]'
                    : file
                    ? 'border-[#5B9A6E] bg-[rgba(91,154,110,0.08)]'
                    : 'border-[rgba(59,77,67,0.2)] hover:border-[rgba(59,77,67,0.3)]'
                }`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
              >
                {file ? (
                  <div className="space-y-2">
                    <CheckCircleIcon className="w-12 h-12 mx-auto text-[#5B9A6E]" />
                    <p className="text-lg font-medium text-[#3D4A44]">{file.name}</p>
                    <p className="text-sm text-[#7A8580]">
                      {(file.size / 1024).toFixed(2)} KB
                    </p>
                    <button
                      onClick={() => setFile(null)}
                      className="text-sm text-[#5B8A72] hover:text-[#7BA594]"
                    >
                      Choose different file
                    </button>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <ArrowUpTrayIcon className="w-12 h-12 mx-auto text-[#7A8580]" />
                    <p className="text-lg font-medium text-[#3D4A44]">
                      Drag and drop your file here
                    </p>
                    <p className="text-sm text-[#7A8580]">or</p>
                    <label className="inline-block">
                      <input
                        type="file"
                        className="hidden"
                        accept=".csv,.xlsx,.xls,.pdf,.docx,.doc"
                        onChange={handleFileChange}
                      />
                      <span className="px-4 py-2 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] cursor-pointer inline-block transition-colors">
                        Browse Files
                      </span>
                    </label>
                    <p className="text-xs text-[#7A8580] mt-2">
                      Supported formats: CSV, Excel (.xlsx, .xls), PDF, Word (.docx)
                    </p>
                  </div>
                )}
              </div>
              
              {error && (
                <div className="mt-4 p-4 bg-[rgba(196,112,104,0.08)] border border-[rgba(196,112,104,0.2)] rounded-lg flex items-start space-x-3">
                  <XCircleIcon className="w-5 h-5 text-[#C47068] flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-[#A45850]">{error}</p>
                </div>
              )}
              
              <div className="mt-6 p-4 bg-[rgba(90,138,154,0.08)] border border-[rgba(90,138,154,0.15)] rounded-lg">
                <div className="flex items-center gap-2 mb-3">
                  <SparklesIcon className="w-5 h-5 text-[#5B8A72]" />
                  <h3 className="text-sm font-semibold text-[#4A7A8A]">Smart Import</h3>
                </div>
                <p className="text-xs text-[#5A8A9A] mb-3">
                  Upload spreadsheets or documents and we'll automatically parse your catalog data.
                </p>
                <div className="text-xs text-[#5A8A9A] space-y-1">
                  <p><strong>CSV/Excel:</strong> AI auto-maps your columns (Title, Artist, %, etc.)</p>
                  <p><strong>PDF/Word:</strong> Parses Schedule A documents with "Artist - Song Title XX%" format</p>
                  <p>Creator info (name, PRO IPI#) is auto-detected from document headers</p>
                </div>
              </div>
            </>
          )}
          
          {step === 2 && previewData && isDocImport && (
            <>
              {documentInfo && (
                <div className="mb-4 p-4 bg-[rgba(91,138,114,0.08)] border border-[rgba(91,138,114,0.15)] rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <DocumentTextIcon className="w-5 h-5 text-[#5B8A72]" />
                    <span className="text-sm font-semibold text-[#3D4A44]">Document Info Detected</span>
                  </div>
                  <div className="text-sm text-[#5A7A6A] space-y-1">
                    {documentInfo.creator_name && <p><strong>Creator:</strong> {documentInfo.creator_name}</p>}
                    {documentInfo.pro_name && documentInfo.bmi_ipi && (
                      <p><strong>{documentInfo.pro_name} IPI#:</strong> {documentInfo.bmi_ipi}</p>
                    )}
                    {documentInfo.bmi_id && <p><strong>ID#:</strong> {documentInfo.bmi_id}</p>}
                  </div>
                </div>
              )}
              
              {previewData.warnings?.length > 0 && (
                <div className="mb-3 space-y-1">
                  {previewData.warnings.map((w, i) => (
                    <p key={i} className="text-xs text-[#5A8A6A]">{w}</p>
                  ))}
                </div>
              )}

              <div className="mb-4 flex items-center justify-between">
                <span className="text-sm font-medium text-[#3D4A44]">
                  {totalRows} songs parsed from document
                </span>
                <span className="text-xs text-[#7A8580]">
                  {allRows.filter(r => r.section === 'Schedule A').length} released, {allRows.filter(r => r.section !== 'Schedule A').length} pipeline
                </span>
              </div>
              
              <div className="border border-[rgba(59,77,67,0.1)] rounded-lg overflow-hidden">
                <div className="overflow-x-auto max-h-[340px] overflow-y-auto">
                  <table className="w-full text-xs">
                    <thead className="bg-[rgba(59,77,67,0.03)] sticky top-0">
                      <tr>
                        <th className="px-3 py-2 text-left font-medium text-[#5B8A72]">Artist</th>
                        <th className="px-3 py-2 text-left font-medium text-[#5B8A72]">Song Title</th>
                        <th className="px-3 py-2 text-center font-medium text-[#5B8A72]">Pub %</th>
                        <th className="px-3 py-2 text-left font-medium text-[#5B8A72]">Section</th>
                        <th className="px-3 py-2 text-left font-medium text-[#5B8A72]">Notes</th>
                      </tr>
                    </thead>
                    <tbody>
                      {allRows.map((row, idx) => (
                        <tr key={idx} className={`border-t border-[rgba(59,77,67,0.05)] ${row.section !== 'Schedule A' ? 'bg-[rgba(196,149,107,0.05)]' : ''}`}>
                          <td className="px-3 py-2 text-[#3D4A44]">{row.primary_artist || '-'}</td>
                          <td className="px-3 py-2 text-[#3D4A44] font-medium">{row.title || '-'}</td>
                          <td className="px-3 py-2 text-center text-[#3D4A44]">{row.publishing_percentage ? `${row.publishing_percentage}%` : '-'}</td>
                          <td className="px-3 py-2">
                            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium ${
                              row.section === 'Schedule A' 
                                ? 'bg-[rgba(91,154,110,0.15)] text-[#4A8A5A]' 
                                : 'bg-[rgba(196,149,107,0.15)] text-[#8A6B4A]'
                            }`}>
                              {row.section === 'Schedule A' ? 'Released' : 'Pipeline'}
                            </span>
                          </td>
                          <td className="px-3 py-2 text-[#7A8580] text-[11px]">{row.notes || ''}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
              
              {error && (
                <div className="mt-4 p-4 bg-[rgba(196,112,104,0.08)] border border-[rgba(196,112,104,0.2)] rounded-lg flex items-start space-x-3">
                  <XCircleIcon className="w-5 h-5 text-[#C47068] flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-[#A45850]">{error}</p>
                </div>
              )}
            </>
          )}
          
          {step === 2 && previewData && !isDocImport && (
            <>
              <div className="mb-4 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <SparklesIcon className="w-5 h-5 text-[#5B8A72]" />
                  <span className="text-sm font-medium text-[#3D4A44]">
                    AI Mapped {getMappedFieldsCount()} of {previewData.headers?.length || 0} columns
                  </span>
                </div>
                <span className="text-sm text-[#7A8580]">{totalRows} rows found</span>
              </div>
              
              {!previewData.success && previewData.error && (
                <div className="mb-4 p-3 bg-[rgba(196,149,107,0.1)] border border-[rgba(196,149,107,0.3)] rounded-lg">
                  <p className="text-sm text-[#8A6B4A]">
                    AI mapping encountered an issue. Please map columns manually.
                  </p>
                </div>
              )}
              
              <div className="space-y-3 mb-6">
                {previewData.headers?.map((header) => (
                  <div key={header} className="flex items-center gap-3 p-3 bg-white border border-[rgba(59,77,67,0.1)] rounded-lg">
                    <div className="flex-1">
                      <p className="text-sm font-medium text-[#3D4A44]">{header}</p>
                      {previewRows[0] && (
                        <p className="text-xs text-[#7A8580] truncate">
                          e.g., "{previewRows[0][header] || '(empty)'}"
                        </p>
                      )}
                    </div>
                    <ArrowRightIcon className="w-4 h-4 text-[#7A8580]" />
                    <div className="w-48">
                      <select
                        value={mapping[header] || ''}
                        onChange={(e) => handleMappingChange(header, e.target.value)}
                        className={`w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent ${
                          mapping[header] 
                            ? 'border-[#5B8A72] bg-[rgba(91,138,114,0.05)]' 
                            : 'border-[rgba(59,77,67,0.2)]'
                        }`}
                      >
                        <option value="">Don't import</option>
                        {getAvailableFields(header).map((field) => (
                          <option key={field.value} value={field.value}>
                            {field.label} {field.required ? '*' : ''}
                          </option>
                        ))}
                        {mapping[header] && !getAvailableFields(header).find(f => f.value === mapping[header]) && (
                          <option value={mapping[header]}>
                            {STANDARD_FIELDS.find(f => f.value === mapping[header])?.label || mapping[header]}
                          </option>
                        )}
                      </select>
                    </div>
                  </div>
                ))}
              </div>
              
              {previewRows.length > 0 && (
                <div className="border border-[rgba(59,77,67,0.1)] rounded-lg overflow-hidden">
                  <div className="bg-[rgba(59,77,67,0.03)] px-4 py-2 border-b border-[rgba(59,77,67,0.1)]">
                    <p className="text-sm font-medium text-[#3D4A44]">Preview (first {Math.min(5, previewRows.length)} rows)</p>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead className="bg-[rgba(59,77,67,0.02)]">
                        <tr>
                          {previewData.headers?.filter(h => mapping[h]).map((header) => (
                            <th key={header} className="px-3 py-2 text-left font-medium text-[#5B8A72]">
                              {STANDARD_FIELDS.find(f => f.value === mapping[header])?.label || mapping[header]}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {previewRows.slice(0, 5).map((row, idx) => (
                          <tr key={idx} className="border-t border-[rgba(59,77,67,0.05)]">
                            {previewData.headers?.filter(h => mapping[h]).map((header) => (
                              <td key={header} className="px-3 py-2 text-[#3D4A44] truncate max-w-[150px]">
                                {row[header] || '-'}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
              
              {error && (
                <div className="mt-4 p-4 bg-[rgba(196,112,104,0.08)] border border-[rgba(196,112,104,0.2)] rounded-lg flex items-start space-x-3">
                  <XCircleIcon className="w-5 h-5 text-[#C47068] flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-[#A45850]">{error}</p>
                </div>
              )}
            </>
          )}
          
          {step === 3 && (
            <>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-2">
                    Who should these songs be credited to?
                  </label>
                  
                  <div className="space-y-3">
                    <label className={`flex items-center p-4 border rounded-lg cursor-pointer transition-colors ${
                      !createNewCreator 
                        ? 'border-[#5B8A72] bg-[rgba(91,138,114,0.05)]' 
                        : 'border-[rgba(59,77,67,0.2)] hover:bg-[rgba(59,77,67,0.02)]'
                    }`}>
                      <input
                        type="radio"
                        name="creatorOption"
                        checked={!createNewCreator}
                        onChange={() => setCreateNewCreator(false)}
                        className="sr-only"
                      />
                      <div className={`w-5 h-5 rounded-full border-2 mr-3 flex items-center justify-center ${
                        !createNewCreator ? 'border-[#5B8A72]' : 'border-[rgba(59,77,67,0.3)]'
                      }`}>
                        {!createNewCreator && <div className="w-2.5 h-2.5 rounded-full bg-[#5B8A72]" />}
                      </div>
                      <div className="flex-1">
                        <span className="text-sm font-medium text-[#3D4A44]">Existing Creator</span>
                        {!createNewCreator && (
                          <select
                            value={selectedCreatorId}
                            onChange={(e) => setSelectedCreatorId(e.target.value)}
                            className="mt-2 w-full px-3 py-2 text-sm border border-[rgba(59,77,67,0.2)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <option value="">Select a creator...</option>
                            {creatorList.map((c) => (
                              <option key={c.id} value={c.id}>{c.display_name}</option>
                            ))}
                          </select>
                        )}
                      </div>
                    </label>
                    
                    <label className={`flex items-center p-4 border rounded-lg cursor-pointer transition-colors ${
                      createNewCreator 
                        ? 'border-[#5B8A72] bg-[rgba(91,138,114,0.05)]' 
                        : 'border-[rgba(59,77,67,0.2)] hover:bg-[rgba(59,77,67,0.02)]'
                    }`}>
                      <input
                        type="radio"
                        name="creatorOption"
                        checked={createNewCreator}
                        onChange={() => setCreateNewCreator(true)}
                        className="sr-only"
                      />
                      <div className={`w-5 h-5 rounded-full border-2 mr-3 flex items-center justify-center ${
                        createNewCreator ? 'border-[#5B8A72]' : 'border-[rgba(59,77,67,0.3)]'
                      }`}>
                        {createNewCreator && <div className="w-2.5 h-2.5 rounded-full bg-[#5B8A72]" />}
                      </div>
                      <div className="flex-1">
                        <span className="text-sm font-medium text-[#3D4A44]">Create New Creator</span>
                        {createNewCreator && (
                          <input
                            type="text"
                            value={newCreatorName}
                            onChange={(e) => setNewCreatorName(e.target.value)}
                            placeholder="Enter creator name..."
                            className="mt-2 w-full px-3 py-2 text-sm border border-[rgba(59,77,67,0.2)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                            onClick={(e) => e.stopPropagation()}
                          />
                        )}
                      </div>
                    </label>
                  </div>
                </div>
                
                <div className="p-4 bg-[rgba(90,138,154,0.08)] border border-[rgba(90,138,154,0.15)] rounded-lg">
                  <p className="text-sm text-[#5A8A9A]">
                    <strong>{totalRows}</strong> songs will be imported and credited to the selected creator.
                    Fields not mapped will be left blank.
                  </p>
                </div>
              </div>
              
              {error && (
                <div className="mt-4 p-4 bg-[rgba(196,112,104,0.08)] border border-[rgba(196,112,104,0.2)] rounded-lg flex items-start space-x-3">
                  <XCircleIcon className="w-5 h-5 text-[#C47068] flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-[#A45850]">{error}</p>
                </div>
              )}
            </>
          )}
          
          {step === 4 && result && (
            <div className="space-y-4 text-center py-8">
              <CheckCircleIcon className="w-16 h-16 mx-auto text-[#5B9A6E]" />
              <div>
                <h3 className="text-xl font-bold text-[#3D4A44] mb-2">Import Successful!</h3>
                <div className="space-y-2 text-sm text-[#7A8580]">
                  <p><strong className="text-[#5B9A6E]">{result.songs_created}</strong> songs created</p>
                  {result.songs_failed > 0 && (
                    <p><strong className="text-[#C4956B]">{result.songs_failed}</strong> songs failed</p>
                  )}
                </div>
                {result.errors && result.errors.length > 0 && (
                  <div className="mt-4 p-3 bg-[rgba(196,149,107,0.1)] border border-[rgba(196,149,107,0.2)] rounded-lg text-left max-h-32 overflow-y-auto">
                    <p className="text-sm font-semibold text-[#8A6B4A] mb-1">Issues:</p>
                    <ul className="text-xs text-[#8A6B4A] list-disc list-inside space-y-1">
                      {result.errors.slice(0, 5).map((err, idx) => (
                        <li key={idx}>{err}</li>
                      ))}
                      {result.errors.length > 5 && (
                        <li>...and {result.errors.length - 5} more</li>
                      )}
                    </ul>
                  </div>
                )}
                <p className="text-sm text-[#7A8580] mt-4">Refreshing catalog...</p>
              </div>
            </div>
          )}
        </div>
        
        <div className="flex justify-between items-center p-6 border-t border-[rgba(59,77,67,0.08)]">
          <div>
            {step > 1 && step < 4 && (
              <button
                onClick={() => setStep(step - 1)}
                className="flex items-center gap-2 px-4 py-2 text-[#5B8A72] hover:text-[#4A7A62] transition-colors"
              >
                <ArrowLeftIcon className="w-4 h-4" />
                Back
              </button>
            )}
          </div>
          
          <div className="flex gap-3">
            {step < 4 && (
              <button
                onClick={onClose}
                className="px-6 py-2 border border-[rgba(59,77,67,0.2)] rounded-lg text-[#3D4A44] hover:bg-[#EEF1EC] transition-colors"
              >
                Cancel
              </button>
            )}
            
            {step === 1 && (
              <button
                onClick={analyzeFile}
                disabled={!isValidFile || analyzing}
                className="flex items-center gap-2 px-6 py-2 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-lg hover:shadow-[0px_4px_12px_rgba(91,138,114,0.3)] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {analyzing ? (
                  <>
                    <SparklesIcon className="w-4 h-4 animate-pulse" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    Analyze File
                    <ArrowRightIcon className="w-4 h-4" />
                  </>
                )}
              </button>
            )}
            
            {step === 2 && (
              <button
                onClick={() => {
                  if (isDocImport || hasRequiredMappings()) {
                    setError(null)
                    setStep(3)
                  } else {
                    setError('Please map at least the Song Title column')
                  }
                }}
                disabled={!isDocImport && !hasRequiredMappings()}
                className="flex items-center gap-2 px-6 py-2 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-lg hover:shadow-[0px_4px_12px_rgba(91,138,114,0.3)] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Continue
                <ArrowRightIcon className="w-4 h-4" />
              </button>
            )}
            
            {step === 3 && (
              <button
                onClick={handleImport}
                disabled={importing || (!createNewCreator && !selectedCreatorId) || (createNewCreator && !newCreatorName.trim())}
                className="flex items-center gap-2 px-6 py-2 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-lg hover:shadow-[0px_4px_12px_rgba(91,138,114,0.3)] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {importing ? 'Importing...' : `Import ${totalRows} Songs`}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
