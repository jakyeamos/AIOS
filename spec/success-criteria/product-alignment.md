---
id: product-alignment
title: Product Alignment and Scope Discipline
scope: task-type
blocking: false
evaluation_method: heuristic
version: 1.0
---

## Intent

Prevent technically valid changes from drifting away from the requested outcome, PRD, or project philosophy.

## Applies When

Planning, implementation, refactor, review, and UI/product tasks where user promise, workflow shape, feature scope, or project-specific philosophy matters.

## Required Checks

- Compare delivered outcome with the requested outcome.
- Check against PRD, project truth, roadmap, or relevant design packet.
- Identify unrequested features or behavior changes.
- Preserve the project-specific product principles.
- Record any scope expansion as a tradeoff or follow-up.

## Blockers

- Delivered behavior contradicts the requested outcome or source PRD.
- Scope drift changes the user promise or primary workflow without approval.
- Project-specific philosophy is violated on a core path.

## Warnings

- Minor scope expansion is useful but should be explicitly documented.
- Product source is stale or incomplete.
- Non-core behavior needs later alignment review.

## Evidence To Provide

- Requested outcome.
- Delivered outcome.
- Source PRD/project truth checked.
- Scope drift found or ruled out.

## Related Criteria

- `simplicity`
- `accessibility`
- `agent-claim-verification`

## Example Good

A fix repairs the requested workflow, avoids unrelated redesign, and cites the project truth constraint it preserved.

## Example Bad

A bugfix adds a new dashboard mode and changes navigation without being asked.
