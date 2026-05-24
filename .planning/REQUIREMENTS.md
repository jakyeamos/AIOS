# Requirements: AIOS

**Defined:** 2026-05-13
**Core Value:** AIOS should compile messy human intent into the right context, standards, workflow, agent instructions, evaluation, artifacts, and memory updates with less manual babysitting than direct model use.

## v1 Requirements

### Project And Intent Routing

- [x] **ROUT-01**: User can submit a vague goal and AIOS can identify the target project or explicitly surface ambiguity requiring clarification
- [x] **ROUT-02**: AIOS can classify the requested task type and select the smallest sufficient workflow for it
- [x] **ROUT-03**: AIOS can explain why a workflow route was selected over nearby alternatives
- [x] **ROUT-04**: AIOS can identify the recommended agent or harness and the appropriate prompt/handoff family for the selected workflow, with reasoning

### Context Compilation

- [ ] **CONT-01**: AIOS can compile a task-specific context packet from project truth, standards, packets, prompt assets, and recent evidence without dumping unrelated knowledge
- [ ] **CONT-02**: AIOS records loaded and skipped context with explicit reasons in a durable receipt
- [ ] **CONT-03**: AIOS can surface missing, stale, or conflicting context needed for a task before execution continues
- [ ] **CONT-04**: AIOS can produce an agent-ready briefing packet with task objective, constraints, relevant files, workflow steps, prompt/handoff instructions, and acceptance criteria

### Truth And Knowledge

- [ ] **TRUTH-01**: AIOS maintains a canonical truth file or equivalent structured record for each major linked project
- [ ] **TRUTH-02**: Project truth captures current goals, architecture, active risks, completed work, unresolved deltas, important decisions, and recommended next actions
- [ ] **TRUTH-03**: AIOS can answer what is being built, what changed, what remains unresolved, and what prior decisions or reusable assets are relevant from its knowledge surfaces before manual assembly
- [ ] **TRUTH-04**: AIOS can link truth entries, decisions, notes, prompts, skills, and workflow artifacts through searchable, inspectable knowledge objects

### Workflow Execution And Run State

- [ ] **RUN-01**: AIOS tracks explicit run lifecycle states including not started, in progress, blocked, failed, completed, needs approval, needs follow-up, and partially completed
- [ ] **RUN-02**: AIOS durably links runs, invocations, sessions, artifacts, and lifecycle events for every serious workflow execution
- [ ] **RUN-03**: AIOS can resume a partially completed workflow with the original context packet, current state, and next recommended action intact
- [ ] **RUN-04**: AIOS surfaces what changed during a run, what checks were executed, what approvals were involved, and what remains unresolved at closeout

### Standards And Evaluation

- [ ] **STND-01**: AIOS maps each task to the correct success criteria and standards set before execution
- [ ] **STND-02**: AIOS evaluates outputs against explicit quality criteria rather than generic model judgment
- [ ] **STND-03**: AIOS requires execution-first verification for stateful, cross-system, or core-logic changes
- [ ] **STND-04**: AIOS preserves durable evaluation findings, blockers, warnings, passes, and accepted tradeoffs for completed runs

### Delta Scoring And Health

- [ ] **DELT-01**: AIOS can score project alignment against expected standards across architecture, testing, maintainability, security, UX, observability, documentation, launch readiness, agent-readiness, and standards compliance
- [ ] **DELT-02**: AIOS explains each health or delta score with concrete evidence, confidence, freshness, and remediation guidance
- [ ] **DELT-03**: AIOS distinguishes confirmed, inferred, missing, and contradictory signals in project and capability health views
- [ ] **DELT-04**: AIOS can recommend a prioritized backfill path for the biggest standards or capability gaps in a project

### Governance And Writeback

- [ ] **GOV-01**: AIOS creates reviewable writeback proposals for project truth, prompts, skills, workflows, standards, and context packets instead of silently mutating them
- [ ] **GOV-02**: AIOS requires approval gates for important truth changes, global rule changes, skill/prompt promotion, workflow behavior changes, and destructive actions
- [ ] **GOV-03**: Every meaningful run leaves durable writeback, follow-up, or no-learning evidence so the system becomes more accurate over time
- [ ] **GOV-04**: AIOS records unresolved risks, pending approvals, and follow-up actions at the end of a governed workflow

