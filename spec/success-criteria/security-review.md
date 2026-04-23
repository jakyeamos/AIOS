---
id: security-review
title: Security Review Before Sensitive Change Acceptance
scope: domain-specific
blocking: true
evaluation_method: heuristic
version: 1.0
---

## Intent

Prevent security regressions when sensitive paths or privileges are modified.

## Applies When

Tasks that affect authentication, authorization, secrets, permissions, tokens, cryptography, or security controls.

## Required Checks

- Identify sensitive files and security boundaries touched by the change.
- Verify that secret handling and permission checks remain explicit.
- Confirm no insecure defaults are introduced.
- Capture explicit security tradeoffs where applicable.

## Blockers

- Secret/environment file changes without explicit review evidence.
- Sensitive-path updates with missing or weakened access controls.
- Security-sensitive changes accepted without rationale.

## Warnings

- Security-adjacent files changed without a stated security objective.
- New security assumptions introduced but not documented.

## Evidence To Provide

- Sensitive files changed and why.
- Security assumptions validated.
- Residual risks and mitigation plan.

## Related Criteria

- `repo-boundary-discipline`
- `workflow-state-integrity`

## Example Good

A token validation change includes explicit reasoning, updated checks, and clear risk notes.

## Example Bad

An auth module is changed indirectly via convenience refactor with no security-focused validation or review notes.
