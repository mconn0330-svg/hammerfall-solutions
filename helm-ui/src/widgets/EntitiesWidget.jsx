import { useState } from 'react'
import { ENTITIES } from '../data/mockData'
import { motion, AnimatePresence } from 'framer-motion'

const TYPE_COLOR = {
  person: { color: '#7dd4fc', bg: 'rgba(77,184,255,0.08)' },
  organization: { color: '#a5b4fc', bg: 'rgba(129,140,248,0.08)' },
  concept: { color: '#6ee7b7', bg: 'rgba(52,211,153,0.08)' },
  place: { color: '#fcd34d', bg: 'rgba(245,158,11,0.08)' },
}

export default function EntitiesWidget() {
  const [selected, setSelected] = useState(null)
  const [search, setSearch] = useState('')

  const filtered = ENTITIES.filter(
    (e) =>
      !search ||
      e.name.toLowerCase().includes(search.toLowerCase()) ||
      e.entity_type.includes(search)
  )
  const entity = selected ? ENTITIES.find((e) => e.id === selected) : null

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Search */}
      <div
        style={{
          padding: '10px 18px',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          gap: 10,
          alignItems: 'center',
        }}
      >
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search entities…"
          style={{
            flex: 1,
            background: 'rgba(255,255,255,0.03)',
            border: '1px solid var(--border)',
            borderRadius: 6,
            padding: '5px 10px',
            color: 'var(--text-primary)',
            fontFamily: 'var(--sans)',
            fontSize: 11,
            outline: 'none',
          }}
        />
      </div>

      <AnimatePresence mode="wait">
        {!selected ? (
          <motion.div
            key="table"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            style={{ flex: 1, overflowY: 'auto' }}
          >
            {filtered.map((e) => {
              const tc = TYPE_COLOR[e.entity_type] || TYPE_COLOR.concept
              return (
                <div
                  key={e.id}
                  onClick={() => setSelected(e.id)}
                  style={{
                    padding: '12px 18px',
                    borderBottom: '1px solid var(--border)',
                    cursor: 'pointer',
                    transition: 'background 0.1s',
                  }}
                  onMouseEnter={(ev) =>
                    (ev.currentTarget.style.background = 'rgba(255,255,255,0.02)')
                  }
                  onMouseLeave={(ev) => (ev.currentTarget.style.background = 'transparent')}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
                    <span
                      style={{
                        fontFamily: 'var(--sans)',
                        fontSize: 10,
                        padding: '2px 8px',
                        borderRadius: 4,
                        color: tc.color,
                        background: tc.bg,
                        border: `1px solid ${tc.color}33`,
                        letterSpacing: '0.06em',
                        textTransform: 'uppercase',
                      }}
                    >
                      {e.entity_type}
                    </span>
                    <span style={{ fontSize: 13, color: 'var(--text-primary)', fontWeight: 400 }}>
                      {e.name}
                    </span>
                    {e.aliases.length > 0 && (
                      <span className="body-text-sm" style={{ color: 'var(--text-dim)' }}>
                        aka {e.aliases.join(', ')}
                      </span>
                    )}
                  </div>
                  <p className="body-text-sm" style={{ color: 'var(--text-secondary)' }}>
                    {e.summary}
                  </p>
                </div>
              )
            })}
          </motion.div>
        ) : entity ? (
          <motion.div
            key="detail"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            style={{ flex: 1, overflowY: 'auto' }}
          >
            <button
              onClick={() => setSelected(null)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '12px 18px',
                width: '100%',
                background: 'none',
                border: 'none',
                borderBottom: '1px solid var(--border)',
                color: 'var(--text-secondary)',
                fontFamily: 'var(--sans)',
                fontSize: 10,
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
                cursor: 'pointer',
                textAlign: 'left',
              }}
            >
              ← Back
            </button>
            <div style={{ padding: '16px 18px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
                <span
                  style={{
                    ...TYPE_COLOR[entity.entity_type],
                    fontFamily: 'var(--sans)',
                    fontSize: 10,
                    padding: '2px 8px',
                    borderRadius: 4,
                    border: `1px solid ${TYPE_COLOR[entity.entity_type]?.color || '#4db8ff'}33`,
                    textTransform: 'uppercase',
                    letterSpacing: '0.06em',
                  }}
                >
                  {entity.entity_type}
                </span>
                <h3
                  style={{
                    fontSize: 15,
                    color: 'var(--text-primary)',
                    fontWeight: 400,
                    fontFamily: 'var(--sans)',
                  }}
                >
                  {entity.name}
                </h3>
              </div>
              <p
                className="body-text-sm"
                style={{ color: 'var(--text-secondary)', marginBottom: 14 }}
              >
                {entity.summary}
              </p>
              {entity.aliases.length > 0 && (
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 14 }}>
                  {entity.aliases.map((a) => (
                    <span
                      key={a}
                      style={{
                        fontFamily: 'var(--sans)',
                        fontSize: 10,
                        padding: '2px 8px',
                        borderRadius: 4,
                        border: '1px solid var(--border)',
                        color: 'var(--text-dim)',
                      }}
                    >
                      {a}
                    </span>
                  ))}
                </div>
              )}
              <p
                style={{
                  fontFamily: 'var(--sans)',
                  fontSize: 10,
                  color: 'var(--text-dim)',
                  letterSpacing: '0.06em',
                  textTransform: 'uppercase',
                }}
              >
                First seen: {entity.first_seen} · {entity.relationship_count} relationships
              </p>
            </div>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  )
}
