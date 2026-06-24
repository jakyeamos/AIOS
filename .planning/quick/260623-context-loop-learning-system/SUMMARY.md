# Quick Task Summary: Context Loop Learning System

## Completed

- Added `aios/context-loops/` audit, schema, retrieval policy, review taxonomy, approved/rejected lesson files, examples, metrics report target, and draft-only email pilot docs.
- Added `services/context_loops.py` for inner-loop run records, human review events, outer-loop learning candidates, approval/rejection/application, unsupported commitment checks, rejected-candidate suppression, and metrics.
- Added `context-loops` CLI subcommands through `services/aios_cli.py`.
- Added canonical SQLite table definitions to `schema.sql`.
- Added focused tests in `tests/test_context_loops.py`.
- Updated root project truth and planning state.

## Complexity + Simplification Gate

Gate A:

- No growing nested loops or sort-inside-loop patterns in the new service.
- Review proposal scans are linear over unprocessed review rows.
- Rejected-candidate suppression does one indexed-status candidate lookup per proposed review. This is acceptable for the local-first first pass.

Gate B:

- Kept the primitive in one service instead of spreading run/review/candidate logic across existing learning modules.
- Reused the repo's existing SQLite plus Markdown artifact pattern.
- Deferred real email, semantic diffing, and `improvement_writebacks` integration to avoid prematurely coupling the pilot to external systems.

Gate C:

- `uv run pytest tests/test_context_loops.py -q` passed.
- `uv run ruff check services/context_loops.py services/aios_cli.py tests/test_context_loops.py` passed.
- `uv run basedpyright services/context_loops.py services/aios_cli.py tests/test_context_loops.py` passed.
- `pnpm context:validate` passed.
- `uv run python bin/aios.py --db /private/tmp/aios-context-loop-smoke/aios.db context-loops email-draft --task-input "I can deliver by tomorrow." --context-root /private/tmp/aios-context-loop-smoke/context --json` passed and produced a draft-only record with unsupported commitments flagged.

## Known Verification Caveat

`uv run pytest tests/test_aios_cli.py tests/test_context_loops.py -q` still fails in unrelated/stale CLI expectations around learning analysis, contract audit statuses, and skills harvest validation shape. The new context-loop tests pass in that run.
