import { useState, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ACTIVITY } from '../data/mockData'

// ─── Activity Pane ────────────────────────────────────────────────────────────
// Unified timeline of what Helm and its agents are doing. Each row carries a
// type badge + optional agent tag + message + latency. Click a row to expand
// its `detail` payload (JSON blob or structured fields).

const FILTERS = [
  { id: 'all',           label: 'All' },
  { id: 'routing',       label: 'Routing' },
  { id: 'contemplation', label: 'Contemplation' },
  { id: 'memory',        label: 'Memory' },
  { id: 'agent',         label: 'Agent' },
  { id: 'system',        label: 'System' },
]

const TYPE_STYLE = {
  routing:       { color: '#4db8ff', label: 'ROUTE'     },
  contemplation: { color: '#f59e0b', label: 'CONTEMPL.' },
  memory:        { color: '#a78bfa', label: 'MEMORY'    },
  agent:         { color: '#4ade80', label: 'AGENT'     },
  system:        { color: '#94a3b8', label: 'SYSTEM'    },
}

const LEVEL_COLOR = {
  info:    'var(--text-secondary)',
  warning: '#f59e0b',
  error:   '#f87171',
}

function formatDuration(ms) {
  if (ms == null) return null
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`
}

export default function ActivityPane() {
  const [filter, setFilter] = useState('all')
  const [query, setQuery]   = useState('')
  const [expanded, setExpanded] = useState(null)

  // Type chip AND search query (case-insensitive substring across agent /
  // message / stringified detail). Empty query is a no-op.
  const events = useMemo(() => {
    const typed = filter === 'all' ? ACTIVITY : ACTIVITY.filter(e => e.type === filter)
    const q = query.trim().toLowerCase()
    if (!q) return typed
    return typed.filter(e => {
      if (e.agent && e.agent.toLowerCase().includes(q)) return true
      if (e.message && e.message.toLowerCase().includes(q)) return true
      if (e.detail != null) {
        const detailStr = typeof e.detail === 'string' ? e.detail : JSON.stringify(e.detail)
        if (detailStr.toLowerCase().includes(q)) return true
      }
      return false
    })
  }, [filter, query])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minWidth: 0 }}>
      {/* Filter bar */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 6,
        padding: '10px 18px',
        borderBottom: '1px solid var(--border)',
        flexShrink: 0,
      }}>
        {FILTERS.map(f => (
          <FilterChip
            key={f.id}
            active={filter === f.id}
            onClick={() => setFilter(f.id)}
          >
            {f.label}
          </FilterChip>
        ))}
        <div style={{
          marginLeft: 'auto',
          display: 'flex', alignItems: 'center', gap: 10,
          minWidth: 0,
        }}>
          <div style={{
            position: 'relative',
            display: 'flex', alignItems: 'center',
          }}>
            <svg width="11" height="11" viewBox="0 0 16 16" fill="none" style={{
              position: 'absolute', left: 8,
              opacity: 0.5, pointerEvents: 'none',
            }}>
              <circle cx="7" cy="7" r="5" stroke="currentColor" strokeWidth="1.4"/>
              <path d="M11 11 L14 14" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
            </svg>
            <input
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="Search activity…"
              spellCheck={false}
              style={{
                width: 180,
                background: 'rgba(255,255,255,0.03)',
                border: '1px solid var(--border)',
                borderRadius: 4,
                color: 'var(--text-primary)',
                fontFamily: 'var(--sans)', fontSize: 11,
                padding: '4px 26px 4px 26px',
                outline: 'none',
              }}
            />
            {query && (
              <button
                onClick={() => setQuery('')}
                title="Clear search"
                style={{
                  position: 'absolute', right: 4,
                  width: 18, height: 18,
                  background: 'transparent', border: 'none',
                  color: 'var(--text-dim)', cursor: 'pointer',
                  fontSize: 12, padding: 0, lineHeight: 1,
                }}
              >
                ×
              </button>
            )}
          </div>
          <span style={{
            fontFamily: 'var(--sans)', fontSize: 10,
            color: 'var(--text-dim)', letterSpacing: '0.08em',
            flexShrink: 0,
          }}>
            {events.length} event{events.length === 1 ? '' : 's'}
          </span>
        </div>
      </div>

      {/* Timeline */}
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {events.length === 0 ? (
          <div style={{
            padding: '36px 18px', textAlign: 'center',
            color: 'var(--text-dim)',
            fontFamily: 'var(--sans)', fontSize: 11,
            letterSpacing: '0.06em',
          }}>
            {query.trim() ? `No events match "${query.trim()}".` : 'No events match this filter.'}
          </div>
        ) : (
          events.map(event => (
            <EventRow
              key={event.id}
              event={event}
              expanded={expanded === event.id}
              onToggle={() => setExpanded(x => x === event.id ? null : event.id)}
            />
          ))
        )}
      </div>
    </div>
  )
}

function FilterChip({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: '4px 10px',
        fontFamily: 'var(--sans)', fontSize: 10,
        letterSpacing: '0.08em', textTransform: 'uppercase',
        background: active ? 'rgba(77,184,255,0.1)' : 'transparent',
        border: active ? '1px solid rgba(77,184,255,0.35)' : '1px solid var(--border)',
        borderRadius: 4,
        color: active ? 'var(--node-primary)' : 'var(--text-secondary)',
        cursor: 'pointer',
      }}
      onMouseEnter={e => { if (!active) e.currentTarget.style.background = 'rgba(255,255,255,0.04)' }}
      onMouseLeave={e => { if (!active) e.currentTarget.style.background = 'transparent' }}
    >
      {children}
    </button>
  )
}

function EventRow({ event, expanded, onToggle }) {
  const ts     = TYPE_STYLE[event.type] || TYPE_STYLE.system
  const hasDetail = event.detail != null
  const messageColor = event.type === 'system' && event.level
    ? LEVEL_COLOR[event.level] || LEVEL_COLOR.info
    : 'var(--text-secondary)'

  return (
    <div
      onClick={hasDetail ? onToggle : undefined}
      style={{
        padding: '9px 18px',
        borderBottom: '1px solid var(--border)',
        cursor: hasDetail ? 'pointer' : 'default',
        transition: 'background 0.1s',
      }}
      onMouseEnter={e => { if (hasDetail) e.currentTarget.style.background = 'rgba(255,255,255,0.02)' }}
      onMouseLeave={e => { e.currentTarget.style.background = 'transparent' }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{
          fontFamily: 'var(--mono, monospace)', fontSize: 10,
          color: 'var(--text-dim)',
          minWidth: 60, flexShrink: 0,
        }}>
          {event.timestamp.length > 8 ? event.timestamp.slice(-8) : event.timestamp}
        </span>

        {/* Type chip */}
        <span style={{
          fontFamily: 'var(--sans)', fontSize: 9,
          letterSpacing: '0.08em',
          padding: '2px 6px',
          borderRadius: 3,
          background: `${ts.color}1a`,
          border: `1px solid ${ts.color}40`,
          color: ts.color,
          flexShrink: 0,
          minWidth: 68, textAlign: 'center',
        }}>
          {ts.label}
        </span>

        {/* Agent tag */}
        {event.agent && (
          <span style={{
            fontFamily: 'var(--sans)', fontSize: 10,
            color: 'var(--text-secondary)',
            flexShrink: 0,
          }}>
            {event.agent}
          </span>
        )}

        <p style={{
          flex: 1, minWidth: 0,
          fontFamily: 'var(--sans)', fontSize: 12,
          color: messageColor,
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }}>
          {event.message}
        </p>

        {event.duration_ms != null && (
          <span style={{
            fontFamily: 'var(--mono, monospace)', fontSize: 10,
            color: 'var(--text-dim)',
            flexShrink: 0,
          }}>
            {formatDuration(event.duration_ms)}
          </span>
        )}

        {hasDetail && (
          <span style={{
            fontSize: 9, color: 'var(--text-dim)',
            flexShrink: 0,
            transform: expanded ? 'rotate(90deg)' : 'rotate(0deg)',
            transition: 'transform 0.15s',
          }}>
            ▸
          </span>
        )}
      </div>

      <AnimatePresence>
        {expanded && hasDetail && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            style={{ overflow: 'hidden' }}
          >
            <DetailBlock detail={event.detail} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function DetailBlock({ detail }) {
  // String payload — render as monospace pre
  if (typeof detail === 'string') {
    return (
      <pre style={{
        marginTop: 8,
        padding: '10px 12px',
        background: 'rgba(255,255,255,0.02)',
        border: '1px solid var(--border)',
        borderRadius: 4,
        fontFamily: 'var(--mono, monospace)', fontSize: 10,
        color: 'var(--text-secondary)',
        whiteSpace: 'pre-wrap', wordBreak: 'break-word',
      }}>
        {detail}
      </pre>
    )
  }

  // Object payload — render key/value list
  return (
    <div style={{
      marginTop: 8,
      padding: '10px 12px',
      background: 'rgba(255,255,255,0.02)',
      border: '1px solid var(--border)',
      borderRadius: 4,
    }}>
      {Object.entries(detail).map(([k, v]) => (
        <div key={k} style={{ display: 'flex', gap: 12, padding: '3px 0' }}>
          <span style={{
            fontFamily: 'var(--sans)', fontSize: 10,
            color: 'var(--text-dim)',
            minWidth: 120, flexShrink: 0,
            letterSpacing: '0.02em',
          }}>
            {k}
          </span>
          <span style={{
            fontFamily: 'var(--mono, monospace)', fontSize: 10,
            color: 'var(--text-secondary)',
            flex: 1, minWidth: 0,
            wordBreak: 'break-word',
          }}>
            {formatValue(v)}
          </span>
        </div>
      ))}
    </div>
  )
}

function formatValue(v) {
  if (v == null) return '—'
  if (Array.isArray(v)) {
    if (v.length === 0) return '[]'
    if (v.every(x => typeof x === 'string' || typeof x === 'number')) {
      return v.join(', ')
    }
    return JSON.stringify(v)
  }
  if (typeof v === 'object') return JSON.stringify(v)
  return String(v)
}
