# Task: Debug Failure

Task ID: `@task:debug_failure`

## Trigger

Use for bugs, failing tests, runtime errors, regressions, flaky behavior, confusing logs, or broken local workflows.

## Required Modules

- `@module:reproduce_first`
- `@module:quality_gate`

## Instructions

1. Reproduce the failure on the exact path the user cares about before proposing a fix.
2. Minimize the failing case only after the original failure is observed or clearly unavailable.
3. Read the code path that produced the failure.
4. Change the smallest surface that explains the observed behavior.
5. Add or update a regression test when the bug is durable and testable.

## Exit

Exit with reproduction evidence, root-cause hypothesis, fix plan, and verification command.

