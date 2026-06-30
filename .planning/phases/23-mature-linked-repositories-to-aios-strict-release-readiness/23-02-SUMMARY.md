---
phase: 23-mature-linked-repositories-to-aios-strict-release-readiness
plan: "02"
subsystem: linked-repo-adoption
tags:
  - quality-contract
  - quality-pipeline
  - governance
key-files:
  created:
    - docs/quality/linked-repo-strict-release-readiness.md
  modified:
    - config/quality-pipeline.json
key-decisions:
  - "Strict release readiness is class-based rather than one identical gate set for every repo."
  - "Repo-local .aios-quality-gate.json files declare gate IDs only; executable commands remain AIOS-owned."
  - "Repos with floor_only or pre_cr_only maturity cannot be marked adoption-ready."
requirements-completed:
  - TBD
completed: 2026-06-24
---

# Phase 23 Plan 02: Class-Based Strict Readiness Contract Summary

Defined the strict release-readiness contract used by the remaining Phase 23 maturation plans.

## Outcome

- Added `docs/quality/linked-repo-strict-release-readiness.md`.
- Added class standards for:
  - platform/control-plane
  - production/public web apps
  - developer tools/packages
  - Python/data/research/course repos
  - content/vault/container repos
- Added `standard.classes`, `standard.non_remote_ci_exception_schema`, and `standard.adoption_readiness_rule` to `config/quality-pipeline.json`.
- Added `repo_class` metadata for all 23 active Phase 23 repos.
- Removed stale inactive quality-pipeline rows so the pipeline config no longer carries inactive-row contamination.
- Updated portfolio and amos-saas inferred commands to use `pnpm` where a `pnpm-lock.yaml` is present.
- Preserved BBDSE as blocked until aggregate or delegated subproject gates replace the floor-only contract.

## Verification

| Check | Result |
| --- | --- |
| `python3 -m json.tool config/quality-pipeline.json` | PASS |
| `jq -e '.standard.classes.platform_control_plane and .standard.non_remote_ci_exception_schema and .standard.adoption_readiness_rule and (.projects \| length == 23)' config/quality-pipeline.json` | PASS |
| `python3 -c '... get_project_quality_pipeline(...) ...'` across active repos | PASS; summaries compute and mostly report expected missing-gate errors |
| `pnpm context:validate` | PASS |
| `git diff --check -- docs/quality/linked-repo-strict-release-readiness.md config/quality-pipeline.json .planning/phases/23-mature-linked-repositories-to-aios-strict-release-readiness` | PASS |

## Deviations From Plan

The generated Plan 23-02 file had no GSD `<task>` blocks. I executed its prose scope inline and recorded this summary as the durable closeout artifact.

## Issues Encountered

Most repos now compute as `error` or `blocked` in the pipeline summary because class metadata exposes missing commands and missing evidence. That is expected and is the input to Plans 23-03 through 23-06.

## Self-Check: PASSED
