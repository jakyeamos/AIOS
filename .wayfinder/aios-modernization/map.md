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

## Fog

No additional question is sharp enough to chart yet. New implementation,
cutover, and adversarial-review questions should be added only after the open
product, data, UI, subsystem, and validation-contract tickets resolve.
