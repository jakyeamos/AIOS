# Developer Experience Pack Eval

Date: 2026-06-23
Status: Implemented fixture-backed contract

## Purpose

This eval verifies that the Developer Experience capability pack improves repo usability without becoming an always-loaded checklist. The pack should route intent-specific capabilities only when the task shape justifies them, work with and without second-brain context, and leave small reviewable changes with honest validation evidence.

Machine-readable fixtures live at `config/agent-eval/developer-experience-fixtures.json` and use the `developer-experience` category.

## Criteria

The eval checks whether a run:

- detects missing setup instructions
- detects missing validation commands
- identifies dev-loop bottlenecks such as slow setup, unclear test commands, or missing feedback loops
- produces a priority matrix with impact and effort
- improves README clarity without marketing fluff
- reviews CLI or API interfaces from the consumer perspective, including naming, defaults, errors, examples, and migration impact
- invokes security review only for contextual shell, network, filesystem, credential, destructive, or permission-sensitive risk
- invokes the TypeScript specialist only when API, package boundary, strictness, inference, or build impact justifies it
- routes spec-to-code work into implementation mode with scoped spec fidelity
- logs assumptions instead of blocking unnecessarily
- runs with second-brain context available
- runs with second-brain context unavailable
- produces small, reviewable diffs
- records before/after metrics when measurable, or marks metrics as not measured with a reason

## Fixtures

### Poor Onboarding Repo

The task is to improve first-run onboarding in a repo with stale setup steps, missing validation commands, and unclear clone-to-run expectations.

Expected behavior:

- detect setup ambiguity and cite the source
- propose or implement a README quickstart improvement
- list validation commands or record that they could not be found
- produce an impact/effort priority matrix
- avoid TypeScript specialist invocation when there is no TypeScript API or type-boundary change
- log bounded assumptions instead of blocking on every missing detail

### Public CLI Change

The task is to review and implement a user-facing CLI flag or default change.

Expected behavior:

- review naming, defaults, error text, examples, and migration impact from the user's perspective
- update docs or help text when the interface changes
- invoke security review only when the change touches shell, network, filesystem, credential, destructive, or permission-sensitive behavior
- avoid TypeScript specialist invocation unless the CLI change also changes a TypeScript API or type surface

### TypeScript Package Boundary Change

The task is to implement a package API boundary change from a spec.

Expected behavior:

- invoke TypeScript specialist review for public API surface, strictness, inference, and build impact
- keep implementation scoped to the spec and call out non-goals
- run tests or typecheck, or document why they could not run
- update public contract or migration docs when the package boundary changes

## Second-Brain Parity

Every fixture must define both `available` and `unavailable` second-brain modes. Available second-brain context may improve local recall, but it must not be required for correctness. Unavailable mode must fall back to repo-local artifacts, explicit assumptions, and task evidence without importing private or personal corpus context.

## Metrics

Runs should record or explicitly mark:

- setup command count
- validation command count
- dev-server or test feedback loop time when measurable
- README quickstart ambiguity before and after the change
- changed file count and diff scope
- capabilities invoked and capabilities intentionally skipped
- assumptions logged
- second-brain mode

`not_measured` is acceptable only when paired with a reason, such as no runnable setup command, missing dependency installation permission, or task scope being review-only.

## Failure Cases

A run fails this eval when it:

- treats the DX pack as a generic checklist instead of task-routed capabilities
- invokes security, TypeScript, or docs review without a task-shaped trigger
- rewrites docs into marketing copy instead of improving operator clarity
- makes broad refactors while claiming a small DX change
- skips validation and reports success without a documented reason
- relies on second-brain context in a way that cannot be reproduced in repo-only mode

## Harness Link

`services/harness_eval.py` loads the fixture registry and validates the required `developer-experience` scenarios. The loader is intentionally separate from the normal harness run scorer because these fixtures define routing and capability expectations rather than executable run artifacts.
