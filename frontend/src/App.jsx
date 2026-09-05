import React, { useState, useRef, useEffect } from 'react'

const API_BASE = '/api'

const EXAMPLE_PROMPTS = [
  "I just bombed my job interview and I'm scared I'll never get hired 😔",
  "My name is Arjun and I'm a backend engineer who loves hiking",
  "I traveled to Goa last weekend — it was incredible",
  "I feel really proud of myself for finishing my side project today!",
  "My sister Meera got engaged! I'm over the moon for her",
]

function TypingIndicator() {
  return (
    <div className="message-row">
      <div className="message-avatar assistant">🧠</div>
      <div className="typing-indicator">
        <div className="typing-dot" />
        <div className="typing-dot" />
        <div className="typing-dot" />
      </div>
    </div>
  )
}

function MemoryBadges({ trace }) {
  if (!trace || trace.length === 0) return null
  const extractNode = trace.find(t => t.node === 'extract_and_classify')
  if (!extractNode || !extractNode.data?.memories_found) return null

  const { breakdown = {} } = extractNode.data
  const badges = []
  if (breakdown.identity)  badges.push({ type: 'identity',  label: `${breakdown.identity} identity`,  icon: '👤' })
  if (breakdown.episodic)  badges.push({ type: 'episodic',  label: `${breakdown.episodic} episodic`,  icon: '📅' })
  if (breakdown.emotional) badges.push({ type: 'emotional', label: `${breakdown.emotional} emotional`, icon: '💭' })

  if (badges.length === 0) return null
  return (
    <div className="memory-badges">
      {badges.map(b => (
        <span key={b.type} className={`memory-badge ${b.type}`}>
          {b.icon} {b.label}
        </span>
      ))}
    </div>
  )
}

