# Phase 29 Parked Implementation Plan: Linked Repo AIOS Adoption Readiness Remediation

Status: parked, not started
Created: 2026-06-24
Scope: current 23 in-scope repositories: the 20 Phase 24 targets plus `BidCamp`, `tenure`, and `EliHealth`
Excluded: `agent-router`, `video-pipeline`, `manga-sync`
CI policy: local CI replacement proof
Order: easiest first

## Summary

Make the current in-scope portfolio adoption-ready: 23 repos, local CI proof accepted, easiest-first order. Keep `agent-router`, `video-pipeline`, and `manga-sync` excluded unless separately reactivated.

Current baseline:

- `ready_count: 0`
- `blocked_count: 23`
- `evidence_required_count: 0`
- `adoption_ready_count: 0`
- `adopted_but_blocked_count: 23`
- `not_adopted_count: 0`
- `excluded_count: 3`
- No missing required gate configs remain.
- Remaining blockers are failing required gates and missing passing local CI evidence.
- Newly added `BidCamp`, `tenure`, and `EliHealth` have first evidence rows recorded and remain blocked until failing required gates pass.
- Fresh baseline artifacts: `29-BASELINE.json` and `29-BASELINE.md`.

Adoption-ready means:

- `python3 scripts/linked-repo-quality-runner.py --report` shows each in-scope repo with `missing_gate_keys: []`.
- Each repo has a passing recorded `ci` run through local CI replacement proof.
- `ready_count: 23`, `blocked_count: 0`, `evidence_required_count: 0`, `excluded_count: 3`.
- `adoption_ready_count: 23`, `adopted_but_blocked_count: 0`, `not_adopted_count: 0`.
- Each in-scope repo's `quality_certification.stage_statuses` shows `aios_wired: pass`, `quality_standard_compliant: pass`, and `release_ready: pass`.
- Each in-scope repo's `quality_certification.required_subworkflow` is `repo_gate_adoption_v1` or an explicitly approved successor recorded in `config/quality-pipeline.json`.
- AIOS truth, audit, and Phase verification ledgers match the report.

## Key Changes

- Track this as the next GSD remediation phase after the current completed phase.
- For each repo, collect configured gate evidence first, generate the repo-class broad rubric pack and gate-specific rubric pack, then plan remediation from the combined audits.
- Require the generated adoption pack to carry repo classification evidence, selected AIOS quality-pipeline profile context, configured command proof, visual-proof route when applicable, and a passing document-quality structure check before it becomes phase input.
- Treat TMCP expert enrichment as conditional: use it when `repo_gate_adoption_v1` records `enriched`, and rely on AIOS standard rubrics when it records `insufficient_source`.
- Keep generated adoption docs in the target repo's git-ignored `AIOS-backfill/gate-adoption/{run_id}` folder; do not write rubric packs into tracked repo docs folders.
- For UI-bearing repos, require visual/runtime confirmation with local launch plus browser/device automation, screenshots, computer use, Xcode simulator, or equivalent platform proof; UI lint/typecheck/component tests and TMCP UI rubric review are not enough by themselves.
- For each repo, fix required gates in this order after rubric planning: non-`ci` gates first, then local `ci`, then final readiness report.
- Keep all executable gate commands AIOS-owned in `config/quality-pipeline.json`; repo-local files only change when needed to make real gates pass.
- Use atomic commits per repo or tightly coupled repo group, followed by AIOS truth/audit updates.
- Treat dirty trees as final hygiene only after gate evidence is passing.
- Passing command gates are not sufficient by themselves: passing `anti_slop` does not prove broad anti-slop/product-quality compliance, passing `architecture` does not prove complexity or maintainability compliance, and passing UI static checks does not prove the rendered interface is visually correct.

## Workflow Pilot Order

Before using the adoption-document workflow across the full portfolio, run three branch-isolated pilots:

