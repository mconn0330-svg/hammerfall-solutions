# Hammerfall Solutions — Architecture Pivot Plan
**IDE-First Model · Agent Memory Rewrite · Project Helm Clone**
*March 2026 · v1.0 · Confidential*

> **What this document is:** A complete task list for bringing the hammerfall-solutions repo in line with the new architecture. Every file that must be deleted, rewritten, or created is listed with explicit instructions. Execution Helm runs this in Antigravity.

---

## 1. What Changed and Why

> **PIVOT TRIGGER:** UAT v1.2 on dummy-app exposed a fundamental architectural problem: the fragmented environment (Claude.ai Project + Google Drive + Antigravity + Gemini) created more integration failures than it solved. A subsequent test running everything through the IDE alone produced dramatically better results — agents coordinated autonomously, memory persisted naturally via the repo, and the pipeline ran without Maxwell as the relay.

### 1.1 What the UAT Proved

- Agent coordination works well when all agents share a common environment and filesystem
- Google Drive as a memory and staging store failed in every write test — it is out
- Claude.ai Project platform memory does not persist reliably across sessions — it is out as primary memory
- The repo IS the brain. Every artifact, every memory, every decision lives in .md files committed to Git
- Replit to Antigravity handoff worked well once agents resolved setup hurdles — that flow stays
- Helm PR gatekeeping failed because Core Helm was walled off in a separate environment — this is the architecture problem being fixed

### 1.2 The New Model in One Paragraph

The IDE is the primary interface on desktop. Claude Code on mobile/desktop apps connects to the hammerfall-solutions repo and absorbs agent personas from .md files — no manual seeding, no platform memory tricks. All artifacts are .md files committed to Git. Memory is automatic — agents journal their own scratchpad and long-term files without waiting for Maxwell to say "log this." A Project Helm clone lives inside every project repo, acts as chief of staff, and syncs upward to Core Helm on a schedule. Google Drive and Claude.ai platform memory are retired from the pipeline.

### 1.3 What Stays the Same

- Replit builds production React frontend on replit/ui-v1 branch
- Antigravity runs the full build with PM, FE, BE, QA, UX Lead agents
- PR-first rule: no branch absorbs another without a merged PR
- Maxwell makes all merge decisions — HIL is non-negotiable
- The 3-Round Debate for technical disagreements
- bootstrap.sh creates the project repo structure
- Gemini stays for Antigravity worker-tier agents (cost management)

---

## 2. The New Architecture

### 2.1 Interface Layer

| Surface | Role |
|---|---|
| IDE (Antigravity standing session) | Primary desktop interface. Full agent coordination. All file operations. Scheduled sync jobs. |
| Claude Code — Desktop App | Secondary desktop interface. Same repo access. Helm persona from .md files. Persistent across devices. |
| Claude Code — Mobile App | Mobile interface. Validated in test — full agent coordination confirmed. Same repo = same brain. |
| Claude.ai Project (Hammerfall Command) | Retained for ideation and high-level strategy only. Not used for memory, staging, or execution. |

### 2.2 Memory Model

> **CORE PRINCIPLE:** The repo is the memory. No Google Drive. No platform memory. All agent state lives in .md files committed to Git. Agents journal automatically — no "log this" command required for routine updates. Maxwell still has a manual override for significant decisions.

| Memory File | Purpose and Update Trigger |
|---|---|
| `ShortTerm_Scratchpad.md` | Active working memory for the current session. Agent writes to it continuously. Flushed at session end after transfer to long-term. |
| `BEHAVIORAL_PROFILE.md` | Architectural decisions, Maxwell preferences, patterns learned. Updated automatically when significant decisions are made. Most important file. |
| `LongTerm/MEMORY_INDEX.md` | One-line card catalog of all archived events. Updated after every launch, merge, and significant decision. |
| `LongTerm/[Date]_[Topic].md` | Dense permanent archive of a specific event. Written once, never edited. |

### 2.3 Project Helm Clone

