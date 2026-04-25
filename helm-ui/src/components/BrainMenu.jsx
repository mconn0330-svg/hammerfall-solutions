import { useEffect, useRef, useState, useMemo } from 'react'
import { motion, AnimatePresence, useMotionValue, animate } from 'framer-motion'
import { MENU_ITEMS } from '../data/mockData'
import { BAR_HEIGHT } from './SystemBar'

// ─── BRAIN MENU ───────────────────────────────────────────────────────────────
// Elastic tentacles — each contracts via spring toward nearest widget/bar/viewport wall.
// Labels are independent floating objects placed in open space via 8-slot candidate search.
// Tentacle angle spring-rotates to point at its label's committed slot.
// Hover (label visible): hovered item brightens only — no dimming.
// Hover (label hidden):  dim overlay + label reveals at natural angle for disambiguation.
// Hidden endpoint orb:   faint pulsing ring as discovery hint.

const MIN_TENTACLE = 32
const VP_PAD = 28
const MIN_LABEL_DIST = 96
const LABEL_PAD = 22
const LABEL_BOX_W = 150 // real footprint (used for viewport rejection)
const LABEL_BOX_H = 32
const LABEL_GUTTER = 18 // extra breathing room around each label for collision

const TENTACLE_SPRING = { type: 'spring', stiffness: 180, damping: 28 }
const ANGLE_SPRING = { type: 'spring', stiffness: 100, damping: 22 }

const ITEM_STYLE = {
  contemplate: {
    lineColor: '#f59e0b',
    labelColor: '#fbbf24',
    strokeW: 2.5,
    glow: 'url(#bm-glow-amber)',
  },
}
const DEFAULT_STYLE = {
  lineColor: '#4db8ff',
  labelColor: '#3a6a8a',
  strokeW: 1.8,
  glow: 'url(#bm-glow)',
}
const ACTIVE_STYLE = {
  lineColor: '#7dd4fc',
  labelColor: '#a8d8ff',
  strokeW: 2.5,
  glow: 'url(#bm-glow)',
}

function degreesToRad(deg) {
  return (deg * Math.PI) / 180
}

function menuLinePath(cx, cy, rad, progress, lineLen) {
  const ex = cx + Math.cos(rad) * lineLen * progress
  const ey = cy + Math.sin(rad) * lineLen * progress
  const mx = (cx + ex) / 2,
    my = (cy + ey) / 2
  const bow = lineLen * progress * 0.18
  const cpx = mx + -Math.sin(rad) * bow
  const cpy = my + Math.cos(rad) * bow
  return `M ${cx} ${cy} Q ${cpx} ${cpy} ${ex} ${ey}`
}

function boxOverlap(a, b) {
  return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y
}

// Ray vs AABB slabs — top wall is BAR_HEIGHT (not y=0)
function rayDist(ox, oy, angle, rects, vpW, vpH) {
  const rad = degreesToRad(angle)
  const dx = Math.cos(rad)
  const dy = Math.sin(rad)
  let minT = Infinity

  if (dx > 1e-9) minT = Math.min(minT, (vpW - ox) / dx)
  else if (dx < -1e-9) minT = Math.min(minT, -ox / dx)
  if (dy > 1e-9) minT = Math.min(minT, (vpH - oy) / dy)
  else if (dy < -1e-9) minT = Math.min(minT, (BAR_HEIGHT - oy) / dy)

  for (const r of rects) {
    let tmin = -Infinity,
      tmax = Infinity
    if (Math.abs(dx) < 1e-9) {
      if (ox < r.x || ox > r.x + r.w) continue
    } else {
      const t1 = (r.x - ox) / dx,
        t2 = (r.x + r.w - ox) / dx
      tmin = Math.max(tmin, Math.min(t1, t2))
      tmax = Math.min(tmax, Math.max(t1, t2))
    }
    if (Math.abs(dy) < 1e-9) {
      if (oy < r.y || oy > r.y + r.h) continue
    } else {
      const t1 = (r.y - oy) / dy,
        t2 = (r.y + r.h - oy) / dy
      tmin = Math.max(tmin, Math.min(t1, t2))
      tmax = Math.min(tmax, Math.max(t1, t2))
    }
    if (tmax >= tmin && tmin > 0) minT = Math.min(minT, tmin)
  }
  return minT
}

