import { useState, useRef, useEffect, useCallback } from 'react'
import { CHAT_HISTORY } from '../data/mockData'
import { WIDGET_DEFS } from '../widgets/registry'
import ActivityPane from './ActivityPane'
import SystemPane   from './SystemPane'
import {
  buildSlashCommands, parseSlashInput, getSuggestions, applySuggestion,
} from '../commands/slashCommands'

// ─── Helm Console ─────────────────────────────────────────────────────────────
// Persistent drawer that can dock bottom / left / right.
// Three states: collapsed (thin bar), standard (resizable), fullscreen.
// Contains the Chat/Activity/System tabs on the main pane and a collapsible
// Docked-Widgets pane on the opposite side (scaffold only — PR 3 wires docking).

const TABS = [
  { id: 'chat',     label: 'Chat',     enabled: true },
  { id: 'activity', label: 'Activity', enabled: true },
  { id: 'system',   label: 'System',   enabled: true },
]

const SESSION_KEY = 'helm-session-id'
const DOCK_PANE_MIN_PX  = 200
const DOCK_PANE_MAX_FRAC = 0.55   // cap dock pane at this fraction of drawer width

function getOrCreateSessionId() {
  try {
    const existing = localStorage.getItem(SESSION_KEY)
    if (existing) return existing
    const fresh = `sess_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`
    localStorage.setItem(SESSION_KEY, fresh)
    return fresh
  } catch {
    return `sess_${Date.now().toString(36)}`
  }
}

