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
      
      // Wait 2 seconds then close and refresh
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
        className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-6 border-b border-gray-200 bg-gradient-to-r from-purple-50 to-pink-50">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">Upload Schedule A</h2>
              <p className="text-sm text-gray-600 mt-1">Import songs from CSV or Excel file</p>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <XMarkIcon className="w-6 h-6" />
            </button>
          </div>
        </div>
        
        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {!result && (
            <>
              {/* File Upload Area */}
              <div
                className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                  dragActive
                    ? 'border-purple-500 bg-purple-50'
                    : file
                    ? 'border-green-500 bg-green-50'
                    : 'border-gray-300 hover:border-gray-400'
                }`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
              >
                {file ? (
                  <div className="space-y-2">
                    <CheckCircleIcon className="w-12 h-12 mx-auto text-green-500" />
                    <p className="text-lg font-medium text-gray-900">{file.name}</p>
                    <p className="text-sm text-gray-500">
                      {(file.size / 1024).toFixed(2)} KB
                    </p>
                    <button
                      onClick={() => setFile(null)}
                      className="text-sm text-purple-600 hover:text-purple-700"
                    >
                      Choose different file
                    </button>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <ArrowUpTrayIcon className="w-12 h-12 mx-auto text-gray-400" />
                    <p className="text-lg font-medium text-gray-900">
                      Drag and drop your file here
                    </p>
                    <p className="text-sm text-gray-500">or</p>
                    <label className="inline-block">
                      <input
                        type="file"
                        className="hidden"
                        accept=".csv,.xlsx,.xls"
                        onChange={handleFileChange}
                      />
                      <span className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 cursor-pointer inline-block transition-colors">
                        Browse Files
                      </span>
                    </label>
                    <p className="text-xs text-gray-400 mt-2">
                      Supported formats: CSV, Excel (.xlsx, .xls)
                    </p>
                  </div>
                )}
              </div>
              
              {error && (
                <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start space-x-3">
                  <XCircleIcon className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              )}
              
              {/* File Format Guide */}
              <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <h3 className="text-sm font-semibold text-blue-900 mb-2">File Naming</h3>
                <p className="text-xs text-blue-800 mb-3">
                  Name your file: <strong>CREATOR NAME - Placement Sheet.xlsx</strong><br/>
                  Example: "JACK LOMASTRO - Placement Status Sheet.xlsx"
                </p>
                <h3 className="text-sm font-semibold text-blue-900 mb-2">Expected Columns</h3>
                <div className="text-xs text-blue-800 space-y-1">
                  <p><strong>Required:</strong> Song Title, Artist Name</p>
                  <p><strong>Financial:</strong> Publishing %, Royalty/Master %, Advance ($)</p>
                  <p><strong>Status:</strong> Credited, Received Paperwork, Agreement, BMI Registration, Kobalt Reg, SoundExchange, Payment Received, Invoice Sent</p>
                  <p><strong>Details:</strong> Label, Date Released, Notes</p>
                </div>
                <p className="text-xs text-blue-700 mt-3">
                  The system will create the creator if they don't exist, then import all songs and link them to that creator.
                </p>
              </div>
            </>
          )}
          
          {/* Success Result */}
          {result && (
            <div className="space-y-4">
              <div className="flex items-center justify-center">
                <CheckCircleIcon className="w-16 h-16 text-green-500" />
              </div>
              <div className="text-center">
                <h3 className="text-xl font-bold text-gray-900 mb-2">Upload Successful!</h3>
                {result.creator_name && (
                  <p className="text-purple-600 font-medium mb-3">
                    Creator: {result.creator_name}
                  </p>
                )}
                <div className="space-y-2 text-sm text-gray-600">
                  <p><strong className="text-green-600">{result.songs_created}</strong> songs created</p>
                  <p><strong className="text-blue-600">{result.songs_updated}</strong> songs updated</p>
                  {result.songs_skipped > 0 && (
                    <p><strong className="text-yellow-600">{result.songs_skipped}</strong> songs skipped</p>
                  )}
                  {result.credits_created > 0 && (
                    <p><strong className="text-purple-600">{result.credits_created}</strong> credits linked</p>
                  )}
                </div>
                {result.warnings && result.warnings.length > 0 && (
                  <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg text-left">
                    <p className="text-sm font-semibold text-blue-900 mb-1">Notes:</p>
                    <ul className="text-xs text-blue-800 list-disc list-inside space-y-1">
                      {result.warnings.map((warn, idx) => (
                        <li key={idx}>{warn}</li>
                      ))}
                    </ul>
                  </div>
                )}
                <p className="text-sm text-gray-500 mt-4">Refreshing catalog...</p>
              </div>
            </div>
          )}
        </div>
        
        {/* Actions */}
        {!result && (
          <div className="flex justify-end space-x-3 p-6 border-t border-gray-200">
            <button
              onClick={onClose}
              className="px-6 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
              disabled={uploading}
            >
              Cancel
            </button>
            <button
              onClick={handleUpload}
              disabled={!isValidFile || uploading}
              className="px-6 py-2 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-lg hover:from-purple-700 hover:to-pink-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {uploading ? 'Uploading...' : 'Upload File'}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
