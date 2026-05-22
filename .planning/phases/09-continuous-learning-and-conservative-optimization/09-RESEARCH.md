---
phase: 09-continuous-learning-and-conservative-optimization
phase_number: "09"
type: research
updated: 2026-05-21
---

# Phase 9 Research

**Researched:** 2026-05-21
**Domain:** Cross-run learning signals, recurring-failure detection, conservative route/packet/workflow improvement proposals, operator-visible compounding
**Confidence:** HIGH

## Summary

Phase 9 turns the per-run evidence already captured by Phases 1–8 into **cross-run, governed self-improvement** of routing, packets, workflows, and evaluation — without silently mutating policy. The structural primitives are already substantially present: `workflow_learning_events` (created in `bin/aios_orchestration_runtime.py` lines 191-208 and re-ensured in `services/aios_cli.py` lines 2111-2132) already records per-run `evidence_type` ∈ {`workflow_evidence`, `prompt_template_evidence`, `standards_health_evidence`, `bug_quality_evidence`, `no_learning_signal`} with `proposal_target`, `confidence`, `approval_state`, `rationale`, and `source_json` [VERIFIED: read schema.sql:499-510 + services/aios_cli.py:2111-2193]; `services/aios_cli.py:_workflow_learning_payload` (lines 2208-2377) already classifies terminal runs into the five-bucket taxonomy and persists rows idempotently keyed on `(run_id, evidence_type, proposal_target)` [VERIFIED: read]; the CLI `aios workflow-learning-audit` is already wired (lines 3197, 3326, 3536-3538) and returns `summary{terminal_run_count, runs_with_learning, no_learning_count, inferred_evidence_count, persisted_event_count, proposal_count, pending_approval_count}` plus `classification_counts`, `persisted_events[]`, `inferred_evidence[]`, `no_learning_runs[]`, `proposals[]` [VERIFIED: read]; `improvement_writebacks` + `improvement_writeback_events` (Phase 5) already carry the cross-asset governed-proposal contract [VERIFIED: schema.sql:376-410]; `promotion_lifecycle_items` (Phase 5/8) carries cross-asset state transitions [VERIFIED: schema.sql:487-498]; `divergent_runs` + `divergent_candidates` + `divergent_judgments` + `memory_writeback_proposals` (the `divergent-strategy` workflow) already run governed strategy comparisons and emit proposals [VERIFIED: schema.sql:411-477 + services/divergent_strategy.py]; `experiments` + `workflow_skill_experiments` + `github_skill_candidates` carry experiment outcomes [VERIFIED: schema.sql:147-158 + services/workflow_experiments.py]; `agentize_evaluations` records per-packet `outcome_quality`, `tests_passed`, `follow_up_required`, `major_repair_required`, `selected_skills_json`, `selected_standards_json` [VERIFIED: schema.sql:78-92]; `workflow_execution_reports.report_json` carries per-stage state and (after Phase 8 ships) `stage_evaluations[]` [VERIFIED: read]; `success_criteria_findings` + `success_criteria_stage_findings` (Phase 6) record validation findings with lifecycle states (`open`/`accepted`/`resolved`/`waived`/`stale`) [VERIFIED: read services/aios_cli.py:146]; `standards_health_snapshots` + `standards_delta_items` (Phase 7) carry domain-level deltas; `aios-ui/server/aios/learning.ts:proposeRunWritebacks` already emits the legacy "project + workflow learning" pair of writebacks on terminal runs [VERIFIED: read complete file]; `aios-ui/server/aios/control-plane.ts` already surfaces governance proposals + run gaps via `terminalRunGaps` [VERIFIED: read lines 199-236].

What is missing and what Phase 9 must add: (1) **A learning signal taxonomy that goes wider than evidence_type** — the current five values are run-shape buckets (workflow vs prompt vs standards vs bug vs none), not signal kinds (ignored_rule, bloated_packet, weak_prompt, weak_workflow, route_misroute, repeated_failure). Phase 9 must add a **signal taxonomy** (a small typed literal set) and persist it either as a `signal_kind` column on `workflow_learning_events` or as a sibling `learning_signals` table that joins to `workflow_learning_events`. (2) **Cross-run analysis** — `_workflow_learning_payload` aggregates evidence per terminal run; nothing today scans across runs to detect "the same `success_criteria_findings` blocker fires 7 times in 30 days on the same workflow" or "this prompt template's `outcome_quality` is < 3 on 60% of runs since 2026-05-01" or "this packet's `loaded_section_count` is 2.3× the mean and rework_rate is 4× the mean." Phase 9 must add a `services/learning_analysis.py` module that runs **bounded** queries (last N runs or last D days) against `agentize_evaluations`, `success_criteria_findings`, `workflow_execution_reports`, `prompts_used`, `improvement_writebacks`, `standards_delta_items`, `briefing_packets` and emits `RecurringPattern` records. (3) **Conservative improvement proposals** — `improvement_writebacks` (Phase 5) is the right rail, but no module today **synthesizes** an improvement proposal from a `RecurringPattern` (e.g., "Pattern: route X frequently misroutes Y → propose route hint update with `requires_approval=True`"). Phase 9 adds `services/conservative_optimizer.py` that converts pattern → writeback proposal with strict thresholds (minimum sample size, minimum recurrence count, minimum confidence interval) and ALWAYS sets `requires_approval=True` for routing/packet/evaluation policy changes — never `proposed → active` autoflip. (4) **Feedback into Phase 1 and Phase 2** — Phase 1's `recommend_route_primitives` and Phase 2's packet compilation must learn from Phase 9 evidence. The clean seam is to introduce a `route_quality_signals` + `packet_quality_signals` read-time projection that the existing recommenders consult as a tie-breaker, not as a replacement (route hint suggestions from pattern analysis must be **applied only after approval** via writebacks → asset lifecycle promotion, not at runtime by the recommender). (5) **Operator-visible compounding** — `aios-ui/server/aios/learning.ts` exists but only proposes per-run writebacks; nothing today shows "what each meaningful run improved for future work" across runs. Phase 9 adds a `LearningImpact` projection (per-run: which routes/prompts/workflows now have better evidence because of this run; per-workflow: rework_rate trajectory over time; per-prompt: success_rate trajectory) and surfaces it via `aios-ui/server/routers/control-plane.ts` (extend) or a new `learning.ts` router. (6) **`prompt experiment` and `divergent-strategy` feed into governed promotion** — `divergent_strategy.py` already calls `transition_promotion_lifecycle` (line 578) but uses freeform statuses; after Phase 8 standardizes the five-state literal, Phase 9 wires divergent + experiment outcomes into the same `propose_workflow_promotion`/`propose_asset_promotion` paths so portfolio winners flow through writeback gates rather than direct lifecycle writes.

