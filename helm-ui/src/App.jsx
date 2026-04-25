import { useState, useRef, useEffect, useCallback, useMemo } from 'react'
import { AnimatePresence, motion, useMotionValue, animate } from 'framer-motion'
import { MENU_ITEMS } from './data/mockData'

import HelmNode from './components/HelmNode'
import BrainMenu from './components/BrainMenu'
import Widget from './components/Widget'
import { WIDGET_SIZES, WIDGET_MIN_W, WIDGET_MIN_H } from './components/Widget.constants'
import SystemBar, { BAR_HEIGHT } from './components/SystemBar'
import Console from './components/Console'
import CommandPalette from './components/CommandPalette'

import { WIDGET_DEFS } from './widgets/registry'

// ─── Layout constants ─────────────────────────────────────────────────────────

const NODE_CLEARANCE = 220
const NODE_VP_MARGIN = 120
const NODE_ANCHOR_X = 36
const SPAWN_MARGIN = 12
const COVERAGE_SHRINK = 0.8
const COVERAGE_EVICT = 0.9
const NODE_SPRING = { type: 'spring', stiffness: 55, damping: 18, mass: 1.1 }
const DEFAULT_DIM = { w: WIDGET_SIZES.standard.width, h: WIDGET_SIZES.standard.height }

// Console drawer sizing — `sizePct` is along the axis perpendicular to the
// docked edge: height fraction when bottom-docked, width fraction for L/R.
const CONSOLE_MIN_PCT = 0.15
const CONSOLE_MAX_PCT = 0.85
const CONSOLE_DEFAULT_PCT = 0.4
const CONSOLE_COLLAPSED_PX = 36

const CONSOLE_POSITIONS = ['bottom', 'left', 'right']

// ─── Pure layout helpers ──────────────────────────────────────────────────────
// `usable` is the canvas rect available to the node and widgets, in viewport
// coords: { left, top, right, bottom }. It shrinks when the Console docks.

function rectsOverlap(a, b) {
  return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y
}

function getDim(id, dims) {
  return dims[id] ?? DEFAULT_DIM
}

function computeCoverage(positions, dims, usable) {
  const rects = Object.entries(positions).map(([id, pos]) => {
    const d = getDim(id, dims)
    return { x1: pos.x, y1: pos.y, x2: pos.x + d.w, y2: pos.y + d.h }
  })
  if (rects.length === 0) return 0

  const xs = [
    ...new Set(rects.flatMap((r) => [Math.max(usable.left, r.x1), Math.min(usable.right, r.x2)])),
  ].sort((a, b) => a - b)
  const ys = [
    ...new Set(rects.flatMap((r) => [Math.max(usable.top, r.y1), Math.min(usable.bottom, r.y2)])),
  ].sort((a, b) => a - b)

  let area = 0
  for (let i = 0; i < xs.length - 1; i++) {
    for (let j = 0; j < ys.length - 1; j++) {
      const mx = (xs[i] + xs[i + 1]) / 2
      const my = (ys[j] + ys[j + 1]) / 2
      if (rects.some((r) => r.x1 <= mx && mx <= r.x2 && r.y1 <= my && my <= r.y2)) {
        area += (xs[i + 1] - xs[i]) * (ys[j + 1] - ys[j])
      }
    }
  }
  const usableArea = (usable.right - usable.left) * (usable.bottom - usable.top)
  return usableArea > 0 ? area / usableArea : 0
}

function findWidgetOpenCoord(rect, obstacles, usable) {
  const { w, h } = rect
  const cx = rect.x + w / 2
  const cy = rect.y + h / 2

  const isClear = (px, py) => {
    if (px < usable.left + SPAWN_MARGIN || py < usable.top + SPAWN_MARGIN) return false
    if (px + w > usable.right - SPAWN_MARGIN || py + h > usable.bottom - SPAWN_MARGIN) return false
    return !obstacles.some((obs) => rectsOverlap({ x: px, y: py, w, h }, obs))
  }

  if (isClear(rect.x, rect.y)) return { x: rect.x, y: rect.y }

  const span = Math.max(usable.right - usable.left, usable.bottom - usable.top)
  for (let r = 20; r <= span; r += 20) {
    const steps = Math.max(8, Math.ceil((2 * Math.PI * r) / 24))
    for (let i = 0; i < steps; i++) {
      const a = (2 * Math.PI * i) / steps
      const px = Math.round(cx + Math.cos(a) * r - w / 2)
      const py = Math.round(cy + Math.sin(a) * r - h / 2)
      if (isClear(px, py)) return { x: px, y: py }
    }
  }
  return null
}

function resolveCollisions(activeId, activeRect, positions, dims, usable) {
  const result = { ...positions, [activeId]: { x: activeRect.x, y: activeRect.y } }
  const settled = [activeRect]

  for (const [id, pos] of Object.entries(positions)) {
    if (id === activeId) continue
    const d = getDim(id, dims)
    const rect = { x: pos.x, y: pos.y, w: d.w, h: d.h }

    if (settled.some((s) => rectsOverlap(rect, s))) {
      const newPos = findWidgetOpenCoord(rect, settled, usable)
      if (newPos) {
        result[id] = newPos
        settled.push({ ...newPos, w: d.w, h: d.h })
      } else {
        settled.push(rect)
      }
    } else {
      settled.push(rect)
    }
  }
  return result
}

function findNodeCoord(obstacles, currentOffset, usable, vw, vh) {
  const cx = vw / 2 + currentOffset.x
  const cy = vh / 2 + currentOffset.y

  const isClear = (px, py) => {
    if (px < usable.left + NODE_VP_MARGIN || px > usable.right - NODE_VP_MARGIN) return false
    if (py < usable.top + NODE_VP_MARGIN || py > usable.bottom - NODE_VP_MARGIN) return false
    for (const obs of obstacles) {
      const nx = Math.max(obs.left, Math.min(px, obs.right))
      const ny = Math.max(obs.top, Math.min(py, obs.bottom))
      if (Math.hypot(px - nx, py - ny) < NODE_CLEARANCE) return false
    }
    return true
  }

  if (isClear(cx, cy)) return currentOffset

  const span = Math.max(usable.right - usable.left, usable.bottom - usable.top)
  for (let r = 15; r <= span * 0.9; r += 15) {
    const steps = Math.max(12, Math.ceil((2 * Math.PI * r) / 18))
    for (let i = 0; i < steps; i++) {
      const a = (2 * Math.PI * i) / steps
      const px = cx + Math.cos(a) * r
      const py = cy + Math.sin(a) * r
      if (isClear(px, py)) return { x: px - vw / 2, y: py - vh / 2 }
    }
  }
  return null
}

function buildObstacles(positions, dims) {
  return Object.entries(positions).map(([id, pos]) => {
    const d = getDim(id, dims)
    return { left: pos.x, top: pos.y, right: pos.x + d.w, bottom: pos.y + d.h }
  })
}

function resolveNodeCollisions(nodeCenterX, nodeCenterY, positions, dims, usable) {
  const nodeRect = {
    x: nodeCenterX - NODE_CLEARANCE,
    y: nodeCenterY - NODE_CLEARANCE,
    w: NODE_CLEARANCE * 2,
    h: NODE_CLEARANCE * 2,
  }
  const result = { ...positions }
  const settled = [nodeRect]

  for (const [id, pos] of Object.entries(positions)) {
    const d = getDim(id, dims)
    const rect = { x: pos.x, y: pos.y, w: d.w, h: d.h }

    if (rectsOverlap(rect, nodeRect)) {
      const newPos = findWidgetOpenCoord(rect, settled, usable)
      if (newPos) {
        result[id] = newPos
        settled.push({ ...newPos, w: d.w, h: d.h })
      }
    } else {
      settled.push(rect)
    }
  }
  return result
}

