---
id: coding_debug
name: Coding Debug
version: "1.0"
classification: debug
tags:
  - debug
  - bug
  - error
  - fix
  - failing
purpose: Diagnose a concrete software failure and produce a minimal, evidence-backed fix path.
when_to_use: Use for runtime errors, failing tests, regressions, and broken behavior.
when_not_to_use: Do not use for exploratory redesigns or broad refactors without a concrete failure.
required_inputs:
  - symptom: Exact error or observed failure behavior.
  - context: Relevant code paths, commands, or logs.
optional_inputs:
  - hypothesis: Current likely root cause.
  - constraints: Boundaries such as no new deps or compatibility requirements.
output_contract: Return root cause, evidence, smallest safe fix, and verification steps.
eval_criteria:
  - Root cause is explicit and evidence-based.
  - Fix scope is minimal and targeted.
  - Verification plan can detect regressions.
owner: jakyeamos
last_updated: "2026-04-23"
lifecycle_state: active
applicability:
  - failure_recovery
  - audit_and_implement
last_evaluated_at: "2026-05-21T00:00:00Z"
changelog:
  - version: "1.0"
    date: "2026-04-23"
    note: Initial seed template for roadmap phase 1a.
---

## Instructions

1. Restate expected behavior vs actual behavior.
2. Isolate the smallest failing unit.
3. Propose the top root-cause hypothesis with evidence.
4. Confirm or refute using code/log/test signals.
5. Propose the minimum safe fix.
6. Define exact verification steps.

## Example

**Inputs:**
- symptom: `TypeError: Cannot read properties of undefined (reading 'id')`
- context: `user.profile.id` access after optional join path.

**Output:**
- Root cause, bounded fix options, and concrete verification commands.
