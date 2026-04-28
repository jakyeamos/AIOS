---
schemaVersion: 1
projectName: AIOS
summary: Active infra project powering Claude Code agent workflows with committed CTS backend, command-center UI, standalone query/audit utilities, design specs, and verified fixes for the latest AIOS UI/backend handoff gaps.
healthScore: 72
statusLabel: improving
nextStep: Triage remaining anti-slop warnings and the Turbopack tracing warning, then resume broader BasedPyright remediation.
blockers: []
lastUpdated: 2026-04-28
tags: [infra, ai-os, hooks, automation]
areas: [engineering]
goals: []
repoType: infra
sourceOfTruth: mixed
primaryLanguage: Python
activeBranch: main
lastCommitDate: 2026-04-08
quality:
  lint: pass
  types: fail
  tests: pass
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

AIOS is an active, git-versioned Python/shell infrastructure project (first commit 2026-04-01, latest normalization commits on 2026-04-12). It runs continuously as the backbone of all Claude Code sessions: lifecycle hooks fire on session start, stop, prompt submit, and tool events, writing structured data to a SQLite ops database at `~/AIOS/data/aios.db`.

The codebase is large — roughly 60 scripts in `bin/`, one committed test file, growing docs, and now a committed `aios-ui/` Next.js command-center app. `pyproject.toml` is now part of the repo, so Ruff, BasedPyright, and Vulture configuration live in source control instead of only existing locally. The Code Topology Service (CTS) backend is committed: `services/cts/` provides graph storage, parsing, search, impact analysis, incremental updates, and MCP/CLI entrypoints, and `hook-session-start.py` can inject CTS context when an index is current. The command-center UI is also committed and lintable, with project detail pages now exposing persisted per-project AIOS component scope controls for Taski summary, knowledge dossier, standards health, quality pipeline, learning writebacks, and active runs. Two standalone operational utilities are now committed as well: `bin/aios-query.py` exposes agent-friendly JSON views into the ops database, and `bin/token-audit.py` audits Claude transcript token usage and estimated spend. The anti-slop ESLint design spec is committed under `docs/superpowers/specs/`. The Python quality pass from 2026-04-12 still shows 20 Ruff issues and 22 BasedPyright errors plus 60 warnings.

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

## Open Problems

1. **BasedPyright baseline still needs a fresh full pass** — earlier baseline had hook-adjacent and dynamic import issues
2. **Anti-slop warnings remain in the UI** — `pnpm lint` exits 0, but still reports warning-level empty-state/action-copy findings
3. **Turbopack tracing warning remains** — `pnpm build` succeeds but reports broad NFT tracing through `server/routers/prompts.ts`
4. **Vulture dead-code scan not yet run** — `bin/` has ~60 scripts; some are likely stale or unused
## Next Concrete Steps

1. Reduce remaining UI anti-slop warnings in the touched command-center surfaces
2. Triage BasedPyright errors, starting with hook-adjacent scripts and dynamic import helpers
3. Run `vulture . --min-confidence 70` and remove or annotate confirmed dead code in `bin/`
4. Add smoke-test coverage for the remaining high-risk hooks: `hook-session-start.py` and `hook-stop.py`

## Risks / Blockers

- Hook regressions are silent — no test safety net catches a broken stop hook until a session closes without writing its record
- The large number of scripts in `bin/` (60+) means drift and dead code accumulation are likely without regular Vulture runs
- Quality tooling is now explicit but failing, so the repo is at least observable but not yet at the target standard

## Quality Ladder Notes

| Step | Status | Notes |
|------|--------|-------|
| Lint (ruff) | Pass | Targeted Ruff pass on touched hook/backend files succeeded on 2026-04-28; full-repo Ruff should still be run before broad cleanup claims |
| Type check (basedpyright) | Fail | 22 errors, 60 warnings on 2026-04-12 |
| Dead code (vulture) | Unknown | Installed and configured via `pyproject.toml`; not yet run |
| Tests | Pass | Focused hook/RTK/workflow synthesis tests pass; `hook-post-tool-use.py` now has literal-newline JSON regression coverage |
| Structure | Pass | `pyproject.toml`, `schema.sql`, `bin/`, `services/`, `aios-ui/`, and `tests/` are organized, and the working tree is back to a clean committed baseline |

## Agent Notes

- `bin/` contains both hook scripts (prefix `hook-`) and standalone utility scripts. Treat hook scripts as highest-priority for type-safety review — they run in every Claude Code session.
- `services/cts/` is the Code Topology Service package — in early state per docs.
- `archive/` and `staging/` are excluded from all quality tools per `pyproject.toml`. Do not audit those directories.
- The DB schema is append-only in practice; migration scripts exist in `bin/`. Always check `schema.sql` for current canonical table definitions before querying.
- shellcheck skips `.py` files named like shell scripts — no action needed there.
- zsh scripts (if any) are intentionally skipped by shellcheck; this is expected, not a gap.
