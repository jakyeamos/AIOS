# AIOS Project Truth

Last updated: 2026-05-19

## What AIOS Is

AIOS is the local operating system for work context, agent workflows, and durable project memory.
It is the orchestration layer for agents across all linked development projects, not just a dashboard or standards system for this repository. It is intended to unify:

- structured knowledge pages
- grounded retrieval and query surfaces
- workflow and orchestration state
- task-specific delegation packets
- durable continuity across long-running sessions

## Current Reality

The repository currently contains four meaningful subsystems:

1. `aios-ui/`
   A Next.js local dashboard over `~/AIOS/data/aios.db`. It is strongest at session/run observability.

2. `bin/` and `services/`
   Python hooks, importers, storage maintenance tools, and the CTS prototype.

3. `docs/`
   Design intent for storage, knowledge, CTS, and the current UI, but not yet a single implemented architecture.

4. `aios/context/`
   The file-backed AIOS Context Compiler: tiered Markdown routing manifests, deterministic task compilation, generated briefings, and context receipts.

Root operator documentation now lives in `README.md`, including local UI launch commands, key UI routes, store paths, workflow proposal backfill, and verification commands.

## Current Product Boundary

Shipped AIOS behavior today is primarily:

- session logging
- prompt logging
- artifact logging
- bug capture
- pattern extraction
- lightweight startup retrieval
- dashboard-style visibility into runs, prompts, projects, and costs
- CLI-started routed work packets for serious agent sessions

AIOS is now partially usable as a preflight and routing layer for selected work, but it is not yet the default launcher for every agent session.

## Target Architecture Direction

AIOS must separate and expose these layers explicitly:

1. Durable knowledge
2. Project memory
3. Live workflow/orchestration state
4. Briefing packet generation
5. Grounded retrieval/query logic
6. Inspectability for routing, retrieval, assumptions, and changes

## This Pass

This implementation pass establishes:

- an audit artifact documenting the gap to the target system
- first-class control-plane schema and modules inside `aios-ui`
- knowledge-oriented information architecture instead of dashboard-only navigation
- grounded query and inspectable retrieval surfaces
- orchestration run logging and briefing packet generation
- ADR support and handoff documentation for continuation
- post-run memory updates written into dedicated control-plane state
- explicit run/session handshake and invocation records
- event-driven lifecycle transitions with durable history
- approval review surfaces for gated writebacks
- structured evaluator outputs for contradiction, drift, and stale-truth detection
- a real managed invocation backend path tied to the workflow/agent registry

## Implemented On 2026-05-14

AIOS tiered context standards now make machine readability a top-level precedence rule:

- `aios/context/standards/global.maintainability.md` requires instructions, packets, errors, logs, schemas, receipts, and status surfaces to preserve parseable structure, stable identifiers, explicit states, deterministic labels, and actionable remediation fields before human-friendly presentation
- `aios/context/domains/agent-harnesses.md` narrows the rule for packets, prompts, workflows, states, IDs, and remediation steps
- human-readable text remains allowed as clarification, but must not replace, obscure, or contradict machine-readable data

## Implemented On 2026-05-16

AIOS agent rules in `config/agent-rules.md` are now part of runtime behavior:

- session start packets inject the parsed agent-rule summary before learned active rules
- context compilation treats `config/agent-rules.md` as an immutable global context source and records it in receipts
- workflow execution loads the same rules into normalized prompts and report artifacts
- installed skill sync now preserves `source_path` and `installed_name` metadata so workflow skill reports can trace synced skills back to their installed `SKILL.md`

## Implemented On 2026-05-17

AIOS now treats orchestrated sub-agent development as the default strategy for most non-trivial work:

- `config/agent-rules.md` and `AGENTS.md` define the durable rule, including direct-execution exceptions for tiny local work
- `config/execution-strategies/model-routing-policy.json` records the configurable routing table for direct execution, subagent preference signals, agent roles, model tiers, reasoning levels, telemetry fields, benchmark classes, marginal-value learning, and promotion statuses
- `services/execution_strategy.py` and `bin/validate-execution-strategies.py` validate the routing policy alongside the existing execution-strategy catalog
- `docs/workflows/orchestrated-subagent-development.md` documents the workflow, eval plan, and follow-up implementation path for persistent telemetry and approval-gated policy updates
- `docs/evals/aios-harness-eval-v0.md` now includes the model-routing eval extension for learning cheapest reliable model/reasoning defaults over time

AIOS now has a first-class service-layer route contract for serious-work intent:

- `services/project_inventory.py` can now list registered projects across sparse or full project schemas and rank candidate projects from objective text, working-directory evidence, and explicit project overrides
- `services/task_routing.py` turns a vague objective into a machine-readable route result with project outcome (`exact`, `likely`, `ambiguous`, or `unsupported`), selected workflow, nearby workflow alternatives, prompt-family recommendation, backend recommendation, and blocked-reason semantics
- `tests/test_project_inventory.py` and `tests/test_task_routing.py` now lock exact-match, ambiguity, unsupported, implementation-route, failure-recovery-route, audit-route, and prompt-fallback behavior
- this establishes the route contract for Phase 1, but `aios start-work` still needs to adopt and persist it before AIOS can claim routed serious work flows through the main entrypoint by default

AIOS `start-work` now uses and persists the Phase 1 route contract:

- `services/aios_cli.py` now routes serious-work objectives before packet creation, deriving project/workflow/agent/backend defaults from the route layer while still allowing explicit overrides
- blocked project outcomes now stop `start-work` before run or packet creation, returning an explicit `route-blocked` CLI error instead of silently guessing
- `orchestration_runs` and `briefing_packets` now persist `route_id` plus machine-readable route metadata so later packet/query/operator surfaces can inspect routing decisions without recomputing them
- `tests/test_aios_cli.py` and `tests/test_orchestration_runtime.py` now cover route-aware packet creation, persisted route metadata, and ambiguity blocking in the main control-plane entrypoint

AIOS now has a shared route-aware packet contract across the CLI and UI/runtime packet surfaces:

- `aios-ui/lib/control-plane.ts` now models `routeId`, `routeResult`, and route-aware run metadata in the shared control-plane types
- `aios-ui/server/aios/schema.ts` now keeps UI/runtime schema upkeep aligned with the route-aware `orchestration_runs` and `briefing_packets` columns already present in `schema.sql` and `services/aios_cli.py`
- `aios-ui/server/aios/control-plane.ts` now reads and writes route-aware packet/run metadata instead of assuming the older packet-only shape
- `aios-ui/server/aios/packet-assembly.ts` now emits packet objects that conform to the shared route-aware packet contract, even when routing data is not yet attached in the UI-created path
- this closes the Phase 2 storage/reader drift between CLI and UI packet surfaces, but compiler/query provenance convergence and final governed handoff composition still remain

AIOS context compilation and grounded query now share packet-compatible provenance semantics:

- `tools/context-compile.mjs` now emits `retrieval_trace` and `packet_contract` metadata in the compiler payload and durable receipt JSON so context selection can flow into packet and query surfaces without translation loss
- `tests/context-compiler.test.mjs` now locks the packet-compatible provenance contract, including deterministic selection policy, route compatibility, loaded-context counts, and populated retrieval reasons
- `aios-ui/server/aios/query.ts` now loads the latest persisted packet provenance for a project and folds it into grounded `project_state` and `agent_brief` answers instead of relying only on adjacent dossier/topic traces
- grounded-query retrieval traces can now cite the latest briefing packet with objective, top context, and route-summary evidence, making compiler output and operator answers tell one provenance story
- this closes the main Phase 2 provenance gap between compiler receipts and query answers, but the final governed handoff packet still needs explicit workflow instructions, checks, and acceptance criteria

AIOS serious-work packets now use a governed handoff contract instead of a generic context summary:

- `services/aios_cli.py` now builds `start-work` packets with explicit workflow stages, routed prompt-family guidance, required checks, escalation rules, and closeout/writeback instructions
- the CLI packet response now returns the governed section structure directly and persists packet-contract metadata alongside the routed retrieval trace
- `tests/test_aios_cli.py` now locks the new packet contract, including section presence and persisted `governed-handoff-v1` metadata
- `aios-ui/server/aios/packet-assembly.ts` now composes the same contract shape for control-plane planned packets so UI-created work packets are also execution-oriented
- `aios-ui/server/aios/control-plane.ts` now records the packet contract version in the ready-state reason metadata for planned UI runs
- this closes Phase 2 with an agent-ready packet contract that combines context, workflow, prompt, checks, and governed closeout expectations in one default serious-work handoff

