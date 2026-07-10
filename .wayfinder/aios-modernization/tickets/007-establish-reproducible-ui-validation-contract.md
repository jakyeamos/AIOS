---
title: Establish a Reproducible UI Validation Contract
type: research
status: open
claim: unclaimed
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

Unresolved.
