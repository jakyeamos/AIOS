---
phase: 28
slug: expert-rubric-remediation-cli-and-verification
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-24
---

# Phase 28 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/test_aios_cli.py::test_tmcp_review_plan_writes_expert_review_artifacts tests/test_workflow_orchestration.py::test_expert_review_workflow_executes_with_artifacts -q` |
| **Full suite command** | `uv run pytest tests/test_aios_cli.py tests/test_workflow_orchestration.py tests/test_expert_rubric_remediation.py -q` |
| **Estimated runtime** | under 120 seconds targeted; full focused slice may run longer |

## Sampling Rate

- **After every task commit:** Run the focused test or check named in that task.
- **After every plan wave:** Run the quick command above.
- **Before `/gsd-verify-work`:** Run the full focused suite plus Ruff, format, BasedPyright, Vulture, smoke command, and git status review.
- **Max feedback latency:** 120 seconds for targeted checks.

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 28-01-01 | 01 | 1 | Phase goal | T-28-01 | CLI rejects malformed evidence JSON and missing required inputs | unit | `uv run pytest tests/test_aios_cli.py::test_tmcp_review_plan_writes_expert_review_artifacts -q` | yes | pending |
| 28-01-02 | 01 | 1 | Phase goal | T-28-02 | CLI writes artifacts under caller output dir and reports paths | unit | `uv run pytest tests/test_aios_cli.py::test_tmcp_review_plan_writes_expert_review_artifacts -q` | yes | pending |
| 28-02-01 | 02 | 2 | Phase goal | T-28-03 | Focused quality gates run on touched implementation files | quality | `uv run ruff check services/aios_cli.py tests/test_aios_cli.py services/workflow_orchestration.py tests/test_workflow_orchestration.py services/expert_rubric_remediation.py tests/test_expert_rubric_remediation.py` | yes | pending |
| 28-02-02 | 02 | 2 | Phase goal | T-28-04 | Project truth preserves focused-vs-repo quality distinction | docs | `git diff --check .tracker/PROJECT_TRUTH.md` | yes | pending |
| 28-03-01 | 03 | 3 | Phase goal | T-28-05 | Smoke command produces review-plan JSON and local artifacts | smoke | `uv run python bin/aios.py --json tmcp review-plan "Review Soundscape UI polish with TMCP expertise and create a rubric remediation plan" --project-path /Users/jakyeamos/projects/soundscape-app --output-dir /tmp/aios-expert-review-smoke --evidence-json '{"dimension_id":"data_realism","severity":"blocker","summary":"Feed waveform uses random visual data.","evidence":["packages/web/src/components/feed/FeedItem.tsx:427"],"recommended_fix":"Derive waveform heights from stable input."}' --selected-slice-id slice-1` | yes | pending |
| 28-03-02 | 03 | 3 | Phase goal | T-28-06 | Final handoff records checks, artifacts, caveats, and next action | docs | `git diff --check .planning/phases/28-expert-rubric-remediation-cli-and-verification/28-VERIFICATION.md` | no | pending |

## Wave 0 Requirements

Existing pytest, Ruff, BasedPyright, Vulture, and CLI infrastructure cover Phase 28 requirements.

## Manual-Only Verifications

All phase behaviors have automated or command-based verification. Human review is required only to interpret final repo-level quality caveats.

## Validation Sign-Off

- [x] All tasks have `<automated>` verify commands.
- [x] Sampling continuity: no 3 consecutive tasks without automated verify.
- [x] Wave 0 covers all test infrastructure needs.
- [x] No watch-mode flags.
- [x] Feedback latency target is under 120 seconds for focused checks.
- [x] `nyquist_compliant: true` set in frontmatter.

**Approval:** approved 2026-06-24