AIOS run lifecycle semantics now distinguish nuanced terminal outcomes instead of overloading clean completion:

- `bin/aios_orchestration_runtime.py` now recognizes `partial` and `needs_follow_up` as first-class runtime statuses and stamps closeout time for those terminal-but-incomplete outcomes
- `services/aios_cli.py` now treats `partial` and `needs_follow_up` as canonical lifecycle states, includes them in audit attention visibility, and reports them as supported terminal outcomes instead of unsupported noise
- `tests/test_orchestration_runtime.py` now locks partial closeout transitions and persisted reason metadata
- `tests/test_aios_cli.py` now verifies lifecycle audits include the widened attention/terminal contract and still isolate truly unsupported states
- this opens Phase 3 with a stronger lifecycle vocabulary for partial completion and follow-up debt before resume snapshots and closeout summaries are added

AIOS now persists explicit resume snapshots for serious runs:

- `bin/aios_orchestration_runtime.py` now stores and loads `resume_snapshot_json` on `orchestration_runs`, giving each resumable run a durable packet id, current stage, next recommended action, pending approval count, and approval targets
- `schema.sql` and `services/aios_cli.py` now keep the resume snapshot field in the canonical schema and in the `start-work` bootstrapping path
- `aios start-work` now seeds a `packet_ready` resume snapshot so serious work is resumable immediately after handoff creation
- `services/aios_cli.py status` now exposes resumable runs directly instead of forcing manual event reconstruction
- `bin/hook-session-start.py` now upgrades linked run snapshots to `execution_active` on session launch and surfaces the resume snapshot in the startup packet for resumed serious work
- `tests/test_orchestration_runtime.py`, `tests/test_aios_cli.py`, and `tests/test_agent_rules_runtime.py` now lock runtime persistence, status visibility, start-work seeding, and session-start packet injection for the resume contract
- this closes the main Phase 3 resume gap: AIOS can now preserve packet identity, stage, next action, and approval context without replaying raw run history

AIOS now persists governed closeout evidence for serious runs:

- `bin/hook-stop.py` now compiles a governed closeout summary after runtime completion, combining changed artifacts, checks run, pending approvals, unresolved deltas, and writeback implications in one persisted payload
- `bin/aios_orchestration_runtime.py` now allows workflow execution reports to attach closeout summaries even when only a run-level linkage is available
- `services/aios_cli.py status` now exposes recent governed closeouts so operators can inspect serious-run outcomes without manually joining workflow reports, writebacks, criteria evaluations, and memory updates
- `tests/test_orchestration_runtime.py` now verifies explicit-handshake stop closes with a persisted governed closeout report
- `tests/test_aios_cli.py` now verifies recent closeout visibility through the status payload
- this closes Phase 3 with a default serious-work execution contract that covers routing, packets, lifecycle nuance, resumable state, and governed closeout evidence

AIOS now has a first reusable personalized humanizer skill:

- `skills/personalized-humanizer/SKILL.md` defines the local skill contract for voice matching, context modes, privacy boundaries, debug/audit output, and feedback-gated learning
- `config/personalized-humanizer/profile.json` stores the versioned personal voice profile with global voice rules, mode-specific profiles, anti-style rules, confidence, and provenance
- `services/personalized_humanizer.py` implements task classification, bounded corpus example selection, compact voice packet generation, conservative rewriting, quality scorecards, feedback capture, candidate profile updates, and eval execution
- `config/workflows/registry.json` and `config/workflows/skills.json` expose the `personalized-humanizer` workflow and its staged skills for AIOS workflow routing
- `schema.sql` includes durable tables for personalized humanizer runs, feedback, candidate profile updates, and eval results
- `docs/architecture/personalized-humanizer.md` documents usage, retrieval, profile versioning, feedback promotion, evals, privacy boundaries, and debug inspection
- `tests/test_personalized_humanizer.py` covers the five required writing modes, mode-boundary retrieval, privacy-preserving provenance, prompt structure preservation, feedback proposal gating, eval cases, and workflow execution

AIOS personalized humanizer now has an explicit optional pipeline-step contract:

- `services/personalized_humanizer.py` supports `pipeline_position="standalone"` for the existing conservative cleanup-plus-voice path and `pipeline_position="after_generic_humanizer"` for a voice-specific pass after the generic humanizer
- debug output and durable run metadata now record the selected pipeline position and contract so agents can inspect whether a run owned generic cleanup or only personal voice adaptation
- `skills/personalized-humanizer/SKILL.md`, `config/workflows/skills.json`, and `docs/architecture/personalized-humanizer.md` now describe the intended composition: generic humanizer first for broad AI-writing cleanup, personalized humanizer second only when the user wants the result closer to their voice
- `tests/test_personalized_humanizer.py` covers the post-generic voice pass, explicit invalid pipeline-position failures, and the existing standalone behavior

AIOS now has an `agentize` intent compiler skill:

- `services/agentize.py` defines the `AgentizedTaskPacket` schema and deterministic request transformation pipeline for task classification, execution mode selection, targeted context planning, standards attachment, success criteria attachment, verification planning, output contracts, and prompt-pattern evidence
- `skills/agentize/SKILL.md` documents the reusable skill contract and reframes prompt templates as supporting evidence instead of the primary routing abstraction
- `config/workflows/registry.json` and `config/workflows/skills.json` register the `agentize` workflow and `agentize_intent_compiler` skill for AIOS workflow routing
- `schema.sql` and `data/schema.sql` add `agentize_evaluations` so outcome quality, tests, user correction, follow-up rate, and major-repair signals can improve packet generation over time
- `docs/architecture/agentize-skill.md` records the audit, architecture decision, packet contract, evaluation loop, compatibility notes, and migration plan
- `prompts/README.md` now describes the prompt library as a pattern/evidence corpus that `agentize` can use without requiring static request-to-template mapping
- `tests/test_agentize.py` covers packet structure, classification, execution-mode selection, context planning, standards attachment, verification planning, prompt-library demotion, evaluation logging, and workflow/skill registry binding

AIOS vault-root resolution is now centralized:

- `services/path_resolution.py` owns the vault root contract for Python services, preserving explicit overrides and `AIOS_VAULT_ROOT`
- `bin/aios_paths.py` wraps that resolver for script imports and shell use
- health checks, maintenance, import, sync, and ingest scripts no longer carry independent `~/projects/Vaults/Command-Center` or legacy `~/Vaults/Command-Center` defaults
- `bin/health_check.sh` creates the dashboard directory before writing and can skip macOS notification with `AIOS_SKIP_NOTIFICATION=1` for non-interactive validation
- `tests/test_path_resolution.py` covers override behavior, canonical-vs-legacy fallback, legacy path rewriting, and the script CLI used by shell entrypoints

AIOS hook session resolution now repairs stale payload ids:

- `hook_lifecycle.resolve_hook_session_id` prefers the open `logs/current_session` pointer when a hook payload points at a different cwd or an already closed stale session
- prompt-submit, post-tool-use, and stop hooks use the shared resolver before writing prompt rows, tool events, artifacts, summaries, or closeout state
- `bin/repair-stale-open-sessions.py` provides a dry-run-first backfill that abandons old open sessions only when they have no prompts, no non-start tool events, and no runtime invocation linkage
- the live smoke session `codex-agent-rules-live-check-260516` now has a captured prompt row, closeout summary, criteria evaluation, and standards-health snapshot
- `tests/test_hook_lifecycle.py` covers stale prompt reassignment, stale stop closeout reassignment, and inactive-session backfill filtering

## Implemented On 2026-05-19

AIOS now has a governed project truth audit contract:

- `aios truth-audit --json` inspects the canonical truth file, defaults to `PROJECT.md`, and reports freshness, required operating facet coverage, review findings, recent governed closeout evidence, and resumable run evidence
- `services/aios_cli.py` defines the truth-update contract: accepted truth comes from the selected truth file, proposals come from `workflow_execution_reports.report_json` and `orchestration_runs.resume_snapshot_json`, and important updates require review
- the truth audit checks for required facets covering goals, architecture, risks, completed work, unresolved deltas, next actions, and decisions
- `tests/test_aios_cli.py` verifies the governed truth contract, proposal-source linkage, resumable evidence, closeout evidence, and missing-facet warnings
- this starts Phase 4 by making truth freshness and governed truth updates inspectable through the same JSON-first control-plane CLI used by agents

