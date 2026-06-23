# AIOS Meta-Learning Architecture Audit

Date: 2026-06-23
Phase: 18 Plan 18-01
Requirement: META-01

## Current-State Summary

AIOS already has several learning-adjacent surfaces, but they are split by source and maturity.

Instruction and rule surfaces:

- `AGENTS.md` is the repo-level always-loaded contract for AIOS work.
- `config/agent-rules.md` is loaded through `services/agent_rules.py` and injected as concise rule summaries.
- Rule 11 in `config/agent-rules.md` requires always-loaded agent files to stay thin and pushes intent-specific detail into skills, TMCP routes, packets, checklists, or docs.

Skill, workflow, and command surfaces:

- `config/workflows/skills.json` is the structured skill registry with lifecycle state, allowed stages, schemas, invariants, and side effects.
- `config/workflows/registry.json` owns governed workflow stages, validation bindings, approval gates, prompt bindings, and learning signals.
- `services/skills_harvest.py` can discover and classify instruction/skill candidates, detect duplicate/conflicting sources, redact secrets, and generate a portable skill library.
- `services/aios_cli.py` is the main command surface. New commands should be added deliberately because CLI behavior becomes operational muscle memory for agents.

Learning and writeback surfaces:

- `services/learning_taxonomy.py` defines the current workflow-level signal kinds: repeated failures, ignored rules, bloated packets, weak prompts/workflows, route misroutes, standards regressions, writeback outcomes, and compounding gains.
- `services/learning_analysis.py` detects recurring patterns from SQLite evidence and emits stable pattern IDs with sample size, recurrence, confidence, scope, and suggested remediation class.
- `services/learning_impact.py` builds per-run and rollup views showing signals emitted, assets evidenced, proposals created, and no-learning reasons.
- `services/workflow_learning.py` converts retrospective artifacts into pending review proposals and explicitly sets `auto_apply` to false.
- `schema.sql` already includes `workflow_learning_events`, `improvement_writebacks`, `memory_writeback_proposals`, `retrospective_artifacts`, and `model_selection_records`.

Session and transcript surfaces:

- `services/session_providers/base.py` defines the provider interface and normalized session shape for Claude, Codex, Cursor, and Antigravity sources.
- `services/session_summarizer.py` extracts structured summaries from normalized sessions after redaction, including context used, decisions, files, commands, failures, fixes, follow-ups, reusable patterns, candidate skills, confidence, provenance, and writeback status.
- `services/session_writeback.py` emits proposal-only writeback candidates. It records `memory_writeback_proposals` and does not mutate the vault directly.
- `config/session-provider-config.yaml` defines enabled providers, ignore paths, retention windows, minimum session sizes, and redaction patterns.
- `docs/session-ingestion.md` and `docs/audits/session-ingestion-audit.md` document that raw transcript handling and vault promotion are governed rather than automatic.

Eval, shadow, and model-routing surfaces:

- `docs/evals/benchmark-eval-architecture.md` defines context profiles, shadow branch delta, failure taxonomy, completion gates, and anti-cheating rules.
- `docs/evals/context-profiles.md` separates local second-brain runs from repo-only, peer, portable-packet, and clean-room runs.
- `services/eval_run_service.py` persists eval tasks, runs, scores, failures, gold-set context, and second-brain retrieval evidence.
- `services/shadow_branch_runner.py` creates shadow worktrees, records comparison metadata, computes deltas, and preserves replay/parity metadata.
- `config/execution-strategies/model-routing-policy.json` defines subagent roles, model tiers, reasoning levels, routing categories, approval-required promotion statuses, and telemetry fields.

Memory and second-brain surfaces:

- `docs/STORES.md` distinguishes what agents may write automatically from what requires human approval.
- `schema.sql` has local-first storage for session imports, memory writeback proposals, memory updates, eval records, and workflow learning events.
- The Obsidian vault remains a curated destination; raw transcripts and direct self-mutations should not be promoted there automatically.

## Gaps

