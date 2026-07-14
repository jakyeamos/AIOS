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
- [Establish a Reproducible UI Validation Contract](tickets/007-establish-reproducible-ui-validation-contract.md) - UI acceptance now requires deterministic pnpm/Node/package, local-font, explicit-root, independent quality-gate, runtime, browser, network, and console evidence; current anti-slop, font/root, and tRPC failures remain recorded blockers for implementation.
- [Classify Satellite Subsystems and Select the Modernization Strategy](tickets/005-classify-satellite-subsystems-and-select-modernization-strategy.md) - V2 uses a parallel surface with progressive migration and one state/mutation owner: core runtime/UI/eval/learning/session systems stay in AIOS, CTS/business memory remain sidecars, and extracted contracts/tools stay adapter-only.
- [Write the V2 Target and Vertical Modernization Plan](tickets/006-write-v2-target-and-vertical-modernization-plan.md) - The accepted target and execution contract define one operator loop, one authority boundary, and eight gated vertical milestones from shared fixtures and canonical recovery through UI validation, governed closeout, satellites, cutover, adversarial review, and deletion.
- [Close the M2 Browser Validation Frontier](tickets/008-close-m2-browser-validation-frontier.md) - Pinned Playwright now proves seeded routes, responsive layouts, console/network policy, and keyboard traversal; generated catalogs and static spawn arguments remove the NFT warning, so M3 is unblocked.
- [Ship the Read-Only V2 Operator Shell](tickets/009-ship-read-only-v2-operator-shell.md) - Today, Start work, and canonical Current run now render from source-backed projections with task-centred navigation, explicit state/provenance contracts, and zero-mutation browser proof; M4 is next for Python-owned governed writes.
- [Govern the Start Work Verify Slice](tickets/010-govern-start-work-verify-slice.md) - Python-owned start-work now creates a foreign-key-safe route/packet/run/invocation envelope, preserves partial-state resume evidence and project provenance, and completes source-backed verification; M5 is next for gated review and closeout.
- [Add Gated Review and Closeout](tickets/011-gated-review-and-closeout.md) - Python-owned governed effect events and closeout reviews now enforce capability, loopback, egress, redaction, rollback, approval, changed-artifact, unresolved-delta, and next-action gates; UI mutation procedures fail closed behind the owner, and M5A is next for paired effectiveness measurement.
- [Measure Paired AIOS Effectiveness](tickets/012-measure-paired-aios-effectiveness.md) - Deterministic five-fixture control/treatment evidence shows +0.4621 lift with no fixture safety regression, but the dirty baseline and fixture-only execution defer promotion; M6 remains blocked pending clean real paired evaluation.

## Fog

No additional question is sharp enough to chart yet. A remote, redacted,
read-only observer may be reconsidered only after the local state-authority and
privacy contracts are proven; it is not a v2 implementation ticket. Migration
implementation belongs in the later vertical plan after the UI, subsystem,
and validation-contract tickets resolve.
