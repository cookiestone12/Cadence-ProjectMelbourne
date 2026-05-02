import React, { useState, useRef, useEffect, useCallback } from 'react'
import axios from 'axios'
import { apiUrl } from '../lib/apiBase'
import {
  ChatBubbleLeftRightIcon,
  XMarkIcon,
  PaperAirplaneIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  PlayIcon,
  Cog6ToothIcon,
} from '@heroicons/react/24/outline'
import {
  getAssistantContext,
  pageFromPath,
} from '../lib/assistantContext'

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

const TOOL_LABELS = {
  search_songs: 'Searching songs',
  get_song_health: 'Checking song health',
  search_creators: 'Searching creators',
  get_creator_summary: 'Looking up creator',
  search_contracts: 'Searching contracts',
  list_expiring_contracts: 'Finding expiring contracts',
  get_royalty_summary_for_song: 'Pulling royalty summary',
  list_action_items_for_user: 'Listing your action items',
  create_song: 'Drafting a song',
  create_placement: 'Drafting a placement',
  update_placement_status: 'Drafting a status change',
  create_action_item: 'Drafting an action item',
  create_contract_stub: 'Drafting a contract',
}

function ToolChip({ name, completed }) {
  return (
    <div className="inline-flex items-center gap-1.5 px-2 py-1 bg-[#EEF3EE] border border-[rgba(91,138,114,0.18)] rounded-full text-[11px] text-[#3D4A44]">
      {completed ? (
        <CheckCircleIcon className="w-3 h-3 text-[#5B8A72]" />
      ) : (
        <Cog6ToothIcon className="w-3 h-3 text-[#5B8A72] animate-spin" />
      )}
      <span className="font-medium">{TOOL_LABELS[name] || name}</span>
    </div>
  )
}

function _deepLinkFor(name, row) {
  if (!row?.id) return null
  if (name === 'search_songs') return `/catalog?songId=${row.id}`
  if (name === 'search_creators') return `/creators/${row.id}`
  if (name === 'search_contracts' || name === 'list_expiring_contracts')
    return `/contracts/${row.id}`
  if (name === 'list_action_items_for_user') return `/actions`
  return null
}

function _rowLabel(name, row) {
  if (row?.title) return row.title
  if (row?.name) return row.name
  if (row?.song_title) return row.song_title
  if (row?.id) return `#${row.id}`
  return 'Item'
}

function _rowSubtitle(name, row) {
  if (name === 'search_songs')
    return [row?.primary_artist, row?.isrc, row?.is_released ? 'Released' : 'Unreleased']
      .filter(Boolean).join(' · ')
  if (name === 'search_creators') return row?.email || row?.creator_type || ''
  if (name === 'search_contracts' || name === 'list_expiring_contracts')
    return [row?.contract_type, row?.status, row?.end_date && `ends ${row.end_date}`]
      .filter(Boolean).join(' · ')
  if (name === 'list_action_items_for_user')
    return [row?.priority_label, row?.deadline].filter(Boolean).join(' · ')
  return ''
}

function _summaryLine(name, data) {
  if (!data || typeof data !== 'object') return null
  if (name === 'get_song_health') {
    const gaps = (data.gaps || []).length
    return `${data.title || 'Song'} · health ${data.health_score ?? '–'} · ${gaps} gap${gaps === 1 ? '' : 's'}`
  }
  if (name === 'get_creator_summary') {
    return `${data.name || 'Creator'} · ${data.song_count ?? 0} songs · ${data.contract_count ?? 0} contracts · ${data.open_action_items ?? 0} open tasks`
  }
  if (name === 'get_royalty_summary_for_song') {
    const period = data.period || 'all time'
    const cur = data.currency || 'USD'
    return `${data.song_title || 'Song'} (${period}) · ${cur} ${(data.net_royalties ?? 0).toFixed(2)} · ${data.total_streams ?? 0} streams`
  }
  return null
}

