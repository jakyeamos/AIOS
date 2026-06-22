# Task: CI Triage

Task ID: `@task:ci_triage`

## Trigger

Use for failing GitHub Actions, Vercel checks, build pipelines, branch protection failures, or remote test failures.

## Required Modules

- `@module:ci_triage`
- `@module:quality_gate`

## Instructions

1. Collect the failing job, command, environment, and first meaningful error.
2. Map remote commands to local equivalents.
3. Reproduce locally when practical.
4. Separate infrastructure failures from code failures.
5. Fix code failures with the same standards as local debugging.

## Exit

Exit with failed job summary, local reproduction command, suspected owner, and fix order.

