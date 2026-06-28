---
schemaVersion: 1
projectName: AIOS
summary: Active local-first agent operating system with durable eval-run recording, context-loop learning primitives, TMCP expertise compilation, repo gate adoption planning, standalone Quality Runner consumption boundary, a fully triaged Codex/Claude session-intelligence backlog, and six review-gated session-intelligence tool surfaces while broader Ruff and BasedPyright baseline issues remain open.
healthScore: 73
statusLabel: needs_attention
nextStep: Use the new review-gated session-intelligence tool surfaces in live Codex sessions and decide whether `aios repo inspect` should absorb more CTS/context evidence.
blockers:
  - Full repo Ruff and format baselines are not green: Ruff reports 25 issues and Ruff format reports 169 files needing formatting.
  - Full repo BasedPyright is not green: 110 errors and 78 warnings, including the existing `services/aios_cli.py` `run_cli` complexity baseline.
  - `uv run vulture . --min-confidence 70` scans `.venv` and fails on third-party package findings; project-scoped `uv run vulture bin services --min-confidence 70` passes.
lastUpdated: 2026-06-28
tags: [infra, ai-os, hooks, automation]
areas: [engineering]
goals: []
repoType: infra
sourceOfTruth: mixed
primaryLanguage: Python
activeBranch: codex/project-aios-component-scope
lastCommitDate: 2026-06-28
quality:
  lint: fail
  types: fail
  tests: pass
  deadCode: warning
  structure: fail
canonicalCommands:
  install: uv sync
  dev: unknown
  lint: ruff check .
  typecheck: basedpyright
  test: uv run pytest -q
  deadcode: vulture . --min-confidence 70
agentExpectationsVersion: 1
---

## Current State

AIOS is an active, git-versioned Python/shell infrastructure project (first commit 2026-04-01, latest normalization commits on 2026-04-12). It runs continuously as the backbone of all Claude Code sessions: lifecycle hooks fire on session start, stop, prompt submit, and tool events, writing structured data to a SQLite ops database at `~/AIOS/data/aios.db`.

The codebase is large, with Python services and scripts in `services/` and `bin/`, a committed `aios-ui/` Next.js command-center app, schema-backed operational storage, growing context/planning docs, and explicit Python quality configuration in `pyproject.toml`. The Code Topology Service (CTS) backend is committed: `services/cts/` provides graph storage, parsing, search, impact analysis, incremental updates, and MCP/CLI entrypoints. Phase 11 eval-run infrastructure is now coherent end to end: `schema.sql` defines eval task/run/score/failure tables, `services/eval_run_service.py` creates and reads durable eval records, and `services/aios_cli.py` exposes `aios eval record-run`, `list-runs`, and `summary`. The latest full Python quality pass on 2026-06-25 shows repo-level Ruff and BasedPyright failures outside the user commit gate visibility slice, while targeted hook-policy checks pass.

AIOS now also has a file-backed and SQLite-backed context-loop learning primitive: `services/context_loops.py`, `schema.sql`, and `python bin/aios.py context-loops ...` record inner-loop context/draft runs, review events, learning candidates, explicit approvals/rejections, approved lesson application, metrics, and a draft-only email pilot. Contract docs and examples live under `aios/context-loops/`.

AIOS now has `expert_rubric_remediation_v1` implemented and smoke-verified through the core artifact service, workflow runtime dispatch, active workflow/skill registry contracts, route scoring, and `aios tmcp review-plan`. The workflow compiles TMCP expertise into an explicit rubric, audits concrete evidence, produces ordered remediation slices, and writes an approval-gated implementation handoff without executing implementation.

AIOS also has `repo_gate_adoption_v1`, a narrow audit-and-plan workflow for repository quality-gate adoption. It scans repo-local scripts, Pre-CR, anti-slop, local AIOS quality contracts, CI, hooks, dead-code, structural-scan, and truth-file evidence; produces a core gate readiness matrix; conditionally records TMCP expert enrichment only when source sufficiency passes; writes broad repo-class and gate-specific rubric packs; writes a staged rollout plan under git-ignored `AIOS-backfill/gate-adoption/{run_id}`; and exposes the flow through `aios gate adoption-plan`.

Quality Runner now lives in `/Users/jakyeamos/quality-runner` as a standalone audit-and-plan package with CLI and MCP surfaces. AIOS should consume it as an external tool and may provide adapters, standards profiles, or workflow shortcuts, but the standalone package owns the core workflow and `.quality-runner/` artifact contract.

AIOS now has a review-gated Codex/Claude Session Intelligence loop. The loop enriches Codex session normalization with tool calls, commands, cwd, approval friction, errors, and terminal outcomes; stores lane candidates in SQLite; emits redacted Markdown/JSON reports; exposes `aios session-intel` commands; runs daily through the Codex automation `daily-codex-session-intelligence`; and supports resumable historical backfill across Codex and Claude sources.

Repo quality certification now lives in the standalone repository `/Users/jakyeamos/repo-quality-certifier`, with remote `git@github.com:jakyeamos/repo-quality-certifier.git`. That repo owns deterministic repo scanning, gate matrix synthesis, broad and gate-specific rubrics, rollout phase generation, document-quality evaluation, artifact writing, CLI/MCP/plugin surfaces, tests, and its own Pre-CR config. AIOS consumes it through a local path dependency and keeps a thin `services/repo_gate_adoption.py` adapter that injects AIOS TMCP enrichment and preserves existing workflow/CLI imports.

Shared quality evidence/finding normalization now lives in the standalone repository `/Users/jakyeamos/quality-evidence-contract`, with remote `git@github.com:jakyeamos/quality-evidence-contract.git`. The success-criteria evaluator remains AIOS-owned because registry policy, SQLite writes, and artifact lifecycle are still product-integrated, but stage/evaluation findings now carry an additive nested `quality_contract` payload for portable consumers.

Context compiler contract validation now lives in the standalone repository `/Users/jakyeamos/context-compiler-contract`, with remote `git@github.com:jakyeamos/context-compiler-contract.git`. AIOS consumes it through a local file dependency, while `tools/context-compile.mjs` remains AIOS-owned until context-root and routing assumptions are external-fixture backed.

