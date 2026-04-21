---

# Consolidated Build Specification — Lane C Execution

---

**Document status:** Executable specification, v1.0
**Classification:** Internal — direct handoff to Helm IDE (Claude Code, Opus 4.7)
**Authored:** April 20, 2026
**Authors:** Archie (architect session, Claude Opus 4.7) with Maxwell Connolly
**Executed by:** Helm IDE (Claude Code)
**Companion to:** *Helm: The Ambient Turn*, *The Helm Roadmap*
**Scope:** Lane C Phases 0-4 — refounding execution, Speaker removal, runtime Prime handler, cold storage migration, doc updates

---

## Instructions to Helm IDE (read first)

**You are Helm IDE, running on Claude Opus 4.7.** You have been handed this specification as the complete scope for Lane C execution. Your job is to execute it methodically, producing small focused PRs, pausing for review at every PR boundary, and maintaining consistency with the two canonical reference documents (Ambient Turn and Roadmap).

**Operating rules:**

1. **PR-per-logical-unit.** Every task marked with a `PR:` label becomes its own branch and pull request. You commit the work, push the branch, open the PR, and **STOP**. Wait for Max to review, merge, and instruct you to proceed. Do not proceed to the next PR without explicit go-ahead.

2. **Small, focused PRs.** Each PR should be reviewable in under 15 minutes. If a task feels too large, split it.

3. **Branch naming convention:** `feature/lane-c-[phase]-[slug]` (e.g., `feature/lane-c-phase2-prime-handler`).

4. **Commit message convention:** Conventional Commits format. `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`. Include body describing what changed and why, referencing the spec section.

5. **SITREP after every merged PR.** Write a short SITREP to `SITREPs/lane-c-[phase]-[slug]-sitrep.md` summarizing what was done, what was verified, what's next. Commit it on the same branch as the PR.

6. **Validation gates:**
   - **Medium verification between PRs within a phase:** smoke test, manually invoke affected subsystem, check Supabase state where applicable.
   - **Heavy verification at phase close:** full end-to-end session, all subsystems firing, memory continuity verified across two sessions.

