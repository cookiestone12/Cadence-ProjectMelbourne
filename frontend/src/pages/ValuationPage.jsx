import React, { useState, useEffect } from 'react'
import axios from 'axios'
import {
  CurrencyDollarIcon,
  ArrowTrendingUpIcon,
  MusicalNoteIcon,
  ArrowDownTrayIcon,
  XMarkIcon,
  ChartBarIcon
} from '@heroicons/react/24/outline'

export default function ValuationPage() {
  const [loading, setLoading] = useState(true)
  const [catalogData, setCatalogData] = useState(null)
  const [selectedSong, setSelectedSong] = useState(null)
  const [songDetail, setSongDetail] = useState(null)
  const [loadingDetail, setLoadingDetail] = useState(false)

  useEffect(() => {
    loadCatalogData()
  }, [])

  const loadCatalogData = async () => {
    try {
      setLoading(true)
      const response = await axios.get('/api/valuation/catalog/summary')
      setCatalogData(response.data)
    } catch (error) {
      console.error('Error loading catalog data:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadSongDetail = async (songId) => {
    try {
      setLoadingDetail(true)
      const response = await axios.get(`/api/valuation/song/${songId}/detail`)
      setSongDetail(response.data)
    } catch (error) {
      console.error('Error loading song detail:', error)
    } finally {
      setLoadingDetail(false)
    }
  }

  const handleSongClick = (song) => {
    setSelectedSong(song)
    loadSongDetail(song.song_id)
  }

  const handleDownloadReport = async () => {
    try {
      const response = await axios.get('/api/valuation/catalog/download/excel', {
        responseType: 'blob'
      })
      
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `ampersound_catalog_report_${new Date().toISOString().split('T')[0]}.xlsx`)
      document.body.appendChild(link)
      link.click()
      link.remove()
    } catch (error) {
      console.error('Error downloading report:', error)
    }
  }

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value)
  }

  const formatPercentage = (value) => {
    return `${(value * 100).toFixed(1)}%`
  }

  if (loading) {
    return (
      <div className="p-8">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="h-4 bg-gray-200 rounded w-1/3 mb-8"></div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-32 bg-gray-200 rounded-xl"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (!catalogData) {
    return (
      <div className="p-8">
        <h1 className="text-4xl font-bold text-gray-900 mb-2">Catalog Valuation</h1>
        <div className="mt-8 bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl shadow-sm p-12 text-center">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full mb-6">
            <CurrencyDollarIcon className="w-10 h-10 text-white" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-3">No Valuation Data</h2>
          <p className="text-gray-600 max-w-2xl mx-auto">
            Your catalog doesn't have valuation data yet. Valuation calculations will be available once streaming metrics and revenue data are imported.
          </p>
        </div>
      </div>
    )
  }

  const hasData = catalogData.top_songs && catalogData.top_songs.length > 0

  return (
    <div className="p-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold text-gray-900 mb-2">Catalog Valuation</h1>
          <p className="text-gray-600">{catalogData.organization_name}</p>
        </div>
        <button
          onClick={handleDownloadReport}
          className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-lg hover:from-purple-700 hover:to-pink-700 transition-all shadow-md"
        >
          <ArrowDownTrayIcon className="w-5 h-5" />
          <span>Download Report</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl shadow-sm p-6 border border-purple-100">
          <div className="flex items-center space-x-3 mb-3">
            <div className="p-2 bg-gradient-to-r from-purple-500 to-pink-500 rounded-lg">
              <CurrencyDollarIcon className="w-6 h-6 text-white" />
            </div>
            <h3 className="font-bold text-gray-900">Total Catalog Value</h3>
          </div>
          <div className="text-3xl font-bold bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
            {formatCurrency(catalogData.total_catalog_value)}
          </div>
          <p className="text-sm text-gray-600 mt-1">{catalogData.total_songs} songs</p>
        </div>

        <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
          <div className="flex items-center space-x-3 mb-3">
            <div className="p-2 bg-green-100 rounded-lg">
              <ArrowTrendingUpIcon className="w-6 h-6 text-green-600" />
            </div>
            <h3 className="font-bold text-gray-900">Annual Revenue</h3>
          </div>
          <div className="text-3xl font-bold text-gray-900">
            {formatCurrency(catalogData.total_annual_revenue)}
          </div>
          <p className="text-sm text-green-600 mt-1">
            +{formatPercentage(catalogData.avg_growth_rate)} avg growth
          </p>
        </div>

        <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
          <div className="flex items-center space-x-3 mb-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <MusicalNoteIcon className="w-6 h-6 text-blue-600" />
            </div>
            <h3 className="font-bold text-gray-900">30-Day Revenue</h3>
          </div>
          <div className="text-3xl font-bold text-gray-900">
            {formatCurrency(catalogData.total_thirty_day_revenue)}
          </div>
          <p className="text-sm text-gray-600 mt-1">Last month projection</p>
        </div>
      </div>

      {hasData ? (
        <div className="bg-white rounded-xl shadow-sm mb-8">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-xl font-bold text-gray-900">Top Valued Songs</h2>
          </div>
          <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Song</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Artist</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Streams</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Valuation</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Annual Revenue</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Growth</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Black Box</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {catalogData.top_songs.map((song) => (
                <tr
                  key={song.song_id}
                  onClick={() => handleSongClick(song)}
                  className="hover:bg-gray-50 cursor-pointer transition-colors"
                >
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="font-medium text-gray-900">{song.title}</div>
                    <div className="text-sm text-gray-500">{song.isrc || 'No ISRC'}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                    {song.primary_artist}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-700">
                    {song.total_streams.toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <div className="font-semibold text-purple-600">
                      {formatCurrency(song.final_valuation)}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-700">
                    {formatCurrency(song.annual_revenue)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <span className={`text-sm font-medium ${song.growth_rate >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {song.growth_rate >= 0 ? '+' : ''}{formatPercentage(song.growth_rate)}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium text-gray-900">
                    {formatCurrency(song.black_box_value)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm p-12 text-center mb-8">
          <p className="text-gray-500">No song valuation data available yet</p>
        </div>
      )}

      {catalogData.territory_breakdown && catalogData.territory_breakdown.length > 0 ? (
      <div className="bg-white rounded-xl shadow-sm">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-xl font-bold text-gray-900">Territory Breakdown</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Territory</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Streams</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Publishing</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Master</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Total Revenue</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {catalogData.territory_breakdown.map((territory) => (
                <tr key={territory.territory_code} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <span className="font-medium text-gray-900">{territory.territory_code}</span>
                      <span className="ml-2 text-sm text-gray-500">{territory.territory_name}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-700">
                    {territory.total_streams.toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-700">
                    {formatCurrency(territory.publishing_revenue)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-700">
                    {formatCurrency(territory.master_revenue)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right font-semibold text-gray-900">
                    {formatCurrency(territory.total_revenue)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      ) : null}

      {selectedSong && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
            <div className="p-6 border-b border-gray-200 flex items-center justify-between bg-gradient-to-r from-purple-50 to-pink-50">
              <div>
                <h2 className="text-2xl font-bold text-gray-900">{selectedSong.title}</h2>
                <p className="text-gray-600">{selectedSong.primary_artist}</p>
              </div>
              <button
                onClick={() => {
                  setSelectedSong(null)
                  setSongDetail(null)
                }}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <XMarkIcon className="w-6 h-6" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6">
              {loadingDetail ? (
                <div className="flex items-center justify-center h-64">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600"></div>
                </div>
              ) : songDetail ? (
                <div className="space-y-6">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="bg-purple-50 rounded-lg p-4">
                      <div className="text-sm text-gray-600 mb-1">Final Valuation</div>
                      <div className="text-xl font-bold text-purple-600">
                        {formatCurrency(songDetail.valuation.final_valuation)}
                      </div>
                    </div>
                    <div className="bg-green-50 rounded-lg p-4">
                      <div className="text-sm text-gray-600 mb-1">Annual Revenue</div>
                      <div className="text-xl font-bold text-green-600">
                        {formatCurrency(songDetail.valuation.annual_revenue)}
                      </div>
                    </div>
                    <div className="bg-blue-50 rounded-lg p-4">
                      <div className="text-sm text-gray-600 mb-1">Total Streams</div>
                      <div className="text-xl font-bold text-blue-600">
                        {songDetail.streaming_metrics.total_streams?.toLocaleString() || '0'}
                      </div>
                    </div>
                    <div className="bg-orange-50 rounded-lg p-4">
                      <div className="text-sm text-gray-600 mb-1">Growth Rate</div>
                      <div className="text-xl font-bold text-orange-600">
                        {formatPercentage(songDetail.valuation.growth_rate)}
                      </div>
                    </div>
                  </div>

                  <div className="bg-gray-50 rounded-lg p-6">
                    <h3 className="font-bold text-gray-900 mb-4 flex items-center">
                      <ChartBarIcon className="w-5 h-5 mr-2 text-purple-600" />
                      Valuation Breakdown
                    </h3>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <div className="text-sm text-gray-600">Streaming Multiple</div>
                        <div className="font-semibold text-gray-900">
                          {formatCurrency(songDetail.valuation.streaming_multiple_value)}
                        </div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-600">Revenue Multiple</div>
                        <div className="font-semibold text-gray-900">
                          {formatCurrency(songDetail.valuation.revenue_multiple_value)}
                        </div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-600">Market Comp</div>
                        <div className="font-semibold text-gray-900">
                          {formatCurrency(songDetail.valuation.market_comp_value)}
                        </div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-600">Black Box Value</div>
                        <div className="font-semibold text-purple-600">
                          {formatCurrency(songDetail.valuation.black_box_value)}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="bg-gray-50 rounded-lg p-6">
                    <h3 className="font-bold text-gray-900 mb-4">Streaming Metrics</h3>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                      <div>
                        <div className="text-gray-600">Ad-Supported</div>
                        <div className="font-semibold text-gray-900">
                          {songDetail.streaming_metrics.ad_supported_streams?.toLocaleString() || '0'}
                        </div>
                      </div>
                      <div>
                        <div className="text-gray-600">Premium</div>
                        <div className="font-semibold text-gray-900">
                          {songDetail.streaming_metrics.premium_streams?.toLocaleString() || '0'}
                        </div>
                      </div>
                      <div>
                        <div className="text-gray-600">On-Demand</div>
                        <div className="font-semibold text-gray-900">
                          {songDetail.streaming_metrics.on_demand_streams?.toLocaleString() || '0'}
                        </div>
                      </div>
                      <div>
                        <div className="text-gray-600">Audio</div>
                        <div className="font-semibold text-gray-900">
                          {songDetail.streaming_metrics.audio_streams?.toLocaleString() || '0'}
                        </div>
                      </div>
                      <div>
                        <div className="text-gray-600">Video</div>
                        <div className="font-semibold text-gray-900">
                          {songDetail.streaming_metrics.video_streams?.toLocaleString() || '0'}
                        </div>
                      </div>
                      <div>
                        <div className="text-gray-600">Sales</div>
                        <div className="font-semibold text-gray-900">
                          {songDetail.streaming_metrics.song_sales?.toLocaleString() || '0'}
                        </div>
                      </div>
                    </div>
                  </div>

                  {songDetail.territory_revenues && songDetail.territory_revenues.length > 0 && (
                    <div className="bg-gray-50 rounded-lg p-6">
                      <h3 className="font-bold text-gray-900 mb-4">Top Territories</h3>
                      <div className="space-y-2">
                        {songDetail.territory_revenues.slice(0, 5).map((territory) => (
                          <div key={territory.territory_code} className="flex items-center justify-between">
                            <div className="flex items-center space-x-2">
                              <span className="font-medium text-gray-900">{territory.territory_code}</span>
                              <span className="text-sm text-gray-600">{territory.territory_name}</span>
                            </div>
                            <div className="text-right">
                              <div className="font-semibold text-gray-900">
                                {formatCurrency(territory.total_revenue)}
                              </div>
                              <div className="text-xs text-gray-500">
                                {territory.total_streams.toLocaleString()} streams
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center text-gray-500">No detail available</div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
