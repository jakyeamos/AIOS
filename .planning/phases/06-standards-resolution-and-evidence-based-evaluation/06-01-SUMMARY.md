# 06-01 Summary: Standards Resolution Before Execution

## Result

AIOS now resolves applicable success criteria and standards before execution and persists that selection on briefing packets.

## Shipped

- Added `resolve_task_standards()` in `services/success_criteria.py` to merge registry criteria, standards profiles, execution-first triggers, and resolution warnings.
- Added `selected_criteria_json` and `selected_standards_json` briefing packet columns in schema helpers and runtime migration paths.
- Updated `services/agentize.py` to use registry-backed standards and criteria instead of hardcoded packet standards.
- Updated `bin/hook-session-start.py` to surface applicable criteria, standards, and execution-first triggers in startup context.
- Added regression coverage for resolution merging, briefing packet persistence, agentize packet output, and session-start packet content.

## Files Modified

- `services/success_criteria.py` - 1341 lines
- `services/agentize.py` - 739 lines
- `bin/hook-session-start.py` - 517 lines
- `services/aios_cli.py` - 3938 lines
- `bin/aios_orchestration_runtime.py` - 1553 lines
- `tests/test_success_criteria.py` - 476 lines
- `tests/test_agentize.py` - 300 lines
- `tests/test_agent_rules_runtime.py` - 207 lines

## Verification

- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_success_criteria.py tests/test_agentize.py tests/test_agent_rules_runtime.py -q` -> 27 passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check services/success_criteria.py services/agentize.py bin/hook-session-start.py bin/aios_orchestration_runtime.py services/aios_cli.py tests/test_success_criteria.py tests/test_agentize.py tests/test_agent_rules_runtime.py`
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format --check services/success_criteria.py services/agentize.py bin/hook-session-start.py bin/aios_orchestration_runtime.py services/aios_cli.py tests/test_success_criteria.py tests/test_agentize.py tests/test_agent_rules_runtime.py`
- `UV_CACHE_DIR=/tmp/uv-cache uv run basedpyright services/success_criteria.py services/agentize.py bin/hook-session-start.py bin/aios_orchestration_runtime.py services/aios_cli.py` -> 0 errors

## Requirement Evidence

- STND-01 is backed by `resolve_task_standards()` and persisted briefing packet criteria/standards columns.
- The existing live migration pattern was verified through in-memory schema checks.
