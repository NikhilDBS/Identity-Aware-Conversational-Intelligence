import React, { useState, useRef, useEffect } from 'react'
import { alpha } from '@mui/material/styles'
import {
  AppBar, Toolbar, Typography, Button, Chip, Paper, Stack, Box,
  Avatar, IconButton, Tooltip,
} from '@mui/material'
import {
  SmartToy as BotIcon,
  Person as UserIcon,
  Add as NewChatIcon,
  Science as TraceIcon,
  Search as EmptyTraceIcon,
  Event as EpisodicIcon,
  Mood as EmotionalIcon,
  Psychology as BrandIcon,
} from '@mui/icons-material'
import { ArrowUp as SendArrowIcon } from 'lucide-react'
import { GitHubSky } from './components/ui/git-hub-sky'
import { MetalFx } from './components/ui/metal-fx'
import JobListingComponent from './components/ui/job-listing'
import theme from './theme.js'

// three.js is heavy (~600KB): load the orb only when first needed
const GradientOrb = React.lazy(() => import('./components/ui/gradient-orb'))

const API_BASE = '/api'
const REPO_URL = 'https://github.com/NikhilDBS/Identity-Aware-Conversational-Intelligence'

const EXAMPLE_PROMPTS = [
  "I just bombed my job interview and I'm scared I'll never get hired",
  'My name is Arjun and I am a backend engineer who loves hiking',
  'I traveled to Goa last weekend, it was incredible',
  'I feel really proud of myself for finishing my side project today',
  'My sister Meera got engaged, I am over the moon for her',
]

const MEMORY_META = {
  identity:  { color: theme.palette.memory.identity,  icon: <UserIcon fontSize="inherit" />,     label: 'identity' },
  episodic:  { color: theme.palette.memory.episodic,  icon: <EpisodicIcon fontSize="inherit" />,  label: 'episodic' },
  emotional: { color: theme.palette.memory.emotional, icon: <EmotionalIcon fontSize="inherit" />, label: 'emotional' },
}

// Buffer visual: shown after the user sends a message while the reply streams in
function ThinkingOrb() {
  return (
    <Stack direction="row" spacing={1.5} alignItems="flex-start" className="message-enter">
      <Avatar sx={{ width: 32, height: 32, flexShrink: 0, mt: 0.25, bgcolor: 'primary.main', color: '#1A1206' }}>
        <BotIcon fontSize="small" />
      </Avatar>
      <Box sx={{ minWidth: 0 }}>
        <Box sx={{ width: 128, height: 128, borderRadius: 3, overflow: 'hidden', border: 1, borderColor: 'divider' }}>
          <React.Suspense fallback={<span className="typing-dots"><span className="typing-dot" /><span className="typing-dot" /><span className="typing-dot" /></span>}>
            <GradientOrb config={{ background: '#05070C', hue: 18, rotationSpeed: 0.5 }} />
          </React.Suspense>
        </Box>
        <Typography variant="caption" color="text.disabled" sx={{ mt: 0.5, fontSize: 10 }}>
          Thinking through memory...
        </Typography>
      </Box>
    </Stack>
  )
}

function MemoryBadges({ trace }) {
  if (!trace || trace.length === 0) return null
  const extractNode = trace.find(t => t.node === 'extract_and_classify')
  if (!extractNode || !extractNode.data?.memories_found) return null

  const { breakdown = {} } = extractNode.data
  return (
    <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap sx={{ mt: 1 }}>
      {Object.entries(MEMORY_META).map(([type, meta]) =>
        breakdown[type] ? (
          <Chip
            key={type}
            size="small"
            icon={meta.icon}
            label={`${breakdown[type]} ${meta.label}`}
            sx={{
              height: 22,
              fontSize: 11,
              color: meta.color,
              bgcolor: alpha(meta.color, 0.12),
              border: `1px solid ${alpha(meta.color, 0.3)}`,
            }}
          />
        ) : null
      )}
    </Stack>
  )
}

