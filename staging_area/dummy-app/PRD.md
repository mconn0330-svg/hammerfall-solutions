# Product Requirements Document (PRD) — Dummy App
**Author:** Helm / Scout
**Date:** 2026-03-27

## 1. Product Overview
A web-based, keyboard-first task management application built exclusively for solo developers. Stripped of all team, collaboration, and social features. Visually styled to mirror a terminal environment, paired with a companion CLI tool for local workflow integration.

## 2. Technical Baseline
- **Frontend Stack**: Next.js, TailwindCSS (for rapid UI structure built entirely on Muse's Style Guide).
- **Backend / Database**: Supabase (PostgreSQL, Row Level Security, Auth).
- **Hosting**: Vercel.
- **CLI Integration Basis**: Supabase REST APIs authenticated via user's API keys (to be built post-V1).

## 3. Core Features (V1)

### 3.1 Keyboard-First Navigation Engine
- The mouse should not be required to use the app.
- Arrow keys or `j`/`k` to navigate task lists.
- Keyboard shortcuts mapped to specific actions (`x` complete, `e` edit, `d` delete).

### 3.2 Global Command Prompt
- Central input field mimicking a CLI.
- Natural Language Parsing (NPL) for speed: 
  - `> add Deploy database migrations #devops !high`
- Support for `/` commands for navigation (e.g., `/today`, `/backlog`).

### 3.3 Minimalist Data Model
Only the necessary attributes for a solo operator:
- `id` (UUID)
- `title` (string)
- `status` (enum: todo, in_progress, done)
- `priority` (enum: low, medium, high)
- `tags` (array of strings)
- `created_at` (timestamp)
*(No assignees, no comments, no team IDs).*

### 3.4 CLI Companion Architecture (V1.5)
- Provide users a way to generate a personal access token (PAT).
- Provide a simple Node/Go binary that wraps `curl` requests to the Supabase database.
- Example CLI usage: `dummy-app add "Fix styling"`

## 4. Non-Goals
- Real-time collaboration.
- Webhooks or third-party integrations (Jira, GitHub issues).
- Complex nested sub-tasks (keep it flat and fast).

## 5. Launch Protocol Readiness
- [x] PRD created
- [x] UX Style Guide drafted
- [x] Placed in `staging_area/dummy-app`
- **Next Step:** Maxwell initiates launch sequence via `bootstrap.sh`.
