---
id: testing-trust
title: Do Not Treat Test Volume as Trust
domain: testing
weight: 9
severity_if_missing: high
evaluation_method: manual
version: 1.0
---

## Intent

Test count, coverage, or AI-generated breadth must never be treated as evidence that a system is well-designed or safe to ship. The goal of testing is durable trust, not reassurance theater.

## Applies When

Any task that creates, reviews, expands, or evaluates a test suite.

## Core Principle

Optimize for **trust per test**, not total number of tests.

## Required Checks

When creating, reviewing, or expanding tests:

1. Prefer **contract, invariant, property, adversarial, and regression** tests over large volumes of shallow example tests.
2. Distinguish clearly between:
   - **Spec tests**: behaviors that must remain true across refactors
   - **Implementation tests**: behaviors tied to the current internal design
3. Keep the spec-layer test suite small, durable, and high-signal.
4. Treat any newly discovered edge case that reveals flawed architecture as a **design signal**, not just a missing test.
5. Convert real bugs, incidents, and production failures into regression tests quickly.
6. Pair test strategy with observability: logs, metrics, traces, failure capture, and replay where possible.
7. Use AI to generate **failure hypotheses and adversarial scenarios**, not just boilerplate test files.

## Blockers

A test suite must be rejected if it has:
- high volume but low behavioral depth
- many mock-heavy or structure-coupled tests
- weak protection of core invariants
- no regression tests from real bugs
- no evidence of adversarial or edge-case thinking

Do not accept:
- total test count as a quality argument
- coverage percentages as a substitute for reasoning
- large suites of implementation-coupled tests generated cheaply by AI
- claims that a component is trustworthy because it has "hundreds of tests"
- preservation of weak tests that make refactors harder without protecting meaningful behavior

## Warnings

- coverage percentage alone is not meaningful signal
- mock-heavy suites are likely testing implementation, not behavior
- AI-generated test files without hypothesis review should be treated as untrusted drafts

## Evidence to Provide

When claiming a test suite is adequate, supply:
- which invariants are protected and by which tests
- which real failure modes are covered
- which regression tests exist and what incidents they came from
- adversarial or edge-case scenarios considered and addressed

## Required Review Questions

Before accepting a test suite, ask:

- What invariant does this protect?
- Would this test still matter after a major refactor?
- Does this test verify product intent or just current implementation?
- What real failure mode does this cover?
- What production issue would slip through this suite today?

## Preferred Output Pattern

For meaningful systems, AI-generated testing should prioritize in this order:

1. contract/spec tests
2. invariant/property tests
3. adversarial/failure-mode tests
4. regression tests from real defects
5. observability recommendations for unknown unknowns

## Decision Standard

The question is not: **"How many tests exist?"**

The question is: **"How much justified trust does this suite create?"**

## Related Criteria

- `code-simplicity` — tests coupled to implementation details signal abstraction problems
- `observability` — unknown unknowns require traces and failure capture, not more tests
