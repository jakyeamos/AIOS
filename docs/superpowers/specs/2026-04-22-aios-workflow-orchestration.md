# AIOS Workflow Orchestration — Deterministic Execution Model Audit + Implementation Prompt

**Date:** 2026-04-22
**Status:** Ready to run
**Type:** Audit + implementation prompt
**Author:** jakyeamos

---

## Purpose

Move AIOS away from loose, freeform AI interactions toward a procedural, deterministic execution model built around typed workflows, staged execution, attached skills, and explicit validation gates.

**Core intent:** Convert broad human requests into deterministic workflow executions, where proven prompt formats, user-specific corpus conditioning, and specialized skills are attached at defined stages — not improvised inside one giant model prompt.

**Reference example:** A request like "write a paper" routes into `academic_paper_v1` with ordered stages: request parsing → prompt normalization → context enrichment → drafting → voice alignment → validation → output finalization. The humanizer uses the personal Obsidian corpus through a structured retrieval stage, not raw prompt stuffing.

---

## Prompt

You are auditing and implementing a major architectural improvement for AIOS.

Objective:
Move AIOS away from loose, freeform AI interactions and toward a more procedural, deterministic execution model built around workflows, staged execution, attached skills, and explicit validation gates.

Core intent:
The system should convert broad human requests into deterministic workflow executions, where proven prompt formats, user-specific corpus conditioning, and specialized skills are attached at defined stages rather than improvised inside one giant model prompt.

Example target behavior:
A request like "write a paper" should not be handled as one prompt. It should be routed into a typed workflow such as `academic_paper_v1` with ordered stages like:
1. request parsing
2. prompt normalization via prompt library
3. context enrichment
4. drafting
5. voice alignment / humanizer
6. validation
7. output finalization

In this example, the humanizer should be able to use the personal corpus from Obsidian, but only through a structured, explicit stage in the workflow. Do not design this as random prompt stuffing. Design it as deterministic workflow architecture.

Your task has two parts:
1. Audit the current AIOS state against this target architecture
2. Implement the highest-leverage parts of the target architecture directly in the repo

Important operating principles:
- Prefer procedural and deterministic behavior over clever but implicit prompting
- Workflows must own skills; skills must not decide when to run themselves
- Skills must have explicit contracts: inputs, outputs, invariants, allowed transformations, forbidden transformations
- Prompt library usage should be stage-bound and typed, not globally slapped onto all requests
- Personal corpus usage should be retrieval-based and structured, not raw uncontrolled context dumping
- Validation gates must be explicit and machine-checkable where possible
- Favor maintainability, extensibility, and observability over novelty
- Large refactors are allowed if they improve architectural clarity
- Keep the system understandable by a future human operator

---

### What to Audit

1. Whether AIOS currently has real workflow primitives or is still mostly prompt orchestration
2. Whether there is a workflow registry, stage model, or typed execution graph
3. Whether skills are explicit, typed, stage-bound modules or just reusable prompt fragments
4. Whether there is a prompt library and, if so, whether it is actually integrated into request handling
5. Whether there is any notion of validation gates, pass/fail checks, or required post-processing
6. Whether there is any existing context retrieval path from Obsidian or similar personal corpus sources
7. Whether current agent behavior is procedural and deterministic or still mostly heuristic and improvisational
8. Where architecture is weak but clever rather than strong and legible
9. What needs to change in the control plane, registries, routing, contracts, storage, and docs to support this model

Classify the current repo as: prompt-centric, workflow-centric, rule-centric, registry-driven, heuristic, or deterministic — and explain why.

---

### Target Architecture

#### A. Workflow Registry

A registry of typed workflows such as:
- `academic_paper_v1`
- `prd_generation_v1`
- `bugfix_v1`
- `refactor_v1`
- `ui_polish_v1`

Each workflow defines:
- name
- purpose
- trigger / routing hints
- ordered stages
- required skills
- optional skills
- required validations
- output contract
- observability / reporting fields

#### B. Stage Model

Each workflow runs through explicit stages such as:
- parse_request
- normalize_prompt
- enrich_context
- generate
- transform
- validate
- finalize

Stages are typed, inspectable, and ordered.

#### C. Skill Registry

