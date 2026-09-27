import React, { useState, useRef, useEffect } from 'react'
import { alpha } from '@mui/material/styles'
import {
  AppBar, Toolbar, Typography, Button, Chip, Paper, Stack, Box,
  Avatar, TextField, IconButton, Accordion, AccordionSummary,
  AccordionDetails, Tooltip,
} from '@mui/material'
import {
  SmartToy as BotIcon,
  Person as UserIcon,
  Send as SendIcon,
  Add as NewChatIcon,
  Science as TraceIcon,
  Search as EmptyTraceIcon,
  ChevronRight as ExpandIcon,
  Event as EpisodicIcon,
  Mood as EmotionalIcon,
  Psychology as BrandIcon,
} from '@mui/icons-material'
import theme from './theme.js'

const API_BASE = '/api'

const EXAMPLE_PROMPTS = [
  "I just bombed my job interview and I'm scared I'll never get hired",
  "My name is Arjun and I'm a backend engineer who loves hiking",
  "I traveled to Goa last weekend, it was incredible",
  "I feel really proud of myself for finishing my side project today",
  "My sister Meera got engaged, I'm over the moon for her",
]

const MEMORY_META = {
  identity:  { color: theme.palette.memory.identity,  icon: <UserIcon fontSize="inherit" />,     label: 'identity' },
  episodic:  { color: theme.palette.memory.episodic,  icon: <EpisodicIcon fontSize="inherit" />,  label: 'episodic' },
  emotional: { color: theme.palette.memory.emotional, icon: <EmotionalIcon fontSize="inherit" />, label: 'emotional' },
}

