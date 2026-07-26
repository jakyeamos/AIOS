---
id: workflow-state-integrity
title: Workflow State Integrity
scope: domain-specific
blocking: false
evaluation_method: heuristic
version: 1.0
---

## Intent

Ensure workflow lifecycle state remains coherent, traceable, and grounded in explicit run/session linkage.

## Applies When

Tasks that trigger orchestration runs, runtime invocations, hook lifecycle transitions, or control-plane state updates.

## Required Checks

- Prefer explicit run/session/invocation linkage over heuristic fallback.
- Ensure terminal outcomes include inspectable reason context.
- Preserve traceable lifecycle events for key transitions.
- Record evaluation results against the relevant run or session.

## Blockers

- Lifecycle transitions that lose run/session ownership.
- Untraceable terminal outcomes for managed workflow runs.

## Warnings

- Legacy linkage fallback used where explicit handshake should be present.
- Session closes without linked orchestration record.

## Evidence To Provide

- Run/session/invocation identifiers involved.
- Transition and event records for state changes.
- Any fallback or override reason.

## Related Criteria

- `observability`

## Example Good

Session start and stop both include explicit run linkage and produce consistent lifecycle events with reason metadata.

## Example Bad

A workflow completes but state is inferred heuristically with missing linkage and no clear event rationale.
