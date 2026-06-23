# AIOS Prompt/Template Boundary Audit

Date: 2026-06-23

## Scope

Reviewed the workflow registry, prompt registry, and active prompt templates for Phase 16 Plan 16-05. The goal was to find prompt prose that should become deterministic workflow metadata without rewriting the prompt library.

Primary surfaces:

- `config/workflows/registry.json`
- `prompts/registry.json`
- `prompts/research.md`
- `prompts/reasoning.md`
- `prompts/coding_debug.md`
- `prompts/behavioral_spec_verification.md`

## Findings

### Duplicated Instructions

- Implementation workflows repeatedly describe validation, evidence, and closeout expectations in stage output contracts, expected artifacts, prompt bindings, and prompt prose.
- Audit-style workflows repeat "review before action" guidance across `research`, `reasoning`, and workflow output contracts.

Impact: duplicated prose makes it unclear which surface is authoritative when a workflow must block closeout.

### Stale Or Risky Rules

- Some prompt templates still act as broad behavioral contracts rather than narrow prompt-shaping surfaces.
- Prompt prose can say verification evidence is required, but before this plan the loader did not expose evidence or verifier gate requirements as first-class stage metadata.

Impact: agents could satisfy the prompt narrative with a summary while deterministic code had no direct gate to inspect.

### Unclear Phase Boundaries

- `implementation-delivery` had clear `validate` and `finalize` stages, but the distinction between command evidence and independent verifier evidence was implicit.
- `audit-and-implement` also references verification evidence and closeout, but it remains a candidate workflow and should not receive broader gate changes in this minimal patch.

Impact: implementation, validation, verifier, and closeout responsibilities were easy to blend in one implementer narrative.

### Missing Output Schemas

- Prompt templates define evaluation criteria, but they do not define machine-readable evidence artifact or verifier artifact references.
- Workflow stage outputs specify reports/artifacts, but not the deterministic gate fields that closeout should inspect.

Impact: downstream tooling could not list stage gate requirements without reading prose.

### Prompt Prose Doing Deterministic Work

- "Run verification evidence before closeout" belongs in workflow metadata once evidence and verifier artifacts exist.
- "Independent verifier required before closeout" belongs in a stage gate, not only in agent instructions.

## Deterministic Gates Moved

Moved the smallest safe target into workflow config:

- `implementation-delivery` `validate` stage now declares `required_evidence: ["evidence_artifacts"]`.
- `implementation-delivery` `finalize` stage now declares `required_verifier: true`.
- `services/workflow_orchestration.py` normalizes these fields for every stage with backward-compatible defaults.
- `aios workflow-gates --workflow implementation-delivery --json` exposes the requirements without reading prompt prose.

## Left In Prose For Now

- Role-specific prompt wording for researcher, implementer, reviewer, and verifier remains in templates because the exact output text still benefits from human-readable instruction.
- Candidate workflows beyond `implementation-delivery` were not broadly rewritten; their gate policy should be promoted after the active workflow path proves stable.

## Result

Phase-critical evidence and verifier requirements now have deterministic metadata while prompt changes stay narrowly scoped.
