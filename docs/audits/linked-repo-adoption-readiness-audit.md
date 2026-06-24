# Linked Repo Adoption Readiness Audit

Date: 2026-06-24
Phase: 23
Plan: 23-01

## Verdict

The active linked-repo inventory is clean enough to execute Phase 23, but the portfolio is not adoption-ready under strict release standards.

Current state:

- Active inventory has 23 source repos.
- Every active repo path exists and is a git worktree.
- Every active repo has `.aios-quality-gate.json`.
- Dirty trees are widespread but are not the first readiness blocker for most repos.
- `floor_only` and `pre_cr_only` contracts are not adoption-ready.
- AIOS-owned quality-pipeline coverage is missing for most active repos.
- Architecture-enforcement coverage is currently limited to AIOS, amos-saas, soundscape-app, Terrace, and portfolio.
- CI evidence is missing for most active repos.
- No fresh `quality_pipeline_runs` evidence exists in the live AIOS DB for the active portfolio at audit time.

## Execution Order

Phase 23 keeps the latest distance ordering, closest first:

1. soundscape-app
2. portfolio
3. Terrace
4. AIOS
5. dispatches-from-cyberspace
6. remodelvision
7. pre-cr-suite-lsp
8. Bballedu
9. tm
10. video-pipeline
11. amos-saas
12. eslint-plugin-anti-slop
13. career-ops
14. Dsci-proj
15. claude-improvement-lab
16. R-Project
17. LIS
18. csds391-s26-6
19. manga-sync
20. Vaults
21. agent-router
22. BBDSE
23. Fantasy

Dirty-tree count is recorded for closeout hygiene, not as the primary distance factor.

## Class Map

| Repo | Class |
| --- | --- |
| AIOS | Platform/control-plane |
| soundscape-app | Production/public web app |
| amos-saas | Production/public web app |
| portfolio | Production/public web app |
| remodelvision | Production/public web app |
| dispatches-from-cyberspace | Production/public web app |
| Bballedu | Production/public web app |
| tm | Production/public web app |
| Terrace | Developer tool/package |
| pre-cr-suite-lsp | Developer tool/package |
| eslint-plugin-anti-slop | Developer tool/package |
| video-pipeline | Developer tool/package |
| agent-router | Developer tool/package |
| LIS | Python/data/research/course |
| R-Project | Python/data/research/course |
| Dsci-proj | Python/data/research/course |
| Fantasy | Python/data/research/course |
| manga-sync | Python/data/research/course |
| career-ops | Python/data/research/course |
| claude-improvement-lab | Python/data/research/course |
| csds391-s26-6 | Python/data/research/course |
| Vaults | Content/vault/container |
| BBDSE | Content/vault/container |

## Portfolio Readiness Table

