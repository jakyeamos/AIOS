# M6 promotion-grade adversarial review

**Protected start SHA:** `4d8adbca3b89d6259e252f26aaad0db69a9bf102`  
**Review source:** fresh read-only Codex review over all six disposable worktrees  
**Decision:** defer M6 promotion

No pair is promotion-ready. There are no P0 findings. The review found credible
owner-migration implementations in A and B, but the browser/build proof is not
executable in the isolated environment and the context packet provenance is not
independently captured by the run receipts.

| Pair | Decision | Main reason |
| --- | --- | --- |
| A — workflow skill candidates | defer | Owner migration is strong, but browser/build proof and treatment-context provenance are incomplete. |
| B — shadow approval | defer | Protected-boundary/report provenance failure; implementation itself is credible. |
| C — browser contract | revise | Treatment omits the dedicated Review journey and does not seed full closeout evidence. |

## Independent scores

Scores are reviewer estimates, not provider telemetry. Cost is unavailable and
is stored as `null`; overall scores in the durable ledger are the arithmetic
mean of the seven available dimensions.

| Worktree | Success | Quality | Speed | Context effectiveness | Context portability | Autonomy | User trust | Overall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A control | 0.92 | 0.86 | 0.72 | 0.60 | 0.55 | 0.87 | 0.80 | 0.7600 |
| A treatment | 0.94 | 0.87 | 0.81 | 0.63 | 0.56 | 0.90 | 0.83 | 0.7914 |
| B control | 0.95 | 0.80 | 0.84 | 0.60 | 0.54 | 0.93 | 0.59 | 0.7500 |
| B treatment | 0.95 | 0.86 | 0.85 | 0.61 | 0.57 | 0.89 | 0.64 | 0.7671 |
| C control | 0.71 | 0.78 | 0.82 | 0.55 | 0.59 | 0.84 | 0.75 | 0.7200 |
| C treatment | 0.52 | 0.58 | 0.70 | 0.50 | 0.56 | 0.82 | 0.54 | 0.6029 |

## Findings

### P1 — promotion-critical

- Benchmark condition provenance is not independently auditable in the run
  receipts. The compiled-context and receipt artifacts observed by the review
  are byte-identical; no treatment-only packet identity or prompt/context hash
  was captured during the runs. The new ledger records hashes for the next
  gate, but this benchmark remains fail-closed rather than claiming parity.
- `task-b-control` ends at `e7b45ec5…`, not the protected SHA. Its commit parent
  is the protected SHA and its files are task-B-only, so cross-pair source
  contamination was not detected; the committed-result anomaly is retained in
  the ledger.
- `task-b-treatment` reports the wrong rollback parent (`4cd4183f…`) even
  though the protected benchmark SHA is `4d8adbca…`.
- C-treatment does not cover the dedicated Review run. Its matrix contains
  Verify, failed Verify, and Closeout but omits `run-fixture-review` and does
  not assert the stage rail. Its setup also seeds no run events or artifacts,
  weakening closeout coverage.

### P2 — incomplete but environment-limited

- Browser and production-build proof is incomplete for every pair. The observed
  failures are environment failures: external `node_modules` symlinks, blocked
  Google Fonts access, and sandbox `listen EPERM`; they are not source-test
  failures.
- C-treatment's error allowlist accepts any error from
  `controlPlane.reviewWriteback`, not only the expected 412, weakening that
  browser gate.
- All worktrees contain an untracked `.venv` link and ignored caches/test
  results. No generated files were found tracked. B-control truth-file changes
  remain uncommitted.

### P3 — audit ambiguity

- C-control uses M5 naming for an M6 task (`m5-verify-review-closeout.spec.ts`
  and `m5-*` screenshots).

## Contamination verdict

Cross-pair source contamination was not detected. A, B-treatment, C-control,
and C-treatment start from the protected SHA; B-control has a task-local commit
whose parent is protected. Promotion-grade treatment-context cleanliness is
**unproven**, so the durable pairs use `contamination_status=failed` and remain
ineligible for promotion.

## Required next gate

Rerun B from a clean protected-SHA pair with the treatment packet identity and
prompt/context hashes captured in the run receipt; repair C-treatment's Review
and full closeout fixtures; then execute build and browser tests in a runner with
in-worktree dependencies, network/font handling, and loopback access.