**Primary recommendation:** Treat Phase 9 as **four additive layers on top of Phase 5/6/7/8 primitives**, in this order: **(a) Learning signal taxonomy** — extend `workflow_learning_events` with a `signal_kind` TEXT column (nullable for back-compat) and seed a typed literal `LearningSignalKind = Literal["repeated_failure","ignored_rule","bloated_packet","weak_prompt","weak_workflow","route_misroute","standards_regression","writeback_adopted","writeback_rejected","compounding_gain"]`; the new column is read-only for existing rows, populated for new ones; the existing five `evidence_type` values stay as the **run-shape bucket** and `signal_kind` becomes the **signal-content axis** — two orthogonal classifications, both surfaced. **(b) Cross-run analysis module** — `services/learning_analysis.py` exposes `detect_recurring_patterns(conn, *, since: str | None, project_id: str | None) -> list[RecurringPattern]` with a small dispatch table of pattern detectors (`detect_repeated_failures`, `detect_ignored_rules`, `detect_bloated_packets`, `detect_weak_prompts`, `detect_weak_workflows`, `detect_route_misroutes`); each detector returns `RecurringPattern{signal_kind, evidence_run_ids, sample_size, recurrence_count, confidence, summary, suggested_remediation_class}`. **(c) Conservative optimizer** — `services/conservative_optimizer.py` consumes `RecurringPattern[]` and emits `improvement_writebacks` rows with `requires_approval=True` and `impact_scope` derived from the pattern class (route → `route-default`, packet → `packet-default`, prompt → `prompt-default`, workflow → `workflow-default`, evaluation → `standards-default`). Thresholds are declarative in `config/learning/conservatism-policy.json` (sample size, recurrence count, confidence floor) so they are reviewable. **(d) Compounding visibility surface** — `services/learning_impact.py` projects `LearningImpactPerRun{run_id, signals_emitted[], assets_evidenced[], proposals_created[]}` and `LearningImpactRollup{workflow_key|prompt_id, rework_rate_30d, rework_rate_90d, sample_size, trend: "improving"|"flat"|"regressing"}`; UI exposes via extended `aios-ui/server/aios/learning.ts` + new `getLearningImpact` tRPC route on `aios-ui/server/routers/control-plane.ts` (or a sibling `aios-ui/server/routers/learning.ts`). The CLI gets `aios learning-analyze --since 30d`, `aios learning-impact --workflow X` (or `--prompt Y`), and the existing `aios workflow-learning-audit` is extended to surface recurring patterns and conservative proposals alongside per-run evidence. **Critical constraint:** Phase 9 NEVER auto-promotes proposals into routing/packet/workflow defaults — every change flows through Phase 5 approval policy via `writeback_approval_policy`, and `improvement_writebacks.requires_approval=1` is the hard gate. Phase 1/2 recommenders **read** approved writebacks (via lifecycle-state filters on assets, already covered by Phase 8) but do NOT consume pending pattern proposals at runtime.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Learning signal taxonomy (`LearningSignalKind` literal) | Python control plane (new `services/learning_taxonomy.py`) | SQLite (`workflow_learning_events.signal_kind` column extension) | The literal is shared by `learning_analysis`, `conservative_optimizer`, and `learning_impact`; one source of truth avoids drift. |
| Cross-run pattern detection | Python control plane (new `services/learning_analysis.py`) | SQLite (reads from `workflow_learning_events`, `agentize_evaluations`, `success_criteria_findings`, `workflow_execution_reports`, `prompts_used`, `standards_delta_items`, `briefing_packets`, `improvement_writebacks`) | All inputs already persisted; Phase 9 only adds bounded read queries + small in-memory aggregation. No new evidence tables required. |
| Conservative proposal synthesis | Python control plane (new `services/conservative_optimizer.py`) | Reuse Phase 5 `writeback_approval_policy` + `insert_writeback` | Proposals are writebacks; never a new approval engine. Policy thresholds live in declarative config (`config/learning/conservatism-policy.json`). |
| Routing-quality and packet-quality signal feedback | Python control plane (`services/task_routing.py` + `services/agentize.py` continue to consume **approved** lifecycle-state assets via Phase 8 surfaces) | — | Feedback is mediated by approved writebacks → asset lifecycle promotion; recommenders do NOT consult `workflow_learning_events` at runtime. |
| Compounding visibility (per-run + rollup) | Python control plane (new `services/learning_impact.py`) | UI (extend `aios-ui/server/aios/learning.ts`; extend `aios-ui/server/routers/control-plane.ts` or new `learning.ts` router) | UI projects what's already persisted; no new persistence. |
| Divergent / experiment outcomes feeding governed promotion | Python (`services/divergent_strategy.py` + `services/workflow_experiments.py`) consume Phase 8 `propose_workflow_promotion` / `propose_asset_promotion` | SQLite (`promotion_lifecycle_items` standardized to five-state literal by Phase 8) | Wiring is one-line per call site; the heavy lifting was Phase 8's. |
| Operator CLI parity | Python (`services/aios_cli.py`) | — | `aios learning-analyze`, `aios learning-impact`, `aios learning-propose`; existing `aios workflow-learning-audit` is extended. |
| Declarative conservatism thresholds | Config (`config/learning/conservatism-policy.json` — NEW) | Python (`services/conservative_optimizer.py` loader) | Reviewable in git; tunable without code changes. |

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LEARN-01 | AIOS captures run evidence that informs future prompt, skill, workflow, and packet improvements | `workflow_learning_events` already persists per-terminal-run evidence keyed by `(run_id, evidence_type, proposal_target)` with `confidence`, `rationale`, `source_json` [VERIFIED: services/aios_cli.py:2111-2193]. `agentize_evaluations.outcome_quality`/`tests_passed`/`follow_up_required`/`major_repair_required` per packet [VERIFIED: schema.sql:78-92]. `success_criteria_findings.level`/`evidence_json`/`resolution_status` per criterion [VERIFIED: schema.sql:566-583]. `prompts_used.classification`/`outcome_score`/`reusable_candidate`/`retrieval_fired`/`retrieval_source` per session [VERIFIED: schema.sql:44-52, 97-98, 183]. `workflow_execution_reports.report_json` per run carries stages and (post-Phase-8) `stage_evaluations[]`. `improvement_writebacks` carries proposals. **Phase 9 adds** the `signal_kind` axis to `workflow_learning_events` so signals are taxonomy-typed, and adds `services/learning_analysis.py` so the evidence is queryable cross-run. |
| LEARN-02 | AIOS identifies recurring failure modes, ignored rules, bloated packets, weak workflows from accumulated evidence | New `services/learning_analysis.py` with `detect_recurring_patterns()` dispatching to detectors: `detect_repeated_failures` (groups `success_criteria_findings` by `criterion_id` × `workflow_key` × 30-day window, recurrence ≥ N), `detect_ignored_rules` (joins `success_criteria_findings.resolution_status='open'` with `criterion.blocking=True` across multiple runs), `detect_bloated_packets` (compares `briefing_packets` size metrics — `selection_trace_json` length, `selected_context_packets` count, token estimates — against per-workflow median; flags > 2σ), `detect_weak_prompts` (groups `prompts_used.outcome_score` and `agentize_evaluations.outcome_quality` by prompt template id over a window; flags mean < threshold with sample_size ≥ N), `detect_weak_workflows` (groups `workflow_execution_reports.status='failed'` and per-stage `blocker_count` by workflow_key; flags failure rate > threshold), `detect_route_misroutes` (joins `orchestration_runs.route_result_json` with `success_criteria_findings.level='blocker'` to find routes that frequently lead to immediate rework). |
| LEARN-03 | AIOS proposes conservative improvements to routing, context selection, and evaluation based on reviewed outcomes | New `services/conservative_optimizer.py` consumes `RecurringPattern[]` from `learning_analysis.py` and emits `improvement_writebacks` rows via Phase 5 `insert_writeback` + `writeback_approval_policy`. Thresholds in `config/learning/conservatism-policy.json` (NEW): `min_sample_size`, `min_recurrence_count`, `min_confidence`, `cooling_period_days` (don't re-propose the same pattern within N days). ALL proposals get `requires_approval=1`; runtime recommenders consume **only** approved writebacks via Phase 8 asset lifecycle states. The optimizer DOES NOT mutate registries directly — it writes proposals, the operator approves them, and approval triggers asset lifecycle promotion (Phase 8 path). |
| LEARN-04 | AIOS makes compounding visible by showing what each meaningful run improved for future work | New `services/learning_impact.py` projects two views: (a) `LearningImpactPerRun{run_id, signals_emitted: tuple[LearningSignalKind, ...], assets_evidenced: tuple[{kind, key, evidence_delta}, ...], proposals_created: tuple[{writeback_id, signal_kind, requires_approval}, ...]}` — answers "what did THIS run improve?"; (b) `LearningImpactRollup{scope: workflow|prompt|skill, key, rework_rate_30d, rework_rate_90d, sample_size, trend: improving|flat|regressing, since: str}` — answers "is this asset getting better over time?". UI surfaces both; existing `aios-ui/server/aios/learning.ts` `proposeRunWritebacks` continues to emit per-run writebacks but is now joined by `getLearningImpact*` projections. |

## Project Constraints (from CLAUDE.md / AGENTS.md)

| Constraint | Source | Phase 9 Implication |
|------------|--------|---------------------|
| Run quality ladder: `ruff check . && ruff format --check . && basedpyright && vulture` | `~/.claude/CLAUDE.md` Python canonical commands | Every implementation task in this phase ends with these as a hard gate. |
| UI quality ladder: `pnpm lint && pnpm tsc --noEmit` (no `pnpm test` is wired in `aios-ui/package.json`) | `~/.claude/CLAUDE.md` + AGENTS.md | Any TypeScript edit in `aios-ui/server/aios/learning.ts` or `aios-ui/server/routers/{control-plane,learning}.ts` ends with these. |
| Atomic commits scoped to one project + one concern, followed by immediate `PROJECT.md` truth update commit | `~/.claude/CLAUDE.md` Git rules | Each task in this phase commits independently and updates `PROJECT.md` before the next task begins. |
| `main` stays deployable | `~/.claude/CLAUDE.md` Git | Phase 9 work goes through feature branches per repo discipline; `.planning/config.json` has `branching_strategy: none` so confirm in discuss-phase whether autonomous mode bypasses branching here. |
| No `--no-verify` or `--no-gpg-sign` bypasses | `~/.claude/CLAUDE.md` Git | Honor pre-commit hooks. |
| Never use `cat << EOF` or heredoc for file creation | Agent harness rule | Use Write tool for any new file. |
| Don't add comments/docstrings/type annotations to code I didn't change | `~/.claude/CLAUDE.md` Working style | Edits stay scoped; do not blanket-annotate touched modules. |
| Three similar lines is better than premature abstraction | `~/.claude/CLAUDE.md` Working style | Resist building a generic "pattern-detection framework"; extend the per-detector dispatch pattern that `services/success_criteria.py` evaluators and `services/standards_health.py` evaluators already use. |
| Local-first + files-authoritative | AGENTS.md (Constraints) | All learning data lives in SQLite + JSON config. No external ML services, no remote inference. |
| Governance must remain reviewable | AGENTS.md (Constraints) | EVERY pattern → proposal flow MUST emit `improvement_writebacks` rows via `writeback_approval_policy` with `requires_approval=True`. Phase 9 explicitly forbids silent mutation. |
| Explainability is required | AGENTS.md (Constraints) | Every `RecurringPattern` MUST carry `evidence_run_ids` and a human-readable `summary`; every conservative proposal MUST carry the pattern id and citation back to the evidence. |
| Brownfield continuity | AGENTS.md (Constraints) | Existing `workflow_learning_events` rows must keep loading after `signal_kind` is added (nullable column, additive migration). Existing `_workflow_learning_payload` payload shape must remain backward-compatible (add new keys; do not remove or rename). |
| Architecture boundary: `services/` cannot import `bin/` | `tests/test_architecture_enforcement.py` | New `services/learning_analysis.py`, `services/conservative_optimizer.py`, `services/learning_impact.py` cannot import from `bin/aios_orchestration_runtime`. They need `writeback_approval_policy` / `insert_writeback` / `insert_writeback_event` — Phase 8 already established the pattern (duplicate the policy function or re-export through a `services/` shim). Phase 9 reuses whatever Phase 8 chose. |
| Execution-first verification for stateful/cross-system changes | AGENTS.md "Rule: Execution-First Verification" | Pattern detection touches multiple persistence layers; tests must seed real fixture rows and assert against the dispatcher, not just mock. |

## Standard Stack

### Core (existing — extend, don't replace)

| Library / Surface | Version | Purpose | Why Standard |
|-------------------|---------|---------|--------------|
| `services/aios_cli.py` `_workflow_learning_payload` | in-tree (lines 2208-2377) | Per-terminal-run learning evidence classification + idempotent persistence to `workflow_learning_events` | Already the canonical learning-evidence writer; Phase 9 extends with `signal_kind` and adds recurring-pattern + impact projections, NOT replaces. |
| `bin/aios_orchestration_runtime.py` schema bootstrap (lines 189-209) | in-tree | Creates `workflow_learning_events` table at runtime | Phase 9 adds a `signal_kind` column via `_ensure_column` pattern (same idempotent additive style used everywhere). |
| `bin/hook-stop.py` closeout (lines 600-720) | in-tree | Emits `governed_closeout` workflow_execution_report including `workflow_learning_writeback_expected` flag | Phase 9 emits the new `signal_kind` rows at closeout via the existing `_record_workflow_learning_event` seam called from `_workflow_learning_payload`. |
| `services/divergent_strategy.py` | in-tree | Runs strategy comparison; writes `divergent_runs`/`divergent_candidates`/`divergent_judgments`/`memory_writeback_proposals`/`promotion_lifecycle_items` | Phase 9 wires divergent portfolio winners into Phase 8's `propose_workflow_promotion`/`propose_asset_promotion` instead of direct `transition_promotion_lifecycle` calls. |
| `services/workflow_experiments.py` | in-tree (779 lines) | `workflow_skill_experiments` + `github_skill_candidates` runners | Phase 9 reads experiment outcomes as one input to `detect_weak_prompts` / `detect_weak_workflows`; existing experiment scoring is reused. |
| `services/workflow_synthesis.py` | in-tree (917 lines) | `workflow_synthesis_proposals` with `pending_approval`/`approved`/`rejected` lifecycle | Existing precedent for "proposal-with-evidence-then-approval" — Phase 9 mirrors the lifecycle shape for `RecurringPattern` proposals (which go through `improvement_writebacks` rather than `workflow_synthesis_proposals`). |
| `services/success_criteria.py` | in-tree (986 lines) | `success_criteria_findings` writer; lifecycle states `open`/`accepted`/`resolved`/`waived`/`stale` | Phase 9's `detect_ignored_rules` reads `resolution_status='open'` across runs; `detect_repeated_failures` reads `level='blocker'`. |
| `services/standards_health.py` | in-tree (1599 lines) | `standards_delta_items.priority_score`/`priority_bucket`; `recommend_workflow_from_health` (Phase 7) | Phase 9's `detect_standards_regression` reads `standards_health_snapshots` deltas over time. |
| `services/agentize.py` | in-tree | `agentize_evaluations` writer with `outcome_quality`/`tests_passed`/`follow_up_required`/`major_repair_required`/`selected_skills_json`/`selected_standards_json` | Phase 9's `detect_weak_prompts` and `detect_bloated_packets` read these columns. |
| `services/task_routing.py` | in-tree | `RouteResult` with `task_family`, `workflow_key`, `prompt_family`, `recommended_surface`, rationale; persisted in `orchestration_runs.route_result_json` | Phase 9's `detect_route_misroutes` reads `route_result_json` joined with run outcome status. |
| `services/asset_lifecycle.py` / `services/asset_recommendation.py` / `services/workflow_promotion.py` | in-tree (Phase 8) | Cross-asset lifecycle, asset usage evidence, workflow comparison + promotion | Phase 9's conservative optimizer emits proposals that, once approved, flow through Phase 8 asset promotion. |
| `bin/aios_orchestration_runtime.py` `writeback_approval_policy` + `insert_writeback` + `insert_writeback_event` (Phase 5) | in-tree | Approval policy class derivation + writeback row insertion | Phase 9 reuses verbatim through whatever services-side shim Phase 8 established (assumption A4). |
| `aios-ui/server/aios/learning.ts` `proposeRunWritebacks` | in-tree (170 lines) | Per-run writeback synthesis (legacy backfill path) | Phase 9 keeps this writer (it serves the per-run "project writeback + workflow learning writeback" pair) and adds `getLearningImpact*` sibling functions. |
| `aios-ui/server/routers/control-plane.ts` | in-tree | Governance overview tRPC routes | Phase 9 extends with `getLearningImpactForRun`, `getLearningImpactRollup`, `listRecurringPatterns`, `listConservativeProposals`. Confirm in discuss-phase whether to add a separate `aios-ui/server/routers/learning.ts` or extend `control-plane.ts`. |
| `config/workflows/registry.json` (Phase 8 vNext) | post-Phase-8 | Includes `learning_signals: tuple[LearningSignalBinding, ...]` on every stage | Phase 9's analyzers can consult per-stage `learning_signals` to decide which evidence rows are stage-relevant. |

### Supporting (no new external deps required)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `sqlite3` (stdlib) | 3.x | All persistence + bounded read queries | Pattern detectors run windowed `SELECT ... WHERE created_at >= ?` queries; no new schema beyond `signal_kind` column addition. |
| `json` (stdlib) | — | Config + evidence parsing | Reuse `_load_json` / `_json` helpers from existing modules. |
| `dataclasses` (stdlib) | — | Frozen dataclasses for `RecurringPattern`, `LearningSignal`, `LearningImpactPerRun`, `LearningImpactRollup`, `ConservatismPolicy` | Follow `TrustedSignal` / `EvaluatedStandard` / `DeltaExplanation` shape from Phase 7. |
| `typing.Literal` | stdlib | `LearningSignalKind` literal | Single source — import from `services/learning_taxonomy.py`. |
| `statistics` (stdlib) | stdlib | Mean / median / stdev for packet bloat and rework-rate trend detection | Lightweight; no need for numpy / pandas. |
| `pytest` 8.x | — | Test framework | Follow `tests/test_aios_cli.py` and `tests/test_standards_health.py` in-memory sqlite + seed-runtime patterns. |
| `better-sqlite3` (UI) | per `aios-ui/package.json` | Direct DB access in `aios-ui/server/db.ts` | Reuse — Phase 9 adds prepared statements next to existing `listControlPlaneRuns` / `terminalRunGaps`. |
| `zod` | per `aios-ui/package.json` | Runtime validation in tRPC routers | New `getLearningImpact*` input/output schemas use `z.object(...)`. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `signal_kind` as nullable column on `workflow_learning_events` | New `learning_signals` table joined by `event_id` | Adding a column is one ALTER + one read filter; a sibling table is a JOIN per query and a new schema-ensure path. **Choose: nullable column** for new rows, populated by `_record_workflow_learning_event` extension. |
| One typed `LearningSignalKind` literal across all detectors and proposers | Per-detector enums | Per-detector enums drift; one shared literal stays consistent. **Choose: one literal in `services/learning_taxonomy.py`** (mirrors Phase 8 `AssetLifecycleState`). |
| Declarative thresholds in `config/learning/conservatism-policy.json` | Hardcoded thresholds in `services/conservative_optimizer.py` | Three similar threshold values is better than premature configuration (CLAUDE.md). However, conservatism THRESHOLDS need to be inspectable by operators without code changes (they affect what gets proposed). **Choose: small JSON config file** — fewer than 10 keys, but reviewable. |
| Recompute patterns on read (no cache) | `learning_pattern_snapshots` cache table | Recurring-pattern detection runs at most a few times per day (manual + via daily hook); no per-request hot path. **Choose: recompute on read.** Cache only if profiling shows it. |
| `services/conservative_optimizer.py` emits `improvement_writebacks` directly | New `learning_proposals` table that feeds `improvement_writebacks` indirectly | Two parallel proposal queues defeat the Phase 5 "one cross-asset writeback contract" goal. **Choose: emit directly to `improvement_writebacks`** with a `metadata_json.source: "learning_analysis"` tag for traceability. |
| Real-time recommender consumption of pattern proposals | Recommender consumes only approved (post-writeback) asset lifecycle state | Real-time consumption would silently bias routes/packets before review — directly violates the phase's "no silent policy drift" mandate. **Choose: approved-asset-lifecycle only.** This is the load-bearing safety property of the phase. |
| New approval engine for learning proposals | Reuse Phase 5 `writeback_approval_policy` | Phase 5 already covers all four impact scopes Phase 9 needs (`prompt-default`, `skill-default`, `workflow-default`, `standards-default`); add `route-default` and `packet-default` as new scopes within the existing policy function if needed (one-line addition each). **Choose: reuse + extend by one or two scopes.** Confirm in discuss-phase. |
| Building a new bandit / multi-armed-bandit policy for exploration | Keep exploration heuristics simple: when sample_size below threshold, recommend an alternative as "exploration" | Bandits are a 200-line addition with no current upstream use; existing Phase 8 recommender already includes a sample-size-based exploration rule. **Choose: keep simple.** Bandit logic can land in a follow-up phase if signal-to-noise warrants. |
| Aggregating pattern detection across all projects | Per-project default with cross-project fallback when per-project sample size < N | Per-project respects project boundaries (a misroute on project A is not always a misroute on project B). **Choose: per-project + cross-project fallback** for low-sample patterns; the proposal rationale cites which scope was used. |
| Adding new UI router `aios-ui/server/routers/learning.ts` | Extending `aios-ui/server/routers/control-plane.ts` | Control-plane router is already large; learning surfaces are conceptually distinct. **Recommend: NEW `aios-ui/server/routers/learning.ts`.** Confirm in discuss-phase. |

**Installation:** No new external dependencies. Phase 9 is entirely additive to existing in-tree modules.

**Version verification:** `workflow_learning_events` schema bootstrap is at the in-tree version inside `bin/aios_orchestration_runtime.py` lines 189-209 and `services/aios_cli.py` lines 2111-2132 (no explicit version field). Phase 9 adds the `signal_kind` column via `_ensure_column` idempotent migration; no version bump needed. `config/learning/conservatism-policy.json` is NEW and will start at `version: "2026-05-21"`.

## Architecture Patterns

### System Architecture Diagram

```
                ┌────────────────────────────────────────────────────────────────────┐
                │ Per-run evidence (already persisted by Phases 1–8)                 │
                │                                                                    │
                │  orchestration_runs.route_result_json                              │
                │  briefing_packets (selection_trace_json, selected_*_json)          │
                │  agentize_evaluations (outcome_quality, follow_up_required, ...)   │
                │  workflow_execution_reports.report_json + stage_evaluations[]      │
                │  success_criteria_findings + success_criteria_stage_findings       │
                │  standards_health_snapshots + standards_delta_items                │
                │  prompts_used (classification, outcome_score, reusable_candidate)  │
                │  improvement_writebacks + improvement_writeback_events             │
                │  workflow_skill_experiments (baseline/candidate scores)            │
                │  divergent_runs + divergent_judgments + memory_writeback_proposals │
                │  promotion_lifecycle_items (post-Phase 8 standardized statuses)    │
                └────────────────┬───────────────────────────────────────────────────┘
                                 │ bounded windowed reads
                                 ▼
   ┌───────────────────────────────────────────────────────┐
   │ services/learning_taxonomy.py                         │
   │   LearningSignalKind = Literal[...]                   │
   │   ConservatismPolicy dataclass                        │
   │   ImpactScopeForSignal()  (signal -> impact_scope)    │
   └───────────────┬───────────────────────────────────────┘
                   │ imported by all Phase 9 modules
                   ▼
   ┌───────────────────────────────────────────────────────┐
   │ services/learning_analysis.py                         │
   │   detect_recurring_patterns(conn, *, since, project)  │
   │     dispatches to:                                    │
   │       detect_repeated_failures()                      │
   │       detect_ignored_rules()                          │
   │       detect_bloated_packets()                        │
   │       detect_weak_prompts()                           │
   │       detect_weak_workflows()                         │
   │       detect_route_misroutes()                        │
   │       detect_standards_regression()                   │
   │     returns list[RecurringPattern]                    │
   └───────────────┬───────────────────────────────────────┘
                   │ patterns fed into
                   ▼
   ┌───────────────────────────────────────────────────────┐
   │ services/conservative_optimizer.py                    │
   │   load_conservatism_policy() ← reads JSON config      │
   │   propose_from_pattern(pattern, policy) → writeback   │
   │     - guard: sample_size >= min_sample_size           │
   │     - guard: recurrence_count >= min_recurrence_count │
   │     - guard: confidence >= min_confidence             │
   │     - guard: cooling_period_days not violated         │
   │   policy = writeback_approval_policy(                 │
   │     layer_type=..., impact_scope=...,                 │
   │     proposed_change=..., requires_approval=True)      │
   │   insert_writeback(...)                               │
   │   insert_writeback_event(... 'proposed' ...)          │
   └───────────────┬───────────────────────────────────────┘
                   │ writes
                   ▼
   ┌───────────────────────────────────────────────────────┐
   │ improvement_writebacks (Phase 5)                      │
   │   requires_approval=1 always for LEARN-03             │
   │   metadata_json.source = "learning_analysis"          │
   │   metadata_json.pattern_id = ...                      │
   │   metadata_json.evidence_run_ids = [...]              │
   └───────────────┬───────────────────────────────────────┘
                   │ approved writebacks trigger
                   ▼
   ┌───────────────────────────────────────────────────────┐
   │ Phase 8 asset lifecycle promotion                     │
   │   propose_workflow_promotion()                        │
   │   propose_asset_promotion()                           │
   │   route/packet config updates (gated by approval)     │
   └───────────────┬───────────────────────────────────────┘
                   │ Phase 1/2 recommenders consume
                   │ approved lifecycle states (NOT pending)
                   ▼
   ┌───────────────────────────────────────────────────────┐
   │ services/task_routing.py / services/agentize.py       │
   │   read approved assets only; never pending proposals  │
   └───────────────────────────────────────────────────────┘

                   ┌──────────────────────────┐
                   │ Per-run closeout         │
                   │ services/aios_cli.py     │
                   │   _record_workflow_      │
                   │   learning_event(...)    │
                   │   + extended with        │
                   │   signal_kind            │
                   └────────┬─────────────────┘
                            │ writes
                            ▼
                   ┌──────────────────────────┐
                   │ workflow_learning_events │
                   │ + signal_kind column     │
                   └──────────────────────────┘

   ┌──────────────────────────────────────────────────────────────────────┐
   │ services/learning_impact.py                                          │
   │   build_per_run_impact(conn, run_id) -> LearningImpactPerRun         │
   │   build_rollup(conn, *, scope, key, since) -> LearningImpactRollup   │
   └─────────────────┬────────────────────────────────────────────────────┘
                     │ exposed via
                     ▼
   ┌──────────────────────────────────────────────────────────────────────┐
   │ UI (aios-ui/server/aios/learning.ts extension)                       │
   │   proposeRunWritebacks(...)  (existing — kept)                       │
   │   getLearningImpactForRun(db, run_id)                                │
   │   getLearningImpactRollup(db, scope, key, since)                     │
   │   listRecurringPatterns(db, since)                                   │
   │   listConservativeProposals(db, status)                              │
   │ Router: aios-ui/server/routers/learning.ts (NEW — preferred)         │
   │   OR extend aios-ui/server/routers/control-plane.ts                  │
   └──────────────────────────────────────────────────────────────────────┘
                                 ▲
                                 │ CLI parity via
                                 │
   ┌─────────────────────────────┴────────────────────────────────────────┐
   │ services/aios_cli.py:                                                │
   │   aios workflow-learning-audit  (existing — extended with patterns)  │
   │   aios learning-analyze [--since 30d] [--project X] [--json]         │
   │   aios learning-impact --run-id X | --workflow X | --prompt X        │
   │   aios learning-propose [--dry-run]  (one-shot propose-from-patterns)│
   └──────────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure (additions)

```
services/
├── learning_taxonomy.py          # NEW: LearningSignalKind literal,
│                                 #      ConservatismPolicy dataclass,
│                                 #      impact_scope_for_signal() mapper.
│
├── learning_analysis.py          # NEW: detect_recurring_patterns()
│                                 #      with per-signal-kind detectors;
│                                 #      RecurringPattern dataclass.
│
├── conservative_optimizer.py     # NEW: load_conservatism_policy(),
│                                 #      propose_from_pattern(),
│                                 #      propose_from_all_patterns(); reuses
│                                 #      Phase 5 writeback_approval_policy.
│
├── learning_impact.py            # NEW: build_per_run_impact(),
│                                 #      build_rollup(),
│                                 #      LearningImpactPerRun / Rollup dataclasses.
│
├── divergent_strategy.py         # extend: wire portfolio winners into
│                                 #         Phase 8 propose_*_promotion()
│                                 #         instead of direct
│                                 #         transition_promotion_lifecycle.
│
├── workflow_experiments.py       # extend: emit RecurringPattern-shape rows
│                                 #         from experiment outcomes via
│                                 #         services/learning_analysis hook.
│
├── aios_cli.py                   # extend: signal_kind column ensure,
│                                 #         _record_workflow_learning_event
│                                 #         takes signal_kind kwarg,
│                                 #         _workflow_learning_payload surfaces
│                                 #         recurring patterns + proposals;
│                                 #         new CLI subcommands:
│                                 #         learning-analyze, learning-impact,
│                                 #         learning-propose.
│
└── task_routing.py + agentize.py # NO RUNTIME CHANGE in Phase 9 — they
                                  # continue to consume Phase 8 asset
                                  # lifecycle states; pending Phase 9
                                  # proposals do NOT affect runtime.

bin/
├── aios_orchestration_runtime.py # extend: workflow_learning_events
│                                 #         CREATE TABLE statement gains
│                                 #         signal_kind TEXT NULL.
│                                 #         _ensure_column path used for
│                                 #         existing-DB upgrade.
│
└── hook-stop.py                  # extend: when emitting workflow-learning
                                  #         event, populate signal_kind from
                                  #         the same heuristics that
                                  #         _workflow_learning_payload uses
                                  #         (workflow status, blocker_count,
                                  #         follow_up_required, etc.).

config/
└── learning/                     # NEW directory
    └── conservatism-policy.json  # NEW: declarative thresholds
                                  #      (min_sample_size, min_recurrence_count,
                                  #       min_confidence, cooling_period_days,
                                  #       per-signal-kind overrides).

aios-ui/
├── lib/
│   ├── types.ts                  # extend: LearningSignalKind, RecurringPattern,
│   │                             #         LearningImpactPerRun,
│   │                             #         LearningImpactRollup types.
│   └── trusted-signals.ts        # reuse for rationale projection.
├── server/
│   ├── aios/
│   │   └── learning.ts           # extend: getLearningImpactForRun,
│   │                             #         getLearningImpactRollup,
│   │                             #         listRecurringPatterns,
│   │                             #         listConservativeProposals.
│   └── routers/
│       └── learning.ts           # NEW (preferred) OR extend control-plane.ts:
│                                 #         tRPC procedures matching the four
│                                 #         server functions above + zod schemas.

tests/
├── test_learning_taxonomy.py     # NEW: literal completeness + impact_scope mapping
├── test_learning_analysis.py     # NEW: each detector with fixtures
├── test_conservative_optimizer.py # NEW: threshold gates + writeback emission +
│                                 #      cooling-period dedupe
├── test_learning_impact.py       # NEW: per-run + rollup projections
├── test_aios_cli.py              # extend: new CLI subcommands + extended
│                                 #         workflow-learning-audit shape
└── test_orchestration_runtime.py  # extend: signal_kind column migration
```

### Pattern 1: Learning Signal Taxonomy (LEARN-01 axis 2)

**What:** One typed literal shared across detectors, optimizer, and impact module. Distinct from `workflow_learning_events.evidence_type` (which is run-shape: workflow_evidence | prompt_template_evidence | standards_health_evidence | bug_quality_evidence | no_learning_signal). `signal_kind` is signal-content: repeated_failure, ignored_rule, bloated_packet, weak_prompt, weak_workflow, route_misroute, standards_regression, writeback_adopted, writeback_rejected, compounding_gain.

**When to use:** Anytime a learning event is recorded or a pattern is detected.

**Example:**
```python
# Source: NEW services/learning_taxonomy.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

LearningSignalKind = Literal[
    "repeated_failure",
    "ignored_rule",
    "bloated_packet",
    "weak_prompt",
    "weak_workflow",
    "route_misroute",
    "standards_regression",
    "writeback_adopted",
    "writeback_rejected",
    "compounding_gain",
]

# Map signal kind to Phase 5 impact_scope so writeback approval policy applies
SIGNAL_TO_IMPACT_SCOPE: dict[LearningSignalKind, str] = {
    "repeated_failure":     "workflow-default",
    "ignored_rule":         "standards-default",
    "bloated_packet":       "packet-default",      # NEW scope — confirm in discuss-phase
    "weak_prompt":          "prompt-default",
    "weak_workflow":        "workflow-default",
    "route_misroute":       "route-default",       # NEW scope — confirm in discuss-phase
    "standards_regression": "standards-default",
    "writeback_adopted":    "scoped",              # informational
    "writeback_rejected":   "scoped",              # informational
    "compounding_gain":     "scoped",              # informational
}


@dataclass(frozen=True)
class ConservatismPolicy:
    min_sample_size: int
    min_recurrence_count: int
    min_confidence: float
    cooling_period_days: int
    per_signal_overrides: dict[LearningSignalKind, dict[str, float | int]]
```

### Pattern 2: Cross-Run Recurring-Pattern Detection (LEARN-02)

**What:** A dispatch table of detectors that each runs bounded windowed reads against existing evidence tables and emits `RecurringPattern` records. No new schema; no real-time path.

**When to use:** On operator request (`aios learning-analyze`) or via a daily / weekly cron-like hook (out of scope for Phase 9 itself; can be wired by Phase 10).

**Example:**
```python
# Source: NEW services/learning_analysis.py
from __future__ import annotations
import sqlite3
from dataclasses import dataclass, field
from typing import Any, Callable
from services.learning_taxonomy import LearningSignalKind


@dataclass(frozen=True)
class RecurringPattern:
    pattern_id: str                              # stable hash of (signal_kind, scope_key, window)
    signal_kind: LearningSignalKind
    scope_kind: str                              # "workflow" | "prompt" | "skill" | "route" | "packet" | "standard"
    scope_key: str                               # e.g. workflow_key or prompt_id
    project_id: str | None
    sample_size: int
    recurrence_count: int
    confidence: float                            # 0..1; recurrence_count / sample_size for frequency-based detectors
    since: str                                   # ISO timestamp lower bound
    summary: str
    evidence_run_ids: tuple[str, ...]
    suggested_remediation_class: str             # e.g. "deprecate_prompt" | "tighten_route_hint" | "trim_packet_section"
    metadata: dict[str, Any] = field(default_factory=dict)


# Detectors are independent functions; one dispatch dict keeps them grep-able.
DETECTORS: dict[LearningSignalKind, Callable[..., list[RecurringPattern]]] = {
    "repeated_failure":     "_detect_repeated_failures",   # bound at module load
    "ignored_rule":         "_detect_ignored_rules",
    "bloated_packet":       "_detect_bloated_packets",
    "weak_prompt":          "_detect_weak_prompts",
    "weak_workflow":        "_detect_weak_workflows",
    "route_misroute":       "_detect_route_misroutes",
    "standards_regression": "_detect_standards_regression",
}


def detect_recurring_patterns(
    conn: sqlite3.Connection,
    *,
    since: str | None = None,
    project_id: str | None = None,
    signal_kinds: tuple[LearningSignalKind, ...] | None = None,
) -> list[RecurringPattern]:
    kinds = signal_kinds or tuple(DETECTORS.keys())
    patterns: list[RecurringPattern] = []
    for kind in kinds:
        detector = DETECTORS[kind]
        patterns.extend(detector(conn, since=since, project_id=project_id))
    return patterns


def _detect_repeated_failures(
    conn: sqlite3.Connection,
    *,
    since: str | None,
    project_id: str | None,
) -> list[RecurringPattern]:
    # GROUP BY criterion_id, workflow_key WHERE level='blocker' AND created_at >= since
    # HAVING COUNT(*) >= min_recurrence_count
    # Returns one RecurringPattern per (criterion_id, workflow_key) above threshold.
    ...
```

### Pattern 3: Conservative Proposal Synthesis (LEARN-03)

**What:** Convert `RecurringPattern` to an `improvement_writebacks` row with `requires_approval=True`, gated by declarative thresholds and a per-pattern cooling period. NEVER mutate registries directly; NEVER auto-approve.

**When to use:** After `detect_recurring_patterns()` returns; once on operator request, optionally as a cron hook.

**Example:**
```python
# Source: NEW services/conservative_optimizer.py
from __future__ import annotations
import json
import sqlite3
from dataclasses import dataclass
from typing import Any
from services.learning_taxonomy import (
    ConservatismPolicy,
    LearningSignalKind,
    SIGNAL_TO_IMPACT_SCOPE,
)
from services.learning_analysis import RecurringPattern
# NOTE: writeback_approval_policy lives in bin/aios_orchestration_runtime.py.
# Phase 8 established the services-side shim approach. Reuse whatever Phase 8 chose.
from services.asset_lifecycle import writeback_approval_policy_shim as writeback_approval_policy


def load_conservatism_policy() -> ConservatismPolicy:
    # Reads config/learning/conservatism-policy.json
    ...


def propose_from_pattern(
    conn: sqlite3.Connection,
    pattern: RecurringPattern,
    policy: ConservatismPolicy,
    *,
    actor: str = "learning_analysis",
) -> dict[str, Any] | None:
    overrides = policy.per_signal_overrides.get(pattern.signal_kind, {})
    min_sample = int(overrides.get("min_sample_size", policy.min_sample_size))
    min_recur = int(overrides.get("min_recurrence_count", policy.min_recurrence_count))
    min_conf = float(overrides.get("min_confidence", policy.min_confidence))

    if pattern.sample_size < min_sample:
        return None
    if pattern.recurrence_count < min_recur:
        return None
    if pattern.confidence < min_conf:
        return None

    # Cooling-period dedupe: skip if a writeback for this pattern_id exists
    # within the last cooling_period_days.
    if _writeback_within_cooling_period(conn, pattern.pattern_id, policy.cooling_period_days):
        return None

    impact_scope = SIGNAL_TO_IMPACT_SCOPE[pattern.signal_kind]
    layer_type = _layer_type_for_signal(pattern.signal_kind)
    proposed_change = {
        "signal_kind": pattern.signal_kind,
        "scope_kind": pattern.scope_kind,
        "scope_key": pattern.scope_key,
        "suggested_remediation_class": pattern.suggested_remediation_class,
    }
    approval = writeback_approval_policy(
        layer_type=layer_type,
        impact_scope=impact_scope,
        proposed_change=proposed_change,
    )
    # CRITICAL: requires_approval is ALWAYS True for LEARN-03 proposals.
    requires_approval = True

    writeback_id = _insert_writeback(
        conn,
        run_id=None,
        project_id=pattern.project_id,
        layer_type=layer_type,
        layer_key=pattern.scope_key,
        title=f"Conservative improvement: {pattern.signal_kind} on {pattern.scope_kind} {pattern.scope_key}",
        summary=pattern.summary,
        evidence=list(pattern.evidence_run_ids),
        proposed_change={
            **proposed_change,
            "rationale": pattern.summary,
            "policy_class": approval.get("policy_class"),
            "pattern_id": pattern.pattern_id,
        },
        impact_scope=impact_scope,
        status="pending_approval",
        requires_approval=requires_approval,
        approval_reason=approval.get("reason"),
        metadata={
            "source": "learning_analysis",
            "pattern_id": pattern.pattern_id,
            "evidence_run_ids": list(pattern.evidence_run_ids),
            "sample_size": pattern.sample_size,
            "recurrence_count": pattern.recurrence_count,
            "confidence": pattern.confidence,
        },
        actor=actor,
    )
    _insert_writeback_event(conn, writeback_id=writeback_id, event_type="proposed", actor=actor)
    return {"writeback_id": writeback_id, "pattern_id": pattern.pattern_id, "requires_approval": requires_approval}
```

### Pattern 4: Compounding Visibility (LEARN-04)

**What:** Two projections answer "what did this run improve?" (per-run) and "is this asset getting better?" (rollup). Both read-only.

**When to use:** Per-run view on every terminal run inspection; rollup view on operator request or periodic dashboard refresh.

**Example:**
```python
# Source: NEW services/learning_impact.py
from __future__ import annotations
import sqlite3
from dataclasses import dataclass
from typing import Literal
from services.learning_taxonomy import LearningSignalKind


@dataclass(frozen=True)
class AssetEvidenceDelta:
    asset_kind: Literal["prompt", "skill", "workflow", "standard", "route"]
    asset_key: str
    delta_sample_size: int
    delta_success_count: int
    delta_blocker_count: int


@dataclass(frozen=True)
class ProposalCreated:
    writeback_id: str
    signal_kind: LearningSignalKind
    requires_approval: bool
    status: str


@dataclass(frozen=True)
class LearningImpactPerRun:
    run_id: str
    workflow_key: str | None
    signals_emitted: tuple[LearningSignalKind, ...]
    assets_evidenced: tuple[AssetEvidenceDelta, ...]
    proposals_created: tuple[ProposalCreated, ...]
    learning_events_persisted: int
    no_learning_reason: str | None


@dataclass(frozen=True)
class LearningImpactRollup:
    scope: Literal["workflow", "prompt", "skill"]
    key: str
    since: str
    sample_size: int
    rework_rate_30d: float | None
    rework_rate_90d: float | None
    success_rate_30d: float | None
    blocker_rate_30d: float | None
    trend: Literal["improving", "flat", "regressing", "insufficient_data"]
    rationale: str
```

### Pattern 5: Idempotent Schema Migration for `signal_kind`

**What:** Add a nullable `signal_kind` column to `workflow_learning_events` using the existing `_ensure_column` idempotent pattern. Old rows stay valid with NULL; new writes populate it.

**When to use:** First task in the phase, before any detector runs.

**Example:**
```python
# Source: extends bin/aios_orchestration_runtime.py + services/aios_cli.py
def _ensure_workflow_learning_signal_kind_column(conn: sqlite3.Connection) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(workflow_learning_events)").fetchall()}
    if "signal_kind" not in cols:
        conn.execute("ALTER TABLE workflow_learning_events ADD COLUMN signal_kind TEXT")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_workflow_learning_events_signal "
            "ON workflow_learning_events(signal_kind, created_at DESC)"
        )

