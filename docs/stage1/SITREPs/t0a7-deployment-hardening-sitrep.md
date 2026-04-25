# SITREP — T0.A7 Deployment Hardening

**Date:** 2026-04-25
**Branch:** `feature/t0a7-deployment-hardening`
**Tier:** ARCH (architect-approved per [arch_notes/T0.A7_deployment_hardening.md](../arch_notes/T0.A7_deployment_hardening.md))
**Spec:** `docs/stage1/Helm_T1_Launch_Spec_V2.md` §T0.A7

## Scope executed

Production-shaped runtime container per the architect-approved one-pager. Five artifacts:

1. **`services/helm-runtime/Dockerfile`** — multi-stage (builder + runtime), pinned `python:3.12.4-slim-bookworm`, non-root `helm:1000`, healthcheck via stdlib urllib (no curl in slim base).
2. **`docker-compose.yml`** hardening — `read_only: true`, `tmpfs: /tmp`, `cap_drop: ALL`, `no-new-privileges`, `mem_limit: 512m`, `cpus: 1.0`, healthcheck mirroring the Dockerfile, `helm_state` volume mount at `/home/helm/.helm` (for the T0.B2 outbox).
3. **pip-compile lockfile workflow** — renamed `requirements.txt` → `requirements.in` (and the same for dev). Lockfiles are now generated, hash-pinned, fully transitive (1742 lines for prod, 437 for dev). pip enforces hashes automatically when present.
4. **CI sync check** — re-runs `pip-compile` and diffs against committed lockfiles. Drift fails the build.
5. **Root `.gitignore`** — bundled here because it's bitten T0.A6 and T0.A7 both with accidental `__pycache__` commits. Resolves Finding #003.

## Verification (local)

- `docker build -t helm-runtime:t0a7-test services/helm-runtime/` → green
- `docker run --rm helm-runtime:t0a7-test id` → `uid=1000(helm) gid=1000(helm)` ✓ non-root confirmed
- `docker run --rm helm-runtime:t0a7-test python -c "import main; print('main importable')"` → `main importable` ✓
- mypy strict: no Python source changes; still clean
- ruff + black: clean
- pre-commit: clean (prettier reformatted yaml; restaged; clean)

CI will validate the lockfile sync check + the rest of the pipeline.

## Files changed

| File                                         | Change                                                                                                                                                    |
| -------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `.gitignore`                                 | NEW — root-level. Catches `__pycache__`, `.venv`, `node_modules`, `.vite`, `dist`, OS turds, `.env`, supabase scratch, `$TMPFILE`. Resolves Finding #003. |
| `services/helm-runtime/Dockerfile`           | Rewritten as multi-stage; pinned base; non-root user; healthcheck.                                                                                        |
| `docker-compose.yml`                         | Hardening (read-only, caps, limits, healthcheck) + `helm_state` named volume.                                                                             |
| `services/helm-runtime/requirements.in`      | NEW (renamed from requirements.txt) — top-level deps, source of truth.                                                                                    |
| `services/helm-runtime/requirements-dev.in`  | NEW (renamed from requirements-dev.txt) — top-level dev deps + `pip-tools==7.5.3`.                                                                        |
| `services/helm-runtime/requirements.txt`     | REGENERATED — hashed lockfile via `pip-compile --generate-hashes --strip-extras`. 1742 lines.                                                             |
| `services/helm-runtime/requirements-dev.txt` | REGENERATED — same, with `--allow-unsafe --constraint requirements.txt`. 437 lines.                                                                       |
| `.github/workflows/ci.yml`                   | + lockfile sync check step (between Install and Lint).                                                                                                    |

## Spec deviations

None on the architect's design. A few implementation decisions worth flagging:

1. **Healthcheck via Python stdlib, not curl.** Slim base doesn't ship curl. `python -c "import urllib.request,sys; r=urllib.request.urlopen(...); sys.exit(0 if r.status == 200 else 1)"` is one line, no extra package, matches Dockerfile + compose for consistent health reporting.

2. **`--strip-extras` in pip-compile.** pip-tools 8 will make this the default; passing it now silences the deprecation warning and matches future behavior.

3. **`--allow-unsafe` for dev lockfile only.** Dev pulls in `setuptools`/`pip` itself (via `pip-tools`) which pip-compile classifies as "unsafe to pin" by default. We need them pinned for reproducible CI; dev-only scope means the trade-off is fine.

4. **`.gitignore` bundled in this PR rather than its own.** Spec for T0.A7 doesn't mention it, but Finding #003 has surfaced concretely in the last two PRs (forced cleanup commits in PR #105). Adjacent under "clean adjacent debt as you go" because deployment hardening is itself a hygiene area.

## Architect open-question resolutions

The arch note had four open questions; the architect resolved three in their review. The fourth (read-only root + tmpfs `/tmp`) was addressed via the `helm_state` volume for the T0.B2 outbox at `~/.helm/`. Coordination point with T0.B2 documented in compose comments.

## Adjacent debt explicitly NOT in scope

- **Building the container in CI (T0.A12).** The arch note says T0.A12 depends on T0.A7's Dockerfile being buildable; it is. Wiring the CI build job is T0.A12's work.
- **Renovate/Dependabot (T0.A14).** The arch note flags this. T0.A14 is its own task. pip-compile workflow is now in place for it to consume.
- **Resource-limit tuning from bench data (T4.8).** Architect: "Revise from T4.8 bench data later." 512m/1.0cpu is the deliberate starting point.

## What this unlocks

- **T0.A12 (CI: container build + GHCR publish)** — the Dockerfile is buildable, ARCH-approved, and `docker build` succeeded locally. T0.A12's job is to wire that into a CI job that pushes to GHCR.
- **T0.B2 (Outbox pattern)** — `helm_state` volume + `~/.helm/` writable directory inside the read-only container is ready for SQLite outbox persistence.
- **T0.A14 (Dependency automation)** — Renovate/Dependabot can drive `requirements.in` bumps; CI will catch any drift. Workflow is in place.
- **T4.4 / T4.11 (Render deployment)** — image is production-shaped; healthcheck matches Render's expectations; resource limits sized for free tier.
- **Finding #003 resolved** — every contributor's `git status` now reads cleanly. No more accidental `__pycache__` commits.

Phase 0A pacing note: task 7 of ~15. Observability arc (T0.A6) closed; deployment-hardening arc opens here. T0.A7 is the first ARCH-tier task to actually build (PRs #88-95 were spec authoring + arch_notes; T0.A1-A6 were STOP/Batch/IMPL). The architect-review-then-build pattern works as designed.

## Review

ARCH-tier — architect already approved the design (one-pager). This PR is the build under that approval. Bundle review for: (a) implementation matches the design, (b) the small flagged items (healthcheck via Python, pip-compile flags) are defensible, (c) bundling `.gitignore` was the right adjacency call.

After merge, T0.A8 (API auth) is next — also ARCH-tier with an existing architect-approved one-pager.
