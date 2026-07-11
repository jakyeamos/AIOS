---
title: Choose the V2 Operating Loop and Trust Boundary
type: grilling
status: closed
claim: /root (2026-07-10)
blocked_by: []
blocks:
  - 003-define-canonical-state-and-migration-authority
  - 004-specify-task-centred-information-architecture-and-design-system
  - 005-classify-satellite-subsystems-and-select-modernization-strategy
---

# Choose the V2 Operating Loop and Trust Boundary

## Question

What is the smallest coherent v2 operating loop, who is allowed to invoke or
approve mutations, and is AIOS intentionally local-only, authenticated remote,
or a split control-plane product?

## Decision Inputs

- The baseline's verified daily-use behavior and the product invariants it
  identifies.
- The current agent-first, local-first product statement.
- The operational consequences of public UI mutation procedures, local SQLite
  paths, process spawning, deployment scripts, and sensitive-data handling.

## Completion Evidence

- A one-page product and trust-boundary decision with explicit non-goals.
- A named canonical loop from intent through closeout, including human/agent
  roles, approval points, and source-backed success signals.
- A compatibility decision for existing UI routes and CLI/hook entry points.

## Dependencies

Blocked by [Establish a Reproducible Baseline and Product Invariants](001-establish-reproducible-baseline-and-invariants.md).

## Resolution

Accepted [ADR-001: V2 Operating Loop and Trust Boundary](../../../docs/modernization/ADR-001-v2-operating-loop-and-trust-boundary.md).

AIOS v2 is a single-user, local-first, loopback-only control plane. The local
operator approves privileged effects; agents may do scoped work, retain bounded
evidence, and propose but not self-approve durable changes. The canonical loop
is `doctor → intent → route/start → execute → verify → gated review → closeout
→ daily-flow / next-action replay`. Remote authoritative and split control
planes, multi-user sharing, and connector egress are out of scope for v2.

The decision preserves CLI/hook semantics while requiring a future single local
mutation owner and reclassification of direct UI mutation routes. Ticket 003
must resolve data integrity, schema ownership, configuration, recovery, and
migration authority before that boundary can be implemented.
