# Phase 1: Project, Workflow, And Prompt Routing - Context

**Gathered:** 2026-05-16
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers the governed entry contract for serious AIOS work.

The implementation scope is:

- resolve vague work goals to a project candidate set and a final project target or explicit ambiguity block
- classify the task into a routeable task family
- select the smallest sufficient governed workflow for that task family
- select the prompt or handoff family as part of routing
- recommend the execution surface or invocation backend tied to workflow constraints
- persist route rationale and route metadata so Phase 2 packet compilation and later operator surfaces can reuse it

This phase does **not** own full packet compilation, grounded query completeness, standards scoring, or approval/writeback flows beyond the route metadata needed to feed those later phases.

</domain>

<decisions>
## Implementation Decisions

### Route Result Contract
- **D-01:** Phase 1 should introduce an explicit route-result contract rather than returning loosely shaped routing data from multiple helpers.
- **D-02:** The route result must persist at least: route id, objective, project candidate set, final project target or ambiguity block, task family, selected workflow, selected prompt/handoff family, recommended execution surface, rationale, and timestamp.
- **D-03:** Ambiguity is a valid route outcome. The system must block unsafe project guesses when multiple plausible projects fit the request.

### Project Resolution
- **D-04:** Project resolution should be inventory-backed and candidate-based, not a single direct string match.
- **D-05:** Project resolution must support four explicit outcomes: exact match, likely match, ambiguous match, and unsupported/no match.
- **D-06:** Candidate reasoning should be preserved in route metadata so later query and operator surfaces can explain why a project won or why the route blocked.

### Task Family And Workflow Selection
- **D-07:** Task-family classification should be implemented as a separate step from workflow selection so AIOS can explain both layers independently.
- **D-08:** Phase 1 should harden the early default serious-work routes first: `implementation-delivery`, `failure-recovery`, `audit-only`, `audit-and-implement`, and `agent handoff generation`.
- **D-09:** Workflow selection should prefer the smallest sufficient governed workflow rather than a generic implementation route.
- **D-10:** Route rationale must record nearby alternatives and why they lost, especially for `audit-only` vs `audit-and-implement`, `implementation-delivery` vs `failure-recovery`, and handoff-only vs execution workflows.

### Prompt And Handoff Family Selection
- **D-11:** Prompt selection belongs in routing at the family level first; detailed prompt asset lifecycle and promotion can remain a later phase concern.
- **D-12:** The route must identify a prompt or handoff family even when the best available asset is only partial or candidate quality; in that case the fallback state should be explicit in route metadata.
- **D-13:** Existing prompt registry data should be extended toward prompt-family recommendation rather than replaced with a disconnected system.

### Execution Surface Recommendation
- **D-14:** Route results should recommend an invocation backend or execution surface based on workflow constraints, not generic preference.
- **D-15:** Codex-managed runtime should be treated as the preferred surface for Codex serious-work routes when its required workflow constraints are satisfied.
- **D-16:** Manual legacy execution should never be the default route recommendation when a managed runtime is available.

### Persistence And Observability
- **D-17:** Route decisions must be stored durably enough to be reused by Phase 2 packet compilation and later run/evaluation/operator views.
- **D-18:** Phase 1 success depends on inspectability. The system should preserve route rationale, selected alternatives, and fallback states in machine-readable form rather than prose-only logs.

### Claude's Discretion
- exact scoring heuristics for candidate ranking
- schema shape and storage location for route metadata, as long as it remains durable and inspectable
- whether to implement routing as a dedicated module or as a bounded extension of existing workflow/orchestration surfaces
- the precise mapping layer between prompt templates, prompt families, and workflow families

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Planning Contract
- `.planning/ROADMAP.md` — Phase 1 scope, expected outputs, dependencies, and observable success criteria.
- `.planning/PHASE_01_SUBROADMAP.md` — detailed workstreams, deliverables, risks, and exit gates for this phase.
- `.planning/REQUIREMENTS.md` — authority for `ROUT-01` through `ROUT-04`.
- `.planning/REQUIREMENTS_CODE_SURFACE_MATRIX.md` — concrete implementation surfaces and evidence targets for the routing requirements.
- `.planning/TIER_ONE_ACCEPTANCE_CHECKLIST.md` — per-phase capability gates, evidence gates, and failure conditions.
- `.planning/WORKFLOW_MATRIX.md` — routeable workflow families, trigger conditions, stage contracts, validations, approvals, artifacts, and tier-one gaps.
- `.planning/FUNCTIONALITY_MAP.md` — current status and tier-one gaps for routing, prompt selection, and execution-surface recommendation.

