import React, { useState, useRef, useEffect, useCallback } from 'react'
import axios from 'axios'
import { apiUrl } from '../lib/apiBase'
import {
  ChatBubbleLeftRightIcon,
  XMarkIcon,
  PaperAirplaneIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline'

function parseMarkdownInline(text) {
  const parts = []
  const regex = /\*\*(.+?)\*\*/g
  let lastIndex = 0
  let match

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index))
    }
    parts.push(<strong key={match.index} className="font-semibold text-[#3D4A44]">{match[1]}</strong>)
    lastIndex = regex.lastIndex
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex))
  }

  return parts.length > 0 ? parts : [text]
}

function MessageContent({ content }) {
  const lines = content.split('\n')

  return (
    <div className="space-y-1">
      {lines.map((line, i) => {
        const trimmed = line.trim()
        if (!trimmed) return <div key={i} className="h-1" />

        const numberedMatch = trimmed.match(/^(\d+)\.\s+(.+)/)
        if (numberedMatch) {
          return (
            <div key={i} className="flex gap-2 pl-1">
              <span className="text-[#5B8A72] font-semibold text-xs mt-0.5 flex-shrink-0">{numberedMatch[1]}.</span>
              <span>{parseMarkdownInline(numberedMatch[2])}</span>
            </div>
          )
        }

        if (trimmed.startsWith('- ') || trimmed.startsWith('• ')) {
          return (
            <div key={i} className="flex gap-2 pl-1">
              <span className="text-[#5B8A72] mt-1 flex-shrink-0">&#8226;</span>
              <span>{parseMarkdownInline(trimmed.slice(2))}</span>
            </div>
          )
        }

        return <p key={i}>{parseMarkdownInline(line)}</p>
      })}
    </div>
  )
}

