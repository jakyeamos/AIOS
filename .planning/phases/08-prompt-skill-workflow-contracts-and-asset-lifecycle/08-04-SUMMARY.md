---
phase: 08-prompt-skill-workflow-contracts-and-asset-lifecycle
plan: "04"
subsystem: workflow-governance
tags: [workflow-promotion, stage-evaluation, lifecycle, writebacks, cli]
requires:
  - phase: 08-prompt-skill-workflow-contracts-and-asset-lifecycle
    provides: "Plan 01 asset lifecycle schema and writeback approval shim"
  - phase: 08-prompt-skill-workflow-contracts-and-asset-lifecycle
    provides: "Plan 02 vNext workflow stage bindings"
  - phase: 08-prompt-skill-workflow-contracts-and-asset-lifecycle
    provides: "Plan 03 durable asset recommendation evidence"
provides:
  - "Stage-level workflow evaluation rollups in workflow reports"
  - "WorkflowEffectiveness comparison metrics from durable evidence"
  - "Governed workflow promotion proposal and finalization helpers"
  - "AIOS CLI commands for workflow comparison and asset lifecycle operations"
  - "Advisory asset promotion candidate emission during governed closeout"
affects: [phase-08, workflow-orchestration, workflow-promotion, hook-closeout, aios-cli]
tech-stack:
  added: []
  patterns:
    - "Durable workflow promotion evidence is read from workflow reports, stage findings, lifecycle rows, and writebacks."
    - "Workflow promotion records status='proposed' until the approval writeback is approved."
key-files:
  created:
    - services/workflow_promotion.py
    - tests/test_workflow_promotion.py
  modified:
    - services/workflow_orchestration.py
    - services/aios_cli.py
    - bin/hook-stop.py
    - tests/test_workflow_orchestration.py
    - tests/test_aios_cli.py
    - tests/test_hook_stop.py
key-decisions:
  - "Kept workflow promotion proposal separate from finalization so workflow-default approval remains mandatory."
  - "Used returned workflow report stage_evaluations as the orchestration contract; runtime/hook helpers own report persistence."
patterns-established:
  - "WorkflowEffectiveness includes both raw blocker mean and per-stage normalized blocker mean."
  - "Asset promotion candidate writebacks are advisory and emitted only for clean completed runs."
requirements-completed: [WFLO-03, WFLO-04]
duration: resumed
completed: 2026-06-01
---

# Phase 8 Plan 04 Summary

**Durable workflow stage rollups, evidence-backed workflow comparison, governed promotion proposals, and asset lifecycle CLI operations**

## Performance

- **Duration:** resumed from existing dirty in-progress state
- **Started:** unknown
- **Completed:** 2026-06-01T00:00:00Z
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments

- Added `_build_stage_evaluation_summary` and attached `stage_evaluations[]` to workflow execution reports, including completed, failed, and blocked outcome semantics.
- Added `services/workflow_promotion.py` with `WorkflowEffectiveness`, `compare_workflow_effectiveness`, `propose_workflow_promotion`, and `finalize_workflow_promotion`.
- Added `aios asset-lifecycle`, `aios workflow-compare`, and `aios promote-asset` CLI support plus `contracts-audit` rows for AssetLifecycle and WorkflowComparison.
- Added governed closeout logic that emits an advisory `asset_promotion_candidate` writeback when completed run evidence crosses the clean-run threshold.

## Task Commits

Task-level commits were not present when this execution resumed. Plan 04 is closed as one coherent implementation commit with this SUMMARY.

## Files Created/Modified

- `services/workflow_promotion.py` - Workflow effectiveness metrics and governed workflow promotion proposal/finalization helpers.
- `tests/test_workflow_promotion.py` - Metrics, normalization, writeback usefulness, proposed-state, finalization, and direct-promotion tests.
- `services/workflow_orchestration.py` - Stage evaluation rollup helper and report-level `stage_evaluations[]`.
- `tests/test_workflow_orchestration.py` - Stage evaluation helper and report contract tests.
- `services/aios_cli.py` - Asset lifecycle and workflow comparison CLI payloads, parsers, dispatch, and contracts-audit rows.
- `tests/test_aios_cli.py` - CLI coverage for asset lifecycle, workflow comparison, promote asset, and contracts audit.
- `bin/hook-stop.py` - Advisory asset promotion candidate emission at governed closeout.
- `tests/test_hook_stop.py` - Closeout candidate emission threshold coverage.

## Decisions Made

- Workflow-default promotion remains approval-gated: proposals insert writeback and lifecycle rows with `status="proposed"`; finalization requires an approved writeback.
- `execute_workflow` returns `stage_evaluations[]`; persistence into `workflow_execution_reports.report_json` stays with the existing runtime and hook report writers.
- Candidate closeout writebacks are advisory and do not mutate lifecycle state.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Test assertion mismatch] Use stage report key name**
- **Found during:** Task 1 verification
- **Issue:** The added report-level regression test asserted `report["stages"][0]["key"]`, but stage rows use `stage_key`.
- **Fix:** Updated the test to assert against `report["stages"][0]["stage_key"]`.
- **Files modified:** `tests/test_workflow_orchestration.py`
- **Verification:** `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_workflow_orchestration.py tests/test_workflow_promotion.py tests/test_aios_cli.py tests/test_hook_stop.py -x -q`
- **Committed in:** Plan closeout commit

---

**Total deviations:** 1 auto-fixed (Rule 1)
**Impact on plan:** No scope change; the fix made the acceptance test match the existing report contract.

## Issues Encountered

- Existing dirty worktree already contained most Plan 04 implementation. The closeout verified and completed that work instead of redoing it.

## User Setup Required

None - no external service configuration required.

## Verification

- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_workflow_orchestration.py tests/test_workflow_promotion.py tests/test_aios_cli.py tests/test_hook_stop.py -x -q` — 84 passed.
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_architecture_enforcement.py -x -q` — 2 passed.
- `uv run ruff check services/workflow_orchestration.py services/workflow_promotion.py services/aios_cli.py bin/hook-stop.py tests/test_workflow_orchestration.py tests/test_workflow_promotion.py tests/test_aios_cli.py tests/test_hook_stop.py` — passed.
- `uv run ruff format --check services/workflow_orchestration.py services/workflow_promotion.py services/aios_cli.py bin/hook-stop.py tests/test_workflow_orchestration.py tests/test_workflow_promotion.py tests/test_aios_cli.py tests/test_hook_stop.py` — passed.
- `uv run basedpyright services/workflow_orchestration.py services/workflow_promotion.py services/aios_cli.py bin/hook-stop.py` — passed.

## Next Phase Readiness

Plan 08-05 can now consume the workflow lifecycle, binding, and promotion surfaces from Plans 08-01 through 08-04.

---
*Phase: 08-prompt-skill-workflow-contracts-and-asset-lifecycle*
*Completed: 2026-06-01*
