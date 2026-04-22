import { useState } from 'react'
import { LOGS } from '../data/mockData'
import { motion, AnimatePresence } from 'framer-motion'

const LEVEL_STYLE = {
  info:    { color: 'var(--text-dim)',    dot: '#334155' },
  warning: { color: '#f59e0b',           dot: '#f59e0b' },
  error:   { color: '#f87171',           dot: '#f87171' },
}

export default function LogsWidget() {
  const [tab, setTab] = useState('session')
  const [expanded, setExpanded] = useState(null)

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div className="tab-bar">
        {['session', 'contemplator', 'system'].map(t => (
          <button key={t} className={`tab ${tab === t ? 'active' : ''}`} onClick={() => setTab(t)}>
            {t}
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflowY: 'auto' }}>
        {tab === 'session' && LOGS.session.map(entry => (
          <div key={entry.id} style={{ padding: '10px 18px', borderBottom: '1px solid var(--border)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
              <span style={{ fontFamily: 'var(--sans)', fontSize: 10, color: 'var(--text-dim)', minWidth: 50 }}>
                {entry.timestamp}
              </span>
              <span className={`badge ${entry.routing === 'HELM_PRIME' ? 'badge-blue' : 'badge'}`}>
                T{entry.turn} · {entry.routing}
              </span>
            </div>
            <p className="body-text-sm" style={{ color: 'var(--text-secondary)', marginBottom: 4 }}>
              <span style={{ color: 'var(--text-dim)', fontFamily: 'var(--sans)', fontSize: 10 }}>User: </span>{entry.user}
            </p>
            <p className="body-text-sm">
              <span style={{ color: 'var(--node-primary)', fontFamily: 'var(--sans)', fontSize: 10 }}>Helm: </span>{entry.helm}
            </p>
          </div>
        ))}

        {tab === 'contemplator' && LOGS.contemplator.map(entry => (
          <div key={entry.id} style={{ borderBottom: '1px solid var(--border)' }}>
            <div onClick={() => setExpanded(expanded === entry.id ? null : entry.id)}
              style={{ padding: '12px 18px', cursor: 'pointer', transition: 'background 0.1s' }}
              onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.02)'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                <span style={{ fontFamily: 'var(--sans)', fontSize: 10, color: 'var(--text-dim)' }}>
                  {entry.timestamp}
                </span>
                <span className="badge badge-amber">
                  {(entry.duration_ms / 1000).toFixed(1)}s
                </span>
              </div>
              <p className="body-text-sm">
                {entry.summary}
              </p>
            </div>

            <AnimatePresence>
              {expanded === entry.id && (
                <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }} style={{ padding: '0 18px 16px', borderTop: '1px solid var(--border)' }}>

                  {/* Belief patches */}
                  <p style={{ fontFamily: 'var(--sans)', fontSize: 10, color: 'var(--text-dim)', letterSpacing: '0.08em', textTransform: 'uppercase', marginTop: 14, marginBottom: 8 }}>
                    Belief Patches
                  </p>
                  {entry.belief_patches.map((bp, i) => (
                    <div key={i} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                      <span className="body-text-sm" style={{ color: 'var(--text-secondary)', flex: 1, marginRight: 12 }}>
                        {bp.rationale}
                      </span>
                      <span style={{ fontFamily: 'var(--sans)', fontSize: 11, color: bp.delta >= 0 ? '#4ade80' : '#f59e0b', flexShrink: 0 }}>
                        {bp.delta >= 0 ? '+' : ''}{bp.delta.toFixed(2)}
                      </span>
                    </div>
                  ))}

                  {/* Monologue */}
                  <p style={{ fontFamily: 'var(--sans)', fontSize: 10, color: 'var(--text-dim)', letterSpacing: '0.08em', textTransform: 'uppercase', marginTop: 14, marginBottom: 8 }}>
                    Reflection
                  </p>
                  <div style={{ padding: '12px 14px', background: 'rgba(245,158,11,0.04)', border: '1px solid rgba(245,158,11,0.15)', borderRadius: 6 }}>
                    <p className="body-text-sm" style={{ color: 'var(--text-secondary)', whiteSpace: 'pre-wrap' }}>
                      {entry.monologue}
                    </p>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        ))}

        {tab === 'system' && LOGS.system.map(entry => {
          const ls = LEVEL_STYLE[entry.level] || LEVEL_STYLE.info
          return (
            <div key={entry.id} onClick={() => setExpanded(expanded === entry.id ? null : entry.id)}
              style={{ padding: '8px 18px', borderBottom: '1px solid var(--border)', cursor: 'pointer', transition: 'background 0.1s' }}
              onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.015)'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: ls.dot, flexShrink: 0 }} />
                <span style={{ fontFamily: 'var(--sans)', fontSize: 10, color: 'var(--text-dim)', minWidth: 56 }}>
                  {entry.timestamp}
                </span>
                <p className="body-text-sm" style={{ color: ls.color }}>
                  {entry.message}
                </p>
              </div>
              {expanded === entry.id && entry.detail && (
                <motion.pre initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                  style={{ fontFamily: 'var(--sans)', fontSize: 10, color: 'var(--text-dim)', marginTop: 6, paddingLeft: 16, lineHeight: 1.5, whiteSpace: 'pre-wrap' }}>
                  {entry.detail}
                </motion.pre>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
