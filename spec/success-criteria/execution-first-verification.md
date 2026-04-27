---
id: execution-first-verification
title: Execution-First Verification
scope: global
blocking: true
evaluation_method: heuristic
version: 1.0
---

## Intent

Agents must run the exact behavior they are changing before relying on static reasoning when the work involves meaningful runtime risk.

## Applies When

Any implementation, refactor, bugfix, test, or review task involving one or more of:

- non-trivial side effects or state
- cross-system interactions
- core/shared logic modification
- debugging inconsistent behavior
- low trust in tests
- complex domain models

## Required Checks

- Run the exact code path being modified.
- Call all relevant functions directly.
- Reproduce real inputs, using mocks only when necessary.
- Observe outputs, side effects, and state changes.
- Only then propose or implement changes.

## Blockers

- Triggered work completes with no recorded direct execution evidence.
- The agent relies solely on static reasoning for a triggered change.
- Execution uses only broad or unrelated checks that do not exercise the modified path.

## Warnings

- Execution evidence is indirect and should be followed with a narrower path check.
- Real inputs could not be reproduced and the tradeoff is not recorded.

## Evidence To Provide

- Commands or invocations that exercised the changed path.
- Direct function calls used to inspect behavior.
- Real inputs and observed outputs or state changes.
- Explicit tradeoff notes when exact execution was impossible.

## Related Criteria

- `testing-trust`
- `workflow-state-integrity`

## Example Good

A workflow-state change is verified by calling the modified functions with real session/run inputs and observing the persisted rows.

## Example Bad

A shared runtime function is changed after reading the code only, with no command, function call, or state observation exercising the new path.
