# AIOS Context Briefing

## Task Summary

Add a commit hook quality ladder that enforces AIOS standards before commits land

## Task Classification

- Signals: all_tasks
- Domains: none

## Selected Context Files

- `standards/global.maintainability.md` (global.maintainability) — 1 applies_when signal(s) matched; 2 title/summary term(s) matched
- `index.md` (context.index) — Bootloader context is always loaded.
- `schema.md` (context.schema) — Bootloader context is always loaded.
- `router.md` (context.router) — Bootloader context is always loaded.
- `config/agent-rules.md` (config.agent-rules) — 1 applies_when signal(s) matched; 2 title/summary term(s) matched
- `handoffs/latest.md` (handoffs.latest) — Bootloader context is always loaded.

## Relevant Rules

- global.maintainability: Keep AIOS changes simple, bounded, readable, and aligned to existing architecture.
- context.index: Thin entrypoint for AIOS context routing and compiled briefing generation.
- context.schema: Required schema for AIOS Context Compiler Markdown files.
- context.router: Agent bootloader for AIOS-managed projects and context receipts.
- config.agent-rules: Behavioral rules loaded for all AIOS agent sessions and workflow execution.
- handoffs.latest: Current handoff node for the file-backed AIOS Context Compiler.

## Project State

- Latest Context Compiler Handoff: Current handoff node for the file-backed AIOS Context Compiler.

## Feature Context

- None.

## Known Risks

- No context-selection risks detected by the compiler.

## Acceptance Criteria

- global.maintainability: New code has a narrow surface and deterministic behavior.
- global.maintainability: Expanded concepts update the original contract and stale generic names instead of leaving parallel, semantically overlapping APIs.
- global.maintainability: Existing call sites, tests, fixtures, docs, and persisted shapes are checked for implicit-default assumptions when a second variant is added.
- global.maintainability: Message/worker response code reflects the actual event-loop or runtime ordering guarantees instead of guarding against impossible races.
- global.maintainability: If a handler is registered before a send, the code or plan identifies a real reentrancy, synchronous callback, replay buffer, or platform-specific reason.
- global.maintainability: Recurring error surfaces are resolved with durable remediation or captured as explicit follow-up work.
- global.maintainability: Agent-facing files fit a bounded context budget, or document why the larger surface remains coherent.
- global.maintainability: Agent-facing artifacts preserve machine-readable structure before prose or visual presentation.
- global.maintainability: Project truth or handoff files reflect meaningful architecture changes.
- global.maintainability: Context routing remains auditable from receipt output.
- context.index: Agents produce a context receipt before treating context selection as complete.
- context.index: Loaded context is explainable by task classification, score, or explicit linked packet.
- context.index: Skipped context remains visible in the receipt.
- context.schema: `pnpm context:validate` passes before a context file is treated as authoritative.
- context.schema: `load_if_matched` links point to existing files relative to `aios/context/`.
- context.schema: Thin routing files stay below the deep-packet threshold unless they declare a larger `token_budget`.
- context.router: Every non-trivial run has a loaded/skipped context receipt.
- context.router: Missing, stale, and conflicting context are explicit.
- context.router: Writebacks are proposed for missing rules or reusable patterns.
- handoffs.latest: Update this handoff when compiler output shape or routing conventions change.
- handoffs.latest: Keep detailed implementation history in docs or project truth, not this routing node.

## Missing Context

- None.

## Writeback Candidates

- None.
