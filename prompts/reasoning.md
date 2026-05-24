---
id: reasoning
name: Decision Reasoning
version: "1.0"
classification: plan
tags:
  - reasoning
  - decision
  - tradeoff
  - strategy
purpose: Turn ambiguous asks into decision-ready recommendations with explicit assumptions and tradeoffs.
when_to_use: Use for planning, architecture choices, sequencing, and prioritization.
when_not_to_use: Do not use when the ask is purely executional and already unambiguous.
required_inputs:
  - question: The decision or problem to resolve.
  - constraints: Hard boundaries, dependencies, and risk tolerance.
optional_inputs:
  - options: Candidate approaches already under consideration.
  - decision_deadline: Time horizon for recommendation.
output_contract: Return a recommendation with assumptions, tradeoffs, alternatives, and next-step plan.
eval_criteria:
  - Assumptions and unknowns are explicit.
  - Recommendation is justified by constraints and evidence.
  - Alternatives are fairly compared, not dismissed.
owner: jakyeamos
last_updated: "2026-04-23"
lifecycle_state: active
applicability:
  - audit_only
  - audit_and_implement
last_evaluated_at: "2026-05-21T00:00:00Z"
changelog:
  - version: "1.0"
    date: "2026-04-23"
    note: Initial seed template for roadmap phase 1a.
---

## Instructions

1. Clarify the decision frame and success criteria.
2. List hard constraints and non-negotiables.
3. Compare viable options with tradeoffs.
4. State assumptions and confidence level.
5. Recommend one path and define immediate next steps.

## Example

**Inputs:**
- question: Should AIOS ship prompt library before orchestration upgrades?
- constraints: roadmap dependencies and engineering capacity.

**Output:**
- Recommendation with dependency-aware sequencing and risk notes.
