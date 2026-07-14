# M6 Live Paired Evidence Report

**Date:** 2026-07-14  
**Decision:** Promote the bounded paired-evidence result; keep broader M6
execution gated on the documented limitations.  
**Protected baseline SHA:** `7797f3ed34f15322d34d296f078cfffc604ef28f`  
**Model:** `gpt-5.6-luna`  
**Reasoning effort:** `high`  
**Declared budget:** 20,000 tokens / 900 seconds per run

## Task and conditions

Task `m6-gate-readiness-v1` asked the model to assess whether M6 could proceed,
separate deterministic fixture evidence from live evidence, and state the
minimum contamination, parity, scoring, and independent-review gates. The
model was prohibited from editing files, accessing private state, using the
network, or touching production systems.

| Side | Condition | Context profile | Result |
| --- | --- | --- | --- |
| Control | `baseline_repo_only` | `peer_repo_only` | Correctly kept M6 blocked. |
| Treatment | `aios_portable_context_packet` | `peer_portable_context_packet` | Correctly kept M6 blocked and confirmed the packet-aware report-path contract. |

The control and treatment used the same task statement, acceptance criteria,
protected SHA, model, effort, tools, and declared budget. The treatment also
received the bounded checked-in AIOS context packet described in the review.

## Durable pair evidence

The run and pair identifiers are persisted in the temporary benchmark database
used for this report and are reproduced below:

- Task ID: `eval-task-cdda9c37-3ffb-4572-b18d-c2a5bd360738`
- Control run ID: `eval-run-8f4b9f45-d1b6-4d1d-ac82-1022a6cebe5e`
- Treatment run ID: `eval-run-528bc7c9-ac97-4491-90f1-dbad26ee15f2`
- Pair ID: `eval-pair-c6b68b87-48ac-4268-8908-61c2c5ae5161`
- Task hash: `5eeb7ed57f4fd6246e7023406826accd29372f9171710412005821123920d3e3`
- Prompt hash: `7c43df777c987d2bfdd6aadd67afdc517f3eb1df75bfb124de8cbaafbb08e3cb`
- Context hash: `b8fa6aa3de877ce6a0867464b0f2daa8b613315d7070b9d7169cac4951f68b68`
- Report path: `docs/evals/M6_LIVE_PAIRED_REPORT.md`
- Durable pair export: `docs/evals/M6_LIVE_PAIRED_EVIDENCE.json`
- Independent review: `docs/evals/M6_LIVE_PAIRED_REVIEW.md`

The pair was finalized with `contamination_status=passed`,
`independent_review_status=passed`, and `decision=promote`. The service's
promotion gate was exercised only after both scores were present.

## Scores

| Condition | Overall score |
| --- | ---: |
| Control | 0.9500 |
| Treatment | 1.0000 |
| Delta | **+0.0500** |

The score is limited to this report-assessment task. It measures a portable
context-packet lift and is not a general productivity, safety, or M6 satellite
promotion claim.

## Verification

- Clean control and treatment clones were created from the protected SHA.
- Both model runs completed without repository changes.
- In-memory schema and pair smoke checks confirmed `eval_pairs.report_path`
  round-trips and fail-closed deferred status when evidence is incomplete.
- The independent reviewer inspected both outputs, the acceptance criteria,
  parity declaration, and worktree cleanliness.
- The canonical service/CLI focused suite passed before this benchmark:
  `UV_CACHE_DIR=/tmp/uv-cache .venv/bin/pytest -q
  tests/test_eval_run_service.py tests/test_aios_cli.py` — 107 passed.

## Limitations and next gate

This is one bounded live task. The provider did not expose durable token/cost
telemetry, and the clean clones lacked the local `.agents` directory; treatment
therefore used only the explicit portable packet. The M5A report still calls
for three to five real tasks before a broad effectiveness claim. M6's
consumer-by-consumer satellite migration and later cutover remain gated on
that broader benchmark and its adversarial review.
