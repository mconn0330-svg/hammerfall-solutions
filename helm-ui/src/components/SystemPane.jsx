import { useMemo } from 'react'
import { AGENT_STATUS, LOGS, ACTIVITY } from '../data/mockData'

// ─── System Pane ──────────────────────────────────────────────────────────────
// Operational state at a glance:
//   • Metrics strip — route counts, latency, contemplation tally
//   • Agents grid  — live cards from AGENT_STATUS
//   • System log   — LOGS.system with level-colored rows

const STATUS_CONFIG = {
  ok:       { color: '#4ade80', label: 'online',   glow: 'rgba(74,222,128,0.4)' },
  warning:  { color: '#f59e0b', label: 'degraded', glow: 'rgba(245,158,11,0.4)' },
  error:    { color: '#f87171', label: 'error',    glow: 'rgba(248,113,113,0.4)' },
  inactive: { color: '#334155', label: 'inactive', glow: 'transparent' },
}

const LEVEL_STYLE = {
  info:    { color: 'var(--text-secondary)', dot: '#334155' },
  warning: { color: '#f59e0b',                dot: '#f59e0b' },
  error:   { color: '#f87171',                dot: '#f87171' },
}

function formatLatency(ms) {
  if (ms == null) return '—'
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`
}

export default function SystemPane() {
  const metrics = useMemo(() => computeMetrics(), [])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minWidth: 0 }}>
      {/* Metrics strip */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 18,
        padding: '10px 18px',
        borderBottom: '1px solid var(--border)',
        background: 'rgba(77,184,255,0.03)',
        flexShrink: 0,
        overflowX: 'auto',
      }}>
        <Metric label="Routes"       value={metrics.totalRoutes} />
        <Metric label="→ HELM_PRIME" value={metrics.helmPrime}   accent="#4db8ff" />
        <Metric label="→ LOCAL"      value={metrics.local}       accent="#4ade80" />
        <Metric label="p50 latency"  value={formatLatency(metrics.p50)} />
        <Metric label="Contempl."    value={metrics.contempl}    accent="#f59e0b" />
        <Metric label="Memory ops"   value={metrics.memoryOps}   accent="#a78bfa" />
      </div>

      {/* Scrollable content */}
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {/* Agents grid */}
        <SectionHeader title="Agents" />
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
          gap: 10,
          padding: '0 18px 16px',
        }}>
          {AGENT_STATUS.map(a => <AgentCard key={a.id} agent={a} />)}
        </div>

        {/* System log */}
        <SectionHeader title="System Log" />
        <div style={{ paddingBottom: 12 }}>
          {LOGS.system.map(entry => {
            const ls = LEVEL_STYLE[entry.level] || LEVEL_STYLE.info
            return (
              <div key={entry.id} style={{
                display: 'flex', alignItems: 'flex-start', gap: 10,
                padding: '8px 18px',
                borderBottom: '1px solid rgba(255,255,255,0.04)',
              }}>
                <span style={{
                  width: 6, height: 6, borderRadius: '50%',
                  background: ls.dot,
                  marginTop: 7, flexShrink: 0,
                }} />
                <span style={{
                  fontFamily: 'var(--mono, monospace)', fontSize: 10,
                  color: 'var(--text-dim)',
                  minWidth: 60, flexShrink: 0,
                  paddingTop: 2,
                }}>
                  {entry.timestamp}
                </span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={{
                    fontFamily: 'var(--sans)', fontSize: 12,
                    color: ls.color,
                  }}>
                    {entry.message}
                  </p>
                  {entry.detail && (
                    <pre style={{
                      marginTop: 4,
                      fontFamily: 'var(--mono, monospace)', fontSize: 10,
                      color: 'var(--text-dim)',
                      whiteSpace: 'pre-wrap', wordBreak: 'break-word',
                    }}>
                      {entry.detail}
                    </pre>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

function SectionHeader({ title }) {
  return (
    <div style={{
      padding: '14px 18px 8px',
      fontFamily: 'var(--sans)', fontSize: 10,
      color: 'var(--text-accent)',
      letterSpacing: '0.12em', textTransform: 'uppercase',
    }}>
      {title}
    </div>
  )
}

function Metric({ label, value, accent }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 2, flexShrink: 0 }}>
      <span style={{
        fontFamily: 'var(--sans)', fontSize: 9,
        color: 'var(--text-dim)',
        letterSpacing: '0.1em', textTransform: 'uppercase',
      }}>
        {label}
      </span>
      <span style={{
        fontFamily: 'var(--mono, monospace)', fontSize: 13,
        color: accent || 'var(--text-primary)',
      }}>
        {value}
      </span>
    </div>
  )
}

function AgentCard({ agent }) {
  const sc = STATUS_CONFIG[agent.status] || STATUS_CONFIG.inactive
  const dim = agent.status === 'inactive'
  return (
    <div style={{
      padding: '10px 12px',
      background: 'rgba(255,255,255,0.02)',
      border: '1px solid rgba(255,255,255,0.08)',
      borderRadius: 8,
      opacity: dim ? 0.45 : 1,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
        <span
          className={agent.status === 'ok' ? 'animate-status-pulse' : ''}
          style={{
            width: 7, height: 7, borderRadius: '50%',
            background: sc.color,
            boxShadow: agent.status === 'ok' ? `0 0 6px ${sc.glow}` : 'none',
            flexShrink: 0,
          }}
        />
        <span style={{
          fontFamily: 'var(--sans)', fontSize: 12,
          color: 'var(--text-primary)',
          flex: 1, minWidth: 0,
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }}>
          {agent.name}
        </span>
        <span style={{
          fontFamily: 'var(--sans)', fontSize: 9,
          letterSpacing: '0.08em', textTransform: 'uppercase',
          color: sc.color,
        }}>
          {sc.label}
        </span>
      </div>

      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        fontFamily: 'var(--sans)', fontSize: 10,
        color: 'var(--text-dim)',
      }}>
        <span style={{
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          minWidth: 0, flex: 1,
        }}>
          {agent.model}
        </span>
        {agent.latency_ms != null && (
          <span style={{ color: sc.color, marginLeft: 8, flexShrink: 0 }}>
            {formatLatency(agent.latency_ms)}
          </span>
        )}
      </div>

      {agent.partition && (
        <div style={{
          marginTop: 4,
          fontFamily: 'var(--mono, monospace)', fontSize: 10,
          color: 'var(--text-dim)',
        }}>
          {agent.partition}
        </div>
      )}
    </div>
  )
}

function computeMetrics() {
  const routes    = ACTIVITY.filter(e => e.type === 'routing')
  const helmPrime = routes.filter(r => r.detail?.route === 'HELM_PRIME').length
  const local     = routes.filter(r => r.detail?.route === 'LOCAL').length
  const contempl  = ACTIVITY.filter(e => e.type === 'contemplation').length
  const memoryOps = ACTIVITY.filter(e => e.type === 'memory').length

  // p50 latency across agent/routing/memory events with duration_ms
  const durations = ACTIVITY
    .map(e => e.duration_ms)
    .filter(d => typeof d === 'number')
    .sort((a, b) => a - b)
  const p50 = durations.length
    ? durations[Math.floor(durations.length / 2)]
    : null

  return {
    totalRoutes: routes.length,
    helmPrime,
    local,
    contempl,
    memoryOps,
    p50,
  }
}
