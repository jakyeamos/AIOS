---
phase: 6
slug: standards-resolution-and-evidence-based-evaluation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-20
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (Python 3.12) |
| **Config file** | `pyproject.toml` (ruff + basedpyright + vulture sections) |
| **Quick run command** | `uv run pytest tests/test_success_criteria.py tests/test_orchestration_runtime.py -x -q` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** `uv run pytest tests/test_success_criteria.py tests/test_orchestration_runtime.py tests/test_agentize.py tests/test_aios_cli.py -x -q && uv run ruff check services bin tests && uv run ruff format --check services bin tests && uv run basedpyright`
- **After every plan wave:** `uv run pytest -q && uv run ruff check . && uv run ruff format --check . && uv run basedpyright`
- **Before `/gsd-verify-work`:** Full suite must be green + governance-audit and contracts-audit both report `implemented_count = canonical_contract_count` for `EvaluationFinding`
- **Max feedback latency:** ~30 seconds (quick run)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 06-01-T1 | 06-01 | 1 | STND-01 | — | Resolution merges criteria + standards before execution | unit | `uv run pytest tests/test_success_criteria.py::test_resolve_task_standards_merges_criteria_and_standards -x` | ❌ W0 | ⬜ pending |
| 06-01-T2 | 06-01 | 1 | STND-01 | — | Resolution persisted on `briefing_packets` and consumed at closeout | integration | `uv run pytest tests/test_orchestration_runtime.py::test_packet_resolution_round_trip -x` | ❌ W0 | ⬜ pending |
| 06-02-T1 | 06-02 | 2 | STND-02 | — | Stage-level evaluation produces structured findings, not free-form `issues[]` | unit | `uv run pytest tests/test_orchestration_runtime.py::test_stage_evaluation_emits_findings -x` | ❌ W0 | ⬜ pending |
| 06-02-T2 | 06-02 | 2 | STND-02 | — | `agentize.py` packet pulls registry-resolved standards | unit | `uv run pytest tests/test_agentize.py::test_agentize_standards_come_from_registry -x` | ❌ W0 | ⬜ pending |
| 06-03-T1a | 06-03 | 3 | STND-03 | — | Execution-first ignores docs-only sessions under `services/` | unit | `uv run pytest tests/test_success_criteria.py::test_execution_first_skips_pure_doc_changes -x` | ❌ W0 | ⬜ pending |
| 06-03-T1b | 06-03 | 3 | STND-03 | — | Broadened evidence sources (tool_events Bash) feed the evaluator | integration | `uv run pytest tests/test_success_criteria.py::test_execution_first_accepts_tool_event_evidence -x` | ❌ W0 | ⬜ pending |
| 06-03-T2a | 06-03 | 3 | STND-04 | — | Stage findings survive session close as queryable rows + JSON artifact | integration | `uv run pytest tests/test_orchestration_runtime.py::test_stage_findings_persisted_to_db_and_artifact -x` | ❌ W0 | ⬜ pending |
| 06-03-T2b | 06-03 | 3 | STND-04 | — | Closeout report references stage findings under `governance.stage_evaluations` | integration | `uv run pytest tests/test_aios_cli.py::test_governance_audit_includes_stage_findings -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_success_criteria.py` — add stubs for `test_resolve_task_standards_merges_criteria_and_standards`, `test_execution_first_skips_pure_doc_changes`, `test_execution_first_accepts_tool_event_evidence`
- [ ] `tests/test_orchestration_runtime.py` — add stubs for `test_stage_evaluation_emits_findings`, `test_packet_resolution_round_trip`, `test_stage_findings_persisted_to_db_and_artifact`
- [ ] `tests/test_agentize.py` — add stub for `test_agentize_standards_come_from_registry`
- [ ] `tests/test_aios_cli.py` — add stub for `test_governance_audit_includes_stage_findings`
- [ ] `tests/fixtures/harness/` — add stage-evaluation fixture mirroring `passing-complete.json` shape with explicit stage finding expectations

*No new conftest.py needed — existing tests use direct `sqlite3.connect(":memory:")` and `_seed_minimal_runtime_tables` patterns.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Phase-gate: governance-audit and contracts-audit report `implemented_count = canonical_contract_count` for `EvaluationFinding` | STND-04 | Requires live CLI run | Run `aios governance-audit` and `aios contracts-audit`; verify counts match |
