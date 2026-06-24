---
schemaVersion: 1
projectName: AIOS
summary: Active local-first agent operating system with durable eval-run recording, context-loop learning primitives, differentiated branch-aware commit quality gates, TMCP expertise compilation, an approved expert-rubric-remediation workflow spec plus implementation plan, and broad but currently failing repo-level Python quality baselines.
healthScore: 66
statusLabel: needs_attention
nextStep: Implement `docs/superpowers/plans/2026-06-24-expert-rubric-remediation.md` task by task, starting with the expert review service module and validator tests.
blockers:
  - Full Python test, Ruff, format, and BasedPyright baselines are failing outside the gate-audit slice.
lastUpdated: 2026-06-24
tags: [infra, ai-os, hooks, automation]
areas: [engineering]
goals: []
repoType: infra
sourceOfTruth: mixed
primaryLanguage: Python
activeBranch: main
lastCommitDate: 2026-06-24
quality:
  lint: fail
  types: fail
  tests: fail
  deadCode: pass
  structure: warning
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

AIOS has an approved design and implementation plan for `expert_rubric_remediation_v1`, a general workflow that compiles TMCP expertise into an explicit rubric, audits concrete evidence, and produces ordered remediation slices before any implementation handoff.

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

## Open Problems

1. **Full Python test suite is not green** — `uv run pytest -q` failed on 2026-06-23 with 18 failures in learning analysis/CLI expectations, contract audit expectations, skills harvest validation shape, hook lifecycle/orchestration runtime, tier-one regression expectations, and workflow experiment fixture commits.
2. **Full Ruff baseline is not green** — `uv run ruff check .` failed on 2026-06-23 with 21 issues outside the gate-audit slice.
3. **Full format baseline is not green** — `uv run ruff format --check .` reported 147 files needing formatting on 2026-06-23.
4. **Full BasedPyright baseline is not green** — `uv run basedpyright` failed on 2026-06-23 with 100 errors and 100 warnings.
## Next Concrete Steps

1. Execute `docs/superpowers/plans/2026-06-24-expert-rubric-remediation.md` with subagent-driven development or executing-plans, preserving the task-by-task commit boundaries.
2. Fix the 18 current `uv run pytest -q` failures or update stale expectations where the underlying contract intentionally changed.
3. Run Ruff autofix/format in planned chunks rather than broad unreviewed churn.
4. Triage BasedPyright errors in touched/runtime-critical modules first, especially hook and managed-runtime scripts.
5. Keep the eval-run service/CLI contract covered as later external harness adapters add more write paths.

## Risks / Blockers

- Hook regressions are silent — no test safety net catches a broken stop hook until a session closes without writing its record
- The large number of scripts in `bin/` (60+) means drift and dead code accumulation are likely without regular Vulture runs
- Quality tooling is explicit but failing at repo level, so completion claims must distinguish targeted eval-run checks from full-repo health.

## Quality Ladder Notes

| Step | Status | Notes |
|------|--------|-------|
| Lint (ruff) | Fail | `uv run ruff check .` failed on 2026-06-23 with 21 existing issues; targeted audit/hook Ruff passed on 2026-06-23 |
| Type check (basedpyright) | Fail | `uv run basedpyright` failed on 2026-06-23 with 100 errors and 100 warnings; targeted audit/user-gate BasedPyright passed on 2026-06-23, while `services/commit_quality_ladder.py` still has existing optional-access errors |
| Dead code (vulture) | Pass | `uv run vulture . --min-confidence 70` exited 0 on 2026-06-22 |
| Tests | Fail | `uv run pytest -q` failed on 2026-06-23 with 18 failures; focused context-loop tests passed on 2026-06-23, and a broader `tests/test_aios_cli.py tests/test_context_loops.py` run still has unrelated/stale CLI expectation failures |
| Structure | Warning | Full format check wants 147 files reformatted; touched gate-audit files are formatted |

Doc-only update note: the 2026-06-24 expert-rubric-remediation spec and plan commits ran the staged AIOS commit-quality checks and passed the registered standards, context, success-criteria, quality-pipeline, allowlist, and staged handler-race gates. No repo-level Ruff, BasedPyright, Vulture, or pytest run was performed for those design/plan-only commits; existing repo-level failures remain authoritative.

## Agent Notes

- `bin/` contains both hook scripts (prefix `hook-`) and standalone utility scripts. Treat hook scripts as highest-priority for type-safety review — they run in every Claude Code session.
- `services/cts/` is the Code Topology Service package — in early state per docs.
- `archive/` and `staging/` are excluded from all quality tools per `pyproject.toml`. Do not audit those directories.
- The DB schema is append-only in practice; migration scripts exist in `bin/`. Always check `schema.sql` for current canonical table definitions before querying.
- shellcheck skips `.py` files named like shell scripts — no action needed there.
- zsh scripts (if any) are intentionally skipped by shellcheck; this is expected, not a gap.
- Agents should proactively surface better long-term approaches when they see them, including tradeoffs and a recommended path, while keeping the active task moving.