AIOS now has a strict subsystem ownership map in `.planning/SUBSYSTEM_EXTRACTION_PLAN.md`. The map classifies major surfaces as `core_aios`, `adapter_inside_aios`, `contract_package`, `standalone_tool`, or `incubator_candidate`. The current scope truth is that AIOS is better scoped after extracting `repo-quality-certifier`, `quality-evidence-contract`, `context-compiler-contract`, and the Research Domain Writing standalone tool, but it still contains incubator candidates that need future boundary decisions, including CTS, agent/eval harness pieces, personalized humanizer, benchmark tooling, and quality/standards consolidation surfaces.

The three extracted repos now have release governance and pushed `v0.1.0` tags. `repo-quality-certifier` release governance is at commit `3ff7eb4`, `quality-evidence-contract` at `36c94bc`, and `context-compiler-contract` at `de60ba1`. AIOS still uses local path/file dependencies for active development; the remaining release-boundary decision is whether to switch those dependencies to tagged Git refs.

Research Domain Writing now lives in the standalone repository `/Users/jakyeamos/research-domain-writing`, with remote `git@github.com:jakyeamos/research-domain-writing.git` and pushed tag `v0.1.0` at commit `ba0f608`. AIOS no longer owns RDW prompts, domain packs, examples, installers, packet validation, or release process; local slash commands and agent skills point at the external repo.

## Why This Matters / Intended Outcome

AIOS is not an app — it is the operating layer for all AI-assisted development work across every project. Hook correctness and DB integrity are load-bearing. Breakage here silently degrades all Claude Code sessions. The ops database is the canonical store for sessions, prompts, artifacts, patterns, bug logs, and next-action candidates across all projects.

## Recent Progress

