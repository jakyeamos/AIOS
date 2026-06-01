---
phase: 08-prompt-skill-workflow-contracts-and-asset-lifecycle
plan: "05"
subsystem: workflow-contracts
tags: [workflow-registry, skill-registry, prompt-validation, lifecycle]
requires:
  - phase: 08-prompt-skill-workflow-contracts-and-asset-lifecycle
    provides: "Plan 01 lifecycle metadata fields for prompts, skills, and workflows"
  - phase: 08-prompt-skill-workflow-contracts-and-asset-lifecycle
    provides: "Plan 02 vNext workflow stage binding schema"
provides:
  - "Four candidate workflow contracts: audit-only, audit-and-implement, standards-backfill, security-review"
  - "Four draft executor skill stubs for planned workflow contracts"
  - "Prompt validator enforcement for lifecycle_state, applicability, and last_evaluated_at"
  - "Health workflow recommendations that resolve planned registry keys"
affects: [phase-08, workflow-registry, skill-registry, prompt-registry, prompt-validation]
tech-stack:
  added: []
  patterns:
    - "Candidate workflow contracts can carry full vNext bindings before their executor skills are promoted active."
    - "Prompt registry generation preserves route-facing metadata needed by workflow recommendation."
key-files:
  created:
    - tests/test_planned_workflows.py
  modified:
    - config/workflows/registry.json
    - config/workflows/skills.json
    - bin/validate-prompts.py
    - prompts/registry.json
    - tests/fixtures/prompts/valid_template.md
    - tests/fixtures/prompts/duplicate_id.md
    - tests/test_validate_prompts.py
    - tests/test_workflow_orchestration.py
    - services/workflow_orchestration.py
key-decisions:
  - "New workflow contracts are candidate, not active, while their executor skills remain draft stubs."
  - "Prompt validation now emits route-facing registry fields so validation does not break prompt recommendation."
  - "Active workflows receive a small ranking boost so new candidate workflows do not displace current defaults."
patterns-established:
  - "Planned workflow contracts bind prompts, standards, approvals, expected artifacts, learning signals, and validation criteria at the stage level."
  - "Lifecycle validation uses the five-state literal: draft, candidate, approved, active, deprecated."
requirements-completed: [WFLO-01, WFLO-02]
duration: resumed
completed: 2026-06-01
---

# Phase 8 Plan 05 Summary

**Candidate workflow contracts and strict prompt lifecycle validation for the next governed workflow set**

## Performance

- **Duration:** resumed in current session
- **Started:** 2026-06-01T00:00:00Z
- **Completed:** 2026-06-01T00:00:00Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments

- Registered `audit-only`, `audit-and-implement`, `standards-backfill`, and `security-review` as lifecycle `candidate` workflows with vNext stage bindings.
- Added draft executor stubs for the four planned workflows so `validate_workflow_bindings` resolves the full ten-workflow registry.
- Extended `bin/validate-prompts.py` to require `lifecycle_state`, `applicability`, and `last_evaluated_at`, and to reject lifecycle states outside the five-state literal.
- Preserved prompt recommendation compatibility by emitting `prompt_family`, `route_status`, and `applicable_workflow_families` in generated `prompts/registry.json`.
- Updated health recommendation keys to registry-safe `standards-backfill` and `security-review`.

## Task Commits

Task-level commits were collapsed into one Plan 05 implementation commit for this resumed execution.

## Files Created/Modified

- `config/workflows/registry.json` - Four candidate planned workflow contracts with stage-rich vNext bindings.
- `config/workflows/skills.json` - Four draft executor stubs.
- `bin/validate-prompts.py` - Lifecycle metadata requirement and five-state validation.
- `prompts/registry.json` - Regenerated prompt registry retaining route-facing metadata.
- `services/workflow_orchestration.py` - Planned workflow registry-key recommendations and active-workflow route ranking stability.
- `tests/test_planned_workflows.py` - Planned workflow load, validation, stub resolution, lifecycle, and health recommendation tests.
- `tests/test_validate_prompts.py` - Prompt lifecycle validation tests.
- `tests/test_workflow_orchestration.py` - Updated expectations for ten workflows and registry-safe recommendation keys.
- `tests/fixtures/prompts/valid_template.md` - Lifecycle fixture metadata.
- `tests/fixtures/prompts/duplicate_id.md` - Lifecycle fixture metadata.

## Decisions Made

- Candidate workflows are discoverable and validated, but active defaults remain preferred for route selection until promotion evidence justifies changing defaults.
- The validator owns deterministic prompt-family defaults for the canonical five templates so generated registry output remains usable by routing.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Compatibility] Preserve prompt routing metadata during validation**
- **Found during:** Task 2 verification
- **Issue:** `validate-prompts.py` generated registry rows without `prompt_family`, which caused `recommend_prompt_family` to return no match after the smoke command rewrote `prompts/registry.json`.
- **Fix:** Added deterministic `prompt_family`, `route_status`, and `applicable_workflow_families` output fields.
- **Files modified:** `bin/validate-prompts.py`, `prompts/registry.json`
- **Verification:** `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_planned_workflows.py tests/test_validate_prompts.py tests/test_workflow_orchestration.py -q`
- **Committed in:** Plan closeout commit

**2. [Rule 1 - Compatibility] Keep active workflows ahead of candidate workflows for default routing**
- **Found during:** Task 1 verification
- **Issue:** New candidate `audit-and-implement` outranked active `implementation-delivery` for an existing implementation objective.
- **Fix:** Added a small active-lifecycle ranking boost in `rank_workflow_candidates`.
- **Files modified:** `services/workflow_orchestration.py`
- **Verification:** Existing orchestration tests pass.
- **Committed in:** Plan closeout commit

---

**Total deviations:** 2 auto-fixed (Rule 1)
**Impact on plan:** Both fixes preserve existing runtime behavior while enabling the new planned contracts and lifecycle validation gates.

## Issues Encountered

- `uv run python bin/validate-prompts.py --prompts-root prompts` initially failed under sandbox cache permissions when `UV_CACHE_DIR` was not set. Re-ran successfully with `UV_CACHE_DIR=/tmp/uv-cache`.

## User Setup Required

None - no external service configuration required.

## Verification

- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_planned_workflows.py tests/test_validate_prompts.py tests/test_workflow_orchestration.py -q` — 58 passed.
- `UV_CACHE_DIR=/tmp/uv-cache uv run python bin/validate-prompts.py --prompts-root prompts` — validated 5 templates.
- JSON assertion commands for planned workflow keys, candidate states, stub skill keys, and draft states — passed.
- `uv run ruff check services/workflow_orchestration.py bin/validate-prompts.py tests/test_planned_workflows.py tests/test_validate_prompts.py tests/test_workflow_orchestration.py` — passed.
- `uv run ruff format --check services/workflow_orchestration.py bin/validate-prompts.py tests/test_planned_workflows.py tests/test_validate_prompts.py tests/test_workflow_orchestration.py` — passed.
- `uv run basedpyright services/workflow_orchestration.py bin/validate-prompts.py` — passed.

## Next Phase Readiness

Phase 8 now has summaries for all five plans. Phase verification can check WFLO-01 through WFLO-04 and ASSET-01 through ASSET-04 against the lifecycle, recommendation, workflow contract, validation, and promotion surfaces.

---
*Phase: 08-prompt-skill-workflow-contracts-and-asset-lifecycle*
*Completed: 2026-06-01*
