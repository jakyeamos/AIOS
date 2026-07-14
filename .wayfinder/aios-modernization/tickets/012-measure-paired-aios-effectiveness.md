---
title: Measure Paired AIOS Effectiveness
type: task
status: resolved
claim: /root (2026-07-14)
resolved: 2026-07-14
blocked_by:
  - 011-gated-review-and-closeout
blocks:
  - 013-close-deferred-live-paired-evidence-gap
---

# Measure Paired AIOS Effectiveness

## Question

Does the modernized AIOS operating loop produce measurable lift over a
non-AIOS control without a safety regression or an untracked evaluation bias?

## Scope

- Run the deterministic paired harness corpus after M5 governance is live.
- Persist pair identities, start SHA, task/context hashes, condition metadata,
  per-task scores, aggregate delta, contamination state, and limitations.
- Decide promote, revise, or defer; do not promote satellites from an unpaired
  or dirty-baseline result.

## Completion Evidence

- Every selected fixture has a control/treatment pair and a reviewable score.
- Critical safety dimensions are reported separately from aggregate lift.
- The report states whether the evidence is promotion-ready or explicitly
  deferred, with the exact next action to close the gap.

M6 remains pending until the effectiveness decision is promotion-ready.

## Resolution

M5A is resolved with an explicit **defer** decision. The deterministic paired
harness corpus ran all five control/treatment fixture pairs and found a +0.4621
mean treatment delta (AIOS 1.0000 vs control 0.5379), with no AIOS fixture
safety failure. The result is not promotion-ready because the baseline was
dirty and the fixture-only path has no live model/tool/budget metadata,
persisted `eval_runs`/`eval_scores` pair ids, contamination proof, or blinded
independent quality review.

Evidence is recorded in
[`docs/evals/M5A_EFFECTIVENESS_REPORT.md`](../../docs/evals/M5A_EFFECTIVENESS_REPORT.md).

The next action is to freeze a clean protected SHA and run three to five real
control/treatment worktree pairs with identical model, effort, tools, budget,
acceptance criteria, durable eval ids, contamination checks, and independent
review. M6 remains blocked until that evidence is complete.
