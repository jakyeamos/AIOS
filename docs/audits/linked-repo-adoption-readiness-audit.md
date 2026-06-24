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

### Phase 24 Plan 24-02 Evidence Update

Phase 24 Plan 24-02 recorded fresh local `quality_pipeline_runs` rows for `soundscape-app` and AIOS. Neither repo is ready after this pass.

`soundscape-app` currently reports `blocked`. Passing local evidence exists for:

- `install`: `quality-soundscape-app-install-20260624030240386207`
- `build`: `quality-soundscape-app-build-20260624030754235748`
- `architecture`: `quality-soundscape-app-architecture-20260624030903961084`
- `repo_truth`: `quality-soundscape-app-repo_truth-20260624030921689608`

`soundscape-app` has failed or blocked evidence for `lint`, `typecheck`, `test`, `ci`, `secret_scan`, `env_validation`, `dependency_security`, `coverage`, `e2e_smoke`, `seo`, `telemetry_utility`, `db_restore`, `pitr_monitor`, `mobile_release`, `full_e2e`, and `pre_cr`. CI/default-branch status was not verified locally; workflow-file presence was recorded only as blocked proof.

AIOS currently reports `blocked`. Passing local evidence exists for:

- `lint`: `quality-aios-lint-20260624031207273699`
- `typecheck`: `quality-aios-typecheck-20260624031219178848`
- `build`: `quality-aios-build-20260624031232586125`
- `pre_pr_readiness`: `quality-aios-pre_pr_readiness-20260624031144459912`
- `thermo_nuclear_simplification`: `quality-aios-thermo_nuclear_simplification-20260624031145649704`
- `repo_truth`: `quality-aios-repo_truth-20260624031332592940`

AIOS has failed or blocked evidence for `install`, `test`, `architecture`, `ci`, `divergent_strategy_standard`, and `pre_cr`. Dirty-tree state remains closeout hygiene and is separate from this readiness verdict.

### Phase 24 Plan 24-03 Evidence Update

Phase 24 Plan 24-03 added real production-web gate surfaces for `portfolio`, `dispatches-from-cyberspace`, `Bballedu`, and `tm`, then registered matching AIOS-owned commands in `config/quality-pipeline.json` and `config/quality-gates.json`. Repo-local implementation commits:

- `portfolio`: `665821a` (`feat(24-03): add production web validation scripts`)
- `dispatches-from-cyberspace`: `afddf2d` (`feat(24-03): add production web validation scripts`)
- `Bballedu`: `7acad4f` (`feat(24-03): add production web validation scripts`)
- `tm`: `07c1222` (`feat(24-03): add production web validation scripts`)

`portfolio` currently reports `blocked`. Passing local evidence exists for:

- `install`: `quality-portfolio-install-20260624032452263030`
- `lint`: `quality-portfolio-lint-20260624032455322977`
- `typecheck`: `quality-portfolio-typecheck-20260624032458464758`
- `test`: `quality-portfolio-test-20260624032458980244`
- `build`: `quality-portfolio-build-20260624032502512166`
- `architecture`: `quality-portfolio-architecture-20260624032506414684`
- `secret_scan`: `quality-portfolio-secret_scan-20260624032503535755`
- `env_validation`: `quality-portfolio-env_validation-20260624032502978956`
- `dependency_security`: `quality-portfolio-dependency_security-20260624032505025821`
- `e2e_smoke`: `quality-portfolio-e2e_smoke-20260624032505648266`
- `repo_truth`: `quality-portfolio-repo_truth-20260624032717648038`

`portfolio` remains blocked on `ci`, `coverage`, `seo`, `full_e2e`, and `pre_cr`. CI workflow-file presence was recorded as blocked proof in `quality-portfolio-ci-20260624032718438878`, not default-branch pass proof. Pre-CR failure is recorded in `quality-portfolio-pre_cr-20260624032506234166`.

`dispatches-from-cyberspace` currently reports `blocked`. Passing local evidence exists for:

