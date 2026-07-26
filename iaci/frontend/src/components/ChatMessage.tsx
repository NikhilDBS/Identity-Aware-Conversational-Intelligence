export default function ChatMessage({ role, content }: { role: 'user' | 'assistant'; content: string }) {
  return (
    <div className={`message ${role}`}>
      <div className="avatar">{role === 'user' ? 'You' : 'AI'}</div>
      <div className="bubble">{content}</div>
    </div>
  )
}
