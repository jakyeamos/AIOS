---
title: Migrate Project Component Settings Behind the Python Owner
type: task
status: resolved
claim: /root (2026-07-14)
resolved: 2026-07-14
blocked_by: []
---

# Migrate Project Component Settings Behind the Python Owner

## Question

Can the Taski project-scope component toggle move from a direct UI SQLite write
behind the Python owner while preserving the existing component-definition
read model and rollback path?

## Scope

- Add a validated Python service and JSON CLI command for one component toggle.
- Route `projects.setAiosComponentEnabled` through a typed server adapter.
- Keep the existing TypeScript component definitions and read projection as the
  UI presentation contract; remove only the direct TypeScript write helper.
- Prove invalid project/component inputs fail closed and no duplicate UI write
  path remains.
- Leave automation, workflow, pattern, and skill mutation families for later
  bounded tickets.

## Resolution

Resolved the project component-settings write-owner slice. The Python service
now validates project identity, component-key membership, and the boolean
toggle before applying the idempotent SQLite upsert through the
`project-component-update` JSON CLI. The tRPC mutation invokes that command
through a typed server adapter and then reuses the existing TypeScript read
projection for the returned component settings. The prior TypeScript write
helper was deleted.

Rollback is the parent revision and requires no schema migration. Deletion
proof is the repository search showing the only
`project_aios_component_settings` insert in `services/project_components.py`.

Evidence:

- `/Users/jakyeamos/AIOS/.venv/bin/python -m pytest -q tests/test_project_components.py` — 4 passed.
- `/Users/jakyeamos/AIOS/.venv/bin/python -m pytest -q tests/test_aios_cli.py tests/test_project_components.py` — 96 passed.
- Focused Ruff — passed; focused BasedPyright — 0 errors (pytest import warning only).
- UI lint, architecture lint (128 modules, 260 dependencies), and production build — passed.
- Pinned browser contract — 3 passed.
- `rg "INSERT INTO project_aios_component_settings|setAiosProjectComponentEnabled" aios-ui services tests` — only the Python owner write and typed adapter remain.

M6 remains deferred because the paired-effectiveness decision is audit-only
with unavailable provider telemetry; automation, workflow, pattern, and skill
write families still need bounded owner migrations.
