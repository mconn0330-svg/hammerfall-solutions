import { useEffect, useRef } from 'react'
import * as THREE from 'three'

// ─── HELM NODE — PARTICLE VERSION ────────────────────────────────────────────
// Three orbital particle layers (outer cloud, mid swirl, inner corona) plus
// a bright nucleus sphere. No wireframes — pure light and motion.
//
// idle:          slow blue swirl, soft luminescence
// processing:    accelerated swirl, blue-white, tight corona
// contemplating: amber warmth, slower drift, amber neural lines radiate

const COLORS = {
  idle:          { outer: 0x2a7bbf, mid: 0x4db8ff, inner: 0x9dd8ff, glow: 0x1a6aff },
  processing:    { outer: 0x4db8ff, mid: 0x93d5ff, inner: 0xdff2ff, glow: 0x38bdf8 },
  contemplating: { outer: 0xc27a10, mid: 0xf59e0b, inner: 0xfde68a, glow: 0xd97706 },
}

const SPEED = {
  idle:          1.0,
  processing:    2.8,
  contemplating: 1.4,
}

// Soft radial gradient sprite — gives each particle a glowing halo
function makeSprite() {
  const sz = 64
  const c  = document.createElement('canvas')
  c.width  = sz; c.height = sz
  const ctx = c.getContext('2d')
  const g   = ctx.createRadialGradient(sz/2, sz/2, 0, sz/2, sz/2, sz/2)
  g.addColorStop(0.00, 'rgba(255,255,255,1.0)')
  g.addColorStop(0.20, 'rgba(255,255,255,0.75)')
  g.addColorStop(0.55, 'rgba(255,255,255,0.20)')
  g.addColorStop(1.00, 'rgba(255,255,255,0.00)')
  ctx.fillStyle = g
  ctx.fillRect(0, 0, sz, sz)
  return new THREE.CanvasTexture(c)
}

// ── Build one particle layer ─────────────────────────────────────────────────
// Returns { points, geo, data: Float32Arrays } for per-frame updates.
// Each particle orbits in a randomly inclined 3D plane → spherical cloud shape.
function buildLayer(count, rMin, rMax, baseSpeedMin, baseSpeedMax, size, opacity, color, sprite) {
  const r      = new Float32Array(count)   // orbital radius
  const theta0 = new Float32Array(count)   // initial phase
  const speed  = new Float32Array(count)   // angular speed (rad/s)
  const incl   = new Float32Array(count)   // orbital inclination (uniform sphere)
  const lon    = new Float32Array(count)   // longitude of ascending node

  const positions = new Float32Array(count * 3)

  for (let i = 0; i < count; i++) {
    r[i]      = rMin + Math.random() * (rMax - rMin)
    theta0[i] = Math.random() * Math.PI * 2
    speed[i]  = baseSpeedMin + Math.random() * (baseSpeedMax - baseSpeedMin)
    // acos(uniform) gives inclinations uniformly distributed over the sphere
    incl[i]   = Math.acos(2 * Math.random() - 1)
    lon[i]    = Math.random() * Math.PI * 2

    // Initial position using orbital plane math
    const cosT = Math.cos(theta0[i]), sinT = Math.sin(theta0[i])
    const cosI = Math.cos(incl[i]),   sinI = Math.sin(incl[i])
    const cosL = Math.cos(lon[i]),    sinL = Math.sin(lon[i])
    positions[i*3]   = r[i] * (cosL * cosT - sinL * sinT * cosI)
    positions[i*3+1] = r[i] * (sinL * cosT + cosL * sinT * cosI)
    positions[i*3+2] = r[i] * sinT * sinI
  }

  const geo = new THREE.BufferGeometry()
  geo.setAttribute('position', new THREE.BufferAttribute(positions, 3))

  const mat = new THREE.PointsMaterial({
    color,
    size,
    map: sprite,
    transparent: true,
    opacity,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    sizeAttenuation: true,
    alphaTest: 0.002,
  })

  const points = new THREE.Points(geo, mat)

  return { points, geo, positions, r, theta0, speed, incl, lon, count }
}

// ── Per-frame position update for one layer ──────────────────────────────────
function updateLayer(layer, t, speedMult) {
  const { positions, r, theta0, speed, incl, lon, count } = layer
  for (let i = 0; i < count; i++) {
    const theta = theta0[i] + t * speed[i] * speedMult
    const cosT  = Math.cos(theta), sinT = Math.sin(theta)
    const cosI  = Math.cos(incl[i]), sinI = Math.sin(incl[i])
    const cosL  = Math.cos(lon[i]),  sinL = Math.sin(lon[i])
    positions[i*3]   = r[i] * (cosL * cosT - sinL * sinT * cosI)
    positions[i*3+1] = r[i] * (sinL * cosT + cosL * sinT * cosI)
    positions[i*3+2] = r[i] * sinT * sinI
  }
  layer.geo.attributes.position.needsUpdate = true
}

// ─────────────────────────────────────────────────────────────────────────────

