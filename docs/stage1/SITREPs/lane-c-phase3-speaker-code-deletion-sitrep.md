# SITREP — Lane C Phase 3.1: Speaker Code Deletion

**Date:** 2026-04-22
**Branch:** `feature/lane-c-phase3-speaker-code-deletion`
**Phase:** Lane C, Phase 3, Tasks 3.1–3.5
**Spec:** `docs/stage1/refounding-ba.md`
**Architectural rationale:** `docs/founding_docs/Helm_The_Ambient_Turn.md` §4

## Scope executed

Removed Speaker from the Helm Runtime Service. Speaker was a Thor-era routing layer that intercepted user-facing voice generation. Under the Ambient Turn architecture, Helm Prime is invoked directly — there is no routing layer between Maxwell and Prime. Speaker's only remaining responsibilities (personality injection on the Prime escalation path) were previously absorbed into `agents/helm_prime.py` (PR #76).

This PR is the **first** of three Phase 3 sub-PRs:
1. **Code deletion (this PR)** — remove Speaker from runtime, config, model pulls, and stress tests.
2. **Contract archival (next PR)** — `git mv agents/helm/speaker/speaker.md docs/archive/speaker-deprecated/`.
3. **Reference scrub (third PR)** — clear lingering Speaker references from living documents (config, agent contracts, COMPANY_BEHAVIOR), banner historical docs.

## Files modified

| File | Change |
|---|---|
| `services/helm-runtime/main.py` | Removed `speaker` import, `_handle_speaker` function, AGENT_HANDLERS entry, and `"speaker"` from health check role tuple. |
| `services/helm-runtime/config.yaml` | Removed entire `agents.speaker` block. |
| `services/helm-runtime/middleware.py` | Rewrote `_personality_inject` docstring (Prime now does injection directly). Updated `_session_context_inject` and Prime Directives guard docstrings to remove Speaker references. |
| `services/helm-runtime/agents/archivist.py` | Updated line 288 comment — removed Speaker translation table reference, replaced with note that /10 display is a presentation-time rendering choice. |
| `scripts/pull_models.sh` | Dropped `qwen3:8b` from MODELS array. Updated disk total comment from `~17 GB` to `~12 GB`. Per memory note `project_speaker_kill_followups.md` — bundled into this PR rather than tracked separately. |

## Files deleted

| File | Reason |
|---|---|
| `services/helm-runtime/agents/speaker.py` | Speaker agent module — obsoleted. |
| `scripts/speaker_prompt_test.js` | Tested Speaker routing prompts — dead code. |
| `scripts/agent_stress_test_qwen3.js` | qwen3 stress test included Speaker comparison — dead code. |
| `scripts/agent_stress_test.js` | Multi-agent benchmark whose Speaker block dominated structure; also tested obsolete qwen2.5 family. Historical artifact; if a refreshed multi-agent stress test is needed it should be written fresh against qwen3. **Spec deviation #1 — see below.** |

## Verification

Live boot test executed against the rebuilt runtime container (placeholder env vars, since this shell does not have ANTHROPIC_API_KEY or SUPABASE_BRAIN_URL set):

**`/config/agents`**
```json
{"agents":{
  "helm_prime":{"provider":"anthropic","model":"claude-opus-4-6"},
  "projectionist":{"provider":"ollama","model":"qwen3:4b","base_url":"http://ollama:11434"},
  "archivist":{"provider":"ollama","model":"qwen3:14b","base_url":"http://ollama:11434"},
  "contemplator":{"provider":"ollama","model":"qwen3:14b","base_url":"http://ollama:11434"}
}}
```
Speaker no longer present. Four agents only.

**`/health`**
- `service`: ok
- `models.projectionist`: ok
- `models.archivist`: ok
- `models.contemplator`: ok
- `models.helm_prime`: unreachable (placeholder API key — auth error; expected in this verification context)
- `models.speaker`: not in the response — health check tuple no longer iterates Speaker.

**Startup log confirmation:**
```
ModelRouter initialized. Agents: ['helm_prime', 'projectionist', 'archivist', 'contemplator']
```

**Code-level checks:**
- `python -c "import yaml; ..."` confirmed `agents` key has 4 entries, `speaker` not present.
- `py_compile` of main.py, middleware.py, archivist.py: clean.
- Repo-wide grep for `speaker` and `qwen3:8b` against `services/helm-runtime/` and `scripts/pull_models.sh` returns only the deliberate historical phrase "post-Speaker architecture" in middleware.py:286.

