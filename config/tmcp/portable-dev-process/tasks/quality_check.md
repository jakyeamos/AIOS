# Task: Quality Check

Task ID: `@task:quality_check`

## Trigger

Use when the agent needs to run or recommend lint, typecheck, tests, build, smoke checks, architecture checks, or equivalent verification.

## Required Modules

- `@module:command_discovery`
- `@module:quality_gate`

## Instructions

1. Discover the narrowest relevant commands before running broad suites.
2. Run commands in the project-preferred package manager or runtime.
3. Capture exact failures, not just pass/fail labels.
4. Separate blockers from warnings.
5. If checks are impossible, record the missing prerequisite and the closest useful substitute.

## Exit

Exit with command results, failure summary, and next fix targets.

