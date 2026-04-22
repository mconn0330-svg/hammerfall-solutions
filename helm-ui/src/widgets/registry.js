// ─── Widget registry ─────────────────────────────────────────────────────────
// Canonical map from widget id → { title, Component, initialSize }.
// Shared between App.jsx (canvas rendering) and Console.jsx (dock rendering)
// so docking doesn't have to thread component refs through props.

import PersonalityWidget from './PersonalityWidget'
import BeliefsWidget     from './BeliefsWidget'
import EntitiesWidget    from './EntitiesWidget'
import SignalsWidget     from './SignalsWidget'
import LogsWidget        from './LogsWidget'
import AgentStatusWidget from './AgentStatusWidget'
import MemoryWidget      from './MemoryWidget'

export const WIDGET_DEFS = {
  beliefs:      { title: 'Core Beliefs',  Component: BeliefsWidget,     initialSize: 'standard' },
  memory:       { title: 'Memory',        Component: MemoryWidget,      initialSize: 'standard' },
  entities:     { title: 'Entities',      Component: EntitiesWidget,    initialSize: 'standard' },
  signals:      { title: 'Signals',       Component: SignalsWidget,     initialSize: 'standard' },
  logs:         { title: 'System Logs',   Component: LogsWidget,        initialSize: 'standard' },
  personality:  { title: 'Personality',   Component: PersonalityWidget, initialSize: 'expanded' },
  agent_status: { title: 'Agent Status',  Component: AgentStatusWidget, initialSize: 'standard' },
}
