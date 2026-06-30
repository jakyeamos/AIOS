# Graph-Native Memory Backfill Plan

Phase 12 Plan 12-07 inventory for upgrading existing AIOS memory hotspots into Layer B facts and Layer C relationships. This document does not perform the backfill; it gives a future agent concrete rows and edges to create.

Priority guide:

- `P0`: missing structure is actively causing memory loss or flat retrieval today, matching `docs/audits/graph-native-memory-audit.md`.
- `P1`: missing structure weakens retrieval quality or packet completeness.
- `P2`: useful structure, but not currently a blocker.

Scope guide:

- `stable-prefix`: durable enough to appear in stable memory/context prefixes.
- `dynamic`: task/run-specific and usually compiled only when relevant.
- `global`: applies across AIOS or all linked projects.
- `project`: scoped to one project or subsystem.

Required category coverage: project truth files, PRDs, agent rules, user preference files,
long-term memory notes, repo decision logs, code quality rules, prompt libraries or skill files,
AIOS design specs, and wiki/context pages.

## P0 Backfill Entries

| Hotspot | Current memory value | Missing structure | Recommended Layer B facts | Recommended Layer C relationships | Prefix | Scope | Priority |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `PROJECT.md` | Canonical current AIOS project truth, subsystem list, implemented milestones, guardrails, and missing work. | Truth is long-form prose; model packets cannot query individual current facts, guardrails, or missing items with status/provenance. | Create facts for AIOS identity, four implemented subsystems, SQLite/Vault/staging guardrails, current missing capabilities, and each recent implemented-on section. | `belongs_to_project` from facts to `aios`; `supports` from implemented facts to related requirements; `has_constraint` from guardrails to project; `has_status` from missing-work facts to open. | stable-prefix | global + project | P0 |
| `.planning/PROJECT.md` | Planning authority for project identity, constraints, decisions, and evolution policy. | Decision table remains prose and decisions are not linked to later phase plans or requirements. | Create facts for operating-system v1 scope, agents-as-primary-user, default-layer success gate, and canonical workflow test. | `decided_in` from decision facts to `.planning/PROJECT.md`; `supports` to roadmap phases; `has_constraint` for local-first, governance, brownfield continuity, explainability, and compounding memory. | stable-prefix | global | P0 |
| `.planning/STATE.md` | Current roadmap position, latest completed plan, progress counts, quick-task history, and active plan pointer. | Active position and completed work are not decomposed into queryable facts or relationships; agents must read the whole file. | Create facts for active milestone, active phase, active plan, latest completed phase, latest completed plan, completed plan count, and dependency chain. | `depends_on` edges from active phase to completed chain; `has_status` from plan facts to complete/active; `implemented_by` from latest-plan facts to summary files. | dynamic | project | P0 |
| `docs/audits/graph-native-memory-audit.md` | Source audit of memory loss hotspots, flat retrieval, provenance gaps, prompt caching opportunities, and ranked recommendations. | Recommendations are a Markdown table, not actionable fact/relationship inputs for compiler and backfill routing. | Create one fact per ranked recommendation with impact, effort, target files, and evidence summary. | `derived_from` each recommendation to audit sections; `blocks` from memory-loss facts to Phase 12 compiler quality; `supports` from recommendations to Plans 12-02 through 12-08. | stable-prefix | project | P0 |
| `bin/hook-prompt-submit.py` plus `config/retrieval-policy.json` | Prompt-time retrieval policy and injected context behavior. | Retrieval traces are not persisted as structured selected/skipped candidates with scores, stale/conflict status, or injected hashes. | Create facts for each retrieval source category: prompt templates, open bugs, handoff decisions, active rules, wiki snippets, reusable prompt hints. | `derived_from` retrieval facts to config policy; `has_risk` to missing trace persistence; `supports` to prompt construction; `blocks` to provenance auditability until trace rows exist. | dynamic | global | P0 |
| `bin/hook-stop.py` and `memory_updates` in `schema.sql` | Session closeout writes summaries, changes, risks, open questions, writebacks, standards health, and learning signals. | `memory_updates` stores compact JSON lists without item-level source, criterion, artifact, or packet-section edges. | Create facts for memory summary, each change item, risk item, and open question with status and source session/run. | `implemented_by` from change facts to artifacts; `has_risk` from project/run to risk facts; `has_open_question` from project/run to open questions; `derived_from` to session/run ids. | dynamic | project | P0 |
| `bin/vault-search.py` and `aios/context/packets/knowledge.obsidian-routing.md` | Vault search supports flat grep/tag/project/handoff lookup; packet states intended MOC-first graph routing. | Notes are not represented as graph nodes with backlinks, MOC hierarchy, freshness, or skipped clusters. | Create facts for MOC notes, project notes, handoffs, tags, note titles, freshness, and source paths when retrieved. | `belongs_to_project` notes to projects; `related_to` note backlinks/tags; `derived_from` fact rows to vault source; `supports` retrieved notes to packet sections. | dynamic | project + global | P0 |
| `prompts/registry.json` and `prompts/*.md` | Reusable prompt template metadata and body files for coding, debugging, research, content writing, reasoning, and summarization. | Prompt capabilities are not fact rows linked to task types, evidence, or successful use. | Create facts for prompt template id, task family, description, body path, validation status, and reusable hint status. | `supports` prompt facts to workflow/task families; `implemented_by` prompt facts to files; `evidence_for` prompt facts to `prompts_used` rows. | stable-prefix | global | P0 |
| `config/agent-rules.md` | Global behavioral rules injected into sessions and context packets. | Rules are stable prose and not individual constraint facts or causal links to failures they prevent. | Create one fact per rule with title, applicability, enforcement status, and stable-prefix eligibility. | `has_constraint` from AIOS to each rule; `caused_by` or `derived_from` from recurring failure records where known; `supports` to success criteria and commit ladder gates. | stable-prefix | global | P0 |

