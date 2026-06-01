---
phase: 09-continuous-learning-and-conservative-optimization
plan: "06"
subsystem: governed-promotion-wiring
tags: [learning, governance, divergent-strategy, workflow-experiments, promotion-lifecycle]
requires:
  - phase: 08-prompt-skill-workflow-contracts-and-asset-lifecycle
    provides: workflow promotion proposal surface
  - phase: 09-continuous-learning-and-conservative-optimization
    provides: LEARN-03 conservative promotion discipline
provides:
  - Divergent strategy winners routed through governed asset promotion proposals
  - Workflow-skill experiment winners routed through governed asset promotion proposals
  - Missing Phase 8 asset-promotion helper required by Phase 9 wiring
affects: [divergent-strategy, workflow-experiments, workflow-promotion, approval-gated-writebacks]
tech-stack:
  added: []
  patterns:
    - propose-then-approve promotion wiring
    - fallback warning for partially shipped Phase 8 promotion surfaces
key-files:
  created:
    - .planning/phases/09-continuous-learning-and-conservative-optimization/09-06-SUMMARY.md
  modified:
    - services/workflow_promotion.py
    - services/divergent_strategy.py
    - services/workflow_experiments.py
    - tests/test_divergent_strategy.py
    - tests/test_workflow_experiments.py
key-decisions:
  - "Added `propose_asset_promotion` to `services/workflow_promotion.py` because the Phase 8 module existed without the public asset proposal function Phase 9 depends on."
  - "Divergent strategy now emits an approval-required improvement writeback and a `promotion_lifecycle_items` row with status `proposed`; the target state remains `candidate` in metadata until approval."
  - "Workflow-skill experiments keep their existing `promotion_ready` outcome semantics while additionally emitting governed skill promotion proposals for successful winners."
  - "Fallback paths preserve legacy direct candidate/status behavior and emit stderr warnings when the Phase 8 proposal surface is unavailable."
patterns-established:
  - "Promotion-producing learning paths emit reviewable writebacks before lifecycle activation."
  - "Runtime recommendation and experiment scoring paths remain unchanged; only post-result promotion governance tightened."
requirements-completed: [LEARN-03]
duration: 18min
completed: 2026-06-01
---

# Phase 9 Plan 06 Summary

**Governed promotion wiring for divergent and experiment winners**

## Accomplishments

- Added `propose_asset_promotion` to `services/workflow_promotion.py` so prompt and skill winners can use the same proposal/writeback contract as workflow promotions.
- Replaced the divergent strategy direct lifecycle write with `_propose_via_workflow_promotion_if_available`, routing the divergent strategy skill winner to `to_state="candidate"` through an approval-required writeback and `proposed` lifecycle row.
- Added the same proposal helper to workflow experiments and invoked it when a workflow-skill experiment reaches `promotion_ready`.
- Preserved defensive fallback behavior: when the Phase 8 proposal surface is unavailable, divergent strategy falls back to the legacy candidate lifecycle row and workflow experiments fall back to the existing `promotion_ready` status-only behavior, both with explicit stderr warnings.
- Updated tests to assert live proposal rows, fallback warnings, unchanged runtime persistence, and prompt/skill asset-kind routing.

## Files Created/Modified

- `services/workflow_promotion.py` - Added `propose_asset_promotion` and exported it.
- `services/divergent_strategy.py` - Added guarded proposal helper and routed the divergent winner through governed asset promotion.
- `services/workflow_experiments.py` - Added guarded proposal helper and promotion proposal emission for successful workflow-skill experiments.
- `tests/test_divergent_strategy.py` - Added live-path, fallback, runtime-regression, and asset-kind routing tests.
- `tests/test_workflow_experiments.py` - Added live-path, fallback, runtime-regression, and full experiment proposal assertions.

## Pitfall 6

The lifecycle row now stays reviewable instead of directly representing the final target state. Live-path rows use `status="proposed"` and store `target_state="candidate"` in metadata; fallback rows preserve the legacy `candidate` write when the Phase 8 proposal surface is unavailable.

## Verification

- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_divergent_strategy.py tests/test_workflow_experiments.py tests/test_workflow_promotion.py tests/test_architecture_enforcement.py -x -q` -> 27 passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check services/workflow_promotion.py services/divergent_strategy.py services/workflow_experiments.py tests/test_divergent_strategy.py tests/test_workflow_experiments.py tests/test_workflow_promotion.py` -> passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format --check services/workflow_promotion.py services/divergent_strategy.py services/workflow_experiments.py tests/test_divergent_strategy.py tests/test_workflow_experiments.py tests/test_workflow_promotion.py` -> passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run basedpyright services/workflow_promotion.py services/divergent_strategy.py services/workflow_experiments.py` -> passed

## Next Phase Readiness

Phase 9 has all six plan summaries present. The next step is Phase 9 closeout verification across the learning taxonomy, analysis, optimizer, impact, surfaces, and governed promotion wiring.

---
*Phase: 09-continuous-learning-and-conservative-optimization*
*Completed: 2026-06-01*
