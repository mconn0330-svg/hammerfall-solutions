import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence, useMotionValue, animate } from 'framer-motion'
import { BAR_HEIGHT } from './SystemBar'
import { WIDGET_MIN_W, WIDGET_MIN_H } from './Widget.constants'

// ─── WIDGET SHELL ─────────────────────────────────────────────────────────────

const SPRING = { type: 'spring', stiffness: 200, damping: 28 }
const SPAWN_MARGIN = 12
const SPAWN_TOP = BAR_HEIGHT + 8
const HANDLE_THICK = 7 // edge grab width
const HANDLE_CORNER = 12 // corner grab size

// ─── Resize handle ────────────────────────────────────────────────────────────
function ResizeHandle({ type, cursor, style, onMouseDown }) {
  const [hovered, setHovered] = useState(false)
  return (
    <div
      className="no-drag"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onMouseDown={(e) => onMouseDown(e, type)}
      style={{
        position: 'absolute',
        cursor,
        zIndex: 12,
        background: hovered ? 'rgba(77,184,255,0.16)' : 'transparent',
        transition: 'background 0.12s',
        ...(type.length === 2 ? { borderRadius: 3 } : {}),
        ...style,
      }}
    />
  )
}

// ─── Widget header ────────────────────────────────────────────────────────────
function WidgetHeader({
  title,
  isMaximized,
  onMaximize,
  isPinned,
  onPinToggle,
  onMinimize,
  onDock,
  onClose,
  noClose,
  onMouseDown,
}) {
  return (
    <div
      className="widget-header"
      onMouseDown={onMouseDown}
      style={{ cursor: isMaximized ? 'default' : 'grab', userSelect: 'none' }}
    >
      <span className="widget-title">{title}</span>
      <div style={{ display: 'flex', gap: 4 }} className="no-drag">
        {!noClose && (
          <button
            className="icon-btn no-drag"
            title={isPinned ? 'Unpin' : 'Pin to toolbar'}
            onClick={(e) => {
              e.stopPropagation()
              onPinToggle?.()
            }}
            style={{ color: isPinned ? 'var(--node-primary)' : undefined }}
          >
            <IconPin pinned={isPinned} />
          </button>
        )}
        {onDock && (
          <button
            className="icon-btn no-drag"
            title="Dock to console"
            onClick={(e) => {
              e.stopPropagation()
              onDock?.()
            }}
          >
            <IconDock />
          </button>
        )}
        <button
          className="icon-btn no-drag"
          title={isMaximized ? 'Restore' : 'Maximize'}
          onClick={(e) => {
            e.stopPropagation()
            onMaximize?.()
          }}
        >
          {isMaximized ? <IconRestore /> : <IconMaximize />}
        </button>
        <button
          className="icon-btn no-drag"
          title="Minimize"
          onClick={(e) => {
            e.stopPropagation()
            onMinimize?.()
          }}
        >
          <IconMinus />
        </button>
        {!noClose && (
          <button
            className="icon-btn no-drag"
            title="Close"
            onClick={(e) => {
              e.stopPropagation()
              onClose?.()
            }}
          >
            <IconX />
          </button>
        )}
      </div>
    </div>
  )
}

