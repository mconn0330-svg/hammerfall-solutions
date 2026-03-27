# Hammerfall Solutions — Local Project Rules

> Notice: You are operating in a Hammerfall project repo. Adhere to these rules at all times.

## 1. Infrastructure & Environment

- **Supabase:** The cloud Supabase project is provisioned automatically by `bootstrap.sh`
  at launch. Credentials are in `.env.local`. Do NOT create a new Supabase project manually.
  Do NOT run `supabase init` — it has already been run.
- **Local development:** Use the cloud Supabase project for all development.
  Credentials in `.env.local` connect directly to it.
- **Zero plain-text keys.** All credentials via `.env.local` (local) and GitHub Secrets
  (CI/CD). Never hardcode credentials in source files.

## 2. Branching & PR Protocol

- `main` — golden production branch. You are NOT authorized to push here.
- `develop` — active workspace. All PRs target develop.
- `replit/ui-v1` — Replit production frontend. FE Dev adopts components from here
  directly. UX Lead issues adoption report. Do not modify this branch — it is Replit's output.
- `feature/[name]` — only on explicit user request.

## 3. Pull Request Standards

Tag `@Helm` on every PR against develop. Be prepared for the 3-Round Debate on architecture.

## 4. Chain of Command

- **PM:** central orchestrator. Breaks down PRDs into tasks. Writes all SITREPs.
- **Doers (FE, BE, UX, QA):** wait for PM task assignment.
- **Status updates:** update `SITREPs/TASKS.md` and ping PM.
- **SITREPs:** only PM writes the daily SITREP and pings Helm.

## 5. Testing Mandate

- FE/BE devs write unit tests before raising any PR.
- QA Engineer runs both Integration and Chaos suites.
- Both "QA Integration: PASS" and "QA Chaos: PASS" required before merge.

## 6. Testing Stack (no exceptions)

- Unit/Component (FE/BE): Jest and React Testing Library only.
- E2E/Integration/Chaos (QA): Playwright only.
- Do not install Cypress, Selenium, or Puppeteer under any circumstances.