### Current Routing And Workflow Surfaces
- `services/workflow_orchestration.py` — existing workflow/skill registry loading, prompt normalization hooks, and workflow execution helpers.
- `services/execution_strategy.py` — task family and execution strategy catalogs for `codex` and `claude_code`.
- `services/invocation_backends.py` — managed runtime and legacy backend contract surfaces.
- `config/workflows/registry.json` — current governed workflow definitions and stage layout.
- `config/workflows/skills.json` — current workflow-skill bindings.

### Prompt Surfaces
- `prompts/registry.json` — current prompt template metadata and classifications.
- `bin/hook-prompt-submit.py` — existing prompt classification and prompt-template matching logic.

### Related Product Truth
- `.planning/PROJECT.md` — product identity, active requirements, constraints, and the default-operating-layer target.
- `.planning/STATE.md` — current milestone, active phase, dependency chain, and planning memory.
- `PROJECT.md` — current shipped reality and truth notes about workflow routing, orchestration, prompts, and control-plane state.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `services/workflow_orchestration.py`: already loads workflow and skill registries into typed dataclasses and has a bounded prompt-template selection hook. This is the strongest existing base for route-result assembly.
- `services/execution_strategy.py`: already defines task-family specs, per-surface strategy bundles, and validation rules for active `codex` and `claude_code` strategies. This is the strongest existing base for routeable task families and execution-surface recommendation.
- `services/invocation_backends.py`: already exposes managed runtime and legacy backend identities with strict-handshake semantics. This should anchor execution-surface recommendation instead of inventing a new backend layer.
- `prompts/registry.json`: already contains prompt metadata, classifications, tags, required inputs, and template files. This is the existing asset surface to extend toward prompt-family routing.
- `bin/hook-prompt-submit.py`: already contains lightweight prompt classification and prompt-template matching logic. It is useful as a source of heuristics and telemetry, but not sufficient as the whole Phase 1 routing system.

### Established Patterns
- The repo already favors typed registry loading over ad hoc dictionaries for stable contracts.
- Existing control-plane work prefers machine-readable metadata with explicit states and validation over prose-only status.
- Managed runtime work is already split by `surface` and strict invocation handshake, which aligns with a route recommendation layer rather than a generic “pick an agent” abstraction.

### Integration Points
- Route results need to feed Phase 2 packet compilation and should therefore be persistable and retrievable from later orchestration or query surfaces.
- Prompt-family recommendation should be aligned with workflow selection so later packet generation can attach prompt/handoff instructions without re-deciding the route.
- Project resolution will likely need to connect to the existing project inventory and project/query surfaces rather than only local workflow code.

</code_context>

<specifics>
## Specific Ideas

- Project resolution should probably use an inspectable candidate set with confidence and explanation fields, not a single opaque “matched project” string.
- Workflow routing should treat `audit-only` and `audit-and-implement` as first-class route targets immediately, even if their full workflow contracts harden later.
- Prompt recommendation should likely normalize around prompt families such as implementation, debugging/recovery, audit/review, planning/reasoning, and handoff generation rather than only single templates.
- Route persistence should be designed so a later operator view can answer “why did AIOS pick this workflow and runtime?” without re-running routing logic.

</specifics>

<deferred>
## Deferred Ideas

- Full packet compilation quality and receipt expansion belong to Phase 2.
- Rich lifecycle state and resume semantics belong to Phase 3.
- Governed truth-update and approval workflows belong to Phases 4 and 5.
- Full asset lifecycle, promotion/deprecation policy, and workflow-library scoring belong to Phases 8 and 9.

</deferred>

---

*Phase: 1-project-workflow-and-prompt-routing*
*Context gathered: 2026-05-16*
