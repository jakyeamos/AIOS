---
id: testing-trust
title: Do Not Treat Test Volume as Trust
scope: task-type
blocking: false
evaluation_method: heuristic
version: 1.0
---

## Intent

Test count, coverage, or AI-generated breadth must never be treated as evidence that a system is well-designed or safe to ship.
The goal of testing is durable trust, not reassurance theater.

## Applies When

Any task that creates, reviews, expands, or evaluates a test suite, including implementation tasks where behavior changes should be protected.

## Required Checks

- Prefer contract, invariant, property, adversarial, and regression tests over shallow volume.
- Distinguish spec tests (durable behavior) from implementation-coupled tests (design detail).
- Convert real bugs/incidents into regression tests quickly.
- Treat edge cases as design signals, not just opportunities to increase test count.
- Pair test strategy with observability and failure inspection paths.

## Blockers

- High test volume with low behavioral depth.
- Core invariants left unprotected while test count is used as quality justification.
- Regression risk accepted without tests or explicit mitigation rationale.

## Warnings

- Coverage percentage used without invariant/failure-mode reasoning.
- Mock-heavy suites likely testing implementation details rather than behavior.
- AI-generated tests accepted without hypothesis review.

## Evidence To Provide

- Which invariants are protected and where.
- Which real failure modes are covered.
- Which regression tests map to real incidents or bugs.
- Which adversarial/edge scenarios were considered.

## Related Criteria

- `code-simplicity`
- `observability`

## Example Good

An implementation change ships with focused invariant/regression tests tied to known failure modes and clear behavior contracts.

## Example Bad

A change is accepted based on large generated test volume and coverage numbers alone, with no invariant mapping or regression evidence.
