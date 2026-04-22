import { useState } from 'react'
import { BELIEFS } from '../data/mockData'
import { motion, AnimatePresence } from 'framer-motion'

const DOMAIN_COLORS = {
  process:      { bar: '#4db8ff', text: '#7dd4fc' },
  architecture: { bar: '#818cf8', text: '#a5b4fc' },
  product:      { bar: '#34d399', text: '#6ee7b7' },
  people:       { bar: '#f59e0b', text: '#fcd34d' },
  identity:     { bar: '#f87171', text: '#fca5a5' },
  ethics:       { bar: '#e879f9', text: '#f0abfc' },
}

export default function BeliefsWidget() {
  const [selected, setSelected] = useState(null)
  const belief = selected ? BELIEFS.find(b => b.id === selected) : null

  return (
    <div style={{ height: '100%', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
      <AnimatePresence mode="wait">
        {!selected ? (
          // ── Bar chart view ────────────────────────────────────────────────
          <motion.div
            key="list"
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -12 }}
            style={{ flex: 1, overflowY: 'auto', padding: '12px 0' }}
          >
            {BELIEFS.map(b => {
              const colors = DOMAIN_COLORS[b.domain] || DOMAIN_COLORS.process
              return (
                <div
                  key={b.id}
                  onClick={() => setSelected(b.id)}
                  style={{
                    padding: '12px 18px',
                    borderBottom: '1px solid var(--border)',
                    cursor: 'pointer',
                    transition: 'background 0.15s',
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.03)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                >
                  {/* Belief text */}
                  <p className="body-text-sm" style={{ marginBottom: 10 }}>
                    {b.belief}
                  </p>

                  {/* Bar + metadata */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <span className="badge" style={{ color: colors.text, borderColor: 'rgba(255,255,255,0.1)', flexShrink: 0 }}>
                      {b.domain}
                    </span>
                    <div style={{ flex: 1 }}>
                      <div className="strength-bar-track">
                        <motion.div
                          className="strength-bar-fill"
                          initial={{ width: 0 }}
                          animate={{ width: `${b.strength * 100}%` }}
                          transition={{ delay: 0.1, duration: 0.7, ease: 'easeOut' }}
                          style={{ background: `linear-gradient(90deg, ${colors.bar}88, ${colors.bar})` }}
                        />
                      </div>
                    </div>
                    <span style={{ fontFamily: 'var(--sans)', fontSize: 11, color: colors.text, flexShrink: 0 }}>
                      {b.strength.toFixed(2)}
                    </span>
                  </div>
                </div>
              )
            })}
          </motion.div>
        ) : (
          // ── Belief detail view ────────────────────────────────────────────
          <motion.div
            key="detail"
            initial={{ opacity: 0, x: 12 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 12 }}
            style={{ flex: 1, overflowY: 'auto', padding: '0' }}
          >
            {/* Back */}
            <button
              onClick={() => setSelected(null)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '12px 18px',
                borderBottom: '1px solid var(--border)',
                width: '100%',
                background: 'none',
                border: 'none',
                borderBottom: '1px solid var(--border)',
                color: 'var(--text-secondary)',
                fontFamily: 'var(--sans)',
                fontSize: 10,
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
                cursor: 'pointer',
                textAlign: 'left',
              }}
            >
              ← Back
            </button>

            <div style={{ padding: '16px 18px' }}>
              {/* Belief */}
              <p className="body-text" style={{ marginBottom: 16 }}>
                {belief.belief}
              </p>

              {/* Strength bar */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
                <span className="badge" style={{ color: (DOMAIN_COLORS[belief.domain] || DOMAIN_COLORS.process).text, borderColor: 'rgba(255,255,255,0.1)' }}>
                  {belief.domain}
                </span>
                <div style={{ flex: 1 }}>
                  <div className="strength-bar-track">
                    <motion.div
                      className="strength-bar-fill"
                      initial={{ width: 0 }}
                      animate={{ width: `${belief.strength * 100}%` }}
                      transition={{ duration: 0.6 }}
                    />
                  </div>
                </div>
                <span className="glow-text" style={{ fontFamily: 'var(--sans)', fontSize: 13 }}>
                  {belief.strength.toFixed(2)}
                </span>
              </div>

              {/* Observations */}
              <p className="field-label" style={{ marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.06em', fontSize: 10 }}>
                Last 3 Observations
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {belief.observations.map((obs, i) => (
                  <div key={i} style={{
                    padding: '10px 14px',
                    background: 'rgba(255,255,255,0.02)',
                    border: '1px solid var(--border)',
                    borderRadius: 8,
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span style={{ fontFamily: 'var(--sans)', fontSize: 10, color: 'var(--text-dim)' }}>
                        {obs.date}
                      </span>
                      <span style={{
                        fontFamily: 'var(--sans)',
                        fontSize: 11,
                        color: obs.delta >= 0 ? '#4ade80' : '#f59e0b',
                        fontWeight: 500,
                      }}>
                        {obs.delta >= 0 ? '+' : ''}{obs.delta.toFixed(2)}
                      </span>
                    </div>
                    <p className="body-text-sm" style={{ color: 'var(--text-secondary)' }}>
                      {obs.summary}
                    </p>
                  </div>
                ))}
              </div>

              <button style={{
                marginTop: 14,
                padding: '6px 14px',
                borderRadius: 6,
                border: '1px solid var(--border)',
                background: 'none',
                color: 'var(--text-dim)',
                fontFamily: 'var(--sans)',
                fontSize: 10,
                letterSpacing: '0.06em',
                textTransform: 'uppercase',
                cursor: 'pointer',
              }}>
                View full history
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
