import React, { useState, useEffect, useRef, useCallback } from 'react'
import axios from 'axios'
import {
  LifebuoyIcon,
  PlusIcon,
  XMarkIcon,
  PaperClipIcon,
  CheckCircleIcon,
  ClockIcon,
  ExclamationCircleIcon,
  PencilIcon,
  ArrowPathIcon,
  PhotoIcon,
  TrashIcon,
} from '@heroicons/react/24/outline'

const CATEGORIES = [
  { value: 'BUG_REPORT', label: 'Bug Report', color: '#C47068' },
  { value: 'FEATURE_REQUEST', label: 'Feature Request', color: '#5A8A9A' },
  { value: 'GENERAL_SUPPORT', label: 'General Support', color: '#5B8A72' },
]

const STATUS_CONFIG = {
  OPEN: { label: 'Open', color: '#C47068', bg: '#C47068/10', icon: ExclamationCircleIcon },
  IN_PROGRESS: { label: 'In Progress', color: '#C4956B', bg: '#C4956B/10', icon: ClockIcon },
  RESOLVED: { label: 'Resolved', color: '#5B8A72', bg: '#5B8A72/10', icon: CheckCircleIcon },
  CLOSED: { label: 'Closed', color: '#7A8580', bg: '#7A8580/10', icon: CheckCircleIcon },
}

function StatusBadge({ status }) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.OPEN
  return (
    <span
      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium"
      style={{ backgroundColor: `${config.color}18`, color: config.color }}
    >
      <config.icon className="w-3.5 h-3.5" />
      {config.label}
    </span>
  )
}

function CategoryBadge({ category }) {
  const cat = CATEGORIES.find(c => c.value === category) || CATEGORIES[2]
  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
      style={{ backgroundColor: `${cat.color}18`, color: cat.color }}
    >
      {cat.label}
    </span>
  )
}

