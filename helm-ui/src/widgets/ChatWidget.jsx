import { useState, useRef, useEffect } from 'react'
import { CHAT_HISTORY } from '../data/mockData'

export default function ChatWidget({ onNodeStateChange }) {
  const [messages, setMessages] = useState(CHAT_HISTORY)
  const [input, setInput] = useState('')
  const [nodeState, setNodeState] = useState('idle')
  const [holdProgress, setHoldProgress] = useState(0)
  const [isHolding, setIsHolding] = useState(false)
  const [contemplating, setContemplating] = useState(false)
  const holdTimerRef = useRef(null)
  const holdStartRef = useRef(null)
  const holdRafRef = useRef(null)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Hold-to-contemplate
  const startHold = () => {
    if (contemplating) return
    setIsHolding(true)
    holdStartRef.current = Date.now()

    const tick = () => {
      const elapsed = Date.now() - holdStartRef.current
      const p = Math.min(elapsed / 1500, 1)
      setHoldProgress(p)
      if (p < 1) {
        holdRafRef.current = requestAnimationFrame(tick)
      } else {
        triggerContemplate()
      }
    }
    holdRafRef.current = requestAnimationFrame(tick)
  }

  const endHold = () => {
    setIsHolding(false)
    setHoldProgress(0)
    if (holdRafRef.current) cancelAnimationFrame(holdRafRef.current)
  }

  const triggerContemplate = () => {
    setIsHolding(false)
    setHoldProgress(0)
    setContemplating(true)
    onNodeStateChange?.('contemplating')

    setMessages(prev => [...prev, {
      id: Date.now(),
      role: 'helm',
      content: 'Thinking.',
      timestamp: new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }),
      routing: 'HELM_PRIME',
      isContemplating: true,
    }])

    // Simulate deep pass completion (~4s)
    setTimeout(() => {
      setContemplating(false)
      onNodeStateChange?.('idle')
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        role: 'helm',
        content: "Deep pass complete. Two observations worth noting:\n\nFirst, the pattern-synthesis pass flagged a growing tension between small-PR preference and the BA3 bundle decision. I've logged it as a curiosity flag for next session — the resolution you gave me was partial.\n\nSecond, I updated the cost-asymmetry-routing belief by +0.10. The imperative-directive regression was the clearest evidence yet for that principle. It's now at 0.85.",
        timestamp: new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }),
        routing: 'HELM_PRIME',
      }])
    }, 4000)
  }

  const sendMessage = (e) => {
    e.preventDefault()
    if (!input.trim() || contemplating) return

    const userMsg = {
      id: Date.now(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }),
    }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    onNodeStateChange?.('processing')

    // Simulate response delay
    setTimeout(() => {
      onNodeStateChange?.('idle')
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        role: 'helm',
        content: "Noted. That's on the board for BA4 scope — I'll flag it when we get to the full spec.",
        timestamp: new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }),
        routing: 'HELM_PRIME',
      }])
    }, 1800)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>

      {/* Session open banner */}
      <div style={{
        padding: '12px 18px',
        borderBottom: '1px solid var(--border)',
        background: 'rgba(77, 184, 255, 0.04)',
      }}>
        <p className="body-text-sm" style={{
          color: 'var(--text-accent)',
          fontStyle: 'italic',
        }}>
          Before we get into it — I've been thinking about a couple of things since we last spoke.
          The Contemplator inner-life loop was broken, and the write path was missing embeddings.
          Both fixed in PR #69. Worth knowing before we move forward.
        </p>
      </div>

      {/* Message list */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '16px 18px', display: 'flex', flexDirection: 'column', gap: 20 }}>
        {messages.map(msg => (
          <div key={msg.id} style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start',
          }}>
            {/* Routing badge — always "Helm" regardless of internal routing */}
            {msg.routing && (
              <span style={{ marginBottom: 4 }} className="badge badge-blue">
                Helm
              </span>
            )}

            <div style={{
              maxWidth: '88%',
              padding: '10px 0',
              borderBottom: '1px solid rgba(255,255,255,0.04)',
            }}>
              {msg.role === 'helm' ? (
                <p className="body-text" style={{
                  whiteSpace: 'pre-wrap',
                  color: msg.isContemplating ? 'var(--amber)' : undefined,
                  opacity: msg.isContemplating ? 0.8 : 1,
                }}>
                  {msg.content}
                </p>
              ) : (
                <p className="user-voice" style={{ textAlign: 'right' }}>
                  {msg.content}
                </p>
              )}
            </div>

            <span style={{ fontFamily: 'var(--sans)', fontSize: 10, color: 'var(--text-dim)', marginTop: 4 }}>
              {msg.timestamp}
            </span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div style={{ padding: '12px 18px', borderTop: '1px solid var(--border)' }}>
        <form onSubmit={sendMessage} style={{ display: 'flex', gap: 10, alignItems: 'flex-end' }}>
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(e) } }}
            placeholder="Message Helm…"
            rows={2}
            disabled={contemplating}
            style={{
              flex: 1,
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid var(--border)',
              borderRadius: 8,
              padding: '8px 12px',
              color: 'var(--text-primary)',
              fontFamily: 'var(--sans)',
              fontSize: 13,
              resize: 'none',
              outline: 'none',
              lineHeight: 1.5,
            }}
          />

          {/* Hold-to-contemplate */}
          <button
            type="button"
            onMouseDown={startHold}
            onMouseUp={endHold}
            onMouseLeave={endHold}
            onTouchStart={startHold}
            onTouchEnd={endHold}
            title="Hold to trigger deep pass"
            style={{
              width: 36,
              height: 36,
              borderRadius: '50%',
              border: '1px solid rgba(245, 158, 11, 0.4)',
              background: `conic-gradient(rgba(245,158,11,0.7) ${holdProgress * 360}deg, rgba(255,255,255,0.05) 0deg)`,
              cursor: contemplating ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
              transition: 'border-color 0.2s',
              boxShadow: isHolding ? '0 0 12px rgba(245,158,11,0.4)' : 'none',
            }}
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <circle cx="7" cy="7" r="5" stroke="rgba(245,158,11,0.8)" strokeWidth="1.2"/>
              <circle cx="7" cy="7" r="2" fill="rgba(245,158,11,0.6)"/>
            </svg>
          </button>

          <button
            type="submit"
            disabled={!input.trim() || contemplating}
            style={{
              height: 36,
              padding: '0 16px',
              borderRadius: 8,
              border: '1px solid rgba(77,184,255,0.3)',
              background: 'rgba(77,184,255,0.08)',
              color: 'var(--node-primary)',
              fontFamily: 'var(--sans)',
              fontSize: 11,
              letterSpacing: '0.06em',
              textTransform: 'uppercase',
              cursor: 'pointer',
              flexShrink: 0,
            }}
          >
            Send
          </button>
        </form>
      </div>
    </div>
  )
}
