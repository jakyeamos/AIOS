# AIOS Harness Determinism Audit

Phase 16 Plan 16-01 harness audit of the current AIOS execution and evaluation harness.

Scope: entrypoints, managed runtime, hooks, orchestration, lifecycle state, prompt/template routing, model selection, context routing, second-brain integration, evaluation, evidence, recovery, shadow workflows, learning, operator surfaces, scripts, CI-style checks, and known WIP areas.

## 1. Existing AIOS Architecture Summary

AIOS already has a durable local-first harness. The main runtime spine is SQLite plus file artifacts, with conversation hooks and managed runs writing explicit state instead of relying only on chat history.

- `bin/aios.py` is the thin CLI bootstrap into `services.aios_cli.main`.
- `services/aios_cli.py` is the broad operator CLI. It exposes status, metadata, logs, learning, eval, shadow, peer trace, ablation, packet generation, benchmark adapters, standards, asset lifecycle, workflow comparison, harness briefing/simulation/replay/shadow evaluation, start-work, quality gates, skills harvest, corpus, and harness-eval commands.
- `bin/aios-managed-run.py` is the managed backend runtime. It loads an `orchestration_runs` row, emits lifecycle hooks, compiles a TMCP packet, executes a registered workflow, writes `logs/control-plane/workflow-reports/<invocation>.json`, persists a workflow report row, writes a control-plane invocation report, and closes through explicit run/session/invocation linkage.
- `bin/aios_orchestration_runtime.py` owns the most complete runtime schema helpers and deterministic transition helpers: `ensure_runtime_schema`, `record_run_event`, `transition_run`, `create_invocation`, `update_invocation`, `link_session_runtime`, and `insert_workflow_execution_report`.
- Hooks are still important runtime adapters: `bin/hook-session-start.py` opens or links sessions and generates compact context packets; `bin/hook-prompt-submit.py` records prompt metadata and prompt-time retrieval; `bin/hook-post-tool-use.py` records tool events, artifacts, RTK compression events, and bugs; `bin/hook-stop.py` performs closeout, evaluation, memory updates, writebacks, standards snapshots, effectiveness receipts, and governed closeout artifacts.
- `services/workflow_orchestration.py` loads JSON workflow/skill registries, validates bindings, selects prompt/templates and execution strategies, executes staged skills, records stage-level success criteria findings, and returns workflow reports.
- `services/task_routing.py` chooses project, workflow, prompt, backend, agent, skill, and workflow alternatives before run creation.
- `services/invocation_backends.py` defines the backend contract fields and supported managed/manual backend records.
- `tools/context-compile.mjs` is the file-backed deterministic context compiler. It writes `aios/context/compiled/latest.*` and `aios/context/receipts/latest.*` with selected/skipped context, conflicts, stale/missing context, writeback candidates, retrieval trace, and a packet contract.
- `services/context_compiler.py` is the memory-backed compiler with deterministic stable-prefix sections and dynamic task memory.
- `services/tmcp_runtime.py` compiles and persists intent-specific TMCP packets and traversal receipts, including selected/skipped nodes, transition trace, fingerprint, token estimates, shortcut governance, and validation evidence.
- `services/success_criteria.py` evaluates registry criteria at closeout and per workflow stage. It persists evaluation/finding artifacts in SQLite and JSON under `data/success-criteria/evaluations/`.
- `services/harness.py` provides backend-neutral harness brief, fixture simulation, session replay, shadow evaluation, and active-readiness reporting. It currently reports active enforcement as disabled until fake, replay, and shadow gates have reviewed evidence.
- `services/harness_eval.py` scores deterministic fixture runs for context precision/recall, gate accuracy, criteria recall, trace completeness, false-completion detection, recovery evidence, and writeback usefulness.
- `services/eval_run_service.py`, `services/second_brain_eval.py`, `services/shadow_branch_runner.py`, `services/shadow_automation.py`, and `services/peer_trace.py` implement the Phase 11 eval, second-brain lift, shadow worktree, automation-state, and peer-trace surfaces.
- Learning and promotion are split across `services/learning_analysis.py`, `services/learning_impact.py`, `services/workflow_experiments.py`, `services/workflow_promotion.py`, `services/learning_taxonomy.py`, and closeout-written `workflow_learning_events`.

