# Task: Git Hygiene

Task ID: `@task:git_hygiene`

## Trigger

Use for dirty tree inspection, staging, commit planning, branch naming, hooks, pre-commit checks, pre-push checks, or release readiness.

## Required Modules

- `@module:git_hygiene`
- `@module:hook_guidance`

## Instructions

1. Inspect branch and dirty state before staging or committing.
2. Keep unrelated user changes out of the current commit.
3. Prefer atomic commits scoped to one concern.
4. Run the relevant quality gate before commit when practical.
5. Treat hook installation and push as explicit user-approved side effects.

## Exit

Exit with worktree status, proposed commit scope, hook status, and next command.