function ToolResultCard({ name, data }) {
  if (!data || data.error) {
    if (data?.error) {
      return (
        <div className="mt-2 px-3 py-2 bg-amber-50 border border-amber-200 rounded-lg text-[12px] text-amber-800">
          {data.error}
        </div>
      )
    }
    return null
  }

  // Single-entity get_* result
  const summary = _summaryLine(name, data)
  if (summary) {
    return (
      <div className="mt-2 px-3 py-2 bg-[#F5F7F4] border border-[rgba(91,138,114,0.18)] rounded-lg">
        <div className="text-[10px] font-semibold uppercase tracking-wide text-[#7A8580] mb-0.5">
          {TOOL_LABELS[name] || name}
        </div>
        <div className="text-[12.5px] text-[#3D4A44] leading-snug">{summary}</div>
      </div>
    )
  }

  // List-style result with preview rows
  const rows = data.preview || data.results || []
  const count = data.count ?? rows.length
  if (!rows.length && typeof count !== 'number') return null
  return (
    <div className="mt-2 border border-[rgba(91,138,114,0.18)] rounded-lg bg-white overflow-hidden">
      <div className="px-3 py-1.5 bg-[#F5F7F4] flex items-center justify-between">
        <span className="text-[10px] font-semibold uppercase tracking-wide text-[#7A8580]">
          {TOOL_LABELS[name] || name}
        </span>
        <span className="text-[10px] text-[#7A8580]">
          {count} result{count === 1 ? '' : 's'}
        </span>
      </div>
      {rows.length === 0 ? (
        <div className="px-3 py-2 text-[12px] text-[#7A8580] italic">No matches.</div>
      ) : (
        <ul className="divide-y divide-[rgba(91,138,114,0.10)]">
          {rows.slice(0, 3).map((row, i) => {
            const link = _deepLinkFor(name, row)
            const label = _rowLabel(name, row)
            const sub = _rowSubtitle(name, row)
            return (
              <li key={i} className="px-3 py-1.5 flex items-center justify-between gap-2">
                <div className="min-w-0">
                  <div className="text-[12.5px] text-[#3D4A44] font-medium truncate">{label}</div>
                  {sub && <div className="text-[11px] text-[#7A8580] truncate">{sub}</div>}
                </div>
                {link && (
                  <a
                    href={link}
                    className="text-[11px] font-semibold text-[#5B8A72] hover:underline flex-shrink-0"
                  >
                    Open
                  </a>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}

function ProposedActionCard({ action, onConfirm, onCancel, status, error }) {
  const expired = status === 'expired'
  const done = status === 'confirmed'
  const cancelled = status === 'cancelled'
  return (
    <div className="mt-2 border border-[rgba(91,138,114,0.25)] rounded-xl bg-white shadow-sm overflow-hidden">
      <div className="px-3 py-2 bg-[#F5F7F4] border-b border-[rgba(91,138,114,0.15)] flex items-center gap-2">
        <PlayIcon className="w-3.5 h-3.5 text-[#5B8A72]" />
        <span className="text-[11px] font-semibold text-[#3D4A44] uppercase tracking-wide">
          Confirm to run
        </span>
      </div>
      <div className="px-3 py-2.5">
        <p className="text-[13px] text-[#3D4A44] leading-relaxed">{action.summary}</p>
        {error && (
          <p className="mt-1.5 text-[12px] text-red-600">{error}</p>
        )}
        {!done && !cancelled && !expired && (
          <div className="mt-2.5 flex items-center gap-2">
            <button
              onClick={() => onConfirm(action)}
              disabled={status === 'running'}
              className="px-3 py-1.5 bg-[#5B8A72] text-white text-[12px] font-semibold rounded-lg hover:bg-[#4A7A62] disabled:opacity-50 transition-colors"
            >
              {status === 'running' ? 'Running…' : 'Confirm'}
            </button>
            <button
              onClick={() => onCancel(action)}
              disabled={status === 'running'}
              className="px-3 py-1.5 bg-white border border-[rgba(59,77,67,0.15)] text-[#3D4A44] text-[12px] font-semibold rounded-lg hover:bg-[#F5F7F4] disabled:opacity-50 transition-colors"
            >
              Cancel
            </button>
          </div>
        )}
        {done && (
          <p className="mt-1.5 text-[12px] text-[#5B8A72] font-semibold flex items-center gap-1">
            <CheckCircleIcon className="w-3.5 h-3.5" /> Done
          </p>
        )}
        {cancelled && (
          <p className="mt-1.5 text-[12px] text-[#7A8580] italic">Cancelled.</p>
        )}
        {expired && (
          <p className="mt-1.5 text-[12px] text-[#7A8580] italic">
            This proposal has expired — ask again to retry.
          </p>
        )}
      </div>
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
        content: `Hi${user?.username ? ` ${user.username}` : ''}! I'm Cadence. Ask me anything about the app — or about your catalog, placements, or royalties — I'll look it up and walk you through next steps.`,
        toolRuns: [],
        proposedActions: [],
      }])
    }
  }

  const buildContext = () => {
    const path = (typeof window !== 'undefined' && window.location?.pathname) || '/'
    return {
      page: pageFromPath(path),
      path,
      ...getAssistantContext(),
    }
  }

  const updateAssistantBubble = (mutator) => {
    setMessages(prev => {
      const updated = [...prev]
      const idx = updated.length - 1
      updated[idx] = mutator(updated[idx])
      return updated
    })
  }

  const handleSend = async () => {
    const text = input.trim()
    if (!text || streaming) return

    const userMsg = { role: 'user', content: text }
    const newMessages = [...messages, userMsg]
    setMessages(newMessages)
    setInput('')
    setStreaming(true)

    const assistantMsg = { role: 'assistant', content: '', toolRuns: [], toolResults: [], proposedActions: [] }
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
          context: buildContext(),
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
          if (!trimmed.startsWith('data: ')) continue
          let data
          try {
            data = JSON.parse(trimmed.slice(6))
          } catch {
            continue
          }

          if (data.content) {
            accumulated += data.content
            const text = accumulated
            updateAssistantBubble(m => ({ ...m, content: text }))
          }
          if (data.tool_running) {
            const name = data.tool_running.name
            updateAssistantBubble(m => ({
              ...m,
              toolRuns: [...(m.toolRuns || []), { name, completed: false }],
            }))
          }
          if (data.tool_result) {
            const { name, data: payload } = data.tool_result
            updateAssistantBubble(m => {
              const tr = [...(m.toolRuns || [])]
              for (let i = tr.length - 1; i >= 0; i--) {
                if (tr[i].name === name && !tr[i].completed) {
                  tr[i] = { ...tr[i], completed: true }
                  break
                }
              }
              return {
                ...m,
                toolRuns: tr,
                toolResults: [
                  ...(m.toolResults || []),
                  { name, data: payload },
                ],
              }
            })
          }
          if (data.proposed_action) {
            const pa = data.proposed_action
            updateAssistantBubble(m => {
              const tr = [...(m.toolRuns || [])]
              for (let i = tr.length - 1; i >= 0; i--) {
                if (!tr[i].completed) {
                  tr[i] = { ...tr[i], completed: true }
                  break
                }
              }
              return {
                ...m,
                toolRuns: tr,
                proposedActions: [
                  ...(m.proposedActions || []),
                  { ...pa, status: 'pending' },
                ],
              }
            })
          }
          if (data.error) {
            accumulated = 'Sorry, I ran into an issue. Please try again.'
            const text = accumulated
            updateAssistantBubble(m => ({ ...m, content: text }))
          }
        }
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        updateAssistantBubble(m => ({
          ...m,
          content: m.content || 'Sorry, I couldn\'t process that request. Please try again.',
        }))
      }
    } finally {
      setStreaming(false)
      abortRef.current = null
    }
  }

  const updateProposedAction = (msgIdx, actionId, mutator) => {
    setMessages(prev => {
      const updated = [...prev]
      const m = updated[msgIdx]
      if (!m || !m.proposedActions) return prev
      updated[msgIdx] = {
        ...m,
        proposedActions: m.proposedActions.map(a =>
          a.id === actionId ? mutator(a) : a
        ),
      }
      return updated
    })
  }

  const handleConfirm = async (msgIdx, action) => {
    updateProposedAction(msgIdx, action.id, a => ({ ...a, status: 'running', error: null }))
    try {
      const resp = await axios.post(apiUrl(`/api/assistant/actions/${action.id}/confirm`))
      const { entity_type, entity_id, entity_name } = resp.data || {}
      updateProposedAction(msgIdx, action.id, a => ({ ...a, status: 'confirmed' }))
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Done — created ${entity_type?.toLowerCase() || 'it'} **${entity_name || `#${entity_id}`}**.`,
        toolRuns: [],
        proposedActions: [],
      }])
    } catch (err) {
      const detail = err?.response?.data?.detail
      const expired = err?.response?.status === 404
      updateProposedAction(msgIdx, action.id, a => ({
        ...a,
        status: expired ? 'expired' : 'pending',
        error: detail || 'Couldn\'t run that — try again.',
      }))
    }
  }

  const handleCancel = async (msgIdx, action) => {
    updateProposedAction(msgIdx, action.id, a => ({ ...a, status: 'cancelled' }))
    try {
      await axios.delete(apiUrl(`/api/assistant/actions/${action.id}`))
    } catch {
      /* best-effort */
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
      content: `Hi${user?.username ? ` ${user.username}` : ''}! I'm Cadence. Ask me anything about the app — or about your catalog, placements, or royalties.`,
      toolRuns: [],
      proposedActions: [],
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

      <div className={`fixed bottom-6 right-6 z-50 w-[380px] max-w-[calc(100vw-2rem)] h-[560px] max-h-[calc(100vh-6rem)] bg-white rounded-2xl shadow-2xl border border-[rgba(59,77,67,0.12)] flex flex-col overflow-hidden transition-all duration-300 ease-out origin-bottom-right ${
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
        {messages.map((msg, i) => {
          const hasTools = (msg.toolRuns && msg.toolRuns.length > 0)
          const hasActions = (msg.proposedActions && msg.proposedActions.length > 0)
          return (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[85%] ${msg.role === 'user' ? '' : 'w-[85%]'}`}>
                <div
                  className={`px-3.5 py-2.5 text-[13px] leading-relaxed ${
                    msg.role === 'user'
                      ? 'bg-[#5B8A72] text-white rounded-2xl rounded-br-md'
                      : 'bg-[#F5F7F4] text-[#3D4A44] rounded-2xl rounded-bl-md'
                  }`}
                >
                  {msg.role === 'assistant' ? (
                    <>
                      {hasTools && (
                        <div className="flex flex-wrap gap-1.5 mb-2">
                          {msg.toolRuns.map((t, k) => (
                            <ToolChip key={k} name={t.name} completed={t.completed} />
                          ))}
                        </div>
                      )}
                      {msg.content
                        ? <MessageContent content={msg.content} />
                        : (!hasTools && !hasActions && (
                          <div className="flex items-center gap-1.5 py-1">
                            <div className="w-1.5 h-1.5 bg-[#5B8A72] rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                            <div className="w-1.5 h-1.5 bg-[#5B8A72] rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                            <div className="w-1.5 h-1.5 bg-[#5B8A72] rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                          </div>
                        ))
                      }
                    </>
                  ) : (
                    <p>{msg.content}</p>
                  )}
                </div>
                {(msg.toolResults || []).map((r, k) => (
                  <ToolResultCard key={`tr-${k}`} name={r.name} data={r.data} />
                ))}
                {hasActions && msg.proposedActions.map(a => (
                  <ProposedActionCard
                    key={a.id}
                    action={a}
                    status={a.status}
                    error={a.error}
                    onConfirm={() => handleConfirm(i, a)}
                    onCancel={() => handleCancel(i, a)}
                  />
                ))}
              </div>
            </div>
          )
        })}
        <div ref={messagesEndRef} />
      </div>

      <div className="px-3 py-3 border-t border-[rgba(59,77,67,0.08)] bg-white flex-shrink-0">
        <div className="flex items-end gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about any feature or your data..."
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