## P1 Backfill Entries

| Hotspot | Current memory value | Missing structure | Recommended Layer B facts | Recommended Layer C relationships | Prefix | Scope | Priority |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `.tracker/PROJECT_TRUTH.md` | Tracker-facing project truth snapshot. | Potential divergence from `PROJECT.md` is not tracked as relationship state. | Create facts for tracker project identity, current status, and known deltas from root truth. | `contradicts` or `supports` between tracker facts and root `PROJECT.md` facts; `has_status` for stale/current. | stable-prefix | project | P1 |
| `docs/adr/0001-explicit-state-layers.md`, `docs/adr/0002-control-plane-run-and-packet-ledger.md`, `docs/adr/0003-tmcp-decision-graph-traversal.md` | Durable architecture decisions for state layers, run/packet ledger, and TMCP traversal. | ADR decisions are not connected to current code surfaces or roadmap phases. | Create facts for each decision, accepted rationale, affected subsystem, and consequences. | `decided_in` from facts to ADRs; `implemented_by` to schema/services; `supports` to roadmap phases; `depends_on` between decisions where applicable. | stable-prefix | global | P1 |
| `docs/superpowers/specs/*.md` | AIOS design specs for workflow orchestration, prompt library, success criteria, standards delta, architecture enforcement, UI command center, and improvement engine. | Spec claims are not linked to implemented surfaces, superseded scope, or current status. | Create facts for spec goals, key constraints, target components, and implementation status. | `implemented_by` from spec facts to services/UI/routes; `supersedes` from newer specs to older architecture notes; `supports` to requirements. | stable-prefix | project | P1 |
| `docs/evals/*.md` and `docs/evals/templates/*.md` | Eval architecture, context profiles, templates, failure records, shadow branch comparisons, and portable packet vocabulary. | Eval vocabulary is not queryable as stable facts for packet/eval routing. | Create facts for context profiles, portability labels, failure taxonomy, eval minimum checklist, and anti-cheating rules. | `has_constraint` from eval workflows to anti-cheating facts; `supports` from templates to eval run tasks; `belongs_to_project` to AIOS. | stable-prefix | global | P1 |
| `config/success-criteria/registry.json` and `spec/success-criteria/*.md` | Success criteria registry and individual gate docs. | Criteria are structured JSON/docs but not memory facts connected to file patterns and workflows. | Create facts for criterion id, title, blocking level, domain signals, and required evidence. | `supports` from criteria to workflows; `has_constraint` from task families to criteria; `evidence_for` from findings to criteria. | stable-prefix | global | P1 |
| `config/standards/registry.json` and `aios/context/standards/*.md` | Standards definitions and context compiler standards. | Standards are selected by context compiler but not represented as facts with relationships to failures, gates, or projects. | Create facts for standard id, quality dimension, applies_when signals, and current authority. | `has_constraint` from projects/tasks to standards; `supports` to quality gates; `derived_from` to source docs. | stable-prefix | global | P1 |
| `config/execution-strategies/*.json` | Model routing, strategy, and task-spec policy. | Routing choices are not memory facts linked to observed quality/cost outcomes. | Create facts for strategy ids, model tiers, task classes, and promotion status. | `supports` from strategy to task families; `evidence_for` from eval/shadow runs; `has_status` for active/candidate/deprecated. | stable-prefix | global | P1 |
| `docs/workflows/*.md` and `config/workflows/*.json` | Workflow registry and workflow docs. | Workflow contracts are not decomposed into stage facts, required gates, or approval relationships. | Create facts for workflow key, stages, gate requirements, approval policy, and validation expectations. | `depends_on` between stages; `has_constraint` for gates; `supports` to task families and skills. | stable-prefix | global | P1 |
| `skills/*/SKILL.md` and `skills/*/references/*.md` | Local reusable skills and references. | Skill capabilities are not linked to routing cases, workflows, source provenance, or maturity. | Create facts for skill name, trigger, capabilities, reference files, and promotion status. | `supports` skill-to-workflow/task relationships; `derived_from` to harvested source; `has_status` candidate/approved/local. | stable-prefix | global | P1 |
| `aios/context/features/*.md`, `aios/context/packets/*.md`, `aios/context/domains/*.md`, `aios/context/projects/*.md` | Context compiler routing nodes and packets. | Context files have frontmatter and receipts but are not Layer B/C facts for memory compiler use. | Create facts for context id, tier, applies_when, source_refs, stale areas, and load_if_matched links. | `supports` context to task domains; `depends_on` load_if_matched edges; `contradicts` from conflicts metadata. | stable-prefix | global + project | P1 |

