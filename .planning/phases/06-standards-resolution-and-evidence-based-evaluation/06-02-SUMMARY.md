# 06-02 Summary: Workflow Stage Findings

## Result

AIOS now records workflow-stage success criteria findings as durable queryable evidence and includes stage blockers in closeout governance.

## Shipped

- Added `success_criteria_stage_findings` to `schema.sql` and runtime schema helpers.
- Added `stage_applicability` to criterion records so criteria can opt into workflow-stage evaluation.
- Added `evaluate_stage_findings()` and `persist_stage_findings()` in `services/success_criteria.py`.
- Updated `services/workflow_orchestration.py` to evaluate and persist stage findings when workflows run with a DB connection and run id.
- Updated `bin/hook-stop.py` to include stage evaluations in governed closeout reports and require review when blocker stage findings remain open.
- Added regression coverage for stage applicability, durable finding persistence, runtime schema creation, and closeout aggregation.

## Files Modified

- `schema.sql` - 852 lines
- `services/success_criteria.py` - 1341 lines
- `services/workflow_orchestration.py` - 1086 lines
- `bin/hook-stop.py` - 881 lines
- `bin/aios_orchestration_runtime.py` - 1553 lines
- `tests/test_success_criteria.py` - 476 lines
- `tests/test_agentize.py` - 300 lines
- `tests/test_orchestration_runtime.py` - 1045 lines

## Verification

- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_success_criteria.py tests/test_agentize.py tests/test_orchestration_runtime.py -q` -> 41 passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check services/success_criteria.py services/workflow_orchestration.py bin/hook-stop.py bin/aios_orchestration_runtime.py tests/test_success_criteria.py tests/test_agentize.py tests/test_orchestration_runtime.py`
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format --check services/success_criteria.py services/workflow_orchestration.py bin/hook-stop.py bin/aios_orchestration_runtime.py tests/test_success_criteria.py tests/test_agentize.py tests/test_orchestration_runtime.py`
- `UV_CACHE_DIR=/tmp/uv-cache uv run basedpyright services/success_criteria.py services/workflow_orchestration.py bin/hook-stop.py bin/aios_orchestration_runtime.py` -> 0 errors

## Requirement Evidence

- STND-02 and STND-04 are backed by durable stage findings, JSON evaluation artifacts, and closeout report aggregation.