| Order | Repo | Class | Dirty | Contract maturity | Configured AIOS gates | Pipeline gates | Architecture | CI | First blocker |
| ---: | --- | --- | ---: | --- | --- | --- | --- | --- | --- |
| 1 | soundscape-app | Production/public web app | 3 | mature_candidate | architecture, pre_cr, test_quality | install, lint, typecheck, test, build, architecture, ci, secret_scan, env_validation, dependency_security, coverage, e2e_smoke, seo, telemetry_utility, db_restore, pitr_monitor, mobile_release, full_e2e | yes | yes | Fresh local and remote evidence missing |
| 2 | portfolio | Production/public web app | 3 | mature_candidate | architecture, pre_cr, test_quality | install, lint, build, architecture, ci | yes | yes | Production/public web gates incomplete |
| 3 | Terrace | Developer tool/package | 2 | mature_candidate | pre_cr, test_quality | install, test, architecture, ci | yes | yes | Package lint/build/consumer smoke not fully represented |
| 4 | AIOS | Platform/control-plane | 74 | mature_candidate | architecture, pre_cr, test_quality, thermo_nuclear_simplification | install, lint, typecheck, test, build, architecture, ci, divergent_strategy_standard, pre_pr_readiness, thermo_nuclear_simplification | yes | yes | Fresh Phase 23 proof missing; dirty tree deferred |
| 5 | dispatches-from-cyberspace | Production/public web app | 2 | mature_candidate | pre_cr, test_quality | none | no | yes | Missing AIOS pipeline and architecture bindings |
| 6 | remodelvision | Production/public web app | 6 | mature_candidate | pre_cr, test_quality | none | no | no | Missing AIOS pipeline, architecture, and CI bindings |
| 7 | pre-cr-suite-lsp | Developer tool/package | 19 | mature_candidate | pre_cr, test_quality | none | no | yes | Missing package pipeline and architecture binding |
| 8 | Bballedu | Production/public web app | 2 | mature_candidate | pre_cr, test_quality | none | no | no | Missing production pipeline, architecture, and CI bindings |
| 9 | tm | Production/public web app | 2 | mature_candidate | pre_cr, test_quality | none | no | no | Missing production pipeline, architecture, and CI bindings |
| 10 | video-pipeline | Developer tool/package | 2 | mature_candidate | pre_cr, test_quality | none | no | no | Missing package pipeline, architecture, and CI bindings |
| 11 | amos-saas | Production/public web app | 6 | mature_candidate | test_quality | install, lint, build, architecture, ci | yes | no | Production/public web gates incomplete and CI evidence absent |
| 12 | eslint-plugin-anti-slop | Developer tool/package | 10 | mature_candidate | pre_cr, test_quality | none | no | yes | Missing package pipeline and architecture binding |
| 13 | career-ops | Python/data/research/course | 7 | mature_candidate | test_quality | none | no | no | Missing class-specific validation pipeline |
| 14 | Dsci-proj | Python/data/research/course | 2 | pre_cr_only | pre_cr | none | no | yes | `pre_cr_only` contract; missing real validation gates |
| 15 | claude-improvement-lab | Python/data/research/course | 2 | pre_cr_only | pre_cr | none | no | no | `pre_cr_only` contract; missing Python validation gates |
| 16 | R-Project | Python/data/research/course | 2 | pre_cr_only | pre_cr | none | no | no | `pre_cr_only` contract; missing R validation gates |
| 17 | LIS | Python/data/research/course | 3 | pre_cr_only | pre_cr | none | no | no | `pre_cr_only` contract; missing Python validation gates |
| 18 | csds391-s26-6 | Python/data/research/course | 0 | pre_cr_only | pre_cr | none | no | no | `pre_cr_only` contract; missing course validation gates |
| 19 | manga-sync | Python/data/research/course | 2 | pre_cr_only | pre_cr | none | no | no | `pre_cr_only` contract; missing data validation gates |
| 20 | Vaults | Content/vault/container | 5 | pre_cr_only | pre_cr | none | no | no | `pre_cr_only` contract; missing content/vault validation |
| 21 | agent-router | Developer tool/package | 2 | pre_cr_only | pre_cr | none | no | no | `pre_cr_only` contract; missing package/tool gates |
| 22 | BBDSE | Content/vault/container | 12 | floor_only | test_quality | none | no | no | `floor_only` diff-check gate only; needs aggregate/delegated subproject gates |
| 23 | Fantasy | Python/data/research/course | 18 | pre_cr_only | pre_cr | none | no | no | `pre_cr_only` contract; missing validation gates |

## Inventory Hygiene Result

The active inventory excludes inactive duplicate, non-source, missing-source, and broad-container rows. Known inactive rows include `.claude`, `Bball`, `Downloads`, duplicate uppercase-path `Dsci-proj` and `Fantasy` rows, `jakyeamos`, `LinkedinHelper`, `oslab`, `projects`, `sleeper_league_pack`, and `Terrace `.

`prove-project-health --all-inventory` should remain scoped to active rows only during Phase 23 so inactive rows do not contaminate standards-health proof.