### Prompt, Skill, And Workflow Assets

- [ ] **ASSET-01**: AIOS tracks prompts, skills, and workflows as lifecycle-managed assets with purpose, applicability, status, and evidence of usefulness
- [ ] **ASSET-02**: AIOS can distinguish draft, candidate, approved, active, and deprecated reusable assets
- [ ] **ASSET-03**: AIOS links reusable assets to the workflows and task types where they have succeeded or failed
- [ ] **ASSET-04**: AIOS can recommend proven prompts, skills, and workflows during packet generation and handoff creation

### Workflow Contracts And Library

- [ ] **WFLO-01**: AIOS defines each governed workflow as a stage-based contract with required inputs, required outputs, validations, and expected artifacts
- [ ] **WFLO-02**: AIOS can bind prompts, skills, tools, standards, approval gates, and writeback behavior to specific workflow stages
- [ ] **WFLO-03**: AIOS can evaluate workflow success at both the stage level and the overall run level using durable evidence
- [ ] **WFLO-04**: AIOS can compare workflow effectiveness over time and promote, revise, or deprecate workflows based on evidence

### Continuous Improvement

- [ ] **LEARN-01**: AIOS can capture run evidence that informs future prompt, skill, workflow, and packet improvements
- [ ] **LEARN-02**: AIOS can identify recurring failure modes, ignored rules, bloated packets, or weak workflows from accumulated evidence
- [ ] **LEARN-03**: AIOS can propose conservative improvements to routing, context selection, and evaluation based on reviewed outcomes
- [ ] **LEARN-04**: AIOS makes compounding visible by showing what each meaningful run improved for future work

### Operator Surfaces

- [ ] **OPER-01**: AIOS provides searchable, inspectable operator views for projects, runs, workflows, knowledge, prompts, deltas, approvals, and recent changes
- [ ] **OPER-02**: AIOS can answer which project needs attention, what good looks like, which workflow should run, which prompt/skill assets apply, and which context an agent needs before manual prep
- [ ] **OPER-03**: AIOS exposes receipts, routing decisions, evidence trails, and drill-down paths for visible metrics and recommendations
- [ ] **OPER-04**: AIOS can surface the default-layer daily flow end to end: vague goal -> routing -> execution -> evaluation -> writeback -> unresolved deltas

### Testing, Benchmark Evaluation, And Shadow Workflows

- [ ] **EVAL-01**: Every AIOS eval run is recorded in a durable, queryable eval_runs table with context profile, condition, model, harness, result, cost, and failure labels; eval tasks are replayable from the recorded start SHA and acceptance criteria
- [ ] **EVAL-02**: AIOS can run the same task in full-second-brain mode and repo-only mode and compute Second Brain Lift; AIOS detects stale context retrievals and proposes writebacks; gold-set tasks have known-required-context so recall is measured deterministically
- [ ] **EVAL-03**: AIOS can run a task from the same starting SHA on an isolated branch/worktree under a specified condition and compare the result against a baseline using shared acceptance criteria, tests, lint, and typecheck without contaminating the baseline branch
- [ ] **EVAL-04**: AIOS can disable individual features (context packets, second brain, success criteria, subagents, model routing, personal corpus, project truth) and produce an EvalRun per variant from the same starting SHA; ablation scorecard comparison identifies which features contribute measurable lift
- [ ] **EVAL-05**: AIOS can observe peer workflow sessions without modifying prompts, injecting context, spawning subagents, or changing model selection; trace captures are privacy-safe by default; shadow candidate detection automatically scores each observed task
- [ ] **EVAL-06**: After a shadow candidate is approved in person, AIOS automatically executes the full benchmark pipeline through snapshot, worktree, task packet generation, AIOS run, verification, scoring, comparison report, and backlog item creation without touching the peer active branch
- [ ] **EVAL-07**: AIOS can generate a portable context packet from a task description and repo structure that allows peer/core runs to access relevant context without the personal second brain; packets explicitly exclude personal notes, private history, and secrets
- [ ] **EVAL-08**: AIOS can translate eval tasks into SWE-bench and Terminal-Bench formats and normalize external harness results into EvalRun rows with context_profile = external_clean_room

