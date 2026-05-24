---
id: summarization
name: Structured Summarization
version: "1.0"
classification: explain
tags:
  - summarize
  - brief
  - digest
purpose: Convert long or noisy material into a concise, structured summary without losing key meaning.
when_to_use: Use when source material is long and the user needs fast understanding.
when_not_to_use: Do not use when the user needs original analysis, recommendations, or implementation planning.
required_inputs:
  - source_content: The content to summarize.
  - focus: What matters most for the summary audience.
optional_inputs:
  - length_target: Desired output length.
  - format: Preferred output shape such as bullets or sections.
output_contract: Produce a concise summary with core points, critical details, and explicit omissions if any.
eval_criteria:
  - Preserves original meaning and key claims.
  - Avoids invented facts and unsupported interpretation.
  - Highlights what changed, matters, or requires follow-up.
owner: jakyeamos
last_updated: "2026-04-23"
lifecycle_state: candidate
applicability:
  - audit_and_implement
last_evaluated_at: "2026-05-21T00:00:00Z"
changelog:
  - version: "1.0"
    date: "2026-04-23"
    note: Initial seed template for roadmap phase 1a.
---

## Instructions

1. Identify the source scope and intended audience.
2. Extract central claims, decisions, and outcomes.
3. Remove repetition and low-signal detail.
4. Preserve critical caveats and constraints.
5. Return a compact structure with clear headings.

## Example

**Inputs:**
- source_content: 15-page architecture memo.
- focus: implementation impact and unresolved risks.

**Output:**
- Summary with sections for intent, decisions, risks, and next actions.
