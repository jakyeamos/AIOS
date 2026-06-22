# Quick Task Plan: AIOS Subsystem Extraction Governance

**Date:** 2026-06-05
**Task:** Create a Markdown plan for consolidating overlap and splitting mature AIOS functionality into reusable subsystems or repos, and update repo rules so the plan stays current as boundaries evolve.

## Context

AIOS currently hosts orchestration, context compilation, success criteria, workflow learning, CTS, hooks, local storage, and the operator UI in one repository. That is useful while subsystem contracts are still changing together, but it risks hiding reusable product boundaries as capabilities mature and can also hide overlapping concepts that should be consolidated before extraction.

## Scope

- Add a living subsystem consolidation and extraction plan under `.planning/`.
- Define maturity gates for keeping functionality in-repo, modularizing internally, extracting into packages, or promoting into separate repos.
- Identify consolidation candidates where overlapping subsystems should merge, share a contract, or clarify boundaries before extraction.
- Add an `AGENTS.md` rule requiring agents to update the plan when subsystem ownership, contracts, maturity, or extraction status changes.
- Require every new roadmap phase to declare subsystem consolidation and extraction posture goals.
- Keep the change doc-only and avoid touching unrelated modified files.

## Acceptance Criteria

- The plan names candidate subsystems, current home, extraction posture, dependencies, consolidation candidates, and next maturity evidence.
- The plan makes AIOS remain the orchestrating product instead of forcing premature repo splits.
- `AGENTS.md` tells future agents when and how to update the plan.
- New phases are required to state the subsystem consolidation and extraction posture goals they are aiming for.
- The truth file records that this architecture governance artifact now exists.

## Verification

- Review Markdown structure and links.
- Run `git diff --check` after edits.
