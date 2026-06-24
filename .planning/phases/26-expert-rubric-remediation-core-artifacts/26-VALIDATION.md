---
phase: 26
slug: expert-rubric-remediation-core-artifacts
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-24
---

# Phase 26 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/test_expert_rubric_remediation.py -q` |
| **Full suite command** | `uv run pytest tests/test_expert_rubric_remediation.py -q` |
| **Estimated runtime** | under 30 seconds |

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_expert_rubric_remediation.py -q`
- **After every plan wave:** Run `uv run pytest tests/test_expert_rubric_remediation.py -q`
- **Before `/gsd-verify-work`:** Run targeted pytest, Ruff check, Ruff format check, and BasedPyright commands from the plans.
- **Max feedback latency:** 60 seconds for targeted checks.

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 26-01-01 | 01 | 1 | Phase goal | T-26-01 | Missing evidence/verification rejects invalid artifacts | unit | `uv run pytest tests/test_expert_rubric_remediation.py -q` | yes | pending |
| 26-01-02 | 01 | 1 | Phase goal | T-26-02 | Artifact writes stay under explicit output dir | unit | `uv run pytest tests/test_expert_rubric_remediation.py -q` | yes | pending |
| 26-02-01 | 02 | 2 | Phase goal | T-26-03 | Fixture findings retain source evidence references | unit | `uv run pytest tests/test_expert_rubric_remediation.py::test_soundscape_fixture_builds_evidence_backed_audit_and_plan -q` | yes | pending |
| 26-02-02 | 02 | 2 | Phase goal | T-26-04 | Handoff requires user approval and does not execute code | unit | `uv run pytest tests/test_expert_rubric_remediation.py -q` | yes | pending |

## Wave 0 Requirements

Existing pytest infrastructure covers all Phase 26 requirements.

## Manual-Only Verifications

All phase behaviors have automated verification.

## Validation Sign-Off

- [x] All tasks have `<automated>` verify commands.
- [x] Sampling continuity: no 3 consecutive tasks without automated verify.
- [x] Wave 0 covers all test infrastructure needs.
- [x] No watch-mode flags.
- [x] Feedback latency target is under 60 seconds.
- [x] `nyquist_compliant: true` set in frontmatter.

**Approval:** approved 2026-06-24
