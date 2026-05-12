# AIOS Context Briefing

## Task Summary

Improve the AIOS UI health score system so standards deltas are clearer and users can drill into critical deltas.

## Task Classification

- Signals: all_tasks, task_changes_core_logic, task_touches_aios_ui, task_touches_design, task_touches_observability, task_touches_product_design, task_touches_standards_delta, task_touches_web_app
- Domains: web-apps, product-design

## Selected Context Files

- `standards/global.design.md` (global.design) — 2 applies_when signal(s) matched; 1 tag(s) matched; 3 title/summary term(s) matched
- `standards/global.observability.md` (global.observability) — 2 applies_when signal(s) matched; 2 title/summary term(s) matched
- `standards/global.maintainability.md` (global.maintainability) — 2 applies_when signal(s) matched; 2 title/summary term(s) matched
- `standards/global.testing.md` (global.testing) — 1 applies_when signal(s) matched; 1 title/summary term(s) matched
- `schema.md` (context.schema) — Bootloader context is always loaded.
- `index.md` (context.index) — Bootloader context is always loaded.
- `router.md` (context.router) — Bootloader context is always loaded.
- `domains/web-apps.md` (domains.web-apps) — 2 applies_when signal(s) matched; 2 title/summary term(s) matched
- `domains/product-design.md` (domains.product-design) — 2 applies_when signal(s) matched; 2 title/summary term(s) matched
- `projects/aios-ui.md` (projects.aios-ui) — 4 applies_when signal(s) matched; 2 tag(s) matched; 3 title/summary term(s) matched
- `features/standards-delta.md` (features.standards-delta) — 3 applies_when signal(s) matched; 3 tag(s) matched; 10 title/summary term(s) matched
- `packets/ui.command-center.md` (packets.ui.command-center) — Loaded because features.standards-delta matched and requested this packet.
- `packets/maintainability.architecture-boundaries.md` (packets.maintainability.architecture-boundaries) — 1 applies_when signal(s) matched; 1 title/summary term(s) matched
- `handoffs/latest.md` (handoffs.latest) — Bootloader context is always loaded.

## Relevant Rules

- global.design: AIOS UI should expose system state clearly without decorative or low-density surfaces.
- global.observability: AIOS behavior should leave inspectable traces, receipts, and failure evidence.
- global.maintainability: Keep AIOS changes simple, bounded, readable, and aligned to existing architecture.
- global.testing: Behavior must be validated with deterministic tests or equivalent execution evidence.
- context.schema: Required schema for AIOS Context Compiler Markdown files.
- context.index: Thin entrypoint for AIOS context routing and compiled briefing generation.
- context.router: Agent bootloader for AIOS-managed projects and context receipts.
- domains.web-apps: Routing standard for Next.js, React, dashboard, and deployment work.
- domains.product-design: Routing standard for product UX, operational workflows, and explainable surfaces.
- projects.aios-ui: Project truth routing for the local AIOS Next.js command center.
- features.standards-delta: Feature context for project health scores, standards deltas, and critical-delta drilldowns.
- packets.ui.command-center: UI packet for exposing AIOS operational state, drilldowns, receipts, and warnings.
- packets.maintainability.architecture-boundaries: Packet for preserving AIOS module and ownership boundaries during implementation.
- handoffs.latest: Current handoff node for the file-backed AIOS Context Compiler.

## Project State

- AIOS UI Project Context: Project truth routing for the local AIOS Next.js command center.
- Latest Context Compiler Handoff: Current handoff node for the file-backed AIOS Context Compiler.

## Feature Context

- Standards Delta Health Feature: Feature context for project health scores, standards deltas, and critical-delta drilldowns.
- AIOS Command Center UI Packet: UI packet for exposing AIOS operational state, drilldowns, receipts, and warnings.
- Architecture Boundaries Packet: Packet for preserving AIOS module and ownership boundaries during implementation.

## Known Risks

- No context-selection risks detected by the compiler.

## Acceptance Criteria

- global.design: Users can inspect why a score, warning, or packet was produced.
- global.design: Critical states are not collapsed into vague healthy/unhealthy labels.
- global.design: Controls match expected operational workflows.
- global.observability: Generated receipts include loaded and skipped context.
- global.observability: Missing and stale context are visible as warnings.
- global.observability: Scoring decisions are preserved in structured output.
- global.maintainability: New code has a narrow surface and deterministic behavior.
- global.maintainability: Project truth or handoff files reflect meaningful architecture changes.
- global.maintainability: Context routing remains auditable from receipt output.
- global.testing: Schema validation is exercised against real Markdown files.
- global.testing: Routing tests assert selected files and receipt content.
- global.testing: Conflict precedence is covered by executable tests.
- context.schema: `pnpm context:validate` passes before a context file is treated as authoritative.
- context.schema: `load_if_matched` links point to existing files relative to `aios/context/`.
- context.schema: Thin routing files stay below the deep-packet threshold unless they declare a larger `token_budget`.
- context.index: Agents produce a context receipt before treating context selection as complete.
- context.index: Loaded context is explainable by task classification, score, or explicit linked packet.
- context.index: Skipped context remains visible in the receipt.
- context.router: Every non-trivial run has a loaded/skipped context receipt.
- context.router: Missing, stale, and conflicting context are explicit.
- context.router: Writebacks are proposed for missing rules or reusable patterns.
- domains.web-apps: User-facing state is source-backed and inspectable.
- domains.web-apps: UI changes follow the existing component and routing patterns.
- domains.product-design: Important system state can be inspected without reading logs.
- domains.product-design: Warnings and blockers are visually distinct and textually precise.
- projects.aios-ui: Project health and delta UI stays source-backed.
- projects.aios-ui: New UI surfaces can explain missing, inferred, or conflicting signals.
- projects.aios-ui: Meaningful architecture changes update `PROJECT.md`.
- features.standards-delta: Health score explanations point to source-backed delta records.
- features.standards-delta: Unknown and missing states remain visible.
- features.standards-delta: Critical deltas can be inspected by domain, severity, and remediation path.
- packets.ui.command-center: Operators can drill into source-backed evidence.
- packets.ui.command-center: Missing and conflicting state appears as actionable warnings.
- packets.ui.command-center: Receipts can later be attached to run history.
- packets.maintainability.architecture-boundaries: New modules have a clear owner and caller.
- packets.maintainability.architecture-boundaries: Cross-layer changes are deliberate and documented.
- handoffs.latest: Update this handoff when compiler output shape or routing conventions change.
- handoffs.latest: Keep detailed implementation history in docs or project truth, not this routing node.

## Missing Context

- None.

## Writeback Candidates

- None.