### Graph-Native Memory Architecture

- [ ] **MEM-01**: AIOS stores memory across four distinct layers: raw source (Layer A with provenance), normalized facts (Layer B with validity status), graph relationships (Layer C with typed predicates), and model-facing compiled briefing packets (Layer D)
- [ ] **MEM-02**: AIOS compiles retrieved memory into readable markdown briefing packets — never raw JSON or graph edge rows — with sections for Current Truth, Prior Decisions, Constraints, Causal Chain, Contradictions, Open Questions, and Sources/Provenance
- [ ] **MEM-03**: AIOS assembles prompt context in stable-prefix-first order so identical project/rule/preference sections appear early and dynamic task content appears late, maximizing API provider prompt cache hit rate
- [ ] **MEM-04**: A formal memory packet contract governs required/optional sections, section ordering, provenance rules, staleness rules, contradiction handling, confidence levels, and token budgeting with documented good and bad packet examples
- [ ] **MEM-05**: Integration tests and a standalone validation script enforce nine retrieval quality constraints: provenance present, superseded facts excluded from Current Truth, contradictions surfaced, project constraints included, stable/dynamic separation, no raw JSON in output, token budgets respected, deterministic stable prefix, and no unrelated memory bloat
- [ ] **MEM-06**: A prioritized backfill plan identifies existing AIOS memory hotspots (truth files, PRDs, agent rules, skills, prompt libraries, design specs) with recommended Layer B fact extraction and Layer C relationship backfill at P0/P1/P2 priority
- [ ] **MEM-07**: AIOS represents memory as connected knowledge using typed graph-edge relationships (caused_by, depends_on, blocks, supersedes, contradicts, supports, evidence_for, belongs_to_project, decided_in, implemented_by, requested_by_user, derived_from, related_to, has_open_question, has_constraint, has_risk, has_owner, has_status) stored in the existing SQLite operational spine
- [ ] **MEM-08**: A future design note documents why direct KV-cache injection is not a core AIOS dependency for API models, what prerequisites would need to be true for a local-runner path, and how the stable-prefix ContextCompiler bridges today's architecture to that future without requiring it

### Session Ingestion And Provider Extensibility

- [ ] **SESS-01**: AIOS defines a `SessionProvider` abstract interface with nine methods (discover_sources, scan_since, extract_raw_session, normalize_session, compute_fingerprint, upsert_session, summarize_session, emit_writeback_candidates, health_check) and a `NormalizedSession` model with full provenance, timestamp, workspace, participant, message, tool-call, file-edit, command, decision, and status fields; existing Claude and Codex ingestion is wrapped as conforming providers
- [ ] **SESS-02**: AIOS can discover and ingest Cursor sessions from local SQLite workspace storage databases (opened read-only with temp-copy safety) and agent-transcript JSONL files; workspace hash and resolved folder path are both preserved; SQLite and JSONL sources for the same session are deduplicated
- [ ] **SESS-03**: AIOS can discover and ingest Antigravity CLI sessions from brain/session directories; file formats are detected before parsing (JSON, JSONL, SQLite, Markdown, text, unknown binary); unknown binary files are stored as metadata-only with a health warning; reasoning traces are stored as raw artifact pointers only and never promoted to vault content
- [ ] **SESS-04**: Session sync is incremental and idempotent; a `session_provider_cursors` table tracks last mtime, size, hash, and provider session ID per source path; dry-run mode makes no DB writes; backfill mode rescans all sources without duplication; repair mode re-normalizes sessions with stale or missing fields
- [ ] **SESS-05**: Raw session content is stored in the operational SQLite database, not in the curated Obsidian vault; secret redaction (API keys, tokens, .env values, auth headers, PEM keys) runs before any summary or writeback is generated; sessions with redaction failures are held with a flag and excluded from writeback candidates; per-provider ignore-path patterns and retention policies are configurable
- [ ] **SESS-06**: Each imported session produces a structured `SessionSummary` with 16 defined fields: what I was trying to do, project/repo involved, important context used, decisions made, files/modules touched, commands/tools used, bugs/failures encountered, successful fixes, unresolved follow-ups, reusable patterns, candidate skills to extract, whether to update a truth file, whether to create an Obsidian note, confidence, source provenance, and writeback proposal status
- [ ] **SESS-07**: Session writeback follows the governed proposal flow (proposal → approval → vault mutation); raw transcripts and reasoning traces never appear in writeback candidate content; truth file update proposals are generated only for high-confidence sessions that clearly changed project state; skillification candidates are detected when the same pattern appears in 3+ sessions across any providers within 30 days
- [ ] **SESS-08**: The CLI exposes `aios sessions sync`, `status`, `backfill`, `repair`, and `debug` sub-commands; a cron-friendly wrapper script runs all-provider sync hourly; operator documentation covers all four providers with what is imported, what is not imported, default paths by OS, privacy warnings, backfill and sync instructions, debug instructions, and provider disable instructions; a `docs/backfills/session-provider-backfill.md` report is generated from a dry run on the live machine

