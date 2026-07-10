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

- None. The current evidence is sufficient to chart the questions but not to
  choose a redesign strategy responsibly.

## Fog

- Whether AIOS should remain a single-user local control plane, gain an
  authenticated remote operator mode, or explicitly split those products.
- Which satellite surfaces—CTS, business memory, evaluation, and learning—are
  core to the daily operating loop versus separately owned or removable.
- The scope of legacy-data migration, compatibility, and cutover once the
  product and persistence decisions are made.
- The right implementation slices, release strategy, and adversarial review
  gates; these become concrete only after the target architecture and operator
  experience are chosen.
