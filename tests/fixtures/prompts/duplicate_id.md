---
id: valid_template
name: Duplicate ID Template
version: "1.0"
classification: debug
tags:
  - debug
purpose: Duplicate ID fixture for validator tests.
when_to_use: Use for duplicate-id failure coverage.
when_not_to_use: Never in production.
required_inputs:
  - symptom: Observed failure.
output_contract: Root cause and minimal fix.
eval_criteria:
  - Root cause is explicit.
owner: test-suite
last_updated: "2026-04-23"
lifecycle_state: active
applicability:
  - failure_recovery
last_evaluated_at: "2026-05-21T00:00:00Z"
changelog:
  - version: "1.0"
    date: "2026-04-23"
    note: Fixture seed.
---

## Instructions

Intentionally duplicates another id.
