---
phase: 28-expert-rubric-remediation-cli-and-verification
plan: 02
subsystem: quality
tags: [tmcp, expert-review, quality-gates, project-truth, basedpyright]
requires:
  - phase: 28-expert-rubric-remediation-cli-and-verification
    provides: `aios tmcp review-plan` CLI implementation and focused CLI regressions
provides:
  - Focused Phase 26-28 quality command ledger
  - Honest `.tracker/PROJECT_TRUTH.md` snapshot for expert rubric remediation
  - Known caveat list for Phase 28 smoke verification
affects: [phase-28-smoke-verification, project-truth, quality-ladder]
tech-stack:
  added: []
  patterns: [focused quality evidence, truth-file caveat preservation, repo-baseline separation]
key-files:
  created:
    - .planning/phases/28-expert-rubric-remediation-cli-and-verification/28-02-SUMMARY.md
  modified:
    - .tracker/PROJECT_TRUTH.md
key-decisions:
  - "Recorded focused expert workflow lint/format/new-test/Vulture passes without claiming full repo quality health."
  - "Left existing broader CLI pytest and BasedPyright failures visible as blockers instead of broadening this plan into unrelated remediation."
patterns-established:
  - "Feature truth updates should distinguish focused touched-slice evidence from full-repo baseline health."
requirements-completed: []
duration: 3min
completed: 2026-06-24
---

# Phase 28 Plan 02: Focused Quality Gates And Project Truth Closeout Summary

**Expert workflow quality evidence is recorded, and project truth now reflects both the landed review-plan feature and the remaining baseline debt.**

## Performance

- **Duration:** 3 min
- **Started:** 2026-06-24T16:39:07-04:00
- **Completed:** 2026-06-24T16:43:53-04:00
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Ran the focused Phase 26-28 quality command set from `28-VALIDATION.md`.
- Updated `.tracker/PROJECT_TRUTH.md` to say `expert_rubric_remediation_v1` is implemented through service artifacts, runtime dispatch, registry/routing, and `aios tmcp review-plan`.
- Preserved caveats for existing broader CLI test failures and BasedPyright baseline failures.
- Kept the next step pointed at Phase 28 smoke verification.

## Task Commits

Each task was committed atomically:

1. **Task 1: Run focused quality gates and record results** - command-only evidence, no file commit
2. **Task 2: Update project truth from actual quality evidence** - `d8b63dd6` (docs)

## Files Created/Modified

- `.tracker/PROJECT_TRUTH.md` - Updated current state, quality status, blockers, next step, open problems, and focused expert workflow check ledger.

## Decisions Made

- Treated the broader `tests/test_aios_cli.py` failures as existing baseline debt because the new expert workflow regressions pass and the failures are in learning/contracts/skills-harvest expectations.
- Marked focused lint and dead-code status as passing while keeping tests/types as failing because the actual focused command set still found existing failures.
- Did not auto-fix unrelated BasedPyright complexity/type-helper issues inside the quality closeout plan.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- `uv run pytest tests/test_aios_cli.py tests/test_workflow_orchestration.py tests/test_expert_rubric_remediation.py -q` failed with 8 existing `tests/test_aios_cli.py` failures:
  - `test_learning_analyze_cli_dry_run`
  - `test_learning_analyze_cli_per_project`
  - `test_learning_propose_cli_writes_writebacks`
  - `test_contracts_audit_includes_operator_surface_row`
  - `test_contracts_audit_includes_next_action_row`
  - `test_contracts_audit_includes_daily_flow_row`
  - `test_workflow_learning_payload_includes_recurring_patterns_and_proposals`
  - `test_skills_harvest_cli_dry_run`
- `uv run basedpyright services/aios_cli.py services/workflow_orchestration.py services/expert_rubric_remediation.py tests/test_aios_cli.py tests/test_workflow_orchestration.py tests/test_expert_rubric_remediation.py` failed with existing `run_cli` complexity, an existing `_dx_pack_payload` test helper type mismatch, and pytest import resolution warnings.

## Command Evidence

- `uv run pytest tests/test_aios_cli.py tests/test_workflow_orchestration.py tests/test_expert_rubric_remediation.py -q` - failed, 8 failed and 124 passed; failures are existing broader CLI-slice debt, while new expert workflow tests pass.
- `uv run ruff check services/aios_cli.py tests/test_aios_cli.py services/workflow_orchestration.py tests/test_workflow_orchestration.py services/expert_rubric_remediation.py tests/test_expert_rubric_remediation.py` - passed.
- `uv run ruff format --check services/aios_cli.py tests/test_aios_cli.py services/workflow_orchestration.py tests/test_workflow_orchestration.py services/expert_rubric_remediation.py tests/test_expert_rubric_remediation.py` - passed.
- `uv run basedpyright services/aios_cli.py services/workflow_orchestration.py services/expert_rubric_remediation.py tests/test_aios_cli.py tests/test_workflow_orchestration.py tests/test_expert_rubric_remediation.py` - failed with 2 errors and 2 warnings.
- `uv run vulture . --min-confidence 70` - passed.
- `git diff --check .tracker/PROJECT_TRUTH.md` - passed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plan 28-03 can run the operator-facing `aios tmcp review-plan` smoke command and write the final Phase 28 verification ledger. The handoff must carry forward the known broader CLI pytest and BasedPyright caveats.

## Self-Check: PASSED

- Truth file reflects actual command evidence.
- Focused pass results are not presented as full repo health.
- Existing caveats are visible in both blockers and Quality Ladder Notes.
- The next action is concrete and matches Plan 28-03.

---
*Phase: 28-expert-rubric-remediation-cli-and-verification*
*Completed: 2026-06-24*