1. `BidCamp` on branch `codex/phase-29-bidcamp-adoption-pilot`
   - Purpose: dense production-web pilot with UI visual proof, architecture, dependency/security, Pre-CR, anti-slop, and local CI surfaces.
   - Minimum output: adoption docs under `AIOS-backfill/gate-adoption/{run_id}`, `adoption-doc-quality` report, one GSD phase generated from the combined broad and gate-specific audit pack, and a post-phase gate evidence rerun.

2. `EliHealth` on branch `codex/phase-29-elihealth-adoption-pilot`
   - Purpose: mobile/native pilot for Xcode or simulator-backed visual/runtime proof, mobile release validation, native build/test repair, and local CI replacement proof.
   - Minimum output: adoption docs under `AIOS-backfill/gate-adoption/{run_id}`, `adoption-doc-quality` report, one GSD phase generated from the combined broad and gate-specific audit pack, and a post-phase gate evidence rerun.

3. `pre-cr-suite-lsp` on branch `codex/phase-29-pre-cr-suite-lsp-adoption-pilot`
   - Purpose: non-UI developer-tool pilot that validates package/tool classification, `no_ui_exception`, architecture/dependency-security remediation planning, and local CI replacement proof without a rendered UI path.
   - Minimum output: adoption docs under `AIOS-backfill/gate-adoption/{run_id}`, `adoption-doc-quality` report, one GSD phase generated from the combined broad and gate-specific audit pack, and a post-phase gate evidence rerun.

Each pilot branch must be created in the target linked repo before running remediation. AIOS evidence and Phase 29 docs may be updated in this repo after each pilot, but target repo source fixes must stay on the pilot branch until reviewed.

## Artifact-Driven Pilot Remediation Plans

The three pilot repos now have final post-setup adoption-doc-quality passes and dedicated repo-local execution phases:

- `BidCamp` phases `151` through `155`, sourced from `/Users/jakyeamos/projects/BidCamp/AIOS-backfill/gate-adoption/phase29-bidcamp-pilot-final-doc-pass-001`
- `EliHealth` phases `09` through `13`, sourced from `/Users/jakyeamos/EliHealth/AIOS-backfill/gate-adoption/phase29-elihealth-pilot-final-doc-pass-001`
- `pre-cr-suite-lsp` phases `04` through `06`, sourced from `/Users/jakyeamos/projects/pre-cr-suite-lsp/AIOS-backfill/gate-adoption/phase29-pre-cr-suite-lsp-pilot-final-doc-pass-001`

These repo-local phases are the next execution surface for the pilot repos. They convert broad rubric docs, gate-specific docs, and real command failures into scoped remediation work inside the owning repository before the broader portfolio waves claim readiness. AIOS Phase 29 remains the portfolio coordination layer; it does not own per-repo implementation phases.

## Execution Order

1. Smallest blocker sets first:
   - `portfolio`: `ci`, `pre_cr`
   - `R-Project`: `lint`, `ci`, `pre_cr`
   - `career-ops`: `ci`, `pre_cr`, `validation`
   - `claude-improvement-lab`: `ci`, `dependency_security`, `pre_cr`
   - `csds391-s26-6`: `lint`, `ci`, `pre_cr`
   - `pre-cr-suite-lsp`: `architecture`, `ci`, `dependency_security`
   - `BBDSE`: `ci`, `pre_cr`, `validation`

2. Medium blocker sets:
   - `LIS`: `lint`, `test`, `ci`, `dependency_security`
   - `eslint-plugin-anti-slop`: `lint`, `typecheck`, `architecture`, `ci`
   - `tm`: `architecture`, `ci`, `dependency_security`, `pre_cr`
   - `Bballedu`: `architecture`, `ci`, `dependency_security`, `e2e_smoke`, `pre_cr`
   - `Dsci-proj`: `lint`, `test`, `ci`, `dependency_security`, `pre_cr`
   - `Fantasy`: `lint`, `test`, `ci`, `dependency_security`, `validation`
   - `Terrace`: `test`, `architecture`, `ci`, `dependency_security`, `pre_cr`
   - `Vaults`: `architecture`, `ci`, `secret_scan`, `pre_cr`, `validation`
   - `aios`: `install`, `test`, `architecture`, `ci`, `pre_cr`
   - `dispatches-from-cyberspace`: `typecheck`, `architecture`, `ci`, `dependency_security`, `pre_cr`