AIOS knowledge surfaces now distinguish accepted truth, proposed evidence, and inferred context assets:

- `aios-ui/lib/control-plane.ts` defines a `TruthKnowledgeBoundary` contract with accepted, proposed, and inferred authority states for agent-readable knowledge linkage
- `aios-ui/server/aios/knowledge.ts` exposes accepted truth from `PROJECT.md` and accepted decision records, proposed knowledge from workflow closeout reports and resumable run snapshots, and inferred knowledge from workflows, agent/skill profiles, prompt-library context, and research-tagged wiki pages
- `aios-ui/server/routers/knowledge.ts` adds `knowledge.truthBoundary`, giving agents one typed UI/server surface for truth-vs-proposal boundaries instead of forcing them to infer authority from page names or raw tables
- runtime closeouts and resume snapshots remain proposal evidence until reviewed; prompts, skills, workflows, and research can shape packets but cannot overwrite truth directly
- this advances Phase 4 by making truth, decisions, prompts, skills, workflows, and research explicitly linkable while preserving authority boundaries

## Implemented On 2026-05-14

AIOS now has a fixture-backed harness eval v0 contract:

- `docs/evals/aios-harness-eval-v0.md` defines the same-model/same-task/same-budget harness comparison frame and the deterministic v0 fixture/run artifact contract
- `docs/aios/harness-eval/config.json` registers five initial categories: context routing, false completion, approval gates, recovery, and writebacks
- `services/harness_eval.py` scores context precision/recall, gate accuracy, success-criteria recall, trace completeness, false-completion detection, recovery evidence, and useful writeback evidence without live model calls
- `aios harness-eval run --json` exposes the suite through the normal AIOS CLI JSON envelope
- `tests/fixtures/harness-eval/` contains baseline and AIOS-shadow sample runs for each v0 category, covered by `tests/test_harness_eval.py`

## Implemented On 2026-05-13

AIOS planning now has an explicit functionality-to-tier-one mapping layer:

- `.planning/FUNCTIONALITY_MAP.md` now maps major current and planned AIOS capabilities to:
  - concrete code surfaces
  - current implementation status
  - v1 requirements
  - roadmap phases
  - tier-one gaps
- `.planning/FUNCTIONALITY_PLAN.md` now expands that summary into detailed planning guidance for every major functionality group and the workflow library, including:
  - current state
  - tier-one target
  - detailed scope
  - implementation tracks
  - dependencies
  - exit evidence
- `.planning/WORKFLOW_MATRIX.md` now gives workflows their own first-class planning artifact with one row per current or planned workflow covering:
  - trigger conditions
  - stage contract
  - prompt family
  - required skills and validations
  - approval gates
  - artifacts
  - writebacks
  - learning signals
  - roadmap ownership
  - tier-one gaps
- `.planning/ROADMAP.md` is now expanded from a short phase summary into a fuller execution contract:
  - each phase now includes detailed scope
  - current code surfaces to evolve
  - workflow ownership
  - expected outputs
  - dependencies
  - observable success criteria
  - a phase dependency chain and explicit workflow rollout strategy are also recorded
- three deeper planning control artifacts now sit underneath the roadmap so execution can be traced more concretely:
  - `.planning/PHASE_01_SUBROADMAP.md` breaks Phase 1 into detailed routing workstreams, deliverables, dependencies, risks, and exit gates
  - `.planning/REQUIREMENTS_CODE_SURFACE_MATRIX.md` maps every v1 requirement to the concrete code/config/storage surfaces that must evolve to reach tier one
  - `.planning/TIER_ONE_ACCEPTANCE_CHECKLIST.md` defines per-phase capability gates, evidence gates, and failure conditions for default-layer readiness
- the map makes prompt-library selection, grounded query, automation observability, CTS/repository intelligence, reusable asset lifecycle, and other current/planned surfaces explicit instead of leaving them implied inside broader requirements
- `.planning/REQUIREMENTS.md` and `.planning/ROADMAP.md` were tightened so prompt-library selection and prompt/handoff composition are represented in the early execution loop:
  - Phase 1 routing now includes prompt/handoff-family selection
  - Phase 2 packet compilation now includes prompt assets and prompt/handoff instructions
  - operator answers now explicitly include reusable prompt/skill relevance
- workflow contracts are now first-class planning scope instead of being spread implicitly across routing and asset lifecycle:
  - `.planning/REQUIREMENTS.md` adds `WFLO-01` through `WFLO-04`
  - Phase 8 now covers workflow-stage contracts, prompt/skill/tool bindings, stage-level evaluation, and workflow promotion/revision/deprecation
- roadmap phase names now carry more explicit product meaning for the runtime loop:
  - Phase 1 is now `Project, Workflow, And Prompt Routing`
  - Phase 2 is now `Context, Query, And Briefing Compilation`
  - Phase 4 is now `Project Truth, Knowledge, And Grounded Query`
  - Phase 8 is now `Prompt, Skill, Workflow Contracts, And Asset Lifecycle`
  - Phase 10 is now `Operator Surfaces, Query, And Daily-Flow Visibility`
- this gives the repo a clearer planning contract for “all current or planned functionality must reach tier one through requirements and roadmap coverage,” not just broad thematic phase buckets

## Implemented On 2026-05-13

AIOS now treats the requested harness durability rules as first-class context standards:

- common error surfaces should be fixed durably at their recurrence point or captured as explicit follow-up work
- agent-facing code, packets, prompts, and workflows should stay inviting under limited context, using responsibility-based splits instead of arbitrary line-count ceilings
- errors surfaced to agents should be machine-readable and include actionable remediation steps
- the rules live in `global.maintainability`, `global.observability`, and `domains.agent-harnesses` so future context compiler receipts can load them for relevant work

## Implemented On 2026-05-14

AIOS now has the first backend-neutral agent harness test ladder slice:

- `aios harness-brief --json` combines deterministic context compiler packet selection with success-criteria preview for a task before any live agent run
- `aios harness-simulate --json` replays fake-agent fixture events into the existing orchestration run/event/briefing tables and refuses to mark claimed completion complete when tests or gates fail
- `aios harness-replay --json` converts stored sessions, tool events, and artifacts into stable harness events for deterministic post-hoc evaluation
- `aios harness-shadow-evaluate --json` evaluates an existing or latest session in read-only shadow mode without blocking tools, creating writebacks, or launching an agent
- active harness enforcement remains explicitly disabled behind `aios harness-active-readiness --json` until fake lifecycle, replay, shadow, approval, and writeback evidence gates are satisfied
- the runtime lifecycle vocabulary now accepts blocked, waiting-for-user, waiting-for-tool, and failed-validation states for harness and control-plane tests
- the harness CLI import surface is lint-clean under the existing Ruff import ordering gate

AIOS now has a fixture-backed harness eval v0 contract:

- `docs/evals/aios-harness-eval-v0.md` defines the same-model/same-task/same-budget harness comparison frame and the deterministic v0 fixture/run artifact contract
- `docs/aios/harness-eval/config.json` registers five initial categories: context routing, false completion, approval gates, recovery, and writebacks
- `services/harness_eval.py` scores context precision/recall, gate accuracy, success-criteria recall, trace completeness, false-completion detection, recovery evidence, and useful writeback evidence without live model calls
- `aios harness-eval run --json` exposes the suite through the normal AIOS CLI JSON envelope
- `tests/fixtures/harness-eval/` contains baseline and AIOS-shadow sample runs for each v0 category, covered by `tests/test_harness_eval.py`

## Implemented On 2026-05-13

AIOS now has a first-class Pre-PR readiness gate backed by `pre-cr-suite-lsp`:

