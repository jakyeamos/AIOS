# Quick Task: Bake Harness Rules Into AIOS Standards

Date: 2026-05-13

## Scope

Make the requested harness rules durable in the AIOS context standards:

- Common error surfaces require durable fixes, not repeated one-off handling.
- Agent-facing codebases should remain inviting when context is limited, including a soft file-size ceiling.
- Errors should be machine-readable and include remediation steps.

## Execution Plan

1. Update the relevant context standards and domain standard.
2. Update `PROJECT.md` with the new truth about harness quality expectations.
3. Run context validation and focused verification.
4. Commit the logical change set, then commit the truth/planning update.
