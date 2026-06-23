# Plan 20-07 Summary: Internal Planning Schema And Logs

**Status:** Complete  
**Requirement:** ESPL-07  
**Completed:** 2026-06-23

## What Changed

- Added `services/planning_context.py` with structured planning fields for source invocation, workflow, phase, task type, complexity, risk, selected lenses, handoff target, validation depth, output format, sub-agent strategy, model strategy, TMCP evidence, execution result, validation result, rework, and notes.
- Added `services/planning_log.py` for local JSONL planning logs, execution-symmetric comparison axes, serialization round-trips, and managed-run TMCP default/bypass contract metadata.
- Fixed `bin/aios-managed-run.py` import ordering so managed-runtime subprocess runs can import repo services reliably.
- Narrowed `bin/hook-stop.py` verifier-gate reclassification so explicit normal managed-runtime closeouts are not converted to failed closeouts after the managed workflow has already produced runtime evidence.
- Added `tests/test_planning_context.py` and `tests/test_planning_log.py`.
- Marked ESPL-07 complete in `.planning/REQUIREMENTS.md`.

## Key Decisions

- No schema change was added. JSONL plan logs cover lightweight planning evaluation, while existing `tmcp_traversal_receipts`, artifacts, and workflow reports remain the durable managed-run evidence path.
- Planning log comparison axes explicitly distinguish generic versus execution-symmetric plans, natural-language versus GSD phase planning, slash-command versus auto-routed planning, and selected-lens versus no-lens plans.
- TMCP default adoption is represented as structured metadata: non-trivial managed runs require packet and receipt IDs unless an explicit bypass reason is recorded.
- TMCP and planning behavior stayed in intent-specific services and logs, not broad always-loaded agent instructions.

## Verification

- `uv run pytest -q tests/test_planning_context.py tests/test_planning_log.py tests/test_execution_symmetric_planner.py tests/test_orchestration_runtime.py`
- `uv run ruff check services/planning_context.py services/planning_log.py tests/test_planning_context.py tests/test_planning_log.py bin/aios-managed-run.py bin/hook-stop.py`
- `git diff --check`
