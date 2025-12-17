import React, { useState } from 'react'
import axios from 'axios'
import { XMarkIcon, ArrowUpTrayIcon, CheckCircleIcon, XCircleIcon } from '@heroicons/react/24/outline'

export default function ScheduleAUploadModal({ onClose, onSuccess, organizationId }) {
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [dragActive, setDragActive] = useState(false)
  
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
  
  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file to upload')
      return
    }
    
    setUploading(true)
    setError(null)
    setResult(null)
    
    try {
      const token = localStorage.getItem('token')
      const formData = new FormData()
      formData.append('file', file)
      
      const response = await axios.post(
        `/api/schedule-a/upload/${organizationId}`,
        formData,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          }
        }
      )
      
      setResult(response.data)
      
      setTimeout(() => {
        onSuccess()
        onClose()
      }, 2000)
    } catch (err) {
      console.error('Upload failed:', err)
      setError(err.response?.data?.detail || 'Failed to upload file. Please try again.')
    } finally {
      setUploading(false)
    }
  }
  
  const isValidFile = file && (
    file.name.endsWith('.csv') ||
    file.name.endsWith('.xlsx') ||
    file.name.endsWith('.xls')
  )
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div 
        className="bg-[#FAFBF9] rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-6 border-b border-[rgba(59,77,67,0.08)] bg-gradient-to-r from-[rgba(91,138,114,0.08)] to-[rgba(123,165,148,0.08)]">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-[#3D4A44]">Upload Schedule A</h2>
              <p className="text-sm text-[#7A8580] mt-1">Import songs from CSV or Excel file</p>
            </div>
            <button
              onClick={onClose}
              className="text-[#7A8580] hover:text-[#3D4A44] transition-colors"
            >
              <XMarkIcon className="w-6 h-6" />
            </button>
          </div>
        </div>
        
        <div className="flex-1 overflow-y-auto p-6">
          {!result && (
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
                        accept=".csv,.xlsx,.xls"
                        onChange={handleFileChange}
                      />
                      <span className="px-4 py-2 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] cursor-pointer inline-block transition-colors">
                        Browse Files
                      </span>
                    </label>
                    <p className="text-xs text-[#7A8580] mt-2">
                      Supported formats: CSV, Excel (.xlsx, .xls)
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
                <h3 className="text-sm font-semibold text-[#4A7A8A] mb-2">File Naming</h3>
                <p className="text-xs text-[#5A8A9A] mb-3">
                  Name your file: <strong>CREATOR NAME - Placement Sheet.xlsx</strong><br/>
                  Example: "JACK LOMASTRO - Placement Status Sheet.xlsx"
                </p>
                <h3 className="text-sm font-semibold text-[#4A7A8A] mb-2">Expected Columns</h3>
                <div className="text-xs text-[#5A8A9A] space-y-1">
                  <p><strong>Required:</strong> Song Title, Artist Name</p>
                  <p><strong>Financial:</strong> Publishing %, Royalty/Master %, Advance ($)</p>
                  <p><strong>Status:</strong> Credited, Received Paperwork, Agreement, BMI Registration, Kobalt Reg, SoundExchange, Payment Received, Invoice Sent</p>
                  <p><strong>Details:</strong> Label, Date Released, Notes</p>
                </div>
                <p className="text-xs text-[#5A8A9A] mt-3">
                  The system will create the creator if they don't exist, then import all songs and link them to that creator.
                </p>
              </div>
            </>
          )}
          
          {result && (
            <div className="space-y-4">
              <div className="flex items-center justify-center">
                <CheckCircleIcon className="w-16 h-16 text-[#5B9A6E]" />
              </div>
              <div className="text-center">
                <h3 className="text-xl font-bold text-[#3D4A44] mb-2">Upload Successful!</h3>
                {result.creator_name && (
                  <p className="text-[#5B8A72] font-medium mb-3">
                    Creator: {result.creator_name}
                  </p>
                )}
                <div className="space-y-2 text-sm text-[#7A8580]">
                  <p><strong className="text-[#5B9A6E]">{result.songs_created}</strong> songs created</p>
                  <p><strong className="text-[#5A8A9A]">{result.songs_updated}</strong> songs updated</p>
                  {result.songs_skipped > 0 && (
                    <p><strong className="text-[#C4956B]">{result.songs_skipped}</strong> songs skipped</p>
                  )}
                  {result.credits_created > 0 && (
                    <p><strong className="text-[#5B8A72]">{result.credits_created}</strong> credits linked</p>
                  )}
                </div>
                {result.warnings && result.warnings.length > 0 && (
                  <div className="mt-4 p-3 bg-[rgba(90,138,154,0.08)] border border-[rgba(90,138,154,0.15)] rounded-lg text-left">
                    <p className="text-sm font-semibold text-[#4A7A8A] mb-1">Notes:</p>
                    <ul className="text-xs text-[#5A8A9A] list-disc list-inside space-y-1">
                      {result.warnings.map((warn, idx) => (
                        <li key={idx}>{warn}</li>
                      ))}
                    </ul>
                  </div>
                )}
                <p className="text-sm text-[#7A8580] mt-4">Refreshing catalog...</p>
              </div>
            </div>
          )}
        </div>
        
        {!result && (
          <div className="flex justify-end space-x-3 p-6 border-t border-[rgba(59,77,67,0.08)]">
            <button
              onClick={onClose}
              className="px-6 py-2 border border-[rgba(59,77,67,0.2)] rounded-lg text-[#3D4A44] hover:bg-[#EEF1EC] transition-colors"
              disabled={uploading}
            >
              Cancel
            </button>
            <button
              onClick={handleUpload}
              disabled={!isValidFile || uploading}
              className="px-6 py-2 bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white rounded-lg hover:shadow-[0px_4px_12px_rgba(91,138,114,0.3)] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {uploading ? 'Uploading...' : 'Upload File'}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
