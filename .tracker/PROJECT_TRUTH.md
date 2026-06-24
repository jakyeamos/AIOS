---
schemaVersion: 1
projectName: AIOS
summary: Active local-first agent operating system with durable eval-run recording, context-loop learning primitives, TMCP expertise compilation, and a smoke-verified expert-rubric-remediation workflow through service artifacts, runtime, registry, routing, and `aios tmcp review-plan`; the full Python pytest baseline is green again while broader Ruff and BasedPyright baseline issues remain open.
healthScore: 72
statusLabel: needs_attention
nextStep: Use the smoke-verified `aios tmcp review-plan` workflow on the full Soundscape visual-polish evidence set, then triage the remaining Ruff format/check and BasedPyright baseline failures.
blockers:
  - Full repo Ruff and format baselines are not green: Ruff reports 25 issues and Ruff format reports 178 files needing formatting.
  - Full repo BasedPyright is not green: 110 errors and 101 warnings, including the existing `services/aios_cli.py` `run_cli` complexity baseline.
lastUpdated: 2026-06-24
tags: [infra, ai-os, hooks, automation]
areas: [engineering]
goals: []
repoType: infra
sourceOfTruth: mixed
primaryLanguage: Python
activeBranch: codex/project-aios-component-scope
lastCommitDate: 2026-06-24
quality:
  lint: fail
  types: fail
  tests: pass
  deadCode: pass
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

The codebase is large, with Python services and scripts in `services/` and `bin/`, a committed `aios-ui/` Next.js command-center app, schema-backed operational storage, growing context/planning docs, and explicit Python quality configuration in `pyproject.toml`. The Code Topology Service (CTS) backend is committed: `services/cts/` provides graph storage, parsing, search, impact analysis, incremental updates, and MCP/CLI entrypoints. Phase 11 eval-run infrastructure is now coherent end to end: `schema.sql` defines eval task/run/score/failure tables, `services/eval_run_service.py` creates and reads durable eval records, and `services/aios_cli.py` exposes `aios eval record-run`, `list-runs`, and `summary`. The latest full Python quality pass on 2026-06-22 shows repo-level failures outside the hook-policy slice, while targeted hook-policy checks pass.

AIOS now also has a file-backed and SQLite-backed context-loop learning primitive: `services/context_loops.py`, `schema.sql`, and `python bin/aios.py context-loops ...` record inner-loop context/draft runs, review events, learning candidates, explicit approvals/rejections, approved lesson application, metrics, and a draft-only email pilot. Contract docs and examples live under `aios/context-loops/`.

AIOS now has `expert_rubric_remediation_v1` implemented and smoke-verified through the core artifact service, workflow runtime dispatch, active workflow/skill registry contracts, route scoring, and `aios tmcp review-plan`. The workflow compiles TMCP expertise into an explicit rubric, audits concrete evidence, produces ordered remediation slices, and writes an approval-gated implementation handoff without executing implementation.

## Why This Matters / Intended Outcome

AIOS is not an app — it is the operating layer for all AI-assisted development work across every project. Hook correctness and DB integrity are load-bearing. Breakage here silently degrades all Claude Code sessions. The ops database is the canonical store for sessions, prompts, artifacts, patterns, bug logs, and next-action candidates across all projects.

## Recent Progress

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

## Open Problems

1. **Full Ruff baseline is not green** — `uv run ruff check .` failed on 2026-06-24 with 25 issues; touched-file Ruff checks pass for the pytest-baseline fix.
2. **Full format baseline is not green** — `uv run ruff format --check .` reported 178 files needing formatting on 2026-06-24; touched-file format checks pass for the pytest-baseline fix.
3. **Full BasedPyright baseline is not green** — `uv run basedpyright` failed on 2026-06-24 with 110 errors and 101 warnings, including existing `run_cli` complexity.

## Next Concrete Steps

1. Use `aios tmcp review-plan` on the full Soundscape visual-polish evidence set and review the generated implementation handoff before approving any remediation slice.
2. Triage the full BasedPyright baseline, starting with `run_cli` complexity and optional-access/type-helper errors in runtime-critical modules.
3. Run Ruff autofix/format in planned chunks rather than broad unreviewed churn.
4. Keep the eval-run service/CLI contract covered as later external harness adapters add more write paths.

## Risks / Blockers

- Hook regressions are silent — no test safety net catches a broken stop hook until a session closes without writing its record
- The large number of scripts in `bin/` (60+) means drift and dead code accumulation are likely without regular Vulture runs
- Quality tooling is explicit but failing at repo level, so completion claims must distinguish targeted eval-run checks from full-repo health.

## Quality Ladder Notes

| Step | Status | Notes |
|------|--------|-------|
| Lint (ruff) | Fail | `uv run ruff check .` failed on 2026-06-24 with 25 issues. Focused expert workflow Ruff checks pass. |
| Type check (basedpyright) | Fail | `uv run basedpyright` failed on 2026-06-24 with 110 errors and 101 warnings, including existing `run_cli` complexity. |
| Dead code (vulture) | Pass | `uv run vulture . --min-confidence 70` exited 0 on 2026-06-24. |
| Tests | Pass | `uv run pytest -q` passed on 2026-06-24 with 961 tests. |
| Structure | Fail | `uv run ruff format --check .` reported 178 files needing formatting on 2026-06-24. Focused expert workflow format checks pass. |

Focused expert workflow checks on 2026-06-24:
- `uv run pytest tests/test_aios_cli.py::test_tmcp_review_plan_writes_expert_review_artifacts tests/test_aios_cli.py::test_tmcp_review_plan_rejects_malformed_evidence_json -q` passed.
- `uv run pytest tests/test_workflow_orchestration.py::test_expert_review_workflow_registry_contract tests/test_workflow_orchestration.py::test_expert_review_workflow_executes_with_artifacts -q` passed.
- `uv run pytest tests/test_expert_rubric_remediation.py -q` passed.

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
