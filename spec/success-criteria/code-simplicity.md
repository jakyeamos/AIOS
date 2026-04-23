---
id: code-simplicity
title: Protect Simplicity and Comprehension
scope: global
blocking: true
evaluation_method: heuristic
version: 1.0
---

## Intent

Protect readability and maintainability by preventing unnecessary complexity growth during implementation and refactoring.

## Applies When

Any implementation, bugfix, refactor, or review task that changes code behavior.

## Required Checks

- Keep change sets narrowly scoped to the task objective.
- Prefer explicit logic over abstraction layers that hide behavior.
- Avoid introducing mixed-concern files when boundaries already exist.
- Ensure complexity added has a clear operational or correctness payoff.

## Blockers

- Large complexity increases without documented necessity.
- Refactors that increase indirection while reducing local clarity.
- Structural changes that make ownership and data flow harder to inspect.

## Warnings

- Broad code changes touching many areas for a small objective.
- New helpers/abstractions added where duplication would be clearer.

## Evidence To Provide

- Why any complexity increase was necessary.
- Which files and modules were intentionally affected.
- What readability/maintainability guardrail is preserved.

## Related Criteria

- `testing-trust`
- `repo-boundary-discipline`

## Example Good

A refactor splits one overloaded function into two explicit helpers with clear names and unchanged external behavior.

## Example Bad

A refactor introduces a generic framework layer and multiple abstractions for a one-off workflow with no measurable maintainability gain.
