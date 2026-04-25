# ADR 0001 — TypeScript conversion for helm-ui (Path A)

**Status:** Accepted
**Date:** 2026-04-25
**Deciders:** Maxwell McConnell (sole stakeholder), with architect input via T0.A5 spec

## Context

T0.A5 ("Type Discipline") asks for static type guarantees across the codebase. The Python side has an obvious answer — `mypy --strict` on `services/helm-runtime/` — and that's what this same task lands. The JavaScript side has no such default. helm-ui is currently ~30 `.jsx` files with no type information beyond what eslint can infer at the syntax level.

The V2 spec (§T0.A5) frames the decision as a binary choice and recommends a path; this ADR records the decision so the choice and its alternatives are durable.

The two paths the spec considered:

- **Path A — TypeScript conversion.** Convert every `.jsx` file to `.tsx`. Add `tsconfig.json` with strict settings. Vite already supports TS out of the box; vitest already supports `.test.tsx`. The eslint flat config picks up TS via `typescript-eslint`. ~3 PRs of mechanical work; bigger first diff but durable type safety on every prop, every state shape, every event handler.
- **Path B — JSDoc type comments + ESLint strict.** Keep `.jsx`. Add JSDoc type comments on exported component props and any non-obvious local function signatures. Add `eslint-plugin-jsdoc` to enforce. Cheaper to land, lighter guarantees: type info is comment-shaped, IDE-supported but not compiler-enforced, and the migration cost grows with the codebase rather than shrinking.

## Decision

**Take Path A — convert helm-ui from JSX to TSX.** Bundle the conversion with T1.5b ("design-token application"), which is queued and already touches every component. Two birds.

T0.A5 (this PR) does not perform the conversion. It records the decision so T1.5b's PR description can cite ADR 0001 instead of re-litigating the choice. The conversion lands as a single `refactor(ui)` PR (or three sequential PRs if the diff is too noisy to review as one) once T1.5b begins.

## Consequences

- **Positive:**
  - Compile-time guarantees on prop shapes, state types, event handler signatures, and module boundaries — same posture as the Python side.
  - Better IDE support across the stack (autocomplete, refactor safety, jump-to-definition through prop chains).
  - The conversion happens once, while the codebase is small (~30 files). At T2.x the UI roughly doubles; converting then would be ~2x the diff and ~3x the review burden.
  - Catches a class of bugs ESLint can't see: passing a number where a string is expected, accessing properties on a possibly-undefined object, untyped event payloads from `framer-motion` and `react-three-fiber`.

- **Negative:**
  - One bigger PR (or three medium ones) where every component file changes. Even mechanical TS conversion is reviewable surface area.
  - Some third-party libraries (`framer-motion`, `@react-three/drei`, `@react-three/fiber`) have type signatures that are loose or `any`-heavy. We'll inherit some of that looseness; perfection is not the bar.
  - `tsconfig.json` adds one more piece of toolchain to keep aligned with eslint and vitest. Not free, but the cost is one-time setup.

- **Neutral / open:**
  - Strictness level for `tsconfig.json` will be decided at T1.5b (likely `strict: true` plus `noUncheckedIndexedAccess` to mirror mypy strict). Not a decision to make in this ADR.
  - Whether to enforce TS-specific lint rules (`@typescript-eslint/no-unused-vars`, `no-floating-promises`, etc.) is a downstream decision; the eslint config will be updated as part of T1.5b too.

## Alternatives considered

- **Path B — JSDoc + ESLint strict:** rejected. The advantages (cheaper to land, smaller diff) are real but front-loaded; the disadvantages (lighter guarantees, growing migration cost, no compiler enforcement) compound over time. JSDoc as a long-term type strategy works for libraries that need to keep emitting plain JS — that's not this codebase. helm-ui ships transformed code via vite either way; there's no runtime cost to TS.

- **Status quo (no JS type discipline):** considered and rejected by T0.A5's existence. Asymmetric type discipline (strict Python, untyped JS) is a worse outcome than either consistent strictness or consistent looseness. The runtime side has chosen strict; the UI side should match.

- **Defer the decision to Stage 2:** considered. Rejected because the conversion gets more expensive every PR. T1.5b is the natural opportunity (every component touched); skipping that window means re-touching everything later.

## References

- Related ADRs: none (this is the first)
- Related spec sections: `docs/stage1/Helm_T1_Launch_Spec_V2.md` §T0.A5 (Type Discipline), §T1.5 (UI design-token application)
- External: [TypeScript handbook on JSX](https://www.typescriptlang.org/docs/handbook/jsx.html); [Vite TS support](https://vite.dev/guide/features.html#typescript)

---

_Format: [Michael Nygard ADR](https://github.com/joelparkerhenderson/architecture-decision-record/tree/main/locales/en/templates/decision-record-template-by-michael-nygard)._
