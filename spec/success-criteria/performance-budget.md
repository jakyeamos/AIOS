---
id: performance-budget
title: Practical Performance Budget
scope: domain-specific
blocking: false
evaluation_method: heuristic
version: 1.0
---

## Intent

Protect real user and operator experience from expensive renders, bundle growth, blocking requests, and unmeasured hot-path slowdowns.

## Applies When

Tasks that touch UI routes, client components, rendering paths, media, network waterfalls, background jobs, batch jobs, or known hot paths.

## Required Checks

- Identify bundle, render, network, or runtime cost added by the change.
- Check unnecessary client components and expensive rerenders.
- Check blocking requests and avoidable network waterfalls.
- Check image/media loading impact.
- Measure or bound deltas when the path is user-facing or hot.

## Blockers

- Severe user-facing slowdown is introduced without mitigation.
- Blocking work is added to a critical path with no budget or measurement.
- Bundle or render regression makes a core workflow unusable.

## Warnings

- Performance is plausible but unmeasured.
- Non-core page has a moderate render or network risk.
- Optimization should be deferred with an explicit follow-up.

## Evidence To Provide

- Bundle impact.
- Render risk.
- Network risk.
- Measured delta or reason measurement was not required.

## Related Criteria

- `complexity-budget`
- `thin-display`
- `accessibility`

## Example Good

A route adds data fetching but keeps it server-side, measures the slow path, and records no meaningful bundle delta.

## Example Bad

A dashboard moves heavy data shaping into a client component and adds several blocking requests before first render.
