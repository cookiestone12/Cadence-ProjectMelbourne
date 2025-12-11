import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import axios from 'axios'

export default function RosterPage() {
  const [creators, setCreators] = useState([])
  const [loading, setLoading] = useState(true)
  const [orgId, setOrgId] = useState(null)
  
  useEffect(() => {
    async function loadData() {
      try {
        const orgResponse = await axios.get('/api/organizations/current')
        const currentOrgId = orgResponse.data.id
        setOrgId(currentOrgId)
        
        const creatorsResponse = await axios.get(`/api/creators/org/${currentOrgId}`)
        setCreators(creatorsResponse.data)
      } catch (error) {
        console.error('Failed to load roster:', error)
      } finally {
        setLoading(false)
      }
    }
    
    loadData()
  }, [])
  
  if (loading) {
    return (
      <div className="min-h-screen bg-[#F7F7F9] flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-[#A020F0] border-t-transparent"></div>
          <p className="mt-4 text-[#86868B]">Loading roster...</p>
        </div>
      </div>
    )
  }
  
  return (
    <div className="min-h-screen bg-[#F7F7F9] p-6 lg:p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-[34px] font-semibold text-[#1D1D1F] leading-tight">Roster</h1>
          <p className="text-[17px] text-[#86868B] mt-1">Manage your creators and view their catalog performance</p>
        </div>
        
        {creators.length === 0 ? (
          <div className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] p-12 text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[#F2F2F5] flex items-center justify-center">
              <svg className="w-8 h-8 text-[#86868B]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
            </div>
            <p className="text-[#86868B] mb-4 text-[17px]">No creators in your roster yet</p>
            <p className="text-[#A020F0] font-medium">Upload a Schedule A to add creators</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {creators.map((creator) => (
              <Link
                key={creator.id}
                to={`/roster/${creator.id}`}
                className="bg-white rounded-[18px] shadow-[0px_4px_12px_rgba(0,0,0,0.08)] hover:shadow-[0px_8px_24px_rgba(0,0,0,0.12)] transition-all duration-300 overflow-hidden group"
              >
                <div className="aspect-square bg-gradient-to-br from-[#A020F0] to-[#E540AC] relative overflow-hidden">
                  {creator.hero_image_url ? (
                    <img 
                      src={creator.hero_image_url} 
                      alt={creator.display_name}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <div className="text-white text-6xl font-bold opacity-90">
                        {creator.display_name.charAt(0).toUpperCase()}
                      </div>
                    </div>
                  )}
                  <div className="absolute inset-0 bg-black opacity-0 group-hover:opacity-10 transition-opacity duration-200"></div>
                </div>
                
                <div className="p-5">
                  <h3 className="font-semibold text-[17px] text-[#1D1D1F] mb-1 truncate">
                    {creator.display_name}
                  </h3>
                  <p className="text-[13px] text-[#86868B] mb-4">
                    {Array.isArray(creator.roles) ? creator.roles.join(', ') : creator.roles}
                  </p>
                  
                  <div className="flex justify-between items-center">
                    <div>
                      <p className="text-[13px] text-[#86868B]">Songs</p>
                      <p className="font-semibold text-[17px] text-[#1D1D1F]">{creator.song_count}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-[13px] text-[#86868B]">Health</p>
                      <p className={`font-semibold text-[17px] ${
                        creator.avg_health_score >= 80 ? 'text-[#34C759]' :
                        creator.avg_health_score >= 60 ? 'text-[#FF9500]' :
                        'text-[#FF3B30]'
                      }`}>
                        {creator.avg_health_score?.toFixed(0) || 0}%
                      </p>
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