### Code Quality Gates And Cross-Project Complexity Standards

- [ ] **QUAL-01**: After any large piece of work (5+ files, 300+ lines, new feature, cross-package, DB/schema, pipeline/model logic, UI with state, agent/workflow change, performance-sensitive path, or infrastructure code), agents run a mandatory Complexity + Simplification Gate covering Gate A (algorithmic complexity/performance), Gate B (simplification/maintainability), and Gate C (verification)
- [ ] **QUAL-02**: Agent workflows include 8 pre-check implementation questions that surface the most common complexity and simplification issues during coding — before the post-work gate runs — reducing the number of findings that reach the gate
- [ ] **QUAL-03**: A root quality gate specification exists at `docs/quality/complexity-simplification-gate.md` explaining why the gate exists, when it runs, what agents must check, how to use available tools, how to write backfill findings, how to decide fix-vs-defer, and the Definition of Done for a completed gate pass
- [ ] **QUAL-04**: A local complexity pattern checklist at `docs/quality/complexity-checklist.md` covers 17 named algorithmic patterns across three categories (algorithmic, render/UI, data access), each with code signature, why-it-matters, and preferred remedy — no external dependencies
- [ ] **QUAL-05**: AIOS has a complexity+simplification backfill inventory at `docs/backfill/complexity-simplification-backfill.md` with observation-backed findings across all major source areas (services, bin scripts, aios-ui, config, tests), a remediation order, and a Definition of Done for the quality standard
- [ ] **QUAL-06**: Every first-class linked project (soundscape-app, portfolio, amos-saas, GitNexus, tm, Terrace) has a `docs/complexity-simplification-backfill.md` with observation-backed findings or an honest "no major hotspots" statement, quality command results, and a Definition of Done
- [ ] **QUAL-07**: The quality gate explicitly distinguishes "report hotspot" from "fix hotspot" — agents record every finding before any fix attempt; fixes are permitted only for sub-5-line, no-behavior-risk changes; all other findings are deferred to a dedicated remediation pass
- [ ] **QUAL-08**: The cross-project summary table in the AIOS backfill doc links all six external project backfill inventories with P0/P1/P2 hotspot counts, providing the operator a portfolio-level view for prioritizing remediation across all projects

## v2 Requirements

None currently. The full operating-system vision is intentionally being planned into v1 and sequenced through milestones rather than deferred into a later release bucket.

## Out of Scope

