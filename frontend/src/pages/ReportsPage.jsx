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
          { name: 'Critical (0-25%)', value: songs.filter(s => s.status_health_score < 25).length, color: '#ef4444' },
          { name: 'Needs Work (25-50%)', value: songs.filter(s => s.status_health_score >= 25 && s.status_health_score < 50).length, color: '#f59e0b' },
          { name: 'Good (50-75%)', value: songs.filter(s => s.status_health_score >= 50 && s.status_health_score < 75).length, color: '#3b82f6' },
          { name: 'Excellent (75-100%)', value: songs.filter(s => s.status_health_score >= 75).length, color: '#10b981' }
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
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-400">Loading reports...</div>
      </div>
    )
  }
  
  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-gray-900 mb-2">Reports</h1>
        <p className="text-gray-600">Catalog health and performance insights</p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-white rounded-xl shadow-sm p-6">
          <p className="text-sm text-gray-500 mb-1">Total Songs</p>
          <p className="text-3xl font-bold text-gray-900">{stats.totalSongs}</p>
        </div>
        
        <div className="bg-white rounded-xl shadow-sm p-6">
          <p className="text-sm text-gray-500 mb-1">Avg Health Score</p>
          <p className="text-3xl font-bold text-gray-900">{stats.avgHealthScore.toFixed(1)}%</p>
        </div>
        
        <div className="bg-white rounded-xl shadow-sm p-6">
          <p className="text-sm text-gray-500 mb-1">Placement Rate</p>
          <p className="text-3xl font-bold text-gray-900">{stats.placementRate.toFixed(1)}%</p>
        </div>
        
        <div className="bg-white rounded-xl shadow-sm p-6">
          <p className="text-sm text-gray-500 mb-1">Registered Songs</p>
          <p className="text-3xl font-bold text-gray-900">{stats.registeredCount}</p>
        </div>
      </div>
      
      <div className="bg-white rounded-xl shadow-sm p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-6">Health Score Distribution</h2>
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
  )
}