function MessageBubble({ msg }) {
  const isUser = msg.role === 'user'
  return (
    <Stack
      direction={isUser ? 'row-reverse' : 'row'}
      spacing={1.5}
      alignItems="flex-start"
      className="message-enter"
    >
      <Avatar
        sx={{
          width: 32, height: 32, flexShrink: 0, mt: 0.25,
          ...(isUser
            ? { bgcolor: '#1C2536', color: 'text.secondary', border: 1, borderColor: 'divider' }
            : { bgcolor: 'primary.main', color: '#1A1206' }),
        }}
      >
        {isUser ? <UserIcon fontSize="small" /> : <BotIcon fontSize="small" />}
      </Avatar>
      {/* minWidth: 0 lets long content wrap instead of forcing overflow (Bug 1) */}
      <Box sx={{ minWidth: 0, maxWidth: '72%' }}>
        <Paper
          elevation={0}
          sx={{
            px: 2, py: 1.5,
            fontSize: 14, lineHeight: 1.6,
            overflowWrap: 'break-word', wordBreak: 'break-word',
            border: 1, borderColor: 'divider',
            ...(isUser
              ? { bgcolor: '#1C2536', borderBottomRightRadius: 4 }
              : { bgcolor: 'rgba(11, 14, 21, 0.78)', borderBottomLeftRadius: 4 }),
          }}
        >
          {msg.content}
        </Paper>
        {!isUser && <MemoryBadges trace={msg.trace} />}
        <Typography variant="caption" color="text.disabled" sx={{ mt: 0.75, fontSize: 10 }}>
          {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          {!isUser && msg.trace ? ` · ${msg.trace.length} steps` : ''}
        </Typography>
      </Box>
    </Stack>
  )
}

export { MessageBubble, ThinkingOrb, EXAMPLE_PROMPTS }

// ── Pipeline trace → job-listing rows ─────────────────────────────────────────
// One row per conversation turn; clicking a row expands the full turn detail
// in a modal. Backend trace strings are sanitized (no em-dashes in UI copy).
const cleanText = s => String(s ?? '').replace(/—/g, '-').replace(/–/g, '-')

function turnToJob(turn, index) {
  const t = turn.trace || []
  const assess = t.find(n => n.node === 'assess_context')
  const extract = t.find(n => n.node === 'extract_and_classify')
  const write = t.find(n => n.node === 'write_memory')
  const retrieve = t.find(n => n.node === 'retrieve_memory')

  const memoriesCount = extract?.data?.memories_found ?? 0
  const didRetrieve = !!assess?.data?.needs_retrieval
  const accent = didRetrieve
    ? theme.palette.memory.episodic
    : memoriesCount > 0
      ? theme.palette.primary.main
      : '#5B6373'

  const parts = []
  if (assess?.data?.reasoning) parts.push('Assess: ' + cleanText(assess.data.reasoning))
  ;(assess?.data?.intents ?? []).forEach(i => parts.push('Intent: ' + cleanText(i)))
  ;(retrieve?.data?.results_summary ?? []).forEach(
    r => parts.push(`Retrieved ${r.rows_found} rows: ` + cleanText(r.intent))
  )
  ;(extract?.data?.memories ?? []).forEach(
    m => parts.push(`[${m.memory_type}] ` + cleanText(m.content))
  )
  if (extract?.data?.reasoning) parts.push('Extract: ' + cleanText(extract.data.reasoning))
  ;(write?.data?.write_results ?? []).forEach(
    w => parts.push(`Wrote ${w.memory_type}: ` + cleanText(w.content))
  )

  const ts = t[0]?.timestamp
  return {
    company: `Turn ${index + 1}`,
    title: (turn.userMsg || '').slice(0, 60),
    logo: (
      <span style={{
        display: 'flex', width: 30, height: 30, borderRadius: '50%',
        alignItems: 'center', justifyContent: 'center',
        fontSize: 12, fontWeight: 700, color: '#05070C', background: accent,
        flexShrink: 0,
      }}>
        {index + 1}
      </span>
    ),
    job_description: parts.length > 0 ? parts.join(' | ') : 'No trace details recorded for this turn.',
    salary: `${t.length} steps`,
    location: ts ? new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '',
    remote: didRetrieve ? 'Yes' : 'No',
    job_time: memoriesCount > 0 ? `+${memoriesCount} stored` : 'no writes',
  }
}

export default function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [showDebug, setShowDebug] = useState(true)
  const [backendUp, setBackendUp] = useState(null)
  const [conversationId, setConversationId] = useState(() => crypto.randomUUID())
  const [traceHistory, setTraceHistory] = useState([])
  const messagesBoxRef = useRef(null)
  const composerRef = useRef(null)

  // Real backend health drives the header status dot (semantic state, not decor)
  useEffect(() => {
    let cancelled = false
    fetch('health')
      .then(r => { if (!cancelled) setBackendUp(r.ok) })
      .catch(() => { if (!cancelled) setBackendUp(false) })
    return () => { cancelled = true }
  }, [])

  // Bug 1 fix: scroll ONLY the message list, vertically only. The old
  // scrollIntoView() scrolled every scrollable ancestor on both axes,
  // which shifted content left whenever anything overflowed horizontally.
  useEffect(() => {
    const el = messagesBoxRef.current
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  }, [messages, isLoading])

  const autosizeComposer = () => {
    const el = composerRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 120) + 'px'
  }

  const sendMessage = async (text) => {
    const content = (text || input).trim()
    if (!content || isLoading) return

    setInput('')
    if (composerRef.current) composerRef.current.style.height = 'auto'

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
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Something went wrong: ${err.message}. Is the backend running?`,
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

  const newConversation = () => {
    if (isLoading) return
    setConversationId(crypto.randomUUID())
    setMessages([])
    setTraceHistory([])
  }

  const dotColor = backendUp === null
    ? 'text.disabled'
    : backendUp
      ? theme.palette.memory.episodic
      : theme.palette.error.main
  const dotTitle = backendUp === null ? 'Checking backend' : backendUp ? 'Backend connected' : 'Backend unreachable'

  return (
    <>
      {/* Night-sky backdrop (fixed, behind the app) */}
      <Box sx={{ position: 'fixed', inset: 0, zIndex: 0 }} aria-hidden={false}>
        <GitHubSky
          href={REPO_URL}
          headline="Identity-Aware Conversational Intelligence"
          description="A memory-powered companion that remembers who you are."
          buttonLabel="Star on GitHub"
          seed={7}
          starCount={240}
          className="h-full w-full max-w-none rounded-none border-0"
        />
      </Box>

      <Box sx={{ position: 'relative', zIndex: 1, height: '100dvh', display: 'flex', flexDirection: 'column', maxWidth: 1400, mx: 'auto', px: 2 }}>
        <AppBar position="static" elevation={0} sx={{ bgcolor: 'transparent', color: 'text.primary', borderBottom: 1, borderColor: 'divider' }}>
          <Toolbar disableGutters sx={{ py: 1.25, gap: 1.25 }}>
            <Avatar sx={{ width: 34, height: 34, borderRadius: 1.5, bgcolor: 'primary.main', color: '#1A1206' }}>
              <BrandIcon fontSize="small" />
            </Avatar>
            <Box sx={{ flexGrow: 1 }}>
              <Typography variant="subtitle1" fontWeight={600} sx={{ letterSpacing: -0.2, lineHeight: 1.2 }}>
                IACI
              </Typography>
              <Typography variant="caption" color="text.disabled" sx={{ fontSize: 11 }}>
                Identity-Aware Conversational Intelligence
              </Typography>
            </Box>
            <Tooltip title={`${dotTitle}: ${conversationId.slice(0, 8)}`}>
              <Chip
                size="small"
                icon={<Box sx={{ width: 7, height: 7, borderRadius: '50%', bgcolor: dotColor, ml: '4px !important' }} />}
                label={conversationId.slice(0, 8)}
                variant="outlined"
                sx={{ fontFamily: 'monoFamily', fontSize: 12, color: 'text.secondary' }}
              />
            </Tooltip>
            <Button size="small" variant="outlined" color="inherit" startIcon={<NewChatIcon />} onClick={newConversation} sx={{ color: 'text.secondary', borderColor: 'divider' }}>
              New chat
            </Button>
            <Button
              size="small"
              variant={showDebug ? 'contained' : 'outlined'}
              color={showDebug ? 'primary' : 'inherit'}
              startIcon={<TraceIcon />}
              onClick={() => setShowDebug(v => !v)}
              sx={showDebug ? { color: '#1A1206' } : { color: 'text.secondary', borderColor: 'divider' }}
            >
              {showDebug ? 'Hide trace' : 'Show trace'}
            </Button>
          </Toolbar>
        </AppBar>

        <Box sx={{ flex: 1, display: 'flex', gap: 2, py: 1.5, minHeight: 0, overflow: 'hidden' }}>
          {/* Chat panel: translucent dark glass over the starfield */}
          <Paper elevation={0} sx={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, overflow: 'hidden', border: 1, borderColor: 'divider', bgcolor: 'rgba(11, 14, 21, 0.82)', backdropFilter: 'blur(14px)' }}>
            <Box
              ref={messagesBoxRef}
              sx={{ flex: 1, overflowY: 'auto', overflowX: 'hidden', overscrollBehavior: 'contain', p: 2.5 }}
            >
              {messages.length === 0 ? (
                <Stack alignItems="center" justifyContent="center" spacing={2} textAlign="center" sx={{ minHeight: '100%', p: 4 }}>
                  <Avatar sx={{ width: 64, height: 64, borderRadius: 3, bgcolor: alpha(theme.palette.primary.main, 0.14), color: 'primary.main' }}>
                    <BrandIcon fontSize="large" />
                  </Avatar>
                  <Typography variant="h6" fontWeight={600}>
                    Memory-powered conversation
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 380, lineHeight: 1.7 }}>
                    Tell me about yourself: your experiences, feelings, and who you are.
                    I remember it all across our conversations and use it to know you better.
                  </Typography>
                  <Stack direction="row" flexWrap="wrap" useFlexGap justifyContent="center" spacing={1} sx={{ mt: 0.5 }}>
                    {EXAMPLE_PROMPTS.map((p, i) => (
                      <Chip
                        key={i}
                        label={p.length > 50 ? p.slice(0, 50) + '…' : p}
                        onClick={() => sendMessage(p)}
                        variant="outlined"
                        sx={{ color: 'text.secondary', '&:hover': { color: 'primary.main', borderColor: 'primary.main', bgcolor: alpha(theme.palette.primary.main, 0.08) } }}
                      />
                    ))}
                  </Stack>
                </Stack>
              ) : (
                <Stack spacing={2}>
                  {messages.map((msg, i) => <MessageBubble key={i} msg={msg} />)}
                  {isLoading && <ThinkingOrb />}
                </Stack>
              )}
            </Box>

            {/* Metal composer: background + send only (no Plus/Agent/Auto chips) */}
            <Box sx={{ p: 1.5, pb: 2, borderTop: 1, borderColor: 'divider', flexShrink: 0 }}>
              <div
                className="flex w-full flex-col rounded-[20px] px-4 pb-4 pt-5"
                style={{ background: 'rgba(20, 24, 33, 0.78)', backdropFilter: 'blur(12px)', border: '1px solid rgba(255,255,255,0.08)' }}
              >
                <textarea
                  ref={composerRef}
                  rows={1}
                  value={input}
                  aria-label="Chat message"
                  placeholder="Tell me something about yourself..."
                  onChange={e => { setInput(e.target.value); autosizeComposer() }}
                  onKeyDown={handleKeyDown}
                  disabled={isLoading}
                  className="mb-4 w-full resize-none border-none bg-transparent p-0 text-sm leading-5 text-[#f0f4ff] outline-none placeholder:text-[#5B6373] disabled:opacity-50"
                  style={{ maxHeight: 120, overflowY: 'auto' }}
                />
                <div className="mt-auto flex items-center gap-3">
                  <div className="flex-1" />
                  <MetalFx preset="silver" variant="circle" strength={1} theme="dark">
                    <button
                      aria-label="Send"
                      onClick={() => sendMessage()}
                      disabled={!input.trim() || isLoading}
                      className="flex size-10 items-center justify-center rounded-full bg-[#1d1d1d] text-[#fbfbfb] disabled:opacity-40"
                    >
                      <SendArrowIcon className="size-4" />
                    </button>
                  </MetalFx>
                </div>
              </div>
              <Typography variant="caption" color="text.disabled" align="center" display="block" sx={{ mt: 0.75, fontSize: 11 }}>
                Enter to send · Shift+Enter for newline
              </Typography>
            </Box>
          </Paper>

          {showDebug && (
            <Paper
              elevation={0}
              sx={{
                width: 380, flexShrink: 0, minHeight: 0,
                display: { xs: 'none', lg: 'flex' }, flexDirection: 'column',
                overflow: 'hidden', border: 1, borderColor: 'divider',
                bgcolor: 'rgba(11, 14, 21, 0.82)', backdropFilter: 'blur(14px)',
              }}
            >
              <Box sx={{ px: 2, py: 1.5, borderBottom: 1, borderColor: 'divider', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0 }}>
                <Stack direction="row" alignItems="center" spacing={0.75}>
                  <TraceIcon fontSize="small" color="action" />
                  <Typography variant="overline" fontWeight={600} color="text.secondary" sx={{ letterSpacing: 0.5 }}>
                    Pipeline trace
                  </Typography>
                </Stack>
                <Typography variant="caption" color="text.disabled" sx={{ fontFamily: 'monoFamily', fontSize: 11 }}>
                  {traceHistory.length} turns
                </Typography>
              </Box>

              {/* Bounded outer scroll; the expanded modal confines itself here */}
              <Box sx={{ flex: 1, minHeight: 0, overflowY: 'auto', overscrollBehavior: 'contain', position: 'relative' }}>
                {traceHistory.length === 0 ? (
                  <Stack alignItems="center" justifyContent="center" spacing={1} textAlign="center" sx={{ minHeight: '100%', p: 4, color: 'text.disabled' }}>
                    <EmptyTraceIcon />
                    <Typography variant="body2">Send a message to see the pipeline trace here</Typography>
                    <Typography variant="caption">Each turn shows retrieval decisions, memory classification, and write operations</Typography>
                  </Stack>
                ) : (
                  <JobListingComponent
                    jobs={[...traceHistory].reverse().map((turn, ri) =>
                      turnToJob(turn, traceHistory.length - 1 - ri)
                    )}
                  />
                )}
              </Box>
            </Paper>
          )}
        </Box>
      </Box>
    </>
  )
}
