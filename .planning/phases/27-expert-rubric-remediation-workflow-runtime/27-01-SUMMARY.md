---
phase: 27-expert-rubric-remediation-workflow-runtime
plan: 01
subsystem: workflow
tags: [tmcp, expert-review, workflow-runtime, artifact-dispatch, pytest]
requires:
  - phase: 26-expert-rubric-remediation-core-artifacts
    provides: Expert rubric remediation service builders and validators
provides:
  - Workflow execution context fields for review evidence and selected remediation slice
  - Expert-review skill dispatch branches for rubric, audit, remediation, handoff, and validations
  - Expert artifact keys in workflow execution reports
affects: [phase-27-registry-contracts, phase-28-cli-verification]
tech-stack:
  added: []
  patterns: [deterministic workflow skill dispatch, review artifact path exposure, explicit missing-input failures]
key-files:
  created: []
  modified:
    - services/workflow_orchestration.py
    - tests/test_workflow_orchestration.py
key-decisions:
  - "Kept registry entries out of Plan 27-01 so runtime dispatch can land independently from first-class workflow registration."
  - "Runtime writes expert review artifacts only under `{repo_path}/.aios/reviews/{run_id}` when the implementation handoff skill runs."
patterns-established:
  - "Expert validate-stage skills return validation dictionaries with keys matching workflow required_validations."
  - "Expert runtime report artifacts expose both in-memory objects and the generated artifact path map."
requirements-completed: []
duration: 2min
completed: 2026-06-24
---

# Phase 27 Plan 01: Workflow Runtime Expert Dispatch Summary

**Workflow execution can now carry expert-review inputs, dispatch expert artifact builders, and expose expert review artifacts in execution reports.**

## Performance

- **Duration:** 2 min
- **Started:** 2026-06-24T16:23:25-04:00
- **Completed:** 2026-06-24T16:24:59-04:00
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Extended `WorkflowExecutionContext` with `evidence_items` and `selected_slice_id`.
- Seeded workflow `run_state` with `review_evidence_items` and `selected_slice_id`.
- Added expert-review dispatch for TMCP expertise compilation, rubric synthesis, evidence audit, remediation planning, implementation handoff artifact writing, and required validation skills.
- Added expert-review artifact keys to `report["artifacts"]`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add runtime execution test and context fields** - `884cbee5` (test)
2. **Task 2: Dispatch expert workflow skills and expose report artifacts** - `cd6ddd23` (feat)

## Files Created/Modified

- `services/workflow_orchestration.py` - Added expert runtime inputs, dispatch branches, validation branches, artifact writing, and report artifact exposure.
- `tests/test_workflow_orchestration.py` - Added expert workflow runtime regression that will pass after Plan 27-02 registers the workflow and skills.

## Decisions Made

- Followed the phase boundary: no workflow registry, skill registry, or route scoring changes in this plan.
- Preserved explicit failure for missing TMCP packet via `ValueError("tmcp_expertise_compiler requires context.tmcp_packet")`.
- Used `context.run_id or "expert-review-preview"` consistently for generated review artifact paths.

## Deviations from Plan

### Expected Cross-Plan Failure

**1. Focused execution test remains blocked on registry registration until Plan 27-02**
- **Found during:** Task 1 and Task 2 verification
- **Issue:** `uv run pytest tests/test_workflow_orchestration.py::test_expert_review_workflow_executes_with_artifacts -q` fails with `Unknown workflow key: expert_rubric_remediation_v1`.
- **Reason:** Plan 27-01 intentionally adds runtime dispatch only; Plan 27-02 owns workflow and skill registry entries.
- **Verification:** The failure occurs after context construction, proving `evidence_items` and `selected_slice_id` are accepted.
- **Committed in:** `884cbee5` and `cd6ddd23`

---

**Total deviations:** 1 expected cross-plan failure.
**Impact on plan:** No scope creep; the failing test is the handoff signal for Plan 27-02.

## Issues Encountered

None beyond the planned registry boundary.

## Verification

- `uv run pytest tests/test_workflow_orchestration.py::test_expert_review_workflow_executes_with_artifacts -q` - expected failure: `Unknown workflow key: expert_rubric_remediation_v1`.
- `uv run ruff check services/workflow_orchestration.py tests/test_workflow_orchestration.py` - passed.
- `uv run ruff format --check services/workflow_orchestration.py tests/test_workflow_orchestration.py` - passed after applying `uv run ruff format`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plan 27-02 can now register `expert_rubric_remediation_v1` and its skills. The existing focused runtime test should move from `Unknown workflow key` to completed execution once registry bindings are present.

## Self-Check: PASSED

- `WorkflowExecutionContext` includes `evidence_items` and `selected_slice_id`.
- `execute_workflow` seeds `review_evidence_items` and `selected_slice_id`.
- Expert runtime dispatch uses Phase 26 service builders and validators.
- Registry and route behavior remain untouched for follow-up plans.

---
*Phase: 27-expert-rubric-remediation-workflow-runtime*
*Completed: 2026-06-24*
