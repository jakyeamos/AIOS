---
phase: 05-governed-writeback-and-approval-control
phase_number: "05"
title: Governed Writeback And Approval Control
status: pending
autonomous: true
updated: 2026-05-19
---

# Phase 5 Context

## Goal

Make writebacks, approvals, unresolved risks, and follow-up evidence durable parts of every meaningful run.

## Why This Phase Exists

Phases 1 through 4 established routing, packet identity, explicit run state, governed closeouts, truth freshness, knowledge boundaries, and truth-first query. The next gap is governance: important state changes must be emitted as reviewable proposals, approval-sensitive mutations must not silently promote, and every terminal serious run needs durable writeback, follow-up, or explicit no-learning evidence.

## Current Reality

- `improvement_writebacks`, `memory_writeback_proposals`, `workflow_synthesis_proposals`, and `promotion_lifecycle_items` already exist but do not yet present one cross-asset governance contract.
- Closeout summaries contain pending approvals and unresolved deltas, but there is no single audit that proves terminal runs are not silently dropping writeback/follow-up/no-learning evidence.
- Divergent strategy and workflow synthesis already use approval concepts, but project truth, prompts, skills, workflows, standards, and packets need a uniform authority boundary.

## Main Gaps

1. Cross-asset writeback proposals need one inspection contract across truth, prompts, skills, workflows, standards, packets, and memory.
2. Approval policy classes need explicit gate semantics so high-impact changes cannot silently promote.
3. Terminal runs need an auditable guarantee that they ended with writeback, follow-up, or no-learning evidence.
4. Unresolved risks and follow-up actions need durable closeout visibility beyond narrative summaries.

## Required Surfaces

- `services/aios_cli.py`
- `bin/hook-stop.py`
- `bin/aios_orchestration_runtime.py`
- `schema.sql`
- `improvement_writebacks`
- `memory_writeback_proposals`
- `workflow_execution_reports`
- `workflow_learning_events`
- `promotion_lifecycle_items`
- `aios-ui/server/routers/control-plane.ts`
- `aios-ui/server/routers/divergent.ts`

## Exit Condition For The Phase

AIOS can prove that important truth, prompt, skill, workflow, standard, and packet changes are reviewable; approval-sensitive changes cannot silently promote; terminal meaningful runs leave writeback, follow-up, or no-learning evidence; and unresolved risks/follow-ups remain visible after closeout.