function WidgetBody({ children }) {
  return (
    <div
      style={{
        height: 'calc(100% - 49px)',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {children}
    </div>
  )
}

// ─── Widget ───────────────────────────────────────────────────────────────────
export default function Widget({
  title,
  width = 420,
  height = 480,
  onResizeEnd, // (w, h, x, y) — committed on mouseup
  position, // { x, y } — controlled by App
  onDragStart,
  onDrag,
  onDragEnd,
  children,
  onClose,
  noClose = false,
  isMinimized = false,
  onMinimize,
  zIndex = 10,
  staticStyle,
  isMaximized = false,
  onMaximize,
  isPinned = false,
  onPinToggle,
  onDock,
}) {
  const [localW, setLocalW] = useState(width)
  const [localH, setLocalH] = useState(height)
  const isResizingRef = useRef(false)
  const isDraggingRef = useRef(false)
  const [isDragging, setIsDragging] = useState(false)

  const xMV = useMotionValue(position?.x ?? 0)
  const yMV = useMotionValue(position?.y ?? 0)

  // Sync dims from props (handles maximize/restore, not during active resize)
  useEffect(() => {
    if (!isResizingRef.current) {
      setLocalW(width)
      setLocalH(height)
    }
  }, [width, height])

  // Init to spawn position on mount
  useEffect(() => {
    if (position) {
      xMV.set(position.x)
      yMV.set(position.y)
    }
  }, []) // eslint-disable-line

  // Spring to new position when App updates it (displacement, restore, etc.)
  useEffect(() => {
    if (isDraggingRef.current || isResizingRef.current || !position) return
    animate(xMV, position.x, SPRING)
    animate(yMV, position.y, SPRING)
  }, [position?.x, position?.y]) // eslint-disable-line

  // ── Drag ─────────────────────────────────────────────────────────────────
  const handleDragMouseDown = (e) => {
    if (e.target.closest('.no-drag') || staticStyle || isMaximized) return
    e.preventDefault()
    const startX = xMV.get(),
      startY = yMV.get()
    const startMX = e.clientX,
      startMY = e.clientY
    isDraggingRef.current = true
    setIsDragging(true)
    onDragStart?.()
    const onMove = (ev) => {
      const nx = startX + (ev.clientX - startMX)
      const ny = startY + (ev.clientY - startMY)
      xMV.set(nx)
      yMV.set(ny)
      onDrag?.(nx, ny)
    }
    const onUp = () => {
      isDraggingRef.current = false
      setIsDragging(false)
      onDragEnd?.(xMV.get(), yMV.get())
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
  }

  // ── Resize ───────────────────────────────────────────────────────────────
  const handleResizeMouseDown = (e, type) => {
    e.preventDefault()
    e.stopPropagation()
    if (isMaximized) return

    const startMX = e.clientX,
      startMY = e.clientY
    const startW = localW,
      startH = localH
    const startX = xMV.get(),
      startY = yMV.get()
    // Mutable ref captures latest dims/pos for use in mouseup handler
    const latest = { w: startW, h: startH, x: startX, y: startY }
    isResizingRef.current = true

    const vpW = window.innerWidth,
      vpH = window.innerHeight

    const onMove = (ev) => {
      const dx = ev.clientX - startMX
      const dy = ev.clientY - startMY
      let nW = startW,
        nH = startH,
        nX = startX,
        nY = startY

      switch (type) {
        case 'TL':
          nW = Math.max(WIDGET_MIN_W, startW - dx)
          nH = Math.max(WIDGET_MIN_H, startH - dy)
          nX = startX + (startW - nW)
          nY = startY + (startH - nH)
          break
        case 'BL':
          nW = Math.max(WIDGET_MIN_W, startW - dx)
          nH = Math.max(WIDGET_MIN_H, startH + dy)
          nX = startX + (startW - nW)
          break
        case 'BR':
          nW = Math.max(WIDGET_MIN_W, startW + dx)
          nH = Math.max(WIDGET_MIN_H, startH + dy)
          break
        case 'LEFT':
          nW = Math.max(WIDGET_MIN_W, startW - dx)
          nX = startX + (startW - nW)
          break
        case 'BOTTOM':
          nH = Math.max(WIDGET_MIN_H, startH + dy)
          break
        case 'RIGHT':
          nW = Math.max(WIDGET_MIN_W, startW + dx)
          break
      }

      // Viewport boundary clamp
      nY = Math.max(SPAWN_TOP, nY)
      nX = Math.max(SPAWN_MARGIN, nX)
      nW = Math.min(nW, vpW - nX - SPAWN_MARGIN)
      nH = Math.min(nH, vpH - nY - SPAWN_MARGIN)
      // Re-enforce min after clamp
      nW = Math.max(WIDGET_MIN_W, nW)
      nH = Math.max(WIDGET_MIN_H, nH)

      setLocalW(nW)
      setLocalH(nH)
      xMV.set(nX)
      yMV.set(nY)
      latest.w = nW
      latest.h = nH
      latest.x = nX
      latest.y = nY
    }

    const onUp = () => {
      isResizingRef.current = false
      onResizeEnd?.(latest.w, latest.h, latest.x, latest.y)
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }

    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
  }

  if (isMinimized) return null

  const showHandles = !isMaximized && !staticStyle

  // ── Chat / static position widget ────────────────────────────────────────
  if (staticStyle) {
    return (
      <AnimatePresence>
        <motion.div
          key="panel"
          initial={{ opacity: 0, y: 20, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 20, scale: 0.95 }}
          transition={SPRING}
          style={{ position: 'absolute', width: localW, height: localH, zIndex, ...staticStyle }}
          className="glass-bright"
        >
          <WidgetHeader
            title={title}
            isMaximized={isMaximized}
            onMaximize={onMaximize}
            isPinned={isPinned}
            onPinToggle={onPinToggle}
            onMinimize={onMinimize}
            onDock={onDock}
            onClose={onClose}
            noClose={noClose}
            onMouseDown={handleDragMouseDown}
          />
          <WidgetBody>{children}</WidgetBody>
        </motion.div>
      </AnimatePresence>
    )
  }

  // ── Dynamic widget ────────────────────────────────────────────────────────
  return (
    <AnimatePresence>
      <motion.div
        key="panel"
        initial={{ opacity: 0, scale: 0.92 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.88 }}
        transition={{ type: 'spring', stiffness: 300, damping: 28 }}
        style={{
          position: 'fixed',
          left: 0,
          top: 0,
          x: xMV,
          y: yMV,
          width: localW,
          height: localH,
          zIndex: isDragging ? 200 : zIndex,
          cursor: isDragging ? 'grabbing' : 'default',
        }}
        className="glass-bright"
      >
        {showHandles && (
          <>
            <ResizeHandle
              type="TL"
              cursor="nw-resize"
              style={{ top: 0, left: 0, width: HANDLE_CORNER, height: HANDLE_CORNER }}
              onMouseDown={handleResizeMouseDown}
            />
            <ResizeHandle
              type="BL"
              cursor="sw-resize"
              style={{ bottom: 0, left: 0, width: HANDLE_CORNER, height: HANDLE_CORNER }}
              onMouseDown={handleResizeMouseDown}
            />
            <ResizeHandle
              type="BR"
              cursor="se-resize"
              style={{ bottom: 0, right: 0, width: HANDLE_CORNER, height: HANDLE_CORNER }}
              onMouseDown={handleResizeMouseDown}
            />
            <ResizeHandle
              type="LEFT"
              cursor="ew-resize"
              style={{ top: HANDLE_CORNER, left: 0, width: HANDLE_THICK, bottom: HANDLE_CORNER }}
              onMouseDown={handleResizeMouseDown}
            />
            <ResizeHandle
              type="BOTTOM"
              cursor="ns-resize"
              style={{ bottom: 0, left: HANDLE_CORNER, right: HANDLE_CORNER, height: HANDLE_THICK }}
              onMouseDown={handleResizeMouseDown}
            />
            <ResizeHandle
              type="RIGHT"
              cursor="ew-resize"
              style={{ top: HANDLE_CORNER, right: 0, width: HANDLE_THICK, bottom: HANDLE_CORNER }}
              onMouseDown={handleResizeMouseDown}
            />
          </>
        )}

        <WidgetHeader
          title={title}
          isMaximized={isMaximized}
          onMaximize={onMaximize}
          isPinned={isPinned}
          onPinToggle={onPinToggle}
          onMinimize={onMinimize}
          onDock={onDock}
          onClose={onClose}
          noClose={noClose}
          onMouseDown={handleDragMouseDown}
        />
        <WidgetBody>{children}</WidgetBody>
      </motion.div>
    </AnimatePresence>
  )
}

// ─── Icons ────────────────────────────────────────────────────────────────────
const IconX = () => (
  <svg
    width="12"
    height="12"
    viewBox="0 0 12 12"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.5"
  >
    <line x1="1" y1="1" x2="11" y2="11" />
    <line x1="11" y1="1" x2="1" y2="11" />
  </svg>
)
const IconMinus = () => (
  <svg
    width="12"
    height="12"
    viewBox="0 0 12 12"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.5"
  >
    <line x1="2" y1="6" x2="10" y2="6" />
  </svg>
)
const IconMaximize = () => (
  <svg
    width="12"
    height="12"
    viewBox="0 0 12 12"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.5"
  >
    <path d="M1 4V1h3M8 1h3v3M11 8v3H8M4 11H1V8" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
)
const IconRestore = () => (
  <svg
    width="12"
    height="12"
    viewBox="0 0 12 12"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.5"
  >
    <path
      d="M4 1.5v3H1M8 1.5h3v3M8 10.5h3v-3M4 10.5H1v-3"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
)
const IconDock = () => (
  <svg
    width="12"
    height="12"
    viewBox="0 0 12 12"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.2"
  >
    <rect x="1.25" y="1.75" width="9.5" height="8.5" rx="1" />
    <line x1="7.5" y1="1.75" x2="7.5" y2="10.25" />
    <rect x="8" y="3" width="2" height="1.5" fill="currentColor" stroke="none" />
    <rect x="8" y="5.25" width="2" height="1.5" fill="currentColor" stroke="none" />
  </svg>
)
const IconPin = ({ pinned }) => (
  <svg width="12" height="12" viewBox="0 0 10 10" fill="none">
    <circle
      cx={5}
      cy={3.5}
      r={2.5}
      fill={pinned ? 'rgba(77,184,255,0.85)' : 'rgba(255,255,255,0.5)'}
      stroke={pinned ? '#4db8ff' : 'rgba(255,255,255,0.25)'}
      strokeWidth={0.8}
    />
    <line
      x1={5}
      y1={6}
      x2={5}
      y2={9.5}
      stroke={pinned ? '#4db8ff' : 'rgba(255,255,255,0.5)'}
      strokeWidth={1.2}
      strokeLinecap="round"
    />
  </svg>
)
