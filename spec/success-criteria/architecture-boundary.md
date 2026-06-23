---
id: architecture-boundary
title: Architecture Boundary and Modularity Gate
scope: global
blocking: true
evaluation_method: heuristic
version: 1.0
---

## Intent

Keep changes inside the right layers and prevent agent-generated giant files, circular imports, and duplicated subsystem logic.

## Applies When

Any implementation, bugfix, refactor, or review task that changes code structure, module boundaries, UI/server boundaries, data access, or shared utilities.

## Required Checks

- Confirm the change belongs in the touched layer.
- Keep domain rules out of display components.
- Keep API, database, and filesystem IO behind established module boundaries.
- Check for circular imports and forbidden cross-package imports.
- Reuse existing utilities instead of duplicating behavior.
- Identify files/components that became too large for the local convention.

## Blockers

- New circular dependency is introduced.
- Code crosses an enforced architecture boundary.
- Business logic is moved into display-only UI code.
- Existing utility or domain behavior is duplicated instead of reused.
- One file becomes a mixed-concern object without documented necessity.

## Warnings

- Component or module size is above local guidance but still coherent.
- Extraction would help but is not required to keep the current change safe.
- Boundary ownership is unclear and should be clarified in project truth.

## Evidence To Provide

- Boundary violations found or ruled out.
- Files that grew too large.
- Suggested extraction or reason none is needed.
- Import or architecture-check output where available.

## Related Criteria

- `repo-boundary-discipline`
- `thin-display`
- `simplicity`

## Example Good

A server mutation delegates domain calculation to an existing service and leaves the UI component as a thin renderer.

## Example Bad

A dashboard component starts querying the database, enforcing permissions, transforming data, and rendering all in one file.
