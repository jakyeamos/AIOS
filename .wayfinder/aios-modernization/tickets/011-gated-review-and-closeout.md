---
title: Add Gated Review and Closeout
type: task
status: resolved
claim: /root (2026-07-14)
resolved: 2026-07-14
blocked_by:
  - 010-govern-start-work-verify-slice
blocks:
  - 012-measure-paired-aios-effectiveness
---

# Add Gated Review and Closeout

## Question

Can a verified run move through approval, capability, egress, writeback, and
closeout as explicit governed states without allowing the UI or a replay to
self-authorize durable effects?

## Scope

- Identify the existing Python-owned proposal, approval, capability, egress,
  writeback, and closeout contracts.
- Add one coherent governed transition that records target, actor, capability,
  classification/redaction outcome, evidence, approval state, and rollback
  reference before any durable effect.
- Prove negative paths for missing capability, non-loopback access, missing
  approval, egress policy failure, stale/returned proposals, and closeout
  before verification.
- Preserve the v2 UI as read-only until this owner boundary is executable.

## Completion Evidence

- Approval, rejection/return, stale, and waived states remain distinguishable
  and append-only.
- No rejected, stale, unapproved, non-loopback, or unredacted proposal causes
  a writeback or promotion side effect.
- Closeout cannot report success without verification, required approval,
  changed-artifact evidence, unresolved-delta accounting, and an explicit next
  action or no-follow-up state.
- Focused Python tests, security/egress negative tests, UI/static checks, and
  closeout replay pass.

## Resolution

M5 is complete at the Python-owned governed-effect boundary. `governed_effects`
now records append-only effect events and closeout reviews, enforces the
capability/loopback/egress/redaction/approval contract, rejects terminal
writeback reuse, and preserves rollback/evidence metadata. `verify_run` and
`hook-stop` use the closeout gate so pending approval, unresolved deltas,
missing changed-artifact evidence, or missing next action downgrade a run
instead of allowing a false successful closeout. The v2 UI mutation procedures
now fail closed with an explicit Python-owner error.

Evidence:

- `tests/test_m5_gated_review.py` proves negative security paths, governed
  writeback transitions, terminal-state rejection, approval blocking, and
  closeout after approval.
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_m5_gated_review.py tests/test_m4_start_work.py tests/test_run_verification.py tests/test_orchestration_runtime.py tests/test_workflow_promotion.py tests/test_asset_lifecycle.py tests/test_daily_flow.py tests/test_hook_stop.py` — 82 passed.
- Focused Ruff and BasedPyright checks — passed.
- `pnpm context:validate`, UI lint/typecheck/architecture/build, and the
  pinned browser contract — passed (2 browser tests).

M5A remains pending for a later session: paired AIOS/non-AIOS effectiveness
measurement must precede satellite promotion or v2 cutover.
