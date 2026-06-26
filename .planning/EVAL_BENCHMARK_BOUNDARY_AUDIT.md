# Eval And Benchmark Harness Boundary Audit

Date: 2026-06-26
Branch: `codex/eval-benchmark-boundary-audit`

## Verdict

Do not split the agent eval / benchmark harness as a standalone repo yet.

AIOS should keep the runtime and storage pieces because they are part of the operating layer: eval run recording, local SQLite tables, major-task closeout expectations, peer trace state, shadow worktree lifecycle, operator UI projections, corpus execution, and TMCP benchmark evidence all depend on AIOS-local workflow state, project inventory, context profiles, and quality gates.

The best next extraction candidate is narrower: a future `agent-eval-contract` package containing portable schemas, context profile vocabulary, failure taxonomy, score dimensions, template validation, harness fixture format, external benchmark normalization, and sample records. That package should be built only after AIOS validates live eval artifacts against it and at least one non-AIOS runner consumes the contract fixtures.

## Evidence Inspected

- `services/eval_run_service.py` owns durable SQLite-backed eval tasks, runs, scores, failures, gold-set tasks, context profiles, priorities, and status validation.
- `schema.sql` defines `eval_tasks`, `eval_runs`, `eval_scores`, `eval_failures`, `eval_gold_set_tasks`, `eval_second_brain_retrievals`, `eval_gold_set_context`, `shadow_branch_runs`, `peer_sessions`, `peer_traces`, and `shadow_candidates`.
- `services/harness.py` executes AIOS-specific context compilation, success-criteria preview, orchestration-run insertion, briefing-packet creation, and lifecycle event recording.
- `services/harness_eval.py` is more portable: it scores deterministic fixture artifacts for context precision/recall, gate accuracy, success-criteria recall, trace completeness, false-completion detection, recovery evidence, and writeback usefulness.
- `docs/evals/aios-harness-eval-v0.md` defines a stable fixture contract under `tests/fixtures/harness-eval/**`.
- `docs/evals/benchmark-eval-architecture.md` defines the four-layer eval stack, scoring formula, comparison semantics, failure taxonomy, completion gates, and anti-cheating rules.
- `docs/evals/context-profiles.md` defines six context profiles and explicitly separates personalized/local lift from portable or clean-room claims.
- `config/agent-eval/eval-schemas.py` already contains TypedDict-style portable contract candidates for `EvalTask`, `EvalRun`, `ShadowCandidate`, `EvalScore`, and `EvalFailure`.
- `services/external_benchmark_adapter.py` is already mostly portable: it maps eval tasks to SWE-bench / Terminal-Bench-style formats and normalizes external results as `external_clean_room`.
- `services/shadow_branch_runner.py` is AIOS/runtime-bound because it creates git worktrees, writes `shadow_branch_runs`, and joins eval-run records.
- `services/peer_trace.py` is AIOS/runtime-bound because it stores privacy-safe peer sessions/traces and shadow candidates in the local eval schema.
- `services/second_brain_eval.py` is AIOS-local by definition because it measures local retrievals, gold-set context, staleness, and second-brain lift.
- `services/tmcp_benchmark.py` and `bin/tmcp-benchmark.py` provide a file-backed TMCP benchmark scaffold, but the benchmark is still strongly tied to local repositories, TMCP graph/shortcut state, and AIOS claims discipline.
- `scripts/aios-corpus-eval.cjs` runs AIOS corpus checks against copied/synthetic workspaces and assumes AIOS command paths, config roots, state DBs, and local test suites.
- Focused tests exist for the main surfaces: eval run service, harness eval, agent harness, external benchmark adapter, TMCP benchmark, peer trace, shadow branch runner, and corpus eval.

## Keep Inside AIOS

These surfaces should remain AIOS-owned:

- SQLite schema and runtime persistence for eval records, peer traces, shadow candidates, and shadow branch runs.
- `aios eval`, `aios harness-*`, `aios peer-trace`, `aios shadow`, and `aios corpus` command integration.
- AIOS context compiler, success-criteria, briefing packet, orchestration-run, and operator UI integration.
- Shadow worktree creation, contamination checks, and AIOS branch comparison metadata.
- Second-brain lift, retrieval metrics, local gold-set context, and personalized/local portability labeling.
- TMCP benchmark execution and claims discipline while it depends on local TMCP graph, shortcut registry, and local repo inventory.
- Corpus eval execution while it is primarily a product regression harness for AIOS itself.

## Portable Contract Candidate

A future `agent-eval-contract` package could contain:

- Context profile enum and comparison semantics.
- Eval task, run, score, failure, shadow candidate, and peer trace schemas.
- Failure taxonomy and priority/status validation.
- AIOS Effectiveness Score dimensions and weighting metadata.
- Harness fixture schema and deterministic scoring expectations.
- External benchmark request/response normalization types.
- Major-task eval, failure-record, shadow-branch, backfill, and portable-context-packet template validators.
- Sample records that explicitly label `jakye_second_brain_full` and `jakye_second_brain_limited` as personalized/local.

This contract should be shared with `quality-evidence-contract` rather than duplicating generic finding/evidence concepts.

## Why A Standalone Runtime Split Is Premature

1. Storage and lifecycle are AIOS-owned.
   Eval records are not just files; they are linked to AIOS SQLite state, runs, projects, session closeout, operator surfaces, and success criteria.

2. The harness depends on AIOS context and workflow services.
   `services/harness.py` calls the context compiler, success criteria preview, orchestration tables, and briefing packet storage.

3. Shadow automation is operationally local.
   Worktree creation, branch contamination checks, replay metadata, and shadow comparisons belong with the local operating layer that launches and records them.

4. TMCP benchmark is not a general benchmark product yet.
   It has useful file contracts and tests, but the current scope is proving TMCP graph/shortcut behavior across local repos while preserving conservative AIOS claim gates.

5. External benchmark adapters are too thin to justify their own repo.
   They are good package-contract material, but not enough runtime/product surface by themselves.

## Required Before Reconsidering Extraction

- Validate live eval run artifacts against a shared schema package.
- Add JSON-schema or package-level validators for docs/eval templates and harness fixtures.
- Prove a non-AIOS runner can produce records accepted by AIOS without importing AIOS services.
- Split generic eval evidence from AIOS-specific storage writes and operator projections.
- Decide how `quality-evidence-contract` and a possible `agent-eval-contract` share finding/evidence vocabulary.
- Produce at least one clean-room fixture run that uses the contract without AIOS local DB state.
- Run repeated real TMCP benchmark tasks with passing quality commands before treating `tmcp-benchmark` as product-ready.

## Decision

Keep eval and benchmark runtime inside AIOS. Promote only the schema/template/fixture layer toward a future contract package after validator coverage and non-AIOS fixture consumption exist.
