---
id: api-contract
title: API and Caller Contract Compatibility
scope: domain-specific
blocking: true
evaluation_method: heuristic
version: 1.0
---

## Intent

Prevent silent breaking changes to request/response shapes, status behavior, typed contracts, and frontend/backend assumptions.

## Applies When

Tasks that touch API routes, tRPC routers, server actions, typed DTOs, CLI JSON output, persisted JSON artifacts, or public module contracts.

## Required Checks

- Identify changed request and response shapes.
- Check for breaking renames, removed fields, or changed nullability.
- Confirm errors are typed or documented where callers depend on them.
- Verify old clients or downstream consumers remain supported or have a migration path.
- Check that frontend callers do not assume fields the backend may omit.

## Blockers

- Breaking contract change ships without migration plan.
- Consumer compatibility is unknown for a public or durable contract.
- Error or status behavior changes without caller updates.

## Warnings

- Internal contract changed with limited consumer scan.
- Optional field behavior is plausible but not exhaustively verified.
- Documentation should be updated before broader adoption.

## Evidence To Provide

- Contracts changed.
- Consumers affected.
- Backward compatibility plan.
- Typed/schema evidence or caller scan.

## Related Criteria

- `data-integrity`
- `test-quality`
- `architecture-boundary`

## Example Good

A response gains an optional field while existing required fields remain stable and callers are checked.

## Example Bad

A route renames a response field and only updates one frontend consumer.
