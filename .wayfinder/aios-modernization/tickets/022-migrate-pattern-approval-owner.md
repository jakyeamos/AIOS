---
title: Route Pattern Approval Decisions Through the Python Owner
type: task
status: resolved
claim: /root (2026-07-15)
blocked_by: []
---

# Route Pattern Approval Decisions Through the Python Owner

## Scope

Move `patterns.approve` and `patterns.reject` behind a validated Python-owned
JSON CLI boundary. Preserve the existing result contract and read projection,
delete the direct TypeScript updates, and keep the transition auditable and
rollback-safe.

## Proof

- validated Python service and JSON CLI own both state transitions
- typed UI adapter preserves `{ ok, id, changedRows }`
- focused service/CLI tests and existing CLI regressions pass
- UI lint, architecture, build, and browser contracts pass
- source scan proves the pattern router has no direct update statements
- rollback is the parent revision; no schema migration is introduced

## Deferred

Pattern extraction/scoring/promotion jobs and workflow/skill registry writes
remain separate owner migrations.

## Resolution

Commit `4cd4183` adds the validated `pattern-approval-update` Python service
and JSON CLI owner, routes both tRPC mutations through a typed adapter, and
deletes the direct TypeScript `UPDATE` statements. Five focused owner tests and
the 97-test CLI regression slice pass; the full suite passes 1,178 tests with
one unrelated pre-existing shadow-branch foreign-key failure. Ruff and
BasedPyright pass for the new service, UI lint/typecheck, architecture, build,
and the pinned three-test browser contract pass, and a source scan confirms no
direct pattern update remains. Rollback is the parent revision and no schema
migration was introduced.