Every project bootstrapped by Helm gets a Project Helm instance — a copy of the Helm agent files scoped to that project. Project Helm is chief of staff for the build team. He does not replace Core Helm; he extends him.

| Responsibility | Project Helm vs Core Helm |
|---|---|
| PR gatekeeping | Project Helm — lives in the repo, reviews PRs directly |
| Agent coordination | Project Helm — works with PM, FE, BE, QA, UX Lead daily |
| SITREP consumption | Project Helm — receives updates from PM automatically |
| Strategic direction | Core Helm — sets architectural direction, Maxwell liaison |
| Cross-project learning | Core Helm — syncs from all projects, updates BEHAVIORAL_PROFILE |
| Memory sync (upward) | Project Helm writes → Core Helm reads on sync schedule |

### 2.4 Scheduled Sync

One scheduled job. Core Helm reads `active-projects.md`, iterates all active project repos, consumes Project Helm memory updates, and updates his own `BEHAVIORAL_PROFILE.md`.

| Schedule | Trigger |
|---|---|
| 7:00 AM daily | Core Helm morning sync — reads all active project memories, updates BEHAVIORAL_PROFILE |
| 12:00 PM daily | Core Helm midday sync — same routine, catches morning build progress |
| 6:00 PM daily | Core Helm evening sync — end of day consolidation |
| On demand | Maxwell says "Helm, sync now" — runs same routine immediately |

### 2.5 Data Flow

> **THE RULE:** All agent outputs → .md → committed to repo. All memory → .md → committed to repo. All staging artifacts → .md → `staging_area/` in hammerfall-solutions. The only time a .docx or .gdoc enters the pipeline is if Maxwell manually provides it. Agents never produce .docx.

---

## 3. Full File Audit

*Current state of hammerfall-solutions main branch as of March 25, 2026. Every file assessed against the new architecture.*

**Action key:** `DELETE` · `REWRITE` · `UPDATE` · `NEW` · `KEEP`

### 3.1 Root Level

| File / Folder | Action | Reason |
|---|---|---|
| `README.md` | REWRITE | References Google Drive, Claude.ai Project workflow, old memory model. Full rewrite to new architecture. |
| `bootstrap.sh` | REWRITE | Missing: Project Helm clone step, active-projects.md update, Drive references present. Full rewrite. |
| `.claude/` | UPDATE | Review contents — may contain stale tool config or Drive references. |

### 3.2 agents/helm/

| File / Folder | Action | Reason |
|---|---|---|
| `helm_prompt.md` | REWRITE | Heavy Drive references, Claude.ai platform memory instructions, old "log this" routing, old Routine 1 (staging watch via Drive). Full rewrite for new model. |
| `memory/ShortTerm_Scratchpad.md` | UPDATE | Add auto-journal instructions to helm_prompt.md so Helm maintains this automatically. |
| `memory/BEHAVIORAL_PROFILE.md` | KEEP | Existing decisions are valid. No structural change needed. |
| `memory/LongTerm/MEMORY_INDEX.md` | KEEP | Valid as-is. |
| `memory/LongTerm/*.md` | KEEP | Permanent archives — never modified. |

### 3.3 agents/scout/

| File / Folder | Action | Reason |
|---|---|---|
| `scout_prompt.md` | REWRITE | References Google Drive staging push, Claude.ai platform memory. Rewrite for repo-based staging, automatic memory journaling. |
| `memory/` | UPDATE | Add ShortTerm_Scratchpad.md if missing. Ensure BEHAVIORAL_PROFILE.md exists. |

### 3.4 agents/muse/

| File / Folder | Action | Reason |
|---|---|---|
| `muse_prompt.md` | REWRITE | Same issues as Scout — Drive references, old memory model. Rewrite for repo-based staging, automatic memory journaling. |
| `memory/` | UPDATE | Add ShortTerm_Scratchpad.md if missing. Ensure BEHAVIORAL_PROFILE.md exists. |

### 3.5 management/

| File / Folder | Action | Reason |
|---|---|---|
| `COMPANY_BEHAVIOR.md` | REWRITE | Memory section references Google Drive. "The Bridge" section describes Maxwell as manual relay. Rewrite memory protocol. Keep comms style, technical baseline, 3-round debate, merge protocol. |

