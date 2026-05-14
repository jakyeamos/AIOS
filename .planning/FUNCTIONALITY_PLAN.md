# AIOS Detailed Functionality Plan

**Created:** 2026-05-13  
**Purpose:** Provide detailed tier-one planning guidance for every major current or planned AIOS functionality. This document expands the summary matrix in [FUNCTIONALITY_MAP.md](/Users/jakyeamos/AIOS/.planning/FUNCTIONALITY_MAP.md) into execution-grade planning detail.

## How To Use This Document

- Use this document when planning or reviewing any roadmap phase.
- Every functionality section below answers:
  - what exists now
  - what tier-one means for that functionality
  - what work tracks are required
  - what dependencies and risks exist
  - what evidence closes the gap
- This document is intentionally detailed. It is the functionality-level contract beneath the roadmap.

## Planning Conventions

- **Current state:** today’s code surfaces and limitations
- **Tier-one target:** what “default operating layer” means for the functionality
- **Detailed scope:** the capabilities that must exist
- **Implementation tracks:** the concrete work streams needed
- **Dependencies:** adjacent functionality required first or in parallel
- **Exit evidence:** what proves the functionality is tier-one enough

## Group 1: Governed Entry Loop

### 1. Project Identification From Vague Intent

**Current state**
- AIOS has project inventory, project truth, and run-start surfaces, but no clearly dominant project-resolution engine for vague human goals.
- Resolution likely happens through a mixture of explicit project ids, operator context, and route-specific assumptions.

**Tier-one target**
- AIOS must resolve the project for most serious tasks automatically, or block with explicit ambiguity instead of silently guessing.

**Detailed scope**
- Detect project references from name, repo, feature, domain, or standards context.
- Rank possible project matches with confidence and reasons.
- Block when ambiguity is too high rather than silently routing the wrong project.
- Preserve the chosen project in run state, packet receipts, and writeback targets.

**Implementation tracks**
- Add deterministic project-candidate ranking and ambiguity thresholds.
- Tie project resolution to truth files, codebase maps, project inventory, and recent run history.
- Persist “why this project was selected” into run metadata.
- Surface project-resolution failure modes in the operator UI and query layer.

**Dependencies**
- Project inventory quality
- Truth-file freshness
- Grounded query / project dossier quality

**Exit evidence**
- Route decisions cite the selected project and alternatives considered.
- Wrong-project routing becomes rare and inspectable.
- Ambiguous tasks block or ask for clarification explicitly.

### 2. Task Classification And Workflow Routing

**Current state**
- Workflow registries and execution-strategy catalogs exist.
- Trigger-hint routing exists in registry form, but the planning layer still treats workflow choice too broadly.

**Tier-one target**
- AIOS must choose the smallest sufficient workflow for the task and explain why.

**Detailed scope**
- Classify tasks by intent family, risk, repo scope, verification needs, and expected artifacts.
- Route tasks to the appropriate governed workflow instead of generic execution.
- Explain why a workflow was selected and why adjacent workflows were not.
- Allow graceful “unknown route” handling with explicit fallback behavior.

**Implementation tracks**
- Unify workflow registry, execution strategy, and prompt normalization into one route decision surface.
- Make route selection durable and inspectable in run state.
- Add confidence scoring and ambiguity handling for workflow selection.
- Add evaluation signals showing which routes perform well or poorly over time.

**Dependencies**
- Workflow library quality
- Prompt-library selection
- Task-family execution strategies

**Exit evidence**
- Most serious requests start with an explicit workflow route and rationale.
- Workflow misroutes are measurable and auditable.
- Route decisions are reused in packet generation and closeout.

### 3. Agent/Harness Recommendation

**Current state**
- Invocation backends exist for Codex, Claude, and legacy manual paths.
- The recommended surface is not yet a robust first-class route output everywhere.

**Tier-one target**
- AIOS must recommend the right execution surface for the chosen workflow and constrain expectations accordingly.

**Detailed scope**
- Match workflows to execution surfaces based on task family, repo scope, verification needs, and tool access.
- Distinguish between “good fit,” “acceptable fallback,” and “not allowed.”
- Persist chosen surface in invocation state and route explanation.

**Implementation tracks**
- Expand backend recommendation logic beyond static surface mapping.
- Add surface-specific constraints and capabilities to route outputs.
- Teach workflows and strategy profiles what they require from a harness.

