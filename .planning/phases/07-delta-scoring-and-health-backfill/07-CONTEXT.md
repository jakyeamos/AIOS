---
phase: 07-delta-scoring-and-health-backfill
phase_number: "07"
title: Delta Scoring And Health Backfill
status: ready-for-execution
autonomous: true
updated: 2026-05-24
---

# Phase 7: Delta Scoring And Health Backfill - Context

**Gathered:** 2026-05-24
**Status:** Ready for execution
**Mode:** Autonomous continuation after Phase 6 completion

<domain>
## Phase Boundary

Phase 7 turns Phase 6 standards and evaluation evidence into explainable health scoring, provenance-aware delta drill-downs, and prioritized workflow recommendations.

This phase should extend the existing standards-health stack rather than creating a parallel scorer. The canonical implementation surfaces are `services/standards_health.py`, `config/standards/registry.json`, `services/workflow_orchestration.py`, `services/aios_cli.py`, and the existing `aios-ui/server/aios/standards-health.ts` projection.

The phase closes requirements:

- DELT-01: ten named quality domains have measurable domain scores.
- DELT-02: each score has evidence, confidence, freshness, contradiction, and remediation.
- DELT-03: health views distinguish confirmed, inferred, missing, and contradictory signals.
- DELT-04: AIOS can prioritize backfill work and recommend workflows from health state.

</domain>

<decisions>
## Implementation Decisions

- Execute the existing three plans in order: `07-01-PLAN.md`, `07-02-PLAN.md`, then `07-03-PLAN.md`.
- Keep scoring additive. Do not rename or remove existing standards domains.
- Preserve `profile.default_attached_version` at `2026.04.0`; registry version bumps must not silently migrate existing projects.
- New domain evaluators should be honest by default: return `unknown` with explicit reasons unless real local evidence exists.
- Project delta explanations should be read-time projections from existing health, assessment, delta, and criteria-finding rows. Do not add a `delta_explanations` cache table.
- Workflow recommendations are advisory and must carry registry availability plus approval-policy context.
- Manual override support belongs in Phase 7 only where it lets the new manual/unknown standards become operator-resolvable.

</decisions>

<code_context>
## Existing Code Insights

- `services/standards_health.py` already loads registry standards, computes domain scores, persists assessments, delta items, backfill tasks, and latest snapshots.
- Phase 6 added `success_criteria_stage_findings`, which Phase 7 can include in contradiction detection.
- `services/capability_truth.py` already defines the four-state `Provenance` literal.
- `services/workflow_orchestration.py` already loads workflow registry data and ranks workflows from objective text; Phase 7 adds a health-state sibling recommender.
- `services/aios_cli.py` already contains audit-style JSON subcommands and governance audit payload builders; new commands should follow that dispatch style.
- `aios-ui/lib/control-plane.ts` and `aios-ui/server/aios/standards-health.ts` already expose standards health data to operator surfaces.

</code_context>

<specifics>
## Specific Ideas

Follow the three plan outputs exactly:

1. `07-01` expands standards coverage to all ten DELT-01 domains and verifies new evaluator behavior.
2. `07-02` adds `DeltaExplanation`, provenance classification, contradiction detection, and Python workflow recommendations.
3. `07-03` surfaces explanations and recommendations through CLI and UI contracts, plus durable manual overrides.

Run Python checks with `uv` and UI checks with `pnpm` from `aios-ui/` when TypeScript changes are touched.

</specifics>

<deferred>
## Deferred Ideas

- Cross-project ranking remains out of scope for this phase unless an existing plan explicitly requires it.
- Grounded-query integration for recommended workflows is deferred to Phase 10 operator surface work.
- Planned workflows such as `standards backfill`, `audit-only`, `codebase architecture review`, and `security review` should be marked unavailable when not present in `config/workflows/registry.json`, not silently launched.

</deferred>