function TypingIndicator() {
  return (
    <Stack direction="row" spacing={1.5} alignItems="flex-start" className="message-enter">
      <Avatar sx={{ width: 32, height: 32, bgcolor: 'primary.main' }}>
        <BotIcon fontSize="small" />
      </Avatar>
      <Paper variant="outlined" sx={{ px: 2, py: 1.75, borderBottomLeftRadius: 4, width: 'fit-content' }}>
        <span className="typing-dots">
          <span className="typing-dot" />
          <span className="typing-dot" />
          <span className="typing-dot" />
        </span>
      </Paper>
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
              bgcolor: alpha(meta.color, 0.1),
              border: `1px solid ${alpha(meta.color, 0.25)}`,
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
            ? { bgcolor: 'background.paper', color: 'text.secondary', border: 1, borderColor: 'divider' }
            : { bgcolor: 'primary.main' }),
        }}
      >
        {isUser ? <UserIcon fontSize="small" /> : <BotIcon fontSize="small" />}
      </Avatar>
      {/* minWidth: 0 lets long content wrap instead of forcing overflow (Bug 1) */}
      <Box sx={{ minWidth: 0, maxWidth: '72%' }}>
        <Paper
          variant={isUser ? 'elevation' : 'outlined'}
          elevation={0}
          sx={{
            px: 2, py: 1.5,
            fontSize: 14, lineHeight: 1.6,
            overflowWrap: 'break-word', wordBreak: 'break-word',
            ...(isUser
              ? { bgcolor: '#EDE5D3', borderBottomRightRadius: 4 }
              : { borderBottomLeftRadius: 4 }),
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

export { MessageBubble, TypingIndicator, EXAMPLE_PROMPTS }

function NodePill({ text, color }) {
  return (
    <Chip
      size="small"
      label={text}
      sx={{ height: 18, fontSize: 9, fontWeight: 600, color, bgcolor: alpha(color, 0.12) }}
    />
  )
}

function NodeCard({ name, pills = [], reasoning, children }) {
  return (
    <Paper
      variant="outlined"
      sx={{ p: 1.25, bgcolor: 'background.default', borderRadius: 1.5, flexShrink: 0 }}
    >
      <Stack direction="row" alignItems="center" spacing={0.75} flexWrap="wrap" useFlexGap sx={{ mb: 0.5 }}>
        <Typography
          variant="caption"
          sx={{ fontFamily: 'monoFamily', fontWeight: 600, fontSize: 10, color: 'text.secondary', textTransform: 'uppercase', letterSpacing: 0.4 }}
        >
          {name.replace(/_/g, ' ')}
        </Typography>
        {pills.map((p, i) => <NodePill key={i} text={p.text} color={p.color} />)}
      </Stack>
      {children}
      {reasoning && (
        <Typography variant="caption" color="text.disabled" fontStyle="italic" sx={{ mt: 0.5, display: 'block', lineHeight: 1.5, overflowWrap: 'anywhere' }}>
          {reasoning}
        </Typography>
      )}
    </Paper>
  )
}

// Inner scroll box for long step content (Bug 2: step details must scroll)
function StepScroll({ children }) {
  return (
    <Box sx={{ maxHeight: 220, overflowY: 'auto', overscrollBehavior: 'contain', mt: 0.75, pr: 0.5 }}>
      {children}
    </Box>
  )
}

function TraceTurn({ index, turn, open, onToggle }) {
  const assessNode = turn.trace?.find(t => t.node === 'assess_context')
  const extractNode = turn.trace?.find(t => t.node === 'extract_and_classify')
  const writeNode = turn.trace?.find(t => t.node === 'write_memory')
  const retrieveNode = turn.trace?.find(t => t.node === 'retrieve_memory')

  const memoriesCount = extractNode?.data?.memories_found ?? 0
  const didRetrieve = assessNode?.data?.needs_retrieval
  const okGreen = theme.palette.memory.episodic
  const neutral = theme.palette.text.disabled

  return (
    <Accordion
      expanded={!!open}
      onChange={onToggle}
      disableGutters
      elevation={0}
      sx={{ flexShrink: 0, border: 1, borderColor: 'divider', borderRadius: '12px !important', '&:before': { display: 'none' } }}
    >
      <AccordionSummary expandIcon={<ExpandIcon fontSize="small" />} sx={{ px: 1.5, minHeight: 44 }}>
        <Stack direction="row" alignItems="center" spacing={0.75} flexWrap="wrap" useFlexGap>
          <Typography variant="caption" sx={{ fontFamily: 'monoFamily', fontWeight: 600, fontSize: 11, color: 'text.secondary' }}>
            Turn #{index + 1}
          </Typography>
          {didRetrieve && <NodePill text="retrieved" color={okGreen} />}
          {memoriesCount > 0 && <NodePill text={`+${memoriesCount} stored`} color={theme.palette.primary.main} />}
        </Stack>
      </AccordionSummary>
      <AccordionDetails sx={{ pt: 0, px: 1, pb: 1 }}>
        <Stack spacing={0.5}>
          <Typography variant="caption" color="text.disabled" fontStyle="italic" sx={{ px: 0.5, overflowWrap: 'anywhere' }}>
            "{turn.userMsg?.slice(0, 80)}{turn.userMsg?.length > 80 ? '…' : ''}"
          </Typography>

          {assessNode && (
            <NodeCard
              name="assess context"
              pills={[assessNode.data.needs_retrieval
                ? { text: 'retrieve', color: okGreen }
                : { text: 'skip retrieve', color: neutral }]}
              reasoning={assessNode.data.reasoning}
            >
              {assessNode.data.intents?.length > 0 && (
                <StepScroll>
                  <Stack spacing={0.25}>
                    {assessNode.data.intents.map((intent, j) => (
                      <Typography key={j} variant="caption" color="text.disabled" sx={{ fontSize: 10, borderLeft: 2, borderColor: 'primary.light', pl: 0.75, ml: 0.25, overflowWrap: 'anywhere' }}>
                        {intent}
                      </Typography>
                    ))}
                  </Stack>
                </StepScroll>
              )}
            </NodeCard>
          )}

          {retrieveNode && (
            <NodeCard
              name="retrieve memory"
              pills={(retrieveNode.data.results_summary ?? []).map(r => ({ text: `${r.rows_found} rows`, color: okGreen }))}
            >
              <StepScroll>
                <Stack spacing={0.25}>
                  {(retrieveNode.data.results_summary ?? []).map((r, j) => (
                    <Typography key={j} variant="caption" color="text.disabled" sx={{ fontSize: 10, borderLeft: 2, borderColor: 'primary.light', pl: 0.75, ml: 0.25, overflowWrap: 'anywhere' }}>
                      {r.intent} → {r.rows_found} result{r.rows_found !== 1 ? 's' : ''}
                    </Typography>
                  ))}
                </Stack>
              </StepScroll>
            </NodeCard>
          )}

          {extractNode && (
            <NodeCard
              name="extract and classify"
              pills={[{ text: `${memoriesCount} memories`, color: theme.palette.primary.main }]}
              reasoning={extractNode.data.reasoning}
            >
              {extractNode.data.memories?.length > 0 && (
                <StepScroll>
                  <Stack spacing={0.5}>
                    {extractNode.data.memories.map((m, j) => {
                      const meta = MEMORY_META[m.memory_type]
                      return (
                        <Box key={j} sx={{ fontSize: 10, p: 0.75, borderRadius: 1, fontFamily: 'monoFamily', lineHeight: 1.4, overflowWrap: 'anywhere', color: meta?.color, bgcolor: alpha(meta?.color ?? '#999', 0.08) }}>
                          [{m.memory_type}] {m.content?.slice(0, 70)}{m.content?.length > 70 ? '…' : ''}
                        </Box>
                      )
                    })}
                  </Stack>
                </StepScroll>
              )}
            </NodeCard>
          )}

          {writeNode && (
            <NodeCard
              name="write memory"
              pills={[{ text: `${writeNode.data.writes} writes`, color: theme.palette.memory.emotional }]}
            >
              {(writeNode.data.write_results?.length ?? 0) > 0 && (
                <StepScroll>
                  <Stack spacing={0.5}>
                    {writeNode.data.write_results.map((w, j) => {
                      const meta = MEMORY_META[w.memory_type]
                      return (
                        <Box key={j} sx={{ fontSize: 10, p: 0.75, borderRadius: 1, fontFamily: 'monoFamily', lineHeight: 1.4, overflowWrap: 'anywhere', color: meta?.color, bgcolor: alpha(meta?.color ?? '#999', 0.08) }}>
                          ✓ {w.memory_type}: {w.content?.slice(0, 60)}{w.content?.length > 60 ? '…' : ''}
                        </Box>
                      )
                    })}
                  </Stack>
                </StepScroll>
              )}
            </NodeCard>
          )}
        </Stack>
      </AccordionDetails>
    </Accordion>
  )
}

export default function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [showDebug, setShowDebug] = useState(true)
  const [backendUp, setBackendUp] = useState(null)
  const [conversationId, setConversationId] = useState(() => crypto.randomUUID())
  const [traceHistory, setTraceHistory] = useState([])
  const [expandedTurns, setExpandedTurns] = useState({})
  const messagesBoxRef = useRef(null)

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

  const sendMessage = async (text) => {
    const content = (text || input).trim()
    if (!content || isLoading) return

    setInput('')
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

  const toggleTurn = (i) => setExpandedTurns(prev => ({ ...prev, [i]: !prev[i] }))

  const newConversation = () => {
    if (isLoading) return
    setConversationId(crypto.randomUUID())
    setMessages([])
    setTraceHistory([])
    setExpandedTurns({})
  }

  const dotColor = backendUp === null ? 'text.disabled' : backendUp ? theme.palette.memory.episodic : theme.palette.error.main
  const dotTitle = backendUp === null ? 'Checking backend' : backendUp ? 'Backend connected' : 'Backend unreachable'

  return (
    <Box sx={{ height: '100dvh', display: 'flex', flexDirection: 'column', maxWidth: 1400, mx: 'auto', px: 2 }}>
      <AppBar position="static" elevation={0} sx={{ bgcolor: 'transparent', color: 'text.primary', borderBottom: 1, borderColor: 'divider' }}>
        <Toolbar disableGutters sx={{ py: 1.25, gap: 1.25 }}>
          <Avatar sx={{ width: 34, height: 34, borderRadius: 1.5, bgcolor: 'primary.main' }}>
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
            sx={showDebug ? {} : { color: 'text.secondary', borderColor: 'divider' }}
          >
            {showDebug ? 'Hide trace' : 'Show trace'}
          </Button>
        </Toolbar>
      </AppBar>

      <Box sx={{ flex: 1, display: 'flex', gap: 2, py: 1.5, minHeight: 0, overflow: 'hidden' }}>
        <Paper elevation={0} sx={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, overflow: 'hidden', border: 1, borderColor: 'divider' }}>
          <Box
            ref={messagesBoxRef}
            sx={{ flex: 1, overflowY: 'auto', overflowX: 'hidden', overscrollBehavior: 'contain', p: 2.5 }}
          >
            {messages.length === 0 ? (
              <Stack alignItems="center" justifyContent="center" spacing={2} textAlign="center" sx={{ minHeight: '100%', p: 4 }}>
                <Avatar sx={{ width: 64, height: 64, borderRadius: 3, bgcolor: alpha(theme.palette.primary.main, 0.12), color: 'primary.main' }}>
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
                      sx={{ color: 'text.secondary', '&:hover': { color: 'primary.main', borderColor: 'primary.main', bgcolor: alpha(theme.palette.primary.main, 0.06) } }}
                    />
                  ))}
                </Stack>
              </Stack>
            ) : (
              <Stack spacing={2}>
                {messages.map((msg, i) => <MessageBubble key={i} msg={msg} />)}
                {isLoading && <TypingIndicator />}
              </Stack>
            )}
          </Box>

          <Box sx={{ p: 1.5, pt: 1.5, pb: 2, borderTop: 1, borderColor: 'divider', flexShrink: 0 }}>
            <Box
              sx={{
                display: 'flex', alignItems: 'flex-end', gap: 1.25, p: 1.25,
                border: 1, borderColor: 'divider', borderRadius: 2, bgcolor: 'background.paper',
                transition: 'border-color 0.15s ease, box-shadow 0.15s ease',
                '&:focus-within': { borderColor: 'primary.main', boxShadow: `0 0 0 3px ${alpha(theme.palette.primary.main, 0.12)}` },
              }}
            >
              <TextField
                id="chat-input"
                multiline
                minRows={1}
                maxRows={5}
                fullWidth
                variant="standard"
                placeholder="Tell me something about yourself..."
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={isLoading}
                InputProps={{ disableUnderline: true, sx: { fontSize: 14, lineHeight: 1.5 } }}
              />
              <IconButton
                id="send-btn"
                color="primary"
                onClick={() => sendMessage()}
                disabled={!input.trim() || isLoading}
                title="Send (Enter)"
                sx={{ bgcolor: 'primary.main', color: '#fff', width: 34, height: 34, flexShrink: 0, '&:hover': { bgcolor: 'primary.dark' }, '&.Mui-disabled': { opacity: 0.4, color: '#fff' } }}
              >
                <SendIcon fontSize="small" />
              </IconButton>
            </Box>
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

            {/* Bug 2 fix: bounded outer scroll (flex + minHeight 0 + overflowY auto) */}
            <Box sx={{ flex: 1, minHeight: 0, overflowY: 'auto', overscrollBehavior: 'contain', p: 1.5, display: 'flex', flexDirection: 'column', gap: 1 }}>
              {traceHistory.length === 0 ? (
                <Stack alignItems="center" justifyContent="center" spacing={1} textAlign="center" sx={{ flex: 1, p: 4, color: 'text.disabled' }}>
                  <EmptyTraceIcon />
                  <Typography variant="body2">Send a message to see the pipeline trace here</Typography>
                  <Typography variant="caption">Each turn shows retrieval decisions, memory classification, and write operations</Typography>
                </Stack>
              ) : (
                [...traceHistory].reverse().map((turn, ri) => {
                  const i = traceHistory.length - 1 - ri
                  return (
                    <TraceTurn
                      key={i}
                      index={i}
                      turn={turn}
                      open={expandedTurns[i]}
                      onToggle={() => toggleTurn(i)}
                    />
                  )
                })
              )}
            </Box>
          </Paper>
        )}
      </Box>
    </Box>
  )
}