// 8-slot candidate label placement — sequential commitment.
// Returns { [id]: { angle, hidden } }
function placeLabelAngles(items, cx, cy, widgetRects, vpW, vpH, naturalLengths) {
  const claimed = []
  const result = {}

  for (const item of items) {
    const natural = item.angle
    const candidates = [0, 45, -45, 90, -90, 135, -135, 180].map((d) => natural + d)
    let placed = null

    for (const cand of candidates) {
      const rad = degreesToRad(cand)
      const cosC = Math.cos(rad)
      const tentLen = naturalLengths[item.id] ?? MIN_TENTACLE
      const lDist = Math.max(tentLen + LABEL_PAD, MIN_LABEL_DIST)
      const lx = cx + cosC * lDist
      const ly = cy + Math.sin(rad) * lDist

      // Anchor-aware real box — matches how Tentacle renders the text
      let boxX
      if (cosC > 0.25) boxX = lx
      else if (cosC < -0.25) boxX = lx - LABEL_BOX_W
      else boxX = lx - LABEL_BOX_W / 2

      const realBox = { x: boxX, y: ly - LABEL_BOX_H / 2, w: LABEL_BOX_W, h: LABEL_BOX_H }

      // Strict viewport rejection using real box (no clamping — clamped text still clips)
      if (realBox.x < VP_PAD) continue
      if (realBox.x + realBox.w > vpW - VP_PAD) continue
      if (realBox.y < BAR_HEIGHT + VP_PAD) continue
      if (realBox.y + realBox.h > vpH - VP_PAD) continue

      // Collision checks use gutter-inflated box to keep labels well-separated
      const G = LABEL_GUTTER
      const gutterBox = {
        x: realBox.x - G,
        y: realBox.y - G,
        w: realBox.w + G * 2,
        h: realBox.h + G * 2,
      }

      if (widgetRects.some((wr) => boxOverlap(gutterBox, wr))) continue
      if (claimed.some((cr) => boxOverlap(gutterBox, cr))) continue

      placed = { angle: cand }
      claimed.push(gutterBox) // claim with gutter so future items stay clear
      break
    }

    result[item.id] = placed
      ? { angle: placed.angle, hidden: false }
      : { angle: natural, hidden: true }
  }
  return result
}