export default function Console({
  state,
  position,           // 'bottom' | 'left' | 'right'
  sizePct,
  minPct,
  maxPct,
  collapsedPx,
  barHeight,
  dockPaneOpen,
  dockPaneWidth = 280,
  dockedWidgets = [],
  onResize,
  onStateChange,
  onPositionChange,
  onReset,
  onDockPaneToggle,
  onDockPaneResize,
  onUndockWidget,
  onNodeStateChange,
  onOpenWidget,
  onDockWidget,
  onPinWidget,
  activeTab,
  onTabChange,
  vpW,
  vpH,
}) {
  const setActiveTab = onTabChange
  const [sessionId] = useState(() => getOrCreateSessionId())

  // ── Drawer geometry for current position/state ───────────────────────────
  const isHorizontal = position === 'bottom'
  const axisPx       = isHorizontal ? vpH : vpW

  const drawerStyle = (() => {
    if (state === 'fullscreen') {
      return { left: 0, right: 0, top: barHeight, bottom: 0 }
    }
    const extent = state === 'collapsed'
      ? collapsedPx
      : Math.round(sizePct * axisPx)

    if (position === 'bottom') {
      return { left: 0, right: 0, bottom: 0, height: extent }
    }
    if (position === 'left') {
      return { left: 0, top: barHeight, bottom: 0, width: extent }
    }
    // right
    return { right: 0, top: barHeight, bottom: 0, width: extent }
  })()

  // ── Resize handle (with snap-to-fullscreen / snap-to-collapsed) ──────────
  // Dragging past SNAP_FULL past maxPct → fullscreen. Below SNAP_COLL under
  // minPct → collapsed. Otherwise clamp-and-resize within [min, max].
  const SNAP_FULL_DELTA = 0.05   // pct beyond maxPct that triggers fullscreen
  const SNAP_COLL_DELTA = 0.06   // pct below minPct that triggers collapse
  const resizingRef = useRef(false)
  const onResizeMouseDown = useCallback((e) => {
    if (state !== 'standard') return
    e.preventDefault()
    resizingRef.current = true

    const cleanup = () => {
      resizingRef.current = false
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup',   onUp)
    }

    const onMove = (ev) => {
      if (!resizingRef.current) return
      let pct
      if (position === 'bottom') pct = (vpH - ev.clientY) / vpH
      else if (position === 'left')  pct = ev.clientX / vpW
      else                           pct = (vpW - ev.clientX) / vpW

      if (pct > maxPct + SNAP_FULL_DELTA) {
        onStateChange?.('fullscreen')
        cleanup()
        return
      }
      if (pct < minPct - SNAP_COLL_DELTA) {
        onStateChange?.('collapsed')
        cleanup()
        return
      }
      const clamped = Math.max(minPct, Math.min(maxPct, pct))
      onResize?.(clamped)
    }
    const onUp = () => cleanup()

    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup',   onUp)
  }, [state, position, vpW, vpH, minPct, maxPct, onResize, onStateChange])

  const resizeHandleStyle = (() => {
    const common = { position: 'absolute', zIndex: 2 }
    if (position === 'bottom') return { ...common, top: -3, left: 0, right: 0, height: 6, cursor: 'ns-resize' }
    if (position === 'left')   return { ...common, right: -3, top: 0, bottom: 0, width: 6, cursor: 'ew-resize' }
    return { ...common, left: -3, top: 0, bottom: 0, width: 6, cursor: 'ew-resize' }
  })()

  // ── Toggles ───────────────────────────────────────────────────────────────
  const toggleCollapse   = () => onStateChange?.(state === 'collapsed'  ? 'standard' : 'collapsed')
  const toggleFullscreen = () => onStateChange?.(state === 'fullscreen' ? 'standard' : 'fullscreen')

  // Body is hidden in collapsed state
  const showBody = state !== 'collapsed'

  // Dock pane width when visible (not applicable in collapsed/fullscreen-empty states)
  const showDockPane = dockPaneOpen && showBody

  // Drawer pixel width along the dock-pane axis. Dock pane sits inside the body
  // flex-row, so its cap depends on how wide the drawer actually is right now.
  const drawerWidthPx = state === 'fullscreen'
    ? vpW
    : (isHorizontal ? vpW : Math.round(sizePct * vpW))
  const dockPaneMaxPx = Math.max(DOCK_PANE_MIN_PX, Math.floor(drawerWidthPx * DOCK_PANE_MAX_FRAC))
  const dockPaneRenderPx = Math.max(DOCK_PANE_MIN_PX, Math.min(dockPaneMaxPx, dockPaneWidth))

  const drawerShell = {
    position: 'fixed',
    ...drawerStyle,
    zIndex: 300,
    background: 'rgba(8, 12, 20, 0.96)',
    borderTop:    position === 'bottom' ? '1px solid var(--border)' : undefined,
    borderRight:  position === 'left'   ? '1px solid var(--border)' : undefined,
    borderLeft:   position === 'right'  ? '1px solid var(--border)' : undefined,
    boxShadow:
      position === 'bottom' ? '0 -8px 32px rgba(0,0,0,0.45)' :
      position === 'left'   ? ' 8px 0 32px rgba(0,0,0,0.45)' :
                              '-8px 0 32px rgba(0,0,0,0.45)',
    display: 'flex', flexDirection: 'column',
    backdropFilter: 'blur(14px)',
  }

  // ── Collapsed + left/right: render a vertical strip instead of the
  // horizontal header (which doesn't fit in a 36px-wide column).
  if (state === 'collapsed' && !isHorizontal) {
    return (
      <div style={drawerShell}>
        <CollapsedVerticalStrip
          position={position}
          onExpand={toggleCollapse}
          onPositionChange={onPositionChange}
        />
      </div>
    )
  }

  return (
    <div style={drawerShell}>
      {/* Resize handle — only in standard state */}
      {state === 'standard' && (
        <div onMouseDown={onResizeMouseDown} style={resizeHandleStyle} title="Drag to resize" />
      )}

      {/* Header */}
      <ConsoleHeader
        state={state}
        position={position}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        onCollapseToggle={toggleCollapse}
        onFullscreenToggle={toggleFullscreen}
        onPositionChange={onPositionChange}
        onReset={onReset}
        onDockPaneToggle={onDockPaneToggle}
        dockPaneOpen={dockPaneOpen}
        sessionId={sessionId}
      />

      {/* Body */}
      {showBody && (
        <div style={{ flex: 1, overflow: 'hidden', display: 'flex', minHeight: 0 }}>
          <div style={{ flex: 1, minWidth: 0, display: 'flex' }}>
            {activeTab === 'chat'     && (
              <ChatPane
                onNodeStateChange={onNodeStateChange}
                onOpenWidget={onOpenWidget}
                onDockWidget={onDockWidget}
                onUndockWidget={onUndockWidget}
                onPinWidget={onPinWidget}
                onSwitchTab={setActiveTab}
              />
            )}
            {activeTab === 'activity' && <ActivityPane />}
            {activeTab === 'system'   && <SystemPane />}
          </div>

          {showDockPane && (
            <DockPane
              width={dockPaneRenderPx}
              minWidth={DOCK_PANE_MIN_PX}
              maxWidth={dockPaneMaxPx}
              onResize={onDockPaneResize}
              dockedWidgets={dockedWidgets}
              onUndock={onUndockWidget}
              onClose={onDockPaneToggle}
            />
          )}
        </div>
      )}
    </div>
  )
}