- repo-level `.pre-cr.json` config now defines the current AIOS `pre-cr` contract around Python changed-line coverage using an external temp LCOV artifact
- `uv run python bin/aios.py pre-pr-readiness` now starts the built `pre-cr-suite-lsp` server locally, runs `$/preCr/runPreCrCheck`, and returns a JSON-safe gate result
- the AIOS-specific wrapper fails fast when the current diff touches unsupported JS/TS or shell surfaces so the gate cannot silently overclaim repo-wide coverage
- `config/quality-pipeline.json` now exposes `pre_pr_readiness` as a required AIOS quality gate
- `README.md` now documents the operator command for this gate
- Stop-hook closeout now supports RTK metrics aggregation on the default SQLite tuple row factory used by `bin/hook-stop.py`; the May 12 post-standards-snapshot crash path now records the Stop event after RTK logging instead of failing with tuple string-index access.

## Implemented On 2026-04-28

Tier-one AIOS planning now has a dedicated execution pack under `docs/superpowers/plans/tier-one-aios/`:

- `00-index.md` defines the tier-one acceptance gate and execution order
- section plans cover runtime/invocation reliability, command-center UI, knowledge/personal memory, workflow learning, project standards health, observability/telemetry, integrations/retrieval, testing/release hardening, and rollout governance
- the pack treats UI polish as the final stage after runtime, knowledge, learning, telemetry, and contract trust are proven

## Implemented On 2026-04-29

The tier-one audit fix pass has started with capability trust gates before UI polish:

- release and regression gates now lock the current audit promises for lifecycle states, canonical contracts, Prompt Library visibility, RTK explanations, readable automation schedules, workflow learning counts, and capability missing-data reasons
- UI quality CI now runs lint, the 71-warning ESLint ratchet, architecture lint, anti-slop fixture lint, and production build; Python CI now runs `uv run pytest -q`
- project health audit output now reports explicit states/subtypes such as `healthy`, `degraded`, `missing_source`, `missing_snapshot`, `unknown`, `active_with_sessions`, and `active_no_sessions`
- automation health now treats missing durable run history as unknown/inferred instead of confirmed seeded reliability
- RTK audit output now distinguishes `token_regressive` from inactive or beneficial states
- workflow learning now persists `workflow_learning_events` from writebacks, durable inferred evidence, and explicit no-learning reasons
- the live workflow-learning audit backfilled 110 terminal runs into persisted events: 96 learning events and 14 no-learning signals
- contracts audit now reports `WorkflowLearningEvent` as implemented
- knowledge objects now enforce valid kinds, report unknown kinds as audit findings, expose source refs/backlinks/freshness/confidence plus retrieval trace counts, and search across topic text plus reference labels/excerpts/source kinds
- briefing packets now persist retrieval traces with query, matched objects, omitted context count, expansion path, citations, token budget, and ranking reason
- success-criteria findings now have lifecycle/resolution metadata matching consistency findings
- the live contracts audit now reports all seven canonical contracts as implemented with zero partial contracts
- automation reliability now has a durable `automation_run_history` schema shared by Python audits and the UI schema
- automation audit and UI states now derive success rate, status, urgency, last run, next run, failure summary, approvals, and writeback blockers from run history; empty history is surfaced as unknown/watch instead of seeded health
- RTK command execution now honors the configured short-output compression threshold for successful runs, passing small outputs through as raw telemetry instead of manufacturing token-regressive compression events
- the first critical implementation target is managed runtime closeout and explicit handshake reliability
- `EXECUTION.md` now routes agents through the plan pack by priority gates, verification commands, stop conditions, parallelization rules, and final tier-one claim checklist
- Managed runtime closeout now has direct start and closeout guards in `bin/aios-managed-run.py` so hook-side evaluator failures cannot leave authoritative runs stuck in `ready`; `tests/test_orchestration_runtime.py::test_managed_runtime_completes_via_explicit_handshake` and the full Python suite now pass.
- Managed runtime closeout now has an explicit regression for authoritative closeout repair: `tests/test_orchestration_runtime.py::test_managed_closeout_repairs_authoritative_run_state` verifies a run left in `ready` is completed with the correct session, invocation, closeout event, and closed session state.
- Workflow learning audit now recognizes inferred durable evidence from workflow reports, memory updates, standards snapshots, success evaluations, and session artifacts linked through runs; the live audit moved from 110 no-learning terminal runs to 96 inferred evidence records and 14 no-learning runs.
- Priority standards-health snapshots were regenerated for AIOS, Terrace, amos-saas, portfolio, and soundscape-app using `services.standards_health.evaluate_and_record(..., trigger_kind="tier_one_priority_audit")`; the current priority scores are AIOS 64.8, Terrace 63.2, amos-saas 63.2, portfolio 72.8, and soundscape-app 63.2. GitNexus is not present in the current project inventory.
- `aios prove-project-health --json` now records repeatable tier-one standards-health proof snapshots for the six proving projects and reports missing inventory/source explicitly; the live proof recorded snapshots for AIOS 68.0, soundscape-app 63.2, Terrace 63.2, portfolio 72.8, and amos-saas 63.2, while GitNexus is `missing_source` because `/Users/jakyeamos/Projects/GitNexus` is absent.
- `aios prove-project-health --all-inventory --json` now processes every inventory row by project id, including duplicate project names; the live all-inventory proof recorded 27 standards-health snapshots and left only concrete missing-source findings for `Bball`, the duplicate `Terrace ` path with trailing whitespace, `sleeper_league_pack`, and absent configured `GitNexus`.
- `aios sync-automation-history --json` now imports durable daily pipeline evidence from `logs/pipeline.log` into `automation_run_history`; the live sync parsed 3 runs and the capability audit now reports no automation-history findings, with Daily ingest status confirmed from history as latest `healthy`, success rate 0.667, and urgency `watch`.
- RTK metrics now separate total telemetry from eligible compression telemetry using the configured compression threshold, so short pass-through outputs are counted as ineligible instead of token-regressive compression attempts; the live RTK state remains `token_regressive` because one eligible historical event is still net-regressive, while 2 of 3 events are now classified as pass-through/ineligible.
- Prompt Library visibility is now backed by the existing prompt sync path: `bin/sync-prompts.py` copied 5 prompt templates into the configured vault template directory and created 5 `prompt_library_links` rows, removing the `prompt_library_empty` finding from the live capability audit.
- RTK telemetry now distinguishes state from benefit: `aios rtk --json` and `aios capability-audit --json` report `benefit_state` values such as `beneficial`, `no_benefit`, `token_regressive`, and `no_eligible_data`; the current live RTK signal is `inactive` with `token_regressive` evidence because 3 events recorded 47 raw tokens and 110 compressed tokens.
- Tier-one audit regressions now lock the current control-plane promises in `tests/test_tier_one_regressions.py`: lifecycle audits reject unsupported states, contract audits expose seven canonical contracts, capability audits preserve prompt-library visibility, RTK explanations, readable automation schedules, and missing automation history.
- Capability truth now separates project health subtypes (`healthy`, `degraded`, `missing_source`, `missing_snapshot`, `unknown`) from broad inventory status, and project findings include source, freshness, confidence, and missing reason. Broad `active` status is qualified as `active_with_sessions`, `active_no_sessions`, or `missing_source`.
- Automation reliability no longer treats seeded health as confirmed: when `automation_run_history` is absent, automation status and success rate are `missing` with explicit missing-history reasons, readable schedules remain the primary trigger label, and urgency is reported as `watch`.
- RTK `token_regressive` is now a first-class runtime state in Python and UI types; the live RTK audit reports `state=token_regressive` and `benefit_state=token_regressive` rather than hiding the condition behind a generic inactive zero-savings state.
- Tier-one release gates now include Python CI for `uv run pytest -q`, UI CI production build, and an ESLint warning ratchet at the current 71-warning baseline via `aios-ui/scripts/assert-eslint-warning-baseline.mjs`; README quality-check docs now mirror the CI command set.

## Implemented On 2026-05-07

AIOS now has a repeatable corpus evaluation harness for product-level regression testing:

- `scripts/aios-corpus-eval.cjs` runs configured AIOS commands against disposable copied or synthetic workspaces and defaults evidence output to the system temp directory to avoid live project mutation.
- `docs/aios/corpus/config.json` defines the initial migrated, scratch-real, synthetic, dirty, and negative corpus tracks plus CLI, prompt-library, workflow, success-criteria, hook, repo-intelligence, state, and negative command suites.
- `npm run corpus:evaluate` is the project command, and `aios corpus run` / `aios corpus report` wrap the same harness through the Python CLI.
- The harness captures stdout, stderr, exit code, duration, parsed JSON, artifacts written, git status/diff summaries, classification, raw evidence paths, JSON reports, Markdown reports, dry-run plans, sample/full filters, suite/repo/mode filters, report-only regeneration, timeouts, and `--keep-worktrees`.
- Full-mode evaluation now includes explicit oracles for workflow start packets, hook DB/log side effects, CTS build/status behavior, dirty worktree detection, JSON shape, clean negative failures, and SQLite artifact persistence rather than relying on exit codes alone.
- Corpus harness checks now cover self-test behavior, suite filtering, and Python CLI passthrough in `tests/test_corpus_eval.py`.

