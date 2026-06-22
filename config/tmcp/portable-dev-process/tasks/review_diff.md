# Task: Review Diff

Task ID: `@task:review_diff`

## Trigger

Use for code review, staged-diff review, pull-request review, risk assessment, or commit-readiness checks.

## Required Modules

- `@module:diff_review`
- `@module:git_hygiene`

## Instructions

1. Inspect the diff and surrounding code before commenting.
2. Lead with correctness, regressions, security, data loss, broken UX, and missing tests.
3. Cite files and lines when findings are actionable.
4. Do not block on style unless it affects maintainability or violates explicit local standards.
5. If no issues are found, state residual risks and unrun checks.

## Exit

Exit with ordered findings, open questions, and commit-readiness status.

