---
title: Specify a Task-Centred Information Architecture and Accessible Design System
type: prototype
status: resolved
claim: /root (2026-07-13)
blocked_by: []
blocks:
  - 006-write-v2-target-and-vertical-modernization-plan
---

# Specify a Task-Centred Information Architecture and Accessible Design System

## Question

How should the chosen v2 operating loop appear as an agent/operator experience
with clear task modes, disciplined navigation, evidence visibility, and
accessible responsive interaction?

## Scope

- Turn the operating loop into a small set of primary modes and contextual
  drill-downs; decide which current pages merge, move, or retire.
- Establish a coherent accessible design-system contract for tokens,
  typography, semantic controls/tables, focus behavior, labels, error/loading
  states, keyboard interactions, contrast, and responsive layouts.
- Prototype the `start work → verify → gated review → closeout → daily flow /
  next action` vertical slice before redesigning every route.
- Define browser, keyboard, console, screenshot, and responsive proof needed
  for later UI milestones.

## Completion Evidence

- A target information architecture with preservation/retirement mapping for
  current routes.
- Representative visual or coded prototype screens for the core vertical slice.
- An accessibility and visual-regression acceptance matrix.

## Dependencies

Blocked by [Establish a Reproducible Baseline and Product Invariants](001-establish-reproducible-baseline-and-invariants.md) and [Choose the V2 Operating Loop and Trust Boundary](002-choose-v2-operating-loop-and-trust-boundary.md).

## Resolution

Accepted [ADR-003](../../../docs/modernization/ADR-003-task-centred-ia-and-accessible-design-system.md)
as the v2 operator-experience contract. The primary surface is now Today →
Start work → Current run → Verify → Gated review → Closeout, with daily flow
and next action returning the operator to Today. Current routes have an
explicit preserve/merge/demote/retire disposition, and the first vertical
slice has representative structural prototypes, required state coverage,
semantic interaction rules, responsive behavior, and an executable browser,
keyboard, accessibility, console, and evidence matrix. Implementation remains
gated by Ticket 007's reproducible UI validation contract and Ticket 005's
subsystem strategy.
