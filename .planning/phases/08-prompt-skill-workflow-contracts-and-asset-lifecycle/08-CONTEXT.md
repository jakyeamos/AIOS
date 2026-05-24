# Phase 8: Prompt, Skill, Workflow Contracts, And Asset Lifecycle - Context

**Gathered:** 2026-05-24
**Status:** Ready for execution
**Mode:** Autonomous continuation from Phase 7 completion

<domain>
## Phase Boundary

Phase 8 treats reusable prompts, skills, and workflows as governed assets and workflow contracts. The phase must normalize lifecycle metadata across prompts, skills, and workflows; enrich workflows into stage-level contracts; recommend reusable assets from durable evidence; and support comparison, promotion, revision, and deprecation through governed writeback paths.

This phase extends existing brownfield surfaces rather than replacing them:

- `prompts/registry.json`
- `config/workflows/registry.json`
- `config/workflows/skills.json`
- `services/workflow_orchestration.py`
- existing promotion, writeback, success-criteria, and workflow evidence tables

</domain>

<decisions>
## Implementation Decisions

- Use one shared lifecycle vocabulary for prompts, skills, and workflows: `draft`, `candidate`, `approved`, `active`, `deprecated`.
- Reuse `promotion_lifecycle_items` for cross-asset lifecycle history instead of adding a parallel lifecycle table.
- Preserve the `services/` -> `bin/` architecture boundary. Any Phase 5 writeback approval policy needed inside `services/` must be mirrored or wrapped inside `services/`, not imported from `bin/`.
- Keep registry JSON files authoritative for reviewed asset definitions; SQLite stores runtime evidence, lifecycle history, and proposals.
- Keep backward compatibility for one cycle where legacy prompt `route_status` and legacy workflow/stage shapes still load.
- Introduce planned workflow contracts conservatively as `candidate` workflows with draft executor stubs, not active defaults.

</decisions>

<code_context>
## Existing Code Insights

- Phase 6 provides durable criteria and stage finding evidence through `success_criteria_findings` and `success_criteria_stage_findings`.
- Phase 7 provides standards-health snapshots, delta explanations, provenance classification, and workflow recommendations from health deltas.
- `services/workflow_orchestration.py` is the canonical workflow and skill registry loader and execution seam.
- `services/divergent_strategy.py` already writes `promotion_lifecycle_items`; Phase 8 must normalize that behavior rather than fork it.
- `services/agentize.py` and `services/task_routing.py` are the packet and routing seams where asset recommendations should surface.

</code_context>

<specifics>
## Specific Ideas

- Execute the existing plans in order, committing each logical plan slice independently and immediately updating `.planning/PROJECT.md` after each implementation commit.
- Start with `08-01-PLAN.md` because all later recommendation, comparison, and planned workflow work depends on canonical lifecycle state and registry metadata.
- Keep tests focused on the behavior each plan introduces, then run the affected Python/UI quality gates before committing.
- Leave the untracked `logs/session-effectiveness/` artifact out of source commits unless a later verification step intentionally promotes it.

</specifics>

<deferred>
## Deferred Ideas

- Full UI operator surfaces for asset lifecycle and workflow effectiveness can follow the Python/CLI contract work unless a plan explicitly requires UI edits.
- Consolidating duplicated writeback approval policy into a shared services module is deferred to a later phase unless needed for a Phase 8 blocker.
- Shipping all planned workflow families is out of scope for this phase; Phase 8 introduces the four high-leverage candidate workflows identified in the plan.

</deferred>