// ─── Per-item tentacle ────────────────────────────────────────────────────────
function Tentacle({
  item,
  cx,
  cy,
  targetLen,
  open,
  travelProgress,
  isActive,
  isContempl,
  onSelect,
  vpW,
  vpH,
  labelAngle,
  labelHidden,
  isHovered,
  dimmed,
  onHover,
}) {
  const st = isContempl ? ITEM_STYLE.contemplate : isActive ? ACTIVE_STYLE : DEFAULT_STYLE
  const gradId = isContempl
    ? 'url(#sprite-amber)'
    : isActive
      ? 'url(#sprite-blue-active)'
      : 'url(#sprite-blue)'
  const coreColor = isContempl ? '#fff3b0' : isActive ? '#ffffff' : '#b8e4ff'

  // Length spring
  const lenMV = useMotionValue(targetLen)
  const [len, setLen] = useState(targetLen)
  useEffect(() => {
    const ctrl = animate(lenMV, targetLen, TENTACLE_SPRING)
    return () => ctrl.stop()
  }, [targetLen, lenMV])
  useEffect(() => lenMV.on('change', setLen), [lenMV])

  // Angle spring — shortest-path rotation toward placed label slot
  const angleMV = useMotionValue(item.angle)
  const [angle, setAngle] = useState(item.angle)
  useEffect(() => {
    const current = angleMV.get()
    const delta = ((((labelAngle - current) % 360) + 540) % 360) - 180
    const ctrl = animate(angleMV, current + delta, ANGLE_SPRING)
    return () => ctrl.stop()
  }, [labelAngle, angleMV])
  useEffect(() => angleMV.on('change', setAngle), [angleMV])

  const isSettled = Math.abs(len - targetLen) < 3 && Math.abs(angle - labelAngle) < 1.5

  const rad = degreesToRad(angle)
  const cosA = Math.cos(rad)
  const sinA = Math.sin(rad)

  // Clamp rendered length so endpoint orb never rises above the bar
  // (MIN_TENTACLE can overshoot the ray-cast result when node is near the bar)
  // 28 = max orb radius (22) + glow bleed (~6) — keeps full orb visual below bar
  const barMaxLen = sinA < -1e-9 ? Math.max(0, (cy - BAR_HEIGHT - 28) / Math.abs(sinA)) : Infinity
  const renderLen = Math.min(len, barMaxLen)

  const ex = cx + cosA * renderLen
  const ey = cy + sinA * renderLen

  const labelDist = Math.max(len + LABEL_PAD, MIN_LABEL_DIST)

  // Hidden + hovered: reveal label at natural angle
  const dispRad = labelHidden && isHovered ? degreesToRad(item.angle) : rad
  const dispCosA = Math.cos(dispRad)
  const rawLx = cx + dispCosA * labelDist
  const ly = Math.max(
    VP_PAD + BAR_HEIGHT,
    Math.min(cy + Math.sin(dispRad) * labelDist, vpH - VP_PAD)
  )
  // Clamp anchor point so the rendered text stays fully within viewport
  let lx, textAnchor
  if (dispCosA > 0.25) {
    lx = Math.max(VP_PAD, Math.min(rawLx, vpW - VP_PAD - LABEL_BOX_W))
    textAnchor = 'start'
  } else if (dispCosA < -0.25) {
    lx = Math.max(VP_PAD + LABEL_BOX_W, Math.min(rawLx, vpW - VP_PAD))
    textAnchor = 'end'
  } else {
    lx = Math.max(VP_PAD + LABEL_BOX_W / 2, Math.min(rawLx, vpW - VP_PAD - LABEL_BOX_W / 2))
    textAnchor = 'middle'
  }

  const lineOpacity = open ? (isActive || isContempl ? 0.85 : 0.45) : 0
  const pathId = `bm-path-${item.id}`
  const pulseDur = 2.2 + ((item.angle % 60) / 60) * 0.9
  const phaseOff = (item.angle / 360) * pulseDur

  const showLabel = open && travelProgress > 0.86 && (!labelHidden || isHovered)

  const brightLabel = isHovered ? (isContempl ? '#fde68a' : '#b8e4ff') : st.labelColor
  const lineColor = isHovered && !dimmed ? (isContempl ? '#fbbf24' : '#7dd4fc') : st.lineColor
  const lineStrokeW = isHovered && !dimmed ? st.strokeW + 0.8 : st.strokeW

  return (
    <g style={{ opacity: dimmed ? 0.12 : 1, transition: 'opacity 0.22s' }}>
      {/* Elastic path */}
      <path
        id={pathId}
        d={menuLinePath(cx, cy, rad, travelProgress, renderLen)}
        stroke={lineColor}
        strokeWidth={lineStrokeW}
        fill="none"
        opacity={lineOpacity}
        style={{ transition: 'opacity 0.25s, stroke 0.15s' }}
        filter={st.glow}
      />

      {/* Traveling dots — gated on spring-settled to prevent SMIL path artefacts */}
      {open && travelProgress >= 0.98 && isSettled && (
        <>
          <g opacity={isActive || isContempl ? 0.92 : 0.72} filter={st.glow}>
            <circle r={isContempl ? 10 : isActive ? 9 : 8} fill={gradId} />
            <circle r={isContempl ? 2.8 : isActive ? 2.4 : 2.0} fill={coreColor} />
            <animateMotion dur={`${pulseDur}s`} repeatCount="indefinite" begin={`-${phaseOff}s`}>
              <mpath href={`#${pathId}`} />
            </animateMotion>
          </g>
          <g opacity={isActive || isContempl ? 0.55 : 0.4} filter={st.glow}>
            <circle r={isContempl ? 7 : isActive ? 6 : 5.5} fill={gradId} />
            <circle r={isContempl ? 1.8 : isActive ? 1.5 : 1.3} fill={coreColor} />
            <animateMotion
              dur={`${pulseDur}s`}
              repeatCount="indefinite"
              begin={`-${(phaseOff + pulseDur * 0.47) % pulseDur}s`}
            >
              <mpath href={`#${pathId}`} />
            </animateMotion>
          </g>
        </>
      )}

      {/* Endpoint orb */}
      <AnimatePresence>
        {open && travelProgress > 0.8 && (
          <motion.g
            key={`dot-${item.id}`}
            initial={{ opacity: 0, scale: 0 }}
            animate={{ opacity: 1, scale: isHovered ? 1.2 : 1 }}
            exit={{ opacity: 0, scale: 0 }}
            transition={{ type: 'spring', stiffness: 420, damping: 22 }}
            style={{ cursor: 'pointer', pointerEvents: 'all' }}
            onClick={(e) => {
              e.stopPropagation()
              onSelect(item.id)
            }}
            onMouseEnter={() => onHover(item.id)}
            onMouseLeave={() => onHover(null)}
            filter={isContempl ? 'url(#bm-glow-amber)' : 'url(#bm-glow)'}
          >
            {/* Transparent hit zone */}
            <circle cx={ex} cy={ey} r={28} fill="transparent" />
            {/* Orb fill */}
            <circle
              cx={ex}
              cy={ey}
              r={isContempl ? 22 : isActive ? 18 : 15}
              fill={
                isContempl
                  ? 'url(#sprite-amber)'
                  : isActive
                    ? 'url(#sprite-blue-active)'
                    : 'url(#sprite-blue)'
              }
            />
            <circle
              cx={ex}
              cy={ey}
              r={isContempl ? 3.5 : isActive ? 2.8 : 2.2}
              fill={coreColor}
              opacity={0.95}
            />
            {/* Pulsing ring — discovery hint when label is hidden */}
            {labelHidden && !isHovered && (
              <circle
                cx={ex}
                cy={ey}
                r={18}
                fill="none"
                stroke={isContempl ? '#f59e0b' : '#4db8ff'}
                strokeWidth={1.2}
              >
                <animate
                  attributeName="r"
                  values="15;26;15"
                  dur={`${pulseDur + 0.4}s`}
                  repeatCount="indefinite"
                  begin={`-${phaseOff * 0.5}s`}
                />
                <animate
                  attributeName="opacity"
                  values="0.5;0;0.5"
                  dur={`${pulseDur + 0.4}s`}
                  repeatCount="indefinite"
                  begin={`-${phaseOff * 0.5}s`}
                />
              </circle>
            )}
          </motion.g>
        )}
      </AnimatePresence>

      {/* Label — rides placed slot; reveals at natural angle when hidden+hovered */}
      <AnimatePresence>
        {showLabel && (
          <motion.text
            key={`label-${item.id}`}
            x={lx}
            y={ly}
            textAnchor={textAnchor}
            dominantBaseline="middle"
            fill={brightLabel}
            fontSize={isContempl ? '12' : '11'}
            fontWeight={isContempl ? '500' : '400'}
            fontFamily="'Inter', sans-serif"
            letterSpacing="0.08em"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.22 }}
            style={{ cursor: 'pointer', userSelect: 'none', pointerEvents: 'all' }}
            onClick={(e) => {
              e.stopPropagation()
              onSelect(item.id)
            }}
            onMouseEnter={() => onHover(item.id)}
            onMouseLeave={() => onHover(null)}
          >
            {item.label.toUpperCase()}
          </motion.text>
        )}
      </AnimatePresence>
    </g>
  )
}

