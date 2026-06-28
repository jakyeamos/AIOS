# Phase 29: Linked Repo AIOS Adoption Readiness Remediation - Research

**Researched:** 2026-06-24
**Domain:** AIOS linked-repo quality remediation and evidence recording
**Confidence:** HIGH

## User Constraints

- [VERIFIED: user request] Phase 29 must remediate the current linked-repo blockers until all in-scope repos reach AIOS adoption-ready status.
- [VERIFIED: `29-IMPLEMENTATION.md`] Scope is the current 23 in-scope repositories: the 20 Phase 24 targets plus `BidCamp`, `tenure`, and `EliHealth`.
- [VERIFIED: `29-IMPLEMENTATION.md`] `agent-router`, `video-pipeline`, and `manga-sync` remain excluded.
- [VERIFIED: `29-IMPLEMENTATION.md`] Local CI replacement proof is the CI standard because GitHub Actions credits are constrained.
- [VERIFIED: user request] Workflow pilots must run on new linked-repo branches before portfolio-wide use.
- [VERIFIED: `24-VERIFICATION.md`] Dirty trees are closeout hygiene, not the first readiness driver.

## Summary

Phase 24 created the AIOS-owned gate and evidence setup. The prerequisite `repo_gate_adoption_v1` certification layer now separates AIOS wiring from standards compliance and release readiness. Phase 29 is the execution-grade remediation pass: collect real gate evidence, generate broad repo-class and gate-specific rubric packs, plan scoped GSD remediation from those audits, record fresh `quality_pipeline_runs` evidence, and move the readiness report from `ready_count: 0` / `adoption_ready_count: 0` to `ready_count: 23` / `adoption_ready_count: 23`.

The phase should run easiest-first by current required failing gate count. Each repo is adoption-ready only when `python3 scripts/linked-repo-quality-runner.py --report` shows `missing_gate_keys: []`, `adoption_status: adoption_ready`, and passing `aios_wired`, `quality_standard_compliant`, and `release_ready` certification stages for that repo.

**Primary recommendation:** Execute repo remediation in sequential waves, but do not start code fixes for a sizable repo until broad-standard and gate-specific rubric docs exist. Then fix non-`ci` gates before local `ci` proof for each repo and close with portfolio proof and truth updates.

**Pilot recommendation:** Quality-test the workflow on `BidCamp`, `EliHealth`, and `pre-cr-suite-lsp` before broad rollout. This sequence covers dense production web, mobile/native, and non-UI developer-tool repos. Each pilot should use a new target-repo branch and generate one scoped GSD phase from the validated adoption docs before any wider execution.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
| --- | --- | --- | --- |
| Gate command authority | AIOS control plane | Linked repos | Executable commands remain in `config/quality-pipeline.json`; repos only change to make configured commands pass. |
| Gate failure remediation | Linked repos | AIOS evidence runner | Source fixes belong in the failing repo; evidence is recorded through AIOS. |
| Local CI proof | AIOS runner | Linked repos | `linked-repo-ci-local-proof.py` checks required gate pass state and records `ci` evidence. |
| Readiness verdict | AIOS control plane | Phase ledger | `linked-repo-quality-runner.py --report` is the readiness source of truth. |
| Truth and closeout | AIOS docs/planning | Linked repo truth files | AIOS records portfolio state; repo truth changes are made only when repo behavior changes. |

## Pilot Branch Matrix

| Order | Repo | Repo class | Branch | Workflow stress tested |
| ---: | --- | --- | --- | --- |
| 1 | `BidCamp` | Production/public web app | `codex/phase-29-bidcamp-adoption-pilot` | Dense web-app classification, UI visual proof, architecture, dependency/security, Pre-CR, anti-slop, local CI. |
| 2 | `EliHealth` | Mobile app | `codex/phase-29-elihealth-adoption-pilot` | Native/mobile classification, Xcode or simulator proof, mobile release validation, native build/test repair, local CI. |
| 3 | `pre-cr-suite-lsp` | Developer tool/package | `codex/phase-29-pre-cr-suite-lsp-adoption-pilot` | Non-UI package/tool classification, `no_ui_exception`, architecture and dependency-security planning, local CI. |

## Standard Stack

### Core

