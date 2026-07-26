---
name: agentize
version: 0.1.0
description: |
  Compile messy human requests into execution-ready agent task packets with
  intent normalization, targeted context, standards, verification, and
  handoff requirements.
license: MIT
compatibility: AIOS Codex Claude Code
allowed-tools:
  - Read
  - Grep
  - Bash
---

# Agentize

Use this skill when a user request needs to become a stronger agent handoff,
execution packet, workflow preflight, sub-agent assignment, implementation
prompt, audit packet, or planning packet.

The skill is a compiler from human intent into agent-executable work. It does
not replace the user's goal. It makes the goal explicit enough that an agent can
select context, act, verify, and report back without guessing.

## Inputs

- `original_request`: the user-provided request.
- Optional project/workflow hints from the current AIOS route.
- Optional prompt-pattern evidence from `prompts/registry.json`.

## Output

Return an `AgentizedTaskPacket` with:

- original request
- normalized objective
- task classifications
- execution mode and reasoning
- targeted context plan
- relevant skills
- relevant success criteria
- relevant standards
- constraints and non-goals
- risks and assumptions
- sub-agent recommendations
- model/reasoning recommendation
- verification plan
- acceptance criteria
- expected deliverables
- handoff/update format
- experiment/logging metadata
- prompt-pattern evidence

## Pipeline

1. Extract intent, probable success, ambiguity, and whether clarification is
   required.
2. Classify the task into one or more supported task families.
3. Select execution mode with reasoning.
4. Produce a targeted context plan; do not load the whole repo by default.
5. Attach relevant standards and success criteria.
6. Build a verification plan before execution starts.
7. Define the output contract and learning/writeback requirements.

## Prompt Library Role

The prompt library is supporting evidence and pattern memory:

- prompt templates show proven structures
- prompt fragments can inform packet wording
- successful transformations can become agentization examples
- failed transformations can become negative examples
- outcomes can validate or demote prompt patterns

Do not require a one-to-one static mapping from request text to template ID.
When no prompt pattern matches, still produce a packet from the request
semantics and record that static mapping was not required.

## Anti-Patterns

- Treating a template match as authority over the user's request.
- Loading every Markdown file instead of a targeted context packet.
- Emitting a prose-only plan when schema/types/tests need machine-readable
  fields.
- Selecting sub-agents without explaining decomposition value.
- Omitting verification because the request sounds like planning or writing.
- Silently promoting prompt or skill learnings into active rules.

## Local Implementation

- Service: `services/agentize.py`
- Workflow registry: `config/workflows/registry.json`
- Skill registry: `config/workflows/skills.json`
- Evaluation table: `agentize_evaluations`
- Tests: `tests/test_agentize.py`
