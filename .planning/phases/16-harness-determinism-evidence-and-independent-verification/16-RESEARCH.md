# Phase 16: Harness Determinism, Evidence, And Independent Verification - Research

**Gathered:** 2026-06-01
**Status:** Ready for planning

<source_spec>
## Source Spec

Phase 16 is specified in the pasted "Case-inspired AIOS harness audit and targeted improvement" prompt ingested on 2026-06-01. The spec asks AIOS to audit its existing agent execution and evaluation harness, compare it against the strongest ideas from Nick Nisi's Case system, and implement the smallest high-leverage deltas that make the harness more deterministic, auditable, evidence-backed, context-efficient, and self-improving.

The source prompt is inspiration, not a blueprint. AIOS is explicitly not greenfield, and the phase must not create a parallel harness unless an important concept has no existing equivalent.
</source_spec>

<domain>
## Phase Boundary

Phase 16 is a cross-cutting harness integrity phase. It comes after the focused primitives already planned in earlier phases:

- Phase 3 owns durable workflow execution and run state.
- Phase 6 owns standards resolution and evidence-backed evaluation.
- Phase 8 owns prompt, skill, workflow contracts, and asset lifecycle.
- Phase 9 owns continuous learning and conservative optimization.
- Phase 11 owns testing, benchmark evaluation, shadow branches, and ablations.
- Phase 12 owns graph-native memory and cache-aware context compilation.

Phase 16 does not replace those phases. It audits how they combine into one end-to-end harness and patches the weakest joints where prose instructions, loose completion markers, implementer-only verification, or missing evidence can still let bad work be marked complete.
</domain>

<placement_decision>
## Placement Decision

This work belongs in a new Phase 16 rather than inside an existing phase.

It overlaps many phases, but no existing phase owns the full combined concern:

- It is wider than Phase 11 because it touches lifecycle gates, context routing, prompts, verification, retrospectives, and model selection, not only eval automation.
- It is wider than Phase 6 because it requires hard-to-fake command evidence and independent verifier artifacts, not only success criteria evaluation.
- It is wider than Phase 9 because retrospectives are one output, but the phase also changes evidence, closeout, verifier, and phase-control contracts.
- It is wider than Phase 8 because prompt tightening is only one part; state-machine responsibility must move out of prompts where feasible.

The correct shape is an integration and hardening phase after the focused subsystems exist.
</placement_decision>

<key_concepts>
## Source Concepts To Borrow

The source spec identifies seven concepts to adapt:

1. Conversation should not be the workflow interface. Task state, rules, context, decisions, evidence, and outcomes should live in durable files or structured runtime artifacts.
2. Agents should not be trusted as state machines. Critical phase transitions should be controlled by deterministic harness logic.
3. Verification should be structurally independent. The implementer session should not be the only verifier.
4. Evidence must be hard to fake. Completion should require real command output, logs, hashes, tests, diffs, benchmarks, or structured artifacts.
5. Context should be routed, not dumped. Stable rules, repo knowledge, second-brain context, task context, and volatile run notes should remain separated.
6. Retrospectives should improve the harness. Repeated failures should become reviewable checks, playbooks, routing rules, benchmark cases, model-selection rules, or memory proposals.
7. Multi-agent work should be intentional. Model and reasoning choice should be logged and testable by phase/task type.
</key_concepts>

<existing_aios_surfaces>
## Existing AIOS Surfaces To Audit Before Patching

- Harness entrypoints: `bin/aios.py`, `bin/aios-managed-run.py`, `bin/aios_orchestration_runtime.py`
- Hooks: `bin/hook-session-start.py`, `bin/hook-prompt-submit.py`, `bin/hook-post-tool-use.py`, `bin/hook-stop.py`
- Orchestration: `services/workflow_orchestration.py`, `services/task_routing.py`, `services/invocation_backends.py`
- Evaluation: `services/success_criteria.py`, `services/harness_eval.py`, `services/standards_health.py`
- Learning: `services/workflow_learning.py`, `services/workflow_promotion.py`, `services/workflow_experiments.py`
- Context: `tools/context-compile.mjs`, `aios/context/**`, context receipts, packet artifacts
- Benchmark and shadow work: Phase 11 eval services, shadow branch runner, ablation runner, peer trace, portable packet generator
- Prompt/template assets: `prompts/registry.json`, `config/workflows/registry.json`, `config/workflows/skills.json`
- Storage: `schema.sql`, `data/success-criteria/evaluations/**`, workflow execution reports, artifacts, run events
- Operator surfaces: `services/aios_cli.py`, `aios-ui/server/routers/**`, `aios-ui/server/aios/**`
</existing_aios_surfaces>