- 2026-06-25: Added an AIOS quality-pipeline `anti_slop` adoption/backfill gate for platform, production public web app, and developer-tool package repos, with audit-mode linked-repo commands and readiness regression coverage.
- 2026-06-26: Linked-repo adoption reports now require quality certification through `repo_gate_adoption_v1`, separating `aios_wired`, `quality_standard_compliant`, and `release_ready` stages from final `adoption_ready`, `adopted_but_blocked`, or `not_adopted` status.
- 2026-06-26: Completed Phase 29 pre-execution prep by refreshing the linked-repo adoption baseline, documenting first-wave repo branch/dirty state, and updating Phase 29 acceptance criteria to require `adoption_ready` plus passing certification stages.
- 2026-06-26: Added `BidCamp`, `tenure`, and `EliHealth` to the linked-repo adoption list, expanding Phase 29 to 23 in-scope repos; first evidence rows are recorded and the new repos are AIOS-wired but blocked until failing required gates pass.
- 2026-06-26: Upgraded `repo_gate_adoption_v1` to generate broad and gate-specific rubric packs before rollout planning, preventing sizable repo adoption from being scoped only by failed command gates.
- 2026-06-26: Wired conditional TMCP expert enrichment into `repo_gate_adoption_v1`; adoption artifacts now record `enriched` only when relevant TMCP source sufficiency passes, otherwise `insufficient_source` with AIOS standard rubric fallback.
- 2026-06-26: Added a UI visual/runtime verification broad rubric to `repo_gate_adoption_v1`, requiring rendered proof through local launch, browser/device automation, screenshots, computer use, Xcode simulator, or equivalent evidence for UI-bearing repos.
- 2026-06-26: Extended `repo_gate_adoption_v1` to materialize per-rubric audit and implementation docs in both Markdown and JSON, plus `rubric-detail-manifest.json` for agent-readable GSD phase inputs.
- 2026-06-26: Extended `repo_gate_adoption_v1` generated docs with repo classification evidence, selected AIOS quality-pipeline profile context, required profile gates, configured command metadata, strict-readiness blockers, and UI visual-proof routing.
- 2026-06-26: Added `aios gate adoption-doc-quality`, which generates adoption docs and writes `adoption-doc-quality.json` / `.md` so agents can fail structurally invalid docs and carry explicit phase-readiness fields before execution planning.
- 2026-06-26: Strengthened adoption-doc generation so broad and gate-specific rubric docs include scan-derived evidence, evidence-of-absence findings, missing-proof blockers, non-generic root causes, likely affected files/scripts, accepted-exception status, and validation commands.
- 2026-06-26: BidCamp Phase 29 workflow-quality pilot `phase29-bidcamp-pilot-008` passes adoption doc quality with `status=pass`, `warning_count=0`, `ready_for_phase_planning=true`, and `ready_for_execution=true`; gate summary now distinguishes `present=14`, `enforceable=13`, `absent=7`, and `skipped=2`, with `local_quality_contract` treated as required setup rather than a skip.
- 2026-06-26: Set Phase 29 workflow-quality pilots to `BidCamp`, `EliHealth`, and `pre-cr-suite-lsp`, each on a new target-repo branch, so the adoption-doc workflow is tested against dense web, mobile/native, and non-UI developer-tool repos before portfolio-wide rollout.
- 2026-06-26: Set up and pushed repo-local adoption gates in the three Phase 29 pilot repos: `BidCamp` commit `145b6bd0` with run `phase29-bidcamp-pilot-setup-002`, `EliHealth` commit `30b9d4d` with run `phase29-elihealth-pilot-setup-002`, and `pre-cr-suite-lsp` commit `cfc8afd` with run `phase29-pre-cr-suite-lsp-pilot-setup-002`. All three latest adoption-doc-quality runs pass with `warning_count=0`, `absent=0`, and `local_quality_contract` present; only repo-class skips remain.
- 2026-06-26: Corrected Phase 29 pilot planning so gate-scoped remediation lives inside the owning repos: `BidCamp` phases `151`-`155`, `EliHealth` phases `09`-`13`, and `pre-cr-suite-lsp` phases `04`-`06`.
- 2026-06-26: Hardened `repo_gate_adoption_v1` so generated rollout plans now require repo-local gate-scoped phases, target-repo ownership, per-gate phase templates by default, final certification, and explicit cluster rationale before any multi-gate phase can pass validation.
- 2026-06-26: Tightened `repo_gate_adoption_v1` strict clearance semantics so inherited full lint/test failures become repo-local remediation targets; focused checks are interim proof only, and final certification cannot mark a repo `adoption_ready` while full lint or full tests fail from an inherited baseline.
- 2026-06-26: Expanded `repo_gate_adoption_v1` tier-one certification to fifteen broad rubrics and first-class gate rows where actionable, adding build/package integrity, runtime smoke, release/rollback readiness, data/state integrity, and observability/debuggability while preserving existing lint, tests, security, dependency, architecture, anti-slop, dead-code, truth, CI/local proof, and UI runtime requirements.
- 2026-06-26: Strengthened the complexity/simplification rubric so thermo/simplifier skills are treated as expert audit input rather than full proof; certification now requires hotspots, implementation phases, runtime/product/architecture/over-abstraction review, verification commands, and exception rationale/expiry.
- 2026-06-26: Split repo quality certification into the standalone `repo_quality_certifier` package boundary while keeping AIOS as the workflow adapter/orchestrator; focused contract tests prove standalone import does not load `services.tmcp_runtime` and non-AIOS callers receive valid TMCP fallback output.
- 2026-06-26: Promoted `repo_quality_certifier` to repo-ready extraction posture by adding standalone CLI, MCP-shaped stdio/JSON-RPC tool handlers, plugin manifest/skill artifacts, package-data metadata, and external fixture tests for plan/doc-quality execution.
- 2026-06-26: Physically extracted repo quality certification into `/Users/jakyeamos/repo-quality-certifier`, pushed remote `git@github.com:jakyeamos/repo-quality-certifier.git`, and wired AIOS to consume `repo-quality-certifier @ file:///Users/jakyeamos/repo-quality-certifier`; the external repo has initial commits `dd5c00f` and `dab399f`, and AIOS focused adapter tests pass with the in-tree package removed.
- 2026-06-26: Extracted `quality_evidence_contract` for portable quality evidence/finding schemas, normalization, validation, and counts; `services.success_criteria` now adds `quality_contract` to stage and evaluation finding payloads without changing legacy fields.
- 2026-06-26: Physically extracted quality evidence contracts into `/Users/jakyeamos/quality-evidence-contract`, pushed remote `git@github.com:jakyeamos/quality-evidence-contract.git`, and wired AIOS to consume `quality-evidence-contract @ file:///Users/jakyeamos/quality-evidence-contract`; initial commit `5bb3b85` passes external Ruff, BasedPyright, pytest, and Pre-CR, and AIOS success-criteria integration tests pass with the in-tree package removed.
- 2026-06-26: Updated `bin/aios.py` to re-enter the project virtualenv before importing service modules, restoring plain `python3 bin/aios.py ...` command paths after local packages moved to path dependencies.
- 2026-06-26: Extracted `context_compiler_contract` for compiled context result/receipt validation and wired the live context compiler regression test through that contract.
- 2026-06-26: Physically extracted context compiler contracts into `/Users/jakyeamos/context-compiler-contract`, pushed remote `git@github.com:jakyeamos/context-compiler-contract.git`, and wired AIOS to consume `context-compiler-contract` through a local file dependency; initial commit `e8c6e90` passes standalone package tests, syntax check, and Pre-CR, and AIOS context compiler regression tests pass with the in-tree contract removed.
- 2026-06-26: Added a strict subsystem ownership map to `.planning/SUBSYSTEM_EXTRACTION_PLAN.md`, classifying core AIOS surfaces, AIOS adapters, extracted contract packages, standalone tool candidates, and incubator candidates before any further repo splits.
- 2026-06-26: Added `CHANGELOG.md`, `RELEASE.md`, release validation checklists, Pre-CR doc ignores, and pushed annotated `v0.1.0` tags for `repo-quality-certifier`, `quality-evidence-contract`, and `context-compiler-contract`.
- 2026-06-26: Audited `research-domain-writing/` and classified it as a standalone tool to extract after a narrow hardening pass, with AIOS retaining only skill/tool consumption and future adapter hooks.
- 2026-06-26: Extracted Research Domain Writing into `/Users/jakyeamos/research-domain-writing`, created private remote `jakyeamos/research-domain-writing`, pushed `main`, tagged `v0.1.0`, and repointed local Claude/Cursor/Codex skill installs to the standalone repo.
- 2026-06-27: Added the review-ready Quality Runner design spec for a standalone audit-and-plan engine with CLI and MCP surfaces, shared core package, pluggable adapters, `.quality-runner/` artifacts, and explicit v1 non-execution boundaries.
- 2026-06-27: Added the Quality Runner implementation plan for a Python-first standalone package at `/Users/jakyeamos/quality-runner`, covering scaffold, core contracts, discovery, standards, audit planning, CLI, MCP, plugin metadata, quality checks, and AIOS adoption notes.
- 2026-06-28: Built Quality Runner as the standalone repository `/Users/jakyeamos/quality-runner` with audit-and-plan core contracts, discovery/standards/capability detection, remediation planning, `.quality-runner/runs/<run-id>/` artifacts, CLI commands, MCP tools, plugin metadata, packaging checks, and explicit v1 non-execution boundaries.
- 2026-06-28: Added the Codex Session Intelligence loop with enriched Codex JSONL normalization, review-gated `friction_tool`, `workflow_skill`, and `impact_idea` candidates, redacted daily reports, `aios session-intel` CLI commands, and the daily Codex automation `daily-codex-session-intelligence`.
- 2026-06-28: Added resumable `aios session-intel backfill` mode for historical Codex and Claude sessions, with provider `all`, batch sizing, cursor-based resume, optional reports, and review-gated candidate storage only.
- 2026-06-28: Ran the first full local Codex/Claude session-intelligence backfill and hardened it into a tier-one workflow by fixing session-intel CLI commit durability, Claude Bash/tool-result normalization, and cross-batch candidate merging; the live DB now has 1,923 cursors, 973 pending candidates, and zero duplicate lane/title groups.
- 2026-06-28: Added `aios session-intel clusters` as a compact triage queue, intent-level friction grouping, review-event recording, and successful command-sequence workflow mining; the live pending queue now rolls up into 621 clusters, with top clusters for repo state inspection, git history review, git commit/publish, reusable workflow, and tool execution.
- 2026-06-28: Completed the first conservative top-cluster triage pass in `aios.db`: approved 7 representative candidates, superseded 321 redundant exact-command variants, observed 18 broad/low-certainty items, rejected 11 project-specific one-offs, and left 616 friction candidates pending review.
- 2026-06-28: Completed the remaining session-intelligence candidate triage. The candidate table now has zero pending rows: 10 approved candidate rows, 783 superseded variants, 47 observed items, and 134 rejected one-offs; a backup was written to `data/aios.db.pre-session-intel-full-triage-20260628`.
- 2026-06-28: Promoted the 10 approved session-intelligence representatives into six review-gated deterministic tool surfaces: `aios repo inspect`, `aios quality ladder`, `aios ship guard`, `aios service probe`, `aios workflow-skill codex`, and `aios planning state`.
- 2026-06-28: Strengthened the user commit quality gate so low-value static UI copy tests require documented behavior value, and long Pre-CR runs emit visible heartbeat/start/finish progress.
- 2026-06-28: Wired AIOS context compiler tests to consume the standalone `context-compiler-contract` package through the project `package.json` and `pnpm-lock.yaml`.
- 2026-06-28: Wired AIOS Python dependency metadata to consume the extracted `quality-evidence-contract` and `repo-quality-certifier` packages while recording dev quality tools in `uv.lock`.
- 2026-06-28: Integrated `quality-evidence-contract` into success-criteria findings so stage and evaluation findings carry a portable nested `quality_contract` payload alongside legacy fields.
- 2026-06-28: Added ignore rules for generated AIOS DB backups, session-intelligence reports, `AIOS-backfill/`, and Node dependency folders so local operational artifacts do not enter source commits.
- 2026-04-08: Added ops/maintenance utilities, retrieval rule and provenance tooling, enriched hook event capture, AI history import tooling
- 2026-04-08: Design specs added for Code Topology Service (CTS), AIOS Command UI, and prompt library
- 2026-04-09: Ruff 0.15.10 auto-fixed 181 issues; shellcheck clean on `auto_ingest.sh` and `health_check.sh`; BasedPyright and Vulture installed
- 2026-04-12: Committed `pyproject.toml` and a broad low-risk script cleanup pass (UTC datetime normalization, unused import cleanup, small lint-oriented simplifications)
- 2026-04-12: Committed the CTS backend (`services/cts/`), CTS CLI entrypoints, local CTS graph-store rules, and session-start CTS context integration
- 2026-04-12: Committed the `aios-ui/` command-center app scaffold; `npm run lint` passes with 5 anti-slop warnings and no errors
- 2026-04-12: Committed `bin/aios-query.py` and `bin/token-audit.py`; targeted `ruff check` and `python3 -m compileall` pass on both files
- 2026-04-12: Committed the anti-slop ESLint design spec; AIOS returned to a clean committed working tree
- 2026-04-27: Added persisted per-project AIOS component scope controls to the command-center project surface, including a dropdown selector and UI suppression for disabled sections
- 2026-04-28: Verified and corrected latest UI/backend handoff gaps: literal-newline hook JSON recovery now has regression coverage, UI lint errors were removed, focused Python tests pass, and the Next.js production build passes after rebuilding `better-sqlite3` for the active Node ABI
- 2026-05-20: Committed Phase 7 (delta scoring and health backfill) plans 07-01, 07-02, 07-03 covering DELT-01..DELT-04 — registry extension to 10 DELT-01 domains, explainable DeltaExplanation projection with four-state provenance (confirmed/inferred/missing/contradictory), and workflow-from-health recommender with CLI + UI surfaces.
- 2026-06-22: Tightened Phase 11 eval-run recording so runs cannot be recorded for missing tasks, eval summaries count runs once when multiple score rows exist, and CLI JSON errors surface missing-task failures consistently.
- 2026-06-22: Evolved the user commit quality gate's oversized-source rule to distinguish production source, scripts, tests, and generated files, with focused regression coverage.
- 2026-06-23: Added `.aios/audit/` gate audit events, summaries, and learning lessons for AIOS ladder and portable commit-gate findings, with protected branches/dev environments blocking and unprotected feature branches warning.
- 2026-06-23: Added context-loop learning records and artifacts for inner-loop context capture, outer-loop review diffing, approval-gated lessons, metrics, and local draft-only email pilot behavior.
- 2026-06-23: Upgraded TMCP toward graph-backed default skill composition with a tracked canonical graph profile, harvest-emitted `skills.tmcp/graph.json`, runtime source-skill scoring, fallback warnings, and receipt-promoted shortcut materialization.
- 2026-06-23: Advanced TMCP tier-one readiness by planning the remaining managed-run default adoption blocker in Phase 20 Plan 20-07, refreshing the local 99-skill graph metadata, adding graph verification/repair, source-hash shortcut freshness, overlay behavior gating, and an explicit tier-one candidate contract.
- 2026-06-23: Reframed TMCP as a behavior-atom skill compiler with graph token/utility metadata, behavior-diff packet optimization, source-skill section excerpts, negative selection evidence, node usefulness and omitted-requirement receipt fields, and richer shortcut compiled-packet metadata.
- 2026-06-23: Added TMCP behavior-atom and golden-prompt registries, semantic source-skill extraction, receipt feedback and missed-requirement repair summaries, node/atom token ROI learning summaries, `aios tmcp` inspect/feedback CLI commands, and a `tmcp_behavior_optimized` benchmark condition.
- 2026-06-23: Added TMCP packet-adherence evaluation, granular receipt/intervention events, phase-aware and domain-aware packet compilation, negative precision fixtures, packet diffing, shortcut governance recommendations, and benchmark claim gating for quality/token/missed-requirement discipline.
- 2026-06-24: Added an AIOS agent rule requiring proactive strategic improvement suggestions when a more durable path is visible than the tactical request.
- 2026-06-24: Added the review-ready `expert_rubric_remediation_v1` design spec for turning compiled TMCP expertise into an explicit rubric, evidence-backed audit, ordered remediation plan, and optional implementation handoff.
- 2026-06-24: Added the `expert_rubric_remediation_v1` implementation plan covering the service module, workflow/skill registry entries, routing, `aios tmcp review-plan`, fixtures, validation, and truth update sequence.
- 2026-06-24: Split the oversized `expert_rubric_remediation_v1` implementation plan into GSD Phases 26-28: core artifacts, workflow runtime, and CLI/verification.
- 2026-06-24: Added routing coverage for expert audit-plan/rubric-remediation objectives and suppressed diagnostic workflow-key mentions from content-generation routing.
- 2026-06-24: Planned all three expert rubric remediation phases with GSD research, validation, and eight executable plans: Phase 26 has two core-artifact plans, Phase 27 has three workflow-runtime plans, and Phase 28 has three CLI/verification plans.
- 2026-06-24: Added an AIOS-local TDD Test Value Adoption Gate across the backfill quality ratchet, standards ladder contract, testing context, and test-quality/testing-trust criteria so TDD-heavy repos are judged by behavioral test signal rather than test volume.
- 2026-06-24: Executed expert rubric remediation through Phase 28 Plan 28-01: core artifact builders, workflow runtime dispatch, active registry entries, expert route scoring, and the read-only `aios tmcp review-plan` CLI now exist with focused regression coverage.
- 2026-06-24: Smoke-verified `aios tmcp review-plan` against Soundscape visual-polish evidence, producing rubric, audit, remediation, and approval-gated handoff artifacts under `/tmp/aios-expert-review-smoke`.
- 2026-06-24: Restored the full Python pytest baseline by fixing stale relative-window learning fixtures, updating implemented contract-audit expectations, restoring the skills-harvest validation boolean, generating the missing default TMCP approval branch, and making workflow-experiment temp repos satisfy the user commit quality gate without blocking artifact commits.
- 2026-06-25: Made the global user commit quality gate visible during long Pre-CR runs by emitting flushed Pre-CR start, heartbeat, and finish messages while preserving captured JSON output for failure summaries.
- 2026-06-25: Added `aios humanize` CLI commands for personalized humanizer rewrites, feedback capture, and eval execution, with JSON output, optional file/stdin input, run recording, and focused CLI regression coverage.
- 2026-06-25: Added a global/AIOS agent rule that completed feature-branch work must be integrated into canonical `dev` before feature branches are pruned, keeping `main` deployable for release/mainline merges.
- 2026-06-25: Added expert-UI-rubric aliases so natural prompts such as "Use the TMCP expert UI rubric on Hoopscout" route to `expert_rubric_remediation_v1` instead of generic UI implementation/review handling.
- 2026-06-26: Added `repo_gate_adoption_v1` with deterministic artifact builders, workflow runtime dispatch, active workflow/skill registry entries, route aliases for quality/commit gate adoption, and `aios gate adoption-plan` CLI output.

