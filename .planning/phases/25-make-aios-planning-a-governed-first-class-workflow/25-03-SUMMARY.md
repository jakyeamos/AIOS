---
phase: 25-make-aios-planning-a-governed-first-class-workflow
plan: "03"
subsystem: planning-packets
tags: [planning-lenses, start-work, packet-contract, verification-handoff]
requires:
  - phase: 25-02
    provides: Active planning-governance route.
provides:
  - Planning-governance lenses for standards surfacing and verification handoff.
  - Execution-symmetric planning contract sections.
  - Start-work packet sections for planning quality, artifacts, standards, and verification handoff.
affects: [aios-cli, execution-symmetric-planning, planning-lenses, phase-25]
tech-stack:
  added: []
  patterns: [planning-specific packet sections]
key-files:
  created: []
  modified:
    - config/planning/planning-lenses.json
    - services/aios_cli.py
    - services/execution_symmetric_planner.py
    - tests/test_aios_cli.py
    - tests/test_execution_symmetric_planner.py
    - tests/test_planning_lenses.py
key-decisions:
  - "Planning-governance packets now tell agents to create planning artifacts before implementation."
  - "Packet standards use selected planning lenses rather than broad context dumps."
patterns-established:
  - "Planning routes append explicit packet sections instead of relying on generic implementation handoff copy."
requirements-completed: []
duration: 14 min
completed: 2026-06-25
---

# Phase 25 Plan 03: Planning Packet Contract Summary

**Planning-governance packets surface standards, required artifacts, evidence expectations, and verification handoff before execution**

## Performance

- **Duration:** 14 min
- **Started:** 2026-06-25T03:40:19Z
- **Completed:** 2026-06-25T03:40:19Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Added `standards-surfacing` and `verification-handoff` lenses and mapped them to `planning-governance:plan`.
- Added execution-symmetric planning sections: `planning_quality_contract`, `acceptance_criteria_contract`, `evidence_contract`, and `verification_handoff`.
- Added `Planning Quality Contract`, `Required Planning Artifacts`, `Standards Before Execution`, and `Verification Handoff` sections to planning-governance start-work packets.
- Made the next recommended action planning-specific for planning-governance routes.

## Task Commits

Commit deferred because the worktree already contained unrelated dirty changes in overlapping truth files before Phase 25 started. Phase 25 changes and verification evidence are recorded below.

## Files Created/Modified

- `config/planning/planning-lenses.json` - Planning-governance workflow-phase mapping and new lenses.
- `services/execution_symmetric_planner.py` - GSD-ready plans expose planning contract sections.
- `services/aios_cli.py` - Start-work packets include planning-specific contract sections and next action.
- `tests/test_planning_lenses.py` - Lens selection coverage.
- `tests/test_execution_symmetric_planner.py` - Planning contract section coverage.
- `tests/test_aios_cli.py` - Persisted packet and route JSON coverage.

## Decisions Made

The packet sections are appended only when the selected workflow is `planning-governance`, preserving implementation-delivery packet shape for normal implementation work.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Verification

- `uv run pytest -q tests/test_planning_lenses.py tests/test_execution_symmetric_planner.py tests/test_aios_cli.py tests/test_task_routing.py` - passed, 107 tests after Plan 25-03.
- Included in final expanded Phase 25 suite - passed, 192 tests.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plan 25-04 can prove the Codex route and shadow helpers now produce durable planning and known-command route evidence.

## Self-Check: PASSED

- Packet section titles appear in CLI packet markdown.
- Route JSON preserves `planning-governance`.
- Next recommended action starts with planning artifact creation.

---
*Phase: 25-make-aios-planning-a-governed-first-class-workflow*
*Completed: 2026-06-25*