The harness is not greenfield and should not be replaced. Phase 16 should bind existing state, evidence, verifier, context, and learning surfaces more tightly.

## 2. Current Source-Of-Truth Map

| Question | Current source of truth | Implementation location | Current strength | Gap |
| --- | --- | --- | --- | --- |
| Task objective | `orchestration_runs.objective`, `sessions.objective`, `briefing_packets.objective`, prompt text in `prompts_used` | `services/aios_cli.py`, `bin/hook-session-start.py`, `bin/hook-prompt-submit.py`, `bin/aios-managed-run.py` | Durable when using `start-work` or managed runtime | Manual hook sessions can close without linked `orchestration_runs`; stop hook warns rather than blocks. |
| Current phase/plan | `.planning/STATE.md`, phase plan files, GSD summaries | GSD planning files and tools | Durable file truth | Not linked to `orchestration_runs` unless the objective carries it; phase transition remains outside AIOS runtime state. |
| Phase owner/agent | `orchestration_runs.agent_key`, `orchestration_invocations.backend_key`, workflow report surface | `services/aios_cli.py`, `bin/aios-managed-run.py`, `services/task_routing.py` | Agent/backend are explicit for governed runs | Model tier/reasoning choice is defined in config but not always logged per live run. |
| Context received | `briefing_packets`, `aios/context/compiled/latest.*`, `aios/context/receipts/latest.*`, `tmcp_traversal_receipts.packet_json`, session packet files under `~/AIOS/logs` | `tools/context-compile.mjs`, `services/tmcp_runtime.py`, `bin/hook-session-start.py`, `services/harness.py` | Context compiler and TMCP receipts are strong | Prompt-time retrieval stores only `retrieval_source`; exact injected snippets/candidate scores are not durable. |
| Commands run | `artifacts.metadata_json` for Bash candidates, `rtk_compression_events`, some `tool_events`, test command events in harness fixtures | `bin/hook-post-tool-use.py`, `bin/hook-stop.py`, `services/harness.py` | Commands can be reconstructed for some sessions | Raw stdout/stderr paths or hashes are not consistently bound to completion markers. |
| Evidence produced | `artifacts`, `workflow_execution_reports`, `success_criteria_evaluations`, `success_criteria_findings`, `success_criteria_stage_findings`, `standards_health_snapshots`, `session_effectiveness_receipts`, TMCP receipts | Managed runtime, stop hook, success criteria service, standards health, RTK integration | Broad durable coverage | Evidence freshness and command output integrity are not enforced before completion. |
| Verification result | Workflow report `status`, success criteria pass/warning/blocker counts, harness eval scores, eval run scores, shadow deltas | `services/workflow_orchestration.py`, `services/success_criteria.py`, `services/harness_eval.py`, `services/eval_run_service.py`, `services/shadow_branch_runner.py` | Multiple verification surfaces exist | No mandatory independent verifier artifact for implementation-bearing closeout yet. |
| Changes made after the run | Git status at stop, artifacts, memory updates, writebacks, summary JSON | `bin/hook-stop.py`, `bin/hook-post-tool-use.py` | Dirty worktree blocker exists in success criteria | Diff or commit hash is not first-class on every completion artifact. |
| Learnings proposed for future runs | `memory_updates`, `improvement_writebacks`, `workflow_learning_events`, learning pattern detectors, promotion lifecycle items | `bin/hook-stop.py`, `services/learning_analysis.py`, `services/learning_impact.py`, `services/workflow_promotion.py` | Conservative and approval-oriented | Repeated failures do not automatically create a typed retrospective artifact tied to verifier/evidence results. |