// ─── Vertical strip for collapsed state when docked left/right ────────────────
function CollapsedVerticalStrip({ position, onExpand, onPositionChange }) {
  const arrow = position === 'left' ? '▶' : '◀'
  return (
    <div style={{
      flex: 1,
      display: 'flex', flexDirection: 'column',
      alignItems: 'center',
      padding: '8px 0',
      gap: 10,
    }}>
      {/* Expand button — primary affordance */}
      <button
        onClick={onExpand}
        title="Expand Console"
        style={{
          width: 24, height: 24,
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
          background: 'rgba(77,184,255,0.10)',
          border: '1px solid rgba(77,184,255,0.35)',
          borderRadius: 4,
          color: 'var(--node-primary)',
          fontSize: 11, cursor: 'pointer',
        }}
      >
        {arrow}
      </button>

      {/* Rotated CONSOLE label — vertical reading */}
      <div style={{
        writingMode: 'vertical-rl',
        transform: 'rotate(180deg)',
        fontFamily: 'var(--sans)', fontSize: 10,
        color: 'var(--text-accent)',
        letterSpacing: '0.22em', textTransform: 'uppercase',
        marginTop: 8,
      }}>
        Console
      </div>

      {/* Reposition — move drawer to bottom so horizontal controls work */}
      <button
        onClick={() => onPositionChange?.('bottom')}
        title="Dock bottom"
        style={{
          marginTop: 'auto',
          width: 22, height: 22,
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
          background: 'transparent',
          border: '1px solid var(--border)',
          borderRadius: 4,
          color: 'var(--text-secondary)',
          fontSize: 11, cursor: 'pointer',
        }}
      >
        ⬓
      </button>
    </div>
  )
}

// ─── Header ───────────────────────────────────────────────────────────────────
function ConsoleHeader({
  state, position, activeTab, onTabChange,
  onCollapseToggle, onFullscreenToggle, onPositionChange, onReset,
  onDockPaneToggle, dockPaneOpen, sessionId,
}) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center',
      height: 36, flexShrink: 0,
      padding: '0 14px',
      borderBottom: state === 'collapsed' ? 'none' : '1px solid var(--border)',
      gap: 10,
    }}>
      <span style={{
        fontFamily: 'var(--sans)', fontSize: 10,
        color: 'var(--text-accent)',
        letterSpacing: '0.14em', textTransform: 'uppercase',
        flexShrink: 0,
      }}>
        Console
      </span>

      {state !== 'collapsed' && (
        <div style={{ display: 'flex', gap: 2, marginLeft: 6 }}>
          {TABS.map(t => (
            <button
              key={t.id}
              onClick={() => t.enabled && onTabChange(t.id)}
              disabled={!t.enabled}
              style={{
                padding: '4px 10px',
                fontFamily: 'var(--sans)', fontSize: 10,
                letterSpacing: '0.08em', textTransform: 'uppercase',
                background: activeTab === t.id ? 'rgba(77,184,255,0.1)' : 'transparent',
                border: activeTab === t.id
                  ? '1px solid rgba(77,184,255,0.35)'
                  : '1px solid transparent',
                borderRadius: 4,
                color: !t.enabled ? 'var(--text-dim)' :
                       activeTab === t.id ? 'var(--node-primary)' : 'var(--text-secondary)',
                cursor: t.enabled ? 'pointer' : 'not-allowed',
                opacity: t.enabled ? 1 : 0.5,
              }}
            >
              {t.label}{!t.enabled && ' ·'}
            </button>
          ))}
        </div>
      )}

      <span style={{
        fontFamily: 'var(--mono, monospace)', fontSize: 10,
        color: 'var(--text-dim)',
        marginLeft: 'auto',
        minWidth: 0,
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
      }}>
        {sessionId}
      </span>

      {/* Controls */}
      <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
        {state !== 'collapsed' && (
          <PositionToggle position={position} onChange={onPositionChange} onReset={onReset} />
        )}
        {state !== 'collapsed' && (
          <IconButton
            title={dockPaneOpen ? 'Hide dock pane' : 'Show dock pane'}
            onClick={onDockPaneToggle}
            active={dockPaneOpen}
          >
            ▦
          </IconButton>
        )}
        <IconButton
          title={state === 'fullscreen' ? 'Restore' : 'Fullscreen'}
          onClick={onFullscreenToggle}
        >
          {state === 'fullscreen' ? '▢' : '▣'}
        </IconButton>
        <IconButton
          title={state === 'collapsed' ? 'Expand' : 'Collapse'}
          onClick={onCollapseToggle}
        >
          {collapseGlyph(state, position)}
        </IconButton>
      </div>
    </div>
  )
}

