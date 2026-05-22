---
phase: 08-prompt-skill-workflow-contracts-and-asset-lifecycle
phase_number: "08"
type: research
updated: 2026-05-21
---

# Phase 8 Research

**Researched:** 2026-05-21
**Domain:** Asset lifecycle normalization (prompts/skills/workflows), stage-rich workflow contracts, evidence-backed recommendation, comparison and promotion model
**Confidence:** HIGH

## Summary

Phase 8 promotes prompts, skills, and workflows from "loosely-typed registry rows that route table lookups consult" into **lifecycle-managed governed assets** with explicit purpose, applicability, status, usefulness evidence, and stage-bound contracts. The structural primitives are already substantially present: `prompts/registry.json` already carries `route_status` ("approved"/"candidate") and `applicable_workflow_families` per template; `config/workflows/skills.json` already declares per-skill `purpose`, `allowed_stages`, `input_schema`, `output_schema`, `invariants`, `failure_conditions`, `side_effects`, `execution_mode` and partial `source_path`/`installed_name`; `config/workflows/registry.json` already carries per-workflow `workflow_family`, `purpose`, `trigger_hints`, `output_contract`, `required_validations`, and stage rows with `key`/`kind`/`required_skills`; `promotion_lifecycle_items` already exists (`item_kind`, `item_key`, `source_run_id`, `status`, `evidence_json`, `status_reason`, `metadata_json`) but is only written by `services/divergent_strategy.py`; `workflow_skill_experiments` + `github_skill_candidates` + `workflow_paper_fixtures` already exist for experimentation; `workflow_synthesis_proposals` already exists with `workflow_spec_json` + `skill_specs_json` + `validation_plan_json` + `evidence_json` + a `pending_approval`/`approved`/`rejected` lifecycle; `workflow_learning_events` and `improvement_writebacks` already carry the governed-writeback rails Phase 5 shipped; Phase 6's `success_criteria_stage_findings` and Phase 7's `recommend_workflow_from_health` give Phase 8 the durable stage-level + health-level evidence inputs.

What is missing and what Phase 8 must add: (1) **lifecycle normalization** — `route_status` is prompt-only, skills have no status field at all, workflows have no status field at all, and the five-state contract (`draft`/`candidate`/`approved`/`active`/`deprecated`) is not enforced anywhere; `promotion_lifecycle_items` is the right home for cross-asset lifecycle history but its `status` is freeform string today and only divergent runs populate it. (2) **Workflow schema vNext** — the current workflow row has stages with `key`/`kind`/`required_skills` only; it does **not** yet bind per-stage `required_inputs`, `required_outputs`, `validations`, `approval_gates`, `expected_artifacts`, `writeback_behavior`, or `learning_signals`. Phase 8 must extend the registry schema and `WorkflowSpec`/`StageSpec` dataclasses in `services/workflow_orchestration.py` while keeping existing workflows valid via defaults. (3) **Usefulness evidence** — `agentize_evaluations`, `workflow_execution_reports`, `workflow_skill_experiments`, `prompts_used`, and `success_criteria_findings` already record per-run evidence about which prompt/skill/workflow ran and how it scored, but there is no unified `asset_usage_evidence` view that aggregates "this prompt has run N times in workflow X with success-rate Y" to drive recommendation. (4) **Asset recommendation in packet/handoff generation** — `services/agentize.py` `_standards()` and `_success_criteria()` currently emit hardcoded strings (Phase 6 already flagged this for replacement) and the agentized packet's `relevant_skills` field is populated from classification heuristics, not from the proven-asset evidence; Phase 8 connects evidence-backed recommendation into `agentize_request` and into the start-work packet seam. (5) **Workflow comparison / promotion model** — `recommend_workflow_from_health` (Phase 7) and `rank_workflow_candidates` (existing) score workflows at *selection* time but there is no per-version effectiveness comparison surface and no governed promotion gate that requires evidence + Phase-5 approval before a workflow flips `candidate` → `approved` → `active`. Finally, (6) **planned workflow families** — `WORKFLOW_MATRIX.md` lists ten planned workflow families (audit-only, audit-and-implement, PRD, test-first implementation, repo cleanup, UI polish, security review, prompt experiment, standards backfill, codebase architecture review, research-to-plan, project truth update, agent handoff generation) that are surfaced as recommendations from Phase 7 with `available_in_registry: false` but have no stage-rich governed contracts yet. Phase 8 owns introducing these.

**Primary recommendation:** Treat Phase 8 as four additive layers on top of existing primitives, in this order: **(a) Asset lifecycle normalization** — define a single five-state `asset_lifecycle_state` literal (`draft|candidate|approved|active|deprecated`) and a shared `AssetRecord` shape; extend `prompts/registry.json` to add per-template `lifecycle_state` + `purpose` + `applicability` + `usefulness_evidence` (rename `route_status` to `lifecycle_state` with a migration mapping `approved` → `active`, `candidate` → `candidate`); add the same fields to every entry in `config/workflows/skills.json` and `config/workflows/registry.json`; persist lifecycle transitions through the existing `promotion_lifecycle_items` table with `item_kind in {prompt, skill, workflow}` so the cross-asset surface is one table not three. **(b) Workflow schema vNext** — extend `WorkflowSpec` and `StageSpec` with `required_inputs`, `required_outputs`, `validations`, `approval_gates`, `expected_artifacts`, `writeback_behavior`, `learning_signals`; keep existing six workflows passing by defaulting omitted fields to safe values; harden `implementation-delivery` and `failure-recovery` first, then `academic_paper_v1` (kept as proof case), then `divergent-strategy` (tighten governance per phase scope). **(c) Asset-aware packet/handoff recommendation** — add `services/asset_recommendation.py` that joins `prompts_used`/`agentize_evaluations`/`workflow_execution_reports`/`success_criteria_findings`/`workflow_skill_experiments` into a `asset_usage_evidence` projection, then wire it into `agentize_request()` so `relevant_skills`/`relevant_standards` come from evidence rather than hardcoded classification rules; route results from Phase 1 already store `prompt_recommendation` so the seam exists. **(d) Workflow comparison and promotion** — add `services/workflow_promotion.py` with `compare_workflow_effectiveness(workflow_key, since)` and `propose_workflow_promotion(workflow_key, to_state)`; promotion proposals reuse the Phase 5 `writeback_approval_policy(layer_type="workflow", impact_scope="workflow-default")` path and write to `improvement_writebacks` + `promotion_lifecycle_items`. The CLI gets `aios asset-lifecycle` and `aios workflow-compare`; the UI gets `getAssetLifecycle`/`getWorkflowEffectiveness`/`promoteWorkflowAsset` sibling functions in `aios-ui/server/aios/` and tRPC routes in `aios-ui/server/routers/{workflows,prompts,control-plane}.ts`. Introducing the **planned workflow families** as governed contracts is a separate task wave inside this phase that uses the vNext schema directly.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Five-state lifecycle vocabulary (`draft`/`candidate`/`approved`/`active`/`deprecated`) | Python control plane (new `services/asset_lifecycle.py`) | Config registries (prompts/skills/workflows) | The vocabulary needs to be a single typed literal shared by all three registries plus `promotion_lifecycle_items.status`; one canonical source avoids drift. |
| Cross-asset lifecycle persistence | SQLite (`promotion_lifecycle_items` — existing) | Python (`services/asset_lifecycle.py` extends `services/divergent_strategy.py` schema ensure) | Table already supports `item_kind`/`item_key`/`status`/`evidence_json`/`status_reason`; Phase 8 standardizes `item_kind in {prompt, skill, workflow}` and writes transition rows from every promotion path. |
| Workflow schema vNext (inputs/outputs/validations/approvals/artifacts/writeback/learning per stage) | Config (`config/workflows/registry.json`) + Python (`services/workflow_orchestration.py` `WorkflowSpec`/`StageSpec` extension) | SQLite (no new table — extended JSON in `workflow_execution_reports.report_json`) | Schema lives in JSON registry for review; loader normalizes into dataclasses; executor honors stage-local bindings during `execute_workflow`. |
| Asset usefulness evidence aggregation | Python control plane (new `services/asset_recommendation.py`) | SQLite (reads from existing `prompts_used`, `agentize_evaluations`, `workflow_execution_reports`, `success_criteria_findings`, `workflow_skill_experiments`) | All inputs are already persisted; Phase 8 only adds a read-time projection plus a small `asset_usage_snapshots` cache to avoid recomputing per request. |
| Asset recommendation in packet/handoff generation | Python control plane (`services/agentize.py` consumes `services/asset_recommendation.py`) | Config (prompts/skills lifecycle + applicability) | Recommendation replaces hardcoded `_standards()` / `_success_criteria()` / `relevant_skills` heuristics in `agentize.py`. |
| Workflow comparison + promotion governance | Python control plane (new `services/workflow_promotion.py`) | Reuse Phase 5 `writeback_approval_policy` + `improvement_writebacks` | Promotion is a governed writeback class; Phase 8 does NOT introduce a new approval engine. |
| Planned workflow family contracts (audit-only, audit-and-implement, security review, etc.) | Config (`config/workflows/registry.json` additions) + Python (any new skill keys in `config/workflows/skills.json`) | UI (`aios-ui/server/routers/workflows.ts` continues to consume) | Stage-rich contracts are the deliverable; concrete `_execute_skill` dispatch handlers can stay minimal (delegating to the existing learned-workflow-skill or executor seams). |
| Operator-visible asset lifecycle surface | UI (`aios-ui/server/routers/prompts.ts`, `workflows.ts`, `control-plane.ts`) | UI library types (`aios-ui/lib/types.ts`) | tRPC routers extend with `getAssetLifecycle*` / `getWorkflowEffectiveness*` procedures; the App Router pages already exist as inspection surfaces. |
| CLI parity | Python (`services/aios_cli.py`) | — | `aios asset-lifecycle`, `aios workflow-compare`, `aios promote-asset` subcommands cover the headless path. |

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ASSET-01 | Track prompts, skills, workflows as lifecycle-managed assets with purpose, applicability, status, evidence of usefulness | Existing surfaces partially cover this: `prompts/registry.json` has `purpose`/`applicable_workflow_families`/`route_status` (rename to `lifecycle_state`); `config/workflows/skills.json` has `purpose` + `allowed_stages` but no `applicability` (`allowed_stages` is stage-fit, not workflow-fit) and no `status`; `config/workflows/registry.json` has `purpose`/`trigger_hints` but no `lifecycle_state`. Phase 8 adds canonical fields to all three. Usefulness evidence aggregation comes from `services/asset_recommendation.py` (new) reading `prompts_used`, `agentize_evaluations`, `workflow_execution_reports`, `workflow_skill_experiments`. |
| ASSET-02 | Distinguish draft/candidate/approved/active/deprecated reusable assets | `promotion_lifecycle_items.status` is already TEXT — Phase 8 narrows it to the five-state literal and writes a `LifecycleTransition` row on every state change. Audited via `aios contracts-audit` extension (new `AssetLifecycle` contract row). |
| ASSET-03 | Link reusable assets to the workflows and task types where they succeeded or failed | `agentize_evaluations` already records `selected_skills_json` + `selected_standards_json` + `outcome_quality` + `tests_passed` per packet/run; `workflow_execution_reports.report_json` records `stages[].skills[].skill_key`; `prompts_used.classification` + `prompts_used.outcome_score` per session; `workflow_skill_experiments` records per-skill baseline/candidate scores. Phase 8's `asset_usage_evidence` projection joins these by `(asset_kind, asset_key, workflow_key, task_family)` and persists a periodic `asset_usage_snapshots` cache row. |
| ASSET-04 | Recommend proven prompts, skills, workflows during packet generation and handoff creation | `services/agentize.py` is the entry point: `agentize_request()` currently uses heuristic classifications to populate `relevant_skills`/`relevant_standards`. Phase 8 swaps the heuristic for `asset_recommendation.recommend_assets_for_packet(task_classifications, workflow_family, project_id)` which sorts by `(lifecycle_state == 'active', success_rate desc, recent_use)`. The route result from Phase 1 already carries `prompt_recommendation`; Phase 8 expands it with `skill_recommendations` and `workflow_alternatives`. |
| WFLO-01 | Each governed workflow is a stage-based contract with required inputs, outputs, validations, expected artifacts | `WorkflowSpec`/`StageSpec` extension: add `required_inputs: tuple[InputBinding, ...]`, `required_outputs: tuple[OutputBinding, ...]`, `validations: tuple[ValidationBinding, ...]`, `expected_artifacts: tuple[ArtifactBinding, ...]` to `StageSpec`; `validate_workflow_bindings` extends to verify each binding resolves. Registry rev `2026-04-23` → `2026-05-21` (Phase 8). |
| WFLO-02 | Bind prompts, skills, tools, standards, approval gates, writeback behavior to specific workflow stages | Same `StageSpec` extension adds `approval_gates: tuple[ApprovalGateBinding, ...]` (calls `writeback_approval_policy` from Phase 5), `writeback_behavior: WritebackBindingSpec` (which writeback classes the stage emits on success/failure), `prompt_bindings: tuple[PromptBinding, ...]` (refs `prompts/registry.json` by id), `standards_bindings: tuple[str, ...]` (refs Phase 6 standards by `standard_id`). Loader honors backward compat: omitted fields default to empty tuples / `no_writeback`. |
| WFLO-03 | Evaluate workflow success at stage level and run level using durable evidence | Stage-level evidence already exists post-Phase 6 (`success_criteria_stage_findings`); Phase 8 adds a `_build_stage_evaluation_summary()` helper called inside `execute_workflow` that records per-stage `passed`/`failed`/`blocked` from validations and stage findings into `workflow_execution_reports.report_json.stage_evaluations[]`. Run-level rollup is the existing `report.status`. Comparison surface in `compare_workflow_effectiveness()` aggregates by `(workflow_key, version)` over a configurable lookback. |
| WFLO-04 | Compare workflow effectiveness over time and promote/revise/deprecate based on evidence | `services/workflow_promotion.py` exposes `compare_workflow_effectiveness(workflow_key, since)` returning per-version rework rate, validation pass rate, blocker count, writeback usefulness, mean run time. `propose_workflow_promotion(workflow_key, to_state, evidence)` emits an `improvement_writebacks` row with `layer_type="workflow"` + `impact_scope="workflow-default"` + Phase-5 approval policy class; on approval, writes a `promotion_lifecycle_items` row and bumps the registry entry's `lifecycle_state`. Revision is the same flow at the per-stage level (transition `active` → `candidate` then iterate). Deprecation is a state flip + a sunset note in `status_reason`. |

