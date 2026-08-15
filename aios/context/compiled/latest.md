# AIOS Context Briefing

## Task Summary

Reconcile AIOS context compiler contracts and quality gates

## Task Classification

- Signals: all_tasks, task_changes_core_logic, task_touches_agent_harness, task_touches_context_compiler, task_touches_knowledge_system, task_touches_permissions
- Domains: agent-harnesses, knowledge-systems

## Selected Context Files

- `.context/README.md` (context.module-index) — 1 applies_when signal(s) matched; 2 tag(s) matched; 6 title/summary term(s) matched
- `index.md` (context.index) — Bootloader context is always loaded.
- `standards/global.observability.md` (global.observability) — 2 applies_when signal(s) matched; 1 title/summary term(s) matched
- `standards/global.maintainability.md` (global.maintainability) — 2 applies_when signal(s) matched; 1 title/summary term(s) matched
- `schema.md` (context.schema) — Bootloader context is always loaded.
- `router.md` (context.router) — Bootloader context is always loaded.
- `standards/index.md` (standards.index) — 1 applies_when signal(s) matched; 2 title/summary term(s) matched
- `standards/global.security.md` (global.security) — 1 applies_when signal(s) matched; 1 title/summary term(s) matched
- `standards/global.testing.md` (global.testing) — 1 applies_when signal(s) matched
- `config/agent-rules.md` (config.agent-rules) — 1 applies_when signal(s) matched; 2 title/summary term(s) matched
- `domains/agent-harnesses.md` (domains.agent-harnesses) — 2 applies_when signal(s) matched
- `domains/knowledge-systems.md` (domains.knowledge-systems) — 1 applies_when signal(s) matched
- `domains/index.md` (domains.index) — 1 applies_when signal(s) matched
- `.agents/context/context-compiler.md` (repo.context.compiler) — 1 tag(s) matched; 8 title/summary term(s) matched; colocated path matched task text
- `projects/index.md` (projects.index) — 1 applies_when signal(s) matched; 3 title/summary term(s) matched
- `features/context-compiler.md` (features.context-compiler) — 2 applies_when signal(s) matched; 1 tag(s) matched; 6 title/summary term(s) matched
- `features/prompt-library.md` (features.prompt-library) — 1 applies_when signal(s) matched; 1 title/summary term(s) matched
- `features/obsidian-search.md` (features.obsidian-search) — 1 applies_when signal(s) matched; 1 title/summary term(s) matched
- `features/index.md` (features.index) — 1 applies_when signal(s) matched; 1 title/summary term(s) matched
- `features/skill-registry.md` (features.skill-registry) — 1 applies_when signal(s) matched; 1 title/summary term(s) matched
- `packets/workflow.approval-gates.md` (packets.workflow.approval-gates) — 2 applies_when signal(s) matched; 3 title/summary term(s) matched
- `packets/knowledge.notebooklm-routing.md` (packets.knowledge.notebooklm-routing) — Loaded because domains.knowledge-systems matched and requested this packet.
- `packets/workflow.durable-agent-workflows.md` (packets.workflow.durable-agent-workflows) — Loaded because domains.agent-harnesses matched and requested this packet.
- `packets/knowledge.obsidian-routing.md` (packets.knowledge.obsidian-routing) — Loaded because domains.knowledge-systems matched and requested this packet.
- `packets/maintainability.architecture-boundaries.md` (packets.maintainability.architecture-boundaries) — 1 applies_when signal(s) matched; 1 title/summary term(s) matched
- `packets/security.oidc-secrets.md` (packets.security.oidc-secrets) — Loaded because global.security matched and requested this packet.
- `handoffs/latest.md` (handoffs.latest) — Bootloader context is always loaded.

## Relevant Rules

