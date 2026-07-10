---
title: Classify Satellite Subsystems and Select the Modernization Strategy
type: research
status: open
claim: unclaimed
blocked_by:
  - 002-choose-v2-operating-loop-and-trust-boundary
  - 003-define-canonical-state-and-migration-authority
blocks:
  - 006-write-v2-target-and-vertical-modernization-plan
---

# Classify Satellite Subsystems and Select the Modernization Strategy

## Question

Which current subsystems earn a place in the v2 core, which retain a narrow
adapter/sidecar contract, and should the resulting change be a deep refactor,
parallel v2 migration, or clean rewrite?

## Scope

- Assess CTS, business memory, evaluation, learning, context compilation,
  session intelligence, and workflow orchestration against the chosen daily
  loop and data-authority rules.
- Identify duplicated or obsolete paths, compatibility hazards, and external
  contracts that constrain deletion.
- Compare in-place, parallel-v2, and clean-rewrite strategies against data
  safety, deployability, verification, and future maintainability.

## Completion Evidence

- A retain/adapt/retire matrix with owners and contract boundaries.
- One justified modernization strategy with rollback/cutover posture.
- A list of old code, dependencies, routes, flags, and docs expected to leave
  once all consumers migrate.

## Dependencies

Blocked by [Choose the V2 Operating Loop and Trust Boundary](002-choose-v2-operating-loop-and-trust-boundary.md) and [Define Canonical State and Migration Authority](003-define-canonical-state-and-migration-authority.md).

## Resolution

Unresolved.
