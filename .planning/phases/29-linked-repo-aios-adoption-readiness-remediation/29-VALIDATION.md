---
phase: 29
slug: linked-repo-aios-adoption-readiness-remediation
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-24
---

# Phase 29 - Validation Strategy

## Test Infrastructure

| Property | Value |
| --- | --- |
| Framework | Pytest for AIOS services; repo-native gate commands for linked repos |
| Config file | `config/quality-pipeline.json` |
| Quick run command | `uv run pytest -q tests/test_linked_repo_readiness.py tests/test_quality_pipeline.py` |
| Full suite command | `uv run pytest -q tests/test_quality_gates.py tests/test_commit_quality_ladder.py tests/test_tier_one_regressions.py tests/test_quality_pipeline.py tests/test_linked_repo_readiness.py && pnpm context:validate` |
| Readiness command | `python3 scripts/linked-repo-quality-runner.py --report` |

## Sampling Rate

- **After each repo group:** Run the affected repo gates, then `python3 scripts/linked-repo-quality-runner.py --report`.
- **After each wave:** Run the quick AIOS command and confirm target repo `missing_gate_keys` shrank to `[]`, `adoption_status` is `adoption_ready`, and certification stages show `aios_wired: pass`, `quality_standard_compliant: pass`, and `release_ready: pass`.
- **Before closeout:** Run the full suite, readiness report, copied all-inventory proof, and live all-inventory proof.

## Per-Plan Verification Map

| Plan | Wave | Repos | Automated Command | Expected Final Status |
| --- | ---: | --- | --- | --- |
| 29-01 | 1 | portfolio, R-Project, csds391-s26-6 | `python3 scripts/linked-repo-quality-runner.py --report` | three repos `adoption_ready` with all certification stages passing |
| 29-02 | 2 | career-ops, claude-improvement-lab, pre-cr-suite-lsp | `python3 scripts/linked-repo-quality-runner.py --report` | three repos `adoption_ready` with all certification stages passing |
| 29-03 | 3 | BBDSE, Vaults | `python3 scripts/linked-repo-quality-runner.py --report` | two repos `adoption_ready` with all certification stages passing |
| 29-04 | 4 | LIS, Dsci-proj, Fantasy | `python3 scripts/linked-repo-quality-runner.py --report` | three repos `adoption_ready` with all certification stages passing |
| 29-05 | 5 | eslint-plugin-anti-slop, Terrace, AIOS | `python3 scripts/linked-repo-quality-runner.py --report` | three repos `adoption_ready` with all certification stages passing |
| 29-06 | 6 | tm, Bballedu, dispatches-from-cyberspace | `python3 scripts/linked-repo-quality-runner.py --report` | three repos `adoption_ready` with all certification stages passing |
| 29-07 | 7 | BidCamp, tenure, EliHealth, amos-saas, soundscape-app, remodelvision | `python3 scripts/linked-repo-quality-runner.py --report` | six repos `adoption_ready` with all certification stages passing |
| 29-08 | 8 | portfolio closeout | `python3 scripts/linked-repo-quality-runner.py --report` | ready 23, adoption-ready 23, blocked 0, evidence-required 0, excluded 3 |

## Manual-Only Verifications

None planned. Remote CI is not required for this phase; local CI replacement proof is the accepted CI evidence.