### 3.6 project_structure_template/

| File / Folder | Action | Reason |
|---|---|---|
| `CLAUDE.md` | UPDATE | Add PR-first rule explicitly. Add Supabase auth re-login to startup sequence. |
| `Project_Rules` | UPDATE | Reconcile the two Project Rules files found in UAT — pick one canonical version, delete the other. |
| `REPLIT_INSTRUCTIONS.md` | KEEP | Validated in UAT — agent read and followed it. No changes needed. |
| `agents/helm/` (template) | NEW | Add Project Helm template folder. Must include: helm_prompt.md (project-scoped), memory/ShortTerm_Scratchpad.md, memory/BEHAVIORAL_PROFILE.md, memory/LongTerm/MEMORY_INDEX.md. |
| `orchestration.md` | DELETE | Confirmed vestigial in UAT. Remove. |
| `specs/incoming/` | DELETE | Pre-staging drop zone superseded by staging_area/ pattern. Remove from template. |

### 3.7 Root Level — New Files Required

| File | Action | Reason |
|---|---|---|
| `active-projects.md` | NEW | Manifest of all live project repos with local paths. Core Helm reads this for scheduled sync. Helm maintains it as projects launch and complete. |
| `scripts/sync_projects.sh` | NEW | Shell script Core Helm runs for scheduled and on-demand syncs. Iterates active-projects.md, reads each project Helm memory, updates Core BEHAVIORAL_PROFILE.md. |

### 3.8 scripts/

| File | Action | Reason |
|---|---|---|
| `watch_log.md` (if present) | DELETE | Artifact of the old Drive staging watch routine. No longer needed. |
| Any Drive-related scripts | DELETE | Google Drive is out of the pipeline entirely. |
| `sync_projects.sh` | NEW | See 3.7 above. |

---

## 4. Execution Task List

> **WHO RUNS THIS:** Execution Helm in Antigravity. Maxwell opens hammerfall-solutions on main, pastes the Execution Helm startup prompt, and says: *"Run the Architecture Pivot Plan."* Helm works through every task in order, commits after each phase, and reports completion.

---

### Phase 1 — Cleanup

*Run first. Creates a clean baseline before any rewrites. One commit at the end of this phase.*

| Task | File / Location | Action |
|---|---|---|
| 1.1 | `project_structure_template/orchestration.md` | Delete file |
| 1.2 | `project_structure_template/specs/incoming/` | Delete folder and contents |
| 1.3 | Duplicate `Project_Rules` in template | Identify both files, keep the one matching COMPANY_BEHAVIOR.md, delete the other |
| 1.4 | `scripts/watch_log.md` (if exists) | Delete file |
| 1.5 | Any scripts referencing Google Drive | Delete or move to `scripts/deprecated/` |

**Commit:** `chore: phase 1 cleanup — remove stale files and deprecated Drive scripts`

---

### Phase 2 — COMPANY_BEHAVIOR.md Rewrite

*The global law document. All agents read this. Gets it right before touching individual agent prompts.*

- **KEEP:** Communication Style, Operational Rules, Technical Baseline, 3-Round Debate, Merge Protocol
- **REWRITE:** Memory Protocol section — remove all Drive references, remove Claude.ai platform memory references, replace with repo-based automatic journaling model
- **ADD:** PR-First Rule — no branch absorbs another without a merged PR
- **ADD:** `.md everywhere` rule — all agent outputs are .md files, no .docx, no .gdoc
- **REMOVE:** "The Bridge" section — Maxwell is no longer the manual relay between environments

**New Memory Protocol (replace existing section with this):**

```
All memory lives in the repo as .md files. Agents maintain their own
ShortTerm_Scratchpad.md during sessions and transfer to BEHAVIORAL_PROFILE.md
at session end. No "log this" required for routine updates — agents journal
automatically. Maxwell may say "log this" to flag a decision for immediate
explicit documentation. No Google Drive. No platform memory.
The repo is the single source of truth.
```