## Implemented On 2026-05-13

AIOS now has a committed GSD codebase map for brownfield planning initialization:

- `.planning/codebase/` now exists with:
  - `STACK.md`
  - `INTEGRATIONS.md`
  - `ARCHITECTURE.md`
  - `STRUCTURE.md`
  - `CONVENTIONS.md`
  - `TESTING.md`
  - `CONCERNS.md`
- the codebase map captures the current stack, integrations, architecture, structure, conventions, testing posture, and known concerns for this repository at commit `c8817f21`
- this gives the repo a concrete GSD planning baseline before `/gsd-new-project` generates requirements, roadmap, and execution phases

## Implemented On 2026-05-12

AIOS now has the first file-backed Context Compiler:

- `aios/context/` defines thin tiered Markdown manifests for global standards, domains, project routers, feature routers, packets, handoffs, generated briefings, and receipts.
- `tools/context-compile.mjs` scans context Markdown, validates frontmatter, classifies tasks with deterministic signals, scores candidate context, follows `load_if_matched`, resolves immutable-global conflicts, reports missing/stale context, and writes latest briefing/receipt outputs.
- Root scripts now include `pnpm context:compile --task "..."`, `pnpm context:validate`, and `pnpm test:context`.
- `AGENTS.md` now includes the Context Compiler bootloader so agents load the smallest sufficient context packet instead of sweeping every Markdown file.
- `docs/context/context-compiler.md` records the audit, operating model, schema, conflict precedence, Obsidian evolution path, and UI integration follow-up.
- `aios-ui/app/context/page.tsx` now exposes the latest compiled context packet, loaded/skipped files, context inventory, conflicts, missing/stale context, writeback candidates, and the raw receipt from the file-backed compiler.

AIOS now has a branch-level Divergent Strategy Workflow experiment:

- `services/divergent_strategy.py` creates local deterministic divergent runs with task classification, role-based candidate generation, reusable judges, portfolio selection, entropy tracking, and approval-gated writeback proposals.
- New SQLite tables store `divergent_runs`, `divergent_candidates`, `divergent_judgments`, `memory_writeback_proposals`, `entropy_observations`, and `promotion_lifecycle_items`.
- Candidate and judge registries live in `config/divergent-strategy/`, and the workflow is registered as `divergent-strategy` in the AIOS workflow registry.
- UI read surfaces now expose `/runs/divergent`, `/runs/divergent/:id`, `/writebacks`, and `/skills/candidates`.
- Memory writebacks are separated into HOW, WHAT, FAILURE, and ENTROPY categories and remain proposals until approved.
- Prompt/skill/judge/workflow promotion now has a lightweight evidence-gated lifecycle: `draft -> candidate -> tested -> approved -> active -> deprecated`.
- The skill packet lives at `skills/divergent-strategy/`, with thin `SKILL.md` and tiered reference files.
- Architecture docs now cover divergent strategy, memory writebacks, prompt/skill promotion, and entropy tracking.
- The divergent strategy contract is now appended to preexisting test and experiment surfaces as `experimentation.divergent_strategy_standard`: standards registry, AIOS quality pipeline, corpus eval config, experiment test repos, and workflow skill experiment artifacts.

Stage 1 capability-truth baseline work has started with a first trusted-signal slice in `aios-ui`:

- added a shared UI/server `TrustedSignal` contract for capability metrics with:
  - provenance: `confirmed`, `inferred`, `missing`, `contradictory`
  - confidence
  - source label/table/field
  - freshness
  - explanation
  - missing reason
  - contradiction detail
- Projects now attach trusted signals to:
  - health score
  - health trend
  - critical delta count
  - unknown coverage
  - pipeline state
  - project status
- Projects no longer render the confusing health parenthetical as the primary display; health score and trend are separate visible signals.
- Pipeline badges now render an explicit configured/required label, and an `error` status with zero configured required checks is represented as a contradictory trusted signal instead of silently rendering as `0/5 ERROR`.
- Efficiency/RTK now exposes an explicit RTK state:
  - `active`
  - `inactive`
  - `no_eligible_data`
  with source-backed explanation for zero-savings states.
- Automations now infer readable schedule labels from persisted RRULE triggers and preserve the raw RRULE as secondary evidence instead of the primary trigger display.
- Automations now attach trusted signals to trigger, success rate, and status while acknowledging seeded automation health until durable run history exists.
- Projects and Automations tables now have dedicated grid layouts to avoid the screenshot-observed column wrapping/overlap.
- `aios capability-audit --json` now exposes the same Stage 1 trusted-signal contract from the CLI for core capability surfaces:
  - Projects
  - RTK
  - Automations
  - Prompt Library
  - Knowledge
- The capability audit emits source-backed/missing/inferred states and backend findings such as missing project health snapshots.
- Prompt Library audit now verifies whether `prompt_library_links` exists and whether body-hash-backed templates are actually visible.
- Knowledge audit now reports topic count, source-reference coverage, relationship count, and findings for topics without references.
- This gives later runtime, knowledge, workflow-learning, architecture, and UI phases a concrete Stage 1 gate instead of relying only on dashboard rendering.
- Grounded Query now recognizes capability/status audit questions and answers them from live SQLite counts for:
  - project health snapshot coverage
  - RTK telemetry events
  - seeded automation status
  - prompt library body-hash visibility
  - knowledge topic/reference coverage
- Stage 2 agent-runtime capability has started with an invocation backend contract:
  - added a shared backend registry in `services/invocation_backends.py` for Codex managed runtime, Claude managed runtime, and the deprecated manual-session legacy path
  - `aios invocation-audit --json` now exposes backend count, required invocation contract fields, handshake coverage, and legacy fallback policy
  - `aios start-work --backend ...` now persists the selected backend key and label instead of labeling every invocation as Codex
  - strict handshake fields are now an explicit CLI contract: run id, invocation id, backend key, objective, project id, workflow key, packet id, lifecycle events, artifacts, and closeout evaluation
  - `aios lifecycle-audit --json` now exposes the canonical run lifecycle contract, observed state counts, unsupported states, and attention-state events for blocked, waiting-for-user, waiting-for-tool, and failed-validation runs
- Stage 3 knowledge-memory capability has started with a Knowledge Object contract:
  - `aios knowledge-objects --json` adapts existing `knowledge_topics`, `knowledge_references`, and `knowledge_relationships` rows into stable objects with source refs, backlinks, freshness, and confidence
  - the command reports source-reference coverage and objects without sources so grouped topic summaries can be distinguished from citable memory
- Stage 4 workflow-learning capability has started with an evidence classification audit:
  - `aios workflow-learning-audit --json` classifies terminal runs as workflow evidence, prompt-template evidence, standards-health evidence, bug/quality evidence, or no-learning signal
  - the command reports proposal counts, approval-gated proposals, and completed/failed/canceled/superseded runs that produced no durable learning record
- Stage 5 architecture hardening has started with a canonical contract audit:
  - `aios contracts-audit --json` reports the current status and storage source for TrustedSignal, InvocationBackend, RunLifecycleEvent, KnowledgeObject, RetrievalTrace, WorkflowLearningEvent, and EvaluationFinding
  - the contract audit distinguishes implemented contracts from partial contracts so later UI work can avoid exposing unstable abstractions as finished product surfaces

This pass makes milestones 1 and 2 operational for selected work from the local CLI:

- `aios start-work "<objective>"` creates a routed work record before implementation:
  - `orchestration_runs`
  - `briefing_packets`
  - `orchestration_invocations`
  - `orchestration_run_events`
- when `logs/current_session` points at a hook-created session, `start-work` links that session through:
  - `sessions.run_id`
  - `sessions.invocation_id`
  - `sessions.runtime_metadata_json`
