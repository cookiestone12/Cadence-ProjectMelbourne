import React from 'react'
import { Squares2X2Icon, ListBulletIcon } from '@heroicons/react/24/outline'

const STORAGE_KEY_PREFIX = 'view_mode_'

export function getStoredViewMode(pageKey, defaultMode = 'grid') {
  try {
    const stored = localStorage.getItem(STORAGE_KEY_PREFIX + pageKey)
    if (stored === 'grid' || stored === 'list') return stored
    return defaultMode
  } catch {
    return defaultMode
  }
}

export function setStoredViewMode(pageKey, mode) {
  try {
    localStorage.setItem(STORAGE_KEY_PREFIX + pageKey, mode)
  } catch {}
}

export default function ViewToggle({ viewMode, onViewModeChange }) {
  return (
    <div className="flex items-center bg-[#EEF1EC] rounded-xl p-1">
      <button
        onClick={() => onViewModeChange('grid')}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
          viewMode === 'grid'
            ? 'bg-white text-[#3D4A44] shadow-sm'
            : 'text-[#7A8580] hover:text-[#3D4A44]'
        }`}
      >
        <Squares2X2Icon className="w-4 h-4" />
        <span className="hidden sm:inline">Grid</span>
      </button>
      <button
        onClick={() => onViewModeChange('list')}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
          viewMode === 'list'
            ? 'bg-white text-[#3D4A44] shadow-sm'
            : 'text-[#7A8580] hover:text-[#3D4A44]'
        }`}
      >
        <ListBulletIcon className="w-4 h-4" />
        <span className="hidden sm:inline">List</span>
      </button>
    </div>
  )
}