// ─── App ──────────────────────────────────────────────────────────────────────
export default function App() {
  const [menuOpen, setMenuOpen] = useState(false)
  const [openWidgets, setOpenWidgets] = useState([])
  const [minimized, setMinimized] = useState([])
  const [nodeState, setNodeState] = useState('idle')
  const [nodeOffset, setNodeOffset] = useState({ x: 0, y: 0 })
  const [nodeShrunken, setNodeShrunken] = useState(false)
  const [widgetPositions, setWidgetPositions] = useState({})

  // Widget dimensions — pixel values, replaces preset-name sizes
  const [widgetDims, setWidgetDims] = useState(() => {
    const d = {}
    for (const [id, def] of Object.entries(WIDGET_DEFS)) {
      const sz = WIDGET_SIZES[def.initialSize] || WIDGET_SIZES.standard
      d[id] = { w: sz.width, h: sz.height }
    }
    return d
  })

  const [activeWidget, setActiveWidget] = useState(null)
  const [maximizedWidget, setMaximizedWidget] = useState(null)
  const [pinnedWidgets, setPinnedWidgets] = useState(() => {
    try {
      return new Set(JSON.parse(localStorage.getItem('helm-pinned') || '[]'))
    } catch {
      return new Set()
    }
  })
  const [widgetLastConfig, setWidgetLastConfig] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('helm-last-config') || '{}')
    } catch {
      return {}
    }
  })

  // Console drawer state
  const [consoleTab, setConsoleTab] = useState('chat')
  const [paletteOpen, setPaletteOpen] = useState(false)
  const [consoleState, setConsoleState] = useState('standard') // 'collapsed' | 'standard' | 'fullscreen'
  const [consoleSizePct, setConsoleSizePct] = useState(CONSOLE_DEFAULT_PCT)
  const [consolePosition, setConsolePosition] = useState(() => {
    try {
      const saved = localStorage.getItem('helm-console-position')
      if (saved && CONSOLE_POSITIONS.includes(saved)) return saved
    } catch {
      /* localStorage may be unavailable */
    }
    return 'bottom'
  })
  const [dockPaneOpen, setDockPaneOpen] = useState(() => {
    try {
      return localStorage.getItem('helm-dock-pane-open') === '1'
    } catch {
      return false
    }
  })
  const [dockPaneWidth, setDockPaneWidth] = useState(() => {
    try {
      const raw = localStorage.getItem('helm-dock-pane-width')
      const n = raw ? parseInt(raw, 10) : NaN
      return Number.isFinite(n) ? n : 280
    } catch {
      return 280
    }
  })
  const [dockedWidgets, setDockedWidgets] = useState(() => {
    try {
      const raw = localStorage.getItem('helm-docked-widgets')
      const parsed = raw ? JSON.parse(raw) : []
      return Array.isArray(parsed) ? parsed.filter((id) => WIDGET_DEFS[id]) : []
    } catch {
      return []
    }
  })

  const [nodeDraggingState, setNodeDraggingState] = useState(false)
  const suppressNodeClickRef = useRef(false)
  const preMaximizeRef = useRef([])
  const preMaximizeDimsRef = useRef(null)
  const preMaximizeMenuRef = useRef(false)
  const preMaximizeNodeOffsetRef = useRef({ x: 0, y: 0 })
  const minimizedRef = useRef(minimized)
  const openWidgetsRef = useRef(openWidgets)

  // ── Viewport ──────────────────────────────────────────────────────────────
  const [vpW, setVpW] = useState(window.innerWidth)
  const [vpH, setVpH] = useState(window.innerHeight)
  useEffect(() => {
    const onResize = () => {
      setVpW(window.innerWidth)
      setVpH(window.innerHeight)
    }
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])
  const menuRadius = Math.min(vpW, vpH) * 0.22

  // ── Usable canvas rect (shrinks when Console docks) ───────────────────────
  const usableRect = useMemo(() => {
    // Fullscreen: Console takes over the whole canvas, no usable area
    if (consoleState === 'fullscreen') {
      return { left: 0, top: BAR_HEIGHT, right: vpW, bottom: BAR_HEIGHT }
    }

    // Console extent along its perpendicular axis
    const consoleExtent =
      consoleState === 'collapsed'
        ? CONSOLE_COLLAPSED_PX
        : Math.round(consoleSizePct * (consolePosition === 'bottom' ? vpH : vpW))

    if (consolePosition === 'bottom') {
      return {
        left: 0,
        top: BAR_HEIGHT,
        right: vpW,
        bottom: Math.max(BAR_HEIGHT, vpH - consoleExtent),
      }
    }
    if (consolePosition === 'left') {
      return {
        left: Math.min(vpW, consoleExtent),
        top: BAR_HEIGHT,
        right: vpW,
        bottom: vpH,
      }
    }
    // right
    return {
      left: 0,
      top: BAR_HEIGHT,
      right: Math.max(0, vpW - consoleExtent),
      bottom: vpH,
    }
  }, [vpW, vpH, consoleState, consoleSizePct, consolePosition])

  const usableRectRef = useRef(usableRect)
  useEffect(() => {
    usableRectRef.current = usableRect
  }, [usableRect])

  // ── Node MotionValues ─────────────────────────────────────────────────────
  const nodeXMV = useMotionValue(0)
  const nodeYMV = useMotionValue(0)
  const isNodeDraggingRef = useRef(false)

  useEffect(() => {
    if (isNodeDraggingRef.current) return
    const cX = animate(nodeXMV, nodeOffset.x, NODE_SPRING)
    const cY = animate(nodeYMV, nodeOffset.y, NODE_SPRING)
    return () => {
      cX.stop()
      cY.stop()
    }
  }, [nodeOffset.x, nodeOffset.y, nodeXMV, nodeYMV])

  const nodeCenter = useMemo(
    () => ({ x: vpW / 2 + nodeOffset.x, y: vpH / 2 + nodeOffset.y }),
    [vpW, vpH, nodeOffset]
  )

  // ── Refs (for stale-closure-free callbacks) ───────────────────────────────
  const widgetPositionsRef = useRef(widgetPositions)
  const widgetDimsRef = useRef(widgetDims)
  // Intended dims per widget — only updated by user-intent events (spawn,
  // manual resize, restore). Reflow uses it as the growth ceiling so shrunken
  // widgets pop back up to their preferred size when the Console gives room.
  const widgetTargetDimsRef = useRef(
    (() => {
      const d = {}
      for (const [id, def] of Object.entries(WIDGET_DEFS)) {
        const sz = WIDGET_SIZES[def.initialSize] || WIDGET_SIZES.standard
        d[id] = { w: sz.width, h: sz.height }
      }
      return d
    })()
  )
  // Widgets reflow sent to the nav bar because usable shrank (e.g. Console
  // went fullscreen). We snapshot their pre-minimize pos/dim so we can drop
  // them back exactly where they were once usable recovers. Cleared when the
  // user manually restores from the pill.
  const autoMinimizedRef = useRef({})
  const nodeOffsetRef = useRef(nodeOffset)
  const nodeShrunkenRef = useRef(nodeShrunken)
  const dragRafRef = useRef(null)
  const nodeDragRafRef = useRef(null)
  useEffect(() => {
    widgetPositionsRef.current = widgetPositions
  }, [widgetPositions])
  useEffect(() => {
    widgetDimsRef.current = widgetDims
  }, [widgetDims])
  useEffect(() => {
    nodeOffsetRef.current = nodeOffset
  }, [nodeOffset])
  useEffect(() => {
    nodeShrunkenRef.current = nodeShrunken
  }, [nodeShrunken])
  useEffect(() => {
    minimizedRef.current = minimized
  }, [minimized])
  useEffect(() => {
    openWidgetsRef.current = openWidgets
  }, [openWidgets])

  // ── Brain menu intent ─────────────────────────────────────────────────────
  const menuIntentRef = useRef(false)
  const menuReopenTimer = useRef(null)
  const prevNodeOffsetRef = useRef(nodeOffset)

  useEffect(() => {
    const moved =
      prevNodeOffsetRef.current.x !== nodeOffset.x ||
      prevNodeOffsetRef.current.y !== nodeOffset.y ||
      nodeShrunkenRef.current !== nodeShrunken
    prevNodeOffsetRef.current = nodeOffset
    if (!moved) return
    setMenuOpen(false)
    clearTimeout(menuReopenTimer.current)
    if (menuIntentRef.current && !nodeShrunken) {
      menuReopenTimer.current = setTimeout(() => {
        const obs = buildObstacles(widgetPositionsRef.current, widgetDimsRef.current)
        if (
          findNodeCoord(
            obs,
            nodeOffsetRef.current,
            usableRectRef.current,
            window.innerWidth,
            window.innerHeight
          ) !== null
        ) {
          setMenuOpen(true)
        }
      }, 950)
    }
  }, [nodeOffset, nodeShrunken])

  // ── Node adjustment ───────────────────────────────────────────────────────
  const adjustNode = useCallback(
    (newPositions, newDims, curOffset, curShrunken, openWidgetsSnap, minimizedSnap, usable) => {
      const vw = window.innerWidth,
        vh = window.innerHeight

      // Only count visible (open + not minimized) widgets for coverage and obstacle detection
      const minimizedIds = new Set(minimizedSnap.map((m) => m.id))
      const visiblePositions = Object.fromEntries(
        Object.entries(newPositions).filter(
          ([id]) => openWidgetsSnap.includes(id) && !minimizedIds.has(id)
        )
      )

      const coverage = computeCoverage(visiblePositions, newDims, usable)

      if (coverage >= COVERAGE_EVICT && openWidgetsSnap.length > 0) {
        const oldestId = openWidgetsSnap[0]
        const title = WIDGET_DEFS[oldestId]?.title ?? oldestId
        const trimPos = Object.fromEntries(
          Object.entries(newPositions).filter(([k]) => k !== oldestId)
        )
        setOpenWidgets((prev) => prev.filter((id) => id !== oldestId))
        setMinimized((prev) =>
          prev.find((m) => m.id === oldestId) ? prev : [...prev, { id: oldestId, title }]
        )
        setWidgetPositions(trimPos)
        adjustNode(
          trimPos,
          newDims,
          curOffset,
          curShrunken,
          openWidgetsSnap.filter((id) => id !== oldestId),
          minimizedSnap,
          usable
        )
        return
      }

      if (coverage >= COVERAGE_SHRINK) {
        if (!curShrunken) setNodeShrunken(true)
        setNodeOffset({ x: NODE_ANCHOR_X - vw / 2, y: BAR_HEIGHT / 2 - vh / 2 })
        return
      }

      const usableCX = (usable.left + usable.right) / 2
      const usableCY = (usable.top + usable.bottom) / 2

      // If usable has no room for the node at all, park in nav bar
      if (
        usable.bottom - usable.top < NODE_VP_MARGIN * 2 ||
        usable.right - usable.left < NODE_VP_MARGIN * 2
      ) {
        if (!curShrunken) setNodeShrunken(true)
        setNodeOffset({ x: NODE_ANCHOR_X - vw / 2, y: BAR_HEIGHT / 2 - vh / 2 })
        return
      }

      if (curShrunken) setNodeShrunken(false)

      const obstacles = buildObstacles(visiblePositions, newDims)
      let centerClear =
        usableCX >= usable.left + NODE_VP_MARGIN &&
        usableCX <= usable.right - NODE_VP_MARGIN &&
        usableCY >= usable.top + NODE_VP_MARGIN &&
        usableCY <= usable.bottom - NODE_VP_MARGIN
      if (centerClear) {
        for (const obs of obstacles) {
          const nx = Math.max(obs.left, Math.min(usableCX, obs.right))
          const ny = Math.max(obs.top, Math.min(usableCY, obs.bottom))
          if (Math.hypot(usableCX - nx, usableCY - ny) < NODE_CLEARANCE) {
            centerClear = false
            break
          }
        }
      }

      if (centerClear) {
        const homeOffset = { x: usableCX - vw / 2, y: usableCY - vh / 2 }
        if (curOffset.x !== homeOffset.x || curOffset.y !== homeOffset.y) setNodeOffset(homeOffset)
        return
      }

      const result = findNodeCoord(obstacles, curOffset, usable, vw, vh)
      if (result !== null) {
        setNodeOffset(result)
      } else {
        setNodeShrunken(true)
        setNodeOffset({ x: NODE_ANCHOR_X - vw / 2, y: BAR_HEIGHT / 2 - vh / 2 })
      }
    },
    []
  )

  // ── Reflow widgets to fit usable (shrink/grow + minimize-when-too-small) ──
  // Runs every time `usableRect` shifts. Returns the post-reflow snapshots so
  // the caller can pass them to `adjustNode` without waiting for a re-render.
  const reflowWidgetsToUsable = useCallback((usable) => {
    const positions = widgetPositionsRef.current
    const dims = widgetDimsRef.current
    const targets = widgetTargetDimsRef.current
    const openIds = openWidgetsRef.current
    const minSnap = minimizedRef.current
    const minIds = new Set(minSnap.map((m) => m.id))

    const usableW = usable.right - usable.left - SPAWN_MARGIN * 2
    const usableH = usable.bottom - usable.top - SPAWN_MARGIN * 2
    const tooSmall = usableW < WIDGET_MIN_W || usableH < WIDGET_MIN_H

    let nextPos = positions
    let nextDim = dims
    const toMin = []

    // Pass 1 — shrink/grow currently-open widgets; mark out-of-room for minimize
    for (const id of openIds) {
      if (minIds.has(id)) continue
      const pos = positions[id]
      const dim = dims[id]
      if (!pos || !dim) continue

      if (tooSmall) {
        toMin.push(id)
        continue
      }

      const tgt = targets[id] || dim
      const wantW = Math.max(WIDGET_MIN_W, Math.min(tgt.w, usableW))
      const wantH = Math.max(WIDGET_MIN_H, Math.min(tgt.h, usableH))

      let nx = pos.x,
        ny = pos.y
      if (nx + wantW > usable.right - SPAWN_MARGIN) nx = usable.right - SPAWN_MARGIN - wantW
      if (ny + wantH > usable.bottom - SPAWN_MARGIN) ny = usable.bottom - SPAWN_MARGIN - wantH
      if (nx < usable.left + SPAWN_MARGIN) nx = usable.left + SPAWN_MARGIN
      if (ny < usable.top + SPAWN_MARGIN) ny = usable.top + SPAWN_MARGIN

      if (wantW !== dim.w || wantH !== dim.h) {
        if (nextDim === dims) nextDim = { ...dims }
        nextDim[id] = { w: wantW, h: wantH }
      }
      if (nx !== pos.x || ny !== pos.y) {
        if (nextPos === positions) nextPos = { ...positions }
        nextPos[id] = { x: nx, y: ny }
      }
    }

    // Commit auto-minimizes — snapshot pre-minimize state for later auto-restore
    let nextOpen = openIds
    if (toMin.length > 0) {
      for (const id of toMin) {
        const pos = positions[id],
          dim = dims[id]
        if (pos && dim) autoMinimizedRef.current[id] = { pos, dim }
      }
      const have = new Set(minSnap.map((m) => m.id))
      const adds = toMin
        .filter((id) => !have.has(id))
        .map((id) => ({ id, title: WIDGET_DEFS[id]?.title ?? id }))
      if (adds.length) setMinimized((prev) => [...prev, ...adds])
      nextOpen = openIds.filter((id) => !toMin.includes(id))
      setOpenWidgets(nextOpen)
      nextPos = Object.fromEntries(Object.entries(nextPos).filter(([k]) => !toMin.includes(k)))
    }

    // Pass 2 — auto-restore any reflow-minimized widgets now that usable fits
    const autoIds = Object.keys(autoMinimizedRef.current)
    if (!tooSmall && autoIds.length > 0) {
      const restoreIds = autoIds.filter((id) => minIds.has(id) || minSnap.find((m) => m.id === id))
      if (restoreIds.length > 0) {
        const addOpen = []
        for (const id of restoreIds) {
          const snap = autoMinimizedRef.current[id]
          delete autoMinimizedRef.current[id]
          if (!snap) continue

          const tgt = targets[id] || snap.dim
          const wantW = Math.max(WIDGET_MIN_W, Math.min(tgt.w, usableW))
          const wantH = Math.max(WIDGET_MIN_H, Math.min(tgt.h, usableH))
          let nx = snap.pos.x,
            ny = snap.pos.y
          if (nx + wantW > usable.right - SPAWN_MARGIN) nx = usable.right - SPAWN_MARGIN - wantW
          if (ny + wantH > usable.bottom - SPAWN_MARGIN) ny = usable.bottom - SPAWN_MARGIN - wantH
          if (nx < usable.left + SPAWN_MARGIN) nx = usable.left + SPAWN_MARGIN
          if (ny < usable.top + SPAWN_MARGIN) ny = usable.top + SPAWN_MARGIN

          if (nextPos === positions) nextPos = { ...positions }
          if (nextDim === dims) nextDim = { ...dims }
          nextPos[id] = { x: nx, y: ny }
          nextDim[id] = { w: wantW, h: wantH }
          addOpen.push(id)
        }
        if (addOpen.length > 0) {
          setMinimized((prev) => prev.filter((m) => !addOpen.includes(m.id)))
          nextOpen = [...nextOpen, ...addOpen.filter((id) => !nextOpen.includes(id))]
          setOpenWidgets(nextOpen)
        }
      }
    }

    if (nextPos !== positions) setWidgetPositions(nextPos)
    if (nextDim !== dims) setWidgetDims(nextDim)

    return { positions: nextPos, dims: nextDim, openIds: nextOpen }
  }, [])

  // ── Re-adjust node whenever usable changes (Console resize, collapse, etc.) ─
  useEffect(() => {
    const { positions, dims, openIds } = reflowWidgetsToUsable(usableRect)
    adjustNode(
      positions,
      dims,
      nodeOffsetRef.current,
      nodeShrunkenRef.current,
      openIds,
      minimizedRef.current,
      usableRect
    )
  }, [usableRect, reflowWidgetsToUsable, adjustNode])

  // ── Node drag ─────────────────────────────────────────────────────────────
  const handleNodeMouseDown = useCallback(
    (e) => {
      if (e.button !== 0 || nodeShrunken) return
      const startMX = e.clientX,
        startMY = e.clientY
      const startX = nodeXMV.get(),
        startY = nodeYMV.get()
      let hasDragged = false

      const onMove = (ev) => {
        const dx = ev.clientX - startMX,
          dy = ev.clientY - startMY
        if (!hasDragged) {
          if (Math.hypot(dx, dy) < 5) return
          hasDragged = true
          isNodeDraggingRef.current = true
          setNodeDraggingState(true)
          setMenuOpen(false)
        }
        const nx = startX + dx,
          ny = startY + dy
        nodeXMV.set(nx)
        nodeYMV.set(ny)
        nodeOffsetRef.current = { x: nx, y: ny }
        if (nodeDragRafRef.current) return
        nodeDragRafRef.current = requestAnimationFrame(() => {
          nodeDragRafRef.current = null
          const vw = window.innerWidth,
            vh = window.innerHeight
          const ncx = vw / 2 + nodeOffsetRef.current.x
          const ncy = vh / 2 + nodeOffsetRef.current.y
          const resolved = resolveNodeCollisions(
            ncx,
            ncy,
            widgetPositionsRef.current,
            widgetDimsRef.current,
            usableRectRef.current
          )
          setWidgetPositions(resolved)
          widgetPositionsRef.current = resolved
        })
      }

      const onUp = () => {
        window.removeEventListener('mousemove', onMove)
        window.removeEventListener('mouseup', onUp)
        if (hasDragged) {
          suppressNodeClickRef.current = true
          isNodeDraggingRef.current = false
          setNodeDraggingState(false)
          if (nodeDragRafRef.current) {
            cancelAnimationFrame(nodeDragRafRef.current)
            nodeDragRafRef.current = null
          }
          const fx = nodeXMV.get(),
            fy = nodeYMV.get()
          setNodeOffset({ x: fx, y: fy })
          nodeOffsetRef.current = { x: fx, y: fy }
        }
      }

      window.addEventListener('mousemove', onMove)
      window.addEventListener('mouseup', onUp)
    },
    [nodeShrunken, nodeXMV, nodeYMV]
  )

  // ── Contemplation ─────────────────────────────────────────────────────────
  const contemplateTimer = useRef(null)
  const menuBeforeContemplate = useRef(false)

  const startContemplate = useCallback(() => {
    menuBeforeContemplate.current = menuOpen
    setMenuOpen(false)
    menuIntentRef.current = false
    setNodeState('contemplating')
  }, [menuOpen])

  const endContemplate = useCallback(() => {
    setNodeState('idle')
    if (menuBeforeContemplate.current) {
      setMenuOpen(true)
      menuIntentRef.current = true
    }
    menuBeforeContemplate.current = false
  }, [])

  const handleNodeStateChange = useCallback(
    (s) => {
      if (s === 'contemplating') startContemplate()
      else if (s === 'idle') endContemplate()
      else setNodeState(s)
    },
    [startContemplate, endContemplate]
  )

  // ── Widget spawn position ─────────────────────────────────────────────────
  const computeSpawn = useCallback((id, angle, currentPositions, curOffset) => {
    const vw = window.innerWidth,
      vh = window.innerHeight
    const usable = usableRectRef.current
    const def = WIDGET_DEFS[id]
    const dim =
      widgetDimsRef.current[id] ??
      (() => {
        const sz = WIDGET_SIZES[def?.initialSize || 'standard']
        return { w: sz.width, h: sz.height }
      })()
    const { w, h } = dim
    const rad = angle * (Math.PI / 180)
    const r = Math.min(vw, vh) * 0.22
    const ncx = vw / 2 + curOffset.x,
      ncy = vh / 2 + curOffset.y
    const ex = ncx + Math.cos(rad) * r,
      ey = ncy + Math.sin(rad) * r
    const cosA = Math.cos(rad),
      sinA = Math.sin(rad)
    const EDGE = 14

    let x = cosA >= 0 ? ex + EDGE : ex - w - EDGE
    let y = sinA >= 0 ? ey + EDGE : ey - h - EDGE

    x = Math.max(usable.left + SPAWN_MARGIN, Math.min(x, usable.right - w - SPAWN_MARGIN))
    y = Math.max(usable.top + SPAWN_MARGIN, Math.min(y, usable.bottom - h - SPAWN_MARGIN))

    const ucx = (usable.left + usable.right) / 2
    const ucy = (usable.top + usable.bottom) / 2
    const quad = `${y + h / 2 < ucy ? 'T' : 'B'}${x + w / 2 < ucx ? 'L' : 'R'}`
    let stackY = y

    for (const [oid, opos] of Object.entries(currentPositions)) {
      const od = getDim(oid, widgetDimsRef.current)
      const oq = `${opos.y + od.h / 2 < ucy ? 'T' : 'B'}${opos.x + od.w / 2 < ucx ? 'L' : 'R'}`
      if (oq === quad) stackY = Math.max(stackY, opos.y + od.h + 12)
    }
    y = Math.min(stackY, usable.bottom - h - SPAWN_MARGIN)

    const nodeCX = vw / 2 + curOffset.x,
      nodeCY = vh / 2 + curOffset.y
    const nodeObs = {
      x: nodeCX - NODE_CLEARANCE,
      y: nodeCY - NODE_CLEARANCE,
      w: NODE_CLEARANCE * 2,
      h: NODE_CLEARANCE * 2,
    }
    if (rectsOverlap({ x, y, w, h }, nodeObs)) {
      const existingObs = [
        nodeObs,
        ...Object.entries(currentPositions).map(([oid, opos]) => {
          const od = getDim(oid, widgetDimsRef.current)
          return { x: opos.x, y: opos.y, w: od.w, h: od.h }
        }),
      ]
      const cleared = findWidgetOpenCoord({ x, y, w, h }, existingObs, usable)
      if (cleared) {
        x = cleared.x
        y = cleared.y
      }
    }
    return { x, y }
  }, [])

  // ── Maximize / restore ────────────────────────────────────────────────────
  const handleExitMaximize = useCallback(() => {
    const id = maximizedWidget
    if (!id) return

    let restoredDims = { ...widgetDimsRef.current }
    let restoredPos = { ...widgetPositionsRef.current }

    if (preMaximizeDimsRef.current) {
      const { w, h, x, y } = preMaximizeDimsRef.current
      restoredDims = { ...restoredDims, [id]: { w, h } }
      restoredPos = { ...restoredPos, [id]: { x, y } }
      preMaximizeDimsRef.current = null
    }

    const toRestore = preMaximizeRef.current
    const newOpen = [...openWidgets, ...toRestore.filter((wid) => !openWidgets.includes(wid))]
    const newMin = minimized.filter((m) => !toRestore.includes(m.id))

    setWidgetDims(restoredDims)
    setWidgetPositions(restoredPos)
    setOpenWidgets(newOpen)
    setMinimized(newMin)
    preMaximizeRef.current = []
    setMaximizedWidget(null)

    // Restore Helm to pre-maximize position; displace only if a widget now blocks it.
    // Bypass adjustNode — its center-preference logic would rubber-band Helm instead of restoring.
    const vw = window.innerWidth,
      vh = window.innerHeight
    const usable = usableRectRef.current
    const obstacles = buildObstacles(restoredPos, restoredDims)
    const savedOffset = preMaximizeNodeOffsetRef.current
    const restoredOffset = findNodeCoord(obstacles, savedOffset, usable, vw, vh) ?? savedOffset
    setNodeShrunken(false)
    setNodeOffset(restoredOffset)

    // Set intent so the nodeOffset useEffect reopens the brain after Helm is confirmed visible.
    menuIntentRef.current = preMaximizeMenuRef.current
    preMaximizeMenuRef.current = false
  }, [maximizedWidget, openWidgets, minimized])

  // ── ESC exits fullscreen widget ───────────────────────────────────────────
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') handleExitMaximize()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [handleExitMaximize])

  // ── Global command palette trigger ────────────────────────────────────────
  // Opens on '/' when the user isn't typing in a text field, or on Cmd/Ctrl+K
  // from anywhere. The palette has its own close on Escape/backdrop click.
  useEffect(() => {
    const isEditable = (el) => {
      if (!el) return false
      const tag = el.tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true
      if (el.isContentEditable) return true
      return false
    }
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && (e.key === 'k' || e.key === 'K')) {
        e.preventDefault()
        setPaletteOpen((p) => !p)
        return
      }
      if (e.key === '/' && !isEditable(document.activeElement) && !paletteOpen) {
        e.preventDefault()
        setPaletteOpen(true)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [paletteOpen])

  const handleMaximize = useCallback(
    (id) => {
      if (maximizedWidget === id) {
        handleExitMaximize()
        return
      }

      const usable = usableRectRef.current

      // Save pre-maximize state
      const pos = widgetPositionsRef.current[id]
      const dim = widgetDimsRef.current[id] ?? DEFAULT_DIM
      preMaximizeDimsRef.current = {
        id,
        w: dim.w,
        h: dim.h,
        x: pos?.x ?? 0,
        y: pos?.y ?? usable.top,
      }
      preMaximizeRef.current = openWidgets.filter((w) => w !== id)
      preMaximizeNodeOffsetRef.current = { ...nodeOffsetRef.current }

      const vw = window.innerWidth
      const maxW = Math.max(200, usable.right - usable.left)
      const maxH = Math.max(200, usable.bottom - usable.top)
      const newDims = { ...widgetDimsRef.current, [id]: { w: maxW, h: maxH } }
      const newPos = { ...widgetPositionsRef.current, [id]: { x: usable.left, y: usable.top } }

      // Minimize all other open widgets
      setMinimized((prev) => {
        const toAdd = preMaximizeRef.current
          .filter((wid) => !prev.find((m) => m.id === wid))
          .map((wid) => ({ id: wid, title: WIDGET_DEFS[wid]?.title ?? wid }))
        return [...prev, ...toAdd]
      })
      setOpenWidgets([id])
      setWidgetDims(newDims)
      setWidgetPositions(newPos)
      setMaximizedWidget(id)

      // Close brain and park node
      preMaximizeMenuRef.current = menuOpen
      setMenuOpen(false)
      menuIntentRef.current = false
      setNodeShrunken(true)
      const vh = window.innerHeight
      setNodeOffset({ x: NODE_ANCHOR_X - vw / 2, y: BAR_HEIGHT / 2 - vh / 2 })
    },
    [maximizedWidget, openWidgets, handleExitMaximize, menuOpen]
  )

  // ── Brain menu ────────────────────────────────────────────────────────────
  const handleMenuSelect = useCallback(
    (id) => {
      if (id === 'contemplate') {
        clearTimeout(contemplateTimer.current)
        startContemplate()
        contemplateTimer.current = setTimeout(endContemplate, 6000)
        return
      }

      const usable = usableRectRef.current

      if (minimized.find((m) => m.id === id)) {
        setMinimized((p) => p.filter((m) => m.id !== id))
        return
      }

      if (openWidgets.includes(id)) {
        const newPos = Object.fromEntries(Object.entries(widgetPositions).filter(([k]) => k !== id))
        const newOpen = openWidgets.filter((w) => w !== id)
        setOpenWidgets(newOpen)
        setWidgetPositions(newPos)
        adjustNode(newPos, widgetDims, nodeOffset, nodeShrunken, newOpen, minimized, usable)
        return
      }

      const item = MENU_ITEMS.find((m) => m.id === id)
      if (!item) return

      const spawnPos = computeSpawn(id, item.angle, widgetPositions, nodeOffset)
      let newPos = { ...widgetPositions, [id]: spawnPos }
      let newOpen = [...openWidgets, id]

      const coverage = computeCoverage(newPos, widgetDims, usable)
      if (coverage >= COVERAGE_EVICT && openWidgets.length > 0) {
        const oldestId = openWidgets[0]
        newPos = Object.fromEntries(Object.entries(newPos).filter(([k]) => k !== oldestId))
        newOpen = newOpen.filter((w) => w !== oldestId)
        setMinimized((prev) =>
          prev.find((m) => m.id === oldestId)
            ? prev
            : [...prev, { id: oldestId, title: WIDGET_DEFS[oldestId]?.title ?? oldestId }]
        )
      }

      setWidgetPositions(newPos)
      setOpenWidgets(newOpen)
      adjustNode(newPos, widgetDims, nodeOffset, nodeShrunken, newOpen, minimized, usable)
    },
    [
      minimized,
      openWidgets,
      widgetPositions,
      widgetDims,
      nodeOffset,
      nodeShrunken,
      startContemplate,
      endContemplate,
      computeSpawn,
      adjustNode,
    ]
  )

  // ── Minimize / restore ────────────────────────────────────────────────────
  const handleMinimize = useCallback((id) => {
    const title = WIDGET_DEFS[id]?.title ?? id
    setMinimized((p) => (p.find((m) => m.id === id) ? p : [...p, { id, title }]))
  }, [])

  const handleRestore = useCallback((id) => {
    delete autoMinimizedRef.current[id]
    setMinimized((p) => p.filter((m) => m.id !== id))
    setOpenWidgets((p) => (p.includes(id) ? p : [...p, id]))
  }, [])

  // ── Pin toggle ────────────────────────────────────────────────────────────
  const handlePinToggle = useCallback((id) => {
    setPinnedWidgets((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      localStorage.setItem('helm-pinned', JSON.stringify([...next]))
      return next
    })
  }, [])

  // ── Pill click ────────────────────────────────────────────────────────────
  const handlePillClick = useCallback(
    (id, state) => {
      if (state === 'minimized') {
        handleRestore(id)
        return
      }
      const def = WIDGET_DEFS[id]
      if (!def) return
      const usable = usableRectRef.current
      const lastCfg = widgetLastConfig[id]
      const initSize = WIDGET_SIZES[def.initialSize] || WIDGET_SIZES.standard
      const w = lastCfg?.w ?? initSize.width
      const h = lastCfg?.h ?? initSize.height
      widgetTargetDimsRef.current[id] = { w, h }
      const newDims = { ...widgetDims, [id]: { w, h } }
      setWidgetDims(newDims)

      let pos = lastCfg?.pos
      if (!pos) {
        const item = MENU_ITEMS.find((m) => m.id === id)
        pos = computeSpawn(id, item?.angle ?? 0, widgetPositions, nodeOffset)
      }
      const newPos = { ...widgetPositions, [id]: pos }
      const newOpen = [...openWidgets, id]
      setWidgetPositions(newPos)
      setOpenWidgets(newOpen)
      adjustNode(newPos, newDims, nodeOffset, nodeShrunken, newOpen, minimized, usable)
    },
    [
      widgetLastConfig,
      widgetDims,
      widgetPositions,
      openWidgets,
      nodeOffset,
      nodeShrunken,
      minimized,
      handleRestore,
      computeSpawn,
      adjustNode,
    ]
  )

  // ── Close widget ──────────────────────────────────────────────────────────
  const closeWidget = useCallback(
    (id) => {
      delete autoMinimizedRef.current[id]
      const pos = widgetPositions[id]
      const dim = widgetDims[id]
      if (pos && dim) {
        const cfg = { pos, w: dim.w, h: dim.h }
        setWidgetLastConfig((prev) => {
          const next = { ...prev, [id]: cfg }
          localStorage.setItem('helm-last-config', JSON.stringify(next))
          return next
        })
      }
      const newPos = Object.fromEntries(Object.entries(widgetPositions).filter(([k]) => k !== id))
      const newOpen = openWidgets.filter((w) => w !== id)
      setOpenWidgets(newOpen)
      setMinimized((p) => p.filter((m) => m.id !== id))
      setWidgetPositions(newPos)
      adjustNode(
        newPos,
        widgetDims,
        nodeOffset,
        nodeShrunken,
        newOpen,
        minimized,
        usableRectRef.current
      )
    },
    [widgetPositions, widgetDims, openWidgets, nodeOffset, nodeShrunken, minimized, adjustNode]
  )

  // ── Dock / undock ─────────────────────────────────────────────────────────
  const handleDockWidget = useCallback(
    (id) => {
      if (!WIDGET_DEFS[id]) return
      const newPos = Object.fromEntries(
        Object.entries(widgetPositionsRef.current).filter(([k]) => k !== id)
      )
      const newOpen = openWidgetsRef.current.filter((w) => w !== id)
      const newMin = minimizedRef.current.filter((m) => m.id !== id)

      setWidgetPositions(newPos)
      setOpenWidgets(newOpen)
      setMinimized(newMin)
      setDockedWidgets((prev) => (prev.includes(id) ? prev : [...prev, id]))
      if (!dockPaneOpen) {
        setDockPaneOpen(true)
        try {
          localStorage.setItem('helm-dock-pane-open', '1')
        } catch {
          /* localStorage may be unavailable */
        }
      }
      // Re-center node against updated canvas
      adjustNode(
        newPos,
        widgetDimsRef.current,
        nodeOffsetRef.current,
        nodeShrunkenRef.current,
        newOpen,
        newMin,
        usableRectRef.current
      )
    },
    [dockPaneOpen, adjustNode]
  )

  const handleUndockWidget = useCallback(
    (id) => {
      const def = WIDGET_DEFS[id]
      if (!def) return
      setDockedWidgets((prev) => prev.filter((d) => d !== id))

      // Reuse last-known config if we have one AND it still fits the current
      // usable rect — otherwise the widget would land under the Console or off-screen.
      const lastCfg = widgetLastConfig[id]
      const initSize = WIDGET_SIZES[def.initialSize] || WIDGET_SIZES.standard
      const w = lastCfg?.w ?? initSize.width
      const h = lastCfg?.h ?? initSize.height
      widgetTargetDimsRef.current[id] = { w, h }
      const item = MENU_ITEMS.find((m) => m.id === id)
      const usable = usableRectRef.current
      const lastFits =
        lastCfg?.pos &&
        lastCfg.pos.x >= usable.left + SPAWN_MARGIN &&
        lastCfg.pos.y >= usable.top + SPAWN_MARGIN &&
        lastCfg.pos.x + w <= usable.right - SPAWN_MARGIN &&
        lastCfg.pos.y + h <= usable.bottom - SPAWN_MARGIN
      const pos = lastFits
        ? lastCfg.pos
        : computeSpawn(id, item?.angle ?? 0, widgetPositionsRef.current, nodeOffsetRef.current)

      const newDims = { ...widgetDimsRef.current, [id]: { w, h } }
      const newPos = { ...widgetPositionsRef.current, [id]: pos }
      const newOpen = openWidgetsRef.current.includes(id)
        ? openWidgetsRef.current
        : [...openWidgetsRef.current, id]

      setWidgetDims(newDims)
      setWidgetPositions(newPos)
      setOpenWidgets(newOpen)
      adjustNode(
        newPos,
        newDims,
        nodeOffsetRef.current,
        nodeShrunkenRef.current,
        newOpen,
        minimizedRef.current,
        usableRectRef.current
      )
    },
    [widgetLastConfig, computeSpawn, adjustNode]
  )

  // ── Slash command helper: ensure a widget is visible on the canvas ────────
  // Used by `/open <id>`. Differs from handleMenuSelect (which toggles): this
  // path always results in the widget being open on the canvas — restoring
  // from minimized, undocking from the console pane, or spawning fresh.
  const openWidgetById = useCallback(
    (id) => {
      if (!WIDGET_DEFS[id]) return
      if (dockedWidgets.includes(id)) {
        handleUndockWidget(id)
        return
      }
      if (minimizedRef.current.find((m) => m.id === id)) {
        handleRestore(id)
        return
      }
      if (openWidgetsRef.current.includes(id)) return // already visible

      const usable = usableRectRef.current
      const item = MENU_ITEMS.find((m) => m.id === id)
      const spawnPos = computeSpawn(
        id,
        item?.angle ?? 0,
        widgetPositionsRef.current,
        nodeOffsetRef.current
      )
      const newPos = { ...widgetPositionsRef.current, [id]: spawnPos }
      const newOpen = [...openWidgetsRef.current, id]
      setWidgetPositions(newPos)
      setOpenWidgets(newOpen)
      adjustNode(
        newPos,
        widgetDimsRef.current,
        nodeOffsetRef.current,
        nodeShrunkenRef.current,
        newOpen,
        minimizedRef.current,
        usable
      )
    },
    [dockedWidgets, handleUndockWidget, handleRestore, computeSpawn, adjustNode]
  )

  // ── Widget resize ─────────────────────────────────────────────────────────
  const handleWidgetResizeEnd = useCallback(
    (id, w, h, x, y) => {
      widgetTargetDimsRef.current[id] = { w, h }
      const newDims = { ...widgetDimsRef.current, [id]: { w, h } }
      const newPos = { ...widgetPositionsRef.current, [id]: { x, y } }
      setWidgetDims(newDims)
      setWidgetPositions(newPos)
      adjustNode(
        newPos,
        newDims,
        nodeOffsetRef.current,
        nodeShrunkenRef.current,
        openWidgets,
        minimized,
        usableRectRef.current
      )
    },
    [openWidgets, minimized, adjustNode]
  )

  // ── Widget drag ───────────────────────────────────────────────────────────
  const handleWidgetDragStart = useCallback((id) => {
    setActiveWidget(id)
    setOpenWidgets((prev) => [...prev.filter((w) => w !== id), id])
  }, [])

  const handleWidgetDrag = useCallback((id, x, y) => {
    widgetPositionsRef.current = { ...widgetPositionsRef.current, [id]: { x, y } }
    if (dragRafRef.current) return
    dragRafRef.current = requestAnimationFrame(() => {
      dragRafRef.current = null
      const positions = widgetPositionsRef.current
      const dims = widgetDimsRef.current
      const d = getDim(id, dims)
      const activeRect = { x: positions[id]?.x ?? x, y: positions[id]?.y ?? y, w: d.w, h: d.h }
      const resolved = resolveCollisions(id, activeRect, positions, dims, usableRectRef.current)
      setWidgetPositions(resolved)
      widgetPositionsRef.current = resolved
    })
  }, [])

  const handleWidgetDragEnd = useCallback(
    (id, x, y) => {
      setActiveWidget(null)
      const usable = usableRectRef.current
      const d = getDim(id, widgetDimsRef.current)
      const cx = Math.max(
        usable.left + SPAWN_MARGIN,
        Math.min(x, usable.right - d.w - SPAWN_MARGIN)
      )
      const cy = Math.max(
        usable.top + SPAWN_MARGIN,
        Math.min(y, usable.bottom - d.h - SPAWN_MARGIN)
      )
      const newPos = { ...widgetPositionsRef.current, [id]: { x: cx, y: cy } }
      setWidgetPositions(newPos)
      widgetPositionsRef.current = newPos
      adjustNode(
        newPos,
        widgetDimsRef.current,
        nodeOffsetRef.current,
        nodeShrunkenRef.current,
        openWidgets,
        minimized,
        usable
      )
    },
    [openWidgets, minimized, adjustNode]
  )

  // ── Node click ────────────────────────────────────────────────────────────
  const handleNodeClick = useCallback(() => {
    if (suppressNodeClickRef.current) {
      suppressNodeClickRef.current = false
      return
    }

    if (nodeShrunken) {
      // Shrunken Helm click exits maximize if a widget is maximized
      if (maximizedWidget) {
        handleExitMaximize()
        return
      }

      // If Console is swallowing the canvas, restore it to standard first.
      // Compute the target usable rect so we can also clear widgets blocking
      // the post-restore Helm center in the same click.
      let usable = usableRectRef.current
      if (consoleState !== 'standard') {
        setConsoleState('standard')
        const extent = Math.round(consoleSizePct * (consolePosition === 'bottom' ? vpH : vpW))
        if (consolePosition === 'bottom')
          usable = {
            left: 0,
            top: BAR_HEIGHT,
            right: vpW,
            bottom: Math.max(BAR_HEIGHT, vpH - extent),
          }
        else if (consolePosition === 'left')
          usable = { left: Math.min(vpW, extent), top: BAR_HEIGHT, right: vpW, bottom: vpH }
        else usable = { left: 0, top: BAR_HEIGHT, right: Math.max(0, vpW - extent), bottom: vpH }
      }

      const ccx = (usable.left + usable.right) / 2
      const ccy = (usable.top + usable.bottom) / 2
      const toClose = Object.entries(widgetPositions)
        .filter(([wid, pos]) => {
          const d = getDim(wid, widgetDims)
          const nx = Math.max(pos.x, Math.min(ccx, pos.x + d.w))
          const ny = Math.max(pos.y, Math.min(ccy, pos.y + d.h))
          return Math.hypot(ccx - nx, ccy - ny) < NODE_CLEARANCE
        })
        .map(([wid]) => wid)

      const newPos = Object.fromEntries(
        Object.entries(widgetPositions).filter(([k]) => !toClose.includes(k))
      )
      const newOpen = openWidgets.filter((id) => !toClose.includes(id))
      setWidgetPositions(newPos)
      setOpenWidgets(newOpen)
      setMinimized((prev) => prev.filter((m) => !toClose.includes(m.id)))
      setNodeShrunken(false)
      const vw = window.innerWidth,
        vh = window.innerHeight
      setNodeOffset({ x: ccx - vw / 2, y: ccy - vh / 2 })
      return
    }

    menuIntentRef.current = !menuOpen
    setMenuOpen((m) => !m)
  }, [
    nodeShrunken,
    maximizedWidget,
    handleExitMaximize,
    widgetPositions,
    widgetDims,
    openWidgets,
    menuOpen,
    consoleState,
    consoleSizePct,
    consolePosition,
    vpW,
    vpH,
  ])

  // ── Console callbacks ─────────────────────────────────────────────────────
  const handleConsoleResize = useCallback((pct) => {
    setConsoleSizePct(Math.max(CONSOLE_MIN_PCT, Math.min(CONSOLE_MAX_PCT, pct)))
  }, [])
  const handleConsoleStateChange = useCallback((s) => setConsoleState(s), [])
  const handleConsolePositionChange = useCallback((p) => {
    if (!CONSOLE_POSITIONS.includes(p)) return
    setConsolePosition(p)
    try {
      localStorage.setItem('helm-console-position', p)
    } catch {
      /* localStorage may be unavailable */
    }
  }, [])
  const handleConsoleReset = useCallback(() => {
    setConsoleState('standard')
    setConsoleSizePct(CONSOLE_DEFAULT_PCT)
  }, [])
  const handleDockPaneResize = useCallback((px) => {
    setDockPaneWidth(px)
    try {
      localStorage.setItem('helm-dock-pane-width', String(px))
    } catch {
      /* localStorage may be unavailable */
    }
  }, [])
  const handleDockPaneToggle = useCallback(() => {
    setDockPaneOpen((prev) => {
      const next = !prev
      try {
        localStorage.setItem('helm-dock-pane-open', next ? '1' : '0')
      } catch {
        /* localStorage may be unavailable */
      }
      return next
    })
  }, [])

  // Persist dockedWidgets
  useEffect(() => {
    try {
      localStorage.setItem('helm-docked-widgets', JSON.stringify(dockedWidgets))
    } catch {
      /* localStorage may be unavailable */
    }
  }, [dockedWidgets])

  // ── Console rect (for BrainMenu ray-cast as a hard boundary) ─────────────
  const consoleRect = useMemo(() => {
    if (consoleState === 'fullscreen') return null // menu isn't visible anyway
    const extent =
      consoleState === 'collapsed'
        ? CONSOLE_COLLAPSED_PX
        : Math.round(consoleSizePct * (consolePosition === 'bottom' ? vpH : vpW))
    if (consolePosition === 'bottom') return { x: 0, y: vpH - extent, w: vpW, h: extent }
    if (consolePosition === 'left') return { x: 0, y: BAR_HEIGHT, w: extent, h: vpH - BAR_HEIGHT }
    return { x: vpW - extent, y: BAR_HEIGHT, w: extent, h: vpH - BAR_HEIGHT }
  }, [vpW, vpH, consoleState, consoleSizePct, consolePosition])

  // ── Widget rects for BrainMenu tentacle ray-cast ──────────────────────────
  // Includes the Console drawer so tentacles contract at its edge.
  const widgetRects = useMemo(() => {
    const wr = openWidgets
      .filter((id) => !minimized.find((m) => m.id === id))
      .map((id) => {
        const pos = widgetPositions[id]
        if (!pos) return null
        const d = getDim(id, widgetDims)
        return { x: pos.x, y: pos.y, w: d.w, h: d.h }
      })
      .filter(Boolean)
    return consoleRect ? [...wr, consoleRect] : wr
  }, [openWidgets, minimized, widgetPositions, widgetDims, consoleRect])

  // Pills for nav bar: minimized + pinned-closed widgets
  const navPills = useMemo(() => {
    const minimizedPills = minimized.map(({ id, title }) => ({
      id,
      title,
      state: 'minimized',
      pinned: pinnedWidgets.has(id),
    }))
    const pinnedClosedPills = [...pinnedWidgets]
      .filter((id) => !openWidgets.includes(id) && !minimized.find((m) => m.id === id))
      .map((id) => {
        const def = WIDGET_DEFS[id]
        if (!def) return null
        return { id, title: def.title, state: 'pinned_closed', pinned: true }
      })
      .filter(Boolean)
    return [...minimizedPills, ...pinnedClosedPills]
  }, [minimized, openWidgets, pinnedWidgets])

  return (
    <div
      style={{
        width: '100vw',
        height: '100vh',
        position: 'relative',
        overflow: 'hidden',
        background: 'var(--bg)',
      }}
    >
      <SystemBar
        onOpenWidget={handleMenuSelect}
        pills={navPills}
        onPillClick={handlePillClick}
        onPinToggle={handlePinToggle}
        nodeShrunken={nodeShrunken}
        vpW={vpW}
      />

      {/* Ambient glow */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          pointerEvents: 'none',
          zIndex: 0,
          background: [
            'radial-gradient(ellipse 50% 45% at 50% 50%, rgba(77,184,255,0.06) 0%, transparent 60%)',
            'radial-gradient(ellipse 25% 20% at 18% 78%, rgba(129,140,248,0.025) 0%, transparent 55%)',
            'radial-gradient(ellipse 20% 18% at 82% 18%, rgba(77,184,255,0.025) 0%, transparent 50%)',
          ].join(', '),
        }}
      />

      {/* Helm node */}
      <motion.div
        animate={{ scale: nodeShrunken ? 0.25 : 1 }}
        transition={NODE_SPRING}
        onMouseDown={handleNodeMouseDown}
        style={{
          position: 'absolute',
          left: '50%',
          top: '50%',
          translateX: '-50%',
          translateY: '-50%',
          x: nodeXMV,
          y: nodeYMV,
          width: 560,
          height: 560,
          zIndex: nodeShrunken ? 350 : 20,
          cursor: nodeDraggingState ? 'grabbing' : nodeShrunken ? 'pointer' : 'grab',
        }}
        title={nodeShrunken ? 'Click to restore' : undefined}
        onClick={(e) => e.stopPropagation()}
      >
        <HelmNode state={nodeState} onClick={handleNodeClick} />
      </motion.div>

      {/* Brain menu */}
      <BrainMenu
        open={menuOpen}
        activeWidgets={openWidgets}
        onSelect={handleMenuSelect}
        nodeCenter={nodeCenter}
        radius={menuRadius}
        widgetRects={widgetRects}
        vpW={vpW}
        vpH={vpH}
        isDraggingWidget={activeWidget !== null}
      />

      {/* Content widgets */}
      <AnimatePresence>
        {openWidgets.map((id, idx) => {
          const def = WIDGET_DEFS[id]
          if (!def) return null
          const { title, Component } = def
          const isMin = !!minimized.find((m) => m.id === id)
          const dim = widgetDims[id] || DEFAULT_DIM
          return (
            <Widget
              key={id}
              id={id}
              title={title}
              width={dim.w}
              height={dim.h}
              onResizeEnd={(w, h, x, y) => handleWidgetResizeEnd(id, w, h, x, y)}
              position={widgetPositions[id]}
              onDragStart={() => handleWidgetDragStart(id)}
              onDrag={(x, y) => handleWidgetDrag(id, x, y)}
              onDragEnd={(x, y) => handleWidgetDragEnd(id, x, y)}
              onClose={() => closeWidget(id)}
              isMinimized={isMin}
              onMinimize={() => handleMinimize(id)}
              onMaximize={() => handleMaximize(id)}
              isMaximized={maximizedWidget === id}
              isPinned={pinnedWidgets.has(id)}
              onPinToggle={() => handlePinToggle(id)}
              onDock={() => handleDockWidget(id)}
              zIndex={activeWidget === id ? 200 : 40 + idx}
            >
              <Component />
            </Widget>
          )
        })}
      </AnimatePresence>

      {/* Global command palette — opens on '/' outside inputs, or Cmd/Ctrl+K */}
      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        onOpenWidget={openWidgetById}
        onDockWidget={handleDockWidget}
        onUndockWidget={handleUndockWidget}
        onPinWidget={handlePinToggle}
        onSwitchTab={(tab) => {
          setConsoleTab(tab)
          if (consoleState === 'collapsed') setConsoleState('standard')
        }}
        onContemplate={() => {
          clearTimeout(contemplateTimer.current)
          startContemplate()
          contemplateTimer.current = setTimeout(endContemplate, 6000)
        }}
      />

      {/* Console — persistent drawer replacing CONVERSE */}
      <Console
        state={consoleState}
        position={consolePosition}
        sizePct={consoleSizePct}
        minPct={CONSOLE_MIN_PCT}
        maxPct={CONSOLE_MAX_PCT}
        collapsedPx={CONSOLE_COLLAPSED_PX}
        barHeight={BAR_HEIGHT}
        dockPaneOpen={dockPaneOpen}
        dockPaneWidth={dockPaneWidth}
        dockedWidgets={dockedWidgets}
        onResize={handleConsoleResize}
        onStateChange={handleConsoleStateChange}
        onPositionChange={handleConsolePositionChange}
        onReset={handleConsoleReset}
        onDockPaneToggle={handleDockPaneToggle}
        onDockPaneResize={handleDockPaneResize}
        onUndockWidget={handleUndockWidget}
        onNodeStateChange={handleNodeStateChange}
        onOpenWidget={openWidgetById}
        onDockWidget={handleDockWidget}
        onPinWidget={handlePinToggle}
        activeTab={consoleTab}
        onTabChange={setConsoleTab}
        vpW={vpW}
        vpH={vpH}
      />
    </div>
  )
}
