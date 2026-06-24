# Quick Task 260623: AIOS Readiness Check Summary

Date: 2026-06-23

## Result

The CLI/copied-live-DB readiness gate passes.

`scripts/aios-readiness-check.py` now copies `data/aios.db`, runs route selector
stories, creates real `start-work` packets in the copied DB, verifies route
decision search, checks daily-flow preview and replay, and confirms next-action
returns structured output.

## Changed

- Added `scripts/aios-readiness-check.py`.
- Fixed `services.next_action._from_open_blockers()` so it supports both older
  fixture-style `success_criteria_findings.run_id` schemas and the canonical
  schema where findings link to runs through `success_criteria_evaluations`.
- Added `tests/test_next_action.py` coverage for the canonical schema.
- Wrote readiness reports:
  - `.planning/quick/260623-aios-readiness-check/readiness-report.json`
  - `.planning/quick/260623-aios-readiness-check/readiness-report.md`

## Verification

- Passed: `python3 scripts/aios-readiness-check.py --db-copy /tmp/aios-readiness-check.db`
- Passed: `uv run pytest -q tests/test_next_action.py tests/test_task_routing.py tests/test_aios_cli.py::test_next_action_cli_json tests/test_aios_cli.py::test_daily_flow_preview_cli tests/test_aios_cli.py::test_daily_flow_replay_cli`
- Passed: `uv run ruff check services/next_action.py tests/test_next_action.py scripts/aios-readiness-check.py`

## Adoption Boundary

AIOS is now ready for default routing smoke usage at the CLI/copied-live-DB
level. Before making it the mandatory launcher for all serious work, run a
small real managed-run pilot with three low-risk tasks and confirm closeout,
evaluation, writeback, and operator inspection all work without manual joins.