**Dependencies**
- Invocation backend contracts
- Workflow contracts
- Strategy catalog completeness

**Exit evidence**
- Route outputs always include an execution surface recommendation and rationale.
- Surface mismatch becomes a visible route or validation failure.

### 4. Prompt-Library Selection During Routing

**Current state**
- AIOS has prompt templates, a registry, prompt sync, prompt visibility, and hook-side prompt normalization.
- Prompt selection exists operationally, but planning had previously treated it too late.

**Tier-one target**
- Prompt-family selection must be part of route resolution, not only a passive library or telemetry surface.

**Detailed scope**
- Associate workflows and task families with prompt families or template classes.
- Distinguish approved, candidate, and deprecated prompt assets at route time.
- Provide prompt provenance in handoffs and receipts.
- Fall back safely when no exact template match exists.

**Implementation tracks**
- Formalize prompt-family selection inside route outputs.
- Add prompt status/approval checks to packet generation.
- Expose prompt-family recommendation and confidence in operator surfaces.
- Track prompt effectiveness per workflow and task family.

**Dependencies**
- Prompt registry quality
- Prompt lifecycle metadata
- Workflow contracts

**Exit evidence**
- Route outputs include prompt/handoff-family selection.
- Packets include approved or candidate prompt assets with provenance.
- Prompt recommendations improve with evidence over time.

### 5. Context Compilation

**Current state**
- The file-backed context compiler exists and produces receipts.
- Context selection is real, but not yet obviously the default entry path for all serious work.

**Tier-one target**
- AIOS must consistently deliver the right 5–20% of available knowledge for a task, not a broad semantic dump.

**Detailed scope**
- Select relevant truth, standards, domain context, feature packets, prompts, and recent evidence.
- Record loaded and skipped context with reasons.
- Surface missing, stale, or conflicting inputs before execution continues.
- Preserve packet identity so downstream runs and writebacks point back to it.

**Implementation tracks**
- Improve task/project-aware context scoring.
- Add stronger stale/missing/conflict handling.
- Integrate prompt assets and workflow-bound context requirements into packet selection.
- Make packet generation the required preflight for serious work.

**Dependencies**
- Project identification
- Truth freshness
- Workflow routing
- Prompt lifecycle and standards registries

**Exit evidence**
- Packets are smaller, more relevant, and more inspectable.
- Receipts clearly explain both inclusion and exclusion.
- Operators stop manually assembling context for common serious tasks.

### 6. Briefing Packet / Agent Handoff Generation

**Current state**
- Briefing packet tables and routed work exist.
- Handoff quality is still only partially governed and may omit prompt/handoff composition details.

**Tier-one target**
- A receiving agent should know exactly what to do from the AIOS packet alone.

**Detailed scope**
- Include objective, target project, workflow, constraints, relevant files, standards, prompt/handoff instructions, and acceptance criteria.
- Include required checks, prohibited behaviors, and writeback expectations.
- Link the packet to the route decision, selected assets, and projected closeout requirements.

**Implementation tracks**
- Standardize packet schema across workflows.
- Add workflow-stage-specific handoff sections where needed.
- Add packet completeness validation before execution begins.
- Capture packet effectiveness in later learning loops.

**Dependencies**
- Workflow contracts
- Context compiler
- Prompt selection
- Standards matching

**Exit evidence**
- Agents can execute from packet alone with fewer follow-up clarifications.
- Packet omissions become measurable and reviewable.

### 7. Run / Invocation Lifecycle Tracking

**Current state**
- Durable run, invocation, and event tables exist.
- Lifecycle audit is real.
- Handshake coverage still remains below the stated tier-one target.

**Tier-one target**
- Serious work must move through deterministic, explicit lifecycle state with durable linkage.

**Detailed scope**
- Model ready, in progress, blocked, waiting-for-user, waiting-for-tool, failed-validation, completed, failed, canceled, and superseded cleanly.
- Track exact run/invocation/session relationships.
- Record closeout summaries, validation state, approvals touched, and pending follow-up.

**Implementation tracks**
- Raise explicit handshake coverage beyond tier-one target.
- Remove remaining heuristic fallback paths where possible.
- Tighten UI and CLI parity around lifecycle meanings.
- Add failure repair and orphan detection surfaces.

