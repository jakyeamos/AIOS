---
phase: 11-testing-benchmark-evaluation-and-shadow-workflows
plan: "01"
completed_at: "2026-06-13T00:00:00.000Z"
requirements:
  - EVAL-01
key-files:
  created:
    - services/eval_run_service.py
    - tests/test_eval_run_service.py
  modified:
    - schema.sql
    - services/aios_cli.py
    - tests/test_aios_cli.py
metrics:
  focused_tests_passed: 14
---

# Phase 11 Plan 01 Summary

## Result

Created the durable eval-run record foundation for Phase 11. AIOS now has SQLite tables for eval tasks, runs, scores, failures, and gold-set task metadata; a Python service contract for writing and reading eval evidence; and CLI commands for recording, listing, and summarizing eval runs.

## Changed Files

- `schema.sql`
  - Added `eval_tasks`, `eval_runs`, `eval_scores`, `eval_failures`, and `eval_gold_set_tasks` with the columns specified by the plan.

- `services/eval_run_service.py`
  - Added `create_eval_task`, `create_eval_run`, `record_eval_score`, `record_eval_failure`, `list_eval_runs`, `get_eval_run_detail`, and `get_eval_summary`.
  - Validates context profiles, final statuses, and failure priorities with remediation-bearing `ValueError` messages.
  - Validates that eval runs reference an existing eval task before insertion.
  - Stores list fields as JSON strings and returns decoded list fields in read APIs.
  - Summarizes latest score-per-run without inflating run counts when a run has multiple score rows.
  - Initializes only the eval-run tables it owns, so the service works before later Phase 11 tables exist.

- `services/aios_cli.py`
  - Added `aios eval record-run`, `aios eval list-runs`, and `aios eval summary`.
  - Wired the eval command family into DB connection setup, command naming, JSON output, human rendering, and command dispatch.
  - Preserved global `--json` behavior while also accepting subcommand-level `--json`.

- `tests/test_eval_run_service.py`
  - Added service-contract tests for task/run round trips, missing-task rejection, score defaults, failure priority validation, condition and context-profile filters, joined run detail output, summary aggregation, multi-score summary de-duplication, context-profile validation, final-status validation, and missing-later-table tolerance.

- `tests/test_aios_cli.py`
  - Added eval CLI coverage for record/list/summary JSON output and missing-task JSON errors through the real `run_cli` path.

## Verification

- `uv run pytest -q tests/test_eval_run_service.py tests/test_aios_cli.py::test_eval_run_cli_record_list_and_summary_json tests/test_aios_cli.py::test_eval_run_cli_rejects_missing_task_json` passed: 14 tests.
- `uv run ruff check services/eval_run_service.py services/aios_cli.py tests/test_eval_run_service.py tests/test_aios_cli.py` passed.
- `uv run ruff format --check services/eval_run_service.py services/aios_cli.py tests/test_eval_run_service.py tests/test_aios_cli.py` passed.
- `uv run basedpyright services/eval_run_service.py services/aios_cli.py tests/test_eval_run_service.py tests/test_aios_cli.py` passed with 0 errors and 2 existing environment warnings for unresolved `pytest` imports.
- Plan-contract grep verified the five schema blocks, service exports/validators, CLI parser/dispatch wiring, and required test cases.

## Broader Check Notes

The full Python ladder was also run on 2026-06-22. The eval-run slice passed its targeted checks, but repo-level checks still fail outside this slice:

- `uv run pytest -q`: 10 failures in learning analysis, contract audit expectations, skills harvest validation shape, and tier-one regression expectations.
- `uv run ruff check .`: 21 issues outside the eval-run slice.
- `uv run ruff format --check .`: 133 files would be reformatted.
- `uv run basedpyright`: 79 errors and 96 warnings.
- `uv run vulture . --min-confidence 70`: passed.

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

All Plan 11-01 must-haves are present and were verified through focused service tests, CLI execution tests, lint, type checking, and direct contract inspection.
