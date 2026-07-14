---
title: Expand the Clean Live Paired Benchmark and Adversarial Review
type: task
status: resolved
claim: /root (2026-07-14)
resolved: 2026-07-14
blocked_by:
  - 013-close-deferred-live-paired-evidence-gap
blocks:
  - 014-migrate-contextual-satellites
---

# Expand the Clean Live Paired Benchmark and Adversarial Review

## Question

Does the bounded live paired result remain correct across a small, frozen
three-to-five-task corpus, with durable pair evidence and a separate
adversarial review strong enough to inform the M6 promotion gate?

## Scope

- Freeze one protected clean SHA and one task corpus of three to five real,
  independent repository tasks.
- Run matched control/treatment worktree pairs with identical model, effort,
  tools, budget, prompt, acceptance criteria, and contamination checks.
- Persist every task, run, score, pair, report path, and review reference
  through the canonical eval contract.
- Score each side with a fixed rubric, report aggregate and safety dimensions,
  and record provider telemetry gaps without estimation.
- Obtain a reviewer that did not run either condition; classify findings and
  keep promotion fail-closed on missing or unsafe evidence.

## Completion criteria

- At least three complete, independently scored live pairs share the same
  protected SHA and parity metadata.
- Every pair has passed contamination checks, durable run and score IDs, and
  an independent review reference; incomplete pairs remain insufficient
  evidence.
- The aggregate report includes per-task results, deltas, safety outcomes,
  limitations, and an explicit promote/revise/defer decision.
- M6 advances only if the evidence satisfies the existing promotion gates;
  otherwise M6 remains blocked with the exact next action recorded.

## Stop conditions

Stop and record the blocker if credentials, provider telemetry, clean
worktrees, reproducible scoring, or independent review are unavailable. Do not
convert fixture evidence or a single bounded pair into a broad effectiveness
claim.

## Resolution

Captured a corrected three-task live control/treatment corpus from protected
SHA `7797f3ed34f15322d34d296f078cfffc604ef28f`. The tasks covered paired-
effectiveness gate readiness, canonical state/migration authority, and UI/
governed write-path readiness. All six corrected runs were read-only, used
`gpt-5.6-luna` at high effort with matched tools and a declared 20,000-token /
900-second budget, and left six clean worktrees.

Persisted evidence includes three task rows, six run rows, six score rows,
three corrected `eval_pairs` rows, task/prompt/context hashes, pair-specific
contamination evidence, report paths, and fresh independent review. The
independent rubric means are control `0.963`, treatment `0.977`, delta
`+0.013`.

The pair-level decisions are explicitly `defer` / `insufficient_evidence`:
these are read-only audit tasks with unavailable provider usage telemetry and
cannot support a general productivity, satellite-readiness, or production-
safety claim. A prior single-task pair remains append-only in the temporary
ledger as a superseded `promote` row because its treatment artifact was
missing; it is excluded from the corrected report and must not support M6.

Evidence: [`M6_LIVE_BENCHMARK_REPORT.md`](../../docs/evals/M6_LIVE_BENCHMARK_REPORT.md),
[`M6_LIVE_BENCHMARK_EVIDENCE.json`](../../docs/evals/M6_LIVE_BENCHMARK_EVIDENCE.json),
and [`M6_LIVE_BENCHMARK_REVIEW.md`](../../docs/evals/M6_LIVE_BENCHMARK_REVIEW.md).

M6 remains blocked. Ticket 014 must not begin satellite promotion until the
superseded ledger row is excluded from consumers and the first named satellite
has read-only adapter proof, Python-owner mutation migration, rollback/
deletion evidence, and full Verify → Review → Closeout browser coverage.
