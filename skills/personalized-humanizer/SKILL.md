---
name: personalized-humanizer
version: 0.1.0
description: |
  Rewrite text toward the local user's approved personal voice profiles using
  bounded corpus evidence, mode-specific guardrails, debug/audit output, and
  feedback-gated profile learning.
license: MIT
compatibility: AIOS Codex Claude Code
allowed-tools:
  - Read
  - Grep
  - Bash
---

# Personalized Humanizer

Use this skill when the user asks to make writing sound closer to them, mirror
their voice, rewrite outreach, adapt project updates, improve prompts/PRDs,
polish reflections, or preserve creative/narrative tone.

Do not use this skill for AI-detector evasion. The goal is authentic voice
matching, clarity, and intent preservation.

This skill is optional in a broader humanizing pipeline. When the user wants
general AI-writing cleanup, use the generic humanizer first. Use this skill as a
second pass only when the user also wants the result adapted toward the local
voice profile.

## Modes

- `professional_outreach`: LinkedIn messages, cold emails, recruiter notes,
  mentor updates, and networking messages.
- `project_build_in_public`: Twitter/X, LinkedIn posts, project updates, and
  AIOS/Soundscape/Court Vision/Terrace writeups.
- `academic_reflective`: essays, reflections, discussion posts, and personal
  explanatory writing.
- `prompt_prd`: Codex prompts, implementation prompts, audit prompts, PRDs,
  and agent handoffs.
- `creative_narrative`: scenes, character development, emotional realism, and
  philosophical narration.

## Pipeline

1. Classify the writing task and select a mode.
2. Retrieve only mode-compatible approved corpus examples.
3. Build a compact voice packet with tone, rules, anti-rules, confidence, and
   provenance.
4. Rewrite while preserving meaning, facts, constraints, and useful structure.
5. Run the quality scorecard.
6. Return only the rewrite in normal mode.
7. In debug/audit mode, include selected profile, rules, evidence refs, risks,
   scorecard, confidence, and why the rewrite changed.

## Pipeline Positions

- `standalone`: Perform the conservative built-in cleanup and then apply the
  selected voice mode.
- `after_generic_humanizer`: Treat the input as already cleaned by the generic
  humanizer. Apply only the selected personal voice mode and preserve the
  generic humanizer's output choices unless they conflict with the voice
  profile or requested constraints.

## Boundaries

- Do not add personal facts unless they are already present or explicitly
  requested.
- Do not use creative/narrative corpus for professional outreach unless the
  user explicitly allows cross-mode references.
- Do not use outreach/professional corpus to flatten creative prose.
- Do not turn writing into generic startup copy.
- Do not over-polish informal or reflective writing.
- Do not silently delete constraints from prompts or PRDs.

## Learning

User feedback is evidence, not an automatic profile mutation.

Feedback states:

- `draft profile`
- `candidate profile update`
- `approved profile update`
- `rejected profile update`
- `deprecated style rule`

New reusable patterns must become candidate updates with evidence links before
they can affect the canonical voice profile.

## Local Implementation

- Profile: `config/personalized-humanizer/profile.json`
- Retrieval policy: `config/personalized-humanizer/retrieval-policy.json`
- Eval suite: `config/personalized-humanizer/evals.json`
- Service: `services/personalized_humanizer.py`
- Tests: `tests/test_personalized_humanizer.py`
