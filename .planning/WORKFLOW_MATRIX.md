# AIOS Workflow Matrix

**Created:** 2026-05-14  
**Purpose:** Define the workflow library as a first-class planning surface. Each workflow below is mapped as a contract with trigger conditions, stage structure, prompt family, required skills/tools, validations, approval gates, artifacts, writebacks, learning signals, and tier-one gaps.

## How To Read This Matrix

- **Current** workflows already exist in `config/workflows/registry.json`
- **Planned** workflows are required by the AIOS product vision and detailed functionality plan, even if they are not yet implemented as governed registry entries
- **Tier-one gap** defines what must become true before the workflow can count toward default operating layer readiness

## Common Contract Fields

Every tier-one workflow should ultimately have:

- trigger conditions
- task family and route rationale
- stage contract
- prompt family or template selection
- required skills and tools by stage
- standards / success-criteria bindings
- approval gates
- required artifacts
- writeback behavior
- learning and promotion signals

## Registry Stage Kinds

Current workflow registry stage kinds:

- `parse_request`
- `normalize_prompt`
- `enrich_context`
- `generate`
- `transform`
- `validate`
- `finalize`

Tier-one expectation: these stage kinds should remain bounded and inspectable, but workflows may bind additional stage-local policies, approvals, artifacts, and evidence requirements.

## Current Governed Workflows

| Workflow | Status | Trigger Conditions | Current Stage Shape | Prompt Family | Required Skills | Required Validations | Approval Gates | Expected Artifacts | Writebacks | Learning Signals | Roadmap Ownership | Tier-One Gap |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `implementation-delivery` | Current / partial | feature implementation, build, refactor, scoped code change | `parse_request -> normalize_prompt -> validate -> finalize` | `prompt_library_normalizer` plus future implementation-handoff family | `prompt_library_normalizer`, `scope_check` | `scope_check` | currently implicit; should gate destructive actions, truth updates, and standards-affecting changes | scoped plan, changed files, validation checklist, route metadata, packet id | project truth updates, follow-up items, no-learning or workflow evidence, prompt/workflow observations | route quality, packet quality, validation pass rate, rework rate, prompt effectiveness | Phase 1, Phase 2, Phase 3, Phase 5, Phase 6, Phase 8, Phase 9 | Needs richer stage contract, explicit execution/check stages, standards binding, approval behavior, and stage-level evidence |
| `failure-recovery` | Current / partial | debug, broken run, regression, recovery task | `parse_request -> normalize_prompt -> validate -> finalize` | `prompt_library_normalizer` plus future failure-recovery prompt family | `prompt_library_normalizer`, `scope_check` | `scope_check` | should gate risky rollback/destructive repair paths and truth changes | failure brief, root-cause hypothesis, retest steps, route metadata | failure learning evidence, follow-up tasks, truth updates where diagnosis changes project state | recovery success rate, retest completion, false-completion avoidance, repeat-failure rate | Phase 1, Phase 3, Phase 5, Phase 6, Phase 8, Phase 9 | Needs explicit debugging stages, execution-first verification, retest evidence, and better blocked/partial lifecycle handling |
| `academic_paper_v1` | Current / bounded side workflow | paper-writing or essay-style requests | `parse_request -> normalize_prompt -> enrich_context -> generate -> transform -> validate -> finalize` | prompt-library normalization plus academic-writing family | `prompt_library_normalizer`, `obsidian_corpus_retriever`, `academic_draft_generator`, `personal_corpus_humanizer`, validation checkers | `structure_checker`, `citation_checker`, `meaning_preservation_checker` | low governance risk; should still gate citation or meaning-integrity failures | structured draft, transformed prose, validation summary | prompt/performance observations, potential reusable writing asset evidence | prompt success, structure quality, citation quality, meaning-preservation outcomes | Phase 8, Phase 9 | Already closest to a stage-rich workflow contract; mainly useful as a proof shape for broader workflow-library hardening |
| `divergent-strategy` | Current / partial | strategy questions, architecture decisions, prompt/skill/workflow evaluation, multiple plausible approaches | `parse_request -> generate -> validate -> finalize` | future strategy-evaluation prompt family plus candidate/judge prompts | `divergent_task_classifier`, `divergent_candidate_generator`, `divergent_judge_panel`, `divergent_portfolio_selector`, `memory_writeback_proposer` | `divergent_judge_panel` | should gate promotion of conclusions into prompts, skills, workflows, or memory | task classification, candidates, judgments, portfolio, entropy observation, writeback proposals | approval-gated HOW/WHAT/FAILURE/ENTROPY proposals | experiment quality, portfolio usefulness, accepted writeback rate, entropy/useful-failure yield | Phase 5, Phase 8, Phase 9 | Needs stronger boundaries between experimentation and promoted truth, plus better integration with asset lifecycle and route recommendation |

## Planned Tier-One Workflow Families

These workflows do not yet have full governed registry entries but should become explicit workflow contracts.