# _record_workflow_learning_event() gains an optional signal_kind kwarg;
# existing call sites in _workflow_learning_payload pass None until they
# learn how to classify; new detector emissions pass the literal.
```

### Pattern 6: Wiring Divergent / Experiment Winners Into Governed Promotion

**What:** Phase 8 introduced `propose_workflow_promotion` and `propose_asset_promotion`. Phase 9 replaces direct `transition_promotion_lifecycle` calls in `divergent_strategy.py` and `workflow_experiments.py` with the propose-then-approve path, so portfolio / experiment winners flow through `improvement_writebacks` like everything else.

**When to use:** Inside `divergent_strategy.py` after portfolio selection; inside `workflow_experiments.py` after experiment scoring.

**Example:**
```python
# Source: extends services/divergent_strategy.py
# BEFORE (current):
transition_promotion_lifecycle(conn, item_id=..., to_status="promoted", ...)

# AFTER (Phase 9):
from services.workflow_promotion import propose_asset_promotion
promotion = propose_asset_promotion(
    conn,
    asset_kind="skill",            # or "prompt" / "workflow"
    asset_key=winning_candidate_key,
    to_state="candidate",          # divergent winners enter as candidate, not active
    evidence={
        "source": "divergent_strategy",
        "run_id": divergent_run_id,
        "judge_scores": judge_scores,
    },
    actor="divergent_strategy",
)
# promotion -> { writeback_id, lifecycle_id, requires_approval }
```

### Anti-Patterns to Avoid

- **Real-time recommender consumption of pending pattern proposals:** This would silently bias routes/packets before review. Phase 9 forbids it. The runtime path is: pattern → writeback → approval → asset lifecycle promotion (Phase 8) → recommender reads approved asset. No shortcuts.
- **Inventing a multi-armed-bandit policy in Phase 9:** Bandits are interesting but unverified for this codebase. Phase 8 already includes a sample-size-based exploration rule in `recommend_assets_for_packet`. Phase 9 keeps it simple; if signal-to-noise demands more, a follow-up phase can replace the heuristic.
- **Aggregating evidence across project boundaries by default:** A misroute on project A may not be a misroute on project B. Default to per-project detection; fall back to cross-project only when per-project sample_size < threshold, and tag the rationale accordingly.
- **Cross-asset rank collapse:** A `success_rate` of 0.9 for a prompt with 5 samples is weaker evidence than 0.85 for a prompt with 200 samples. Every `RecurringPattern` and every conservative proposal MUST surface `sample_size` in its rationale, not just rate metrics.
- **Re-proposing the same pattern every run:** Without cooling-period dedupe, an unresolved blocker pattern would generate a fresh writeback every day. The `cooling_period_days` policy field prevents this; the optimizer checks `improvement_writebacks` for an open proposal with the same `metadata.pattern_id` before emitting.
- **Treating divergent / experiment winners as automatic promotions:** Divergent's existing `transition_promotion_lifecycle` direct call predates Phase 5 governance and Phase 8 lifecycle discipline. Phase 9 routes these through `propose_asset_promotion` so portfolio winners get reviewable proposals like everything else.
- **Adding new evidence tables for things we already capture:** `workflow_learning_events`, `agentize_evaluations`, `success_criteria_findings`, `workflow_execution_reports`, `prompts_used`, `improvement_writebacks`, `standards_delta_items`, `briefing_packets`, and `workflow_skill_experiments` collectively cover every signal Phase 9 needs. A `learning_signals` or `pattern_evidence` table would duplicate data already in those tables.
- **Letting `evidence_type` and `signal_kind` collapse into one axis:** Run-shape (workflow vs prompt vs standards vs bug) and signal-content (repeated_failure vs ignored_rule vs bloated_packet vs weak_prompt) are orthogonal. Two columns make the surface richer; combining them loses information.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Approval policy for routing / packet / workflow / standards changes | New approval engine | `writeback_approval_policy(layer_type, impact_scope, ...)` (Phase 5, lines 816-851 of `bin/aios_orchestration_runtime.py`) | Already covers prompt/skill/workflow/standards default scopes; add `route-default` + `packet-default` as new scopes if needed (one-line each). |
| Cross-asset writeback persistence | New table | `improvement_writebacks` + `improvement_writeback_events` (Phase 5, schema.sql:376-410) | Already has all columns: run_id, project_id, layer_type, layer_key, title, summary, evidence_json, proposed_change_json, impact_scope, status, requires_approval, decision_*. |
| Pattern → writeback synthesis | New proposal table | Insert directly into `improvement_writebacks` with `metadata_json.source="learning_analysis"` | One queue keeps governance audits trustworthy; two queues create a hidden parallel path. |
| Per-run learning event persistence | New writer | `_record_workflow_learning_event` (services/aios_cli.py:2156-2193) — extend with `signal_kind` kwarg | Already idempotent on `(run_id, evidence_type, proposal_target)`; extend by adding `signal_kind` to the dedupe key. |
| Per-run learning evidence classification | New classifier | `_inferred_learning_evidence` (services/aios_cli.py:2056-2108) + `_no_learning_reason` (lines 2196-2205) | Already maps run-state to evidence_type; Phase 9 extends to also infer signal_kind heuristically. |
| Workflow effectiveness comparison | New metric calculator | `services/workflow_promotion.compare_workflow_effectiveness()` (Phase 8) | Already returns rework_rate, validation_pass_rate, mean_blocker_count, writeback_usefulness per workflow_key. Phase 9 reads it as one input to `LearningImpactRollup`. |
| Asset usage evidence aggregation | New evidence joiner | `services/asset_recommendation.build_asset_usage_evidence()` (Phase 8) | Already joins `prompts_used` + `agentize_evaluations` + `workflow_execution_reports` + `workflow_skill_experiments`. Phase 9 uses for `LearningImpactRollup`. |
| Standards delta priority math | New scorer | `services/standards_health._build_delta_items()` (Phase 7) | Already encodes severity × leverage × dependency_unlock × regression_penalty / effort with bucket assignment. Phase 9's `detect_standards_regression` reads `priority_bucket="regressed"` directly. |
| Provenance / four-state signal classification | New enum | `Provenance = Literal["confirmed","inferred","missing","contradictory"]` from `services/capability_truth.py` | Phase 7 already enforces; Phase 9 reuses for `RecurringPattern.confidence` tagging when projecting through TrustedSignal-style payloads. |
| Workflow stage iteration | New executor | `execute_workflow` in `services/workflow_orchestration.py` | Phase 9 doesn't touch executor; it reads `workflow_execution_reports.report_json.stage_evaluations[]` produced by Phase 8 extension. |
| Trust-signal UI contract | New types | `aios-ui/lib/trusted-signals.ts` (existing) | RecurringPattern rationale can re-use `TrustedSignal<T>` shape. |

**Key insight:** Phase 9 is overwhelmingly an **analysis layer over already-persisted evidence**, not a new subsystem. The novel work is: (1) the `signal_kind` axis on `workflow_learning_events`, (2) the seven detectors, (3) the conservative optimizer, and (4) the impact projections. Everything else extends primitives that Phases 1–8 shipped.

## Runtime State Inventory

*Phase 9 is an analysis + projection phase. It adds one nullable column (`workflow_learning_events.signal_kind`), one new config file (`config/learning/conservatism-policy.json`), and four new `services/learning_*.py` modules. No renames, no migrations of existing semantic values, no external services. The Runtime State Inventory categories apply only narrowly:*

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `workflow_learning_events` rows exist with `evidence_type` populated but no `signal_kind` column. After Phase 9 task 01, the column exists as TEXT NULL. Existing rows stay NULL forever (back-compat); detectors only act on rows written post-migration. | **Schema migration only (additive nullable column):** `ALTER TABLE workflow_learning_events ADD COLUMN signal_kind TEXT`. No data backfill required — pattern detection reads from source evidence tables (`success_criteria_findings`, `agentize_evaluations`, etc.), not from historical `workflow_learning_events.signal_kind` values. |
| Stored data | `promotion_lifecycle_items.status` is freeform today and will be standardized to the five-state literal by Phase 8 (assumption A3 in Phase 8 RESEARCH). Phase 9 depends on Phase 8 migration completing. | None directly — Phase 8 owns the migration. Phase 9 reads only post-standardization values. **Risk:** if Phase 8 migration is incomplete or partially applied when Phase 9 runs, divergent-strategy winners may have legacy status values. Mitigation: `services/divergent_strategy.py` wiring (Pattern 6) should defensively coerce to the literal when reading. |
| Live service config | None — all phase 9 config (`config/learning/conservatism-policy.json`) is checked into git. No external CI/CD or UI configures these out-of-band. | None — verified by Phase 8 research that registries are git-tracked. |
| OS-registered state | None — no OS-level service registers learning-event identifiers or pattern keys. | None. |
| Secrets / env vars | None — learning analysis runs on local SQLite + local JSON config. No secrets. | None. |
| Build artifacts / installed packages | None — pure-Python module additions; no compiled artifacts. | None. |

**Nothing else found in scan.** The runtime concern is the `signal_kind` column migration (additive, low risk) and the dependency on Phase 8's `promotion_lifecycle_items` standardization.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12+ | All Phase 9 work | ✓ | 3.12 (per `pyproject.toml`) | — |
| sqlite3 stdlib | Persistence (column migration + bounded queries) | ✓ | stdlib | — |
| ruff | Lint gate | Assumed (per quality ladder) | per `pyproject.toml` | Quality ladder fails fast if missing |
| basedpyright | Typecheck gate | Assumed | per `pyproject.toml` | — |
| pytest 8.x | Test gate | ✓ (used in Phases 5/6/7/8) | — | — |
| vulture | Dead-code report | Assumed | per `pyproject.toml` | Report-only, non-blocking |
| `uv` runner | Existing phase verification commands use it | Likely ✓ (per `uv.lock`) | — | Fall back to `python -m pytest` |
| pnpm | UI quality ladder | Assumed (per `aios-ui/`) | — | — |
| better-sqlite3 | UI server DB access | ✓ (per `aios-ui/package.json`) | — | — |
| tRPC v11 | UI router boundary | ✓ | — | — |
| zod | UI runtime validation | ✓ | — | — |
| Phase 8 deliverables (`services/workflow_promotion.py`, `services/asset_lifecycle.py`, `services/asset_recommendation.py`) | divergent-wiring + experiment-wiring + workflow_promotion read paths | Pending Phase 8 completion | Phase 8 is the current active phase per ROADMAP.md / STATE.md | If Phase 8 is incomplete when Phase 9 starts, defer Patterns 6 (wiring divergent + experiments) to a Phase-9 follow-up task; the core learning analysis + optimizer + impact modules can land without it. |

**Missing dependencies with no fallback:** None identified.

**Missing dependencies with fallback:** Phase 8 completion is a hard prerequisite for Pattern 6 (wiring divergent + experiments into Phase 8 promotion). If Phase 8 partially completes, Pattern 6 is descoped and Phase 9 still delivers LEARN-01..04 via the analysis + optimizer + impact modules.

## Common Pitfalls

### Pitfall 1: Pattern Detection Threshold Tuning Drift

**What goes wrong:** Conservatism thresholds (`min_sample_size`, `min_recurrence_count`, `min_confidence`) live in `config/learning/conservatism-policy.json`. If thresholds are tuned too loose, the optimizer floods the operator with proposals; too tight, and obvious recurring failures never surface.

**Why it happens:** The "correct" threshold depends on traffic volume and signal noise, which vary per project and over time.

**How to avoid:** Start conservative (`min_sample_size: 5`, `min_recurrence_count: 3`, `min_confidence: 0.6`); ship a `aios learning-analyze --dry-run` mode that lists patterns that WOULD be proposed at current thresholds without writing writebacks; require operator review of dry-run output before flipping to live propose mode.

**Warning signs:** `improvement_writebacks` accumulates > 20 pending-approval rows from `metadata.source="learning_analysis"` within a single week; operators stop reading them.

### Pitfall 2: `signal_kind` Migration On Existing Rows

**What goes wrong:** Existing `workflow_learning_events` rows have NULL `signal_kind` after the column is added. If the detector code or UI filters require non-NULL values, historical rows disappear from views, looking like data loss.

**Why it happens:** Forgetting that the column is additive-with-defaults; old rows are not retroactively classified.

**How to avoid:** Detector queries always filter on **source evidence tables** (`success_criteria_findings`, `agentize_evaluations`, etc.), not on `workflow_learning_events.signal_kind`. The `signal_kind` column is for **new** events going forward; UI views show "NULL" as "unclassified (legacy)" with a clear label. Tests explicitly assert that pre-migration rows remain visible in `_workflow_learning_payload` output.

**Warning signs:** `aios workflow-learning-audit` shows `persisted_event_count` dropping after the migration.

### Pitfall 3: Conservative Optimizer Loops On Its Own Proposals

**What goes wrong:** Optimizer emits a writeback for `signal_kind=weak_prompt`. Operator rejects it. The next run, the same pattern is still present, the optimizer emits the same writeback again.

**Why it happens:** Cooling period not implemented or applied only to approved proposals.

**How to avoid:** `cooling_period_days` applies to ANY writeback with the same `metadata.pattern_id`, regardless of decision (`approved`/`rejected`/`pending`). Once a pattern is decided (either direction), the optimizer waits N days before re-proposing. If a `rejected` decision should permanently silence the pattern, add a `permanently_silenced` flag to `improvement_writebacks` metadata (out of scope; document for Phase 10).

**Warning signs:** The same `pattern_id` appears in multiple rejected `improvement_writebacks` rows within a 30-day window.

### Pitfall 4: Pattern Proposals Bypass `requires_approval=True`

**What goes wrong:** A developer adds a "fast path" to the optimizer for low-impact signal kinds (e.g., `compounding_gain`) that skips the approval gate.

**Why it happens:** Convenience — some signal kinds (`writeback_adopted`, `compounding_gain`) are informational, not policy changes.

**How to avoid:** Distinguish "informational signals" (which DO NOT emit `improvement_writebacks` at all; they go to `LearningImpactRollup` directly) from "proposal signals" (which DO emit writebacks and MUST set `requires_approval=True`). Add an `is_actionable` field on the literal mapping; the optimizer's main loop checks it and skips informational signals.

**Warning signs:** `improvement_writebacks` rows from `metadata.source="learning_analysis"` exist with `requires_approval=0`.

### Pitfall 5: Detector Performance On Large Run Histories

**What goes wrong:** `detect_bloated_packets` joins `briefing_packets` × `workflow_execution_reports` × `success_criteria_findings` across all runs in a 90-day window. On a long-running deployment, this is a 5-second query.

**Why it happens:** No bound on window size; no use of existing indices.

**How to avoid:** All detectors take a hard `since: str` parameter (default to 30 days); detectors use indexed columns (`created_at DESC`, `workflow_key`, `project_id`); aggregations happen in SQL `GROUP BY` rather than Python loops where possible. Add `EXPLAIN QUERY PLAN` checks to the test suite for each detector.

**Warning signs:** `aios learning-analyze --since 90d` takes > 5 seconds on the AIOS dev DB.

### Pitfall 6: `divergent_strategy.py` Wiring Breaks Existing Behavior

**What goes wrong:** Phase 9 task replaces the direct `transition_promotion_lifecycle` call with `propose_asset_promotion`. The divergent flow now requires approval before promotion; existing tests that asserted "divergent winner ends in 'promoted' state" fail.

**Why it happens:** Behavior change — the new path is governance-correct but breaks tests written against the old behavior.

**How to avoid:** Phase 9 task that wires divergent into Phase 8 promotion also updates `tests/test_divergent_strategy.py` to assert the new contract: divergent winner emits `improvement_writebacks` row with `requires_approval=True` and the `promotion_lifecycle_items` row stays at `candidate` until approval. Document in PROJECT.md that this is a tightening of governance discipline, not a regression.

**Warning signs:** `tests/test_divergent_strategy.py` fails with assertion on `promotion_lifecycle_items.status` post-Phase-9 task.

### Pitfall 7: New Impact Scopes (`route-default`, `packet-default`) Missing From Phase 5 Policy

**What goes wrong:** `writeback_approval_policy(layer_type="route", impact_scope="route-default", ...)` returns `requires_approval=False` because Phase 5 didn't include `route-default` in its scope map.

**Why it happens:** Phase 5 covered `prompt-default`, `skill-default`, `workflow-default`, `standards-default`, `global` — not `route-default` or `packet-default`.

**How to avoid:** First task in Phase 9 extends `writeback_approval_policy` (or the Phase 8 services-side shim) to recognize `route-default` and `packet-default` impact scopes with `requires_approval=True` policy classes. Add test: `test_route_default_requires_approval`.

**Warning signs:** A `route_misroute` pattern proposal lands in `improvement_writebacks` with `requires_approval=0`.

### Pitfall 8: UI Surface Confuses Pending Proposals With Active Policy

**What goes wrong:** Operator opens the learning UI; sees "Recommended: deprecate prompt X"; assumes it's already applied. Production runs continue to route to prompt X because the proposal is pending approval and the lifecycle state hasn't flipped.

**Why it happens:** UI doesn't surface the gap between proposal status and actual lifecycle state.

**How to avoid:** Every UI row for a learning proposal MUST display both `proposal_status: pending_approval | approved | rejected` AND `current_lifecycle_state: active | candidate | deprecated`. The UI labels proposals as "Proposed (not yet active)" until the lifecycle state matches the proposal's target.

**Warning signs:** Operator reports confusion: "I approved this — why is it still happening?"

### Pitfall 9: `learning_impact` Rollup Says "Improving" When Sample Size Is Tiny

**What goes wrong:** A workflow with 3 runs in the last 30 days, all successful, gets `trend: "improving"` because rework_rate went from 50% (prior window) to 0% (current window).

**Why it happens:** Naive trend calculation without sample-size weighting.

**How to avoid:** `LearningImpactRollup.trend` returns `"insufficient_data"` when sample_size < `min_sample_size_for_trend` (e.g., 10). Rationale text always includes sample_size: `"Improving (rework_rate dropped 50% → 0% over 12 runs)"` not just "Improving".

**Warning signs:** Operator-visible "improving" labels on workflows that have barely been used.

## Code Examples

Verified patterns from existing code:

### Existing Workflow Learning Event Writer (Phase 9 Extends With `signal_kind`)

```python
# Source: services/aios_cli.py:_record_workflow_learning_event (verbatim, lines 2156-2193)
def _record_workflow_learning_event(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    evidence_type: str,
    proposal_target: str | None,
    confidence: float,
    approval_state: str,
    rationale: str,
    source: dict[str, Any],
    # PHASE 9 ADDS:
    # signal_kind: LearningSignalKind | None = None,
) -> None:
    if _workflow_learning_event_exists(
        conn,
        run_id=run_id,
        evidence_type=evidence_type,
        proposal_target=proposal_target,
    ):
        return
    conn.execute(
        """
        INSERT INTO workflow_learning_events (
          id, run_id, evidence_type, proposal_target, confidence,
          approval_state, rationale, source_json, created_at
          -- PHASE 9 ADDS: , signal_kind
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        -- PHASE 9: extra ? for signal_kind
        """,
        (
            f"learning-{uuid.uuid4()}",
            run_id,
            evidence_type,
            proposal_target,
            confidence,
            approval_state,
            rationale,
            json.dumps(source, sort_keys=True),
            _now_iso(),
        ),
    )