## Project Constraints (from CLAUDE.md / AGENTS.md)

| Constraint | Source | Phase 8 Implication |
|------------|--------|---------------------|
| Run quality ladder: `ruff check . && ruff format --check . && basedpyright && vulture` | `~/.claude/CLAUDE.md` Python canonical commands | Every implementation task in this phase ends with these as a hard gate. |
| UI quality ladder: `pnpm lint && pnpm tsc --noEmit` (no `pnpm test` is wired in `aios-ui/package.json`) | `~/.claude/CLAUDE.md` + AGENTS.md | Any TypeScript edit in `aios-ui/server/aios/` or `aios-ui/server/routers/` ends with these. |
| Atomic commits scoped to one project + one concern, followed by immediate `PROJECT.md` truth update commit | `~/.claude/CLAUDE.md` Git rules | Each task in this phase commits independently and updates `PROJECT.md` before the next task begins. |
| `main` stays deployable | `~/.claude/CLAUDE.md` Git | Phase 8 work goes through feature branches per repo discipline; `.planning/config.json` has `branching_strategy: none` so confirm in discuss-phase whether autonomous mode bypasses branching here. |
| No `--no-verify` or `--no-gpg-sign` bypasses | `~/.claude/CLAUDE.md` Git | Honor pre-commit hooks. |
| Never use `cat << EOF` or heredoc for file creation | Agent harness rule | Use Write tool for any new file. |
| Don't add comments/docstrings/type annotations to code I didn't change | `~/.claude/CLAUDE.md` Working style | Edits stay scoped; do not blanket-annotate touched modules. |
| Three similar lines is better than premature abstraction | `~/.claude/CLAUDE.md` Working style | Resist building a generic "asset framework"; extend the per-asset-kind dispatch pattern that Phase 5/6/7 already follow. |
| Local-first + files-authoritative | AGENTS.md (Constraints) | All new lifecycle data lives in SQLite + registry JSON; no external services. Registry JSON remains the source of truth, SQLite holds runtime evidence and lifecycle history. |
| Governance must remain reviewable | AGENTS.md (Constraints) | Promotion of prompt/skill/workflow assets MUST flow through `writeback_approval_policy` with `impact_scope in {prompt-default, skill-default, workflow-default}` — these scopes already exist in Phase 5 and emit `requires_approval: true`. |
| Explainability is required | AGENTS.md (Constraints) | Every asset recommendation MUST carry a `rationale_json` with the evidence rows that drove it (success rate, recent uses, applicable_workflow_families match). |
| Brownfield continuity | AGENTS.md (Constraints) | Existing six workflow registry entries MUST keep loading under the vNext schema without manual migration; defaults are required. |
| Architecture boundary: `services/` cannot import `bin/` | `tests/test_architecture_enforcement.py` | New `services/asset_lifecycle.py`, `services/asset_recommendation.py`, `services/workflow_promotion.py` cannot import `bin/aios_orchestration_runtime`; if they need `writeback_approval_policy`, that function must be re-exported from `services/` or moved (likely re-exported as a thin shim to avoid a wider refactor). |

## Standard Stack

### Core (existing — extend, don't replace)

| Library / Surface | Version | Purpose | Why Standard |
|-------------------|---------|---------|--------------|
| `services/workflow_orchestration.py` | in-tree (979 lines) | Workflow + skill registry loaders, `WorkflowSpec`/`StageSpec`/`SkillSpec` dataclasses, `validate_workflow_bindings`, `rank_workflow_candidates`, `recommend_prompt_family`, `recommend_route_primitives`, `execute_workflow` stage iteration | Already the canonical workflow plane; Phase 8 extends dataclasses and the registry loader, NOT replaces. |
| `services/agentize.py` | in-tree | Compiles freeform requests into `AgentizedTaskPacket` with `relevant_skills`, `relevant_standards`, verification plan, output contract | Already the packet seam; Phase 8 replaces `_standards()` / `_success_criteria()` heuristics with evidence-backed recommendation. |
| `services/divergent_strategy.py` | in-tree | Owns `promotion_lifecycle_items` schema ensure + writers (`upsert_promotion_lifecycle_item`) | Phase 8 reuses the schema; either Phase 8 imports the helpers OR moves them to `services/asset_lifecycle.py`. **Choose: import + add a sibling helper** to avoid a rename in this phase. |
| `services/workflow_experiments.py` | in-tree (779 lines) | `workflow_skill_experiments` + `github_skill_candidates` schema and writers; pairs/runs experiments through `execute_workflow` | Already a usefulness evidence source; Phase 8's `asset_usage_evidence` reads from it. |
| `services/workflow_synthesis.py` | in-tree (917 lines) | `workflow_synthesis_proposals` (`pending_approval`/`approved`/`rejected`) | Existing precedent for "proposal-with-evidence-then-approval"; Phase 8 mirrors this shape for promotion proposals. |
| `services/task_routing.py` | in-tree | Joins `recommend_route_primitives` output into `RouteResult` with `task_family`, `workflow_key`, `prompt_family`, `recommended_surface`, rationale | Phase 1 already shipped; Phase 8 extends `RouteResult` to carry `skill_recommendations` + `workflow_alternatives`. |
| `services/success_criteria.py` | in-tree (986 lines) | Standards/criteria resolution + per-stage findings (Phase 6) | Phase 8's stage-level evaluation summary reads `success_criteria_stage_findings`. |
| `services/standards_health.py` | in-tree (1599 lines) | Health snapshots + Phase 7's `recommend_workflow_from_health` | Phase 8's recommender consumes Phase 7's output as one input among many. |
| `bin/aios_orchestration_runtime.py` | in-tree | `writeback_approval_policy`, `insert_writeback`, `insert_writeback_event` (Phase 5) | Phase 8 reuses verbatim; promotion proposals are writeback rows. |
| `bin/hook-stop.py` | in-tree | Governed closeout emits writeback + follow-up + no-learning evidence | Phase 8 adds an `asset_promotion_candidates` enrichment at closeout when a run produced strong asset evidence. |
| `bin/sync-prompts.py` + `bin/validate-prompts.py` | in-tree | Sync prompt source files into `prompt_library_links`; validate frontmatter required fields | Phase 8 extends `REQUIRED_FIELDS` to include `lifecycle_state`, `applicability`, `purpose`, `last_evaluated_at`; bumps `validate-prompts` accordingly. |
| `config/workflows/registry.json` | 2026-04-23 | Six current workflow rows (`implementation-delivery`, `failure-recovery`, `academic_paper_v1`, `divergent-strategy`, `personalized-humanizer`, `agentize`) | Phase 8 bumps version to `2026-05-21` and adds vNext fields per stage. |
| `config/workflows/skills.json` | 2026-04-23 | 23 skill specs spanning `prompt_library_normalizer`, `agentize_intent_compiler`, validators, divergent, personalized humanizer, etc. | Phase 8 adds `lifecycle_state`, `applicability`, `usefulness_evidence_ref` per skill. |
| `prompts/registry.json` | 2026-04-23 | Five templates (`coding_debug`, `content_writing`, `reasoning`, `research`, `summarization`) | Phase 8 renames `route_status` → `lifecycle_state` (with one-cycle alias for back-compat) and adds `purpose` clarification, `usefulness_evidence_ref`. |
| `aios-ui/server/aios/standards-health.ts` + `aios-ui/server/routers/workflows.ts` + `aios-ui/server/routers/prompts.ts` | in-tree | UI projections of workflow/prompt state | Phase 8 adds `getAssetLifecycle*` and `getWorkflowEffectiveness*` and `promoteAsset` mutation. |

### Supporting (no new external deps required)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `sqlite3` (stdlib) | 3.x | All persistence | Lifecycle transitions on existing `promotion_lifecycle_items`; new read-time projections; one small `asset_usage_snapshots` cache table. |
| `json` (stdlib) | — | Registry parsing + JSON-column persistence | Reuse `_load_json` and `_json` helpers from existing modules. |
| `dataclasses` (stdlib) | — | Frozen dataclasses for `InputBinding`, `OutputBinding`, `ValidationBinding`, `ApprovalGateBinding`, `WritebackBindingSpec`, `ArtifactBinding`, `LearningSignalBinding`, `AssetRecord`, `LifecycleTransition` | Follow `StandardDefinition` / `WorkflowSpec` / `TrustedSignal` shape. |
| `typing.Literal` | stdlib | `AssetLifecycleState = Literal["draft","candidate","approved","active","deprecated"]` | Single source — import from `services/asset_lifecycle.py`. |
| `pytest` 8.x | — | Test framework | Follow `tests/test_workflow_orchestration.py` in-memory sqlite pattern. |
| `better-sqlite3` (UI) | per `aios-ui/package.json` | Direct DB access in `aios-ui/server/db.ts` | Reuse — Phase 8 adds prepared statements next to `getProjectStandardsHealth`. |
| `zod` | per `aios-ui/package.json` | Runtime validation in tRPC routers | New `getAssetLifecycle`/`getWorkflowEffectiveness`/`promoteAsset` input/output schemas use `z.object(...)`. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| One typed `AssetLifecycleState` literal across prompts/skills/workflows | Three independent enums per asset kind | Three enums drift; one shared literal stays consistent. **Choose: one literal in `services/asset_lifecycle.py`.** |
| Renaming `prompts/registry.json` `route_status` → `lifecycle_state` | Adding a parallel `lifecycle_state` field and keeping `route_status` as legacy | Parallel fields drift; rename + one-cycle alias is cleaner. **Choose: rename with the loader accepting either key for one revision cycle.** |
| Persisting lifecycle in `promotion_lifecycle_items` | New `asset_lifecycle_transitions` table | Table already exists with the exact shape needed; a new table would denormalize. **Choose: reuse `promotion_lifecycle_items`.** |
| Extending `StageSpec` dataclass with new fields | New `StageContract` dataclass alongside `StageSpec` | Two parallel types confuse callers; the dataclass is `frozen=True` so adding fields is straightforward. **Choose: extend `StageSpec` with default-valued new fields.** |
| Caching `asset_usage_evidence` in a new `asset_usage_snapshots` table | Recomputing per request from base tables | Recommendation is called inside `agentize_request` and `recommend_route_primitives` — a few times per session, not per keystroke. **Choose: recompute on read for the first cycle; promote to a cache table only if profiling shows it.** |
| Building a new approval engine | Reusing Phase 5 `writeback_approval_policy` | Two parallel engines defeat governance uniformity. **Choose: reuse.** |
| Encoding all ten planned workflow families in this phase | Encoding the four most critical first (`audit-only`, `audit-and-implement`, `standards backfill`, `security review`) and deferring others | Time pressure + scope realism; four high-leverage contracts deliver the schema vNext value without spreading thin. **Choose: ship four planned workflows in this phase, defer six to Phase 9 or a follow-up.** Confirm in discuss-phase. |
| Hardcoded bucket→workflow promotion gates in code | Declarative gate map in `config/workflows/promotion-policy.json` | Hardcoding three similar gate rules is better than premature abstraction (CLAUDE.md). Start hardcoded in `services/workflow_promotion.py`; promote to config only if rule count > ~6. |
| Inventing a new `evidence_strength` score | Reusing `success_rate` + `last_evaluated_at` + sample-count tuple already present in evidence sources | Two parallel "how good is this" metrics confuse; surface raw success rate + sample size + recency and let the UI render strength. **Choose: surface raw, don't synthesize a score.** |