- Session summaries identify reusable patterns and candidate skills, but there is no normalized meta-learning signal schema for explicit corrections, repeated corrections, approvals, tool friction, context misses, model mismatch, contradictions, repeated scope restatements, second-brain misses, or irrelevant loaded context.
- Existing workflow learning detects recurring operational failures, but it does not route session-level preference/correction signals to target layers.
- There is no single proposal object for meta-learning changes that includes target layer, target file, confidence, risk, evidence, rollback instructions, approval requirement, and conflict status.
- Auto-permission recommendations are not separated from ordinary workflow-learning proposals.
- Shadow-branch infrastructure exists, but meta-learning proposals do not yet generate shadow eval plans.
- Agent/sub-agent suggestions currently live in model-routing policy and workflow registries; there is no review queue for suggested role/routing changes.
- Command suggestions have no first-class target layer beyond docs, CLI code, or backlog notes.
- Observe-only learnings have no dedicated holding area with expiration, recurrence counters, and evidence links.
- Project-specific preferences can leak into global rules if the routing layer does not force a project-vs-global decision.

## Target-Layer Storage Decisions

| Learned target | Storage target | Promotion path |
| --- | --- | --- |
| Learned workflow rules | `workflow_learning_events` for evidence, then `improvement_writebacks` or meta proposal rows targeting `config/workflows/registry.json` | Manual approval, focused tests, then registry patch |
| Project-specific conventions | Project truth files, project packets under `aios/context/projects/` or `aios/context/features/`, and scoped memory facts | Proposal first; never promote to global without multi-project evidence |
| Reusable skills | `config/workflows/skills.json` for AIOS registry metadata, local skill directories for implementation, and skillification candidates from `memory_writeback_proposals` | Candidate proposal, source evidence, tests, then skill/registry patch |
| Command suggestions | Meta proposal targeting `services/aios_cli.py`, docs, or a future command registry | Proposal plus CLI tests; do not silently add commands |
| Agent/sub-agent suggestions | Meta proposal targeting `config/execution-strategies/model-routing-policy.json` or workflow stage routing metadata | Shadow or sampled eval evidence before approval |
| Observe-only learnings | New meta-learning proposal store with `target_layer=observe_only`, or JSONL under a future `data/meta-learning/` path | Promote only after recurrence/confidence thresholds are met |
| Second-brain notes | `memory_writeback_proposals` with destination metadata for vault or memory layer | Human-reviewed vault promotion; raw transcript excluded |
| Eval/test cases | `config/agent-eval/`, `docs/evals/`, or test fixtures | Proposal with acceptance criteria and validation command |
| Auto-permission recommendations | Separate permission recommendation object, not ordinary proposal | Safety gate, manual approval, dry-run evidence, never auto-apply dangerous classes |

## Recommended Architecture

Use a four-step review-first pipeline:

1. Extract normalized session signals from normalized sessions, tool events, context receipts, eval failures, model-selection records, and user corrections.
2. Score signals with sample size, recurrence, recency, explicitness, project scope, security sensitivity, permission risk, blast radius, contradictions, and portability.
3. Route accepted signals to a target layer with a mandatory project-vs-global decision and an observe-only fallback.
4. Generate reviewable proposals. Proposals may include patches, markdown, eval plans, rollback instructions, and approval requirements, but they must not apply themselves.

The minimal v1 should prefer a small service and JSON/SQLite-backed proposal records over a broad new subsystem. Existing tables can carry some evidence, but a dedicated meta-learning proposal shape is justified once META-04 and META-05 need lifecycle operations.

## Shadow-Branch Testing

Medium/high-impact proposals should generate shadow eval plans before promotion.

Use `services/shadow_branch_runner.py` to create isolated branches from the same start SHA, then compare:

- baseline behavior
- proposed rule/skill/routing/command behavior
- test, lint, typecheck, and task acceptance results
- context profile and portability labels
- failure taxonomy entries from `docs/evals/benchmark-eval-architecture.md`

Do not shadow-test changes by contaminating the active branch. Do not use private second-brain context for peer or clean-room claims.

## Never Auto-Modify

These areas must not be modified automatically by meta-learning:

- `AGENTS.md`
- `config/agent-rules.md`
- user-level agent files under home directories
- skill `SKILL.md` files or generated skill libraries
- `config/execution-strategies/model-routing-policy.json`
- `config/workflows/registry.json`
- `config/workflows/skills.json`
- prompt registries and prompt templates
- Obsidian vault notes
- permission allowlists, auto-allow settings, deployment credentials, and auth config
- CI/deployment configuration
- tests, fixtures, or acceptance criteria when the proposal's purpose is merely to make a failing run pass

All of these may be proposal targets. None should be directly mutated by the extractor or scorer.

## Auto-Permission Safety Checks

Before any auto-permission recommendation is even proposed, AIOS should score:

