import React, { useState, useCallback } from 'react'
import axios from 'axios'
import { FolderIcon, XMarkIcon, ArrowUturnLeftIcon, ChevronRightIcon } from '@heroicons/react/24/outline'

function getAuthHeaders() {
  return { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } }
}

export default function FolderPicker({ isOpen, onClose, onSelect, provider = 'DROPBOX', orgId, initialPath = '' }) {
  const [currentPath, setCurrentPath] = useState(initialPath || '')
  const [currentName, setCurrentName] = useState('')
  const [folderContents, setFolderContents] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [initialized, setInitialized] = useState(false)
  const [navStack, setNavStack] = useState([])

   const modalRef = React.useRef(null)

  const isGoogleDrive = provider === 'GOOGLE_DRIVE'

  const browseFolders = useCallback(async (path = '', folderName = '') => {
    setLoading(true)
    setError(null)
    try {
      let response
      if (orgId) {
        response = await axios.get(
          `/api/storage-scan/org/${orgId}/browse?provider=${encodeURIComponent(provider)}&path=${encodeURIComponent(path || '')}`,
          getAuthHeaders()
        )
      } else {
        response = await axios.get(
          `/api/integrations/dropbox/files?path=${encodeURIComponent(path || '')}`,
          getAuthHeaders()
        )
      }
      const files = response.data?.files || response.data?.entries || []
      setFolderContents(files)
      setCurrentPath(path || '')
      setCurrentName(folderName || '')
    } catch (err) {
      console.error('Error browsing folders:', err)
      const detail = err.response?.data?.detail
      if (detail) {
        setError(detail)
      } else if (err.response?.status === 401) {
        setError('Session expired. Please log in again.')
      } else if (err.response?.status >= 500) {
        setError('Server error. Please try again or reconnect your account in Settings.')
      } else {
        setError('Failed to load folders. Please check your connection in Settings > Integrations.')
      }
      setFolderContents([])
    } finally {
      setLoading(false)
    }
  }, [orgId, provider])

  React.useEffect(() => {
    if (isOpen && !initialized) {
      setNavStack([])
      browseFolders(initialPath || '', '')
      setInitialized(true)
    }
  }, [isOpen, initialized, browseFolders, initialPath])

  React.useEffect(() => {
  if (isOpen) {
    modalRef.current?.focus()
  }
}, [isOpen])

  React.useEffect(() => {
    if (!isOpen) {
      setInitialized(false)
      setFolderContents([])
      setCurrentPath('')
      setCurrentName('')
      setError(null)
      setNavStack([])
    }
  }, [isOpen])

React.useEffect(() => {
  const handleKeyDown = (event) => {
    if (event.key === 'Escape' && isOpen) {
      onClose()
    }
  }

  window.addEventListener('keydown', handleKeyDown)

  return () => {
    window.removeEventListener('keydown', handleKeyDown)
  }
}, [isOpen, onClose])

  if (!isOpen) return null

  const folders = folderContents.filter(item =>
    item['.tag'] === 'folder' || item.type === 'folder' || item.is_folder
  )

  const goUp = () => {
    if (navStack.length > 0) {
      const prev = navStack[navStack.length - 1]
      setNavStack(s => s.slice(0, -1))
      browseFolders(prev.path, prev.name)
    } else {
      browseFolders('', '')
    }
  }

  const navigateToFolder = (folder) => {
    setNavStack(s => [...s, { path: currentPath, name: currentName }])
    if (isGoogleDrive) {
      browseFolders(folder.id, folder.name)
    } else {
      const folderPath = folder.path_lower || folder.path_display || `${currentPath}/${folder.name}`
      browseFolders(folderPath, folder.name)
    }
  }

  const goToRoot = () => {
    setNavStack([])
    browseFolders('', '')
  }

  const handleSelect = () => {
    if (isGoogleDrive) {
      const displayPath = navStack.map(s => s.name).filter(Boolean).concat(currentName ? [currentName] : []).join('/')
      onSelect(currentPath || 'root', displayPath ? `/${displayPath}` : '/')
    } else {
      onSelect(currentPath || '/')
    }
    onClose()
  }

  const breadcrumbLabel = isGoogleDrive
    ? navStack.map(s => s.name).filter(Boolean).concat(currentName ? [currentName] : []).join(' / ') || 'root'
    : currentPath || '/ (root)'

  const hasParent = isGoogleDrive ? navStack.length > 0 || !!currentPath : !!currentPath

  return (
    <div className="fixed inset-0 bg-black/50 z-[60] flex items-center justify-center p-4" onClick={onClose}>
      <div
  ref={modalRef}
  tabIndex="-1"
  role="dialog"
  aria-modal="true"
  className="bg-white rounded-[18px] shadow-xl w-full max-w-lg max-h-[70vh] flex flex-col"
  onClick={e => e.stopPropagation()}
>
        <div className="flex items-center justify-between p-5 border-b border-[rgba(59,77,67,0.08)]">
          <div className="flex-1 min-w-0">
            <h3
  id="folder-picker-title"
  className="text-[18px] font-medium text-[#3D4A44]"
>
  Select Folder
</h3>
            <div className="flex items-center gap-1 mt-1 text-[13px] text-[#7A8580] overflow-hidden">
              <button
                onClick={goToRoot}
                className="shrink-0 hover:text-[#5B8A72] transition-colors"
              >
                / root
              </button>
              {isGoogleDrive ? (
                <>
                  {navStack.filter(s => s.name).map((s, idx) => (
                    <React.Fragment key={idx}>
                      <ChevronRightIcon className="w-3 h-3 shrink-0 text-[#B0B8B3]" />
                      <span className="truncate">{s.name}</span>
                    </React.Fragment>
                  ))}
                  {currentName && (
                    <>
                      <ChevronRightIcon className="w-3 h-3 shrink-0 text-[#B0B8B3]" />
                      <span className="truncate font-medium text-[#3D4A44]">{currentName}</span>
                    </>
                  )}
                </>
              ) : (
                currentPath && currentPath.split('/').filter(Boolean).map((part, idx) => (
                  <React.Fragment key={idx}>
                    <ChevronRightIcon className="w-3 h-3 shrink-0 text-[#B0B8B3]" />
                    <span className="truncate">{part}</span>
                  </React.Fragment>
                ))
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-[#7A8580] hover:text-[#3D4A44] rounded-lg hover:bg-[#FAFBF9] transition-colors ml-2"
          >
            <XMarkIcon className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-3">
          {hasParent && (
            <button
              onClick={goUp}
              className="w-full flex items-center gap-3 px-3 py-3 rounded-xl hover:bg-[#FAFBF9] transition-colors text-left mb-1"
            >
              <ArrowUturnLeftIcon className="w-5 h-5 text-[#7A8580]" />
              <span className="text-[15px] text-[#7A8580]">Go back</span>
            </button>
          )}

          {loading ? (
            <div className="flex items-center justify-center py-12 text-[#7A8580]">
              <svg className="animate-spin w-5 h-5 mr-2 text-[#5B8A72]" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              <span className="text-[15px]">Loading folders...</span>
            </div>
          ) : error ? (
            <div className="text-center py-8">
              <p className="text-red-500 text-[14px] mb-2">{error}</p>
              <button
                onClick={() => browseFolders(currentPath, currentName)}
                className="text-[13px] text-[#5B8A72] hover:underline"
              >
                Retry
              </button>
            </div>
          ) : folders.length === 0 ? (
            <div className="text-center py-8 text-[#7A8580] text-[14px]">
              No subfolders in this directory
            </div>
          ) : (
            <div className="space-y-0.5">
              {folders.map((folder, idx) => (
                <button
                  key={folder.id || idx}
                  onClick={() => navigateToFolder(folder)}
                  className="w-full flex items-center gap-3 px-3 py-3 rounded-xl hover:bg-[#FAFBF9] transition-colors text-left group"
                >
                  <FolderIcon className="w-5 h-5 text-[#5B8A72] shrink-0" />
                  <span className="text-[15px] text-[#3D4A44] truncate flex-1">{folder.name}</span>
                  <ChevronRightIcon className="w-4 h-4 text-[#B0B8B3] opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="p-4 border-t border-[rgba(59,77,67,0.08)]">
          <button
            onClick={handleSelect}
            className="w-full px-4 py-3 bg-[#5B8A72] text-white font-medium rounded-xl hover:bg-[#4A7862] transition-colors"
          >
            Select This Folder
          </button>
        </div>
      </div>
    </div>
  )
}
