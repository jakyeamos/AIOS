# AIOS Case Study

AIOS is a local-first operating layer for agent-driven software work. The goal is to make serious AI-assisted work inspectable after the session ends: what happened, what evidence was produced, what project state changed, and what should happen next.

## Problem

Agent sessions generate a lot of useful operational data, but most of it disappears into transcripts or terminal scrollback. That makes follow-up work expensive because the next session has to rediscover decisions, blockers, quality results, and project context.

## Architecture

The public branch shows the foundation of a larger local system:

```text
agent session
  -> lifecycle hooks
  -> local logs and SQLite-ready storage
  -> review scripts and archive planning
  -> project memory and follow-up notes
```

The architecture is intentionally local-first. AIOS stores work context on disk, keeps structured state in SQLite, and treats Git repositories as the reviewed source of truth for code and durable documentation.

## What Works Today In This Public Branch

- Session lifecycle hook entrypoints exist for start, prompt, tool, stop, and compaction events.
- Hook scripts are designed around local AIOS paths under `$HOME/AIOS`.
- A SQLite initialization path exists for local installations that provide the expected schema.
- The AI-history import design explains how exported conversations should become reviewable archive notes.
- The implementation plan documents the separation between raw imports, generated artifacts, reviewed notes, and promoted memory.

## What Works In The Broader Local System

The broader local AIOS workbench is used as an operating layer for routed project work: run state, project packets, quality evidence, linked project health, dashboard inspection, and follow-up visibility. The public branch is not yet the full clean-clone productization of that workbench, which is why the README now presents this repo as a case study rather than a finished SaaS-style release.

## Technical Decisions

- **Local-first by default:** operational data stays on the developer machine unless explicitly promoted elsewhere.
- **Boundary capture:** hooks record events at session boundaries so later review starts from evidence.
- **Review before memory:** raw automation output is not treated as trusted knowledge until reviewed.
- **Git as reviewed truth:** code and durable project docs remain in repos; AIOS records operational context around them.
- **Small scripts over opaque services:** the public slice favors inspectable entrypoints that can be audited before installation.

## Next Public Promotion Steps

1. Promote the current SQLite schema and daily-use CLI flow to the public branch.
2. Add a seeded demo dataset so the dashboard can be evaluated without private local history.
3. Publish a clean-clone walkthrough for `doctor -> start-work -> daily-flow -> next-action`.
4. Add screenshots or a short recording of the dashboard inspecting a completed run.
5. Separate private/local path defaults from portable example configuration.

## Hiring Signal

AIOS demonstrates infrastructure thinking around AI-assisted development: local state, evidence trails, project health, workflow routing, and a bias toward reviewable automation instead of hidden background magic.
