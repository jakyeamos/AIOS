---
id: thin-display
title: Thin Display UI Purity
scope: domain-specific
blocking: false
evaluation_method: heuristic
version: 1.0
---

## Intent

Keep UI components focused on displaying prepared state while hooks, services, actions, and domain modules own behavior.

## Applies When

UI work that changes React, Next.js, dashboard, mobile, or other display-layer components.

## Required Checks

- Confirm JSX is mostly rendering prepared state.
- Keep fetches, mutations, permissions, and domain rules out of display components.
- Perform transformations before render when practical.
- Preserve readable conditionals and state branching.
- Include loading, error, and empty states where the surface needs them.
- Confirm the display can be tested without mocking the whole application.

## Blockers

- Display component takes ownership of database/API IO, permissions, or business rules.
- Critical UI state has no loading, error, or empty path.
- UI change becomes untestable without full-app mocking.

## Warnings

- Component is somewhat fat but still locally understandable.
- Minor transformation logic remains in render.
- Non-core UI lacks a complete state set.

## Evidence To Provide

- Logic found in display components.
- Hook/service/action extraction considered.
- Missing state handling.
- Testability notes.

## Related Criteria

- `architecture-boundary`
- `accessibility`
- `performance-budget`

## Example Good

A component receives a prepared view model from a hook and renders state variants without owning fetch or permission logic.

## Example Bad

A component fetches data, validates permissions, reshapes records, writes mutations, and renders complex UI in one body.
