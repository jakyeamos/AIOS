---
title: Establish a Reproducible Baseline and Product Invariants
type: research
status: open
claim: unclaimed
blocked_by: []
blocks:
  - 002-choose-v2-operating-loop-and-trust-boundary
  - 003-define-canonical-state-and-migration-authority
  - 004-specify-task-centred-information-architecture-and-design-system
---

# Establish a Reproducible Baseline and Product Invariants

## Question

What does AIOS demonstrably do today, which user journeys and durable contracts
must survive a v2 modernization, and what failures already exist before any
new implementation begins?

## Scope

- Record the exact branch, dirty-worktree boundary, current commands, and
  baseline failures without attributing them to the modernization.
- Run the relevant Python, UI, context, and smoke checks; start the locally
  runnable product and exercise the daily loop where its data/configuration
  permits.
- Inventory user-facing journeys, state stores, mutation paths, public or
  external contracts, background jobs, and irreversible operations.
- Capture representative UI screenshots, browser/console evidence, and
  responsive/accessibility observations when the app can run locally.
- Produce evidence and a concise invariants list, not application-code edits.

## Known Leads

- The documented daily loop is `doctor → start-work → daily-flow → next-action
  → closeout`, while the dashboard currently presents many competing monitoring
  panels and the navigation exposes many equal-priority destinations.
- Main SQLite schema/migration ownership appears split between snapshot SQL,
  Python runtime DDL, and UI-side lazy schema creation.
- UI mutation routes currently assume a local trust boundary; hosting and
  operator-access assumptions need explicit verification before redesign.
- Business-memory sources may contain sensitive raw text, and provider egress
  must be checked against the stated privacy contract.

## Completion Evidence

- A dated baseline report with command results, known failures, journey matrix,
  state/contract inventory, and evidence links.
- A clear list of preserve, explicitly-migrate, and intentionally-retire
  candidates for the next decision.

## Resolution

Unresolved.
