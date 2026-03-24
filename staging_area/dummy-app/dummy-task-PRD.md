---
source: dummy-task-PRD.docx
captured: 2026-03-24
type: PRD
project: dummy-app
status: pending
---





PROJECT DUMMY TASK



Product Requirements Document



v0.1 Draft  •  2026-03-24  •  Author: Scout — Hammerfall Solutions







1. Purpose



This document defines the minimal product requirements for Project Dummy Task — a lightweight task management application built exclusively for solo developers. It is scoped as a UAT dummy app to validate the Hammerfall build pipeline end-to-end. It may also serve as a concept validation vehicle for the solo dev task management market.







2. Core Jobs to Be Done (JTBD)





Primary Job: When I am deep in a development session, I need to capture and triage tasks instantly — without breaking my flow state — so I can stay focused on the current problem and trust that nothing is lost.









Secondary Job: When I switch contexts between projects or sessions, I need a frictionless view of what&apos;s next — so I don&apos;t waste cognitive energy reconstructing where I left off.









Tertiary Job: When I&apos;ve been working for an extended period, I need passive awareness of time elapsed — so I can manage my own energy without actively monitoring the clock.







3. Target Persona



Solo Developer — &quot;The Independent Builder&quot;





Works alone on 1–3 projects simultaneously





Primary environment: desktop (Mac or Windows), keyboard-driven





Owns a wearable device (Apple Watch or Wear OS) — nice to have, not universal





Already has an entrenched tool (Notion, Todoist, Things 3) but is dissatisfied with team-centric UX





Values speed of capture above all else





Deeply allergic to onboarding friction and subscription fatigue







4. Problem Statement



Existing task managers are built for teams. Solo developers using these tools are paying — in money and cognitive overhead — for collaboration features they will never use. The context-switching cost of task capture is high enough that most solo devs abandon them and fall back to text files or sticky notes. The result: lost tasks, lost context, lost focus.







No current tool is built around the solo developer&apos;s actual workflow: deep focus sessions, rapid context switching, and a need for passive (not active) awareness.







5. Scope — MVP (Dummy App / UAT)





In Scope





Task creation (keyboard-first, sub-3-second capture)





Task list view (today / backlog)





Task status: To Do → In Progress → Done





Focus session mode (active task highlighted, UI goes quiet)





Passive timer display during focus session





Basic persistence (local-first via Supabase)





Cross-platform: React Native (iOS + Android + Desktop via Expo)





Out of Scope (This Phase)





Wearable integration (architecture supports it; build deferred)





AI-powered suggestions or auto-prioritization (data model supports it; build deferred)





Team features of any kind





Calendar integration





Recurring tasks





Tags / labels / projects hierarchy beyond flat list







6. Key Design Constraints (from Muse)





Keyboard-first always. Keyboard-first always.





No interruption during focus mode. No interruption during focus mode.





Sub-3-second task capture. Sub-3-second task capture.





Anti-team-tool aesthetic. Anti-team-tool aesthetic.







7. Technical Constraints (from Helm)





Stack: Stack: React Native (Expo), Supabase (local-first + realtime enabled)





Data model must not preclude: Data model must not preclude: wearable push layer, AI suggestion layer





Wearable architecture: Wearable architecture: display-only output, one-way push via Supabase realtime, Phase 2





Notification model: Notification model: focus session = silent, no background push during focus block





Platform targets (v1): Platform targets (v1): iOS + Android. Desktop (Expo Web) as stretch.







8. SWOT Summary





Quadrant

Factor

STRENGTH

Narrow persona, deep pain — solo devs underserved by team tools

STRENGTH

Low infrastructure cost — Helm&apos;s stack keeps burn negligible at v1

STRENGTH

Flow protection as core value prop and defensible moat

STRENGTH

Wearable-ready architecture without wearable build cost

WEAKNESS

Crowded category — high switching cost vs entrenched tools

WEAKNESS

Solo devs are hard to monetize — freemium with clear value gate required

WEAKNESS

No network effect — growth is purely pull-based

WEAKNESS

Dummy app may generate false signal if used for real concept validation

OPPORTUNITY

AI integration expected — clean data model makes it low-friction later

OPPORTUNITY

Anti-team-tool positioning is a genuine marketing angle

OPPORTUNITY

Wearable as PR hook even before v1 ships

OPPORTUNITY

Build-in-public distribution via developer community

THREAT

Linear and Notion moving toward solo/indie use cases

THREAT

AI-native clones are low-barrier to build

THREAT

Apple/Google platform risk on wearable integration

THREAT

Attention economics — no second chance if onboarding fails







9. Success Criteria (UAT)



This dummy app passes UAT if all of the following are met:





A task can be created from cold launch in under 3 seconds





Focus session mode activates and suppresses all non-essential UI





Task state persists across app restarts (Supabase local-first confirmed)





The pipeline (Antigravity → build → deploy) executes cleanly end-to-end





No wearable features are present in the build (deferred phase confirmed clean)







10. Open Questions





Maxwell to confirm: is this dummy app also a real concept validation, or pure pipeline UAT?





Monetization model TBD if concept validation proceeds beyond dummy





Desktop (Expo Web) as v1 target or Phase 2 — Helm to decide based on pipeline scope





Build-in-public strategy — Maxwell&apos;s call





Drive write access — pipeline gap flagged for Antigravity resolution (Helm)











PRD authored by Scout — Hammerfall Solutions. Status: Staged for Review.