| Feature | Reason |
|---------|--------|
| None currently | The project is intentionally planning the full target capability set as v1 and managing scope through roadmap sequencing instead of exclusions |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| ROUT-01 | Phase 1: Project, Workflow, And Prompt Routing | Complete |
| ROUT-02 | Phase 1: Project, Workflow, And Prompt Routing | Complete |
| ROUT-03 | Phase 1: Project, Workflow, And Prompt Routing | Complete |
| ROUT-04 | Phase 1: Project, Workflow, And Prompt Routing | Complete |
| CONT-01 | Phase 2: Context, Query, And Briefing Compilation | Pending |
| CONT-02 | Phase 2: Context, Query, And Briefing Compilation | Pending |
| CONT-03 | Phase 2: Context, Query, And Briefing Compilation | Pending |
| CONT-04 | Phase 2: Context, Query, And Briefing Compilation | Pending |
| TRUTH-01 | Phase 4: Project Truth, Knowledge, And Grounded Query | Pending |
| TRUTH-02 | Phase 4: Project Truth, Knowledge, And Grounded Query | Pending |
| TRUTH-03 | Phase 4: Project Truth, Knowledge, And Grounded Query | Pending |
| TRUTH-04 | Phase 4: Project Truth, Knowledge, And Grounded Query | Pending |
| RUN-01 | Phase 3: Workflow Execution And Run State | Pending |
| RUN-02 | Phase 3: Workflow Execution And Run State | Pending |
| RUN-03 | Phase 3: Workflow Execution And Run State | Pending |
| RUN-04 | Phase 3: Workflow Execution And Run State | Pending |
| STND-01 | Phase 6: Standards Resolution And Evidence-Based Evaluation | Pending |
| STND-02 | Phase 6: Standards Resolution And Evidence-Based Evaluation | Pending |
| STND-03 | Phase 6: Standards Resolution And Evidence-Based Evaluation | Pending |
| STND-04 | Phase 6: Standards Resolution And Evidence-Based Evaluation | Pending |
| DELT-01 | Phase 7: Delta Scoring And Health Backfill | Pending |
| DELT-02 | Phase 7: Delta Scoring And Health Backfill | Pending |
| DELT-03 | Phase 7: Delta Scoring And Health Backfill | Pending |
| DELT-04 | Phase 7: Delta Scoring And Health Backfill | Pending |
| GOV-01 | Phase 5: Governed Writeback And Approval Control | Pending |
| GOV-02 | Phase 5: Governed Writeback And Approval Control | Pending |
| GOV-03 | Phase 5: Governed Writeback And Approval Control | Pending |
| GOV-04 | Phase 5: Governed Writeback And Approval Control | Pending |
| ASSET-01 | Phase 8: Prompt, Skill, Workflow Contracts, And Asset Lifecycle | Pending |
| ASSET-02 | Phase 8: Prompt, Skill, Workflow Contracts, And Asset Lifecycle | Pending |
| ASSET-03 | Phase 8: Prompt, Skill, Workflow Contracts, And Asset Lifecycle | Pending |
| ASSET-04 | Phase 8: Prompt, Skill, Workflow Contracts, And Asset Lifecycle | Pending |
| WFLO-01 | Phase 8: Prompt, Skill, Workflow Contracts, And Asset Lifecycle | Pending |
| WFLO-02 | Phase 8: Prompt, Skill, Workflow Contracts, And Asset Lifecycle | Pending |
| WFLO-03 | Phase 8: Prompt, Skill, Workflow Contracts, And Asset Lifecycle | Pending |
| WFLO-04 | Phase 8: Prompt, Skill, Workflow Contracts, And Asset Lifecycle | Pending |
| LEARN-01 | Phase 9: Continuous Learning And Conservative Optimization | Pending |
| LEARN-02 | Phase 9: Continuous Learning And Conservative Optimization | Pending |
| LEARN-03 | Phase 9: Continuous Learning And Conservative Optimization | Pending |
| LEARN-04 | Phase 9: Continuous Learning And Conservative Optimization | Pending |
| OPER-01 | Phase 10: Operator Surfaces, Query, And Daily-Flow Visibility | Pending |
| OPER-02 | Phase 10: Operator Surfaces, Query, And Daily-Flow Visibility | Pending |
| OPER-03 | Phase 10: Operator Surfaces, Query, And Daily-Flow Visibility | Pending |
| OPER-04 | Phase 10: Operator Surfaces, Query, And Daily-Flow Visibility | Pending |
| EVAL-01 | Phase 11: Testing, Benchmark Evaluation, And Shadow Workflows | Pending |
| EVAL-02 | Phase 11: Testing, Benchmark Evaluation, And Shadow Workflows | Pending |
| EVAL-03 | Phase 11: Testing, Benchmark Evaluation, And Shadow Workflows | Pending |
| EVAL-04 | Phase 11: Testing, Benchmark Evaluation, And Shadow Workflows | Pending |
| EVAL-05 | Phase 11: Testing, Benchmark Evaluation, And Shadow Workflows | Pending |
| EVAL-06 | Phase 11: Testing, Benchmark Evaluation, And Shadow Workflows | Pending |
| EVAL-07 | Phase 11: Testing, Benchmark Evaluation, And Shadow Workflows | Pending |
| EVAL-08 | Phase 11: Testing, Benchmark Evaluation, And Shadow Workflows | Pending |

