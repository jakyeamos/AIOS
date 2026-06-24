---
id: test-quality
title: Behavior-Proving Test Quality
scope: task-type
blocking: true
evaluation_method: heuristic
version: 1.0
---

## Intent

Require tests or execution evidence to prove the behavior that changed, especially for critical paths.

## Applies When

Implementation, refactor, bugfix, testing, or review tasks that change behavior, permissions, migrations, core logic, billing, legal/criminal-case logic, or durable data.

## Required Checks

- Identify the behavior changed by the task.
- Confirm changed behavior is covered by tests or equivalent execution evidence.
- Include edge cases, failure states, and permission paths when relevant.
- For new or changed TDD tests, confirm each test protects behavior, a public contract, a confirmed bug, or meaningful domain branching rather than only increasing volume.
- Avoid snapshot-heavy tests as the only proof.
- Check that tests were not merely updated to match broken behavior.

## Blockers

- Critical behavior changes without tests or direct execution evidence.
- Auth, data migration, billing, legal/criminal-case, or core logic changes lack focused coverage.
- Tests assert mocks or implementation echoes instead of observable behavior.

## Warnings

- Non-critical behavior has partial coverage.
- Edge or failure cases are missing but scoped follow-up is acceptable.
- Test evidence is manual and should be automated later.
- New tests appear redundant, implementation-coupled, snapshot-heavy, or coverage-driven and should be routed through the TDD Test Value Adoption Gate when part of backfill.

## Evidence To Provide

- Behavior changed.
- Tests added or updated.
- Missing coverage and risk if untested.
- Commands or runtime evidence used.

## Related Criteria

- `testing-trust`
- `execution-first-verification`
- `data-integrity`
- `docs/adoption/backfill-quality-ratchet.md`

## Example Good

A parser bugfix includes a failing fixture before the fix, edge cases, and a command showing the focused test passed.

## Example Bad

A critical mutation changes semantics and only updates a snapshot that mirrors the new output.
