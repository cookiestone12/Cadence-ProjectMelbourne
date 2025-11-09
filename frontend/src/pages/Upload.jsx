import React, { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import axios from 'axios'
import { useNavigate } from 'react-router-dom'

export default function Upload() {
  const [uploading, setUploading] = useState(false)
  const [message, setMessage] = useState('')
  const navigate = useNavigate()

  const onDrop = useCallback(async (acceptedFiles) => {
    if (acceptedFiles.length === 0) return

    const file = acceptedFiles[0]
    setUploading(true)
    setMessage('')

    const formData = new FormData()
    formData.append('file', file)

    try {
      const token = localStorage.getItem('token')
      const response = await axios.post('/api/catalog/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
          'Authorization': `Bearer ${token}`
        }
      })
      setMessage(`Success: ${response.data.message}`)
      setTimeout(() => navigate('/dashboard'), 2000)
    } catch (error) {
      setMessage(`Error: ${error.response?.data?.detail || 'Upload failed'}`)
    } finally {
      setUploading(false)
    }
  }, [navigate])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls']
    },
    multiple: false
  })

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8">Upload Schedule A</h1>
      
      <div className="max-w-2xl mx-auto">
        <div
          {...getRootProps()}
          className={`border-4 border-dashed rounded-lg p-12 text-center cursor-pointer transition ${
            isDragActive ? 'border-mime-purple bg-purple-50' : 'border-gray-300 hover:border-mime-purple'
          }`}
        >
          <input {...getInputProps()} />
          <svg className="mx-auto h-12 w-12 text-gray-400 mb-4" stroke="currentColor" fill="none" viewBox="0 0 48 48">
            <path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          {isDragActive ? (
            <p className="text-lg">Drop the file here...</p>
          ) : (
            <>
              <p className="text-lg mb-2">Drag & drop your Schedule A file here</p>
              <p className="text-sm text-gray-500">or click to browse</p>
              <p className="text-xs text-gray-400 mt-4">Supported formats: PDF, Excel (.xlsx, .xls)</p>
            </>
          )}
        </div>

        {uploading && (
          <div className="mt-8 text-center">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-mime-purple"></div>
            <p className="mt-2">Uploading and processing...</p>
          </div>
        )}

        {message && (
          <div className={`mt-8 p-4 rounded ${message.startsWith('Error') ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'}`}>
            {message}
          </div>
        )}

        <div className="mt-8 bg-blue-50 border-l-4 border-blue-500 p-4">
          <h3 className="font-semibold mb-2">Important Notes:</h3>
          <ul className="list-disc list-inside text-sm text-gray-700 space-y-1">
            <li>Use the official MIME Schedule A template</li>
            <li>Ensure all required fields are filled out</li>
            <li>Deviations from the format may result in parsing errors</li>
            <li>The system will automatically fetch analytics and calculate valuations</li>
          </ul>
        </div>
      </div>
    </div>
  )
}
