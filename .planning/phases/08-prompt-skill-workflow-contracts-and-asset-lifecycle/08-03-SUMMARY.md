---
phase: 08-prompt-skill-workflow-contracts-and-asset-lifecycle
plan: "03"
subsystem: recommendation
tags: [asset-recommendation, agentize, routing, evidence]
requires:
  - phase: 08-prompt-skill-workflow-contracts-and-asset-lifecycle
    provides: Plans 01-02 lifecycle metadata and workflow contracts
provides:
  - Asset usage evidence projection
  - Evidence-backed asset recommendation
  - Agentize skill recommendation integration
  - Route result skill/workflow recommendations
affects: [workflow-promotion, operator-surfaces, learning-loop]
tech-stack:
  added: []
  patterns: [read-time evidence projection, recommender-first fallback]
key-files:
  created:
    - services/asset_recommendation.py
    - tests/test_asset_recommendation.py
  modified:
    - services/agentize.py
    - services/task_routing.py
    - tests/test_agentize.py
    - tests/test_task_routing.py
key-decisions:
  - "Read registry assets directly because runtime lifecycle rows do not yet exist for every checked-in asset."
  - "Keep standards and criteria recommendation on the existing success-criteria resolver for this plan."
  - "Record recommendation_source in packet metadata instead of adding a new packet field."
patterns-established:
  - "Recommendations cite raw success_rate, sample_size, and top workflow evidence."
  - "Agentize uses recommender output for skills when available and falls back to existing heuristics when empty."
requirements-completed: [ASSET-03, ASSET-04]
duration: active session
completed: 2026-05-24
---

# Phase 8 Plan 03 Summary

**Evidence-backed prompt, skill, and workflow recommendations feeding agentized packets and project routing**

## Accomplishments

- Added `services/asset_recommendation.py` with `AssetUsageEvidence`, `AssetRecommendation`, `build_asset_usage_evidence`, `recommend_assets_for_packet`, and `recommend_skills_for_workflow_stage`.
- Aggregated existing evidence from `prompts_used`, `workflow_execution_reports`, `workflow_skill_experiments`, and `success_criteria_findings`, tolerating absent tables for in-memory and partial schemas.
- Ranked prompt, skill, and workflow assets by lifecycle state, success rate, sample size, and key stability; draft and deprecated assets are excluded.
- Added exploration-mode candidate inclusion below `sample_size < 10`.
- Wired `agentize_request` to use skill recommendations when available and to record `recommendation_source` in `experiment_metadata`.
- Extended `RouteResult` with `skill_recommendations` and `workflow_alternatives`, and enriched prompt rationale with usage evidence.

## Files Created/Modified

- `services/asset_recommendation.py` (474 lines) - read-time asset evidence and recommendation service.
- `tests/test_asset_recommendation.py` (296 lines) - evidence aggregation, ranking, filtering, exploration, and rationale tests.
- `services/agentize.py` (765 lines) - recommender-first skill selection with fallback metadata.
- `services/task_routing.py` (270 lines) - route-level skill/workflow recommendations and prompt evidence enrichment.
- `tests/test_agentize.py` (379 lines) - recommender/fallback and recommendation-source persistence tests.
- `tests/test_task_routing.py` (138 lines) - route recommendation payload coverage.

## Verification

- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_asset_recommendation.py tests/test_agentize.py tests/test_task_routing.py -q` -> 32 passed.
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_asset_lifecycle.py tests/test_workflow_orchestration.py tests/test_divergent_strategy.py tests/test_architecture_enforcement.py tests/test_asset_recommendation.py tests/test_agentize.py tests/test_task_routing.py -q` -> 87 passed.
- `uv run ruff check services/asset_recommendation.py services/agentize.py services/task_routing.py tests/test_asset_recommendation.py tests/test_agentize.py tests/test_task_routing.py` -> passed.
- `uv run ruff format --check ...` for touched Python files -> passed.
- `uv run basedpyright services/asset_recommendation.py services/agentize.py services/task_routing.py` -> 0 errors.
- `uv run vulture services/asset_recommendation.py services/agentize.py services/task_routing.py --min-confidence 70` -> no findings.

## Deviations from Plan

- Standards and success-criteria recommendations remain with the existing standards resolver in `services/success_criteria.py`; Plan 03 now records recommender/fallback source for skills and leaves standard/criterion asset lifecycle expansion for a later, explicit registry extension.
- The evidence projection reads registry assets directly instead of requiring a lifecycle history row first. This matches the current repo state where checked-in assets have lifecycle metadata but most do not yet have transition rows.
- `prompts_used` does not currently have a template-id column, so prompt evidence uses classification or prompt-text matching until a later schema extension adds explicit prompt asset linkage.

## Next Phase Readiness

Plan 08-04 can consume `AssetUsageEvidence` and `AssetRecommendation` to compare workflow effectiveness and propose governed promotions from the same raw evidence vocabulary.

---
*Phase: 08-prompt-skill-workflow-contracts-and-asset-lifecycle*
*Completed: 2026-05-24*
