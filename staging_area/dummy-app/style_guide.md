# Dummy App — UX Style Guide & Schema
**Author:** Muse
**Date:** 2026-03-27

## Aesthetic Core
**Neo-Terminal.** We are bringing the intimacy and raw functionalism of a developer's terminal instance into the browser. 
- No drop shadows.
- No rounded corners (or extremely minimal, `rounded-sm`).
- No unnecessary borders.

## Color Palette
- **Background:** `#000000` (True Black) or `#0D0D0D` (Deep Charcoal)
- **Primary Text:** `#E5E5E5` (Off-White) or `#00FF41` (Terminal Green) for accents
- **Muted/Secondary:** `#666666` (Dim Grey) for shortcuts, timestamps, and borders
- **Critical/Alert:** `#FF3333` (Red) or `#FFCC00` (Amber)

## Typography
Exclusively **Monospace**.
- **Primary Font:** `JetBrains Mono`, `Fira Code`, or `Geist Mono`.
- All sizing should feel slightly smaller and denser than consumer apps (e.g., `text-sm` as base).

## Layout & Components

### 1. The Global Command Palette (The CLI inside the UI)
The centerpiece of the application. Triggered by `Cmd/Ctrl + K`.
- Looks like a terminal prompt: `> add fix authentication bug @high #backend`
- Handles routing, task creation, and task deletion.

### 2. The Task List (The Output)
- Rendered like console output. 
- Active task highlighted permanently.
- `j` and `k` to move up and down the list.
- `x` to complete.
- `e` to edit inline.
- `d` to delete.

### 3. The Status Bar
- Bottom of the viewport.
- Inspired by `tmux` or `vim` Airline.
- Shows total open tasks, current focus, and hints: `[?] Help | [Cmd+K] Command | [j/k] Navigate`

## Motion
- Instantaneous. No ease-in/ease-out. State changes should feel like a terminal redraw.
