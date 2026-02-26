import React, { useState, useEffect } from 'react'
import { XMarkIcon, PaperAirplaneIcon, EnvelopeIcon } from '@heroicons/react/24/outline'

export default function EmailSendModal({
  isOpen,
  onClose,
  onSend,
  title = 'Send Email',
  subtitle = '',
  defaultTo = '',
  defaultSubject = '',
  defaultMessage = '',
  sending = false,
  result = null,
  contacts = [],
  showContactPicker = false,
}) {
  const [to, setTo] = useState(defaultTo)
  const [subject, setSubject] = useState(defaultSubject)
  const [message, setMessage] = useState(defaultMessage)
  const [selectedContactId, setSelectedContactId] = useState('')

  useEffect(() => {
    if (isOpen) {
      setTo(defaultTo)
      setSubject(defaultSubject)
      setMessage(defaultMessage)
      setSelectedContactId('')
    }
  }, [isOpen, defaultTo, defaultSubject, defaultMessage])

  const handleContactSelect = (contactId) => {
    setSelectedContactId(contactId)
    if (contactId) {
      const contact = contacts.find(c => c.id === parseInt(contactId))
      if (contact) {
        setTo(contact.email || '')
      }
    } else {
      setTo('')
    }
  }

  const handleSend = () => {
    onSend({ to, subject, message, contactId: selectedContactId ? parseInt(selectedContactId) : null })
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg">
        <div className="flex items-center justify-between p-5 border-b border-[rgba(59,77,67,0.1)]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#5B8A72]/10 flex items-center justify-center">
              <EnvelopeIcon className="w-5 h-5 text-[#5B8A72]" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-[#3D4A44]">{title}</h2>
              {subtitle && <p className="text-sm text-[#7A8580] mt-0.5">{subtitle}</p>}
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-[#F5F7F4] rounded-lg transition-colors">
            <XMarkIcon className="w-5 h-5 text-[#7A8580]" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          {result && (
            <div className={`p-3 rounded-lg text-sm ${result.success ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-red-50 text-red-700 border border-red-200'}`}>
              {result.message}
            </div>
          )}

          {showContactPicker && contacts.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-[#3D4A44] mb-1.5">Select Contact</label>
              <select
                value={selectedContactId}
                onChange={e => handleContactSelect(e.target.value)}
                className="w-full border border-[rgba(59,77,67,0.15)] rounded-xl px-3 py-2.5 bg-white text-[#3D4A44] focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent text-sm"
              >
                <option value="">— Choose from directory or enter manually —</option>
                {contacts.map(c => (
                  <option key={c.id} value={c.id}>
                    {c.display_name || c.name} {c.email ? `— ${c.email}` : ''}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-[#3D4A44] mb-1.5">To</label>
            <input
              type="email"
              value={to}
              onChange={e => setTo(e.target.value)}
              placeholder="recipient@example.com"
              className="w-full border border-[rgba(59,77,67,0.15)] rounded-xl px-3 py-2.5 text-[#3D4A44] focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent text-sm"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-[#3D4A44] mb-1.5">Subject</label>
            <input
              type="text"
              value={subject}
              onChange={e => setSubject(e.target.value)}
              placeholder="Email subject"
              className="w-full border border-[rgba(59,77,67,0.15)] rounded-xl px-3 py-2.5 text-[#3D4A44] focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent text-sm"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-[#3D4A44] mb-1.5">Message</label>
            <textarea
              value={message}
              onChange={e => setMessage(e.target.value)}
              placeholder="Enter your message..."
              rows={4}
              className="w-full border border-[rgba(59,77,67,0.15)] rounded-xl px-3 py-2.5 text-[#3D4A44] focus:ring-2 focus:ring-[#5B8A72] focus:border-transparent text-sm resize-none"
            />
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 p-5 border-t border-[rgba(59,77,67,0.1)]">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-[#7A8580] hover:text-[#3D4A44] transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSend}
            disabled={!to || sending}
            className="flex items-center gap-2 px-5 py-2.5 bg-[#5B8A72] text-white rounded-xl text-sm font-semibold hover:bg-[#4A7660] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {sending ? (
              <>Sending...</>
            ) : (
              <>
                <PaperAirplaneIcon className="w-4 h-4" />
                Send
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
