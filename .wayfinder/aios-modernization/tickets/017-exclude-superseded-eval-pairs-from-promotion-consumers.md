---
title: Exclude Superseded Eval Pairs from Promotion Consumers
type: task
status: resolved
claim: /root (2026-07-14)
resolved: 2026-07-14
blocked_by: []
---

# Exclude Superseded Eval Pairs from Promotion Consumers

## Question

Can the durable eval ledger retain superseded evidence for audit while making
it impossible for a downstream promotion consumer to select that evidence?

## Scope

- Add explicit, durable supersession metadata to `eval_pairs` with an
  append-only `superseded` event.
- Preserve `list_eval_pairs` as the complete audit-history view.
- Add a promotion-ready query and CLI path that requires every promotion
  gate and excludes superseded rows.
- Add a CLI command to mark a known stale pair superseded with a reason.
- Do not delete or rewrite prior pair events, report files, or benchmark rows.

## Completion Evidence

- A finalized promote pair appears in the promotion-ready view only while it
  is not superseded and all score, contamination, review, and report gates
  are present.
- Superseding that pair removes it from the promotion-ready view while the
  full audit view still returns the row and its superseded event/reason.
- Service and CLI regression tests cover the fail-closed selection contract.
- The implementation documents that M6 remains blocked until the remaining
  evidence, telemetry, UI, and satellite gates are closed.

## Resolution

Resolved the consumer-boundary blocker. `eval_pairs` now carries durable
`superseded_at` and `superseded_reason` fields, and `supersede_eval_pair`
records an append-only `superseded` event without changing the original
decision or status. The new `list_promotion_ready_eval_pairs` service query
requires finalized promotion, scores/delta, passed contamination, passed
independent review with a reference, and a report path, while excluding
superseded rows. The CLI exposes this as `eval pair-list --promotion-ready`
and provides `eval pair-supersede --pair-id ... --reason ...`. The ordinary
pair list remains the complete audit view.

Evidence:

- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_eval_run_service.py tests/test_aios_cli.py` — 108 passed.
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check services/eval_run_service.py services/aios_cli.py tests/test_eval_run_service.py tests/test_aios_cli.py` — passed.
- `UV_CACHE_DIR=/tmp/uv-cache uv run basedpyright services/eval_run_service.py services/aios_cli.py tests/test_eval_run_service.py tests/test_aios_cli.py` — 0 errors, 0 warnings, 0 notes.

M6 remains blocked by the corrected benchmark's audit-only scope, missing
provider telemetry, incomplete Verify → Review → Closeout browser coverage,
and the remaining satellite rollback/deletion and mutation-owner gates.