| MEM-01 | Phase 12: Graph-Native Memory Architecture And Cache-Aware Context Compilation | Pending |
| MEM-02 | Phase 12: Graph-Native Memory Architecture And Cache-Aware Context Compilation | Pending |
| MEM-03 | Phase 12: Graph-Native Memory Architecture And Cache-Aware Context Compilation | Pending |
| MEM-04 | Phase 12: Graph-Native Memory Architecture And Cache-Aware Context Compilation | Pending |
| MEM-05 | Phase 12: Graph-Native Memory Architecture And Cache-Aware Context Compilation | Pending |
| MEM-06 | Phase 12: Graph-Native Memory Architecture And Cache-Aware Context Compilation | Pending |
| MEM-07 | Phase 12: Graph-Native Memory Architecture And Cache-Aware Context Compilation | Pending |
| MEM-08 | Phase 12: Graph-Native Memory Architecture And Cache-Aware Context Compilation | Pending |
| SESS-01 | Phase 13: Multi-Provider Session Ingestion And Second Brain Data Pipeline | Pending |
| SESS-02 | Phase 13: Multi-Provider Session Ingestion And Second Brain Data Pipeline | Pending |
| SESS-03 | Phase 13: Multi-Provider Session Ingestion And Second Brain Data Pipeline | Pending |
| SESS-04 | Phase 13: Multi-Provider Session Ingestion And Second Brain Data Pipeline | Pending |
| SESS-05 | Phase 13: Multi-Provider Session Ingestion And Second Brain Data Pipeline | Pending |
| SESS-06 | Phase 13: Multi-Provider Session Ingestion And Second Brain Data Pipeline | Pending |
| SESS-07 | Phase 13: Multi-Provider Session Ingestion And Second Brain Data Pipeline | Pending |
| SESS-08 | Phase 13: Multi-Provider Session Ingestion And Second Brain Data Pipeline | Pending |
| QUAL-01 | Phase 14: Code Quality Gates And Cross-Project Complexity Standards | Pending |
| QUAL-02 | Phase 14: Code Quality Gates And Cross-Project Complexity Standards | Pending |
| QUAL-03 | Phase 14: Code Quality Gates And Cross-Project Complexity Standards | Pending |
| QUAL-04 | Phase 14: Code Quality Gates And Cross-Project Complexity Standards | Pending |
| QUAL-05 | Phase 14: Code Quality Gates And Cross-Project Complexity Standards | Pending |
| QUAL-06 | Phase 14: Code Quality Gates And Cross-Project Complexity Standards | Pending |
| QUAL-07 | Phase 14: Code Quality Gates And Cross-Project Complexity Standards | Pending |
| QUAL-08 | Phase 14: Code Quality Gates And Cross-Project Complexity Standards | Pending |
| SKIL-01 | Phase 15: Agent Skill Portfolio Audit And External Library Integration | Pending |
| SKIL-02 | Phase 15: Agent Skill Portfolio Audit And External Library Integration | Pending |
| SKIL-03 | Phase 15: Agent Skill Portfolio Audit And External Library Integration | Pending |
| SKIL-04 | Phase 15: Agent Skill Portfolio Audit And External Library Integration | Pending |
| SKIL-05 | Phase 15: Agent Skill Portfolio Audit And External Library Integration | Pending |
| SKIL-06 | Phase 15: Agent Skill Portfolio Audit And External Library Integration | Pending |
| SKIL-07 | Phase 15: Agent Skill Portfolio Audit And External Library Integration | Pending |
| SKIL-08 | Phase 15: Agent Skill Portfolio Audit And External Library Integration | Pending |

**Coverage:**
- v1 requirements: 84 total (76 prior + 8 SKIL)
- Mapped to phases: 84
- Unmapped: 0

---
*Requirements defined: 2026-05-13*
*Last updated: 2026-05-23 after adding Phase 15 SKIL requirements*
