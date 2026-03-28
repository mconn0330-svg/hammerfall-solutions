# Dummy App — Implementation Phase Plan
**Author:** Helm
**Date:** 2026-03-27

## Phase 1: Foundation & Data (The Core Backend)
- **Goal:** Flat, fast, solo-isolated database.
- Create Supabase project (`bootstrap.sh`).
- Single table: `tasks`.
  - Columns: `id, user_id, title, status, priority, tags, created_at, closed_at`.
- RLS Policy: `auth.uid() = user_id`. No sharing, no orgs, no teams.
- Stand up Next.js application skeleton.

## Phase 2: The Command Palette (The Engine)
- **Goal:** The application exists inside the `Cmd+K` prompt.
- Do not build from scratch. Adopt `pacocoursey/cmdk` for accessibility and keyboard focus trapping.
- Wire generic task creation mapping to the Supabase endpoint.
- Implement `/` routing commands (e.g., `/today`, `/all`, `/settings`).

## Phase 3: The View & Navigation (The Neo-Terminal)
- **Goal:** Display output and allow `vim`-style navigation when the prompt is closed.
- Render task list using Muse's high-contrast, monospace style guide.
- Global event listeners for `j` (down), `k` (up), `x` (toggle complete).
- Handle focus management: if user types `/` or `Cmd+K`, focus jumps back to Palette. Otherwise, inputs are blurred so `j/k` work safely.

## Phase 4: NLP and Visual Polish (The Chrome)
- **Goal:** Natural language parsing and terminal aesthetics.
- Add client-side parsing for inputs: e.g., `Update database schema #dev !high` automatically strips tags and priorities before saving.
- Add ANSI-based colored feedback for statuses (Red/critical, Green/success).
- Prepare API endpoints for future CLI integration using PATs (Personal Access Tokens).
