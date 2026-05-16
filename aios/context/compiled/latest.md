# AIOS Context Briefing

## Task Summary

Verify config agent rules are authoritative runtime context for AIOS sessions and workflow execution

## Task Classification

- Signals: all_tasks, task_changes_core_logic, task_touches_agent_harness, task_touches_auth, task_touches_context_compiler, task_touches_knowledge_system
- Domains: agent-harnesses, knowledge-systems

## Selected Context Files

- `router.md` (context.router) — Bootloader context is always loaded.
- `index.md` (context.index) — Bootloader context is always loaded.
- `standards/global.observability.md` (global.observability) — 2 applies_when signal(s) matched; 1 title/summary term(s) matched
- `standards/global.maintainability.md` (global.maintainability) — 2 applies_when signal(s) matched; 1 title/summary term(s) matched
- `config/agent-rules.md` (config.agent-rules) — 1 applies_when signal(s) matched; 4 tag(s) matched; 12 title/summary term(s) matched
- `standards/global.security.md` (global.security) — 1 applies_when signal(s) matched; 1 tag(s) matched; 2 title/summary term(s) matched
- `schema.md` (context.schema) — Bootloader context is always loaded.
- `standards/global.testing.md` (global.testing) — 1 applies_when signal(s) matched; 1 title/summary term(s) matched
- `standards/index.md` (standards.index) — 1 applies_when signal(s) matched; 1 title/summary term(s) matched
- `domains/agent-harnesses.md` (domains.agent-harnesses) — 2 applies_when signal(s) matched; 3 title/summary term(s) matched
- `domains/knowledge-systems.md` (domains.knowledge-systems) — 1 applies_when signal(s) matched
- `domains/index.md` (domains.index) — 1 applies_when signal(s) matched; 1 title/summary term(s) matched
- `projects/index.md` (projects.index) — 1 applies_when signal(s) matched; 3 title/summary term(s) matched
- `features/context-compiler.md` (features.context-compiler) — 2 applies_when signal(s) matched; 4 title/summary term(s) matched
- `features/skill-registry.md` (features.skill-registry) — 1 applies_when signal(s) matched; 3 title/summary term(s) matched
- `features/prompt-library.md` (features.prompt-library) — 1 applies_when signal(s) matched; 1 title/summary term(s) matched
- `features/obsidian-search.md` (features.obsidian-search) — 1 applies_when signal(s) matched; 1 title/summary term(s) matched
- `features/index.md` (features.index) — 1 applies_when signal(s) matched; 1 title/summary term(s) matched
- `packets/workflow.approval-gates.md` (packets.workflow.approval-gates) — 1 applies_when signal(s) matched; 1 tag(s) matched; 3 title/summary term(s) matched
- `packets/security.oidc-secrets.md` (packets.security.oidc-secrets) — Loaded because global.security matched and requested this packet.
- `packets/knowledge.obsidian-routing.md` (packets.knowledge.obsidian-routing) — Loaded because domains.knowledge-systems matched and requested this packet.
- `packets/maintainability.architecture-boundaries.md` (packets.maintainability.architecture-boundaries) — 1 applies_when signal(s) matched; 1 title/summary term(s) matched
- `handoffs/latest.md` (handoffs.latest) — Bootloader context is always loaded.

## Relevant Rules

- context.router: Agent bootloader for AIOS-managed projects and context receipts.
- context.index: Thin entrypoint for AIOS context routing and compiled briefing generation.
- global.observability: AIOS behavior should leave inspectable traces, receipts, and failure evidence.
- global.maintainability: Keep AIOS changes simple, bounded, readable, and aligned to existing architecture.
- config.agent-rules: Behavioral rules loaded for all AIOS agent sessions and workflow execution.
- global.security: Baseline security expectations for all AIOS-managed work.
- context.schema: Required schema for AIOS Context Compiler Markdown files.
- global.testing: Behavior must be validated with deterministic tests or equivalent execution evidence.
- standards.index: Index of global standards available to the Context Compiler.
- domains.agent-harnesses: Routing standard for agent workflows, prompts, packets, skills, and orchestration.
- domains.knowledge-systems: Routing standard for vault, retrieval, topic graph, and second-brain workflows.
- domains.index: Index of domain-specific standards that narrow global rules for task categories.
- projects.index: Index of project truth routing files for AIOS-managed work.
- features.context-compiler: Feature context for tiered Markdown routing, scoring, receipts, and writeback candidates.
- features.skill-registry: Feature context for installed skill discovery, sync, and agent workflow routing.
- features.prompt-library: Feature context for reusable prompt templates, validation, sync, and evaluation workflows.
- features.obsidian-search: Feature context for future Obsidian vault retrieval and graph-aware note routing.
- features.index: Index of feature packets available for task-specific routing.
- packets.workflow.approval-gates: Packet for approval-gated writebacks, major context changes, and reviewable proposals.
- packets.security.oidc-secrets: Deep-enough packet for routing deployment secret work toward short-lived OIDC credentials.
- packets.knowledge.obsidian-routing: Packet for treating Obsidian notes as graph nodes and loading MOCs before detailed notes.
- packets.maintainability.architecture-boundaries: Packet for preserving AIOS module and ownership boundaries during implementation.
- handoffs.latest: Current handoff node for the file-backed AIOS Context Compiler.

## Project State

- Project Context Index: Index of project truth routing files for AIOS-managed work.
- Latest Context Compiler Handoff: Current handoff node for the file-backed AIOS Context Compiler.

## Feature Context

