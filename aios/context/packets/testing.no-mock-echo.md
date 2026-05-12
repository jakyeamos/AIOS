---
id: packets.testing.no-mock-echo
title: No Mock Echo Testing Packet
tier: packet
scope:
  - all_projects
priority: high
status: active
summary: Testing packet for avoiding shallow tests that only mirror mocked behavior.
applies_when:
  - task_touches_testing
tags:
  - testing
  - validation
  - mocks
last_reviewed: 2026-05-12
---

Avoid tests that only assert the mock returned what the mock was told to return.
Routing tests should exercise real parsing, scoring, selection, and output generation.
Mocks are acceptable only at unavoidable external boundaries.

## Acceptance Criteria

- Tests fail before implementation when behavior is absent.
- Tests inspect actual output and side effects.
