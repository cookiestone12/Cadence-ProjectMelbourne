import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, Link, useLocation, useNavigate } from 'react-router-dom'
import axios from 'axios'
import { ArrowLeftIcon, ArrowDownTrayIcon, ArrowUpTrayIcon, CheckIcon, XMarkIcon, PencilIcon, DocumentTextIcon, DocumentArrowDownIcon, PlusIcon, MusicalNoteIcon, TrashIcon, CloudArrowUpIcon, PaperClipIcon, LinkIcon, DocumentDuplicateIcon, SparklesIcon } from '@heroicons/react/24/outline'
import { CheckCircleIcon, XCircleIcon, MinusCircleIcon } from '@heroicons/react/24/solid'
import ActionsTab from '../components/ActionsTab'
import CreatorAccountingEnhanced from '../components/CreatorAccountingEnhanced'
import PlatformIcon from '../components/PlatformIcon'
import SocialCard from '../components/SocialCard'
import SongDetailModal from '../components/SongDetailModal'
import AddSongModal from '../components/AddSongModal'

const DollarOrNAInput = ({ value, onChange, placeholder = "Amount" }) => {
  const isNA = value === 'N/A'
  const displayVal = (value === 'true' || value === true) ? '' : (value === 'false' || value === false) ? '' : value
  return (
    <div className="flex items-center gap-1" style={{ minWidth: '120px' }}>
      {isNA ? (
        <button
          type="button"
          onClick={() => onChange('')}
          className="px-3 py-2 border border-[rgba(0,0,0,0.1)] rounded-xl text-sm bg-[#F5F7F4] text-[#7A8580] hover:bg-[#EEF1EC] transition-colors w-full text-center"
        >
          N/A
        </button>
      ) : (
        <div className="flex items-center gap-1 w-full">
          <div className="relative flex-1">
            <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[#7A8580] text-sm font-medium">$</span>
            <input
              type="number"
              min="0"
              step="0.01"
              value={displayVal}
              onChange={(e) => onChange(e.target.value)}
              className="w-full pl-6 pr-2 py-2 border border-[rgba(0,0,0,0.1)] rounded-xl text-sm bg-white focus:outline-none focus:border-[#5B8A72] focus:ring-1 focus:ring-[#5B8A72]"
              placeholder={placeholder}
              style={{ minWidth: '80px' }}
            />
          </div>
          <button
            type="button"
            onClick={() => onChange('N/A')}
            className="px-2 py-2 text-xs font-medium text-[#7A8580] hover:text-[#5B8A72] hover:bg-[#F5F7F4] rounded-lg transition-colors whitespace-nowrap border border-transparent hover:border-[rgba(0,0,0,0.1)]"
            title="Set to N/A"
          >
            N/A
          </button>
        </div>
      )}
    </div>
  )
}

const PlacementStatusBadge = ({ status }) => {
  const colors = {
    'Paid': { bg: 'rgba(52, 199, 89, 0.15)', color: '#5B9A6E' },
    'Invoiced': { bg: 'rgba(0, 122, 255, 0.15)', color: '#5A8A9A' },
    'Contracted': { bg: 'rgba(160, 32, 240, 0.15)', color: '#5B8A72' },
    'Contract Sent': { bg: 'rgba(88, 86, 214, 0.15)', color: '#6B9A84' },
    'Released - Awaiting Contract': { bg: 'rgba(255, 149, 0, 0.15)', color: '#C4956B' },
    'In Pipeline': { bg: 'rgba(0, 0, 0, 0.05)', color: '#7A8580' }
  }
  const style = colors[status] || colors['In Pipeline']
  return (
    <span 
      className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium"
      style={{ background: style.bg, color: style.color }}
    >
      {status}
    </span>
  )
}

export default function CreatorDetailPage() {
  const { id } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const locationState = location.state || {}
  const [creator, setCreator] = useState(null)
  const [songs, setSongs] = useState([])
  const [scheduleAData, setScheduleAData] = useState(null)
  const [activeTab, setActiveTab] = useState('overview')
  const [loading, setLoading] = useState(true)
  const [editingSong, setEditingSong] = useState(null)
  const [editForm, setEditForm] = useState({})
  const [saving, setSaving] = useState(false)
  const [organizationId, setOrganizationId] = useState(null)
  const [organizationName, setOrganizationName] = useState('')
  const [showAddSongModal, setShowAddSongModal] = useState(false)
  const [addingSong, setAddingSong] = useState(false)
  const [uploadingScheduleA, setUploadingScheduleA] = useState(false)
  const [uploadFeedback, setUploadFeedback] = useState(null)
  const [newSong, setNewSong] = useState({
    title: '',
    primary_artist: '',
    isrc: '',
    iswc: '',
    project_title: '',
    release_date: '',
    label: '',
    publishing_percentage: '',
    master_percentage: '',
    advance_amount: '',
    notes: '',
    credit_role: 'ARTIST'
  })
  const [selectedSongs, setSelectedSongs] = useState(new Set())
  const [selectedSongForDetail, setSelectedSongForDetail] = useState(null)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [showMergeModal, setShowMergeModal] = useState(false)
  const [mergePrimaryId, setMergePrimaryId] = useState(null)
  const [merging, setMerging] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [creatorReleases, setCreatorReleases] = useState([])
  const [releaseArtworkUrls, setReleaseArtworkUrls] = useState({})
  const [sortColumn, setSortColumn] = useState(null)
  const [sortDirection, setSortDirection] = useState('asc')
  const [sharedVersion, setSharedVersion] = useState(null)
  const [sharedModules, setSharedModules] = useState(null)
  const [showEditCreatorModal, setShowEditCreatorModal] = useState(false)
  const [editingCreator, setEditingCreator] = useState(false)
  const [showSpotifyModal, setShowSpotifyModal] = useState(false)
  const [spotifyModalSong, setSpotifyModalSong] = useState(null)
  const [spotifyLinkInput, setSpotifyLinkInput] = useState('')
  const [savingSpotifyLink, setSavingSpotifyLink] = useState(false)
  const [accountingData, setAccountingData] = useState(null)
  const [accountingLoading, setAccountingLoading] = useState(false)
  const [creatorContracts, setCreatorContracts] = useState([])
  const [contractsLoading, setContractsLoading] = useState(false)
  const [showCreateContractModal, setShowCreateContractModal] = useState(false)
  const [createContractForm, setCreateContractForm] = useState({
    title: '', contract_type: 'MASTER', payment_direction: 'INCOMING', status: 'DRAFT',
    reference_number: '', start_date: '', end_date: '', territory: '',
    advance_amount: '', advance_currency: 'USD', notes: '', terms_summary: ''
  })
  const [createContractParties, setCreateContractParties] = useState([])
  const [createContractPartyForm, setCreateContractPartyForm] = useState({ party_name: '', party_role: 'ARTIST', contact_email: '' })
  const [createContractError, setCreateContractError] = useState('')
  const [createContractLoading, setCreateContractLoading] = useState(false)
  const [showUploadDocModal, setShowUploadDocModal] = useState(false)
  const [uploadDocFile, setUploadDocFile] = useState(null)
  const [uploadDocContractId, setUploadDocContractId] = useState('')
  const [uploadDocDescription, setUploadDocDescription] = useState('')
  const [uploadDocError, setUploadDocError] = useState('')
  const [uploadDocLoading, setUploadDocLoading] = useState(false)
  const [showAddFeeModal, setShowAddFeeModal] = useState(false)
  const [showAddAdvanceModal, setShowAddAdvanceModal] = useState(false)
  const [feeForm, setFeeForm] = useState({ fee_type: 'MANAGEMENT_FEE', description: '', amount: '', fee_date: '', notes: '' })
  const [advanceForm, setAdvanceForm] = useState({ description: '', amount: '', advance_date: '', notes: '' })
  const [savingFee, setSavingFee] = useState(false)
  const [savingAdvance, setSavingAdvance] = useState(false)
  const [creditsData, setCreditsData] = useState(null)
  const [creditsLoading, setCreditsLoading] = useState(false)
  const [creditsSongs, setCreditsSongs] = useState([])
  const [creditsSongsLoading, setCreditsSongsLoading] = useState(false)
  const [showShareModal, setShowShareModal] = useState(false)
  const [shareSettings, setShareSettings] = useState({ is_public: true, passcode: '' })
  const [shareResult, setShareResult] = useState(null)
  const [savingShare, setSavingShare] = useState(false)
  const [refreshingCredits, setRefreshingCredits] = useState(false)
  const [generatingSocialCard, setGeneratingSocialCard] = useState(false)
  const [showSocialCard, setShowSocialCard] = useState(false)
  const [socialCardFormat, setSocialCardFormat] = useState('story')
  const [showFormatMenu, setShowFormatMenu] = useState(false)
  const socialCardRef = useRef(null)
  const [directoryContacts, setDirectoryContacts] = useState([])
  const [creatorContacts, setCreatorContacts] = useState([])
  const [addingContact, setAddingContact] = useState(false)
  const [newContactId, setNewContactId] = useState('')
  const [newContactRole, setNewContactRole] = useState('ADMIN')
  const CONTACT_ROLES = ['DISTRIBUTION', 'LEGAL', 'ADMIN', 'MANAGER', 'PUBLISHER', 'A_AND_R', 'MARKETING', 'OTHER']
  const ROLE_DISPLAY = { A_AND_R: 'A&R', DISTRIBUTION: 'Distribution', LEGAL: 'Legal', ADMIN: 'Admin', MANAGER: 'Manager', PUBLISHER: 'Publisher', MARKETING: 'Marketing', OTHER: 'Other' }
  const CONTACT_ROLE_COLORS = {
    DISTRIBUTION: 'bg-blue-100 text-blue-700',
    LEGAL: 'bg-purple-100 text-purple-700',
    ADMIN: 'bg-teal-100 text-teal-700',
    MANAGER: 'bg-orange-100 text-orange-700',
    PUBLISHER: 'bg-indigo-100 text-indigo-700',
    A_AND_R: 'bg-pink-100 text-pink-700',
    MARKETING: 'bg-yellow-100 text-yellow-700',
    OTHER: 'bg-gray-100 text-gray-600',
  }
  const [creatorForm, setCreatorForm] = useState({
    display_name: '',
    legal_name: '',
    email: '',
    roles: [],
    primary_territory: '',
    primary_pro: '',
    primary_ipi: '',
    publisher_contact_id: null,
    admin_contact_id: null,
    bio: '',
    roster_export_fields: [],
    spotify_url: '',
    apple_music_url: '',
    youtube_url: '',
    instagram_url: '',
    twitter_url: '',
    custom_links: []
  })
  
  const loadSongs = async (orgId) => {
    const songsResponse = await axios.get(`/api/songs/org/${orgId}?creator_id=${id}&limit=1000`)
    setSongs(songsResponse.data)
  }
  
  const loadScheduleAData = async () => {
    try {
      const response = await axios.get(`/api/schedule-a/creator/${id}/data`)
      setScheduleAData(response.data)
    } catch (error) {
      console.error('Failed to load Schedule A data:', error)
    }
  }
  
  useEffect(() => {
    async function loadCreatorData() {
      try {
        const creatorResponse = await axios.get(`/api/creators/${id}`)
        const creatorData = creatorResponse.data
        setCreator(creatorData)
        
        const orgResponse = await axios.get('/api/organizations/current')
        const myOrgId = orgResponse.data.id
        setOrganizationName(orgResponse.data.name || '')
        
        const creatorOrgId = creatorData.organization_id
        const isShared = creatorData.is_shared || locationState.is_shared || (creatorOrgId && creatorOrgId !== myOrgId)
        const sharedOrgId = creatorOrgId || locationState.organization_id
        const effectiveOrgId = (isShared && sharedOrgId && sharedOrgId !== myOrgId) ? sharedOrgId : myOrgId
        if (isShared && !creatorData.is_shared) {
          creatorData.is_shared = true
          creatorData.organization_id = sharedOrgId
          setCreator({ ...creatorData })
        }
        if (isShared) {
          try {
            const sharedRes = await axios.get('/api/client-sharing/shared-clients')
            const sharedData = (sharedRes.data || []).find(sc => sc.creator_id === parseInt(id))
            if (sharedData) {
              setSharedModules(sharedData.shared_modules || ['catalog', 'contracts', 'placements', 'royalties', 'contacts'])
            }
          } catch (e) {
            console.error('Failed to load shared modules:', e)
          }
        }
        setOrganizationId(effectiveOrgId)
        
        await loadSongs(effectiveOrgId)

        try {
          const relRes = await axios.get(`/api/releases/org/${effectiveOrgId}?creator_id=${id}`)
          const releases = relRes.data.releases || relRes.data || []
          setCreatorReleases(releases)
          const withArt = releases.filter(r => r.cover_art_url)
          if (withArt.length > 0) {
            const urls = {}
            await Promise.all(withArt.map(async (r) => {
              try {
                const resp = await axios.get(`/api/releases/${r.id}/artwork`, { responseType: 'blob' })
                urls[r.id] = URL.createObjectURL(resp.data)
              } catch {}
            }))
            setReleaseArtworkUrls(prev => ({ ...prev, ...urls }))
          }
        } catch (e) {
          console.error('Failed to load creator releases:', e)
        }

        if (!creatorData.is_shared) {
          try {
            const rosterRes = await axios.get(`/api/creators/org/${myOrgId}`)
            const rosterData = Array.isArray(rosterRes.data) ? rosterRes.data : []
            const match = rosterData.find(c =>
              c.shared && c.display_name.trim().toLowerCase() === creatorData.display_name.trim().toLowerCase() && c.id !== creatorData.id
            )
            if (match && match.song_count > 0) {
              navigate(`/roster/${match.id}`, {
                state: { is_shared: true, organization_id: match.organization_id },
                replace: true
              })
              return
            } else if (match) {
              setSharedVersion(match)
            }
          } catch (e) {}

          try {
            const contactsRes = await axios.get(`/api/creative-directory/org/${myOrgId}`)
            const contactsData = contactsRes.data
            setDirectoryContacts(Array.isArray(contactsData) ? contactsData : contactsData.contacts || [])
          } catch (e) {
            console.error('Failed to load directory contacts:', e)
          }

          try {
            const ccRes = await axios.get(`/api/creators/${id}/contacts`)
            setCreatorContacts(Array.isArray(ccRes.data) ? ccRes.data : ccRes.data.contacts || [])
          } catch (e) {
            console.error('Failed to load creator contacts:', e)
          }
        }
      } catch (error) {
        console.error('Failed to load creator:', error)
      } finally {
        setLoading(false)
      }
    }
    
    loadCreatorData()
  }, [id])

  const loadCreatorContacts = async () => {
    try {
      const res = await axios.get(`/api/creators/${id}/contacts`)
      setCreatorContacts(Array.isArray(res.data) ? res.data : res.data.contacts || [])
    } catch (e) {
      console.error('Failed to load creator contacts:', e)
    }
  }

  const handleAddCreatorContact = async () => {
    if (!newContactId) return
    setAddingContact(true)
    try {
      await axios.post(`/api/creators/${id}/contacts`, {
        contact_id: parseInt(newContactId),
        role: newContactRole
      })
      await loadCreatorContacts()
      setNewContactId('')
      setNewContactRole('ADMIN')
    } catch (e) {
      console.error('Failed to add contact:', e)
      alert(e.response?.data?.detail || 'Failed to add contact')
    } finally {
      setAddingContact(false)
    }
  }

  const handleRemoveCreatorContact = async (contactId) => {
    try {
      await axios.delete(`/api/creators/${id}/contacts/${contactId}`)
      await loadCreatorContacts()
    } catch (e) {
      console.error('Failed to remove contact:', e)
      alert(e.response?.data?.detail || 'Failed to remove contact')
    }
  }
  
  const loadAccounting = async () => {
    if (!organizationId) return
    setAccountingLoading(true)
    try {
      const response = await axios.get(`/api/royalties/creator-accounting/${organizationId}/${id}`)
      setAccountingData(response.data)
    } catch (err) {
      console.error('Failed to load accounting:', err)
    } finally {
      setAccountingLoading(false)
    }
  }

  const loadContracts = async () => {
    setContractsLoading(true)
    try {
      const res = await axios.get(`/api/rights/contracts/creator/${id}`)
      setCreatorContracts(res.data.contracts || [])
    } catch (err) {
      console.error('Failed to load contracts:', err)
    } finally {
      setContractsLoading(false)
    }
  }

  useEffect(() => {
    if (activeTab === 'contracts') {
      loadContracts()
    }
  }, [activeTab, id])

  useEffect(() => {
    if (activeTab === 'accounting' && organizationId) {
      loadAccounting()
    }
  }, [activeTab, organizationId])

  useEffect(() => {
    if (activeTab === 'schedule-a') {
      loadScheduleAData()
    }
  }, [activeTab, id])

  const loadCreditsData = async () => {
    if (!organizationId) return
    setCreditsLoading(true)
    try {
      const res = await axios.get(`/api/streaming-credits/org/${organizationId}/creator/${parseInt(id)}`)
      setCreditsData(res.data)
    } catch (err) {
      console.error('Failed to load credits:', err)
    } finally {
      setCreditsLoading(false)
    }
  }

  const loadCreditsSongs = async () => {
    if (!organizationId) return
    setCreditsSongsLoading(true)
    try {
      const res = await axios.get(`/api/streaming-credits/org/${organizationId}/creator/${parseInt(id)}/songs?per_page=100`)
      setCreditsSongs(res.data.songs || [])
    } catch (err) {
      console.error('Failed to load credits songs:', err)
    } finally {
      setCreditsSongsLoading(false)
    }
  }

  useEffect(() => {
    if (activeTab === 'credits' && organizationId) {
      loadCreditsData()
      loadCreditsSongs()
    }
  }, [activeTab, organizationId, id])

  const handleRefreshCredits = async () => {
    if (!organizationId) return
    setRefreshingCredits(true)
    try {
      await axios.post(`/api/streaming-credits/org/${organizationId}/creator/${parseInt(id)}/refresh`)
      await loadCreditsData()
      await loadCreditsSongs()
    } catch (err) {
      console.error('Failed to refresh credits:', err)
    } finally {
      setRefreshingCredits(false)
    }
  }

  const handleShareCredits = async () => {
    if (!organizationId) return
    setSavingShare(true)
    try {
      const res = await axios.post(`/api/streaming-credits/org/${organizationId}/creator/${parseInt(id)}/share`, {
        is_public: shareSettings.is_public,
        passcode: shareSettings.passcode || ''
      })
      setShareResult(res.data)
    } catch (err) {
      console.error('Failed to manage share link:', err)
      alert('Failed to manage share link')
    } finally {
      setSavingShare(false)
    }
  }

  const handleRevokeShare = async () => {
    if (!organizationId) return
    try {
      await axios.delete(`/api/streaming-credits/org/${organizationId}/creator/${parseInt(id)}/share`)
      setShareResult(null)
      setShowShareModal(false)
    } catch (err) {
      console.error('Failed to revoke share link:', err)
    }
  }

  const handleDownloadSocialCard = useCallback(async (fmt) => {
    if (!creditsData || !creator) return
    const chosenFormat = fmt || socialCardFormat
    setSocialCardFormat(chosenFormat)
    setGeneratingSocialCard(true)
    setShowSocialCard(true)
    setShowFormatMenu(false)
    try {
      await new Promise(r => setTimeout(r, 500))
      const html2canvas = (await import('html2canvas')).default
      const node = socialCardRef.current
      if (!node) return
      const h = chosenFormat === 'square' ? 1080 : 1350
      const canvas = await html2canvas(node, {
        scale: 1,
        useCORS: true,
        allowTaint: true,
        backgroundColor: null,
        width: 1080,
        height: h,
        logging: false,
      })
      let url
      try {
        const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/png'))
        if (blob) {
          url = URL.createObjectURL(blob)
        } else {
          url = canvas.toDataURL('image/png')
        }
      } catch {
        url = canvas.toDataURL('image/png')
      }
      const a = document.createElement('a')
      a.href = url
      const safeName = (creator.display_name || creator.name || 'creator').replace(/[^a-zA-Z0-9]/g, '_')
      const suffix = chosenFormat === 'square' ? '_credits_square' : '_credits'
      a.download = `${safeName}${suffix}.png`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      if (url.startsWith('blob:')) URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Failed to generate social card:', err)
      alert('Failed to generate social card image')
    } finally {
      setGeneratingSocialCard(false)
      setShowSocialCard(false)
    }
  }, [creditsData, creator, socialCardFormat])

  const formatStreamCount = (num) => {
    if (!num || num === 0) return '0'
    if (num >= 1000000000) return (num / 1000000000).toFixed(1) + 'B'
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K'
    return num.toLocaleString()
  }

  const PLATFORM_ICONS = {
    SPOTIFY: { color: '#1DB954', label: 'Spotify' },
    APPLE_MUSIC: { color: '#FA233B', label: 'Apple Music' },
    YOUTUBE_MUSIC: { color: '#FF0000', label: 'YouTube Music' },
    AMAZON_MUSIC: { color: '#FF9900', label: 'Amazon Music' },
    TIDAL: { color: '#000000', label: 'Tidal' },
    DEEZER: { color: '#A238FF', label: 'Deezer' },
  }

  const handleScheduleAExportCSV = async () => {
    try {
      const response = await axios.get(`/api/schedule-a/creator/${id}/csv`, {
        responseType: 'blob'
      })
      
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `Schedule_A_${creator.display_name.replace(/ /g, '_')}.csv`)
      document.body.appendChild(link)
      link.click()
      link.remove()
    } catch (error) {
      console.error('Failed to export Schedule A CSV:', error)
    }
  }
  
  const handleScheduleAExportPDF = async () => {
    try {
      const response = await axios.get(`/api/schedule-a/creator/${id}/schedule-a-pdf`, {
        responseType: 'blob'
      })
      
      const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `Schedule_A_${creator.display_name.replace(/ /g, '_')}.pdf`)
      document.body.appendChild(link)
      link.click()
      link.remove()
    } catch (error) {
      console.error('Failed to export Schedule A PDF:', error)
    }
  }

  const handleCatalogDocExportPDF = async () => {
    try {
      const response = await axios.get(`/api/schedule-a/creator/${id}/pdf`, {
        responseType: 'blob'
      })
      
      const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `Catalog_Doc_${creator.display_name.replace(/ /g, '_')}.pdf`)
      document.body.appendChild(link)
      link.click()
      link.remove()
    } catch (error) {
      console.error('Failed to export Catalog Doc PDF:', error)
    }
  }
  
  const handleScheduleAUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    
    const ext = file.name.toLowerCase()
    if (!ext.endsWith('.csv') && !ext.endsWith('.xlsx') && !ext.endsWith('.xls')) {
      setUploadFeedback({ msg: 'Please upload a CSV or Excel file (.csv, .xlsx, .xls)', type: 'error' })
      setTimeout(() => setUploadFeedback(null), 4000)
      return
    }
    
    setUploadingScheduleA(true)
    setUploadFeedback(null)
    
    try {
      const token = localStorage.getItem('token')
      const formData = new FormData()
      formData.append('file', file)
      
      const creatorNameParam = encodeURIComponent(creator.display_name)
      const response = await axios.post(
        `/api/schedule-a/upload/${organizationId}?creator_name=${creatorNameParam}`,
        formData,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          }
        }
      )
      
      const data = response.data
      const parts = []
      if (data.songs_created) parts.push(`${data.songs_created} songs created`)
      if (data.songs_updated) parts.push(`${data.songs_updated} songs updated`)
      if (data.songs_skipped) parts.push(`${data.songs_skipped} skipped`)
      
      setUploadFeedback({ msg: `Import complete: ${parts.join(', ')}`, type: 'success' })
      setTimeout(() => setUploadFeedback(null), 5000)
      
      loadCreator()
      loadScheduleAData()
    } catch (error) {
      const detail = error.response?.data?.detail || 'Failed to upload file. Please check format.'
      setUploadFeedback({ msg: detail, type: 'error' })
      setTimeout(() => setUploadFeedback(null), 5000)
    } finally {
      setUploadingScheduleA(false)
      e.target.value = ''
    }
  }
  
  const normalizeDollarField = (val) => {
    if (val === null || val === undefined) return ''
    const s = String(val).toLowerCase()
    if (s === 'n/a' || s === 'na') return 'N/A'
    if (s === 'true' || s === 'yes' || s === 'false' || s === 'no' || s === '') return ''
    return String(val)
  }

  const normalizeTriState = (val) => {
    if (val === null || val === undefined || val === '') return ''
    const s = String(val).toLowerCase()
    if (s === 'n/a' || s === 'na') return 'N/A'
    if (s === 'true' || s === 'yes') return 'Yes'
    if (s === 'false' || s === 'no') return 'No'
    return val
  }

  const startEdit = (song) => {
    setEditingSong(song.id)
    setEditForm({
      title: song.title || '',
      primary_artist: song.primary_artist || '',
      publishing_percentage: song.publishing_percentage || '',
      master_percentage: song.master_percentage || '',
      advance_amount: song.advance_amount ? (song.advance_amount / 100) : '',
      label: song.label || '',
      is_registered_with_pro: song.is_registered_with_pro || false,
      is_registered_with_dsp: normalizeDollarField(song.is_registered_with_dsp),
      soundexchange_registered: normalizeTriState(song.soundexchange_registered),
      mlc_registered: normalizeTriState(song.mlc_registered),
      is_paid: normalizeTriState(song.is_paid),
      is_invoiced: normalizeDollarField(song.is_invoiced),
      has_contract_executed: song.has_contract_executed || false,
      is_released: song.is_released || false,
      spotify_link: song.spotify_link || '',
      notes: song.notes || '',
      credit_role: song.credit_role || 'ARTIST'
    })
  }
  
  const cancelEdit = () => {
    setEditingSong(null)
    setEditForm({})
  }
  
  const saveEdit = async (songId) => {
    setSaving(true)
    try {
      const payload = {
        title: editForm.title || undefined,
        primary_artist: editForm.primary_artist || undefined,
        publishing_percentage: editForm.publishing_percentage === '' ? null : Math.min(parseFloat(editForm.publishing_percentage), 100),
        master_percentage: editForm.master_percentage === '' ? null : Math.min(parseFloat(editForm.master_percentage), 100),
        advance_amount: editForm.advance_amount === '' ? null : Math.round(parseFloat(editForm.advance_amount) * 100),
        label: editForm.label || null,
        is_registered_with_pro: editForm.is_registered_with_pro,
        is_registered_with_dsp: editForm.is_registered_with_dsp || null,
        soundexchange_registered: editForm.soundexchange_registered || null,
        mlc_registered: editForm.mlc_registered || null,
        is_paid: editForm.is_paid || null,
        is_invoiced: editForm.is_invoiced || null,
        has_contract_executed: editForm.has_contract_executed,
        is_released: editForm.is_released,
        spotify_link: editForm.spotify_link || null,
        notes: editForm.notes || null
      }

      setSongs(prev => prev.map(s => s.id === songId ? {
        ...s,
        ...payload,
        advance_amount: payload.advance_amount,
      } : s))
      setEditingSong(null)
      setEditForm({})
      
      await axios.patch(`/api/songs/${songId}`, payload)
      
      const orgResponse = await axios.get('/api/organizations/current')
      await loadSongs(orgResponse.data.id)
    } catch (error) {
      console.error('Failed to update song:', error)
      alert('Failed to save changes')
      const orgResponse = await axios.get('/api/organizations/current')
      await loadSongs(orgResponse.data.id)
    } finally {
      setSaving(false)
    }
  }

  const handleReleasedToggle = async (song) => {
    const newReleasedStatus = !song.is_released
    if (newReleasedStatus && !song.spotify_link) {
      setSpotifyModalSong(song)
      setSpotifyLinkInput('')
      setShowSpotifyModal(true)
    } else {
      try {
        await axios.patch(`/api/songs/${song.id}`, { is_released: newReleasedStatus })
        const orgResponse = await axios.get('/api/organizations/current')
        await loadSongs(orgResponse.data.id)
      } catch (error) {
        console.error('Failed to update released status:', error)
      }
    }
  }

  const handleSpotifyModalSave = async () => {
    if (!spotifyModalSong) return
    setSavingSpotifyLink(true)
    try {
      await axios.patch(`/api/songs/${spotifyModalSong.id}`, { 
        is_released: true,
        spotify_link: spotifyLinkInput || null
      })
      const orgResponse = await axios.get('/api/organizations/current')
      await loadSongs(orgResponse.data.id)
      setShowSpotifyModal(false)
      setSpotifyModalSong(null)
      setSpotifyLinkInput('')
    } catch (error) {
      console.error('Failed to save Spotify link:', error)
    } finally {
      setSavingSpotifyLink(false)
    }
  }

  const handleAddSong = async (e) => {
    e.preventDefault()
    if (!newSong.title.trim()) return
    
    setAddingSong(true)
    try {
      const payload = {
        title: newSong.title,
        primary_artist: newSong.primary_artist || creator.display_name,
        isrc: newSong.isrc || null,
        iswc: newSong.iswc || null,
        project_title: newSong.project_title || null,
        release_date: newSong.release_date || null,
        label: newSong.label || null,
        publishing_percentage: newSong.publishing_percentage ? parseFloat(newSong.publishing_percentage) : null,
        master_percentage: newSong.master_percentage ? parseFloat(newSong.master_percentage) : null,
        advance_amount: newSong.advance_amount ? parseFloat(newSong.advance_amount) : null,
        notes: newSong.notes || null
      }
      
      const response = await axios.post(`/api/songs/org/${organizationId}`, payload)
      const newSongData = response.data
      
      await axios.post(`/api/songs/${newSongData.id}/credits`, {
        creator_id: parseInt(id),
        role: newSong.credit_role || 'ARTIST',
        share_percentage: newSong.publishing_percentage ? parseFloat(newSong.publishing_percentage) : 100
      })
      
      await loadSongs(organizationId)
      
      setShowAddSongModal(false)
      setNewSong({
        title: '',
        primary_artist: '',
        isrc: '',
        iswc: '',
        project_title: '',
        release_date: '',
        label: '',
        publishing_percentage: '',
        master_percentage: '',
        advance_amount: '',
        notes: '',
        credit_role: 'ARTIST'
      })

      setSelectedSongForDetail(newSongData)
    } catch (error) {
      console.error('Failed to add song:', error)
      alert(error.response?.data?.detail || 'Failed to add song')
    } finally {
      setAddingSong(false)
    }
  }

  const ROLE_OPTIONS = ['ARTIST', 'PRIMARY_ARTIST', 'FEATURED_ARTIST', 'SONGWRITER', 'PRODUCER', 'COMPOSER', 'LYRICIST']
  const PRO_OPTIONS = ['ASCAP', 'BMI', 'PRS', 'SESAC', 'OTHER']

  const openEditCreatorModal = () => {
    setCreatorForm({
      display_name: creator.display_name || '',
      legal_name: creator.legal_name || '',
      email: creator.email || '',
      roles: creator.roles || [],
      primary_territory: creator.primary_territory || '',
      primary_pro: creator.primary_pro || '',
      primary_ipi: creator.primary_ipi || '',
      publisher_contact_id: creator.publisher_contact_id || null,
      admin_contact_id: creator.admin_contact_id || null,
      bio: creator.bio || '',
      roster_export_fields: creator.roster_export_fields || [],
      spotify_url: creator.spotify_url || '',
      apple_music_url: creator.apple_music_url || '',
      youtube_url: creator.youtube_url || '',
      instagram_url: creator.instagram_url || '',
      twitter_url: creator.twitter_url || '',
      custom_links: creator.custom_links ? [...creator.custom_links.map(l => ({...l}))] : []
    })
    setShowEditCreatorModal(true)
  }

  const handleCreatorRoleToggle = (role) => {
    setCreatorForm(prev => ({
      ...prev,
      roles: prev.roles.includes(role)
        ? prev.roles.filter(r => r !== role)
        : [...prev.roles, role]
    }))
  }

  const handleUpdateCreator = async (e) => {
    e.preventDefault()
    if (!creatorForm.display_name.trim()) return
    
    setEditingCreator(true)
    try {
      const response = await axios.put(`/api/creators/${id}`, creatorForm)
      setCreator(prev => ({ ...prev, ...response.data }))
      setShowEditCreatorModal(false)
    } catch (error) {
      console.error('Failed to update creator:', error)
      alert(error.response?.data?.detail || 'Failed to update creator')
    } finally {
      setEditingCreator(false)
    }
  }
  
  const StatusBadge = ({ value, label }) => {
    const strVal = String(value ?? '').toLowerCase()
    if (value === true || strVal === 'yes' || strVal === 'true') {
      return (
        <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium" style={{ background: 'rgba(52, 199, 89, 0.15)', color: '#5B9A6E' }}>
          <CheckCircleIcon className="w-3 h-3" />
          {label ? `${label}` : 'Yes'}
        </span>
      )
    } else if (value === false || strVal === 'no' || strVal === 'false') {
      return (
        <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium" style={{ background: 'rgba(255, 59, 48, 0.15)', color: '#C47068' }}>
          <XCircleIcon className="w-3 h-3" />
          {label ? `${label}` : 'No'}
        </span>
      )
    } else if (strVal === 'n/a' || strVal === 'na') {
      return (
        <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium" style={{ background: 'rgba(0, 0, 0, 0.05)', color: '#7A8580' }}>
          <MinusCircleIcon className="w-3 h-3" />
          {label ? `${label}: N/A` : 'N/A'}
        </span>
      )
    } else if (value === null || value === undefined || strVal === '') {
      return (
        <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium" style={{ background: 'rgba(0, 0, 0, 0.03)', color: '#A8B0AC' }}>
          <MinusCircleIcon className="w-3 h-3" />
          {label ? `${label}: —` : '—'}
        </span>
      )
    } else {
      const num = parseFloat(value)
      return (
        <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium" style={{ background: 'rgba(52, 199, 89, 0.15)', color: '#5B9A6E' }}>
          <CheckCircleIcon className="w-3 h-3" />
          {label ? `${label}: ` : ''}{isNaN(num) ? 'Yes' : `$${num.toLocaleString()}`}
        </span>
      )
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full bg-[#F5F7F4]">
        <div className="text-[#7A8580]">Loading creator...</div>
      </div>
    )
  }
  
  if (!creator) {
    return (
      <div className="flex items-center justify-center h-full bg-[#F5F7F4]">
        <div className="text-[#7A8580]">Creator not found</div>
      </div>
    )
  }
  
  const placedSongs = songs.filter(s => s.is_paid === 'Yes' || s.is_paid === true)
  const registeredPro = songs.filter(s => s.is_registered_with_pro).length
  const registeredFee = songs.filter(s => {
    const v = s.is_registered_with_dsp
    return v === 'Yes' || v === true || (v && v !== 'N/A' && v !== 'No' && !isNaN(parseFloat(v)))
  }).length
  const totalAdvance = songs.reduce((sum, s) => sum + (s.advance_amount || 0), 0) / 100
  
  const toggleSongSelection = (songId) => {
    setSelectedSongs(prev => {
      const next = new Set(prev)
      if (next.has(songId)) next.delete(songId)
      else next.add(songId)
      return next
    })
  }

  const toggleSelectAll = () => {
    if (selectedSongs.size === songs.length) {
      setSelectedSongs(new Set())
    } else {
      setSelectedSongs(new Set(songs.map(s => s.id)))
    }
  }

  const handleSort = (column) => {
    if (sortColumn === column) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc')
    } else {
      setSortColumn(column)
      setSortDirection('asc')
    }
  }

  const sortedSongs = [...songs].sort((a, b) => {
    if (!sortColumn) return 0
    const dir = sortDirection === 'asc' ? 1 : -1
    let aVal = a[sortColumn]
    let bVal = b[sortColumn]
    if (sortColumn === 'publishing_percentage' || sortColumn === 'advance_amount') {
      aVal = parseFloat(aVal) || 0
      bVal = parseFloat(bVal) || 0
      return (aVal - bVal) * dir
    }
    if (sortColumn === 'is_registered_with_pro' || sortColumn === 'is_paid' || sortColumn === 'is_released' || sortColumn === 'has_contract_executed' || sortColumn === 'soundexchange_registered' || sortColumn === 'mlc_registered' || sortColumn === 'is_invoiced') {
      const toBool = (v) => v === true || v === 'Yes' || v === 'true' ? 1 : 0
      return (toBool(aVal) - toBool(bVal)) * dir
    }
    aVal = String(aVal || '').toLowerCase()
    bVal = String(bVal || '').toLowerCase()
    if (aVal < bVal) return -1 * dir
    if (aVal > bVal) return 1 * dir
    return 0
  })

  const SortHeader = ({ column, children, className = '' }) => (
    <th
      className={`px-4 py-3 font-semibold text-[#3D4A44] cursor-pointer select-none hover:bg-[#EEF1EC] transition-colors ${className}`}
      onClick={() => handleSort(column)}
    >
      <span className="inline-flex items-center gap-1">
        {children}
        {sortColumn === column ? (
          <span className="text-[#5B8A72]">{sortDirection === 'asc' ? '▲' : '▼'}</span>
        ) : (
          <span className="text-[#B0BDB4]">⇅</span>
        )}
      </span>
    </th>
  )

  const handleCreateFee = async (e) => {
    e.preventDefault()
    setSavingFee(true)
    try {
      await axios.post(`/api/royalties/fees/${organizationId}`, {
        creator_id: parseInt(id),
        fee_type: feeForm.fee_type,
        description: feeForm.description,
        amount_cents: Math.round(parseFloat(feeForm.amount) * 100),
        fee_date: feeForm.fee_date || null,
        notes: feeForm.notes || null,
      })
      setShowAddFeeModal(false)
      setFeeForm({ fee_type: 'MANAGEMENT_FEE', description: '', amount: '', fee_date: '', notes: '' })
      loadAccounting()
    } catch (err) {
      alert('Failed to create fee: ' + (err.response?.data?.detail || err.message))
    } finally {
      setSavingFee(false)
    }
  }

  const handleCreateAdvance = async (e) => {
    e.preventDefault()
    setSavingAdvance(true)
    try {
      await axios.post(`/api/royalties/advances/${organizationId}`, {
        creator_id: parseInt(id),
        description: advanceForm.description,
        amount_cents: Math.round(parseFloat(advanceForm.amount) * 100),
        advance_date: advanceForm.advance_date || null,
        notes: advanceForm.notes || null,
      })
      setShowAddAdvanceModal(false)
      setAdvanceForm({ description: '', amount: '', advance_date: '', notes: '' })
      loadAccounting()
    } catch (err) {
      alert('Failed to create advance: ' + (err.response?.data?.detail || err.message))
    } finally {
      setSavingAdvance(false)
    }
  }

  const handleDeleteFee = async (feeId) => {
    if (!confirm('Delete this fee?')) return
    try {
      await axios.delete(`/api/royalties/fees/${organizationId}/${feeId}`)
      loadAccounting()
    } catch (err) {
      alert('Failed to delete fee')
    }
  }

  const handleDeleteAdvance = async (advanceId) => {
    if (!confirm('Delete this advance?')) return
    try {
      await axios.delete(`/api/royalties/advances/${organizationId}/${advanceId}`)
      loadAccounting()
    } catch (err) {
      alert('Failed to delete advance')
    }
  }

  const handleDuplicateSong = async (songId, e) => {
    if (e) e.stopPropagation()
    try {
      const res = await axios.post(`/api/songs/${songId}/duplicate`)
      if (organizationId) await loadSongs(organizationId)
      setSelectedSongForDetail(res.data)
    } catch (error) {
      console.error('Failed to duplicate song:', error)
      alert(error.response?.data?.detail || 'Failed to duplicate song')
    }
  }

  const handleBulkDelete = async () => {
    if (selectedSongs.size === 0) return
    setDeleting(true)
    try {
      await axios.post('/api/songs/bulk-delete', { song_ids: Array.from(selectedSongs) })
      setSelectedSongs(new Set())
      setShowDeleteConfirm(false)
      if (organizationId) await loadSongs(organizationId)
    } catch (err) {
      alert('Failed to delete songs: ' + (err.response?.data?.detail || err.message))
    } finally {
      setDeleting(false)
    }
  }

  const handleMergeSongs = async () => {
    if (!mergePrimaryId || selectedSongs.size < 2) return
    setMerging(true)
    try {
      const mergeIds = Array.from(selectedSongs).filter(id => id !== mergePrimaryId)
      await axios.post(`/api/songs/org/${organizationId}/merge`, {
        primary_song_id: mergePrimaryId,
        merge_song_ids: mergeIds,
      })
      setShowMergeModal(false)
      setSelectedSongs(new Set())
      setMergePrimaryId(null)
      if (organizationId) await loadSongs(organizationId)
    } catch (err) {
      alert('Failed to merge songs: ' + (err.response?.data?.detail || err.message))
    } finally {
      setMerging(false)
    }
  }

  const PARTY_ROLES = ['LICENSOR', 'LICENSEE', 'PUBLISHER', 'ARTIST', 'LABEL', 'MANAGER', 'PRODUCER', 'OTHER']

  const handleCreateContract = async () => {
    if (!createContractForm.title.trim()) {
      setCreateContractError('Please enter a contract title.')
      return
    }
    setCreateContractError('')
    setCreateContractLoading(true)
    try {
      const payload = { ...createContractForm }
      if (payload.advance_amount) payload.advance_amount = parseFloat(payload.advance_amount)
      else delete payload.advance_amount
      if (!payload.start_date) delete payload.start_date
      if (!payload.end_date) delete payload.end_date
      if (!payload.reference_number) delete payload.reference_number
      if (payload.territory && typeof payload.territory === 'string') {
        payload.territory = payload.territory.split(',').map(t => t.trim()).filter(Boolean)
      } else {
        payload.territory = []
      }
      payload.creator_id = parseInt(id)
      const creatorName = creator?.display_name || creator?.legal_name || 'Client'
      const defaultParty = { party_name: creatorName, party_role: 'ARTIST', creator_id: parseInt(id) }
      const allParties = [defaultParty, ...createContractParties.map(p => {
        const cleaned = { ...p }
        if (!cleaned.contact_email) delete cleaned.contact_email
        return cleaned
      })]
      payload.parties = allParties
      await axios.post(`/api/rights/contracts/org/${organizationId}`, payload)
      setShowCreateContractModal(false)
      setCreateContractForm({
        title: '', contract_type: 'MASTER', payment_direction: 'INCOMING', status: 'DRAFT',
        reference_number: '', start_date: '', end_date: '', territory: '',
        advance_amount: '', advance_currency: 'USD', notes: '', terms_summary: ''
      })
      setCreateContractParties([])
      setCreateContractError('')
      await loadContracts()
    } catch (error) {
      const detail = error.response?.data?.detail
      setCreateContractError(typeof detail === 'string' ? detail : 'Failed to create contract. Please try again.')
    } finally {
      setCreateContractLoading(false)
    }
  }

  const handleUploadDoc = async () => {
    if (!uploadDocFile) {
      setUploadDocError('Please select a file to upload.')
      return
    }
    if (!uploadDocContractId) {
      setUploadDocError('Please select which contract to attach this document to.')
      return
    }
    setUploadDocError('')
    setUploadDocLoading(true)
    try {
      const formData = new FormData()
      formData.append('file', uploadDocFile)
      formData.append('description', uploadDocDescription || uploadDocFile.name)
      await axios.post(`/api/rights/contracts/${uploadDocContractId}/documents`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      setShowUploadDocModal(false)
      setUploadDocFile(null)
      setUploadDocContractId('')
      setUploadDocDescription('')
      setUploadDocError('')
      await loadContracts()
    } catch (error) {
      const detail = error.response?.data?.detail
      setUploadDocError(typeof detail === 'string' ? detail : 'Failed to upload document.')
    } finally {
      setUploadDocLoading(false)
    }
  }

  const allTabs = [
    { id: 'overview', label: 'Overview', module: null },
    { id: 'records', label: `Records (${songs.length})`, module: 'catalog' },
    { id: 'releases', label: `Artist Releases (${creatorReleases.length})`, module: 'catalog' },
    { id: 'contracts', label: `Contracts${creatorContracts.length ? ` (${creatorContracts.length})` : ''}`, module: 'contracts' },
    { id: 'credits', label: 'Credits', module: null },
    { id: 'actions', label: 'Actions', module: null },
    { id: 'accounting', label: 'Accounting', module: 'royalties' },
    { id: 'schedule-a', label: 'Schedule A', module: 'contracts' }
  ]
  const tabs = sharedModules
    ? allTabs.filter(tab => !tab.module || sharedModules.includes(tab.module))
    : allTabs
  
  return (
    <div className="min-h-screen bg-[#F5F7F4]">
      <div className="relative h-72 overflow-hidden">
        {creator.hero_image_url ? (
          <>
            <img 
              src={`/api/creators/${creator.id}/image`} 
              alt=""
              className="absolute inset-0 w-full h-full object-cover scale-110 blur-2xl brightness-75"
            />
            <div className="absolute inset-0 bg-black/30"></div>
          </>
        ) : (
          <div className="absolute inset-0" style={{ background: 'linear-gradient(135deg, #5B8A72 0%, #7BA594 100%)' }}></div>
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent"></div>
        
        <div className="relative h-full flex flex-col justify-end p-4 sm:p-8">
          <Link 
            to="/roster" 
            className="inline-flex items-center space-x-2 text-white/90 hover:text-white mb-4 w-fit transition-colors"
          >
            <ArrowLeftIcon className="w-5 h-5" />
            <span>Back to Roster</span>
          </Link>
          
          <div className="flex items-center gap-5 mb-2">
            {creator.hero_image_url && (
              <img 
                src={`/api/creators/${creator.id}/image`} 
                alt={creator.display_name}
                className="w-20 h-20 rounded-xl object-cover border-2 border-white/30 shadow-lg flex-shrink-0"
              />
            )}
            <div>
              <div className="flex items-center gap-3 mb-1">
                <h1 className="text-3xl sm:text-5xl font-semibold text-white">{creator.display_name}</h1>
                <button
                  onClick={openEditCreatorModal}
                  className="p-2 rounded-full bg-white/20 hover:bg-white/30 transition-colors"
                  title="Edit Creator"
                >
                  <PencilIcon className="w-5 h-5 text-white" />
                </button>
                <button
                  onClick={() => navigate(`/valuation?creatorId=${creator.id}`)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/20 hover:bg-white/30 transition-colors text-white text-xs font-medium"
                  title="Run a catalog valuation scoped to this client"
                >
                  <SparklesIcon className="w-4 h-4" />
                  <span>Run Valuation</span>
                </button>
              </div>
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-white/90">
                <span className="text-base sm:text-lg">{creator.roles?.join(', ') || 'Producer'}</span>
                <span className="hidden sm:inline">·</span>
                <span>{songs.length} songs</span>
                <span>·</span>
                <span>{placedSongs.length} paid placements</span>
                <span className="hidden sm:inline">·</span>
                <span className="hidden sm:inline">${totalAdvance.toLocaleString()} advances</span>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <div className="bg-white border-b border-[rgba(59,77,67,0.08)] sticky top-0 z-10">
        <div className="px-4 sm:px-8 overflow-x-auto">
          <div className="flex space-x-4 sm:space-x-8 min-w-max">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`py-4 px-2 border-b-2 font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'border-[#5B8A72] text-[#5B8A72]'
                    : 'border-transparent text-[#7A8580] hover:text-[#3D4A44]'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>
      
      {sharedVersion && songs.length === 0 && (
        <div className="mx-4 sm:mx-8 mt-4 p-4 bg-blue-50 border border-blue-200 rounded-xl flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-blue-800">
              A shared version of this creator is available with {sharedVersion.song_count} song{sharedVersion.song_count !== 1 ? 's' : ''}
            </p>
            <p className="text-xs text-blue-600 mt-0.5">Shared from {sharedVersion.shared_from}</p>
          </div>
          <Link
            to={`/roster/${sharedVersion.id}`}
            state={{ is_shared: true, organization_id: sharedVersion.organization_id }}
            className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors whitespace-nowrap ml-4"
          >
            View Shared Profile
          </Link>
        </div>
      )}

      <div className="p-4 sm:p-8">
        {activeTab === 'overview' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              <div className="bg-white rounded-[18px] p-7" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                <h2 className="text-xl font-semibold text-[#3D4A44] mb-5">Performance</h2>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <p className="text-sm text-[#7A8580] mb-1">Total Songs</p>
                    <p className="text-2xl font-semibold text-[#3D4A44]">{songs.length}</p>
                  </div>
                  <div>
                    <p className="text-sm text-[#7A8580] mb-1">Paid Placements</p>
                    <p className="text-2xl font-semibold text-[#5B9A6E]">{placedSongs.length}</p>
                  </div>
                  <div>
                    <p className="text-sm text-[#7A8580] mb-1">PRO Registered</p>
                    <p className="text-2xl font-semibold text-[#5A8A9A]">{registeredPro}</p>
                  </div>
                  <div>
                    <p className="text-sm text-[#7A8580] mb-1">Fee Received</p>
                    <p className="text-2xl font-semibold text-[#5B8A72]">{registeredFee}</p>
                  </div>
                </div>
              </div>
              
              <div className="bg-white rounded-[18px] p-7" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                <h2 className="text-xl font-semibold text-[#3D4A44] mb-5">Financials</h2>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <div>
                    <p className="text-sm text-[#7A8580] mb-1">Total Advances</p>
                    <p className="text-2xl font-semibold text-[#5B9A6E]">${totalAdvance.toLocaleString()}</p>
                  </div>
                  <div>
                    <p className="text-sm text-[#7A8580] mb-1">Avg Publishing %</p>
                    <p className="text-2xl font-semibold text-[#3D4A44]">
                      {songs.filter(s => s.publishing_percentage).length > 0 
                        ? (songs.reduce((sum, s) => sum + (s.publishing_percentage || 0), 0) / songs.filter(s => s.publishing_percentage).length).toFixed(1)
                        : 0}%
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-[#7A8580] mb-1">Avg Health Score</p>
                    <p className="text-2xl font-semibold text-[#3D4A44]">{creator.avg_health_score?.toFixed(0) || 0}%</p>
                  </div>
                </div>
              </div>
              
              <div className="bg-white rounded-[18px] p-7" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                <h2 className="text-xl font-semibold text-[#3D4A44] mb-5">Recent Songs</h2>
                <div className="space-y-3">
                  {songs.slice(0, 5).map((song) => (
                    <div key={song.id} className="flex items-center justify-between p-4 bg-[#F8F8FB] rounded-xl">
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-[#3D4A44] truncate">{song.title}</p>
                        <p className="text-sm text-[#7A8580]">{song.primary_artist}</p>
                      </div>
                      <div className="flex items-center gap-2 ml-4">
                        <StatusBadge value={song.is_paid} label="Paid" />
                        <StatusBadge value={song.is_registered_with_pro} label="PRO" />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            
            <div className="space-y-6">
              <div className="bg-white rounded-[18px] p-7" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                <h2 className="text-xl font-semibold text-[#3D4A44] mb-5">Details</h2>
                <div className="space-y-4 text-sm">
                  {creator.legal_name && (
                    <div>
                      <p className="text-[#7A8580]">Legal Name</p>
                      <p className="font-medium text-[#3D4A44]">{creator.legal_name}</p>
                    </div>
                  )}
                  {creator.primary_territory && (
                    <div>
                      <p className="text-[#7A8580]">Territory</p>
                      <p className="font-medium text-[#3D4A44]">{creator.primary_territory}</p>
                    </div>
                  )}
                  {creator.primary_pro && (
                    <div>
                      <p className="text-[#7A8580]">PRO</p>
                      <p className="font-medium text-[#3D4A44]">{creator.primary_pro}</p>
                    </div>
                  )}
                  {creator.primary_ipi && (
                    <div>
                      <p className="text-[#7A8580]">IPI</p>
                      <p className="font-medium text-[#3D4A44]">{creator.primary_ipi}</p>
                    </div>
                  )}
                  {creator.publisher_contact && (
                    <div className="flex items-center justify-between py-2 border-b border-[rgba(59,77,67,0.06)]">
                      <span className="text-[13px] text-[#7A8580]">Publisher</span>
                      <Link to="/directory" className="text-[13px] font-medium text-[#5B8A72] hover:underline">
                        {creator.publisher_contact.display_name}{creator.publisher_contact.company ? ` (${creator.publisher_contact.company})` : ''}
                      </Link>
                    </div>
                  )}
                  {creator.admin_contact && (
                    <div className="flex items-center justify-between py-2 border-b border-[rgba(59,77,67,0.06)]">
                      <span className="text-[13px] text-[#7A8580]">Administrator</span>
                      <Link to="/directory" className="text-[13px] font-medium text-[#5B8A72] hover:underline">
                        {creator.admin_contact.display_name}{creator.admin_contact.company ? ` (${creator.admin_contact.company})` : ''}
                      </Link>
                    </div>
                  )}
                </div>
              </div>

              <div className="bg-white rounded-[18px] p-7" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                <h2 className="text-xl font-semibold text-[#3D4A44] mb-5">Contacts</h2>
                {creatorContacts.length > 0 ? (
                  <div className="space-y-3 mb-4">
                    {creatorContacts.map((cc) => (
                      <div key={cc.id || cc.contact_id} className="flex items-start justify-between p-3 bg-[#F8F8FB] rounded-xl">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <p className="font-medium text-[#3D4A44] text-sm truncate">{cc.display_name || cc.contact_name || cc.name || 'Contact'}</p>
                            <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${CONTACT_ROLE_COLORS[cc.role] || CONTACT_ROLE_COLORS.OTHER}`}>
                              {ROLE_DISPLAY[cc.role] || (cc.role || 'Other').replace(/_/g, ' ')}
                            </span>
                          </div>
                          {(cc.email || cc.contact_email) && (
                            <p className="text-xs text-[#7A8580]">
                              <a href={`mailto:${cc.email || cc.contact_email}`} className="hover:text-[#5B8A72] transition-colors">{cc.email || cc.contact_email}</a>
                            </p>
                          )}
                          {(cc.phone || cc.contact_phone) && (
                            <p className="text-xs text-[#7A8580] mt-0.5">{cc.phone || cc.contact_phone}</p>
                          )}
                        </div>
                        <button
                          onClick={() => handleRemoveCreatorContact(cc.id)}
                          className="p-1 text-[#7A8580] hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors flex-shrink-0 ml-2"
                          title="Remove contact"
                        >
                          <XMarkIcon className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-[#7A8580] mb-4">No contacts assigned yet.</p>
                )}
                <div className="border-t border-[rgba(59,77,67,0.06)] pt-4 space-y-2">
                  <select
                    value={newContactId}
                    onChange={e => setNewContactId(e.target.value)}
                    className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 text-sm bg-white text-[#3D4A44] focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                  >
                    <option value="">Select a contact...</option>
                    {directoryContacts
                      .filter(dc => !creatorContacts.some(cc => (cc.contact_id || cc.id) === dc.id))
                      .map(dc => (
                        <option key={dc.id} value={dc.id}>{dc.display_name}{dc.email ? ` (${dc.email})` : ''}</option>
                      ))
                    }
                  </select>
                  <div className="flex items-center gap-2">
                    <select
                      value={newContactRole}
                      onChange={e => setNewContactRole(e.target.value)}
                      className="flex-1 border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 text-sm bg-white text-[#3D4A44] focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                    >
                      {CONTACT_ROLES.map(role => (
                        <option key={role} value={role}>{ROLE_DISPLAY[role] || role.replace(/_/g, ' ')}</option>
                      ))}
                    </select>
                    <button
                      onClick={handleAddCreatorContact}
                      disabled={!newContactId || addingContact}
                      className="flex items-center gap-1.5 px-4 py-2 bg-[#5B8A72] text-white rounded-lg text-sm font-medium hover:bg-[#4A7862] transition-colors disabled:opacity-50"
                    >
                      <PlusIcon className="w-4 h-4" />
                      {addingContact ? 'Adding...' : 'Add'}
                    </button>
                  </div>
                </div>
              </div>

              {creator.bio && (
                <div className="bg-white rounded-[18px] p-7" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                  <h2 className="text-xl font-semibold text-[#3D4A44] mb-4">About</h2>
                  <p className="text-sm text-[#7A8580] leading-relaxed whitespace-pre-line">{creator.bio}</p>
                </div>
              )}

              {(creator.spotify_url || creator.apple_music_url || creator.youtube_url || creator.instagram_url || creator.twitter_url || (creator.custom_links && creator.custom_links.length > 0)) && (
                <div className="bg-white rounded-[18px] p-7" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                  <h2 className="text-xl font-semibold text-[#3D4A44] mb-4">Links & Profiles</h2>
                  <div className="space-y-2">
                    {creator.spotify_url && (
                      <a href={creator.spotify_url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-3 px-4 py-2.5 rounded-xl hover:bg-[#F5F7F4] transition-colors group">
                        <svg className="w-5 h-5 flex-shrink-0" viewBox="0 0 24 24" fill="#1DB954"><path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/></svg>
                        <span className="text-sm font-medium text-[#3D4A44] group-hover:text-[#1DB954] transition-colors">Spotify</span>
                      </a>
                    )}
                    {creator.apple_music_url && (
                      <a href={creator.apple_music_url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-3 px-4 py-2.5 rounded-xl hover:bg-[#F5F7F4] transition-colors group">
                        <svg className="w-5 h-5 flex-shrink-0" viewBox="0 0 24 24"><defs><linearGradient id="am-grad" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stopColor="#FA233B"/><stop offset="100%" stopColor="#FB5C74"/></linearGradient></defs><path d="M23.994 6.124a9.23 9.23 0 00-.24-2.19c-.317-1.31-1.062-2.31-2.18-3.043A5.022 5.022 0 0019.7.28C18.96.094 18.2.017 17.44.001 17.2-.003 16.96 0 16.72 0H7.28c-.24 0-.48-.003-.72.001C5.8.017 5.04.094 4.3.28c-.9.23-1.7.67-2.38 1.31-.55.5-.96 1.12-1.24 1.83-.24.6-.36 1.23-.4 1.88-.04.5-.06 1-.07 1.5V17.2c.01.5.03 1 .07 1.5.04.65.16 1.28.4 1.88.28.71.69 1.33 1.24 1.83.68.64 1.48 1.08 2.38 1.31.74.19 1.5.26 2.26.28.24.003.48.01.72.01h9.44c.24 0 .48.003.72-.01.76-.02 1.52-.09 2.26-.28.9-.23 1.7-.67 2.38-1.31.55-.5.96-1.12 1.24-1.83.24-.6.36-1.23.4-1.88.04-.5.06-1 .07-1.5V6.124zm-6.74 6.636a.544.544 0 01-.54.56c-.12 0-.24-.04-.36-.12l-.04-.04c-.52-.44-1.12-.68-1.8-.76-.16-.02-.32-.02-.48-.02-.4 0-.8.08-1.16.24-.4.18-.74.42-1 .72a2.71 2.71 0 00-.52.92 3.78 3.78 0 00-.16 1.12c0 .4.06.8.16 1.16.12.4.3.76.56 1.06.28.32.6.56.96.72.4.18.84.26 1.28.26.16 0 .32 0 .48-.02.68-.08 1.28-.32 1.8-.76l.04-.04c.12-.08.24-.12.36-.12a.544.544 0 01.54.56c0 .16-.06.3-.18.4-.68.6-1.48.98-2.4 1.1-.2.02-.4.04-.6.04-.64 0-1.24-.12-1.76-.38a3.78 3.78 0 01-1.36-1.02 4.4 4.4 0 01-.82-1.46 5.16 5.16 0 01-.28-1.7c0-.58.1-1.14.28-1.66.2-.56.5-1.04.82-1.46a3.78 3.78 0 011.36-1.02c.52-.26 1.12-.38 1.76-.38.2 0 .4.02.6.04.92.12 1.72.5 2.4 1.1.12.1.18.24.18.4zM9.16 7.88c.12-.36.46-.56.82-.48l4.6 1.2c.36.08.6.4.6.78v5.36c0 .6-.16 1.14-.44 1.6-.3.5-.72.88-1.24 1.12-.36.16-.74.26-1.12.3-.14.02-.28.02-.42.02-.56 0-1.08-.14-1.52-.42s-.74-.68-.86-1.18c-.06-.24-.08-.48-.06-.72.04-.46.22-.86.52-1.18.32-.34.72-.56 1.16-.66l2.84-.72V9.56l-3.4-.88v4.76c0 .6-.16 1.14-.44 1.6-.3.5-.72.88-1.24 1.12-.36.16-.74.26-1.12.3-.14.02-.28.02-.42.02-.56 0-1.08-.14-1.52-.42s-.74-.68-.86-1.18c-.06-.24-.08-.48-.06-.72.04-.46.22-.86.52-1.18.32-.34.72-.56 1.16-.66l2.84-.72V8.36c0-.2.06-.36.14-.48z" fill="url(#am-grad)"/></svg>
                        <span className="text-sm font-medium text-[#3D4A44] group-hover:text-[#FA233B] transition-colors">Apple Music</span>
                      </a>
                    )}
                    {creator.youtube_url && (
                      <a href={creator.youtube_url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-3 px-4 py-2.5 rounded-xl hover:bg-[#F5F7F4] transition-colors group">
                        <svg className="w-5 h-5 flex-shrink-0" viewBox="0 0 24 24" fill="#FF0000"><path d="M23.498 6.186a3.016 3.016 0 00-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 00.502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 002.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 002.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>
                        <span className="text-sm font-medium text-[#3D4A44] group-hover:text-[#FF0000] transition-colors">YouTube</span>
                      </a>
                    )}
                    {(creator.spotify_url || creator.apple_music_url || creator.youtube_url) && (creator.instagram_url || creator.twitter_url) && (
                      <div className="border-t border-[rgba(59,77,67,0.06)] my-1"></div>
                    )}
                    {creator.instagram_url && (
                      <a href={creator.instagram_url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-3 px-4 py-2.5 rounded-xl hover:bg-[#F5F7F4] transition-colors group">
                        <svg className="w-5 h-5 flex-shrink-0" viewBox="0 0 24 24"><defs><linearGradient id="ig-grad" x1="0%" y1="100%" x2="100%" y2="0%"><stop offset="0%" stopColor="#FFDC80"/><stop offset="25%" stopColor="#F77737"/><stop offset="50%" stopColor="#E1306C"/><stop offset="75%" stopColor="#C13584"/><stop offset="100%" stopColor="#833AB4"/></linearGradient></defs><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z" fill="url(#ig-grad)"/></svg>
                        <span className="text-sm font-medium text-[#3D4A44] group-hover:text-[#E1306C] transition-colors">Instagram</span>
                      </a>
                    )}
                    {creator.twitter_url && (
                      <a href={creator.twitter_url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-3 px-4 py-2.5 rounded-xl hover:bg-[#F5F7F4] transition-colors group">
                        <svg className="w-5 h-5 flex-shrink-0" viewBox="0 0 24 24" fill="#000000"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
                        <span className="text-sm font-medium text-[#3D4A44] group-hover:text-[#000000] transition-colors">X (Twitter)</span>
                      </a>
                    )}
                    {creator.custom_links && creator.custom_links.length > 0 && (
                      <>
                        {(creator.spotify_url || creator.apple_music_url || creator.youtube_url || creator.instagram_url || creator.twitter_url) && (
                          <div className="border-t border-[rgba(59,77,67,0.06)] my-1"></div>
                        )}
                        {creator.custom_links.map((link, idx) => (
                          <a key={idx} href={link.url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-3 px-4 py-2.5 rounded-xl hover:bg-[#F5F7F4] transition-colors group">
                            <svg className="w-5 h-5 flex-shrink-0 text-[#5B8A72]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
                            <span className="text-sm font-medium text-[#3D4A44] group-hover:text-[#5B8A72] transition-colors">{link.name || link.url}</span>
                          </a>
                        ))}
                      </>
                    )}
                  </div>
                </div>
              )}
              
              <div className="bg-white rounded-[18px] p-7" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                <h2 className="text-xl font-semibold text-[#3D4A44] mb-5">Registration Status</h2>
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <span className="text-[#7A8580]">PRO Registered</span>
                    <span className="font-medium text-[#3D4A44]">{registeredPro} / {songs.length}</span>
                  </div>
                  <div className="w-full bg-[#EEF1EC] rounded-full h-2">
                    <div 
                      className="h-2 rounded-full" 
                      style={{ width: `${songs.length > 0 ? (registeredPro / songs.length) * 100 : 0}%`, background: '#5A8A9A' }}
                    />
                  </div>
                  
                  <div className="flex justify-between items-center mt-4">
                    <span className="text-[#7A8580]">Fee Received</span>
                    <span className="font-medium text-[#3D4A44]">{registeredFee} / {songs.length}</span>
                  </div>
                  <div className="w-full bg-[#EEF1EC] rounded-full h-2">
                    <div 
                      className="h-2 rounded-full" 
                      style={{ width: `${songs.length > 0 ? (registeredFee / songs.length) * 100 : 0}%`, background: '#5B8A72' }}
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
        
        {activeTab === 'records' && (
          <div className="bg-white rounded-[18px] overflow-hidden" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
            <div className="p-5 border-b border-[rgba(59,77,67,0.08)] bg-[#F8F8FB] flex items-center justify-between">
              <p className="text-sm text-[#7A8580]">
                {selectedSongs.size > 0 
                  ? `${selectedSongs.size} song${selectedSongs.size > 1 ? 's' : ''} selected`
                  : `Showing all ${songs.length} records. Click the edit button to update details.`
                }
              </p>
              <div className="flex items-center gap-2">
                {selectedSongs.size >= 2 && (
                  <button
                    onClick={() => {
                      const firstSelected = songs.find(s => selectedSongs.has(s.id))
                      setMergePrimaryId(firstSelected?.id || null)
                      setShowMergeModal(true)
                    }}
                    className="flex items-center gap-2 px-4 py-2 bg-[#5A8A9A] text-white rounded-xl font-medium hover:bg-[#4A7A8A] transition-colors text-sm"
                  >
                    <LinkIcon className="w-4 h-4" />
                    Merge Songs ({selectedSongs.size})
                  </button>
                )}
                {selectedSongs.size > 0 && (
                  <button
                    onClick={() => setShowDeleteConfirm(true)}
                    className="flex items-center gap-2 px-4 py-2 bg-[#C47068] text-white rounded-xl font-medium hover:bg-[#B05E56] transition-colors text-sm"
                  >
                    <TrashIcon className="w-4 h-4" />
                    Delete Selected ({selectedSongs.size})
                  </button>
                )}
                <button
                  onClick={() => setShowAddSongModal(true)}
                  className="flex items-center gap-2 px-4 py-2 bg-[#5B8A72] text-white rounded-xl font-medium hover:bg-[#4A7862] transition-colors text-sm"
                >
                  <PlusIcon className="w-4 h-4" />
                  Add Song
                </button>
              </div>
            </div>
            <div className="overflow-auto" style={{ maxHeight: '70vh' }}>
              <table className="w-full text-sm min-w-[900px]">
                <thead className="bg-[#F8F8FB] border-b border-[rgba(59,77,67,0.08)] sticky top-0 z-10">
                  <tr>
                    <th className="px-3 py-3 text-center w-10">
                      <input
                        type="checkbox"
                        checked={songs.length > 0 && selectedSongs.size === songs.length}
                        onChange={toggleSelectAll}
                        className="w-4 h-4 rounded accent-[#5B8A72]"
                      />
                    </th>
                    <SortHeader column="title" className="text-left sticky left-0 bg-[#F8F8FB]">Title / Artist</SortHeader>
                    <SortHeader column="credit_role" className="text-left">Role</SortHeader>
                    <SortHeader column="label" className="text-left">Label</SortHeader>
                    <SortHeader column="publishing_percentage" className="text-center">Pub %</SortHeader>
                    <SortHeader column="advance_amount" className="text-center">Advance</SortHeader>
                    <SortHeader column="is_registered_with_pro" className="text-center">PRO</SortHeader>
                    <SortHeader column="is_invoiced" className="text-center">Fee</SortHeader>
                    <SortHeader column="soundexchange_registered" className="text-center">Sound Ex.</SortHeader>
                    <SortHeader column="mlc_registered" className="text-center">MLC</SortHeader>
                    <SortHeader column="has_contract_executed" className="text-center">Contract</SortHeader>
                    <SortHeader column="is_paid" className="text-center">Paid</SortHeader>
                    <SortHeader column="is_released" className="text-center">Released</SortHeader>
                    <th className="px-4 py-3 text-center font-semibold text-[#3D4A44]">Spotify</th>
                    <th className="px-4 py-3 text-center font-semibold text-[#3D4A44]">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedSongs.map((song, index) => (
                    <tr key={song.id} onClick={() => { if (editingSong !== song.id) setSelectedSongForDetail(song) }} className={`hover:bg-[#F8F8FB] transition-colors border-b border-[rgba(0,0,0,0.05)] cursor-pointer ${index % 2 === 0 ? 'bg-white' : 'bg-[#F8F8FB]'} ${selectedSongs.has(song.id) ? 'bg-[#EDF5F0] hover:bg-[#E0EDE5]' : ''}`}>
                      <td className="px-3 py-3 text-center w-10" onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          checked={selectedSongs.has(song.id)}
                          onChange={() => toggleSongSelection(song.id)}
                          className="w-4 h-4 rounded accent-[#5B8A72]"
                        />
                      </td>
                      {editingSong === song.id ? (
                        <>
                          <td className={`px-4 py-2 sticky left-0 ${index % 2 === 0 ? 'bg-white' : 'bg-[#F8F8FB]'}`}>
                            <input
                              type="text"
                              value={editForm.title || ''}
                              onChange={(e) => setEditForm({...editForm, title: e.target.value})}
                              className="w-full px-3 py-1.5 border border-[rgba(0,0,0,0.1)] rounded-xl text-sm font-medium bg-white focus:outline-none focus:border-[#5B8A72] focus:ring-2 focus:ring-[rgba(91,138,114,0.15)] mb-1"
                              placeholder="Song title"
                            />
                            <input
                              type="text"
                              value={editForm.primary_artist || ''}
                              onChange={(e) => setEditForm({...editForm, primary_artist: e.target.value})}
                              className="w-full px-3 py-1.5 border border-[rgba(0,0,0,0.1)] rounded-xl text-xs bg-white focus:outline-none focus:border-[#5B8A72] focus:ring-2 focus:ring-[rgba(91,138,114,0.15)] text-[#7A8580]"
                              placeholder="Artist name"
                            />
                          </td>
                          <td className="px-4 py-2">
                            <select
                              value={editForm.credit_role || 'ARTIST'}
                              onChange={async (e) => {
                                const newRole = e.target.value
                                setEditForm({...editForm, credit_role: newRole})
                                if (song.credit_id) {
                                  try {
                                    await axios.patch(`/api/songs/${song.id}/credits/${song.credit_id}`, { role: newRole })
                                  } catch (err) {
                                    console.error('Failed to update role:', err)
                                  }
                                }
                              }}
                              className="w-full px-2 py-2 border border-[rgba(0,0,0,0.1)] rounded-xl text-xs bg-white focus:outline-none focus:border-[#5B8A72] focus:ring-2 focus:ring-[rgba(91,138,114,0.15)]"
                            >
                              {ROLE_OPTIONS.map(r => (
                                <option key={r} value={r}>{r.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</option>
                              ))}
                            </select>
                          </td>
                          <td className="px-4 py-2">
                            <input 
                              type="text" 
                              value={editForm.label}
                              onChange={(e) => setEditForm({...editForm, label: e.target.value})}
                              className="w-full px-3 py-2 border border-[rgba(0,0,0,0.1)] rounded-xl text-sm bg-white focus:outline-none focus:border-[#5B8A72] focus:ring-2 focus:ring-[rgba(160,32,240,0.1)]"
                              placeholder="Label"
                            />
                          </td>
                          <td className="px-4 py-2">
                            <input 
                              type="number" 
                              value={editForm.publishing_percentage}
                              onChange={(e) => setEditForm({...editForm, publishing_percentage: e.target.value})}
                              className="w-16 px-3 py-2 border border-[rgba(0,0,0,0.1)] rounded-xl text-sm text-center bg-white focus:outline-none focus:border-[#5B8A72] focus:ring-2 focus:ring-[rgba(160,32,240,0.1)]"
                              placeholder="%"
                              step="0.01"
                              max="100"
                            />
                          </td>
                          <td className="px-4 py-2">
                            <DollarOrNAInput
                              value={editForm.is_invoiced}
                              onChange={(val) => setEditForm({...editForm, is_invoiced: val})}
                              placeholder="0"
                            />
                          </td>
                          <td className="px-4 py-2 text-center">
                            <input 
                              type="checkbox" 
                              checked={editForm.is_registered_with_pro}
                              onChange={(e) => setEditForm({...editForm, is_registered_with_pro: e.target.checked})}
                              className="w-4 h-4 text-[#5B8A72] rounded accent-[#5B8A72]"
                            />
                          </td>
                          <td className="px-4 py-2">
                            <DollarOrNAInput
                              value={editForm.is_registered_with_dsp}
                              onChange={(val) => setEditForm({...editForm, is_registered_with_dsp: val})}
                              placeholder="0"
                            />
                          </td>
                          <td className="px-4 py-2 text-center">
                            <select 
                              value={editForm.soundexchange_registered}
                              onChange={(e) => setEditForm({...editForm, soundexchange_registered: e.target.value})}
                              className="px-3 py-2 border border-[rgba(0,0,0,0.1)] rounded-xl text-sm bg-white focus:outline-none focus:border-[#5B8A72]"
                            >
                              <option value="">—</option>
                              <option value="Yes">Yes</option>
                              <option value="No">No</option>
                              <option value="N/A">N/A</option>
                            </select>
                          </td>
                          <td className="px-4 py-2 text-center">
                            <select 
                              value={editForm.mlc_registered}
                              onChange={(e) => setEditForm({...editForm, mlc_registered: e.target.value})}
                              className="px-3 py-2 border border-[rgba(0,0,0,0.1)] rounded-xl text-sm bg-white focus:outline-none focus:border-[#5B8A72]"
                            >
                              <option value="">—</option>
                              <option value="Yes">Yes</option>
                              <option value="No">No</option>
                              <option value="N/A">N/A</option>
                            </select>
                          </td>
                          <td className="px-4 py-2 text-center">
                            <input 
                              type="checkbox" 
                              checked={editForm.has_contract_executed}
                              onChange={(e) => setEditForm({...editForm, has_contract_executed: e.target.checked})}
                              className="w-4 h-4 text-[#5B8A72] rounded accent-[#5B8A72]"
                            />
                          </td>
                          <td className="px-4 py-2 text-center">
                            <select 
                              value={editForm.is_paid}
                              onChange={(e) => setEditForm({...editForm, is_paid: e.target.value})}
                              className="px-3 py-2 border border-[rgba(0,0,0,0.1)] rounded-xl text-sm bg-white focus:outline-none focus:border-[#5B8A72]"
                            >
                              <option value="">—</option>
                              <option value="Yes">Yes</option>
                              <option value="No">No</option>
                              <option value="N/A">N/A</option>
                            </select>
                          </td>
                          <td className="px-4 py-2 text-center">
                            <input 
                              type="checkbox" 
                              checked={editForm.is_released}
                              onChange={(e) => setEditForm({...editForm, is_released: e.target.checked})}
                              className="w-4 h-4 text-[#5B8A72] rounded accent-[#5B8A72]"
                            />
                          </td>
                          <td className="px-4 py-2">
                            <input 
                              type="text" 
                              value={editForm.spotify_link}
                              onChange={(e) => setEditForm({...editForm, spotify_link: e.target.value})}
                              disabled={!editForm.is_released}
                              placeholder={editForm.is_released ? "Spotify URL" : "-"}
                              className={`w-24 px-2 py-1 border border-[rgba(0,0,0,0.1)] rounded-lg text-xs ${!editForm.is_released ? 'bg-gray-100 text-gray-400 cursor-not-allowed' : 'bg-white focus:outline-none focus:border-[#5B8A72]'}`}
                            />
                          </td>
                          <td className="px-4 py-2">
                            <div className="flex items-center gap-2 justify-center">
                              <button 
                                onClick={() => saveEdit(song.id)}
                                disabled={saving}
                                className="p-2 rounded-lg transition-colors" style={{ background: 'rgba(52, 199, 89, 0.15)', color: '#5B9A6E' }}
                              >
                                <CheckIcon className="w-5 h-5" />
                              </button>
                              <button 
                                onClick={cancelEdit}
                                disabled={saving}
                                className="p-2 rounded-lg transition-colors" style={{ background: 'rgba(255, 59, 48, 0.15)', color: '#C47068' }}
                              >
                                <XMarkIcon className="w-5 h-5" />
                              </button>
                            </div>
                          </td>
                        </>
                      ) : (
                        <>
                          <td className={`px-4 py-3 sticky left-0 ${index % 2 === 0 ? 'bg-white' : 'bg-[#F8F8FB]'}`}>
                            <div className="font-medium text-[#3D4A44]">{song.title}</div>
                            <div className="text-xs text-[#7A8580]">{song.primary_artist}</div>
                          </td>
                          <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                            <select
                              value={song.credit_role || 'ARTIST'}
                              onChange={async (e) => {
                                const newRole = e.target.value
                                if (song.credit_id) {
                                  try {
                                    await axios.patch(`/api/songs/${song.id}/credits/${song.credit_id}`, { role: newRole })
                                    setSongs(prev => prev.map(s => s.id === song.id ? {...s, credit_role: newRole} : s))
                                  } catch (err) {
                                    console.error('Failed to update role:', err)
                                    alert('Failed to update role')
                                  }
                                }
                              }}
                              className="px-2 py-1 border border-[rgba(59,77,67,0.15)] rounded-lg text-xs text-[#3D4A44] bg-transparent hover:bg-white focus:outline-none focus:border-[#5B8A72] focus:ring-1 focus:ring-[rgba(91,138,114,0.2)] cursor-pointer"
                            >
                              {ROLE_OPTIONS.map(r => (
                                <option key={r} value={r}>{r.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</option>
                              ))}
                            </select>
                          </td>
                          <td className="px-4 py-3 text-[#7A8580] max-w-32 truncate" title={song.label}>
                            {song.label || '-'}
                          </td>
                          <td className="px-4 py-3 text-center text-[#7A8580]">
                            {song.publishing_percentage ? `${Math.min(song.publishing_percentage, 100).toFixed(1)}%` : '-'}
                          </td>
                          <td className="px-4 py-3 text-center">
                            <StatusBadge value={song.is_invoiced} />
                          </td>
                          <td className="px-4 py-3 text-center">
                            <StatusBadge value={song.is_registered_with_pro} />
                          </td>
                          <td className="px-4 py-3 text-center">
                            <StatusBadge value={song.is_registered_with_dsp} />
                          </td>
                          <td className="px-4 py-3 text-center">
                            <StatusBadge value={song.soundexchange_registered} />
                          </td>
                          <td className="px-4 py-3 text-center">
                            <StatusBadge value={song.mlc_registered} />
                          </td>
                          <td className="px-4 py-3 text-center">
                            <StatusBadge value={song.has_contract_executed} />
                          </td>
                          <td className="px-4 py-3 text-center">
                            <StatusBadge value={song.is_paid} />
                          </td>
                          <td className="px-4 py-3 text-center" onClick={(e) => e.stopPropagation()}>
                            <input 
                              type="checkbox" 
                              checked={song.is_released || false}
                              onChange={() => handleReleasedToggle(song)}
                              className="w-4 h-4 text-[#5B8A72] rounded accent-[#5B8A72] cursor-pointer"
                            />
                          </td>
                          <td className="px-4 py-3 text-center" onClick={(e) => e.stopPropagation()}>
                            {song.is_released && song.spotify_link ? (
                              <a
                                href={song.spotify_link}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="px-2 py-1 text-xs font-medium rounded-lg transition-colors"
                                style={{ background: 'rgba(30, 215, 96, 0.15)', color: '#1DB954' }}
                              >
                                Open
                              </a>
                            ) : (
                              <span className={`text-xs ${song.is_released ? 'text-[#7A8580]' : 'text-gray-300'}`}>
                                {song.is_released ? 'Add link' : '-'}
                              </span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-center" onClick={(e) => e.stopPropagation()}>
                            <div className="flex items-center justify-center gap-1">
                              <button 
                                onClick={(e) => handleDuplicateSong(song.id, e)}
                                className="p-2 text-[#7A8580] hover:text-[#5A8A9A] rounded-lg transition-colors"
                                title="Duplicate song"
                              >
                                <DocumentDuplicateIcon className="w-4 h-4" />
                              </button>
                              <button 
                                onClick={() => startEdit(song)}
                                className="p-2 text-[#7A8580] hover:text-[#5B8A72] rounded-lg transition-colors" style={{ background: 'rgba(0,0,0,0.03)' }}
                              >
                                <PencilIcon className="w-4 h-4" />
                              </button>
                            </div>
                          </td>
                        </>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
        
        {activeTab === 'releases' && (
          <div className="space-y-4">
            {creatorReleases.length === 0 ? (
              <div className="bg-[#FAFBF9] rounded-xl shadow-sm p-12 text-center">
                <MusicalNoteIcon className="w-12 h-12 text-[#7A8580] mx-auto mb-3" />
                <p className="text-[#7A8580] text-lg font-medium">No releases assigned yet</p>
                <p className="text-[#7A8580] text-sm mt-1">Assign releases to this client from the Artist Releases page</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {creatorReleases.map(rel => (
                  <Link
                    key={rel.id}
                    to={`/releases`}
                    className="bg-[#FAFBF9] rounded-xl shadow-sm overflow-hidden hover:shadow-md transition-shadow group"
                  >
                    <div className="aspect-square bg-[#EEF1EC] flex items-center justify-center">
                      {(releaseArtworkUrls[rel.id] || rel.cover_art_url) ? (
                        <img src={releaseArtworkUrls[rel.id] || ''} alt={rel.title} className="w-full h-full object-cover" onError={(e) => e.target.style.display='none'} />
                      ) : (
                        <MusicalNoteIcon className="w-16 h-16 text-[#7A8580]" />
                      )}
                    </div>
                    <div className="p-4">
                      <h3 className="font-semibold text-[#3D4A44] group-hover:text-[#5B8A72] transition-colors truncate">{rel.title}</h3>
                      <p className="text-sm text-[#7A8580] mt-0.5">{rel.primary_artist || 'No artist'}</p>
                      <div className="flex items-center justify-between mt-2">
                        <span className="text-xs bg-[#EEF1EC] text-[#7A8580] px-2 py-0.5 rounded-full">{rel.release_type}</span>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${
                          rel.status === 'RELEASED' ? 'bg-green-100 text-green-700' :
                          rel.status === 'READY' ? 'bg-blue-100 text-blue-700' :
                          rel.status === 'SUBMITTED' ? 'bg-amber-100 text-amber-700' :
                          'bg-gray-100 text-gray-700'
                        }`}>{rel.status}</span>
                      </div>
                      {rel.release_date && (
                        <p className="text-xs text-[#7A8580] mt-2">{new Date(rel.release_date).toLocaleDateString()}</p>
                      )}
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'contracts' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-[#3D4A44] text-lg">Contracts & Agreements</h3>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => { setShowUploadDocModal(true); setUploadDocError(''); setUploadDocFile(null); setUploadDocContractId(''); setUploadDocDescription('') }}
                  disabled={creatorContracts.length === 0}
                  className="flex items-center gap-1.5 px-3 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg text-[#3D4A44] hover:bg-[#EEF1EC] transition-colors text-sm disabled:opacity-40 disabled:cursor-not-allowed"
                  title={creatorContracts.length === 0 ? 'Create a contract first' : 'Upload a document to an existing contract'}
                >
                  <CloudArrowUpIcon className="w-4 h-4" />
                  <span>Upload Document</span>
                </button>
                <button
                  onClick={() => {
                    setCreateContractForm({ title: '', contract_type: 'MASTER', payment_direction: 'INCOMING', status: 'DRAFT', reference_number: '', start_date: '', end_date: '', territory: '', advance_amount: '', advance_currency: 'USD', notes: '', terms_summary: '' })
                    setCreateContractParties([])
                    setCreateContractPartyForm({ party_name: '', party_role: 'ARTIST', contact_email: '' })
                    setCreateContractError('')
                    setShowCreateContractModal(true)
                  }}
                  className="flex items-center gap-1.5 px-3 py-2 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] transition-colors text-sm"
                >
                  <PlusIcon className="w-4 h-4" />
                  <span>New Contract</span>
                </button>
              </div>
            </div>
            {contractsLoading ? (
              <div className="text-center py-12 text-[#7A8580]">Loading contracts...</div>
            ) : creatorContracts.length === 0 ? (
              <div className="bg-white rounded-2xl border border-[rgba(59,77,67,0.08)] p-12 text-center">
                <DocumentTextIcon className="w-12 h-12 text-[#B0BDB4] mx-auto mb-3" />
                <p className="text-[#7A8580] mb-1">No contracts found</p>
                <p className="text-xs text-[#B0BDB4] mb-4">Contracts where {creator.display_name || creator.legal_name} is a party or assigned client will appear here.</p>
                <button
                  onClick={() => {
                    setCreateContractForm({ title: '', contract_type: 'MASTER', payment_direction: 'INCOMING', status: 'DRAFT', reference_number: '', start_date: '', end_date: '', territory: '', advance_amount: '', advance_currency: 'USD', notes: '', terms_summary: '' })
                    setCreateContractParties([])
                    setCreateContractPartyForm({ party_name: '', party_role: 'ARTIST', contact_email: '' })
                    setCreateContractError('')
                    setShowCreateContractModal(true)
                  }}
                  className="inline-flex items-center gap-1.5 px-4 py-2 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] transition-colors text-sm"
                >
                  <PlusIcon className="w-4 h-4" />
                  <span>Create First Contract</span>
                </button>
              </div>
            ) : (
              <div className="bg-white rounded-2xl border border-[rgba(59,77,67,0.08)] overflow-hidden">
                <div className="divide-y divide-[rgba(59,77,67,0.06)]">
                  {creatorContracts.map(contract => (
                    <Link
                      key={contract.id}
                      to="/contracts"
                      className="flex items-center justify-between px-6 py-4 hover:bg-[#F5F7F4] transition-colors group"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <p className="font-medium text-[#3D4A44] truncate group-hover:text-[#5B8A72] transition-colors">{contract.title}</p>
                          {contract.reference_number && (
                            <span className="text-xs text-[#7A8580] bg-[#F5F7F4] px-2 py-0.5 rounded-full">{contract.reference_number}</span>
                          )}
                        </div>
                        <div className="flex items-center gap-3 text-xs text-[#7A8580]">
                          {contract.start_date && <span>Start: {new Date(contract.start_date).toLocaleDateString()}</span>}
                          {contract.end_date && <span>End: {new Date(contract.end_date).toLocaleDateString()}</span>}
                          {contract.territory?.length > 0 && <span>{contract.territory.join(', ')}</span>}
                          {contract.advance_amount > 0 && (
                            <span className={`font-medium ${contract.payment_direction === 'OUTGOING' ? 'text-amber-600' : 'text-[#5B8A72]'}`}>
                              {contract.payment_direction === 'OUTGOING' ? '↑' : '↓'} {contract.advance_currency} {contract.advance_amount.toLocaleString()}
                            </span>
                          )}
                        </div>
                        {contract.parties?.length > 0 && (
                          <div className="flex items-center gap-1 mt-1.5 flex-wrap">
                            {contract.parties.map((p, i) => (
                              <span key={i} className="text-xs bg-[#EEF1EC] text-[#5B8A72] px-2 py-0.5 rounded-full">{p.party_name} ({p.party_role})</span>
                            ))}
                          </div>
                        )}
                      </div>
                      <div className="flex items-center gap-2 ml-4 flex-shrink-0">
                        <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${contract.payment_direction === 'OUTGOING' ? 'bg-amber-100 text-amber-700' : 'bg-green-100 text-green-700'}`}>
                          {contract.payment_direction === 'OUTGOING' ? '↑ Outgoing' : '↓ Incoming'}
                        </span>
                        <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${
                          contract.contract_type === 'MASTER' ? 'bg-purple-100 text-purple-700' :
                          contract.contract_type === 'PUBLISHING' ? 'bg-blue-100 text-blue-700' :
                          contract.contract_type === 'SYNC_LICENSE' ? 'bg-teal-100 text-teal-700' :
                          contract.contract_type === 'DISTRIBUTION' ? 'bg-orange-100 text-orange-700' :
                          'bg-gray-100 text-gray-700'
                        }`}>
                          {contract.contract_type === 'SYNC_LICENSE' ? 'Sync' : contract.contract_type?.charAt(0) + contract.contract_type?.slice(1).toLowerCase()}
                        </span>
                        <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${
                          contract.status === 'ACTIVE' ? 'bg-green-100 text-green-700' :
                          contract.status === 'DRAFT' ? 'bg-gray-100 text-gray-600' :
                          contract.status === 'EXPIRED' ? 'bg-red-100 text-red-700' :
                          contract.status === 'TERMINATED' ? 'bg-red-100 text-red-600' :
                          'bg-yellow-100 text-yellow-700'
                        }`}>
                          {contract.status}
                        </span>
                      </div>
                    </Link>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'credits' && (
          <div className="space-y-6">
            {creditsLoading ? (
              <div className="bg-white rounded-[18px] p-12 text-center" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                <div className="text-[#7A8580]">Loading credits data...</div>
              </div>
            ) : (
              <>
                <div className="rounded-[18px] p-8 text-white" style={{ background: 'linear-gradient(135deg, #5B8A72 0%, #3D6B4F 100%)', boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                  <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                    <div>
                      <h2 className="text-2xl font-semibold mb-1">Streaming Credits</h2>
                      <p className="text-white/70 text-sm">Streaming intelligence & credit profile for {creator.display_name}</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <button
                        onClick={handleRefreshCredits}
                        disabled={refreshingCredits}
                        className="inline-flex items-center gap-1.5 px-3 sm:px-4 py-2 bg-white/20 text-white rounded-xl text-sm font-medium hover:bg-white/30 transition-all border border-white/30 disabled:opacity-50"
                      >
                        <svg className={`w-4 h-4 ${refreshingCredits ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                        {refreshingCredits ? 'Refreshing...' : 'Refresh'}
                      </button>
                      <div className="relative">
                        <button
                          onClick={() => setShowFormatMenu(!showFormatMenu)}
                          disabled={generatingSocialCard}
                          className="inline-flex items-center gap-1.5 px-3 sm:px-4 py-2 bg-white/20 text-white rounded-xl text-sm font-medium hover:bg-white/30 transition-all border border-white/30 disabled:opacity-50"
                        >
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
                          </svg>
                          <span className="hidden sm:inline">{generatingSocialCard ? 'Generating...' : 'Download for Social'}</span>
                          <span className="sm:hidden">{generatingSocialCard ? '...' : 'Social'}</span>
                          <svg className="w-3 h-3 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
                          </svg>
                        </button>
                        {showFormatMenu && !generatingSocialCard && (
                          <div className="absolute top-full mt-2 right-0 bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden z-50 min-w-[180px]">
                            <button
                              onClick={() => handleDownloadSocialCard('story')}
                              className="w-full px-4 py-3 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-3"
                            >
                              <div className="w-5 h-7 rounded border-2 border-gray-400 flex-shrink-0" />
                              <div>
                                <div className="font-medium">Story</div>
                                <div className="text-xs text-gray-400">1080 x 1350</div>
                              </div>
                            </button>
                            <button
                              onClick={() => handleDownloadSocialCard('square')}
                              className="w-full px-4 py-3 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-3 border-t border-gray-100"
                            >
                              <div className="w-5 h-5 rounded border-2 border-gray-400 flex-shrink-0" />
                              <div>
                                <div className="font-medium">Square</div>
                                <div className="text-xs text-gray-400">1080 x 1080</div>
                              </div>
                            </button>
                          </div>
                        )}
                      </div>
                      <button
                        onClick={() => setShowShareModal(true)}
                        className="inline-flex items-center gap-1.5 px-3 sm:px-4 py-2 bg-white text-[#5B8A72] rounded-xl text-sm font-medium hover:bg-white/90 transition-all"
                        style={{ boxShadow: '0px 2px 8px rgba(0,0,0,0.1)' }}
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
                        </svg>
                        Share
                      </button>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-white rounded-[18px] p-5" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                    <p className="text-sm text-[#7A8580] mb-1">Total Credits</p>
                    <p className="text-3xl font-bold text-[#3D4A44]">{creditsData?.total_credits || 0}</p>
                  </div>
                  <div className="bg-white rounded-[18px] p-5" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                    <p className="text-sm text-[#7A8580] mb-1">Total Estimated Streams</p>
                    <p className="text-3xl font-bold text-[#5B8A72]">{formatStreamCount(creditsData?.total_estimated_streams || 0)}</p>
                  </div>
                  <div className="bg-white rounded-[18px] p-5" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                    <p className="text-sm text-[#7A8580] mb-1">Album Units (RIAA)</p>
                    <p className="text-3xl font-bold text-[#5A8A9A]">{formatStreamCount(creditsData?.riaa_equivalents?.album_units || Math.floor((creditsData?.total_estimated_streams || 0) / 1500))}</p>
                  </div>
                  <div className="bg-white rounded-[18px] p-5" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                    <p className="text-sm text-[#7A8580] mb-1">Single Units (RIAA)</p>
                    <p className="text-3xl font-bold text-[#7BA594]">{formatStreamCount(creditsData?.riaa_equivalents?.single_units || Math.floor((creditsData?.total_estimated_streams || 0) / 150))}</p>
                  </div>
                </div>

                {creditsData?.platform_breakdown && Object.keys(creditsData.platform_breakdown).length > 0 && (
                  <div className="bg-white rounded-[18px] p-7" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                    <h3 className="text-lg font-semibold text-[#3D4A44] mb-4">Platform Breakdown</h3>
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
                      {Object.entries(creditsData.platform_breakdown).map(([platform, streamData]) => {
                        const pInfo = PLATFORM_ICONS[platform] || { color: '#7A8580', label: platform }
                        const streamCount = typeof streamData === 'object' && streamData !== null ? (streamData.streams || 0) : (streamData || 0)
                        return (
                          <div key={platform} className="flex items-center gap-3 p-3 rounded-xl bg-[#F8F8FB]">
                            <PlatformIcon platform={platform} size={28} />
                            <div className="min-w-0">
                              <p className="text-xs text-[#7A8580] truncate">{pInfo.label}</p>
                              <p className="text-sm font-semibold text-[#3D4A44]">{formatStreamCount(streamCount)}</p>
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )}

                {creditsData?.role_breakdown && Object.keys(creditsData.role_breakdown).length > 0 && (
                  <div className="bg-white rounded-[18px] p-7" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                    <h3 className="text-lg font-semibold text-[#3D4A44] mb-4">Role Breakdown</h3>
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                      {Object.entries(creditsData.role_breakdown).map(([role, count]) => {
                        const roleColors = {
                          PRODUCER: { bg: 'rgba(91, 138, 114, 0.12)', text: '#5B8A72', border: 'rgba(91, 138, 114, 0.2)' },
                          SONGWRITER: { bg: 'rgba(90, 138, 154, 0.12)', text: '#5A8A9A', border: 'rgba(90, 138, 154, 0.2)' },
                          ARTIST: { bg: 'rgba(196, 149, 107, 0.12)', text: '#C4956B', border: 'rgba(196, 149, 107, 0.2)' },
                          FEATURED_ARTIST: { bg: 'rgba(160, 32, 240, 0.12)', text: '#8B5CF6', border: 'rgba(160, 32, 240, 0.2)' },
                          MIX_ENGINEER: { bg: 'rgba(123, 165, 148, 0.12)', text: '#7BA594', border: 'rgba(123, 165, 148, 0.2)' },
                          OTHER: { bg: 'rgba(122, 133, 128, 0.12)', text: '#7A8580', border: 'rgba(122, 133, 128, 0.2)' },
                        }
                        const rc = roleColors[role] || roleColors.OTHER
                        return (
                          <div key={role} className="rounded-xl p-5 border" style={{ background: rc.bg, borderColor: rc.border }}>
                            <p className="text-3xl font-bold mb-1" style={{ color: rc.text }}>{count}</p>
                            <p className="text-sm font-medium" style={{ color: rc.text }}>{role.replace(/_/g, ' ')}</p>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )}

                <div className="bg-white rounded-[18px] overflow-hidden" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                  <div className="p-5 border-b border-[rgba(59,77,67,0.08)]">
                    <h3 className="text-lg font-semibold text-[#3D4A44]">Credited Songs</h3>
                    <p className="text-sm text-[#7A8580] mt-1">Songs ranked by estimated total streams</p>
                  </div>
                  {creditsSongsLoading ? (
                    <div className="p-8 text-center text-[#7A8580]">Loading songs...</div>
                  ) : creditsSongs.length > 0 ? (
                    <div className="divide-y divide-[rgba(59,77,67,0.06)]">
                      {creditsSongs.map((song, idx) => (
                        <div key={song.song_id} className="flex items-center gap-4 px-5 py-4 hover:bg-[#F8F8FB] transition-colors">
                          <span className="text-lg font-bold text-[#B0BDB4] w-8 text-right flex-shrink-0">{idx + 1}</span>
                          <div className="w-10 h-10 rounded-lg bg-[#EEF1EC] flex items-center justify-center flex-shrink-0 overflow-hidden">
                            {song.artwork_url ? (
                              <img src={song.artwork_url} alt="" className="w-full h-full object-cover" />
                            ) : (
                              <MusicalNoteIcon className="w-5 h-5 text-[#7A8580]" />
                            )}
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="font-medium text-[#3D4A44] truncate">{song.title}</p>
                            <div className="flex items-center gap-2 mt-0.5">
                              <p className="text-xs text-[#7A8580] truncate">{song.artist}</p>
                              {song.role && (
                                <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-[#EEF1EC] text-[#5B8A72]">
                                  {song.role.replace(/_/g, ' ')}
                                </span>
                              )}
                              {song.share_percentage && (
                                <span className="text-[10px] text-[#7A8580]">{song.share_percentage}%</span>
                              )}
                            </div>
                          </div>
                          <div className="text-right flex-shrink-0">
                            <p className="text-sm font-semibold text-[#3D4A44]">{formatStreamCount(song.total_streams)}</p>
                            <p className="text-xs text-[#7A8580]">streams</p>
                          </div>
                          {song.platforms && Object.keys(song.platforms).length > 0 && (
                            <div className="hidden md:flex items-center gap-1.5 flex-shrink-0 ml-2">
                              {Object.entries(song.platforms).map(([plat, platData]) => {
                                const pInfo = PLATFORM_ICONS[plat] || { color: '#7A8580', label: plat }
                                const platStreams = typeof platData === 'object' && platData !== null ? (platData.streams || 0) : (platData || 0)
                                return (
                                  <div key={plat} className="flex items-center gap-1 px-2 py-1 rounded-md bg-[#F8F8FB]" title={`${pInfo.label}: ${formatStreamCount(platStreams)}`}>
                                    <PlatformIcon platform={plat} size={14} />
                                    <span className="text-[10px] text-[#7A8580]">{formatStreamCount(platStreams)}</span>
                                  </div>
                                )
                              })}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="p-12 text-center">
                      <MusicalNoteIcon className="w-12 h-12 text-[#C7C7CC] mx-auto mb-4" />
                      <h3 className="text-lg font-medium text-[#3D4A44] mb-2">No credits data yet</h3>
                      <p className="text-[#7A8580] text-sm">Credits are computed from song credits and streaming data. Click "Refresh" to generate.</p>
                    </div>
                  )}
                </div>

                <p className="text-xs text-[#B0BDB4] text-center italic">
                  Stream estimates are derived from chart data, market-share ratios, and available platform data. Actual numbers may vary. Confidence levels are applied to all estimates.
                </p>
              </>
            )}
          </div>
        )}

        {showSocialCard && creditsData && creator && (
          <div style={{ position: 'fixed', top: 0, left: 0, opacity: 0, pointerEvents: 'none', zIndex: -1, overflow: 'hidden' }}>
            <SocialCard
              ref={socialCardRef}
              data={creditsData}
              avatarUrl={creator.hero_image_url}
              creatorName={creator.display_name || creator.name}
              orgName={organizationName}
              format={socialCardFormat}
            />
          </div>
        )}

        {showShareModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-[18px] w-full max-w-md">
              <div className="p-6 border-b border-[rgba(59,77,67,0.12)]">
                <div className="flex items-center justify-between">
                  <h2 className="text-xl font-semibold text-[#3D4A44]">Share Credits Profile</h2>
                  <button onClick={() => setShowShareModal(false)} className="p-2 hover:bg-[#EEF1EC] rounded-lg transition-colors">
                    <XMarkIcon className="w-5 h-5 text-[#7A8580]" />
                  </button>
                </div>
              </div>
              <div className="p-6 space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-[#3D4A44]">Public Access</p>
                    <p className="text-xs text-[#7A8580]">Allow anyone with the link to view</p>
                  </div>
                  <button
                    onClick={() => setShareSettings(prev => ({ ...prev, is_public: !prev.is_public }))}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${shareSettings.is_public ? 'bg-[#5B8A72]' : 'bg-[#D1D5DB]'}`}
                  >
                    <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${shareSettings.is_public ? 'translate-x-6' : 'translate-x-1'}`} />
                  </button>
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-2">Passcode (optional)</label>
                  <input
                    type="text"
                    value={shareSettings.passcode}
                    onChange={(e) => setShareSettings(prev => ({ ...prev, passcode: e.target.value }))}
                    placeholder="Leave empty for no passcode"
                    className="w-full px-4 py-3 border border-[rgba(59,77,67,0.2)] rounded-xl focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent text-sm"
                  />
                </div>
                {shareResult && (
                  <div className="bg-[#F5F7F4] rounded-xl p-4">
                    <p className="text-xs text-[#7A8580] mb-2">Share Link</p>
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        readOnly
                        value={`${window.location.origin}${shareResult.share_url}`}
                        className="flex-1 px-3 py-2 bg-white border border-[rgba(59,77,67,0.12)] rounded-lg text-sm text-[#3D4A44]"
                      />
                      <button
                        onClick={() => {
                          navigator.clipboard.writeText(`${window.location.origin}${shareResult.share_url}`)
                          alert('Link copied!')
                        }}
                        className="px-3 py-2 bg-[#5B8A72] text-white rounded-lg text-sm font-medium hover:bg-[#4A7862] transition-colors"
                      >
                        Copy
                      </button>
                    </div>
                    {shareResult.has_passcode && (
                      <p className="text-xs text-[#7A8580] mt-2">🔒 Passcode protected</p>
                    )}
                  </div>
                )}
              </div>
              <div className="p-6 border-t border-[rgba(59,77,67,0.08)] flex items-center justify-between">
                {shareResult && (
                  <button
                    onClick={handleRevokeShare}
                    className="text-sm text-[#C47068] hover:text-[#A45850] font-medium"
                  >
                    Revoke Link
                  </button>
                )}
                <div className="flex gap-3 ml-auto">
                  <button onClick={() => setShowShareModal(false)} className="px-4 py-2 text-[#7A8580] hover:bg-[#EEF1EC] rounded-xl transition-colors text-sm font-medium">
                    Cancel
                  </button>
                  <button
                    onClick={handleShareCredits}
                    disabled={savingShare}
                    className="px-4 py-2 bg-[#5B8A72] text-white rounded-xl font-medium hover:bg-[#4A7862] transition-colors text-sm disabled:opacity-50"
                  >
                    {savingShare ? 'Saving...' : shareResult ? 'Update' : 'Generate Link'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'actions' && organizationId && (
          <ActionsTab 
            creatorId={parseInt(id)} 
            organizationId={organizationId}
            creatorName={creator.display_name}
          />
        )}

        {activeTab === 'accounting' && (
          <CreatorAccountingEnhanced orgId={organizationId} creatorId={parseInt(id)} existingAccountingData={accountingData} accountingLoading={accountingLoading} onRefresh={loadAccounting} />
        )}
        
        {activeTab === 'schedule-a' && (
          <div className="space-y-6">
            {uploadFeedback && (
              <div className={`px-5 py-3 rounded-xl text-sm font-medium ${
                uploadFeedback.type === 'error' ? 'bg-[rgba(196,112,104,0.15)] text-[#A45850]' : 'bg-[rgba(91,154,110,0.15)] text-[#3D6B4F]'
              }`}>
                {uploadFeedback.msg}
              </div>
            )}
            <div className="rounded-[18px] p-8 text-white" style={{ background: 'linear-gradient(135deg, #5B8A72 0%, #7BA594 100%)', boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                <div>
                  <h2 className="text-2xl font-semibold mb-2">Schedule A - Catalog of Compositions</h2>
                  <p className="text-white/80">
                    Official export document for {creator.display_name}'s catalog with industry-standard fields.
                  </p>
                </div>
                <div className="flex gap-3 flex-wrap">
                  <label className={`inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl font-medium transition-all duration-200 border border-white/30 cursor-pointer ${
                    uploadingScheduleA ? 'bg-white/10 text-white/60' : 'bg-white text-[#5B8A72] hover:bg-white/90'
                  }`} style={{ boxShadow: '0px 2px 8px rgba(0,0,0,0.1)' }}>
                    <input
                      type="file"
                      className="hidden"
                      accept=".csv,.xlsx,.xls"
                      onChange={handleScheduleAUpload}
                      disabled={uploadingScheduleA}
                    />
                    <ArrowUpTrayIcon className="w-5 h-5" />
                    <span>{uploadingScheduleA ? 'Uploading...' : 'Upload Schedule A'}</span>
                  </label>
                  <button
                    onClick={handleScheduleAExportPDF}
                    className="inline-flex items-center space-x-2 bg-white/20 text-white px-5 py-2.5 rounded-xl font-medium hover:bg-white/30 transition-all duration-200 border border-white/30"
                  >
                    <DocumentTextIcon className="w-5 h-5" />
                    <span>Schedule A</span>
                  </button>
                  <button
                    onClick={handleCatalogDocExportPDF}
                    className="inline-flex items-center space-x-2 bg-white/20 text-white px-5 py-2.5 rounded-xl font-medium hover:bg-white/30 transition-all duration-200 border border-white/30"
                  >
                    <DocumentArrowDownIcon className="w-5 h-5" />
                    <span>Catalog Doc</span>
                  </button>
                  <button
                    onClick={handleScheduleAExportCSV}
                    className="inline-flex items-center space-x-2 bg-white/20 text-white px-5 py-2.5 rounded-xl font-medium hover:bg-white/30 transition-all duration-200 border border-white/30"
                  >
                    <ArrowDownTrayIcon className="w-5 h-5" />
                    <span>CSV</span>
                  </button>
                </div>
              </div>
            </div>
            
            {scheduleAData && (
              <>
                <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
                  <div className="bg-white rounded-[18px] p-5" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                    <p className="text-sm text-[#7A8580] mb-1">Total Compositions</p>
                    <p className="text-2xl font-semibold text-[#3D4A44]">{scheduleAData.summary.total_songs}</p>
                  </div>
                  <div className="bg-white rounded-[18px] p-5" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                    <p className="text-sm text-[#7A8580] mb-1">Released</p>
                    <p className="text-2xl font-semibold text-[#5B8A72]">{scheduleAData.summary.released_count}</p>
                  </div>
                  <div className="bg-white rounded-[18px] p-5" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                    <p className="text-sm text-[#7A8580] mb-1">Pipeline</p>
                    <p className="text-2xl font-semibold text-[#7BA594]">{scheduleAData.summary.pipeline_count}</p>
                  </div>
                  <div className="bg-white rounded-[18px] p-5" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                    <p className="text-sm text-[#7A8580] mb-1">Paid</p>
                    <p className="text-2xl font-semibold text-[#5B9A6E]">{scheduleAData.summary.paid_count}</p>
                  </div>
                  <div className="bg-white rounded-[18px] p-5" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                    <p className="text-sm text-[#7A8580] mb-1">Contracted</p>
                    <p className="text-2xl font-semibold text-[#5A8A9A]">{scheduleAData.summary.contracted_count}</p>
                  </div>
                  <div className="bg-white rounded-[18px] p-5" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                    <p className="text-sm text-[#7A8580] mb-1">Total Advances</p>
                    <p className="text-2xl font-semibold text-[#5B9A6E]">{scheduleAData.summary.total_advance_display}</p>
                  </div>
                </div>
                
                {scheduleAData.released.length > 0 && (
                  <div className="bg-white rounded-[18px] overflow-hidden" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                    <div className="p-5 border-b border-[rgba(59,77,67,0.08)]" style={{ background: 'rgba(160, 32, 240, 0.08)' }}>
                      <h3 className="text-lg font-semibold text-[#5B8A72]">Released Catalog ({scheduleAData.released.length})</h3>
                      <p className="text-sm text-[#7A8580]">Songs that have been officially released</p>
                    </div>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead className="bg-[#F8F8FB] border-b border-[rgba(59,77,67,0.08)]">
                          <tr>
                            <th className="px-4 py-3 text-left font-semibold text-[#3D4A44]">Title</th>
                            <th className="px-4 py-3 text-left font-semibold text-[#3D4A44]">Artist</th>
                            <th className="px-4 py-3 text-left font-semibold text-[#3D4A44]">Release</th>
                            <th className="px-4 py-3 text-left font-semibold text-[#3D4A44]">Label</th>
                            <th className="px-4 py-3 text-center font-semibold text-[#3D4A44]">Pub %</th>
                            <th className="px-4 py-3 text-right font-semibold text-[#3D4A44]">Advance</th>
                            <th className="px-4 py-3 text-center font-semibold text-[#3D4A44]">Status</th>
                            <th className="px-4 py-3 text-center font-semibold text-[#3D4A44]">PRO</th>
                            <th className="px-4 py-3 text-center font-semibold text-[#3D4A44]">Fee</th>
                          </tr>
                        </thead>
                        <tbody>
                          {scheduleAData.released.map((song, index) => (
                            <tr key={song.id} className={`hover:bg-[#F8F8FB] border-b border-[rgba(0,0,0,0.05)] ${index % 2 === 0 ? 'bg-white' : 'bg-[#F8F8FB]'}`}>
                              <td className="px-4 py-3 font-medium text-[#3D4A44]">{song.title}</td>
                              <td className="px-4 py-3 text-[#7A8580]">{song.primary_artist}</td>
                              <td className="px-4 py-3 text-[#7A8580]">{song.release_date || '-'}</td>
                              <td className="px-4 py-3 text-[#7A8580] max-w-32 truncate">{song.label || '-'}</td>
                              <td className="px-4 py-3 text-center text-[#7A8580]">
                                {song.publishing_percentage ? `${Math.min(song.publishing_percentage, 100).toFixed(1)}%` : '-'}
                              </td>
                              <td className="px-4 py-3 text-right text-[#7A8580]">{song.advance_display || '-'}</td>
                              <td className="px-4 py-3 text-center">
                                <PlacementStatusBadge status={song.status} />
                              </td>
                              <td className="px-4 py-3 text-center">
                                <StatusBadge value={song.is_registered_with_pro} />
                              </td>
                              <td className="px-4 py-3 text-center">
                                <StatusBadge value={song.is_registered_with_dsp} />
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
                
                {scheduleAData.pipeline.length > 0 && (
                  <div className="bg-white rounded-[18px] overflow-hidden" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                    <div className="p-5 border-b border-[rgba(59,77,67,0.08)]" style={{ background: 'rgba(229, 64, 172, 0.08)' }}>
                      <h3 className="text-lg font-semibold text-[#7BA594]">Pipeline ({scheduleAData.pipeline.length})</h3>
                      <p className="text-sm text-[#7A8580]">Unreleased songs in various stages of the placement process</p>
                    </div>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead className="bg-[#F8F8FB] border-b border-[rgba(59,77,67,0.08)]">
                          <tr>
                            <th className="px-4 py-3 text-left font-semibold text-[#3D4A44]">Title</th>
                            <th className="px-4 py-3 text-left font-semibold text-[#3D4A44]">Artist</th>
                            <th className="px-4 py-3 text-left font-semibold text-[#3D4A44]">Label</th>
                            <th className="px-4 py-3 text-center font-semibold text-[#3D4A44]">Pub %</th>
                            <th className="px-4 py-3 text-right font-semibold text-[#3D4A44]">Advance</th>
                            <th className="px-4 py-3 text-center font-semibold text-[#3D4A44]">Status</th>
                            <th className="px-4 py-3 text-center font-semibold text-[#3D4A44]">Contract</th>
                            <th className="px-4 py-3 text-center font-semibold text-[#3D4A44]">Paid</th>
                          </tr>
                        </thead>
                        <tbody>
                          {scheduleAData.pipeline.map((song, index) => (
                            <tr key={song.id} className={`hover:bg-[#F8F8FB] border-b border-[rgba(0,0,0,0.05)] ${index % 2 === 0 ? 'bg-white' : 'bg-[#F8F8FB]'}`}>
                              <td className="px-4 py-3 font-medium text-[#3D4A44]">{song.title}</td>
                              <td className="px-4 py-3 text-[#7A8580]">{song.primary_artist}</td>
                              <td className="px-4 py-3 text-[#7A8580] max-w-32 truncate">{song.label || '-'}</td>
                              <td className="px-4 py-3 text-center text-[#7A8580]">
                                {song.publishing_percentage ? `${Math.min(song.publishing_percentage, 100).toFixed(1)}%` : '-'}
                              </td>
                              <td className="px-4 py-3 text-right text-[#7A8580]">{song.advance_display || '-'}</td>
                              <td className="px-4 py-3 text-center">
                                <PlacementStatusBadge status={song.status} />
                              </td>
                              <td className="px-4 py-3 text-center">
                                <StatusBadge value={song.has_contract_executed} />
                              </td>
                              <td className="px-4 py-3 text-center">
                                <StatusBadge value={song.is_paid} />
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
                
                {scheduleAData.released.length === 0 && scheduleAData.pipeline.length === 0 && (
                  <div className="bg-white rounded-[18px] p-12 text-center" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                    <DocumentTextIcon className="w-12 h-12 text-[#C7C7CC] mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-[#3D4A44] mb-2">No compositions yet</h3>
                    <p className="text-[#7A8580]">Add songs to this creator's catalog to generate a Schedule A.</p>
                  </div>
                )}
              </>
            )}
            
            {!scheduleAData && (
              <div className="bg-white rounded-[18px] p-12 text-center" style={{ boxShadow: '0px 4px 12px rgba(0,0,0,0.08)' }}>
                <div className="text-[#7A8580]">Loading Schedule A data...</div>
              </div>
            )}
          </div>
        )}
      </div>

      {showSpotifyModal && spotifyModalSong && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-[18px] w-full max-w-md">
            <div className="p-6 border-b border-[rgba(59,77,67,0.12)]">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full flex items-center justify-center" style={{ background: 'rgba(30, 215, 96, 0.15)' }}>
                    <svg className="w-5 h-5" style={{ color: '#1DB954' }} viewBox="0 0 24 24" fill="currentColor">
                      <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
                    </svg>
                  </div>
                  <h2 className="text-[22px] font-semibold text-[#3D4A44]">Add Spotify Link</h2>
                </div>
                <button
                  onClick={() => {
                    setShowSpotifyModal(false)
                    setSpotifyModalSong(null)
                  }}
                  className="p-2 hover:bg-[#EEF1EC] rounded-lg transition-colors"
                >
                  <XMarkIcon className="w-5 h-5 text-[#7A8580]" />
                </button>
              </div>
            </div>
            <div className="p-6">
              <p className="text-sm text-[#7A8580] mb-4">
                Add a Spotify link for <span className="font-medium text-[#3D4A44]">{spotifyModalSong.title}</span>
              </p>
              <input
                type="text"
                value={spotifyLinkInput}
                onChange={(e) => setSpotifyLinkInput(e.target.value)}
                placeholder="https://open.spotify.com/track/..."
                className="w-full px-4 py-3 border border-[rgba(0,0,0,0.1)] rounded-xl text-sm bg-white focus:outline-none focus:border-[#5B8A72] focus:ring-2 focus:ring-[rgba(91,138,114,0.1)]"
              />
              <p className="text-xs text-[#7A8580] mt-2">Optional - you can skip this and add the link later</p>
            </div>
            <div className="p-6 border-t border-[rgba(59,77,67,0.08)] flex justify-end gap-3">
              <button
                onClick={() => {
                  setShowSpotifyModal(false)
                  setSpotifyModalSong(null)
                }}
                className="px-4 py-2 text-[#7A8580] hover:bg-[#EEF1EC] rounded-xl transition-colors text-sm font-medium"
              >
                Cancel
              </button>
              <button
                onClick={handleSpotifyModalSave}
                disabled={savingSpotifyLink}
                className="px-4 py-2 bg-[#5B8A72] text-white rounded-xl font-medium hover:bg-[#4A7862] transition-colors text-sm disabled:opacity-50"
              >
                {savingSpotifyLink ? 'Saving...' : 'Mark as Released'}
              </button>
            </div>
          </div>
        </div>
      )}

      {showAddSongModal && (
        <AddSongModal
          organizationId={organizationId}
          defaultCreatorId={parseInt(id)}
          defaultPrimaryArtist={creator?.display_name || ''}
          onClose={() => setShowAddSongModal(false)}
          onSuccess={() => {
            loadSongs(organizationId)
          }}
        />
      )}

      {showEditCreatorModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6 mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-semibold text-[#3D4A44]">Edit Creator</h2>
              <button onClick={() => setShowEditCreatorModal(false)} className="p-2 hover:bg-[#EEF1EC] rounded-lg">
                <XMarkIcon className="w-5 h-5 text-[#7A8580]" />
              </button>
            </div>

            <form onSubmit={handleUpdateCreator} className="space-y-4">
              <div>
                <label className="block text-[15px] font-medium text-[#3D4A44] mb-2">Display Name *</label>
                <input
                  type="text"
                  value={creatorForm.display_name}
                  onChange={(e) => setCreatorForm({...creatorForm, display_name: e.target.value})}
                  required
                  className="w-full px-4 py-3 border border-[rgba(59,77,67,0.2)] rounded-xl focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                  placeholder="Stage name or brand"
                />
              </div>

              <div>
                <label className="block text-[15px] font-medium text-[#3D4A44] mb-2">Legal Name</label>
                <input
                  type="text"
                  value={creatorForm.legal_name}
                  onChange={(e) => setCreatorForm({...creatorForm, legal_name: e.target.value})}
                  className="w-full px-4 py-3 border border-[rgba(59,77,67,0.2)] rounded-xl focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                  placeholder="Full legal name"
                />
              </div>

              <div>
                <label className="block text-[15px] font-medium text-[#3D4A44] mb-2">Email</label>
                <input
                  type="email"
                  value={creatorForm.email}
                  onChange={(e) => setCreatorForm({...creatorForm, email: e.target.value})}
                  className="w-full px-4 py-3 border border-[rgba(59,77,67,0.2)] rounded-xl focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                  placeholder="creator@example.com"
                />
              </div>

              <div>
                <label className="block text-[15px] font-medium text-[#3D4A44] mb-2">Roles</label>
                <div className="flex flex-wrap gap-2">
                  {ROLE_OPTIONS.map(role => (
                    <button
                      key={role}
                      type="button"
                      onClick={() => handleCreatorRoleToggle(role)}
                      className={`px-4 py-2 rounded-lg border font-medium transition-colors ${
                        creatorForm.roles.includes(role)
                          ? 'bg-[#5B8A72] text-white border-[#5B8A72]'
                          : 'border-[rgba(59,77,67,0.2)] text-[#3D4A44] hover:bg-[#EEF1EC]'
                      }`}
                    >
                      {role}
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-[15px] font-medium text-[#3D4A44] mb-2">Primary Territory</label>
                  <input
                    type="text"
                    value={creatorForm.primary_territory}
                    onChange={(e) => setCreatorForm({...creatorForm, primary_territory: e.target.value})}
                    className="w-full px-4 py-3 border border-[rgba(59,77,67,0.2)] rounded-xl focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                    placeholder="e.g., US, UK, WW"
                  />
                </div>
                <div>
                  <label className="block text-[15px] font-medium text-[#3D4A44] mb-2">Primary PRO</label>
                  <select
                    value={creatorForm.primary_pro}
                    onChange={(e) => setCreatorForm({...creatorForm, primary_pro: e.target.value})}
                    className="w-full px-4 py-3 border border-[rgba(59,77,67,0.2)] rounded-xl focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                  >
                    <option value="">Select PRO</option>
                    {PRO_OPTIONS.map(pro => (
                      <option key={pro} value={pro}>{pro}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-[15px] font-medium text-[#3D4A44] mb-2">IPI Number</label>
                <input
                  type="text"
                  value={creatorForm.primary_ipi}
                  onChange={(e) => setCreatorForm({...creatorForm, primary_ipi: e.target.value})}
                  className="w-full px-4 py-3 border border-[rgba(59,77,67,0.2)] rounded-xl focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                  placeholder="IPI/CAE Number"
                />
              </div>

              <div>
                <label className="block text-[15px] font-medium text-[#3D4A44] mb-2">Publisher Contact</label>
                <select
                  value={creatorForm.publisher_contact_id || ''}
                  onChange={(e) => setCreatorForm({...creatorForm, publisher_contact_id: e.target.value ? parseInt(e.target.value) : 0})}
                  className="w-full px-4 py-3 border border-[rgba(59,77,67,0.2)] rounded-xl focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                >
                  <option value="">No publisher linked</option>
                  {directoryContacts.filter(c => (c.primary_role || '').toLowerCase().includes('publisher') || (c.primary_role || '').toLowerCase().includes('admin')).length > 0 && (
                    <optgroup label="Publishers">
                      {directoryContacts.filter(c => (c.primary_role || '').toLowerCase().includes('publisher')).map(c => (
                        <option key={c.id} value={c.id}>{c.display_name}{c.company ? ` (${c.company})` : ''}</option>
                      ))}
                    </optgroup>
                  )}
                  <optgroup label="All Contacts">
                    {directoryContacts.map(c => (
                      <option key={c.id} value={c.id}>{c.display_name}{c.company ? ` (${c.company})` : ''}</option>
                    ))}
                  </optgroup>
                </select>
              </div>

              <div>
                <label className="block text-[15px] font-medium text-[#3D4A44] mb-2">Administrator Contact</label>
                <select
                  value={creatorForm.admin_contact_id || ''}
                  onChange={(e) => setCreatorForm({...creatorForm, admin_contact_id: e.target.value ? parseInt(e.target.value) : 0})}
                  className="w-full px-4 py-3 border border-[rgba(59,77,67,0.2)] rounded-xl focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                >
                  <option value="">No administrator linked</option>
                  {directoryContacts.filter(c => (c.primary_role || '').toLowerCase().includes('admin')).length > 0 && (
                    <optgroup label="Administrators">
                      {directoryContacts.filter(c => (c.primary_role || '').toLowerCase().includes('admin')).map(c => (
                        <option key={c.id} value={c.id}>{c.display_name}{c.company ? ` (${c.company})` : ''}</option>
                      ))}
                    </optgroup>
                  )}
                  <optgroup label="All Contacts">
                    {directoryContacts.map(c => (
                      <option key={c.id} value={c.id}>{c.display_name}{c.company ? ` (${c.company})` : ''}</option>
                    ))}
                  </optgroup>
                </select>
              </div>

              <div className="border-t border-[rgba(59,77,67,0.1)] pt-4 mt-4">
                <h3 className="text-[15px] font-semibold text-[#3D4A44] mb-3">Bio</h3>
                <textarea
                  value={creatorForm.bio}
                  onChange={(e) => setCreatorForm({...creatorForm, bio: e.target.value})}
                  className="w-full px-4 py-3 border border-[rgba(59,77,67,0.2)] rounded-xl focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent resize-none"
                  placeholder="Brief bio or description..."
                  rows={3}
                />
              </div>

              <div className="border-t border-[rgba(59,77,67,0.1)] pt-4 mt-4">
                <h3 className="text-[15px] font-semibold text-[#3D4A44] mb-3">DSP Links</h3>
                <div className="space-y-3">
                  <div>
                    <label className="block text-xs font-medium text-[#7A8580] mb-1">Spotify URL</label>
                    <div className="flex items-center gap-2">
                      <svg className="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24" fill="#1DB954"><path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/></svg>
                      <input
                        type="url"
                        value={creatorForm.spotify_url}
                        onChange={(e) => setCreatorForm({...creatorForm, spotify_url: e.target.value})}
                        className="flex-1 px-3 py-2 border border-[rgba(59,77,67,0.2)] rounded-xl text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                        placeholder="https://open.spotify.com/artist/..."
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-[#7A8580] mb-1">Apple Music URL</label>
                    <div className="flex items-center gap-2">
                      <svg className="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24" fill="#FA233B"><path d="M23.994 6.124a9.23 9.23 0 00-.24-2.19c-.317-1.31-1.062-2.31-2.18-3.043A5.022 5.022 0 0019.7.28C18.96.094 18.2.017 17.44.001 17.2-.003 16.96 0 16.72 0H7.28c-.24 0-.48-.003-.72.001C5.8.017 5.04.094 4.3.28c-.9.23-1.7.67-2.38 1.31-.55.5-.96 1.12-1.24 1.83-.24.6-.36 1.23-.4 1.88-.04.5-.06 1-.07 1.5V17.2c.01.5.03 1 .07 1.5.04.65.16 1.28.4 1.88.28.71.69 1.33 1.24 1.83.68.64 1.48 1.08 2.38 1.31.74.19 1.5.26 2.26.28.24.003.48.01.72.01h9.44c.24 0 .48.003.72-.01.76-.02 1.52-.09 2.26-.28.9-.23 1.7-.67 2.38-1.31.55-.5.96-1.12 1.24-1.83.24-.6.36-1.23.4-1.88.04-.5.06-1 .07-1.5V6.124z"/></svg>
                      <input
                        type="url"
                        value={creatorForm.apple_music_url}
                        onChange={(e) => setCreatorForm({...creatorForm, apple_music_url: e.target.value})}
                        className="flex-1 px-3 py-2 border border-[rgba(59,77,67,0.2)] rounded-xl text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                        placeholder="https://music.apple.com/artist/..."
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-[#7A8580] mb-1">YouTube URL</label>
                    <div className="flex items-center gap-2">
                      <svg className="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24" fill="#FF0000"><path d="M23.498 6.186a3.016 3.016 0 00-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 00.502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 002.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 002.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>
                      <input
                        type="url"
                        value={creatorForm.youtube_url}
                        onChange={(e) => setCreatorForm({...creatorForm, youtube_url: e.target.value})}
                        className="flex-1 px-3 py-2 border border-[rgba(59,77,67,0.2)] rounded-xl text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                        placeholder="https://youtube.com/@..."
                      />
                    </div>
                  </div>
                </div>
              </div>

              <div className="border-t border-[rgba(59,77,67,0.1)] pt-4 mt-4">
                <h3 className="text-[15px] font-semibold text-[#3D4A44] mb-3">Social Media</h3>
                <div className="space-y-3">
                  <div>
                    <label className="block text-xs font-medium text-[#7A8580] mb-1">Instagram URL</label>
                    <div className="flex items-center gap-2">
                      <svg className="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24" fill="#E1306C"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z"/></svg>
                      <input
                        type="url"
                        value={creatorForm.instagram_url}
                        onChange={(e) => setCreatorForm({...creatorForm, instagram_url: e.target.value})}
                        className="flex-1 px-3 py-2 border border-[rgba(59,77,67,0.2)] rounded-xl text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                        placeholder="https://instagram.com/..."
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-[#7A8580] mb-1">X (Twitter) URL</label>
                    <div className="flex items-center gap-2">
                      <svg className="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24" fill="#000000"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
                      <input
                        type="url"
                        value={creatorForm.twitter_url}
                        onChange={(e) => setCreatorForm({...creatorForm, twitter_url: e.target.value})}
                        className="flex-1 px-3 py-2 border border-[rgba(59,77,67,0.2)] rounded-xl text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                        placeholder="https://x.com/..."
                      />
                    </div>
                  </div>
                </div>
              </div>

              <div className="border-t border-[rgba(59,77,67,0.1)] pt-4 mt-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-[15px] font-semibold text-[#3D4A44]">Custom Links</h3>
                  <button
                    type="button"
                    onClick={() => setCreatorForm({...creatorForm, custom_links: [...creatorForm.custom_links, { name: '', url: '' }]})}
                    className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-[#5B8A72] border border-[#5B8A72] rounded-lg hover:bg-[#5B8A72] hover:text-white transition-colors"
                  >
                    <PlusIcon className="w-3.5 h-3.5" />
                    Add Link
                  </button>
                </div>
                {creatorForm.custom_links.length === 0 && (
                  <p className="text-xs text-[#7A8580] italic">No custom links added yet.</p>
                )}
                <div className="space-y-2">
                  {creatorForm.custom_links.map((link, idx) => (
                    <div key={idx} className="flex items-center gap-2">
                      <input
                        type="text"
                        value={link.name}
                        onChange={(e) => {
                          const updated = [...creatorForm.custom_links]
                          updated[idx] = { ...updated[idx], name: e.target.value }
                          setCreatorForm({...creatorForm, custom_links: updated})
                        }}
                        className="w-1/3 px-3 py-2 border border-[rgba(59,77,67,0.2)] rounded-xl text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                        placeholder="Name"
                      />
                      <input
                        type="url"
                        value={link.url}
                        onChange={(e) => {
                          const updated = [...creatorForm.custom_links]
                          updated[idx] = { ...updated[idx], url: e.target.value }
                          setCreatorForm({...creatorForm, custom_links: updated})
                        }}
                        className="flex-1 px-3 py-2 border border-[rgba(59,77,67,0.2)] rounded-xl text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent"
                        placeholder="https://..."
                      />
                      <button
                        type="button"
                        onClick={() => {
                          const updated = creatorForm.custom_links.filter((_, i) => i !== idx)
                          setCreatorForm({...creatorForm, custom_links: updated})
                        }}
                        className="p-2 text-[#C47068] hover:bg-[rgba(255,59,48,0.1)] rounded-lg transition-colors"
                      >
                        <TrashIcon className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              <div className="border-t border-[rgba(59,77,67,0.1)] pt-4 mt-4">
                <h3 className="text-[15px] font-semibold text-[#3D4A44] mb-1">Roster Export Settings</h3>
                <p className="text-xs text-[#7A8580] mb-3">Choose which fields appear in the exported Roster PDF</p>
                <div className="space-y-2">
                  {[
                    { key: 'bio', label: 'Bio / Description', alwaysShow: true },
                    { key: 'spotify_url', label: 'Spotify' },
                    { key: 'apple_music_url', label: 'Apple Music' },
                    { key: 'youtube_url', label: 'YouTube' },
                    { key: 'instagram_url', label: 'Instagram' },
                    { key: 'twitter_url', label: 'X / Twitter' },
                    { key: 'website_url', label: 'Website' },
                  ]
                    .filter(f => f.alwaysShow || creatorForm[f.key])
                    .map(field => (
                      <div key={field.key} className="flex items-center justify-between py-1.5 px-3 rounded-lg hover:bg-[#F5F7F4] transition-colors">
                        <span className="text-sm text-[#3D4A44]">{field.label}</span>
                        <button
                          type="button"
                          onClick={() => {
                            const fields = creatorForm.roster_export_fields || []
                            const updated = fields.includes(field.key)
                              ? fields.filter(f => f !== field.key)
                              : [...fields, field.key]
                            setCreatorForm({...creatorForm, roster_export_fields: updated})
                          }}
                          className="relative inline-flex h-5 w-9 items-center rounded-full transition-colors"
                          style={{ backgroundColor: (creatorForm.roster_export_fields || []).includes(field.key) ? '#5B8A72' : '#D1D5DB' }}
                        >
                          <span
                            className="inline-block h-3.5 w-3.5 rounded-full bg-white transition-transform shadow-sm"
                            style={{ transform: (creatorForm.roster_export_fields || []).includes(field.key) ? 'translateX(18px)' : 'translateX(3px)' }}
                          />
                        </button>
                      </div>
                    ))
                  }
                  <div className="flex items-center justify-between py-1.5 px-3 rounded-lg hover:bg-[#F5F7F4] transition-colors">
                    <span className="text-sm text-[#3D4A44]">Custom Links (e.g. Demos)</span>
                    <button
                      type="button"
                      onClick={() => {
                        const fields = creatorForm.roster_export_fields || []
                        const updated = fields.includes('custom_links')
                          ? fields.filter(f => f !== 'custom_links')
                          : [...fields, 'custom_links']
                        setCreatorForm({...creatorForm, roster_export_fields: updated})
                      }}
                      className="relative inline-flex h-5 w-9 items-center rounded-full transition-colors"
                      style={{ backgroundColor: (creatorForm.roster_export_fields || []).includes('custom_links') ? '#5B8A72' : '#D1D5DB' }}
                    >
                      <span
                        className="inline-block h-3.5 w-3.5 rounded-full bg-white transition-transform shadow-sm"
                        style={{ transform: (creatorForm.roster_export_fields || []).includes('custom_links') ? 'translateX(18px)' : 'translateX(3px)' }}
                      />
                    </button>
                  </div>
                </div>
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowEditCreatorModal(false)}
                  className="flex-1 px-4 py-3 border border-[rgba(59,77,67,0.2)] text-[#3D4A44] rounded-xl font-medium hover:bg-[#EEF1EC] transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={editingCreator || !creatorForm.display_name.trim()}
                  className="flex-1 px-4 py-3 bg-[#5B8A72] text-white rounded-xl font-medium hover:bg-[#4A7862] transition-colors disabled:opacity-50"
                >
                  {editingCreator ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showAddFeeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/20 backdrop-blur-sm" onClick={() => setShowAddFeeModal(false)} />
          <div className="relative w-full max-w-md bg-white rounded-[18px] shadow-2xl overflow-hidden">
            <div className="border-b border-[rgba(59,77,67,0.08)] px-6 py-4 flex items-center justify-between">
              <h2 className="text-lg font-bold text-[#3D4A44]">Add Fee</h2>
              <button onClick={() => setShowAddFeeModal(false)} className="p-2 rounded-lg text-[#7A8580] hover:bg-[#EEF1EC]"><XMarkIcon className="w-5 h-5" /></button>
            </div>
            <form onSubmit={handleCreateFee} className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-medium text-[#7A8580] mb-1">Fee Type</label>
                <select value={feeForm.fee_type} onChange={(e) => setFeeForm({...feeForm, fee_type: e.target.value})} className="w-full border border-[rgba(59,77,67,0.15)] rounded-lg px-3 py-2 text-sm text-[#3D4A44] bg-white focus:outline-none focus:ring-2 focus:ring-[#5B8A72]/30">
                  <option value="MANAGEMENT_FEE">Management Fee</option>
                  <option value="ADMIN_FEE">Admin Fee</option>
                  <option value="DISTRIBUTION_FEE">Distribution Fee</option>
                  <option value="SYNC_FEE">Sync Fee</option>
                  <option value="LEGAL_FEE">Legal Fee</option>
                  <option value="OTHER">Other</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-[#7A8580] mb-1">Description</label>
                <input type="text" value={feeForm.description} onChange={(e) => setFeeForm({...feeForm, description: e.target.value})} className="w-full border border-[rgba(59,77,67,0.15)] rounded-lg px-3 py-2 text-sm text-[#3D4A44] bg-white focus:outline-none focus:ring-2 focus:ring-[#5B8A72]/30" />
              </div>
              <div>
                <label className="block text-xs font-medium text-[#7A8580] mb-1">Amount ($)</label>
                <input type="number" step="0.01" value={feeForm.amount} onChange={(e) => setFeeForm({...feeForm, amount: e.target.value})} required className="w-full border border-[rgba(59,77,67,0.15)] rounded-lg px-3 py-2 text-sm text-[#3D4A44] bg-white focus:outline-none focus:ring-2 focus:ring-[#5B8A72]/30" />
              </div>
              <div>
                <label className="block text-xs font-medium text-[#7A8580] mb-1">Date</label>
                <input type="date" value={feeForm.fee_date} onChange={(e) => setFeeForm({...feeForm, fee_date: e.target.value})} className="w-full border border-[rgba(59,77,67,0.15)] rounded-lg px-3 py-2 text-sm text-[#3D4A44] bg-white focus:outline-none focus:ring-2 focus:ring-[#5B8A72]/30" />
              </div>
              <div>
                <label className="block text-xs font-medium text-[#7A8580] mb-1">Notes</label>
                <textarea value={feeForm.notes} onChange={(e) => setFeeForm({...feeForm, notes: e.target.value})} rows={2} className="w-full border border-[rgba(59,77,67,0.15)] rounded-lg px-3 py-2 text-sm text-[#3D4A44] bg-white focus:outline-none focus:ring-2 focus:ring-[#5B8A72]/30" />
              </div>
              <div className="flex gap-3 pt-2">
                <button type="submit" disabled={savingFee || !feeForm.amount} className="bg-[#5B8A72] hover:bg-[#4A7A62] text-white px-5 py-2.5 rounded-xl font-medium transition-all disabled:opacity-50">
                  {savingFee ? 'Saving...' : 'Add Fee'}
                </button>
                <button type="button" onClick={() => setShowAddFeeModal(false)} className="px-5 py-2.5 rounded-xl font-medium text-[#7A8580] hover:bg-[#EEF1EC]">Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showAddAdvanceModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/20 backdrop-blur-sm" onClick={() => setShowAddAdvanceModal(false)} />
          <div className="relative w-full max-w-md bg-white rounded-[18px] shadow-2xl overflow-hidden">
            <div className="border-b border-[rgba(59,77,67,0.08)] px-6 py-4 flex items-center justify-between">
              <h2 className="text-lg font-bold text-[#3D4A44]">Add Advance</h2>
              <button onClick={() => setShowAddAdvanceModal(false)} className="p-2 rounded-lg text-[#7A8580] hover:bg-[#EEF1EC]"><XMarkIcon className="w-5 h-5" /></button>
            </div>
            <form onSubmit={handleCreateAdvance} className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-medium text-[#7A8580] mb-1">Description</label>
                <input type="text" value={advanceForm.description} onChange={(e) => setAdvanceForm({...advanceForm, description: e.target.value})} className="w-full border border-[rgba(59,77,67,0.15)] rounded-lg px-3 py-2 text-sm text-[#3D4A44] bg-white focus:outline-none focus:ring-2 focus:ring-[#5B8A72]/30" />
              </div>
              <div>
                <label className="block text-xs font-medium text-[#7A8580] mb-1">Amount ($)</label>
                <input type="number" step="0.01" value={advanceForm.amount} onChange={(e) => setAdvanceForm({...advanceForm, amount: e.target.value})} required className="w-full border border-[rgba(59,77,67,0.15)] rounded-lg px-3 py-2 text-sm text-[#3D4A44] bg-white focus:outline-none focus:ring-2 focus:ring-[#5B8A72]/30" />
              </div>
              <div>
                <label className="block text-xs font-medium text-[#7A8580] mb-1">Date</label>
                <input type="date" value={advanceForm.advance_date} onChange={(e) => setAdvanceForm({...advanceForm, advance_date: e.target.value})} className="w-full border border-[rgba(59,77,67,0.15)] rounded-lg px-3 py-2 text-sm text-[#3D4A44] bg-white focus:outline-none focus:ring-2 focus:ring-[#5B8A72]/30" />
              </div>
              <div>
                <label className="block text-xs font-medium text-[#7A8580] mb-1">Notes</label>
                <textarea value={advanceForm.notes} onChange={(e) => setAdvanceForm({...advanceForm, notes: e.target.value})} rows={2} className="w-full border border-[rgba(59,77,67,0.15)] rounded-lg px-3 py-2 text-sm text-[#3D4A44] bg-white focus:outline-none focus:ring-2 focus:ring-[#5B8A72]/30" />
              </div>
              <div className="flex gap-3 pt-2">
                <button type="submit" disabled={savingAdvance || !advanceForm.amount} className="bg-[#5B8A72] hover:bg-[#4A7A62] text-white px-5 py-2.5 rounded-xl font-medium transition-all disabled:opacity-50">
                  {savingAdvance ? 'Saving...' : 'Add Advance'}
                </button>
                <button type="button" onClick={() => setShowAddAdvanceModal(false)} className="px-5 py-2.5 rounded-xl font-medium text-[#7A8580] hover:bg-[#EEF1EC]">Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl p-6 max-w-md w-full">
            <h3 className="text-xl font-semibold text-[#3D4A44] mb-3">Delete {selectedSongs.size} Song{selectedSongs.size > 1 ? 's' : ''}?</h3>
            <p className="text-[#7A8580] mb-6">
              This will permanently remove the selected song{selectedSongs.size > 1 ? 's' : ''} and all associated data (credits, contracts, checklist items). This cannot be undone.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                disabled={deleting}
                className="flex-1 px-4 py-3 border border-[rgba(59,77,67,0.2)] rounded-xl text-[#3D4A44] font-medium hover:bg-[#F5F7F4] transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleBulkDelete}
                disabled={deleting}
                className="flex-1 px-4 py-3 bg-[#C47068] text-white rounded-xl font-medium hover:bg-[#B05E56] transition-colors disabled:opacity-50"
              >
                {deleting ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}

      {showMergeModal && (() => {
        const mergeSongsList = songs.filter(s => selectedSongs.has(s.id))
        return (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[90vh] flex flex-col">
              <div className="flex items-center justify-between p-6 border-b border-[rgba(59,77,67,0.08)]">
                <div>
                  <h3 className="text-lg font-semibold text-[#3D4A44]">Merge Songs</h3>
                  <p className="text-sm text-[#7A8580] mt-0.5">Select which song to keep as the primary. All credits and data from other songs will be merged into it.</p>
                </div>
                <button onClick={() => { setShowMergeModal(false); setMergePrimaryId(null) }} className="text-[#7A8580] hover:text-[#3D4A44]">
                  <XMarkIcon className="w-5 h-5" />
                </button>
              </div>
              <div className="flex-1 overflow-y-auto p-6 space-y-3">
                {mergeSongsList.map(song => (
                  <div
                    key={song.id}
                    onClick={() => setMergePrimaryId(song.id)}
                    className={`p-4 rounded-xl border-2 cursor-pointer transition-all ${
                      mergePrimaryId === song.id
                        ? 'border-[#5B8A72] bg-[#EDF5F0]'
                        : 'border-[rgba(59,77,67,0.1)] hover:border-[rgba(59,77,67,0.2)]'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-[#3D4A44] text-sm truncate">{song.title}</p>
                        <p className="text-xs text-[#7A8580]">{song.primary_artist || 'No artist'}</p>
                        <div className="flex items-center gap-3 mt-1 text-xs text-[#A0A8A3]">
                          {song.isrc && <span>ISRC: {song.isrc}</span>}
                          {song.release_date && <span>Released: {song.release_date}</span>}
                          {song.client_name && <span>Client: {song.client_name}</span>}
                        </div>
                      </div>
                      {mergePrimaryId === song.id && (
                        <span className="px-2.5 py-1 bg-[#5B8A72] text-white text-xs font-semibold rounded-full ml-3 whitespace-nowrap">Primary</span>
                      )}
                    </div>
                  </div>
                ))}
                <div className="bg-[#FAFBF9] rounded-xl p-3 text-xs text-[#7A8580]">
                  <p className="font-medium text-[#3D4A44] mb-1">What happens when you merge:</p>
                  <ul className="list-disc pl-4 space-y-0.5">
                    <li>All credits from merged songs are combined onto the primary</li>
                    <li>Placements, contracts, and accounting data are transferred</li>
                    <li>Missing metadata on the primary is filled from merged songs</li>
                    <li>Merged songs are permanently deleted</li>
                  </ul>
                </div>
              </div>
              <div className="flex gap-3 p-6 border-t border-[rgba(59,77,67,0.08)]">
                <button
                  onClick={() => { setShowMergeModal(false); setMergePrimaryId(null) }}
                  disabled={merging}
                  className="flex-1 px-4 py-3 border border-[rgba(59,77,67,0.2)] rounded-xl text-[#3D4A44] font-medium hover:bg-[#F5F7F4] transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleMergeSongs}
                  disabled={merging || !mergePrimaryId}
                  className="flex-1 px-4 py-3 bg-[#5A8A9A] text-white rounded-xl font-medium hover:bg-[#4A7A8A] transition-colors disabled:opacity-50"
                >
                  {merging ? 'Merging...' : `Merge into Primary`}
                </button>
              </div>
            </div>
          </div>
        )
      })()}

      {showCreateContractModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between p-6 border-b border-[rgba(59,77,67,0.08)]">
              <div>
                <h3 className="text-lg font-semibold text-[#3D4A44]">New Contract</h3>
                <p className="text-sm text-[#7A8580] mt-0.5">{creator.display_name || creator.legal_name} will be added as a party automatically</p>
              </div>
              <button onClick={() => setShowCreateContractModal(false)} className="text-[#7A8580] hover:text-[#3D4A44]">
                <XMarkIcon className="w-5 h-5" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Contract Title *</label>
                  <input
                    type="text"
                    value={createContractForm.title}
                    onChange={(e) => setCreateContractForm(prev => ({ ...prev, title: e.target.value }))}
                    className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                    placeholder="e.g., Master Recording Agreement"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Type</label>
                  <select
                    value={createContractForm.contract_type}
                    onChange={(e) => setCreateContractForm(prev => ({ ...prev, contract_type: e.target.value }))}
                    className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  >
                    <option value="MASTER">Master</option>
                    <option value="PUBLISHING">Publishing</option>
                    <option value="SYNC_LICENSE">Sync License</option>
                    <option value="DISTRIBUTION">Distribution</option>
                    <option value="MANAGEMENT">Management</option>
                    <option value="SPLIT_SHEET">Split Sheet</option>
                    <option value="OTHER">Other</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Direction</label>
                  <select
                    value={createContractForm.payment_direction}
                    onChange={(e) => setCreateContractForm(prev => ({ ...prev, payment_direction: e.target.value }))}
                    className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  >
                    <option value="INCOMING">Incoming (Revenue)</option>
                    <option value="OUTGOING">Outgoing (Expense)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Status</label>
                  <select
                    value={createContractForm.status}
                    onChange={(e) => setCreateContractForm(prev => ({ ...prev, status: e.target.value }))}
                    className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  >
                    <option value="DRAFT">Draft</option>
                    <option value="ACTIVE">Active</option>
                    <option value="EXPIRED">Expired</option>
                    <option value="TERMINATED">Terminated</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Reference #</label>
                  <input
                    type="text"
                    value={createContractForm.reference_number}
                    onChange={(e) => setCreateContractForm(prev => ({ ...prev, reference_number: e.target.value }))}
                    className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                    placeholder="e.g., AGR-2026-001"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Start Date</label>
                  <input
                    type="date"
                    value={createContractForm.start_date}
                    onChange={(e) => setCreateContractForm(prev => ({ ...prev, start_date: e.target.value }))}
                    className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">End Date</label>
                  <input
                    type="date"
                    value={createContractForm.end_date}
                    onChange={(e) => setCreateContractForm(prev => ({ ...prev, end_date: e.target.value }))}
                    className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Territory</label>
                  <input
                    type="text"
                    value={createContractForm.territory}
                    onChange={(e) => setCreateContractForm(prev => ({ ...prev, territory: e.target.value }))}
                    className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                    placeholder="e.g., Worldwide, US, UK"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Advance</label>
                  <div className="flex gap-2">
                    <select
                      value={createContractForm.advance_currency}
                      onChange={(e) => setCreateContractForm(prev => ({ ...prev, advance_currency: e.target.value }))}
                      className="w-20 border border-[rgba(59,77,67,0.12)] rounded-lg px-2 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44] text-sm"
                    >
                      <option value="USD">USD</option>
                      <option value="EUR">EUR</option>
                      <option value="GBP">GBP</option>
                    </select>
                    <input
                      type="number"
                      value={createContractForm.advance_amount}
                      onChange={(e) => setCreateContractForm(prev => ({ ...prev, advance_amount: e.target.value }))}
                      className="flex-1 border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                      placeholder="0.00"
                    />
                  </div>
                </div>
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-[#3D4A44] mb-1">Notes</label>
                  <textarea
                    value={createContractForm.notes}
                    onChange={(e) => setCreateContractForm(prev => ({ ...prev, notes: e.target.value }))}
                    className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                    rows={2}
                    placeholder="Additional notes..."
                  />
                </div>
              </div>

              <div className="border-t border-[rgba(59,77,67,0.08)] pt-4">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-sm font-semibold text-[#3D4A44]">Additional Parties</h4>
                </div>
                <div className="mb-2 p-2 bg-[#EEF1EC] rounded-lg flex items-center gap-2">
                  <span className="text-sm text-[#3D4A44] flex-1">{creator.display_name || creator.legal_name}</span>
                  <span className="text-xs px-2 py-0.5 bg-[#5B8A72] text-white rounded-full">ARTIST</span>
                  <span className="text-xs text-[#7A8580] italic">auto-added</span>
                </div>
                {createContractParties.map((p, idx) => (
                  <div key={idx} className="flex items-center space-x-2 mb-2 p-2 bg-[#F5F7F4] rounded-lg">
                    <span className="text-sm text-[#3D4A44] flex-1">{p.party_name}</span>
                    <span className="text-xs px-2 py-0.5 bg-[#EEF1EC] rounded-full text-[#7A8580]">{p.party_role}</span>
                    {p.contact_email && <span className="text-xs text-[#7A8580]">{p.contact_email}</span>}
                    <button onClick={() => setCreateContractParties(prev => prev.filter((_, i) => i !== idx))} className="text-[#7A8580] hover:text-red-500">
                      <XMarkIcon className="w-4 h-4" />
                    </button>
                  </div>
                ))}
                <div className="grid grid-cols-4 gap-2">
                  <input
                    type="text"
                    placeholder="Name"
                    value={createContractPartyForm.party_name}
                    onChange={(e) => setCreateContractPartyForm(prev => ({ ...prev, party_name: e.target.value }))}
                    className="border border-[rgba(59,77,67,0.12)] rounded-lg px-2 py-1.5 text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  />
                  <select
                    value={createContractPartyForm.party_role}
                    onChange={(e) => setCreateContractPartyForm(prev => ({ ...prev, party_role: e.target.value }))}
                    className="border border-[rgba(59,77,67,0.12)] rounded-lg px-2 py-1.5 text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  >
                    {PARTY_ROLES.map(r => <option key={r} value={r}>{r}</option>)}
                  </select>
                  <input
                    type="email"
                    placeholder="Email"
                    value={createContractPartyForm.contact_email}
                    onChange={(e) => setCreateContractPartyForm(prev => ({ ...prev, contact_email: e.target.value }))}
                    className="border border-[rgba(59,77,67,0.12)] rounded-lg px-2 py-1.5 text-sm focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  />
                  <button
                    onClick={() => {
                      if (!createContractPartyForm.party_name.trim()) return
                      setCreateContractParties(prev => [...prev, { ...createContractPartyForm }])
                      setCreateContractPartyForm({ party_name: '', party_role: 'ARTIST', contact_email: '' })
                    }}
                    className="px-3 py-1.5 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] transition-colors text-sm"
                  >
                    Add
                  </button>
                </div>
              </div>
            </div>
            {createContractError && (
              <div className="mx-6 mb-0 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                {createContractError}
              </div>
            )}
            <div className="flex justify-end space-x-3 p-6 border-t border-[rgba(59,77,67,0.08)]">
              <button
                onClick={() => { setShowCreateContractModal(false) }}
                className="px-4 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg text-[#3D4A44] hover:bg-[#EEF1EC] transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateContract}
                disabled={!createContractForm.title.trim() || createContractLoading}
                className="px-4 py-2 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {createContractLoading ? 'Creating...' : 'Create Contract'}
              </button>
            </div>
          </div>
        </div>
      )}

      {showUploadDocModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between p-6 border-b border-[rgba(59,77,67,0.08)]">
              <h3 className="text-lg font-semibold text-[#3D4A44]">Upload Contract Document</h3>
              <button onClick={() => setShowUploadDocModal(false)} className="text-[#7A8580] hover:text-[#3D4A44]">
                <XMarkIcon className="w-5 h-5" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              <div className="border-2 border-dashed border-[rgba(59,77,67,0.2)] rounded-lg p-6 text-center hover:border-[#5B8A72] transition-colors">
                {uploadDocFile ? (
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <PaperClipIcon className="w-5 h-5 text-[#5B8A72]" />
                      <span className="text-sm text-[#3D4A44] truncate max-w-[250px]">{uploadDocFile.name}</span>
                      <span className="text-xs text-[#7A8580]">({(uploadDocFile.size / 1024 / 1024).toFixed(2)} MB)</span>
                    </div>
                    <button onClick={() => setUploadDocFile(null)} className="text-[#7A8580] hover:text-red-500">
                      <XMarkIcon className="w-4 h-4" />
                    </button>
                  </div>
                ) : (
                  <label className="cursor-pointer">
                    <CloudArrowUpIcon className="w-10 h-10 text-[#7A8580] mx-auto mb-2" />
                    <p className="text-sm text-[#5B8A72] font-medium">Click to select a contract file</p>
                    <p className="text-xs text-[#7A8580] mt-1">PDF, DOC, DOCX, Excel, or images (max 50MB)</p>
                    <input
                      type="file"
                      className="hidden"
                      accept=".pdf,.doc,.docx,.xls,.xlsx,.jpg,.jpeg,.png"
                      onChange={(e) => { if (e.target.files[0]) setUploadDocFile(e.target.files[0]) }}
                    />
                  </label>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Attach to Contract *</label>
                <select
                  value={uploadDocContractId}
                  onChange={(e) => setUploadDocContractId(e.target.value)}
                  className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                >
                  <option value="">Select a contract...</option>
                  {creatorContracts.map(c => (
                    <option key={c.id} value={c.id}>{c.title}{c.reference_number ? ` (${c.reference_number})` : ''}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-[#3D4A44] mb-1">Description (optional)</label>
                <input
                  type="text"
                  value={uploadDocDescription}
                  onChange={(e) => setUploadDocDescription(e.target.value)}
                  className="w-full border border-[rgba(59,77,67,0.12)] rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent bg-white text-[#3D4A44]"
                  placeholder="e.g., Signed master agreement"
                />
              </div>
            </div>
            {uploadDocError && (
              <div className="mx-6 mb-0 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                {uploadDocError}
              </div>
            )}
            <div className="flex justify-end space-x-3 p-6 border-t border-[rgba(59,77,67,0.08)]">
              <button
                onClick={() => setShowUploadDocModal(false)}
                className="px-4 py-2 border border-[rgba(59,77,67,0.12)] rounded-lg text-[#3D4A44] hover:bg-[#EEF1EC] transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleUploadDoc}
                disabled={!uploadDocFile || !uploadDocContractId || uploadDocLoading}
                className="flex items-center space-x-2 px-4 py-2 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <CloudArrowUpIcon className="w-5 h-5" />
                <span>{uploadDocLoading ? 'Uploading...' : 'Upload Document'}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {selectedSongForDetail && (
        <SongDetailModal
          song={selectedSongForDetail}
          onClose={() => setSelectedSongForDetail(null)}
          onSongUpdated={(data, action) => {
            if (action === 'duplicate' && data) {
              setTimeout(() => setSelectedSongForDetail(data), 100)
            }
            if (organizationId) loadSongs(organizationId)
            if (activeTab === 'accounting') loadAccounting()
          }}
        />
      )}
    </div>
  )
}