```

### Existing Workflow Learning Audit Payload Shape (Phase 9 Extends)

```python
# Source: services/aios_cli.py:_workflow_learning_payload return shape (verbatim, lines 2354-2377)
return {
    "summary": {
        "terminal_run_count": ...,
        "runs_with_learning": ...,
        "no_learning_count": ...,
        "inferred_evidence_count": ...,
        "persisted_event_count": ...,
        "proposal_count": ...,
        "pending_approval_count": ...,
        # PHASE 9 ADDS:
        # "recurring_pattern_count": ...,
        # "conservative_proposal_count": ...,
    },
    "contract": {
        "evidence_types": WORKFLOW_LEARNING_EVIDENCE_TYPES,
        "run_source": "orchestration_runs",
        "event_source": "workflow_learning_events",
        "proposal_source": "improvement_writebacks",
        "promotion_gate": "status + requires_approval on improvement_writebacks",
        # PHASE 9 ADDS:
        # "signal_kinds": LEARNING_SIGNAL_KINDS,
        # "pattern_source": "services/learning_analysis.detect_recurring_patterns()",
        # "conservatism_policy_source": "config/learning/conservatism-policy.json",
    },
    "classification_counts": classification_counts,
    "persisted_events": persisted_event_rows[:50],
    "inferred_evidence": inferred_evidence[:50],
    "no_learning_runs": no_learning_runs[:20],
    "proposals": proposals[:50],
    # PHASE 9 ADDS:
    # "recurring_patterns": recurring_patterns[:50],
    # "conservative_proposals": conservative_proposals[:50],
}
```

### Approval Policy Class Reuse (Phase 5 — Used For Every Phase 9 Proposal)

```python
# Source: bin/aios_orchestration_runtime.py:writeback_approval_policy (verbatim)
policy = writeback_approval_policy(
    layer_type="workflow",
    impact_scope="workflow-default",
    proposed_change={"signal_kind": "weak_workflow", "workflow_key": "implementation-delivery"},
)
# policy = {
#   "policy_class": "workflow-default_change",
#   "requires_approval": True,
#   "reason": "workflow-default changes require approval before promotion."
# }
# Phase 9 ALWAYS sets requires_approval=True on the resulting writeback,
# regardless of what writeback_approval_policy returns.
```

### Existing UI Learning Writer (Phase 9 Keeps + Joins With New Impact Views)

```typescript
// Source: aios-ui/server/aios/learning.ts:proposeRunWritebacks (verbatim shape, lines 15-169)
export const proposeRunWritebacks = (db: Database.Database, runId: string): void => {
  ensureControlPlaneSchema(db);
  // ... already emits a "project" writeback and a "workflow" learning writeback
  //     per terminal run with run_id linkage.
  // PHASE 9 KEEPS THIS WRITER AS-IS (it serves the per-run path).
  // PHASE 9 ADDS sibling functions in the same file:
  //   getLearningImpactForRun(db, runId): LearningImpactPerRun
  //   getLearningImpactRollup(db, scope, key, since): LearningImpactRollup
  //   listRecurringPatterns(db, since): RecurringPattern[]
  //   listConservativeProposals(db, status): ConservativeProposalRow[]
};
```

### Existing Divergent Promotion Path (Phase 9 Replaces With Propose-Then-Approve)

```python
# Source: services/divergent_strategy.py (verbatim shape, line 784)
# BEFORE (current, predates Phase 8 governance):
transition_promotion_lifecycle(
    conn,
    item_id=lifecycle_id,
    to_status="promoted",  # freeform; Phase 8 standardizes to literal
    actor="divergent_strategy",
    rationale="Portfolio winner with judge consensus",
)

