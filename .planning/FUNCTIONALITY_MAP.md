# AIOS Functionality Map

**Created:** 2026-05-13  
**Purpose:** Map all major current or planned AIOS functionalities to the current codebase, tier-one expectations, v1 requirements, and roadmap phases so no important capability is orphaned.

## Status Key

- **Current**: implemented in some meaningful form today
- **Partial**: exists, but not yet at tier-one reliability or scope
- **Planned**: not meaningfully implemented yet, but required by the product definition
- **Tier-One Gap**: what must become true for this functionality to count toward default-layer readiness

## Functionality Matrix

| Functionality | Current Code/Surface | Current Status | Requirements | Roadmap Phase | Tier-One Gap |
|---|---|---|---|---|---|
| Project identification from vague intent | `services/aios_cli.py`, workflow surfaces, project inventory, planning docs | Partial | ROUT-01 | Phase 1 | Must resolve or explicitly block on ambiguity instead of relying on operator guesswork |
| Task classification and workflow routing | `config/workflows/registry.json`, `services/workflow_orchestration.py`, `services/execution_strategy.py` | Partial | ROUT-02, ROUT-03 | Phase 1 | Must choose the smallest sufficient workflow with inspectable rationale |
| Agent/harness recommendation | `services/invocation_backends.py`, managed runtime surfaces, workflow config | Partial | ROUT-04 | Phase 1 | Must consistently attach the right execution surface to the selected workflow |
| Prompt-library selection during routing | `prompts/*`, `prompts/registry.json`, `bin/validate-prompts.py`, `bin/sync-prompts.py`, `bin/hook-prompt-submit.py`, `aios-ui/server/routers/prompts.ts` | Partial | ROUT-04, ASSET-04 | Phase 1, Phase 8 | Must become part of route selection rather than only a passive library/telemetry surface |
| Context compilation | `tools/context-compile.mjs`, `aios/context/**`, `aios-ui/app/context/page.tsx` | Current | CONT-01, CONT-02, CONT-03 | Phase 2 | Must become the default entry path for serious work with stronger project/task-specific packet quality |
| Briefing packet / agent handoff generation | `briefing_packets`, start-work path, context receipts, prompt assets | Partial | CONT-04 | Phase 2 | Must include prompt/handoff instructions and reusable asset choices consistently |
| Run / invocation lifecycle tracking | `orchestration_runs`, `orchestration_invocations`, `orchestration_run_events`, `bin/hook-session-start.py`, `bin/hook-stop.py`, lifecycle audit | Current | RUN-01, RUN-02 | Phase 3 | Must eliminate residual heuristic linkage and meet tier-one handshake coverage |
| Resume / partial completion flow | lifecycle surfaces, session linkage, run state, current planning docs | Partial | RUN-03, RUN-04 | Phase 3 | Must restore packet, state, approvals, and next action cleanly after interruptions |
| Project truth files | `PROJECT.md`, linked project docs, planning truth, context project routers | Partial | TRUTH-01, TRUTH-02 | Phase 4 | Must stay fresher and broader across all major linked projects, not only AIOS itself |
| Knowledge graph / linked knowledge | `knowledge_topics`, `knowledge_references`, `knowledge_relationships`, `aios-ui/server/routers/knowledge.ts` | Current | TRUTH-03, TRUTH-04 | Phase 4 | Must feel like operational knowledge, not just indexed notes |
| Grounded query / inspectable answers | `aios-ui/server/routers/query.ts`, CTS-backed query logic, capability/status answers | Partial | TRUTH-03, OPER-02, OPER-03 | Phase 4, Phase 10 | Must answer default-layer questions before manual context assembly and cite sources reliably |
| Governed writeback proposals | `improvement_writebacks`, `memory_writeback_proposals`, `writebacks` UI, hook closeout | Current | GOV-01, GOV-03, GOV-04 | Phase 5 | Must cover all meaningful writeback classes consistently and surface unresolved follow-up clearly |
| Approval gates | writeback approval flows, router actions, workflow config, governance docs | Partial | GOV-02 | Phase 5 | Must govern high-impact truth/prompt/skill/workflow/standards changes uniformly |
| Success criteria matching | `config/success-criteria/*`, `services/success_criteria.py`, hook integration | Current | STND-01, STND-02, STND-03, STND-04 | Phase 6 | Must broaden task-to-criteria matching and remain evidence-driven under real workload |
| Standards health / project-quality scoring | `services/standards_health.py`, `aios-ui/server/routers/projects.ts`, capability truth | Partial | DELT-01, DELT-02, DELT-03, DELT-04 | Phase 7 | Must tie all major health views to concrete remediation and comparable domain coverage |
| Capability truth / explainable metrics | `services/capability_truth.py`, trusted-signal contracts in UI/server | Current | DELT-02, DELT-03 | Phase 7 | Must expand from seeded/partial surfaces to a more complete default operating scorecard |
| Prompt / skill / workflow lifecycle registry | `config/workflows/skills.json`, `prompts/registry.json`, workflow skill experiment surfaces, divergent strategy promotion lifecycle | Partial | ASSET-01, ASSET-02, ASSET-03, ASSET-04 | Phase 8 | Must unify version, status, evidence, owner/history, and recommendation behavior |
| Workflow learning loop | `workflow_learning_events`, `services/workflow_learning.py`, writebacks, audits | Current | LEARN-01, LEARN-02 | Phase 9 | Must become more selective and more useful for improving routing/packets, not only recording evidence |
| Conservative self-improvement | divergent strategy, experiments, promotion lifecycle, workflow synthesis | Partial | LEARN-03, LEARN-04 | Phase 9 | Must improve future work without silent policy drift or low-trust writebacks |
| Prompt / skill experiments | `aios-ui/server/routers/experiments.ts`, `workflow_skill_experiments`, divergent strategy docs | Partial | ASSET-03, LEARN-01, LEARN-03 | Phase 8, Phase 9 | Must connect experiment outcomes directly to asset promotion and routing recommendations |
| Operator command center UI | `aios-ui/app/**`, `aios-ui/server/routers/_app.ts`, page routes for projects, runs, workflows, prompts, knowledge, query | Current | OPER-01, OPER-02, OPER-03, OPER-04 | Phase 10 | Must expose a trustworthy end-to-end default-layer loop, not partial concepts or seeded fallbacks |
| Automations observability | `automation_run_history`, `aios-ui/server/routers/automations.ts`, capability audit | Partial | RUN-04, GOV-04, OPER-01, OPER-03 | Phase 3, Phase 5, Phase 10 | Must move beyond seeded or sparse history to durable, high-coverage automation evidence |
| Project health / standards delta views | project routers, standards snapshots, quality pipeline, insights router | Partial | DELT-01, DELT-04, OPER-01 | Phase 7, Phase 10 | Must become recommendation-driven and consistent across all priority projects |
| Corpus / regression harness | `scripts/aios-corpus-eval.cjs`, `tests/test_corpus_eval.py`, `docs/aios/corpus/config.json` | Current | STND-03, LEARN-02 | Phase 6, Phase 9 | Must keep protecting real operating flows as more functionality becomes tier-one-critical |
| CTS / repository intelligence | `services/cts/**`, grounded query enrichment, graph stores | Partial | CONT-01, TRUTH-04, OPER-02 | Phase 2, Phase 4, Phase 10 | Must become a reliable source of repo understanding, not just a sidecar prototype |
| Architecture enforcement / quality gates | `services/architecture_enforcement.py`, `.dependency-cruiser.cjs`, CI/local checks | Current | STND-01, STND-02 | Phase 6 | Must stay integrated with standards resolution and visible project deltas |