function AnnotationCanvas({ imageFile, onSave, onCancel }) {
  const canvasRef = useRef(null)
  const imgRef = useRef(null)
  const [drawing, setDrawing] = useState(false)
  const [tool, setTool] = useState('circle')
  const [color, setColor] = useState('#C47068')
  const [startPos, setStartPos] = useState(null)
  const [shapes, setShapes] = useState([])
  const [imageLoaded, setImageLoaded] = useState(false)

  useEffect(() => {
    if (!imageFile) return
    const img = new Image()
    img.onload = () => {
      imgRef.current = img
      setImageLoaded(true)
    }
    img.src = URL.createObjectURL(imageFile)
    return () => URL.revokeObjectURL(img.src)
  }, [imageFile])

  useEffect(() => {
    if (!imageLoaded || !canvasRef.current || !imgRef.current) return
    const canvas = canvasRef.current
    const img = imgRef.current
    const maxW = Math.min(600, window.innerWidth - 40)
    const scale = maxW / img.width
    canvas.width = maxW
    canvas.height = img.height * scale
    redraw()
  }, [imageLoaded, shapes])

  const redraw = useCallback(() => {
    if (!canvasRef.current || !imgRef.current) return
    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    const img = imgRef.current
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height)

    for (const shape of shapes) {
      ctx.strokeStyle = shape.color
      ctx.lineWidth = 3
      if (shape.type === 'circle') {
        const rx = Math.abs(shape.ex - shape.sx) / 2
        const ry = Math.abs(shape.ey - shape.sy) / 2
        const cx = (shape.sx + shape.ex) / 2
        const cy = (shape.sy + shape.ey) / 2
        ctx.beginPath()
        ctx.ellipse(cx, cy, rx, ry, 0, 0, 2 * Math.PI)
        ctx.stroke()
      } else if (shape.type === 'arrow') {
        const dx = shape.ex - shape.sx
        const dy = shape.ey - shape.sy
        const angle = Math.atan2(dy, dx)
        const headLen = 15
        ctx.beginPath()
        ctx.moveTo(shape.sx, shape.sy)
        ctx.lineTo(shape.ex, shape.ey)
        ctx.stroke()
        ctx.beginPath()
        ctx.moveTo(shape.ex, shape.ey)
        ctx.lineTo(shape.ex - headLen * Math.cos(angle - Math.PI / 6), shape.ey - headLen * Math.sin(angle - Math.PI / 6))
        ctx.moveTo(shape.ex, shape.ey)
        ctx.lineTo(shape.ex - headLen * Math.cos(angle + Math.PI / 6), shape.ey - headLen * Math.sin(angle + Math.PI / 6))
        ctx.stroke()
      } else if (shape.type === 'freehand') {
        ctx.beginPath()
        for (let i = 0; i < shape.points.length; i++) {
          if (i === 0) ctx.moveTo(shape.points[i].x, shape.points[i].y)
          else ctx.lineTo(shape.points[i].x, shape.points[i].y)
        }
        ctx.stroke()
      }
    }
  }, [shapes])

  const getPos = (e) => {
    const rect = canvasRef.current.getBoundingClientRect()
    const clientX = e.touches ? e.touches[0].clientX : e.clientX
    const clientY = e.touches ? e.touches[0].clientY : e.clientY
    return { x: clientX - rect.left, y: clientY - rect.top }
  }

  const handleStart = (e) => {
    e.preventDefault()
    const pos = getPos(e)
    setDrawing(true)
    setStartPos(pos)
    if (tool === 'freehand') {
      setShapes(prev => [...prev, { type: 'freehand', color, points: [pos] }])
    }
  }

  const handleMove = (e) => {
    if (!drawing) return
    e.preventDefault()
    const pos = getPos(e)
    if (tool === 'freehand') {
      setShapes(prev => {
        const updated = [...prev]
        const last = { ...updated[updated.length - 1] }
        last.points = [...last.points, pos]
        updated[updated.length - 1] = last
        return updated
      })
    }
  }

  const handleEnd = (e) => {
    if (!drawing) return
    e.preventDefault()
    setDrawing(false)
    if (tool !== 'freehand' && startPos) {
      const pos = e.changedTouches ? { x: e.changedTouches[0].clientX - canvasRef.current.getBoundingClientRect().left, y: e.changedTouches[0].clientY - canvasRef.current.getBoundingClientRect().top } : getPos(e)
      setShapes(prev => [...prev, { type: tool, color, sx: startPos.x, sy: startPos.y, ex: pos.x, ey: pos.y }])
    }
    setStartPos(null)
  }

  const handleSave = () => {
    if (!canvasRef.current) return
    canvasRef.current.toBlob((blob) => {
      if (blob) {
        const file = new File([blob], imageFile.name.replace(/\.[^.]+$/, '_annotated.png'), { type: 'image/png' })
        onSave(file)
      }
    }, 'image/png')
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white rounded-2xl max-w-[650px] w-full max-h-[90vh] overflow-auto">
        <div className="flex items-center justify-between p-4 border-b border-[rgba(59,77,67,0.08)]">
          <h3 className="text-lg font-bold text-[#3D4A44]">Annotate Screenshot</h3>
          <button onClick={onCancel} className="p-1 hover:bg-[#F5F7F4] rounded-lg">
            <XMarkIcon className="w-5 h-5 text-[#7A8580]" />
          </button>
        </div>

        <div className="p-4 space-y-3">
          <div className="flex items-center gap-2 flex-wrap">
            {[
              { value: 'circle', label: 'Circle' },
              { value: 'arrow', label: 'Arrow' },
              { value: 'freehand', label: 'Draw' },
            ].map(t => (
              <button
                key={t.value}
                onClick={() => setTool(t.value)}
                className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                  tool === t.value ? 'bg-[#5B8A72] text-white' : 'bg-[#F5F7F4] text-[#3D4A44] hover:bg-[#E8ECE6]'
                }`}
              >
                {t.label}
              </button>
            ))}
            <div className="flex items-center gap-1 ml-2">
              {['#C47068', '#5B8A72', '#5A8A9A', '#3D4A44'].map(c => (
                <button
                  key={c}
                  onClick={() => setColor(c)}
                  className={`w-6 h-6 rounded-full border-2 ${color === c ? 'border-[#3D4A44]' : 'border-transparent'}`}
                  style={{ backgroundColor: c }}
                />
              ))}
            </div>
            <button
              onClick={() => setShapes(prev => prev.slice(0, -1))}
              disabled={shapes.length === 0}
              className="ml-auto px-3 py-1.5 text-xs font-medium rounded-lg bg-[#F5F7F4] text-[#7A8580] hover:bg-[#E8ECE6] disabled:opacity-40"
            >
              Undo
            </button>
          </div>

          <div className="border border-[rgba(59,77,67,0.12)] rounded-xl overflow-hidden bg-[#F5F7F4] flex items-center justify-center">
            <canvas
              ref={canvasRef}
              className="cursor-crosshair touch-none max-w-full"
              onMouseDown={handleStart}
              onMouseMove={handleMove}
              onMouseUp={handleEnd}
              onMouseLeave={(e) => { if (drawing) { setDrawing(false); setStartPos(null) } }}
              onTouchStart={handleStart}
              onTouchMove={handleMove}
              onTouchEnd={handleEnd}
            />
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 p-4 border-t border-[rgba(59,77,67,0.08)]">
          <button onClick={onCancel} className="px-4 py-2 text-sm font-medium text-[#7A8580] hover:text-[#3D4A44]">
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="px-4 py-2 text-sm font-medium bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62]"
          >
            Save Annotation
          </button>
        </div>
      </div>
    </div>
  )
}

function NewTicketForm({ onSubmit, onCancel, submitting }) {
  const [category, setCategory] = useState('GENERAL_SUPPORT')
  const [subject, setSubject] = useState('')
  const [description, setDescription] = useState('')
  const [attachments, setAttachments] = useState([])
  const [annotatingFile, setAnnotatingFile] = useState(null)
  const [annotatingIndex, setAnnotatingIndex] = useState(null)
  const fileInputRef = useRef(null)

  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files || [])
    const remaining = 2 - attachments.length
    const toAdd = files.slice(0, remaining)
    setAttachments(prev => [...prev, ...toAdd])
    e.target.value = ''
  }

  const removeAttachment = (index) => {
    setAttachments(prev => prev.filter((_, i) => i !== index))
  }

  const handleAnnotate = (index) => {
    setAnnotatingFile(attachments[index])
    setAnnotatingIndex(index)
  }

  const handleAnnotationSave = (annotatedFile) => {
    setAttachments(prev => {
      const updated = [...prev]
      updated[annotatingIndex] = annotatedFile
      return updated
    })
    setAnnotatingFile(null)
    setAnnotatingIndex(null)
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!subject.trim() || !description.trim()) return
    const formData = new FormData()
    formData.append('category', category)
    formData.append('subject', subject.trim())
    formData.append('description', description.trim())
    attachments.forEach(file => formData.append('attachments', file))
    onSubmit(formData)
  }

  return (
    <>
      {annotatingFile && (
        <AnnotationCanvas
          imageFile={annotatingFile}
          onSave={handleAnnotationSave}
          onCancel={() => { setAnnotatingFile(null); setAnnotatingIndex(null) }}
        />
      )}

      <form onSubmit={handleSubmit} className="bg-white rounded-2xl border border-[rgba(59,77,67,0.12)] shadow-sm">
        <div className="p-5 sm:p-6 space-y-5">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-bold text-[#3D4A44]">New Support Ticket</h3>
            <button type="button" onClick={onCancel} className="p-1 hover:bg-[#F5F7F4] rounded-lg">
              <XMarkIcon className="w-5 h-5 text-[#7A8580]" />
            </button>
          </div>

          <div>
            <label className="block text-sm font-medium text-[#3D4A44] mb-2">Category</label>
            <div className="flex flex-wrap gap-2">
              {CATEGORIES.map(cat => (
                <button
                  key={cat.value}
                  type="button"
                  onClick={() => setCategory(cat.value)}
                  className={`px-4 py-2 text-sm font-medium rounded-xl transition-all ${
                    category === cat.value
                      ? 'text-white shadow-sm'
                      : 'bg-[#F5F7F4] text-[#3D4A44] hover:bg-[#E8ECE6]'
                  }`}
                  style={category === cat.value ? { backgroundColor: cat.color } : {}}
                >
                  {cat.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-[#3D4A44] mb-1.5">Subject</label>
            <input
              type="text"
              value={subject}
              onChange={e => setSubject(e.target.value)}
              placeholder="Brief summary of the issue..."
              maxLength={500}
              className="w-full px-4 py-2.5 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm text-[#3D4A44] placeholder-[#B0B5B2] focus:outline-none focus:ring-2 focus:ring-[#5B8A72]/20 focus:border-[#5B8A72]"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-[#3D4A44] mb-1.5">Description</label>
            <textarea
              value={description}
              onChange={e => setDescription(e.target.value)}
              placeholder="Provide as much detail as possible. What happened? What did you expect? Steps to reproduce..."
              rows={5}
              className="w-full px-4 py-2.5 border border-[rgba(59,77,67,0.15)] rounded-xl text-sm text-[#3D4A44] placeholder-[#B0B5B2] focus:outline-none focus:ring-2 focus:ring-[#5B8A72]/20 focus:border-[#5B8A72] resize-none"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-[#3D4A44] mb-1.5">
              Screenshots <span className="text-[#7A8580] font-normal">(optional, max 2)</span>
            </label>
            {attachments.length > 0 && (
              <div className="flex flex-wrap gap-3 mb-3">
                {attachments.map((file, i) => (
                  <div key={i} className="relative group">
                    <img
                      src={URL.createObjectURL(file)}
                      alt={file.name}
                      className="w-24 h-24 object-cover rounded-xl border border-[rgba(59,77,67,0.12)]"
                    />
                    <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity rounded-xl flex items-center justify-center gap-1">
                      <button
                        type="button"
                        onClick={() => handleAnnotate(i)}
                        className="p-1.5 bg-white/90 rounded-lg hover:bg-white"
                        title="Annotate"
                      >
                        <PencilIcon className="w-4 h-4 text-[#3D4A44]" />
                      </button>
                      <button
                        type="button"
                        onClick={() => removeAttachment(i)}
                        className="p-1.5 bg-white/90 rounded-lg hover:bg-white"
                        title="Remove"
                      >
                        <TrashIcon className="w-4 h-4 text-[#C47068]" />
                      </button>
                    </div>
                    <p className="text-[10px] text-[#7A8580] mt-1 max-w-[96px] truncate">{file.name}</p>
                  </div>
                ))}
              </div>
            )}
            {attachments.length < 2 && (
              <>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/webp,image/gif"
                  multiple
                  onChange={handleFileSelect}
                  className="hidden"
                />
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="flex items-center gap-2 px-4 py-2.5 border-2 border-dashed border-[rgba(59,77,67,0.15)] rounded-xl text-sm text-[#7A8580] hover:border-[#5B8A72] hover:text-[#5B8A72] transition-colors"
                >
                  <PhotoIcon className="w-5 h-5" />
                  Attach Screenshot
                </button>
              </>
            )}
            <p className="text-xs text-[#7A8580] mt-1.5">You can draw circles, arrows, or freehand on screenshots after attaching them.</p>
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 px-5 py-4 border-t border-[rgba(59,77,67,0.08)]">
          <button type="button" onClick={onCancel} className="px-4 py-2 text-sm font-medium text-[#7A8580] hover:text-[#3D4A44]">
            Cancel
          </button>
          <button
            type="submit"
            disabled={!subject.trim() || !description.trim() || submitting}
            className="px-5 py-2.5 text-sm font-medium bg-[#5B8A72] text-white rounded-xl hover:bg-[#4A7A62] disabled:opacity-50 transition-colors"
          >
            {submitting ? 'Submitting...' : 'Submit Ticket'}
          </button>
        </div>
      </form>
    </>
  )
}

export default function SupportPage() {
  const [tickets, setTickets] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [selectedTicket, setSelectedTicket] = useState(null)
  const [successMessage, setSuccessMessage] = useState(null)

  const loadTickets = async () => {
    try {
      const res = await axios.get('/api/support/tickets')
      setTickets(res.data.tickets || [])
    } catch (err) {
      console.error('Failed to load tickets:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadTickets()
  }, [])

  const handleSubmit = async (formData) => {
    setSubmitting(true)
    try {
      await axios.post('/api/support/tickets', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setShowForm(false)
      setSuccessMessage('Your ticket has been submitted. We\'ll review it shortly.')
      setTimeout(() => setSuccessMessage(null), 5000)
      loadTickets()
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to submit ticket')
    } finally {
      setSubmitting(false)
    }
  }

  const formatDate = (iso) => {
    if (!iso) return ''
    return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' })
  }

  return (
    <div className="max-w-4xl mx-auto p-4 sm:p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#5B8A72] to-[#4A7A62] flex items-center justify-center">
            <LifebuoyIcon className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-[#3D4A44]">Support</h1>
            <p className="text-sm text-[#7A8580]">Submit and track support requests</p>
          </div>
        </div>
        {!showForm && (
          <button
            onClick={() => setShowForm(true)}
            className="flex items-center gap-2 px-4 py-2.5 bg-[#5B8A72] text-white rounded-xl text-sm font-medium hover:bg-[#4A7A62] transition-colors shadow-sm"
          >
            <PlusIcon className="w-4 h-4" />
            <span className="hidden sm:inline">New Ticket</span>
          </button>
        )}
      </div>

      {successMessage && (
        <div className="bg-[#5B8A72]/10 border border-[#5B8A72]/20 rounded-xl p-4 flex items-center gap-3">
          <CheckCircleIcon className="w-5 h-5 text-[#5B8A72] flex-shrink-0" />
          <p className="text-sm text-[#3D4A44]">{successMessage}</p>
        </div>
      )}

      {showForm && (
        <NewTicketForm
          onSubmit={handleSubmit}
          onCancel={() => setShowForm(false)}
          submitting={submitting}
        />
      )}

      {selectedTicket && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={() => setSelectedTicket(null)}>
          <div className="bg-white rounded-2xl max-w-lg w-full max-h-[80vh] overflow-auto shadow-xl" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between p-5 border-b border-[rgba(59,77,67,0.08)]">
              <h3 className="text-lg font-bold text-[#3D4A44]">Ticket #{selectedTicket.id}</h3>
              <button onClick={() => setSelectedTicket(null)} className="p-1 hover:bg-[#F5F7F4] rounded-lg">
                <XMarkIcon className="w-5 h-5 text-[#7A8580]" />
              </button>
            </div>
            <div className="p-5 space-y-4">
              <div className="flex items-center gap-2 flex-wrap">
                <StatusBadge status={selectedTicket.status} />
                <CategoryBadge category={selectedTicket.category} />
              </div>
              <div>
                <h4 className="font-semibold text-[#3D4A44]">{selectedTicket.subject}</h4>
                <p className="text-xs text-[#7A8580] mt-1">{formatDate(selectedTicket.created_at)}</p>
              </div>
              <div className="bg-[#F5F7F4] rounded-xl p-4">
                <p className="text-sm text-[#3D4A44] whitespace-pre-wrap">{selectedTicket.description}</p>
              </div>
              {selectedTicket.attachments?.length > 0 && (
                <div>
                  <p className="text-sm font-medium text-[#3D4A44] mb-2">Attachments</p>
                  <div className="flex flex-wrap gap-3">
                    {selectedTicket.attachments.map(att => (
                      <a key={att.id} href={att.url} target="_blank" rel="noreferrer" className="block">
                        <img
                          src={att.url}
                          alt={att.file_name}
                          className="w-32 h-32 object-cover rounded-xl border border-[rgba(59,77,67,0.12)] hover:border-[#5B8A72] transition-colors"
                        />
                        <p className="text-[10px] text-[#7A8580] mt-1 max-w-[128px] truncate">{att.file_name}</p>
                      </a>
                    ))}
                  </div>
                </div>
              )}
              {selectedTicket.resolved_at && (
                <p className="text-xs text-[#5B8A72]">Resolved: {formatDate(selectedTicket.resolved_at)}</p>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="space-y-3">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <ArrowPathIcon className="w-6 h-6 text-[#7A8580] animate-spin" />
          </div>
        ) : tickets.length === 0 && !showForm ? (
          <div className="text-center py-16">
            <LifebuoyIcon className="w-12 h-12 text-[#B0B5B2] mx-auto mb-3" />
            <h3 className="text-lg font-semibold text-[#3D4A44] mb-1">No tickets yet</h3>
            <p className="text-sm text-[#7A8580] mb-4">Submit a support ticket if you need help or want to report an issue.</p>
            <button
              onClick={() => setShowForm(true)}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-[#5B8A72] text-white rounded-xl text-sm font-medium hover:bg-[#4A7A62] transition-colors"
            >
              <PlusIcon className="w-4 h-4" />
              Submit a Ticket
            </button>
          </div>
        ) : (
          tickets.map(ticket => (
            <button
              key={ticket.id}
              onClick={() => setSelectedTicket(ticket)}
              className="w-full text-left bg-white rounded-xl border border-[rgba(59,77,67,0.12)] p-4 hover:border-[#5B8A72]/30 hover:shadow-sm transition-all"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-1.5">
                    <StatusBadge status={ticket.status} />
                    <CategoryBadge category={ticket.category} />
                  </div>
                  <h4 className="font-semibold text-[#3D4A44] text-sm truncate">{ticket.subject}</h4>
                  <p className="text-xs text-[#7A8580] mt-0.5 line-clamp-2">{ticket.description}</p>
                </div>
                <div className="flex-shrink-0 text-right">
                  <p className="text-xs text-[#7A8580]">{formatDate(ticket.created_at)}</p>
                  {ticket.attachments?.length > 0 && (
                    <div className="flex items-center gap-1 mt-1 justify-end">
                      <PaperClipIcon className="w-3.5 h-3.5 text-[#7A8580]" />
                      <span className="text-xs text-[#7A8580]">{ticket.attachments.length}</span>
                    </div>
                  )}
                </div>
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  )
}