## P2 Backfill Entries

| Hotspot | Current memory value | Missing structure | Recommended Layer B facts | Recommended Layer C relationships | Prefix | Scope | Priority |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `docs/plans/2026-04-01-ai-history-import.md` and `docs/specs/2026-04-01-ai-history-import-design.md` | Historical AI history import design and plan. | Useful lineage is not linked to current import scripts or known limitations. | Create facts for import provider support, staging policy, key exchange extraction, and limitations. | `implemented_by` to `bin/import_ai_history.py` and `bin/cron-ingest-codex.py`; `has_risk` for summary-only structured storage. | dynamic | project | P2 |
| `docs/architecture/notebooklm-mcp-addon.md`, `docs/contracts/notebooklm-mcp-cli-contract.md`, `aios/policies/notebooklm-routing.md`, `aios/context/packets/knowledge.notebooklm-routing.md` | NotebookLM bounded synthesis policy and backend contract. | Route policy is not linked to source-bundle safety and provenance facts. | Create facts for route kinds, rejection cases, backend experimental status, and staging rules. | `has_constraint` from NotebookLM route to safety policy; `supports` bounded synthesis workflows; `has_status` experimental/unavailable. | stable-prefix | global | P2 |
| `config/personalized-humanizer/*.json` and `skills/personalized-humanizer/SKILL.md` | Personalized writing/humanizer configuration and skill. | Personalization rules are not separated into preference facts with sensitivity/scope. | Create facts for allowed voice dimensions, retrieval policy, eval criteria, and privacy constraints. | `has_constraint` from humanizer workflow to privacy facts; `supports` to writing tasks. | stable-prefix | global | P2 |
| `config/operator-surfaces/search-policy.json` | Operator search policy. | Search policy is not linked to entity kinds and graph expansion opportunities. | Create facts for searchable entity kinds, ranking rules, and drilldown expectations. | `supports` from policy to operator search services; `related_to` entity kinds to memory layers. | stable-prefix | project | P2 |
| `docs/wiki-maintenance.md` and `config/wiki-maintenance/critical-pages.json` | Wiki maintenance rules and critical context page inventory. | Maintenance state is not represented as facts tied to stale context and source refs. | Create facts for critical page ids, expected metadata, validation cadence, and stale state. | `has_status` current/stale; `supports` context validation; `derived_from` to wiki maintenance config. | stable-prefix | global | P2 |
| `docs/evals/templates/backfill-hotspot.md` and PRD-like planning docs under `docs/plans/` | Backfill templates and PRD-style planning records capture intended behavior and acceptance expectations. | PRD facts are not queryable by requirement, acceptance criterion, implementation status, or supersession state. | Create facts for PRD title, objective, acceptance criteria, linked requirements, current status, and owner/source file path. | `supports` from PRD facts to roadmap phases; `implemented_by` to code/docs; `supersedes` where later plans replace older PRD scope. | stable-prefix | project | P2 |
| `config/quality-pipeline.json`, `config/standards/registry.json`, and `docs/backfill/agent-eval-backfill.md` | Code quality rules, standards gates, and backfill hotspot records. | Quality expectations are spread across JSON registries and prose, not relationship-linked to task families or failures. | Create facts for each code quality rule/gate, severity, required evidence, and adoption/backfill mode. | `has_constraint` from projects and task families to quality facts; `evidence_for` from quality runs and findings; `has_status` active/warn-only/blocking. | stable-prefix | global | P2 |
| Long-term memory notes from `memory_updates`, `aios/context/handoffs/latest.md`, and vault handoff/project notes | Durable session lessons, handoffs, and project-specific long-term memory. | Long-term memory notes are retrievable only as flat summaries, not facts with status, project scope, source span, or related decisions. | Create facts for recurring lesson, unresolved risk, open question, accepted decision, and follow-up status. | `derived_from` to session/handoff source; `has_open_question` and `has_risk` to project/run; `supports` future packet sections. | dynamic | project | P2 |
| User preference files: `config/personalized-humanizer/profile.json`, `config/personalized-humanizer/retrieval-policy.json`, and `config/retrieval-policy.json` | User preference and retrieval behavior for voice, context, and prompt-time memory. | Preferences are not separated from operational policy or marked by sensitivity, scope, confidence, and review date. | Create facts for preference name, value, scope, sensitivity class, confidence, and source file path. | `has_constraint` from workflows to preferences; `belongs_to_project` for project-specific preferences; `has_status` active/uncertain/archived. | stable-prefix | global | P2 |

