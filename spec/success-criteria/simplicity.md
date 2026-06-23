---
id: simplicity
title: Simplicity and De-Slop Gate
scope: global
blocking: false
evaluation_method: heuristic
version: 1.0
---

## Intent

Catch agentic overbuilding, premature abstraction, dead code, unclear names, and unnecessary framework/config expansion.

## Applies When

Any implementation, bugfix, refactor, review, or planning task.

## Required Checks

- Ask whether the task could be solved with less code.
- Check for unnecessary abstractions, frameworks, config, or patterns.
- Confirm names are clear and specific.
- Remove dead code and unused paths introduced by the change.
- Prefer boring explicit code where it stays understandable.

## Blockers

- Implementation adds broad abstractions or frameworks for a narrow task.
- New dead code or unused config is introduced.
- Complexity increase has no correctness, usability, or maintainability payoff.

## Warnings

- Some code could be shorter but is acceptable for clarity.
- Names are serviceable but should be improved in a later cleanup.
- Minor duplicate lines are intentionally clearer than abstraction.

## Evidence To Provide

- Unnecessary complexity found or ruled out.
- Lines or files removable.
- Simpler alternative considered.
- Reason current shape is justified.

## Related Criteria

- `code-simplicity`
- `architecture-boundary`
- `product-alignment`

## Example Good

A one-off conversion stays as three explicit lines rather than introducing a generic mapping framework.

## Example Bad

A small validation task adds a registry, plugin interface, and background worker with no actual need.
