# AIOS Project Truth

Last updated: 2026-04-28

## What AIOS Is

AIOS is the local operating system for work context, agent workflows, and durable project memory.
It is the orchestration layer for agents across all linked development projects, not just a dashboard or standards system for this repository. It is intended to unify:

- structured knowledge pages
- grounded retrieval and query surfaces
- workflow and orchestration state
- task-specific delegation packets
- durable continuity across long-running sessions

## Current Reality

The repository currently contains three meaningful subsystems:

1. `aios-ui/`
   A Next.js local dashboard over `~/AIOS/data/aios.db`. It is strongest at session/run observability.

2. `bin/` and `services/`
   Python hooks, importers, storage maintenance tools, and the CTS prototype.

3. `docs/`
   Design intent for storage, knowledge, CTS, and the current UI, but not yet a single implemented architecture.

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

## Implemented On 2026-04-28

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
  - `services/workflow_synthesis.py` turns high-confidence prompt/workflow patterns into reviewable workflow proposals with generated workflow specs, skill specs, and validation plans
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