## 3. Lifecycle Phase Comparison Table

| Lifecycle phase | Existing equivalent | Implementation location | Transition logic | Completion artifact | Failure mode | Minimal patch |
| --- | --- | --- | --- | --- | --- | --- |
| Intake | `aios start-work`, hook SessionStart, prompt submit capture | `services/aios_cli.py`, `bin/hook-session-start.py`, `bin/hook-prompt-submit.py`, `services/task_routing.py` | Deterministic project/workflow routing, but manual sessions may start outside run linkage | `orchestration_runs`, `sessions`, `prompts_used`, `tool_events` | Unsupported/ambiguous projects block routing; manual sessions can still proceed outside governed run | Require or explicitly exempt run linkage for governed implementation tasks. |
| Context routing | Context compiler, TMCP packet, session packet, prompt retrieval | `tools/context-compile.mjs`, `services/tmcp_runtime.py`, `services/context_compiler.py`, hooks | Mostly deterministic scoring and graph selection; prompt retrieval is policy-driven keyword logic | context receipt files, `tmcp_traversal_receipts`, `briefing_packets` | Prompt-time injected context lacks selected/skipped candidate trace | Add durable context routing manifest for all runtime retrieval, including no-second-brain fallback. |
| Planning | GSD phase plans and workflow registry stages | `.planning/**`, `config/workflows/registry.json`, `services/workflow_orchestration.py` | GSD plan advancement is file/tool-driven; workflow stages are registry-driven | plan files, workflow stage specs | Phase state is not always connected to run records | Store plan/phase ids on governed run metadata when available. |
| Implementation | Managed workflow stage execution and normal agent edits | `bin/aios-managed-run.py`, `services/workflow_orchestration.py`, hooks | Workflow stages are deterministic; actual code changes are performed by agent/tooling | workflow reports, artifacts, tool events | Skill execution can summarize actions without raw command evidence | Bind implementation run records to diff/commit hashes and command evidence artifacts. |
| Verification | Workflow validate stage, success criteria, quality gates, harness replay/eval | `services/workflow_orchestration.py`, `services/success_criteria.py`, `services/quality_gates.py`, `services/harness.py`, `services/harness_eval.py` | Deterministic checks exist; many are advisory/warn-only depending on trigger | success criteria JSON, stage findings, harness/eval scores | Implementer-authored "tests passed" can still be stronger than captured raw evidence in some paths | Require fresh evidence rows with command, exit code, output path/hash, parsed summary, status, caveats. |
| Review | Code review is mostly external; eval/shadow can review outcomes | eval services, shadow services, PR workflow outside AIOS | Not structurally independent for normal governed closeout | eval scores, shadow comparison reports when used | No mandatory independent verifier for implementation-bearing tasks | Add verifier artifact gate before closeout for governed implementation workflows. |
| Closeout | Stop hook governed closeout | `bin/hook-stop.py` | Deterministic session close and criteria/standards evaluation | summary JSON, memory update, closeout report, success criteria and standards rows | Stop hook can record warnings but still close session; completion claim may happen before hook closeout result is inspected | Make closeout consume verifier/evidence bundle and expose pass/fail/needs-work route. |
| Retrospective/learning | Closeout learning signal, learning analysis, workflow promotion | `bin/hook-stop.py`, `services/learning_analysis.py`, `services/learning_impact.py`, `services/workflow_promotion.py` | Conservative, approval-gated proposals | `workflow_learning_events`, `improvement_writebacks`, promotion lifecycle items | Signals are fragmented and not always tied to verifier failure classes | Add structured retrospective artifact per substantial governed run. |

## 4. What Already Overlaps With Case

This audit treats Case as inspiration, not a blueprint. AIOS already overlaps with the strongest Case ideas in several places:

