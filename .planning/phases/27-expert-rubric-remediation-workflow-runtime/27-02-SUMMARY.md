---
phase: 27-expert-rubric-remediation-workflow-runtime
plan: 02
subsystem: workflow
tags: [tmcp, expert-review, workflow-registry, skill-registry, pytest]
requires:
  - phase: 27-expert-rubric-remediation-workflow-runtime
    provides: Phase 27 Plan 01 expert-review runtime dispatch
provides:
  - Active `expert_rubric_remediation_v1` workflow registry contract
  - Active expert-review skill and validation registry entries
  - Registry contract regression for stage order and required validations
affects: [phase-27-routing, phase-28-cli-verification]
tech-stack:
  added: []
  patterns: [active audit-and-plan workflow, validate-stage required validations, approval-gated handoff stage]
key-files:
  created: []
  modified:
    - config/workflows/registry.json
    - config/workflows/skills.json
    - tests/test_workflow_orchestration.py
key-decisions:
  - "Registered the expert workflow as active with `implementation_bearing: false`; it produces a handoff but does not execute implementation."
  - "Placed the implementation handoff behind an always-on workflow-default approval gate."
patterns-established:
  - "First-class workflows must bind required validation keys to validate-stage skill keys."
  - "Expert-review registry entries preserve stage-kind permissions for deterministic runtime dispatch."
requirements-completed: []
duration: 2min
completed: 2026-06-24
---

# Phase 27 Plan 02: Expert Workflow Registry Contract Summary

**Expert rubric remediation is now a first-class active audit-and-plan workflow with registry-backed skills and validations.**

## Performance

- **Duration:** 2 min
- **Started:** 2026-06-24T16:27:14-04:00
- **Completed:** 2026-06-24T16:29:28-04:00
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added `test_expert_review_workflow_registry_contract` for exact workflow family, six-stage ordering, registry validation, and required validation keys.
- Registered `expert_rubric_remediation_v1` as an active `audit_and_plan` workflow.
- Added nine expert skill/validation entries with stage-kind permissions matching runtime dispatch.
- Confirmed the Plan 27-01 runtime execution test now passes through the registered workflow and writes review artifacts.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add registry contract test** - `e391afb3` (test)
2. **Task 2: Add workflow and skill registry entries** - `420e8b96` (feat)

## Files Created/Modified

- `tests/test_workflow_orchestration.py` - Added the expert workflow registry contract regression.
- `config/workflows/registry.json` - Added active expert rubric remediation workflow with six stages and required validations.
- `config/workflows/skills.json` - Added expert generation, finalize, and validate skill specs.

## Decisions Made

- Preserved valid JSON registry structure without changing existing workflow order except appending the new workflow.
- Kept CLI behavior out of Phase 27.
- Made the handoff stage explicit and approval-gated rather than implementation-bearing.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Verification

- `uv run pytest tests/test_workflow_orchestration.py::test_expert_review_workflow_registry_contract -q` - failed first with `KeyError: 'expert_rubric_remediation_v1'`, confirming the RED step.
- `uv run python -c "import json; json.load(open('config/workflows/registry.json')); json.load(open('config/workflows/skills.json')); print('json ok')"` - passed.
- `uv run pytest tests/test_workflow_orchestration.py::test_expert_review_workflow_registry_contract tests/test_workflow_orchestration.py::test_expert_review_workflow_executes_with_artifacts -q` - passed, 2 tests.
- `uv run ruff check tests/test_workflow_orchestration.py` - passed.
- `uv run ruff format --check tests/test_workflow_orchestration.py` - passed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plan 27-03 can now complete routing support for expert review/remediation objectives against the active registry workflow.

## Self-Check: PASSED

- `expert_rubric_remediation_v1` loads from `config/workflows/registry.json`.
- All expert workflow skills load from `config/workflows/skills.json`.
- `validate_workflow_bindings(load_workflow_registry(...), load_skill_registry(...))` returns `[]`.
- `test_expert_review_workflow_executes_with_artifacts` passes after registry wiring.

---
*Phase: 27-expert-rubric-remediation-workflow-runtime*
*Completed: 2026-06-24*