**Installation:** No new external dependencies. Phase 8 is entirely additive to existing in-tree modules and JSON registries.

**Version verification:** `prompts/registry.json` and `config/workflows/{registry,skills}.json` are at `version: "2026-04-23"`. Phase 8 will bump to `"2026-05-21"` (or current commit date) when introducing the new fields. No external package version checks required.

## Architecture Patterns

### System Architecture Diagram

```
                     ┌────────────────────────────────────────────────────────────────┐
                     │ config/workflows/registry.json   (vNext: stages carry          │
                     │ config/workflows/skills.json      required_inputs/outputs/      │
                     │ prompts/registry.json             validations/approval_gates/   │
                     │                                    expected_artifacts/           │
                     │                                    writeback_behavior/           │
                     │                                    learning_signals)             │
                     └───────────────────────┬────────────────────────────────────────┘
                                             │ loaded by
                                             ▼
   ┌─────────────────────────────┐    ┌────────────────────────────────────┐
   │ services/asset_lifecycle.py │    │ services/workflow_orchestration.py │
   │  AssetRecord                │    │  WorkflowSpec / StageSpec / SkillSpec
   │  AssetLifecycleState        │    │   (vNext: bindings on StageSpec)   │
   │  LifecycleTransition        │    │  load_workflow_registry()          │
   │  promote_asset(...)         │    │  validate_workflow_bindings()      │
   │  list_assets(kind?, state?) │    │  execute_workflow()                │
   └──────────────┬──────────────┘    └─────────────┬──────────────────────┘
                  │ writes                          │ executes stages,
                  │ promotion_lifecycle_items       │ records evidence into
                  ▼                                 ▼ workflow_execution_reports
   ┌─────────────────────────────┐    ┌──────────────────────────────────────────┐
   │ SQLite                      │    │ Existing evidence tables (read-only here)│
   │  promotion_lifecycle_items  │    │  prompts_used (classification, outcome)  │
   │  (existing schema)          │    │  agentize_evaluations (selected_skills)  │
   │   item_kind in              │    │  workflow_execution_reports (stages[])   │
   │   {prompt,skill,workflow}   │    │  workflow_skill_experiments              │
   │   status in 5-state literal │    │  success_criteria_stage_findings         │
   │   evidence_json,            │    │  improvement_writebacks (Phase 5)        │
   │   status_reason             │    │  standards_health_snapshots (Phase 7)    │
   └─────────────────────────────┘    └────────────────────┬─────────────────────┘
                                                            │ joined into
                                                            ▼
                                  ┌──────────────────────────────────────────────────┐
                                  │ services/asset_recommendation.py                 │
                                  │   build_asset_usage_evidence(asset_kind, key)    │
                                  │     -> { success_rate, sample_size, recent_use,  │
                                  │          per_workflow_outcomes, per_task_family }│
                                  │   recommend_assets_for_packet(                   │
                                  │     task_classifications, workflow_family,        │
                                  │     project_id) -> AssetRecommendation[]         │
                                  └──────────────────┬───────────────────────────────┘
                                                     │ consumed by
              ┌──────────────────────────────────────┼──────────────────────────────┐
              ▼                                      ▼                              ▼
   ┌────────────────────────┐     ┌────────────────────────────┐    ┌────────────────────────┐
   │ services/agentize.py   │     │ services/task_routing.py   │    │ services/workflow_     │
   │  agentize_request()    │     │  start_route()             │    │   promotion.py         │
   │   replaces hardcoded   │     │   adds skill_recs[]        │    │  compare_workflow_     │
   │   _standards / _skills │     │   adds workflow_alts[]     │    │   effectiveness()      │
   │   with rec output      │     │                            │    │  propose_workflow_     │
   └────────────────────────┘     └────────────────────────────┘    │   promotion()          │
                                                                     │   reuses Phase 5       │
                                                                     │   writeback_approval_  │
                                                                     │   policy()             │
                                                                     └───────────┬────────────┘
                                                                                 │ writes
                                                                                 ▼
                                                           ┌──────────────────────────────────┐
                                                           │ improvement_writebacks (Phase 5) │
                                                           │ promotion_lifecycle_items        │
                                                           └──────────────────────────────────┘
                                             │
                                             │ surfaced via
                                             ▼
   ┌────────────────────────────────────────────────────────────────────────────────────────┐
   │ UI: aios-ui/server/aios/{workflow-effectiveness.ts, asset-lifecycle.ts}                │
   │   getAssetLifecycle(db, kind?, state?)                                                 │
   │   getWorkflowEffectiveness(db, workflow_key, since)                                    │
   │   promoteAsset(db, kind, key, to_state, evidence, actor)                               │
   │ Routers: workflows.ts, prompts.ts, control-plane.ts                                    │
   │ Pages: aios-ui/app/workflows, aios-ui/app/prompts                                      │
   └────────────────────────────────────────────────────────────────────────────────────────┘
                                             ▲
                                             │ also reachable via
                                             │
   ┌─────────────────────────────────────────┴──────────────────────────────────────────────┐
   │ CLI (services/aios_cli.py):                                                            │
   │   aios asset-lifecycle list [--kind prompt|skill|workflow] [--state active|...]        │
   │   aios asset-lifecycle promote --kind prompt --key research --to active --evidence-id  │
   │   aios workflow-compare --workflow-key implementation-delivery --since 30d             │
   │   aios contracts-audit  (extended with AssetLifecycle contract row)                    │
   └────────────────────────────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure (additions)

```
services/
├── asset_lifecycle.py            # NEW: AssetRecord, AssetLifecycleState literal,
│                                 #      LifecycleTransition dataclass,
│                                 #      ensure_asset_lifecycle_schema (extends existing
│                                 #      promotion_lifecycle_items),
│                                 #      promote_asset(), list_assets()
│
├── asset_recommendation.py       # NEW: build_asset_usage_evidence(),
│                                 #      recommend_assets_for_packet(),
│                                 #      recommend_skills_for_workflow_stage()
│
├── workflow_promotion.py         # NEW: compare_workflow_effectiveness(),
│                                 #      propose_workflow_promotion(),
│                                 #      finalize_workflow_promotion()
│                                 #      (reuses Phase 5 writeback_approval_policy)
│
├── workflow_orchestration.py     # extend: StageSpec gains required_inputs,
│                                 #         required_outputs, validations,
│                                 #         approval_gates, expected_artifacts,
│                                 #         writeback_behavior, learning_signals,
│                                 #         prompt_bindings, standards_bindings.
│                                 #         WorkflowSpec gains lifecycle_state,
│                                 #         applicability, purpose_long.
│                                 #         load_workflow_registry honors defaults
│                                 #         for backward compat.
│                                 #         validate_workflow_bindings extends to
│                                 #         resolve new bindings.
│                                 #         execute_workflow records stage_evaluations.
│                                 #         rank_workflow_candidates filters by
│                                 #         lifecycle_state >= candidate.
│
├── agentize.py                   # extend: _standards(), _success_criteria(),
│                                 #         and relevant_skills selection consume
│                                 #         asset_recommendation.recommend_*().
│                                 #         Keep hardcoded fallbacks for one cycle
│                                 #         when no recommendation is available.
│
├── task_routing.py               # extend: RouteResult includes skill_recommendations,
│                                 #         workflow_alternatives with rationale.
│
└── aios_cli.py                   # extend: asset-lifecycle / workflow-compare /
                                  #         promote-asset CLI subcommands.
                                  #         contracts-audit adds AssetLifecycle row.

config/
├── workflows/
│   ├── registry.json             # extend: per-workflow lifecycle_state,
│   │                             #         applicability, purpose_long.
│   │                             #         per-stage required_inputs,
│   │                             #         required_outputs, validations,
│   │                             #         approval_gates, expected_artifacts,
│   │                             #         writeback_behavior, learning_signals.
│   │                             #         add planned workflows: audit-only,
│   │                             #         audit-and-implement,
│   │                             #         standards-backfill, security-review
│   │                             #         (confirm exact set in discuss-phase).
│   └── skills.json               # extend: per-skill lifecycle_state,
│                                 #         applicability (workflow families it has
│                                 #         shown evidence in), purpose_long.
│
└── prompts/                      # (file lives at prompts/registry.json)

prompts/
└── registry.json                 # extend: rename route_status -> lifecycle_state
                                  #         (loader honors both for one cycle);
                                  #         add applicability + usefulness_evidence_ref.

bin/
├── validate-prompts.py           # extend: REQUIRED_FIELDS adds lifecycle_state,
│                                 #         applicability, last_evaluated_at.
└── hook-stop.py                  # extend: emit asset_promotion_candidate writebacks
                                  #         when a run produced strong evidence
                                  #         (high success rate, low rework).

tests/
├── test_workflow_orchestration.py    # extend: vNext schema parsing, backward
│                                     #         compat for omitted fields,
│                                     #         stage-level evaluation summary.
├── test_asset_lifecycle.py           # NEW: state transitions, promotion governance,
│                                     #      five-state literal enforcement.
├── test_asset_recommendation.py      # NEW: evidence aggregation, recommendation
│                                     #      ranking, fallback to defaults.
├── test_workflow_promotion.py        # NEW: compare + propose + finalize flow.
├── test_agentize.py                  # extend: recommended skills come from
│                                     #         asset_recommendation, not hardcoded.
└── test_aios_cli.py                  # extend: asset-lifecycle / workflow-compare /
                                      #         promote-asset CLI fixtures.

aios-ui/
├── lib/
│   ├── types.ts                  # extend: AssetLifecycleState, AssetRecord,
│   │                             #         WorkflowEffectiveness types.
│   └── trusted-signals.ts        # reuse — recommendation rationale uses TrustedSignal shape
├── server/
│   ├── aios/
│   │   ├── asset-lifecycle.ts    # NEW: getAssetLifecycle(db, kind?, state?),
│   │   │                         #      promoteAsset(db, kind, key, to_state, evidence)
│   │   └── workflow-effectiveness.ts  # NEW: getWorkflowEffectiveness(db, workflow_key, since)
│   └── routers/
│       ├── workflows.ts          # extend: getAssetLifecycle*, getEffectiveness*,
│       │                         #         promoteAsset mutation
│       ├── prompts.ts            # extend: same surfaces for prompts
│       └── control-plane.ts      # extend: asset lifecycle overview pane
```

### Pattern 1: Five-State Lifecycle Vocabulary (ASSET-02)

**What:** One typed literal shared across all three registries plus the lifecycle persistence table. Five states with explicit transition rules.

**When to use:** Anytime an asset record is created, transitioned, displayed, or filtered.

**State transitions (allowed):**
```
draft     → candidate    (proposed: by author or by experiment outcome)
candidate → approved     (review accepted; not yet activated)
candidate → draft        (review rejected, sent back for rework)
approved  → active       (activated for production use)
active    → candidate    (revision in progress; takes traffic share but flagged)
active    → deprecated   (sunset; new use blocked, existing references kept)
deprecated → archived    (out of scope for Phase 8; future cleanup)
```

**Example:**
```python
# Source: new services/asset_lifecycle.py
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

AssetKind = Literal["prompt", "skill", "workflow"]
AssetLifecycleState = Literal["draft", "candidate", "approved", "active", "deprecated"]

LIFECYCLE_TRANSITIONS: dict[AssetLifecycleState, frozenset[AssetLifecycleState]] = {
    "draft":      frozenset({"candidate"}),
    "candidate":  frozenset({"approved", "draft"}),
    "approved":   frozenset({"active"}),
    "active":     frozenset({"candidate", "deprecated"}),
    "deprecated": frozenset(),
}


@dataclass(frozen=True)
class AssetRecord:
    kind: AssetKind
    key: str
    purpose: str
    applicability: tuple[str, ...]           # workflow_family tags or task_family tags
    lifecycle_state: AssetLifecycleState
    usefulness_evidence: dict[str, Any]      # {success_rate, sample_size, recent_use}
    last_evaluated_at: str | None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LifecycleTransition:
    asset_kind: AssetKind
    asset_key: str
    from_state: AssetLifecycleState | None
    to_state: AssetLifecycleState
    actor: str
    rationale: str
    evidence_ids: tuple[str, ...]
    requires_approval: bool
    approval_writeback_id: str | None
    transitioned_at: str
```

### Pattern 2: Workflow Schema vNext (WFLO-01 / WFLO-02)

**What:** Extend `StageSpec` (and the registry JSON shape) so each stage carries the seven binding classes that Phase 8 requires. Keep existing six workflows valid via defaults.

**When to use:** Anytime a workflow is loaded, validated, or executed.

**Example (Python):**
```python
# Source: extends services/workflow_orchestration.py
from dataclasses import dataclass, field

