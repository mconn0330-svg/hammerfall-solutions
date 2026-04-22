import { useState, useEffect, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  buildSlashCommands, parseSlashInput, getSuggestions, applySuggestion,
} from '../commands/slashCommands'

// ─── Command Palette ─────────────────────────────────────────────────────────
// Global overlay. Trigger: `/` outside text inputs, or Cmd/Ctrl+K anywhere.
// Anchors near the top of the viewport, dims the rest of the canvas, and reuses
// the same command registry as the chat slash popover. Side-effect commands
// (open/dock/pin/tab/contemplate) fire directly; informational output (help /
// status) renders inline, since the palette has no persistent log of its own.

export default function CommandPalette({
  open, onClose,
  onOpenWidget, onDockWidget, onUndockWidget, onPinWidget,
  onSwitchTab, onContemplate,
}) {
  const [input, setInput]             = useState('/')
  const [selectedIdx, setSelectedIdx] = useState(0)
  const [feedback, setFeedback]       = useState(null)   // { content, kind: 'info' | 'error' }
  const inputRef   = useRef(null)
  const emittedRef = useRef(false)   // did the current command render inline output?

  // ── Reset on open; autofocus input ────────────────────────────────────────
  useEffect(() => {
    if (!open) return
    setInput('/')
    setSelectedIdx(0)
    setFeedback(null)
    requestAnimationFrame(() => {
      const el = inputRef.current
      if (el) { el.focus(); el.setSelectionRange(1, 1) }
    })
  }, [open])

  // Window-level Esc so feedback panes (help/status) can be dismissed even
  // when the input has lost focus.
  useEffect(() => {
    if (!open) return
    const onKey = (e) => { if (e.key === 'Escape') { e.preventDefault(); onClose?.() } }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  // ── Commands context — emit renders inline, clear is a no-op with hint ────
  // (the chat history lives inside ChatPane; from the palette we can't clear it).
  // `emittedRef` is set whenever a command produces inline output, which blocks
  // auto-close so users can actually read /help, /status, etc.
  const commands = buildSlashCommands({
    emit:         (content) => { emittedRef.current = true; setFeedback({ content, kind: 'info' }) },
    clear:        ()        => { emittedRef.current = true; setFeedback({ content: 'Open the chat tab to clear history.', kind: 'error' }) },
    openWidget:   (id)      => onOpenWidget?.(id),
    dockWidget:   (id)      => onDockWidget?.(id),
    undockWidget: (id)      => onUndockWidget?.(id),
    pinWidget:    (id)      => onPinWidget?.(id),
    switchTab:    (tab)     => onSwitchTab?.(tab),
    contemplate:  ()        => onContemplate?.(),
  })

  const parsed      = parseSlashInput(input)
  const suggestions = getSuggestions(commands, parsed)

  // Keep selection index in bounds as the list shrinks.
  useEffect(() => {
    if (selectedIdx >= suggestions.length) setSelectedIdx(0)
  }, [suggestions.length, selectedIdx])

  const acceptSuggestion = useCallback((idx) => {
    const pick = suggestions[idx]
    if (!pick) return
    const next = applySuggestion(input, parsed, pick)
    setInput(next)
    setSelectedIdx(0)
    requestAnimationFrame(() => {
      const el = inputRef.current
      if (el) { el.focus(); el.setSelectionRange(next.length, next.length) }
    })
  }, [suggestions, input, parsed])

  const runCurrent = useCallback(() => {
    const p = parseSlashInput(input)
    if (!p || !p.name) return
    const match = commands.find(c => c.name === p.name)
    if (!match) {
      emittedRef.current = true
      setFeedback({ content: `Unknown command: "/${p.name}"`, kind: 'error' })
      setInput('/')
      setSelectedIdx(0)
      return
    }
    setFeedback(null)
    emittedRef.current = false
    match.run(p.arg.trim())
    // Pure side-effect commands (no inline output) close the palette.
    // Commands that emit (help / status) reset the input so the user can
    // chain another command without dismissing first.
    if (!emittedRef.current) {
      onClose?.()
    } else {
      setInput('/')
      setSelectedIdx(0)
      requestAnimationFrame(() => {
        const el = inputRef.current
        if (el) { el.focus(); el.setSelectionRange(1, 1) }
      })
    }
  }, [commands, input, onClose])

  const handleKeyDown = (e) => {
    if (e.key === 'Escape') { e.preventDefault(); onClose?.(); return }
    if (suggestions.length > 0) {
      if (e.key === 'ArrowDown') { e.preventDefault(); setSelectedIdx(i => (i + 1) % suggestions.length); return }
      if (e.key === 'ArrowUp')   { e.preventDefault(); setSelectedIdx(i => (i - 1 + suggestions.length) % suggestions.length); return }
      if (e.key === 'Tab')       { e.preventDefault(); acceptSuggestion(selectedIdx); return }
    }
    if (e.key === 'Enter') {
      e.preventDefault()
      // If exactly one suggestion AND it's a pure-command completion for an
      // arg-taking cmd, auto-complete first so Enter feels responsive on `/o`.
      const p = parseSlashInput(input)
      if (p && !p.hasSpace && suggestions.length === 1) {
        const only = suggestions[0]
        if (only.kind === 'command' && only.hint) {
          acceptSuggestion(0)
          return
        }
      }
      runCurrent()
    }
  }

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          key="palette-backdrop"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.12 }}
          onMouseDown={onClose}
          style={{
            position: 'fixed', inset: 0,
            background: 'rgba(4, 8, 14, 0.55)',
            backdropFilter: 'blur(2px)',
            zIndex: 900,
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'flex-start',
            paddingTop: 72,
          }}
        >
          <motion.div
            key="palette"
            initial={{ opacity: 0, y: -8, scale: 0.985 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.99 }}
            transition={{ duration: 0.14 }}
            onMouseDown={e => e.stopPropagation()}
            style={{
              width: 'min(560px, 92vw)',
              background: 'rgba(10, 15, 24, 0.98)',
              border: '1px solid rgba(77,184,255,0.3)',
              borderRadius: 10,
              boxShadow: '0 12px 48px rgba(0,0,0,0.55), 0 0 0 1px rgba(0,0,0,0.3)',
              backdropFilter: 'blur(16px)',
              overflow: 'hidden',
              display: 'flex', flexDirection: 'column',
              maxHeight: '70vh',
            }}
          >
            {/* Input row */}
            <div style={{
              display: 'flex', alignItems: 'center', gap: 10,
              padding: '14px 18px',
              borderBottom: suggestions.length || feedback ? '1px solid var(--border)' : 'none',
            }}>
              <span style={{
                fontFamily: 'var(--sans)', fontSize: 10,
                color: 'var(--text-accent)',
                letterSpacing: '0.14em', textTransform: 'uppercase',
                flexShrink: 0,
              }}>
                Command
              </span>
              <input
                ref={inputRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                spellCheck={false}
                autoComplete="off"
                style={{
                  flex: 1,
                  background: 'transparent',
                  border: 'none',
                  outline: 'none',
                  color: 'var(--text-primary)',
                  fontFamily: 'var(--mono, monospace)',
                  fontSize: 14,
                  padding: 0,
                }}
                placeholder="/help, /open, /dock, /tab…"
              />
              <kbd style={{
                fontFamily: 'var(--sans)', fontSize: 10,
                color: 'var(--text-dim)',
                padding: '2px 6px',
                border: '1px solid var(--border)',
                borderRadius: 3,
                flexShrink: 0,
              }}>
                esc
              </kbd>
            </div>

            {/* Inline feedback (help / status / error) — stays visible while
                the user types the next command. The live suggestions below
                reflect the new input; feedback above is the last result. */}
            {feedback && (
              <div style={{
                padding: '12px 18px 14px',
                borderBottom: suggestions.length > 0 ? '1px solid var(--border)' : 'none',
                maxHeight: 280, overflowY: 'auto',
                background: 'rgba(255,255,255,0.015)',
              }}>
                <pre style={{
                  margin: 0,
                  fontFamily: 'var(--mono, monospace)', fontSize: 11,
                  color: feedback.kind === 'error' ? '#f87171' : 'var(--text-secondary)',
                  whiteSpace: 'pre-wrap', wordBreak: 'break-word',
                  lineHeight: 1.55,
                }}>
                  {feedback.content}
                </pre>
              </div>
            )}

            {/* Suggestion list */}
            {suggestions.length > 0 && (
              <div style={{ overflowY: 'auto', padding: '4px 0' }}>
                {suggestions.map((s, i) => {
                  const active = i === selectedIdx
                  return (
                    <div
                      key={`${s.kind}:${s.value}`}
                      onMouseEnter={() => setSelectedIdx(i)}
                      onClick={() => { acceptSuggestion(i); }}
                      style={{
                        display: 'flex', alignItems: 'center', gap: 12,
                        padding: '8px 18px',
                        cursor: 'pointer',
                        background: active ? 'rgba(77,184,255,0.1)' : 'transparent',
                        borderLeft: active ? '2px solid var(--node-primary)' : '2px solid transparent',
                      }}
                    >
                      <span style={{
                        fontFamily: 'var(--mono, monospace)', fontSize: 13,
                        color: active ? 'var(--node-primary)' : 'var(--text-primary)',
                        minWidth: 120,
                      }}>
                        {s.label}
                      </span>
                      {s.hint && (
                        <span style={{
                          fontFamily: 'var(--mono, monospace)', fontSize: 11,
                          color: 'var(--text-dim)',
                          flexShrink: 0,
                        }}>
                          {s.hint}
                        </span>
                      )}
                      <span style={{
                        fontFamily: 'var(--sans)', fontSize: 11,
                        color: 'var(--text-secondary)',
                        flex: 1, minWidth: 0,
                        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                        textAlign: 'right',
                      }}>
                        {s.description}
                      </span>
                    </div>
                  )
                })}
              </div>
            )}

            {/* Footer hints */}
            {(suggestions.length > 0 || feedback) && (
              <div style={{
                padding: '8px 18px',
                borderTop: '1px solid rgba(255,255,255,0.05)',
                fontFamily: 'var(--sans)', fontSize: 9,
                color: 'var(--text-dim)',
                letterSpacing: '0.08em',
                display: 'flex', gap: 18,
              }}>
                {suggestions.length > 0 && <span>↑↓ navigate</span>}
                {suggestions.length > 0 && <span>tab complete</span>}
                {suggestions.length > 0 && <span>enter run</span>}
                <span>esc close</span>
              </div>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
