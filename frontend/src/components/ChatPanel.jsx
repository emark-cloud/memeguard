import { useState, useRef, useEffect } from 'react'
import { sendChatMessage, clearChatHistory, getChatHistory } from '../services/api'

export default function ChatPanel({ tokenAddress = null, tokenName = null }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [isOpen, setIsOpen] = useState(false)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Load persisted history when the panel opens or token scope changes.
  useEffect(() => {
    if (!isOpen) return
    let cancelled = false
    getChatHistory(tokenAddress)
      .then((rows) => {
        if (cancelled) return
        setMessages(rows.map((r) => ({ role: r.role, content: r.content })))
      })
      .catch(() => {
        /* ignore — empty history is a valid state */
      })
    return () => {
      cancelled = true
    }
  }, [isOpen, tokenAddress])

  const handleSend = async () => {
    const text = input.trim()
    if (!text || loading) return

    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: text }])
    setLoading(true)

    try {
      const data = await sendChatMessage(text, tokenAddress)
      setMessages((prev) => [...prev, { role: 'assistant', content: data.reply }])
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Sorry, something went wrong. Please try again.' },
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleClear = async () => {
    setMessages([])
    try {
      await clearChatHistory(tokenAddress)
    } catch {
      /* ignore */
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 w-14 h-14 rounded-full bg-[var(--accent-gold)] text-black flex items-center justify-center cursor-pointer shadow-lg hover:opacity-90 transition-opacity z-50"
        title="AI Advisor"
      >
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
      </button>
    )
  }

  return (
    <div className="fixed bottom-6 right-6 w-96 h-[500px] bg-[var(--bg-card)] border border-[var(--border)] rounded-xl shadow-2xl flex flex-col z-50">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border)]">
        <div>
          <h3 className="text-sm font-semibold text-[var(--text-primary)]">AI Trading Advisor</h3>
          {tokenName && (
            <span className="text-xs text-[var(--text-secondary)]">Context: {tokenName}</span>
          )}
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleClear}
            className="text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)] cursor-pointer"
            title="Clear history"
          >
            Clear
          </button>
          <button
            onClick={() => setIsOpen(false)}
            className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] cursor-pointer text-lg leading-none"
          >
            &times;
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && (
          <div className="text-center text-[var(--text-secondary)] text-sm py-8">
            <p className="mb-2">Ask me about tokens, risks, or trading strategies.</p>
            <div className="space-y-1 text-xs">
              <p className="text-[var(--accent-gold)] cursor-pointer hover:underline" onClick={() => setInput('Why is this token risky?')}>
                "Why is this token risky?"
              </p>
              <p className="text-[var(--accent-gold)] cursor-pointer hover:underline" onClick={() => setInput('What should I look for in a safe token?')}>
                "What should I look for in a safe token?"
              </p>
              <p className="text-[var(--accent-gold)] cursor-pointer hover:underline" onClick={() => setInput('Explain the bonding curve')}>
                "Explain the bonding curve"
              </p>
            </div>
          </div>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`text-sm ${
              msg.role === 'user'
                ? 'text-right'
                : ''
            }`}
          >
            <div
              className={`inline-block max-w-[85%] px-3 py-2 rounded-lg ${
                msg.role === 'user'
                  ? 'bg-[var(--accent-gold)] text-black'
                  : 'bg-[var(--bg-secondary)] text-[var(--text-primary)]'
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="text-sm">
            <div className="inline-block px-3 py-2 rounded-lg bg-[var(--bg-secondary)] text-[var(--text-secondary)]">
              Thinking...
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-3 border-t border-[var(--border)]">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about tokens, risks..."
            disabled={loading}
            className="flex-1 bg-[var(--bg-secondary)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-[var(--text-primary)] outline-none focus:border-[var(--accent-gold)] disabled:opacity-50 placeholder:text-[var(--text-secondary)]"
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className="px-4 py-2 bg-[var(--accent-gold)] text-black text-sm font-medium rounded-lg cursor-pointer hover:opacity-90 disabled:opacity-50 transition-opacity"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  )
}
