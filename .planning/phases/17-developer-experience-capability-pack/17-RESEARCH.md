# Phase 17: Developer Experience Capability Pack - Research

**Gathered:** 2026-06-01
**Status:** Ready for planning

<source_spec>
## Source Spec

Phase 17 is specified in the pasted "Audit + Implement Prompt: Add Developer Experience Agent Pack to AIOS" ingested on 2026-06-01. The spec asks AIOS to audit its current architecture and implement the strongest ideas from Nick Nisi's `developer-experience` Claude plugin while adapting them to AIOS routing, telemetry, second-brain integration, shadow-branch testing, and model-agnostic execution philosophy.

The plugin is inspiration only. AIOS should not blindly copy static agent files or hardcoded model choices. The pack must become a measurable, routed, context-aware capability/workflow pack.
</source_spec>

<domain>
## Phase Boundary

Phase 17 creates a Developer Experience capability pack. It does not replace existing prompt, skill, workflow, eval, or routing systems.

It overlaps earlier phases but has a distinct domain boundary:

- Phase 8 owns lifecycle-managed prompts, skills, workflows, and asset promotion.
- Phase 14 owns complexity and simplification gates.
- Phase 15 owns external skill portfolio audit and skill-file integration.
- Phase 16 owns harness determinism, evidence, independent verification, and context manifests.

Phase 17 consumes those primitives to deliver a domain-specific DX pack covering repo onboarding, workflow friction, public interface ergonomics, README/docs quality, contextual security review, TypeScript specialist review, and spec-fidelity implementation routing.
</domain>

<placement_decision>
## Placement Decision

This work belongs in a new Phase 17 rather than inside Phase 8, 14, 15, or 16.

It is wider than Phase 15 because it is not just a skill import. It requires routing metadata, output schemas, modes, telemetry, eval fixtures, second-brain parity, and documentation. It is also more domain-specific than Phase 16: harness determinism should make this pack measurable and auditable, but DX capability design should remain its own phase.
</placement_decision>

<capabilities>
## Developer Experience Pack Capabilities

### DX Optimizer
Audits setup, commands, docs, validation loops, CI, local development, and common task flows. Produces measurable metrics when possible, friction points, quick wins, larger improvements, and a priority matrix.

### Interface DX Reviewer
Reviews public APIs, SDKs, CLIs, config schemas, developer-facing errors, examples, and migration paths from the consumer perspective.

### Documentation Writer
Creates authentic developer-first documentation. Avoids marketing copy, starts with what the project actually does, shows working examples, documents limitations, and includes validation commands where applicable.

### Security Reviewer
Performs contextual security review across permissions, secrets, auth/authz, dependencies, tool/MCP/agent access, shell/network/filesystem risk, CI/CD, logging, privacy, and SSRF where relevant. It must not dump generic OWASP text as final output.

### TypeScript Specialist
Invoked only when TypeScript complexity justifies it: public TypeScript APIs, inference quality, strict compiler issues, package boundaries, monorepo tooling, or typecheck/build performance.

### Spec-Fidelity Coder
Implements from PRDs, ADRs, design specs, issues, and acceptance criteria. It extracts requirements, maps files, respects architecture, keeps diffs small, updates tests/docs, and logs assumptions. It stops only for destructive, security-sensitive, permission-sensitive, data-loss, broad architecture, or explicitly approval-gated decisions.
</capabilities>

<requirements>
## Phase 17 Requirements

### DXPK-01: Existing DX Infrastructure Audit
AIOS must audit where skills, agents, commands, routing rules, telemetry, eval specs, shadow-branch testing, second-brain integration, documentation, generated concepts, and quality gates currently live. The audit must identify equivalents, duplication risks, conventions, proposed files, risks, and implementation plan.

### DXPK-02: Capability Pack Contract
AIOS must define a Developer Experience capability pack with six capabilities: DX optimizer, interface DX reviewer, documentation writer, security reviewer, TypeScript specialist, and spec-fidelity coder. Each capability must define purpose, responsibilities, invocation triggers, compact/full/review/implementation modes as applicable, required output schemas, assumptions policy, and evidence expectations.

### DXPK-03: Measurable DX Metrics
The pack must measure or explicitly mark as not measured: clone-to-running-app time, setup time, dev server startup, hot reload/feedback loop speed, unit test runtime, typecheck runtime, lint runtime, build runtime, CI runtime, manual setup steps, validation command count, README quickstart presence, setup validation presence, ambiguous developer instructions, and agent/token cost where telemetry supports it.

### DXPK-04: Routing And Mode Selection
AIOS must add routing metadata or logic so each capability is invoked only when justified. Routing must support compact audit, full audit, implementation, and review-only modes, and must include dynamic model/reasoning metadata instead of fixed model-per-agent choices.

### DXPK-05: Second-Brain And Peer-Run Parity
The DX pack must work with `second_brain_available: true` and `second_brain_available: false`. When available, second-brain context can provide project conventions, prior decisions, known pain points, and workflow preferences. Peer-run workflows must fall back to repo-local artifacts only.

### DXPK-06: Contextual Quality And Security Gates
The pack must integrate with existing quality, security, TypeScript, docs, and implementation workflows without checklist bloat. Security review must be contextual. TypeScript specialist review must be targeted. Docs output must avoid marketing fluff.

### DXPK-07: DX Evaluation Fixtures
AIOS must add DX eval coverage with at least three fixture scenarios: poor onboarding repo, public CLI change, and TypeScript package boundary change. Evals must test routing, metrics, README clarity, interface review, contextual security review, TypeScript specialist invocation discipline, assumption logging, second-brain and no-second-brain modes, small diffs, and before/after metrics where possible.

### DXPK-08: Documentation And Validation Workflow
AIOS must document what the Developer Experience pack is, when each capability is invoked, how it differs from static prompts, how it supports shadow-branch testing and second-brain parity, how metrics and model routing work, and how to disable or override recommendations. Final validation must report tests/lint/typecheck/AIOS validation commands run or why they could not run.
</requirements>

<plan_sequence>
## Recommended Plan Sequence

- **17-01**: Audit current AIOS DX-relevant infrastructure and duplication risks.
- **17-02**: Design capability contracts, modes, output schemas, metrics, and second-brain parity.
- **17-03**: Implement capability assets and routing metadata.
- **17-04**: Add dynamic model/reasoning routing and compact/full/review/implementation mode selection.
- **17-05**: Add DX eval hooks and fixture scenarios.
- **17-06**: Add developer-first documentation and validation/reporting workflow.
</plan_sequence>

<implementation_constraints>
## Implementation Constraints

- Do not create a parallel architecture if AIOS already has a skill, agent, prompt, workflow, or plugin system.
- Do not hardcode one model per agent unless the existing repo architecture requires it.
- Do not add huge context-heavy prompts without compact modes.
- Do not remove existing user workflow rules.
- Do not make peer-run testing depend on the user's second brain.
- Do not use generic security checklists as final output.
- Do not overfit TypeScript strictness for simple tasks.
- Do not ask for clarification unless the decision is high-risk or irreversible.
- Prefer small, reviewable diffs.
- Preserve existing repo style and package-management rules.
</implementation_constraints>