- read vs write capability
- filesystem scope
- network access
- credential or secret exposure
- destructive potential
- external service side effects
- deployment/release impact
- reversibility and rollback path
- repo sensitivity
- sandboxability
- dry-run support
- audit logging support
- whether the command can be allowlisted as exact argv rather than broad shell text

Dangerous classes must never be auto-allowed by default: destructive commands, credential changes, deploy/release actions, external writes, broad filesystem writes, secret reads, auth mutations, and commands that bypass tests or hooks.

## Minimal Implementation Path

1. Add a normalized `MetaLearningSignal` schema and extractor over session summaries, messages, tool events, context receipts, eval failures, and model-selection records.
2. Add a confidence scorer and quality filter that rejects vague, one-off, generic, unsafe, or contradictory signals.
3. Add target-layer routing with explicit project/global/observe-only decisions.
4. Add proposal generation with stable IDs, evidence links, risk, target file, proposed patch/markdown, rollback instructions, approval requirement, and conflict status.
5. Add separated auto-permission recommendation scoring.
6. Add shadow eval plan generation for medium/high-impact proposals.
7. Add a minimal `aios meta` CLI for audit, analyze, list, approve/reject, and eval-plan operations.

This sequence produces immediate value from existing session/eval data without building a large autonomous self-modifying system.

## Files To Modify Later

- `services/meta_learning.py` for signal extraction, scoring, routing, and proposal generation.
- `services/aios_cli.py` for `aios meta` read/review commands.
- `schema.sql` if proposal lifecycle needs first-class queryability beyond existing writeback tables.
- `tests/test_meta_learning.py` for extractor, scorer, router, proposal, and permission safety coverage.
- `docs/aios/meta-learning.md` for operator-facing documentation.
- `config/agent-eval/` or `docs/evals/` for meta-learning fixtures and shadow-eval templates.

## Risks

- Silent mutation would damage trust in AIOS. The layer must propose, not apply.
- Global-rule pollution is likely if project-specific corrections are not scoped.
- Permission recommendations are high risk and need a separate safety class.
- Session transcripts may contain private or sensitive material; extraction must use redacted/normalized forms and evidence references.
- Overfitting to one user's corrections could make AIOS less portable.
- Too many low-confidence proposals would create review fatigue.
- Shadow eval plans can be expensive; require them only for medium/high-impact changes.

## Test Plan

- Extract explicit user corrections from normalized session messages.
- Detect repeated corrections across sessions and increase confidence with recurrence.
- Detect approvals and rejected proposals as separate signal types.
- Detect repeated command friction and failed tool loops.
- Detect context misses, second-brain misses, and irrelevant loaded context from receipts/eval records.
- Detect contradictions and route them to review instead of guessing.
- Route project-specific conventions to project targets, not global rules.
- Route skill-like patterns to skill candidates and command-like patterns to command proposals.
- Score auto-permission recommendations by risk and reject dangerous classes.
- Generate proposal objects with stable IDs, evidence, target layer, rollback instructions, and manual approval state.
- Generate shadow eval plans for medium/high-impact proposals.
- Verify no extractor/scorer test mutates protected files.

## Answers To Plan Questions

1. Learned workflow rules belong in workflow-learning evidence first, then proposal targets for `config/workflows/registry.json` or workflow docs after approval.
2. Project-specific conventions belong in project truth/context packets or scoped memory proposals, not global agent rules.
3. Reusable skills belong as skillification candidates first, then skill files and `config/workflows/skills.json` after review.
4. Command suggestions belong in meta proposals targeting CLI/docs/command registry surfaces, with tests before implementation.
5. Agent/sub-agent suggestions belong in proposals targeting model-routing or workflow routing metadata, backed by eval evidence.
6. Unproven but potentially useful observations belong in observe-only meta-learning records with recurrence counters.
7. Learned changes can be tested by generating shadow branch plans that use the same start SHA, acceptance criteria, context profile, and checks.
8. Always-loaded agent files, skill files, routing policy, workflow registries, permission allowlists, vault notes, prompts, CI/deployment config, and tests/fixtures must never be auto-modified.
9. Auto-permission recommendations need risk scoring for access scope, credentials, destructive behavior, reversibility, sandboxing, dry-run support, external effects, and auditability.
10. The minimal useful implementation is signal extraction, scoring/filtering, target routing, reviewable proposals, separated permission safety, shadow eval plans, and a small CLI.
