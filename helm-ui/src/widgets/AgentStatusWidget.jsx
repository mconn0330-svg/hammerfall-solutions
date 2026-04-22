import { useState, useEffect } from 'react'
import { AGENT_STATUS } from '../data/mockData'

const STATUS_CONFIG = {
  ok:       { color: '#4ade80', label: 'online',   glow: 'rgba(74,222,128,0.4)' },
  warning:  { color: '#f59e0b', label: 'degraded', glow: 'rgba(245,158,11,0.4)' },
  error:    { color: '#f87171', label: 'error',    glow: 'rgba(248,113,113,0.4)' },
  inactive: { color: '#334155', label: 'inactive', glow: 'transparent' },
}

export default function AgentStatusWidget() {
  const [agents, setAgents] = useState(AGENT_STATUS)
  const [selected, setSelected] = useState(null)
  const [lastPoll, setLastPoll] = useState(new Date())

  // Simulate health poll every 30s
  useEffect(() => {
    const id = setInterval(() => {
      setLastPoll(new Date())
    }, 30000)
    return () => clearInterval(id)
  }, [])

  const agent = selected ? agents.find(a => a.id === selected) : null

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Poll timestamp */}
      <div style={{ padding: '8px 18px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontFamily: 'var(--sans)', fontSize: 10, color: 'var(--text-dim)' }}>
          Last poll: {lastPoll.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
        </span>
        <span style={{ fontFamily: 'var(--sans)', fontSize: 10, color: 'var(--text-dim)' }}>
          30s interval
        </span>
      </div>

      {!selected ? (
        // ── Tile grid ──────────────────────────────────────────────────────
        <div style={{ flex: 1, overflowY: 'auto', padding: 14, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
          {agents.map(a => {
            const sc = STATUS_CONFIG[a.status] || STATUS_CONFIG.inactive
            return (
              <div key={a.id} onClick={() => a.status !== 'inactive' && setSelected(a.id)}
                style={{
                  padding: '12px 14px',
                  background: 'rgba(255,255,255,0.02)',
                  border: `1px solid ${a.status !== 'inactive' ? 'rgba(255,255,255,0.08)' : 'rgba(255,255,255,0.04)'}`,
                  borderRadius: 10,
                  cursor: a.status !== 'inactive' ? 'pointer' : 'default',
                  transition: 'background 0.15s, border-color 0.15s',
                  opacity: a.status === 'inactive' ? 0.45 : 1,
                }}
                onMouseEnter={e => { if (a.status !== 'inactive') e.currentTarget.style.background = 'rgba(255,255,255,0.04)' }}
                onMouseLeave={e => e.currentTarget.style.background = 'rgba(255,255,255,0.02)'}
              >
                {/* Status dot + name */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 6 }}>
                  <span
                    className={a.status === 'ok' ? 'animate-status-pulse' : ''}
                    style={{
                      width: 7, height: 7, borderRadius: '50%',
                      background: sc.color,
                      boxShadow: a.status === 'ok' ? `0 0 6px ${sc.glow}` : 'none',
                      flexShrink: 0,
                    }}
                  />
                  <span style={{ fontSize: 13, color: 'var(--text-primary)', fontWeight: 400 }}>
                    {a.name}
                  </span>
                </div>

                {/* Model */}
                <p style={{ fontFamily: 'var(--sans)', fontSize: 10, color: 'var(--text-dim)', marginBottom: 4, letterSpacing: '0.02em' }}>
                  {a.model}
                </p>

                {/* Latency */}
                {a.latency_ms !== null && (
                  <p style={{ fontFamily: 'var(--sans)', fontSize: 10, color: sc.color }}>
                    {a.latency_ms >= 1000 ? `${(a.latency_ms/1000).toFixed(1)}s` : `${a.latency_ms}ms`}
                  </p>
                )}

                {a.status === 'inactive' && (
                  <p style={{ fontFamily: 'var(--sans)', fontSize: 10, color: 'var(--text-dim)' }}>
                    BA8+
                  </p>
                )}
              </div>
            )
          })}
        </div>
      ) : (
        // ── Agent detail ───────────────────────────────────────────────────
        <div style={{ flex: 1, overflowY: 'auto' }}>
          <button onClick={() => setSelected(null)}
            style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '12px 18px', borderBottom: '1px solid var(--border)', width: '100%', background: 'none', border: 'none', borderBottom: '1px solid var(--border)', color: 'var(--text-secondary)', fontFamily: 'var(--sans)', fontSize: 10, letterSpacing: '0.08em', textTransform: 'uppercase', cursor: 'pointer', textAlign: 'left' }}>
            ← Back
          </button>
          <div style={{ padding: '16px 18px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
              <span style={{
                width: 10, height: 10, borderRadius: '50%',
                background: STATUS_CONFIG[agent.status]?.color,
                boxShadow: `0 0 8px ${STATUS_CONFIG[agent.status]?.glow}`,
                flexShrink: 0,
              }} />
              <h3 style={{ fontSize: 15, color: 'var(--text-primary)', fontWeight: 400, fontFamily: 'var(--sans)' }}>
                {agent.name}
              </h3>
            </div>

            {[
              ['Provider', agent.provider],
              ['Model', agent.model],
              ['Partition', agent.partition || '—'],
              ['Last check', agent.last_check || '—'],
              ['Last invocation', agent.last_invocation || '—'],
              ['Response latency', agent.latency_ms != null ? (agent.latency_ms >= 1000 ? `${(agent.latency_ms/1000).toFixed(1)}s` : `${agent.latency_ms}ms`) : '—'],
              ...(agent.last_deep_pass ? [['Last deep pass', agent.last_deep_pass]] : []),
            ].map(([label, value]) => (
              <div key={label} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                <span className="field-label" style={{ color: 'var(--text-dim)' }}>{label}</span>
                <span className="body-text-sm" style={{ color: 'var(--text-secondary)' }}>{value}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