**Dependencies**
- Managed runtime closeout quality
- Hook integrity
- Approval state integration

**Exit evidence**
- `lifecycle-audit` stays clean.
- `invocation-audit` meets target coverage.
- Orphaned or misleading run state becomes rare and visible.

### 8. Resume / Partial Completion Flow

**Current state**
- Lifecycle state and durable records exist, but resume is not yet a visibly complete product flow.

**Tier-one target**
- Interrupted work must restart from preserved state instead of reconstructed memory.

**Detailed scope**
- Resume from packet id, active state, incomplete validations, pending approvals, and next recommended actions.
- Distinguish resume-after-blocked from resume-after-partial-success from resume-after-failure.
- Preserve provenance across resumed runs or branches of work.

**Implementation tracks**
- Define resumable state bundles.
- Add operator surfaces for “resume this run with context.”
- Teach workflows how to restore stage-local progress.

**Dependencies**
- Lifecycle tracking
- Packet identity
- Approval and writeback state

**Exit evidence**
- AIOS can resume real interrupted work without manual reconstruction.
- Resume behavior is tested and auditable.

## Group 2: Truth, Governance, And Evidence

### 9. Project Truth Files

**Current state**
- `PROJECT.md` exists and is treated seriously in this repo.
- Broader multi-project truth freshness is still incomplete.

**Tier-one target**
- Every major project should have a canonical current-state truth surface AIOS can trust.

**Detailed scope**
- Capture goals, architecture, active risks, decisions, completed work, unresolved deltas, and next actions.
- Show freshness and provenance.
- Tie truth updates to meaningful run closeout instead of manual cleanup alone.

**Implementation tracks**
- Strengthen truth update discipline and writeback proposals.
- Standardize project-truth schema across linked projects.
- Add drift detection between truth, codebase maps, and operational evidence.

**Dependencies**
- Writeback proposals
- Knowledge surfaces
- Run closeout quality

**Exit evidence**
- Operators stop asking “what is the current state of this project?”
- Truth updates become a routine governed artifact of serious work.

### 10. Knowledge Graph / Linked Knowledge

**Current state**
- Knowledge objects, relationships, and references exist.
- Retrieval is real but still not fully “operational knowledge” in product feel.

**Tier-one target**
- Knowledge must be linked, citable, searchable, and actually useful to route and evaluate work.

**Detailed scope**
- Represent decisions, concepts, projects, rules, workflows, prompts, and references as linked objects.
- Maintain source references, freshness, confidence, and backlinks.
- Allow both human browsing and machine consumption.

**Implementation tracks**
- Improve relationship quality and coverage.
- Tie knowledge entries more tightly to truth, workflows, and deltas.
- Expose better operator summaries for “why this matters now.”

**Dependencies**
- Truth maintenance
- Grounded query
- Context compiler

**Exit evidence**
- Linked knowledge reduces repeated rediscovery across serious tasks.
- Query and packet generation rely on it meaningfully.

### 11. Grounded Query / Inspectable Answers

**Current state**
- Query surfaces and grounded capability answers exist.
- Still too easy to think of this as a convenience route instead of a default-layer primitive.

**Tier-one target**
- AIOS should answer the operator’s key questions before manual context assembly.

**Detailed scope**
- Answer what changed, what needs attention, what workflow should run, what standards apply, and what evidence supports those answers.
- Cite sources and explain confidence and missing data.
- Bridge knowledge, truth, run state, and health deltas.

**Implementation tracks**
- Expand query coverage to default-layer questions.
- Improve provenance and confidence reporting.
- Connect query answers to operator next actions and workflow launch surfaces.

**Dependencies**
- Knowledge quality
- Truth freshness
- Capability truth and standards health

**Exit evidence**
- Query answers become a trusted starting point for serious work.
- Operators rely less on manual repo/vault/database inspection.

### 12. Governed Writeback Proposals

**Current state**
- Writeback proposal tables and UI surfaces exist.
- Coverage is still uneven across all asset and truth classes.

**Tier-one target**
- Every meaningful run should leave reviewable evidence of what AIOS learned or what needs follow-up.

**Detailed scope**
- Cover truth files, prompts, skills, workflows, packets, standards, and learned observations.
- Preserve rationale, evidence, actor, and approval path.
- Distinguish writeback proposal from accepted truth.

