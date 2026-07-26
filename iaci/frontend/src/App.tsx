import { useState, useRef, useEffect } from 'react'
import ChatMessage from './components/ChatMessage'
import ChatInput from './components/ChatInput'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

export default function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const [userId] = useState(() => `user_${Math.random().toString(36).slice(2, 10)}`)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const send = async (text: string) => {
    if (!text.trim() || loading) return
    setMessages(prev => [...prev, { role: 'user', content: text }])
    setLoading(true)
    try {
      const res = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, message: text }),
      })
      const data = await res.json()
      setMessages(prev => [...prev, { role: 'assistant', content: data.reply }])
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Something went wrong. Please try again.' }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="header">
        <h1>IACI</h1>
        <span className="subtitle">Identity-Aware Conversational Intelligence</span>
      </header>
      <main className="chat-container">
        {messages.length === 0 && (
          <div className="empty-state">
            <p>Start a conversation. I'll remember what matters.</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <ChatMessage key={i} role={msg.role} content={msg.content} />
        ))}
        {loading && (
          <div className="typing-indicator">
            <span className="dot" /><span className="dot" /><span className="dot" />
          </div>
        )}
        <div ref={bottomRef} />
      </main>
      <ChatInput onSend={send} disabled={loading} />
    </div>
  )
}