- `install`: `quality-dispatches-from-cyberspace-install-20260624032507767345`
- `lint`: `quality-dispatches-from-cyberspace-lint-20260624032509770861`
- `test`: `quality-dispatches-from-cyberspace-test-20260624032514593445`
- `build`: `quality-dispatches-from-cyberspace-build-20260624032522267754`
- `secret_scan`: `quality-dispatches-from-cyberspace-secret_scan-20260624032525060238`
- `env_validation`: `quality-dispatches-from-cyberspace-env_validation-20260624032523918225`
- `e2e_smoke`: `quality-dispatches-from-cyberspace-e2e_smoke-20260624032532125788`
- `repo_truth`: `quality-dispatches-from-cyberspace-repo_truth-20260624032717873106`

`dispatches-from-cyberspace` remains blocked on `typecheck`, `architecture`, `ci`, `dependency_security`, `coverage`, `seo`, `full_e2e`, and `pre_cr`. Failed or blocked evidence is recorded in `quality-dispatches-from-cyberspace-typecheck-20260624032513862355`, `quality-dispatches-from-cyberspace-dependency_security-20260624032530929952`, `quality-dispatches-from-cyberspace-ci-20260624032718599623`, and `quality-dispatches-from-cyberspace-pre_cr-20260624032532797575`.

`Bballedu` currently reports `blocked`. Passing local evidence exists for:

- `install`: `quality-Bballedu-install-20260624032535220734`
- `lint`: `quality-Bballedu-lint-20260624032544997910`
- `typecheck`: `quality-Bballedu-typecheck-20260624032557287349`
- `test`: `quality-Bballedu-test-20260624032600696138`
- `build`: `quality-Bballedu-build-20260624032609063990`
- `secret_scan`: `quality-Bballedu-secret_scan-20260624032610141624`
- `env_validation`: `quality-Bballedu-env_validation-20260624032609514313`
- `repo_truth`: `quality-Bballedu-repo_truth-20260624032718059533`

`Bballedu` remains blocked on `architecture`, `ci`, `dependency_security`, `coverage`, `e2e_smoke`, `seo`, `full_e2e`, and `pre_cr`. Failed evidence is recorded in `quality-Bballedu-dependency_security-20260624032611656430`, `quality-Bballedu-e2e_smoke-20260624032614173994`, and `quality-Bballedu-pre_cr-20260624032614759093`.

`tm` currently reports `blocked`. Passing local evidence exists for:

- `install`: `quality-tm-install-20260624032615788962`
- `lint`: `quality-tm-lint-20260624032617726525`
- `typecheck`: `quality-tm-typecheck-20260624032620734886`
- `test`: `quality-tm-test-20260624032623534647`
- `build`: `quality-tm-build-20260624032649964524`
- `secret_scan`: `quality-tm-secret_scan-20260624032651051237`
- `env_validation`: `quality-tm-env_validation-20260624032650531900`
- `e2e_smoke`: `quality-tm-e2e_smoke-20260624032653281131`
- `repo_truth`: `quality-tm-repo_truth-20260624032718215420`

`tm` remains blocked on `architecture`, `ci`, `dependency_security`, `coverage`, `seo`, `full_e2e`, and `pre_cr`. Failed evidence is recorded in `quality-tm-dependency_security-20260624032652880198` and `quality-tm-pre_cr-20260624032653973497`.

No production web app in this plan is ready. Plan 24-09 still owns CI/default proof and non-remote exception handling.

### Phase 24 Plan 24-04 Evidence Update

Phase 24 Plan 24-04 added targeted validation gates for the production apps that needed cleanup before ordinary evidence capture: `remodelvision` and `amos-saas`.

Repo-local implementation commits:

- `remodelvision`: `64e1618` (`feat(24-04): add targeted production validation gates`)
- `amos-saas`: `1b92195` (`feat(24-04): add targeted production validation gates`)

Both repos now declare `pnpm@10.26.0` as the package manager and no longer keep `package-lock.json` as a competing lockfile. Both repos have `.github/workflows/aios-quality.yml` locally; this is workflow-file presence only, not CI/default-branch proof.