<requirements>
## Phase 16 Requirements

### HARN-01: Existing Harness Audit
AIOS must produce a concise audit report mapping harness entrypoints, orchestration logic, lifecycle state, prompt/template system, model selection, context routing, second-brain integration, evaluation, evidence, verification, recovery, shadow branches, learning, docs, scripts, CI checks, and known WIP areas. The report must identify current sources of truth for task, phase, owner, context, commands, evidence, verification result, changed state, and future learning.

### HARN-02: Deterministic Phase Control
AIOS must compare its current lifecycle against intake, context routing, planning, implementation, verification, review, closeout, and retrospective phases. For each phase it must identify equivalent implementation, transition logic, completion artifact, failure mode, and minimal reliability patch.

### HARN-03: Evidence Chain Hardening
AIOS must bind completion markers to durable evidence artifacts containing timestamp, task id, phase, agent/model, command, exit code, stdout/stderr path or hash, parsed summary, diff or commit hash, verifier identity where applicable, status, and caveats. Empty marker files, stale evidence, and agent-written "tests passed" claims must not satisfy completion gates.

### HARN-04: Independent Verification Gate
AIOS must require structurally independent verification before closeout for implementation-bearing governed workflows. The verifier must review task spec, diff, and evidence artifacts, emit structured pass/fail/needs-work output, cite concrete files/commands/evidence paths, and deterministically route failures back to implementation retry or human review.

### HARN-05: Context Routing And Second-Brain Parity
AIOS must record context routing manifests showing loaded/skipped sources, reasons, second-brain availability, fallback behavior, estimated context budget, and retrieval reasons. Tests must cover both second-brain-available and no-second-brain conditions.

### HARN-06: Prompt And Template Boundary Tightening
AIOS must audit prompts/templates for duplicated instructions, stale rules, unclear phase boundaries, missing output schemas, and prose instructions doing deterministic state-machine work. Patches must tighten phase-specific prompts and move obvious gates into code/config where feasible.

### HARN-07: Retrospective And Model-Selection Instrumentation
AIOS must add or tighten structured retrospective artifacts and model-selection logs so repeated failures can become reviewable rules, checks, playbooks, benchmark cases, memory proposals, or model-routing updates. Model choice, phase, task type, reasoning level, selection reason, fallback, tokens/cost when available, latency, and outcome should be inspectable.

### HARN-08: Shadow Branch And Benchmark Parity Metadata
AIOS must preserve the existing shadow-branch workflow while improving branch/run metadata, comparison artifacts, parity checklists, failure classification, and replay instructions where current Phase 11 artifacts are too weak.
</requirements>

<plan_sequence>
## Recommended Plan Sequence

- **16-01**: Audit existing AIOS harness architecture and source-of-truth map.
- **16-02**: Harden evidence chain and completion artifact binding.
- **16-03**: Add independent verifier gate and structured verifier artifacts.
- **16-04**: Add context routing manifests and second-brain parity checks.
- **16-05**: Tighten deterministic phase transitions and prompt/template boundaries.
- **16-06**: Add retrospective, model-selection, and shadow parity metadata improvements.
</plan_sequence>

<implementation_constraints>
## Implementation Constraints

- Preserve AIOS architecture. Patch existing components before creating new ones.
- Do not create a separate Case clone.
- Do not add heavyweight dependencies unless unavoidable.
- Do not alter production behavior unrelated to the harness.
- Do not assume command names. Discover them during implementation.
- Do not fabricate benchmark, lint, typecheck, test, or verifier results.
- If evidence cannot be verified, mark it honestly.
- Major learning and rule changes must be queued for review, not silently applied.
</implementation_constraints>