## Open Problems

1. **Full Ruff baseline is not green** — `uv run ruff check .` failed on 2026-06-26 with 25 issues; touched-file Ruff checks pass for the repo gate adoption workflow.
2. **Full format baseline is not green** — `uv run ruff format --check .` reported 172 files needing formatting on 2026-06-26; touched-file format checks pass for the repo gate adoption workflow.
3. **Full BasedPyright baseline is not green** — `uv run basedpyright` failed on 2026-06-26 with 110 errors and 101 warnings, including existing `run_cli` complexity.
## Next Concrete Steps

1. Use `aios repo inspect` and `aios quality ladder` in live Codex sessions, then decide whether they should ingest CTS/context evidence or remain lightweight deterministic helpers.
2. Decide whether AIOS should add a thin shortcut or adapter for invoking external Quality Runner runs.
3. Resume linked-repo adoption execution with BidCamp repo-local Phase 151, then continue BidCamp 152-155, EliHealth 09-13, and pre-cr-suite-lsp 04-06.

## Risks / Blockers

- Hook regressions are silent — no test safety net catches a broken stop hook until a session closes without writing its record
- The large number of scripts in `bin/` (60+) means drift and dead code accumulation are likely without regular Vulture runs
- Quality tooling is explicit but failing at repo level, so completion claims must distinguish targeted eval-run checks from full-repo health.

