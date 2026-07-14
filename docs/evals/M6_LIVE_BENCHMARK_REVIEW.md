# Independent adversarial review

Scope is limited to the corrected three-task corpus. No repository or benchmark files were modified.

## Scores

### Task 1 — paired-effectiveness readiness

Pair: `eval-pair-b03e71ec-ab5b-4469-81ea-d4817ee8badd`

| Dimension | Control | Treatment | Rationale |
|---|---:|---:|---|
| Acceptance coverage | 1.00 | 1.00 | Covers the M6 blocker, evidence distinction, parity/contamination/score/review gates, report-path sufficiency, and telemetry limits. |
| Evidence accuracy | 0.95 | 0.95 | Source-backed and appropriately distinguishes fixture from live evidence; does not independently verify the corrected ledger. |
| Risk/verification quality | 0.95 | 0.95 | Gives concrete promotion gates and a clean next action. |
| Decision discipline | 1.00 | 1.00 | Correctly blocks M6 promotion without overstating fixture results. |
| Portability/limitations | 0.95 | 0.95 | Clearly limits productivity, safety, cost, and token claims. |
| **Overall** | **0.97** | **0.97** | **Delta: 0.00** |

### Task 2 — canonical state and migration authority

Pair: `eval-pair-daa21647-950b-4c06-8a49-1a28234753d0`

| Dimension | Control | Treatment | Rationale |
|---|---:|---:|---|
| Acceptance coverage | 1.00 | 1.00 | Identifies ownership and boundary, classifies gates, gives more than three risks with verification, makes a bounded decision, and separates evidence classes. |
| Evidence accuracy | 0.95 | 0.95 | Uses specific ADR, code, test, and project-truth references while labeling historical claims as independently unverified. |
| Risk/verification quality | 0.95 | 1.00 | Control is strong; treatment adds clearer first-satellite, rollback, quarantine, privacy, and authority verification requirements. |
| Decision discipline | 1.00 | 1.00 | Both correctly defer satellite migration and avoid treating fixture evidence as live effectiveness. |
| Portability/limitations | 0.95 | 0.95 | Explicitly distinguishes checked-in, historical, fixture, and live evidence. |
| **Overall** | **0.97** | **0.98** | **Delta: +0.01** |

### Task 3 — UI and governed write-path readiness

Pair: `eval-pair-2f676491-0c8a-4384-aa05-b94dcdac2284`

| Dimension | Control | Treatment | Rationale |
|---|---:|---:|---|
| Acceptance coverage | 0.90 | 1.00 | Treatment explicitly covers mutation, authorization, accessibility, responsive, browser, console, and provenance gaps. Control covers most but is less explicit on accessibility and responsive risk. |
| Evidence accuracy | 0.95 | 0.95 | Claims are source-backed and clearly distinguish fixture/browser/production evidence. |
| Risk/verification quality | 0.95 | 1.00 | Both provide exact checks; treatment gives the more complete state and viewport/browser matrix. |
| Decision discipline | 1.00 | 1.00 | Both defer promotion and permit only read-only adapter work. |
| Portability/limitations | 0.95 | 0.95 | Both clearly state that no production or live browser proof was performed. |
| **Overall** | **0.95** | **0.98** | **Delta: +0.03** |

## Aggregate

| Measure | Control | Treatment | Delta |
|---|---:|---:|---:|
| Acceptance coverage mean | 0.967 | 1.000 | +0.033 |
| Evidence accuracy mean | 0.950 | 0.950 | 0.000 |
| Risk/verification mean | 0.950 | 0.983 | +0.033 |
| Decision discipline mean | 1.000 | 1.000 | 0.000 |
| Portability/limitations mean | 0.950 | 0.950 | 0.000 |
| **Overall corpus mean** | **0.963** | **0.977** | **+0.013** |

This is an audit-quality delta only. It is not evidence of productivity improvement, satellite readiness, or production safety.

## Ledger and contamination verification

| Check | Result |
|---|---|
| Durable task/run/pair linkage | **Pass** — each corrected pair links one task, control run, and treatment run. |
| Durable score linkage | **Fail** — no `eval_scores` rows exist for any corrected run; pair scores and deltas are null. |
| Shared protected SHA | **Pass** — all corrected pairs and all six worktrees use `7797f3ed34f15322d34d296f078cfffc604ef28f`. |
| Task/prompt/context hashes | **Pass structurally** — all are present, 64-character hashes, and match within each pair. |
| Model/effort/tools/budget parity | **Pass structurally** — shared model, high effort, tools, and 900-second/20,000-token budget cap. |
| Provider token/cost fields | **Pass** — usage and cost fields remain null; no estimates were made. |
| Contamination status | **Partial/fail for row integrity** — status is `passed`, but all three corrected rows incorrectly reference the Task 1 rerun worktrees. |
| Actual six-worktree cleanliness | **Pass** — all six worktrees are clean and at the protected SHA. |
| Independent review reference | **Fail** — all corrected pairs remain `pending` with no review reference. |
| Report reference | **Fail** — every corrected pair points to `docs/evals/M6_LIVE_BENCHMARK_REPORT.md`, which is absent from the corrected worktrees and does not point to the supplied final-output files. |
| Pair finalization | **Fail** — all corrected pairs remain `open` with no scores, decision, or finalization timestamp. |

## Findings

### P0 — promotion-critical corrected-ledger incompleteness

None of the corrected pairs is promotion-admissible: scores are not durably recorded, independent review is still pending, review references are absent, and pairs are not finalized.

The Task 2 and Task 3 contamination records also point to Task 1 worktrees, so their row-level contamination evidence is not trustworthy even though the six actual worktrees are clean.

### P1 — superseded old-pair promote state remains

The old pair `eval-pair-c6b68b87-48ac-4268-8908-61c2c5ae5161` remains durably marked `finalized` with `decision = promote`, scores `0.95` and `1.00`, and a passed review.

Treat this as a superseded evidence-integrity finding only. It must not support M6.

### P1 — corrected report traceability is incomplete

The corrected ledger references a missing generic report path rather than the six supplied final outputs or a valid independent-review artifact.

### P2 — limited operational telemetry

Corrected runs have no persisted duration, token usage, cost, or meaningful run-level execution telemetry. Provider token/cost unavailability is correctly preserved, but this corpus cannot support speed, cost-efficiency, or usage claims.

### P3

No additional P3 finding affecting the bounded audit conclusion.

## Decision

**M6: DEFER promotion. Revise the evidence package before reconsideration.**

The three outputs are substantively strong and consistently conclude that M6 should not promote. However, the corrected durable ledger is incomplete and contains contamination-path mislinkage. The old promoted pair remains superseded and invalid support.

Minimum next gate:

1. Correct each pair’s worktree and report references.
2. Persist one score record per run and control/treatment/delta values per pair.
3. Attach an independent review artifact and reference.
4. Re-run or attest contamination checks per pair.
5. Finalize all three pairs with a non-promote decision and verify that automated consumers exclude the superseded old pair.

Until that gate passes, M6 remains deferred.