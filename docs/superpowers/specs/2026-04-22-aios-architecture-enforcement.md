# AIOS Architecture Enforcement — Dependency Cruiser + Lint Audit + Implementation Prompt

**Date:** 2026-04-22
**Status:** Ready to run
**Type:** Audit + implementation prompt
**Author:** jakyeamos

---

## Purpose

Turn AIOS's intended architecture standards into executable rules for all linked development projects. Make architectural drift difficult, obvious, and CI-blocking where each project supports blocking checks. Use stack-appropriate enforcement: Dependency Cruiser/ESLint for TypeScript module boundaries, ruff/import checks for Python, and additional adapters where a project profile warrants them.

**Primary outcome:** AIOS can tell agents which architecture rules apply to the project they are editing, run those checks, and report violations through a global control plane instead of relying on docs or convention.

---

## Prompt

You are implementing AIOS-managed architectural constraints for agent-run development across all linked projects.

Goal:
Make architecture enforceable by tooling instead of relying on docs or convention. AIOS is the orchestration/control layer; this repository is the implementation home and first self-check target, not the only target. Use Dependency Cruiser/ESLint where they fit TypeScript/React projects, ruff/import checks where they fit Python, and other narrow adapters where needed. The result should make architectural drift difficult, obvious, and CI-blocking when appropriate across linked projects.

Primary outcome:
Turn AIOS's global architecture standards into executable project profiles and checks.

Context:
AIOS is evolving into a durable orchestration and command-center system. Maintainability, modularity, observability, and agent-safe structure matter more than clever shortcuts. This implementation should support long-term growth, sub-agent-driven development, experimentation systems, UI visibility, and clean separation of concerns.

Instructions:
1. Audit AIOS's current project registry/control-plane structure before changing anything.
2. Audit this repository as the control-plane implementation target and use it as a self-check proof, but do not treat `aios-ui/` as the whole scope.
3. Infer the architectural layers, module boundaries, and likely failure points that AIOS must enforce across linked project types.
4. Propose a target rule model with project profiles/adapters so each linked repo can declare its stack, layers, allowed boundaries, and enforcement commands.
5. Implement enforcement using the strongest available mechanism:
   - Use Dependency Cruiser for TypeScript cross-folder/module dependency constraints
   - Use ESLint/Biome where they can enforce policy cleanly
   - Use ruff/import validation or a small custom checker for Python where appropriate
   - If a tool cannot realistically express a rule, use an appropriate supplemental validation mechanism instead of faking it
6. Prefer real enforcement over aspirational comments.
7. Keep the implementation understandable and maintainable by future agents.
8. Do not introduce heavy complexity unless it clearly improves enforcement quality.

Execution guardrail:
Do not begin by installing Dependency Cruiser or other tooling only in `aios-ui/`. That would harden one bootstrap target while missing the purpose of this phase. First create or update the AIOS-level enforcement profile model, then wire `aios-ui/` as a TypeScript/Next.js proof of that model.

---

### Audit Objectives

Find in AIOS and the first target project profiles:
- Current AIOS control-plane architecture and project registry shape
- Current top-level architecture and major subsystems in this repository as a self-check target
- Existing linked-project metadata or missing metadata needed to apply rules outside this repo
- Circular dependencies
- Cross-layer violations
- Feature-to-feature coupling that should go through shared/public APIs
- Files or directories acting as architectural "leak points"
- Areas where the intended design is unclear and needs codification
- Existing lint/tooling/CI hooks to integrate rather than duplicate

---

### Target Enforcement Categories

Implement rules for as many of these as project profiles support. A rule may be global, stack-specific, or project-specific.

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
- Enforce obvious project-specific rules only when they can be represented in an AIOS project profile, not as one-off assumptions hidden in this repo

---

### Implementation Requirements

- Add or update Dependency Cruiser config
- Add or update ESLint/Biome/ruff/custom validation config as appropriate per project profile
- Add or update AIOS metadata that records which enforcement profile applies to which project
- Wire checks into package scripts or project-local commands where available
- Wire checks into CI where available and expose non-CI checks through AIOS command surfaces
- Make failures readable and actionable
- Document the rule system in a concise architecture-enforcement doc
- Include examples of allowed vs disallowed dependency patterns
- Avoid overblocking legitimate development unless there is a strong architectural reason

**Important constraint:**
Do not force everything through Biome if it weakens the solution. If AIOS needs Dependency Cruiser plus a supplemental lint/custom rule path, do that. Choose correctness over tool purity.

---

### Deliverables

1. Architectural audit summary for AIOS as the global control plane
2. Proposed project-profile and dependency/layer model
3. Implemented rule configs/adapters for the first target profiles
4. Any required script/CI/AIOS metadata changes
5. Short documentation for developers/agents explaining how checks apply in any linked project
6. A backlog of rules or project adapters that should exist later but are not yet safe to enforce
7. A note explaining each rule and why it exists

---

### Acceptance Criteria

- Architectural boundary violations are automatically detected for at least one AIOS self-check target and one reusable project profile
- CI or an AIOS-visible check command fails on real violations where the project supports blocking checks
- At least the major layers/modules of AIOS and the first linked-project profile are protected from obvious drift
- Circular dependencies are surfaced and addressed or explicitly documented
- The rule set is understandable enough that future agents can extend it safely
- AIOS is more capable of guiding agents across projects after the change than before
- No fake enforcement, no dead config, no decorative tooling

---

### Execution Style

- Be aggressive but sensible
- Large refactors are allowed if needed to support enforceable boundaries
- Prefer thin display layers, consolidated helpers, explicit public APIs, and clean module contracts
- Preserve working behavior unless a structural improvement requires change
- Explain tradeoffs when a rule is intentionally softened

If a project is too inconsistent to enforce strong rules immediately:
- implement the strongest safe baseline now
- document the next ratchet step
- leave AIOS with a clearer enforcement profile and a better path to ratchet that project later

---

### Output Format

Return:
1. Audit findings
2. Proposed rule model
3. Exact implementation plan
4. Files changed
5. Remaining risks / follow-up opportunities
