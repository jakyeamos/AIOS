---
title: Choose the V2 Operating Loop and Trust Boundary
type: grilling
status: open
claim: unclaimed
blocked_by:
  - 001-establish-reproducible-baseline-and-invariants
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

Unresolved.