`remodelvision` currently reports `blocked`. Passing local evidence exists for:

- `install`: `quality-remodelvision-install-20260624033731152399`
- `repo_truth`: `quality-remodelvision-repo_truth-20260624034007273603`

`remodelvision` remains blocked on `lint`, `typecheck`, `test`, `build`, `architecture`, `ci`, `secret_scan`, `env_validation`, `dependency_security`, `coverage`, `e2e_smoke`, `seo`, `full_e2e`, and `pre_cr`. Failed or blocked evidence is recorded in:

- `lint`: `quality-remodelvision-lint-20260624033737492463`
- `typecheck`: `quality-remodelvision-typecheck-20260624033744444284`
- `test`: `quality-remodelvision-test-20260624033748371031`
- `build`: `quality-remodelvision-build-20260624033804028691`
- `ci`: `quality-remodelvision-ci-20260624034007583633`
- `secret_scan`: `quality-remodelvision-secret_scan-20260624034006512092`
- `env_validation`: `quality-remodelvision-env_validation-20260624033807366600`
- `dependency_security`: `quality-remodelvision-dependency_security-20260624033809737561`
- `coverage`: `quality-remodelvision-coverage-20260624033805071075`
- `e2e_smoke`: `quality-remodelvision-e2e_smoke-20260624033805661106`
- `pre_cr`: `quality-remodelvision-pre_cr-20260624033810428334`

Primary `remodelvision` blockers observed locally: source lint/typecheck debt, failing tests/build, `TESTING.md` secret-literal finding, missing local env values, dependency-security findings, e2e smoke failure, no architecture binding, and no verified CI/default-branch proof. `.worktrees/**` and `coverage/**` are now excluded from lint so copied/generated trees no longer dominate the lint signal.

`amos-saas` currently reports `blocked`. Passing local evidence exists for:

- `install`: `quality-amos-saas-install-20260624033811477990`
- `test`: `quality-amos-saas-test-20260624033837901213`
- `secret_scan`: `quality-amos-saas-secret_scan-20260624034007114250`
- `e2e_smoke`: `quality-amos-saas-e2e_smoke-20260624033902990651`
- `repo_truth`: `quality-amos-saas-repo_truth-20260624034007427650`

`amos-saas` remains blocked on `lint`, `typecheck`, `build`, `architecture`, `ci`, `env_validation`, `dependency_security`, `coverage`, `seo`, `full_e2e`, and `pre_cr`. Failed or blocked evidence is recorded in:

- `lint`: `quality-amos-saas-lint-20260624033824558685`
- `typecheck`: `quality-amos-saas-typecheck-20260624033834419814`
- `build`: `quality-amos-saas-build-20260624033902395753`
- `ci`: `quality-amos-saas-ci-20260624034007739848`
- `env_validation`: `quality-amos-saas-env_validation-20260624033904121881`
- `dependency_security`: `quality-amos-saas-dependency_security-20260624033905876802`

Primary `amos-saas` blockers observed locally: existing lint/typecheck/build debt, missing local env values, Next.js high-severity dependency advisories, no architecture binding, no Pre-CR gate, and no verified CI/default-branch proof.

No targeted production app in this plan is ready. The package-manager ambiguity blocker is resolved for both repos, but readiness remains blocked on failed evidence and Plan 24-09 CI/default proof.

### Phase 24 Plan 24-05 Evidence Update

Phase 24 Plan 24-05 added developer-tool security gate surfaces for the active package/tool repos in scope: `Terrace`, `pre-cr-suite-lsp`, and `eslint-plugin-anti-slop`.

Repo-local implementation commits:

- `Terrace`: `6b484f1` (`feat(24-05): add developer tool security gates`)
- `pre-cr-suite-lsp`: `7bcdb51` (`feat(24-05): add developer tool security gates`)
- `eslint-plugin-anti-slop`: `78d42c9` (`feat(24-05): add developer tool security gates`)

