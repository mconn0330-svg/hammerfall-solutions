# Contributing

Hammerfall is a single-developer project (Maxwell McConnell), but the discipline below applies to anyone — including future-Maxwell — touching the code.

## Read first

1. **[AGENTS.md](AGENTS.md)** — operating contract for any agent (or human) working in this repo. Hard rules, soft defaults, where to look for known failures.
2. **[V2 launch spec](docs/stage1/Helm_T1_Launch_Spec_V2.md)** — canonical for all T1 work. If you're unsure what to build, this is the source of truth.
3. **[Architecture decision records](docs/adr/)** — load-bearing decisions and the reasoning behind them. Template at `docs/adr/0000-template.md`.
4. **[Runbooks](docs/runbooks/)** — known failure modes with diagnosis + fix steps. Template at `docs/runbooks/0000-template.md`.

## Commit conventions

Every commit follows [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/). Enforced by `commitlint.config.js` locally (T0.A2 hook) and in CI (T0.A4).

Allowed types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `ci`, `build`, `perf`, `style`, `revert`.
Allowed scopes: `memory`, `runtime`, `ui`, `agent`, `prompt`, `infra`, `ci`, `docs`, `migration`, `repo`, `auth`, `obs`, `ops`.

Format: `type(scope): subject in lowercase, no trailing period`

Examples (from the spec):

- `feat(memory): add outbox pattern for write durability`
- `fix(prompt): resolve helm_prompt.md brain.sh references`
- `chore(repo): add AGENTS.md operating contract`

## Branching

- One feature branch per task ID. Branch name: `feature/<task-id>-<short-slug>` (e.g., `feature/t0a1-repo-operating-contract`).
- Never push directly to `main`. PR every change.
- Each PR opens with a SITREP in `docs/stage1/SITREPs/` citing the task ID(s) addressed and any out-of-scope items surfaced.

## Review gates

- **STOP-tier tasks** require Maxwell's explicit approval before merge.
- **ARCH-tier tasks** require the architect's approval of the matching one-pager in `docs/stage1/arch_notes/` before build starts.
- **IMPL-tier tasks** ship under standard PR review.

Tier labels are set in the V2 spec at task definition time. They are not relabeled mid-build.

## When you find a problem

**Adjacent to the current task** (same file, same module, code you're already editing): fix it in flight. Accumulated debt is worse than a slightly larger diff. See AGENTS.md "Clean adjacent debt as you go."

**Outside the current task's adjacency** (a different module, something you'd have to go looking for): append a `### Finding #NNN — title` block to `docs/stage1/Post_T1_Findings.md` and reference it in the PR's SITREP. The queue is for genuinely out-of-scope discoveries.

The line: did you notice it because of work you were already doing, or did you go hunting for it? The former gets fixed; the latter gets queued.