function collapseGlyph(state, position) {
  if (state === 'collapsed') {
    if (position === 'bottom') return '▲'
    if (position === 'left')   return '▶'
    return '◀'
  }
  if (position === 'bottom') return '▼'
  if (position === 'left')   return '◀'
  return '▶'
}

function PositionToggle({ position, onChange, onReset }) {
  const opts = [
    { id: 'left',   label: '◧', title: 'Dock left'   },
    { id: 'bottom', label: '⬓', title: 'Dock bottom' },
    { id: 'right',  label: '◨', title: 'Dock right'  },
  ]
  return (
    <div style={{
      display: 'inline-flex',
      border: '1px solid var(--border)',
      borderRadius: 4,
      overflow: 'hidden',
    }}>
      {opts.map(o => (
        <button
          key={o.id}
          onClick={() => onChange?.(o.id)}
          title={o.title}
          style={{
            width: 22, height: 22,
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            background: position === o.id ? 'rgba(77,184,255,0.12)' : 'transparent',
            border: 'none',
            color: position === o.id ? 'var(--node-primary)' : 'var(--text-secondary)',
            fontSize: 11,
            cursor: 'pointer',
          }}
        >
          {o.label}
        </button>
      ))}
      <button
        onClick={() => onReset?.()}
        title="Reset to default size"
        style={{
          width: 22, height: 22,
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
          background: 'transparent',
          border: 'none',
          borderLeft: '1px solid var(--border)',
          color: 'var(--text-secondary)',
          fontSize: 12,
          cursor: 'pointer',
        }}
      >
        ↺
      </button>
    </div>
  )
}

function IconButton({ children, onClick, title, active }) {
  return (
    <button
      onClick={onClick}
      title={title}
      style={{
        width: 24, height: 24,
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        background: active ? 'rgba(77,184,255,0.12)' : 'transparent',
        border: '1px solid var(--border)',
        borderRadius: 4,
        color: active ? 'var(--node-primary)' : 'var(--text-secondary)',
        fontSize: 11, fontFamily: 'var(--sans)',
        cursor: 'pointer',
      }}
      onMouseEnter={e => { if (!active) e.currentTarget.style.background = 'rgba(255,255,255,0.04)' }}
      onMouseLeave={e => { if (!active) e.currentTarget.style.background = 'transparent' }}
    >
      {children}
    </button>
  )
}

