# AIOS Context Briefing

## Task Summary

Add make-interfaces-feel-better skill to AIOS skill graph

## Task Classification

- Signals: all_tasks, task_touches_agent_harness, task_touches_skill_registry
- Domains: agent-harnesses

## Selected Context Files

- `standards/global.observability.md` (global.observability) — 1 applies_when signal(s) matched; 1 title/summary term(s) matched
- `index.md` (context.index) — Bootloader context is always loaded.
- `schema.md` (context.schema) — Bootloader context is always loaded.
- `router.md` (context.router) — Bootloader context is always loaded.
- `standards/global.maintainability.md` (global.maintainability) — 1 applies_when signal(s) matched; 1 title/summary term(s) matched
- `config/agent-rules.md` (config.agent-rules) — 1 applies_when signal(s) matched; 2 title/summary term(s) matched
- `domains/agent-harnesses.md` (domains.agent-harnesses) — 2 applies_when signal(s) matched
- `features/skill-registry.md` (features.skill-registry) — 2 applies_when signal(s) matched; 3 title/summary term(s) matched
- `features/context-compiler.md` (features.context-compiler) — 1 applies_when signal(s) matched; 1 title/summary term(s) matched
- `features/prompt-library.md` (features.prompt-library) — 1 applies_when signal(s) matched
- `features/obsidian-search.md` (features.obsidian-search) — 1 tag(s) matched; 1 title/summary term(s) matched
- `packets/knowledge.obsidian-routing.md` (packets.knowledge.obsidian-routing) — Loaded because features.obsidian-search matched and requested this packet.
- `packets/workflow.approval-gates.md` (packets.workflow.approval-gates) — 1 applies_when signal(s) matched
- `handoffs/latest.md` (handoffs.latest) — Bootloader context is always loaded.

## Relevant Rules

- global.observability: AIOS behavior should leave inspectable traces, receipts, and failure evidence.
- context.index: Thin entrypoint for AIOS context routing and compiled briefing generation.
- context.schema: Required schema for AIOS Context Compiler Markdown files.
- context.router: Agent bootloader for AIOS-managed projects and context receipts.
- global.maintainability: Keep AIOS changes simple, bounded, readable, and aligned to existing architecture.
- config.agent-rules: Behavioral rules loaded for all AIOS agent sessions and workflow execution.
- domains.agent-harnesses: Routing standard for agent workflows, prompts, packets, skills, and orchestration.
- features.skill-registry: Feature context for installed skill discovery, sync, and agent workflow routing.
- features.context-compiler: Feature context for tiered Markdown routing, scoring, receipts, and writeback candidates.
- features.prompt-library: Feature context for reusable prompt templates, validation, sync, and evaluation workflows.
- features.obsidian-search: Feature context for future Obsidian vault retrieval and graph-aware note routing.
- packets.knowledge.obsidian-routing: Packet for treating Obsidian notes as graph nodes and loading MOCs before detailed notes.
- packets.workflow.approval-gates: Packet for approval-gated writebacks, major context changes, and reviewable proposals.
- handoffs.latest: Current handoff node for the file-backed AIOS Context Compiler.

## Project State

- Latest Context Compiler Handoff: Current handoff node for the file-backed AIOS Context Compiler.

## Feature Context

- Skill Registry Feature: Feature context for installed skill discovery, sync, and agent workflow routing.
- AIOS Context Compiler Feature: Feature context for tiered Markdown routing, scoring, receipts, and writeback candidates.
- Prompt Library Feature: Feature context for reusable prompt templates, validation, sync, and evaluation workflows.
- Obsidian Search Feature: Feature context for future Obsidian vault retrieval and graph-aware note routing.
- Obsidian Graph Routing Packet: Packet for treating Obsidian notes as graph nodes and loading MOCs before detailed notes.
- Workflow Approval Gates Packet: Packet for approval-gated writebacks, major context changes, and reviewable proposals.

## Known Risks

- No context-selection risks detected by the compiler.

## Acceptance Criteria

- global.observability: Generated receipts include loaded and skipped context.
- global.observability: Missing and stale context are visible as warnings.
- global.observability: Scoring decisions are preserved in structured output.
- global.observability: Error output includes remediation guidance that an agent can execute or propose as a follow-up.
- context.index: Agents produce a context receipt before treating context selection as complete.
- context.index: Loaded context is explainable by task classification, score, or explicit linked packet.
- context.index: Skipped context remains visible in the receipt.
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
- domains.agent-harnesses: Routing decisions include reasons and skipped alternatives.
- domains.agent-harnesses: Prompt or skill changes include validation paths.
- domains.agent-harnesses: Repeated harness failures are promoted into durable standards, checks, or explicit backlog items.
- domains.agent-harnesses: Agent-facing files remain small enough for agents to load and reason over without losing local context.
- domains.agent-harnesses: Error records include parseable remediation steps.
- domains.agent-harnesses: Packet, prompt, and workflow surfaces preserve stable machine-readable fields when adding human-facing copy.
- domains.agent-harnesses: Writebacks are proposed for review rather than silently promoted.
- domains.agent-harnesses: Non-trivial execution records whether direct execution or subagent execution was chosen and why.
- domains.agent-harnesses: Model or reasoning upgrades track whether extra cost produced meaningful quality improvement.
- features.skill-registry: Skill routing remains inspectable and deterministic where possible.
- features.skill-registry: Missing skill metadata becomes a writeback candidate.
- features.context-compiler: Compilation produces structured JSON and agent-readable Markdown.
- features.context-compiler: Receipts include loaded, skipped, conflicts, missing context, and writebacks.
- features.context-compiler: Scoring favors specific, recent, authoritative, low-cost context.
- features.prompt-library: New prompt workflows preserve frontmatter validation and registry generation.
- features.prompt-library: Evaluation output can be traced to prompt template IDs.
- features.obsidian-search: MOC notes are preferred as routing nodes.
- features.obsidian-search: Loaded notes and skipped clusters are auditable.
- features.obsidian-search: Vault search does not override authoritative project or global standards.
- packets.knowledge.obsidian-routing: MOC notes act as routing nodes into deeper context.
- packets.knowledge.obsidian-routing: Backlink and tag traversal is receipt-backed.
- packets.knowledge.obsidian-routing: Broad vault search cannot weaken authoritative project or global rules.
- packets.workflow.approval-gates: Writeback candidates include type, severity, target file, and reason.
- packets.workflow.approval-gates: Approval needs are visible before promotion to authoritative context.
- handoffs.latest: Update this handoff when compiler output shape or routing conventions change.
- handoffs.latest: Keep detailed implementation history in docs or project truth, not this routing node.

## Missing Context

- None.

## Writeback Candidates

- None.
