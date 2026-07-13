---
title: AIOS Modernization Map
type: map
status: active
created: 2026-07-10
---

# AIOS Modernization Map

## Notes

- This map turns the "Upgrading to 5.6" mandate into a sequence of bounded
  decisions. It does not replace the established `.planning/` roadmap; once a
  target is approved, the executable milestones belong there.
- Large architectural and UI changes are authorized. Preserve or explicitly
  migrate durable data, authorization/trust properties, valuable domain rules,
  and still-needed external contracts.
- Discovery is read-only for application code. The current `dev` worktree was
  already dirty when the effort began, so its user-owned guidance changes are
  out of scope. The AIOS shadow lane is trace-only rather than a clean baseline
  comparison.
- Existing product invariants are local-first operation, files as durable
  project/context truth, SQLite as the operational spine, governed mutations,
  and agents as the primary user. The first research ticket must verify which
  of these remain intentional product constraints rather than legacy shape.

## Decisions so far

- [Establish a Reproducible Baseline and Product Invariants](tickets/001-establish-reproducible-baseline-and-invariants.md) - The daily loop is real and tested, but data integrity, trust, recovery, UI accessibility, and reproducible verification block an in-place redesign.
- [Choose the V2 Operating Loop and Trust Boundary](tickets/002-choose-v2-operating-loop-and-trust-boundary.md) - V2 is a single-user, local-first, loopback-only control plane: local human approval gates privileged effects; agents can execute scoped work and propose changes; remote authoritative, split, and shared control planes are out of scope.
- [Define Canonical State and Migration Authority](tickets/003-define-canonical-state-and-migration-authority.md) - One Python-owned, versioned migration ledger and logical mutation authority will govern the local `AIOS_DB`; current schema divergence and 557 FK violations block implementation until quarantine and restore gates pass.
- [Specify a Task-Centred Information Architecture and Accessible Design System](tickets/004-specify-task-centred-information-architecture-and-design-system.md) - The v2 UI follows Today → Start work → Current run → Verify → Gated review → Closeout, with contextual satellites, explicit authority/evidence states, and WCAG 2.2 AA proof gates; implementation waits for the UI validation and subsystem decisions.

## Fog

No additional question is sharp enough to chart yet. A remote, redacted,
read-only observer may be reconsidered only after the local state-authority and
privacy contracts are proven; it is not a v2 implementation ticket. Migration
implementation belongs in the later vertical plan after the UI, subsystem,
and validation-contract tickets resolve.