| Tool/File | Purpose | Why Standard |
| --- | --- | --- |
| `scripts/linked-repo-quality-runner.py` | Run configured gates and record evidence | Existing Phase 24 evidence entrypoint. |
| `scripts/linked-repo-ci-local-proof.py` | Local CI replacement proof | Approved current CI policy. |
| `aios gate adoption-plan --repo-root <repo>` | Generate broad and gate-specific rubric pack plus rollout plan | Prevents command failures from being treated as the whole remediation scope. |
| `aios gate adoption-doc-quality --repo-root <repo> --run-id <run-id>` | Generate adoption docs and validate their agent/human quality before phase execution | Prevents structurally incomplete, generic, or evidence-light docs from becoming implementation inputs. |
| `AIOS-backfill/gate-adoption/{run_id}` | Git-ignored adoption artifact folder in the target repo | Keeps broad rubric, audit, and rollout documents out of tracked repo docs folders. |
| `tmcp-expert-enrichment.json` | Record whether TMCP expert context was source-sufficient for the repo/gate rubric pack | Allows expert enrichment when real source exists without pretending TMCP is expert on unsupported gates. |
| `rubric-detail-manifest.json` | Agent-readable index of every per-rubric audit and implementation Markdown/JSON doc | Lets GSD phase generation consume stable structured documents instead of scraping prose. |
| Browser/computer-use/Xcode visual proof | Confirm UI-bearing repos through actual rendered runtime evidence | UI code standards and TMCP UI rubric review do not prove the interface renders or behaves correctly. |
| `config/quality-pipeline.json` | Repo classes, required gates, commands, local CI exception metadata | AIOS-owned command authority. |
| `services/quality_pipeline.py` | Required-gate status and evidence summaries | Existing readiness evaluator. |
| `services/linked_repo_readiness.py` | Phase 24/29 readiness aggregation | Existing report contract. |

### Supporting

| Tool/File | Purpose | When to Use |
| --- | --- | --- |
| `pre-cr run --json --workspace {repo_root}` | Changed-line/readiness gate | Every repo with `pre_cr` in `missing_gate_keys`. |
| `uv run python bin/aios.py --json prove-project-health --all-inventory` | Active inventory proof | Final portfolio closeout. |
| `pnpm context:validate` | Context compiler validation | Any AIOS config/truth update. |

## Architecture Patterns

### Pattern 1: Non-CI Gates Before CI

**What:** Fix and record every required non-`ci` gate for a repo before running its local `ci` proof.
**When to use:** Every in-scope repo.
**Source:** [VERIFIED: `scripts/linked-repo-ci-local-proof.py` behavior documented in `24-VERIFICATION.md`]

### Pattern 2: Failing Is Evidence, Passing Is Readiness

**What:** A failed gate run is useful evidence but never clears readiness. A repo becomes ready only from passing required gate runs.
**When to use:** Every plan.
**Source:** [VERIFIED: `services/linked_repo_readiness.py`]

### Pattern 3: Commands Stay AIOS-Owned

**What:** Change repo source/scripts to satisfy the configured command. Edit `config/quality-pipeline.json` only when the command is objectively wrong for the repo's canonical tooling.
**When to use:** Every remediation.
**Source:** [VERIFIED: `docs/audits/linked-repo-adoption-readiness-audit.md`]

### Pattern 4: Rubric Pack Before Remediation

**What:** Generate broad repo-class rubrics and gate-specific rubrics before writing implementation phases. Use broad rubrics for complexity/simplification, anti-slop/product quality, architecture, test value, UI visual/runtime verification, dead code, security/secret handling, dependency risk, truth/docs, and CI/local proof integrity. Materialize each rubric as audit and implementation Markdown plus JSON, then use `rubric-detail-manifest.json` as the agent entrypoint for GSD phase generation. TMCP expert context can enrich those rubrics only when the workflow records source sufficiency; otherwise continue with the AIOS standard rubric fallback.
**When to use:** Every sizable repo and every repo with broad quality-standard blockers.
**Source:** [VERIFIED: `repo_gate_adoption_v1` workflow contract]

### Pattern 5: Pilot Branch Before Workflow Execution

**What:** Create a new branch in the target linked repo before running remediation from generated adoption docs. The generated docs can live in git-ignored `AIOS-backfill/`, but any source, scripts, truth, or gate fixes belong on the pilot branch.
**When to use:** The `BidCamp`, `EliHealth`, and `pre-cr-suite-lsp` pilots, then every repo-specific remediation slice after the workflow is accepted.
**Source:** [VERIFIED: user request]

## Common Pitfalls

### Pitfall 1: Treating CI Exception As CI Pass
**What goes wrong:** A repo has exception metadata but no passing local `ci` run.
**How to avoid:** Always run `python3 scripts/linked-repo-quality-runner.py --project <repo> --gate ci` after non-`ci` gates pass.

### Pitfall 2: Hiding Real Failures Behind Config Edits
**What goes wrong:** A required gate is weakened to make the report green.
**How to avoid:** Do not remove required gates or downgrade blocking gates without a separate user-approved scope decision.

### Pitfall 3: Mixed Cross-Repo Commits
**What goes wrong:** Remediation across unrelated repos becomes impossible to review or roll back.
**How to avoid:** Commit atomically per repo or tightly coupled repo group; update AIOS truth after each committed slice.

### Pitfall 4: Treating Passing Commands As Broad Compliance
**What goes wrong:** Passing `anti_slop`, `architecture`, or tests is treated as proof that product quality, complexity, maintainability, or test value is acceptable.
**How to avoid:** Require the broad rubric audit pack before making a quality-standard compliance claim.