## Coverage Notes

### Explicitly tightened in requirements/roadmap

These capabilities were previously implied but are now explicitly represented earlier in the execution loop:

- prompt-library selection as part of routing, not only lifecycle management
- prompt/handoff instructions as part of compiled briefing packets
- approvals as a visible part of run closeout
- reusable prompt/skill asset relevance as part of operator answers

### Functionality that already has a home but needs stronger tier-one treatment

- Prompt library: now spans Phase 1, Phase 2, Phase 5, and Phase 8
- Grounded query: should be treated as part of knowledge grounding and operator surfaces, not just a nice-to-have route
- Automations: currently represented in capability truth, but tier-one requires stronger runtime evidence
- CTS/repo intelligence: should support context and knowledge grounding, but remains a bounded sidecar until trust is higher
- Experiments/divergent strategy: should inform conservative learning loops, not become autonomous policy mutation

## Tier-One Checklist By Functionality Group

### Governed entry loop

- project identification
- workflow routing
- agent/harness selection
- prompt/handoff family selection
- context compilation
- durable run state

Tier-one means these feel like one deterministic pipeline, not separate subsystems.

### Truth, governance, and evidence

- truth files
- knowledge surfaces
- grounded query
- writeback proposals
- approval gates

Tier-one means a serious run leaves auditable truth and next actions behind.

### Standards and health intelligence

- success criteria
- standards health
- capability truth
- delta scoring

Tier-one means scores are explainable, actionable, and trusted.

### Reusable improvement loops

- prompt/skill/workflow lifecycle
- workflow learning
- experiments
- conservative self-improvement

Tier-one means reusable assets improve from evidence without silent drift.

### Default operating layer surfaces

- command center UI
- project/knowledge/query/prompt/run/workflow views
- automation and health observability

Tier-one means AIOS can answer what to do next before the operator manually assembles context.

## Immediate Planning Implications

1. Phase 1 and Phase 2 must explicitly own prompt-library selection and handoff composition.
2. Phase 3 and Phase 5 must make approvals and unresolved follow-up first-class runtime outputs.
3. Phase 4 and Phase 10 must treat grounded query as a default-layer capability, not just a convenience route.
4. Phase 7 must make health and delta scoring more obviously tied to concrete remediation.
5. Phase 8 and Phase 9 must separate governed asset promotion from broader experimental autonomy.

---
*Last updated: 2026-05-13 after functionality-to-tier-one mapping*
