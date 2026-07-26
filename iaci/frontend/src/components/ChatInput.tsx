import { useState, useRef } from 'react'

export default function ChatInput({ onSend, disabled }: { onSend: (text: string) => void; disabled: boolean }) {
  const [value, setValue] = useState('')
  const ref = useRef<HTMLTextAreaElement>(null)

  const submit = () => {
    if (!value.trim()) return
    onSend(value)
    setValue('')
    ref.current?.focus()
  }

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  return (
    <div className="chat-input-wrapper">
      <textarea
        ref={ref}
        className="chat-input"
        value={value}
        onChange={e => setValue(e.target.value)}
        onKeyDown={handleKey}
        placeholder="Say something..."
        disabled={disabled}
        rows={1}
      />
      <button className="send-btn" onClick={submit} disabled={disabled || !value.trim()}>
        Send
      </button>
    </div>
  )
}