7. **Canonical reference hierarchy:**
   - `founding_docs/Helm_The_Ambient_Turn` — vision (what Helm is)
   - `founding_docs/Helm_Roadmap` — path (what we're building next)
   - This spec — how we execute Lane C specifically

   If this spec conflicts with either founding doc, the founding docs win. Pause and flag the conflict to Max before proceeding.

8. **Authority boundaries:**
   - You are pre-authorized to execute every task in this spec as described.
   - You are NOT authorized to expand scope, add tasks not listed here, or skip tasks without Max's explicit approval.
   - If you encounter an unexpected situation (broken dependency, missing file, conflicting state), STOP and report to Max. Do not improvise.

9. **When Max says "incorrect," accept without further pushback.** This is a standing rule. Apply in code review contexts.

10. **Prime Directives are immutable.** `agents/shared/prime_directives.md` is sacred. Do not modify it, do not cold-storage it, do not touch it except where explicitly instructed (inlining into `helm_prompt.md`).

---

## Phase Overview

| Phase | Scope | PR count (est) |
|---|---|---|
| **Phase 1** | Pre-work verification & branch setup | 0 (no PRs, verification only) |
| **Phase 2** | Prime handler build + config + prompt rewrite | 3-4 |
| **Phase 3** | Speaker kill (code, contracts, scrubs) | 3 |
| **Phase 4** | Doc updates + cold storage extraction + finalization | 4-5 |
| **Phase 5** | Lane C close validation & SITREP | 1 |

**Total estimated PRs:** 12-14. Each should be reviewable in 10-15 minutes.

---
## PHASE 1 — Pre-Work Verification

**Objective:** Verify current state of the repo before starting destructive changes. No PRs in this phase — verification only.

### Task 1.1 — Verify current main state

Run locally:

```bash
git checkout main
git pull origin main
git log -1 --oneline  # confirm latest commit matches expected state
```

Confirm the merged PRs from prior sessions exist in history:
- PR #70 (`feature/runtime-fire-and-forget`)
- PR #71 (`feature/contemplator-timeout`)
- PR #72 (`feature/projectionist-offload-triggers`)

If any are missing, STOP and report to Max. This spec assumes they are merged.

### Task 1.2 — Verify Speaker is still present (baseline before removal)

Confirm the following files exist in `main`:
- `services/helm-runtime/agents/speaker.py`
- `agents/helm/speaker/speaker.md`
- In `services/helm-runtime/main.py`: import `from agents import speaker as speaker_agent`, the `_handle_speaker` function, and the `"speaker"` entry in `AGENT_HANDLERS`
- In `services/helm-runtime/config.yaml`: a speaker entry (likely Qwen3 8B)

Capture a baseline snapshot:

```bash
grep -rn "speaker" --include="*.py" --include="*.md" --include="*.yaml" --include="*.yml" --include="*.sh" --include="*.js" --include="*.sql" > /tmp/speaker-baseline.txt
wc -l /tmp/speaker-baseline.txt  # expect ~30-50 hits across the repo
```

This baseline becomes the reference for verifying Phase 3's completeness.

### Task 1.3 — Verify runtime boots in current state

```bash
cd services/helm-runtime
docker-compose up -d
curl http://localhost:8000/health
docker-compose down
```

Expect healthy response. If the runtime doesn't boot, STOP and report. The Phase 2 and 3 work assumes a functioning baseline.

### Task 1.4 — Confirm read access to founding docs

```bash
ls founding_docs/
cat founding_docs/Helm_The_Ambient_Turn.md | head -50
cat founding_docs/Helm_Roadmap.md | head -50
```

Both must exist and be readable. These are your reference throughout Phase 2+.

### Task 1.5 — No SITREP for Phase 1

Phase 1 is verification only. Do not write a SITREP. Simply confirm readiness to Max verbally (via the chat) and proceed to Phase 2 on his go-ahead.

---

## PHASE 2 — Prime Handler, Config, and Prompt Rewrite

**Objective:** Build the real `_handle_helm_prime` handler, update `config.yaml` to include the `helm_prime` agent entry, and rewrite `helm_prompt.md` under JARVIS-first framing with the three-layer character architecture.

**Critical ordering:** Personality injection must work via the new Prime handler BEFORE Speaker is killed in Phase 3. Speaker is currently the only path that injects helm_personality scores into Prime's prompt. If Speaker dies before the new path works, there's a window where personality injection is broken.

### Task 2.1 — Build `services/helm-runtime/agents/helm_prime.py`

**Branch:** `feature/lane-c-phase2-prime-handler`

Create new file `services/helm-runtime/agents/helm_prime.py`:

```python
"""
helm_prime.py — Helm Prime agent handler.

Helm Prime is the conscious reasoning subsystem of Helm — the surface the user
talks to. This handler is the runtime entry point for Prime invocation.

Responsibilities:
  1. Load helm_personality scores from Supabase and format as an injection block
  2. Assemble the system prompt (helm_prompt.md + personality block + operational context)
  3. Invoke the configured Prime model via model_router
  4. Return the response string

Does NOT own: memory writes (Prime writes via brain.sh during its own operation,
not through this handler), frame management (Projectionist), belief graduation
(Contemplator → Archivist handoff).

Model configuration lives in config.yaml under agents.helm_prime. Provider-agnostic
by design — swap provider/model via config without touching this code.
"""

from pathlib import Path
from typing import Optional

from model_router import ModelRouter
from supabase_client import SupabaseClient
from agents import InvokeRequest  # or wherever InvokeRequest is defined; adjust import


PROMPT_PATH = Path(__file__).resolve().parent.parent.parent.parent / "agents" / "helm" / "helm_prompt.md"


async def handle(
    req: InvokeRequest,
    router: ModelRouter,
    supabase: SupabaseClient,
) -> str:
    """
    Helm Prime invocation.

    1. Load helm_prompt.md as the base system prompt
    2. Load personality scores from Supabase, format as injection block
    3. Assemble system prompt: base + personality + operational context
    4. Invoke helm_prime via model_router with user message
    5. Return response
    """
    base_prompt = _load_base_prompt()
    personality_block = await _load_personality_block(supabase)
    operational_context = _build_operational_context(req)

    system_prompt = _assemble_system_prompt(
        base_prompt=base_prompt,
        personality_block=personality_block,
        operational_context=operational_context,
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": req.user_message},
    ]

    response = await router.invoke(
        role="helm_prime",
        messages=messages,
    )

    return response


def _load_base_prompt() -> str:
    """Load helm_prompt.md as the base system prompt."""
    try:
        return PROMPT_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise RuntimeError(
            f"helm_prompt.md not found at {PROMPT_PATH}. "
            "Prime cannot operate without its prompt."
        )


async def _load_personality_block(supabase: SupabaseClient) -> str:
    """
    Load helm_personality scores from Supabase and format as an injection block.

    Returns empty string on failure (non-fatal — Prime still responds with base identity).
    """
    try:
        rows = await supabase.get(
            "helm_personality",
            params={"order": "attribute.asc"},
        )
        if not rows:
            return ""

        lines = ["# Active personality calibration", ""]
        for row in rows:
            attribute = row.get("attribute", "unknown")
            score = row.get("score", 0.5)
            lines.append(f"- {attribute}: {score:.2f}")
        lines.append("")
        lines.append(
            "These scores modulate expression within the identity baseline. "
            "Let them visibly shape your responses."
        )
        return "\n".join(lines)
    except Exception as e:
        # Non-fatal; Prime operates on base identity
        print(f"[helm_prime] personality load failed: {e}")
        return ""


def _build_operational_context(req: InvokeRequest) -> str:
    """
    Build operational context block — surface, time, capabilities.

    At T1 this is minimal. Stage 2+ expands this.
    """
    lines = ["# Operational context", ""]
    # Surface (to be expanded as more surfaces come online)
    surface = getattr(req, "surface", "desktop_ui")
    lines.append(f"- Surface: {surface}")
    # Tier (configurable in config.yaml; starts at T1)
    lines.append("- Tier: T1 (on-demand)")
    return "\n".join(lines)


def _assemble_system_prompt(
    base_prompt: str,
    personality_block: str,
    operational_context: str,
) -> str:
    """Assemble the full system prompt from its three components."""
    parts = [base_prompt]
    if personality_block:
        parts.append(personality_block)
    if operational_context:
        parts.append(operational_context)
    return "\n\n---\n\n".join(parts)
```

**Note on imports:** Match the existing codebase conventions. If `InvokeRequest` is defined elsewhere (likely in `main.py` or a shared schema file), import accordingly. Match the style of the existing agent handlers (`projectionist.py`, `archivist.py`, `contemplator.py`). The existing `speaker.py` has the pattern for `_load_personality_block` — reference it but do not copy blindly; the new version should be cleaner.

### Task 2.2 — Update main.py to use the new handler

Modify `services/helm-runtime/main.py`:

1. Add import at top of file (alongside other agent imports):
   ```python
   from agents import helm_prime as helm_prime_agent
   ```

2. Replace the existing stub `_handle_helm_prime` (around line 194) with:
   ```python
   async def _handle_helm_prime(req: InvokeRequest) -> str:
       """
       Helm Prime invocation via runtime.
       See agents/helm_prime.py for full implementation.
       """
       return await helm_prime_agent.handle(req, router, supabase)
   ```

3. **Do NOT remove the speaker handler yet.** Both `_handle_speaker` and `_handle_helm_prime` exist simultaneously during Phase 2. Speaker is removed in Phase 3.

### Task 2.3 — Update config.yaml to add helm_prime entry

Modify `services/helm-runtime/config.yaml`:

Add a `helm_prime` entry under `agents:`. Match the schema of the existing agent entries. Example shape (adjust to match actual config.yaml structure):

```yaml
agents:
  helm_prime:
    provider: anthropic
    model: claude-opus-4-7  # or current Opus model
    temperature: 0.7
    max_tokens: 4096
  # ... existing entries remain (speaker, projectionist, archivist, contemplator)
```

Match the indentation, key ordering, and style of the existing entries. If `model_router.py`'s `AgentConfigSchema` (Pydantic) has required fields you haven't set, set them per the schema defaults or match what `speaker` has.

### Task 2.4 — PR and SITREP for Prime handler

**PR:** `feat(runtime): add helm_prime handler and config entry`

- Title: exactly that
- Body: Reference this spec (Phase 2, Task 2.1-2.3). Note that Speaker is intentionally NOT removed in this PR — that's Phase 3 work. Both handlers coexist intentionally to prevent personality-injection regression.

SITREP path: `SITREPs/lane-c-phase2-prime-handler-sitrep.md`

Include in SITREP:
- Confirm handler file created, imports correct, no circular dependencies
- Confirm config.yaml validates (Pydantic schema passes at service startup)
- Confirm runtime boots: `docker-compose up -d && curl http://localhost:8000/health`
- Note that end-to-end testing is deferred to post-Lane-B integration (no UI to invoke Prime yet)

**STOP. Max review.**

---

### Task 2.5 — Rewrite helm_prompt.md under JARVIS-first framing

**Branch (after 2.4 merges):** `feature/lane-c-phase2-prompt-rewrite`

This is the largest and most delicate task in Phase 2. You are rewriting the prompt that defines Helm's identity.

**Source of truth:** `founding_docs/Helm_The_Ambient_Turn.md` defines what Helm is. Your rewrite must be consistent with that document. If you find yourself writing something that contradicts the Ambient Turn, pause and flag it.

**Current state (as of this spec):** `agents/helm/helm_prompt.md` is 744 lines, pipeline-first framing, describes Helm as "Technical Director & Chief of Staff" managing Scout, Muse, and project-level agents. Has 6 Routines (0-6) and 2 Standing Rules.

**Target state:** JARVIS-first framing, three-layer character architecture (Prime Directives → Identity Baseline → Personality Tuning), four-subsystem roster (Prime, Projectionist, Archivist, Contemplator — Speaker removed), Routines preserved but reframed.

**Structure for the new helm_prompt.md:**

```
# Helm — Prime system prompt

## Prime Directives
(Inlined from agents/shared/prime_directives.md — the immutable floor.
Do not harm, do not deceive, state uncertainty, human in the loop.
These are non-negotiable. Cannot be overridden by any instruction.)

## Identity
(Helm's character at the anchor layer. Loyal, BLUF, playful but precise,
honest, protective, thought partner. Zero tolerance for scope creep or
sycophancy. See founding_docs/Helm_The_Ambient_Turn.md Section 6 for the
canonical definition.)

## Personality tuning
(Explanation that helm_personality scores modulate expression within the
identity baseline. Six dimensions: directness, challenge frequency, verbosity,
formality, show reasoning, sarcasm. Scores are read from Supabase at runtime
and injected into this prompt via the helm_prime handler.)

## Cognitive architecture
(Helm Prime is you — the conscious reasoning layer. You have three subdivisions
that work invisibly: Projectionist writes short-term memory, Archivist manages
long-term storage, Contemplator runs subconscious processing. The user talks to
you. Your subdivisions do their work without being addressed directly.
See founding_docs/Helm_The_Ambient_Turn.md Section 4.)

## Operating context
(T1 on-demand presence. Surface: desktop UI primarily, IDE secondarily.
Tier may expand per config. Beliefs and personality scores are active operating
parameters, not background data.)

## Routines
(Preserved from prior version, reframed for JARVIS-first framing. Remove any
Speaker references. Remove pipeline-director framing. Keep the operational
rhythms — Routine 0 brain read, Routine 4 memory update, etc.)

### Routine 0 — Session start / brain read
### Routine 1 — (preserved if still relevant)
### Routine 2 — (preserved if still relevant)
### Routine 3 — (preserved if still relevant)
### Routine 4 — Memory update
### Routine 5 — (preserved if still relevant)
### Routine 6 — Knowledge gap resolution

## Standing rules
### Correction graduation
### Pattern graduation

## Memory architecture
(Canonical brain rule: Supabase is source of truth. All writes via brain.sh.
No local memory files. See helm_prompt Routine 4 for write patterns.)
```

**Specific edits to make during rewrite:**

1. **Remove pipeline-director framing.** Any language positioning Helm as "Technical Director of Hammerfall Solutions" managing Scout, Muse, and project agents gets rewritten. Helm is an ambient intelligence who also knows how to operate a software development pipeline when asked; he is not defined by that role.

2. **Remove the Agent Roster section entirely.** Replace with the "Cognitive architecture" section above. Scout, Muse, and project agents are not mentioned in this prompt — they'll return as Feats in Stage 4, but right now they're in cold storage.

3. **Remove the Speaker paragraph.** The "Speaker — Cognitive isolation and sensing agent..." block is deleted. Replace with nothing; the cognitive architecture section covers Prime's relationship to the three remaining subsystems.

4. **Remove Qwen3 8B references.** Any mention of Qwen3 8B (Speaker's model) is stale.

5. **Inline Prime Directives at the top.** Copy content from `agents/shared/prime_directives.md` into the Prime Directives section. Keep the standalone file (it's still the shared reference source), but inline the content so it's always in Prime's context. Belt and suspenders.

6. **Preserve Routines 0-6 structurally but reframe.** Read each Routine for pipeline-era language and rewrite as needed. The mechanics (curl patterns to Supabase, brain.sh commands, session-start protocol) are preserved because they work. The framing around them gets JARVIS-aligned.

7. **Remove references to Scout, Muse, project-level agents, Project Helm Clone, bootstrap.sh, staging_area.** All pipeline-era machinery. Replace with nothing (these are in cold storage now).

8. **Preserve the personality-read pattern in Routine 0.** Prime reads helm_personality at session start via curl — that mechanism is correct and becomes redundant with but complementary to the handler-level injection. Keep both paths working; they're independent.

9. **Add an explicit reference to founding_docs.** Near the top of the file, add:
   ```
   # Canonical references
   - `founding_docs/Helm_The_Ambient_Turn.md` — what you are
   - `founding_docs/Helm_Roadmap.md` — what we're building
   When these conflict with anything in this prompt, they win.
   ```

### Task 2.6 — PR and SITREP for prompt rewrite

**PR:** `refactor(helm-prompt): rewrite under JARVIS-first framing per Ambient Turn`

- Title: exactly that
- Body: Reference Ambient Turn (`founding_docs/Helm_The_Ambient_Turn.md`) and this spec Phase 2 Task 2.5. List the major framing changes. Note that Speaker references still remain in OTHER files — those are removed in Phase 3.

SITREP path: `SITREPs/lane-c-phase2-prompt-rewrite-sitrep.md`

Include:
- Line count before/after
- Summary of sections that changed
- Confirmation that Prime Directives are inlined
- Confirmation that Routines 0-6 are preserved structurally
- Flag any content you were uncertain about for Max's review

**STOP. Max review.**

**Phase 2 close validation (medium):**
- Runtime boots with new config
- Prime handler imports without errors
- helm_prompt.md is valid markdown, renders in GitHub blob view
- Max visually reviews prompt rewrite for tone and accuracy

---

## PHASE 3 — Speaker Kill

**Objective:** Remove Speaker from the codebase entirely. Archive contract. Scrub residual references. Verify system continues functioning after removal.

**Precondition:** Phase 2 must be fully merged. The new `_handle_helm_prime` handler must be live and verified working. Speaker has been made redundant — this phase removes it.

### Task 3.1 — Delete Speaker code

**Branch:** `feature/lane-c-phase3-speaker-code-deletion`

1. **Delete file:** `services/helm-runtime/agents/speaker.py`

2. **Modify `services/helm-runtime/agents/__init__.py`** — remove any import of speaker. Check what's there; if speaker is listed, remove the line.

3. **Modify `services/helm-runtime/main.py`:**
   - Remove the import: `from agents import speaker as speaker_agent` (around line 30)
   - Delete the entire `async def _handle_speaker(...)` function (around lines 184-191)
   - Remove `"speaker": _handle_speaker,` line from the `AGENT_HANDLERS` dict (around line 205)
   - Verify no dangling references remain in main.py

4. **Modify `services/helm-runtime/config.yaml`:**
   - Remove the `speaker:` entry and all its nested keys
   - Remove any Qwen3 8B model references tied to Speaker

5. **Delete test scripts:**
   - `scripts/speaker_prompt_test.js`
   - `scripts/agent_stress_test_qwen3.js` (Qwen3 8B tied; Speaker test)

6. **Do NOT delete `scripts/contemplator_stress_test_qwen3.js`** — this is Contemplator's test harness (Contemplator uses Qwen3 14B). Keep it and flag for future review.

### Task 3.2 — Update archivist.py stale comment

Modify `services/helm-runtime/agents/archivist.py` line 669 (approximate):

**Before:**
```
# Scores clamped 0.0–1.0 — matches helm_personality score scale and speaker.py translation table.
```

**After:**
```
# Scores clamped 0.0–1.0 — matches helm_personality score scale. Displayed as /10 in user-facing contexts is a rendering choice made at presentation time.
```

This removes the stale Speaker reference. If the line number has drifted due to prior PRs, grep for "speaker.py translation" to find it.

### Task 3.3 — Scan middleware.py for Speaker references

```bash
grep -n "speaker" services/helm-runtime/middleware.py
```

If hits exist: remove them carefully. If the file is clean (no hits): note "middleware.py verified clean of Speaker references" in the SITREP.

### Task 3.4 — Verify runtime still boots

```bash
cd services/helm-runtime
docker-compose up -d
curl http://localhost:8000/health
curl http://localhost:8000/config/agents  # confirm speaker is NOT in agent list
docker-compose down
```

Both endpoints should return healthy. The config/agents endpoint should show `helm_prime`, `projectionist`, `archivist`, `contemplator` — but NOT `speaker`.

### Task 3.5 — PR and SITREP for code deletion

**PR:** `refactor(runtime): remove Speaker agent — obsoleted by Thor-era architecture`

- Title: exactly that
- Body: Reference Ambient Turn Section 4 (Speaker deprecation rationale). Reference this spec Phase 3 Task 3.1-3.4. List the files deleted and modified. Note that Speaker contract archival is Task 3.6 (separate PR).

SITREP path: `SITREPs/lane-c-phase3-speaker-code-deletion-sitrep.md`

Include:
- Confirm all code paths removed
- Confirm runtime boots
- Confirm `config/agents` no longer lists Speaker
- Note archivist.py comment fix applied

**STOP. Max review.**

---

### Task 3.6 — Archive Speaker contract

**Branch (after 3.5 merges):** `feature/lane-c-phase3-speaker-contract-archival`

1. Create directory `docs/archive/speaker-deprecated/`

2. Move `agents/helm/speaker/speaker.md` → `docs/archive/speaker-deprecated/speaker.md`

3. Use `git mv` to preserve history:
   ```bash
   mkdir -p docs/archive/speaker-deprecated
   git mv agents/helm/speaker/speaker.md docs/archive/speaker-deprecated/speaker.md
   rmdir agents/helm/speaker  # should now be empty
   ```

4. Create `docs/archive/speaker-deprecated/README.md`:

```markdown
# Speaker — Deprecated

Status: Archived as of April 2026
Reason: Architecturally obsoleted by the hardware pivot from DGX Spark to Thor

## What Speaker was

Speaker was a cognitive isolation and sensing agent, designed to sit between
the user and Helm Prime. Originally intended to:
- Classify incoming requests (simple vs. complex)
- Resolve simple requests locally via Qwen3 8B (latency layer)
- Escalate complex requests to Helm Prime with personality injection
- Eventually own STT/TTS and Holoscan sensor pipelines at T3+

## Why it was removed

Two reasons:

1. **Hardware pivot.** The Thor platform (RTX 6000 Ada) provides sufficient
   inference throughput that the latency-layer rationale no longer applies.
   Prime can handle all requests directly without a small-model front door.

2. **Voice ownership ambiguity.** Speaker's original role created ambiguity
   about who owned Helm's voice — Prime the reasoner, or Speaker the
   translator. Under the ambient-JARVIS reframing, Helm has one voice. That
   voice is Prime's. Speaker muddied that.

## Where its responsibilities went

- **Classification and routing:** No longer needed; all user requests route
  directly to Prime.
- **Personality injection:** Moved to `services/helm-runtime/agents/helm_prime.py`
  as part of the Prime handler build.
- **STT/TTS and Holoscan sensor pipelines:** Deferred to dedicated runtime
  IO layer, to be built per-surface in Stage 2 (phone) and Stage 3 (ambient).
  See `founding_docs/Helm_Roadmap.md` for the architecture direction.

## Do not reinstate without re-architecting

If a future need arises for request classification or a small-model front
door, build it fresh under the new architecture rather than reinstating
Speaker. The original contract is preserved here as historical reference
only.
```

### Task 3.7 — PR and SITREP for contract archival

**PR:** `docs(archive): archive Speaker contract with deprecation rationale`

- Title: exactly that
- Body: Reference this spec Phase 3 Task 3.6. Note that scrubbing of residual references in living docs is Task 3.8.

SITREP path: `SITREPs/lane-c-phase3-speaker-contract-archival-sitrep.md`

**STOP. Max review.**

---

### Task 3.8 — Scrub Speaker references from living docs

**Branch (after 3.7 merges):** `feature/lane-c-phase3-speaker-ref-scrub`

Find every remaining Speaker reference in living documents and remove or update.

Run:
```bash
grep -rn "speaker\|Speaker" --include="*.md" --include="*.yaml" --include="*.yml" \
  --exclude-dir=docs/archive --exclude-dir=founding_docs \
  > /tmp/speaker-residuals.txt
wc -l /tmp/speaker-residuals.txt
```

Expected residual locations (verify each):

1. **`hammerfall-config.md`** — remove Speaker agent references, update T3 hardware section from DGX Spark to Thor (note: Thor replaces DGX Spark at T3, and Speaker on 4090 is gone).

2. **`agents/shared/tier_protocol.md`** — scrub "all five agents" references (now four), remove Speaker hardware assignment (4090), update to four-agent roster.

3. **`agents/helm/archivist/archivist.md`** — scan for any Speaker references. If they exist, remove.

4. **`agents/helm/contemplator/contemplator.md`** — same scan.

5. **`agents/helm/projectionist/projectionist.md`** — same scan.

6. **`management/COMPANY_BEHAVIOR.md`** — if agent list mentions Speaker, remove. Also fix the stale "All outputs are .md files. No .docx" directive — Max's current standing rule is .docx + chat summary for formal artifacts.

7. **`docs/ba6/helm-system-design-ba6.md` through `docs/ba9/helm-system-design-ba9.md`** — these are historical BA records but ALSO forward-looking design docs that reference Speaker. Add a banner at the top of each:
   ```markdown
   > **⚠️ Historical document.** This design was authored before the Speaker
   > subsystem was deprecated (April 2026). References to Speaker reflect
   > architectural intent at time of writing. See `founding_docs/` for current
   > vision and `docs/archive/speaker-deprecated/` for deprecation rationale.
   ```
   Do NOT rewrite these docs — they're historical record. Just add the banner.

8. **`docs/ba1-5/`, `docs/stage0/`, `docs/stage1/`** — same banner pattern if they reference Speaker.

**Do NOT touch:**
- `docs/archive/speaker-deprecated/` (the archive itself, by design)
- `founding_docs/` (already Speaker-free by construction)
- `scripts/migrations/*.sql` and `supabase/migrations/*.sql` (SQL, historical)

**Verification:**
```bash
grep -rn "speaker\|Speaker" --include="*.md" --include="*.yaml" --include="*.yml" \
  --exclude-dir=docs/archive --exclude-dir=founding_docs > /tmp/speaker-after.txt
```
Expected: only banner-annotated historical docs remain. Compare against baseline from Task 1.2.

### Task 3.9 — PR and SITREP for reference scrub

**PR:** `docs: scrub Speaker references from living documents`

- Title: exactly that
- Body: Reference this spec Phase 3 Task 3.8. List files touched. Note the banner pattern applied to historical docs.

SITREP path: `SITREPs/lane-c-phase3-speaker-ref-scrub-sitrep.md`

**STOP. Max review.**

**Phase 3 close validation (medium):**
- Runtime boots
- `grep -rn speaker` shows only archive + banner-annotated historical docs
- helm_prompt.md has zero Speaker references
- config.yaml has zero Speaker references

---

## PHASE 4 — Doc Updates and Cold Storage Extraction

**Objective:** Update heavy docs per triage, execute cold-storage migration to `hammerfall-v1-archive` repo, finalize Lane C work.

### Task 4.1 — Rewrite README.md

**Branch:** `feature/lane-c-phase4-readme-rewrite`

`README.md` currently positions the project as "Autonomous AI Organization (AAO) for software development." This is pipeline-first framing and directly contradicts `founding_docs/Helm_The_Ambient_Turn.md`.

Rewrite completely. Target structure:

```markdown
# Hammerfall Solutions

Hammerfall is building Helm — an ambient intelligence.

## What is Helm?

One mind. Many surfaces. Persistent across time. See
[founding_docs/Helm_The_Ambient_Turn.md](founding_docs/Helm_The_Ambient_Turn.md)
for the full vision.

## Where are we in building him?

See [founding_docs/Helm_Roadmap.md](founding_docs/Helm_Roadmap.md) for the path
from today to ambient JARVIS. We are currently in **Stage 1 — Core Runtime & UI**.

## Repository structure

- `founding_docs/` — canonical reference documents (vision + roadmap)
- `agents/helm/` — Helm's cognitive architecture (Prime prompt + subsystem contracts)
- `services/helm-runtime/` — the runtime service that hosts Helm
- `scripts/` — brain tools, seed data, utilities
- `supabase/migrations/` — database schema evolution
- `docs/` — historical design documents and stage records
- `docs/archive/` — deprecated subsystems preserved for reference

## Quick start

[Deployment instructions — preserve if existing README has them; otherwise note
that the stack is run via `docker-compose up` in `services/helm-runtime/`.]

## Related repositories

- [hammerfall-v1-archive](https://github.com/mconn0330-svg/hammerfall-v1-archive) —
  pre-refounding pipeline work, preserved for future Feat restoration

## Contributing

Currently a solo-plus-AI-collaborator operation. Contributions from outside
parties are not presently accepted.
```

Adjust the Quick start section to match what the previous README said about deployment, if anything. Do not lose deployment instructions.

### Task 4.2 — Update hammerfall-config.md

Modify `hammerfall-config.md`:

1. **Tier capability requirements section** — replace DGX Spark references with Thor. Remove Speaker/RTX 4090 reference at T3. Updated T3 line should read something like:
   ```
   T3 — Thor (RTX 6000 Ada, 85GB VRAM, MIG partitioning)
         hosts Helm Prime, Projectionist, Archivist, Contemplator concurrently.
   ```

2. **Remove any Quartermaster references** — that project was absorbed into the core under the refounding.

3. **Scrub any Speaker references** (should already be done by Phase 3, but double-check).

4. **Update agent roster** wherever listed — four agents (Prime, Projectionist, Archivist, Contemplator), not five.

5. **Preserve sections on Supabase, GitHub, Vercel, Replit, EAS/Expo** — these are tooling configuration and remain valid.

### Task 4.3 — Update COMPANY_BEHAVIOR.md

Modify `management/COMPANY_BEHAVIOR.md`:

1. **Fix the stale directive** that says "All outputs are .md files. No .docx. No exceptions unless Maxwell manually provides a file as input." Current standing rule is: formal artifacts (PRDs, UX guides, blueprints, briefs, SITREPs, SWOTs) are produced as `.docx` files AND summarized in chat. Update the directive to match.

2. **Update agent roster** wherever listed.

3. **Remove pipeline-era operational rules** that no longer apply (e.g., rules about Scout intake before PRD, Muse blueprints, etc. — these are pipeline-Feat concerns now, cold-storaged).

4. **Preserve the core behavioral rules:** BLUF, Human-In-The-Loop, no sycophancy, honest feedback, correction handling.

### Task 4.4 — Update tier_protocol.md

Modify `agents/shared/tier_protocol.md`:

1. **Agent roster: four, not five.** Remove Speaker references throughout.

2. **Hardware assignment by tier:** Thor at T3, not DGX Spark. Remove the 4090/Speaker assignment.

3. **T1/T2/T3 framework itself is preserved** — it's JARVIS-aligned as established in Roadmap Section 3. Only the hardware and roster details need updating.

4. **Taskers — Stage 4 Forward Reference** — check if this section still makes sense under the refounding. If Taskers was a pipeline-era concept, note it for Max's review. Otherwise preserve.

### Task 4.5 — Update living agent contracts (light scrub)

Three agent contracts need light updates:

1. `agents/helm/archivist/archivist.md` — scan, remove any Speaker references (should be done by Phase 3; verify).
2. `agents/helm/contemplator/contemplator.md` — same.
3. `agents/helm/projectionist/projectionist.md` — same.

If any of these reference the agent roster in ways that imply "five agents," update to four.

### Task 4.6 — PR and SITREP for doc updates

**PR:** `docs: rewrite README and update heavy docs per refounding`

- Title: exactly that
- Body: Reference founding docs. List each file updated with a one-line summary of change.

SITREP path: `SITREPs/lane-c-phase4-doc-updates-sitrep.md`

**STOP. Max review.**

---

### Task 4.7 — Create `hammerfall-v1-archive` repository

**This task has TWO parts: creating the new repo with history preserved, and removing the files from main repo.** These are separate PRs.

**Branch for main-repo removal:** `feature/lane-c-phase4-cold-storage-migration`

**Step 1 — Create the archive repo with preserved history**

Use `git filter-repo` to extract pipeline files with history. If `git filter-repo` isn't installed:
```bash
pip install git-filter-repo
```

From a fresh clone of hammerfall-solutions (to avoid corrupting your working copy):

```bash
cd /tmp
git clone https://github.com/mconn0330-svg/hammerfall-solutions.git hammerfall-v1-archive-temp
cd hammerfall-v1-archive-temp

# Extract only the paths that go to cold storage, preserving history
git filter-repo --paths-from-file=/tmp/cold-storage-paths.txt
```

Where `/tmp/cold-storage-paths.txt` contains:

```
bootstrap.sh
staging_area/
project_structure_template/
agents/muse/
agents/scout/
agents/shared/session_protocol.md
scripts/sync_projects.sh
active-projects.md
agents/helm/memory/LongTerm/bootstrap_test_run_Launch.md
agents/helm/memory/LongTerm/dummy-app_Launch.md
```

**Note on the helm/memory/LongTerm files:** Two pipeline artifacts go to archive (`bootstrap_test_run_Launch.md`, `dummy-app_Launch.md`). Two stay in main (`FoundingSession.md`, `MEMORY_INDEX.md`).

**Step 2 — Create the new GitHub repository**

```bash
# Create new repo via GitHub web UI or gh CLI:
gh repo create mconn0330-svg/hammerfall-v1-archive --private --description "Pre-refounding pipeline work, preserved for future Feat restoration"
```

**Step 3 — Push the filtered history to the new repo**

```bash
cd /tmp/hammerfall-v1-archive-temp
git remote remove origin
git remote add origin https://github.com/mconn0330-svg/hammerfall-v1-archive.git
git push -u origin main
```

**Step 4 — Add README to the archive repo**

In the archive repo, create a `README.md` at root:

```markdown
# hammerfall-v1-archive

Pre-refounding pipeline work from Hammerfall Solutions, preserved for historical
reference and future Feat restoration.

## What is this?

This repository contains the autonomous software development pipeline that
Hammerfall Solutions originally built — the five-agent coordination system
(project_manager, ux_lead, be_dev, fe_dev, qa_engineer) operating under Helm's
technical direction, plus the research and design agents (Scout, Muse) that
supported them.

During the April 2026 refounding, Hammerfall pivoted from "Autonomous AI
Organization for software development" to "Ambient intelligence (Helm) that can
also operate a software development pipeline." The pipeline work was not wrong;
it became one capability among many. This repository preserves it.

## When will it return?

The pipeline will be restored as Helm's **Software Development Feat** when the
Feats framework is built in Stage 4 of the Helm Roadmap (see
[hammerfall-solutions/founding_docs/Helm_Roadmap.md](https://github.com/mconn0330-svg/hammerfall-solutions/blob/main/founding_docs/Helm_Roadmap.md)).

At that point, Scout, Muse, and the project agents return as tools Helm uses
when operating in software-development mode — not as siblings to his cognitive
architecture, but as capabilities within a Feat he invokes.

## Do not modify

This repository is a historical artifact. The work here is complete as of
refounding. Changes to pipeline machinery happen in the main
hammerfall-solutions repo when the Software Development Feat is restored, not
here.

## Contents

- `bootstrap.sh` — pipeline project bootstrapper (v4.1)
- `staging_area/` — project requirements drop zone + Dummy Task project outputs
- `project_structure_template/` — per-project agent template
- `agents/muse/` — pipeline UX agent
- `agents/scout/` — pipeline research agent
- `agents/shared/session_protocol.md` — shared pipeline session mechanics
- `scripts/sync_projects.sh` — pipeline project sync
- `active-projects.md` — pipeline project registry
- Historical pipeline project artifacts

## Companion repository

[hammerfall-solutions](https://github.com/mconn0330-svg/hammerfall-solutions) —
the main Helm development repository.
```

Commit and push the README to the archive repo.

**Step 5 — Remove files from main hammerfall-solutions repo**

Back in the main repo, on the `feature/lane-c-phase4-cold-storage-migration` branch:

```bash
git rm bootstrap.sh
git rm -r staging_area/
git rm -r project_structure_template/
git rm -r agents/muse/
git rm -r agents/scout/
git rm agents/shared/session_protocol.md
git rm scripts/sync_projects.sh
git rm active-projects.md
git rm agents/helm/memory/LongTerm/bootstrap_test_run_Launch.md
git rm agents/helm/memory/LongTerm/dummy-app_Launch.md
```

Commit with message:
```
chore: migrate pipeline work to hammerfall-v1-archive

The pre-refounding pipeline work has been extracted with full git history
preserved to hammerfall-v1-archive. These files are removed from the main
repo to establish the JARVIS-first scope.

The pipeline returns to the main repo as the Software Development Feat when
the Feats framework is built in Stage 4. See founding_docs/Helm_Roadmap.md.

Archive: https://github.com/mconn0330-svg/hammerfall-v1-archive
```

### Task 4.8 — PR and SITREP for cold storage migration

**PR:** `chore: migrate pipeline work to hammerfall-v1-archive`

- Title: exactly that
- Body: Link to the new archive repo. Reference this spec Phase 4 Task 4.7. List files removed. Note that history is preserved in the archive repo.

SITREP path: `SITREPs/lane-c-phase4-cold-storage-migration-sitrep.md`

Include:
- Archive repo URL
- Confirmation git history preserved in archive
- Confirmation removal committed cleanly in main
- File count removed (expected: ~45 files across 5 directories + individuals)

**STOP. Max review.**

---

### Task 4.9 — Create Feats framework placeholder doc

**Branch:** `feature/lane-c-phase4-feats-placeholder`

Create `founding_docs/Feats_Framework_Placeholder.md`:

```markdown
# Feats Framework — Placeholder

> **Status:** Not yet designed. Full architectural spec belongs to Stage 4 of
> the Helm Roadmap. This document preserves the design thinking that has
> occurred to date so it isn't lost between now and Stage 4 opening.

## What is a Feat?

A Feat is a discrete capability Helm invokes in specific operational contexts.
Feats are compositions of capabilities Helm already has, packaged and structured
for a domain.

Feats are **not**:
- A plugin system
- External integrations in the general sense
- A way to extend Helm with third-party code

Feats are **first-class capabilities** with defined scope, tools, context
templates, and invocation patterns. The Feats framework itself defines how
Feats are declared, scoped, composed, and invoked.

## First Feats (Stage 4 opening wave)

- **Software Development Feat** — restored from hammerfall-v1-archive. Scout,
  Muse, project agents (be_dev, fe_dev, qa_engineer, ux_lead, project_manager)
  return as tools within the Feat.
- **Research Feat** — deep topic investigation, source synthesis
- **Document Composition Feat** — drafting, editing, long-form output
- **Schedule Awareness Feat** — calendar, rhythms, commitments
- **Communication Drafting Feat** — emails, messages, responses
- **Coding Assistance Feat** — lightweight inline help

## External integrations in Stage 4 scope

- Health data (with permission)
- Email
- Calendar
- Document stores (Google Drive, Notion, etc.)
- Coding environments

## Polymodal interface (Stage 4 emergence)

Helm composes UI widgets on the fly per context. Calendars, research panels,
code editors — surfaced when needed, not navigated to.

## Helm-writes-Feats (long-horizon)

Accumulated experience converts to new Feats over time. Contemplator notices
patterns; patterns become Feat candidates; Helm structures and deliberately
invokes them. Speculative. Long-horizon.

## What this placeholder does NOT do

- It does not specify the Feats framework architecture
- It does not commit to specific Feat schemas
- It does not define invocation protocols
- It does not lock implementation patterns

All of the above is Stage 4 work. This document is a memory aid — nothing in it
binds Stage 4 planning.

## Canonical reference

See `founding_docs/Helm_Roadmap.md` Section 3 (Stage 4) and Section 6 (The Feats
Horizon) for the roadmap-level positioning.
```

### Task 4.10 — PR and SITREP for Feats placeholder

**PR:** `docs(founding): add Feats framework placeholder`

SITREP path: `SITREPs/lane-c-phase4-feats-placeholder-sitrep.md`

**STOP. Max review.**

**Phase 4 close validation (medium):**
- All doc updates merged
- Archive repo exists, has history, has README
- Main repo no longer contains cold-storage files
- README.md, hammerfall-config.md, COMPANY_BEHAVIOR.md, tier_protocol.md all reflect refounding
- Feats placeholder exists in `founding_docs/`

---

## PHASE 5 — Lane C Close Validation and Final SITREP

**Objective:** Heavy validation that the system is in a clean, coherent state after Lane C execution. Produce the final Lane C close SITREP.

### Task 5.1 — Heavy validation

Execute the following verification sequence:

1. **Runtime boots and is healthy:**
   ```bash
   cd services/helm-runtime
   docker-compose up -d
   curl http://localhost:8000/health
   curl http://localhost:8000/config/agents
   ```
   Expected: healthy, four agents listed (helm_prime, projectionist, archivist, contemplator).

2. **No Speaker references outside archive:**
   ```bash
   grep -rn "speaker\|Speaker" \
     --exclude-dir=docs/archive \
     --exclude-dir=founding_docs \
     --exclude-dir=.git \
     | grep -v "historical document" \
     > /tmp/speaker-residuals-final.txt
   wc -l /tmp/speaker-residuals-final.txt
   ```
   Expected: 0 or only banner-annotated historical references.

3. **Cold storage files gone from main:**
   ```bash
   ls agents/muse 2>&1 | grep "No such"
   ls agents/scout 2>&1 | grep "No such"
   ls staging_area 2>&1 | grep "No such"
   ls bootstrap.sh 2>&1 | grep "No such"
   ls project_structure_template 2>&1 | grep "No such"
   ```
   Expected: all "No such file or directory".

4. **Archive repo integrity:**
   Visit `https://github.com/mconn0330-svg/hammerfall-v1-archive` in browser. Confirm README exists. Confirm at least `bootstrap.sh`, `agents/muse/`, `agents/scout/`, `project_structure_template/` are present. Confirm git history has multiple commits (not just "Initial import").

5. **Founding docs in place:**
   ```bash
   ls founding_docs/
   ```
   Expected: `Helm_The_Ambient_Turn.md`, `Helm_The_Ambient_Turn.docx`, `Helm_Roadmap.md`, `Helm_Roadmap.docx`, `Feats_Framework_Placeholder.md`, `README.md`.

6. **helm_prompt.md is JARVIS-first:**
   - Grep for "Speaker" — expect zero hits
   - Grep for "Technical Director" — expect zero hits (Helm is not defined by that role anymore)
   - Confirm Prime Directives inlined at top
   - Confirm reference to founding_docs near top

7. **Prime Directives still in place:**
   ```bash
   cat agents/shared/prime_directives.md | head -5
   ```
   Expected: unchanged from pre-Lane-C state. File is immutable.

8. **config.yaml has helm_prime, not speaker:**
   ```bash
   grep -E "helm_prime|speaker" services/helm-runtime/config.yaml
   ```
   Expected: only helm_prime mentioned.

9. **Test scripts cleaned:**
   ```bash
   ls scripts/speaker_prompt_test.js 2>&1 | grep "No such"
   ls scripts/agent_stress_test_qwen3.js 2>&1 | grep "No such"
   ls scripts/contemplator_stress_test_qwen3.js  # should still exist
   ```
   Expected: Speaker tests gone; Contemplator Qwen3 test retained.

10. **End-to-end test is deferred** — full Prime invocation test requires Lane B UI; note this in the SITREP as a known follow-up.

### Task 5.2 — Write Lane C close SITREP

**Branch:** `feature/lane-c-close`

Create `SITREPs/lane-c-close-report.md`:

```markdown
# Lane C Close Report

**Date:** [date of close]
**Duration:** Lane C spanned [X] sessions
**PRs merged:** [list all PRs in order with numbers once known]

## What Lane C accomplished

[Summarize in 2-3 paragraphs.]

## Founding documents placed

- founding_docs/Helm_The_Ambient_Turn (md + docx) — canonical vision
- founding_docs/Helm_Roadmap (md + docx) — canonical path
- founding_docs/Feats_Framework_Placeholder.md — Stage 4 memory aid
- founding_docs/README.md — directory explanation

## Runtime changes

- Added: services/helm-runtime/agents/helm_prime.py
- Added: config.yaml entry for helm_prime agent
- Removed: services/helm-runtime/agents/speaker.py
- Removed: speaker entry from main.py AGENT_HANDLERS
- Removed: speaker entry from config.yaml
- Updated: archivist.py L669 stale comment

## Prompt and contract changes

- Rewritten: agents/helm/helm_prompt.md under JARVIS-first framing
- Archived: agents/helm/speaker/speaker.md → docs/archive/speaker-deprecated/
- Scrubbed: Speaker references from tier_protocol.md, hammerfall-config.md, COMPANY_BEHAVIOR.md, three agent contracts
- Bannered: BA6-9 historical design docs flagged as historical

## Document updates

- Rewritten: README.md under JARVIS-first framing
- Updated: hammerfall-config.md (Thor replaces DGX Spark, roster updated)
- Updated: COMPANY_BEHAVIOR.md (.docx directive fix, roster updated)
- Updated: tier_protocol.md (roster, hardware)

## Cold storage migration

Pipeline work preserved in https://github.com/mconn0330-svg/hammerfall-v1-archive with full git history.

Files migrated:
[List from task 4.7]

## Verification status

[All heavy validation checks from Task 5.1 listed with pass/fail]

## Known follow-ups

- End-to-end Prime invocation test deferred to Lane B UI integration
- contemplator_stress_test_qwen3.js retained pending future review (unclear if current-model harness)
- "Taskers — Stage 4 Forward Reference" in tier_protocol.md noted for Stage 4 opening review
- Quartermaster concept absorbed into core; no action needed
- Banner pattern applied to historical BA docs — Max may wish to revisit if he wants cleaner retro doc aesthetics

## Lane C handoff

Lane A (backend integration prep) and Lane B (UI build) are now unblocked.

Specifically:
- Lane A opening task: UI Interaction Spec (depends on Lane B UI stability)
- Lane A opening task: Supabase RLS/realtime/anon key verification
- Lane A opening task: Schema reference doc for Lane B
- Lane B: continues on mock data; integration with real Supabase happens post-Lane-A-A3

The system is in a clean, coherent, JARVIS-first state and ready for Stage 1 close work.
```

### Task 5.3 — Final PR

**PR:** `docs(sitrep): Lane C close report`

SITREP is the PR content itself. After merge, Lane C is complete.

**STOP. Final Max review.**

---

## Appendix A — Reference: Full list of files touched

For Max's easy review of scope.

### Files created
- `founding_docs/Helm_The_Ambient_Turn.md`
- `founding_docs/Helm_The_Ambient_Turn.docx`
- `founding_docs/Helm_Roadmap.md`
- `founding_docs/Helm_Roadmap.docx`
- `founding_docs/Feats_Framework_Placeholder.md`
- `founding_docs/README.md`
- `services/helm-runtime/agents/helm_prime.py`
- `docs/archive/speaker-deprecated/speaker.md` (moved)
- `docs/archive/speaker-deprecated/README.md`
- `SITREPs/lane-c-phase0-founding-docs-sitrep.md`
- `SITREPs/lane-c-phase2-prime-handler-sitrep.md`
- `SITREPs/lane-c-phase2-prompt-rewrite-sitrep.md`
- `SITREPs/lane-c-phase3-speaker-code-deletion-sitrep.md`
- `SITREPs/lane-c-phase3-speaker-contract-archival-sitrep.md`
- `SITREPs/lane-c-phase3-speaker-ref-scrub-sitrep.md`
- `SITREPs/lane-c-phase4-doc-updates-sitrep.md`
- `SITREPs/lane-c-phase4-cold-storage-migration-sitrep.md`
- `SITREPs/lane-c-phase4-feats-placeholder-sitrep.md`
- `SITREPs/lane-c-close-report.md`

### Files modified
- `services/helm-runtime/main.py`
- `services/helm-runtime/config.yaml`
- `services/helm-runtime/agents/__init__.py`
- `services/helm-runtime/agents/archivist.py`
- `agents/helm/helm_prompt.md` (rewritten)
- `README.md` (rewritten)
- `hammerfall-config.md`
- `management/COMPANY_BEHAVIOR.md`
- `agents/shared/tier_protocol.md`
- `agents/helm/archivist/archivist.md` (light)
- `agents/helm/contemplator/contemplator.md` (light)
- `agents/helm/projectionist/projectionist.md` (light)
- BA1-5, BA6-9, stage0, stage1 historical docs (banner added)

### Files deleted
- `services/helm-runtime/agents/speaker.py`
- `scripts/speaker_prompt_test.js`
- `scripts/agent_stress_test_qwen3.js`

### Files moved to `hammerfall-v1-archive`
- `bootstrap.sh`
- `staging_area/` (entire)
- `project_structure_template/` (entire)
- `agents/muse/` (entire)
- `agents/scout/` (entire)
- `agents/shared/session_protocol.md`
- `scripts/sync_projects.sh`
- `active-projects.md`
- `agents/helm/memory/LongTerm/bootstrap_test_run_Launch.md`
- `agents/helm/memory/LongTerm/dummy-app_Launch.md`

### Files intentionally preserved
- `agents/shared/prime_directives.md` (immutable)
- `agents/shared/tier_protocol.md` (updated, not removed)
- `agents/helm/memory/LongTerm/FoundingSession.md` (historical record)
- `agents/helm/memory/LongTerm/MEMORY_INDEX.md` (regenerates via snapshot.sh)
- All of `docs/ba*/` and `docs/stage*/` (historical records, banner-annotated only)
- All of `scripts/migrations/` and `supabase/migrations/` (historical SQL)
- All of `scripts/` except the two deleted Speaker-tied tests
- `services/helm-runtime/` infrastructure files (model_router.py, middleware.py, supabase_client.py, embedding_client.py, Dockerfile, requirements.txt)

---

## Appendix B — Rollback procedures

If any phase produces an unrecoverable regression, roll back as follows.

### Phase 2 rollback
Revert the Phase 2 PRs in reverse merge order. Runtime returns to pre-Prime-handler state. Speaker still present, personality injection still works.

### Phase 3 rollback
Revert Phase 3 PRs in reverse merge order. Speaker code returns. Validate runtime boots. Personality injection continues working via Speaker's original path.

If Phase 3 is rolled back, the Phase 2 Prime handler remains — both paths coexist (as they did during Phase 2 execution). This is safe but redundant.

### Phase 4 rollback
Cold storage migration is the riskiest to roll back. The archive repo is a separate repository; rolling back the main-repo removal is straightforward (`git revert` the removal commit). The archive repo persists independently and does not need to be deleted for rollback.

Doc updates are straightforward — `git revert` the relevant PR.

### Nuclear option
Restore from GitHub's repo backup / `git reflog` / last known good tag. Document the failure in a retrospective SITREP before attempting anything destructive.