3. Largest blocker sets:
   - `BidCamp`: first evidence for production public web app gates plus repo-local AIOS and Pre-CR contract setup
   - `tenure`: first evidence for production public web app gates plus repo-local AIOS contract proof
   - `EliHealth`: first evidence for mobile app gates plus repo-local AIOS and Pre-CR contract setup
   - `amos-saas`: `lint`, `typecheck`, `build`, `architecture`, `ci`, `dependency_security`, `pre_cr`
   - `soundscape-app`: `lint`, `typecheck`, `test`, `ci`, `secret_scan`, `dependency_security`, `e2e_smoke`, `pre_cr`
   - `remodelvision`: `lint`, `typecheck`, `test`, `build`, `architecture`, `ci`, `secret_scan`, `dependency_security`, `e2e_smoke`, `pre_cr`

4. Final closeout:
   - Run `python3 scripts/linked-repo-quality-runner.py --report`.
   - Run copied and live `prove-project-health --all-inventory`.
   - Update Phase verification, linked-repo audit, and `PROJECT.md`.
   - Record remaining excluded repos with no readiness claim.

## Test Plan

For every repo:

- Run each failing gate directly through `python3 scripts/linked-repo-quality-runner.py --project <repo> --gate <gate>`.
- Generate or refresh `repo_gate_adoption_v1` artifacts under `AIOS-backfill/gate-adoption/{run_id}`, including `tmcp-expert-enrichment.json`, `rubric-pack.json`, `rubric-pack.md`, `rubric-detail-manifest.json`, and per-rubric audit/implementation Markdown plus JSON docs.
- Run `uv run python bin/aios.py gate adoption-doc-quality --repo-root <repo> --run-id <run-id>` and resolve blocker findings before using the generated docs as GSD phase input.
- Confirm the adoption pack records the repo classification, selected AIOS quality-pipeline profile, required profile gates, configured commands, strict-readiness blockers, and local CI exception metadata where applicable.
- Confirm TMCP enrichment is either `enriched` with cited packet context or `insufficient_source` with `aios_standard_rubric` fallback before using rubric conclusions.
- Use the generated per-rubric audit and implementation docs as phase inputs instead of planning from the top-level rubric pack alone.
- For web/mobile/desktop UI repos, record visual proof evidence from the real launch path before claiming quality-standard compliance.
- Write rubric-level audit/implementation docs before execution phases, covering blockers, root causes, affected files/scripts, validation commands, risk, and accepted exceptions.
- After non-`ci` gates pass, run `python3 scripts/linked-repo-quality-runner.py --project <repo> --gate ci`.
- Confirm the repo disappears from `missing_gate_keys` and its certification stages all pass.

Portfolio checks:

- `python3 scripts/linked-repo-quality-runner.py --report`
- `uv run pytest -q tests/test_linked_repo_readiness.py tests/test_quality_pipeline.py`
- `uv run pytest -q tests/test_quality_gates.py tests/test_commit_quality_ladder.py tests/test_tier_one_regressions.py`
- `pnpm context:validate`
- `uv run python bin/aios.py --json prove-project-health --all-inventory`

Acceptance checks:

- `ready_count: 23`
- `blocked_count: 0`
- `evidence_required_count: 0`
- `adoption_ready_count: 23`
- `adopted_but_blocked_count: 0`
- `not_adopted_count: 0`
- `excluded_count: 3`
- no in-scope repo has non-empty `missing_gate_keys`
- no in-scope repo has a failing `quality_certification.stage_statuses` value
- no missing-source or inactive-row contamination in all-inventory proof

## Assumptions

- Scope is the current 23 in-scope repos only.
- `agent-router`, `video-pipeline`, and `manga-sync` remain excluded.
- Local CI replacement proof is the CI standard for this remediation because GitHub Actions credits are constrained.
- Failing gates must be fixed; missing gate setup is already complete.
- Dirty tree cleanup happens after gate pass evidence, not before.
