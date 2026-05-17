# Agentize Skill Architecture

Last updated: 2026-05-17

## Audit Summary

AIOS already had several pieces of a request-to-execution system:

- `prompts/` stores validated prompt templates, eval cases, and a generated
  registry consumed by hooks and workflow orchestration.
- `bin/hook-prompt-submit.py` and `services/workflow_orchestration.py` use
  prompt metadata to recommend templates and normalize selected workflows.
- `config/workflows/registry.json` and `config/workflows/skills.json` define
  staged workflow and skill bindings with validation through
  `validate_workflow_bindings`.
- `services/workflow_experiments.py`, workflow synthesis, harness evals, and
  success criteria provide pieces of evaluation and promotion evidence.
- `aios-ui/` exposes prompt, workflow, skill-candidate, control-plane, and
  standards-health surfaces, but it does not yet show agentized packets.

The missing piece was a primary intent compiler. Prompt templates were doing
too much of the conceptual work: they acted as reusable patterns, routing
evidence, and normalized prompt targets. That works for known task families but
is brittle for broad requests such as "clean up this repo" or "audit and
implement this PRD."

## Decision

`agentize` is now the preferred transformation layer for arbitrary human
requests.

```text
Freeform user request
  -> Agentize Skill
  -> Execution Packet
  -> Context/Standards Attachment
  -> Agent or Sub-Agent Execution
  -> Verification/Evaluation
  -> Reviewable learnings for prompt patterns, skills, and rules
```

The prompt library remains active as a supporting pattern/evidence corpus. It
stores proven templates, fragments, successful and failed transformation
examples, and quality outcomes. It should inform packet construction, not force
a static one-to-one mapping from request text to template ID.

## Packet Contract

`services.agentize.AgentizedTaskPacket` includes:

- original request and normalized objective
- task classifications
- execution mode and reasoning
- targeted context requirements
- relevant skills, standards, and success criteria
- constraints, non-goals, risks, and assumptions
- sub-agent and model/reasoning recommendations
- verification plan
- acceptance criteria and expected deliverables
- final response/update contract
- project truth-file update requirements
- experiment metadata
- prompt-pattern evidence

## Evaluation

`agentize_evaluations` records packet quality signals:

- original request
- transformed packet JSON
- selected execution mode
- selected skills and standards
- outcome quality
- test pass/fail signal
- user correction
- follow-up requirement
- major repair requirement

These records should later feed prompt-pattern validation, skill promotion, and
workflow-routing improvements through the existing approval-gated promotion
model.

## Migration Plan

Current state:

- Prompt templates are validated and synced.
- Workflow orchestration still uses `prompt_library_normalizer`.
- Prompt family recommendation remains part of route primitives.
- UI surfaces prompt/workflow state but not agentized packet details.

Target state:

- `agentize` compiles intent into the primary execution packet.
- Prompt templates become evidence and examples.
- Workflow execution consumes packet fields for context, standards, skills, and
  verification.
- UI shows why execution strategy was chosen and what standards/verification
  were attached.

Incremental steps:

1. Add `agentize` service, skill definition, workflow binding, schema, docs, and
   tests.
2. Keep existing prompt workflows backward compatible.
3. Adapt `start-work` and briefing packet creation to persist agentized packet
   JSON alongside route metadata.
4. Add UI drilldowns for packet, selected mode, attached standards, verification
   requirements, and learned pattern candidates.
5. Use `agentize_evaluations` to validate or demote prompt patterns over time.

## Compatibility

Existing prompt-library validation, sync, hook hints, and workflow
normalization remain in place. The new layer adds a packet compiler and
evaluation table without deleting prompt templates or changing existing
template IDs.
