# AIOS Context Briefing

## Task Summary

Improve personalized humanizer as optional voice-specific pipeline step after generic humanizer cleanup

## Task Classification

- Signals: all_tasks, task_touches_user_data
- Domains: none

## Selected Context Files

- `standards/global.security.md` (global.security) — 1 applies_when signal(s) matched
- `schema.md` (context.schema) — Bootloader context is always loaded.
- `router.md` (context.router) — Bootloader context is always loaded.
- `standards/global.maintainability.md` (global.maintainability) — 1 applies_when signal(s) matched
- `index.md` (context.index) — Bootloader context is always loaded.
- `config/agent-rules.md` (config.agent-rules) — 1 applies_when signal(s) matched
- `packets/security.oidc-secrets.md` (packets.security.oidc-secrets) — Loaded because global.security matched and requested this packet.
- `handoffs/latest.md` (handoffs.latest) — Bootloader context is always loaded.

## Relevant Rules

- global.security: Baseline security expectations for all AIOS-managed work.
- context.schema: Required schema for AIOS Context Compiler Markdown files.
- context.router: Agent bootloader for AIOS-managed projects and context receipts.
- global.maintainability: Keep AIOS changes simple, bounded, readable, and aligned to existing architecture.
- context.index: Thin entrypoint for AIOS context routing and compiled briefing generation.
- config.agent-rules: Behavioral rules loaded for all AIOS agent sessions and workflow execution.
- packets.security.oidc-secrets: Deep-enough packet for routing deployment secret work toward short-lived OIDC credentials.
- handoffs.latest: Current handoff node for the file-backed AIOS Context Compiler.

## Project State

- Latest Context Compiler Handoff: Current handoff node for the file-backed AIOS Context Compiler.

## Feature Context

- OIDC Secretless Deployment Packet: Deep-enough packet for routing deployment secret work toward short-lived OIDC credentials.

## Known Risks

- No context-selection risks detected by the compiler.

## Acceptance Criteria

- global.security: No new static secret path is introduced.
- global.security: Sensitive context is scoped to the task and receipt.
- global.security: Security tradeoffs are explicit writeback candidates when unresolved.
- context.schema: `pnpm context:validate` passes before a context file is treated as authoritative.
- context.schema: `load_if_matched` links point to existing files relative to `aios/context/`.
- context.schema: Thin routing files stay below the deep-packet threshold unless they declare a larger `token_budget`.
- context.router: Every non-trivial run has a loaded/skipped context receipt.
- context.router: Missing, stale, and conflicting context are explicit.
- context.router: Writebacks are proposed for missing rules or reusable patterns.
- global.maintainability: New code has a narrow surface and deterministic behavior.
- global.maintainability: Recurring error surfaces are resolved with durable remediation or captured as explicit follow-up work.
- global.maintainability: Agent-facing files fit a bounded context budget, or document why the larger surface remains coherent.
- global.maintainability: Agent-facing artifacts preserve machine-readable structure before prose or visual presentation.
- global.maintainability: Project truth or handoff files reflect meaningful architecture changes.
- global.maintainability: Context routing remains auditable from receipt output.
- context.index: Agents produce a context receipt before treating context selection as complete.
- context.index: Loaded context is explainable by task classification, score, or explicit linked packet.
- context.index: Skipped context remains visible in the receipt.
- packets.security.oidc-secrets: No static deployment secret is introduced as the default path.
- packets.security.oidc-secrets: Provider, subject, audience, and permission scope are explicit.
- packets.security.oidc-secrets: Exceptions include owner, reason, review date, and removal path.
- handoffs.latest: Update this handoff when compiler output shape or routing conventions change.
- handoffs.latest: Keep detailed implementation history in docs or project truth, not this routing node.

## Missing Context

- None.

## Writeback Candidates

- None.
