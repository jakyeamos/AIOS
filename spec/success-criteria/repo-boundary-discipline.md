---
id: repo-boundary-discipline
title: Repository Boundary Discipline
scope: global
blocking: true
evaluation_method: heuristic
version: 1.0
---

## Intent

Prevent unintended edits outside the target repository or task scope.

## Applies When

Any task that writes files, modifies project structure, or automates edits.

## Required Checks

- Keep changed files inside the active project working directory unless explicitly approved.
- Avoid accidental writes to unrelated repositories or personal/system paths.
- Ensure artifact paths are traceable to the intended task scope.

## Blockers

- Changed files detected outside the active project boundary without explicit approval.
- Cross-repo writes performed unintentionally.

## Warnings

- Boundary-adjacent paths touched with ambiguous ownership.
- Scripts writing to multiple roots without explicit intent.

## Evidence To Provide

- List of changed files and why each belongs to scope.
- Any explicit approvals for cross-boundary writes.

## Related Criteria

- `security-review`

## Example Good

All modified files are within the active repo, with any external writes treated as explicit and documented exceptions.

## Example Bad

A refactor task unintentionally edits files in another project due to a broad script path pattern.