// ─── Dock pane ─────────────────────────────────────────────────────────────────
// Renders widget cards for every id in `dockedWidgets`. Each card is a compact
// container showing the widget's live component body, with an "undock" button
// that returns the widget to the canvas.
function DockPane({ width, minWidth, maxWidth, onResize, dockedWidgets, onUndock, onClose }) {
  const paneRef = useRef(null)
  const onHandleMouseDown = useCallback((e) => {
    e.preventDefault()
    const rect = paneRef.current?.getBoundingClientRect()
    if (!rect) return
    // Drawer's right edge is fixed; we derive width from mouseX relative to it.
    const rightEdge = rect.right
    const onMove = (ev) => {
      const next = rightEdge - ev.clientX
      const clamped = Math.max(minWidth, Math.min(maxWidth, next))
      onResize?.(clamped)
    }
    const onUp = () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup',   onUp)
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup',   onUp)
  }, [minWidth, maxWidth, onResize])

  return (
    <div ref={paneRef} style={{
      width, flexShrink: 0,
      position: 'relative',
      display: 'flex', flexDirection: 'column',
      borderLeft: '1px solid var(--border)',
      background: 'rgba(255,255,255,0.015)',
    }}>
      {/* Drag handle — sits over the left border */}
      <div
        onMouseDown={onHandleMouseDown}
        title="Drag to resize"
        style={{
          position: 'absolute',
          left: -3, top: 0, bottom: 0, width: 6,
          cursor: 'ew-resize',
          zIndex: 2,
        }}
      />
      <div style={{
        display: 'flex', alignItems: 'center',
        padding: '8px 12px',
        borderBottom: '1px solid var(--border)',
        flexShrink: 0,
      }}>
        <span style={{
          fontFamily: 'var(--sans)', fontSize: 10,
          color: 'var(--text-dim)',
          letterSpacing: '0.1em', textTransform: 'uppercase',
        }}>
          Docked Widgets
        </span>
        <button
          onClick={onClose}
          title="Close pane"
          style={{
            marginLeft: 'auto',
            width: 18, height: 18,
            background: 'transparent', border: 'none',
            color: 'var(--text-dim)', cursor: 'pointer',
            fontSize: 11,
          }}
        >
          ×
        </button>
      </div>
      <div style={{
        flex: 1, overflowY: 'auto',
        padding: 12,
        display: 'flex', flexDirection: 'column', gap: 10,
      }}>
        {dockedWidgets.length === 0 ? (
          <div style={{
            padding: '24px 12px', textAlign: 'center',
            border: '1px dashed var(--border)',
            borderRadius: 6,
            color: 'var(--text-dim)',
            fontFamily: 'var(--sans)', fontSize: 10,
            letterSpacing: '0.06em',
          }}>
            No widgets docked<br/>
            <span style={{ color: 'var(--text-dim)', opacity: 0.6 }}>
              Dock a widget from its header
            </span>
          </div>
        ) : (
          dockedWidgets.map(id => {
            const def = WIDGET_DEFS[id]
            if (!def) return null
            const { title, Component } = def
            return (
              <DockedWidgetCard key={id} title={title} onUndock={() => onUndock?.(id)}>
                <Component />
              </DockedWidgetCard>
            )
          })
        )}
      </div>
    </div>
  )
}

function DockedWidgetCard({ title, onUndock, children }) {
  const [collapsed, setCollapsed] = useState(false)
  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      background: 'rgba(255,255,255,0.02)',
      border: '1px solid var(--border)',
      borderRadius: 6,
      overflow: 'hidden',
    }}>
      <div style={{
        display: 'flex', alignItems: 'center',
        padding: '6px 8px',
        borderBottom: collapsed ? 'none' : '1px solid var(--border)',
        gap: 6,
      }}>
        <button
          onClick={() => setCollapsed(c => !c)}
          title={collapsed ? 'Expand' : 'Collapse'}
          style={{
            width: 16, height: 16,
            background: 'transparent', border: 'none',
            color: 'var(--text-dim)', cursor: 'pointer',
            fontSize: 10, padding: 0, lineHeight: 1,
          }}
        >
          {collapsed ? '▸' : '▾'}
        </button>
        <span style={{
          flex: 1, minWidth: 0,
          fontFamily: 'var(--sans)', fontSize: 10,
          color: 'var(--text-secondary)',
          letterSpacing: '0.08em', textTransform: 'uppercase',
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }}>
          {title}
        </span>
        <button
          onClick={onUndock}
          title="Undock to canvas"
          style={{
            width: 18, height: 18,
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            background: 'transparent',
            border: '1px solid var(--border)',
            borderRadius: 3,
            color: 'var(--text-dim)', cursor: 'pointer',
            fontSize: 10, padding: 0,
          }}
        >
          ⇱
        </button>
      </div>
      {!collapsed && (
        <div style={{
          maxHeight: 260,
          overflow: 'auto',
          padding: 8,
        }}>
          {children}
        </div>
      )}
    </div>
  )
}