@dataclass(frozen=True)
class InputBinding:
    key: str
    source: str                              # "packet" | "prior_stage" | "registry" | "evidence"
    required: bool = True
    schema_ref: str | None = None            # optional JSON Schema ref


@dataclass(frozen=True)
class OutputBinding:
    key: str
    target: str                              # "report" | "writeback" | "artifact"
    required: bool = True
    schema_ref: str | None = None


@dataclass(frozen=True)
class ValidationBinding:
    criterion_id: str                        # ref to config/success-criteria/registry.json
    blocking: bool = True


@dataclass(frozen=True)
class ApprovalGateBinding:
    impact_scope: str                        # "workflow-default" | "prompt-default" | etc.
    condition: str                           # "always" | "on_failure" | "on_blocker"
    rationale_template: str


@dataclass(frozen=True)
class ArtifactBinding:
    artifact_kind: str                       # "patch" | "report" | "evidence" | "summary"
    path_template: str                       # e.g. "data/success-criteria/evaluations/{run_id}.json"
    required: bool = True


@dataclass(frozen=True)
class WritebackBindingSpec:
    on_success: tuple[str, ...] = ()         # e.g. ("workflow_learning_event",)
    on_failure: tuple[str, ...] = ("workflow_learning_event",)
    no_learning_evidence_required: bool = False


@dataclass(frozen=True)
class LearningSignalBinding:
    signal_kind: str                         # "rework_rate" | "validation_pass" | "writeback_usefulness"
    measure: str                             # how it's computed


@dataclass(frozen=True)
class PromptBinding:
    template_id: str
    role: str                                # "primary" | "fallback"


@dataclass(frozen=True)
class StageSpec:
    key: str
    kind: str
    required_skills: tuple[str, ...]
    # NEW (all default to empty for backward compat):
    required_inputs: tuple[InputBinding, ...] = ()
    required_outputs: tuple[OutputBinding, ...] = ()
    validations: tuple[ValidationBinding, ...] = ()
    approval_gates: tuple[ApprovalGateBinding, ...] = ()
    expected_artifacts: tuple[ArtifactBinding, ...] = ()
    writeback_behavior: WritebackBindingSpec = field(default_factory=WritebackBindingSpec)
    learning_signals: tuple[LearningSignalBinding, ...] = ()
    prompt_bindings: tuple[PromptBinding, ...] = ()
    standards_bindings: tuple[str, ...] = ()
```

**Example (registry JSON for `implementation-delivery` with vNext fields):**
```json
{
  "key": "implementation-delivery",
  "name": "Implementation Delivery",
  "workflow_family": "audit_and_implement",
  "lifecycle_state": "active",
  "purpose": "Default implementation workflow for scoped code changes.",
  "purpose_long": "Compile a scoped change request into a plan, execute the smallest sufficient implementation slice, run gated validations, and emit governed closeout writebacks.",
  "applicability": ["audit_and_implement", "implementation"],
  "trigger_hints": ["implement", "build", "feature", "refactor"],
  "stages": [
    {
      "key": "parse_request",
      "kind": "parse_request",
      "required_skills": [],
      "required_inputs": [
        { "key": "objective", "source": "packet", "required": true }
      ],
      "required_outputs": [
        { "key": "task_family", "target": "report", "required": true }
      ],
      "learning_signals": [
        { "signal_kind": "route_quality", "measure": "ambiguity_count" }
      ]
    },
    {
      "key": "validate",
      "kind": "validate",
      "required_skills": ["scope_check"],
      "validations": [
        { "criterion_id": "scope-integrity", "blocking": true }
      ],
      "approval_gates": [
        {
          "impact_scope": "workflow-default",
          "condition": "on_failure",
          "rationale_template": "Validation failure on workflow {workflow_key} requires review before retry."
        }
      ],
      "writeback_behavior": {
        "on_failure": ["workflow_learning_event", "follow_up_item"]
      }
    }
  ]
}
```

### Pattern 3: Evidence-Backed Asset Recommendation (ASSET-03 / ASSET-04)

**What:** Join existing per-run evidence into a unified `AssetUsageEvidence` projection, then rank candidates by `(lifecycle_state, success_rate, recent_use)`.

**When to use:** Inside `agentize_request`, inside `recommend_route_primitives`, and inside the new `recommend_skills_for_workflow_stage`.

**Example:**
```python
# Source: new services/asset_recommendation.py
from __future__ import annotations
import sqlite3
from dataclasses import dataclass
from typing import Any
from services.asset_lifecycle import AssetKind, AssetLifecycleState


@dataclass(frozen=True)
class AssetUsageEvidence:
    asset_kind: AssetKind
    asset_key: str
    sample_size: int
    success_count: int
    blocker_count: int
    last_used_at: str | None
    per_workflow: dict[str, dict[str, int]]      # {workflow_key: {used, succeeded, failed}}
    per_task_family: dict[str, dict[str, int]]

    @property
    def success_rate(self) -> float:
        return self.success_count / self.sample_size if self.sample_size else 0.0


@dataclass(frozen=True)
class AssetRecommendation:
    asset_kind: AssetKind
    asset_key: str
    lifecycle_state: AssetLifecycleState
    rationale: str
    evidence: AssetUsageEvidence
    rank: int


def build_asset_usage_evidence(
    conn: sqlite3.Connection,
    *,
    asset_kind: AssetKind,
    asset_key: str,
    since: str | None = None,
) -> AssetUsageEvidence:
    # Skills: join workflow_execution_reports.report_json -> stages[].skills[].skill_key,
    #         agentize_evaluations.selected_skills_json, workflow_skill_experiments
    # Prompts: join prompts_used.classification + outcome_score,
    #          plus prompt_library_links + agentize_evaluations
    # Workflows: workflow_execution_reports filtered by workflow_key,
    #            joined with success_criteria_findings (level=blocker)
    ...


def recommend_assets_for_packet(
    conn: sqlite3.Connection,
    *,
    task_classifications: tuple[str, ...],
    workflow_family: str | None,
    project_id: str | None,
    asset_kind: AssetKind,
    limit: int = 5,
) -> list[AssetRecommendation]:
    # 1. Filter assets by lifecycle_state in {candidate, approved, active}
    # 2. Filter further by applicability overlap with workflow_family / task_classifications
    # 3. Rank by (lifecycle_state preference: active > approved > candidate,
    #             success_rate desc, sample_size weighted, recent_use desc)
    # 4. Attach rationale citing the top three evidence rows
    ...
```

### Pattern 4: Workflow Comparison and Promotion (WFLO-04)

**What:** Compare workflow effectiveness over time and emit governed promotion proposals via Phase 5 writeback rails.

**When to use:** On operator request (CLI / UI), or automatically when `recommend_workflow_from_health` keeps surfacing the same workflow as a recurring blocker.

**Example:**
```python
# Source: new services/workflow_promotion.py
from __future__ import annotations
import sqlite3
from dataclasses import dataclass
from typing import Any
# NOTE: writeback_approval_policy lives in bin/aios_orchestration_runtime.py;
# Phase 8 will re-export via services/asset_lifecycle.py to avoid services -> bin import.
from services.asset_lifecycle import (
    AssetLifecycleState,
    promote_asset,
    writeback_approval_policy_shim as writeback_approval_policy,
)


@dataclass(frozen=True)
class WorkflowEffectiveness:
    workflow_key: str
    since: str
    run_count: int
    completed_count: int
    failed_count: int
    rework_rate: float                    # subsequent runs on same packet
    validation_pass_rate: float
    mean_blocker_count: float
    writeback_usefulness: float           # ratio of writebacks adopted vs proposed
    stage_evaluations: dict[str, dict[str, float]]


def compare_workflow_effectiveness(
    conn: sqlite3.Connection,
    *,
    workflow_key: str,
    since: str,
) -> WorkflowEffectiveness:
    # Read workflow_execution_reports filtered by workflow_key + created_at >= since
    # Aggregate stage-level success from success_criteria_stage_findings
    # Aggregate writeback adoption from improvement_writebacks + improvement_writeback_events
    ...


def propose_workflow_promotion(
    conn: sqlite3.Connection,
    *,
    workflow_key: str,
    to_state: AssetLifecycleState,
    evidence: WorkflowEffectiveness,
    actor: str,
) -> dict[str, Any]:
    policy = writeback_approval_policy(
        layer_type="workflow",
        impact_scope="workflow-default",
        proposed_change={
            "workflow_key": workflow_key,
            "to_state": to_state,
            "evidence_summary": evidence,
        },
    )
    # Insert improvement_writebacks row with policy_class + rationale
    # Insert promotion_lifecycle_items row with status='proposed' + evidence_json
    # Return {writeback_id, lifecycle_id, requires_approval, rationale}
    ...
