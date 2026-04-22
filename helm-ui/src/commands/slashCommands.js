import { WIDGET_DEFS } from '../widgets/registry'
import { AGENT_STATUS } from '../data/mockData'

// ─── Slash command registry ───────────────────────────────────────────────────
// Called by ChatPane to build its command set. `ctx` carries the side-effect
// handlers (open/dock/pin widgets, switch tabs, clear chat, emit a helm message).
// Returns the command list and helper parsers used by the autocomplete popover.

const TAB_OPTIONS = ['chat', 'activity', 'system']
const WIDGET_IDS  = Object.keys(WIDGET_DEFS)

function widgetLabel(id) {
  return WIDGET_DEFS[id]?.title ?? id
}

export function buildSlashCommands(ctx) {
  const cmds = [
    {
      name: 'help',
      description: 'List available commands',
      run: () => {
        const lines = cmds.map(c => {
          const sig = c.arg ? `/${c.name} ${c.arg}` : `/${c.name}`
          return `  ${sig.padEnd(28)} ${c.description}`
        })
        ctx.emit('Available commands:\n' + lines.join('\n'))
      },
    },
    {
      name: 'clear',
      description: 'Clear chat history',
      run: () => ctx.clear(),
    },
    {
      name: 'open',
      arg: '<widget>',
      description: 'Open a widget on the canvas',
      suggest: () => WIDGET_IDS,
      describeArg: (id) => widgetLabel(id),
      run: (arg) => {
        if (!arg)              return ctx.emit('Usage: /open <widget>')
        if (!WIDGET_DEFS[arg]) return ctx.emit(`Unknown widget: "${arg}"`)
        ctx.openWidget(arg)
      },
    },
    {
      name: 'dock',
      arg: '<widget>',
      description: 'Dock a widget into the console pane',
      suggest: () => WIDGET_IDS,
      describeArg: (id) => widgetLabel(id),
      run: (arg) => {
        if (!arg)              return ctx.emit('Usage: /dock <widget>')
        if (!WIDGET_DEFS[arg]) return ctx.emit(`Unknown widget: "${arg}"`)
        ctx.dockWidget(arg)
      },
    },
    {
      name: 'undock',
      arg: '<widget>',
      description: 'Undock a widget back to the canvas',
      suggest: () => WIDGET_IDS,
      describeArg: (id) => widgetLabel(id),
      run: (arg) => {
        if (!arg)              return ctx.emit('Usage: /undock <widget>')
        if (!WIDGET_DEFS[arg]) return ctx.emit(`Unknown widget: "${arg}"`)
        ctx.undockWidget(arg)
      },
    },
    {
      name: 'pin',
      arg: '<widget>',
      description: 'Toggle pin on a widget',
      suggest: () => WIDGET_IDS,
      describeArg: (id) => widgetLabel(id),
      run: (arg) => {
        if (!arg)              return ctx.emit('Usage: /pin <widget>')
        if (!WIDGET_DEFS[arg]) return ctx.emit(`Unknown widget: "${arg}"`)
        ctx.pinWidget(arg)
      },
    },
    {
      name: 'tab',
      arg: '<chat|activity|system>',
      description: 'Switch the active console tab',
      suggest: () => TAB_OPTIONS,
      run: (arg) => {
        if (!TAB_OPTIONS.includes(arg)) return ctx.emit('Usage: /tab <chat|activity|system>')
        ctx.switchTab(arg)
      },
    },
    {
      name: 'contemplate',
      description: 'Trigger a deep-pass contemplation',
      run: () => ctx.contemplate(),
    },
    {
      name: 'status',
      description: 'Print an agent status snapshot',
      run: () => {
        const lines = AGENT_STATUS.map(a => {
          const lat = a.latency_ms != null ? ` · ${a.latency_ms}ms` : ''
          return `  ${a.name.padEnd(22)} ${a.status.toUpperCase().padEnd(9)} ${a.model}${lat}`
        })
        ctx.emit('Agent status:\n' + lines.join('\n'))
      },
    },
  ]
  return cmds
}

// Split `/cmd rest of arg` into structured parts. Returns null if not a slash input.
export function parseSlashInput(raw) {
  const trimmed = raw.replace(/^\s+/, '')
  if (!trimmed.startsWith('/')) return null
  const body = trimmed.slice(1)
  const spaceIdx = body.indexOf(' ')
  if (spaceIdx === -1) return { name: body, arg: '', hasSpace: false }
  return { name: body.slice(0, spaceIdx), arg: body.slice(spaceIdx + 1), hasSpace: true }
}

// Build autocomplete suggestions for the current input.
export function getSuggestions(commands, parsed) {
  if (!parsed) return []

  if (!parsed.hasSpace) {
    const q = parsed.name.toLowerCase()
    return commands
      .filter(c => c.name.toLowerCase().startsWith(q))
      .map(c => ({
        kind: 'command',
        value: c.name,
        label: `/${c.name}`,
        hint: c.arg || '',
        description: c.description,
      }))
  }

  const match = commands.find(c => c.name === parsed.name)
  if (!match || !match.suggest) return []

  const q = parsed.arg.toLowerCase()
  return match.suggest()
    .filter(a => a.toLowerCase().startsWith(q))
    .map(a => ({
      kind: 'arg',
      value: a,
      label: a,
      hint: '',
      description: match.describeArg ? match.describeArg(a) : '',
    }))
}

// Apply a selected suggestion to the current input (returns the replacement).
export function applySuggestion(raw, parsed, suggestion) {
  if (!parsed) return raw
  if (suggestion.kind === 'command') {
    // Leading whitespace preserved, followed by `/cmd ` ready for an argument (or bare if none).
    const leading = raw.match(/^\s*/)[0]
    const cmd = suggestion.value
    // If the command takes no arg, just complete the command cleanly.
    const takesArg = suggestion.hint && suggestion.hint.length > 0
    return `${leading}/${cmd}${takesArg ? ' ' : ''}`
  }
  // Arg completion — replace the arg portion only.
  const leading = raw.match(/^\s*/)[0]
  return `${leading}/${parsed.name} ${suggestion.value}`
}
