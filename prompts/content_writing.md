---
id: content_writing
name: Audience-Scoped Content Writing
version: "1.1"
classification: other
tags:
  - writing
  - draft
  - messaging
purpose: Draft clear, audience-appropriate prose with explicit structure and constraints.
when_to_use: Use for emails, updates, docs, and narrative communication drafts.
when_not_to_use: Do not use when factual research or technical debugging is still incomplete.
required_inputs:
  - objective: What the writing must accomplish.
  - audience: Who will read it and what they need.
optional_inputs:
  - tone: Desired tone constraints.
  - must_include: Required facts, links, or sections.
output_contract: Return a complete draft that is clear, structured, and aligned to audience needs.
eval_criteria:
  - Objective is satisfied without ambiguity.
  - Tone and level match the audience.
  - Draft includes required facts and avoids filler.
owner: jakyeamos
last_updated: "2026-08-14"
lifecycle_state: active
applicability:
  - content_generation
last_evaluated_at: "2026-05-21T00:00:00Z"
changelog:
  - version: "1.1"
    date: "2026-08-14"
    note: Make supplied-fact boundaries explicit.
  - version: "1.0"
    date: "2026-04-23"
    note: Initial seed template for roadmap phase 1a.
---

## Instructions

1. Confirm objective, audience, and constraints.
2. Build an outline before drafting.
3. Write directly with concrete language.
4. Remove filler and vague claims.
5. Verify required facts and calls to action are present.
6. Use only supplied or verified claims. Do not invent benefits, logistics,
   eligibility, dates, or commitments to make the draft sound complete; mark a
   required missing fact as unknown.

## Example

**Inputs:**
- objective: announce phase completion and next actions.
- audience: engineering leads and project manager.

**Output:**
- Structured status update with decision-relevant details and clear asks.