export default function HelmNode({ state = 'idle', onClick }) {
  const mountRef = useRef(null)
  const stateRef = useRef(state)

  useEffect(() => { stateRef.current = state }, [state])

  useEffect(() => {
    const mount = mountRef.current
    const W = mount.clientWidth  || 480
    const H = mount.clientHeight || 480

    // ── Renderer ────────────────────────────────────────────────────────
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setSize(W, H)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.setClearColor(0x000000, 0)
    mount.appendChild(renderer.domElement)

    const scene  = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(42, W / H, 0.1, 100)
    camera.position.set(0, 0, 6.2)

    // ── Sprite texture ──────────────────────────────────────────────────
    const sprite = makeSprite()

    // ── Particle layers ─────────────────────────────────────────────────
    //                       count  rMin  rMax  spMin  spMax  size   opacity  color
    const outer = buildLayer(480,   1.35, 1.95, 0.20,  0.42,  0.075, 0.68,   0x4db8ff, sprite)
    const mid   = buildLayer(300,   0.80, 1.30, 0.44,  0.80,  0.095, 0.80,   0x7dd4fc, sprite)
    const inner = buildLayer(140,   0.28, 0.65, 0.85,  1.50,  0.115, 0.92,   0xb8e4ff, sprite)

    scene.add(outer.points, mid.points, inner.points)

    // ── Nucleus — layered sprites (billboard, always camera-facing) ─────
    const mkSpriteMat = (color, opacity, scale) => {
      const mat = new THREE.SpriteMaterial({
        map: sprite, color, transparent: true, opacity,
        blending: THREE.AdditiveBlending, depthWrite: false,
      })
      const spr = new THREE.Sprite(mat)
      spr.scale.set(scale, scale, 1)
      scene.add(spr)
      return { mat, spr, baseScale: scale }
    }
    // pinpoint core — very bright white
    const core  = mkSpriteMat(0xffffff, 1.0,  0.55)
    // mid glow — main color
    const glow1 = mkSpriteMat(0x4db8ff, 0.80, 1.10)
    // outer halo — soft, wide
    const glow2 = mkSpriteMat(0x1a6aff, 0.22, 2.40)

    // ── Lights ──────────────────────────────────────────────────────────
    const pointLight = new THREE.PointLight(0x4db8ff, 5, 14)
    scene.add(pointLight)
    scene.add(new THREE.AmbientLight(0x050810, 1))

    // ── Animation ────────────────────────────────────────────────────────
    const clock = new THREE.Clock()
    let animId

    const animate = () => {
      animId = requestAnimationFrame(animate)
      const t = clock.getElapsedTime()
      const s = stateRef.current
      const sm = SPEED[s] || 1.0

      // Update particle positions
      updateLayer(outer, t, sm)
      updateLayer(mid,   t, sm)
      updateLayer(inner, t, sm)

      // Color shift per state
      const tc = COLORS[s] || COLORS.idle
      outer.points.material.color.setHex(tc.outer)
      mid.points.material.color.setHex(tc.mid)
      inner.points.material.color.setHex(tc.inner)

      // Opacity pulse — breathing
      const pFreq = s === 'processing' ? 2.2 : s === 'contemplating' ? 0.65 : 0.42
      const pWave = Math.sin(t * pFreq * Math.PI * 2)
      outer.points.material.opacity = 0.68 + pWave * 0.10
      mid.points.material.opacity   = 0.80 + pWave * 0.10
      inner.points.material.opacity = 0.92 + pWave * 0.06

      // Nucleus sprite pulse
      const intensity = (s === 'processing' ? 7 : 5) + pWave * (s === 'processing' ? 3 : 1.5)
      pointLight.intensity = intensity
      pointLight.color.setHex(tc.glow)

      const coreScale  = core.baseScale  + pWave * 0.08
      const glow1Scale = glow1.baseScale + pWave * 0.18
      const glow2Scale = glow2.baseScale + pWave * 0.30
      core.spr.scale.set(coreScale,  coreScale,  1)
      glow1.spr.scale.set(glow1Scale, glow1Scale, 1)
      glow2.spr.scale.set(glow2Scale, glow2Scale, 1)
      core.mat.color.setHex(tc.inner)
      glow1.mat.color.setHex(tc.glow)
      glow2.mat.color.setHex(tc.mid)
      glow1.mat.opacity = 0.80 + pWave * 0.12
      glow2.mat.opacity = 0.22 + pWave * 0.07

      renderer.render(scene, camera)
    }

    animate()

    const onResize = () => {
      const w = mount.clientWidth
      const h = mount.clientHeight
      if (!w || !h) return
      camera.aspect = w / h
      camera.updateProjectionMatrix()
      renderer.setSize(w, h)
    }
    window.addEventListener('resize', onResize)

    return () => {
      cancelAnimationFrame(animId)
      window.removeEventListener('resize', onResize)
      if (mount.contains(renderer.domElement)) mount.removeChild(renderer.domElement)
      renderer.dispose()
      sprite.dispose()
    }
  }, [])

  return (
    <div
      ref={mountRef}
      onClick={onClick}
      style={{
        width: '100%', height: '100%',
        cursor: 'pointer',
        filter: state === 'idle'
          ? 'drop-shadow(0 0 32px rgba(77,184,255,0.5)) drop-shadow(0 0 80px rgba(77,184,255,0.2))'
          : state === 'processing'
          ? 'drop-shadow(0 0 40px rgba(125,212,252,0.7)) drop-shadow(0 0 100px rgba(77,184,255,0.3))'
          : 'drop-shadow(0 0 36px rgba(245,158,11,0.6)) drop-shadow(0 0 90px rgba(245,158,11,0.25))',
        transition: 'filter 1s ease',
      }}
    />
  )
}