# AFTER (Phase 9 wires through Phase 8):
from services.workflow_promotion import propose_asset_promotion
proposal = propose_asset_promotion(
    conn,
    asset_kind="skill",  # or "prompt" / "workflow" depending on portfolio item kind
    asset_key=winning_candidate_key,
    to_state="candidate",  # winners enter as candidate; manual approval required for active
    evidence={
        "source": "divergent_strategy",
        "divergent_run_id": divergent_run_id,
        "judge_scores": judge_scores,
        "portfolio_rationale": portfolio_rationale,
    },
    actor="divergent_strategy",
)
# proposal -> { writeback_id, lifecycle_id, requires_approval=True }
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `workflow_learning_events` records only run-shape evidence_type | Two-axis classification: `evidence_type` (run shape) + `signal_kind` (signal content) | Phase 9 (this phase) | Operators can tell "this was a workflow run with a weak prompt finding" apart from "this was a workflow run with a route misroute finding." |
| No cross-run analysis — `_workflow_learning_payload` is per-run | `services/learning_analysis.detect_recurring_patterns()` runs bounded windowed reads | Phase 9 | Recurring failures, ignored rules, bloated packets, and weak prompts become detectable from accumulated evidence. |
| No conservative proposal synthesis | `services/conservative_optimizer.propose_from_pattern()` emits `improvement_writebacks` rows gated by declarative thresholds | Phase 9 | Recurring patterns become reviewable proposals; nothing silently mutates routing or packets. |
| Divergent winners promote via direct `transition_promotion_lifecycle` (predates Phase 5 governance) | Divergent winners flow through `propose_asset_promotion` → writeback → approval → lifecycle | Phase 9 (depends on Phase 8) | Divergent strategy is no longer a back-door to lifecycle promotion. |
| No compounding visibility | `LearningImpactPerRun` (per-run) + `LearningImpactRollup` (per-asset) projections | Phase 9 | Operators see what each run improved and whether assets are getting better over time. |
| Approval policy covered prompt / skill / workflow / standards / global scopes | Adds `route-default` + `packet-default` scopes | Phase 9 | Route hint and packet shape changes get the same approval discipline as prompt/skill/workflow changes. |
| `aios workflow-learning-audit` shows per-run evidence + proposals | Same command also shows recurring patterns and conservative proposals | Phase 9 | One CLI surface answers "what evidence do we have?" and "what should change?" |