```

### Pattern 5: Stage-Level Evaluation Summary (WFLO-03)

**What:** Inside `execute_workflow`, after iterating stages, build a per-stage rollup that joins skill_reports + validations + Phase-6 stage findings into a single `stage_evaluations[]` block on the workflow report.

**When to use:** Always — it is the durable evidence input for `compare_workflow_effectiveness`.

**Example:**
```python
# Source: extends services/workflow_orchestration.py execute_workflow()
def _build_stage_evaluation_summary(
    *,
    stage_key: str,
    skill_reports: list[dict[str, Any]],
    validations: list[dict[str, Any]],
    stage_issues: list[str],
    stage_findings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    stage_validations = [v for v in validations if isinstance(v, dict)]
    pass_count = sum(1 for v in stage_validations if v.get("passed", False))
    total = len(stage_validations)
    blocker_count = (
        sum(1 for f in (stage_findings or []) if f.get("level") == "blocker")
        + sum(1 for issue in stage_issues if "blocker" in issue.lower())
    )
    return {
        "stage_key": stage_key,
        "passed_validations": pass_count,
        "total_validations": total,
        "blocker_count": blocker_count,
        "warning_count": sum(1 for f in (stage_findings or []) if f.get("level") == "warning"),
        "stage_finding_ids": [f.get("id") for f in (stage_findings or []) if f.get("id")],
        "outcome": "completed" if blocker_count == 0 and pass_count == total else "failed",
    }
```

### Pattern 6: Backward-Compatible Registry Loader

**What:** The registry loader must accept old (no lifecycle, no stage bindings) and new (full bindings) JSON without breaking existing six workflows.

**When to use:** Inside `load_workflow_registry`, `load_skill_registry`, and the prompt template loader.

**Example:**
```python
# Source: extends services/workflow_orchestration.py load_workflow_registry()
def _stage_from_row(row: dict[str, Any]) -> StageSpec:
    return StageSpec(
        key=str(row.get("key", "")).strip(),
        kind=str(row.get("kind", "")).strip(),
        required_skills=tuple(
            str(skill).strip()
            for skill in (row.get("required_skills") or [])
            if str(skill).strip()
        ),
        required_inputs=tuple(_input_binding(r) for r in row.get("required_inputs", []) or []),
        required_outputs=tuple(_output_binding(r) for r in row.get("required_outputs", []) or []),
        validations=tuple(_validation_binding(r) for r in row.get("validations", []) or []),
        approval_gates=tuple(_approval_binding(r) for r in row.get("approval_gates", []) or []),
        expected_artifacts=tuple(_artifact_binding(r) for r in row.get("expected_artifacts", []) or []),
        writeback_behavior=_writeback_binding(row.get("writeback_behavior") or {}),
        learning_signals=tuple(_learning_binding(r) for r in row.get("learning_signals", []) or []),
        prompt_bindings=tuple(_prompt_binding(r) for r in row.get("prompt_bindings", []) or []),
        standards_bindings=tuple(str(s) for s in row.get("standards_bindings", []) or [] if isinstance(s, str)),
    )
```

### Anti-Patterns to Avoid

- **Inventing a generic "AssetFramework" with subclasses per kind:** Three asset kinds × five states × the same evidence-aggregation logic is best served by per-kind dispatch + one shared dataclass set. A class hierarchy obscures the simple flow without adding power. CLAUDE.md says "three similar lines is better than a premature abstraction."
- **Renaming `route_status` without an alias cycle:** Existing prompt frontmatter uses `route_status`; renaming abruptly breaks `bin/validate-prompts.py` and the UI router. Honor a one-cycle alias: loader accepts either `route_status` or `lifecycle_state`, but write only `lifecycle_state` going forward; mark the alias for removal in Phase 9.
- **Auto-promoting workflows without approval:** Promotion proposals MUST flow through `writeback_approval_policy("workflow", "workflow-default")`. Phase 5 already returns `requires_approval=True` for that scope; bypassing it defeats governance.
- **Cross-asset rank collapse:** A `success_rate` of 0.9 for a prompt with 5 samples is weaker evidence than 0.85 for a prompt with 200 samples. Surface sample_size in the recommendation rationale; do not pretend small samples are statistically interchangeable.
- **Embedding stage bindings as opaque dicts inside `report_json`:** Phase 9 needs stage-level comparison queries. Persist `stage_evaluations[]` as structured JSON with stable keys; better still, denormalize stage findings into the existing `success_criteria_stage_findings` table (Phase 6) and keep `report_json.stage_evaluations[]` as the rollup pointer.
- **Encoding all ten planned workflows in this phase:** Spreads scope thin. Confirm in discuss-phase but recommend shipping four (`audit-only`, `audit-and-implement`, `standards-backfill`, `security-review`) with stage-rich vNext contracts, and deferring `repo-cleanup`, `UI-polish`, `PRD`, `test-first-implementation`, `research-to-plan`, `project-truth-update`, `prompt-experiment`, `agent-handoff-generation`, `codebase-architecture-review` until Phase 9 or a Phase 8 follow-up wave.
- **Letting `agentize._standards()` and `_success_criteria()` linger as authoritative:** Phase 6 already flagged these for deprecation. Phase 8 must converge them onto registry-driven recommendation; mark the helpers `@deprecated` in code comment and route through `asset_recommendation` for one cycle, then remove in Phase 9.
- **Hand-crafted `prompt_recommendation` rationale strings that don't cite evidence:** The existing `recommend_prompt_family` builds a rationale from "applicable_workflow_families and objective-tag overlap" — Phase 8 must extend it to also cite usefulness evidence (`success_rate=0.83 over 47 runs`) so the recommendation is auditable.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Approval policy for asset promotion | New approval engine | `writeback_approval_policy(layer_type, impact_scope, ...)` from `bin/aios_orchestration_runtime.py` (re-exported through `services/asset_lifecycle.py`) | Phase 5 already covers `prompt`/`skill`/`workflow` layer types and `prompt-default`/`skill-default`/`workflow-default` scopes. |
| Lifecycle transition persistence | New table | `promotion_lifecycle_items` (existing) | Already has `item_kind`/`item_key`/`status`/`evidence_json`/`status_reason`/`metadata_json` columns and is written today by `services/divergent_strategy.py`. |
| Workflow stage iteration | New executor | `execute_workflow` in `services/workflow_orchestration.py` | Already iterates stages, dispatches skills, collects validations. Phase 8 only adds binding resolution and stage-evaluation rollup. |
| Workflow ranking from text | New ranker | `rank_workflow_candidates` (existing) — extend filter to `lifecycle_state in {candidate, approved, active}` | Don't rewrite scoring; just narrow the candidate pool. |
| Prompt-family selection | New selector | `recommend_prompt_family` (existing) — extend to cite usefulness evidence | Existing applicable_workflow_families logic is correct; only the rationale gets richer. |
| Workflow + skill registry parsing | New parser | `load_workflow_registry` / `load_skill_registry` (existing) | Add backward-compatible default-handling, don't rewrite. |
| Per-skill validation in workflows | New validator | `validate_workflow_bindings` (existing) — extend to also resolve `required_inputs`/`required_outputs`/`validations`/`approval_gates`/`prompt_bindings`/`standards_bindings` | Same dispatch pattern, more checks. |
| Writeback emission | New writeback type | `insert_writeback(...)` + `insert_writeback_event(...)` in `bin/aios_orchestration_runtime.py` (Phase 5) | All promotion proposals are writebacks. |
| Per-criterion evaluator | New evaluator | `services/success_criteria.py` `evaluate_criterion` dispatch dict | Workflow stage `validations[]` bind to criterion_ids that already have evaluators. |
| Trust-signal UI contract | New types | `aios-ui/lib/trusted-signals.ts` (existing) | Recommendation rationale can re-use the `TrustedSignal<T>` shape. |
| Workflow promotion comparison math | New stats library | Per-workflow aggregation read directly from `workflow_execution_reports` joined with `success_criteria_stage_findings` and `improvement_writebacks` | Three SQL queries + Python aggregation; no need for pandas or numpy. |

**Key insight:** Phase 8 is overwhelmingly a **schema extension + projection layer**, not a new subsystem. The novel work is the five-state literal, the vNext stage binding dataclasses, the asset-usage-evidence projection, and the promotion proposal flow. Everything else extends primitives that Phases 1–7 already shipped.

## Runtime State Inventory

*Phase 8 is a schema-extension and registry-evolution phase, not a rename or refactor. The Runtime State Inventory categories apply here only narrowly. Confirmed below:*

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `promotion_lifecycle_items` rows currently written by `services/divergent_strategy.py` use freeform `status` strings (e.g., "promoted", "rejected", "pending"). Phase 8 narrows the literal to five values. | **Data migration:** map existing `status` values to the new literal. Inspect at start of phase via `SELECT DISTINCT status FROM promotion_lifecycle_items;` and add a one-shot migration script. Likely mapping: `promoted` → `active`, `rejected` → `deprecated`, `pending` → `candidate`. Confirm in discuss-phase. |
| Stored data | `prompts/registry.json` `route_status` field uses two values: `approved` and `candidate`. Phase 8 renames to `lifecycle_state` and remaps `approved` → `active` (since the prompts are in production use). | **Code edit + registry rev:** rename field, remap value, bump registry version. One-cycle alias support in the loader. |
| Live service config | None — registries are checked into git; no external CI/CD or UI configures these out-of-band. | None — verified by `grep -r "registry.json" .github/`. |
| OS-registered state | None — no OS-level service registers workflow keys. | None. |
| Secrets / env vars | None — workflow/skill/prompt registry entries do not contain secrets. | None. |
| Build artifacts / installed packages | `skills/{agentize,divergent-strategy,personalized-humanizer}/SKILL.md` source files are referenced via `source_path` / `installed_name` in `config/workflows/skills.json`. These are pure documentation and do not need rebuild. | None. |

**Nothing else found in scan.** The major runtime concern is the `promotion_lifecycle_items.status` migration; everything else is additive.

## Common Pitfalls

### Pitfall 1: Stage-Binding Defaults Hide Missing Validations

**What goes wrong:** The vNext `StageSpec` defaults `validations=()`, `approval_gates=()`, and `expected_artifacts=()` to empty tuples for backward compat. If a new planned workflow (e.g., `security-review`) is added with all-default fields, `validate_workflow_bindings` will pass it and `execute_workflow` will run a workflow that, by contract, should require validations.

**Why it happens:** Defaults exist to keep existing six workflows valid; but new entries should always declare bindings explicitly.

**How to avoid:** Add a `lifecycle_state`-aware check in `validate_workflow_bindings`: workflows with `lifecycle_state in {approved, active}` MUST declare `required_validations` on at least one stage; `candidate` workflows can omit them. New planned workflows added in Phase 8 start as `candidate` and graduate to `approved` only after validation contracts are filled in.

**Warning signs:** A new planned workflow ships with `lifecycle_state: "active"` and no `validations[]` on any stage. The binding validator passes; the workflow runs without validation; closeout reports zero stage findings.

### Pitfall 2: Five-State Migration Maps Existing Statuses Incorrectly

**What goes wrong:** `promotion_lifecycle_items.status` today contains freeform divergent-strategy values. A blind migration like `promoted → active` might activate prompt/skill/workflow assets that were promoted via the (looser) divergent flow but never went through Phase-5 approval.

**Why it happens:** Divergent's promotion path predates the Phase-5 governance contract.

**How to avoid:** Before migrating, snapshot the current distinct statuses + counts. Treat "promoted" via divergent as `candidate` rather than `active` unless `evidence_json` carries an explicit approval reference. Surface the migration plan in the Phase 8 plan-check for review.

**Warning signs:** Post-migration, `aios contracts-audit` shows assets in `active` state with no `improvement_writebacks` row tied to their promotion.

### Pitfall 3: Asset Recommendation Loops Back Into Its Own Evidence

**What goes wrong:** `recommend_assets_for_packet` recommends a prompt; the recommendation drives `agentize_request` to pick that prompt; the run completes (success or failure) and writes evidence; next recommendation re-uses the same prompt because its success rate just ticked up by 1/N. If N is small, the recommender locks onto an early winner and never explores alternatives.

**Why it happens:** Pure greedy ranking on `success_rate` without exploration.

**How to avoid:** When sample_size is below a threshold (e.g., 10), include a `candidate` (not-yet-approved) alternative in the top-3 results with a "exploration" rationale. After sample size grows, rely on raw ranking. This is intentionally simple — full multi-armed-bandit logic belongs in Phase 9.

**Warning signs:** `prompts_used` shows the same template_id dominating > 90% of routes within a workflow_family for a week with sample_size < 20.

### Pitfall 4: Promotion Proposals Bypass Phase 5 Approval

**What goes wrong:** `propose_workflow_promotion` writes a `promotion_lifecycle_items` row with `status="approved"` directly because the author thought the evidence was self-explanatory. The Phase-5 approval gate never fires; auditors lose the writeback trace.

**Why it happens:** Convenience — calling `promote_asset` directly skips the writeback step.

**How to avoid:** `promote_asset` MUST call `writeback_approval_policy` and create an `improvement_writebacks` row before transitioning the lifecycle. If `policy.requires_approval=True`, the transition is recorded with `status="proposed"`, not the target state, until the writeback is approved. Add a test: `test_promote_active_requires_writeback`.

**Warning signs:** A `promotion_lifecycle_items` row with `status="active"` exists but no matching `improvement_writebacks` row references it.

### Pitfall 5: Workflow Comparison Skewed by Stage Count

**What goes wrong:** `compare_workflow_effectiveness` reports `mean_blocker_count` for two workflows; `academic_paper_v1` has seven stages (more validation surface, more places to find blockers), `implementation-delivery` has four. The seven-stage workflow looks worse in aggregate even when it's qualitatively better.

**Why it happens:** Mean blocker count isn't normalized for stage count.

**How to avoid:** Surface both raw counts AND per-stage averages (`mean_blockers_per_stage`). Let the operator decide which view is fair for the comparison context. Add this to the rationale text.

**Warning signs:** Operator says "the workflow with more stages always looks worse" — that's the symptom.

### Pitfall 6: New Planned Workflow Families Have No Skill Implementations

**What goes wrong:** Phase 8 registers `security-review`, `audit-only`, `standards-backfill`, and `audit-and-implement` as new workflows in `config/workflows/registry.json` with stage-rich contracts. The stages reference skill keys that don't exist in `config/workflows/skills.json`; `validate_workflow_bindings` correctly rejects the registry; the new entries cannot load.

**Why it happens:** The schema/contract work outpaces the skill implementation work.

**How to avoid:** For each planned workflow shipped in Phase 8, register a minimal skill stub in `config/workflows/skills.json` (executor delegates to the existing `_execute_learned_workflow_skill` seam by naming the stub `<workflow>_executor`). Mark the skill `lifecycle_state: "draft"`; the workflow stays `candidate` until skills graduate. This preserves the schema discipline while not blocking the contract delivery.

**Warning signs:** `aios contracts-audit` shows new workflows in the registry but `WorkflowSpec.stages[].required_skills` references unresolvable skill keys.

### Pitfall 7: `validate-prompts.py` Breaks On Existing Prompts After Required-Field Extension

**What goes wrong:** Phase 8 adds `lifecycle_state`, `applicability`, `last_evaluated_at` to `REQUIRED_FIELDS` in `bin/validate-prompts.py`. Every existing prompt frontmatter that lacks these fields fails validation; CI breaks.

**Why it happens:** Hard requirement before backfill.

**How to avoid:** Two-step approach: (a) Phase 8 task 01 adds the fields to all five existing prompt frontmatter files; (b) Phase 8 task 02 extends `REQUIRED_FIELDS`. Do not reverse the order. Validate after each task.

**Warning signs:** `bin/validate-prompts.py prompts/research.md` exits non-zero after Phase 8 task 02 because task 01 didn't ship the field backfill.

### Pitfall 8: Architecture Boundary Violation On `writeback_approval_policy` Import

**What goes wrong:** `services/asset_lifecycle.py` imports `writeback_approval_policy` from `bin/aios_orchestration_runtime.py`; `tests/test_architecture_enforcement.py` fails because `services/` MUST NOT import from `bin/`.

**Why it happens:** The function lives in `bin/` for historical reasons (Phase 5 placed it there).

**How to avoid:** Two clean options: (a) Move `writeback_approval_policy` to `services/governance_policy.py` (preferred long-term but scope-expanding); (b) Re-export through a thin shim in `services/asset_lifecycle.py` that delegates to a top-level utility module if needed; or (c) Duplicate the small policy-classification function in `services/asset_lifecycle.py` for the three asset-related impact scopes only, with a code comment marking the duplication and pointing to the canonical source. **Recommend (c) for Phase 8 scope; flag a follow-up to consolidate in Phase 9.**

**Warning signs:** `uv run pytest tests/test_architecture_enforcement.py` fails after Phase 8 task 01.

## Code Examples

Verified patterns from existing code:

### Loading the Current Workflow Registry

```python
# Source: services/workflow_orchestration.py:load_workflow_registry (verbatim shape)
from services.workflow_orchestration import load_workflow_registry, load_skill_registry

workflows = load_workflow_registry()  # dict[str, WorkflowSpec]
skills = load_skill_registry()        # dict[str, SkillSpec]
```

### Existing Prompt Template Frontmatter (will be extended)

```json
{
  "id": "research",
  "name": "Research Synthesis",
  "version": "1.0",
  "classification": "plan",
  "prompt_family": "research_handoff",
  "route_status": "approved",
  "applicable_workflow_families": ["audit_only", "audit_and_implement", "content_generation"],
  "tags": ["research", "analysis", "compare", "synthesize"],
  "purpose": "Build a source-grounded synthesis...",
  "required_inputs": [...],
  "optional_inputs": [...],
  "last_updated": "2026-04-23",
  "file": "prompts/research.md"
}
```

After Phase 8 rename + extension:

```json
{
  "id": "research",
  "lifecycle_state": "active",
  "applicability": ["audit_only", "audit_and_implement", "content_generation"],
  "usefulness_evidence": {
    "sample_size": 47,
    "success_rate": 0.83,
    "last_used_at": "2026-05-19T22:31:00Z"
  },
  "last_evaluated_at": "2026-05-21T00:00:00Z"
  // ...all other existing fields kept
}
```

### Approval Policy Class Reuse (Phase 5)

```python
# Source: bin/aios_orchestration_runtime.py:writeback_approval_policy (verbatim)
policy = writeback_approval_policy(
    layer_type="workflow",
    impact_scope="workflow-default",
    proposed_change={"workflow_key": "implementation-delivery", "to_state": "active"},
)
# policy = {
#   "policy_class": "workflow-default_change",
#   "requires_approval": True,
#   "reason": "workflow-default changes require approval before promotion."
# }
```

### Existing Workflow Execution Report Shape (Will Carry stage_evaluations[])

```python
# Source: services/workflow_orchestration.py:execute_workflow (verbatim shape)
report = {
    "report_id": "workflow-report-<uuid>",
    "run_id": "...",
    "workflow_key": "implementation-delivery",
    "status": "completed",
    "stages": [
        {
            "stage_key": "parse_request",
            "kind": "parse_request",
            "status": "completed",
            "skills": [...],
            "issues": [],
            "started_at": "...",
            "ended_at": "...",
        }
        # ...
    ],
    "validations": [...],
    "required_validations": [...],
    "artifacts": {...},
    # PHASE 8 ADDS:
    # "stage_evaluations": [
    #   {stage_key, passed_validations, total_validations, blocker_count,
    #    warning_count, stage_finding_ids, outcome}
    # ]
}
```

### Existing promotion_lifecycle_items Writer (Phase 8 Will Standardize Status)

```python
# Source: services/divergent_strategy.py (verbatim shape)
conn.execute(
    """
    INSERT INTO promotion_lifecycle_items (
        id, item_kind, item_key, source_run_id, status,
        evidence_json, status_reason, created_at, updated_at, metadata_json
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
    (
        f"promo-{uuid.uuid4()}",
        "skill",                       # PHASE 8 standardizes to {prompt, skill, workflow}
        "memory_writeback_proposer",
        source_run_id,
        "candidate",                   # PHASE 8 standardizes to five-state literal
        json.dumps(evidence_refs),
        "Promoted via divergent portfolio with judge consensus",
        now_iso(),
        now_iso(),
        json.dumps(metadata),
    ),
)
```

### Existing UI Workflow Registry Reader (Will Add Lifecycle Surface)

```typescript
// Source: aios-ui/server/routers/workflows.ts (verbatim)
const loadWorkflowRegistry = (): WorkflowRegistry => {
  try {
    return JSON.parse(readFileSync(REGISTRY_PATH, "utf8")) as WorkflowRegistry;
  } catch {
    return { workflows: [] };
  }
};
// PHASE 8: extend WorkflowRegistry type with lifecycle_state, applicability,
// and per-stage required_inputs/outputs/validations/approval_gates/expected_artifacts/
// writeback_behavior/learning_signals fields.
```

### Existing Agentized Packet Construction (Will Source From Recommendation)

```python
# Source: services/agentize.py:agentize_request (verbatim shape, lines 440-490)
packet = AgentizedTaskPacket(
    packet_id=f"packet-{uuid.uuid4()}",
    normalized_objective=normalize(request),
    task_classifications=classifications,
    execution_mode=execution_mode,
    required_context=context_plan,
    relevant_skills=_relevant_skills(classifications),                # PHASE 8 -> from recommender
    relevant_success_criteria=_success_criteria(classifications),    # PHASE 8 -> from recommender
    relevant_standards=_standards(classifications),                  # PHASE 8 -> from recommender
    verification_plan=verification_steps,
    output_contract=output_contract,
    # ...
)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Prompt-only `route_status` field with two values (`approved`, `candidate`) | Cross-asset `lifecycle_state` literal with five values (`draft`, `candidate`, `approved`, `active`, `deprecated`) | Phase 8 (this phase) | Operators distinguish "approved but not yet promoted" from "actively serving traffic" and "sunset". |
| Workflow stage shape: `{key, kind, required_skills[]}` only | Workflow stage shape: + `required_inputs`, `required_outputs`, `validations`, `approval_gates`, `expected_artifacts`, `writeback_behavior`, `learning_signals`, `prompt_bindings`, `standards_bindings` | Phase 8 | Workflow contracts become inspectable and comparable; planning-doc bindings (`WORKFLOW_MATRIX.md`) become executable schema. |
| `agentize.py` hardcoded `_standards()` and `_success_criteria()` lists per classification | Evidence-backed recommendation via `services/asset_recommendation.py` | Phase 8 | Packet contents reflect what has actually worked on similar tasks, not author intuition. |
| Workflow ranking on objective text + workflow family only | Ranking also filters by `lifecycle_state in {candidate, approved, active}` and cites usefulness evidence in rationale | Phase 8 | Deprecated workflows stop being recommended; rationale becomes auditable. |
| `promotion_lifecycle_items` populated only by `services/divergent_strategy.py` with freeform status strings | Populated by all asset-promotion paths with the five-state literal; one cross-asset table | Phase 8 | One canonical source for "what is the current state of every reusable asset". |
| Workflow comparison nonexistent — operators read stage report counts manually | `compare_workflow_effectiveness(workflow_key, since)` returns rework_rate, validation_pass_rate, mean_blocker_count, writeback_usefulness, per-stage breakdown | Phase 8 | Promotion / revision / deprecation decisions sit on durable evidence. |
| Workflow promotion = direct registry edit | Workflow promotion = `propose_workflow_promotion` → Phase 5 writeback → approval → `promote_asset` → registry rev | Phase 8 | Asset mutation is governed, reviewable, and reversible. |
| Planned workflow families exist only in `WORKFLOW_MATRIX.md` prose | Four planned workflows (audit-only, audit-and-implement, standards-backfill, security-review) ship as `lifecycle_state: "candidate"` registry entries with stage-rich contracts | Phase 8 | Phase 7's `recommend_workflow_from_health` no longer recommends workflows that simply don't exist; recommendations surface as `available_in_registry: true` with `lifecycle_state: "candidate"` so operators know they're new. |
| `agentize_evaluations.selected_skills_json` / `selected_standards_json` records what was selected but not _why_ | Selection records also cite `asset_recommendation_id` for audit | Phase 8 | Every selection is traceable back to the evidence that justified it. |

**Deprecated/outdated:**
- `prompts/registry.json` `route_status` field — replaced by `lifecycle_state` (with one-cycle alias). Remove the alias in Phase 9.
- `services/agentize.py` `_standards()` and `_success_criteria()` private helpers — kept as a fallback for one cycle, then removed in Phase 9 once `asset_recommendation` has sufficient sample size.
- Freeform `status` values in `promotion_lifecycle_items` — migrated to the five-state literal; subsequent inserts MUST use the literal.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Phase 8 ships four planned workflow contracts (`audit-only`, `audit-and-implement`, `standards-backfill`, `security-review`) as `lifecycle_state: "candidate"` entries and defers the remaining six (`repo-cleanup`, `UI-polish`, `PRD`, `test-first-implementation`, `research-to-plan`, `project-truth-update`, `prompt-experiment`, `agent-handoff-generation`, `codebase-architecture-review`) to Phase 9 or a follow-up. | Summary / Anti-Patterns | If the user wants all ten in Phase 8, scope balloons significantly — each new workflow needs at least one skill stub and a stage-binding draft. Confirm in discuss-phase. |
| A2 | Renaming `prompts/registry.json` `route_status` → `lifecycle_state` with a one-cycle loader alias is acceptable. Existing prompt template `route_status: approved` values map to `lifecycle_state: active`. | Pattern 1 / Pitfall 7 | If "approved" is meant to mean "review accepted but not yet activated", the mapping should be `approved → approved` and there should be a separate human-driven step to flip to `active`. Confirm in discuss-phase. |
| A3 | Existing `promotion_lifecycle_items.status` values can be migrated: `promoted → candidate` (NOT `active` — because promotions predate Phase 5 approval governance), `rejected → deprecated`, `pending → candidate`. | Pitfall 2 | If the user prefers `promoted → active`, that bypasses Phase 5 governance discipline; recommend keeping conservative mapping. The user may want a manual review pass before any blanket migration. Confirm in discuss-phase. |
| A4 | `writeback_approval_policy` will be duplicated (not moved) into `services/asset_lifecycle.py` for Phase 8 to avoid `services → bin` import boundary violation. Consolidation deferred to Phase 9. | Pitfall 8 | If the user prefers a clean refactor in Phase 8 (move to `services/governance_policy.py`), scope grows by ~half a task (callers in `bin/aios_orchestration_runtime.py` + `bin/hook-stop.py` need import updates). Verifiable via `grep`. Confirm in discuss-phase. |
| A5 | The five-state literal is the right granularity. Adding `archived` (post-deprecated, hidden from default lists) is out of scope for Phase 8. | Pattern 1 | If the user wants `archived` now, add a sixth state and a single new transition rule. Low-risk extension. |
| A6 | Asset usage evidence is computed on read (no `asset_usage_snapshots` cache table in Phase 8). | Alternatives Considered | If profiling shows the recommendation call is hot (e.g., > 100ms per `agentize_request`), the cache table becomes necessary. Phase 8 plan should include a perf check. |
| A7 | Workflow effectiveness comparison uses a 30-day default lookback. | Pattern 4 | If the user wants a different default (e.g., last 50 runs regardless of date), the API takes `since: str | int` and the CLI default is configurable. Trivial to change. |
| A8 | `agentize.py` `_standards()` / `_success_criteria()` stay as fallback for one cycle. | Anti-Patterns | If the user wants them removed in Phase 8, scope grows by one cleanup task; otherwise Phase 9 owns removal. |
| A9 | Planned workflows added in Phase 8 register stub `<workflow>_executor` skills in `config/workflows/skills.json` so `validate_workflow_bindings` passes. The stubs delegate to `_execute_learned_workflow_skill`. | Pitfall 6 | If the user wants real skill implementations for the planned workflows in Phase 8 (not stubs), scope expands significantly. Confirm in discuss-phase. |
| A10 | The `applicability` field on assets is a tuple of workflow_family / task_family tags (free strings, not validated against a closed vocabulary). | Pattern 1 | If applicability needs to be schema-validated against a master taxonomy, an additional config file is required. Confirm. |
| A11 | Sample-size threshold for "exploration mode" recommendation (Pitfall 3) is set at 10 runs. | Pitfall 3 | Tunable. Phase 9 may want a smarter multi-armed-bandit policy; Phase 8's threshold is a deliberate placeholder. |

## Open Questions (RESOLVED)

1. **Should Phase 8 also register skill implementations (not just stubs) for the four planned workflow contracts?**
   - What we know: The schema work requires that skills referenced by a workflow exist in `config/workflows/skills.json`; stubs satisfy the validator.
   - What's unclear: Whether `audit-only`, `audit-and-implement`, `standards-backfill`, `security-review` are expected to actually *run* in Phase 8 or only exist as contracts that Phase 9 fleshes out.
   - Recommendation: Ship stubs in Phase 8 (workflows register, validate, and surface in route recommendations as `candidate`); real execution paths land in Phase 9. Discuss-phase should confirm.

2. **Is cross-project asset recommendation in scope?**
   - What we know: Per-project recommendation is the easier first cut (filter by `project_id`); cross-project would aggregate evidence across all projects.
   - What's unclear: Whether agents working on Project A should be recommended prompts that succeeded only on Project B.
   - Recommendation: Per-project + cross-project-as-fallback for the first cycle. If a per-project sample size is < 5, fall back to global evidence with a clear rationale tag.

3. **How are skills installed under `skills/{name}/SKILL.md` reconciled with `config/workflows/skills.json` entries?**
   - What we know: Some skills (agentize, divergent-strategy, personalized-humanizer) have `source_path: "skills/<name>/SKILL.md"` and `installed_name` in the JSON registry; others (validators, normalizers) live only in the JSON.
   - What's unclear: Whether Phase 8 needs to enforce a 1:1 mapping or whether some skills are intentionally registry-only.
   - Recommendation: Phase 8 doesn't change this. Document in the migration notes that mixed sourcing is intentional.

4. **Does `lifecycle_state` belong on each individual prompt template OR on the prompt _family_ (where the family is the deduplication unit)?**
   - What we know: Today each template has its own `route_status`. The recommender groups by `prompt_family`.
   - What's unclear: Whether two templates in the same `prompt_family` (e.g., two implementation handoffs) can have divergent lifecycle states.
   - Recommendation: Keep per-template `lifecycle_state` (more granular, no information loss). Per-family rollup is computed at read time.

5. **Should the workflow registry version bump to a date or to a semver?**
   - What we know: `prompts/registry.json` uses `"2026-04-23"`; `config/workflows/registry.json` uses `"version": "2026-04-23"` with no semantic version; `config/standards/registry.json` uses `"2026.05.0"`.
   - What's unclear: Which format Phase 8 should adopt.
   - Recommendation: Match existing convention per file (date for workflows/prompts, semver-date for standards). Don't unify in this phase.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12+ | All Phase 8 work | ✓ | 3.12 (per `pyproject.toml`) | — |
| sqlite3 stdlib | Persistence (lifecycle migration + read-time projections) | ✓ | stdlib | — |
| ruff | Lint gate | Assumed (per quality ladder) | per `pyproject.toml` | Quality ladder fails fast if missing |
| basedpyright | Typecheck gate | Assumed | per `pyproject.toml` | — |
| pytest 8.x | Test gate | ✓ (used in Phases 5/6/7) | — | — |
| vulture | Dead-code report | Assumed | per `pyproject.toml` | Report-only, non-blocking |
| `uv` runner | Existing Phase verification commands use it | Likely ✓ (per `uv.lock`) | — | Fall back to `python -m pytest` |
| pnpm | UI quality ladder | Assumed (per `aios-ui/`) | — | — |
| better-sqlite3 | UI server DB access | ✓ (per `aios-ui/package.json`) | — | — |
| tRPC v11 | UI router boundary | ✓ | — | — |
| zod | UI runtime validation | ✓ | — | — |
| `node:fs`, `node:path`, `node:crypto` (stdlib) | UI registry file reads | ✓ | — | — |

**Missing dependencies with no fallback:** None identified.

**Missing dependencies with fallback:** None; all dependencies are in-tree or stdlib.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x (Python 3.12) + Node built-in test runner for context tests |
| Config file | `pyproject.toml` (ruff + basedpyright + vulture sections); no separate `pytest.ini` block |
| Quick run command | `uv run pytest tests/test_workflow_orchestration.py tests/test_asset_lifecycle.py tests/test_asset_recommendation.py tests/test_workflow_promotion.py tests/test_agentize.py tests/test_aios_cli.py -x -q` |
| Full suite command | `uv run pytest -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| ASSET-01 | Registry loader reads `lifecycle_state` + `applicability` + `purpose` for prompts/skills/workflows; defaults for missing fields | unit | `uv run pytest tests/test_workflow_orchestration.py::test_load_registry_normalizes_lifecycle_fields -x` | ❌ Wave 0 |
| ASSET-01 | Asset usefulness evidence aggregates from `prompts_used`, `agentize_evaluations`, `workflow_execution_reports`, `workflow_skill_experiments` | integration | `uv run pytest tests/test_asset_recommendation.py::test_build_asset_usage_evidence_joins_all_sources -x` | ❌ Wave 0 |
| ASSET-02 | `promote_asset` rejects invalid transitions (e.g., `draft → active`) | unit | `uv run pytest tests/test_asset_lifecycle.py::test_promote_asset_rejects_invalid_transition -x` | ❌ Wave 0 |
| ASSET-02 | `promote_asset` writes a `LifecycleTransition` row to `promotion_lifecycle_items` on every state change | unit | `uv run pytest tests/test_asset_lifecycle.py::test_promote_asset_writes_lifecycle_transition -x` | ❌ Wave 0 |
| ASSET-02 | Migration script remaps existing `promotion_lifecycle_items.status` freeform values to the five-state literal | integration | `uv run pytest tests/test_asset_lifecycle.py::test_migration_remaps_legacy_statuses -x` | ❌ Wave 0 |
| ASSET-03 | `AssetUsageEvidence.per_workflow` records per-workflow success/failure counts | unit | `uv run pytest tests/test_asset_recommendation.py::test_usage_evidence_records_per_workflow_outcomes -x` | ❌ Wave 0 |
| ASSET-04 | `recommend_assets_for_packet` returns `active` assets first, then `approved`, then `candidate` | unit | `uv run pytest tests/test_asset_recommendation.py::test_recommendation_orders_by_lifecycle_state -x` | ❌ Wave 0 |
| ASSET-04 | `agentize_request` populates `relevant_skills` from `recommend_assets_for_packet` (not hardcoded) | integration | `uv run pytest tests/test_agentize.py::test_agentize_skills_come_from_recommender -x` | ❌ Wave 0 |
| ASSET-04 | `recommend_route_primitives` (Phase 1) carries `skill_recommendations` and `workflow_alternatives` in its result | integration | `uv run pytest tests/test_task_routing.py::test_route_includes_asset_recommendations -x` | ❌ Wave 0 |
| WFLO-01 | Workflow registry loader parses `required_inputs`, `required_outputs`, `validations`, `expected_artifacts` on stages | unit | `uv run pytest tests/test_workflow_orchestration.py::test_stage_spec_loads_vnext_bindings -x` | ❌ Wave 0 |
| WFLO-01 | `validate_workflow_bindings` errors when a `required_inputs` source is unresolvable | unit | `uv run pytest tests/test_workflow_orchestration.py::test_validate_bindings_rejects_unresolvable_input_source -x` | ❌ Wave 0 |
| WFLO-01 | Existing six workflows load unchanged with default bindings (backward compat) | unit | `uv run pytest tests/test_workflow_orchestration.py::test_existing_workflows_load_with_defaults -x` | ❌ Wave 0 |
| WFLO-02 | `StageSpec` carries `approval_gates`, `writeback_behavior`, `learning_signals`, `prompt_bindings`, `standards_bindings` | unit | `uv run pytest tests/test_workflow_orchestration.py::test_stage_spec_carries_full_bindings -x` | ❌ Wave 0 |
| WFLO-02 | A stage's `approval_gates` invoke `writeback_approval_policy` with the declared `impact_scope` | integration | `uv run pytest tests/test_workflow_orchestration.py::test_stage_approval_gate_invokes_policy -x` | ❌ Wave 0 |
| WFLO-03 | `execute_workflow` produces `report.stage_evaluations[]` with `outcome` per stage | integration | `uv run pytest tests/test_workflow_orchestration.py::test_stage_evaluation_summary_in_report -x` | ❌ Wave 0 |
| WFLO-03 | Stage evaluation summary joins Phase 6 `success_criteria_stage_findings` | integration | `uv run pytest tests/test_workflow_orchestration.py::test_stage_evaluation_summary_includes_stage_findings -x` | ❌ Wave 0 |
| WFLO-04 | `compare_workflow_effectiveness` returns `rework_rate`, `validation_pass_rate`, `mean_blocker_count`, `writeback_usefulness` | integration | `uv run pytest tests/test_workflow_promotion.py::test_compare_workflow_returns_metrics -x` | ❌ Wave 0 |
| WFLO-04 | `propose_workflow_promotion` writes an `improvement_writebacks` row with `policy_class=workflow-default_change` | integration | `uv run pytest tests/test_workflow_promotion.py::test_propose_promotion_uses_phase_5_policy -x` | ❌ Wave 0 |
| WFLO-04 | Promotion requires approval (`requires_approval=True`) before lifecycle flips to `active` | integration | `uv run pytest tests/test_workflow_promotion.py::test_promotion_requires_approval_before_active -x` | ❌ Wave 0 |
| WFLO-04 | CLI `aios workflow-compare --workflow-key X --since 30d` outputs JSON with metrics | integration | `uv run pytest tests/test_aios_cli.py::test_workflow_compare_cli -x` | ❌ Wave 0 |
| WFLO-04 | UI `getWorkflowEffectiveness` returns the projected metrics | integration | `cd aios-ui && pnpm lint && pnpm tsc --noEmit` (type-level guarantee); add manual fixture test if `pnpm test` is wired later | partial — type-level only |
| Cross-cutting | `aios contracts-audit` adds an `AssetLifecycle` row with status `implemented` once `promotion_lifecycle_items` carries normalized five-state values | unit | `uv run pytest tests/test_aios_cli.py::test_contracts_audit_includes_asset_lifecycle -x` | ❌ Wave 0 |
| Cross-cutting | `bin/validate-prompts.py` rejects a prompt frontmatter missing `lifecycle_state` after the field becomes required | unit | `uv run pytest tests/test_validate_prompts.py::test_lifecycle_state_required -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:**
  - Python: `uv run pytest tests/test_workflow_orchestration.py tests/test_asset_lifecycle.py tests/test_asset_recommendation.py tests/test_workflow_promotion.py tests/test_agentize.py tests/test_aios_cli.py tests/test_validate_prompts.py tests/test_task_routing.py -x -q && uv run ruff check services bin tests && uv run ruff format --check services bin tests && uv run basedpyright`
  - UI (when TS files change): `cd aios-ui && pnpm lint && pnpm tsc --noEmit`
- **Per wave merge:**
  - `uv run pytest -q && uv run ruff check . && uv run ruff format --check . && uv run basedpyright && uv run vulture services bin --min-confidence 70`
  - `cd aios-ui && pnpm lint && pnpm tsc --noEmit`
  - `uv run python bin/validate-prompts.py prompts/registry.json` (after task that bumps required fields)
- **Phase gate:**
  - Full suite green
  - `aios contracts-audit` shows `AssetLifecycle` contract row with `status: implemented`
  - `aios asset-lifecycle list --kind workflow` shows all six existing workflows with valid `lifecycle_state` values
  - `aios workflow-compare --workflow-key implementation-delivery --since 30d` returns a populated metrics payload
  - Manual operator check: open `aios-ui/app/workflows` and confirm lifecycle state renders per workflow with a drill-down to effectiveness metrics

### Wave 0 Gaps

- [ ] `tests/test_asset_lifecycle.py` — NEW file, covers state-transition rules, migration, promotion-with-writeback
- [ ] `tests/test_asset_recommendation.py` — NEW file, covers evidence aggregation, ranking, exploration fallback
- [ ] `tests/test_workflow_promotion.py` — NEW file, covers comparison + propose + finalize flow
- [ ] `tests/test_workflow_orchestration.py` — extend with vNext schema + stage evaluation tests (8 new test functions listed above)
- [ ] `tests/test_agentize.py` — extend (recommender-driven skills/standards) (1 new test)
- [ ] `tests/test_aios_cli.py` — extend (CLI subcommands + contracts-audit row) (3 new tests)
- [ ] `tests/test_validate_prompts.py` — extend (lifecycle_state required) (1 new test)
- [ ] `tests/test_task_routing.py` — extend (route includes asset recs) (1 new test)
- [ ] `aios-ui/lib/types.ts` — extend with `AssetLifecycleState`, `AssetRecord`, `WorkflowEffectiveness` types (type-level Wave 0 work; no test file)
- [ ] `aios-ui/server/aios/asset-lifecycle.ts` — NEW file
- [ ] `aios-ui/server/aios/workflow-effectiveness.ts` — NEW file
- [ ] No new conftest.py needed — existing tests use direct `sqlite3.connect(":memory:")` patterns and per-test schema seeding
- [ ] No framework install required; pytest + ruff + basedpyright + pnpm already wired

## Security Domain

> Phase 8 introduces no new authentication, session management, network surface, or cryptographic concerns. Security applicability is bounded to: (a) promotion of assets via Phase-5 approval policy classes, (b) `validate-prompts.py` validating frontmatter strictly so unsigned/unscoped prompt content cannot enter the registry, (c) `usefulness_evidence` payloads not leaking sensitive content beyond what `prompts_used.prompt_text` and `workflow_execution_reports` already expose, and (d) the `security-review` workflow contract (if shipped in Phase 8 per A1) preserving its existing-criterion bindings.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | n/a — internal CLI / hook / UI-server surface |
| V3 Session Management | no | n/a |
| V4 Access Control | yes | Phase-5 approval policy classes gate promotion of any asset whose `impact_scope ∈ {prompt-default, skill-default, workflow-default}`; Phase 8 reuses without weakening. |
| V5 Input Validation | yes | Registry JSON parsed via `_load_json` with type guards; new fields (`lifecycle_state`, `applicability`, `usefulness_evidence`) validated against the five-state literal and tuple-of-strings shape. UI tRPC routes validate input with `zod`. |
| V6 Cryptography | no | n/a |
| V7 Error Handling | yes | Promotion fails closed: if `writeback_approval_policy` returns `requires_approval=True` and no approval is recorded, the lifecycle transition MUST NOT advance to `active`. Recommendation builder returns empty results with a clear rationale rather than crashing on missing evidence sources. |
| V10 Malicious Code | partial | `validate-prompts.py` enforces frontmatter schema, blocking malformed entries; new required fields prevent unscoped prompts. |
| V13 API & Web Service | partial | tRPC routes already validate inputs; new `getAssetLifecycle` / `getWorkflowEffectiveness` / `promoteAsset` routes use the same `zod` pattern. No new external API surface. |
| V14 Configuration | yes | New registry fields are reviewable in git; no secrets enter registries; lifecycle transitions are logged with actor + rationale. |

### Known Threat Patterns for Asset Lifecycle and Recommendation

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Stealth promotion — asset flipped to `active` without an `improvement_writebacks` audit row | Repudiation / Tampering | `promote_asset` MUST go through `propose_workflow_promotion` / `propose_asset_promotion`; bare lifecycle inserts are forbidden. Architecture test `test_promote_active_requires_writeback` enforces. |
| Recommendation poisoning — an attacker (or noisy bug) writes fake evidence rows that inflate one asset's success rate | Tampering | Evidence sources (`prompts_used`, `agentize_evaluations`, `workflow_execution_reports`, `workflow_skill_experiments`) are written only by managed hooks and the orchestration runtime; no operator write path. Recommendation rationale cites raw sample_size so anomalies are visible. |
| Cross-asset confusion — `promotion_lifecycle_items.item_kind` set to an unexpected value (e.g., "memory" by divergent strategy) collides with prompt/skill/workflow lookups | Tampering | Phase 8's read paths filter `item_kind in {'prompt','skill','workflow'}` explicitly; legacy `item_kind='memory'` rows remain untouched. |
| `validate-prompts.py` bypassed via direct registry edit | Tampering / Integrity | CI runs `validate-prompts.py` on `prompts/registry.json` and the markdown files in PRs; pre-commit hook can run it locally. |
| Manual lifecycle override flips state without rationale | Repudiation | `promote_asset` requires a non-empty `rationale` string; CLI/UI must collect it; tests enforce. |
| `last_used_at` becomes a side channel for inferring agent behavior on private project_ids | Information Disclosure | `usefulness_evidence` aggregated at asset level NEVER exposes per-project rows by default; cross-project rollup is the default; per-project drill-down is gated behind the operator-level UI surface that already shows project rows. |
| New planned workflow added with `lifecycle_state: "active"` but no validations — runs without enforcement | Tampering / Integrity | `validate_workflow_bindings` rejects `active` workflows without validations (Pitfall 1). |
| Recommendation cached past asset deprecation — recommender continues to suggest a deprecated asset | Tampering | Recommendation is read-time (no `asset_usage_snapshots` cache in Phase 8); deprecated assets are filtered out at query time. If caching is added later, cache key must include lifecycle state. |

## Sources

### Primary (HIGH confidence)

- `config/workflows/registry.json` (in-tree, 347 lines) — six current workflow rows with `key`/`workflow_family`/`purpose`/`trigger_hints`/`output_contract`/`required_validations`/`stages[]`. [VERIFIED: read complete file]
- `config/workflows/skills.json` (in-tree, 560 lines) — 23 skill specs with `key`/`purpose`/`allowed_stages`/`input_schema`/`output_schema`/`invariants`/`failure_conditions`/`side_effects`/`execution_mode`/`source_path`/`installed_name`. [VERIFIED: read complete file]
- `prompts/registry.json` (in-tree, 188 lines) — five templates with `id`/`name`/`version`/`classification`/`prompt_family`/`route_status`/`applicable_workflow_families`/`tags`/`purpose`/`required_inputs`/`optional_inputs`. [VERIFIED: read complete file]
- `services/workflow_orchestration.py` (in-tree, 979 lines) — `WorkflowSpec`, `StageSpec`, `SkillSpec` dataclasses; `load_workflow_registry`, `load_skill_registry`, `validate_workflow_bindings`, `rank_workflow_candidates`, `recommend_prompt_family`, `recommend_route_primitives`, `execute_workflow`, `_execute_skill`. [VERIFIED: read complete file]
- `services/agentize.py` (in-tree) — `agentize_request`, `_standards`, `_success_criteria`, `relevant_skills` selection, `agentize_evaluations` schema and writer. [VERIFIED: read key sections]
- `services/divergent_strategy.py` (in-tree) — `promotion_lifecycle_items` schema (`item_kind`, `item_key`, `source_run_id`, `status`, `evidence_json`, `status_reason`, `created_at`, `updated_at`, `metadata_json`); current writer with status values `promoted`/`rejected`/`pending`/`candidate`. [VERIFIED: read schema-ensure block]
- `services/workflow_experiments.py` (in-tree, 779 lines) — `workflow_skill_experiments`, `github_skill_candidates`, `workflow_paper_fixtures` schemas and writers. [VERIFIED: read first 120 lines]
- `services/workflow_synthesis.py` (in-tree, 917 lines) — `workflow_synthesis_proposals` with `pending_approval`/`approved`/`rejected` lifecycle and `workflow_spec_json` + `skill_specs_json` + `validation_plan_json` + `evidence_json` columns. [VERIFIED: schema grep]
- `services/task_routing.py` (in-tree) — `RouteResult` with `task_family`, `workflow_key`, `prompt_family`, `recommended_surface`; consumes `recommend_route_primitives`. [VERIFIED: read]
- `services/aios_cli.py` (in-tree) — `_contracts_audit_payload` (lines 2706-2772) lists current canonical contracts; `EVALUATION_FINDING_LIFECYCLE_STATES` literal (line 146); `promotion_lifecycle_items` consumer (lines 2458-2474). [VERIFIED: read]
- `bin/aios_orchestration_runtime.py` (in-tree) — `writeback_approval_policy` (lines 816-851) with policy classes for `prompt-default`/`skill-default`/`workflow-default` impact scopes; `insert_writeback`, `insert_writeback_event`. [VERIFIED: read]
- `bin/hook-prompt-submit.py` (in-tree) — `prompt_library_links` writer, `is_reusable_candidate`, `prompts_used` writer with classification + outcome_score + reusable_candidate + retrieval fields. [VERIFIED: grep]
- `bin/hook-stop.py` (in-tree) — `prompts_used` reader (lines 368-400), criteria evaluation invocation, governed closeout shape. [VERIFIED: grep]
- `bin/sync-prompts.py` + `bin/validate-prompts.py` (in-tree, 141 + 358 lines) — prompt frontmatter validation with `REQUIRED_FIELDS` tuple and `VALID_CLASSIFICATIONS` set. [VERIFIED: read first 80 lines of validate-prompts.py]
- `schema.sql` (in-tree) — `promotion_lifecycle_items`, `workflow_learning_events`, `workflow_synthesis_proposals`, `improvement_writebacks`, `agentize_evaluations`, `prompts_used`, `workflow_execution_reports`, `success_criteria_stage_findings` (Phase 6 add) tables. [VERIFIED: read lines 480-805]
- `aios-ui/server/routers/workflows.ts` (in-tree, 442 lines) — UI workflow + workflow_synthesis_proposals projection. [VERIFIED: read first 100 lines]
- `aios-ui/server/routers/prompts.ts` (in-tree, 237 lines) — prompt template + prompts_used projection. [VERIFIED: read first 100 lines]
- `aios-ui/server/aios/schema.ts` (in-tree) — UI-side schema bootstrapper, includes `promotion_lifecycle_items` create (line 356). [VERIFIED: grep]
- `.planning/REQUIREMENTS.md` — ASSET-01..04, WFLO-01..04 wording. [VERIFIED: read]
- `.planning/ROADMAP.md` — Phase 8 scope, expected outputs, dependencies, observable success criteria. [VERIFIED: read]
- `.planning/REQUIREMENTS_CODE_SURFACE_MATRIX.md` (lines 76-87) — Phase 8 primary/supporting surfaces + tier-one targets + evidence targets. [VERIFIED: read]
- `.planning/TIER_ONE_ACCEPTANCE_CHECKLIST.md` (lines 168-189) — Phase 8 capability gates, evidence gates, failure conditions. [VERIFIED: read]
- `.planning/WORKFLOW_MATRIX.md` — current + planned workflows with stage shape, prompt family, required skills/tools, validations, approval gates, artifacts, writebacks, learning signals, roadmap ownership, tier-one gaps. [VERIFIED: read complete file]
- `.planning/FUNCTIONALITY_MAP.md` — prompt/skill/workflow lifecycle is "Partial", owned by Phase 8 + Phase 9; experiments are Phase 8 + Phase 9. [VERIFIED: read]
- `.planning/phases/05-*/05-CONTEXT.md` — Phase 5 governance/writeback contract that Phase 8 inherits. [VERIFIED: read]
- `.planning/phases/06-*/06-RESEARCH.md` — `agentize.py` `_standards()` / `_success_criteria()` deprecation flag; `success_criteria_stage_findings` table that Phase 8 uses for stage evaluation. [VERIFIED: read]
- `.planning/phases/07-*/07-RESEARCH.md` — `recommend_workflow_from_health` outputs `available_in_registry: false` for `standards backfill` / `audit-only` / `codebase architecture review` / `security review` (Phase 8 owns making them available); reuses `writeback_approval_policy` for workflow promotion gates. [VERIFIED: read]
- `.planning/phases/01-*/01-CONTEXT.md` — Phase 1 route contract carries `prompt_recommendation`; Phase 8 extends with `skill_recommendations` + `workflow_alternatives`. [VERIFIED: read]
- `.planning/phases/02-*/02-CONTEXT.md` — Phase 2 packet contract that Phase 8 enriches via asset recommendation. [VERIFIED: read]
- `AGENTS.md` — local-first, governance, brownfield continuity, explainability constraints; `services/` cannot import `bin/`. [VERIFIED: read]
- `.planning/PROJECT.md` exists per repo state; AGENTS.md confirms PROJECT.md is the durable truth file. [VERIFIED: file presence check]

### Secondary (MEDIUM confidence)

- `services/standards_health.py` Phase 7 `recommend_workflow_from_health` rule table — confirms Phase 8 needs to register `audit-only`/`audit-and-implement`/`standards-backfill`/`security-review` so health-state recommendations can surface them as `available_in_registry: true`. [VERIFIED via Phase 7 research]
- `tests/test_workflow_orchestration.py`, `tests/test_workflow_experiments.py`, `tests/test_workflow_synthesis.py`, `tests/test_task_routing.py`, `tests/test_hook_prompt_submit.py`, `tests/test_validate_prompts.py` — existing test patterns for in-memory sqlite + registry fixture loading. [VERIFIED: file listing]
- `skills/agentize/SKILL.md`, `skills/divergent-strategy/SKILL.md` — confirm `source_path` linkage convention for some-but-not-all skills. [VERIFIED: ls]

### Tertiary (LOW confidence)

- None — Phase 8 is an internal phase researched entirely against in-tree code, config, and planning docs; no external web sources required.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every primary surface is in-tree and read directly during research; no external dependency assumptions.
- Architecture: HIGH — pattern follows Phase 5/6/7 conventions exactly; the lifecycle and recommender layers are additive and use existing data shapes.
- Workflow schema vNext: HIGH — dataclass extension and JSON registry shape are mechanical; backward-compat strategy is verified against existing six workflows.
- Asset recommendation: MEDIUM — the recommender ranking rule (active > approved > candidate, then success_rate, then sample_size, then recency) is opinionated; the user may want different prioritization (e.g., explore-first for low-evidence assets). Confirm in discuss-phase.
- Promotion governance reuse of Phase 5: HIGH — `writeback_approval_policy` already returns `requires_approval=True` for all three relevant impact scopes; no new policy work needed.
- Planned workflow scope: MEDIUM — shipping four out of ten planned workflows (A1) is a deliberate scope cut to keep Phase 8 focused; user may want all ten or a different subset.
- `promotion_lifecycle_items` legacy status migration: MEDIUM — the mapping (`promoted → candidate`, `rejected → deprecated`, `pending → candidate`) is conservative but not formally validated; recommend snapshotting current distinct statuses + counts at start of phase before applying.
- Architecture-boundary handling for `writeback_approval_policy`: MEDIUM — duplicating into `services/asset_lifecycle.py` is pragmatic for Phase 8 but flags a Phase 9 consolidation task.

**Research date:** 2026-05-21
**Valid until:** 2026-06-21 (30 days — stable surfaces; the `config/workflows/registry.json` shape evolves during this phase itself, which is the explicit purpose of the phase).
