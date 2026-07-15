---
title: Run a Promotion-Grade Implementation Benchmark for M6
type: task
status: open
claim: /root (2026-07-15)
blocked_by: []
---

# Run a Promotion-Grade Implementation Benchmark for M6

## Scope

Replace the historical read-only audit corpus with a fresh three-task paired
benchmark over real implementation and verification work. Use one protected
clean SHA, matched control/treatment worktrees, identical model/effort/tools/
budget/task criteria, treatment-only portable context, durable run and score
telemetry, pair-specific contamination evidence, and an independent review.

Candidate tasks are the workflow skill-candidate owner migration, shadow
candidate approval owner migration, and Verify → Review → Closeout browser
coverage. Keep each task isolated and do not promote from incomplete evidence.

## Completion criteria

- six clean task worktrees share one protected SHA and fixed acceptance criteria
- every run has durable duration/token/tool/test telemetry, with unavailable
  cost recorded as null rather than estimated
- every pair has durable task/run/score/pair IDs, hashes, parity metadata,
  pair-specific contamination evidence, report path, and independent review
- `eval pair-list --promotion-ready` returns only pairs that satisfy every gate
- no confirmed P0/P1 findings remain in the adversarial review
- M6 remains deferred unless the evidence supports an explicit promotion
  decision; no score or artifact is synthesized from the historical packet