**Implementation tracks**
- Normalize writeback proposal schema across asset classes.
- Ensure post-run closeout always emits writeback/no-learning/follow-up outcomes.
- Tighten operator review flows and lifecycle states for proposals.

**Dependencies**
- Run closeout quality
- Approval gates
- Knowledge/truth update discipline

**Exit evidence**
- AIOS becomes more accurate after meaningful runs.
- Silent memory mutation becomes rare or eliminated.

### 13. Approval Gates

**Current state**
- Approval behavior exists conceptually and in some surfaces, but not yet as a uniform control-plane contract.

**Tier-one target**
- High-impact changes must be reviewable before they become default behavior.

**Detailed scope**
- Gate truth rewrites, prompt/skill/workflow promotion, standard changes, destructive actions, and risky automations.
- Distinguish advisory review from hard approval requirement.
- Preserve approved/rejected/stale states durably.

**Implementation tracks**
- Define approval policy classes by functionality type.
- Integrate approval state into run closeout and workflow stage outputs.
- Expose pending approvals in operator UI and query answers.

**Dependencies**
- Writeback proposals
- Workflow contracts
- Lifecycle tracking

**Exit evidence**
- High-blast-radius changes always have a visible review trail.
- Pending approvals are easy to inspect and act on.

## Group 3: Standards And Health Intelligence

### 14. Success Criteria Matching

**Current state**
- Success criteria registry and evaluator are real.
- Matching and coverage need to broaden with task complexity.

**Tier-one target**
- Every serious task should be judged against explicit criteria, not generic agent taste.

**Detailed scope**
- Resolve relevant criteria by task family, domain, project, and workflow stage.
- Block or warn appropriately when evidence is missing.
- Preserve evaluation artifacts and resolution state.

**Implementation tracks**
- Improve criteria applicability resolution.
- Expand workflow-stage-level criteria support.
- Tighten feedback loops between criteria findings and remediation planning.

**Dependencies**
- Workflow contracts
- Evaluation evidence capture

**Exit evidence**
- Criteria application is predictable and inspectable.
- Evaluation findings become a reliable part of closeout.

### 15. Standards Health / Project-Quality Scoring

**Current state**
- Standards health snapshots and project health UI exist.
- Scores still need more remediation depth and broader, consistent domain coverage.

**Tier-one target**
- Scores should explain exactly where a project falls short and what to fix first.

**Detailed scope**
- Cover architecture, testing, maintainability, security, UX, observability, docs, launch readiness, agent-readiness, and standards compliance.
- Show deltas, evidence, unknowns, and remediation priority.
- Support multi-project comparison.

**Implementation tracks**
- Improve standards profile coverage.
- Add better remediation-path generation.
- Tighten consistency across project types and inventory quality.

**Dependencies**
- Capability truth
- Standards registry breadth
- Project inventory quality

**Exit evidence**
- Health scores are actionable, not decorative.
- Backfill recommendations are prioritized and concrete.

### 16. Capability Truth / Explainable Metrics

**Current state**
- TrustedSignal contracts and capability audit exist.
- Some surfaces still rely on seeded or missing data patterns.

**Tier-one target**
- Every visible metric should disclose source, confidence, freshness, and missing-data reason.

**Detailed scope**
- Distinguish confirmed, inferred, missing, and contradictory values consistently.
- Cover projects, automations, prompt library, knowledge, RTK, and later surfaces.
- Make contradiction visible rather than smoothing it away.

**Implementation tracks**
- Expand TrustedSignal coverage.
- Remove confusing seed-data ambiguity where possible.
- Improve UI explanations and drill-down paths.

**Dependencies**
- Data ingestion quality
- Standards health
- Automation history coverage

**Exit evidence**
- Operators can tell what is real, inferred, or missing instantly.
- Metric trust increases rather than decreases with surface breadth.

### 17. Project Health / Standards Delta Views

**Current state**
- Project pages and quality pipeline views exist.
- Delta views are present but not yet fully recommendation-driven.

**Tier-one target**
- AIOS should tell you not just that a project is weak, but the best next backfill path.

**Detailed scope**
- Show the largest deltas by domain.
- Tie deltas to standards, evidence, and recommended remediation work.
- Support active-project triage at the portfolio level.

**Implementation tracks**
- Improve health-to-remediation mapping.
- Add “what to do next” surfaces for deltas.
- Connect delta output to workflow routing and roadmap generation.

