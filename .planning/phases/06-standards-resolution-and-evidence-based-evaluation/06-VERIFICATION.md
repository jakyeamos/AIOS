# 06 Verification: Standards Resolution And Evidence-Based Evaluation

## Status

Passed.

## Phase Outcome

Phase 6 binds execution to explicit standards and preserves evidence-backed evaluation outcomes through pre-execution resolution, briefing packet persistence, stage findings, broadened execution-first evidence, closeout aggregation, and operator lifecycle commands.

## Observable Success Criteria

- Each task resolves to the correct success criteria and standards set before execution begins: satisfied by `resolve_task_standards()`, `selected_criteria_json`, `selected_standards_json`, session-start previews, and standards preview CLI.
- Completed work is evaluated against explicit criteria rather than generic model judgment: satisfied by `evaluate_stage_findings()`, workflow-stage persistence, and success criteria evaluator integration.
- Execution-first verification is enforced for stateful, cross-system, and core-logic changes: satisfied by broadened code path detection and execution evidence from artifacts, RTK reports, tool events, and workflow reports.
- Findings, blockers, warnings, passes, and accepted tradeoffs are stored durably per run: satisfied by `success_criteria_findings`, `success_criteria_stage_findings`, evaluation artifacts, closeout reports, and finding lifecycle commands.

## Verification Commands

- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_success_criteria.py tests/test_agentize.py tests/test_agent_rules_runtime.py -q` -> 27 passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_success_criteria.py tests/test_agentize.py tests/test_orchestration_runtime.py -q` -> 41 passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_success_criteria.py tests/test_orchestration_runtime.py tests/test_aios_cli.py -q` -> 51 passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check ...` -> passed for all touched Phase 6 files
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format --check ...` -> passed for all touched Phase 6 files
- `UV_CACHE_DIR=/tmp/uv-cache uv run basedpyright ...` -> 0 errors for touched Phase 6 Python modules

## Commits

- `34ac1c58 feat(criteria): resolve standards before execution`
- `73a3608a docs(planning): record standards resolution`
- `bad40d56 feat(criteria): persist workflow stage findings`
- `19c7f242 docs(planning): record workflow stage findings`
- `94654b53 feat(criteria): resolve findings and broaden evidence`
- `54ee14f8 docs(planning): record finding lifecycle controls`

## Follow-Up

- Add an explicit operator tradeoff-recording command when the accepted-tradeoff authoring workflow is promoted from evaluation metadata to an operator surface.
