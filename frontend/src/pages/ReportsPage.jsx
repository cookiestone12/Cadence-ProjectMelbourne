import React, { useState, useEffect } from 'react'
import axios from 'axios'
import { BarChart, Bar, PieChart, Pie, Cell, ResponsiveContainer, XAxis, YAxis, Tooltip, Legend } from 'recharts'

export default function ReportsPage() {
  const [stats, setStats] = useState({
    totalSongs: 0,
    avgHealthScore: 0,
    placementRate: 0,
    registeredCount: 0
  })
  const [healthDistribution, setHealthDistribution] = useState([])
  const [loading, setLoading] = useState(true)
  
  useEffect(() => {
    async function loadReports() {
      try {
        const orgResponse = await axios.get('/api/organizations/current')
        const orgId = orgResponse.data.id
        
        const songsResponse = await axios.get(`/api/songs/org/${orgId}`)
        const songs = songsResponse.data
        
        const totalSongs = songs.length
        const avgHealth = songs.reduce((sum, s) => sum + (s.status_health_score || 0), 0) / (totalSongs || 1)
        const placedSongs = songs.filter(s => s.is_paid).length
        const registeredSongs = songs.filter(s => s.is_registered_with_pro || s.is_registered_with_dsp).length
        
        setStats({
          totalSongs,
          avgHealthScore: avgHealth,
          placementRate: (placedSongs / totalSongs * 100) || 0,
          registeredCount: registeredSongs
        })
        
        const distribution = [
          { name: 'Critical (0-25%)', value: songs.filter(s => s.status_health_score < 25).length, color: '#FF3B30' },
          { name: 'Needs Work (25-50%)', value: songs.filter(s => s.status_health_score >= 25 && s.status_health_score < 50).length, color: '#FF9500' },
          { name: 'Good (50-75%)', value: songs.filter(s => s.status_health_score >= 50 && s.status_health_score < 75).length, color: '#007AFF' },
          { name: 'Excellent (75-100%)', value: songs.filter(s => s.status_health_score >= 75).length, color: '#34C759' }
        ]
        
        setHealthDistribution(distribution)
      } catch (error) {
        console.error('Failed to load reports:', error)
      } finally {
        setLoading(false)
      }
    }
    
    loadReports()
  }, [])
  
  if (loading) {
    return (
      <div className="min-h-screen bg-[#F7F7F9] flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-[#A020F0] border-t-transparent"></div>
          <p className="mt-4 text-[#86868B]">Loading reports...</p>
        </div>
      </div>
    )
  }
  
  return (
    <div className="min-h-screen bg-[#F7F7F9] p-6 lg:p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-[34px] font-semibold text-[#1D1D1F] leading-tight">Reports</h1>
          <p className="text-[17px] text-[#86868B] mt-1">Catalog health and performance insights</p>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
          <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6 relative overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-[#A020F0] to-[#E540AC]"></div>
            <p className="text-[13px] text-[#86868B] mb-1">Total Songs</p>
            <p className="text-[40px] font-semibold text-[#1D1D1F]">{stats.totalSongs}</p>
          </div>
          
          <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6 relative overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-[#007AFF] to-[#5AC8FA]"></div>
            <p className="text-[13px] text-[#86868B] mb-1">Avg Health Score</p>
            <p className="text-[40px] font-semibold text-[#1D1D1F]">{stats.avgHealthScore.toFixed(1)}%</p>
          </div>
          
          <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6 relative overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-[#34C759] to-[#30D158]"></div>
            <p className="text-[13px] text-[#86868B] mb-1">Placement Rate</p>
            <p className="text-[40px] font-semibold text-[#1D1D1F]">{stats.placementRate.toFixed(1)}%</p>
          </div>
          
          <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6 relative overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-[#FF9500] to-[#FF9F0A]"></div>
            <p className="text-[13px] text-[#86868B] mb-1">Registered Songs</p>
            <p className="text-[40px] font-semibold text-[#1D1D1F]">{stats.registeredCount}</p>
          </div>
        </div>
        
        <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-6">
          <h2 className="text-[22px] font-medium text-[#1D1D1F] mb-6">Health Score Distribution</h2>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={healthDistribution}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={(entry) => `${entry.name}: ${entry.value}`}
                outerRadius={100}
                fill="#8884d8"
                dataKey="value"
              >
                {healthDistribution.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}