**Dependencies**
- Standards health
- Capability truth
- Query layer

**Exit evidence**
- Delta views directly influence task selection and standards backfill workflows.

## Group 4: Reusable Asset And Learning Loops

### 18. Prompt / Skill / Workflow Lifecycle Registry

**Current state**
- Prompt registry, workflow registry, and skills registry exist.
- Lifecycle behavior is fragmented and not uniformly evidence-backed.

**Tier-one target**
- Reusable assets must behave like governed product infrastructure, not text blobs.

**Detailed scope**
- Track name, purpose, applicability, version, status, owner/history, evidence, and failure modes.
- Support promotion, revision, and deprecation flows.
- Connect assets to workflows and task families where they succeed or fail.

**Implementation tracks**
- Normalize lifecycle metadata across prompts, skills, and workflows.
- Expand evidence capture from telemetry and evaluations.
- Improve operator surfaces for asset status and recommendation logic.

**Dependencies**
- Workflow contracts
- Prompt library visibility
- Experiment evidence

**Exit evidence**
- Asset recommendations become trustable and explainable.
- Promotion/deprecation decisions are evidence-backed.

### 19. Workflow Contracts And Library

**Current state**
- Workflow registry already models stage kinds, required skills, output contracts, and validations.
- Planning did not previously give workflow contracts their own first-class requirement block.

**Tier-one target**
- Workflows should be stage-based contracts with explicit inputs, outputs, validations, gates, artifacts, and writeback behavior.

**Detailed scope**
- Model each workflow as a deterministic or bounded-heuristic sequence of stages.
- Bind required prompts, skills, tools, standards, validations, approval gates, and expected artifacts to each stage.
- Record stage-level execution and stage-level success/failure.
- Compare workflows by effectiveness and revise or retire them from evidence.

**Implementation tracks**
- Expand workflow schema to include approvals, artifacts, writebacks, and stage success models.
- Add stage-level telemetry and evaluation state.
- Teach routing and packet generation to consume workflow contracts directly.
- Add workflow comparison and promotion/deprecation loops.

**Dependencies**
- Routing quality
- Prompt/skill lifecycle metadata
- Run state and evaluation evidence

**Exit evidence**
- Workflows are explicit, inspectable contracts rather than loose registry hints.
- Stage-level evidence exists for real runs.

### 20. Workflow Learning Loop

**Current state**
- Workflow learning events and audits exist.
- Current learning is real but not yet selective and prescriptive enough.

**Tier-one target**
- Repeated execution should produce better workflows and better routing decisions.

**Detailed scope**
- Capture workflow evidence, no-learning cases, and failure modes.
- Connect learning to prompt, skill, and packet effectiveness.
- Surface which workflows reduce rework and which create drift.

**Implementation tracks**
- Improve evidence classification quality.
- Tie workflow outcomes to route-quality feedback.
- Build “use this workflow next time” recommendation logic from evidence.

**Dependencies**
- Workflow contracts
- Run closeout integrity
- Prompt/skill experiment evidence

**Exit evidence**
- Workflow recommendations improve over time from reviewed outcomes.

### 21. Conservative Self-Improvement

**Current state**
- Divergent strategy, experiment surfaces, and promotion lifecycle primitives exist.
- Risk remains that experimentation could outrun governance.

**Tier-one target**
- AIOS should improve itself conservatively, with provenance and reversibility.

**Detailed scope**
- Propose improvements to prompts, skills, workflows, packets, and evaluations.
- Require review for high-impact promotion.
- Preserve why an improvement is recommended and what evidence supports it.

**Implementation tracks**
- Tighten proposal generation and approval boundaries.
- Improve ranking of which experiments matter.
- Prevent silent policy mutation from low-trust evidence.

**Dependencies**
- Approval gates
- Workflow learning
- Asset lifecycle registry

**Exit evidence**
- AIOS gets better without becoming less predictable.

### 22. Prompt / Skill Experiments

**Current state**
- Experiment routes and workflow skill experiment tables exist.
- Connection to production routing and promotion remains partial.

**Tier-one target**
- Experiments should feed asset lifecycle decisions and route recommendations directly.

**Detailed scope**
- Compare prompt, skill, and workflow variants.
- Track win/loss/neutral outcomes with rationale.
- Feed promotion, revision, and deprecation decisions.