- context.module-index: Colocated module index for the AIOS context compiler tree.
- context.index: Thin entrypoint for AIOS context routing and compiled briefing generation.
- global.observability: AIOS behavior should leave inspectable traces, receipts, and failure evidence.
- global.maintainability: Keep AIOS changes simple, bounded, readable, and aligned to existing architecture.
- context.schema: Required schema for AIOS Context Compiler Markdown files.
- context.router: Agent bootloader for AIOS-managed projects and context receipts.
- standards.index: Index of global standards available to the Context Compiler.
- global.security: Baseline security expectations for all AIOS-managed work.
- global.testing: Behavior must be validated with deterministic tests or equivalent execution evidence.
- config.agent-rules: Behavioral rules loaded for all AIOS agent sessions and workflow execution.
- domains.agent-harnesses: Routing standard for agent workflows, prompts, packets, skills, and orchestration.
- domains.knowledge-systems: Routing standard for vault, retrieval, topic graph, and second-brain workflows.
- domains.index: Index of domain-specific standards that narrow global rules for task categories.
- repo.context.compiler: Colocated context for AIOS context compiler.
- projects.index: Index of optional project-context routing files for AIOS-managed work.
- features.context-compiler: Feature context for tiered Markdown routing, scoring, receipts, and writeback candidates.
- features.prompt-library: Feature context for reusable prompt templates, validation, sync, and evaluation workflows.
- features.obsidian-search: Feature context for future Obsidian vault retrieval and graph-aware note routing.
- features.index: Index of feature packets available for task-specific routing.
- features.skill-registry: Feature context for installed skill discovery, sync, and agent workflow routing.
- packets.workflow.approval-gates: Packet for approval-gated writebacks, major context changes, and reviewable proposals.
- packets.knowledge.notebooklm-routing: Packet for routing bounded source synthesis and second-brain connection discovery through optional NotebookLM MCP.
- packets.workflow.durable-agent-workflows: Packet for long-running durable agent workspaces, goal verifiers, steering, queueing, artifacts, automation, memory, and skill candidacy.
- packets.knowledge.obsidian-routing: Packet for treating Obsidian notes as graph nodes and loading MOCs before detailed notes.
- packets.maintainability.architecture-boundaries: Packet for preserving AIOS module and ownership boundaries during implementation.
- packets.security.oidc-secrets: Deep-enough packet for routing deployment secret work toward short-lived OIDC credentials.
- handoffs.latest: Current handoff node for the file-backed AIOS Context Compiler.

## Project State

- Context Compiler: Colocated context for AIOS context compiler.
- Project Context Index: Index of optional project-context routing files for AIOS-managed work.
- Latest Context Compiler Handoff: Current handoff node for the file-backed AIOS Context Compiler.

## Feature Context

- AIOS Context Compiler Feature: Feature context for tiered Markdown routing, scoring, receipts, and writeback candidates.
- Prompt Library Feature: Feature context for reusable prompt templates, validation, sync, and evaluation workflows.
- Obsidian Search Feature: Feature context for future Obsidian vault retrieval and graph-aware note routing.
- Feature Context Index: Index of feature packets available for task-specific routing.
- Skill Registry Feature: Feature context for installed skill discovery, sync, and agent workflow routing.
- Workflow Approval Gates Packet: Packet for approval-gated writebacks, major context changes, and reviewable proposals.
- NotebookLM Bounded Synthesis Routing Packet: Packet for routing bounded source synthesis and second-brain connection discovery through optional NotebookLM MCP.
- Durable Agent Workflows Packet: Packet for long-running durable agent workspaces, goal verifiers, steering, queueing, artifacts, automation, memory, and skill candidacy.
- Obsidian Graph Routing Packet: Packet for treating Obsidian notes as graph nodes and loading MOCs before detailed notes.
- Architecture Boundaries Packet: Packet for preserving AIOS module and ownership boundaries during implementation.
- OIDC Secretless Deployment Packet: Deep-enough packet for routing deployment secret work toward short-lived OIDC credentials.

## Known Risks