**Deprecated/outdated:**
- Direct `transition_promotion_lifecycle` calls from `divergent_strategy.py` (line 784) and `workflow_experiments.py` post-experiment scoring — replaced by Phase 8's `propose_asset_promotion`. Kept as fallback for one cycle; remove in Phase 10.
- Per-run-only learning evidence as the sole surface — joined by cross-run pattern detection. The per-run path stays valid; the cross-run path layers on top.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Phase 8 ships `services/workflow_promotion.py` with `propose_asset_promotion` / `propose_workflow_promotion` and standardizes `promotion_lifecycle_items.status` to the five-state literal **before** Phase 9 starts. | Pattern 6 / Environment Availability | If Phase 8 partially completes, Pattern 6 (divergent + experiment wiring) is descoped. Core Phase 9 work (analysis, optimizer, impact) still ships without it. |
| A2 | `route-default` and `packet-default` are acceptable new `impact_scope` values to add to `writeback_approval_policy`. | Pitfall 7 / Pattern 1 | If the user prefers different scope names (e.g., `routing-default`, `context-packet-default`), one-line rename. If the user opposes adding new scopes and prefers reusing existing ones (e.g., `workflow-default` for route changes), the mapping in `SIGNAL_TO_IMPACT_SCOPE` changes but the architecture stays the same. Confirm in discuss-phase. |
| A3 | Conservatism thresholds belong in `config/learning/conservatism-policy.json` rather than hardcoded in `services/conservative_optimizer.py`. | Alternatives Considered | If the user prefers hardcoded defaults with operator override via CLI flag, the config file becomes optional. Low-risk either way. |
| A4 | Phase 9 forbids real-time recommender consumption of pending pattern proposals; recommenders read only approved (post-writeback) asset lifecycle states. | Anti-Patterns / Summary | This is the load-bearing safety property of the phase. If the user wants real-time consumption with confidence-weighted shadow application, scope expands significantly and the "no silent policy drift" guarantee is harder to enforce. Confirm in discuss-phase. |
| A5 | Adding `signal_kind` as a nullable TEXT column on `workflow_learning_events` is preferred over a sibling `learning_signals` table. | Alternatives Considered | If the user prefers a normalized sibling table for analytics queries, scope grows by one table + JOIN paths. The column-add approach is simpler and matches the existing additive-migration style. |
| A6 | The seven detector functions (`repeated_failures`, `ignored_rules`, `bloated_packets`, `weak_prompts`, `weak_workflows`, `route_misroutes`, `standards_regression`) are the right initial set. | Pattern 2 | If the user wants a smaller set (e.g., ship four, defer three), scope is easily reduced; the dispatch table makes it trivial to add detectors in follow-up tasks. The user may also want different detectors (e.g., `weak_skill`, `criterion_drift`). Confirm in discuss-phase. |
| A7 | New UI router `aios-ui/server/routers/learning.ts` is preferred over extending `aios-ui/server/routers/control-plane.ts`. | Alternatives Considered | Either is fine. New file isolates learning concerns; extension keeps fewer files. Confirm in discuss-phase. |
| A8 | Phase 9 does NOT introduce a daily-cron / scheduled-hook trigger for `detect_recurring_patterns` — operator runs `aios learning-analyze` on demand. Scheduling lives in Phase 10. | Pattern 2 | If the user wants Phase 9 to wire a periodic hook (e.g., daily via `bin/hook-stop.py` once per day), scope grows by one task. Low-risk extension. |
| A9 | Existing `_record_workflow_learning_event` dedupe key `(run_id, evidence_type, proposal_target)` should be extended to `(run_id, evidence_type, proposal_target, signal_kind)` so one run can emit multiple signals of different kinds. | Pattern 5 | If the dedupe should stay tight (one row per (run, evidence_type, target) regardless of signal_kind), one run may emit only one signal — restricting the signal taxonomy's expressive power. Confirm in discuss-phase. |
| A10 | The cooling period applies to ANY proposal with the same `pattern_id`, regardless of decision (approved/rejected/pending). A `permanently_silenced` flag is out of scope for Phase 9. | Pitfall 3 | If the user wants rejected proposals to never re-propose, add a `permanently_silenced` flag check (small extension). |
| A11 | `LearningImpactRollup.trend` returns `"insufficient_data"` for sample_size < 10. | Pitfall 9 | Tunable. The threshold sits in `config/learning/conservatism-policy.json.min_sample_size_for_trend`. |
| A12 | The `signal_kind` value emitted at run closeout (per-run) uses heuristics over already-computed evidence (workflow status, blocker count, follow_up_required, etc.). Pattern detection (cross-run) computes signals from source evidence tables independently of the per-run closeout signals. | Pattern 5 | If the user wants per-run and cross-run signal_kind values to always agree, the closeout heuristic must call the same detector logic — scope expands by one helper function. Confirm in discuss-phase. |

## Open Questions (RESOLVED)

> All open questions confirmed-or-recommended below. Items marked **CONFIRM IN DISCUSS-PHASE** are flagged so the user can lock or override the recommendation.

1. **Should the conservative optimizer auto-emit proposals on every terminal run, or only on operator demand via `aios learning-analyze --propose`?**
   - What we know: `_workflow_learning_payload` already runs on every `aios workflow-learning-audit` invocation. Adding `--propose` to that flow is one-line.
   - What's unclear: Whether automatic proposal emission on every terminal run is too noisy.
   - Recommendation: Operator demand only for Phase 9 (one-shot via CLI or UI button). Phase 10 can add scheduling if signal-to-noise is acceptable. **CONFIRM IN DISCUSS-PHASE.**

2. **Should new impact scopes (`route-default`, `packet-default`) live in Phase 5's `writeback_approval_policy` directly, or in a Phase-9 sibling shim?**
   - What we know: Phase 5's policy function is in `bin/aios_orchestration_runtime.py` lines 816-851. Phase 8 already established a services-side shim pattern (assumption A4 from Phase 8 research).
   - What's unclear: Whether to extend Phase 5's function or to add a Phase-9-specific policy that wraps it.
   - Recommendation: Extend Phase 5's function directly with the two new scopes (one-line each); reuse the Phase 8 services-side shim for the services-layer import. **CONFIRM IN DISCUSS-PHASE.**

