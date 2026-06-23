---
id: resilience
title: Failure Mode and Resilience Gate
scope: domain-specific
blocking: false
evaluation_method: heuristic
version: 1.0
---

## Intent

Ensure changed code behaves predictably when dependencies, networks, databases, or repeated requests fail.

## Applies When

Tasks that touch IO, external services, background jobs, retries, database writes, queues, offline behavior, polling, or user-facing failure states.

## Required Checks

- Identify what happens when API calls fail.
- Identify what happens when database writes partially fail.
- Check duplicate request and idempotency behavior.
- Check slow or offline behavior where relevant.
- Confirm retry limits and backoff are bounded.
- Provide safe fallback or explicit failure when recovery is impossible.

## Blockers

- Critical operation can duplicate, corrupt, or lose data on retry.
- Unbounded retry or polling is introduced.
- Partial failure leaves durable state inconsistent without recovery.

## Warnings

- Failure behavior is safe but thinly tested.
- Fallback is manual or operationally acceptable but should be improved.
- Slow-network behavior is not measured for non-core UI.

## Evidence To Provide

- Failure modes considered.
- Fallbacks.
- Retry and idempotency behavior.
- Partial-failure recovery.

## Related Criteria

- `observability`
- `data-integrity`
- `execution-first-verification`

## Example Good

A write path uses a transaction, limits retries, and treats duplicate requests idempotently.

## Example Bad

A background job retries forever and can create duplicate records after a timeout.