- No context-selection risks detected by the compiler.

## Acceptance Criteria

- context.index: Agents produce a context receipt before treating context selection as complete.
- context.index: Loaded context is explainable by task classification, score, or explicit linked packet.
- context.index: Skipped context remains visible in the receipt.
- global.observability: Generated receipts include loaded and skipped context.
- global.observability: Missing and stale context are visible as warnings.
- global.observability: Scoring decisions are preserved in structured output.
- global.observability: Error output includes remediation guidance that an agent can execute or propose as a follow-up.
- global.maintainability: New code has a narrow surface and deterministic behavior.
- global.maintainability: Expanded concepts update the original contract and stale generic names instead of leaving parallel, semantically overlapping APIs.
- global.maintainability: Existing call sites, tests, fixtures, docs, and persisted shapes are checked for implicit-default assumptions when a second variant is added.
- global.maintainability: Message/worker response code reflects the actual event-loop or runtime ordering guarantees instead of guarding against impossible races.
- global.maintainability: If a handler is registered before a send, the code or plan identifies a real reentrancy, synchronous callback, replay buffer, or platform-specific reason.
- global.maintainability: Recurring error surfaces are resolved with durable remediation or captured as explicit follow-up work.
- global.maintainability: Agent-facing files fit a bounded context budget, or document why the larger surface remains coherent.
- global.maintainability: Agent-facing artifacts preserve machine-readable structure before prose or visual presentation.
- global.maintainability: Handoff or optional project-context files reflect meaningful architecture changes when those files are in scope.
- global.maintainability: Context routing remains auditable from receipt output.
- context.schema: `pnpm context:validate` passes before a context file is treated as authoritative.
- context.schema: `load_if_matched` links point to existing files relative to `aios/context/`.
- context.schema: Thin routing files stay below the deep-packet threshold unless they declare a larger `token_budget`.
- context.router: Every non-trivial run has a loaded/skipped context receipt.
- context.router: Missing, stale, and conflicting context are explicit.
- context.router: Writebacks are proposed for missing rules or reusable patterns.
- standards.index: Every global standard has an owner, tags, and concrete applicability signals.
- standards.index: More specific context can add requirements but not weaken protected topics.
- global.security: No new static secret path is introduced.
- global.security: Sensitive context is scoped to the task and receipt.
- global.security: Security tradeoffs are explicit writeback candidates when unresolved.
- global.testing: Schema validation is exercised against real Markdown files.
- global.testing: Routing tests assert selected files and receipt content.
- global.testing: Conflict precedence is covered by executable tests.
- global.testing: New tests protect behavior, public contracts, domain logic, or confirmed regressions; brittle static render/copy assertions are omitted unless their value is documented.
- domains.agent-harnesses: Routing decisions include reasons and skipped alternatives.
- domains.agent-harnesses: Prompt or skill changes include validation paths.
- domains.agent-harnesses: Repeated harness failures are promoted into durable standards, checks, or explicit backlog items.
- domains.agent-harnesses: Agent-facing files remain small enough for agents to load and reason over without losing local context.
- domains.agent-harnesses: Error records include parseable remediation steps.
- domains.agent-harnesses: Packet, prompt, and workflow surfaces preserve stable machine-readable fields when adding human-facing copy.
- domains.agent-harnesses: Writebacks are proposed for review rather than silently promoted.
- domains.agent-harnesses: Non-trivial execution records whether direct execution or subagent execution was chosen and why.
- domains.agent-harnesses: Model or reasoning upgrades track whether extra cost produced meaningful quality improvement.
- domains.agent-harnesses: Durable work records the active goal, verifier, declared surfaces, steering events, queued work, artifacts, memory updates, and next action outside the chat transcript.
- domains.knowledge-systems: Retrieval starts from routing nodes or explicit source refs.
- domains.knowledge-systems: Broad semantic search does not replace authoritative packet selection.
- domains.knowledge-systems: NotebookLM synthesis, when used, runs on bounded source bundles and stages output before promotion.
- domains.index: Domain context adds useful constraints beyond global standards.
- domains.index: Domain files remain thin enough to scan quickly.
- projects.index: Project context links to the durable truth source.
- projects.index: Missing optional project context is not a blocker; add a writeback only when it would prevent a real recurring failure.
- features.context-compiler: Compilation produces structured JSON and agent-readable Markdown.
- features.context-compiler: Receipts include loaded, skipped, conflicts, missing context, and writebacks.
- features.context-compiler: Scoring favors specific, recent, authoritative, low-cost context.
- features.prompt-library: New prompt workflows preserve frontmatter validation and registry generation.
- features.prompt-library: Evaluation output can be traced to prompt template IDs.
- features.obsidian-search: MOC notes are preferred as routing nodes.
- features.obsidian-search: Loaded notes and skipped clusters are auditable.
- features.obsidian-search: Vault search does not override authoritative project or global standards.
- features.index: Feature context loads only when task terms or linked context justify it.
- features.index: Missing feature files are proposed as writebacks.
- features.skill-registry: Skill routing remains inspectable and deterministic where possible.
- features.skill-registry: Missing skill metadata becomes a writeback candidate.
- packets.workflow.approval-gates: Writeback candidates include type, severity, target file, and reason.
- packets.workflow.approval-gates: Approval needs are visible before promotion to authoritative context.
- packets.knowledge.notebooklm-routing: Source bundles are bounded and explicit before NotebookLM is used.
- packets.knowledge.notebooklm-routing: Local retrieval runs before NotebookLM for second-brain source selection.
- packets.knowledge.notebooklm-routing: NotebookLM output is staged before promotion.
- packets.knowledge.notebooklm-routing: Raw operational memory and sensitive sources are excluded by default.
- packets.knowledge.notebooklm-routing: Experimental backend readiness is checked before live NotebookLM routing.
- packets.knowledge.notebooklm-routing: Automated CLI use records provenance and stages output instead of promoting directly.
- packets.workflow.durable-agent-workflows: Durable workspace state records decisions, blockers, owners, dates, useful links, verification status, known pitfalls, and next actions.
- packets.workflow.durable-agent-workflows: Goals include verifiers and explicit stopping conditions.
- packets.workflow.durable-agent-workflows: Steering preserves the active goal unless explicitly changed.
- packets.workflow.durable-agent-workflows: Queued work waits for the current checkpoint and is visible in durable state.
- packets.workflow.durable-agent-workflows: Allowed and out-of-scope work surfaces are declared.
- packets.workflow.durable-agent-workflows: Substantial work has a reviewable artifact when a transcript would be insufficient.
- packets.workflow.durable-agent-workflows: Automation mode is labeled as scheduled fresh work or context-preserving workspace wakeup.
- packets.workflow.durable-agent-workflows: Skill candidacy is based on repeated evidence, not generic preference language.
- packets.knowledge.obsidian-routing: MOC notes act as routing nodes into deeper context.
- packets.knowledge.obsidian-routing: Backlink and tag traversal is receipt-backed.
- packets.knowledge.obsidian-routing: Broad vault search cannot weaken authoritative project or global rules.
- packets.maintainability.architecture-boundaries: New modules have a clear owner and caller.
- packets.maintainability.architecture-boundaries: Cross-layer changes are deliberate and documented.
- packets.security.oidc-secrets: No static deployment secret is introduced as the default path.
- packets.security.oidc-secrets: Provider, subject, audience, and permission scope are explicit.
- packets.security.oidc-secrets: Exceptions include owner, reason, review date, and removal path.
- handoffs.latest: Update this handoff when compiler output shape or routing conventions change.
- handoffs.latest: Keep detailed implementation history in docs or optional project context, not this routing node.

## Missing Context

- None.

## Writeback Candidates

- None.
