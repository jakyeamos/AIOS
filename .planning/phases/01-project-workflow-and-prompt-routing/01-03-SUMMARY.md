---
phase: 01-project-workflow-and-prompt-routing
plan: "03"
subsystem: routing
tags:
  - start-work
  - orchestration
  - route-metadata
  - control-plane
requires:
  - phase: "01"
    provides: workflow, prompt-family, and backend recommendation primitives
  - phase: "02"
    provides: project resolution and machine-readable route results
provides:
  - "Route-aware start-work entrypoint"
  - "Persisted route metadata on runs and briefing packets"
  - "CLI/runtime regression coverage for ambiguity blocking and route inspection"
affects:
  - "Phase 2 packet compilation"
  - "operator routing inspectability"
  - "orchestration runtime closeout surfaces"
tech-stack:
  added: []
  patterns:
    - "Route before packet creation"
    - "Persist route identity and route payload on the orchestration spine"
key-files:
  created: []
  modified:
    - "schema.sql"
    - "services/aios_cli.py"
    - "services/invocation_backends.py"
    - "services/task_routing.py"
    - "tests/test_aios_cli.py"
    - "tests/test_orchestration_runtime.py"
key-decisions:
  - "Made route resolution the default serious-work path for `aios start-work` rather than keeping manual workflow/backend defaults."
  - "Persisted the full route payload on runs and packets so operator surfaces do not have to re-run routing logic."
patterns-established:
  - "Blocked route outcomes fail before packet creation."
  - "Route-aware packet traces now carry route identity plus the selected project/workflow/prompt/backend decision."
requirements-completed:
  - ROUT-01
  - ROUT-02
  - ROUT-03
  - ROUT-04
duration: "session slice"
completed: 2026-05-17
---

# Phase 1 Plan 3: Project, Workflow, And Prompt Routing Summary

**`aios start-work` now routes vague serious-work objectives into persisted run and packet records with explicit ambiguity blocking**

## Performance

- **Duration:** session slice
- **Started:** 2026-05-17T04:42:00Z
- **Completed:** 2026-05-17T04:53:00Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments
- Integrated the Phase 1 route layer into `aios start-work` so project/workflow/agent/backend defaults come from routing instead of static CLI defaults.
- Persisted route identity and route metadata on both `orchestration_runs` and `briefing_packets`.
- Added end-to-end regression coverage for route-aware packet creation, route metadata retrieval, and ambiguity blocking before packet creation.

## Task Commits

Production work shipped as one cohesive change set for this plan:

1. **Tasks 1-3: routed CLI integration, route metadata persistence, and end-to-end Phase 1 coverage** - `65b72d65` (`feat`)

## Files Created/Modified

- `services/aios_cli.py` - routes `start-work` through `task_routing`, persists route metadata, and blocks unsafe routes
- `services/invocation_backends.py` - resolves a concrete backend from the selected execution surface
- `services/task_routing.py` - enriches route results with backend-key and agent recommendations for CLI consumption
- `schema.sql` - adds route metadata columns to orchestration runs and briefing packets
- `tests/test_aios_cli.py` - covers routed packet creation, stored route metadata, and ambiguous-route blocking
- `tests/test_orchestration_runtime.py` - verifies the base orchestration schema exposes the new route metadata columns

## Decisions Made

- Used the route layer as the default `start-work` path instead of preserving CLI defaults as the primary behavior.
- Stored the entire route payload on the orchestration spine so later phases can inspect it without recomputing routing.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Test Scope] Moved ambiguity-only projects out of the shared CLI seed fixture**
- **Found during:** Task 3 (end-to-end Phase 1 coverage)
- **Issue:** Expanding the shared CLI seed with Soundscape variants changed unrelated capability-audit expectations
- **Fix:** Restored the shared seed to the single AIOS project and created the extra projects only inside the ambiguity test
- **Files modified:** `tests/test_aios_cli.py`
- **Verification:** `uv run pytest tests/test_aios_cli.py tests/test_orchestration_runtime.py tests/test_task_routing.py tests/test_workflow_orchestration.py tests/test_execution_strategy.py tests/test_project_inventory.py -q`
- **Committed in:** `65b72d65`

---

**Total deviations:** 1 auto-fixed (1 test-isolation issue)
**Impact on plan:** The fix preserved the routed CLI behavior while keeping unrelated control-plane tests stable.

## Issues Encountered

- `schema.sql` had unrelated local personalized-humanizer additions in the working tree, so only the route-metadata hunk was staged for this plan’s commit.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 1 is now complete at the code and CLI entrypoint layer.
- Phase 2 can consume persisted route metadata when compiling task-specific packets and grounded query receipts.

---
*Phase: 01-project-workflow-and-prompt-routing*
*Completed: 2026-05-17*
