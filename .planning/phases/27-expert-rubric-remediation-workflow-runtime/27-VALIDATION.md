---
phase: 27
slug: expert-rubric-remediation-workflow-runtime
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-24
---

# Phase 27 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/test_workflow_orchestration.py::test_expert_review_workflow_executes_with_artifacts tests/test_workflow_orchestration.py::test_expert_review_workflow_registry_contract tests/test_workflow_orchestration.py::test_expert_review_objective_routes_to_rubric_remediation_workflow -q` |
| **Full suite command** | `uv run pytest tests/test_workflow_orchestration.py -q` |
| **Estimated runtime** | under 90 seconds targeted; full file may run longer |

## Sampling Rate

- **After every task commit:** Run the focused test named in that task.
- **After every plan wave:** Run the quick command above.
- **Before `/gsd-verify-work`:** Run the full workflow orchestration test file plus targeted Ruff/format/BasedPyright checks.
- **Max feedback latency:** 120 seconds for targeted checks.

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 27-01-01 | 01 | 1 | Phase goal | T-27-01 | Runtime refuses missing TMCP packet where required | unit | `uv run pytest tests/test_workflow_orchestration.py::test_expert_review_workflow_executes_with_artifacts -q` | yes | pending |
| 27-01-02 | 01 | 1 | Phase goal | T-27-02 | Artifact paths stay under review output root | unit | `uv run pytest tests/test_workflow_orchestration.py::test_expert_review_workflow_executes_with_artifacts -q` | yes | pending |
| 27-02-01 | 02 | 2 | Phase goal | T-27-03 | Registry skills can only run in declared stage kinds | unit | `uv run pytest tests/test_workflow_orchestration.py::test_expert_review_workflow_registry_contract -q` | yes | pending |
| 27-02-02 | 02 | 2 | Phase goal | T-27-04 | Required validations run and report explicit pass/fail | unit | `uv run pytest tests/test_workflow_orchestration.py::test_expert_review_workflow_registry_contract tests/test_workflow_orchestration.py::test_expert_review_workflow_executes_with_artifacts -q` | yes | pending |
| 27-03-01 | 03 | 3 | Phase goal | T-27-05 | Diagnostic workflow-key text does not route to content workflow | unit | `uv run pytest tests/test_workflow_orchestration.py::test_rank_workflow_candidates_ignores_diagnostic_workflow_key_mentions -q` | yes | pending |
| 27-03-02 | 03 | 3 | Phase goal | T-27-06 | Expert audit-plan objectives route to expert workflow | unit | `uv run pytest tests/test_workflow_orchestration.py::test_expert_review_objective_routes_to_rubric_remediation_workflow -q` | yes | pending |

## Wave 0 Requirements

Existing pytest infrastructure covers all Phase 27 requirements.

## Manual-Only Verifications

All phase behaviors have automated verification.

## Validation Sign-Off

- [x] All tasks have `<automated>` verify commands.
- [x] Sampling continuity: no 3 consecutive tasks without automated verify.
- [x] Wave 0 covers all test infrastructure needs.
- [x] No watch-mode flags.
- [x] Feedback latency target is under 120 seconds for focused checks.
- [x] `nyquist_compliant: true` set in frontmatter.

**Approval:** approved 2026-06-24