## Spec deviations

### Deviation #1 — Deleted `agent_stress_test.js` rather than surgically removing only the Speaker block

**Spec text (Task 3.3):** "drop legacy `speaker_prompt_test.js` and any tests referencing speaker.py from scripts/"

`agent_stress_test.js` does not import `speaker.py` directly — it has its own JS-level Speaker prompt baked in (`SPEAK_SYSTEM` at line 365). A literal reading of the spec would leave it in place. I deleted it because:

- It tests three agents (Projectionist, Archivist, Speaker) against the obsolete `qwen2.5:{3b,8b,14b}` family — both the Speaker dimension AND the model dimension are stale.
- The Speaker block constitutes a meaningful share of the file's structure (~120 lines of Speaker-specific test cases, scoring, summary tables); surgically removing it would leave a hollow comparison framework around obsolete models.
- A future qwen3 multi-agent stress test, if needed, should be written fresh against the current model lineup, not patched onto a Thor-era benchmark scaffold.

Risk if wrong: an old benchmark artifact disappears. There is no production dependency.

### Deviation #2 — Bundled `pull_models.sh` edit into this PR

Memory entry `project_speaker_kill_followups.md` notes "Drop qwen3:8b from `scripts/pull_models.sh` when Speaker is removed in Lane C Phase 3." The spec does not explicitly call out this file under Phase 3 Tasks 3.1–3.5. I bundled it here because:

- It's load-bearing for `docker-compose down -v` recovery — leaving qwen3:8b in MODELS would cause unnecessary 5.2 GB pull on the next clean re-up.
- Splitting it into a separate trivial PR adds review overhead with no isolation benefit.
- Memory entry was explicit that this should land alongside Speaker removal, not separately.

### Deviation #3 — Did not surgically scrub `contemplator_stress_test_qwen3.js`

This file references `qwen3:8b` as a candidate model in the Contemplator selection benchmark. It does NOT reference Speaker. Under strict reading the qwen3:8b reference will become stale (the model is no longer in the pull list), but:

- It is a one-shot historical benchmark that selected qwen3:14b for Contemplator. Re-running it requires manually pulling qwen3:8b first — same operational shape as any model benchmark that exceeds the standard pull set.
- It documents how the model selection decision was reached. Removing it erases that audit trail.

Flagging here rather than scrubbing.

## AAR candidates

### AAR #1 — Image cache surprise during boot verification

The first verification attempt showed Speaker still in `/health` output even though source files were updated. Cause: docker-compose recreates the container against the existing image, but image content (main.py, speaker.py, etc.) is baked at build time — only `config.yaml` and `helm_prompt.md` are mounted. Required `docker-compose build helm-runtime` followed by `docker-compose up -d` to pick up Python source changes.

This is a documented Docker behavior, but it cost a verification cycle and produced confusing output (4-agent ModelRouter init log, but 5-agent /health response — because the live image had old main.py). Worth noting in operator runbooks: **after Python source edits in `services/helm-runtime/`, always rebuild the image, not just restart the container.**

### AAR #2 — Verification env vars not in shell

This shell did not have `ANTHROPIC_API_KEY` or `SUPABASE_BRAIN_URL` set. Boot test required placeholder values to get past startup gates. Useful pattern: structural verification (config, AGENT_HANDLERS, /config/agents enumeration) does not need real credentials. Real credentials are only needed for downstream calls (Anthropic auth, Supabase queries). Future verification flows can use placeholder env vars and read failure modes from `/health` to distinguish "code wrong" from "creds wrong."

## Out of scope (Phase 3 follow-ups still pending)

Per the planned three-PR sub-split:

- **PR 2:** `feature/lane-c-phase3-speaker-contract-archival` — `git mv agents/helm/speaker/speaker.md docs/archive/speaker-deprecated/speaker.md` + create `docs/archive/speaker-deprecated/README.md` with deprecation rationale.
- **PR 3:** `feature/lane-c-phase3-speaker-ref-scrub` — scrub Speaker from `hammerfall-config.md`, `agents/shared/tier_protocol.md`, archivist/contemplator/projectionist contracts, `COMPANY_BEHAVIOR.md`. Add historical-document banners to `docs/ba6-9/`, `docs/ba1-5/`, `docs/stage0/`, `docs/stage1/`.

## STOP gate

Standing by for Maxwell QA before opening the contract-archival PR.
