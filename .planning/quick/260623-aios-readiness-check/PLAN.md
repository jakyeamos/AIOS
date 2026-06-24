# Quick Task 260623: AIOS Readiness Check

Date: 2026-06-23

## Objective

Create and run a repeatable readiness gate for AIOS default routing after the
route-selector hardening work.

## Scope

- Route selector stories against a copied live DB.
- Copied-live DB CLI surfaces: `start-work`, `operator-search`, `daily-flow`,
  and `next-action`.
- Operator inspectability evidence for route decisions and daily-flow traces.
- Regression coverage for canonical success-criteria schema compatibility.

## Boundary

This check proves CLI/copied-live-DB readiness. It does not execute three real
agent implementation runs through the managed runtime; that remains the next
higher-confidence adoption gate.

## Verification

- `python3 scripts/aios-readiness-check.py --db-copy /tmp/aios-readiness-check.db`
- `uv run pytest -q tests/test_next_action.py tests/test_task_routing.py tests/test_aios_cli.py::test_next_action_cli_json tests/test_aios_cli.py::test_daily_flow_preview_cli tests/test_aios_cli.py::test_daily_flow_replay_cli`
- `uv run ruff check services/next_action.py tests/test_next_action.py scripts/aios-readiness-check.py`
