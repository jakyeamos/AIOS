---
id: truth-file-consistency
title: Project Truth File Consistency
scope: project-domain-specific
blocking: true
evaluation_method: heuristic
version: 1.0
---

## Intent

Keep declared project truth synchronized with implemented state so agents and humans can rely on authoritative context.

## Applies When

Any substantive implementation, bugfix, or refactor change in projects that maintain a required truth file (for AIOS: `PROJECT.md`).

## Required Checks

- Update the truth file immediately after each logical change set.
- Reflect new capabilities, constraints, and missing items accurately.
- Avoid stale statements that contradict implemented behavior.

## Blockers

- Substantive code changes committed without corresponding truth-file update.
- Truth file claims behavior that no longer matches implementation.

## Warnings

- Truth file updated but missing important capability or risk implications.
- Broad implementation changes with minimal truth-file detail.

## Evidence To Provide

- Which truth-file section was updated and why.
- How the change set maps to truth-file claims.
- Remaining known gaps after the update.

## Related Criteria

- `workflow-state-integrity`
- `code-simplicity`

## Example Good

Each atomic implementation commit is followed by explicit truth-file updates describing what changed and what remains.

## Example Bad

Control-plane behavior is changed across multiple files while `PROJECT.md` remains unchanged.
