---
title: Establish a Reproducible UI Validation Contract
type: research
status: resolved
claim: /root (2026-07-13)
blocked_by: []
blocks:
  - 006-write-v2-target-and-vertical-modernization-plan
---

# Establish a Reproducible UI Validation Contract

## Question

What dependency, lockfile, font, runtime, lint/typecheck, build, browser, and
console-error contract lets AIOS validate future UI and operator-flow changes
deterministically in local and CI environments?

## Known Evidence

- `pnpm lint` cannot execute ESLint or TypeScript because the local anti-slop
  plugin is missing a referenced rule module.
- `pnpm build` depends on fetching Google-hosted fonts and warns about an
  inferred Turbopack root caused by multiple lockfiles.
- Browser inspection found duplicate React keys and an intermittent missing
  `@trpc/server/adapters/fetch` development-runtime failure.

## Completion Evidence

- One authoritative package-manager/lockfile and workspace-root posture.
- A repeatable lint, strict typecheck, build, local browser, and console-error
  matrix that does not depend on incidental network access.
- Explicit treatment of local font assets, optional external dependencies, and
  known development-runtime errors.

## Resolution

Accepted [ADR-004](../../../docs/modernization/ADR-004-reproducible-ui-validation-contract.md)
as the v2 UI validation contract. The target is one explicit pnpm/Node
toolchain, a consolidated workspace/lockfile posture, packaged dependencies,
local or system fonts, an explicit Next root, independent lint/type/build
gates, and a browser journey that fails on console, network, semantic,
responsive, and duplicate-key regressions. Current evidence is recorded as a
baseline rather than a pass: TypeScript and architecture checks pass
independently, but the anti-slop file dependency is stale/out-of-repo, the
Google-font and Turbopack warnings are not deterministic, and the dev tRPC
handler still reproduces the missing `@trpc/server/adapters/fetch` error.
Ticket 006 may now synthesize the UI target, but implementation remains gated
until ADR-004's completion criteria are met.
