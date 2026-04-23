# AIOS Architecture Enforcement — Dependency Cruiser + Lint Audit + Implementation Prompt

**Date:** 2026-04-22
**Status:** Ready to run
**Type:** Audit + implementation prompt
**Author:** jakyeamos

---

## Purpose

Turn AIOS's intended architecture into executable rules. Make architectural drift difficult, obvious, and CI-blocking. Use Dependency Cruiser for dependency-boundary enforcement and Biome/lint-based checks for import, layering, naming, and policy rules.

**Primary outcome:** Enforce architecture by tooling instead of docs or convention.

---

## Prompt

You are implementing machine-enforced architectural constraints in the AIOS codebase.

Goal:
Make AIOS architecture enforceable by tooling instead of relying on docs or convention. Use Dependency Cruiser for dependency-boundary enforcement and Biome/lint-based checks for import, layering, naming, and policy rules. The result should make architectural drift difficult, obvious, and CI-blocking when appropriate.

Primary outcome:
Turn AIOS's intended architecture into executable rules.

Context:
AIOS is evolving into a durable orchestration and command-center system. Maintainability, modularity, observability, and agent-safe structure matter more than clever shortcuts. This implementation should support long-term growth, sub-agent-driven development, experimentation systems, UI visibility, and clean separation of concerns.

Instructions:
1. Audit the current repo structure before changing anything.
2. Infer the existing architectural layers, module boundaries, and likely failure points.
3. Propose a target rule set that reflects how the repo should be organized going forward.
4. Implement enforcement using the strongest available mechanism:
   - Use Dependency Cruiser for cross-folder/module dependency constraints
   - Use Biome where it can enforce policy cleanly
   - If Biome cannot realistically express a rule, use an appropriate lint/custom validation mechanism instead of faking it
5. Prefer real enforcement over aspirational comments.
6. Keep the implementation understandable and maintainable by future agents.
7. Do not introduce heavy complexity unless it clearly improves enforcement quality.

---

### Audit Objectives

Find in the current repo:
- Current top-level architecture and major subsystems
- Circular dependencies
- Cross-layer violations
- Feature-to-feature coupling that should go through shared/public APIs
- Files or directories acting as architectural "leak points"
- Areas where the intended design is unclear and needs codification
- Existing lint/tooling/CI hooks to integrate rather than duplicate

---

### Target Enforcement Categories

Implement rules for as many of these as the repo structure supports:

#### 1. Layering Rules
- UI/presentation cannot import infra/db/runtime internals directly
- Domain/business logic should not depend on presentation
- Infra/adapters should not reach upward into UI
- Shared utilities must not become a dumping ground for app-specific logic

#### 2. Module Boundary Rules
- Features cannot import each other arbitrarily
- Cross-feature access should happen through explicit public entrypoints where appropriate
- Internal modules should not be imported from outside their package/folder unless explicitly allowed

#### 3. Directionality Rules
- Dependencies should flow inward toward stable core logic, not outward into volatile layers
- Lower-level modules must not depend on higher-level modules

#### 4. Restricted Import Rules
- Ban dangerous relative import patterns if alias/public-entry imports are preferred
- Ban imports from known internal-only paths
- Ban convenience imports that bypass intended APIs

#### 5. Cycle Prevention
- Detect and fail on circular dependencies, with carefully justified exceptions only if absolutely necessary

#### 6. Naming / Placement / Policy Rules
- Enforce conventions that support architecture clarity
- Prevent files of certain types from living in the wrong layers
- Enforce any obvious repo-specific rules that improve maintainability

---

### Implementation Requirements

- Add or update Dependency Cruiser config
- Add or update Biome/lint config as appropriate
- Wire checks into package scripts
- Wire checks into CI
- Make failures readable and actionable
- Document the rule system in a concise architecture-enforcement doc
- Include examples of allowed vs disallowed dependency patterns
- Avoid overblocking legitimate development unless there is a strong architectural reason

**Important constraint:**
Do not force everything through Biome if it weakens the solution. If AIOS needs Dependency Cruiser plus a supplemental lint/custom rule path, do that. Choose correctness over tool purity.

---

### Deliverables

1. Architectural audit summary
2. Proposed target dependency/layer model
3. Implemented rule configs
4. Any required script/CI changes
5. Short documentation for developers/agents
6. A backlog of rules that should exist later but are not yet safe to enforce
7. A note explaining each rule and why it exists

---

### Acceptance Criteria

- Architectural boundary violations are automatically detected
- CI fails on real violations
- At least the major layers/modules of AIOS are protected from obvious drift
- Circular dependencies are surfaced and addressed or explicitly documented
- The rule set is understandable enough that future agents can extend it safely
- The repo is more structurally legible after the change than before
- No fake enforcement, no dead config, no decorative tooling

---

### Execution Style

- Be aggressive but sensible
- Large refactors are allowed if needed to support enforceable boundaries
- Prefer thin display layers, consolidated helpers, explicit public APIs, and clean module contracts
- Preserve working behavior unless a structural improvement requires change
- Explain tradeoffs when a rule is intentionally softened

If the repo is too inconsistent to enforce strong rules immediately:
- implement the strongest safe baseline now
- document the next ratchet step
- leave the repo in a better-enforced state than you found it

---

### Output Format

Return:
1. Audit findings
2. Proposed rule model
3. Exact implementation plan
4. Files changed
5. Remaining risks / follow-up opportunities
