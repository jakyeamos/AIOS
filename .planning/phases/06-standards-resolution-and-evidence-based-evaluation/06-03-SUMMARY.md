# 06-03 Summary: Evidence Broadening And Finding Lifecycle

## Result

AIOS now accepts broader execution-first evidence and exposes operator CLI commands for standards preview and criteria finding lifecycle transitions.

## Shipped

- Expanded `execution_evidence_for_session()` in `bin/hook-stop.py` to accept `tool_events` Bash/TestRun rows and validate/test workflow report stages as execution evidence.
- Extended code-file detection for `.mjs` and `.sh` so execution-first triggers cover local scripts and module tests.
- Added shared criteria finding lifecycle states and `resolve_finding()` for run-level and stage-level criteria findings.
- Extended `aios governance-audit` with stage finding totals, stale-open counts, blocker counts, and recent open findings.
- Added `aios criteria-finding resolve --id --status --rationale --evidence --actor --scope`.
- Added `aios standards-resolution preview --project-id --project-name --objective --classification --changed-file --skill --workflow-key`.
- Added regression coverage for tool-event evidence, workflow-stage evidence, finding resolution, stage finding resolution, governance audit stage findings, standards preview output, and execution-first doc/code path behavior.

## CLI Signatures

- `aios criteria-finding resolve --id <finding-id> --status <open|accepted|resolved|waived|stale> [--rationale TEXT] [--evidence VALUE ...] [--actor TEXT] [--scope run|stage|auto]`
- `aios standards-resolution preview [--project-id ID] [--project-name NAME] [--objective TEXT] [--classification TEXT] [--changed-file PATH ...] [--skill KEY ...] [--workflow-key KEY]`

## Files Modified

- `bin/hook-stop.py` - 881 lines
- `services/success_criteria.py` - 1341 lines
- `services/aios_cli.py` - 3938 lines
- `tests/test_success_criteria.py` - 476 lines
- `tests/test_orchestration_runtime.py` - 1045 lines
- `tests/test_aios_cli.py` - 1701 lines

## Verification

- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_success_criteria.py tests/test_orchestration_runtime.py tests/test_aios_cli.py -q` -> 51 passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check bin/hook-stop.py services/success_criteria.py services/aios_cli.py tests/test_success_criteria.py tests/test_orchestration_runtime.py tests/test_aios_cli.py` -> passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format --check bin/hook-stop.py services/success_criteria.py services/aios_cli.py tests/test_success_criteria.py tests/test_orchestration_runtime.py tests/test_aios_cli.py` -> 6 files already formatted
- `UV_CACHE_DIR=/tmp/uv-cache uv run basedpyright bin/hook-stop.py services/success_criteria.py services/aios_cli.py` -> 0 errors

## Requirement Evidence

- STND-03 is backed by broadened execution evidence from hook tool events and workflow reports.
- STND-04 is backed by lifecycle transitions on both `success_criteria_findings` and `success_criteria_stage_findings`.
- The `aios tradeoff record` CLI remains deferred; accepted tradeoffs still flow through existing evaluation metadata.
