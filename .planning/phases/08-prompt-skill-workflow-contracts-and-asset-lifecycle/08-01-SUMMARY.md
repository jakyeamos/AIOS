---
phase: 08-prompt-skill-workflow-contracts-and-asset-lifecycle
plan: "01"
subsystem: governance
tags: [asset-lifecycle, workflow-registry, prompts, sqlite, writebacks]
requires:
  - phase: 07-delta-scoring-and-health-backfill
    provides: standards health and workflow recommendation surfaces
provides:
  - Canonical prompt/skill/workflow lifecycle vocabulary
  - Cross-asset lifecycle transition helper
  - Legacy lifecycle status migration
  - Registry lifecycle metadata backfill
affects: [workflow-contracts, asset-recommendation, workflow-promotion]
tech-stack:
  added: []
  patterns: [registry-backed asset state, governed active promotion]
key-files:
  created:
    - services/asset_lifecycle.py
    - bin/migrate-lifecycle-statuses.py
    - tests/test_asset_lifecycle.py
  modified:
    - services/workflow_orchestration.py
    - services/divergent_strategy.py
    - config/workflows/registry.json
    - config/workflows/skills.json
    - prompts/registry.json
    - prompts/*.md
key-decisions:
  - "Use promotion_lifecycle_items as the shared lifecycle history table."
  - "Mirror the Phase 5 writeback approval policy in services/ to preserve the services -> bin boundary."
  - "Keep prompt route_status as a one-cycle alias while lifecycle_state becomes authoritative."
patterns-established:
  - "Active asset promotion writes an improvement_writebacks row before the lifecycle row."
  - "Registry loaders accept old and new lifecycle shapes with lifecycle_state winning over legacy aliases."
requirements-completed: [ASSET-01, ASSET-02]
duration: active session
completed: 2026-05-24
---

# Phase 8 Plan 01 Summary

**Canonical asset lifecycle primitives for prompts, skills, and workflows with governed active promotion and registry metadata backfill**

## Accomplishments

- Added `services/asset_lifecycle.py` with `AssetKind`, `AssetLifecycleState`, `AssetRecord`, `LifecycleTransition`, `LIFECYCLE_TRANSITIONS`, `promote_asset`, `list_assets`, schema helpers, and the Phase-5-compatible writeback approval shim.
- Backfilled lifecycle metadata into `prompts/registry.json`, prompt frontmatter, `config/workflows/registry.json`, and `config/workflows/skills.json`.
- Extended workflow and skill registry loaders with `lifecycle_state`, `applicability`, and `purpose_long`, while preserving legacy prompt `route_status` compatibility.
- Added `bin/migrate-lifecycle-statuses.py` for idempotent dry-run-safe migration of legacy lifecycle statuses.
- Tightened `services/divergent_strategy.py` lifecycle writes so new promotion lifecycle rows use the five-state literal.

## Files Created/Modified

- `services/asset_lifecycle.py` (419 lines) - shared lifecycle types, transition helper, lifecycle listing, writeback-gated active promotion.
- `bin/migrate-lifecycle-statuses.py` (121 lines) - dry-run-safe legacy status migration.
- `tests/test_asset_lifecycle.py` (322 lines) - transition, writeback, listing, migration, and divergent writer coverage.
- `services/workflow_orchestration.py` - lifecycle fields on `WorkflowSpec` and `SkillSpec`; prompt alias mapping.
- `services/divergent_strategy.py` - normalized lifecycle writer path.
- `config/workflows/registry.json` - six workflows now carry lifecycle metadata.
- `config/workflows/skills.json` - 25 current skill rows now carry lifecycle metadata.
- `prompts/registry.json` and five prompt Markdown files - prompt lifecycle metadata backfill.

## Lifecycle Contract

- `draft -> candidate`
- `candidate -> approved | draft`
- `approved -> active`
- `active -> candidate | deprecated`
- `deprecated -> <none>`

Legacy migration mapping:

- `promoted -> candidate`
- `rejected -> deprecated`
- `pending -> candidate`

Canonical DB dry-run result at execution time: `scanned=0`, `remapped={}`, `unmapped={}`.

## Verification

- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_asset_lifecycle.py tests/test_workflow_orchestration.py tests/test_divergent_strategy.py tests/test_architecture_enforcement.py -q` -> 41 passed.
- `uv run ruff check services/asset_lifecycle.py services/workflow_orchestration.py services/divergent_strategy.py bin/migrate-lifecycle-statuses.py tests/test_asset_lifecycle.py tests/test_workflow_orchestration.py tests/test_divergent_strategy.py` -> passed.
- `uv run ruff format --check ...` for touched Python files -> passed.
- `uv run basedpyright services/asset_lifecycle.py services/workflow_orchestration.py services/divergent_strategy.py bin/migrate-lifecycle-statuses.py` -> 0 errors.
- `uv run vulture services/asset_lifecycle.py services/workflow_orchestration.py services/divergent_strategy.py bin/migrate-lifecycle-statuses.py --min-confidence 70` -> no findings.
- Registry smoke checks confirmed 5 prompt templates, 6 workflows, and 25 skill rows carry lifecycle metadata.
- `uv run python bin/migrate-lifecycle-statuses.py --dry-run` -> no canonical rows required migration.

## Deviations from Plan

- The skill registry currently contains 25 rows, not the 23 rows named in the plan. All current rows were backfilled.
- The local shell has no bare `python` executable, so Python smoke checks used `uv run python`.
- `improvement_writebacks` uses the richer Phase 5 schema in `schema.sql`; `promote_asset` mirrors that actual schema rather than the plan shorthand.

## Next Phase Readiness

Plan 08-02 can build on the canonical lifecycle fields now present on workflow and skill specs. Plan 08-04 should revisit the duplicated writeback policy once a shared services-level approval helper is justified.

---
*Phase: 08-prompt-skill-workflow-contracts-and-asset-lifecycle*
*Completed: 2026-05-24*
