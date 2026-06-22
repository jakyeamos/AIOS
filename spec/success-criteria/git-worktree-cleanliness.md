---
id: git-worktree-cleanliness
title: Git Worktree Cleanliness at Completion
scope: global
blocking: true
evaluation_method: heuristic
version: 1.0
---

## Intent

Prevent agents from treating implementation work as complete while completed changes remain uncommitted.

## Applies When

Session close, delivery closeout, sprint completion, release preparation, and any task where the agent claims implementation is complete.

## Required Checks

- Inspect `git status --porcelain` for the active repository before completion.
- Commit each completed logical change set before moving on to the next change set.
- If changes must remain uncommitted, record an explicit accepted tradeoff explaining why completion is still valid.

## Blockers

- Tracked or untracked files are present in `git status --porcelain` at session close.
- Planning or truth artifacts say work is complete while related source changes remain uncommitted.

## Warnings

- Git status cannot be evaluated for a repository-backed task.

## Evidence To Provide

- Clean `git status --porcelain` output, or a commit hash containing the completed change set.
- Accepted tradeoff metadata when the tree intentionally remains dirty.

## Related Criteria

- `truth-file-consistency`
- `workflow-state-integrity`

## Example Good

The agent finishes a service hardening slice, commits the source/test change, commits the truth-file update, and session close sees a clean worktree.

## Example Bad

The agent updates planning summaries and reports verification, but leaves source, tests, and truth files modified without a commit.
