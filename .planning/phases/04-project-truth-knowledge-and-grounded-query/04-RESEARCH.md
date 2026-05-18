---
phase: 04-project-truth-knowledge-and-grounded-query
phase_number: "04"
type: research
updated: 2026-05-17
---

# Phase 4 Research

## Existing Strengths

- `PROJECT.md` already acts as a durable repo truth file and has been updated consistently during the autonomous run.
- Grounded query can already incorporate project dossier, topic graph, CTS context, and latest packet provenance.
- Phase 3 now leaves behind lifecycle, resume, and closeout evidence that can enrich truth freshness and query answers.

## Existing Weaknesses

- Truth freshness rules are mostly procedural discipline, not yet enforced as a runtime contract.
- There is still no first-class distinction between accepted truth, candidate updates, and inferred knowledge across every operator surface.
- Grounded query is stronger than before, but it still needs explicit default-layer question coverage tied to truth freshness and runtime closeout evidence.

## Code Observations

- `PROJECT.md` and adjacent docs remain the most immediate truth authority for the local AIOS project.
- `services/aios_cli.py`, `aios-ui/server/aios/query.ts`, and knowledge routers already have enough nearby structure to consume truth freshness signals.
- Phase 3 closeout reports provide a natural bridge between run execution and truth update proposals.

## Recommended Phase Split

### 04-01
Truth freshness contract and governed truth-update workflow primitives.

### 04-02
Knowledge/truth linkage hardening and searchable relationship coverage.

### 04-03
Grounded query default-layer answers using truth + recent evidence + recent closeout context.

## Risks

- The live worktree currently includes fresh edits to truth-adjacent files, so execution must not overwrite active user work.
- Query improvements can overfit to the AIOS repo unless the truth-vs-proposal boundary stays explicit.
- Truth automation must not silently rewrite accepted truth without a reviewable path.