`video-pipeline` is deprecated per the 2026-06-24 scope clarification and is now excluded from Phase 24 readiness targeting alongside `agent-router`. The failed local package-manager migration attempt was reverted in `/Users/jakyeamos/projects/video-pipeline`; no readiness claim is made for that repo.

Developer-tool `secret_scan` and `dependency_security` gates now apply to `developer_tool` projects in `config/quality-pipeline.json`, so the recorded security evidence appears in the readiness report.

`Terrace` currently reports `blocked`. Passing local evidence exists for:

- `install`: `quality-Terrace-install-20260624034759009758`
- `lint`: `quality-Terrace-lint-20260624034801070632`
- `typecheck`: `quality-Terrace-typecheck-20260624034803716103`
- `build`: `quality-Terrace-build-20260624034821324551`
- `package`: `quality-Terrace-package-20260624034827830257`
- `secret_scan`: `quality-Terrace-secret_scan-20260624035100914619`
- `repo_truth`: `quality-Terrace-repo_truth-20260624035102603284`

`Terrace` remains blocked on `test`, `architecture`, `ci`, `dependency_security`, and `pre_cr`. Failed or blocked evidence is recorded in `quality-Terrace-test-20260624034818999070`, `quality-Terrace-dependency_security-20260624034830346213`, `quality-Terrace-ci-20260624035103156812`, and `quality-Terrace-pre_cr-20260624034831063091`.

`pre-cr-suite-lsp` currently reports `blocked`. Passing local evidence exists for:

- `install`: `quality-pre-cr-suite-lsp-install-20260624034838641300`
- `lint`: `quality-pre-cr-suite-lsp-lint-20260624034846268684`
- `typecheck`: `quality-pre-cr-suite-lsp-typecheck-20260624034849184452`
- `test`: `quality-pre-cr-suite-lsp-test-20260624034854621620`
- `build`: `quality-pre-cr-suite-lsp-build-20260624034903257551`
- `package`: `quality-pre-cr-suite-lsp-package-20260624034915195833`
- `secret_scan`: `quality-pre-cr-suite-lsp-secret_scan-20260624035101653213`
- `repo_truth`: `quality-pre-cr-suite-lsp-repo_truth-20260624035102742299`
- `pre_cr`: `quality-pre-cr-suite-lsp-pre_cr-20260624034921887222`

`pre-cr-suite-lsp` remains blocked on `architecture`, `ci`, and `dependency_security`. Failed or blocked evidence is recorded in `quality-pre-cr-suite-lsp-dependency_security-20260624034920983503` and `quality-pre-cr-suite-lsp-ci-20260624035103331796`.

`eslint-plugin-anti-slop` currently reports `blocked`. Passing local evidence exists for:

- `install`: `quality-eslint-plugin-anti-slop-install-20260624034922593819`
- `test`: `quality-eslint-plugin-anti-slop-test-20260624034923675148`
- `package`: `quality-eslint-plugin-anti-slop-package-20260624034925222943`
- `secret_scan`: `quality-eslint-plugin-anti-slop-secret_scan-20260624035102055757`
- `dependency_security`: `quality-eslint-plugin-anti-slop-dependency_security-20260624034926711496`
- `repo_truth`: `quality-eslint-plugin-anti-slop-repo_truth-20260624035102872664`
- `pre_cr`: `quality-eslint-plugin-anti-slop-pre_cr-20260624034927336869`

`eslint-plugin-anti-slop` remains blocked on `lint`, `typecheck`, `build`, `architecture`, and `ci`. The lint/typecheck/build gaps are currently explicit project-shape blockers rather than hidden pass-through scripts. CI workflow-file presence was recorded as blocked proof in `quality-eslint-plugin-anti-slop-ci-20260624035103488638`, not default-branch pass proof.

The Phase 24 report now returns `target_count: 21` and `excluded_count: 2`, with `video-pipeline` and `agent-router` excluded. No developer-tool package repo in this plan is ready; Plan 24-09 still owns CI/default proof and non-remote exception handling.

### Phase 24 Plan 24-06 Evidence Update

