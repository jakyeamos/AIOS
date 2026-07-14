---
title: Close the Deferred Live Paired-Effectiveness Evidence Gap
type: task
status: resolved
claim: /root (2026-07-14)
resolved: 2026-07-14
blocked_by:
  - 012-measure-paired-aios-effectiveness
blocks:
  - 014-migrate-contextual-satellites
---

# Close the Deferred Live Paired-Effectiveness Evidence Gap

## Question

Can AIOS persist and validate a reviewable control/treatment pair so a future
clean live benchmark cannot lose its run identities, parity metadata, or
contamination and independent-review state?

## Scope

- Add a durable `eval_pairs` record linking one control and one treatment run.
- Require a shared protected start SHA, task/prompt/context hashes, and explicit
  model/effort/tools/budget parity metadata.
- Persist contamination status/reason, independent-review status/notes, report
  path, and promote/revise/defer decision state.
- Expose create, finalize, and list operations through the existing eval CLI.
- Keep live model execution out of this slice; this contract must not turn the
  deterministic fixture result into a rollout claim.

## Completion Evidence

- Pair creation rejects unknown runs, mismatched tasks, mismatched start SHAs,
  and incomplete parity metadata.
- Finalization rejects promotion when contamination or independent review is
  missing or failed, while allowing an explicit defer decision.
- Pair records round-trip through SQLite and the CLI with stable JSON shapes.
- Focused service and CLI tests pass; no benchmark effectiveness claim is
  added.

M6 remains blocked until this contract is used by a clean live paired run and
the resulting evidence is independently reviewed.

## Resolution

Implemented the durable `eval_pairs` contract in `schema.sql` and
`services/eval_run_service.py`. Pair creation now links distinct control and
treatment runs from the same task and protected start SHA, requires lowercase
SHA-256 task/prompt/context hashes plus model/effort/tools/budget parity
metadata, rejects duplicate links, and records a created event. Finalization
captures latest scores and delta, records contamination and independent-review
evidence, preserves created/finalized events, and marks deferred or revised
pairs as `insufficient_evidence`; promotion fails closed without both scores,
passed contamination, and passed independent review.

The CLI exposes `eval pair-create`, `eval pair-finalize`, and `eval pair-list`.
The pair schema, service, CLI, and focused tests also persist and round-trip a
durable `report_path` for review artifacts.
Focused service, CLI, shadow, ablation, and harness tests pass (139 tests),
with Ruff and Python compilation clean for the touched implementation. This
does not execute a live model benchmark or change the M5A defer decision. M6
remains blocked until a clean live pair is captured and independently reviewed.
