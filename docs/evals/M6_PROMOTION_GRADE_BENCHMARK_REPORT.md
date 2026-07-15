# M6 promotion-grade implementation benchmark

**Date:** 2026-07-15  
**Protected start SHA:** `4d8adbca3b89d6259e252f26aaad0db69a9bf102`  
**Model:** `gpt-5.6-luna`  
**Effort:** `high`  
**Declared budget:** 20,000 tokens / 900 seconds per run  
**Decision:** **Defer M6 promotion**

This is a fresh three-task implementation benchmark with six clean disposable
worktrees. Control used `peer_repo_only`; treatment used the explicitly named
M6 portable context packet. Every run has durable duration, token, tool-call,
failed-command, changed-file, and test-command telemetry. Provider cost is
unavailable and is stored as `null`, never estimated.

## Pair ledger

| Task | Task ID | Control run | Treatment run | Pair ID | Control | Treatment | Delta | Contamination | Decision |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | --- | --- |
| Workflow skill owner | `eval-task-7881f379-d09a-4079-9223-aa6c4563123b` | `eval-run-30e0d8be-24a2-4562-9ded-824e0cc60ef8` | `eval-run-4340d543-c197-4bfc-9837-a484ab6c4319` | `eval-pair-f1225fbd-1094-4c4d-9123-f3b1d977e1b8` | 0.7600 | 0.7914 | +0.0314 | failed/unproven | defer |
| Shadow approval owner | `eval-task-7a92dd1b-b3ce-40b2-837b-eb78dd190ec7` | `eval-run-acc64f1c-33c0-4fc4-9fcc-79ec7d1a201b` | `eval-run-55739101-a75f-450d-bdc1-68ea244f2df7` | `eval-pair-82c2c36d-95d4-42f0-b5be-4f449e05a9d0` | 0.7500 | 0.7671 | +0.0171 | failed/unproven | defer |
| Verify → Review → Closeout browser contract | `eval-task-3b4d5011-c58a-44f3-9518-766b98f5132a` | `eval-run-997c8c67-743e-44db-955a-a1a73344d279` | `eval-run-a777854d-0f6c-48b5-a26d-60158e4a84f5` | `eval-pair-cb4e9ff0-608c-40d5-a42b-f7fc69d7769a` | 0.7200 | 0.6029 | −0.1171 | failed/unproven | revise |

`eval pair-list --promotion-ready` returns `[]` for the fresh ledger.

## Run telemetry

| Run | Duration | Total tokens | Tool calls | Failed commands | Changed files |
| --- | ---: | ---: | ---: | ---: | ---: |
| A control | 785,512 ms | 8,563,215 | 184 | 12 | 7 |
| A treatment | 613,723 ms | 8,621,701 | 106 | 6 | 6 |
| B control | 607,344 ms | 4,958,489 | 142 | 10 | 9 |
| B treatment | 603,140 ms | 7,433,284 | 160 | 13 | 7 |
| C control | 597,875 ms | 5,000,860 | 120 | 6 | 4 |
| C treatment | 772,027 ms | 6,308,342 | 180 | 15 | 4 |

The raw JSONL event files and final reports remain under
`/private/tmp/aios-m6-promotion/` for this local session. The durable ledger
export is [`M6_PROMOTION_GRADE_BENCHMARK_EVIDENCE.json`](M6_PROMOTION_GRADE_BENCHMARK_EVIDENCE.json),
and the recording script is
[`m6-promotion-ledger.py`](../../benchmark/m6-promotion-ledger.py).

## What passed

- A and B owner migrations have credible focused Python/CLI tests, lint,
  typecheck, architecture checks, preserved tRPC shapes, and no new
  authorization regression.
- Candidate and shadow writes were removed from the changed TypeScript
  surfaces.
- C has deterministic fixture generation, schema validation, lint/typecheck,
  and Playwright discovery for the intended contract.
- Cross-pair source contamination was not detected; B-control's task-local
  commit has the protected SHA as its parent.

## Why M6 remains blocked

The independent review is [`M6_PROMOTION_GRADE_ADVERSARIAL_REVIEW.md`](M6_PROMOTION_GRADE_ADVERSARIAL_REVIEW.md).
It found no P0, but found P1 promotion blockers:

- treatment packet identity was not captured in the original run receipts;
  context cleanliness is therefore fail-closed/unproven;
- B-treatment reports the wrong rollback parent;
- C-treatment omits the dedicated Review journey and does not seed full
  closeout evidence.

All six browser/build executions were environment-blocked by the external
`node_modules` symlink, blocked Google Fonts access, or sandbox `listen EPERM`.
Those are recorded as evidence gaps, not silently counted as passes.

## Required next gate

Rerun B from a clean protected-SHA pair with treatment packet identity and
prompt/context hashes captured in the run receipt; repair C-treatment's Review
and full closeout fixtures; then execute build and browser tests in a runner
with in-worktree dependencies, network/font handling, and loopback access.