**Commit:** `docs: rewrite COMPANY_BEHAVIOR.md — repo-based memory model, PR-first rule, .md everywhere`

---

### Phase 3 — Agent Prompt Rewrites

*Rewrite all four agent prompts in sequence. Maxwell review gate after this phase before proceeding.*

#### Task 3.1 — helm_prompt.md (Core Helm)

- **REMOVE:** Routine 1 (staging watch via Drive) — entire section deleted
- **REMOVE:** All `C:\Users\xbox5\My Drive\...` path references
- **REMOVE:** `memory-queue.gdoc` references
- **REMOVE:** Claude.ai Project / Antigravity split identity — Helm now operates in one primary environment
- **REWRITE:** Context section — Helm operates primarily in IDE. Claude Code on mobile/desktop for remote access.
- **REWRITE:** Memory Management section — automatic journaling, scratchpad → long-term transfer at session end, no manual triggers required
- **REWRITE:** Routine 2 (Project Launch) — remove Drive staging read, replace with read from `staging_area/` in repo
- **REWRITE:** Routine 4 (log this) — simplify to direct file write only, no Drive fallback
- **ADD:** Routine 5 — Scheduled Sync. Reads `active-projects.md`, iterates repos, consumes Project Helm memories, updates `BEHAVIORAL_PROFILE.md`. Runs on schedule (7am/12pm/6pm) and on Maxwell's "Helm, sync now" command.
- **UPDATE:** Staging Watch — reads `staging_area/` in repo directly, not Drive

#### Task 3.2 — scout_prompt.md

- **REMOVE:** All Google Drive staging push instructions
- **REMOVE:** Platform memory references
- **REWRITE:** Staging output — Scout commits PRD as .md to `staging_area/[codename]/` in hammerfall-solutions repo
- **ADD:** Automatic memory journaling — Scout maintains `ShortTerm_Scratchpad.md` and `BEHAVIORAL_PROFILE.md` in `agents/scout/memory/` without prompting
- **KEEP:** JTBD methodology, market validation approach, SWOT as table preference
- **KEEP:** `@Muse` handoff ping after PRD staged

#### Task 3.3 — muse_prompt.md

- **REMOVE:** All Google Drive staging push instructions
- **REMOVE:** Platform memory references
- **REWRITE:** Staging output — Muse commits Blueprint and StyleGuide as .md to `staging_area/[codename]/` in repo
- **ADD:** Automatic memory journaling — same pattern as Scout
- **KEEP:** Technical Blueprint precision, UX constraint approach, information density principles
- **KEEP:** `@Helm` handoff ping after Blueprint staged

#### Task 3.4 — Project Helm Template (NEW FILE)

Create `project_structure_template/agents/helm/helm_prompt.md` — the Project Helm persona.

- **Identity:** Project Helm, chief of staff for `[PROJECT_NAME]`. Scoped to this project only.
- **Core Helm relationship:** Reports upward. Syncs memory to Core Helm on schedule. Does not override Core Helm decisions.
- **Primary responsibilities:** PR gatekeeping for this project, agent coordination with PM, SITREP consumption, project memory management
- **Memory:** Maintains `agents/helm/memory/` within the project repo — ShortTerm_Scratchpad.md, BEHAVIORAL_PROFILE.md, LongTerm/
- **Auto-journal:** Same automatic journaling protocol as Core Helm
- **Sync flag:** Writes a sync-ready flag to memory when significant events occur so Core Helm can detect updates on scheduled sync
- **PR gatekeeping:** Full 3-Round Debate authority within the project. Escalates to Maxwell (not Core Helm) for unresolved disputes.

Also create supporting memory files in template:

- `project_structure_template/agents/helm/memory/ShortTerm_Scratchpad.md` — blank with header
- `project_structure_template/agents/helm/memory/BEHAVIORAL_PROFILE.md` — blank with header and instructions
- `project_structure_template/agents/helm/memory/LongTerm/MEMORY_INDEX.md` — blank with header