- AIOS Context Compiler Feature: Feature context for tiered Markdown routing, scoring, receipts, and writeback candidates.
- Skill Registry Feature: Feature context for installed skill discovery, sync, and agent workflow routing.
- Prompt Library Feature: Feature context for reusable prompt templates, validation, sync, and evaluation workflows.
- Obsidian Search Feature: Feature context for future Obsidian vault retrieval and graph-aware note routing.
- Feature Context Index: Index of feature packets available for task-specific routing.
- Workflow Approval Gates Packet: Packet for approval-gated writebacks, major context changes, and reviewable proposals.
- OIDC Secretless Deployment Packet: Deep-enough packet for routing deployment secret work toward short-lived OIDC credentials.
- Obsidian Graph Routing Packet: Packet for treating Obsidian notes as graph nodes and loading MOCs before detailed notes.
- Architecture Boundaries Packet: Packet for preserving AIOS module and ownership boundaries during implementation.

## Known Risks

- No context-selection risks detected by the compiler.

## Acceptance Criteria

- context.router: Every non-trivial run has a loaded/skipped context receipt.
- context.router: Missing, stale, and conflicting context are explicit.
- context.router: Writebacks are proposed for missing rules or reusable patterns.
- context.index: Agents produce a context receipt before treating context selection as complete.
- context.index: Loaded context is explainable by task classification, score, or explicit linked packet.
- context.index: Skipped context remains visible in the receipt.
- global.observability: Generated receipts include loaded and skipped context.
- global.observability: Missing and stale context are visible as warnings.
- global.observability: Scoring decisions are preserved in structured output.
- global.observability: Error output includes remediation guidance that an agent can execute or propose as a follow-up.
- global.maintainability: New code has a narrow surface and deterministic behavior.
- global.maintainability: Recurring error surfaces are resolved with durable remediation or captured as explicit follow-up work.
- global.maintainability: Agent-facing files fit a bounded context budget, or document why the larger surface remains coherent.
- global.maintainability: Agent-facing artifacts preserve machine-readable structure before prose or visual presentation.
- global.maintainability: Project truth or handoff files reflect meaningful architecture changes.
- global.maintainability: Context routing remains auditable from receipt output.
- global.security: No new static secret path is introduced.
- global.security: Sensitive context is scoped to the task and receipt.
- global.security: Security tradeoffs are explicit writeback candidates when unresolved.
- context.schema: `pnpm context:validate` passes before a context file is treated as authoritative.
- context.schema: `load_if_matched` links point to existing files relative to `aios/context/`.
- context.schema: Thin routing files stay below the deep-packet threshold unless they declare a larger `token_budget`.
- global.testing: Schema validation is exercised against real Markdown files.
- global.testing: Routing tests assert selected files and receipt content.
- global.testing: Conflict precedence is covered by executable tests.
- standards.index: Every global standard has an owner, tags, and concrete applicability signals.
- standards.index: More specific context can add requirements but not weaken protected topics.
- domains.agent-harnesses: Routing decisions include reasons and skipped alternatives.
- domains.agent-harnesses: Prompt or skill changes include validation paths.
- domains.agent-harnesses: Repeated harness failures are promoted into durable standards, checks, or explicit backlog items.
- domains.agent-harnesses: Agent-facing files remain small enough for agents to load and reason over without losing local context.
- domains.agent-harnesses: Error records include parseable remediation steps.
- domains.agent-harnesses: Packet, prompt, and workflow surfaces preserve stable machine-readable fields when adding human-facing copy.
- domains.agent-harnesses: Writebacks are proposed for review rather than silently promoted.
- domains.knowledge-systems: Retrieval starts from routing nodes or explicit source refs.
- domains.knowledge-systems: Broad semantic search does not replace authoritative packet selection.
- domains.index: Domain context adds useful constraints beyond global standards.
- domains.index: Domain files remain thin enough to scan quickly.
- projects.index: Project context links to the durable truth source.
- projects.index: Missing project truth becomes a writeback candidate.
- features.context-compiler: Compilation produces structured JSON and agent-readable Markdown.
- features.context-compiler: Receipts include loaded, skipped, conflicts, missing context, and writebacks.
- features.context-compiler: Scoring favors specific, recent, authoritative, low-cost context.
- features.skill-registry: Skill routing remains inspectable and deterministic where possible.
- features.skill-registry: Missing skill metadata becomes a writeback candidate.
- features.prompt-library: New prompt workflows preserve frontmatter validation and registry generation.
- features.prompt-library: Evaluation output can be traced to prompt template IDs.
- features.obsidian-search: MOC notes are preferred as routing nodes.
- features.obsidian-search: Loaded notes and skipped clusters are auditable.
- features.obsidian-search: Vault search does not override authoritative project or global standards.
- features.index: Feature context loads only when task terms or linked context justify it.
- features.index: Missing feature files are proposed as writebacks.
- packets.workflow.approval-gates: Writeback candidates include type, severity, target file, and reason.
- packets.workflow.approval-gates: Approval needs are visible before promotion to authoritative context.
- packets.security.oidc-secrets: No static deployment secret is introduced as the default path.
- packets.security.oidc-secrets: Provider, subject, audience, and permission scope are explicit.
- packets.security.oidc-secrets: Exceptions include owner, reason, review date, and removal path.
- packets.knowledge.obsidian-routing: MOC notes act as routing nodes into deeper context.
- packets.knowledge.obsidian-routing: Backlink and tag traversal is receipt-backed.
- packets.knowledge.obsidian-routing: Broad vault search cannot weaken authoritative project or global rules.
- packets.maintainability.architecture-boundaries: New modules have a clear owner and caller.
- packets.maintainability.architecture-boundaries: Cross-layer changes are deliberate and documented.
- handoffs.latest: Update this handoff when compiler output shape or routing conventions change.
- handoffs.latest: Keep detailed implementation history in docs or project truth, not this routing node.

## Missing Context

- None.

## Writeback Candidates

- None.
