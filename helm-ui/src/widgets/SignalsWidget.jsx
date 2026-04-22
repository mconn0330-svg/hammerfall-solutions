import { useState } from 'react'
import { SIGNALS } from '../data/mockData'
import { motion } from 'framer-motion'

const PRIORITY_COLOR = {
  high:   { color: '#f87171', bg: 'rgba(248,113,113,0.08)' },
  medium: { color: '#f59e0b', bg: 'rgba(245,158,11,0.08)' },
  low:    { color: '#64748b', bg: 'rgba(100,116,139,0.08)' },
}

const TYPE_LABEL = {
  contradiction: 'Contradiction',
  partial_entity: 'Partial Entity',
  thin_belief: 'Thin Belief',
  novel: 'Novel',
}

export default function SignalsWidget() {
  const [tab, setTab] = useState('observations')
  const [expanded, setExpanded] = useState(null)

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div className="tab-bar">
        <button className={`tab ${tab === 'observations' ? 'active' : ''}`} onClick={() => setTab('observations')}>
          Observations
        </button>
        <button className={`tab ${tab === 'questions' ? 'active' : ''}`} onClick={() => setTab('questions')}>
          Questions
        </button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto' }}>
        {tab === 'observations' && SIGNALS.observations.map(obs => {
          const isExp = expanded === obs.id
          const pct = Math.min((obs.observation_count / obs.graduation_target) * 100, 100)
          const graduated = obs.observation_count >= obs.graduation_target
          return (
            <div key={obs.id} style={{ borderBottom: '1px solid var(--border)' }}>
              <div onClick={() => setExpanded(isExp ? null : obs.id)}
                style={{ padding: '12px 18px', cursor: 'pointer', transition: 'background 0.1s' }}
                onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.02)'}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                  <span style={{ fontFamily: 'var(--sans)', fontSize: 10, color: 'var(--text-dim)', letterSpacing: '0.06em' }}>
                    {obs.slug}
                  </span>
                  <span className={`badge ${graduated ? 'badge-green' : 'badge-blue'}`}>
                    {graduated ? 'graduated' : `${obs.observation_count}/${obs.graduation_target}`}
                  </span>
                </div>
                <p className="body-text-sm" style={{ marginBottom: 8 }}>
                  {obs.statement}
                </p>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <div className="strength-bar-track" style={{ flex: 1 }}>
                    <motion.div className="strength-bar-fill" initial={{ width: 0 }}
                      animate={{ width: `${pct}%` }} transition={{ delay: 0.1, duration: 0.7 }}
                      style={{ background: graduated ? 'linear-gradient(90deg,#4ade80,#86efac)' : undefined }}
                    />
                  </div>
                  <span style={{ fontFamily: 'var(--sans)', fontSize: 10, color: 'var(--text-secondary)', flexShrink: 0 }}>
                    {obs.domain}
                  </span>
                </div>
              </div>
              {isExp && (
                <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}
                  style={{ padding: '0 18px 14px', borderTop: '1px solid var(--border)' }}>
                  <p className="body-text-sm" style={{ color: 'var(--text-secondary)', paddingTop: 12 }}>
                    First observed: {obs.first_seen} · {obs.observation_count} total observations
                  </p>
                  {graduated && (
                    <p className="body-text-sm" style={{ color: '#4ade80', marginTop: 6 }}>
                      ✓ Graduated to belief candidate
                    </p>
                  )}
                </motion.div>
              )}
            </div>
          )
        })}

        {tab === 'questions' && SIGNALS.questions.map(q => {
          const pc = PRIORITY_COLOR[q.priority] || PRIORITY_COLOR.low
          const resolved = q.status === 'resolved'
          return (
            <div key={q.id} onClick={() => setExpanded(expanded === q.id ? null : q.id)}
              style={{
                padding: '12px 18px',
                borderBottom: '1px solid var(--border)',
                cursor: 'pointer',
                opacity: resolved ? 0.5 : 1,
                transition: 'background 0.1s, opacity 0.2s',
              }}
              onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.02)'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
            >
              <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 6 }}>
                <span style={{ fontFamily: 'var(--sans)', fontSize: 10, padding: '2px 8px', borderRadius: 4,
                  color: pc.color, background: pc.bg, border: `1px solid ${pc.color}33`, letterSpacing: '0.06em', textTransform: 'uppercase' }}>
                  {TYPE_LABEL[q.type] || q.type}
                </span>
                {resolved && (
                  <span className="body-text-sm" style={{ color: '#4ade80' }}>✓ Resolved</span>
                )}
              </div>
              <p className="body-text-sm" style={{ marginBottom: 4 }}>
                {q.question}
              </p>
              <span className="body-text-sm" style={{ color: 'var(--text-dim)' }}>
                {q.topic} · {q.created}
              </span>

              {expanded === q.id && q.resolution && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                  style={{ marginTop: 10, padding: '10px 14px', background: 'rgba(74,222,128,0.04)',
                    border: '1px solid rgba(74,222,128,0.15)', borderRadius: 6 }}>
                  <p className="body-text-sm" style={{ color: '#86efac' }}>
                    {q.resolution}
                  </p>
                </motion.div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
