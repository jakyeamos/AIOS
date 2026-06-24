---
phase: 24
slug: rectify-linked-repo-aios-readiness-blockers-except-agent-router
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-24
---

# Phase 24 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Pytest for AIOS services; repo-native commands for linked repos |
| **Config file** | `pyproject.toml`, `config/quality-pipeline.json`, repo-native package/CI config |
| **Quick run command** | `uv run pytest -q tests/test_quality_gates.py tests/test_commit_quality_ladder.py tests/test_quality_pipeline.py` |
| **Full suite command** | `uv run pytest -q tests/test_quality_gates.py tests/test_commit_quality_ladder.py tests/test_tier_one_regressions.py tests/test_quality_pipeline.py && pnpm context:validate` |
| **Estimated runtime** | ~2 seconds for focused AIOS tests plus context validation; repo-native gates vary by repo |

---

## Sampling Rate

- **After every task commit:** Run that task's repo-native gate plus the quick AIOS command when AIOS config/services changed.
- **After every plan wave:** Run the full suite command plus contract validation across the affected repo set.
- **Before `/gsd-verify-work`:** Full suite, copied/live `prove-project-health --all-inventory`, and final portfolio readiness ledger must be green.
- **Max feedback latency:** AIOS-only checks should stay under 60 seconds; long repo-native suites must be recorded with command-level evidence.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 24-01-01 | 01 | 1 | Phase goal | T-24-01 | Evidence runner does not execute repo-local command declarations | unit | `uv run pytest -q tests/test_linked_repo_readiness.py tests/test_quality_pipeline.py` | ❌ W0 | ⬜ pending |
| 24-01-02 | 01 | 1 | Phase goal | T-24-02 | Readiness report excludes `agent-router` | unit | `uv run pytest -q tests/test_linked_repo_readiness.py` | ❌ W0 | ⬜ pending |
| 24-02-01 | 02 | 2 | Phase goal | T-24-03 | Evidence-only repos require pass records before ready | integration | `python3 -c 'from services.quality_gates import validate_commit_quality_gate; ...'` | ✅ | ⬜ pending |
| 24-03-01 | 03 | 3 | Phase goal | T-24-04 | Web-app gates include env/security/dependency/smoke evidence | repo-native | `pnpm lint && pnpm build` per affected repo plus configured gates | ✅ | ⬜ pending |
| 24-04-01 | 04 | 4 | Phase goal | T-24-05 | Dirty/lint/package-manager debt is not hidden as readiness | repo-native | repo-specific lint/build/test commands | ✅ | ⬜ pending |
| 24-05-01 | 05 | 5 | Phase goal | T-24-06 | Package/tool repos prove consumed surface | repo-native | repo-specific lint/typecheck/test/package commands | ✅ | ⬜ pending |
| 24-06-01 | 06 | 6 | Phase goal | T-24-07 | Python/data repos use class validation, not fake app gates | repo-native | repo-specific uv/make validation commands | ✅ | ⬜ pending |
| 24-07-01 | 07 | 7 | Phase goal | T-24-08 | Floor-only Python/data repos get real or excepted validation | repo-native | repo-specific validation commands | ✅ | ⬜ pending |
| 24-08-01 | 08 | 8 | Phase goal | T-24-09 | Content/container repos use delegated/aggregate validation | repo-native | `pre-cr run --json --workspace ...` plus content/container validators | ✅ | ⬜ pending |
| 24-09-01 | 09 | 9 | Phase goal | T-24-10 | CI/default proof or non-remote exceptions are recorded | integration | `uv run python bin/aios.py --json prove-project-health --all-inventory` | ✅ | ⬜ pending |
| 24-10-01 | 10 | 10 | Phase goal | T-24-11 | Final ledger has 22 in-scope repos ready or explicitly excepted | integration | full suite command plus contract validation | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_linked_repo_readiness.py` — service-level tests for portfolio readiness aggregation, evidence requirements, and `agent-router` exclusion.
- [ ] `services/linked_repo_readiness.py` — reusable readiness aggregation if existing `quality_pipeline.py` cannot express final verdicts cleanly.
- [ ] `scripts/linked-repo-quality-runner.py` — CLI runner if direct manual gate execution cannot record durable evidence consistently.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Remote/default-branch CI status | Phase goal | May require GitHub remote/API access or branch protection status unavailable locally | Capture workflow URL/status or record non-remote exception with owner, reason, review date, local proof command, and replacement path. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60 seconds for AIOS-only checks
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
