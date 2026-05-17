---
phase: 03-workflow-execution-and-run-state
phase_number: "03"
title: Workflow Execution And Run State
status: in_progress
autonomous: true
updated: 2026-05-17
---

# Phase 3 Context

## Goal

Make serious workflow execution durable, resumable, approval-aware, and inspectable from start through closeout.

## Why This Phase Exists

Phase 1 established explicit routing. Phase 2 established packet identity, provenance, and a governed handoff contract. AIOS still needs stronger execution semantics so a routed packet can move through a trustworthy lifecycle without collapsing partial work, approval waits, follow-up debt, and terminal outcomes into ambiguous completion signals.

## Current Runtime Reality

- `services/aios_cli.py` already recognizes `blocked`, `waiting_for_user`, `waiting_for_tool`, and `failed_validation` as canonical attention states.
- `bin/aios_orchestration_runtime.py` persists runs, invocations, run events, writebacks, workflow learning events, and execution reports.
- `bin/hook-stop.py` closes runs, writes memory updates, inserts writebacks, and records criteria/consistency evidence through the explicit run handshake.
- Lifecycle auditing currently focuses on supported states and recent attention events, but the end-state contract still lacks richer terminal nuance for partial completion and follow-up-needed outcomes.
- Resume behavior is still mostly implicit in persisted row linkage rather than an explicit contract with current stage, pending approvals, and next recommended action.

## Main Gaps

1. The lifecycle vocabulary is not expressive enough for partial completion and structured follow-up.
2. Resume semantics exist as raw row linkage rather than a durable, inspectable contract.
3. Closeout evidence is distributed across events, writebacks, memory updates, and criteria records instead of one execution-oriented summary.

## Required Surfaces

- `bin/aios_orchestration_runtime.py`
- `services/aios_cli.py`
- `bin/hook-stop.py`
- `schema.sql`
- `tests/test_orchestration_runtime.py`
- `tests/test_aios_cli.py`

## Exit Condition For The Phase

AIOS can represent active, waiting, blocked, failed-validation, partial, complete, and follow-up-needed outcomes explicitly; a run can be resumed with its packet and recommended next action intact; and closeout exposes checks, approvals, artifacts, unresolved deltas, and writeback implications in one inspectable contract.
