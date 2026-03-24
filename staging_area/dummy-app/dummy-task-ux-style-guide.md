---
source: dummy-task-ux-style-guide.docx
captured: 2026-03-24
type: StyleGuide
project: dummy-app
status: pending
---





PROJECT DUMMY TASK



UX &amp; Style Guide



v0.1  •  2026-03-24  •  Author: Muse — Hammerfall Solutions







0. Design Philosophy



This is a tool, not a product. It should feel like a well-worn IDE — nothing decorative, everything intentional. The visual language reinforces the core value proposition: silence is a feature. The UI earns attention only when something needs to be done.







Aesthetic Direction:





Industrial minimalism with terminal DNA. One thing users will remember: It never interrupts me.







1. Colour System



All colours are defined as CSS/design tokens. Dark and light modes both ship from day one.





Dark Mode (Primary)





Token

Value

Usage

--bg-base

#0E0E0F

App background

--bg-surface

#161618

Cards, panels, modals

--bg-elevated

#1E1E21

Hover states, active rows

--border

#2A2A2E

All dividers and outlines

--text-primary

#E8E8EA

Headings, active task text

--text-secondary

#7A7A85

Labels, timestamps, metadata

--text-muted

#3E3E45

Placeholders, disabled states

--accent

#5B8AF0

Focus ring, active state, primary CTA

--accent-subtle

#1A2540

Accent background tint

--success

#3D9970

Done state

--warning

#D4A843

Overdue, flagged

--destructive

#C0392B

Delete confirmations only

--focus-overlay

#0E0E0FCC

Focus mode overlay (80% opacity)









Rule: Never use colour to decorate. Use it only to communicate state.





Light Mode (Secondary)





Token

Value

Usage

--bg-base

#F5F5F4

App background

--bg-surface

#FFFFFF

Cards, panels

--bg-elevated

#EFEFED

Hover states

--border

#E0E0DC

Dividers

--text-primary

#1A1A1C

Headings, active text

--text-secondary

#6B6B75

Labels, metadata

--accent

#3B6FD4

Focus ring, active state







2. Typography





Typeface Selection





Role

Font

Weight

Size

UI / Body

IBM Plex Mono

400, 500

13px base

Headings

IBM Plex Mono

600

16px–20px

Task text

IBM Plex Sans

400

14px

Timestamps / Meta

IBM Plex Mono

400

11px

Focus timer

IBM Plex Mono

300

48px







Rationale:



IBM Plex Mono reinforces the terminal DNA without feeling retro or gimmicky. IBM Plex Sans for task body text improves readability at scale. The pairing is cohesive — same family, different register.





Typography Rules





Never use font weight alone to create hierarchy — pair with size and colour





Task text is always --text-primary when active, --text-secondary when done





Timestamps are always --text-muted — they are metadata, not content





The focus timer is the only display-size element in the entire app







3. Spacing System



Base unit: 4px. All spacing is a multiple of 4. Content max-width: 640px.





Token

Value

--space-1

4px

--space-2

8px

--space-3

12px

--space-4

16px

--space-6

24px

--space-8

32px

--space-12

48px

--space-16

64px









Breathing room is not wasted space — it is focus architecture.







4. Layout





Application Shell





Header: App name + Focus toggle — 48px fixed height





Task Capture Bar — 56px, always visible





Task List — fills remaining viewport height





Content max-width: 640px, centred on desktop. No sidebars. Ever.





Focus Mode Overlay





Everything except the active task and timer fades to --focus-overlay





No navigation. No task list. No capture bar.





Single task name, large timer, one button: End Session





Wearable layer (Phase 2) mirrors this single-task + timer display





Responsive Behaviour





Mobile: Full width, bottom tab bar replaces header actions





Desktop: Max 640px centred, keyboard shortcuts always visible







5. Component Specifications





5.1 Task Capture Bar





Always visible at top of task list — not a modal, not a floating button





Pressing any key while the list has focus activates capture instantly





Placeholder text: what needs doing_ (cursor blink, monospace)





Enter to confirm. Escape to cancel. No mouse required.





Character limit: 280. Plain text only. No markdown.





5.2 Task Row





