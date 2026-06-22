# Phase 18: Meta-Learning Proposal Layer - Research

**Gathered:** 2026-06-01
**Status:** Ready for planning

<source_spec>
## Source Spec

Phase 18 is specified in the pasted "AIOS Meta-Learning Layer - Audit and Implementation Prompt" ingested on 2026-06-01. The spec asks AIOS to adapt the strongest ideas from Nick Nisi's `meta` Claude plugin: workflow analysis, feedback detection, durable preference capture, confidence scoring, conflict resolution, reversible edits, auto-allow safety, and reviewable proposal routing.

The key design choice is that AIOS should become self-improving but not self-mutating. It can notice patterns, score them, route them, and propose changes. Promotion into durable behavior must still require evidence, review, and preferably shadow-branch validation.
</source_spec>

<domain>
## Phase Boundary

Phase 18 creates a review-first meta-learning proposal layer. It does not replace Phase 9 learning primitives or silently mutate rules, skills, commands, agents, permissions, or second-brain notes.

It depends on and extends prior phases:

- Phase 9 provides learning signal taxonomy, cross-run analysis, and conservative proposals.
- Phase 11 provides shadow-branch and eval comparison infrastructure.
- Phase 13 provides session ingestion/transcript storage surfaces.
- Phase 16 provides hard evidence, verifier artifacts, context manifests, and model-selection instrumentation.
- Phase 17 provides capability-pack routing patterns that this layer can inspect and improve.

Phase 18 focuses on session-level and cross-session signals from user corrections, approvals, tool friction, context misses, repeated commands, model mismatch, and contradictions, then turns accepted signals into reviewable proposals.
</domain>

<placement_decision>
## Placement Decision

This work belongs in a new Phase 18 rather than as an expansion of Phase 9.

Phase 9 owns the conservative learning loop at the workflow evidence level. This spec is a higher-level proposal system that needs session ingestion, shadow eval plans, permission safety, CLI review commands, conflict handling, and target-layer routing across global rules, project rules, skills, commands, agents, second-brain notes, and evals.
</placement_decision>

<requirements>
## Phase 18 Requirements

### META-01: Meta-Learning Audit
AIOS must audit existing global/project instruction files, skill files, agent definitions, commands, memory/second-brain integration, shadow branches, logging/session transcript storage, eval/benchmark harnesses, model routing, sub-agent orchestration, and preference/correction capture. The audit must answer where each learning target layer should live and what must never be auto-modified.

### META-02: Session Signal Extraction
AIOS must analyze session logs, transcript exports, or structured workflow traces and extract normalized signals for explicit corrections, repeated corrections, approvals, repeated manual commands, failed tool loops, context misses, model mismatch, contradictions, repeated scope restatements, second-brain misses, and irrelevant loaded context.

### META-03: Confidence Scoring And Quality Filter
AIOS must score extracted signals using weighted evidence, recency, explicit memory requests, multi-project evidence, blast radius, security sensitivity, permission risk, and contradictions. A four-question quality filter must reject generic best practices, one-off preferences, vague preferences, unsafe permission changes, and contradictory signals without enough evidence.

### META-04: Target-Layer Routing
AIOS must route accepted signals to the correct layer: global AIOS rule, project rule, skill instruction, command, agent/sub-agent suggestion, second-brain note, eval/test case, or observe-only. Routing must include a justification and must avoid promoting project-specific preferences into global rules.

### META-05: Reviewable Proposal Generation And Conflict Resolution
AIOS must generate reviewable proposals with stable IDs, title, summary, target layer, target file, confidence score, risk, evidence, layer justification, proposed patch or markdown, rollback instructions, and manual approval requirement. Conflicting signals must be identified and marked for review rather than guessed.

### META-06: Auto-Allow Safety Gate
AIOS must separate auto-allow permission recommendations from ordinary workflow-learning proposals. Auto-allow recommendations must score read/write capability, filesystem writes, network access, credential exposure, destructive potential, reversibility, repo sensitivity, sandboxability, and dry-run support; destructive, secret, deploy, external write, and credential-changing actions must never be auto-allowed by default.

### META-07: Shadow Evaluation Plans And CLI
AIOS must generate shadow-branch eval plans for medium/high-impact proposals and expose a minimal `aios meta` CLI for audit, session analysis, proposal listing, approval/rejection, and eval plan generation, or equivalent scripts if the CLI cannot host the commands.

### META-08: Documentation And Tests
AIOS must document the meta-learning layer, routing policy, scoring policy, auto-allow safety, proposal format, and limitations. Tests must cover correction detection, repeated correction scoring, approval scoring, contradiction detection, project vs global routing, skill vs command routing, auto-allow risk scoring, proposal formatting, and shadow eval plan generation.
</requirements>

<plan_sequence>
## Recommended Plan Sequence

- **18-01**: Audit current learning/session/rule/skill/command/agent/proposal surfaces.
- **18-02**: Implement session signal extractor and normalized signal schema.
- **18-03**: Implement confidence scoring, quality filter, conflict detection, and target-layer router.
- **18-04**: Implement proposal generator and review lifecycle.
- **18-05**: Implement auto-allow safety gate and separated permission recommendations.
- **18-06**: Add shadow-branch eval plan generation and minimal `aios meta` CLI.
- **18-07**: Add docs and tests.
</plan_sequence>

<implementation_constraints>
## Implementation Constraints

- Keep the first implementation lightweight.
- Prefer JSONL, Markdown, or existing AIOS persistence surfaces over a new complex database unless the audit proves a DB table is the cleanest fit.
- Do not silently modify global AIOS instructions.
- Do not silently modify skill files.
- Do not silently change auto-allow settings.
- Do not scrape or import community plugins automatically.
- Do not promote learnings without evidence.
- Do not store vague preferences.
- Do not turn every correction into a rule.
- Do not overwrite user-authored files without creating a diff/proposal first.
</implementation_constraints>
