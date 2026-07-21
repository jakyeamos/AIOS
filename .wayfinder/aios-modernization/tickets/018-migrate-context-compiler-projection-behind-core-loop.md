---
title: Migrate the Context Compiler Projection Behind the Core Loop
type: task
status: resolved
claim: /root (2026-07-14)
resolved: 2026-07-14
blocked_by: []
---

# Migrate the Context Compiler Projection Behind the Core Loop

## Question

Can the existing read-only Context Compiler page become an explicit,
source-backed satellite projection with browser proof, without adding a second
context authority or any mutation path?

## Scope

- Add a typed projection envelope that names the context compiler source,
  freshness, authority, and next action.
- Render that envelope on `/context` using the existing file-backed compiler
  output and receipt.
- Add deterministic browser proof for mobile, tablet, and desktop layouts,
  accessibility/focus, same-origin responses, console cleanliness, and zero
  mutation requests.
- Record the adapter rollback/deletion target; do not change compiler writes,
  packet generation, or context-root ownership.

## Completion Evidence

- The page remains read-only and its displayed data is sourced from the
  compiler output/receipt and context inventory.
- The projection exposes explicit authority, freshness, and next-action state
  instead of presenting file-backed data as an unqualified dashboard fact.
- The pinned browser contract passes at all three viewports with no console,
  request, or mutation failures.
- The prior page shape remains the rollback target and no second context store
  or write path is introduced.

## Resolution

Resolved as a read-only contextual satellite slice. The Context Compiler
server adapter now returns an explicit projection envelope naming its
file-backed source paths, compiler authority, CLI mutation owner, freshness
state, and next action. `/context` renders that contract as a visible
read-only projection without adding any write path or second context store.
The prior page shape remains the rollback target; deleting the projection
envelope and contract panel restores the prior surface without data migration.

Evidence:

- `pnpm --dir aios-ui lint` — passed.
- `pnpm --dir aios-ui lint:architecture` — passed (126 modules, 256 dependencies).
- `pnpm --dir aios-ui build` — passed.
- `pnpm --dir aios-ui test:browser -- m6-context-satellite.spec.ts` — 3 passed, including the new context satellite plus M2/M3 regression contracts; all three viewports had no console errors, failed responses, horizontal overflow, or mutation requests.
- `node tools/context-compile.mjs --validate` — passed.

Complexity + simplification gate: no new loops, N+1 reads, client-side
recomputation, duplicate authority, or speculative abstraction were found.
The projection envelope is constructed once beside the existing file reads;
the UI remains a thin display surface. No findings were deferred.

The root `pnpm context:validate` wrapper attempted an automatic install and
failed because the worktree cannot resolve the existing external
`context-compiler-contract` file dependency; the direct validator passed and
no dependency or lockfile changes were made.

M6 is advanced but not fully promoted. The paired-effectiveness decision
remains deferred because the corpus is audit-only and provider telemetry is
unavailable; the remaining write-owner, rollback/deletion, and broader
evidence gates stay open.