3. **Should `LearningImpactRollup` aggregate per-project by default, or cross-project?**
   - What we know: Phase 7 chose per-project as the default for delta scoring; Phase 8 also per-project with cross-project fallback.
   - What's unclear: Whether learning rollups should match (per-project default + cross-project fallback) or always show cross-project (since learning is a system-level concern).
   - Recommendation: Match Phase 7/8 — per-project default with cross-project as an explicit operator opt-in via `--scope cross-project`. **CONFIRM IN DISCUSS-PHASE.**

4. **Should `divergent_strategy.py` and `workflow_experiments.py` wiring into Phase 8 promotion ship as part of Phase 9, or as a Phase-9 follow-up?**
   - What we know: Both currently call `transition_promotion_lifecycle` directly (predates Phase 5/8 discipline). The wiring is a tightening of governance but breaks existing tests (Pitfall 6).
   - What's unclear: Whether Phase 9 owns the wiring or defers it.
   - Recommendation: Include in Phase 9 since it's the architectural cleanup that makes learning loops governance-correct; flag the test update explicitly so it's not a surprise. **CONFIRM IN DISCUSS-PHASE.**

5. **Should `signal_kind` values be set explicitly on per-run closeout events, or computed lazily on read?**
   - What we know: The per-run path writes to `workflow_learning_events` at terminal run close. The cross-run path reads source evidence tables independently.
   - What's unclear: Whether closeout-time `signal_kind` adds value, or whether read-time computation from source tables is sufficient.
   - Recommendation: Set at closeout when a clear heuristic exists (e.g., `follow_up_required=1` → `repeated_failure` candidate); leave NULL otherwise. Detectors do not rely on this column. **CONFIRM IN DISCUSS-PHASE.**

6. **Should the conservatism policy support per-project overrides?**
   - What we know: AIOS is local-first; current AIOS deployments are largely single-project.
   - What's unclear: Whether per-project threshold tuning is needed for the first cycle.
   - Recommendation: No per-project overrides in Phase 9. The policy is a single global JSON file. Per-project tuning can land in a follow-up if needed. **CONFIRM IN DISCUSS-PHASE.**

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x (Python 3.12) |
| Config file | `pyproject.toml` (ruff + basedpyright + vulture sections); no separate `pytest.ini` block |
| Quick run command | `uv run pytest tests/test_learning_taxonomy.py tests/test_learning_analysis.py tests/test_conservative_optimizer.py tests/test_learning_impact.py tests/test_aios_cli.py tests/test_orchestration_runtime.py -x -q` |
| Full suite command | `uv run pytest -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| LEARN-01 | `workflow_learning_events.signal_kind` column added via idempotent migration; pre-migration rows remain visible | unit | `uv run pytest tests/test_orchestration_runtime.py::test_signal_kind_column_added_idempotently -x` | ❌ Wave 0 |
| LEARN-01 | `_record_workflow_learning_event` accepts optional `signal_kind` kwarg and persists it | unit | `uv run pytest tests/test_aios_cli.py::test_record_learning_event_persists_signal_kind -x` | ❌ Wave 0 |
| LEARN-01 | `_workflow_learning_payload` surfaces `signal_kind` in `persisted_events[]` | unit | `uv run pytest tests/test_aios_cli.py::test_workflow_learning_payload_includes_signal_kind -x` | ❌ Wave 0 |
| LEARN-02 | `detect_repeated_failures` returns one pattern per (criterion_id, workflow_key) above recurrence threshold | unit | `uv run pytest tests/test_learning_analysis.py::test_detect_repeated_failures_groups_by_criterion_and_workflow -x` | ❌ Wave 0 |
| LEARN-02 | `detect_ignored_rules` flags open blocker findings that span multiple runs | unit | `uv run pytest tests/test_learning_analysis.py::test_detect_ignored_rules_requires_multi_run_recurrence -x` | ❌ Wave 0 |
| LEARN-02 | `detect_bloated_packets` flags packets > 2σ above per-workflow median | unit | `uv run pytest tests/test_learning_analysis.py::test_detect_bloated_packets_uses_per_workflow_median -x` | ❌ Wave 0 |
| LEARN-02 | `detect_weak_prompts` flags prompts with mean outcome below threshold AND sample_size ≥ floor | unit | `uv run pytest tests/test_learning_analysis.py::test_detect_weak_prompts_requires_sample_floor -x` | ❌ Wave 0 |
| LEARN-02 | `detect_weak_workflows` reads `workflow_execution_reports.status` + stage blocker counts | unit | `uv run pytest tests/test_learning_analysis.py::test_detect_weak_workflows_aggregates_stage_blockers -x` | ❌ Wave 0 |
| LEARN-02 | `detect_route_misroutes` joins `orchestration_runs.route_result_json` with `success_criteria_findings` blockers | integration | `uv run pytest tests/test_learning_analysis.py::test_detect_route_misroutes_uses_route_result_json -x` | ❌ Wave 0 |
| LEARN-02 | `detect_standards_regression` reads `standards_delta_items.priority_bucket='regressed'` history | unit | `uv run pytest tests/test_learning_analysis.py::test_detect_standards_regression_reads_priority_bucket -x` | ❌ Wave 0 |
| LEARN-02 | All detectors honor the `since` parameter and never query unbounded history | unit | `uv run pytest tests/test_learning_analysis.py::test_detectors_honor_since_parameter -x` | ❌ Wave 0 |
| LEARN-03 | `propose_from_pattern` rejects patterns below `min_sample_size` | unit | `uv run pytest tests/test_conservative_optimizer.py::test_proposer_rejects_low_sample -x` | ❌ Wave 0 |
| LEARN-03 | `propose_from_pattern` rejects patterns below `min_recurrence_count` | unit | `uv run pytest tests/test_conservative_optimizer.py::test_proposer_rejects_low_recurrence -x` | ❌ Wave 0 |
| LEARN-03 | `propose_from_pattern` ALWAYS sets `requires_approval=True` regardless of `writeback_approval_policy` return value | unit | `uv run pytest tests/test_conservative_optimizer.py::test_proposer_always_requires_approval -x` | ❌ Wave 0 |
| LEARN-03 | `propose_from_pattern` honors cooling-period: same `pattern_id` not re-proposed within N days | integration | `uv run pytest tests/test_conservative_optimizer.py::test_cooling_period_dedupe -x` | ❌ Wave 0 |
| LEARN-03 | `writeback_approval_policy` recognizes new `route-default` impact scope with `requires_approval=True` | unit | `uv run pytest tests/test_conservative_optimizer.py::test_route_default_requires_approval -x` | ❌ Wave 0 |
| LEARN-03 | `writeback_approval_policy` recognizes new `packet-default` impact scope with `requires_approval=True` | unit | `uv run pytest tests/test_conservative_optimizer.py::test_packet_default_requires_approval -x` | ❌ Wave 0 |
| LEARN-03 | Conservative optimizer NEVER mutates registries directly | architecture | `uv run pytest tests/test_conservative_optimizer.py::test_optimizer_only_writes_to_improvement_writebacks -x` | ❌ Wave 0 |
| LEARN-04 | `build_per_run_impact` returns signals_emitted + assets_evidenced + proposals_created for a given run | integration | `uv run pytest tests/test_learning_impact.py::test_per_run_impact_returns_full_payload -x` | ❌ Wave 0 |
| LEARN-04 | `build_rollup` returns `trend="insufficient_data"` when sample_size below threshold | unit | `uv run pytest tests/test_learning_impact.py::test_rollup_trend_insufficient_data -x` | ❌ Wave 0 |
| LEARN-04 | `build_rollup` returns `trend="improving"` only when rework_rate decreased AND sample_size ≥ threshold | unit | `uv run pytest tests/test_learning_impact.py::test_rollup_trend_improving_requires_sample_floor -x` | ❌ Wave 0 |
| LEARN-04 | CLI `aios learning-impact --run-id X` returns JSON with per-run payload | integration | `uv run pytest tests/test_aios_cli.py::test_learning_impact_cli_per_run -x` | ❌ Wave 0 |
| LEARN-04 | CLI `aios learning-impact --workflow X --since 30d` returns JSON with rollup | integration | `uv run pytest tests/test_aios_cli.py::test_learning_impact_cli_rollup -x` | ❌ Wave 0 |
| LEARN-04 | UI `getLearningImpactForRun` returns the projected payload | type-level | `cd aios-ui && pnpm lint && pnpm tsc --noEmit` | partial (type-level only; manual fixture test if `pnpm test` wired later) |
| Cross-cutting | `aios learning-analyze --since 30d --json` returns recurring patterns + would-be proposals (dry-run) | integration | `uv run pytest tests/test_aios_cli.py::test_learning_analyze_cli_dry_run -x` | ❌ Wave 0 |
| Cross-cutting | `aios learning-propose` writes pending-approval rows to `improvement_writebacks` | integration | `uv run pytest tests/test_aios_cli.py::test_learning_propose_cli_writes_writebacks -x` | ❌ Wave 0 |
| Cross-cutting | `aios contracts-audit` adds `LearningSignal` contract row with status `implemented` | unit | `uv run pytest tests/test_aios_cli.py::test_contracts_audit_includes_learning_signal -x` | ❌ Wave 0 |
| Cross-cutting (depends on Phase 8) | `services/divergent_strategy.py` portfolio winner emits `improvement_writebacks` row instead of direct lifecycle transition | integration | `uv run pytest tests/test_divergent_strategy.py::test_divergent_winner_goes_through_propose_asset_promotion -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:**
  - Python: `uv run pytest tests/test_learning_taxonomy.py tests/test_learning_analysis.py tests/test_conservative_optimizer.py tests/test_learning_impact.py tests/test_aios_cli.py tests/test_orchestration_runtime.py tests/test_divergent_strategy.py -x -q && uv run ruff check services bin tests && uv run ruff format --check services bin tests && uv run basedpyright`
  - UI (when TS files change): `cd aios-ui && pnpm lint && pnpm tsc --noEmit`
- **Per wave merge:**
  - `uv run pytest -q && uv run ruff check . && uv run ruff format --check . && uv run basedpyright && uv run vulture services bin --min-confidence 70`
  - `cd aios-ui && pnpm lint && pnpm tsc --noEmit`
- **Phase gate:**
  - Full suite green
  - `aios contracts-audit` shows `LearningSignal` contract row with `status: implemented`
  - `aios learning-analyze --since 30d --json` returns a populated payload on the AIOS dev DB with at least one detected pattern
  - `aios learning-impact --workflow implementation-delivery --since 30d` returns a populated rollup
  - Manual operator check: open the learning surface in `aios-ui` and confirm per-run impact + rollup render with proposal-status callouts (Pitfall 8)

### Wave 0 Gaps

- [ ] `tests/test_learning_taxonomy.py` — NEW file: literal completeness + impact_scope mapping (2 tests)
- [ ] `tests/test_learning_analysis.py` — NEW file: 8 detector tests above
- [ ] `tests/test_conservative_optimizer.py` — NEW file: threshold gates, cooling period, scope mapping, never-mutate-registry (7 tests above)
- [ ] `tests/test_learning_impact.py` — NEW file: per-run + rollup projections, trend math (3 tests above)
- [ ] `tests/test_aios_cli.py` — extend: new CLI subcommands + extended workflow-learning-audit shape (6 tests above)
- [ ] `tests/test_orchestration_runtime.py` — extend: `signal_kind` column migration test (1 test)
- [ ] `tests/test_divergent_strategy.py` — extend: assert new propose-then-approve contract (1 test)
- [ ] `aios-ui/lib/types.ts` — extend with `LearningSignalKind`, `RecurringPattern`, `LearningImpactPerRun`, `LearningImpactRollup`, `ConservativeProposalRow` types
- [ ] `aios-ui/server/aios/learning.ts` — extend with `getLearningImpactForRun`, `getLearningImpactRollup`, `listRecurringPatterns`, `listConservativeProposals`
- [ ] `aios-ui/server/routers/learning.ts` — NEW file (or extend `control-plane.ts` per A7)
- [ ] `config/learning/conservatism-policy.json` — NEW file with initial conservative defaults
- [ ] No new conftest.py needed — existing tests use direct `sqlite3.connect(":memory:")` patterns and per-test schema seeding
- [ ] No framework install required; pytest + ruff + basedpyright + pnpm already wired

## Security Domain

> Phase 9 introduces no new authentication, session management, network surface, or cryptographic concerns. Security applicability is bounded to: (a) conservative-optimizer proposals MUST flow through Phase-5 `writeback_approval_policy` with `requires_approval=True` on every emitted proposal; (b) pattern-detection queries must not leak sensitive evidence (filesystem paths, prompt text) beyond what `prompts_used.prompt_text`, `briefing_packets.selected_*_json`, and `workflow_execution_reports.report_json` already expose; (c) the new `route-default` and `packet-default` impact scopes must be added to `writeback_approval_policy` with `requires_approval=True` to match the existing prompt/skill/workflow/standards scope discipline; (d) the runtime path (Phase 1 `recommend_route_primitives`, Phase 2 packet compilation) MUST NOT consume pending pattern proposals — only approved (post-writeback) asset lifecycle states; and (e) Phase 9 wiring of `divergent_strategy.py` and `workflow_experiments.py` MUST tighten governance, not loosen it (divergent winners enter `candidate`, not `active`).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | n/a — internal CLI / hook / UI-server surface |
| V3 Session Management | no | n/a |
| V4 Access Control | yes | All Phase 9 proposals go through `writeback_approval_policy` with `requires_approval=True`; runtime recommenders read only approved-lifecycle assets. |
| V5 Input Validation | yes | `RecurringPattern` and `ConservatismPolicy` fields validated against typed literals; CLI inputs validated by argparse + JSON schema check; UI tRPC routes validate inputs with `zod`. |
| V6 Cryptography | no | n/a |
| V7 Error Handling | yes | Pattern detection fails closed: malformed evidence rows are skipped with a logged warning rather than crashing the detector; the dispatcher returns partial results with a `partial: True` flag if any detector errored. |
| V10 Malicious Code | partial | `config/learning/conservatism-policy.json` is reviewable in git; loader validates required keys against the `ConservatismPolicy` dataclass shape. |
| V13 API & Web Service | partial | tRPC routes already validate inputs; new `getLearningImpact*` and `listRecurringPatterns` / `listConservativeProposals` routes use `zod`. No new external API surface introduced. |
| V14 Configuration | yes | New config file reviewable in git; no secrets enter learning artifacts; conservatism policy changes are auditable via commit history. |

