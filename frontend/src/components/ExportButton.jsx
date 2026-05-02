import { useEffect, useRef, useState } from 'react'
import axios from 'axios'
import { ArrowDownTrayIcon, ChevronDownIcon } from '@heroicons/react/24/outline'

const FORMAT_LABELS = {
  pdf: 'PDF',
  xlsx: 'Excel',
  csv: 'CSV',
}

const FORMAT_ICONS = {
  pdf: '📄',
  xlsx: '📊',
  csv: '📋',
}

const FORMAT_MIME = {
  pdf: 'application/pdf',
  xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  csv: 'text/csv',
}

function buildUrl(baseUrl, format, formatStrategy) {
  if (typeof formatStrategy === 'function') return formatStrategy(format)
  if (formatStrategy === 'extension') {
    if (baseUrl.includes('?')) {
      const [path, query] = baseUrl.split('?')
      return `${path}.${format}?${query}`
    }
    return `${baseUrl}.${format}`
  }
  if (formatStrategy === 'path') {
    return `${baseUrl.replace(/\/$/, '')}/${format}`
  }
  const sep = baseUrl.includes('?') ? '&' : '?'
  return `${baseUrl}${sep}format=${format}`
}

export default function ExportButton({
  baseUrl,
  filename = 'export',
  formats = ['pdf', 'xlsx', 'csv'],
  formatStrategy = 'query',
  size = 'md',
  variant = 'primary',
  label = 'Export',
  className = '',
  onError,
  onSuccess,
}) {
  const [open, setOpen] = useState(false)
  const [downloading, setDownloading] = useState(null)
  const ref = useRef(null)

  useEffect(() => {
    if (!open) return
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  const handleDownload = async (format) => {
    setDownloading(format)
    setOpen(false)
    const url = buildUrl(baseUrl, format, formatStrategy)
    try {
      const res = await axios.get(url, { responseType: 'blob' })
      const blob = new Blob([res.data], { type: FORMAT_MIME[format] || 'application/octet-stream' })
      const objectUrl = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = objectUrl
      a.download = `${filename}.${format}`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      setTimeout(() => URL.revokeObjectURL(objectUrl), 1000)
      if (onSuccess) onSuccess(format)
    } catch (err) {
      const detail = err.response?.data?.detail || err.message || 'Download failed'
      if (onError) onError(detail, format)
      else console.error('ExportButton download failed:', detail)
    } finally {
      setDownloading(null)
    }
  }

  const sizeClasses = {
    sm: 'px-3 py-1.5 text-xs',
    md: 'px-4 py-2 text-sm',
    lg: 'px-5 py-2.5 text-base',
  }[size] || 'px-4 py-2 text-sm'

  const variantClasses =
    variant === 'primary'
      ? 'bg-[#5B8A72] text-white hover:bg-[#4A7A62] disabled:opacity-50'
      : 'bg-white text-[#3D4A44] border border-[#D1D5CE] hover:bg-[#F5F7F4] disabled:opacity-50'

  if (formats.length === 1) {
    const f = formats[0]
    return (
      <button
        type="button"
        onClick={() => handleDownload(f)}
        disabled={!!downloading}
        className={`inline-flex items-center gap-2 rounded-lg font-medium transition ${sizeClasses} ${variantClasses} ${className}`}
      >
        <ArrowDownTrayIcon className="w-4 h-4" />
        {downloading === f ? `Downloading ${FORMAT_LABELS[f]}…` : `Download ${FORMAT_LABELS[f]}`}
      </button>
    )
  }

  return (
    <div ref={ref} className={`relative inline-block ${className}`}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        disabled={!!downloading}
        className={`inline-flex items-center gap-2 rounded-lg font-medium transition ${sizeClasses} ${variantClasses}`}
      >
        <ArrowDownTrayIcon className="w-4 h-4" />
        {downloading ? `Exporting ${FORMAT_LABELS[downloading]}…` : label}
        <ChevronDownIcon className="w-4 h-4 -mr-1 opacity-80" />
      </button>
      {open && (
        <div
          className="absolute right-0 z-30 mt-2 w-44 origin-top-right rounded-lg border border-[#E5E8E3] bg-white shadow-lg ring-1 ring-black/5"
          role="menu"
        >
          <ul className="py-1">
            {formats.map((f) => (
              <li key={f}>
                <button
                  type="button"
                  onClick={() => handleDownload(f)}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm text-[#3D4A44] hover:bg-[#F5F7F4] text-left"
                >
                  <span className="text-base">{FORMAT_ICONS[f] || '📁'}</span>
                  <span className="flex-1 font-medium">{FORMAT_LABELS[f] || f.toUpperCase()}</span>
                  <span className="text-xs text-[#A0A8A3] uppercase">.{f}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
