# SITREP — Lane C Phase 4 Reference Scrub

**Date:** 2026-04-22
**Branch:** `feature/lane-c-phase4-reference-scrub`
**Phase:** Lane C, Phase 4, follow-up to PR #83 (cold-storage migration)
**Spec:** `docs/stage1/refounding-ba.md` §Phase 4 (carry-forward from PR #83)

## Scope executed

PR #83 (cold-storage migration) intentionally shipped as file-removals-only,
leaving four references to now-removed paths in three living docs. This PR
cleans those up. Routine 5 in `helm_prompt.md` is **rewritten** as a
single-project snapshot trigger per Maxwell's explicit guidance — not deleted.

This is **PR 2b of Phase 4** (companion to PR #83). After this merges, the
post-cold-storage main repo reads cleanly with no dangling references to
archived pipeline machinery.

## Files changed

| File | Change |
|---|---|
| `hammerfall-config.md` | (1) Preamble line 3: "read by `bootstrap.sh` and all Helm instances" → "read by Helm and the runtime service." (2) Per-project DB-password note removed entirely — the note explained `bootstrap.sh`-driven password generation that no longer exists. The Supabase block now ends at the config keys with no trailing note. |
| `services/helm-runtime/supabase_client.py` | Module docstring's example-callers list trimmed: `(Helm Prime, Routine 4, snapshot.sh, sync_projects.sh)` → `(Helm Prime, Routine 4, snapshot.sh)`. |
| `agents/helm/helm_prompt.md` | (1) "Session instrumentation" block: removed broken link to `agents/shared/session_protocol.md`; replaced with a one-line slug+script-name reminder so the operational guidance survives. (2) Routine 5 rewritten — see below. |

## Routine 5 rewrite

**Old (calling cold-storaged `scripts/sync_projects.sh`):**

> Routine 5 — Scheduled Sync. Runs `scripts/sync_projects.sh` which
> (1) queries brain for recent activity, (2) prints status summary,
> (3) triggers `snapshot.sh`, (4) reports complete.

**New (calling surviving `scripts/snapshot.sh` directly):**

> Routine 5 — Scheduled Snapshot. Runs
> `scripts/snapshot.sh hammerfall-solutions helm` which writes current brain
> state to the `.md` snapshot files in `agents/helm/memory/`
> (BEHAVIORAL_PROFILE / BRAIN_SUMMARY / BELIEFS_SUMMARY / PERSONALITY_SUMMARY).

**What was preserved:**
- Same triggers (3x daily 7/12/18 + on-demand). On-demand phrase updated from
  "Helm, sync now" to "Helm, snapshot now" to match the new operation name.
- Same one-way-read semantics statement.
- Same token-URL push pattern reminder for non-interactive shells.

**What was dropped:**
- The brain-recency status-summary print step. That was a diagnostic feature of
  `sync_projects.sh`'s outer wrapper, not load-bearing for the snapshot itself.
  The snapshot files themselves contain the recency information.

**Why a rewrite, not a deletion:** Per Maxwell — the snapshot pattern still
applies post-refounding (write current brain state to `.md` snapshot files for
cold-read context). Only the multi-project `sync_projects.sh` wrapper was
pipeline-era. The named scripts (`snapshot.sh`) and the warm-layer outputs all
survive in `scripts/` and `agents/helm/memory/`.

## Spec deviations

### Deviation #1 — On-demand phrase changed from "Helm, sync now" to "Helm, snapshot now"

The old Routine 5 was named "Scheduled Sync" with on-demand trigger phrase
"Helm, sync now." The rewrite renames the routine to "Scheduled Snapshot" to
match what it actually does post-refounding. Trigger phrase updated to match.

Risk if wrong: Maxwell may still type "Helm, sync now" out of habit. Helm should
treat the two as synonymous if asked — flagging here so this is an explicit
decision, not a silent rename.

### Deviation #2 — DB-password generation note in `hammerfall-config.md` removed entirely (not just scrubbed)

The note explained `bootstrap.sh`-driven per-project password generation. With
`bootstrap.sh` cold-stored and no per-project bootstrap flow remaining, the
entire note is moot — not just the `bootstrap.sh` reference within it. Removed
in full. The single live Supabase project (the brain) uses connection details
from the config keys directly; no generated password applies.

Risk if wrong: if a future per-project bootstrap flow is reintroduced (it
won't be, per the Feats framework plan), this note would need to be
re-authored. Trivial.

## Verification

```
$ grep -rn "bootstrap\.sh\|sync_projects\|active-projects\.md\|agents/muse\|agents/scout\|session_protocol\.md" \
    --include="*.md" --include="*.py" --include="*.sh" --include="*.js" \
    services/ agents/ scripts/ management/ supabase/ README.md hammerfall-config.md
# (no output from living code/docs — only memory snapshots, SITREPs, and the spec)
```

Remaining matches (all expected): `docs/stage0/**` (historical, bannered),
`docs/stage1/SITREPs/*` (operating records), `agents/helm/memory/**` (memory
snapshots reflecting prior state), `docs/stage1/refounding-ba.md` (the active
spec), `.claude/settings.local.json` (local permission entries — harmless).

## STOP gate

Standing by for Maxwell QA. After approval + merge, the doc-currency portion of
Phase 4 is complete. Next: PR 3 (Feats framework placeholder doc, Tasks 4.9–4.10).
