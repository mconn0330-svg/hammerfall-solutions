import { useState, useEffect, useRef } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { AGENT_STATUS } from '../data/mockData'

// ─── SYSTEM BAR ───────────────────────────────────────────────────────────────
// Always-visible top bar. Acts as ceiling — no widget spawns beneath it.
// Left zone: helm anchor spacer (64px normal, 114px when node shrunken into bar).
// Pills zone: minimized + pinned-closed widget pills, left of centre.
// Centre: Helm label | system health pill | clock.
// Right: user pill.

export const BAR_HEIGHT = 48

const PILL_W          = 112
const PILL_GAP        = 6
const HELM_SHRUNKEN_W = 114
const CENTER_MIN_W    = 220
const RIGHT_W         = 100
const BAR_H_PAD       = 16

const STATUS_CFG = {
  ok:       { color: '#4ade80', glow: 'rgba(74,222,128,0.45)',  label: 'Nominal'      },
  warning:  { color: '#f59e0b', glow: 'rgba(245,158,11,0.4)',   label: 'Degraded'     },
  error:    { color: '#f87171', glow: 'rgba(248,113,113,0.4)',  label: 'System Error' },
  inactive: { color: '#334155', glow: 'transparent',            label: 'Inactive'     },
}

function computeRollup(agents) {
  const active    = agents.filter(a => a.status !== 'inactive')
  const helmPrime = agents.find(a => a.id === 'a1')
  if (helmPrime?.status !== 'ok' || active.some(a => a.status === 'error')) return 'error'
  if (active.some(a => a.status === 'warning')) return 'warning'
  return 'ok'
}

// ─── Live clock ───────────────────────────────────────────────────────────────
function LocalClock() {
  const [time, setTime] = useState(() => new Date())
  useEffect(() => {
    const id = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(id)
  }, [])
  return (
    <span style={{
      fontFamily: 'var(--sans)', fontSize: 10,
      color: 'rgba(77,184,255,0.38)', letterSpacing: '0.12em', flexShrink: 0,
    }}>
      {time.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
    </span>
  )
}

// ─── Agent popover row ────────────────────────────────────────────────────────
function AgentRow({ agent }) {
  const sc  = STATUS_CFG[agent.status] || STATUS_CFG.inactive
  const lat = agent.latency_ms != null
    ? (agent.latency_ms >= 1000 ? `${(agent.latency_ms / 1000).toFixed(1)}s` : `${agent.latency_ms}ms`)
    : null
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10,
      padding: '7px 14px',
      borderBottom: '1px solid rgba(255,255,255,0.04)',
      opacity: agent.status === 'inactive' ? 0.4 : 1,
    }}>
      <span
        className={agent.status === 'ok' ? 'animate-status-pulse' : ''}
        style={{
          width: 6, height: 6, borderRadius: '50%', flexShrink: 0,
          background: sc.color,
          boxShadow: agent.status === 'ok' ? `0 0 5px ${sc.glow}` : 'none',
        }}
      />
      <span style={{ flex: 1, fontFamily: 'var(--sans)', fontSize: 11, color: 'var(--text-primary)', whiteSpace: 'nowrap' }}>
        {agent.name}
      </span>
      <span style={{ fontFamily: 'var(--sans)', fontSize: 10, color: 'var(--text-dim)', whiteSpace: 'nowrap' }}>
        {agent.model}
      </span>
      {lat && (
        <span style={{ fontFamily: 'var(--sans)', fontSize: 10, color: sc.color, minWidth: 34, textAlign: 'right' }}>
          {lat}
        </span>
      )}
    </div>
  )
}

