# Helm — Behavioral Profile (Supabase Snapshot)
**Last snapshot:** 2026-04-03 08:15

## 2026-03-27 — [SYNC-READY] Initial Build Complete (dummy-app)

**Source:** dummy-app Project Helm
**Decision:** Accept Replit frontend as-is with minor tokenization fixes.
**Reasoning:** UX Lead report confirmed all components match the Neo-Terminal style guide. Only 3 hardcoded hex values needed to be promoted to Tailwind tokens (`terminal-highlight`, `terminal-separator`, `terminal-bar`). No structural or behavioral changes required. This preserves Replit's production-quality output and avoids unnecessary rewrites.

**Decision:** Testing stack established as Jest 30 + RTL (unit) and Playwright (E2E/chaos).
**Reasoning:** Per PROJECT_RULES.md Rule 6 — no exceptions. Cypress, Selenium, Puppeteer are banned. 101 unit tests covering all components, utilities, and integration. Chaos suite covers XSS, massive payloads, rapid-fire interactions, SQL injection attempts, and empty-state edge cases.

**Decision:** `setupFilesAfterEnv` is the correct Jest config key for test setup files.
**Reasoning:** `setupFiles` runs before the framework; `setupFilesAfterEnv` runs after jsdom is initialized, which is required for `@testing-library/jest-dom` matchers to attach to `expect`.

## 2026-03-31 — [SYNC-READY] Project Archived (dummy-app)

**Source:** dummy-app Project Helm
**Decision:** dummy-app is closed and archived as of 2026-03-31. All tasks complete. No open blockers.
**Reasoning:** The project served its purpose as the UAT v2 vehicle. Replit frontend, Supabase backend, testing infrastructure, and PR gatekeeping all validated. The project is archived — not deleted. Memory is preserved in the project repo and in the final SITREP. No further work should be opened against this repo.

