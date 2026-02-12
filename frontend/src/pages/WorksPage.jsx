import React, { useState, useEffect } from 'react'
import axios from 'axios'
import {
  MagnifyingGlassIcon, PlusIcon, XMarkIcon, TrashIcon,
  PencilIcon, MusicalNoteIcon, UserGroupIcon, LinkIcon
} from '@heroicons/react/24/outline'

export default function WorksPage() {
  const [works, setWorks] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [organizationId, setOrganizationId] = useState(null)
  const [showAddModal, setShowAddModal] = useState(false)
  const [selectedWork, setSelectedWork] = useState(null)
  const [workDetail, setWorkDetail] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [songs, setSongs] = useState([])
  const [creators, setCreators] = useState([])
  const [editMode, setEditMode] = useState(false)
  const [editForm, setEditForm] = useState({})
  const [addForm, setAddForm] = useState({ title: '', iswc: '', language: '', genre: '', notes: '', work_type: 'TRACK' })
  const [workTypeFilter, setWorkTypeFilter] = useState('')
  const [trackSearch, setTrackSearch] = useState('')
  const [creditForm, setCreditForm] = useState({ creator_id: '', role: '', share_percentage: '' })
  const [activeDetailTab, setActiveDetailTab] = useState('info')
  const [rightsData, setRightsData] = useState([])
  const [rightsLoading, setRightsLoading] = useState(false)

  useEffect(() => {
    loadData()
  }, [])

  async function loadData() {
    try {
      const orgResponse = await axios.get('/api/organizations/current')
      const orgId = orgResponse.data?.id
      if (!orgId) { setLoading(false); return }
      setOrganizationId(orgId)

      const [worksResponse, songsResponse, creatorsResponse] = await Promise.all([
        axios.get(`/api/works/org/${orgId}?limit=500`),
        axios.get(`/api/songs/org/${orgId}?limit=1000`),
        axios.get(`/api/creators/org/${orgId}`)
      ])

      setWorks(worksResponse.data.works || [])
      setSongs(songsResponse.data)
      setCreators(creatorsResponse.data)
    } catch (error) {
      console.error('Failed to load works:', error)
    } finally {
      setLoading(false)
    }
  }

  const filteredWorks = works.filter(work => {
    if (workTypeFilter && (work.work_type || 'TRACK') !== workTypeFilter) return false
    if (!searchTerm) return true
    const term = searchTerm.toLowerCase()
    return (
      work.title.toLowerCase().includes(term) ||
      (work.iswc && work.iswc.toLowerCase().includes(term))
    )
  })

  async function openWorkDetail(work) {
    setSelectedWork(work)
    setDetailLoading(true)
    setActiveDetailTab('info')
    setEditMode(false)
    setRightsData([])
    try {
      const res = await axios.get(`/api/works/${work.id}`)
      setWorkDetail(res.data)
      setEditForm({
        title: res.data.title || '',
        work_type: res.data.work_type || 'TRACK',
        iswc: res.data.iswc || '',
        language: res.data.language || '',
        genre: res.data.genre || '',
        notes: res.data.notes || ''
      })
      loadWorkRights(work.id)
    } catch (error) {
      console.error('Failed to load work detail:', error)
    } finally {
      setDetailLoading(false)
    }
  }

  async function handleAddWork() {
    if (!addForm.title.trim()) return
    try {
      await axios.post(`/api/works/org/${organizationId}`, addForm)
      setShowAddModal(false)
      setAddForm({ title: '', iswc: '', language: '', genre: '', notes: '', work_type: 'TRACK' })
      await loadData()
    } catch (error) {
      console.error('Failed to create work:', error)
    }
  }

  async function handleUpdateWork() {
    if (!workDetail) return
    try {
      await axios.put(`/api/works/${workDetail.id}`, editForm)
      setEditMode(false)
      await loadData()
      const res = await axios.get(`/api/works/${workDetail.id}`)
      setWorkDetail(res.data)
    } catch (error) {
      console.error('Failed to update work:', error)
    }
  }

  async function handleDeleteWork() {
    if (!workDetail) return
    try {
      await axios.delete(`/api/works/${workDetail.id}`)
      setSelectedWork(null)
      setWorkDetail(null)
      await loadData()
    } catch (error) {
      console.error('Failed to delete work:', error)
    }
  }

  async function handleLinkTrack(songId) {
    if (!workDetail) return
    try {
      await axios.post(`/api/works/${workDetail.id}/tracks`, { song_id: songId })
      const res = await axios.get(`/api/works/${workDetail.id}`)
      setWorkDetail(res.data)
      setTrackSearch('')
      await loadData()
    } catch (error) {
      console.error('Failed to link track:', error)
    }
  }

  async function handleUnlinkTrack(songId) {
    if (!workDetail) return
    try {
      await axios.delete(`/api/works/${workDetail.id}/tracks/${songId}`)
      const res = await axios.get(`/api/works/${workDetail.id}`)
      setWorkDetail(res.data)
      await loadData()
    } catch (error) {
      console.error('Failed to unlink track:', error)
    }
  }

  async function handleAddCredit() {
    if (!workDetail || !creditForm.creator_id || !creditForm.role) return
    try {
      await axios.post(`/api/works/${workDetail.id}/credits`, {
        creator_id: parseInt(creditForm.creator_id),
        role: creditForm.role,
        share_percentage: creditForm.share_percentage ? parseFloat(creditForm.share_percentage) : null
      })
      setCreditForm({ creator_id: '', role: '', share_percentage: '' })
      const res = await axios.get(`/api/works/${workDetail.id}`)
      setWorkDetail(res.data)
      await loadData()
    } catch (error) {
      console.error('Failed to add credit:', error)
    }
  }

  async function handleRemoveCredit(creditId) {
    if (!workDetail) return
    try {
      await axios.delete(`/api/works/${workDetail.id}/credits/${creditId}`)
      const res = await axios.get(`/api/works/${workDetail.id}`)
      setWorkDetail(res.data)
      await loadData()
    } catch (error) {
      console.error('Failed to remove credit:', error)
    }
  }

  async function loadWorkRights(workId) {
    if (!organizationId) return
    setRightsLoading(true)
    try {
      const response = await axios.get(`/api/rights/asset/${organizationId}?asset_type=WORK&asset_id=${workId}`)
      setRightsData(response.data.contracts || [])
    } catch (error) {
      console.error('Failed to load rights data:', error)
      setRightsData([])
    } finally {
      setRightsLoading(false)
    }
  }

  const linkedTrackIds = workDetail?.tracks?.map(t => t.song_id) || []
  const availableTracks = songs.filter(s => {
    if (linkedTrackIds.includes(s.id)) return false
    if (!trackSearch) return true
    return s.title.toLowerCase().includes(trackSearch.toLowerCase()) ||
      s.primary_artist.toLowerCase().includes(trackSearch.toLowerCase())
  })

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-[#7A8580]">Loading works...</div>
      </div>
    )
  }

  return (
    <div className="p-4 sm:p-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl sm:text-4xl font-bold text-[#3D4A44] mb-2">Works</h1>
          <p className="text-[#7A8580]">{works.length} total works</p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            className="flex items-center space-x-2 px-4 py-2 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] transition-colors"
            onClick={() => setShowAddModal(true)}
          >
            <PlusIcon className="w-5 h-5" />
            <span>Add Work</span>
          </button>
        </div>
      </div>

      <div className="bg-[#FAFBF9] rounded-xl shadow-sm p-4 mb-6">
        <div className="flex items-center space-x-4">
          <div className="flex-1 relative">
            <MagnifyingGlassIcon className="w-5 h-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-[#7A8580]" />
            <input
              type="text"
              placeholder="Search by title or ISWC..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
            />
          </div>
          <select
            value={workTypeFilter}
            onChange={(e) => setWorkTypeFilter(e.target.value)}
            className="border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44] text-sm"
          >
            <option value="">All Types</option>
            <option value="DEMO">Demo</option>
            <option value="TRACK">Track</option>
          </select>
        </div>
      </div>

      <div className="bg-[#FAFBF9] rounded-xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-[#EEF1EC] border-b border-[rgba(59,77,67,0.08)]">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-[#3D4A44]">Title</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-[#3D4A44]">Type</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-[#3D4A44]">ISWC</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-[#3D4A44]">Genre</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-[#3D4A44]">Linked Tracks</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-[#3D4A44]">Credits</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[rgba(59,77,67,0.08)]">
              {filteredWorks.map((work) => (
                <tr
                  key={work.id}
                  onClick={() => openWorkDetail(work)}
                  className="hover:bg-[rgba(91,138,114,0.06)] cursor-pointer transition-colors"
                >
                  <td className="px-4 py-3">
                    <div className="font-medium text-[#3D4A44]">{work.title}</div>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium ${
                      (work.work_type || 'TRACK') === 'DEMO'
                        ? 'bg-amber-100 text-amber-700'
                        : 'bg-sky-100 text-sky-700'
                    }`}>
                      {(work.work_type || 'TRACK') === 'DEMO' ? 'Demo' : 'Track'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-[#7A8580]">
                    {work.iswc || '-'}
                  </td>
                  <td className="px-4 py-3 text-sm text-[#7A8580]">
                    {work.genre || '-'}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className="inline-flex items-center space-x-1 text-sm text-[#7A8580]">
                      <MusicalNoteIcon className="w-4 h-4" />
                      <span>{work.track_count}</span>
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className="inline-flex items-center space-x-1 text-sm text-[#7A8580]">
                      <UserGroupIcon className="w-4 h-4" />
                      <span>{work.credit_count}</span>
                    </span>
                  </td>
                </tr>
              ))}
              {filteredWorks.length === 0 && (
                <tr>
                  <td colSpan="6" className="px-6 py-12 text-center text-[#7A8580]">
                    No works found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-md mx-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-[#3D4A44]">Add New Work</h3>
              <button onClick={() => setShowAddModal(false)} className="text-[#7A8580] hover:text-[#3D4A44]">
                <XMarkIcon className="w-5 h-5" />
              </button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Title *</label>
                <input
                  type="text"
                  value={addForm.title}
                  onChange={(e) => setAddForm(prev => ({ ...prev, title: e.target.value }))}
                  className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  placeholder="Work title"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Work Type</label>
                <select
                  value={addForm.work_type}
                  onChange={(e) => setAddForm(prev => ({ ...prev, work_type: e.target.value }))}
                  className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                >
                  <option value="TRACK">Track (Instrumental/Beat)</option>
                  <option value="DEMO">Demo (Song with Lyrics/Melodies)</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">ISWC</label>
                <input
                  type="text"
                  value={addForm.iswc}
                  onChange={(e) => setAddForm(prev => ({ ...prev, iswc: e.target.value }))}
                  className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  placeholder="T-000.000.000-0"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Language</label>
                <input
                  type="text"
                  value={addForm.language}
                  onChange={(e) => setAddForm(prev => ({ ...prev, language: e.target.value }))}
                  className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  placeholder="English"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Genre</label>
                <input
                  type="text"
                  value={addForm.genre}
                  onChange={(e) => setAddForm(prev => ({ ...prev, genre: e.target.value }))}
                  className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  placeholder="Pop, Hip-Hop, R&B..."
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Notes</label>
                <textarea
                  value={addForm.notes}
                  onChange={(e) => setAddForm(prev => ({ ...prev, notes: e.target.value }))}
                  className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  rows={3}
                  placeholder="Additional notes..."
                />
              </div>
            </div>
            <div className="flex justify-end space-x-3 mt-6">
              <button
                onClick={() => setShowAddModal(false)}
                className="px-4 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg text-[#3D4A44] hover:bg-[#EEF1EC] transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleAddWork}
                disabled={!addForm.title.trim()}
                className="px-4 py-2 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Create Work
              </button>
            </div>
          </div>
        </div>
      )}

      {selectedWork && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl mx-4 max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between p-6 border-b border-[rgba(59,77,67,0.08)]">
              <h3 className="text-lg font-semibold text-[#3D4A44]">
                {workDetail?.title || selectedWork.title}
              </h3>
              <div className="flex items-center space-x-2">
                {!editMode && workDetail && (
                  <>
                    <button
                      onClick={() => setEditMode(true)}
                      className="p-2 text-[#7A8580] hover:text-[#5B8A72] hover:bg-[#EEF1EC] rounded-lg transition-colors"
                    >
                      <PencilIcon className="w-5 h-5" />
                    </button>
                    <button
                      onClick={handleDeleteWork}
                      className="p-2 text-[#7A8580] hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                    >
                      <TrashIcon className="w-5 h-5" />
                    </button>
                  </>
                )}
                <button
                  onClick={() => { setSelectedWork(null); setWorkDetail(null); setEditMode(false) }}
                  className="p-2 text-[#7A8580] hover:text-[#3D4A44] hover:bg-[#EEF1EC] rounded-lg transition-colors"
                >
                  <XMarkIcon className="w-5 h-5" />
                </button>
              </div>
            </div>

            <div className="border-b border-[rgba(59,77,67,0.08)]">
              <div className="flex space-x-6 px-6">
                {['info', 'tracks', 'credits', 'rights'].map(tab => (
                  <button
                    key={tab}
                    onClick={() => setActiveDetailTab(tab)}
                    className={`pb-3 pt-3 px-1 border-b-2 font-medium text-sm transition-colors capitalize ${
                      activeDetailTab === tab
                        ? 'border-[#5B8A72] text-[#5B8A72]'
                        : 'border-transparent text-[#7A8580] hover:text-[#3D4A44]'
                    }`}
                  >
                    {tab === 'tracks' ? `Tracks (${workDetail?.tracks?.length || 0})` :
                     tab === 'credits' ? `Credits (${workDetail?.credits?.length || 0})` :
                     tab === 'rights' ? `Rights (${rightsData.length})` :
                     'Info'}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-6">
              {detailLoading ? (
                <div className="flex items-center justify-center py-12">
                  <div className="text-[#7A8580]">Loading...</div>
                </div>
              ) : workDetail && activeDetailTab === 'info' && (
                editMode ? (
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-[#3D4A44] mb-1">Title</label>
                      <input
                        type="text"
                        value={editForm.title}
                        onChange={(e) => setEditForm(prev => ({ ...prev, title: e.target.value }))}
                        className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-[#3D4A44] mb-1">Work Type</label>
                      <select
                        value={editForm.work_type}
                        onChange={(e) => setEditForm(prev => ({ ...prev, work_type: e.target.value }))}
                        className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                      >
                        <option value="TRACK">Track (Instrumental/Beat)</option>
                        <option value="DEMO">Demo (Song with Lyrics/Melodies)</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-[#3D4A44] mb-1">ISWC</label>
                      <input
                        type="text"
                        value={editForm.iswc}
                        onChange={(e) => setEditForm(prev => ({ ...prev, iswc: e.target.value }))}
                        className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-[#3D4A44] mb-1">Language</label>
                      <input
                        type="text"
                        value={editForm.language}
                        onChange={(e) => setEditForm(prev => ({ ...prev, language: e.target.value }))}
                        className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-[#3D4A44] mb-1">Genre</label>
                      <input
                        type="text"
                        value={editForm.genre}
                        onChange={(e) => setEditForm(prev => ({ ...prev, genre: e.target.value }))}
                        className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-[#3D4A44] mb-1">Notes</label>
                      <textarea
                        value={editForm.notes}
                        onChange={(e) => setEditForm(prev => ({ ...prev, notes: e.target.value }))}
                        className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                        rows={3}
                      />
                    </div>
                    <div className="flex justify-end space-x-3 pt-2">
                      <button
                        onClick={() => setEditMode(false)}
                        className="px-4 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg text-[#3D4A44] hover:bg-[#EEF1EC] transition-colors"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleUpdateWork}
                        className="px-4 py-2 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] transition-colors"
                      >
                        Save Changes
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-xs font-medium text-[#7A8580] mb-1">Title</p>
                        <p className="text-sm text-[#3D4A44]">{workDetail.title}</p>
                      </div>
                      <div>
                        <p className="text-xs font-medium text-[#7A8580] mb-1">Work Type</p>
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium ${
                          (workDetail.work_type || 'TRACK') === 'DEMO'
                            ? 'bg-amber-100 text-amber-700'
                            : 'bg-sky-100 text-sky-700'
                        }`}>
                          {(workDetail.work_type || 'TRACK') === 'DEMO' ? 'Demo' : 'Track'}
                        </span>
                      </div>
                      <div>
                        <p className="text-xs font-medium text-[#7A8580] mb-1">ISWC</p>
                        <p className="text-sm text-[#3D4A44]">{workDetail.iswc || '-'}</p>
                      </div>
                      <div>
                        <p className="text-xs font-medium text-[#7A8580] mb-1">Language</p>
                        <p className="text-sm text-[#3D4A44]">{workDetail.language || '-'}</p>
                      </div>
                      <div>
                        <p className="text-xs font-medium text-[#7A8580] mb-1">Genre</p>
                        <p className="text-sm text-[#3D4A44]">{workDetail.genre || '-'}</p>
                      </div>
                    </div>
                    {workDetail.notes && (
                      <div>
                        <p className="text-xs font-medium text-[#7A8580] mb-1">Notes</p>
                        <p className="text-sm text-[#3D4A44]">{workDetail.notes}</p>
                      </div>
                    )}
                  </div>
                )
              )}

              {workDetail && activeDetailTab === 'tracks' && (
                <div className="space-y-4">
                  {workDetail.tracks?.length > 0 && (
                    <div className="space-y-2">
                      {workDetail.tracks.map(track => (
                        <div key={track.id} className="flex items-center justify-between p-3 bg-[#F5F7F4] rounded-lg">
                          <div>
                            <p className="text-sm font-medium text-[#3D4A44]">{track.title}</p>
                            <p className="text-xs text-[#7A8580]">{track.primary_artist} {track.isrc ? `· ${track.isrc}` : ''}</p>
                          </div>
                          <button
                            onClick={() => handleUnlinkTrack(track.song_id)}
                            className="p-1.5 text-[#7A8580] hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                          >
                            <XMarkIcon className="w-4 h-4" />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="border-t border-[rgba(59,77,67,0.08)] pt-4">
                    <p className="text-sm font-medium text-[#3D4A44] mb-2">Link a Track</p>
                    <div className="relative mb-3">
                      <MagnifyingGlassIcon className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-[#7A8580]" />
                      <input
                        type="text"
                        placeholder="Search tracks..."
                        value={trackSearch}
                        onChange={(e) => setTrackSearch(e.target.value)}
                        className="w-full pl-9 pr-4 py-2 text-sm border border-[rgba(59,77,67,0.12)] rounded-lg focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                      />
                    </div>
                    {trackSearch && (
                      <div className="max-h-48 overflow-y-auto space-y-1">
                        {availableTracks.slice(0, 20).map(song => (
                          <button
                            key={song.id}
                            onClick={() => handleLinkTrack(song.id)}
                            className="w-full flex items-center justify-between p-2.5 text-left hover:bg-[rgba(91,138,114,0.06)] rounded-lg transition-colors"
                          >
                            <div>
                              <p className="text-sm text-[#3D4A44]">{song.title}</p>
                              <p className="text-xs text-[#7A8580]">{song.primary_artist}</p>
                            </div>
                            <LinkIcon className="w-4 h-4 text-[#5B8A72]" />
                          </button>
                        ))}
                        {availableTracks.length === 0 && (
                          <p className="text-sm text-[#7A8580] text-center py-4">No matching tracks found</p>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {workDetail && activeDetailTab === 'credits' && (
                <div className="space-y-4">
                  {workDetail.credits?.length > 0 && (
                    <div className="space-y-2">
                      {workDetail.credits.map(credit => (
                        <div key={credit.id} className="flex items-center justify-between p-3 bg-[#F5F7F4] rounded-lg">
                          <div>
                            <p className="text-sm font-medium text-[#3D4A44]">{credit.creator_name}</p>
                            <p className="text-xs text-[#7A8580]">
                              {credit.role}
                              {credit.share_percentage != null ? ` · ${credit.share_percentage}%` : ''}
                            </p>
                          </div>
                          <button
                            onClick={() => handleRemoveCredit(credit.id)}
                            className="p-1.5 text-[#7A8580] hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                          >
                            <XMarkIcon className="w-4 h-4" />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="border-t border-[rgba(59,77,67,0.08)] pt-4">
                    <p className="text-sm font-medium text-[#3D4A44] mb-3">Add Credit</p>
                    <div className="space-y-3">
                      <div>
                        <label className="block text-xs font-medium text-[#7A8580] mb-1">Creator</label>
                        <select
                          value={creditForm.creator_id}
                          onChange={(e) => setCreditForm(prev => ({ ...prev, creator_id: e.target.value }))}
                          className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                        >
                          <option value="">Select creator...</option>
                          {creators.map(c => (
                            <option key={c.id} value={c.id}>{c.display_name}</option>
                          ))}
                        </select>
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="block text-xs font-medium text-[#7A8580] mb-1">Role</label>
                          <select
                            value={creditForm.role}
                            onChange={(e) => setCreditForm(prev => ({ ...prev, role: e.target.value }))}
                            className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                          >
                            <option value="">Select role...</option>
                            <option value="Composer">Composer</option>
                            <option value="Lyricist">Lyricist</option>
                            <option value="Arranger">Arranger</option>
                            <option value="Publisher">Publisher</option>
                            <option value="Administrator">Administrator</option>
                          </select>
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-[#7A8580] mb-1">Share %</label>
                          <input
                            type="number"
                            value={creditForm.share_percentage}
                            onChange={(e) => setCreditForm(prev => ({ ...prev, share_percentage: e.target.value }))}
                            placeholder="0-100"
                            min="0"
                            max="100"
                            className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                          />
                        </div>
                      </div>
                      <button
                        onClick={handleAddCredit}
                        disabled={!creditForm.creator_id || !creditForm.role}
                        className="w-full px-4 py-2 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] transition-colors text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Add Credit
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {workDetail && activeDetailTab === 'rights' && (
                <div className="space-y-4">
                  {rightsLoading ? (
                    <div className="text-center py-8 text-[#7A8580]">Loading rights data...</div>
                  ) : rightsData.length === 0 ? (
                    <div className="text-center py-8 bg-[#F5F7F4] rounded-lg border-2 border-dashed border-[rgba(59,77,67,0.08)]">
                      <p className="text-[#3D4A44] font-medium">No rights or contracts assigned</p>
                      <p className="text-xs text-[#7A8580] mt-1">Link this work to a contract in the Contracts page to define rights splits</p>
                    </div>
                  ) : (
                    rightsData.map((contractInfo, idx) => (
                      <div key={idx} className="bg-[#F5F7F4] rounded-lg p-4">
                        <div className="flex items-center gap-2 mb-3">
                          <h4 className="text-sm font-semibold text-[#3D4A44]">{contractInfo.contract_title}</h4>
                          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium ${
                            contractInfo.contract_type === 'MASTER' ? 'bg-purple-100 text-purple-700' :
                            contractInfo.contract_type === 'PUBLISHING' ? 'bg-blue-100 text-blue-700' :
                            contractInfo.contract_type === 'SYNC_LICENSE' ? 'bg-teal-100 text-teal-700' :
                            'bg-gray-100 text-gray-700'
                          }`}>
                            {(contractInfo.contract_type || '').replace(/_/g, ' ')}
                          </span>
                          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium ${
                            contractInfo.contract_status === 'ACTIVE' ? 'bg-green-100 text-green-700' :
                            contractInfo.contract_status === 'PENDING' ? 'bg-yellow-100 text-yellow-700' :
                            contractInfo.contract_status === 'EXPIRED' ? 'bg-red-100 text-red-700' :
                            'bg-gray-100 text-gray-700'
                          }`}>
                            {contractInfo.contract_status}
                          </span>
                        </div>
                        {contractInfo.splits?.length > 0 ? (
                          <div className="space-y-1.5">
                            {contractInfo.splits.map((split, sidx) => (
                              <div key={sidx} className="flex items-center justify-between p-2.5 bg-white rounded-lg">
                                <div className="flex items-center gap-3">
                                  <span className="text-sm font-medium text-[#3D4A44]">{split.rights_holder_name}</span>
                                  <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium ${
                                    split.rights_type === 'MASTER' ? 'bg-purple-50 text-purple-600' :
                                    split.rights_type === 'PUBLISHING' ? 'bg-blue-50 text-blue-600' :
                                    split.rights_type === 'PERFORMANCE' ? 'bg-amber-50 text-amber-600' :
                                    'bg-gray-50 text-gray-600'
                                  }`}>
                                    {split.rights_type}
                                  </span>
                                </div>
                                <div className="flex items-center gap-2">
                                  <div className="w-16 h-1.5 bg-[#EEF1EC] rounded-full overflow-hidden">
                                    <div
                                      className="h-full bg-gradient-to-r from-[#5B8A72] to-[#7BA594] rounded-full"
                                      style={{ width: `${Math.min(split.share_percentage, 100)}%` }}
                                    ></div>
                                  </div>
                                  <span className="text-sm font-semibold text-[#3D4A44] w-12 text-right">{split.share_percentage}%</span>
                                </div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p className="text-xs text-[#7A8580] text-center py-3">No splits defined yet</p>
                        )}
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
