import { useState, useMemo, useRef, useEffect } from 'react'
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

// Time-range presets. `custom` reveals two datetime-local inputs in the popover.
const TIME_PRESETS = [
  { id: 'all',    label: 'All time'      },
  { id: '1h',     label: 'Last hour'     },
  { id: '24h',    label: 'Last 24 hours' },
  { id: 'today',  label: 'Today'         },
  { id: '7d',     label: 'Last 7 days'   },
  { id: 'custom', label: 'Custom range…' },
]

const TIME_PRESET_SHORT = {
  all:    'All time',
  '1h':   '1h',
  '24h':  '24h',
  today:  'Today',
  '7d':   '7d',
  custom: 'Custom',
}

const MONTHS   = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
const WEEKDAYS = ['Su','Mo','Tu','We','Th','Fr','Sa']

function formatDuration(ms) {
  if (ms == null) return null
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`
}

// `datetime-local` format is "YYYY-MM-DDTHH:mm"; we keep that as the canonical
// wire format so it plugs directly into `new Date(...)` in eventInRange.
function parseDtLocal(s) {
  if (!s) return null
  const m = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(s)
  if (!m) return null
  return { year: +m[1], month: +m[2] - 1, day: +m[3], hour: +m[4], minute: +m[5] }
}

function formatDtLocal({ year, month, day, hour, minute }) {
  const pad = n => String(n).padStart(2, '0')
  return `${year}-${pad(month + 1)}-${pad(day)}T${pad(hour)}:${pad(minute)}`
}

function formatDisplay(s) {
  const p = parseDtLocal(s)
  if (!p) return ''
  const pad = n => String(n).padStart(2, '0')
  return `${MONTHS[p.month]} ${p.day}, ${pad(p.hour)}:${pad(p.minute)}`
}

function sameDay(a, b) {
  return a.getFullYear() === b.getFullYear()
      && a.getMonth()    === b.getMonth()
      && a.getDate()     === b.getDate()
}

// Events carry timestamps in two shapes:
//   - "YYYY-MM-DD HH:MM:SS" → parsed as-is (local time)
//   - "HH:MM:SS"            → treated as today at that wall time
// Anything else returns null and is excluded from time-range filtering.
function parseEventTs(ts) {
  if (!ts || typeof ts !== 'string') return null
  if (ts.length >= 10 && ts[4] === '-' && ts[7] === '-') {
    const d = new Date(ts.replace(' ', 'T'))
    return isNaN(d.getTime()) ? null : d
  }
  const parts = ts.split(':')
  if (parts.length < 2) return null
  const [h, m, s] = parts.map(Number)
  if ([h, m].some(Number.isNaN)) return null
  const d = new Date()
  d.setHours(h, m, s || 0, 0)
  return d
}

// Returns true if `event.timestamp` falls within the active time range.
// `customStart` / `customEnd` are `datetime-local` strings (or empty); either
// may be blank to make one side open-ended.
function eventInRange(event, mode, customStart, customEnd, now) {
  if (mode === 'all') return true
  const ts = parseEventTs(event.timestamp)
  if (!ts) return false
  if (mode === '1h')  return (now - ts) <= 60 * 60 * 1000
  if (mode === '24h') return (now - ts) <= 24 * 60 * 60 * 1000
  if (mode === '7d')  return (now - ts) <= 7  * 24 * 60 * 60 * 1000
  if (mode === 'today') {
    const start = new Date(now); start.setHours(0, 0, 0, 0)
    return ts >= start
  }
  if (mode === 'custom') {
    if (customStart) {
      const s = new Date(customStart)
      if (!isNaN(s.getTime()) && ts < s) return false
    }
    if (customEnd) {
      const e = new Date(customEnd)
      if (!isNaN(e.getTime()) && ts > e) return false
    }
    return true
  }
  return true
}

export default function ActivityPane() {
  const [filter, setFilter] = useState('all')
  const [query, setQuery]   = useState('')
  const [expanded, setExpanded] = useState(null)
  const [timeMode,    setTimeMode]    = useState('all')
  const [customStart, setCustomStart] = useState('')
  const [customEnd,   setCustomEnd]   = useState('')

  // Type chip AND search query AND time range. All three are ANDed together;
  // missing/empty values are no-ops. `now` is recomputed per filter pass so
  // relative windows ("last hour") stay accurate across renders.
  const events = useMemo(() => {
    const now = new Date()
    const typed = filter === 'all' ? ACTIVITY : ACTIVITY.filter(e => e.type === filter)
    const timed = timeMode === 'all'
      ? typed
      : typed.filter(e => eventInRange(e, timeMode, customStart, customEnd, now))
    const q = query.trim().toLowerCase()
    if (!q) return timed
    return timed.filter(e => {
      if (e.agent && e.agent.toLowerCase().includes(q)) return true
      if (e.message && e.message.toLowerCase().includes(q)) return true
      if (e.detail != null) {
        const detailStr = typeof e.detail === 'string' ? e.detail : JSON.stringify(e.detail)
        if (detailStr.toLowerCase().includes(q)) return true
      }
      return false
    })
  }, [filter, query, timeMode, customStart, customEnd])

  const timeActive = timeMode !== 'all'

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
          <TimeRangeControl
            mode={timeMode}
            setMode={setTimeMode}
            customStart={customStart}
            setCustomStart={setCustomStart}
            customEnd={customEnd}
            setCustomEnd={setCustomEnd}
            active={timeActive}
          />
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

function TimeRangeControl({
  mode, setMode,
  customStart, setCustomStart,
  customEnd, setCustomEnd,
  active,
}) {
  const [open, setOpen] = useState(false)
  // Which of the two fields (from / to) is currently showing its inline
  // calendar. Only one at a time to keep the popover compact.
  const [expandedField, setExpandedField] = useState(null)
  const rootRef = useRef(null)

  // Close on outside click / Esc while the popover is open.
  useEffect(() => {
    if (!open) return
    const onDown = (e) => { if (rootRef.current && !rootRef.current.contains(e.target)) setOpen(false) }
    const onKey  = (e) => { if (e.key === 'Escape') setOpen(false) }
    window.addEventListener('mousedown', onDown)
    window.addEventListener('keydown',   onKey)
    return () => {
      window.removeEventListener('mousedown', onDown)
      window.removeEventListener('keydown',   onKey)
    }
  }, [open])

  // Collapse any expanded calendar when leaving custom mode or closing.
  useEffect(() => {
    if (!open || mode !== 'custom') setExpandedField(null)
  }, [open, mode])

  const label = active ? TIME_PRESET_SHORT[mode] || 'Custom' : 'Time'

  return (
    <div ref={rootRef} style={{ position: 'relative', flexShrink: 0 }}>
      <button
        onClick={() => setOpen(o => !o)}
        title="Filter by time range"
        style={{
          display: 'flex', alignItems: 'center', gap: 6,
          padding: '4px 8px 4px 8px',
          fontFamily: 'var(--sans)', fontSize: 10,
          letterSpacing: '0.08em', textTransform: 'uppercase',
          background: active ? 'rgba(77,184,255,0.1)' : 'transparent',
          border: active ? '1px solid rgba(77,184,255,0.35)' : '1px solid var(--border)',
          borderRadius: 4,
          color: active ? 'var(--node-primary)' : 'var(--text-secondary)',
          cursor: 'pointer',
        }}
      >
        <svg width="10" height="10" viewBox="0 0 16 16" fill="none" style={{ flexShrink: 0 }}>
          <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.4"/>
          <path d="M8 4.5 V8 L10.5 9.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
        </svg>
        <span>{label}</span>
        <span style={{ fontSize: 8, opacity: 0.6 }}>▾</span>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.12 }}
            style={{
              position: 'absolute',
              top: 'calc(100% + 6px)', right: 0,
              width: mode === 'custom' ? 300 : 220,
              background: 'rgba(10, 15, 24, 0.98)',
              border: '1px solid rgba(77,184,255,0.3)',
              borderRadius: 6,
              boxShadow: '0 8px 28px rgba(0,0,0,0.55), 0 0 0 1px rgba(0,0,0,0.3)',
              backdropFilter: 'blur(16px)',
              padding: '4px 0',
              zIndex: 40,
            }}
          >
            {TIME_PRESETS.map(p => {
              const selected = p.id === mode
              return (
                <button
                  key={p.id}
                  onClick={() => {
                    setMode(p.id)
                    // Non-custom presets close immediately; custom stays open so
                    // the user can pick a range in the same interaction.
                    if (p.id !== 'custom') setOpen(false)
                  }}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 8,
                    width: '100%',
                    padding: '7px 12px',
                    background: selected ? 'rgba(77,184,255,0.1)' : 'transparent',
                    borderTop: 'none', borderRight: 'none', borderBottom: 'none',
                    borderLeft: selected ? '2px solid var(--node-primary)' : '2px solid transparent',
                    color: selected ? 'var(--node-primary)' : 'var(--text-primary)',
                    fontFamily: 'var(--sans)', fontSize: 11,
                    cursor: 'pointer', textAlign: 'left',
                  }}
                  onMouseEnter={e => { if (!selected) e.currentTarget.style.background = 'rgba(255,255,255,0.04)' }}
                  onMouseLeave={e => { if (!selected) e.currentTarget.style.background = 'transparent' }}
                >
                  <span style={{
                    width: 10, display: 'inline-block',
                    color: selected ? 'var(--node-primary)' : 'transparent',
                    fontSize: 10,
                  }}>
                    ✓
                  </span>
                  {p.label}
                </button>
              )
            })}

            {mode === 'custom' && (
              <div style={{
                borderTop: '1px solid var(--border)',
                padding: '10px 12px',
                display: 'flex', flexDirection: 'column', gap: 8,
              }}>
                <GlassDateTimeField
                  label="From"
                  value={customStart}
                  onChange={setCustomStart}
                  expanded={expandedField === 'from'}
                  onToggle={() => setExpandedField(f => f === 'from' ? null : 'from')}
                />
                <GlassDateTimeField
                  label="To"
                  value={customEnd}
                  onChange={setCustomEnd}
                  expanded={expandedField === 'to'}
                  onToggle={() => setExpandedField(f => f === 'to' ? null : 'to')}
                />
                <button
                  onClick={() => { setCustomStart(''); setCustomEnd(''); setExpandedField(null) }}
                  disabled={!customStart && !customEnd}
                  style={{
                    marginTop: 2,
                    padding: '4px 8px',
                    background: 'transparent',
                    border: '1px solid var(--border)',
                    borderRadius: 4,
                    color: 'var(--text-secondary)',
                    fontFamily: 'var(--sans)', fontSize: 10,
                    letterSpacing: '0.08em', textTransform: 'uppercase',
                    cursor: (customStart || customEnd) ? 'pointer' : 'default',
                    opacity: (customStart || customEnd) ? 1 : 0.4,
                  }}
                >
                  Clear range
                </button>
              </div>
            )}

            {active && (
              <div style={{
                borderTop: '1px solid var(--border)',
                padding: '6px 12px',
              }}>
                <button
                  onClick={() => {
                    setMode('all')
                    setCustomStart('')
                    setCustomEnd('')
                    setOpen(false)
                  }}
                  style={{
                    width: '100%',
                    padding: '4px 8px',
                    background: 'transparent',
                    border: '1px solid var(--border)',
                    borderRadius: 4,
                    color: 'var(--text-dim)',
                    fontFamily: 'var(--sans)', fontSize: 10,
                    letterSpacing: '0.08em', textTransform: 'uppercase',
                    cursor: 'pointer',
                  }}
                >
                  Reset
                </button>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// Bounded datetime field styled to match the surrounding glass popover.
// Collapsed state: a button showing the formatted value (or "Any").
// Expanded state: a mini calendar + HH:MM time row — all custom-drawn so we
// never fall back to the browser's native datetime picker.
function GlassDateTimeField({ label, value, onChange, expanded, onToggle }) {
  const parsed = parseDtLocal(value)
  const seed   = parsed || (() => {
    const n = new Date()
    return { year: n.getFullYear(), month: n.getMonth(), day: n.getDate(), hour: n.getHours(), minute: n.getMinutes() }
  })()
  const [viewYear,  setViewYear]  = useState(seed.year)
  const [viewMonth, setViewMonth] = useState(seed.month)

  const update = (patch) => {
    const next = { ...seed, ...patch }
    onChange(formatDtLocal(next))
  }

  const clear = (e) => {
    e.stopPropagation()
    onChange('')
  }

  return (
    <div>
      <div style={{
        fontFamily: 'var(--sans)', fontSize: 9,
        letterSpacing: '0.1em', textTransform: 'uppercase',
        color: 'var(--text-dim)',
        marginBottom: 4,
      }}>
        {label}
      </div>

      <button
        onClick={onToggle}
        style={{
          display: 'flex', alignItems: 'center', gap: 8,
          width: '100%',
          padding: '6px 8px',
          background: expanded ? 'rgba(77,184,255,0.08)' : 'rgba(255,255,255,0.03)',
          border: `1px solid ${expanded ? 'rgba(77,184,255,0.35)' : 'var(--border)'}`,
          borderRadius: 4,
          color: parsed ? 'var(--text-primary)' : 'var(--text-dim)',
          fontFamily: 'var(--mono, monospace)', fontSize: 11,
          cursor: 'pointer', textAlign: 'left',
        }}
      >
        <svg width="11" height="11" viewBox="0 0 16 16" fill="none" style={{ flexShrink: 0, opacity: 0.7 }}>
          <rect x="2" y="3" width="12" height="11" rx="1.5" stroke="currentColor" strokeWidth="1.3"/>
          <path d="M2 6 H14" stroke="currentColor" strokeWidth="1.3"/>
          <path d="M6 2 V4 M10 2 V4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
        </svg>
        <span style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {parsed ? formatDisplay(value) : 'Any'}
        </span>
        {parsed && (
          <span
            onClick={clear}
            title="Clear"
            style={{
              width: 16, height: 16,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: 'var(--text-dim)', fontSize: 12,
              borderRadius: 3,
            }}
            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.08)' }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent' }}
          >
            ×
          </span>
        )}
        <span style={{ fontSize: 8, opacity: 0.6, flexShrink: 0 }}>▾</span>
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.14 }}
            style={{ overflow: 'hidden' }}
          >
            <div style={{
              marginTop: 6,
              padding: 8,
              background: 'rgba(255,255,255,0.02)',
              border: '1px solid var(--border)',
              borderRadius: 4,
            }}>
              <MiniCalendar
                viewYear={viewYear}
                viewMonth={viewMonth}
                setViewYear={setViewYear}
                setViewMonth={setViewMonth}
                selected={parsed ? new Date(parsed.year, parsed.month, parsed.day) : null}
                onSelect={(d) => update({
                  year: d.getFullYear(),
                  month: d.getMonth(),
                  day: d.getDate(),
                })}
              />
              <TimeInputs
                hour={seed.hour}
                minute={seed.minute}
                onChange={(h, m) => update({ hour: h, minute: m })}
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function MiniCalendar({ viewYear, viewMonth, setViewYear, setViewMonth, selected, onSelect }) {
  const today = new Date()
  const first = new Date(viewYear, viewMonth, 1)
  // Roll back to the Sunday that anchors the visible 6-row grid.
  const gridStart = new Date(first)
  gridStart.setDate(first.getDate() - first.getDay())

  const cells = []
  for (let i = 0; i < 42; i++) {
    const d = new Date(gridStart)
    d.setDate(gridStart.getDate() + i)
    cells.push(d)
  }

  const step = (delta) => {
    const m = viewMonth + delta
    if (m < 0)       { setViewMonth(11); setViewYear(viewYear - 1) }
    else if (m > 11) { setViewMonth(0);  setViewYear(viewYear + 1) }
    else             { setViewMonth(m) }
  }

  return (
    <div>
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        marginBottom: 6,
      }}>
        <CalendarNavButton onClick={() => step(-1)} label="◀" />
        <span style={{
          fontFamily: 'var(--sans)', fontSize: 11,
          color: 'var(--text-primary)',
          letterSpacing: '0.04em',
        }}>
          {MONTHS[viewMonth]} {viewYear}
        </span>
        <CalendarNavButton onClick={() => step(1)} label="▶" />
      </div>

      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)',
        gap: 2, marginBottom: 2,
      }}>
        {WEEKDAYS.map(w => (
          <div key={w} style={{
            textAlign: 'center',
            fontFamily: 'var(--sans)', fontSize: 9,
            color: 'var(--text-dim)',
            letterSpacing: '0.06em', textTransform: 'uppercase',
            padding: '2px 0',
          }}>
            {w}
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 2 }}>
        {cells.map((d, i) => {
          const inMonth = d.getMonth() === viewMonth
          const isSel   = selected && sameDay(d, selected)
          const isToday = sameDay(d, today)
          return (
            <button
              key={i}
              onClick={() => onSelect(d)}
              style={{
                padding: '5px 0',
                fontFamily: 'var(--mono, monospace)', fontSize: 10,
                background: isSel ? 'rgba(77,184,255,0.22)' : 'transparent',
                border: isSel
                  ? '1px solid rgba(77,184,255,0.55)'
                  : isToday
                    ? '1px solid rgba(255,255,255,0.18)'
                    : '1px solid transparent',
                borderRadius: 3,
                color: isSel
                  ? 'var(--node-primary)'
                  : inMonth
                    ? 'var(--text-primary)'
                    : 'var(--text-dim)',
                opacity: inMonth ? 1 : 0.45,
                cursor: 'pointer',
                lineHeight: 1,
              }}
              onMouseEnter={e => { if (!isSel) e.currentTarget.style.background = 'rgba(255,255,255,0.05)' }}
              onMouseLeave={e => { if (!isSel) e.currentTarget.style.background = 'transparent' }}
            >
              {d.getDate()}
            </button>
          )
        })}
      </div>
    </div>
  )
}

function CalendarNavButton({ onClick, label }) {
  return (
    <button
      onClick={onClick}
      style={{
        width: 20, height: 20,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: 'transparent',
        border: '1px solid var(--border)',
        borderRadius: 3,
        color: 'var(--text-secondary)',
        fontSize: 8,
        cursor: 'pointer',
      }}
      onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.05)' }}
      onMouseLeave={e => { e.currentTarget.style.background = 'transparent' }}
    >
      {label}
    </button>
  )
}

function TimeInputs({ hour, minute, onChange }) {
  const clamp = (n, lo, hi) => Math.max(lo, Math.min(hi, n))
  const onH = (e) => {
    const v = parseInt(e.target.value, 10)
    if (!Number.isNaN(v)) onChange(clamp(v, 0, 23), minute)
  }
  const onM = (e) => {
    const v = parseInt(e.target.value, 10)
    if (!Number.isNaN(v)) onChange(hour, clamp(v, 0, 59))
  }
  const pad = n => String(n).padStart(2, '0')

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 6,
      marginTop: 8, paddingTop: 8,
      borderTop: '1px solid var(--border)',
    }}>
      <span style={{
        fontFamily: 'var(--sans)', fontSize: 9,
        letterSpacing: '0.1em', textTransform: 'uppercase',
        color: 'var(--text-dim)',
        flexShrink: 0,
      }}>
        Time
      </span>
      <input
        type="number"
        min={0}
        max={23}
        value={pad(hour)}
        onChange={onH}
        style={timeInputStyle}
      />
      <span style={{ color: 'var(--text-dim)', fontSize: 11 }}>:</span>
      <input
        type="number"
        min={0}
        max={59}
        value={pad(minute)}
        onChange={onM}
        style={timeInputStyle}
      />
    </div>
  )
}

const timeInputStyle = {
  width: 42,
  background: 'rgba(255,255,255,0.03)',
  border: '1px solid var(--border)',
  borderRadius: 3,
  color: 'var(--text-primary)',
  fontFamily: 'var(--mono, monospace)', fontSize: 11,
  padding: '3px 6px',
  textAlign: 'center',
  outline: 'none',
  colorScheme: 'dark',
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
