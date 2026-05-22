---
phase: 9
slug: continuous-learning-and-conservative-optimization
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-22
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (Python 3.12) + pnpm for UI type checks |
| **Config file** | `pyproject.toml` (ruff + basedpyright + vulture sections) |
| **Quick run command** | `uv run pytest tests/test_learning_taxonomy.py tests/test_learning_analysis.py tests/test_conservative_optimizer.py tests/test_learning_impact.py tests/test_aios_cli.py tests/test_orchestration_runtime.py -x -q` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | ~45 seconds |

---

## Sampling Rate

- **After every Python task commit:** `uv run pytest tests/test_learning_taxonomy.py tests/test_learning_analysis.py tests/test_conservative_optimizer.py tests/test_learning_impact.py tests/test_aios_cli.py tests/test_orchestration_runtime.py tests/test_divergent_strategy.py -x -q && uv run ruff check services bin tests && uv run ruff format --check services bin tests && uv run basedpyright`
- **After every UI task commit:** `cd aios-ui && pnpm lint && pnpm tsc --noEmit`
- **After every wave:** `uv run pytest -q && uv run ruff check . && uv run ruff format --check . && uv run basedpyright && uv run vulture services bin --min-confidence 70 && cd aios-ui && pnpm lint && pnpm tsc --noEmit`
- **Phase gate:** Full suite green + `aios contracts-audit` shows `LearningSignal` contract `status: implemented` + `aios learning-analyze --since 30d --json` returns ≥1 detected pattern + `aios learning-impact --workflow implementation-delivery --since 30d` returns populated rollup

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 09-01-T1a | 09-01 | 1 | LEARN-01 | unit | `uv run pytest tests/test_orchestration_runtime.py::test_signal_kind_column_added_idempotently -x` | ❌ W0 | ⬜ pending |
| 09-01-T1b | 09-01 | 1 | LEARN-01 | unit | `uv run pytest tests/test_aios_cli.py::test_record_learning_event_persists_signal_kind -x` | ❌ W0 | ⬜ pending |
| 09-01-T3 | 09-01 | 1 | LEARN-01 | unit | `uv run pytest tests/test_aios_cli.py::test_workflow_learning_payload_includes_signal_kind -x` | ❌ W0 | ⬜ pending |
| 09-02-T1a | 09-02 | 2 | LEARN-02 | unit | `uv run pytest tests/test_learning_analysis.py::test_detect_repeated_failures_groups_by_criterion_and_workflow -x` | ❌ W0 | ⬜ pending |
| 09-02-T1b | 09-02 | 2 | LEARN-02 | unit | `uv run pytest tests/test_learning_analysis.py::test_detect_ignored_rules_requires_multi_run_recurrence -x` | ❌ W0 | ⬜ pending |
| 09-02-T1c | 09-02 | 2 | LEARN-02 | unit | `uv run pytest tests/test_learning_analysis.py::test_detect_bloated_packets_uses_per_workflow_median -x` | ❌ W0 | ⬜ pending |
| 09-02-T2a | 09-02 | 2 | LEARN-02 | unit | `uv run pytest tests/test_learning_analysis.py::test_detect_weak_prompts_requires_sample_floor -x` | ❌ W0 | ⬜ pending |
| 09-02-T2b | 09-02 | 2 | LEARN-02 | unit | `uv run pytest tests/test_learning_analysis.py::test_detect_weak_workflows_aggregates_stage_blockers -x` | ❌ W0 | ⬜ pending |
| 09-02-T3a | 09-02 | 2 | LEARN-02 | integration | `uv run pytest tests/test_learning_analysis.py::test_detect_route_misroutes_uses_route_result_json -x` | ❌ W0 | ⬜ pending |
| 09-02-T3b | 09-02 | 2 | LEARN-02 | unit | `uv run pytest tests/test_learning_analysis.py::test_detect_standards_regression_reads_priority_bucket -x` | ❌ W0 | ⬜ pending |
| 09-02-T3c | 09-02 | 2 | LEARN-02 | unit | `uv run pytest tests/test_learning_analysis.py::test_detectors_honor_since_parameter -x` | ❌ W0 | ⬜ pending |
| 09-03-T1 | 09-03 | 2 | LEARN-04 | integration | `uv run pytest tests/test_learning_impact.py::test_per_run_impact_returns_full_payload -x` | ❌ W0 | ⬜ pending |
| 09-03-T2a | 09-03 | 2 | LEARN-04 | unit | `uv run pytest tests/test_learning_impact.py::test_rollup_trend_insufficient_data -x` | ❌ W0 | ⬜ pending |
| 09-03-T2b | 09-03 | 2 | LEARN-04 | unit | `uv run pytest tests/test_learning_impact.py::test_rollup_trend_improving_requires_sample_floor -x` | ❌ W0 | ⬜ pending |
| 09-04-T1 | 09-04 | 3 | LEARN-03 | unit | `uv run pytest tests/test_conservative_optimizer.py::test_route_default_requires_approval -x` | ❌ W0 | ⬜ pending |
| 09-04-T2a | 09-04 | 3 | LEARN-03 | unit | `uv run pytest tests/test_conservative_optimizer.py::test_proposer_rejects_low_sample -x` | ❌ W0 | ⬜ pending |
| 09-04-T2b | 09-04 | 3 | LEARN-03 | unit | `uv run pytest tests/test_conservative_optimizer.py::test_proposer_always_requires_approval -x` | ❌ W0 | ⬜ pending |
| 09-04-T3 | 09-04 | 3 | LEARN-03 | integration | `uv run pytest tests/test_conservative_optimizer.py::test_cooling_period_dedupe -x` | ❌ W0 | ⬜ pending |
| 09-05-T1a | 09-05 | 3 | LEARN-04 | integration | `uv run pytest tests/test_aios_cli.py::test_learning_impact_cli_per_run -x` | ❌ W0 | ⬜ pending |
| 09-05-T1b | 09-05 | 3 | LEARN-04 | integration | `uv run pytest tests/test_aios_cli.py::test_learning_propose_cli_writes_writebacks -x` | ❌ W0 | ⬜ pending |
| 09-05-T2 | 09-05 | 3 | LEARN-01 | unit | `uv run pytest tests/test_aios_cli.py::test_contracts_audit_includes_learning_signal -x` | ❌ W0 | ⬜ pending |
| 09-05-T3 | 09-05 | 3 | LEARN-04 | type | `cd aios-ui && pnpm lint && pnpm tsc --noEmit` | partial | ⬜ pending |
| 09-06-T1 | 09-06 | 4 | LEARN-03 | integration | `uv run pytest tests/test_divergent_strategy.py::test_divergent_winner_goes_through_propose_asset_promotion -x` | ❌ W0 | ⬜ pending |
| 09-06-T2 | 09-06 | 4 | LEARN-03 | integration | `uv run pytest tests/test_aios_cli.py::test_learning_analyze_cli_dry_run -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_learning_taxonomy.py` — NEW file (literal completeness + impact_scope mapping, 2 tests)
- [ ] `tests/test_learning_analysis.py` — NEW file (8 detector tests)
- [ ] `tests/test_conservative_optimizer.py` — NEW file (threshold gates, cooling period, scope mapping, never-mutate-registry, 7 tests)
- [ ] `tests/test_learning_impact.py` — NEW file (per-run + rollup projections, trend math, 3 tests)
- [ ] `tests/test_aios_cli.py` — extend with 6 new CLI subcommand + contracts-audit tests
- [ ] `tests/test_orchestration_runtime.py` — extend with `test_signal_kind_column_added_idempotently`
- [ ] `tests/test_divergent_strategy.py` — extend with `test_divergent_winner_goes_through_propose_asset_promotion`
- [ ] `aios-ui/lib/types.ts` — extend with `LearningSignalKind`, `RecurringPattern`, `LearningImpactPerRun`, `LearningImpactRollup`, `ConservativeProposalRow`
- [ ] `aios-ui/server/aios/learning.ts` — extend with 4 new exported functions
- [ ] `aios-ui/server/routers/learning.ts` — NEW file (or extend `control-plane.ts`)
- [ ] `config/learning/conservatism-policy.json` — NEW file with conservative defaults
- [ ] No new conftest.py needed — existing tests use `sqlite3.connect(":memory:")` patterns

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| UI renders per-run impact + rollup with proposal-status callouts | LEARN-04 | Requires live browser check | Open learning surface in `aios-ui`; verify impact + rollup panels render |
| `aios learning-analyze --since 30d --json` returns ≥1 pattern on dev DB | LEARN-02 | Requires live DB with run history | Run against dev DB after ≥2 runs with the same criterion failing |
