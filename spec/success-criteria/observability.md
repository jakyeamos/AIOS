---
id: observability
title: Observability Completeness for Operational Changes
scope: domain-specific
blocking: false
evaluation_method: heuristic
version: 1.0
---

## Intent

Ensure operationally meaningful changes remain inspectable through logs, metrics, traces, or explicit diagnostics.

## Applies When

Changes to runtime workflows, orchestration behavior, state transitions, automation, or production-like execution paths.

## Required Checks

- Preserve or improve traceability for important state transitions.
- Maintain actionable logs for failures and critical lifecycle steps.
- Ensure new workflows expose enough data for debugging.
- Record what signals operators should inspect after rollout.

## Blockers

- Critical workflow behavior becomes less observable than before.
- Failures become silent or indistinguishable in logs/events.

## Warnings

- Runtime behavior changed without adding or validating inspection signals.
- Operational claims made without corresponding evidence paths.

## Evidence To Provide

- Which logs/events/metrics confirm expected behavior.
- How failures are identified and classified.
- Where operators should look first during incidents.

## Related Criteria

- `testing-trust`
- `workflow-state-integrity`

## Example Good

A run-lifecycle change includes explicit event records and failure summaries that can be queried deterministically.

## Example Bad

A control-plane behavior change removes event detail and relies on manual terminal inspection for diagnosis.
