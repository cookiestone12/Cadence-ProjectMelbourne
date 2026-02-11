import React, { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import axios from 'axios'
import SongDetailModal from '../components/SongDetailModal'

export default function CatalogView() {
  const [songs, setSongs] = useState([])
  const [catalogSummary, setCatalogSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [uploadMessage, setUploadMessage] = useState('')
  const [selectedSongId, setSelectedSongId] = useState(null)
  const [customMultiplier, setCustomMultiplier] = useState(12)

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

  const calculateCustomValuation = (revenue, multiplier) => {
    return revenue * multiplier
  }

  const getCustomPublishingValuation = () => {
    if (!catalogSummary) return 0
    return calculateCustomValuation(catalogSummary.total_publishing_revenue, customMultiplier)
  }

  const getCustomMasterValuation = () => {
    if (!catalogSummary) return 0
    return calculateCustomValuation(catalogSummary.total_master_revenue, customMultiplier)
  }

  const getTotalCustomValuation = () => {
    return getCustomPublishingValuation() + getCustomMasterValuation()
  }

  const handleDownloadReport = async () => {
    if (!catalogSummary) return
    
    try {
      const token = localStorage.getItem('token')
      const response = await axios.get(`/api/catalog/export/${catalogSummary.id}`, {
        headers: { 'Authorization': `Bearer ${token}` },
        responseType: 'blob'
      })
      
      const blob = new Blob([response.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      })
      
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `Rythm_Catalog_Report_${catalogSummary.name.replace(/\s+/g, '_')}_${new Date().toISOString().split('T')[0]}.xlsx`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Error downloading report:', error)
      alert('Failed to download report. Please try again.')
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#F5F7F4] flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-[#5B8A72] border-t-transparent"></div>
          <p className="mt-4 text-[#7A8580]">Loading catalog...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#F5F7F4] p-6 lg:p-8">
      <div className="max-w-7xl mx-auto">
      <h1 className="text-[34px] font-semibold text-[#3D4A44] mb-6">Catalog View</h1>

      {catalogSummary && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            <div className="col-span-2 bg-white rounded border border-[rgba(59,77,67,0.08)] shadow-lg p-6 hover:shadow-lg transition-colors duration-200">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-bold font-medium ">{catalogSummary.name}</h2>
                <button
                  onClick={handleDownloadReport}
                  className="bg-gradient-to-r from-[#5B8A72] to-[#7BA594] text-white px-4 py-2 rounded hover:scale-105 transition-all duration-200 flex items-center gap-2 font-bold uppercase text-sm shadow-lg shadow-[rgba(91,138,114,0.25)]/20 hover:shadow-xl hover:shadow-[rgba(91,138,114,0.25)]/30"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  Download Report
                </button>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <div>
                  <p className="text-sm text-[#7A8580] mb-1 uppercase text-xs tracking-wide">Total Songs</p>
                  <p className="text-2xl font-bold">{catalogSummary.total_songs}</p>
                </div>
                <div>
                  <p className="text-sm text-[#7A8580] mb-1 flex items-center gap-1 uppercase text-xs tracking-wide">
                    Collectible Pub. Value
                    <span className="cursor-help" title="Based on 2-3 year collection windows. Recent songs are fully collectible, older songs face black box loss.">ℹ️</span>
                  </p>
                  <p className="text-2xl font-bold text-green-500">${formatNumber(catalogSummary.collectible_publishing_value)}</p>
                </div>
                <div>
                  <p className="text-sm text-[#7A8580] mb-1 flex items-center gap-1 uppercase text-xs tracking-wide">
                    Est. Black Box Loss
                    <span className="cursor-help" title="Revenue likely lost forever due to industry collection delays. Songs over 3 years old face increasing black box risk.">ℹ️</span>
                  </p>
                  <p className="text-2xl font-bold text-[#C47068]">${formatNumber(catalogSummary.black_box_loss)}</p>
                </div>
                <div>
                  <p className="text-sm text-[#7A8580] mb-1 uppercase text-xs tracking-wide">Avg Score</p>
                  <p className="text-2xl font-bold">{catalogSummary.avg_score}/100</p>
                </div>
              </div>
              
              {/* Valuation Horizon Slider */}
              <div className="mt-6 pt-6 border-t border-[rgba(59,77,67,0.08)]">
                <h3 className="text-sm font-semibold font-medium text-[#7A8580] mb-3 ">Valuation Horizon</h3>
                <div className="bg-[#EEF1EC] rounded border border-[rgba(59,77,67,0.08)] p-5">
                  <div className="flex items-center justify-between mb-3">
                    <label htmlFor="multiplier-slider" className="text-sm font-medium text-[#7A8580] ">
                      Custom Multiplier
                    </label>
                    <div className="flex items-center gap-3">
                      <span className="text-2xl font-bold text-[#C47068]">{customMultiplier}×</span>
                      <span className="text-xs text-[#7A8580] bg-white px-2 py-1 rounded border border-[rgba(59,77,67,0.08)]">
                        {customMultiplier} years of revenue
                      </span>
                    </div>
                  </div>
                  <input
                    id="multiplier-slider"
                    type="range"
                    min="0"
                    max="15"
                    step="0.5"
                    value={customMultiplier}
                    onChange={(e) => setCustomMultiplier(parseFloat(e.target.value))}
                    className="w-full h-3 rounded appearance-none cursor-pointer slider"
                    style={{
                      background: `linear-gradient(to right, #E62E2E 0%, #E62E2E ${(customMultiplier / 15) * 100}%, #333333 ${(customMultiplier / 15) * 100}%, #333333 100%)`
                    }}
                  />
                  <div className="flex justify-between text-xs text-[#7A8580] mt-2">
                    <span>0×</span>
                    <span>5×</span>
                    <span>10×</span>
                    <span>15×</span>
                  </div>
                  <div className="mt-4 pt-4 border-t border-[rgba(59,77,67,0.08)]">
                    <div className="flex justify-between items-center">
                      <span className="text-sm font-medium text-[#7A8580] ">Total Catalog Value</span>
                      <span className="text-2xl font-bold text-[#C47068]">
                        ${formatNumber(getTotalCustomValuation())}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-3 mt-3">
                      <div className="bg-white border border-[rgba(59,77,67,0.08)] rounded p-2">
                        <p className="text-xs text-[#7A8580] ">Publishing</p>
                        <p className="text-lg font-semibold text-[#5B8A72]">${formatNumber(getCustomPublishingValuation())}</p>
                      </div>
                      <div className="bg-white border border-[rgba(59,77,67,0.08)] rounded p-2">
                        <p className="text-xs text-[#7A8580] ">Master</p>
                        <p className="text-lg font-semibold text-orange-400">${formatNumber(getCustomMasterValuation())}</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Separated Publishing and Master Valuations */}
              <div className="mt-6 pt-6 border-t border-[rgba(59,77,67,0.08)]">
                <h3 className="text-sm font-semibold font-medium text-[#7A8580] mb-4 ">Standard Valuation Scenarios</h3>
                <div className="grid grid-cols-2 gap-6">
                  {/* Publishing Valuations */}
                  <div className="bg-[#EEF1EC] rounded border border-[rgba(59,77,67,0.08)] p-4">
                    <h4 className="text-xs font-semibold font-medium text-[#5B8A72] mb-3 ">Publishing Valuations</h4>
                    <div className="space-y-2">
                      <div>
                        <p className="text-xs text-[#7A8580] mb-1 ">Low Scenario</p>
                        <p className="text-lg font-semibold text-[#5B8A72]">${formatNumber(catalogSummary.total_valuation_low_pub)}</p>
                        <p className="text-xs text-[#7A8580]">8× multiplier</p>
                      </div>
                      <div>
                        <p className="text-xs text-[#7A8580] mb-1 ">Base Scenario</p>
                        <p className="text-lg font-semibold text-[#5B8A72]">${formatNumber(catalogSummary.total_valuation_base_pub)}</p>
                        <p className="text-xs text-[#7A8580]">12× multiplier</p>
                      </div>
                      <div>
                        <p className="text-xs text-[#7A8580] mb-1 ">High Scenario</p>
                        <p className="text-lg font-semibold text-[#5B8A72]">${formatNumber(catalogSummary.total_valuation_high_pub)}</p>
                        <p className="text-xs text-[#7A8580]">18× multiplier</p>
                      </div>
                    </div>
                  </div>
                  
                  {/* Master Valuations */}
                  <div className="bg-[#EEF1EC] rounded border border-[rgba(59,77,67,0.08)] p-4">
                    <h4 className="text-xs font-semibold font-medium text-orange-400 mb-3 ">Master Valuations</h4>
                    <div className="space-y-2">
                      <div>
                        <p className="text-xs text-[#7A8580] mb-1 ">Low Scenario</p>
                        <p className="text-lg font-semibold text-orange-400">${formatNumber(catalogSummary.total_valuation_low_master)}</p>
                        <p className="text-xs text-[#7A8580]">8× multiplier</p>
                      </div>
                      <div>
                        <p className="text-xs text-[#7A8580] mb-1 ">Base Scenario</p>
                        <p className="text-lg font-semibold text-orange-400">${formatNumber(catalogSummary.total_valuation_base_master)}</p>
                        <p className="text-xs text-[#7A8580]">12× multiplier</p>
                      </div>
                      <div>
                        <p className="text-xs text-[#7A8580] mb-1 ">High Scenario</p>
                        <p className="text-lg font-semibold text-orange-400">${formatNumber(catalogSummary.total_valuation_high_master)}</p>
                        <p className="text-xs text-[#7A8580]">18× multiplier</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

          <div className="bg-white rounded border border-[rgba(59,77,67,0.08)] shadow-lg p-6 hover:shadow-lg transition-colors duration-200">
            <h3 className="text-lg font-bold font-medium mb-4 ">Score Breakdown</h3>
            <div className="space-y-3">
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-sm text-[#7A8580] uppercase text-xs tracking-wide">Catalog Value</span>
                  <span className="text-sm font-semibold">{catalogSummary.avg_score_breakdown?.catalog_value || 0}/25</span>
                </div>
                <div className="w-full bg-border-grey rounded-full h-2">
                  <div
                    className="bg-gradient-to-r from-[#5B8A72] to-[#7BA594] h-2 rounded-full"
                    style={{ width: `${((catalogSummary.avg_score_breakdown?.catalog_value || 0) / 25) * 100}%` }}
                  ></div>
                </div>
              </div>
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-sm text-[#7A8580] uppercase text-xs tracking-wide">Growth Momentum</span>
                  <span className="text-sm font-semibold">{catalogSummary.avg_score_breakdown?.growth_momentum || 0}/25</span>
                </div>
                <div className="w-full bg-border-grey rounded-full h-2">
                  <div
                    className="bg-green-500 h-2 rounded-full"
                    style={{ width: `${((catalogSummary.avg_score_breakdown?.growth_momentum || 0) / 25) * 100}%` }}
                  ></div>
                </div>
              </div>
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-sm text-[#7A8580] uppercase text-xs tracking-wide">Metadata Health</span>
                  <span className="text-sm font-semibold">{catalogSummary.avg_score_breakdown?.metadata_health || 0}/25</span>
                </div>
                <div className="w-full bg-border-grey rounded-full h-2">
                  <div
                    className="bg-blue-500 h-2 rounded-full"
                    style={{ width: `${((catalogSummary.avg_score_breakdown?.metadata_health || 0) / 25) * 100}%` }}
                  ></div>
                </div>
              </div>
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-sm text-[#7A8580] uppercase text-xs tracking-wide">Exploitation Potential</span>
                  <span className="text-sm font-semibold">{catalogSummary.avg_score_breakdown?.exploitation_potential || 0}/25</span>
                </div>
                <div className="w-full bg-border-grey rounded-full h-2">
                  <div
                    className="bg-yellow-500 h-2 rounded-full"
                    style={{ width: `${((catalogSummary.avg_score_breakdown?.exploitation_potential || 0) / 25) * 100}%` }}
                  ></div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white rounded border border-[rgba(59,77,67,0.08)] shadow-lg p-6 hover:shadow-lg transition-colors duration-200">
          <h3 className="text-lg font-bold font-medium mb-4 ">Revenue Estimate (Admin Collection)</h3>
          
          {/* Streams Breakdown */}
          <div className="mb-4 pb-4 border-b border-[rgba(59,77,67,0.08)]">
            <h4 className="text-sm font-semibold font-medium text-[#7A8580] mb-2 ">Total Streams</h4>
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-sm text-[#7A8580]">Gross Streams</span>
                <span className="font-semibold">{formatNumber(catalogSummary.total_streams_gross)}</span>
              </div>
              <div className="flex justify-between items-center pl-4">
                <span className="text-xs text-[#7A8580]">Premium (70%)</span>
                <span className="text-sm text-[#7A8580]">{formatNumber(catalogSummary.total_premium_streams)}</span>
              </div>
              <div className="flex justify-between items-center pl-4">
                <span className="text-xs text-[#7A8580]">Ad-Supported (30%)</span>
                <span className="text-sm text-[#7A8580]">{formatNumber(catalogSummary.total_ad_supported_streams)}</span>
              </div>
            </div>
          </div>

          {/* Publishing vs Master Revenue */}
          <div className="mb-4 pb-4 border-b border-[rgba(59,77,67,0.08)]">
            <div className="flex items-center gap-2 mb-2">
              <h4 className="text-sm font-semibold font-medium text-[#7A8580] ">Multi-Platform Revenue</h4>
              <div className="group relative">
                <svg className="w-4 h-4 text-[#7A8580] cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div className="hidden group-hover:block absolute left-0 top-6 w-72 bg-white border border-[rgba(59,77,67,0.08)] text-white text-xs rounded p-3 z-10 shadow-lg">
                  <p className="font-semibold mb-1">Multi-Platform Revenue Calculation</p>
                  <p className="mb-2">Revenue calculated across 5 major streaming platforms: Spotify, Apple Music, YouTube Music, Amazon Music, and Tidal.</p>
                  <p className="mb-2"><span className="font-semibold">Publishing:</span> Consistent $0.0012/stream (premium) across all platforms</p>
                  <p><span className="font-semibold">Master:</span> Platform-specific rates (Apple/Tidal pay 2-3× more than Spotify)</p>
                  <p className="mt-2 pt-2 border-t border-[rgba(59,77,67,0.08)] text-[#7A8580]">These 5 platforms represent ~62.5% of global streaming market. Actual total market revenue may be ~60% higher.</p>
                </div>
              </div>
            </div>
            <div className="space-y-3">
              <div className="bg-[#EEF1EC] border border-[rgba(59,77,67,0.08)] p-3 rounded">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm font-medium text-[#7A8580] ">Publishing Revenue</span>
                  <span className="text-lg font-bold text-[#C47068]">${formatNumber(catalogSummary.total_publishing_revenue)}</span>
                </div>
                <div className="flex justify-between items-center text-xs pl-2">
                  <span className="text-[#7A8580]">Premium Streams</span>
                  <span className="text-[#7A8580]">${formatNumber(catalogSummary.publishing_revenue_by_type.premium)}</span>
                </div>
                <div className="flex justify-between items-center text-xs pl-2">
                  <span className="text-[#7A8580]">Ad-Supported Streams</span>
                  <span className="text-[#7A8580]">${formatNumber(catalogSummary.publishing_revenue_by_type.ad_supported)}</span>
                </div>
              </div>
              
              <div className="bg-[#EEF1EC] border border-[rgba(59,77,67,0.08)] p-3 rounded">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm font-medium text-[#7A8580] ">Master Revenue</span>
                  <span className="text-lg font-bold text-orange-400">${formatNumber(catalogSummary.total_master_revenue)}</span>
                </div>
                <div className="flex justify-between items-center text-xs pl-2">
                  <span className="text-[#7A8580]">Premium Streams</span>
                  <span className="text-[#7A8580]">${formatNumber(catalogSummary.master_revenue_by_type.premium)}</span>
                </div>
                <div className="flex justify-between items-center text-xs pl-2">
                  <span className="text-[#7A8580]">Ad-Supported Streams</span>
                  <span className="text-[#7A8580]">${formatNumber(catalogSummary.master_revenue_by_type.ad_supported)}</span>
                </div>
                <div className="mt-2 pt-2 border-t border-[rgba(59,77,67,0.08)]">
                  <p className="text-xs text-[#7A8580] italic">Platform-specific rates: Spotify $0.004, Apple $0.01, YouTube $0.008, Amazon $0.004, Tidal $0.013</p>
                </div>
              </div>
            </div>
          </div>

          {/* Revenue Split (Publishing Only) */}
          <div>
            <h4 className="text-sm font-semibold font-medium text-[#7A8580] mb-2 ">Revenue Split (Publishing Only)</h4>
            <div className="space-y-2">
              <div className="flex justify-between items-center bg-[#EEF1EC] border border-[rgba(59,77,67,0.08)] p-3 rounded">
                <span className="text-sm font-medium">80/20 Deal (20% to label)</span>
                <span className="text-lg font-bold text-green-500">${formatNumber(catalogSummary.label_share_80_20)}</span>
              </div>
              <div className="flex justify-between items-center bg-[#EEF1EC] border border-[rgba(59,77,67,0.08)] p-3 rounded">
                <span className="text-sm font-medium">60/40 Deal (40% to label)</span>
                <span className="text-lg font-bold text-orange-400">${formatNumber(catalogSummary.label_share_60_40)}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Territory Breakdown */}
        {catalogSummary.territory_breakdown && Object.keys(catalogSummary.territory_breakdown).length > 0 && (
          <div className="bg-white rounded border border-[rgba(59,77,67,0.08)] shadow-lg p-6 hover:shadow-lg transition-colors duration-200">
            <h3 className="text-lg font-bold font-medium mb-4 ">Revenue by Territory</h3>
            <div className="overflow-x-auto">
              <table className="min-w-full">
                <thead>
                  <tr className="border-b border-[rgba(59,77,67,0.08)] bg-[#EEF1EC]">
                    <th className="text-left py-2 px-3 text-sm font-semibold text-[#7A8580] ">Territory</th>
                    <th className="text-right py-2 px-3 text-sm font-semibold text-[#7A8580] ">Streams</th>
                    <th className="text-right py-2 px-3 text-sm font-semibold text-[#C47068] ">Publishing</th>
                    <th className="text-right py-2 px-3 text-sm font-semibold text-orange-400 ">Master</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-grey">
                  {Object.entries(catalogSummary.territory_breakdown)
                    .sort(([, a], [, b]) => b.publishing - a.publishing)
                    .map(([territory, data]) => (
                    <tr key={territory} className="hover:bg-black hover:bg-opacity-30 transition-colors duration-150">
                      <td className="py-2 px-3 font-medium">{territory}</td>
                      <td className="py-2 px-3 text-right text-sm text-[#7A8580]">{formatNumber(data.total_streams)}</td>
                      <td className="py-2 px-3 text-right font-semibold text-[#C47068]">${formatNumber(data.publishing)}</td>
                      <td className="py-2 px-3 text-right font-semibold text-orange-400">${formatNumber(data.master)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </>
      )}

      <div className="bg-white rounded border border-[rgba(59,77,67,0.08)] shadow-lg p-6 mb-6 hover:shadow-lg transition-colors duration-200">
        <h3 className="text-lg font-bold font-medium mb-4 ">Upload Filled Schedule A (Internal Demo)</h3>
        <p className="text-sm text-[#7A8580] mb-4">Use the official Rythm Schedule A template only.</p>
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition ${
            isDragActive ? 'border-signal-red bg-gradient-to-r from-[#5B8A72] to-[#7BA594] bg-opacity-10' : 'border-[rgba(59,77,67,0.08)] hover:shadow-lg'
          }`}
        >
          <input {...getInputProps()} />
          {uploading ? (
            <div>
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-signal-red mb-2"></div>
              <p>Uploading...</p>
            </div>
          ) : isDragActive ? (
            <p className="text-lg">Drop the file here...</p>
          ) : (
            <>
              <svg className="mx-auto h-10 w-10 text-[#7A8580] mb-2" stroke="currentColor" fill="none" viewBox="0 0 48 48">
                <path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <p className="text-sm">Drag & drop file here or click to browse</p>
              <p className="text-xs text-[#7A8580] mt-1">PDF, XLSX, or XLS</p>
            </>
          )}
        </div>
        {uploadMessage && (
          <div className={`mt-3 p-3 rounded border ${uploadMessage.startsWith('Success') ? 'bg-green-500 bg-opacity-20 border-green-500 text-green-400' : 'bg-gradient-to-r from-[#5B8A72] to-[#7BA594] bg-opacity-20 border-signal-red text-red-400'}`}>
            {uploadMessage}
          </div>
        )}
      </div>

      {songs.length === 0 ? (
        <div className="text-center py-12 bg-white rounded border border-[rgba(59,77,67,0.08)] shadow-lg">
          <p className="text-[#7A8580] mb-4">No songs in your catalog yet</p>
          <p className="text-sm text-[#7A8580]">Upload a Schedule A file above to get started</p>
        </div>
      ) : (
        <div className="bg-white rounded border border-[rgba(59,77,67,0.08)] shadow-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-border-grey">
              <thead className="bg-[#EEF1EC]">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] r">Song Title</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] r">Artist(s)</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#5B8A72] r">Client</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] r">Streams</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] r">Publishing %</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] r">Master %</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#C47068] r">Pub. Revenue</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-orange-400 r">Master Revenue</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] r">Publishing Val</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] r">Master Val</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] r">Score</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#7A8580] r">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-border-grey">
                {songs.map((song) => (
                  <tr key={song.id} className="hover:bg-black hover:bg-opacity-30 transition-colors duration-150">
                    <td className="px-6 py-4 whitespace-nowrap font-medium">{song.title}</td>
                    <td className="px-6 py-4 whitespace-nowrap">{song.artist_name}</td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {song.client_name ? (
                        <Link to={`/creators/${song.client_id}`} className="text-[#5B8A72] hover:underline">
                          {song.client_name}
                        </Link>
                      ) : (
                        <span className="text-[#7A8580]">—</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-[#7A8580]">
                      {song.spotify_streams ? formatNumber(song.spotify_streams) : 'N/A'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">{song.publishing_percentage}%</td>
                    <td className="px-6 py-4 whitespace-nowrap">{song.master_percentage}%</td>
                    <td className="px-6 py-4 whitespace-nowrap text-[#C47068] font-semibold">
                      ${formatNumber(song.publishing_revenue)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-orange-400 font-semibold">
                      ${formatNumber(song.master_revenue)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap bg-[#EEF1EC]">
                      <div className="text-xs">
                        <div className="text-[#5B8A72]">${formatNumber(song.valuation_low_pub)} <span className="text-[#7A8580]">(8×)</span></div>
                        <div className="text-[#5B8A72] font-semibold">${formatNumber(song.valuation_base_pub)} <span className="text-[#7A8580]">(12×)</span></div>
                        <div className="text-[#5B8A72]">${formatNumber(song.valuation_high_pub)} <span className="text-[#7A8580]">(18×)</span></div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap bg-[#EEF1EC]">
                      <div className="text-xs">
                        <div className="text-orange-400">${formatNumber(song.valuation_low_master)} <span className="text-[#7A8580]">(8×)</span></div>
                        <div className="text-orange-400 font-semibold">${formatNumber(song.valuation_base_master)} <span className="text-[#7A8580]">(12×)</span></div>
                        <div className="text-orange-400">${formatNumber(song.valuation_high_master)} <span className="text-[#7A8580]">(18×)</span></div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 rounded text-sm font-semibold ${
                        song.score >= 80 ? 'bg-green-500 bg-opacity-20 border border-green-500 text-green-400' :
                        song.score >= 60 ? 'bg-yellow-500 bg-opacity-20 border border-yellow-500 text-yellow-400' :
                        'bg-gradient-to-r from-[#5B8A72] to-[#7BA594] bg-opacity-20 border border-signal-red text-red-400'
                      }`}>
                        {song.score}/100
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <button
                        onClick={() => setSelectedSongId(song.id)}
                        className="text-[#C47068] hover:underline"
                      >
                        View Details
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {selectedSongId && (
        <SongDetailModal
          song={{ id: selectedSongId }}
          onClose={() => setSelectedSongId(null)}
          onSongUpdated={fetchData}
        />
      )}
      </div>
    </div>
  )
}
