# M6 Corrected Live Paired Benchmark Report

**Date:** 2026-07-14  
**Decision:** Defer M6 promotion; revise the evidence package and keep
satellite promotion/cutover blocked.  
**Protected start SHA:** `7797f3ed34f15322d34d296f078cfffc604ef28f`  
**Model:** `gpt-5.6-luna`  
**Reasoning effort:** `high`  
**Declared budget:** 20,000 tokens / 900 seconds per run

## Scope and conditions

This is a bounded three-task audit corpus. Each task used a clean control and
treatment worktree at the same protected SHA, the same task and acceptance
criteria, and the same model, effort, tools, and declared budget. Control used
`baseline_repo_only`; treatment used `aios_portable_context_packet` with an
explicit checked-in packet. All runs were read-only and prohibited private
state, network access, and production systems.

| Task | Control score | Treatment score | Delta | Pair decision |
| --- | ---: | ---: | ---: | --- |
| Paired-effectiveness gate readiness | 0.970 | 0.970 | +0.000 | defer |
| Canonical state and migration authority | 0.970 | 0.980 | +0.010 | defer |
| UI and governed write-path readiness | 0.950 | 0.980 | +0.030 | defer |
| **Corpus mean** | **0.963** | **0.977** | **+0.013** | **defer M6** |

Scores are the independent review rubric mean across acceptance coverage,
evidence accuracy, risk/verification quality, decision discipline, and
portability/limitations. This is an audit-quality context-packet delta, not a
productivity, satellite-readiness, or production-safety claim.

## Durable evidence

| Task | Task ID | Control run | Treatment run | Pair ID | Score IDs |
| --- | --- | --- | --- | --- | --- |
| Gate readiness | `eval-task-87fea31a-afda-4567-ae96-aba8c6f4080f` | `eval-run-9b21a3f2-878b-4591-8a86-fe09ce4af90d` | `eval-run-3897f273-b4d6-45c2-aba3-c75c18eae312` | `eval-pair-b03e71ec-ab5b-4469-81ea-d4817ee8badd` | `39bfb9df`, `79e78c7c` |
| Canonical state | `eval-task-70b0fdc9-27f1-445d-86ce-f9a80f918e66` | `eval-run-0ebf2d9a-d27c-4516-98d7-98019b7366cc` | `eval-run-ccb12906-968a-4c46-af68-14392b26da6b` | `eval-pair-daa21647-950b-4c06-8a49-1a28234753d0` | `7af91d26`, `8e2e9f87` |
| UI/write path | `eval-task-d7e9a6da-fa90-4103-896e-92b6d96fdc92` | `eval-run-a198e8a1-809b-4f0a-a17c-baee5d57417f` | `eval-run-2fe1a42c-a0a2-45b9-b203-c6c77e4a387c` | `eval-pair-2f676491-0c8a-4384-aa05-b94dcdac2284` | `b2fdb713`, `8b2a2b3e` |

All corrected pairs have persisted task/run/score/pair IDs, task/prompt/
context hashes, parity metadata, passed contamination evidence, an independent
review reference, and the report path. Their pair-level decision is `defer`
and status is `insufficient_evidence` because the corpus is not a promotion
claim and provider usage telemetry is unavailable.

## Independent review and findings

The fresh review is [`M6_LIVE_BENCHMARK_REVIEW.md`](M6_LIVE_BENCHMARK_REVIEW.md).
It confirmed all six corrected worktrees are clean at the protected SHA and
that the six reports consistently defer M6 promotion.

The review also found a superseded earlier pair,
`eval-pair-c6b68b87-48ac-4268-8908-61c2c5ae5161`, still marked `promote` in the
temporary database. Its treatment artifact and referenced checked-in review
were not available to the corrected review, so it is excluded from this
benchmark and must not support M6. The append-only ledger retains it for audit
history.

No P0/P1 implementation finding is cleared by this benchmark. The review
keeps the following M6 blockers open: remaining UI-owned mutations and
authorization gaps, incomplete Verify → Review → Closeout browser coverage,
satellite-specific rollback/deletion proof, and the absence of general
productivity or production evidence.

## Limitations and next gate

- Provider token, cost, and detailed runtime telemetry were unavailable and
  remain null rather than estimated.
- Tasks were read-only architecture and validation audits; no implementation
  patch or production behavior was exercised.
- The aggregate is three tasks, not a general benchmark or external clean-room
  claim.
- The old promoted pair remains an explicitly excluded, superseded ledger row.

Next: correct or archive the superseded pair in downstream consumers, keep the
three corrected pairs as deferred evidence, and complete the first named
satellite's read-only adapter, mutation-owner migration, rollback/deletion
ledger, and full browser proof before reopening M6 promotion.