## Quality Ladder Notes

| Step | Status | Notes |
|------|--------|-------|
| Lint (ruff) | Fail | `uv run ruff check .` failed on 2026-06-28 with 25 existing repo issues. Focused Codex session intelligence Ruff checks pass. |
| Type check (basedpyright) | Fail | `uv run basedpyright` failed on 2026-06-28 with 110 errors and 78 warnings, including existing `run_cli` complexity. Focused Codex session intelligence BasedPyright checks pass. |
| Dead code (vulture) | Warning | `uv run vulture . --min-confidence 70` failed on 2026-06-28 because `.venv` third-party packages were scanned; `uv run vulture bin services --min-confidence 70` passed. |
| Tests | Pass | `PYTHONPATH=/Users/jakyeamos/quality-evidence-contract:/Users/jakyeamos/repo-quality-certifier uv run pytest -q` passed on 2026-06-28 with 1051 tests. |
| Structure | Fail | `uv run ruff format --check .` reported 169 files needing formatting on 2026-06-28. Focused Codex session intelligence format checks pass. |

Focused Codex session intelligence checks on 2026-06-28:
- `PYTHONPATH=/Users/jakyeamos/quality-evidence-contract:/Users/jakyeamos/repo-quality-certifier uv run pytest tests/test_session_intelligence_loop.py -q` passed with 12 tests after durability, Claude normalization, and cross-batch merge hardening.
- `PYTHONPATH=/Users/jakyeamos/quality-evidence-contract:/Users/jakyeamos/repo-quality-certifier uv run ruff check services/session_intelligence_loop.py services/session_providers/claude.py services/aios_cli.py tests/test_session_intelligence_loop.py` passed.
- `PYTHONPATH=/Users/jakyeamos/quality-evidence-contract:/Users/jakyeamos/repo-quality-certifier uv run ruff format --check services/session_intelligence_loop.py services/session_providers/claude.py services/aios_cli.py tests/test_session_intelligence_loop.py` passed.
- `PYTHONPATH=/Users/jakyeamos/quality-evidence-contract:/Users/jakyeamos/repo-quality-certifier uv run basedpyright services/session_intelligence_loop.py services/session_providers/claude.py tests/test_session_intelligence_loop.py` passed.
- `PYTHONPATH=/Users/jakyeamos/quality-evidence-contract:/Users/jakyeamos/repo-quality-certifier uv run vulture services/session_intelligence_loop.py services/session_providers/claude.py --min-confidence 70` exited 0.
- `.venv/bin/python /Users/jakyeamos/AIOS/bin/aios.py session-intel backfill --provider all --since all --write-report --batch-size 250` processed 1,923 sources in 9 batches with 1,051 batch candidates; persisted state after the immediate resume is 1,923 cursors, 973 pending candidates, and zero duplicate lane/title groups. Backup before the first live run is `data/aios.db.pre-session-intel-backfill-20260628`.
- `.venv/bin/python bin/aios.py --db /private/tmp/aios-session-intel-backfill-smoke.db session-intel backfill --provider all --codex-source-root /private/tmp/aios-empty-codex --claude-source-root /private/tmp/aios-empty-claude --batch-size 1 --json` passed.
- `.venv/bin/python bin/aios.py --db /private/tmp/aios-session-intel-smoke.db session-intel candidates --json` passed.
- `.venv/bin/python bin/aios.py --db /private/tmp/aios-session-intel-smoke.db session-intel run --provider codex --since all --source-root /private/tmp/no-codex-sessions --write-report --report-root /private/tmp/session-intel-reports --json` passed.
- `python3 bin/aios.py --db /private/tmp/aios-session-intel-smoke.db session-intel candidates --json` failed with `ModuleNotFoundError: quality_evidence_contract`; invoking through `.venv/bin/python` works.

