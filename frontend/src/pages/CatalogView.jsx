import React, { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import axios from 'axios'

export default function CatalogView() {
  const [songs, setSongs] = useState([])
  const [catalogSummary, setCatalogSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [uploadMessage, setUploadMessage] = useState('')

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      const token = localStorage.getItem('token')
      const [songsRes, summaryRes] = await Promise.all([
        axios.get('/api/catalog/songs', {
          headers: { 'Authorization': `Bearer ${token}` }
        }),
        axios.get('/api/catalog/summary', {
          headers: { 'Authorization': `Bearer ${token}` }
        })
      ])
      setSongs(songsRes.data)
      setCatalogSummary(summaryRes.data[0] || null)
    } catch (error) {
      console.error('Error fetching data:', error)
    } finally {
      setLoading(false)
    }
  }

  const onDrop = useCallback(async (acceptedFiles) => {
    if (acceptedFiles.length === 0) return

    const file = acceptedFiles[0]
    setUploading(true)
    setUploadMessage('')

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
      setUploadMessage(`Success: ${response.data.message}`)
      setTimeout(() => {
        fetchData()
        setUploadMessage('')
      }, 2000)
    } catch (error) {
      setUploadMessage(`Error: ${error.response?.data?.detail || 'Upload failed'}`)
    } finally {
      setUploading(false)
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls']
    },
    multiple: false
  })

  const formatNumber = (num) => {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'
    if (num >= 1000) return (num / 1000).toFixed(0) + 'K'
    return num?.toString() || '0'
  }

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8 text-center">
        <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-mime-purple"></div>
        <p className="mt-4">Loading catalog...</p>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-6">Catalog View</h1>

      {catalogSummary && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          <div className="col-span-2 bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold mb-4">{catalogSummary.name}</h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <div>
                <p className="text-sm text-gray-500 mb-1">Total Songs</p>
                <p className="text-2xl font-bold">{catalogSummary.total_songs}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500 mb-1">Controlled Publishing %</p>
                <p className="text-2xl font-bold text-mime-purple">{catalogSummary.total_publishing_percentage}%</p>
              </div>
              <div>
                <p className="text-sm text-gray-500 mb-1">Avg Score</p>
                <p className="text-2xl font-bold">{catalogSummary.avg_score}/100</p>
              </div>
              <div>
                <p className="text-sm text-gray-500 mb-1">Valuation (Low)</p>
                <p className="text-xl font-semibold text-gray-700">${formatNumber(catalogSummary.total_valuation_low)}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500 mb-1">Valuation (Base)</p>
                <p className="text-xl font-semibold text-green-600">${formatNumber(catalogSummary.total_valuation_base)}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500 mb-1">Valuation (High)</p>
                <p className="text-xl font-semibold text-gray-700">${formatNumber(catalogSummary.total_valuation_high)}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-bold mb-4">Score Breakdown</h3>
            <div className="space-y-3">
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-sm text-gray-600">Catalog Value</span>
                  <span className="text-sm font-semibold">{catalogSummary.avg_score_breakdown?.catalog_value || 0}/25</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-mime-purple h-2 rounded-full"
                    style={{ width: `${((catalogSummary.avg_score_breakdown?.catalog_value || 0) / 25) * 100}%` }}
                  ></div>
                </div>
              </div>
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-sm text-gray-600">Growth Momentum</span>
                  <span className="text-sm font-semibold">{catalogSummary.avg_score_breakdown?.growth_momentum || 0}/25</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-green-500 h-2 rounded-full"
                    style={{ width: `${((catalogSummary.avg_score_breakdown?.growth_momentum || 0) / 25) * 100}%` }}
                  ></div>
                </div>
              </div>
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-sm text-gray-600">Metadata Health</span>
                  <span className="text-sm font-semibold">{catalogSummary.avg_score_breakdown?.metadata_health || 0}/25</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-500 h-2 rounded-full"
                    style={{ width: `${((catalogSummary.avg_score_breakdown?.metadata_health || 0) / 25) * 100}%` }}
                  ></div>
                </div>
              </div>
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-sm text-gray-600">Exploitation Potential</span>
                  <span className="text-sm font-semibold">{catalogSummary.avg_score_breakdown?.exploitation_potential || 0}/25</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-yellow-500 h-2 rounded-full"
                    style={{ width: `${((catalogSummary.avg_score_breakdown?.exploitation_potential || 0) / 25) * 100}%` }}
                  ></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h3 className="text-lg font-bold mb-4">Upload Filled Schedule A (Internal Demo)</h3>
        <p className="text-sm text-gray-600 mb-4">Use the official MIME Schedule A template only.</p>
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition ${
            isDragActive ? 'border-mime-purple bg-purple-50' : 'border-gray-300 hover:border-mime-purple'
          }`}
        >
          <input {...getInputProps()} />
          {uploading ? (
            <div>
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-mime-purple mb-2"></div>
              <p>Uploading...</p>
            </div>
          ) : isDragActive ? (
            <p className="text-lg">Drop the file here...</p>
          ) : (
            <>
              <svg className="mx-auto h-10 w-10 text-gray-400 mb-2" stroke="currentColor" fill="none" viewBox="0 0 48 48">
                <path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <p className="text-sm">Drag & drop file here or click to browse</p>
              <p className="text-xs text-gray-500 mt-1">PDF, XLSX, or XLS</p>
            </>
          )}
        </div>
        {uploadMessage && (
          <div className={`mt-3 p-3 rounded ${uploadMessage.startsWith('Success') ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
            {uploadMessage}
          </div>
        )}
      </div>

      {songs.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg shadow">
          <p className="text-gray-600 mb-4">No songs in your catalog yet</p>
          <p className="text-sm text-gray-500">Upload a Schedule A file above to get started</p>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Song Title</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Artist(s)</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Publishing %</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Master %</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Revenue</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Val (Low/Base/High)</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Score</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {songs.map((song) => (
                  <tr key={song.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap font-medium">{song.title}</td>
                    <td className="px-6 py-4 whitespace-nowrap">{song.artist_name}</td>
                    <td className="px-6 py-4 whitespace-nowrap">{song.publishing_percentage}%</td>
                    <td className="px-6 py-4 whitespace-nowrap">{song.master_percentage}%</td>
                    <td className="px-6 py-4 whitespace-nowrap text-mime-purple font-semibold">
                      ${formatNumber(song.estimated_revenue)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-xs">
                        <div className="text-gray-600">${formatNumber(song.valuation_low)}</div>
                        <div className="text-green-600 font-semibold">${formatNumber(song.valuation_base)}</div>
                        <div className="text-gray-600">${formatNumber(song.valuation_high)}</div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 rounded text-sm font-semibold ${
                        song.score >= 80 ? 'bg-green-100 text-green-800' :
                        song.score >= 60 ? 'bg-yellow-100 text-yellow-800' :
                        'bg-red-100 text-red-800'
                      }`}>
                        {song.score}/100
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <Link
                        to={`/song/${song.id}`}
                        className="text-mime-purple hover:underline"
                      >
                        View Details
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