## Gate Maturity Findings

Strict readiness is blocked by these gate classes:

- Weak contract maturity: `agent-router`, `claude-improvement-lab`, `csds391-s26-6`, `Dsci-proj`, `Fantasy`, `LIS`, `manga-sync`, `R-Project`, and `Vaults` are `pre_cr_only`.
- Floor-only contract: `BBDSE` remains `floor_only` and is not mature. Its current gate is only a minimal floor until aggregate or delegated subproject checks exist.
- Missing pipeline config: most repos outside AIOS, soundscape-app, portfolio, Terrace, and amos-saas have no AIOS-owned `config/quality-pipeline.json` entry.
- Missing architecture config: most repos have no architecture-enforcement project binding.
- Missing CI evidence: only soundscape-app, portfolio, Terrace, dispatches-from-cyberspace, Dsci-proj, eslint-plugin-anti-slop, and pre-cr-suite-lsp currently expose workflow files from the local checkout scan.
- Missing recorded proof: live DB query found no fresh `quality_pipeline_runs` for the active portfolio during this audit.

## Plan 23-01 Acceptance Check

- Active repo list recorded: pass.
- Repo class recorded for every active repo: pass.
- Latest distance order preserved: pass.
- Dirty-tree count recorded but not used as the main readiness blocker: pass.
- `floor_only` and `pre_cr_only` contracts explicitly marked non-ready: pass.
- First maturation blocker identified per repo: pass.

## Next Plan Input

Plan 23-02 must define class-based strict readiness in a reusable contract before replacing weak gates. The contract should explicitly say that repo-local `.aios-quality-gate.json` files declare only gate IDs, while executable commands remain in AIOS-owned config.

## Phase 23 Evidence Reporting Update

Plan 23-07 added portfolio reporting support so `services.quality_pipeline.get_project_quality_pipeline` now exposes each repo's class, strict readiness verdict, maturation blockers, and any non-remote CI exception alongside latest gate status, source, timestamp, command, and evidence IDs.

`prove-project-health --all-inventory` was tightened to target active inventory rows only. It no longer appends default proving projects during an all-inventory proof, which prevents inactive or removed repos such as GitNexus from contaminating portfolio standards-health snapshots.

Current strict-readiness distribution from `config/quality-pipeline.json`:

| Verdict | Count | Meaning |
| --- | ---: | --- |
| `ready` | 0 | No active linked repo has complete strict evidence yet. |
| `evidence_required` | 2 | Class gates are substantially configured, but fresh local/remote proof is still missing. |
| `blocked` | 21 | Real gates, CI/default proof, architecture/security validation, repo truth, or aggregate evidence are still missing. |

Repos currently in `evidence_required`:

| Repo | Reason |
| --- | --- |
| soundscape-app | Full class gate configuration exists, but fresh local and remote evidence is still required. |
| AIOS | Platform-control-plane gates exist, but fresh Phase 23 quality-pipeline evidence, standards-health proof, and default-branch CI proof are still required; dirty-tree cleanup is deferred to closeout hygiene. |

All other active linked repos remain `blocked` until their class-specific maturation blockers in `config/quality-pipeline.json` are resolved. Dirty-tree notes remain visible for closeout hygiene but are not treated as the primary adoption-readiness blocker.

## Phase 24 Readiness Report

Phase 24 excludes `agent-router` from remediation scope and uses an AIOS-owned report surface before repo-specific fixes begin:

```bash
python3 scripts/linked-repo-quality-runner.py --report
```

The report returns JSON with `target_count`, `excluded_count`, `ready_count`, `blocked_count`, `evidence_required_count`, `excluded_projects`, and per-project verdicts. Gate execution uses the same script with commands resolved from `config/quality-pipeline.json`, for example:

```bash
python3 scripts/linked-repo-quality-runner.py --project soundscape-app --gate lint --dry-run
```