Focused Codex session intelligence triage checks on 2026-06-28:
- `PYTHONPATH=/Users/jakyeamos/quality-evidence-contract:/Users/jakyeamos/repo-quality-certifier uv run pytest tests/test_session_intelligence_loop.py -q` passed with 15 tests after adding cluster triage, review events, intent grouping, and workflow sequence mining.
- `PYTHONPATH=/Users/jakyeamos/quality-evidence-contract:/Users/jakyeamos/repo-quality-certifier uv run ruff check services/session_intelligence_loop.py services/aios_cli.py tests/test_session_intelligence_loop.py` passed.
- `PYTHONPATH=/Users/jakyeamos/quality-evidence-contract:/Users/jakyeamos/repo-quality-certifier uv run ruff format --check services/session_intelligence_loop.py services/aios_cli.py tests/test_session_intelligence_loop.py` passed.
- `PYTHONPATH=/Users/jakyeamos/quality-evidence-contract:/Users/jakyeamos/repo-quality-certifier uv run basedpyright services/session_intelligence_loop.py tests/test_session_intelligence_loop.py` passed.
- `PYTHONPATH=/Users/jakyeamos/quality-evidence-contract:/Users/jakyeamos/repo-quality-certifier uv run vulture services/session_intelligence_loop.py --min-confidence 70` exited 0.
- `.venv/bin/python /Users/jakyeamos/AIOS/bin/aios.py session-intel clusters --status pending_review --lane all` returned `clusters=50` with the default limit; `--limit 5 --json` returned 5 of 621 total clusters with compact candidate previews.

Focused session-intelligence tool promotion checks on 2026-06-28:
- `PYTHONPATH=/Users/jakyeamos/quality-evidence-contract:/Users/jakyeamos/repo-quality-certifier uv run pytest tests/test_session_intelligence_tools.py tests/test_session_intelligence_loop.py tests/test_aios_cli.py -q` passed with 110 tests.
- `PYTHONPATH=/Users/jakyeamos/quality-evidence-contract:/Users/jakyeamos/repo-quality-certifier uv run pytest -q` passed with 1051 tests.
- `PYTHONPATH=/Users/jakyeamos/quality-evidence-contract:/Users/jakyeamos/repo-quality-certifier uv run ruff check services/session_intelligence_tools.py services/aios_cli.py tests/test_session_intelligence_tools.py` passed.
- `PYTHONPATH=/Users/jakyeamos/quality-evidence-contract:/Users/jakyeamos/repo-quality-certifier uv run ruff format --check services/session_intelligence_tools.py services/aios_cli.py tests/test_session_intelligence_tools.py` passed.
- `PYTHONPATH=/Users/jakyeamos/quality-evidence-contract:/Users/jakyeamos/repo-quality-certifier uv run basedpyright services/session_intelligence_tools.py tests/test_session_intelligence_tools.py` passed.
- `PYTHONPATH=/Users/jakyeamos/quality-evidence-contract:/Users/jakyeamos/repo-quality-certifier uv run vulture services/session_intelligence_tools.py --min-confidence 70` exited 0.

Focused Quality Runner standalone checks on 2026-06-28:
- In `/Users/jakyeamos/quality-runner`, `python3.14 -m pytest -q` passed with 95 tests.
- In `/Users/jakyeamos/quality-runner`, `uv run --with pytest pytest -q` passed with 95 tests, exercising package build/install behavior.
- In `/Users/jakyeamos/quality-runner`, `ruff check .`, `ruff format --check .`, `basedpyright`, and `vulture . --min-confidence 70` passed.
- In `/Users/jakyeamos/quality-runner`, `python3.14 scripts/run_pytest_with_lcov.py` passed with 95 tests, and `pre-cr run --workspace /Users/jakyeamos/quality-runner` exited 0 while reporting no coverage result.

