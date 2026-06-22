# Task: Planning Review

Task ID: `@task:planning_review`

## Trigger

Use when the user asks to compare strategies, review implementation plans, choose a promotion path, define acceptance criteria, or turn a planning decision into a testable verification path.

## Required Modules

- `@module:command_discovery`
- `@module:test_authoring`
- `@module:quality_gate`

## Instructions

1. Identify the candidate strategies, decision criteria, and evidence needed to compare them.
2. Discover existing commands and test conventions before recommending verification.
3. Convert the preferred path into behavior-level acceptance criteria.
4. Define the smallest regression or validation check that would prove the route works.
5. Keep the output read-only unless the user explicitly asks for edits.

## Exit

Exit with strategy options, tradeoff notes, acceptance criteria, and a verification command or test plan.
