---
phase: 8
slug: prompt-skill-workflow-contracts-and-asset-lifecycle
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-21
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (Python 3.12) + pnpm for UI type checks |
| **Config file** | `pyproject.toml` (ruff + basedpyright + vulture sections) |
| **Quick run command** | `uv run pytest tests/test_workflow_orchestration.py tests/test_asset_lifecycle.py tests/test_asset_recommendation.py tests/test_workflow_promotion.py tests/test_agentize.py tests/test_aios_cli.py -x -q` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | ~45 seconds |

---

## Sampling Rate

- **After every Python task commit:** `uv run pytest tests/test_workflow_orchestration.py tests/test_asset_lifecycle.py tests/test_asset_recommendation.py tests/test_workflow_promotion.py tests/test_agentize.py tests/test_aios_cli.py tests/test_validate_prompts.py tests/test_task_routing.py -x -q && uv run ruff check services bin tests && uv run ruff format --check services bin tests && uv run basedpyright`
- **After every UI task commit:** `cd aios-ui && pnpm lint && pnpm tsc --noEmit`
- **After every wave:** `uv run pytest -q && uv run ruff check . && uv run ruff format --check . && uv run basedpyright && uv run vulture services bin --min-confidence 70 && cd aios-ui && pnpm lint && pnpm tsc --noEmit`
- **Phase gate:** Full suite green + `aios contracts-audit` shows `AssetLifecycle` row `status: implemented` + `aios asset-lifecycle list --kind workflow` shows all six existing workflows with valid `lifecycle_state` + `aios workflow-compare --workflow-key implementation-delivery --since 30d` returns populated metrics

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 08-01-T1a | 08-01 | 1 | ASSET-01 | unit | `uv run pytest tests/test_workflow_orchestration.py::test_load_registry_normalizes_lifecycle_fields -x` | ❌ W0 | ⬜ pending |
| 08-01-T1b | 08-01 | 1 | ASSET-01 | integration | `uv run pytest tests/test_asset_recommendation.py::test_build_asset_usage_evidence_joins_all_sources -x` | ❌ W0 | ⬜ pending |
| 08-01-T2a | 08-01 | 1 | ASSET-02 | unit | `uv run pytest tests/test_asset_lifecycle.py::test_promote_asset_rejects_invalid_transition -x` | ❌ W0 | ⬜ pending |
| 08-01-T2b | 08-01 | 1 | ASSET-02 | unit | `uv run pytest tests/test_asset_lifecycle.py::test_promote_asset_writes_lifecycle_transition -x` | ❌ W0 | ⬜ pending |
| 08-01-T3 | 08-01 | 1 | ASSET-02 | integration | `uv run pytest tests/test_asset_lifecycle.py::test_migration_remaps_legacy_statuses -x` | ❌ W0 | ⬜ pending |
| 08-02-T1a | 08-02 | 2 | WFLO-01 | unit | `uv run pytest tests/test_workflow_orchestration.py::test_stage_spec_loads_vnext_bindings -x` | ❌ W0 | ⬜ pending |
| 08-02-T1b | 08-02 | 2 | WFLO-01 | unit | `uv run pytest tests/test_workflow_orchestration.py::test_validate_bindings_rejects_unresolvable_input_source -x` | ❌ W0 | ⬜ pending |
| 08-02-T1c | 08-02 | 2 | WFLO-01 | unit | `uv run pytest tests/test_workflow_orchestration.py::test_existing_workflows_load_with_defaults -x` | ❌ W0 | ⬜ pending |
| 08-02-T2 | 08-02 | 2 | WFLO-02 | unit | `uv run pytest tests/test_workflow_orchestration.py::test_stage_spec_carries_full_bindings -x` | ❌ W0 | ⬜ pending |
| 08-02-T3 | 08-02 | 2 | WFLO-02 | integration | `uv run pytest tests/test_workflow_orchestration.py::test_stage_approval_gate_invokes_policy -x` | ❌ W0 | ⬜ pending |
| 08-03-T1 | 08-03 | 2 | ASSET-03 | unit | `uv run pytest tests/test_asset_recommendation.py::test_usage_evidence_records_per_workflow_outcomes -x` | ❌ W0 | ⬜ pending |
| 08-03-T2a | 08-03 | 2 | ASSET-04 | unit | `uv run pytest tests/test_asset_recommendation.py::test_recommendation_orders_by_lifecycle_state -x` | ❌ W0 | ⬜ pending |
| 08-03-T2b | 08-03 | 2 | ASSET-04 | integration | `uv run pytest tests/test_agentize.py::test_agentize_skills_come_from_recommender -x` | ❌ W0 | ⬜ pending |
| 08-03-T3 | 08-03 | 2 | ASSET-04 | integration | `uv run pytest tests/test_task_routing.py::test_route_includes_asset_recommendations -x` | ❌ W0 | ⬜ pending |
| 08-04-T1a | 08-04 | 3 | WFLO-03 | integration | `uv run pytest tests/test_workflow_orchestration.py::test_stage_evaluation_summary_in_report -x` | ❌ W0 | ⬜ pending |
| 08-04-T1b | 08-04 | 3 | WFLO-03 | integration | `uv run pytest tests/test_workflow_orchestration.py::test_stage_evaluation_summary_includes_stage_findings -x` | ❌ W0 | ⬜ pending |
| 08-04-T2a | 08-04 | 3 | WFLO-04 | integration | `uv run pytest tests/test_workflow_promotion.py::test_compare_workflow_returns_metrics -x` | ❌ W0 | ⬜ pending |
| 08-04-T2b | 08-04 | 3 | WFLO-04 | integration | `uv run pytest tests/test_workflow_promotion.py::test_propose_promotion_uses_phase_5_policy -x` | ❌ W0 | ⬜ pending |
| 08-04-T2c | 08-04 | 3 | WFLO-04 | integration | `uv run pytest tests/test_workflow_promotion.py::test_promotion_requires_approval_before_active -x` | ❌ W0 | ⬜ pending |
| 08-04-T3 | 08-04 | 3 | WFLO-04 | integration | `uv run pytest tests/test_aios_cli.py::test_workflow_compare_cli -x` | ❌ W0 | ⬜ pending |
| 08-05-T1 | 08-05 | 3 | WFLO-01 | unit | `uv run pytest tests/test_validate_prompts.py::test_lifecycle_state_required -x` | ❌ W0 | ⬜ pending |
| Cross-cutting | 08-04 | 3 | WFLO-04 | unit | `uv run pytest tests/test_aios_cli.py::test_contracts_audit_includes_asset_lifecycle -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_asset_lifecycle.py` — NEW file (state-transition rules, migration, promotion-with-writeback)
- [ ] `tests/test_asset_recommendation.py` — NEW file (evidence aggregation, ranking, exploration fallback)
- [ ] `tests/test_workflow_promotion.py` — NEW file (comparison + propose + finalize flow)
- [ ] `tests/test_workflow_orchestration.py` — extend with 8 new vNext schema + stage evaluation test functions
- [ ] `tests/test_agentize.py` — extend with `test_agentize_skills_come_from_recommender`
- [ ] `tests/test_aios_cli.py` — extend with 3 new CLI + contracts-audit tests
- [ ] `tests/test_validate_prompts.py` — extend with `test_lifecycle_state_required`
- [ ] `tests/test_task_routing.py` — extend with `test_route_includes_asset_recommendations`
- [ ] `aios-ui/lib/types.ts` — extend with `AssetLifecycleState`, `AssetRecord`, `WorkflowEffectiveness` types
- [ ] `aios-ui/server/aios/asset-lifecycle.ts` — NEW file
- [ ] `aios-ui/server/aios/workflow-effectiveness.ts` — NEW file
- [ ] No new conftest.py needed — existing tests use `sqlite3.connect(":memory:")` patterns

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| UI renders lifecycle state per workflow with effectiveness metrics drill-down | WFLO-04 | Requires live browser check | Open `aios-ui/app/workflows`, confirm lifecycle state + effectiveness metrics render |
| `aios asset-lifecycle list --kind workflow` shows all six workflows with valid `lifecycle_state` | ASSET-02 | Requires live CLI run | Run command; verify no `null` or legacy `route_status` values in output |