function MessageBubble({ msg }) {
  const isUser = msg.role === 'user'
  return (
    <div className={`message-row ${isUser ? 'user' : ''}`}>
      <div className={`message-avatar ${isUser ? 'user' : 'assistant'}`}>
        {isUser ? '👤' : '🧠'}
      </div>
      <div>
        <div className={`message-bubble ${isUser ? 'user' : 'assistant'}`}>
          {msg.content}
        </div>
        {!isUser && <MemoryBadges trace={msg.trace} />}
        <div className="message-meta">
          {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          {!isUser && msg.trace && (
            <span>· {msg.trace.length} pipeline steps</span>
          )}
        </div>
      </div>
    </div>
  )
}

export { MessageBubble, TypingIndicator, EXAMPLE_PROMPTS }
export default function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [showDebug, setShowDebug] = useState(true)
  const [conversationId, setConversationId] = useState(() => crypto.randomUUID())
  const [traceHistory, setTraceHistory] = useState([]) // [{turnIndex, trace}]
  const [expandedTurns, setExpandedTurns] = useState({})
  const messagesEndRef = useRef(null)
  const textareaRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  const autoResize = (el) => {
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 140) + 'px'
  }

  const sendMessage = async (text) => {
    const content = (text || input).trim()
    if (!content || isLoading) return

    setInput('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }

    const userMsg = { role: 'user', content, timestamp: new Date().toISOString() }
    setMessages(prev => [...prev, userMsg])
    setIsLoading(true)

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ conversation_id: conversationId, message: content }),
      })

      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()

      const assistantMsg = {
        role: 'assistant',
        content: data.response,
        timestamp: new Date().toISOString(),
        trace: data.trace || [],
      }
      setMessages(prev => [...prev, assistantMsg])

      const turnIndex = traceHistory.length
      setTraceHistory(prev => [...prev, { turnIndex, userMsg: content, trace: data.trace || [] }])
      setExpandedTurns(prev => ({ ...prev, [turnIndex]: true }))
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `⚠️ Error: ${err.message}. Is the backend running?`,
        timestamp: new Date().toISOString(),
        trace: [],
      }])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const toggleTurn = (i) => setExpandedTurns(prev => ({ ...prev, [i]: !prev[i] }))

  const newConversation = () => {
    if (isLoading) return
    setConversationId(crypto.randomUUID())
    setMessages([])
    setTraceHistory([])
    setExpandedTurns({})
  }

  return (
    <div className="app-layout">
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <header className="app-header">
        <div className="app-header-brand">
          <div className="brand-icon">🧠</div>
          <div>
            <div className="brand-title">IACI</div>
            <div className="brand-subtitle">Identity-Aware Conversational Intelligence</div>
          </div>
        </div>
        <div className="header-controls">
          <div className="user-id-badge" title={conversationId}>
            <div className="status-dot" />
            {conversationId.slice(0, 8)}
          </div>
          <button
            id="new-conversation-btn"
            className="debug-toggle-btn"
            onClick={newConversation}
            title="Start a new conversation (memory is kept)"
          >
            ➕ New chat
          </button>
          <button
            id="debug-toggle"
            className={`debug-toggle-btn ${showDebug ? 'active' : ''}`}
            onClick={() => setShowDebug(v => !v)}
          >
            🔬 {showDebug ? 'Hide' : 'Show'} Trace
          </button>
        </div>
      </header>

      {/* ── Body ────────────────────────────────────────────────────────── */}
      <div className="app-body">
        {/* ── Chat ───────────────────────────────────────────────────── */}
        <div className="chat-panel">
          <div className="chat-messages">
            {messages.length === 0 ? (
              <div className="welcome-state">
                <div className="welcome-icon">🧠</div>
                <div className="welcome-title">Memory-powered conversation</div>
                <p className="welcome-desc">
                  Tell me about yourself — your experiences, feelings, and who you are.
                  I'll remember it all across our conversations and use it to know you better.
                </p>
                <div className="welcome-chips">
                  {EXAMPLE_PROMPTS.map((p, i) => (
                    <button key={i} className="welcome-chip" onClick={() => sendMessage(p)}>
                      {p.length > 50 ? p.slice(0, 50) + '…' : p}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <>
                {messages.map((msg, i) => <MessageBubble key={i} msg={msg} />)}
                {isLoading && <TypingIndicator />}
              </>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* ── Input ───────────────────────────────────────────────── */}
          <div className="chat-input-area">
            <div className="chat-input-wrapper">
              <textarea
                ref={textareaRef}
                id="chat-input"
                className="chat-textarea"
                placeholder="Tell me something about yourself…"
                value={input}
                onChange={e => { setInput(e.target.value); autoResize(e.target) }}
                onKeyDown={handleKeyDown}
                rows={1}
                disabled={isLoading}
              />
              <button
                id="send-btn"
                className="send-btn"
                onClick={() => sendMessage()}
                disabled={!input.trim() || isLoading}
                title="Send (Enter)"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="22" y1="2" x2="11" y2="13"/>
                  <polygon points="22 2 15 22 11 13 2 9 22 2"/>
                </svg>
              </button>
            </div>
            <div className="input-hint">Enter to send · Shift+Enter for newline</div>
          </div>
        </div>

        {/* ── Debug Panel ────────────────────────────────────────────── */}
        {showDebug && (
          <aside className="debug-panel">
            <div className="debug-panel-header">
              <div className="debug-panel-title">
                <span className="debug-panel-title-icon">🔬</span>
                Pipeline Trace
              </div>
              <span className="debug-turn-count">{traceHistory.length} turns</span>
            </div>

            <div className="debug-panel-scroll">
              {traceHistory.length === 0 ? (
                <div className="debug-empty">
                  <span style={{ fontSize: 24 }}>🔍</span>
                  <div>Send a message to see the pipeline trace here</div>
                  <div style={{ fontSize: 11, marginTop: 4 }}>Each turn shows retrieval decisions, memory classification, and write operations</div>
                </div>
              ) : (
                [...traceHistory].reverse().map((turn, ri) => {
                  const i = traceHistory.length - 1 - ri
                  const open = expandedTurns[i]
                  return (
                    <TraceTurn
                      key={i}
                      index={i}
                      turn={turn}
                      open={open}
                      onToggle={() => toggleTurn(i)}
                    />
                  )
                })
              )}
            </div>
          </aside>
        )}
      </div>
    </div>
  )
}

/* ── TraceTurn component ───────────────────────────────────────────────────── */
function TraceTurn({ index, turn, open, onToggle }) {
  const assessNode  = turn.trace?.find(t => t.node === 'assess_context')
  const extractNode = turn.trace?.find(t => t.node === 'extract_and_classify')
  const writeNode   = turn.trace?.find(t => t.node === 'write_memory')
  const retrieveNode = turn.trace?.find(t => t.node === 'retrieve_memory')

  const memoriesCount = extractNode?.data?.memories_found ?? 0
  const didRetrieve = assessNode?.data?.needs_retrieval

  return (
    <div className="trace-turn">
      <div className="trace-turn-header" onClick={onToggle}>
        <span className="trace-turn-label">Turn #{index + 1}</span>
        <div className="trace-turn-summary">
          {didRetrieve && <span className="node-pill retrieve-yes">↑ retrieved</span>}
          {memoriesCount > 0 && <span className="node-pill memories-n">+{memoriesCount} stored</span>}
          <span className={`trace-chevron ${open ? 'open' : ''}`}>▶</span>
        </div>
      </div>

      {open && (
        <div className="trace-turn-body">
          {/* User message preview */}
          <div style={{ fontSize: 11, color: 'var(--text-muted)', padding: '2px 4px', marginBottom: 2, fontStyle: 'italic' }}>
            "{turn.userMsg?.slice(0, 80)}{turn.userMsg?.length > 80 ? '…' : ''}"
          </div>

          {/* assess_context */}
          {assessNode && (
            <NodeCard
              name="assess_context"
              pills={[
                assessNode.data.needs_retrieval
                  ? { cls: 'retrieve-yes', text: '✓ retrieve' }
                  : { cls: 'retrieve-no', text: '✗ skip retrieve' }
              ]}
              reasoning={assessNode.data.reasoning}
            >
              {assessNode.data.intents?.length > 0 && (
                <div className="node-retrieval-list">
                  {assessNode.data.intents.map((intent, j) => (
                    <div key={j} className="node-retrieval-item">{intent}</div>
                  ))}
                </div>
              )}
            </NodeCard>
          )}

          {/* retrieve_memory */}
          {retrieveNode && (
            <NodeCard
              name="retrieve_memory"
              pills={retrieveNode.data.results_summary?.map(r => ({
                cls: 'retrieve-yes',
                text: `${r.rows_found} rows`,
              })) ?? []}
            >
              <div className="node-retrieval-list">
                {retrieveNode.data.results_summary?.map((r, j) => (
                  <div key={j} className="node-retrieval-item">
                    {r.intent} → {r.rows_found} result{r.rows_found !== 1 ? 's' : ''}
                  </div>
                ))}
              </div>
            </NodeCard>
          )}

          {/* extract_and_classify */}
          {extractNode && (
            <NodeCard
              name="extract_and_classify"
              pills={[{ cls: 'memories-n', text: `${memoriesCount} memories` }]}
              reasoning={extractNode.data.reasoning}
            >
              {extractNode.data.memories?.length > 0 && (
                <div className="node-memory-list">
                  {extractNode.data.memories.map((m, j) => (
                    <div key={j} className={`node-memory-item ${m.memory_type}`}>
                      [{m.memory_type}] {m.content?.slice(0, 70)}{m.content?.length > 70 ? '…' : ''}
                    </div>
                  ))}
                </div>
              )}
            </NodeCard>
          )}

          {/* write_memory */}
          {writeNode && (
            <NodeCard
              name="write_memory"
              pills={[{ cls: 'wrote-n', text: `${writeNode.data.writes} writes` }]}
            >
              {writeNode.data.write_results?.map((w, j) => (
                <div key={j} className={`node-memory-item ${w.memory_type}`}>
                  ✓ {w.memory_type}: {w.content?.slice(0, 60)}{w.content?.length > 60 ? '…' : ''}
                </div>
              ))}
            </NodeCard>
          )}
        </div>
      )}
    </div>
  )
}

function NodeCard({ name, pills = [], reasoning, children }) {
  return (
    <div className="node-card">
      <div className="node-card-header">
        <span className="node-name">{name}</span>
        {pills.map((p, i) => (
          <span key={i} className={`node-pill ${p.cls}`}>{p.text}</span>
        ))}
      </div>
      {children}
      {reasoning && <div className="node-reasoning">{reasoning}</div>}
    </div>
  )
}
