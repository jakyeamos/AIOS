---
phase: 04-project-truth-knowledge-and-grounded-query
phase_number: "04"
title: Project Truth, Knowledge, And Grounded Query
status: pending
autonomous: true
updated: 2026-05-17
---

# Phase 4 Context

## Goal

Maintain current project truth and linked operational knowledge as mandatory operating surfaces rather than best-effort documentation byproducts.

## Why This Phase Exists

Phases 1 through 3 now give AIOS a routed serious-work entrypoint, governed packet contract, lifecycle nuance, resumable state, and governed closeout evidence. The next gap is truth quality: AIOS still needs stronger project-truth discipline, better linkage between truth and knowledge artifacts, and grounded query answers that combine current truth with recent runtime evidence before a human manually assembles context.

## Current Reality

- `PROJECT.md` is the main truth artifact for the AIOS repo itself, but truth freshness still depends on disciplined manual updates.
- Knowledge objects, relationships, and grounded query surfaces already exist, but they are not yet fully governed by explicit truth freshness and truth-vs-proposal boundaries.
- Recent runtime work now produces stronger routing, packet, lifecycle, resume, and closeout evidence that Phase 4 can use as first-class knowledge inputs.

## Main Gaps

1. Truth freshness needs explicit update and drift rules.
2. Truth, decisions, prompts, skills, workflows, and research need stronger linkage in searchable knowledge surfaces.
3. Grounded query should answer default-layer operator questions from truth plus recent evidence, not just from neighboring retrieval signals.

## Current Blocking Context

The live worktree currently has fresh changes in truth-adjacent files including `PROJECT.md`, `README.md`, `docs/STORES.md`, and related runtime surfaces. Those need to be treated as active input rather than overwritten during Phase 4 execution.

## Required Surfaces

- `PROJECT.md`
- `README.md`
- `docs/STORES.md`
- knowledge object and relationship tables
- `aios-ui/server/routers/knowledge.ts`
- `aios-ui/server/routers/query.ts`
- project dossier / grounded query logic

## Exit Condition For The Phase

AIOS has a governed truth-update contract, linked truth and knowledge surfaces, and grounded query answers that can reliably answer what changed, what remains unresolved, and what prior knowledge matters before manual context assembly.
