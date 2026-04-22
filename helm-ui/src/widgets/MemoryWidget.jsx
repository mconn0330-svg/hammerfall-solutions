import { useState } from 'react'
import { MEMORY } from '../data/mockData'
import { motion, AnimatePresence } from 'framer-motion'

const TYPE_CONFIG = {
  behavioral: { color: '#4db8ff', bg: 'rgba(77,184,255,0.08)',  label: 'behavioral' },
  correction:  { color: '#f87171', bg: 'rgba(248,113,113,0.08)', label: 'correction' },
  reasoning:   { color: '#a5b4fc', bg: 'rgba(165,180,252,0.08)', label: 'reasoning' },
  scratchpad:  { color: '#f59e0b', bg: 'rgba(245,158,11,0.08)',  label: 'scratchpad' },
  monologue:   { color: '#6ee7b7', bg: 'rgba(52,211,153,0.08)',  label: 'monologue' },
}

export default function MemoryWidget() {
  const [selected, setSelected] = useState(null)
  const [search, setSearch] = useState('')

  const filtered = MEMORY.filter(m => {
    if (m.memory_type === 'scratchpad' || m.memory_type === 'heartbeat') return false
    if (search && !m.content.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  const entry = selected ? MEMORY.find(m => m.id === selected) : null

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Search */}
      <div style={{ padding: '10px 18px', borderBottom: '1px solid var(--border)', display: 'flex', gap: 10, alignItems: 'center' }}>
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Semantic search…"
          style={{
            flex: 1,
            background: 'rgba(255,255,255,0.03)',
            border: '1px solid var(--border)',
            borderRadius: 6,
            padding: '5px 10px',
            color: 'var(--text-primary)',
            fontFamily: 'var(--sans)',
            fontSize: 11,
            outline: 'none',
          }}
        />
      </div>

      <AnimatePresence mode="wait">
        {entry ? (
          // ── Entry detail ────────────────────────────────────────────────
          <motion.div key="detail" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            style={{ flex: 1, overflowY: 'auto' }}>
            <button onClick={() => setSelected(null)}
              style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '12px 18px', borderBottom: '1px solid var(--border)', width: '100%', background: 'none', border: 'none', borderBottom: '1px solid var(--border)', color: 'var(--text-secondary)', fontFamily: 'var(--sans)', fontSize: 10, letterSpacing: '0.08em', textTransform: 'uppercase', cursor: 'pointer', textAlign: 'left' }}>
              ← Back
            </button>
            <div style={{ padding: '16px 18px' }}>
              {/* Type + date */}
              <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 12 }}>
                {(() => {
                  const tc = TYPE_CONFIG[entry.memory_type] || TYPE_CONFIG.behavioral
                  return (
                    <span style={{ fontFamily: 'var(--sans)', fontSize: 10, padding: '2px 8px', borderRadius: 4,
                      color: tc.color, background: tc.bg, border: `1px solid ${tc.color}33`, letterSpacing: '0.06em', textTransform: 'uppercase' }}>
                      {tc.label}
                    </span>
                  )
                })()}
                <span style={{ fontFamily: 'var(--sans)', fontSize: 10, color: 'var(--text-dim)' }}>
                  {entry.session_date}
                </span>
                <span style={{ fontFamily: 'var(--sans)', fontSize: 10, color: '#4ade80', marginLeft: 'auto' }}>
                  {(entry.confidence * 100).toFixed(0)}% conf
                </span>
              </div>

              {/* Content */}
              <p className="body-text" style={{ marginBottom: 16 }}>
                {entry.content}
              </p>

              {/* Full content (JSONB expansion) */}
              {entry.full_content && (
                <>
                  <p style={{ fontFamily: 'var(--sans)', fontSize: 10, color: 'var(--text-dim)', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 8 }}>
                    Context
                  </p>
                  <div style={{ padding: '12px 14px', background: 'rgba(77,184,255,0.03)', border: '1px solid rgba(77,184,255,0.1)', borderRadius: 6, marginBottom: 14 }}>
                    {Object.entries(entry.full_content).map(([k, v]) => (
                      <div key={k} style={{ display: 'flex', gap: 12, marginBottom: 6 }}>
                        <span className="field-label" style={{ color: 'var(--text-dim)', flexShrink: 0, minWidth: 80 }}>
                          {k}
                        </span>
                        <span className="body-text-sm" style={{ color: 'var(--text-secondary)' }}>
                          {v}
                        </span>
                      </div>
                    ))}
                  </div>
                </>
              )}

              {/* Entity chips */}
              {entry.entity_refs?.length > 0 && (
                <div style={{ marginBottom: 12 }}>
                  <p style={{ fontFamily: 'var(--sans)', fontSize: 10, color: 'var(--text-dim)', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 6 }}>
                    Entities
                  </p>
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                    {entry.entity_refs.map(e => (
                      <span key={e} style={{ fontFamily: 'var(--sans)', fontSize: 10, padding: '2px 10px', borderRadius: 12,
                        border: '1px solid rgba(125,212,252,0.25)', color: '#7dd4fc', background: 'rgba(77,184,255,0.06)' }}>
                        {e}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Belief link */}
              {entry.belief_ref && (
                <div style={{ padding: '8px 12px', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border)', borderRadius: 6 }}>
                  <span style={{ fontFamily: 'var(--sans)', fontSize: 10, color: 'var(--text-dim)' }}>belief → </span>
                  <span style={{ fontFamily: 'var(--sans)', fontSize: 10, color: 'var(--node-primary)' }}>{entry.belief_ref}</span>
                </div>
              )}
            </div>
          </motion.div>
        ) : (
          // ── Table view ───────────────────────────────────────────────────
          <motion.div key="table" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            style={{ flex: 1, overflowY: 'auto' }}>
            {filtered.length === 0 && (
              <div style={{ padding: '32px 18px', textAlign: 'center' }}>
                <span className="body-text-sm" style={{ color: 'var(--text-dim)' }}>
                  No entries match
                </span>
              </div>
            )}
            {filtered.map(m => {
              const tc = TYPE_CONFIG[m.memory_type] || TYPE_CONFIG.behavioral
              return (
                <div key={m.id} onClick={() => setSelected(m.id)}
                  style={{ padding: '12px 18px', borderBottom: '1px solid var(--border)', cursor: 'pointer', transition: 'background 0.1s' }}
                  onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.02)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                >
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 6 }}>
                    <span style={{ fontFamily: 'var(--sans)', fontSize: 10, padding: '1px 7px', borderRadius: 3,
                      color: tc.color, background: tc.bg, border: `1px solid ${tc.color}33`, letterSpacing: '0.05em', textTransform: 'uppercase', flexShrink: 0 }}>
                      {tc.label}
                    </span>
                    <span style={{ fontFamily: 'var(--sans)', fontSize: 10, color: 'var(--text-dim)', marginLeft: 'auto', flexShrink: 0 }}>
                      {m.session_date}
                    </span>
                  </div>
                  <p className="body-text-sm" style={{ color: 'var(--text-secondary)',
                    overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>
                    {m.content}
                  </p>
                  {/* Confidence bar */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 6 }}>
                    <div className="strength-bar-track" style={{ flex: 1 }}>
                      <div className="strength-bar-fill" style={{ width: `${m.confidence * 100}%`, background: `linear-gradient(90deg, ${tc.color}66, ${tc.color})` }} />
                    </div>
                    <span style={{ fontFamily: 'var(--sans)', fontSize: 10, color: tc.color, flexShrink: 0 }}>
                      {(m.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              )
            })}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
