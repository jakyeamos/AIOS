# AIOS V2 Modernization Progress

**Status:** Milestone 0 in progress
**Updated:** 2026-07-13
**Plan:** [EXEC_PLAN.md](EXEC_PLAN.md)

## Current slice

Milestone 0 establishes one machine-readable vertical-fixture contract for
route, packet, run, evidence, approval, and operator projection state. The
fixture is intentionally read-only: it does not create a second database,
change live schema, or authorize a UI mutation.

## Completed

- Added `aios-v2-vertical-fixtures-v0.1` with healthy, empty, blocked, failed,
  needs-review, and closed scenarios.
- Added a TypeScript `satisfies` check so the UI compiler validates the shared
  JSON shape without creating a second runtime model.
- Added Python coverage for state completeness, cross-reference integrity,
  and Python ownership of route authority.
- Preserved user-owned guidance files and generated context artifacts outside
  the scoped implementation change.

## Verification

- `pnpm context:validate` — passed.
- `uv run pytest tests/test_v2_vertical_fixtures.py -q` — passed (2 tests).
- `pnpm --dir aios-ui exec tsc --noEmit` — passed.
- `.venv/bin/ruff check tests/test_v2_vertical_fixtures.py` — passed.
- `.venv/bin/basedpyright tests/test_v2_vertical_fixtures.py` — passed.
- `pnpm --dir aios-ui lint:architecture` — passed (122 modules, 255 dependencies).
- `pnpm quality:eval` — interrupted after the broad vulture scan expanded into
  historical shadow worktrees; the focused checks above are the relevant proof.

## Complexity + simplification gate

### Gate A: complexity and performance

- The TypeScript guard and Python test walk fixture, evidence, and approval
  arrays once; complexity is linear in the fixture document and is not on a
  request or render path.
- No nested growing-collection scans, database calls, serialization loops, or
  client-side derived rendering were added.

### Gate B: simplification and maintainability

- The JSON remains the single fixture source; TypeScript validates it at the
  UI boundary and Python validates cross-reference integrity.
- The allowed-state lists are intentionally repeated in the two language
  validators because no shared runtime package exists yet. This is a low-risk
  deferred consolidation candidate for a future contract package, not a second
  state owner.
- The explicit fixture fields are retained because later slices need stable
  machine-readable evidence, approval, and projection semantics; no page-local
  UI behavior was introduced.

### Gate C: verification

Focused tests, type checks, lint, architecture, and context validation passed.
The broad quality-eval command is not a trustworthy focused signal while it
recurses through historical shadow worktrees, so its interruption is recorded
instead of being presented as a pass.

## Remaining Milestone 0 work

- Add the same fixture consumer to the Python control-plane contract tests and
  the first v2 UI read-only slice without adding a second state owner.
- Attach seeded daily-flow replay evidence and confirm the fixture envelope
  maps to persisted rows before Milestone 1 migration work.

## Known blockers

- The baseline UI lint/build gates remain blocked by ADR-004's known external
  anti-slop dependency, font, root/tracing, and tRPC adapter issues.
- The main store still requires ADR-002 quarantine, migration, and restore
  proof before any write-capable slice.