**Commit:** `feat: phase 3 — rewrite all agent prompts, add Project Helm template`

> ⚠️ **MAXWELL REVIEW GATE — Pause here. Helm reports. Maxwell spot-checks rewritten prompts before Phase 4.**

---

### Phase 4 — bootstrap.sh Rewrite

*The factory script. Must implement new architecture from day one of every project.*

- **REMOVE:** Steps referencing Google Drive
- **KEEP:** Steps 1–12 (scaffold, inject rules, inject Replit instructions, inject specs, git init, create GitHub repo, branches, Supabase init, npm install, initial SITREP)
- **ADD** after scaffold step: Copy `project_structure_template/agents/helm/` into new repo as `agents/helm/` — this creates Project Helm
- **ADD:** Replace `[PROJECT_NAME]` placeholder in Project Helm prompt with actual codename
- **ADD:** Update `active-projects.md` in hammerfall-solutions with new project entry (name, repo path, launch date, status: active)
- **ADD:** Supabase login reminder — print explicit instruction for Maxwell to run `supabase login` if needed
- **ADD:** PR-first reminder in initial SITREP — explicit note that replit/ui-v1 changes must go through PR before Antigravity absorbs them
- **FIX:** Duplicate Project_Rules issue — script copies exactly one file (`PROJECT_RULES.md` from template)

**Commit:** `feat: phase 4 — rewrite bootstrap.sh for new architecture, add Project Helm clone step`

> ⚠️ **MAXWELL REVIEW GATE — Pause here. Helm reports. Maxwell reviews bootstrap.sh before Phase 5.**

---

### Phase 5 — New Infrastructure Files

#### Task 5.1 — active-projects.md (repo root)

Create `hammerfall-solutions/active-projects.md`:

```markdown
# Active Projects

Maintained by Core Helm. Updated on every bootstrap and project completion.
Core Helm reads this file on every scheduled sync to determine which repos to scan.

| Codename | Repo Path | Launch Date | Status |
|---|---|---|---|
| dummy-app | ../Hammerfall-dummy-app | 2026-03-XX | active (testing) |
```

#### Task 5.2 — scripts/sync_projects.sh

Create the sync script Core Helm calls for scheduled and on-demand syncs:

- Reads `active-projects.md` and extracts all active project repo paths
- For each active project: reads `agents/helm/memory/BEHAVIORAL_PROFILE.md` and `ShortTerm_Scratchpad.md`
- Appends relevant learnings to `hammerfall-solutions/agents/helm/memory/BEHAVIORAL_PROFILE.md` with project attribution and date
- Updates `LongTerm/MEMORY_INDEX.md` with sync entry
- Commits: `memory: core sync — [date]`
- Prints summary to stdout: projects synced, entries added, any errors

#### Task 5.3 — Scheduled Tasks Setup

After script is committed, set up three daily scheduled tasks in Claude Code using `/schedule`:

```
/schedule — "Core Helm morning sync"  — 7:00 AM daily  — runs scripts/sync_projects.sh
/schedule — "Core Helm midday sync"   — 12:00 PM daily — runs scripts/sync_projects.sh
/schedule — "Core Helm evening sync"  — 6:00 PM daily  — runs scripts/sync_projects.sh
```

*Scheduled tasks must be set up in a live Claude Code session. Helm confirms setup after commit.*

**Commit:** `feat: phase 5 — add active-projects.md, sync script, scheduled task setup`

---

### Phase 6 — README.md Rewrite

*Final step. README reflects the completed new architecture.*

- **REMOVE:** All Google Drive references
- **REMOVE:** Claude.ai Project as primary workflow interface
- **REMOVE:** Old memory architecture section
- **REWRITE:** How to Launch a Project — new flow: Ideation in IDE → Stage specs to repo → Go word → Bootstrap → Replit build → Antigravity build
- **REWRITE:** Memory Architecture section — repo-based, automatic journaling, Project Helm sync
- **ADD:** Interface options section — IDE, Claude Code desktop, Claude Code mobile
- **ADD:** Project Helm section — brief explanation of clone model
- **UPDATE:** Org chart — add Project Helm as a role

