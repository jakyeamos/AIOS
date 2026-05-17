---
phase: 01-project-workflow-and-prompt-routing
plan: "02"
subsystem: routing
tags:
  - project-routing
  - workflow-routing
  - prompt-library
  - backend-selection
requires:
  - phase: "01"
    provides: workflow, prompt-family, and backend recommendation primitives
provides:
  - "Inventory-backed project candidate ranking"
  - "Machine-readable route-result contract with blocked and ready outcomes"
  - "Route-level regression coverage for exact, ambiguous, unsupported, and serious-work workflow outcomes"
affects:
  - "Phase 1 CLI start-work integration"
  - "Phase 2 packet compilation"
  - "operator routing inspectability"
tech-stack:
  added: []
  patterns:
    - "Project outcome classification before workflow routing"
    - "Blocked route results for ambiguous or unsupported project resolution"
key-files:
  created:
    - "services/task_routing.py"
    - "tests/test_task_routing.py"
  modified:
    - "services/project_inventory.py"
    - "tests/test_project_inventory.py"
key-decisions:
  - "Blocked workflow routing when project resolution is ambiguous or unsupported instead of guessing."
  - "Built the route result on top of existing workflow and execution-strategy primitives rather than creating a second orchestration path."
patterns-established:
  - "Project routing now emits explicit outcomes with candidate rationale."
  - "Workflow, prompt-family, and backend recommendations can be consumed through one route-result envelope."
requirements-completed:
  - ROUT-01
  - ROUT-02
  - ROUT-03
  - ROUT-04
duration: "session slice"
completed: 2026-05-17
---

# Phase 1 Plan 2: Project, Workflow, And Prompt Routing Summary

**Inventory-backed project resolution now produces blocked-or-ready route results with workflow, prompt-family, and backend recommendations**

## Performance

- **Duration:** session slice
- **Started:** 2026-05-17T04:31:00Z
- **Completed:** 2026-05-17T04:41:00Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- Added inventory-backed project ranking that works against both sparse and full `projects` schemas.
- Added a machine-readable route-result layer that blocks on ambiguous or unsupported project selection before workflow routing proceeds.
- Locked the route contract with focused tests for exact-match, ambiguity, unsupported, implementation, recovery, audit, and prompt-fallback behavior.

## Task Commits

Production work shipped as one cohesive change set for this plan:

1. **Tasks 1-3: project resolution, route-result composition, and route-level regression coverage** - `d37b1804` (`feat`)

## Files Created/Modified

- `services/project_inventory.py` - lists registered projects and ranks project candidates from objective/cwd evidence
- `services/task_routing.py` - defines project outcomes and the route-result contract
- `tests/test_project_inventory.py` - covers sparse-schema handling and candidate ranking
- `tests/test_task_routing.py` - covers exact, ambiguous, unsupported, and serious-work route behavior

## Decisions Made

- Treated ambiguous or weak project matches as a routing blocker instead of allowing silent fallback.
- Reused the Plan 01 workflow/prompt/backend recommendation primitives inside the new route-result envelope.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Test Fixture] Reworked the ambiguity fixture so it actually exercised ambiguous project resolution**
- **Found during:** Task 3 (route-level regression fixtures and edge-case coverage)
- **Issue:** The original fixture included a plain `Soundscape` project, which made the objective an honest exact-name match instead of an ambiguity case
- **Fix:** Switched the competing fixtures to `Soundscape App` and `Soundscape Web`
- **Files modified:** `tests/test_task_routing.py`
- **Verification:** `uv run pytest tests/test_project_inventory.py tests/test_task_routing.py tests/test_workflow_orchestration.py tests/test_execution_strategy.py -q`
- **Committed in:** `d37b1804`

---

**Total deviations:** 1 auto-fixed (1 fixture-correctness issue)
**Impact on plan:** The fix tightened route coverage without expanding scope.

## Issues Encountered

- `Connection.executescript()` cannot accept bound parameters, so the project-inventory fixture had to be split into schema creation plus `executemany`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 03 can now wire the route-result contract into `aios start-work` and persist routed metadata on the orchestration spine.
- The remaining gap in Phase 1 is product-path adoption, not routing logic definition.

---
*Phase: 01-project-workflow-and-prompt-routing*
*Completed: 2026-05-17*