## First Backfill Run Recommendation

Start with these P0 entries:

1. `PROJECT.md`
2. `.planning/STATE.md`
3. `docs/audits/graph-native-memory-audit.md`
4. `bin/hook-prompt-submit.py` plus `config/retrieval-policy.json`
5. `bin/hook-stop.py` plus `memory_updates`
6. `config/agent-rules.md`

These entries directly address the audit’s highest-impact memory loss findings: prompt-time retrieval traces are lost, closeout memory is flattened, stable project truth is trapped in prose, and agent rules are injected as unstructured text instead of reusable constraint facts.

## Backfill Row Shape

For each extracted fact:

- `fact_text`: one concise claim.
- `entity`: project, subsystem, workflow, rule, prompt, source file, or decision.
- `predicate`: human-readable predicate, such as `has_constraint`, `has_status`, or `supports`.
- `object_value`: target value when no separate fact id exists.
- `project_scope`: `aios`, a linked project id, or `global`.
- `validity_status`: `active`, `superseded`, `contradicted`, `uncertain`, or `archived`.
- `source_id`: Layer A raw source id for the file or row.
- `confidence`: `0.8` or higher for authoritative truth/config; lower for inferred relationships.

For each relationship:

- `subject_id`: source fact id.
- `predicate`: one of `services.memory_layers.ALLOWED_PREDICATES`.
- `object_id`: target fact, source, project, decision, or artifact id.
- `project_scope`: `aios`, linked project id, or `global`.
- `confidence`: match source authority and extraction certainty.
- `source_id`: Layer A raw source id.

## Guardrails

- Do not backfill raw private logs into stable-prefix memory.
- Do not turn stale or historical plans into `active` facts unless a current truth file confirms them.
- Do not collapse contradictions. Use `contradicted` facts and `contradicts` relationships.
- Prefer source paths and stable ids over long excerpts.
- Keep global rules separate from project-scoped facts so future packets can compile the smallest sufficient memory.