// ─── Health pill with hover popover ──────────────────────────────────────────
function HealthPill({ agents, onOpenWidget }) {
  const [hovered, setHovered] = useState(false)
  const hideTimer = useRef(null)
  const helmPrime = agents.find(a => a.id === 'a1')
  const rollup    = computeRollup(agents)
  const sc        = STATUS_CFG[rollup]
  const lat = helmPrime?.latency_ms != null
    ? (helmPrime.latency_ms >= 1000
        ? `${(helmPrime.latency_ms / 1000).toFixed(1)}s`
        : `${helmPrime.latency_ms}ms`)
    : null

  const showPopover  = () => { clearTimeout(hideTimer.current); setHovered(true) }
  const scheduleHide = () => { hideTimer.current = setTimeout(() => setHovered(false), 180) }
  useEffect(() => () => clearTimeout(hideTimer.current), [])

  return (
    <div style={{ position: 'relative', flexShrink: 0 }}
      onMouseEnter={showPopover}
      onMouseLeave={scheduleHide}
    >
      <div onClick={onOpenWidget} style={{
        display: 'flex', alignItems: 'center', gap: 7,
        padding: '4px 11px 4px 8px',
        background: hovered ? 'rgba(255,255,255,0.05)' : 'rgba(255,255,255,0.025)',
        border: `1px solid ${hovered ? 'rgba(255,255,255,0.1)' : 'rgba(255,255,255,0.06)'}`,
        borderRadius: 20, cursor: 'pointer',
        transition: 'background 0.15s, border-color 0.15s',
      }}>
        <span
          className={rollup === 'ok' ? 'animate-status-pulse' : ''}
          style={{
            width: 7, height: 7, borderRadius: '50%', flexShrink: 0,
            background: sc.color, boxShadow: `0 0 6px ${sc.glow}`,
          }}
        />
        <span style={{
          fontFamily: 'var(--sans)', fontSize: 10,
          color: 'var(--text-secondary)', letterSpacing: '0.04em', whiteSpace: 'nowrap',
        }}>
          {sc.label}
        </span>
        {lat && (
          <span style={{ fontFamily: 'var(--sans)', fontSize: 9, color: sc.color, opacity: 0.7, whiteSpace: 'nowrap' }}>
            {lat}
          </span>
        )}
      </div>

      {hovered && (
        <div
          onMouseEnter={showPopover}
          onMouseLeave={scheduleHide}
          style={{
            position: 'absolute', top: 'calc(100% + 8px)', left: '50%',
            transform: 'translateX(-50%)', minWidth: 340,
            background: 'rgba(6, 10, 24, 0.96)',
            backdropFilter: 'blur(24px)', WebkitBackdropFilter: 'blur(24px)',
            border: '1px solid rgba(77,184,255,0.12)', borderRadius: 10,
            boxShadow: '0 8px 32px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.04)',
            zIndex: 400, overflow: 'hidden',
          }}
        >
          <div style={{
            padding: '9px 14px', borderBottom: '1px solid rgba(255,255,255,0.06)',
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          }}>
            <span style={{
              fontFamily: 'var(--sans)', fontSize: 10, fontWeight: 500,
              color: 'var(--text-dim)', letterSpacing: '0.12em', textTransform: 'uppercase',
            }}>
              Agent Status
            </span>
            <span style={{ fontFamily: 'var(--sans)', fontSize: 10, color: sc.color, letterSpacing: '0.06em' }}>
              {sc.label}
            </span>
          </div>
          {agents.map(a => <AgentRow key={a.id} agent={a} />)}
          <div style={{ padding: '7px 14px', borderTop: '1px solid rgba(255,255,255,0.04)' }}>
            <span style={{
              fontFamily: 'var(--sans)', fontSize: 9,
              color: 'var(--text-dim)', opacity: 0.55, letterSpacing: '0.06em',
            }}>
              Click to open agent status widget
            </span>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Pin icon ─────────────────────────────────────────────────────────────────
function PinIcon({ pinned }) {
  return (
    <svg width={10} height={10} viewBox="0 0 10 10" fill="none">
      <circle cx={5} cy={3.5} r={2.5}
        fill={pinned ? 'rgba(77,184,255,0.85)' : 'rgba(255,255,255,0.5)'}
        stroke={pinned ? '#4db8ff' : 'rgba(255,255,255,0.25)'}
        strokeWidth={0.8}
      />
      <line x1={5} y1={6} x2={5} y2={9.5}
        stroke={pinned ? '#4db8ff' : 'rgba(255,255,255,0.5)'}
        strokeWidth={1.2} strokeLinecap="round"
      />
    </svg>
  )
}

// ─── Nav pill ────────────────────────────────────────────────────────────────
function NavPill({ id, title, state, pinned, onPillClick, onPinToggle }) {
  const [hovered, setHovered] = useState(false)
  const isClosed = state === 'pinned_closed'

  return (
    <motion.div
      layout="position"
      initial={{ opacity: 0, scale: 0.82 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.82 }}
      transition={{ type: 'spring', stiffness: 400, damping: 30 }}
      style={{ flexShrink: 0, originX: 0 }}
    >
      <div
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        style={{
          display: 'flex', alignItems: 'center', gap: 5,
          width: PILL_W, height: 28,
          paddingLeft: 10, paddingRight: 6,
          background: hovered
            ? 'rgba(77,184,255,0.1)'
            : isClosed ? 'rgba(77,184,255,0.03)' : 'rgba(77,184,255,0.06)',
          border: `1px solid ${
            pinned ? 'rgba(77,184,255,0.38)'
            : hovered ? 'rgba(77,184,255,0.26)'
            : 'rgba(77,184,255,0.13)'}`,
          borderRadius: 14,
          cursor: 'pointer',
          transition: 'background 0.15s, border-color 0.15s',
          opacity: isClosed ? 0.65 : 1,
          userSelect: 'none',
          overflow: 'hidden',
          boxSizing: 'border-box',
        }}
        onClick={() => onPillClick(id, state)}
      >
        {/* State indicator */}
        {isClosed
          ? <span style={{ width: 5, height: 1, background: '#4db8ff', flexShrink: 0, opacity: 0.45 }} />
          : <span style={{ width: 4, height: 4, borderRadius: '50%', background: '#4db8ff', flexShrink: 0, opacity: 0.7 }} />
        }

        <span style={{
          flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          fontFamily: 'var(--sans)', fontSize: 10,
          color: isClosed ? 'rgba(77,184,255,0.55)' : '#7dd4fc',
          letterSpacing: '0.07em', textTransform: 'uppercase',
        }}>
          {title}
        </span>

        {/* Pin toggle — always visible if pinned, else on hover */}
        <div
          onClick={(e) => { e.stopPropagation(); onPinToggle(id) }}
          style={{
            flexShrink: 0, width: 18, height: 18,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            opacity: (hovered || pinned) ? 1 : 0,
            transition: 'opacity 0.12s',
            cursor: 'pointer',
            borderRadius: 4,
            background: hovered ? 'rgba(77,184,255,0.14)' : 'transparent',
            pointerEvents: (hovered || pinned) ? 'auto' : 'none',
          }}
        >
          <PinIcon pinned={pinned} />
        </div>
      </div>
    </motion.div>
  )
}

// ─── SystemBar ────────────────────────────────────────────────────────────────
export default function SystemBar({
  onOpenWidget,
  pills = [],
  onPillClick,
  onPinToggle,
  nodeShrunken = false,
  vpW = window.innerWidth,
}) {
  // Compute how many pill slots fit between the left anchor and the centre
  const leftW      = nodeShrunken ? HELM_SHRUNKEN_W : 64
  const pillsMax   = Math.max(0, vpW - BAR_H_PAD * 2 - leftW - CENTER_MIN_W - RIGHT_W)
  const maxSlots   = Math.max(0, Math.floor((pillsMax + PILL_GAP) / (PILL_W + PILL_GAP)))

  const pinnedPills   = pills.filter(p => p.pinned)
  const unpinnedPills = pills.filter(p => !p.pinned)
  const extraSlots    = Math.max(0, maxSlots - pinnedPills.length)
  const visiblePills  = [...pinnedPills, ...unpinnedPills.slice(0, extraSlots)]
  const droppedCount  = unpinnedPills.length - Math.min(unpinnedPills.length, extraSlots)

  // Warning flash when a new pill can't be shown (all slots taken by pinned pills)
  const [warn, setWarn] = useState(false)
  const prevCountRef = useRef(pills.length)
  useEffect(() => {
    if (pills.length > prevCountRef.current && droppedCount > 0) {
      setWarn(true)
      const t = setTimeout(() => setWarn(false), 2200)
      prevCountRef.current = pills.length
      return () => clearTimeout(t)
    }
    prevCountRef.current = pills.length
  }, [pills.length, droppedCount])

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0,
      height: BAR_HEIGHT,
      zIndex: 300,
      background: 'rgba(4, 8, 20, 0.90)',
      backdropFilter:       'blur(20px)',
      WebkitBackdropFilter: 'blur(20px)',
      borderBottom: '1px solid rgba(77,184,255,0.07)',
      display: 'flex', alignItems: 'center',
      padding: `0 ${BAR_H_PAD}px`,
      userSelect: 'none',
    }}>

      {/* LEFT — spacer for helm node anchor; widens when node shrunken into bar */}
      <div style={{
        width: nodeShrunken ? HELM_SHRUNKEN_W : 64,
        flexShrink: 0,
        transition: 'width 0.25s ease-out',
      }} />

      {/* PILLS ZONE — minimized + pinned-closed widget pills */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: PILL_GAP,
        flexShrink: 0, overflow: 'hidden',
        maxWidth: Math.max(0, pillsMax),
      }}>
        <AnimatePresence mode="popLayout">
          {visiblePills.map(pill => (
            <NavPill
              key={pill.id}
              {...pill}
              onPillClick={onPillClick ?? (() => {})}
              onPinToggle={onPinToggle ?? (() => {})}
            />
          ))}
        </AnimatePresence>
      </div>

      {/* CENTRE — Helm label | health pill | clock */}
      <div style={{
        flex: 1, minWidth: CENTER_MIN_W,
        display: 'flex', alignItems: 'center',
        justifyContent: 'center', gap: 12,
      }}>
        <span style={{
          fontFamily: 'var(--sans)', fontSize: 11, fontWeight: 500,
          color: '#4db8ff', letterSpacing: '0.22em',
          textTransform: 'uppercase', opacity: 0.72, flexShrink: 0,
        }}>
          Helm
        </span>

        <div style={{ width: 1, height: 14, background: 'rgba(77,184,255,0.12)', flexShrink: 0 }} />

        <HealthPill agents={AGENT_STATUS} onOpenWidget={() => onOpenWidget?.('agent_status')} />

        <div style={{ width: 1, height: 14, background: 'rgba(77,184,255,0.12)', flexShrink: 0 }} />

        <LocalClock />
      </div>

      {/* RIGHT — user pill */}
      <div style={{ width: RIGHT_W, flexShrink: 0, display: 'flex', justifyContent: 'flex-end' }}>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 7,
          padding: '4px 10px 4px 5px',
          background: 'rgba(77,184,255,0.05)',
          border: '1px solid rgba(77,184,255,0.14)',
          borderRadius: 20, cursor: 'pointer',
        }}>
          <div style={{
            width: 22, height: 22, borderRadius: '50%',
            background: 'rgba(77,184,255,0.16)',
            border: '1px solid rgba(77,184,255,0.28)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontFamily: 'var(--sans)', fontSize: 9, fontWeight: 600,
            color: '#7dd4fc', flexShrink: 0,
          }}>M</div>
          <span style={{ fontFamily: 'var(--sans)', fontSize: 11, color: '#7dd4fc', letterSpacing: '0.04em' }}>
            Max
          </span>
        </div>
      </div>

      {/* WARNING TOAST — below bar, auto-clears after 2.2s */}
      <AnimatePresence>
        {warn && (
          <motion.div
            key="pill-warn"
            initial={{ opacity: 0, y: -6, x: '-50%' }}
            animate={{ opacity: 1, y: 0,  x: '-50%' }}
            exit={{    opacity: 0, y: -6, x: '-50%' }}
            transition={{ duration: 0.18 }}
            style={{
              position: 'absolute', top: BAR_HEIGHT + 8, left: '50%',
              background: 'rgba(245,158,11,0.14)',
              border: '1px solid rgba(245,158,11,0.38)',
              borderRadius: 8, padding: '5px 14px',
              fontFamily: 'var(--sans)', fontSize: 10,
              color: '#f59e0b', letterSpacing: '0.06em', whiteSpace: 'nowrap',
              zIndex: 400, pointerEvents: 'none',
            }}
          >
            All pill slots are pinned — widget minimized but not shown in bar
          </motion.div>
        )}
      </AnimatePresence>

    </div>
  )
}