- the generated packet now includes:
  - objective and project context
  - applicable success criteria preview
  - active rules
  - recent improvement writebacks
  - matching indexed knowledge topics
  - an explicit routing/closeout contract
- this makes AIOS useful as a preflight and handshake layer for serious current-session work without pretending the managed runtime is already the full Codex work loop.

## Implemented On 2026-04-18

The current app now includes:

- `knowledge` routes for projects, decisions, workflows, agents, and system pages
- `control` route for workflow selection, agent registry, run history, and packet generation
- `query` route for grounded, inspectable internal answers
- dedicated control-plane schema:
  - `orchestration_runs`
  - `briefing_packets`
  - `memory_updates`
- ADR-backed decision logging in `docs/adr/`
- upgraded project dossiers with memory, rules, likely files, decisions, and recent changes
- `hook-stop.py` memory update writes on session close
- orchestration run lifecycle closure from `hook-stop.py`, including:
  - `session_id`
  - `memory_update_id`
  - `result_summary`
  - `completed_at`
- curated vault wiki ingestion into first-class `concept` knowledge pages
- derived wiki backlinks and relationship resolution inside the knowledge surface
- CTS-backed enrichment for:
  - control-plane packet generation
  - grounded query project-state answers
  - grounded query agent brief answers
  - inspectable retrieval traces

## Implemented On 2026-04-19

This pass adds the first persisted topic-graph and compact-packet vertical slice:

- persisted indexed knowledge layer:
  - `knowledge_topics`
  - `knowledge_relationships`
  - `knowledge_references`
  - `knowledge_markers`
  - `knowledge_graph_state`
- compact ranked packet delivery as the default orchestration policy
- explicit packet trace and omitted-context storage in `briefing_packets`
- traced targeted expansion logging in `packet_expansions`
- improvement writeback storage in `improvement_writebacks`
- Taski-led project operating surface on `/projects/[id]`
- topic-graph-backed retrieval in grounded query
- concept pages enriched with persisted references, relationships, and drift markers
- post-run improvement writeback proposals from `hook-stop.py`
- architecture note for the hardened retrieval policy:
  - `docs/architecture/2026-04-19-topic-graph-ranked-packets.md`

This pass also turns the execution layer into a real control-plane path:

- explicit durable handshake through:
  - `orchestration_runs.id`
  - `sessions.run_id`
  - `sessions.invocation_id`
  - `orchestration_invocations`
- first-class lifecycle and trace tables:
  - `orchestration_run_events`
  - `improvement_writeback_events`
- event-driven run statuses now written from runtime events:
  - `planned`
  - `ready`
  - `in_progress`
  - `completed`
  - `failed`
  - `canceled`
  - `superseded`
- structured run state on `orchestration_runs`:
  - `backend_key`
  - `active_invocation_id`
  - `started_at`
  - `failed_at`
  - `canceled_at`
  - `superseded_by_run_id`
  - `status_reason_json`
- approval decision persistence on `improvement_writebacks`
- structured evaluation storage:
  - `consistency_evaluations`
  - `consistency_findings`
- `/control` upgraded from packet planning only to:
  - managed run invocation
  - runtime status inspection
  - approval review
  - event timeline / evaluator trace
- Taski project surface upgraded to show:
  - structured findings
  - approval queue
  - event-driven run state
- managed backend runner in `bin/aios-managed-run.py`
- `hook-session-start.py` now moves explicitly linked runs to `in_progress`
- `hook-stop.py` now resolves the exact run by handshake first and only falls back to heuristic matching as a legacy escape hatch

## Implemented On 2026-04-23

Phase 0a architecture enforcement baseline is now live as an AIOS-managed profile system:

- AIOS registry for reusable architecture profiles:
  - `config/architecture-enforcement/profiles.json`
  - `config/architecture-enforcement/projects.json`
- new enforcement runner and CLI:
  - `services/architecture_enforcement.py`
  - `bin/architecture-enforcement.py`
- Python profile (`python-service-v1`) enforcing:
  - `services -> bin` import boundary denial
  - cycle detection for local Python modules
  - optional ruff adapter when local tooling exists
- Next.js profile (`ts-nextjs-v1`) enforcing:
  - Dependency Cruiser layer boundaries + cycle detection
  - existing ESLint/TypeScript lint checks
- proof-target wiring in `aios-ui`:
  - `.dependency-cruiser.cjs`
  - `npm run lint:architecture`
- architecture audit + rollout doc:
  - `docs/architecture/2026-04-23-aios-architecture-enforcement.md`

Phase 0b agent workflow CLI surfaces are now implemented after the hard checkpoint:

- audit package (checkpoint gate):
  - `docs/architecture/2026-04-23-aios-agent-workflow-audit.md`
- unified JSON-first command surface:
  - `bin/aios.py`
  - `services/aios_cli.py`
- implemented command family:
  - `aios status --json`
  - `aios health --json`
  - `aios metadata --json`
  - `aios logs --json`
  - `aios recent-failures --json`
  - `aios skills status --json`
  - `aios skills refresh --json [--apply]`
- standardized semantic exit-code envelope on unified surfaces:
  - usage, not-found, dependency/config, runtime
- instruction/skills refresh flow moved to declarative registry:
  - `config/instruction-registry.json`
- implementation handoff:
  - `docs/handoffs/2026-04-23-aios-agent-workflow-cli-handoff.md`

Phase 0c success criteria control-plane baseline is now live:

- criteria registry + skill mapping:
  - `config/success-criteria/registry.json`
  - `config/success-criteria/skill-map.json`
- canonical criteria docs and discovery index:
  - `spec/success-criteria/index.md`
  - `spec/success-criteria/_template.md`
  - normalized criteria docs for:
    - `code-simplicity`
    - `testing-trust`
    - `security-review`
    - `observability`
    - `truth-file-consistency`
    - `repo-boundary-discipline`
    - `workflow-state-integrity`
- runtime evaluator and artifact persistence:
  - `services/success_criteria.py`
  - `data/success-criteria/evaluations/*.json`
- hook integration:
  - `hook-session-start.py` now previews applicable criteria before implementation
  - `hook-stop.py` now evaluates changed patch paths and records criteria findings
- durable schema additions:
  - `success_criteria_evaluations`
  - `success_criteria_findings`
- metadata snapshot visibility:
  - `aios metadata --json` now exposes criteria catalog + latest evaluation
- phase architecture note:
  - `docs/architecture/2026-04-23-aios-success-criteria-system.md`

## Implemented On 2026-04-27

Execution-first verification is now mechanically represented in the success criteria system:

- new blocker-level criterion:
  - `execution-first-verification`
  - `spec/success-criteria/execution-first-verification.md`
- registry and discovery updates:
  - `config/success-criteria/registry.json`
  - `config/success-criteria/skill-map.json`
  - `spec/success-criteria/index.md`
- evaluator enforcement:
  - `services/success_criteria.py` infers runtime-risk triggers and blocks triggered changes with no execution evidence
  - `hook-stop.py` passes recorded Bash/RTK command evidence into success criteria evaluation
- repo agent contract:
  - `AGENTS.md` now includes the Execution-First Verification rule

The `aios-ui` root layout now suppresses hydration warnings on the root `<html>` element so browser-extension-injected root attributes do not surface as app hydration errors during local development.

The knowledge and topic-graph freshness labels now share one formatter. Routine 8-44 day-old records display as `Updated N days ago`; the stronger `Stale for N days` label is reserved for records 45+ days old.

Phase 1a prompt library baseline is now implemented:

- prompt template source-of-truth tree:
  - `prompts/README.md`
  - `prompts/research.md`
  - `prompts/summarization.md`
  - `prompts/coding_debug.md`
  - `prompts/content_writing.md`
  - `prompts/reasoning.md`
  - `prompts/evals/*/cases.md`
- prompt validation/index generation:
  - `bin/validate-prompts.py`
  - generated registry: `prompts/registry.json`
- vault + DB sync path:
  - `bin/sync-prompts.py`
  - updates `prompt_library_links` using body-hash linkage
- hook integration:
  - `hook-prompt-submit.py` now resolves best template by classification + tag overlap and injects compact hint context
- test coverage:
  - `tests/test_validate_prompts.py`
  - `tests/test_hook_prompt_submit.py`
  - fixture set: `tests/fixtures/prompts/*.md`