**Commit:** `docs: phase 6 — rewrite README for new architecture`

---

## 5. Execution Sequence and Commit Map

| Phase | Commit Message |
|---|---|
| Phase 1 — Cleanup | `chore: phase 1 cleanup — remove stale files and deprecated Drive scripts` |
| Phase 2 — COMPANY_BEHAVIOR | `docs: rewrite COMPANY_BEHAVIOR.md — repo-based memory model, PR-first rule, .md everywhere` |
| Phase 3 — Agent Prompts | `feat: phase 3 — rewrite all agent prompts, add Project Helm template` |
| Phase 4 — bootstrap.sh | `feat: phase 4 — rewrite bootstrap.sh for new architecture, add Project Helm clone step` |
| Phase 5 — Infrastructure | `feat: phase 5 — add active-projects.md, sync script, scheduled task setup` |
| Phase 6 — README | `docs: phase 6 — rewrite README for new architecture` |

### How to Initiate

Open hammerfall-solutions on main in Antigravity. Paste Execution Helm startup prompt. Say:

> *"Read the Architecture Pivot Plan. Run all six phases in order. Pause after Phase 3 and Phase 4 for my review. Commit after each phase. Report when complete."*

### Validation Checklist — After All Phases Complete

| Check | Where to Look | Pass Criteria |
|---|---|---|
| No Drive references remain | `grep -r "Google Drive" .` across all .md files | Zero results |
| No Drive paths remain | `grep -r "My Drive" .` across all .md files | Zero results |
| Project Helm template exists | `project_structure_template/agents/helm/` | Folder with helm_prompt.md and memory/ subfolder |
| active-projects.md exists | repo root | File present with dummy-app entry |
| sync_projects.sh exists | `scripts/` | File present and executable |
| orchestration.md gone | `project_structure_template/` | File does not exist |
| specs/incoming gone | `project_structure_template/` | Folder does not exist |
| bootstrap.sh clone step present | `bootstrap.sh` | Contains: copy agents/helm template step |
| COMPANY_BEHAVIOR no Drive | `management/COMPANY_BEHAVIOR.md` | No Drive references, new memory protocol present |
| README current | `README.md` | Reflects new architecture, no Drive references |

---

## 6. Open Items and Known Gaps

*Real issues from UAT not addressed by this plan. Logged so nothing is lost. Address in follow-up sprint.*

| Item | Detail and Suggested Path |
|---|---|
| Supabase org configuration | MCP connects to IBIS org, not new projects. Add explicit `supabase login` step to Execution Helm startup sequence AND to bootstrap output instructions. Determine whether bootstrap should create the Supabase project or require Maxwell to do it first. |
| Replit branch import | Replit does not allow branch selection on import — builds from default branch. REPLIT_INSTRUCTIONS.md must be on main or Replit must be told to switch branch after connecting. Validate current behavior. |
| Merge conflict protocol | UAT Test 7.1 produced conflicts when Antigravity absorbed Replit changes without PR merge. PR-first rule is now in COMPANY_BEHAVIOR.md. Add explicit conflict resolution steps to CLAUDE.md in project template. |
| TASKS.md location | UAT noted task .md files created in specs/ folder. Define canonical TASKS.md location in project template and update CLAUDE.md accordingly. |
| Claude Code mobile validation | Mobile test was promising but only one test on one concept. Run a full bootstrap-to-build cycle before declaring it production-ready. |
| dummy-app disposition | Repo is in an indeterminate state after UAT. Decision needed: re-bootstrap with new architecture as the first validation test, or archive it. |

---

> **RECOMMENDED FIRST ACTION AFTER PIVOT:** Once all six phases are committed, re-bootstrap dummy-app from scratch using the new bootstrap.sh. This is the validation test for the entire pivot. If the new architecture produces a clean project repo with Project Helm present, memory files initialized, and no Drive references anywhere — the pivot is confirmed.

---

*Hammerfall Solutions · Architecture Pivot Plan · v1.0 · March 2026*
