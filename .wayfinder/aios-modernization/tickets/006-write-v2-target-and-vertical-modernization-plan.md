---
title: Write the V2 Target and Vertical Modernization Plan
type: task
status: resolved
claim: /root (2026-07-13)
blocked_by: []
blocks: []
---

# Write the V2 Target and Vertical Modernization Plan

## Question

What independently verifiable vertical milestones will transform the current
product into the agreed v2 without leaving a permanent half-migrated system?

## Scope

- Synthesize the resolved product, trust, data, UI, and subsystem decisions
  into a durable target document and an executable plan under the repository's
  canonical planning system.
- Use end-to-end slices rather than isolated technical layers.
- Give every milestone preserved/changed behavior, migration and rollback
  needs, test/browser proof, deletion targets, failure modes, and completion
  criteria.
- Include final cutover, adversarial review, security/data-integrity review,
  accessibility review, performance checks, documentation, and cleanup.

## Completion Evidence

- Approved target architecture and operator-experience definition.
- A dependency-ordered, reviewable milestone plan with no undefined
  blocker-level decisions.

## Dependencies

Blocked by [Define Canonical State and Migration Authority](003-define-canonical-state-and-migration-authority.md), [Specify a Task-Centred Information Architecture and Accessible Design System](004-specify-task-centred-information-architecture-and-design-system.md), and [Classify Satellite Subsystems and Select the Modernization Strategy](005-classify-satellite-subsystems-and-select-modernization-strategy.md).

## Resolution

Accepted [TARGET.md](../../../docs/modernization/TARGET.md) and [EXEC_PLAN.md](../../../docs/modernization/EXEC_PLAN.md) as the v2 target and executable modernization contract. The target fixes the operator loop, authority/data model, subsystem ownership, contract envelopes, UI/accessibility bar, privacy/observability rules, quality scores, and non-goals. The plan sequences eight gated vertical milestones: shared fixtures; canonical state and recovery; deterministic UI validation; read-only v2 shell; governed Start work → Verify; review/closeout; contextual satellite migration; and cutover/adversarial review/deletion. Each milestone names dependencies, preserved and changed behavior, proof, rollback, failure modes, completion criteria, and deletion targets. The existing `.planning/ROADMAP.md` now links the modernization overlay. Ticket 006 is resolved; implementation begins only at Milestone 0 with the ADR-002 and ADR-004 gates intact.