- phase architecture note:
  - `docs/architecture/2026-04-23-aios-prompt-library-phase1.md`

Prompt library visibility is now implemented in the UI:

- `/prompts` includes a first-class Prompt Library section backed by `prompts/registry.json`
- prompt template cards expose template name, classification, tags, required inputs, version, update date, and source file
- prompt templates must now be backed by `prompt_library_links` body-hash evidence before the UI or prompt-submit hook surfaces them; registry-only starter templates are hidden
- raw recent prompt history is intentionally hidden from the main `/prompts` surface
- mined prompt/pattern rows are intentionally hidden from `/prompts`; repetition alone is not evidence that a prompt is a reusable library asset
- raw prompt text is no longer written to `patterns`; prompt reuse belongs in the curated prompt library, not the general pattern/rule system

Experiment test repo visibility is now implemented:

- canonical registry:
  - `config/experiments/test-repos.json`
- local git repo workspaces:
  - `staging/experiment-test-repos/clean-small-app`
  - `staging/experiment-test-repos/messy-monorepo`
  - `staging/experiment-test-repos/backend-heavy-service`
  - `staging/experiment-test-repos/weak-tests-ui`
- `/compare` now shows the registered test repos, readiness, purpose, profile, setup, and path before experiment run history
- the local repo workspaces live under ignored `staging/` so they can be mutated during experiments without polluting the AIOS control-plane repository

Phase 1b anti-slop ESLint ratchet is now implemented on top of existing plugin wiring:

- anti-slop fixture lint lane:
  - `aios-ui/eslint/anti-slop-fixtures.config.mjs`
  - `aios-ui/eslint/fixtures/anti-slop/pass/**`
  - `npm --prefix aios-ui run lint:anti-slop:fixtures`
- architecture-enforcement profile metadata:
  - `config/architecture-enforcement/profiles.json` now includes `anti-slop-fixtures` adapter for `ts-nextjs-v1`
- CI quality wiring:
  - `.github/workflows/aios-ui-quality.yml`
  - runs `lint`, `lint:architecture`, and `lint:anti-slop:fixtures` for `aios-ui`
- ratchet docs + rollout guidance:
  - `docs/architecture/2026-04-23-anti-slop-eslint-ratchet.md`

Phase 1c improvement engine audit (audit-only) is complete:

- decision-quality audit memo:
  - `docs/architecture/2026-04-23-aios-improvement-engine-audit.md`
- scored seven capability areas against ideal target architecture:
  - scheduled experimentation infrastructure
  - prompt experimentation
  - rule experimentation
  - evaluation system
  - improvement loop integrity
  - operational architecture
  - cost/speed/complexity tradeoffs
- recommendation selected for downstream planning:
  - hybrid path (deterministic cron gates + selective qualitative judgment)
- explicit "Brutal Truth" section delivered per spec requirements.

Phase 2a workflow orchestration baseline is now implemented:

- typed workflow + skill registry is now first-class:
  - `config/workflows/registry.json`
  - `config/workflows/skills.json`
- deterministic workflow execution engine:
  - `services/workflow_orchestration.py`
  - explicit stage model execution with contract validation
- reference workflow vertical slice delivered:
  - `academic_paper_v1`
  - stages: parse -> normalize -> enrich -> generate -> transform -> validate -> finalize
  - explicit humanizer contract enforcement via meaning-preservation validation gate
- workflow execution reporting is now durable:
  - `workflow_execution_reports` table (runtime + canonical schema files)
  - report artifacts: `logs/control-plane/workflow-reports/<invocation-id>.json`
  - managed runtime writes `workflow-execution-report` artifacts and links them to run/invocation state
- managed runtime integration:
  - `bin/aios-managed-run.py` now executes workflow pipelines, records execution reports, and includes workflow summary linkage in invocation report metadata
- metadata observability:
  - `aios metadata --json` now includes workflow registry summary and latest execution report pointer
- phase architecture note:
  - `docs/architecture/2026-04-23-aios-workflow-orchestration-phase2a.md`

Phase 2b prompt library phase 2 (execution strategies) is now implemented as a hybrid baseline:

- canonical task-spec registry:
  - `config/execution-strategies/task-specs.json`
- surface strategy bundles:
  - `config/execution-strategies/strategies.json`
  - seeded first-slice task family: `audit_and_implement`
  - includes one validated strategy for each required surface:
    - `audit_and_implement_claude_v1`
    - `audit_and_implement_codex_v1`
- deterministic compiler/selector:
  - `services/execution_strategy.py`
  - selects strategy by `task_family + surface`, compiles constraints/contracts/rubric into execution instructions
- validation and generated selection registry:
  - `bin/validate-execution-strategies.py`
  - `config/execution-strategies/registry.json`
- runtime integration:
  - workflow normalization now attaches execution strategy bundles for implementation workflows
  - managed runtime maps backend to strategy surface (`claude_code` vs `codex`)
- metadata observability:
  - `aios metadata --json` now includes execution strategy coverage summary
- phase architecture note:
  - `docs/architecture/2026-04-23-aios-prompt-library-phase2.md`

Phase 3a AIOS UI command center MVP is now implemented:

- command-center homepage (`aios-ui/app/page.tsx`) now provides source-backed situational awareness for:
  - system health
  - active/failing/stale run signals
  - approvals/interventions inbox
  - unified change timeline (runs, approvals, changes, experiments)
- shared status/provenance model added:
  - `aios-ui/lib/status-provenance.ts`
  - explicit states: `confirmed`, `inferred`, `stale`, `missing`
- reusable provenance UI primitive added:
  - `aios-ui/components/primitives/ProvenanceBadge.tsx`
- control-plane observability upgraded with provenance badges:
  - `aios-ui/components/control/ControlPlaneStudio.tsx`
  - run history, run detail, and approval queue now expose status confidence + source metadata
- command-center IA/navigation labels updated:
  - `aios-ui/lib/constants.ts`
  - `aios-ui/components/layout/TopBar.tsx`
- command-center docs delivered per spec:
  - `docs/aios-ui-command-center-audit.md`
  - `docs/aios-ui-command-center-implementation-plan.md`
  - `docs/aios-ui-command-center-handoff.md`

Phase 3b Standards Delta / Project Health is now implemented:

- standards are now first-class AIOS registry objects:
  - `config/standards/registry.json`
  - fields include domain, weight, severity, evaluation method, remediation playbook, applicability, versioning, and waiver policy metadata
- standards-health scoring engine and persistence:
  - `services/standards_health.py`
  - explainable penalty model with explicit handling for:
    - `pass`
    - `partial`
    - `fail`
    - `unknown`
    - `regressed fail`
    - `waived`
    - `not_applicable`
- durable governance/remediation tables are now live:
  - `standards_profiles`
  - `standards_definitions`
  - `project_standards_profiles`
  - `standards_assessments`
  - `standards_delta_items`
  - `standards_backfill_tasks`
  - `standards_health_snapshots`
- runtime integration:
  - `hook-stop.py` now records standards-health snapshots after session close
  - each run writes deltas and Taski-traceable backfill tasks
- metadata observability:
  - `aios metadata --json` now includes standards registry summary + latest health snapshot
- Taski/UI health surfaces:
  - `aios-ui/server/aios/standards-health.ts`
  - `aios-ui/components/projects/TaskiProjectSurface.tsx` now renders:
    - health header
    - domain breakdown
    - delta matrix
    - prioritized backfill lane
    - standards migration view
  - `aios-ui/app/projects/page.tsx` now shows per-project health score, critical deltas, unknown coverage, and score trend
- quality pipeline surfaces:
  - `config/quality-pipeline.json` defines the portable linked-project gate model with three tiers:
    - Tier 1 Core: frozen install, lint, typecheck where applicable, tests, build where applicable, architecture boundary, CI gate
    - Production App: secret scan, env validation, dependency security, coverage, E2E smoke
    - Domain Specific: SEO/Lighthouse, telemetry utility, database restore/PITR, mobile release, full release E2E
  - `quality_pipeline_runs` records durable per-project gate results with evidence and source metadata
  - `services/quality_pipeline.py` and `aios-ui/server/aios/quality-pipeline.ts` resolve generated AIOS project IDs to stable repo slugs/names
  - `services/project_inventory.py` and `bin/sync-project-inventory.py` sync Git repositories from `~/projects` into the Taski `projects` table; Taski project inventory is the source of truth
  - unconfigured Taski projects now receive inferred Tier 1 gates from their repo path, lockfile/package metadata, package scripts, architecture script, and workflow directory
  - `soundscape-app` is the gold-profile implementation with core, production, public-web, telemetry, database, and mobile gates; other projects inherit only applicable gates instead of Soundscape-specific requirements
  - the Projects index now shows per-project pipeline coverage/status, and Taski project detail now includes a first-class Quality Pipeline panel with tier coverage
