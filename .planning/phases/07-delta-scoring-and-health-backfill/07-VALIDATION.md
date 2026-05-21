---
phase: 7
slug: delta-scoring-and-health-backfill
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-20
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (Python 3.12) + pnpm for UI type checks |
| **Config file** | `pyproject.toml` (ruff + basedpyright + vulture sections) |
| **Quick run command** | `uv run pytest tests/test_standards_health.py tests/test_aios_cli.py -x -q` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every Python task commit:** `uv run pytest tests/test_standards_health.py tests/test_aios_cli.py -x -q && uv run ruff check services bin tests && uv run ruff format --check services bin tests && uv run basedpyright`
- **After every UI task commit:** `cd aios-ui && pnpm lint && pnpm tsc --noEmit`
- **After every wave:** `uv run pytest -q && uv run ruff check . && uv run ruff format --check . && uv run basedpyright && cd aios-ui && pnpm lint && pnpm tsc --noEmit`
- **Phase gate:** Full suite green + `aios contracts-audit` counts increase for new contracts + `aios prove-project-health` shows all 10 DELT-01 domains in `domain_scores_json`

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 07-01-T1 | 07-01 | 1 | DELT-01 | unit | `uv run pytest tests/test_standards_health.py::test_registry_covers_all_delt_01_domains -x` | ❌ W0 | ⬜ pending |
| 07-01-T2a | 07-01 | 1 | DELT-01 | unit | `uv run pytest tests/test_standards_health.py::test_compute_score_emits_all_ten_domains -x` | ❌ W0 | ⬜ pending |
| 07-02-T1a | 07-02 | 2 | DELT-02 | unit | `uv run pytest tests/test_standards_health.py::test_build_explanation_includes_required_fields -x` | ❌ W0 | ⬜ pending |
| 07-02-T1b | 07-02 | 2 | DELT-03 | unit | `uv run pytest tests/test_standards_health.py::test_classify_provenance_confirmed_for_auto_with_evidence -x` | ❌ W0 | ⬜ pending |
| 07-02-T1c | 07-02 | 2 | DELT-03 | unit | `uv run pytest tests/test_standards_health.py::test_classify_provenance_missing_without_evidence -x` | ❌ W0 | ⬜ pending |
| 07-02-T1d | 07-02 | 2 | DELT-03 | integration | `uv run pytest tests/test_standards_health.py::test_classify_provenance_contradictory_on_stale_findings -x` | ❌ W0 | ⬜ pending |
| 07-02-T1e | 07-02 | 2 | DELT-03 | unit | `uv run pytest tests/test_standards_health.py::test_classify_provenance_inferred_for_manual -x` | ❌ W0 | ⬜ pending |
| 07-02-T2a | 07-02 | 2 | DELT-04 | unit | `uv run pytest tests/test_standards_health.py::test_recommend_workflow_returns_standards_backfill_for_foundational -x` | ❌ W0 | ⬜ pending |
| 07-02-T2b | 07-02 | 2 | DELT-04 | unit | `uv run pytest tests/test_standards_health.py::test_recommend_workflow_includes_approval_policy -x` | ❌ W0 | ⬜ pending |
| 07-03-T1 | 07-03 | 3 | DELT-02 | type | `cd aios-ui && pnpm lint && pnpm tsc --noEmit` | partial | ⬜ pending |
| 07-03-T2 | 07-03 | 3 | DELT-04 | integration | `uv run pytest tests/test_aios_cli.py::test_recommend_workflow_cli -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_standards_health.py` — add stubs for all 9 new test functions listed above
- [ ] `tests/test_aios_cli.py` — add stub for `test_recommend_workflow_cli`
- [ ] `aios-ui/lib/control-plane.ts` — extend `StandardsHealthSummary` type with `deltaExplanations: DeltaExplanation[]` and `recommendedWorkflows: RecommendedWorkflow[]`
- [ ] No new conftest.py needed — existing tests use `sqlite3.connect(":memory:")` and `_seed_minimal_runtime_tables`
- [ ] No framework install required — pytest + ruff + basedpyright + pnpm already wired

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| UI renders `deltaExplanations` with drill-down and `recommendedWorkflows` with `available_in_registry: false` callouts | DELT-02, DELT-04 | Requires live browser check | Open project surface in `aios-ui`, inspect recommendations panel |
| `aios prove-project-health` reports all 10 DELT-01 domains in `domain_scores_json` | DELT-01 | Requires live CLI run | Run `aios prove-project-health --project AIOS` and verify output |