Focused repo gate adoption workflow checks on 2026-06-26:
- `uv run pytest tests/test_repo_gate_adoption.py tests/test_workflow_orchestration.py tests/test_task_routing.py tests/test_aios_cli.py -q` passed with 163 tests.
- `uv run pytest tests/test_repo_gate_adoption.py tests/test_workflow_orchestration.py::test_repo_gate_adoption_workflow_registry_contract tests/test_workflow_orchestration.py::test_repo_gate_adoption_workflow_executes_with_artifacts tests/test_workflow_orchestration.py::test_repo_gate_adoption_routing_beats_generic_workflow_routes tests/test_task_routing.py::test_route_objective_routes_quality_gate_adoption_to_gate_workflow tests/test_aios_cli.py::test_gate_adoption_plan_json_writes_artifacts -q` passed with 8 tests.
- `uv run pytest -q tests/test_repo_gate_adoption.py tests/test_workflow_orchestration.py::test_repo_gate_adoption_workflow_registry_contract tests/test_workflow_orchestration.py::test_repo_gate_adoption_workflow_executes_with_artifacts tests/test_aios_cli.py::test_gate_adoption_plan_json_writes_artifacts` passed with 8 tests after TMCP expert enrichment wiring.
- `uv run pytest -q tests/test_repo_gate_adoption.py tests/test_workflow_orchestration.py::test_repo_gate_adoption_workflow_registry_contract tests/test_workflow_orchestration.py::test_repo_gate_adoption_workflow_executes_with_artifacts tests/test_aios_cli.py::test_gate_adoption_plan_json_writes_artifacts` passed with 8 tests after per-rubric Markdown/JSON materializer wiring.
- `uv run pytest -q tests/test_repo_gate_adoption.py tests/test_workflow_orchestration.py::test_repo_gate_adoption_workflow_registry_contract tests/test_workflow_orchestration.py::test_repo_gate_adoption_workflow_executes_with_artifacts tests/test_aios_cli.py::test_gate_adoption_plan_json_writes_artifacts tests/test_aios_cli.py::test_gate_adoption_doc_quality_json_writes_report` passed with 9 tests after profile/classification, visual route, and adoption-doc-quality CLI wiring.
- `uv run pytest -q tests/test_repo_gate_adoption.py tests/test_aios_cli.py::test_gate_adoption_doc_quality_json_writes_report tests/test_aios_cli.py::test_gate_adoption_plan_json_writes_artifacts tests/test_workflow_orchestration.py::test_repo_gate_adoption_workflow_executes_with_artifacts` passed with 8 tests after scan-derived rubric evidence/root-cause generation and stricter phase-readiness assertions.
- `uv run pytest -q tests/test_repo_gate_adoption.py tests/test_workflow_orchestration.py::test_repo_gate_adoption_workflow_registry_contract tests/test_workflow_orchestration.py::test_repo_gate_adoption_workflow_executes_with_artifacts tests/test_aios_cli.py::test_gate_adoption_plan_json_writes_artifacts tests/test_aios_cli.py::test_gate_adoption_doc_quality_json_writes_report` passed with 11 tests after repo-local gate-phase rollout hardening.
- `uv run ruff check services/repo_gate_adoption.py services/aios_cli.py tests/test_repo_gate_adoption.py tests/test_aios_cli.py` passed after repo-local gate-phase rollout hardening.
- `uv run pytest -q tests/test_repo_gate_adoption.py tests/test_workflow_orchestration.py::test_repo_gate_adoption_workflow_registry_contract tests/test_workflow_orchestration.py::test_repo_gate_adoption_workflow_executes_with_artifacts tests/test_aios_cli.py::test_gate_adoption_plan_json_writes_artifacts tests/test_aios_cli.py::test_gate_adoption_doc_quality_json_writes_report` passed with 11 tests after strict inherited lint/test clearance hardening.
- `uv run basedpyright services/repo_gate_adoption.py` passed after strict inherited lint/test clearance hardening.
- `uv run pytest -q tests/test_repo_gate_adoption.py tests/test_workflow_orchestration.py::test_repo_gate_adoption_workflow_registry_contract tests/test_workflow_orchestration.py::test_repo_gate_adoption_workflow_executes_with_artifacts tests/test_aios_cli.py::test_gate_adoption_plan_json_writes_artifacts tests/test_aios_cli.py::test_gate_adoption_doc_quality_json_writes_report` passed with 11 tests after fifteen-rubric tier-one gate expansion.
- `uv run ruff check services/repo_gate_adoption.py services/workflow_orchestration.py services/aios_cli.py tests/test_repo_gate_adoption.py tests/test_workflow_orchestration.py tests/test_task_routing.py tests/test_aios_cli.py` passed.
- `uv run ruff format --check services/repo_gate_adoption.py services/workflow_orchestration.py services/aios_cli.py tests/test_repo_gate_adoption.py tests/test_workflow_orchestration.py tests/test_task_routing.py tests/test_aios_cli.py` passed.
- `uv run basedpyright services/repo_gate_adoption.py` passed.
- `uv run vulture services/repo_gate_adoption.py --min-confidence 70` exited 0.
- `uv run pytest -q` passed with 1001 tests.
- `uv run ruff check repo_quality_certifier services/repo_gate_adoption.py tests/test_repo_quality_certifier_package.py tests/test_repo_gate_adoption.py` passed after the `repo_quality_certifier` package-boundary split.
- `uv run basedpyright repo_quality_certifier services/repo_gate_adoption.py tests/test_repo_quality_certifier_package.py` passed after the `repo_quality_certifier` package-boundary split.
- `uv run pytest -q tests/test_repo_quality_certifier_package.py tests/test_repo_gate_adoption.py` passed with 9 tests after the `repo_quality_certifier` package-boundary split.
- `uv run ruff check repo_quality_certifier tests/test_repo_quality_certifier_package.py pyproject.toml` passed after adding standalone CLI/MCP/plugin surfaces.
- `uv run ruff format --check repo_quality_certifier tests/test_repo_quality_certifier_package.py` passed after adding standalone CLI/MCP/plugin surfaces.
- `uv run basedpyright repo_quality_certifier tests/test_repo_quality_certifier_package.py` passed after adding standalone CLI/MCP/plugin surfaces.
- `uv run pytest -q tests/test_repo_quality_certifier_package.py` passed with 8 tests after adding standalone CLI/MCP/plugin surfaces.
- `uv run ruff check services/success_criteria.py tests/test_quality_evidence_contract.py tests/test_success_criteria.py pyproject.toml` passed after wiring external `quality-evidence-contract`.
- `uv run basedpyright services/success_criteria.py tests/test_quality_evidence_contract.py` passed after wiring external `quality-evidence-contract`.
- `uv run --with pytest python -m pytest -q tests/test_quality_evidence_contract.py tests/test_success_criteria.py` passed with 29 tests after wiring external `quality-evidence-contract`.
- `python3 bin/aios.py --json --help` passed after adding the virtualenv re-exec bootstrap.
- `pnpm test:context` passed with 15 tests after wiring external `context-compiler-contract`.
- `node --check tests/context-compiler.test.mjs` passed after wiring external `context-compiler-contract`.

