# Phase 16 Plan 16-06 Summary: Retrospective, Model-Selection, And Shadow Parity Metadata

## Completed

- Added `services/retrospective_artifacts.py` for structured retrospective artifact persistence and querying.
- Added `services/workflow_learning.py` as the reviewable proposal bridge for retrospective artifacts.
- Added model-selection telemetry persistence and query helpers to `services/execution_strategy.py`.
- Enriched `services/shadow_branch_runner.py` with shadow parity metadata fields and read helpers.
- Added CLI inspection surfaces: `aios retrospectives`, `aios model-selection`, and `aios shadow parity`.
- Extended `schema.sql` with retrospective artifact, model-selection, and shadow parity metadata tables/columns.

## Verification

- `uv run pytest -q tests/test_retrospective_artifacts.py tests/test_execution_strategy.py tests/test_shadow_branch_runner.py tests/test_shadow_branch_cli.py`
- `uv run ruff check services/retrospective_artifacts.py services/workflow_learning.py services/execution_strategy.py services/shadow_branch_runner.py services/aios_cli.py tests/test_retrospective_artifacts.py tests/test_execution_strategy.py tests/test_shadow_branch_runner.py`
- `uv run python -m services.aios_cli --json --db /tmp/aios-16-06-cli.db --logs-dir /tmp retrospectives`
- `uv run python -m services.aios_cli --json --db /tmp/aios-16-06-cli.db --logs-dir /tmp model-selection`
- `uv run python -m services.aios_cli --json --db /tmp/aios-16-06-cli.db --logs-dir /tmp shadow parity`

## Requirement Coverage

- HARN-07 is complete: retrospective artifacts and model-selection records are durable, queryable, and reviewable without auto-apply behavior.
- HARN-08 is complete: shadow parity metadata now records comparison refs, parity checklist status, failure classification, and replay command or unavailable reason while preserving existing branch workflows.