Each skill is first-class and declares:
- skill name
- purpose
- allowed stage(s)
- input schema
- output schema
- invariants
- failure conditions
- side effects
- whether it is deterministic, heuristic, or optional

Examples:
- `prompt_library_normalizer`
- `personal_corpus_humanizer`
- `citation_checker`
- `structure_checker`
- `simplifier`
- `ui_ux_polish`
- `rubric_validator`

#### D. Prompt Library Integration

Prompt formats are treated as reusable assets with explicit usage rules. The system transforms a loose human request into a proven prompt format through a workflow stage — not by ad hoc string concatenation.

#### E. Personal Corpus Integration

A clean path for using the Obsidian corpus as a structured conditioning source. Do not dump entire notes into prompts. Instead, create a retrieval/profile layer that can provide:
- writing voice profile
- preferred sentence rhythm
- preferred level of formality
- phrases/patterns to avoid
- good examples by writing type
- style exemplars for specific use cases

#### F. Validation Gates

Outputs pass workflow-specific gates before being considered complete. For paper-writing, gates might include:
- assignment structure satisfied
- citation coverage present
- unsupported claims flagged
- humanizer did not distort meaning
- prose quality improved without losing specificity

#### G. Execution Reporting

Each run produces a structured execution report showing:
- workflow selected
- stages run
- skills invoked
- validations passed/failed
- artifacts produced
- unresolved issues

---

### Minimum Implementation Target

1. Add or refactor the core abstractions for:
   - workflow registry
   - stage model
   - skill registry
   - validation hooks

2. Add at least one real end-to-end reference workflow: `academic_paper_v1`

3. In that workflow, wire:
   - prompt library normalization stage
   - personal corpus / Obsidian style enrichment interface or adapter
   - humanizer stage with explicit contract
   - validation stage(s)

4. Create the schema/types/config structure so more workflows can be added cleanly

5. Add documentation explaining the architecture and how to extend it

6. Add tests or verification checks for the new control flow

7. Add observability/reporting so workflow execution is inspectable

8. Update any truth/status/design docs so the new architecture is discoverable

---

### Humanizer Contract (Reference)

For the `personal_corpus_humanizer` skill in `academic_paper_v1`:

**Must preserve:**
- factual meaning
- argument structure
- citations
- specificity
- technical correctness

**May improve:**
- sentence rhythm
- transitions
- diction
- redundancy
- readability
- naturalness of prose

**Must not:**
- invent evidence
- weaken claims into vagueness
- remove important technical nuance
- rewrite citations incorrectly

---

### Audit Requirements

Before implementing, write down:
- current state
- target state
- major gaps
- architectural risks
- recommended implementation sequence
- what should be deleted, replaced, or deprecated
- what is already strong and should be preserved

---

### Implementation Standards
- prefer simple, explicit types over magic
- reduce hidden behavior
- avoid global prompt hacks
- avoid scattered one-off conditionals
- avoid skill logic that is impossible to trace
- prefer registries, contracts, and explicit pipelines
- prioritize legibility for future agent and human operators
- keep naming crisp and durable
- remove or consolidate weak abstractions where necessary

---

### Deliverables

1. A concise architecture audit
2. A concrete gap analysis
3. A prioritized implementation plan
4. The actual code changes
5. Any new config/spec/docs files
6. A short explanation of how the new model works
7. A list of follow-on improvements that were not completed
8. A handoff document if the work is too large to finish in one pass

---

### Acceptance Criteria

- AIOS now has explicit workflow concepts rather than only loose prompt composition
- workflows can own ordered stages
- skills are attached at defined stages with contracts
- at least one real workflow demonstrates the model end to end
- prompt library integration is structured and stage-bound
- personal corpus integration is designed or implemented cleanly
- validation gates exist in code/config, not only in prose docs
- execution is more inspectable and deterministic than before
- docs clearly explain how to add new workflows and skills

---

### Reference: academic_paper_v1 Stage Flow

```
Workflow: academic_paper_v1
- parse_request
- normalize_prompt         [prompt_library_normalizer]
- enrich_context           [obsidian_corpus_retriever]
- draft_sections           [generate]
- transform_prose          [personal_corpus_humanizer]
- validate                 [structure_checker, citation_checker, meaning_preservation_checker]
- finalize                 [output_contract enforcement, execution_report]
```
