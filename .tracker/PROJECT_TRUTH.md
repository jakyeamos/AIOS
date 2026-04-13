---
schemaVersion: 1
projectName: AIOS
summary: Active infra project powering Claude Code agent workflows with pyproject-based quality tooling now committed and broad script cleanup underway; ruff still has 20 errors and basedpyright now has an explicit failing baseline.
healthScore: 58
statusLabel: needs_attention
nextStep: Finish the remaining 20 ruff fixes, then work down the 22 basedpyright errors starting with hook-adjacent scripts and utility import loaders.
blockers: []
lastUpdated: 2026-04-12
tags: [infra, ai-os, hooks, automation]
areas: [engineering]
goals: []
repoType: infra
sourceOfTruth: mixed
primaryLanguage: Python
activeBranch: main
lastCommitDate: 2026-04-08
quality:
  lint: warning
  types: fail
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

AIOS is an active, git-versioned Python/shell infrastructure project (first commit 2026-04-01, latest normalization commits on 2026-04-12). It runs continuously as the backbone of all Claude Code sessions: lifecycle hooks fire on session start, stop, prompt submit, and tool events, writing structured data to a SQLite ops database at `~/AIOS/data/aios.db`.

The codebase is large — roughly 60 scripts in `bin/`, one committed test file, and growing docs, with additional CTS and command-center work currently being normalized into later commits. `pyproject.toml` is now part of the repo, so Ruff, BasedPyright, and Vulture configuration live in source control instead of only existing locally. A fresh quality pass on 2026-04-12 confirmed that Ruff still has 20 remaining issues and BasedPyright has 22 errors plus 60 warnings.

## Why This Matters / Intended Outcome

AIOS is not an app — it is the operating layer for all AI-assisted development work across every project. Hook correctness and DB integrity are load-bearing. Breakage here silently degrades all Claude Code sessions. The ops database is the canonical store for sessions, prompts, artifacts, patterns, bug logs, and next-action candidates across all projects.

## Recent Progress

- 2026-04-08: Added ops/maintenance utilities, retrieval rule and provenance tooling, enriched hook event capture, AI history import tooling
- 2026-04-08: Design specs added for Code Topology Service (CTS), AIOS Command UI, and prompt library
- 2026-04-09: Ruff 0.15.10 auto-fixed 181 issues; shellcheck clean on `auto_ingest.sh` and `health_check.sh`; BasedPyright and Vulture installed
- 2026-04-12: Committed `pyproject.toml` and a broad low-risk script cleanup pass (UTC datetime normalization, unused import cleanup, small lint-oriented simplifications)

## Open Problems

1. **20 Ruff errors unresolved** — F841 (unused variables), SIM (collapsible-if patterns), B905 (zip-without-strict), plus a few ambiguous-name/context-manager cases
2. **BasedPyright baseline now fails** — 22 errors and 60 warnings on 2026-04-12, including import-loader optionality, typed dict issues in PDF/DOCX indexers, and unresolved optional dependencies
3. **No test coverage for hooks** — only `tests/test_import_ai_history.py` exists. Hook failures are silent in production sessions
4. **Vulture dead-code scan not yet run** — `bin/` has ~60 scripts; some are likely stale or unused
5. **CTS and Command UI work is in progress locally** — the source is present in the working tree but not yet fully normalized into committed units

## Next Concrete Steps

1. Fix the 20 remaining Ruff errors manually — F841 (delete or use the variable), SIM (collapse nested ifs), B905 (add `strict=True` to `zip()` calls)
2. Triage the 22 BasedPyright errors, starting with hook-adjacent scripts and dynamic import helpers
3. Normalize and commit the CTS backend/CLI unit and then the command-center UI unit
4. Run `vulture . --min-confidence 70` and remove or annotate confirmed dead code in `bin/`
5. Add at least smoke-test coverage for the two highest-risk hooks: `hook-session-start.py` and `hook-stop.py`

## Risks / Blockers

- Hook regressions are silent — no test safety net catches a broken stop hook until a session closes without writing its record
- The large number of scripts in `bin/` (60+) means drift and dead code accumulation are likely without regular Vulture runs
- Quality tooling is now explicit but failing, so the repo is at least observable but not yet at the target standard
- Large local CTS/UI feature trees still need to be split into coherent commits without mixing generated artifacts

## Quality Ladder Notes

| Step | Status | Notes |
|------|--------|-------|
| Lint (ruff) | Warning | 20 errors remain on 2026-04-12 after prior auto-fix wave |
| Type check (basedpyright) | Fail | 22 errors, 60 warnings on 2026-04-12 |
| Dead code (vulture) | Unknown | Installed and configured via `pyproject.toml`; not yet run |
| Tests | Unknown | One committed test file exists; hooks still have no coverage |
| Structure | Pass | `pyproject.toml`, `schema.sql`, `bin/`, `services/`, and `tests/` are organized; CTS/UI work remains to be normalized |

## Agent Notes

- `bin/` contains both hook scripts (prefix `hook-`) and standalone utility scripts. Treat hook scripts as highest-priority for type-safety review — they run in every Claude Code session.
- `services/cts/` is the Code Topology Service package — in early state per docs.
- `archive/` and `staging/` are excluded from all quality tools per `pyproject.toml`. Do not audit those directories.
- The DB schema is append-only in practice; migration scripts exist in `bin/`. Always check `schema.sql` for current canonical table definitions before querying.
- shellcheck skips `.py` files named like shell scripts — no action needed there.
- zsh scripts (if any) are intentionally skipped by shellcheck; this is expected, not a gap.