Phase 24 Plan 24-06 registered structured Python/data/course gates for `LIS`, `career-ops`, `Dsci-proj`, and `Fantasy`, then recorded local evidence. No external repo files were changed; the plan used existing repo surfaces and AIOS-owned commands in `config/quality-pipeline.json`.

`LIS` currently reports `blocked`. Passing evidence exists for `install`, `architecture`, `build`, `secret_scan`, `validation`, `repo_truth`, and `pre_cr`: `quality-LIS-install-20260624045907337741`, `quality-LIS-architecture-20260624045507453503`, `quality-LIS-build-20260624050228348123`, `quality-LIS-secret_scan-20260624045508244223`, `quality-LIS-validation-20260624050234041466`, `quality-LIS-repo_truth-20260624050234594487`, and `quality-LIS-pre_cr-20260624050236126416`.

`LIS` remains blocked on `lint`, `typecheck`, `test`, `dependency_security`, and `ci`: `quality-LIS-lint-20260624045908501234`, `quality-LIS-typecheck-20260624045926604675`, `quality-LIS-test-20260624050226953803`, `quality-LIS-dependency_security-20260624045509240579`, and `quality-LIS-ci-20260624045509611238`.

`career-ops` currently reports `blocked`. Passing evidence exists for `install`, `lint`, `typecheck`, `test`, `architecture`, `secret_scan`, `dependency_security`, and `repo_truth`: `quality-career-ops-install-20260624050238846091`, `quality-career-ops-lint-20260624045510407018`, `quality-career-ops-typecheck-20260624045511165084`, `quality-career-ops-test-20260624050239677536`, `quality-career-ops-architecture-20260624050241257668`, `quality-career-ops-secret_scan-20260624045511933742`, `quality-career-ops-dependency_security-20260624045514507903`, and `quality-career-ops-repo_truth-20260624050241669419`.

`career-ops` remains blocked on `validation`, `ci`, and `pre_cr`: `quality-career-ops-validation-20260624050240801712`, `quality-career-ops-ci-20260624045514819305`, and `quality-career-ops-pre_cr-20260624050319804229`.

`Dsci-proj` currently reports `blocked`. Passing evidence exists for `install`, `architecture`, `secret_scan`, `validation`, and `repo_truth`: `quality-Dsci-proj-install-20260624050258087015`, `quality-Dsci-proj-architecture-20260624045515130870`, `quality-Dsci-proj-secret_scan-20260624045515516080`, `quality-Dsci-proj-validation-20260624050301212632`, and `quality-Dsci-proj-repo_truth-20260624050301535560`.

`Dsci-proj` remains blocked on `lint`, `test`, `dependency_security`, `ci`, and `pre_cr`: `quality-Dsci-proj-lint-20260624050259340616`, `quality-Dsci-proj-test-20260624050300818694`, `quality-Dsci-proj-dependency_security-20260624045516653891`, `quality-Dsci-proj-ci-20260624050319294056`, and `quality-Dsci-proj-pre_cr-20260624050302116994`. The dashboard subproject keeps npm as canonical because `apps/dashboard/package-lock.json` is checked in.

`Fantasy` currently reports `blocked`. Passing evidence exists for `install`, `architecture`, `secret_scan`, `repo_truth`, and `pre_cr`: `quality-Fantasy-install-20260624045525251789`, `quality-Fantasy-architecture-20260624045726228498`, `quality-Fantasy-secret_scan-20260624045726465313`, `quality-Fantasy-repo_truth-20260624050302316607`, and `quality-Fantasy-pre_cr-20260624050302978971`.

`Fantasy` remains blocked on aggregate backend/frontend `test`, aggregate backend/frontend `validation`, `dependency_security`, and `ci`: `quality-Fantasy-test-20260624045627439080`, `quality-Fantasy-validation-20260624045725938450`, `quality-Fantasy-dependency_security-20260624045726710884`, and `quality-Fantasy-ci-20260624045726859389`.

No structured Python/data/course repo in this plan is ready. Plan 24-07 owns the remaining floor-replacement Python/data/course repos, and Plan 24-09 owns CI/default proof.