**Implementation tracks**
- Improve experiment metadata and linkage to assets.
- Add experiment outcome summaries for operators.
- Tie experiment wins to candidate promotion proposals.

**Dependencies**
- Asset lifecycle registry
- Workflow learning
- Evaluation evidence

**Exit evidence**
- Experimental results change asset recommendations in a controlled, visible way.

## Group 5: Operator Surfaces And Reliability

### 23. Operator Command Center UI

**Current state**
- The app already has many useful routes and inspection surfaces.
- Some surfaces still expose partial, seeded, or low-trust concepts.

**Tier-one target**
- The UI should be the place where the governed operating loop is visible and actionable.

**Detailed scope**
- Cover projects, runs, workflows, prompts, knowledge, query, approvals, deltas, automations, and experiments.
- Expose receipts, routing decisions, evidence, and next actions.
- Prefer decision-oriented surfaces over dashboard theater.

**Implementation tracks**
- Improve trust labeling across pages.
- Reduce fallback ambiguity.
- Add “what should happen next” and “why” to more surfaces.

**Dependencies**
- Capability truth
- Query layer
- Workflow and writeback quality

**Exit evidence**
- Operators can run serious work through AIOS with less manual prep than direct tool hopping.

### 24. Automations Observability

**Current state**
- Automation state and history surfaces exist, but durable history is sparse.

**Tier-one target**
- Automations should be visible as governed operational actors with real history and follow-up state.

**Detailed scope**
- Track status, success rate, failures, next run, missed runs, approvals, and writeback blockers.
- Distinguish configured automation from observed healthy automation.
- Surface follow-up paths when automations are stale or missing evidence.

**Implementation tracks**
- Expand durable automation history ingestion.
- Improve missed-run and provenance handling.
- Tie automation evidence into health, query, and approval surfaces.

**Dependencies**
- Automation run history coverage
- Capability truth
- Operator surfaces

**Exit evidence**
- Automation health is durable and explainable across the configured set.

### 25. Corpus / Regression Harness

**Current state**
- A real corpus harness and self-tests already exist.

**Tier-one target**
- As AIOS becomes more central, the harness must keep protecting real operating flows from silent regressions.

**Detailed scope**
- Test command surfaces, workflow behavior, packet outputs, hook side effects, and state persistence.
- Add oracles for newly tier-one-critical flows.
- Separate smoke confidence from full-system confidence.

**Implementation tracks**
- Expand suites for routing, packet quality, lifecycle closeout, and operator answers.
- Add more realistic dirty/brownfield/workspace cases.
- Tie regressions back to roadmap phases and functionality groups.

**Dependencies**
- Runtime maturity
- Packet schema stability
- Workflow contracts

**Exit evidence**
- Regressions in default-layer flows are caught early and reproducibly.

### 26. CTS / Repository Intelligence

**Current state**
- CTS exists as a prototype/sidecar intelligence subsystem with graph stores and query enrichment.

**Tier-one target**
- CTS should become a reliable bounded source of repo understanding for packets, query answers, and project memory.

**Detailed scope**
- Support architecture/context extraction without replacing authoritative source files.
- Contribute to project grounding, repo understanding, and query answers.
- Preserve its sidecar role unless and until reliability is much higher.

**Implementation tracks**
- Improve indexing quality, coverage, and relevance.
- Tighten CTS-to-query and CTS-to-packet integration.
- Define clear fallback behavior when CTS data is absent or stale.

**Dependencies**
- Project inventory
- Query surfaces
- Context compiler

**Exit evidence**
- CTS meaningfully improves repo understanding for serious tasks while staying bounded and inspectable.

### 27. Architecture Enforcement / Quality Gates

**Current state**
- Architecture enforcement, lint, type, CI, and quality gates exist.

**Tier-one target**
- Quality gates must remain connected to AIOS standards resolution and visible project deltas.

**Detailed scope**
- Enforce architecture boundaries, repo discipline, and stack-specific rules.
- Feed failures into standards health and remediation.
- Preserve local-first reproducibility for operator verification.

**Implementation tracks**
- Tighten integration between enforcement outputs and delta scoring.
- Improve project-profile coverage.
- Ensure critical gates are visible in project health and run closeout.

**Dependencies**
- Standards health
- Capability truth
- Project inventory

