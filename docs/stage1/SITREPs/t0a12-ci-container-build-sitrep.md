# SITREP — T0.A12 CI Container Build + GHCR Publish

**Date:** 2026-04-25
**Branch:** `feature/t0a12-ci-container-build`
**Tier:** ARCH (architect-approved per [arch_notes/T0.A12_ci_container_build.md](../arch_notes/T0.A12_ci_container_build.md))
**Spec:** `docs/stage1/Helm_T1_Launch_Spec_V2.md` §T0.A12

## Scope executed

One artifact: `.github/workflows/build-publish.yml`. Build under the architect-approved one-pager.

| Trigger                        | Action                                    | Tags                            |
| ------------------------------ | ----------------------------------------- | ------------------------------- |
| `pull_request` (path filter)   | Build only, load to local docker for scan | `pr-<NN>`                       |
| `push` to `main` (path filter) | Build + push to GHCR                      | `latest`, `main`, `sha-<short>` |

BuildKit cache via GHA cache backend (subsequent builds < 2 minutes per arch note's "done at the gate"). Trivy scan runs always, non-blocking, uploads SARIF to GitHub Code Scanning.

**Spec:** [docs/stage1/Helm_T1_Launch_Spec_V2.md §T0.A12](docs/stage1/Helm_T1_Launch_Spec_V2.md)
**Arch note:** [docs/stage1/arch_notes/T0.A12_ci_container_build.md](docs/stage1/arch_notes/T0.A12_ci_container_build.md)

## Verification

**This PR's own CI run validates the build path.** The workflow's path filter matches the workflow file itself, so opening this PR triggers a build-only run.

**The push path** (build + push to GHCR with `latest`/`main`/`sha-<short>`) only fires after merge — first-merge-of-this-PR is the live test. If push fails, fix forward in a follow-up `fix(ci)` PR.

## Files added

| File                                  | Change                                                                                                                                                   |
| ------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `.github/workflows/build-publish.yml` | NEW — single job (build-publish) wired with docker/setup-buildx + login (push only) + metadata-action for tags + build-push-action + Trivy SARIF upload. |

## Implementation notes (small flags)

1. **`pr-<NN>` tags on PR builds.** Architect noted in arch-note open question #2: "T4.6 will reconcile push-on-PR for preview env consumption." Decided: PR builds load to local Docker for Trivy scan but do NOT push to GHCR. T4.6 will flip this to `push: true` for `pr-<NN>` tags when preview environments need the image. Today PR builds verify the Dockerfile compiles; tomorrow they feed previews.

2. **Trivy SARIF → Code Scanning, not PR comment.** Arch note said "PR comment" (`security-events: write` permission). I went with SARIF upload to GitHub Code Scanning instead because:
   - SARIF persists across PRs (history) instead of being a one-shot comment that gets buried
   - Free for public repos (which this is, per architect's visibility decision)
   - Same data, durable surface
   - PR comment alternative is easy to add later if Code Scanning is too quiet

3. **`ignore-unfixed: true` on Trivy.** Vulns without an upstream fix are noise — there's nothing actionable. Filtering them keeps the SARIF report focused on things we can act on (bumping a pinned dep, rebuilding the base image).

4. **Path filter includes the workflow file itself.** So edits to `build-publish.yml` re-run the workflow even when no Dockerfile changes — useful for catching breakage in the workflow during iteration.

5. **Single-arch (amd64) per architect.** Render free tier + Maxwell's box are both amd64. Adding arm64 doubles build time for zero current consumer.

## Spec deviations (small, flagged)

1. **Trivy surface = Code Scanning SARIF, not PR comment** (see implementation note 2).

2. **`pr-<NN>` tag is computed but not pushed** at T0.A12. Will be enabled by T4.6.

## Maxwell-side step (after first merge to main)

GHCR packages start **private by default** when first pushed, even from a public repo. After the first successful merge-and-push, you'll need to flip the package visibility to public (per architect decision):

1. Go to your GitHub profile → Packages → `helm-runtime`
2. Settings → Change visibility → Public
3. Optional: link the package to this repo so it shows in the repo's sidebar

One-time action; future pushes inherit the visibility.

## Adjacent debt explicitly NOT in scope

- **Multi-arch builds (amd64 + arm64).** Architect rejected at T1; revisit when something on ARM enters the picture.
- **Cosign-signed images.** Architect rejected at T1; revisit at Stage 2.
- **Image-size budget.** Architect: "Wait until bloat is a real problem."
- **Build helm-ui in this workflow.** Architect rejected; UI ships to Vercel, separate substrate.
- **PR-tag cleanup on PR close.** When T4.6 flips PR builds to push-on-PR, it'll need a `gh-actions` job that deletes `pr-<NN>` images on PR close. Not in scope here.

## What this unlocks

- **T4.4 (Dev Deployment Decision)** — having images in GHCR makes "deploy to X" a registry-pull conversation
- **T4.11 (Persistent Dev Deployment)** — Render config will reference `ghcr.io/mconn0330-svg/hammerfall-solutions/helm-runtime:latest` (or pinned SHA)
- **T4.6 (Preview Environments per PR)** — flips the `pr-<NN>` build to push, gives every PR a deployable image
- **One-line rollback after T4.11** — `docker pull ghcr.io/.../helm-runtime:sha-<previous>` and restart
- **T0.A7's Dockerfile is now CI-validated on every change** — no more local-only Docker confidence

Phase 0A pacing note: task 12 of ~15. Three left: T0.A13 (gitleaks, Batch), T0.A14 (dependency automation, ARCH), T0.A15 (cost summary, Batch).

## STOP gate

ARCH-tier — architect already approved the design. Bundle review for: (a) implementation matches the design, (b) the small flags (Code Scanning vs PR comment, `pr-<NN>` deferred to T4.6) are defensible.

After approval + merge:

1. The push path runs for the first time. If it works: GHCR has its first published image and you flip visibility to public.
2. T0.A13 (gitleaks secret scanning, Batch) is next.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
