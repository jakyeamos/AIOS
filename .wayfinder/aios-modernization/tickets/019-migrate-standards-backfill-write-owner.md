---
title: Migrate Standards Backfill Writes Behind the Python Owner
type: task
status: resolved
claim: /root (2026-07-14)
resolved: 2026-07-14
blocked_by: []
---

# Migrate Standards Backfill Writes Behind the Python Owner

## Question

Can the first write-capable standards-health satellite move from a direct UI
SQLite mutation to the canonical Python owner while preserving the existing
Taski interaction contract and a reversible cutover?

## Scope

- Route `projects.updateBackfillTask` through a Python-owned service and CLI
  command.
- Preserve Start, Block, and Resolve payloads and the source-backed read model.
- Validate mutable fields and nullable clearing at the owner boundary.
- Delete the prior TypeScript SQLite write helper and prove no duplicate write
  path remains.
- Leave project component settings and other UI mutation families for later
  bounded tickets.

## Resolution

Resolved the standards backfill write-owner slice. The Python service now owns
the validated task transition and returns the canonical row through the
`standards-backfill-update` JSON CLI command. The tRPC mutation invokes that
command through a typed server adapter; the existing Taski buttons and read
projection remain unchanged. The prior TypeScript `UPDATE` helper was deleted,
and the only remaining `standards_backfill_tasks` write is in the Python owner.

Rollback is the parent revision: restore the deleted TypeScript helper and
router import, with no schema or data migration required. Deletion proof is the
repository search showing no UI-owned `UPDATE standards_backfill_tasks` path.

Evidence:

- `/Users/jakyeamos/AIOS/.venv/bin/python -m pytest -q tests/test_standards_health_mutations.py` — 4 passed.
- `/Users/jakyeamos/AIOS/.venv/bin/ruff check services/standards_health_mutations.py services/aios_cli.py tests/test_standards_health_mutations.py` — passed.
- Focused BasedPyright for the new service and tests — 0 errors.
- UI ESLint and TypeScript no-emit — passed.
- UI dependency architecture check — passed (127 modules, 258 dependencies).
- `rg "UPDATE standards_backfill_tasks|updateStandardsBackfillTask" aios-ui services tests` — only the Python owner write and typed adapter remain.

M6 remains deferred because the paired-effectiveness decision is still
audit-only with unavailable provider telemetry, and other write-capable
satellites still need bounded owner migrations and browser evidence.