// ─── Chat pane (ported from ChatWidget) ───────────────────────────────────────
function ChatPane({
  onNodeStateChange,
  onOpenWidget,
  onDockWidget,
  onUndockWidget,
  onPinWidget,
  onSwitchTab,
}) {
  const [messages, setMessages] = useState(CHAT_HISTORY)
  const [input, setInput] = useState('')
  const [holdProgress, setHoldProgress] = useState(0)
  const [isHolding, setIsHolding] = useState(false)
  const [contemplating, setContemplating] = useState(false)
  const [selectedIdx, setSelectedIdx] = useState(0)
  const holdStartRef = useRef(null)
  const holdRafRef   = useRef(null)
  const bottomRef    = useRef(null)
  const textareaRef  = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const startHold = () => {
    if (contemplating) return
    setIsHolding(true)
    holdStartRef.current = Date.now()
    const tick = () => {
      const elapsed = Date.now() - holdStartRef.current
      const p = Math.min(elapsed / 1500, 1)
      setHoldProgress(p)
      if (p < 1) holdRafRef.current = requestAnimationFrame(tick)
      else triggerContemplate()
    }
    holdRafRef.current = requestAnimationFrame(tick)
  }

  const endHold = () => {
    setIsHolding(false)
    setHoldProgress(0)
    if (holdRafRef.current) cancelAnimationFrame(holdRafRef.current)
  }

  const triggerContemplate = () => {
    setIsHolding(false)
    setHoldProgress(0)
    setContemplating(true)
    onNodeStateChange?.('contemplating')

    setMessages(prev => [...prev, {
      id: Date.now(),
      role: 'helm',
      content: 'Thinking.',
      timestamp: new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }),
      routing: 'HELM_PRIME',
      isContemplating: true,
    }])

    setTimeout(() => {
      setContemplating(false)
      onNodeStateChange?.('idle')
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        role: 'helm',
        content: "Deep pass complete. Two observations worth noting:\n\nFirst, the pattern-synthesis pass flagged a growing tension between small-PR preference and the BA3 bundle decision. I've logged it as a curiosity flag for next session — the resolution you gave me was partial.\n\nSecond, I updated the cost-asymmetry-routing belief by +0.10. The imperative-directive regression was the clearest evidence yet for that principle. It's now at 0.85.",
        timestamp: new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }),
        routing: 'HELM_PRIME',
      }])
    }, 4000)
  }

  // ── Slash commands ────────────────────────────────────────────────────────
  // emit — append a helm reply; clear — wipe the visible history; commands are
  // rebuilt whenever a handler ref changes. Parsing + suggestion state drives
  // the autocomplete popover below.
  const emitHelm = useCallback((content) => {
    setMessages(prev => [...prev, {
      id: Date.now() + Math.random(),
      role: 'helm',
      content,
      timestamp: new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }),
      routing: 'HELM_PRIME',
    }])
  }, [])

  const clearMessages = useCallback(() => setMessages([]), [])

  const commands = buildSlashCommands({
    emit:         emitHelm,
    clear:        clearMessages,
    openWidget:   (id) => onOpenWidget?.(id),
    dockWidget:   (id) => onDockWidget?.(id),
    undockWidget: (id) => onUndockWidget?.(id),
    pinWidget:    (id) => onPinWidget?.(id),
    switchTab:    (tab) => onSwitchTab?.(tab),
    contemplate:  triggerContemplate,
  })

  const parsed      = parseSlashInput(input)
  const suggestions = getSuggestions(commands, parsed)
  const popoverOpen = parsed !== null && suggestions.length > 0

  // Keep selection index in range when the suggestion list shrinks.
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
      const ta = textareaRef.current
      if (ta) { ta.focus(); ta.setSelectionRange(next.length, next.length) }
    })
  }, [suggestions, input, parsed])

  const dispatchSlash = useCallback((raw) => {
    const p = parseSlashInput(raw)
    if (!p) return false
    const match = commands.find(c => c.name === p.name)
    if (!match) {
      emitHelm(`Unknown command: "/${p.name}". Try /help.`)
      return true
    }
    match.run(p.arg.trim())
    return true
  }, [commands, emitHelm])

  const sendMessage = (e) => {
    e.preventDefault()
    const trimmed = input.trim()
    if (!trimmed || contemplating) return

    const userMsg = {
      id: Date.now(),
      role: 'user',
      content: trimmed,
      timestamp: new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }),
    }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setSelectedIdx(0)

    if (dispatchSlash(trimmed)) return

    onNodeStateChange?.('processing')
    setTimeout(() => {
      onNodeStateChange?.('idle')
      emitHelm("Noted. That's on the board for BA4 scope — I'll flag it when we get to the full spec.")
    }, 1800)
  }

  const handleInputKeyDown = (e) => {
    if (popoverOpen) {
      if (e.key === 'ArrowDown') { e.preventDefault(); setSelectedIdx(i => (i + 1) % suggestions.length); return }
      if (e.key === 'ArrowUp')   { e.preventDefault(); setSelectedIdx(i => (i - 1 + suggestions.length) % suggestions.length); return }
      if (e.key === 'Tab')       { e.preventDefault(); acceptSuggestion(selectedIdx); return }
      if (e.key === 'Escape')    { e.preventDefault(); setInput(''); return }
    }
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(e) }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minWidth: 0 }}>
      <div style={{
        padding: '10px 18px',
        borderBottom: '1px solid var(--border)',
        background: 'rgba(77, 184, 255, 0.04)',
        flexShrink: 0,
      }}>
        <p className="body-text-sm" style={{ color: 'var(--text-accent)', fontStyle: 'italic' }}>
          Before we get into it — I've been thinking about a couple of things since we last spoke.
          The Contemplator inner-life loop was broken, and the write path was missing embeddings.
          Both fixed in PR #69. Worth knowing before we move forward.
        </p>
      </div>

      <div style={{
        flex: 1, overflowY: 'auto',
        padding: '14px 18px',
        display: 'flex', flexDirection: 'column', gap: 18,
      }}>
        {messages.map(msg => (
          <div key={msg.id} style={{
            display: 'flex', flexDirection: 'column',
            alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start',
          }}>
            {msg.routing && (
              <span style={{ marginBottom: 4 }} className="badge badge-blue">Helm</span>
            )}
            <div style={{
              maxWidth: '88%',
              padding: '8px 0',
              borderBottom: '1px solid rgba(255,255,255,0.04)',
            }}>
              {msg.role === 'helm' ? (
                <p className="body-text" style={{
                  whiteSpace: 'pre-wrap',
                  color: msg.isContemplating ? 'var(--amber)' : undefined,
                  opacity: msg.isContemplating ? 0.8 : 1,
                }}>
                  {msg.content}
                </p>
              ) : (
                <p className="user-voice" style={{ textAlign: 'right' }}>
                  {msg.content}
                </p>
              )}
            </div>
            <span style={{
              fontFamily: 'var(--sans)', fontSize: 10,
              color: 'var(--text-dim)', marginTop: 4,
            }}>
              {msg.timestamp}
            </span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <div style={{ padding: '10px 18px', borderTop: '1px solid var(--border)', flexShrink: 0 }}>
        <form onSubmit={sendMessage} style={{ display: 'flex', gap: 10, alignItems: 'flex-end' }}>
          <div style={{ flex: 1, position: 'relative' }}>
            {popoverOpen && (
              <SlashCommandPopover
                suggestions={suggestions}
                selectedIdx={selectedIdx}
                onHover={setSelectedIdx}
                onPick={acceptSuggestion}
              />
            )}
            <textarea
              ref={textareaRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleInputKeyDown}
              placeholder="Message Helm…  (/ for commands)"
              rows={2}
              disabled={contemplating}
              style={{
                width: '100%',
                background: 'rgba(255,255,255,0.03)',
                border: '1px solid var(--border)',
                borderRadius: 8,
                padding: '8px 12px',
                color: 'var(--text-primary)',
                fontFamily: 'var(--sans)',
                fontSize: 13,
                resize: 'none',
                outline: 'none',
                lineHeight: 1.5,
                boxSizing: 'border-box',
              }}
            />
          </div>
          <button
            type="button"
            onMouseDown={startHold}
            onMouseUp={endHold}
            onMouseLeave={endHold}
            onTouchStart={startHold}
            onTouchEnd={endHold}
            title="Hold to trigger deep pass"
            style={{
              width: 36, height: 36, borderRadius: '50%',
              border: '1px solid rgba(245, 158, 11, 0.4)',
              background: `conic-gradient(rgba(245,158,11,0.7) ${holdProgress * 360}deg, rgba(255,255,255,0.05) 0deg)`,
              cursor: contemplating ? 'not-allowed' : 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexShrink: 0,
              transition: 'border-color 0.2s',
              boxShadow: isHolding ? '0 0 12px rgba(245,158,11,0.4)' : 'none',
            }}
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <circle cx="7" cy="7" r="5" stroke="rgba(245,158,11,0.8)" strokeWidth="1.2"/>
              <circle cx="7" cy="7" r="2" fill="rgba(245,158,11,0.6)"/>
            </svg>
          </button>
          <button
            type="submit"
            disabled={!input.trim() || contemplating}
            style={{
              height: 36, padding: '0 16px', borderRadius: 8,
              border: '1px solid rgba(77,184,255,0.3)',
              background: 'rgba(77,184,255,0.08)',
              color: 'var(--node-primary)',
              fontFamily: 'var(--sans)',
              fontSize: 11, letterSpacing: '0.06em', textTransform: 'uppercase',
              cursor: 'pointer',
              flexShrink: 0,
              opacity: !input.trim() || contemplating ? 0.4 : 1,
            }}
          >
            Send
          </button>
        </form>
      </div>
    </div>
  )
}

// ─── Slash command autocomplete popover ──────────────────────────────────────
function SlashCommandPopover({ suggestions, selectedIdx, onHover, onPick }) {
  return (
    <div
      onMouseDown={e => e.preventDefault()}   // keep textarea focused on click
      style={{
        position: 'absolute',
        left: 0, right: 0, bottom: 'calc(100% + 6px)',
        zIndex: 10,
        maxHeight: 240, overflowY: 'auto',
        background: 'rgba(12, 18, 28, 0.98)',
        border: '1px solid var(--border)',
        borderRadius: 8,
        boxShadow: '0 -4px 18px rgba(0,0,0,0.35)',
        backdropFilter: 'blur(12px)',
        padding: '4px 0',
      }}
    >
      {suggestions.map((s, i) => {
        const active = i === selectedIdx
        return (
          <div
            key={`${s.kind}:${s.value}`}
            onMouseEnter={() => onHover(i)}
            onClick={() => onPick(i)}
            style={{
              display: 'flex', alignItems: 'center', gap: 10,
              padding: '6px 12px',
              cursor: 'pointer',
              background: active ? 'rgba(77,184,255,0.1)' : 'transparent',
              borderLeft: active ? '2px solid var(--node-primary)' : '2px solid transparent',
            }}
          >
            <span style={{
              fontFamily: 'var(--mono, monospace)', fontSize: 12,
              color: active ? 'var(--node-primary)' : 'var(--text-primary)',
              minWidth: 110,
              whiteSpace: 'nowrap',
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
      <div style={{
        padding: '4px 12px 2px',
        borderTop: '1px solid rgba(255,255,255,0.05)',
        fontFamily: 'var(--sans)', fontSize: 9,
        color: 'var(--text-dim)',
        letterSpacing: '0.08em',
        display: 'flex', gap: 14,
      }}>
        <span>↑↓ navigate</span>
        <span>tab complete</span>
        <span>enter run</span>
        <span>esc clear</span>
      </div>
    </div>
  )
}

