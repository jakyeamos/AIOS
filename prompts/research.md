---
id: research
name: Research Synthesis
version: "1.0"
classification: plan
tags:
  - research
  - analysis
  - compare
  - synthesize
purpose: Build a source-grounded synthesis that turns scattered findings into a decision-ready briefing.
when_to_use: Use for multi-source research where conclusions, tradeoffs, and recommendations are required.
when_not_to_use: Do not use for single-source summarization or for requests that only need extraction.
required_inputs:
  - topic: The research question or decision to answer.
  - sources: Relevant source material with links or file references.
optional_inputs:
  - constraints: Time, scope, domain, or policy limits.
  - audience: Decision-maker profile and expected depth.
output_contract: Return a structured briefing with key findings, evidence, risks, unknowns, and recommendation.
eval_criteria:
  - Findings are source-grounded and attributable.
  - Recommendation follows from evidence and constraints.
  - Open questions are explicit and actionable.
owner: jakyeamos
last_updated: "2026-04-23"
changelog:
  - version: "1.0"
    date: "2026-04-23"
    note: Initial seed template for roadmap phase 1a.
---

## Instructions

1. Restate the research objective and decision context.
2. Extract the strongest evidence from each source.
3. Group evidence into themes, contradictions, and unknowns.
4. Separate verified facts from inference.
5. Produce recommendation options with tradeoffs.
6. End with a clear recommendation and unresolved questions.

## Example

**Inputs:**
- topic: Decide whether to enforce architecture checks in all linked repos this quarter.
- sources: enforcement audit notes, CI failure trends, staffing constraints.

**Output:**
- Decision briefing with evidence table, option comparison, and recommended rollout path.
