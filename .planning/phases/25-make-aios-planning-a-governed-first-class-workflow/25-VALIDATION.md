---
phase: 25
slug: make-aios-planning-a-governed-first-class-workflow
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-24
---

# Phase 25 - Validation Strategy

## Test Infrastructure

| Property | Value |
| --- | --- |
| Framework | pytest plus context compiler validation |
| Config file | `pyproject.toml` |
| Quick run command | `uv run pytest -q tests/test_planning_workflow_detection.py tests/test_workflow_orchestration.py tests/test_task_routing.py tests/test_aios_cli.py tests/test_execution_symmetric_planner.py` |
| Full suite command | `uv run pytest -q tests/test_planning_workflow_detection.py tests/test_workflow_orchestration.py tests/test_task_routing.py tests/test_aios_cli.py tests/test_execution_symmetric_planner.py && pnpm context:validate` |
| Estimated runtime | under 60 seconds for targeted suite |

## Sampling Rate

- **After every task commit:** Run the plan-specific pytest command listed in `<verify><automated>`.
- **After every plan wave:** Run the quick run command.
- **Before `/gsd-verify-work`:** Run the full suite command and a live or copied-DB `codex-aios-shadow.py --no-worktree` smoke for the original failing objective.
- **Max feedback latency:** 60 seconds for targeted checks.

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 25-01-01 | 01 | 1 | planning detection | T-25-01 | Preserve weak-route blocking | unit | `uv run pytest -q tests/test_planning_workflow_detection.py` | yes | pending |
| 25-01-02 | 01 | 1 | planning detection | T-25-01 | Exact failing phrase is classified | unit | `uv run pytest -q tests/test_planning_workflow_detection.py` | yes | pending |
| 25-02-01 | 02 | 2 | governed route | T-25-02 | Planning workflow routes only with planning evidence | unit | `uv run pytest -q tests/test_workflow_orchestration.py tests/test_task_routing.py` | yes | pending |
| 25-02-02 | 02 | 2 | governed route | T-25-02 | Ambiguous routes still block | unit | `uv run pytest -q tests/test_task_routing.py` | yes | pending |
| 25-03-01 | 03 | 3 | planning packet | T-25-03 | Packet exposes standards/lenses before execution | CLI/unit | `uv run pytest -q tests/test_aios_cli.py tests/test_execution_symmetric_planner.py` | yes | pending |
| 25-03-02 | 03 | 3 | planning packet | T-25-03 | Route evidence remains drilldown-able | CLI/unit | `uv run pytest -q tests/test_aios_cli.py` | yes | pending |
| 25-04-01 | 04 | 4 | shadow smoke | T-25-04 | Original shadow route no longer blocks | smoke/unit | `uv run pytest -q tests/test_codex_aios_shadow.py tests/test_codex_aios_route.py` | yes | pending |
| 25-04-02 | 04 | 4 | closeout docs | T-25-04 | Truth records planning governance route | docs/check | `pnpm context:validate` | yes | pending |

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

## Manual-Only Verifications

All phase behaviors have automated verification. A final copied-DB smoke may be recorded as evidence if live DB state makes exact assertions too environment-specific.

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify commands.
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify.
- [ ] No watch-mode flags.
- [ ] Feedback latency under 60 seconds for targeted checks.
- [ ] Full suite command passes before phase verification.

**Approval:** pending
