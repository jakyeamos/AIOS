---
id: valid_template
name: Valid Template
version: "1.0"
classification: debug
tags:
  - debug
  - fix
purpose: Valid template fixture for validator tests.
when_to_use: Use when debugging failures.
when_not_to_use: Do not use for planning-only tasks.
required_inputs:
  - symptom: Observed failure.
output_contract: Root cause and minimal fix.
eval_criteria:
  - Root cause is explicit.
owner: test-suite
last_updated: "2026-04-23"
changelog:
  - version: "1.0"
    date: "2026-04-23"
    note: Fixture seed.
---

## Instructions

Do debugging.