- Durable state over conversation-only workflow: `orchestration_runs`, `orchestration_run_events`, `orchestration_invocations`, `briefing_packets`, `workflow_execution_reports`, `tmcp_traversal_receipts`, `success_criteria_evaluations`, `memory_updates`, and eval/shadow tables.
- Deterministic phase/control surfaces: `transition_run` restricts run statuses; workflow/skill registries define stages and validations; context compiler scoring is deterministic; TMCP packet selection is deterministic and fingerprinted.
- Evidence orientation: stop hook records success criteria, standards health, session effectiveness, RTK metrics, artifacts, memory updates, writebacks, and closeout summaries.
- Independent evaluation primitives: harness eval, eval run records, second-brain lift, peer traces, shadow branch runs, ablations, and external benchmark adapters already exist.
- Routed context instead of context dumping: `tools/context-compile.mjs`, `services/context_compiler.py`, `services/tmcp_runtime.py`, `services/task_routing.py`, and hook retrieval policy all select context by rules or graph rather than loading everything.
- Conservative learning: `improvement_writebacks` and workflow promotion require approval for default-changing changes; learning analysis detects repeated failures instead of silently mutating defaults.
- Intent-specific instruction loading: TMCP packets and global skills keep route-specific instructions out of always-loaded agent files.

## 5. Case-Overlap Summary

AIOS is strongest where state is already structured: run lifecycle, context receipts, success criteria, standards health, eval runs, and shadow records. It is weakest where proof still depends on agent narrative: raw command output, verification independence, prompt-time retrieval traces, model choice telemetry, and retrospective failure classification. The right Phase 16 shape is not a second harness; it is a binding layer that makes existing records harder to fake and easier to replay.

## 6. Top 5 Gaps

1. **Completion is not always bound to hard command evidence.** `bin/hook-stop.py` assembles execution evidence from artifact metadata, RTK rows, tool events, and workflow reports, but completion gates do not consistently require timestamped command, exit code, stdout/stderr path or hash, parsed summary, diff/commit hash, status, and caveats.
2. **Independent verification is optional.** `services/harness.py`, `services/harness_eval.py`, eval runs, and shadow workflows provide review mechanisms, but governed implementation closeout does not yet require a verifier artifact that reviews spec, diff, and evidence.
3. **Prompt-time retrieval trace is too thin.** `bin/hook-prompt-submit.py` can inject prompt templates, bugs, archive notes, handoff decisions, wiki snippets, rules, and GitNexus hints, but `prompts_used` records only `retrieval_fired` and `retrieval_source`.
4. **Model and reasoning telemetry is incomplete per run.** `config/execution-strategies/model-routing-policy.json` defines expected telemetry, and `services/execution_strategy.py` validates the policy, but managed run reports do not consistently persist model tier, reasoning level, fallback, tokens/cost, latency, and selection reason.
5. **Retrospectives are fragmented.** Closeout learning events, memory updates, improvement writebacks, learning analysis, and workflow promotion exist, but no single retrospective artifact ties failure class, verifier result, evidence paths, proposed rule/check/playbook/benchmark/memory updates, and approval status together.

## 7. Top 5 Risks If Unchanged

1. Agents can still claim completion from summarized assertions when raw command evidence is missing or stale.
2. Verification failures can be missed because the implementer is also the primary verifier in the common path.
3. Context misses are hard to learn from because prompt-time retrieval omissions and candidate scores are not durable.
4. Model-routing improvements will be speculative because actual model/reasoning/cost/outcome telemetry is incomplete.
5. Harness improvements may sprawl into more always-loaded instructions instead of compact intent-specific pointers, increasing context cost and weakening TMCP's purpose.

## 8. Proposed Targeted Deltas

