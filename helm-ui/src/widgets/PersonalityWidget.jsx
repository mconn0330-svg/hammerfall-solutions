import { useState } from 'react'
import { PERSONALITY } from '../data/mockData'
import { motion } from 'framer-motion'

function getTranslation(attr, score) {
  const thresholds = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
  const key = thresholds.reduce((best, t) => (score >= t ? t : best), 0.0)
  return attr.translations[key] || attr.description
}

export default function PersonalityWidget() {
  const [scores, setScores] = useState(() =>
    Object.fromEntries(PERSONALITY.map((p) => [p.attribute, p.score]))
  )
  const [saved, setSaved] = useState({})

  const handleChange = (attr, val) => {
    setScores((prev) => ({ ...prev, [attr]: parseFloat(val) }))
    setSaved((prev) => ({ ...prev, [attr]: false }))
  }

  const handleApply = (attr) => {
    setSaved((prev) => ({ ...prev, [attr]: true }))
    setTimeout(() => setSaved((prev) => ({ ...prev, [attr]: false })), 1500)
  }

  return (
    <div style={{ height: '100%', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
      {/* Tooltip header */}
      <div
        style={{
          padding: '10px 18px',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
        }}
      >
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" style={{ flexShrink: 0 }}>
          <circle cx="6" cy="6" r="5" stroke="rgba(77,184,255,0.4)" strokeWidth="1" />
          <line x1="6" y1="5" x2="6" y2="9" stroke="rgba(77,184,255,0.6)" strokeWidth="1.2" />
          <circle cx="6" cy="3.5" r="0.8" fill="rgba(77,184,255,0.6)" />
        </svg>
        <span className="body-text-sm" style={{ color: 'var(--text-dim)' }}>
          These parameters shape how I engage — not what I will and won't do.
        </span>
      </div>

      {/* Sliders */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '8px 0' }}>
        {PERSONALITY.map((attr) => {
          const score = scores[attr.attribute]
          const translation = getTranslation(attr, score)
          const isSaved = saved[attr.attribute]

          return (
            <motion.div
              key={attr.attribute}
              animate={{
                background: isSaved ? 'rgba(77, 184, 255, 0.06)' : 'transparent',
              }}
              transition={{ duration: 0.4 }}
              style={{ padding: '14px 18px', borderBottom: '1px solid var(--border)' }}
            >
              {/* Label + score */}
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
                <span
                  className="field-label"
                  style={{
                    color: isSaved ? 'var(--node-bright)' : 'var(--text-secondary)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.06em',
                    transition: 'color 0.3s',
                  }}
                >
                  {attr.attribute.replace('_', ' ')}
                </span>
                <span
                  style={{ fontFamily: 'var(--sans)', fontSize: 11, color: 'var(--node-primary)' }}
                >
                  {score.toFixed(2)}
                </span>
              </div>

              {/* Slider */}
              <div style={{ position: 'relative', marginBottom: 8 }}>
                <div
                  style={{
                    position: 'absolute',
                    top: '50%',
                    left: 0,
                    width: `${score * 100}%`,
                    height: 3,
                    background: 'linear-gradient(90deg, var(--node-primary), var(--node-bright))',
                    borderRadius: 2,
                    transform: 'translateY(-50%)',
                    boxShadow: '0 0 8px var(--node-glow)',
                    pointerEvents: 'none',
                    zIndex: 1,
                  }}
                />
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.01"
                  value={score}
                  className="helm-slider"
                  onChange={(e) => handleChange(attr.attribute, e.target.value)}
                  style={{ position: 'relative', zIndex: 2 }}
                />
              </div>

              {/* Translation text */}
              <p
                className="body-text-sm"
                style={{
                  color: 'var(--text-secondary)',
                  fontStyle: 'italic',
                  marginBottom:
                    saved[attr.attribute] !== undefined && saved[attr.attribute] === false ? 8 : 0,
                }}
              >
                {translation}
              </p>

              {/* Apply button — only if changed */}
              {saved[attr.attribute] === false && (
                <motion.button
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  style={{
                    marginTop: 8,
                    padding: '4px 14px',
                    borderRadius: 6,
                    border: '1px solid rgba(77,184,255,0.3)',
                    background: 'rgba(77,184,255,0.06)',
                    color: 'var(--node-primary)',
                    fontFamily: 'var(--sans)',
                    fontSize: 10,
                    letterSpacing: '0.08em',
                    textTransform: 'uppercase',
                    cursor: 'pointer',
                  }}
                  onClick={() => handleApply(attr.attribute)}
                >
                  Apply
                </motion.button>
              )}

              {/* Saved confirmation */}
              {isSaved && (
                <motion.span
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  style={{
                    fontFamily: 'var(--sans)',
                    fontSize: 10,
                    color: '#4ade80',
                    marginTop: 4,
                    display: 'block',
                  }}
                >
                  ✓ applied
                </motion.span>
              )}
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
