---
title: Ship the Read-Only V2 Operator Shell
type: task
status: resolved
claim: /root (2026-07-14)
resolved: 2026-07-14
blocked_by:
  - 008-close-m2-browser-validation-frontier
blocks:
  - 010-govern-start-work-verify-slice
---

# Ship the Read-Only V2 Operator Shell

## Question

Can AIOS expose a coherent Today → Start work → Current run read path from
canonical projections while keeping all mutation-capable actions gated off?

## Scope

- Reuse existing source-backed projections and shared UI primitives.
- Establish v2 primary navigation for Today, Start work, and Current run.
- Make Today identify the active project, current stage, evidence state, and
  next action.
- Provide a read-only Start work entry surface that explains the future
  governed path without creating runs or packets.
- Provide a Current run read path with provenance and explicit empty/blocked/
  stale states.
- Add browser coverage for seeded happy, empty, blocked, and stale fixtures at
  the M2 viewport and keyboard matrix.
- Do not implement write actions, dual writes, or Python mutation routing in
  this ticket.

## Completion Evidence

- The v2 shell renders from canonical server-side projections with no second
  state store or UI-owned DDL.
- Primary navigation is task-centred and responsive at all required viewports.
- The three read paths expose source, freshness, authority, and next action.
- Empty, blocked, stale, and happy states are distinguishable and actionable.
- Existing v1 read-only routes remain available as fallback.
- Static, browser, console, network, accessibility, and architecture gates
  pass; no mutation request is emitted by the shell.

## Resolution

M3 is complete. The shell now renders Today (`/`), Start work (`/start`), and
canonical control-plane Current run (`/runs/:id`) from existing server-side
tRPC projections. Legacy session ids retain the existing detail fallback.
Task-centred primary navigation, contextual satellite disclosure, skip-link and
focus behavior, responsive layout, and explicit healthy/blocked/stale/empty
state contracts are implemented without a second store, request-time DDL, or
mutation-capable actions.

Evidence:

- `pnpm --dir aios-ui test:browser` — 2 tests passed (M2 and M3); three
  viewports, seeded projections, keyboard traversal, console/network policy,
  screenshots, no horizontal overflow, and zero mutation requests.
- `pnpm --dir aios-ui lint` — passed.
- `pnpm --dir aios-ui lint:architecture` — passed (126 modules / 256 deps).
- `pnpm --dir aios-ui lint:warning-baseline` — passed (0/71).
- `pnpm --dir aios-ui lint:anti-slop:fixtures` — passed.
- `pnpm --dir aios-ui build` and `pnpm context:validate` — passed.

M4 is the next ticket: govern the Start work → Verify mutation slice through
the Python owner before enabling any UI writes.
