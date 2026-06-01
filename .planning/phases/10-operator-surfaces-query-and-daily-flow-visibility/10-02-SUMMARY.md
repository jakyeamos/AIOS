---
phase: 10-operator-surfaces-query-and-daily-flow-visibility
plan: "02"
subsystem: next-action
tags: [operator-surfaces, next-action, cli, drill-down, recommendations]
requires:
  - phase: 05-writeback-governance
    provides: improvement writebacks
  - phase: 06-standards-resolution-and-evaluation
    provides: success criteria findings
  - phase: 07-delta-scoring-and-health-backfill
    provides: standards deltas and backfill tasks
  - phase: 08-prompt-skill-workflow-contracts-and-asset-lifecycle
    provides: promotion lifecycle items
  - phase: 09-continuous-learning-and-conservative-optimization
    provides: learning proposals and terminal-run learning events
provides:
  - Python next-action fusion backend
  - `aios next-action` CLI command
  - NextAction contracts-audit row
affects: [next-action, cli, contracts-audit, operator-surfaces]
tech-stack:
  added: []
  patterns:
    - read-time recommendation fusion
    - priority-bucket ranking with confidence tiebreak
    - drill-down path construction per action source
key-files:
  created:
    - services/next_action.py
    - tests/test_next_action.py
    - .planning/phases/10-operator-surfaces-query-and-daily-flow-visibility/10-02-SUMMARY.md
  modified:
    - services/aios_cli.py
    - tests/test_aios_cli.py
    - tests/test_architecture_enforcement.py
key-decisions:
  - "No new tables or caches; next actions recompute on every read."
  - "Learning proposals are discriminated inside pending writebacks because they share the same governed approval queue."
  - "Promotion lifecycle candidates are project-agnostic when no project_id exists on the source row."
requirements-completed: []
requirements-partial: [OPER-02, OPER-03]
duration: 19min
completed: 2026-06-01
---

# Phase 10 Plan 02 Summary

**Python next-action fusion backend and CLI**

## Action Contract

`NextActionKind` values:

`launch_remediation_workflow`, `approve_pending_writeback`, `resolve_open_blocker`, `review_learning_proposal`, `fix_terminal_run_gap`, `promote_candidate_asset`, `investigate_regressed_metric`, `complete_backfill_task`.

`NextAction` shape:

`kind`, `title`, `rationale`, `project_id`, `priority_bucket`, `recommended_workflow_key`, `evidence_ids`, `drill_down_path`, `confidence`, `metadata`.

## Sources Fused

- `standards_delta_items` -> `launch_remediation_workflow`
- `improvement_writebacks` pending approval -> `approve_pending_writeback`
- learning-analysis writebacks -> `review_learning_proposal`
- open blocker `success_criteria_findings` -> `resolve_open_blocker`
- terminal runs without learning events -> `fix_terminal_run_gap`
- `standards_backfill_tasks` -> `complete_backfill_task`
- `promotion_lifecycle_items.status='candidate'` -> `promote_candidate_asset`

Missing source tables are skipped, and empty results are valid.

## Ranking

Actions sort by bucket weight, then confidence descending:

- `foundational`: 0
- `high_leverage`: 1
- `quick_wins`: 2
- `blocked`: 3
- `waived_deferred`: 4

Default limit is 10; max limit is 50.

## CLI

`aios next-action` accepts:

- `--project <project_id>` optional
- `--limit <n>` default 10, max 50
- `--json`

Response data contains `actions`, `total_actions`, `project_id`, and `limit`.

## Contracts Audit

`contracts-audit` now includes:

- `name`: `NextAction`
- `status`: `partial` until `aios-ui/server/aios/next-action.ts` and later tRPC/UI surfaces ship
- `source_of_truth`: `services/next_action.py`, `services/aios_cli.py:cmd_next_action`

## Verification

- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_next_action.py tests/test_aios_cli.py tests/test_architecture_enforcement.py -x -q` -> 77 passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check services/next_action.py services/aios_cli.py tests/test_next_action.py tests/test_aios_cli.py tests/test_architecture_enforcement.py` -> passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format --check services/next_action.py services/aios_cli.py tests/test_next_action.py tests/test_aios_cli.py tests/test_architecture_enforcement.py` -> passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run basedpyright services/next_action.py services/aios_cli.py` -> passed

## Next Plan Readiness

Plan 10-03 can use this backend as the next-action step in daily-flow traces. Plan 10-04 must mirror this `NextAction` shape and drill-down path discipline in TypeScript.

---
*Phase: 10-operator-surfaces-query-and-daily-flow-visibility*
*Completed: 2026-06-01*