1. Add a durable evidence bundle schema and service that records command evidence with task/run/session/invocation ids, timestamp, command argv/string, cwd, exit code, stdout/stderr path or hash, parsed summary, diff/commit hash, status, caveats, and producing tool. Patch `bin/hook-post-tool-use.py`, `bin/hook-stop.py`, `services/workflow_orchestration.py`, and `services/success_criteria.py` to consume it.
2. Add an independent verifier artifact for implementation-bearing governed workflows. It should review task spec, changed files or diff/commit, evidence bundle rows, success criteria findings, and workflow report, then emit `pass`, `fail`, or `needs_human_review`.
3. Add a context routing manifest for runtime retrieval. It should cover selected and skipped sources, reasons, second-brain availability, fallback behavior, estimated budget, retrieval reasons, and injected-context hash for both context compiler/TMCP and prompt-time hooks.
4. Tighten prompt/template boundary by moving deterministic gates out of prose where a code/config gate already exists. Keep agent files thin: always-loaded files should point to intent-specific routes, TMCP nodes, or skill names instead of embedding phase-specific instructions.
5. Add per-run model-selection telemetry using the existing model routing policy schema: phase/task type, role, model, reasoning level, reason, fallback, tokens/cost when available, latency, outcome, and verifier result.
6. Add a retrospective artifact emitted after substantial governed runs. It should classify failures using the eval taxonomy, link evidence/verifier records, propose reviewable rule/check/playbook/benchmark/memory updates, and never silently mutate defaults.
7. Add shadow parity metadata only where the current shadow tables are weak: baseline/AIOS branch/run ids, start SHA, context profile, parity checklist, contamination status, comparison report path, failure class, replay command, and caveats.

## 9. Files Likely To Edit

- `schema.sql`: add evidence bundle, verifier artifact, context routing manifest, model-selection log, retrospective artifact, or shadow parity metadata tables/columns.
- `bin/aios_orchestration_runtime.py`: central runtime schema helper and transition/linkage helpers.
- `bin/aios-managed-run.py`: managed-run evidence, TMCP, workflow report, invocation report, model telemetry, and closeout linkage.
- `bin/hook-post-tool-use.py`: raw command/tool evidence capture and output hashing/path persistence.
- `bin/hook-stop.py`: closeout gate consumption of evidence bundles, verifier artifacts, context manifests, retrospectives, and clean completion status.
- `bin/hook-prompt-submit.py`: prompt-time retrieval manifest capture.
- `bin/hook-session-start.py`: context manifest attachment for session packets and second-brain fallback.
- `services/workflow_orchestration.py`: stage evidence binding, validation stage output, and prompt-boundary tightening.
- `services/success_criteria.py`: completion criteria that reject stale/empty evidence and require verifier artifacts when triggered.
- `services/harness.py`: replay/shadow compatibility with new evidence/verifier artifacts.
- `services/eval_run_service.py`, `services/second_brain_eval.py`, `services/shadow_branch_runner.py`, `services/shadow_automation.py`: metadata parity and evaluator linkage.
- `services/execution_strategy.py` and `config/execution-strategies/model-routing-policy.json`: model-selection telemetry validation and routing policy conformance.
- `tools/context-compile.mjs`: context routing manifest compatibility if existing receipt shape is extended.
- `config/workflows/registry.json`, `config/workflows/skills.json`, `prompts/registry.json`: prompt/template boundary metadata and stage gate contracts.
- Focused tests under `tests/` and `tests/context/` matching the changed surfaces.

## 10. Files That Should Not Be Touched

- Do not rewrite `PROJECT.md` for the audit-only plan unless later implementation changes shipped behavior.
- Do not expand `AGENTS.md` or `config/agent-rules.md` with large Phase 16 procedure text. If a global rule is missing, add a thin pointer to an intent-specific skill/TMCP route in a later plan.
- Do not replace the GSD planning system or `.planning/**` phase contracts; Phase 16 should consume them.
- Do not replace the existing SQLite runtime spine with a new database or external service.
- Do not replace `tools/context-compile.mjs`, `services/context_compiler.py`, or `services/tmcp_runtime.py` with a new context framework.
- Do not rewrite the UI or operator surfaces for Plan 16-01.
- Do not mutate personal corpus, Obsidian vault content, or historical eval data as part of this audit.

