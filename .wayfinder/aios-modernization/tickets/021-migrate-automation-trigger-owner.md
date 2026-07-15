---
title: Route Automation Triggers Through the Python Owner
type: task
status: open
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
