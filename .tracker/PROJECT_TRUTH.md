---
schemaVersion: 1
projectName: AIOS
summary: Active local-first agent operating system with durable eval-run recording, eval summary CLI surfaces, CTS/backend services, command-center UI, and broad but currently failing repo-level Python quality baselines.
healthScore: 66
statusLabel: needs_attention
nextStep: Triage the 10 full-suite Python test failures and stale repo-wide Ruff/BasedPyright baselines before claiming repo-level quality green.
blockers:
  - Full Python test, Ruff, format, and BasedPyright baselines are failing outside the eval-run slice.
lastUpdated: 2026-06-22
tags: [infra, ai-os, hooks, automation]
areas: [engineering]
goals: []
repoType: infra
sourceOfTruth: mixed
primaryLanguage: Python
activeBranch: main
lastCommitDate: 2026-04-08
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

The codebase is large, with Python services and scripts in `services/` and `bin/`, a committed `aios-ui/` Next.js command-center app, schema-backed operational storage, growing context/planning docs, and explicit Python quality configuration in `pyproject.toml`. The Code Topology Service (CTS) backend is committed: `services/cts/` provides graph storage, parsing, search, impact analysis, incremental updates, and MCP/CLI entrypoints. Phase 11 eval-run infrastructure is now coherent end to end: `schema.sql` defines eval task/run/score/failure tables, `services/eval_run_service.py` creates and reads durable eval records, and `services/aios_cli.py` exposes `aios eval record-run`, `list-runs`, and `summary`. The latest full Python quality pass on 2026-06-22 shows repo-level failures outside the eval-run slice, while targeted eval-run service/CLI checks pass.

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

## Open Problems

1. **Full Python test suite is not green** — `uv run pytest -q` failed on 2026-06-22 with 10 failures in learning analysis, contract audit expectations, skills harvest validation shape, and tier-one regression expectations.
2. **Full Ruff baseline is not green** — `uv run ruff check .` failed on 2026-06-22 with 21 issues outside the eval-run slice.
3. **Full format baseline is not green** — `uv run ruff format --check .` reported 133 files needing formatting on 2026-06-22.
4. **Full BasedPyright baseline is not green** — `uv run basedpyright` failed on 2026-06-22 with 79 errors and 96 warnings.
## Next Concrete Steps

1. Fix the 10 current `uv run pytest -q` failures or update stale expectations where the underlying contract intentionally changed.
2. Run Ruff autofix/format in planned chunks rather than broad unreviewed churn.
3. Triage BasedPyright errors in touched/runtime-critical modules first, especially hook and managed-runtime scripts.
4. Keep the eval-run service/CLI contract covered as later external harness adapters add more write paths.

## Risks / Blockers

- Hook regressions are silent — no test safety net catches a broken stop hook until a session closes without writing its record
- The large number of scripts in `bin/` (60+) means drift and dead code accumulation are likely without regular Vulture runs
- Quality tooling is explicit but failing at repo level, so completion claims must distinguish targeted eval-run checks from full-repo health.

## Quality Ladder Notes

| Step | Status | Notes |
|------|--------|-------|
| Lint (ruff) | Fail | `uv run ruff check .` failed on 2026-06-22 with 21 existing issues; targeted eval slice Ruff passed |
| Type check (basedpyright) | Fail | `uv run basedpyright` failed on 2026-06-22 with 79 errors and 96 warnings; targeted eval slice had 0 errors and 2 pytest import warnings |
| Dead code (vulture) | Pass | `uv run vulture . --min-confidence 70` exited 0 on 2026-06-22 |
| Tests | Fail | `uv run pytest -q` failed on 2026-06-22 with 10 failures; eval-run focused tests passed 14/14 |
| Structure | Warning | Full format check wants 133 files reformatted; touched eval files are formatted |

## Agent Notes

- `bin/` contains both hook scripts (prefix `hook-`) and standalone utility scripts. Treat hook scripts as highest-priority for type-safety review — they run in every Claude Code session.
- `services/cts/` is the Code Topology Service package — in early state per docs.
- `archive/` and `staging/` are excluded from all quality tools per `pyproject.toml`. Do not audit those directories.
- The DB schema is append-only in practice; migration scripts exist in `bin/`. Always check `schema.sql` for current canonical table definitions before querying.
- shellcheck skips `.py` files named like shell scripts — no action needed there.
- zsh scripts (if any) are intentionally skipped by shellcheck; this is expected, not a gap.
