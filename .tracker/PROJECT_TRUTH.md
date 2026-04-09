---
schemaVersion: 1
projectName: AIOS
summary: Active infra project powering Claude Code agent workflows — hooks, SQLite ops db, and automation scripts are functional but quality tooling pass is mid-flight with 20 ruff errors outstanding and basedpyright baseline not yet established.
healthScore: 62
statusLabel: needs_attention
nextStep: Fix the 20 remaining ruff errors (F841 unused vars, SIM collapsible-if, B905 zip-without-strict), then run basedpyright to establish type-check baseline.
blockers: []
lastUpdated: 2026-04-09
tags: [infra, ai-os, hooks, automation]
areas: [engineering]
goals: []
repoType: infra
sourceOfTruth: inferred
primaryLanguage: Python
activeBranch: main
lastCommitDate: 2026-04-08
quality:
  lint: warning
  types: unknown
  tests: unknown
  deadCode: unknown
  structure: pass
canonicalCommands:
  install: uv sync
  dev: unknown
  lint: ruff check .
  typecheck: basedpyright
  test: unknown
  deadcode: vulture . --min-confidence 70
agentExpectationsVersion: 1
---

## Current State

AIOS is an active, git-versioned Python/shell infrastructure project (first commit 2026-04-01, last commit 2026-04-08). It runs continuously as the backbone of all Claude Code sessions: lifecycle hooks fire on session start, stop, prompt submit, and tool events, writing structured data to a SQLite ops database at `~/AIOS/data/aios.db`.

The codebase is large — roughly 60 scripts in `bin/`, a `services/cts/` package, one test file, and growing docs. A quality tooling pass ran on 2026-04-09: ruff auto-fixed 181 issues, but 20 errors remain unresolved. basedpyright is installed and configured but has not yet been run to establish a baseline. shellcheck was applied to `.sh` files; non-bash scripts (zsh) were skipped.

## Why This Matters / Intended Outcome

AIOS is not an app — it is the operating layer for all AI-assisted development work across every project. Hook correctness and DB integrity are load-bearing. Breakage here silently degrades all Claude Code sessions. The ops database is the canonical store for sessions, prompts, artifacts, patterns, bug logs, and next-action candidates across all projects.

## Recent Progress

- 2026-04-08: Added ops/maintenance utilities, retrieval rule and provenance tooling, enriched hook event capture, AI history import tooling.
- 2026-04-08: Design specs added for Code Topology Service (CTS), AIOS Command UI, and prompt library.
- 2026-04-09: ruff 0.15.10 — 181 auto-fixes applied. shellcheck clean on `auto_ingest.sh` and `health_check.sh`. basedpyright 1.39.0 installed. vulture 2.16 installed.

## Open Problems

1. **20 ruff errors unresolved** — F841 (unused variables), SIM (collapsible-if patterns), B905 (zip-without-strict). These require manual judgment, not auto-fix.
2. **basedpyright baseline absent** — tools installed, config in `pyproject.toml`, but no run has been done. Type-safety of hooks is unknown.
3. **No test coverage for hooks** — only `tests/test_import_ai_history.py` exists. Hook failures are silent in production sessions.
4. **vulture dead-code scan not yet run** — bin/ has ~60 scripts; some are likely stale or unused.
5. **CTS and Command UI remain in design phase** — specs in `docs/` but no implementation observed.

## Next Concrete Steps

1. Fix the 20 remaining ruff errors manually — F841 (delete or use the variable), SIM (collapse nested ifs), B905 (add `strict=True` to `zip()` calls).
2. Run `basedpyright` and triage any type errors in hook scripts first (highest blast radius).
3. Run `vulture . --min-confidence 70` and remove or annotate confirmed dead code in `bin/`.
4. Add at least smoke-test coverage for the two highest-risk hooks: `hook-session-start.py` and `hook-stop.py`.

## Risks / Blockers

- Hook regressions are silent — no test safety net catches a broken stop hook until a session closes without writing its record.
- The large number of scripts in `bin/` (60+) means drift and dead code accumulation are likely without regular vulture runs.
- No blockers on the quality ladder steps — all tools are installed and configured.

## Quality Ladder Notes

| Step | Status | Notes |
|------|--------|-------|
| Lint (ruff) | Warning | 181 auto-fixed 2026-04-09; 20 errors remain |
| Type check (basedpyright) | Unknown | Installed and configured; baseline run pending |
| Dead code (vulture) | Unknown | Installed; not yet run |
| Tests | Unknown | One test file exists; hooks have no coverage |
| Structure | Pass | pyproject.toml, schema.sql, bin/, services/, tests/ all present and organized |

## Agent Notes

- `bin/` contains both hook scripts (prefix `hook-`) and standalone utility scripts. Treat hook scripts as highest-priority for type-safety review — they run in every Claude Code session.
- `services/cts/` is the Code Topology Service package — in early state per docs.
- `archive/` and `staging/` are excluded from all quality tools per `pyproject.toml`. Do not audit those directories.
- The DB schema is append-only in practice; migration scripts exist in `bin/`. Always check `schema.sql` for current canonical table definitions before querying.
- shellcheck skips `.py` files named like shell scripts — no action needed there.
- zsh scripts (if any) are intentionally skipped by shellcheck; this is expected, not a gap.
