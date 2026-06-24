---
phase: 28-expert-rubric-remediation-cli-and-verification
plan: 01
subsystem: cli
tags: [tmcp, expert-review, cli, workflow-runtime, pytest]
requires:
  - phase: 27-expert-rubric-remediation-workflow-runtime
    provides: Active expert rubric remediation workflow runtime and registry contract
provides:
  - `aios tmcp review-plan` parser and execution branch
  - CLI JSON output for expert review artifacts, validations, and remediation slices
  - CLI regression coverage for artifact writing and malformed evidence JSON
affects: [phase-28-quality-closeout, phase-28-smoke-verification]
tech-stack:
  added: []
  patterns: [read-only target project CLI, workflow-backed artifact generation, strict JSON evidence parsing]
key-files:
  created: []
  modified:
    - services/aios_cli.py
    - tests/test_aios_cli.py
key-decisions:
  - "Compiled TMCP packets against `--project-path` but routed workflow artifact output through `--output-dir`, keeping the target project read-only."
  - "Implemented the CLI through `execute_workflow` instead of calling Phase 26 builders directly."
patterns-established:
  - "Operator-facing workflow CLIs should return workflow key, run id, validations, artifact paths, and bounded slice summaries."
  - "Malformed operator JSON inputs should return structured CLI errors rather than silently coercing to strings."
requirements-completed: []
duration: 1min
completed: 2026-06-24
---

# Phase 28 Plan 01: TMCP Review-Plan CLI Summary

**`aios tmcp review-plan` now runs the expert rubric remediation workflow and writes review artifacts under a requested output directory.**

## Performance

- **Duration:** 1 min
- **Started:** 2026-06-24T16:37:02-04:00
- **Completed:** 2026-06-24T16:38:17-04:00
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added `tmcp review-plan` under the existing TMCP CLI group.
- Added strict evidence JSON parsing for either one object or a list of objects.
- Compiled a TMCP packet from the operator objective and target project path.
- Executed `expert_rubric_remediation_v1` through `execute_workflow`.
- Returned JSON with workflow metadata, validations, artifact paths, remediation slices, and implementation handoff data.
- Added CLI regression coverage for artifact writing and malformed evidence JSON.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add failing CLI regression for review-plan artifacts** - `ebf58080` (test)
2. **Task 2: Implement tmcp review-plan parser and execution branch** - `8a1cbd97` (feat)

## Files Created/Modified

- `services/aios_cli.py` - Added review-plan evidence parsing, workflow execution payload, parser wiring, and run_cli branch.
- `tests/test_aios_cli.py` - Added artifact-writing and malformed evidence JSON regressions.

## Decisions Made

- Used `--output-dir` as the workflow artifact root so the target project path is not mutated.
- Returned structured error code `invalid-evidence-json` for malformed evidence input.
- Left command documentation to test behavior and Phase 28 verification artifacts; no separate docs file was required by the plan.

## Deviations from Plan

### Auto-Fixed Acceptance Coverage

**1. Added malformed evidence JSON regression**
- **Found during:** Task 2 acceptance review
- **Issue:** The plan required malformed `--evidence-json` to produce a clear non-success CLI result, but Task 1 only specified the artifact-writing success path.
- **Fix:** Added `test_tmcp_review_plan_rejects_malformed_evidence_json`.
- **Files modified:** `tests/test_aios_cli.py`
- **Verification:** Targeted CLI tests passed.
- **Committed in:** `8a1cbd97`

---

**Total deviations:** 1 auto-fixed acceptance coverage gap.
**Impact on plan:** Narrow test coverage only; no scope expansion beyond the plan acceptance criteria.

## Issues Encountered

None.

## Verification

- `uv run pytest tests/test_aios_cli.py::test_tmcp_review_plan_writes_expert_review_artifacts -q` - failed first because `review-plan` was not a TMCP subcommand, confirming the RED step.
- `uv run pytest tests/test_aios_cli.py::test_tmcp_review_plan_writes_expert_review_artifacts tests/test_aios_cli.py::test_tmcp_review_plan_rejects_malformed_evidence_json -q` - passed, 2 tests.
- `uv run ruff check services/aios_cli.py tests/test_aios_cli.py` - passed.
- `uv run ruff format --check services/aios_cli.py tests/test_aios_cli.py` - passed after applying `uv run ruff format`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plan 28-02 can run focused quality gates and update `.tracker/PROJECT_TRUTH.md` with the new expert rubric remediation workflow state.

## Self-Check: PASSED

- Command belongs to the existing `tmcp` parser group.
- Command invokes `compile_tmcp_packet` and `execute_workflow`.
- Output directory is created through artifact writing and artifact paths are reported.
- The target project path is not mutated in the CLI regression.

---
*Phase: 28-expert-rubric-remediation-cli-and-verification*
*Completed: 2026-06-24*