### Pitfall 5: Treating TMCP As Expert Without Source
**What goes wrong:** A TMCP packet with too few relevant source files is used as if it were gate expertise.
**How to avoid:** Require `tmcp-expert-enrichment.json` to show `enriched` before using TMCP-specific judgment; otherwise use the recorded `insufficient_source` fallback and continue with broad and gate-specific AIOS rubrics.

### Pitfall 6: Treating UI Code Checks As Visual Proof
**What goes wrong:** A UI repo passes lint/typecheck/tests or a TMCP UI rubric review, but no one confirms the actual rendered interface through local launch, browser/device automation, screenshots, computer use, Xcode simulator, or equivalent proof.
**How to avoid:** Require the UI visual/runtime verification rubric before claiming quality-standard compliance for web, mobile, or desktop UI surfaces.

### Pitfall 7: Treating Generic Generated Docs As Execution-Ready
**What goes wrong:** A generated rubric pack has the right files but still contains missing evidence, generic root causes, or absent validation details, then becomes a GSD implementation phase anyway.
**How to avoid:** Run `aios gate adoption-doc-quality --repo-root <repo> --run-id <run-id>` and resolve blockers before phase creation. Carry warnings as explicit audit work unless concrete evidence or accepted exceptions close them.

## Validation Architecture

### Test Framework

| Property | Value |
| --- | --- |
| Framework | Pytest for AIOS services; repo-native commands for linked repos |
| Config file | `config/quality-pipeline.json` |
| Quick run command | `uv run pytest -q tests/test_linked_repo_readiness.py tests/test_quality_pipeline.py` |
| Full suite command | `uv run pytest -q tests/test_quality_gates.py tests/test_commit_quality_ladder.py tests/test_tier_one_regressions.py tests/test_quality_pipeline.py tests/test_linked_repo_readiness.py && pnpm context:validate` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
| --- | --- | --- | --- | --- |
| Phase goal | All 23 in-scope repos become ready | integration | `python3 scripts/linked-repo-quality-runner.py --report` | yes |
| Phase goal | No required gate config is missing | unit | `uv run pytest -q tests/test_linked_repo_readiness.py::test_phase24_real_config_has_commands_for_every_required_gate` | yes |
| Phase goal | Inventory proof remains clean | integration | `uv run python bin/aios.py --json prove-project-health --all-inventory` | yes |

### Sampling Rate

- **Per repo slice:** Run affected gates through `scripts/linked-repo-quality-runner.py`.
- **Per wave:** Run `python3 scripts/linked-repo-quality-runner.py --report` and the quick AIOS test command.
- **Phase gate:** Full suite, readiness report, and copied/live all-inventory proof.

### Wave 0 Gaps

None. Required gate commands are configured for all 23 in-scope repos. `BidCamp`, `tenure`, and `EliHealth` now have first recorded evidence and need remediation of failing gates before their blocked verdicts can clear.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
| --- | --- | --- |
| V4 Access Control | yes | Preserve repo-specific Pre-CR and architecture gates. |
| V5 Input Validation | yes | Keep class validation gates blocking for data/content repos. |
| V6 Cryptography | yes | Keep secret scans blocking where configured. |
| V14 Configuration | yes | Keep dependency/security gates blocking where configured. |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
| --- | --- | --- |
| Gate weakening | Tampering | Do not remove required gates; preserve class contracts. |
| False readiness claim | Repudiation | Require recorded `quality_pipeline_runs` pass evidence. |
| Secret leakage during scan | Information Disclosure | Use configured secret scans; do not paste secrets into docs. |
| Dependency vulnerability ignored | Elevation of Privilege | Keep dependency security gates blocking until passing. |

## Open Questions (RESOLVED)

1. **Include excluded repos?** RESOLVED: No. Scope is the 23 in-scope repos.
2. **Require remote CI?** RESOLVED: No. Local CI replacement proof is accepted.
3. **Execution order?** RESOLVED: Easiest-first by current blocker count.
4. **Which repos quality-test the workflow?** RESOLVED: `BidCamp`, `EliHealth`, then `pre-cr-suite-lsp`, each on a new target-repo branch.

## Sources

### Primary (HIGH confidence)

- `29-IMPLEMENTATION.md` - phase seed plan and user-selected scope.
- `24-VERIFICATION.md` - current failure ledger and Phase 24 closeout rules.
- `config/quality-pipeline.json` - class-required gate authority.
- `services/linked_repo_readiness.py` - readiness verdict logic.
- `scripts/linked-repo-quality-runner.py` - evidence runner contract.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - existing AIOS tools already implement the gate model.
- Architecture: HIGH - ownership boundaries were settled in Phase 24.
- Pitfalls: HIGH - derived from current failure ledger.

**Research date:** 2026-06-24
**Valid until:** Current until `config/quality-pipeline.json` or Phase 24 scope changes.
