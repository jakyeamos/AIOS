---
id: complexity-budget
title: Complexity and Big-O Regression Budget
scope: domain-specific
blocking: true
evaluation_method: heuristic
version: 1.0
---

## Intent

Prevent hidden scalability regressions in touched code paths without requiring premature optimization.

## Applies When

Implementation, bugfix, refactor, or review tasks that touch algorithms, queries, pagination, polling, recursion, search, batch processing, or hot paths over user/data collections.

## Required Checks

- Identify the largest expected input sizes for touched paths.
- Compare touched loop, query, and traversal behavior against the prior shape.
- Look for nested loops over user/data collections.
- Check for N+1 database or API calls.
- Check for unbounded pagination, search, recursion, or polling.
- Decide whether a benchmark or large fixture is required.

## Blockers

- Touched hot path becomes asymptotically or practically worse without a documented reason.
- New N+1 database/API pattern is introduced.
- Unbounded work is added to a user-facing or background critical path.
- Large-input behavior is risky and no benchmark, fixture, or mitigation is provided.

## Warnings

- Complexity is plausible but not measured.
- Input-size assumptions are not documented.
- Non-critical path has a localized inefficiency that should become backlog.

## Evidence To Provide

- Worst touched path.
- Expected complexity.
- Largest expected input size.
- Benchmark or fixture evidence when required.
- Required fix or accepted tradeoff.

## Related Criteria

- `performance-budget`
- `test-quality`
- `simplicity`

## Example Good

A feed change pre-indexes related rows before rendering, records expected input sizes, and adds a large fixture regression test.

## Example Bad

A page renders each item by querying related records inside a loop and ships without measuring or bounding the input size.