### Known Threat Patterns for Continuous Learning

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Silent policy drift via real-time recommender consumption of pending pattern proposals | Tampering | Phase 9 forbids real-time consumption (Anti-Patterns). Recommenders read only approved-lifecycle assets via Phase 8 paths. Architecture test `test_recommenders_do_not_consume_pending_writebacks`. |
| Auto-promotion bypass — optimizer emits a writeback with `requires_approval=0` | Repudiation / Elevation of Privilege | Test `test_proposer_always_requires_approval` enforces. `writeback_approval_policy` extended to fail loud on unknown impact scopes. |
| Pattern-detection poisoning — attacker writes fake `prompts_used` / `success_criteria_findings` rows to inflate a recurrence count | Tampering | Evidence sources are written only by managed hooks and the orchestration runtime; no operator write path. Pattern rationale cites raw `evidence_run_ids` so anomalies are visible on review. |
| Cooling-period bypass — pattern re-proposed every analysis run because `metadata.pattern_id` differs slightly | Tampering | `pattern_id` is computed as a stable hash of `(signal_kind, scope_kind, scope_key, since_window_bucket)`; identical patterns yield identical IDs. Test `test_pattern_id_is_stable_across_runs`. |
| `route_misroute` proposal links to a different route than the one with the actual problem | Information Disclosure / Wrong Mitigation | Proposal `evidence_run_ids` MUST cite the specific runs where the misroute fired; reviewer can inspect each run's `orchestration_runs.route_result_json` directly. |
| `bloated_packet` recommendation leaks raw packet content via `summary` field | Information Disclosure | Pattern `summary` text uses bucketed size descriptors (e.g., "median packet size 23 sections, this packet 47 sections") rather than raw content. |
| Divergent winner promoted directly to `active` (bypassing Phase 5/8 governance) | Repudiation | Pattern 6 wiring routes through `propose_asset_promotion` with `to_state="candidate"`; manual approval required for active. Test `test_divergent_winner_enters_as_candidate`. |
| `LearningImpactRollup` shows "improving" for a workflow with only 3 runs in the window | Information Disclosure (misleading metric) | `trend="insufficient_data"` when sample_size < threshold (Pitfall 9). Rationale text always cites sample_size. |
| `signal_kind` migration silently drops pre-migration `workflow_learning_events` from views | Denial of Service (UX) | UI labels NULL `signal_kind` as "unclassified (legacy)"; tests assert pre-migration rows remain visible (Pitfall 2). |
| Phase 9 conservatism policy file (`config/learning/conservatism-policy.json`) tuned too loose, flooding approvers | Denial of Service | Initial conservative defaults; `aios learning-analyze --dry-run` mode for review before live propose; document tuning guidance in PROJECT.md. |

## Sources

### Primary (HIGH confidence)

- `services/aios_cli.py` (in-tree, lines 100-3580 read in sections) — `WORKFLOW_LEARNING_EVIDENCE_TYPES` literal (line 147-153), `TERMINAL_RUN_STATUSES` literal (line 100), `_workflow_learning_kind` (lines 2018-2027), `_ensure_workflow_learning_schema` (lines 2111-2132), `_record_workflow_learning_event` (lines 2156-2193), `_inferred_learning_evidence` (lines 2056-2108), `_no_learning_reason` (lines 2196-2205), `_workflow_learning_payload` (lines 2208-2377), `_run_has_governance_evidence` (lines 2483-2494), `_governance_audit_payload` (lines 2529-2607), CLI subparser wiring (lines 3197, 3326, 3479, 3536-3538). [VERIFIED: read complete sections]
- `bin/aios_orchestration_runtime.py` (in-tree, lines 180-260 read) — `workflow_learning_events` schema bootstrap (lines 189-209). Phase 5 `writeback_approval_policy` and `insert_writeback` referenced from Phase 8 RESEARCH (lines 816-851). [VERIFIED: read schema-ensure block]
- `bin/hook-stop.py` (in-tree, lines 600-720 read) — terminal-run closeout flow including `workflow_learning_writeback_expected` flag, `evaluate_and_record`, `evaluate_standards_health`, `insert_workflow_execution_report`. [VERIFIED: read]
- `schema.sql` (in-tree, sections 44-100, 147-160, 184-260, 376-510, 544-583 read) — `prompts_used`, `agentize_evaluations`, `experiments`, `orchestration_runs`, `improvement_writebacks`, `improvement_writeback_events`, `divergent_runs`, `divergent_candidates`, `divergent_judgments`, `memory_writeback_proposals`, `promotion_lifecycle_items`, `workflow_learning_events`, `consistency_findings`, `success_criteria_findings`. [VERIFIED: read]
- `services/divergent_strategy.py` (in-tree) — `promotion_lifecycle_items` schema ensure (lines 225-235), `transition_promotion_lifecycle` (line 578), direct lifecycle write at line 784 (PHASE 9 TO REPLACE). [VERIFIED: grep + read shape]
- `services/workflow_experiments.py` (in-tree, 779 lines, first 270 lines read) — `workflow_skill_experiments` + `github_skill_candidates` schemas, queue/run flow, status transitions. [VERIFIED: read first 270 lines + grep complete]
- `services/workflow_synthesis.py` (in-tree, 917 lines) — `workflow_synthesis_proposals` with `pending_approval`/`approved`/`rejected` lifecycle, `recurring` keyword usage on line 142 (existing convention for recurring-pattern terminology). [VERIFIED: grep]
- `services/success_criteria.py` (in-tree, 986 lines) — `success_criteria_findings.resolution_status` lifecycle ("open","accepted","resolved","waived","stale"), `evaluate_and_record` writer. [VERIFIED via Phase 6 research]
- `services/standards_health.py` (in-tree, 1599 lines) — `standards_delta_items.priority_score`/`priority_bucket`, `_build_delta_items`, `recommend_workflow_from_health` (Phase 7). [VERIFIED via Phase 7 research]
- `services/agentize.py` (in-tree) — `agentize_evaluations` writer at `bin/aios_orchestration_runtime.py:518-545` mirroring schema.sql definition. [VERIFIED via Phase 8 research + grep]
- `services/task_routing.py` (in-tree) — `RouteResult` shape including `route_result_json` persistence on `orchestration_runs`. [VERIFIED via Phase 8 research]
- `aios-ui/server/aios/learning.ts` (in-tree, 170 lines, complete read) — `proposeRunWritebacks(db, runId)` per-run writeback emitter; the existing per-run UI surface that Phase 9 extends. [VERIFIED: read complete file]
- `aios-ui/server/aios/control-plane.ts` (in-tree, lines 1-420 read in sections) — governance overview, run gaps detector `terminalRunGaps`, `runHasGovernanceEvidence` checks `workflow_learning_events` directly (lines 199-213). [VERIFIED: read]
- `aios-ui/server/routers/_app.ts` — confirms divergent + experiments routers already wired (lines 6-7, 23, 28). [VERIFIED: grep]
- `aios-ui/server/routers/experiments.ts` (in-tree, 161+ lines) — reads `experiments` and `workflow_skill_experiments` tables. [VERIFIED: grep]
- `aios-ui/server/routers/divergent.ts` (in-tree, 320+ lines) — reads `divergent_runs`, `divergent_candidates`, `divergent_judgments`. [VERIFIED: grep]
- `aios-ui/server/routers/patterns.ts` (in-tree, 158+ lines) — reads `patterns` table (existing surface; Phase 9 extends but does not duplicate). [VERIFIED: grep]
- `aios-ui/server/routers/control-plane.ts` — `requestKind: z.enum(["topic", "failure_pattern", "code_area", "policy", "recent_run"])` confirms `failure_pattern` is an existing axis the UI already understands (line 72). [VERIFIED: grep]
- `.planning/REQUIREMENTS.md` — LEARN-01..04 wording (lines 73-77). [VERIFIED: read]
- `.planning/ROADMAP.md` — Phase 9 scope, detailed scope, current surfaces, workflow ownership, expected outputs, dependencies, observable success criteria (lines 444-481). [VERIFIED: read]
- `.planning/REQUIREMENTS_CODE_SURFACE_MATRIX.md` — LEARN-01..04 surface authority mapping (lines 93-96). [VERIFIED: read]
- `.planning/TIER_ONE_ACCEPTANCE_CHECKLIST.md` — Phase 9 capability gates, evidence gates, failure conditions (lines 191-211). [VERIFIED: read]
- `.planning/WORKFLOW_MATRIX.md` — `divergent-strategy` (line 48) and `Prompt experiment` (line 63) workflow shapes; ownership tagging (Phase 8 + Phase 9). [VERIFIED: grep + read]
- `.planning/FUNCTIONALITY_MAP.md` — workflow learning loop, conservative self-improvement, prompt/skill experiments, corpus/regression harness (lines 36-42). [VERIFIED: grep + read]
- `.planning/STATE.md` — Phase 5 is "active", Phase 6/7/8 marked completed in `progress.completed_phases: 5` (mismatch between text "Phase 5" and progress count — confirms STATE.md needs update, but Phase 9 is sequenced after Phase 8). [VERIFIED: read]
- `.planning/phases/05-*/05-CONTEXT.md` — Phase 5 governance contract Phase 9 inherits. [VERIFIED: read]
- `.planning/phases/06-*/06-RESEARCH.md` — Phase 6 stage findings + EvaluationFinding lifecycle ("open","accepted","resolved","waived","stale") that Phase 9 reads. [VERIFIED: read complete]
- `.planning/phases/07-*/07-RESEARCH.md` — Phase 7 standards delta scoring + `recommend_workflow_from_health` that Phase 9 reads. [VERIFIED: read complete]
- `.planning/phases/08-*/08-RESEARCH.md` — Phase 8 asset lifecycle + `propose_workflow_promotion` / `propose_asset_promotion` paths Phase 9 wires divergent + experiments through. [VERIFIED: read complete]
- `AGENTS.md` (in-tree, top portion read) — local-first, governance, brownfield continuity, explainability constraints; runtime sources of truth; hook integration. [VERIFIED: read first 80 lines]
- `tests/test_architecture_enforcement.py` (in-tree, lines 1-100 read) — `services/` cannot import `bin/`. [VERIFIED: read]
- `bin/promote-patterns.py`, `bin/synthesize-workflows.py`, `bin/extract-bug-motifs.py`, `bin/agent-synthesis.py`, `bin/cron-ingest-codex.py` — existing scripts that surface recurring patterns from bug log / codex history (analogous to Phase 9 pattern detection but for different evidence sources; Phase 9 does NOT duplicate these — it adds detectors for workflow / packet / route / standards evidence). [VERIFIED: grep]

### Secondary (MEDIUM confidence)

- `services/harness_eval.py` (in-tree) — `expected_context_packets` and `selected_context_packets` fields confirm the packet-shape evidence shape Phase 9's `detect_bloated_packets` reads (lines 43, 233, 247-248). [VERIFIED: grep]
- `aios-ui/server/aios/learning.ts:proposeRunWritebacks` impact scope assignment (lines 152-153) confirms `workflow-default` is the existing convention for workflow-affecting writebacks. [VERIFIED: read]
- `services/aios_cli.py:_no_learning_reason` (lines 2196-2205) — confirms five existing "no learning" reasons (`canceled_without_signal`, `failed_before_artifact`, `missing_closeout_summary`, `insufficient_evidence`, `one_off_task`) that Phase 9's `LearningImpactPerRun.no_learning_reason` reuses. [VERIFIED: read]

### Tertiary (LOW confidence)

- None — Phase 9 is an internal phase researched entirely against in-tree code, config, planning docs, and Phase 5/6/7/8 research outputs; no external web sources required.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every primary surface is in-tree and read directly during research; no external dependency assumptions.
- Architecture: HIGH — pattern follows Phase 5/6/7/8 conventions exactly; analysis + optimizer + impact modules are additive and use existing data shapes.
- Detector dispatch and signal taxonomy: HIGH — the seven detectors map cleanly to existing evidence tables; the literal axis is orthogonal to existing `evidence_type`.
- Conservative optimizer: HIGH — emits to existing `improvement_writebacks` with Phase 5 approval policy. `requires_approval=True` is a hard invariant.
- LearningImpact projections: HIGH — projects what's already persisted; no new persistence.
- Wiring divergent + experiments into Phase 8: MEDIUM — depends on Phase 8 completion (assumption A1). Pitfall 6 documents the test update required.
- New impact scopes (`route-default`, `packet-default`): MEDIUM — assumption A2 needs user confirmation; the implementation is one-line per scope but the naming is opinionated.
- Conservatism policy thresholds: MEDIUM — initial values are conservative but tuning will require operator iteration; `--dry-run` mode mitigates risk.
- Real-time vs approved-asset-only feedback: HIGH — assumption A4 is the load-bearing safety property of the phase; not negotiable without redesigning the governance discipline.

**Research date:** 2026-05-21
**Valid until:** 2026-06-21 (30 days — stable surfaces; the conservatism policy file and detector implementations evolve during this phase itself.)