export default function AssistantChat({ user }) {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [showPulse, setShowPulse] = useState(true)
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)
  const abortRef = useRef(null)

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, scrollToBottom])

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus()
    }
  }, [isOpen])

  const handleOpen = () => {
    setIsOpen(true)
    setShowPulse(false)
    if (messages.length === 0) {
      setMessages([{
        role: 'assistant',
        content: `Hi${user?.username ? ` ${user.username}` : ''}! I'm Cadence. Ask me anything about the app — I'll tell you exactly where to go and what to click.`
      }])
    }
  }

  const handleSend = async () => {
    const text = input.trim()
    if (!text || streaming) return

    const userMsg = { role: 'user', content: text }
    const newMessages = [...messages, userMsg]
    setMessages(newMessages)
    setInput('')
    setStreaming(true)

    const assistantMsg = { role: 'assistant', content: '' }
    setMessages(prev => [...prev, assistantMsg])

    try {
      const controller = new AbortController()
      abortRef.current = controller

      const response = await fetch(apiUrl('/api/assistant/chat'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': axios.defaults.headers.common['Authorization'] || '',
        },
        body: JSON.stringify({
          messages: newMessages.filter(m => m.role === 'user' || m.role === 'assistant').map(m => ({
            role: m.role,
            content: m.content,
          })),
        }),
        signal: controller.signal,
      })

      if (!response.ok) {
        throw new Error('Failed to get response')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let accumulated = ''
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          const trimmed = line.trim()
          if (trimmed.startsWith('data: ')) {
            try {
              const data = JSON.parse(trimmed.slice(6))
              if (data.content) {
                accumulated += data.content
                setMessages(prev => {
                  const updated = [...prev]
                  updated[updated.length - 1] = { role: 'assistant', content: accumulated }
                  return updated
                })
              }
              if (data.error) {
                accumulated = 'Sorry, I ran into an issue. Please try again.'
                setMessages(prev => {
                  const updated = [...prev]
                  updated[updated.length - 1] = { role: 'assistant', content: accumulated }
                  return updated
                })
              }
            } catch {}
          }
        }
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        setMessages(prev => {
          const updated = [...prev]
          updated[updated.length - 1] = {
            role: 'assistant',
            content: 'Sorry, I couldn\'t process that request. Please try again.',
          }
          return updated
        })
      }
    } finally {
      setStreaming(false)
      abortRef.current = null
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleClear = () => {
    if (streaming && abortRef.current) {
      abortRef.current.abort()
    }
    setMessages([{
      role: 'assistant',
      content: `Hi${user?.username ? ` ${user.username}` : ''}! I'm Cadence. Ask me anything about the app — I'll tell you exactly where to go and what to click.`
    }])
    setStreaming(false)
  }

  return (
    <>
      {!isOpen && (
        <button
          onClick={handleOpen}
          className="fixed bottom-6 right-6 z-40 w-14 h-14 bg-gradient-to-br from-[#5B8A72] to-[#4A7A62] rounded-full shadow-lg hover:shadow-xl flex items-center justify-center transition-all hover:scale-105 active:scale-95 group"
          title="Ask Cadence Assistant"
        >
          <ChatBubbleLeftRightIcon className="w-6 h-6 text-white" />
          {showPulse && (
            <span className="absolute -top-1 -right-1 w-4 h-4 bg-[#C4956B] rounded-full animate-pulse" />
          )}
        </button>
      )}

      {isOpen && <div className="fixed inset-0 z-40 bg-black/10 backdrop-blur-[1px] transition-opacity duration-200" onClick={() => setIsOpen(false)} />}

      <div className={`fixed bottom-6 right-6 z-50 w-[380px] max-w-[calc(100vw-2rem)] h-[520px] max-h-[calc(100vh-6rem)] bg-white rounded-2xl shadow-2xl border border-[rgba(59,77,67,0.12)] flex flex-col overflow-hidden transition-all duration-300 ease-out origin-bottom-right ${
        isOpen ? 'opacity-100 scale-100 translate-y-0' : 'opacity-0 scale-95 translate-y-4 pointer-events-none'
      }`}>
      <div className="flex items-center justify-between px-4 py-3 bg-gradient-to-r from-[#5B8A72] to-[#4A7A62] flex-shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-full overflow-hidden flex-shrink-0 relative">
            <img src="/cadence-assistant-logo.png" alt="Cadence" className="w-full h-full object-cover relative z-10" />
            <div className="absolute inset-0 rounded-full z-20 pointer-events-none" style={{ animation: 'metalPulse 5s cubic-bezier(0.45, 0, 0.55, 1) infinite' }} />
            <style>{`
              @keyframes metalPulse {
                0%, 100% { opacity: 0; background: transparent; box-shadow: none; }
                15% { opacity: 0; }
                45%, 55% { opacity: 1; background: linear-gradient(135deg, rgba(255,255,255,0.02) 0%, rgba(255,255,255,0.13) 50%, rgba(255,255,255,0.02) 100%); box-shadow: inset 0 0 8px rgba(255,255,255,0.12), 0 0 10px rgba(180,220,200,0.25), 0 0 20px rgba(91,138,114,0.15); }
                85% { opacity: 0; }
              }
            `}</style>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white leading-tight">Cadence</h3>
            <p className="text-[10px] text-white/70">Ask me anything about the app</p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={handleClear}
            className="p-1.5 hover:bg-white/15 rounded-lg transition-colors"
            title="Clear chat"
          >
            <ArrowPathIcon className="w-4 h-4 text-white/80" />
          </button>
          <button
            onClick={() => setIsOpen(false)}
            className="p-1.5 hover:bg-white/15 rounded-lg transition-colors"
            title="Close"
          >
            <XMarkIcon className="w-4 h-4 text-white/80" />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3 scroll-smooth">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[85%] px-3.5 py-2.5 text-[13px] leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-[#5B8A72] text-white rounded-2xl rounded-br-md'
                  : 'bg-[#F5F7F4] text-[#3D4A44] rounded-2xl rounded-bl-md'
              }`}
            >
              {msg.role === 'assistant' ? (
                msg.content ? <MessageContent content={msg.content} /> : (
                  <div className="flex items-center gap-1.5 py-1">
                    <div className="w-1.5 h-1.5 bg-[#5B8A72] rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <div className="w-1.5 h-1.5 bg-[#5B8A72] rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <div className="w-1.5 h-1.5 bg-[#5B8A72] rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                )
              ) : (
                <p>{msg.content}</p>
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="px-3 py-3 border-t border-[rgba(59,77,67,0.08)] bg-white flex-shrink-0">
        <div className="flex items-end gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about any feature..."
            rows={1}
            disabled={streaming}
            className="flex-1 px-3.5 py-2.5 bg-[#F5F7F4] border border-[rgba(59,77,67,0.1)] rounded-xl text-sm text-[#3D4A44] placeholder-[#B0B5B2] resize-none focus:outline-none focus:ring-2 focus:ring-[#5B8A72]/20 focus:border-[#5B8A72] disabled:opacity-60 max-h-[80px] overflow-y-auto"
            style={{ minHeight: '40px' }}
            onInput={e => {
              e.target.style.height = '40px'
              e.target.style.height = Math.min(e.target.scrollHeight, 80) + 'px'
            }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || streaming}
            className="p-2.5 bg-[#5B8A72] text-white rounded-xl hover:bg-[#4A7A62] disabled:opacity-40 disabled:hover:bg-[#5B8A72] transition-colors flex-shrink-0"
          >
            <PaperAirplaneIcon className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
    </>
  )
}