## 11. Changes Explicitly Rejected As Too Invasive

- Creating a parallel Case clone or new top-level harness runtime.
- Moving all workflow state into conversation prompts or always-loaded agent files.
- Loading every standards, skill, or context file by default to avoid routing work.
- Replacing TMCP with one monolithic skill prompt.
- Requiring live LLM judges for every closeout before the deterministic evidence/verifier substrate exists.
- Replacing SQLite with a remote service for evidence or run state.
- Rewriting all hooks to a provider-neutral framework before evidence and verifier binding are fixed.
- Auto-promoting new rules, standards, or prompt defaults from retrospective output without review.

## 12. Implementation Plan Ordered By Leverage

1. **Evidence chain hardening.** Add the evidence bundle schema/service and make success criteria reject missing, stale, or agent-authored-only evidence for triggered completion paths. This directly supports HARN-03 and later verifier work.
2. **Independent verifier gate.** Add a verifier artifact and closeout requirement for implementation-bearing governed workflows. Route verifier failures to retry or human review. This supports HARN-04.
3. **Context routing manifest.** Extend prompt-time and session-start retrieval to durable selected/skipped/fallback manifests while preserving the existing context compiler and TMCP receipts. This supports HARN-05.
4. **Prompt/template boundary tightening.** Audit workflow/prompt registries for prose-only phase gates and move the easiest gate into code/config. Keep agent files thin and route-specific. This supports HARN-06.
5. **Model-selection and retrospective instrumentation.** Persist per-run model/reasoning selection telemetry and a structured retrospective artifact linked to verifier/evidence results. This supports HARN-07.
6. **Shadow parity metadata.** Strengthen existing shadow branch tables/reports with parity checklist, replay instructions, failure classes, and caveats. This supports HARN-08.

## 13. Known WIP Or Stale Map Corrections

- Phase 16 research mentions `services/workflow_learning.py`, but the current repo has no such file. Learning is split across `services/learning_analysis.py`, `services/learning_impact.py`, `services/workflow_experiments.py`, `services/workflow_promotion.py`, closeout `workflow_learning_events`, and `services/learning_taxonomy.py`.
- `services/harness.py` has active harness readiness explicitly disabled via `active_harness_ready: False`, so active enforcement should not be assumed.
- `services/cts/flows.py` is known WIP from the Phase 12 memory audit; flow-level retrieval should not be treated as available.
- CTS semantic search is currently FTS/LIKE-shaped, not embedding-backed, per the Phase 12 audit.
- Prompt-time retrieval is useful but lacks durable candidate trace and should not be treated as equivalent to the context compiler receipt.

## 14. Plan 16-01 Contract Coverage Check

- Harness entrypoints mapped: `bin/aios.py`, `services/aios_cli.py`, `bin/aios-managed-run.py`, `bin/aios_orchestration_runtime.py`, hooks.
- Orchestration logic mapped: `services/workflow_orchestration.py`, `services/task_routing.py`, `services/invocation_backends.py`.
- Lifecycle state mapped: `orchestration_runs`, `orchestration_invocations`, `orchestration_run_events`, `sessions`, `workflow_execution_reports`.
- Prompt/template system mapped: `prompts/registry.json`, `config/workflows/registry.json`, `config/workflows/skills.json`, hook prompt retrieval, workflow prompt bindings.
- Model selection mapped: `services/execution_strategy.py`, `config/execution-strategies/model-routing-policy.json`, workflow reports.
- Context routing and second-brain integration mapped: `tools/context-compile.mjs`, `services/context_compiler.py`, `services/tmcp_runtime.py`, hooks, `services/second_brain_eval.py`.
- Evaluation, evidence, and verification mapped: `services/success_criteria.py`, `services/harness.py`, `services/harness_eval.py`, `services/eval_run_service.py`, hooks, RTK/artifacts.
- Recovery, shadow branches, retrospectives, docs/scripts/CI checks, and WIP areas mapped with concrete files and minimal patches.
