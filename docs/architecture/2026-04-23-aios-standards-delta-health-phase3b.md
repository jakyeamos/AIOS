# AIOS Standards Delta / Project Health (Phase 3b)

Date: 2026-04-23
Owner: AIOS
Status: Implemented

## Overview

Phase 3b adds a governance and remediation control plane that evaluates each linked project against structured standards, computes explainable health scores, and generates Taski-traceable backfill actions.

## Core Artifacts

- Standards registry and seed profile:
  - `config/standards/registry.json`
- Scoring and delta service:
  - `services/standards_health.py`
- Runtime hook integration (session-close evaluation):
  - `bin/hook-stop.py`
- Durable schema additions:
  - `schema.sql`
  - `data/schema.sql`
  - `aios-ui/server/aios/schema.ts`
- Metadata snapshot visibility:
  - `services/aios_cli.py` (`aios metadata --json`)
- Taski/UI integration:
  - `aios-ui/server/aios/standards-health.ts`
  - `aios-ui/server/aios/taski.ts`
  - `aios-ui/components/projects/TaskiProjectSurface.tsx`
  - `aios-ui/app/projects/page.tsx`

## Standards Model

Standards are first-class objects with:

- identity and domain (`id`, `domain`, `version`, `introduced_version`)
- severity and weighting (`weight`, `severity_if_missing`)
- evaluation contract (`evaluation_method`, `expected_state`)
- remediation guidance (`remediation_playbook`, `blocking_dependencies`)
- governance controls (`applicability`, `waiver_policy`, related criteria mappings)

Domains currently seeded:

- architecture
- code_quality
- testing
- security
- observability
- documentation
- workflow_agent_control
- release_ci_discipline
- product_readiness

## Assessment and Delta Storage

New tables:

- `standards_profiles`
- `standards_definitions`
- `project_standards_profiles`
- `standards_assessments`
- `standards_delta_items`
- `standards_backfill_tasks`
- `standards_health_snapshots`

Assessment statuses:

- `pass`
- `partial`
- `fail`
- `unknown`
- `waived`
- `not_applicable`

`unknown` is preserved as a first-class state and does not collapse into `fail`.

## Explainable Scoring

Penalty model:

- pass = `0`
- partial = `0.5 × weight`
- fail = `1.0 × weight`
- unknown = `0.75 × weight`
- regressed fail = `1.25 × weight`
- waived = `0`
- not_applicable = excluded

Score normalization:

- denominator: `sum(applicable_weight × 1.25)`
- score: `100 × (1 - weighted_penalty / denominator)`

Additional metrics:

- domain-level scores
- weighted delta
- unmet standards count
- critical delta count
- regression count
- unknown count and unknown coverage
- evaluation confidence

All score inputs are persisted for inspectability.

## Backfill Prioritization and Taski Mapping

`DeltaItem` is the bridge between standards and project work.

Priority formula:

`priority = (severity × leverage × dependency_unlock × regression_penalty) / effort`

Backfill buckets:

- foundational
- high_leverage
- quick_wins
- blocked
- waived_deferred

Each generated backfill task is traceable to a specific standard delta (`standard_id`, `delta_item_id`, expected state, acceptance criteria, expected health impact).

## Versioning and Migration Delta

Version-aware project profiles are stored in `project_standards_profiles`.

Each snapshot includes migration metadata:

- attached standards version
- latest profile version
- migration delta count/weight
- standards introduced after the attached version

This separates active failures from “met prior version but not yet upgraded” gaps.

## Evaluation Architecture

The evaluator is source-agnostic by design:

- supports auto/semi-auto/manual methods
- allows per-standard manual overrides
- supports waiver metadata (`rationale`, `owner`, `review date`, portfolio visibility)

Current runtime trigger:

- `hook-stop.py` evaluates standards health on session close for linked projects.

## UI Surfaces

Project detail view now includes:

- health header
- domain breakdown
- delta matrix
- backfill lane
- standards migration panel

Projects overview adds portfolio-ready health columns:

- health score
- critical deltas
- unknown coverage
- score trend delta (latest vs previous snapshot)

## Tests

Added:

- `tests/test_standards_health.py`

Updated:

- `tests/test_aios_cli.py`

Validation performed:

- `uv run pytest -q` (full suite)
- `pnpm lint` in `aios-ui` (warnings only; no errors)