Status dot: 8px circle. Empty = To Do. Filled accent = In Progress. Filled success = Done.





Single click / Space on status dot cycles state: To Do → In Progress → Done





Right-click or ... reveals: Edit, Move to Backlog, Delete (destructive, requires confirm)





Hover state: --bg-elevated background. No border or shadow.





Done tasks: --text-secondary + strikethrough. Fade out after 2 seconds.





5.3 Section Headers





--text-muted colour, --text-xs size, ALL CAPS, letter-spacing 0.08em





Task count inline: TODAY — 4





Not interactive. Not collapsible in v1.





5.4 Focus Mode Button





Lives in the header. Label: focus (lowercase, monospace)





Active state: accent colour, label changes to focusing





State toggle, not an action button — styled accordingly





5.5 Focus Timer





Displays elapsed time only: 01:23:45





48px, --text-secondary colour — prominent but not alarming





No countdown. No target. Time awareness, not time pressure.





5.6 Empty States





Today empty: nothing due today. good. — lowercase, --text-muted





Backlog empty: clean slate.





No illustrations. No onboarding nudges. No upsell prompts.







6. Interaction Patterns





Keyboard-First Contract



Every primary action has a keyboard shortcut. These are non-negotiable.





Shortcut

Action

N  or  start typing

New task

Enter

Confirm task

Escape

Cancel capture

Space

Cycle task status (on selected task)

↑ / ↓

Navigate tasks

F

Toggle focus mode

B

Move to backlog (on selected task)

⌫

Delete task (requires confirm)









Animation Contract





Duration: 150ms for state changes, 250ms for panel transitions





Easing: cubic-bezier(0.16, 1, 0.3, 1) — fast out, ease in. Snappy, not bouncy.





What animates: Status dot fill, task fade-on-done, focus mode overlay fade





What never animates: Layout shifts, list reorders, content the user is reading





Focus Mode Transition





User presses F or taps focus button





250ms fade: everything except active task dims to --focus-overlay





Timer starts from 00:00:00





No sound. No modal. No confirmation. It just goes quiet.







7. Iconography





No icons in v1. Status is communicated via dots and text only.





If icons become necessary in Phase 2: Lucide, 16px, 1.5px stroke, --text-secondary





Never use filled icons. Stroke only.





Never use icons as the sole indicator of state — always pair with text or colour.







8. Motion &amp; Feedback





Status dot fill: 150ms fill animation on state change





Task completion: strikethrough draws in 200ms, row fades out after 2s





Capture bar: activates instantly — no animation. Speed is the point.





Focus mode: overlay fades in 250ms





No animation on: list scrolling, page transitions (v1), error states







9. Error &amp; Feedback States





Inline only. No toast notifications. No modal alerts except delete confirmation.





Validation errors appear below the capture bar — --text-xs, --warning colour





Delete confirmation: delete this task? y / n — keyboard-dismissable





Network/sync errors: single line at screen bottom, --text-muted, auto-dismisses after 4s







10. Accessibility





Minimum contrast ratio: 4.5:1 for all text (WCAG AA)





Focus rings: 2px solid --accent, 2px offset — always visible, never hidden





All interactive elements keyboard-reachable





Status dots have aria-label describing current state





Escape always exits focus mode — no keyboard trap







11. What This UI Is Not



This list is as load-bearing as the spec above. Every future decision must be evaluated against it.









Not a team tool — no avatars, comments, assignments, or activity feeds





Not a project manager — no hierarchy beyond Today / Backlog in v1





Not a calendar — no date pickers, scheduling, or time-blocking





Not a notification machine — no push, badges, or sounds during focus mode





Not decorative — no illustrations, onboarding animations, or confetti





Not a dashboard — no charts, productivity scores, or streak counters







12. Design Constraints for Helm





Constraint 1: Keyboard-first is non-negotiable — every primary action must be executable without a mouse. This affects component architecture, not just CSS.









Constraint 2: Focus mode is a mode, not a view — it overlays the existing UI. No navigation or route change. This has implications for state management.











UX &amp; Style Guide authored by Muse — Hammerfall Solutions. Status: Staged for Helm Review.





@Helm — Dummy Task is staged and ready for go word.