// ─── BrainMenu ────────────────────────────────────────────────────────────────
export default function BrainMenu({
  open,
  activeWidgets,
  onSelect,
  nodeCenter,
  radius = 200,
  widgetRects = [],
  vpW = window.innerWidth,
  vpH = window.innerHeight,
  isDraggingWidget = false,
}) {
  const [travelProgress, setTravelProgress] = useState(0)
  const [hoveredId, setHoveredId] = useState(null)
  const animRef = useRef(null)
  const startRef = useRef(null)
  const prevPlacementsRef = useRef(null)

  useEffect(() => {
    if (open) {
      setTravelProgress(0)
      startRef.current = null
      const duration = 380
      const step = (ts) => {
        if (!startRef.current) startRef.current = ts
        const p = Math.min((ts - startRef.current) / duration, 1)
        setTravelProgress(1 - Math.pow(1 - p, 3))
        if (p < 1) animRef.current = requestAnimationFrame(step)
      }
      animRef.current = requestAnimationFrame(step)
    } else {
      setTravelProgress(0)
      if (animRef.current) cancelAnimationFrame(animRef.current)
    }
    return () => {
      if (animRef.current) cancelAnimationFrame(animRef.current)
    }
  }, [open])

  useEffect(() => {
    if (!open) setHoveredId(null)
  }, [open])

  // All hooks must precede any early return — derive cx/cy inside memo
  const { targetLengths, labelPlacements, cx, cy } = useMemo(() => {
    if (!nodeCenter) return { targetLengths: {}, labelPlacements: {}, cx: 0, cy: 0 }
    const cx = nodeCenter.x
    const cy = nodeCenter.y

    // Pass 1 — lengths at natural angles (used by placement algorithm)
    const naturalLengths = {}
    for (const item of MENU_ITEMS) {
      const dist = rayDist(cx, cy, item.angle, widgetRects, vpW, vpH)
      naturalLengths[item.id] = Math.max(MIN_TENTACLE, Math.min(radius, dist - 30))
    }

    // Pass 2 — label slot placement (frozen during widget drag to prevent jitter)
    let placements
    if (isDraggingWidget && prevPlacementsRef.current) {
      placements = prevPlacementsRef.current
    } else {
      placements = placeLabelAngles(MENU_ITEMS, cx, cy, widgetRects, vpW, vpH, naturalLengths)
      prevPlacementsRef.current = placements
    }

    // Pass 3 — re-cast at placed angles for accurate elastic contraction
    const targetLengths = {}
    for (const item of MENU_ITEMS) {
      const angle = placements[item.id]?.angle ?? item.angle
      const dist = rayDist(cx, cy, angle, widgetRects, vpW, vpH)
      targetLengths[item.id] = Math.max(MIN_TENTACLE, Math.min(radius, dist - 30))
    }

    return { targetLengths, labelPlacements: placements, cx, cy }
  }, [isDraggingWidget, nodeCenter, widgetRects, vpW, vpH, radius])

  if (!nodeCenter) return null

  // Focus mode: hovering an item whose label is hidden dims everything else
  const hoveredIsHidden = hoveredId ? (labelPlacements[hoveredId]?.hidden ?? false) : false

  return (
    <svg
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        display: 'block',
        overflow: 'visible',
        pointerEvents: 'none',
        zIndex: 50,
      }}
    >
      <defs>
        <filter id="bm-glow" x="-80%" y="-80%" width="260%" height="260%">
          <feGaussianBlur stdDeviation="3" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <filter id="bm-glow-amber" x="-80%" y="-80%" width="260%" height="260%">
          <feGaussianBlur stdDeviation="4" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>

        <radialGradient id="sprite-blue" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#b8e4ff" stopOpacity="1" />
          <stop offset="28%" stopColor="#4db8ff" stopOpacity="0.85" />
          <stop offset="65%" stopColor="#1a6aff" stopOpacity="0.35" />
          <stop offset="100%" stopColor="#1a6aff" stopOpacity="0" />
        </radialGradient>
        <radialGradient id="sprite-blue-active" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#ffffff" stopOpacity="1" />
          <stop offset="22%" stopColor="#7dd4fc" stopOpacity="0.95" />
          <stop offset="60%" stopColor="#4db8ff" stopOpacity="0.4" />
          <stop offset="100%" stopColor="#4db8ff" stopOpacity="0" />
        </radialGradient>
        <radialGradient id="sprite-amber" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#fff3b0" stopOpacity="1" />
          <stop offset="25%" stopColor="#fbbf24" stopOpacity="0.9" />
          <stop offset="60%" stopColor="#d97706" stopOpacity="0.4" />
          <stop offset="100%" stopColor="#d97706" stopOpacity="0" />
        </radialGradient>
      </defs>

      {/* Dim overlay — only when hovering a hidden-label item */}
      {hoveredIsHidden && open && (
        <rect
          x={0}
          y={BAR_HEIGHT}
          width={vpW}
          height={vpH - BAR_HEIGHT}
          fill="rgba(2,5,16,0.65)"
          pointerEvents="none"
        />
      )}

      {MENU_ITEMS.map((item) => {
        const placement = labelPlacements[item.id] ?? { angle: item.angle, hidden: false }
        return (
          <Tentacle
            key={item.id}
            item={item}
            cx={cx}
            cy={cy}
            targetLen={targetLengths[item.id]}
            open={open}
            travelProgress={travelProgress}
            isActive={activeWidgets.includes(item.id)}
            isContempl={item.id === 'contemplate'}
            onSelect={onSelect}
            vpW={vpW}
            vpH={vpH}
            labelAngle={placement.angle}
            labelHidden={placement.hidden}
            isHovered={hoveredId === item.id}
            dimmed={hoveredIsHidden && hoveredId !== item.id}
            onHover={setHoveredId}
          />
        )
      })}
    </svg>
  )
}
