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
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-400">Loading roster...</div>
      </div>
    )
  }
  
  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-gray-900 mb-2">Roster</h1>
        <p className="text-gray-600">Manage your creators and view their catalog performance</p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {creators.map((creator) => (
          <Link
            key={creator.id}
            to={`/roster/${creator.id}`}
            className="bg-white rounded-xl shadow-sm hover:shadow-md transition-shadow duration-200 overflow-hidden group"
          >
            <div className="aspect-square bg-gradient-to-br from-purple-400 to-pink-500 relative overflow-hidden">
              {creator.hero_image_url ? (
                <img 
                  src={creator.hero_image_url} 
                  alt={creator.display_name}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center">
                  <div className="text-white text-6xl font-bold">
                    {creator.display_name.charAt(0).toUpperCase()}
                  </div>
                </div>
              )}
              <div className="absolute inset-0 bg-black opacity-0 group-hover:opacity-10 transition-opacity duration-200"></div>
            </div>
            
            <div className="p-4">
              <h3 className="font-bold text-lg text-gray-900 mb-1 truncate">
                {creator.display_name}
              </h3>
              <p className="text-sm text-gray-500 mb-3">
                {creator.roles.join(', ')}
              </p>
              
              <div className="flex justify-between items-center text-sm">
                <div>
                  <p className="text-gray-400">Songs</p>
                  <p className="font-bold text-gray-900">{creator.song_count}</p>
                </div>
                <div>
                  <p className="text-gray-400">Health</p>
                  <p className="font-bold text-gray-900">{creator.avg_health_score.toFixed(0)}%</p>
                </div>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}