- workflow synthesis loop:
  - `bin/extract-patterns.py` now mines workflow candidates from repeated session traces (prompt classifications + post-tool event counts) instead of low-value handoff verbs
  - `bin/aios-pipeline.py` runs general pattern extraction before scoring and workflow synthesis so captured sessions can become proposal evidence
  - `services/workflow_synthesis.py` turns high-confidence prompt/workflow patterns into reviewable workflow proposals with generated workflow specs, skill specs, and validation plans
  - generated workflow executor skills now run through `learned_workflow_executor_v1` instead of being display-only registry entries
  - generated workflow best practices are not populated from static archetype text; they are gated on test-repo experiment evidence
  - workflow skill experiments are queued across the four registered test repos before promotion, with generated paper fixtures available for humanizer experiments
  - `bin/run-workflow-skill-experiments.py` runs queued workflow-skill experiments without an LLM agent, creates test-repo experiment branches, compares candidate workflows against a loose workflow baseline plus a no-skill ablation, runs repo-specific validation commands with a Python test-file fallback when pytest is unavailable, records repo/workflow fit in baseline/candidate scores, and only marks candidates promotion-ready when validation passes
  - `bin/aios-pipeline.py` now consumes queued workflow-skill experiments after synthesis as a normal automation phase
  - synthesis now also backfills reviewable proposals from the resolved Obsidian vault by clustering markdown workflow signals into archetype-level proposals; one-note vault backfill proposals are treated as too granular and are no longer generated
  - `workflow_synthesis_proposals` stores pending/approved workflow candidates with source pattern evidence
  - `bin/synthesize-workflows.py` creates pending proposals from DB patterns plus vault notes by default, supports `--no-vault`, and can explicitly approve a proposal into `config/workflows/registry.json` + `config/workflows/skills.json`
  - `/workflows` now surfaces pending workflow synthesis proposals with status, source evidence, and created timestamp alongside registered workflow metrics
  - proposal rows are review queue items only; `/workflows/[id]` routes are reserved for approved workflows from `config/workflows/registry.json`
  - `bin/aios-pipeline.py` now runs workflow synthesis as a recurring pipeline phase so repeated successful patterns are continually surfaced for approval
- phase architecture note:
  - `docs/architecture/2026-04-23-aios-standards-delta-health-phase3b.md`

RTK context compression is now integrated as an AIOS system primitive:

- unified command interface:
  - `services/rtk_integration.py`
  - `bin/rtk-run.py`
  - `rtk_run(command, mode)` with `compressed`, `raw`, and `adaptive` modes
- compression rules and context waste map:
  - `config/rtk/rules.json`
  - `docs/architecture/2026-04-27-aios-rtk-context-compression.md`
- lifecycle hook integration:
  - `hook-session-start.py` creates RTK schema and injects active compression policy
  - prompt, focus, and stop hooks now recover a missing session row from the current hook payload when `SessionStart` was not observed, so lifecycle events are captured instead of dropped as unknown sessions
  - `hook-stop.py` treats empty stdin as a recoverable lifecycle edge by falling back to `logs/current_session` before closing or skipping an already closed session
  - hook lifecycle recovery has focused regression coverage for prompt-submit recovery, stop recovery, and empty-stdin stop fallback against real hook entrypoints
  - `hook-post-tool-use.py` compresses Bash tool responses, records telemetry, and surfaces compact output
  - `hook-stop.py` logs per-session RTK savings in Stop event metadata
- workflow/runtime integration:
  - `bin/aios-pipeline.py` routes managed subprocess output through RTK adaptive mode
  - workflow execution reports include RTK policy metadata for implementation and failure-recovery workflows
- telemetry and UI:
  - `rtk_compression_events` records raw/compressed token estimates, reductions, ambiguous failures, raw tee paths, and workflow keys
  - `workflow_metrics` receives RTK token metrics for existing efficiency comparisons
  - `aios metadata --json` and `aios --json rtk` expose RTK rules and metrics
  - `/costs` now surfaces RTK tokens saved, reduction percent, ambiguous failures, and savings by workflow

The wiki/DeepWiki-style knowledge layer now has a minimum maintenance contract for agent use:

- wiki/context pages are treated as compressed maps and task-briefing inputs, not as replacements for repo files, docs, tests, validation scripts, or durable project truth
- `aios-ui/server/aios/wiki-maintenance.ts` defines maintenance metadata, page status labels, confidence labels, typed source refs, source coverage, stale-area tracking, a 0-5 maintenance score, and compact agent packet generation
- `/knowledge` pages now expose maintenance status, confidence, score, source references, known stale areas, related pages, and an agent packet checklist next to existing relationships/backlinks
- `config/wiki-maintenance/critical-pages.json` tracks source refs for the built-in system wiki pages that are otherwise assembled from code
- `pnpm wiki:check` runs `tools/wiki-check.mjs` to validate critical source refs, flag current pages without refs, warn on missing validation timestamps, and check referenced `pnpm` commands against package scripts
- `docs/wiki-maintenance.md` documents the post-task wiki/project-truth checklist agents should apply after meaningful work
- high-risk context routes now have explicit maintenance metadata and source refs: `context.index`, `context.router`, `context.schema`, `handoffs.latest`, `features.context-compiler`, `domains.knowledge-systems`, `packets.knowledge.obsidian-routing`, `packets.workflow.approval-gates`, `packets.ui.command-center`, and `projects.aios-ui`
- `pnpm wiki:check` also validates personal corpus refs against `aios.db` when present, including patterns, sessions, orchestration/divergent runs, briefing packets, memory updates, knowledge topics, vault notes, imported conversations, agent summaries, and task/writeback records
- remaining gap: lower-risk legacy context files and vault wiki pages still need explicit `wiki_status`, `source_refs`, and validation metadata before they can be scored as agent-usable or verified

## Still Missing

- more than one production-grade invocation backend beyond the new managed local runtime
- richer backend adapters for external/manual agent sessions so they emit the same handshake without fallback
- broader evaluator rule coverage and explicit finding resolution workflows
- deeper packet/result inspection at file/topic delta level
- richer Taski operator controls beyond summary, approvals, run/evaluator inspection, and standards backfill visibility
- legacy heuristic run matching still exists only as a fallback for older sessions that lack explicit handshake metadata
- linked-project profile ratchet completion (`amos-saas`, `soundscape-app`, `GitNexus`, `Terrace`, `portfolio`) so each has native profile config + CI wiring in-repo

## Spec Roadmap Corrections On 2026-04-23

The spec execution roadmap has been corrected before execution:

- The roadmap now treats AIOS as the global orchestration/control layer for all linked development projects. This repo is the implementation home and first self-check target, not the whole scope.
- Anti-Slop ESLint is now treated as an existing integration to audit and ratchet, not a greenfield build.
- Workflow orchestration must extend the existing control-plane primitives instead of recreating them.
- Phase 0 is serial by default because architecture enforcement, agent CLI surfaces, and success criteria share scripts, hooks, docs, and runtime contracts.
- Prompt Library Phase 1 uses the schema in `2026-04-08-prompt-library-design.md` as canonical.
- Agent Workflow CLI work must honor the hard checkpoint before implementation.
- Success criteria own judging rubrics; Standards Delta owns project health scoring and remediation.
- Prompt Library Phase 2 is scoped by the Improvement Engine audit rather than requiring full replay/shadow/canary infrastructure up front.
- UI Command Center now has an explicit MVP gate before the broader ten-surface target.

## Guardrails

- SQLite remains authoritative for machine-readable operational state
- Vault remains authoritative for curated human-readable knowledge
- staging remains non-canonical
- AIOS should prefer explicit inspectable pipelines over hidden prompt behavior
- default agent context policy is locked:
  - broad retrieval may happen inside AIOS
  - only compact ranked output reaches the agent by default
  - targeted expansion must be explicit and traced
