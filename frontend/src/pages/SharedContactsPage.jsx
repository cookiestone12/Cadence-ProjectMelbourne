import React, { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import axios from 'axios'
import { UserGroupIcon, EnvelopeIcon, PhoneIcon, GlobeAltIcon } from '@heroicons/react/24/outline'

const ROLE_COLORS = {
  Songwriter: 'bg-blue-100 text-blue-700',
  Producer: 'bg-purple-100 text-purple-700',
  Artist: 'bg-green-100 text-green-700',
  Musician: 'bg-orange-100 text-orange-700',
  Engineer: 'bg-teal-100 text-teal-700',
  'Featured Artist': 'bg-pink-100 text-pink-700',
  Composer: 'bg-indigo-100 text-indigo-700',
  Lyricist: 'bg-yellow-100 text-yellow-700',
  Arranger: 'bg-red-100 text-red-700',
}

export default function SharedContactsPage() {
  const { token } = useParams()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    async function load() {
      try {
        const res = await axios.get(`/api/public/shared-contacts/${token}`)
        setData(res.data)
      } catch (err) {
        if (err.response?.status === 410) {
          setError('This shared link has expired.')
        } else if (err.response?.status === 404) {
          setError('Shared link not found.')
        } else {
          setError('Failed to load shared contacts.')
        }
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [token])

  if (loading) {
    return (
      <div className="min-h-screen bg-[#F8F9F7] flex items-center justify-center">
        <div className="text-[#7A8580]">Loading shared contacts...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#F8F9F7] flex items-center justify-center">
        <div className="bg-white rounded-2xl border border-[rgba(59,77,67,0.12)] p-12 text-center max-w-md">
          <UserGroupIcon className="w-12 h-12 text-[#B0BDB4] mx-auto mb-3" />
          <h2 className="text-lg font-semibold text-[#3D4A44] mb-2">Unavailable</h2>
          <p className="text-sm text-[#7A8580]">{error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#F8F9F7]">
      <div className="max-w-6xl mx-auto p-4 sm:p-8">
        <div className="bg-gradient-to-r from-[#5B8A72] to-[#7A8580] rounded-2xl p-6 sm:p-8 mb-6 text-white">
          <div className="flex items-center gap-3 mb-2">
            <UserGroupIcon className="w-8 h-8" />
            <h1 className="text-2xl sm:text-3xl font-bold">Shared Contacts</h1>
          </div>
          <p className="text-white/80 text-sm sm:text-base">
            Shared by {data.organization_name}
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {data.contacts.map(contact => (
            <div key={contact.id} className="bg-white rounded-2xl border border-[rgba(59,77,67,0.12)] p-5 flex flex-col">
              <div className="mb-3">
                <h3 className="text-lg font-bold text-[#3D4A44] truncate">{contact.display_name}</h3>
                {contact.legal_name && (
                  <p className="text-sm text-[#7A8580] truncate">{contact.legal_name}</p>
                )}
              </div>

              {contact.roles && contact.roles.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mb-3">
                  {contact.roles.map(role => (
                    <span key={role} className={`px-2 py-0.5 rounded-full text-xs font-medium ${ROLE_COLORS[role] || 'bg-gray-100 text-gray-700'}`}>
                      {role}
                    </span>
                  ))}
                </div>
              )}

              <div className="space-y-1.5 text-sm flex-1">
                {(contact.pro || contact.ipi) && (
                  <p className="text-[#3D4A44]">
                    {contact.pro && <span className="font-medium">{contact.pro}</span>}
                    {contact.pro && contact.ipi && <span className="text-[#B0BDB4] mx-1">&middot;</span>}
                    {contact.ipi && <span className="text-[#7A8580]">IPI: {contact.ipi}</span>}
                  </p>
                )}
                {contact.publisher_name && (
                  <p className="text-[#7A8580]">Publisher: <span className="text-[#3D4A44]">{contact.publisher_name}</span></p>
                )}
                {contact.email && (
                  <p className="text-[#7A8580] truncate flex items-center gap-1.5">
                    <EnvelopeIcon className="w-3.5 h-3.5 flex-shrink-0" />
                    <a href={`mailto:${contact.email}`} className="hover:text-[#5B8A72] transition-colors">{contact.email}</a>
                  </p>
                )}
                {contact.phone && (
                  <p className="text-[#7A8580] truncate flex items-center gap-1.5">
                    <PhoneIcon className="w-3.5 h-3.5 flex-shrink-0" />
                    <a href={`tel:${contact.phone}`} className="hover:text-[#5B8A72] transition-colors">{contact.phone}</a>
                  </p>
                )}
                {contact.representation_name && (
                  <p className="text-[#7A8580]">Rep: <span className="text-[#3D4A44]">{contact.representation_name}</span></p>
                )}
                {contact.territory && (
                  <p className="text-[#7A8580] flex items-center gap-1.5">
                    <GlobeAltIcon className="w-3.5 h-3.5 flex-shrink-0" />
                    {contact.territory}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>

        <div className="text-center mt-8 text-xs text-[#B0BDB4]">
          Powered by Cadence &mdash; Catalog Intelligence
        </div>
      </div>
    </div>
  )
}