**Exit evidence**
- Quality gates materially influence health scoring and remediation planning.

## Workflow Library Detail

Detailed per-workflow contract planning now lives in [WORKFLOW_MATRIX.md](/Users/jakyeamos/AIOS/.planning/WORKFLOW_MATRIX.md).

### Current Governed Workflows In Registry

| Workflow | Current State | Tier-One Need | Planning Ownership |
|---|---|---|---|
| `implementation-delivery` | Exists | Needs richer stage contract, stronger route criteria, prompt/handoff integration, and stage evidence | Phase 1, Phase 3, Phase 8 |
| `failure-recovery` | Exists | Needs explicit debug/failure-recovery gates, retest expectations, and better lifecycle/closeout semantics | Phase 1, Phase 3, Phase 6, Phase 8 |
| `academic_paper_v1` | Exists | Useful as proof of workflow contract richness; not central to AIOS core but valuable for asset/workflow modeling | Phase 8 |
| `divergent-strategy` | Exists | Needs stronger integration with learning, promotion, and conservative governance boundaries | Phase 5, Phase 8, Phase 9 |

### Planned Workflow Families That Must Reach Tier One

These come from the product vision and should become explicit governed workflows, not ad hoc agent habits.

#### Audit-only workflow

- Route for evaluation without implementation.
- Must produce scoped findings, evidence, risk level, and next actions.
- Strong fit for standards backfill, repo review, launch readiness, and architecture review.

#### Audit-and-implement workflow

- Route for “fix it, not just evaluate it.”
- Must include prechecks, implementation constraints, verification, and closeout writebacks.
- Strong fit for implementation delivery and bugfix work.

#### PRD / requirements generation workflow

- Route for vague product or feature intent.
- Must gather context, frame goals, extract requirements, and preserve scope boundaries.
- Strong fit for brownfield/new-project planning and research-to-plan conversion.

#### Test-first implementation workflow

- Route for code changes where execution-first verification and strong regression confidence matter.
- Must create or identify executable checks before implementation.
- Strong fit for core/shared logic modifications.

#### Repo cleanup workflow

- Route for structural simplification and cleanup.
- Must respect repo-boundary discipline and destructive-action approval gates.
- Strong fit for backfills, architecture cleanup, and maintenance passes.

#### UI polish workflow

- Route for operator-surface refinement only after backend trust exists.
- Must include UI rules, evidence-backed deltas, and behavior verification.
- Strong fit for Phase 10-adjacent work.

#### Security review workflow

- Route for auth, secret handling, security-sensitive architecture, or risk acceptance work.
- Must bind security criteria and threat-model reasoning explicitly.

#### Prompt experiment workflow

- Route for trying competing prompt patterns with explicit evidence capture.
- Must feed the asset lifecycle and workflow-learning loops.

#### Standards backfill workflow

- Route for closing known quality gaps against standards.
- Must start from delta scoring, prioritize remediation, and preserve evidence at closeout.

#### Codebase architecture review workflow

- Route for repo understanding and boundary risk review.
- Must use codebase map, CTS/repo intelligence, architecture enforcement, and remediation suggestions.

#### Research-to-plan conversion workflow

- Route for taking research artifacts into requirements and roadmap form.
- Must preserve provenance from findings to scoped plans.

#### Project truth update workflow

- Route for truth-file refresh and decision capture.
- Must distinguish proposal from accepted truth and preserve reasons for updates.

#### Agent handoff generation workflow

- Route for creating execution-ready packets for another agent or harness.
- Must include constraints, context, standards, required checks, prompt family, and writeback expectations.

## Immediate Planning Rules

1. Do not treat any current capability as “covered” merely because a broad phase exists.
2. Before phase planning, read both [FUNCTIONALITY_MAP.md](/Users/jakyeamos/AIOS/.planning/FUNCTIONALITY_MAP.md) and this file to ensure every relevant functionality contract is represented in the plan.
3. When a workflow is touched, plan both:
   - the workflow contract itself
   - the prompt/skill/tool bindings and evidence model around it
4. When a new functionality appears in code or vision, add it to both:
   - [FUNCTIONALITY_MAP.md](/Users/jakyeamos/AIOS/.planning/FUNCTIONALITY_MAP.md)
   - this file

---
*Last updated: 2026-05-13 after expanding functionality planning depth*