| Workflow Family | Status | Trigger Conditions | Planned Stage Shape | Prompt Family | Required Skills / Tools | Required Validations | Approval Gates | Expected Artifacts | Writebacks | Learning Signals | Roadmap Ownership | Tier-One Gap |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Audit-only | Planned | “review this”, “what do you think”, standards audit, architecture review, launch readiness audit | `parse_request -> normalize_prompt -> enrich_context -> validate -> finalize` | audit/review prompt family | context compiler, grounded query, standards selectors, repo intelligence, review checkers | standards coverage, evidence sufficiency, scope integrity | approve if converting findings into truth changes or backfill plans | findings list, severity ordering, evidence trail, remediation suggestions | findings, follow-up tasks, truth updates when accepted | finding usefulness, false-positive rate, remediation adoption | Phase 1, Phase 2, Phase 4, Phase 6, Phase 7 | Needs explicit audit contract and evidence-backed finding format |
| Audit-and-implement | Planned | “make this production-ready”, “fix and improve”, standards backfill with action | `parse_request -> normalize_prompt -> enrich_context -> generate(plan) -> generate(implementation) -> validate -> finalize` | implementation prompt family | route selector, context compiler, execution strategy, code-edit harness, validation checks | criteria resolution, tests/runtime checks, scope check | destructive changes, standards mutations, truth rewrites | plan, changed files, verification evidence, closeout summary | truth updates, writebacks, follow-up items, no-learning or learning signal | rework rate, validation success, writeback usefulness | Phase 1, Phase 2, Phase 3, Phase 5, Phase 6 | Needs to become the main default serious-work workflow contract |
| PRD / requirements generation | Planned | “design this”, “define the product”, “turn this into requirements” | `parse_request -> enrich_context -> generate(requirements) -> validate -> finalize` | PRD / scoping prompt family | research retrieval, prompt family selection, planning validators | scope coherence, requirement testability, missing-constraint detection | approval before promotion into roadmap/truth | requirements doc, scope boundaries, open questions | project truth updates, roadmap follow-up, no-learning or planning-learning evidence | requirement churn, acceptance rate, gap rate | Phase 1, Phase 4, Phase 8, Phase 9 | Needs a dedicated planning contract instead of ad hoc planning conversations |
| Test-first implementation | Planned | core/shared logic change, reliability-sensitive implementation, execution-first cases | `parse_request -> normalize_prompt -> enrich_context -> generate(test plan) -> generate(change) -> validate -> finalize` | TDD / verification-first prompt family | execution strategy, test harness, standards selectors, runtime verifiers | test presence, runtime-path evidence, scope check, regression checks | risky refactors, broad shared-surface changes | test plan, changed files, verification outputs, closeout evidence | truth updates, workflow learning evidence, backfill items | first-pass pass rate, regression catch rate, runtime verification quality | Phase 3, Phase 6, Phase 9 | Needs explicit coupling between execution-first verification and workflow shape |
| Repo cleanup | Planned | cleanup, simplification, dead code removal, architecture cleanup | `parse_request -> enrich_context -> generate(cleanup plan) -> validate -> finalize` | cleanup / maintainability prompt family | architecture enforcement, repo-boundary checks, codebase map, diff summarizer | boundary discipline, destructive-risk checks, validation evidence | destructive edits, broad deletions, truth changes | cleanup plan, change set, risk summary, validation evidence | truth updates, follow-up tasks, cleanup-learning signal | cleanup impact, regressions avoided, simplification quality | Phase 4, Phase 5, Phase 6 | Needs strong destructive-action governance and repo-boundary controls |
| UI polish | Planned | operator UI refinement, UX cleanup, command-center improvements | `parse_request -> enrich_context -> generate(ui plan) -> generate(ui changes) -> validate -> finalize` | UI/UX prompt family | UI rules, anti-slop checks, browser verification, design heuristics | real-data behavior, build/lint, behavior verification | approval for large surface direction changes | UI plan, changed files, verification evidence, screenshots or behavior notes | truth updates, UI findings, prompt/workflow observations | usability improvements, regression rate, trust-label clarity | Phase 6, Phase 7, Phase 10 | Needs stronger “only after backend trust” discipline and UI-specific verification contract |
| Security review | Planned | auth, secrets, OIDC, sensitive architecture, risk acceptance | `parse_request -> enrich_context -> validate -> finalize` | security-review prompt family | security standards, threat-model notes, repo intelligence, policy packets | security criteria, evidence sufficiency, risk classification | approval for accepted risks, policy changes, secrets handling changes | risk summary, findings, acceptance recommendations, remediation path | risk decisions, truth updates, follow-up tasks | false-negative rate, remediation adoption, risk acceptance trace quality | Phase 4, Phase 5, Phase 6 | Needs explicit stage contract and stronger policy/evidence bindings |
| Prompt experiment | Planned | compare prompt patterns, improve prompt routing, evaluate handoff formats | `parse_request -> generate(candidates) -> validate(compare) -> finalize` | prompt-experiment family | prompt registry, experiment logic, evaluation rubric | comparison quality, scope preservation, evidence sufficiency | approval before promotion to active prompt | candidate prompts, comparison results, promotion recommendation | prompt lifecycle proposals, learning evidence | win rate, regression rate, recommendation quality | Phase 8, Phase 9 | Needs direct connection to prompt lifecycle and route recommendation |
| Standards backfill | Planned | “bring this project to standard”, close health gaps, backfill missing quality signals | `parse_request -> enrich_context -> validate(gaps) -> generate(remediation plan) -> finalize` | standards-backfill prompt family | standards health, capability truth, query, repo intelligence | gap evidence quality, remediation prioritization, scope check | approval for large remediation or standards changes | backfill plan, delta summary, remediation priorities | follow-up tasks, truth updates, learning evidence | delta reduction, recommendation usefulness, health-score trust | Phase 4, Phase 6, Phase 7 | Needs tighter coupling between health deltas and executable remediation workflows |
| Codebase architecture review | Planned | brownfield repo understanding, boundary review, architecture drift | `parse_request -> enrich_context -> validate(architecture) -> finalize` | architecture-review prompt family | codebase map, CTS, architecture enforcement, standards packets | architecture evidence, boundary rule coverage, remediation quality | approval if converting findings into large design shifts | architecture findings, risk summary, remediation guidance | truth updates, follow-up tasks, architecture learning evidence | review usefulness, architecture drift detection quality | Phase 2, Phase 4, Phase 6 | Needs explicit workflow contract rather than being spread across codebase map and audits |
| Research-to-plan conversion | Planned | convert research outputs into requirements and roadmap | `parse_request -> enrich_context -> generate(plan) -> validate -> finalize` | planning / synthesis prompt family | research artifacts, roadmap planner, planning validators | coverage, requirement mapping, missing-scope checks | approval before roadmap promotion | requirements, roadmap updates, planning summary | planning truth updates, no-learning or planning-learning evidence | planning gap rate, roadmap churn, acceptance rate | Phase 4, Phase 8, Phase 9 | Needs a reusable planning workflow beyond one-off initialization flows |
| Project truth update | Planned | refresh truth after milestone, big run, architecture shift, or drift | `parse_request -> enrich_context -> generate(update proposal) -> validate -> finalize` | truth-update prompt family | truth files, query, project dossier, writeback system | evidence sufficiency, drift detection, update scope | approval before accepted truth mutation | truth diff proposal, rationale, accepted/rejected outcome | truth updates, decision records, follow-up items | truth freshness, false-update rate, acceptance quality | Phase 4, Phase 5 | Needs to be distinguished clearly from silent writeback behavior |
| Agent handoff generation | Planned | prepare another agent or harness to execute work | `parse_request -> enrich_context -> generate(handoff) -> validate -> finalize` | handoff-generation prompt family | context compiler, workflow contract, prompt selector, standards packets | handoff completeness, constraint coverage, packet integrity | approval for high-impact delegation paths if needed | handoff packet, packet receipt, required checks, acceptance criteria | packet/handoff observations, workflow-learning evidence | handoff success rate, clarification rate, packet completeness | Phase 2, Phase 8, Phase 9 | Needs to become a reusable governed workflow rather than a side effect of packet generation |

