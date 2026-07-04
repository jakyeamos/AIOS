---
phase: 25-make-aios-planning-a-governed-first-class-workflow
plan: "02"
subsystem: workflow-routing
tags: [planning-governance, workflow-registry, task-routing, start-work]
requires:
  - phase: 25-01
    provides: GSD planning detection evidence.
provides:
  - Active `planning-governance` workflow registry contract.
  - Route primitive selection for GSD phase-add objectives.
  - Planning-specific route result metadata and agent recommendation.
affects: [workflow-registry, task-routing, phase-25]
tech-stack:
  added: []
  patterns: [workflow-family-specific route evidence]
key-files:
  created: []
  modified:
    - config/workflows/registry.json
    - config/workflows/skills.json
    - services/workflow_orchestration.py
    - services/task_routing.py
    - tests/test_workflow_orchestration.py
    - tests/test_task_routing.py
key-decisions:
  - "Registered planning-governance as active with validation criteria rather than verification exemption."
  - "Mapped planning-governance to the existing audit_and_implement task family for current backend strategy compatibility."
patterns-established:
  - "Route rankers should consume structured detector evidence before semantic fallback."
requirements-completed: []
duration: 10 min
completed: 2026-06-25
---

# Phase 25 Plan 02: Governed Planning Route Summary

**Active planning-governance workflow selected from GSD planning evidence while weak routes still block**

## Performance

- **Duration:** 10 min
- **Started:** 2026-06-25T03:40:19Z
- **Completed:** 2026-06-25T03:40:19Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Added active `planning-governance` to `config/workflows/registry.json` with parse, generate, validate, and finalize stages.
- Added registry-only planning compiler and validator skill contracts.
- Routed configured GSD planning evidence to `planning-governance` without changing project-resolution blocking or weak/tied workflow safeguards.
- Returned planning-specific agent recommendation text for planning-governance routes.

## Task Commits

Commit deferred because the worktree already contained unrelated dirty changes in overlapping truth files before Phase 25 started. Phase 25 changes and verification evidence are recorded below.

## Files Created/Modified

- `config/workflows/registry.json` - Active planning-governance workflow with validation and evidence contracts.
- `config/workflows/skills.json` - Planning compiler and validator skill contracts.
- `services/workflow_orchestration.py` - Planning detector evidence influences ranking for planning-governance.
- `services/task_routing.py` - Ready route output preserves planning lane semantics.
- `tests/test_workflow_orchestration.py` - Registry and route primitive coverage.
- `tests/test_task_routing.py` - `route_objective()` planning-governance coverage.

## Decisions Made

Planning-governance uses the existing `audit_and_implement` task family for now because that is the only active execution-strategy family in this repo. The workflow semantics and packet text remain planning-oriented.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Verification

- `uv run pytest -q tests/test_workflow_orchestration.py tests/test_task_routing.py` - passed, 72 tests after Plan 25-02.
- Included in final expanded Phase 25 suite - passed, 192 tests.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plan 25-03 can use the selected planning-governance route to add standards and verification sections to start-work packets.

## Self-Check: PASSED

- `planning-governance` loads as active.
- `validate_workflow_bindings()` returns no errors.
- Route tests select planning-governance for GSD phase-add objectives.

---
*Phase: 25-make-aios-planning-a-governed-first-class-workflow*
*Completed: 2026-06-25*
