# Divergent Strategy Workflow Audit

## Current State Summary

AIOS already has partial workflow infrastructure: `orchestration_runs`, `workflow_execution_reports`, `briefing_packets`, workflow registries, success criteria, standards health, knowledge topics, and approval-gated `improvement_writebacks`. The system has strong intent around deterministic workflows and inspectable state, but no first-class divergent exploration workflow before this pass.

## Relevant Existing Files / Systems

- `services/workflow_orchestration.py` loads explicit workflow and skill registries.
- `config/workflows/registry.json` and `config/workflows/skills.json` define reusable workflow stages and skills.
- `data/schema.sql` and `aios-ui/server/aios/schema.ts` define local SQLite tables.
- `services/success_criteria.py` and `spec/success-criteria/*.md` provide standards-style evaluation.
- `aios-ui/app/runs/*` exposes session run inspection.
- `improvement_writebacks` already models approval-gated learning proposals.
- `PROJECT.md` is the project truth file.

## Prior-Art Notes

The referenced `nstied/monkeys-with-finger-paints` repository packages the pattern as a skill with thin `SKILL.md`, on-demand references, divergent formulations, a judging panel, lineage, memory accumulation, loop modes, user-judge mode, and entropy/convergence controls. AIOS should adopt those mechanics, but not its branding or voice. Source: https://github.com/nstied/monkeys-with-finger-paints

## Gaps Against Desired Divergent Strategy Workflow

- No explicit divergent run entity.
- No candidate or judge registry.
- No portfolio output model.
- No entropy or convergence-risk record.
- No HOW / WHAT / FAILURE / ENTROPY memory distinction.
- No prompt/skill promotion lifecycle beyond scattered candidate status fields.
- No UI route for divergent candidates, judgments, or writeback proposals.
- No tests preventing auto-promotion or rationale-free judgments.

## Recommended Architecture

Use a focused workflow, not a new generic orchestration framework:

- Add `divergent_runs`, `divergent_candidates`, `divergent_judgments`, `memory_writeback_proposals`, `entropy_observations`, and `promotion_lifecycle_items`.
- Keep candidate and judge definitions in small JSON registries.
- Store judge scores as heuristic evidence with rationale, not truth.
- Generate memory writebacks as proposals only.
- Render runs, candidates, judgments, entropy, and proposals in Taski/AIOS UI.

## Risk Assessment

- The deterministic candidate generator is a baseline, not a replacement for future LLM-backed candidate agents.
- Heuristic scores can look precise; UI and docs must label formulas and uncertainty.
- Duplicate writeback concepts exist. This pass keeps divergent-specific proposals separate because they need HOW / WHAT / FAILURE / ENTROPY categorization, while preserving existing `improvement_writebacks`.
- Promotion gates are lightweight and evidence-driven, but not yet connected to downstream task-completion metrics.

## Implementation Plan

1. Add tests for classification, registries, portfolio selection, entropy, writeback proposals, and lifecycle gates.
2. Add a deterministic `services.divergent_strategy` workflow service.
3. Add schema tables and registries.
4. Register the workflow and skill specs.
5. Add UI read routes for divergent runs, writebacks, and skill candidates.
6. Add skill packet and architecture docs.
7. Update project truth and run verification.

## Files Expected to Change

- `services/divergent_strategy.py`
- `tests/test_divergent_strategy.py`
- `config/divergent-strategy/*.json`
- `config/workflows/registry.json`
- `config/workflows/skills.json`
- `data/schema.sql`
- `schema.sql`
- `aios-ui/server/aios/schema.ts`
- `aios-ui/server/routers/divergent.ts`
- `aios-ui/app/runs/divergent/*`
- `aios-ui/app/writebacks/page.tsx`
- `aios-ui/app/skills/candidates/page.tsx`
- `skills/divergent-strategy/*`
- `docs/workflows/divergent-strategy.md`
- architecture docs under `docs/architecture/`
- `PROJECT.md`

## Questions / Assumptions

- Assumption: AIOS-native naming should be `Divergent Strategy Workflow`; no “monkeys” branding.
- Assumption: local deterministic execution is acceptable for the first production-grade slice; future LLM agents can plug in behind the same candidate/judge records.
- Assumption: writebacks require approval unless a later policy explicitly permits auto-writeback.