Full repo checks on 2026-06-26:
- `uv run ruff check .` failed with 25 existing issues.
- `uv run ruff format --check .` failed with 172 files needing formatting.
- `uv run basedpyright` failed with 110 errors and 101 warnings.
- `uv run pytest -q` passed with 1001 tests.
- `uv run vulture . --min-confidence 70` exited 0.

Doc-only update note: the 2026-06-27 Quality Runner design commit adds a standalone audit-and-plan spec and updates this truth snapshot. It does not change production code; the existing full-repo Ruff, format, and BasedPyright failures remain authoritative.

Doc-only update note: the 2026-06-27 Quality Runner implementation-plan commit adds a Python-first standalone package plan and updates this truth snapshot. It does not change production code; the existing full-repo Ruff, format, and BasedPyright failures remain authoritative.

Focused personalized humanizer CLI checks on 2026-06-25:
- `uv run pytest tests/test_personalized_humanizer.py tests/test_aios_cli.py::test_humanize_run_no_record_outputs_rewrite tests/test_aios_cli.py::test_humanize_run_records_feedback_flow tests/test_aios_cli.py::test_humanize_eval_cli_runs_suite -q` passed with 14 tests.
- `uv run ruff check services/aios_cli.py tests/test_aios_cli.py tests/test_personalized_humanizer.py` passed.
- `uv run ruff format --check services/aios_cli.py tests/test_aios_cli.py tests/test_personalized_humanizer.py` passed.

Focused user commit gate checks on 2026-06-25:
- `uv run pytest tests/test_user_commit_quality_gate.py -q` passed with 28 tests.
- `uv run ruff check bin/user-commit-quality-gate.py tests/test_user_commit_quality_gate.py` passed.
- `uv run ruff format --check bin/user-commit-quality-gate.py tests/test_user_commit_quality_gate.py` passed.
- `uv run basedpyright bin/user-commit-quality-gate.py tests/test_user_commit_quality_gate.py` passed.
- `uv run vulture bin/user-commit-quality-gate.py --min-confidence 70` exited 0.

Focused expert workflow checks on 2026-06-24:
- `uv run pytest tests/test_aios_cli.py::test_tmcp_review_plan_writes_expert_review_artifacts tests/test_aios_cli.py::test_tmcp_review_plan_rejects_malformed_evidence_json -q` passed.
- `uv run pytest tests/test_workflow_orchestration.py::test_expert_review_workflow_registry_contract tests/test_workflow_orchestration.py::test_expert_review_workflow_executes_with_artifacts -q` passed.
- `uv run pytest tests/test_expert_rubric_remediation.py -q` passed.

Focused expert routing alias check on 2026-06-25:
- `uv run pytest tests/test_task_routing.py -k tmcp_expert_rubric -q` passed.

Doc-only update note: the 2026-06-24 expert-rubric-remediation spec, implementation-plan, GSD phase-split, and Phase 26-28 planning commits ran the staged AIOS commit-quality checks and passed the registered standards, context, success-criteria, quality-pipeline, allowlist, and staged handler-race gates. The Phase 26-28 planning pass also ran `verify plan-structure` and `frontmatter validate --schema plan` for all eight plan files plus `git diff --check`; `gap-analysis --phase-dir` exited 0 but warned because global `REQUIREMENTS.md` coverage is not scoped to these TBD-requirement phases. No repo-level Ruff, BasedPyright, Vulture, or pytest run was performed for those design/planning-only commits; existing repo-level failures remain authoritative.

Doc-only update note: the 2026-06-24 TDD Test Value Adoption Gate commit passed the staged AIOS commit-quality checks, `git diff --check`, `uv run pytest -q tests/test_success_criteria.py tests/test_commit_quality_ladder.py`, and `pnpm context:validate`. Full repo-level Ruff, BasedPyright, Vulture, and pytest were not rerun for this policy-only change; the existing repo-level failures remain authoritative.

## Agent Notes

- `bin/` contains both hook scripts (prefix `hook-`) and standalone utility scripts. Treat hook scripts as highest-priority for type-safety review — they run in every Claude Code session.
- `services/cts/` is the Code Topology Service package — in early state per docs.
- `archive/` and `staging/` are excluded from all quality tools per `pyproject.toml`. Do not audit those directories.
- The DB schema is append-only in practice; migration scripts exist in `bin/`. Always check `schema.sql` for current canonical table definitions before querying.
- shellcheck skips `.py` files named like shell scripts — no action needed there.
- zsh scripts (if any) are intentionally skipped by shellcheck; this is expected, not a gap.
- Agents should proactively surface better long-term approaches when they see them, including tradeoffs and a recommended path, while keeping the active task moving.
