---
id: agent-claim-verification
title: Agent Claim Verification
scope: global
blocking: true
evaluation_method: heuristic
version: 1.0
---

## Intent

Prevent AI agents from completing work based on invented APIs, unseen files, assumed environment variables, or unverified test claims.

## Applies When

All agent-managed planning, implementation, bugfix, refactor, review, testing, and completion tasks.

## Required Checks

- Confirm referenced files, APIs, commands, and environment assumptions exist or are clearly marked as assumptions.
- Confirm relevant code was read before modification.
- Do not claim tests, builds, deployments, or validations passed without command evidence.
- Treat generated, lock, and durable artifact changes explicitly.
- Record missing evidence as a blocker or accepted tradeoff.

## Blockers

- Completion claim depends on tests or validation with no evidence.
- Agent references nonexistent files, APIs, commands, or environment variables as facts.
- Relevant code was not inspected before modifying behavior.
- Generated or lock files were modified incorrectly or without explanation.

## Warnings

- Evidence is partial but enough for the local risk.
- Environment assumption is plausible but not verified.
- A skipped check has a clear reason and follow-up.

## Evidence To Provide

- Claims requiring evidence.
- Files and APIs inspected.
- Commands run and outcomes.
- Verification artifacts.
- Explicit assumptions.

## Related Criteria

- `execution-first-verification`
- `test-quality`
- `git-worktree-cleanliness`

## Example Good

An agent cites the files read, the exact test command run, and the remaining skipped check with a concrete reason.

## Example Bad

An agent says the build passes after editing code but never ran a build or equivalent validation.
