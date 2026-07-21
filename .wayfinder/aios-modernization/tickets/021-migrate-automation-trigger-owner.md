---
title: Route Automation Triggers Through the Python Owner
type: task
status: resolved
claim: /root (2026-07-15)
blocked_by: []
---

# Route Automation Triggers Through the Python Owner

## Scope

Move the `automations.triggerWorkflow` mutation behind the Python-owned
control-plane boundary. Preserve the returned plan and invocation contract,
including the automation and workflow identifiers, while deleting the direct
TypeScript write path from this route.

## Proof

- validated Python owner and JSON CLI command accept the mutation payload
- typed UI adapter invokes the owner and preserves the existing router result
- focused Python, CLI, and UI checks pass
- source scan proves this router no longer calls `planTask` or
  `invokeControlPlaneRun`
- rollback is the parent revision; no schema migration is introduced

## Deferred

Workflow, pattern, and skill CRUD satellites remain separate bounded tickets.

## Resolution

Commit `85de909` adds the validated `automation-trigger` Python CLI owner,
launches the managed runtime from that owner, and routes the tRPC mutation
through a typed adapter. Focused owner proof passes 4 tests; the existing CLI
regression slice passes 96 tests; Ruff and BasedPyright pass. UI lint,
architecture, build, and the pinned three-test browser contract pass. A source
scan confirms the automation router no longer calls `planTask` or
`invokeControlPlaneRun`; rollback is the parent revision and no schema
migration was introduced.
