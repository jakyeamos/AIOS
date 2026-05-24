---
phase: 08-prompt-skill-workflow-contracts-and-asset-lifecycle
plan: "02"
subsystem: workflow
tags: [workflow-contracts, stage-bindings, validation, registry]
requires:
  - phase: 08-prompt-skill-workflow-contracts-and-asset-lifecycle
    provides: Plan 01 lifecycle metadata and AssetLifecycleState
provides:
  - Stage-level workflow contract binding dataclasses
  - Backward-compatible vNext stage parser
  - Cross-registry workflow binding validation
  - Lifecycle-aware validation discipline for active workflows
affects: [workflow-promotion, planned-workflows, asset-recommendation]
tech-stack:
  added: []
  patterns: [stage contract bindings, registry resolution validation]
key-files:
  created: []
  modified:
    - services/workflow_orchestration.py
    - config/workflows/registry.json
    - tests/test_workflow_orchestration.py
key-decisions:
  - "Active and approved workflows must declare at least one stage-level validation."
  - "Legacy stage rows remain valid through parser defaults."
  - "Registry validation resolves criteria, prompt templates, and standards by ID before workflows can be trusted."
patterns-established:
  - "StageSpec carries required inputs, outputs, validations, approval gates, artifacts, writeback behavior, learning signals, prompts, and standards."
  - "validate_workflow_bindings reports unresolved cross-registry references without mutating registries."
requirements-completed: [WFLO-01, WFLO-02]
duration: active session
completed: 2026-05-24
---

# Phase 8 Plan 02 Summary

**Stage-rich workflow contracts with resolvable prompt, criteria, standards, approval, artifact, writeback, and learning bindings**

## Accomplishments

- Added eight binding dataclasses to `services/workflow_orchestration.py`: `InputBinding`, `OutputBinding`, `ValidationBinding`, `ApprovalGateBinding`, `ArtifactBinding`, `WritebackBindingSpec`, `LearningSignalBinding`, and `PromptBinding`.
- Extended `StageSpec` with required inputs, required outputs, validations, approval gates, expected artifacts, writeback behavior, learning signals, prompt bindings, and standards bindings.
- Replaced inline stage parsing with `_stage_from_row`, preserving legacy `key`/`kind`/`required_skills` rows through defaults.
- Extended `validate_workflow_bindings` to resolve validation criteria, prompt template IDs, and standards IDs against checked-in registries.
- Enforced the Phase 8 rule that `approved` and `active` workflows must carry at least one stage-level validation.
- Enriched `implementation-delivery` and `failure-recovery` with fuller vNext bindings; added minimum resolvable validation bindings to other active workflows so the existing six-workflow registry remains valid.

## Files Created/Modified

- `services/workflow_orchestration.py` (1559 lines) - vNext binding dataclasses, parser helpers, validation cache helpers, and lifecycle-aware binding validation.
- `config/workflows/registry.json` (946 lines) - vNext stage binding fields on existing workflows.
- `tests/test_workflow_orchestration.py` (805 lines) - parsing, default compatibility, cross-registry validation, and lifecycle validation tests.

## Verification

- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_workflow_orchestration.py -q` -> 35 passed.
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_asset_lifecycle.py tests/test_workflow_orchestration.py tests/test_divergent_strategy.py tests/test_architecture_enforcement.py -q` -> 55 passed.
- `uv run ruff check services/workflow_orchestration.py tests/test_workflow_orchestration.py` -> passed.
- `uv run ruff format --check services/workflow_orchestration.py tests/test_workflow_orchestration.py` -> passed.
- `uv run basedpyright services/workflow_orchestration.py` -> 0 errors.
- `uv run vulture services/workflow_orchestration.py --min-confidence 70` -> no findings.
- JSON smoke check for `config/workflows/registry.json` -> passed.

## Deviations from Plan

- The plan described fully populating only `implementation-delivery` and `failure-recovery`, but the new active-workflow validation rule would reject the other active existing workflows. I added minimum valid stage validations to those active workflows so the canonical six-workflow registry still passes.

## Next Phase Readiness

Plan 08-03 can now consume lifecycle-aware workflow and skill records and can rely on stage-level validation bindings being present for active workflows. Plan 08-05 can append candidate workflow contracts using the same vNext stage shape.

---
*Phase: 08-prompt-skill-workflow-contracts-and-asset-lifecycle*
*Completed: 2026-05-24*