## Workflow-Stage Expectations

### `parse_request`

- resolve project and task family
- identify workflow route candidates
- surface ambiguity and stop unsafe guesses
- set initial risk and approval expectations

### `normalize_prompt`

- choose prompt family / template
- preserve objective intent
- normalize wording into a durable handoff contract
- record prompt provenance

### `enrich_context`

- retrieve project truth, standards, packets, prompt assets, repo context, and recent evidence
- record receipts for loaded and skipped context
- surface missing, stale, or contradictory context

### `generate`

- produce the main workflow artifact for the stage:
  - plan
  - draft
  - implementation proposal
  - candidate set
  - remediation path
- preserve constraints and expected artifact structure

### `transform`

- bounded transformation only
- preserve meaning, policy constraints, or structural intent
- emit transformation evidence where relevant

### `validate`

- run the explicit checks bound to the workflow
- emit pass/fail plus issues and evidence
- block false completion where criteria are not satisfied

### `finalize`

- assemble final artifacts
- capture approvals touched
- emit writeback proposals, follow-up items, and learning signals
- persist closeout state and unresolved work

## Workflow Promotion Rules

A workflow should only move toward active tier-one use when:

- its stage contract is explicit
- its required prompt family is defined
- its required skills/tools are bound
- its validations are meaningful and durable
- its approval behavior is explicit
- its expected artifacts are stable
- its writeback behavior is governed
- its learning signals are reviewable

## Immediate Planning Implications

1. Phase 1 planning should explicitly decide which current/planned workflows become the default serious-work routes first.
2. Phase 2 planning should standardize how workflow contracts consume context packets and prompt families.
3. Phase 8 planning should treat workflow schema hardening as equal priority with prompt/skill lifecycle work.
4. Phase 9 planning should compare workflows by outcome quality, rework rate, and writeback usefulness, not just existence.

---
*Last updated: 2026-05-14 after workflow-matrix creation*
