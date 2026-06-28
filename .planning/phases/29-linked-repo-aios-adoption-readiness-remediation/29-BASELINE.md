# Phase 29 Baseline Report

Generated: 2026-06-26T14:22:06.626308+00:00

Command: `python3 scripts/linked-repo-quality-runner.py --report`

## Counts

| Field | Value |
| --- | ---: |
| `target_count` | 23 |
| `ready_count` | 0 |
| `blocked_count` | 23 |
| `evidence_required_count` | 0 |
| `excluded_count` | 3 |
| `adoption_ready_count` | 0 |
| `adopted_but_blocked_count` | 23 |
| `not_adopted_count` | 0 |

## In-Scope Repos

| Repo | Verdict | Adoption status | Missing gates | Certification blockers |
| --- | --- | --- | --- | --- |
| soundscape-app | blocked | adopted_but_blocked | lint, typecheck, test, ci, secret_scan, dependency_security, e2e_smoke, pre_cr, anti_slop | Fresh local and remote evidence still required before final adoption-ready status.; anti_slop_not_passing; ci_local_replacement_proof_missing; gate_not_passing:anti_slop:stale; ... |
| portfolio | blocked | adopted_but_blocked | ci, pre_cr, anti_slop | Fresh local evidence, coverage proof, and local CI proof are required before final adoption-ready status.; anti_slop_not_passing; ci_local_replacement_proof_missing; gate_not_passing:anti_slop:stale; ... |
| Terrace | blocked | adopted_but_blocked | test, architecture, ci, dependency_security, pre_cr, anti_slop | Missing substantive architecture boundary gate, passing dependency/security evidence, and fresh local CI proof.; anti_slop_not_passing; ci_local_replacement_proof_missing; gate_not_passing:anti_slop:stale; ... |
| aios | blocked | adopted_but_blocked | install, test, architecture, ci, pre_cr, anti_slop | Fresh Phase 23 local quality-pipeline evidence, standards-health proof, and local CI proof are required before final adoption-ready status; dirty-tree cleanup is deferred to closeout hygiene.; anti_slop_not_passing; ci_local_replacement_proof_missing; gate_not_passing:anti_slop:stale; ... |
| dispatches-from-cyberspace | blocked | adopted_but_blocked | typecheck, architecture, ci, dependency_security, pre_cr, anti_slop | Substantive architecture rules, coverage proof, and fresh local CI proof are still required before final adoption-ready status.; anti_slop_not_passing; ci_local_replacement_proof_missing; gate_not_passing:anti_slop:stale; ... |
| remodelvision | blocked | adopted_but_blocked | lint, typecheck, test, build, architecture, ci, secret_scan, dependency_security, e2e_smoke, pre_cr, anti_slop | Substantive architecture proof, passing local evidence for all configured gates, and local CI proof are still required before final adoption-ready status.; anti_slop_not_passing; ci_local_replacement_proof_missing; gate_not_passing:anti_slop:stale; ... |
| pre-cr-suite-lsp | blocked | adopted_but_blocked | architecture, ci, dependency_security, anti_slop | Missing substantive architecture boundary gate, passing dependency/security evidence, and fresh local CI proof.; anti_slop_not_passing; ci_local_replacement_proof_missing; gate_not_passing:anti_slop:stale; ... |
| Bballedu | blocked | adopted_but_blocked | architecture, ci, dependency_security, e2e_smoke, pre_cr, anti_slop | Substantive architecture rules, local CI proof, and coverage proof are still required before final adoption-ready status.; anti_slop_not_passing; ci_local_replacement_proof_missing; gate_not_passing:anti_slop:stale; ... |
| tm | blocked | adopted_but_blocked | architecture, ci, dependency_security, pre_cr, anti_slop | Substantive architecture rules, local CI proof, and coverage proof are still required before final adoption-ready status.; anti_slop_not_passing; ci_local_replacement_proof_missing; gate_not_passing:anti_slop:stale; ... |
| amos-saas | blocked | adopted_but_blocked | lint, typecheck, build, architecture, ci, dependency_security, pre_cr, anti_slop | Substantive architecture proof, passing local evidence for all configured gates, and local CI proof are still required before final adoption-ready status.; anti_slop_not_passing; ci_local_replacement_proof_missing; gate_not_passing:anti_slop:stale; ... |
| eslint-plugin-anti-slop | blocked | adopted_but_blocked | lint, typecheck, architecture, ci, anti_slop | Missing lint/typecheck/build scripts, substantive architecture boundary gate, passing dependency/security evidence, and fresh local CI proof.; anti_slop_not_passing; ci_local_replacement_proof_missing; gate_not_passing:anti_slop:stale; ... |
| career-ops | blocked | adopted_but_blocked | ci, pre_cr, validation | ci_local_replacement_proof_missing; gate_not_passing:ci:blocked; gate_not_passing:pre_cr:fail; gate_not_passing:validation:fail; ... |
| Dsci-proj | blocked | adopted_but_blocked | lint, test, ci, dependency_security, pre_cr | Dashboard npm lockfile is canonical for the dashboard subproject; local CI proof plus passing lint/test/dependency/Pre-CR evidence remain required before final adoption-ready status.; ci_local_replacement_proof_missing; gate_not_passing:ci:blocked; gate_not_passing:dependency_security:fail; ... |
| claude-improvement-lab | blocked | adopted_but_blocked | ci, dependency_security, pre_cr | Compile/structure checks replace py_compile-only floor proof, but benchmark tasks/tests, local CI proof, and passing dependency evidence remain required before readiness.; ci_local_replacement_proof_missing; gate_not_passing:ci:blocked; gate_not_passing:dependency_security:fail; ... |
| R-Project | blocked | adopted_but_blocked | lint, ci, pre_cr | R structure and script validation are configured, but local CI proof, reproducible dependency lock strategy, and passing local evidence remain required before readiness.; ci_local_replacement_proof_missing; gate_not_passing:ci:blocked; gate_not_passing:lint:stale; ... |
| LIS | blocked | adopted_but_blocked | lint, test, ci, dependency_security | ci_local_replacement_proof_missing; gate_not_passing:ci:blocked; gate_not_passing:dependency_security:fail; gate_not_passing:lint:fail; ... |
| csds391-s26-6 | blocked | adopted_but_blocked | lint, ci, pre_cr | Course structure validation replaces pre-cr-only floor proof, but assignment-specific tests/builds and local CI proof remain required before readiness.; ci_local_replacement_proof_missing; gate_not_passing:ci:blocked; gate_not_passing:lint:stale; ... |
| Vaults | blocked | adopted_but_blocked | architecture, ci, secret_scan, pre_cr, validation | Vault content validation is configured, but failing vault/protected-path evidence, Pre-CR status, and local CI proof remain required before readiness.; ci_local_replacement_proof_missing; gate_not_passing:architecture:fail; gate_not_passing:ci:blocked; ... |
| BBDSE | blocked | adopted_but_blocked | ci, pre_cr, validation | All child repos under BBDSE count toward container readiness; any failing child Pre-CR evidence plus local CI proof remain required before readiness.; ci_local_replacement_proof_missing; gate_not_passing:ci:blocked; gate_not_passing:pre_cr:fail; ... |
| Fantasy | blocked | adopted_but_blocked | lint, test, ci, dependency_security, validation | Aggregate backend/frontend validation is configured, but local CI proof plus passing aggregate test/validation/dependency evidence remain required before final adoption-ready status.; ci_local_replacement_proof_missing; gate_not_passing:ci:blocked; gate_not_passing:dependency_security:fail; ... |
| BidCamp | blocked | adopted_but_blocked | install, lint, typecheck, test, build, architecture, ci, secret_scan, dependency_security | Newly added Phase 29 adoption target; needs repo-local AIOS contract, Pre-CR baseline, passing local evidence, and local CI proof before adoption-ready status.; ci_local_replacement_proof_missing; gate_not_passing:architecture:fail; gate_not_passing:build:fail; ... |
| tenure | blocked | adopted_but_blocked | ci, secret_scan, dependency_security, e2e_smoke | Newly added Phase 29 adoption target; needs repo-local AIOS contract, fresh passing local evidence, and local CI proof before adoption-ready status.; ci_local_replacement_proof_missing; gate_not_passing:ci:fail; gate_not_passing:dependency_security:fail; ... |
| EliHealth | blocked | adopted_but_blocked | install, lint, test, ci, mobile_release | Newly added Phase 29 mobile-app adoption target; needs repo-local AIOS contract, Pre-CR baseline, passing mobile release proof, and local CI proof before adoption-ready status.; ci_local_replacement_proof_missing; gate_not_passing:ci:fail; gate_not_passing:install:fail; ... |

## Excluded Repos

| Repo | Reason |
| --- | --- |
| video-pipeline | excluded_by_phase24_scope |
| manga-sync | excluded_by_phase24_scope |
| agent-router | excluded_by_phase24_scope |
