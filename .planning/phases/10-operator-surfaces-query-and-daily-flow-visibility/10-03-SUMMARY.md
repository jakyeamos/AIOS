---
phase: 10-operator-surfaces-query-and-daily-flow-visibility
plan: "03"
subsystem: daily-flow
tags: [operator-surfaces, daily-flow, cli, provenance, dry-run]
requires:
  - phase: 01-project-workflow-and-prompt-routing
    provides: route primitive recommendation
  - phase: 02-context-query-and-briefing-compilation
    provides: agentized packet projection and briefing packets
  - phase: 05-writeback-governance
    provides: improvement writebacks
  - phase: 06-standards-resolution-and-evaluation
    provides: success criteria findings
  - phase: 07-delta-scoring-and-health-backfill
    provides: standards deltas
  - phase: 10-operator-surfaces-query-and-daily-flow-visibility
    provides: next-action fusion
provides:
  - Python DailyFlowTrace backend
  - `aios daily-flow` CLI command
  - `agentize_request(dry_run=True)` SAVEPOINT rollback contract
  - DailyFlow contracts-audit row
affects: [daily-flow, agentize, cli, contracts-audit, operator-surfaces]
tech-stack:
  added: []
  patterns:
    - read-only replay projection
    - SAVEPOINT-backed preview dryness
    - canonical ordered trace steps
    - graceful missing-source degradation
key-files:
  created:
    - services/daily_flow.py
    - tests/test_daily_flow.py
    - .planning/phases/10-operator-surfaces-query-and-daily-flow-visibility/10-03-SUMMARY.md
  modified:
    - services/agentize.py
    - services/aios_cli.py
    - tests/test_aios_cli.py
    - tests/test_architecture_enforcement.py
key-decisions:
  - "Preview traces are inspection-only and do not create orchestration_runs or briefing_packets rows."
  - "Replay returns all eight canonical steps even when upstream phase tables are missing."
  - "Every step carries provenance, evidence_ref, freshness, metadata, and a non-empty drill_down_path."
requirements-completed: []
requirements-partial: [OPER-03, OPER-04]
duration: 31min
completed: 2026-06-01
---

# Phase 10 Plan 03 Summary

**Python daily-flow backend and CLI**

## Trace Contract

`DailyFlowStepKind` values, in canonical order:

`goal`, `route`, `packet`, `run`, `evaluation`, `writeback`, `unresolved_delta`, `next_action`.

`DailyFlowStep` shape:

`kind`, `summary`, `evidence_ref`, `drill_down_path`, `provenance`, `freshness`, `metadata`.

`DailyFlowTrace` shape:

`project_id`, `objective`, `is_preview`, `steps`.

## Source Mapping

- `goal` -> objective text
- `route` -> preview route primitive projection or `orchestration_runs.route_result_json`
- `packet` -> preview `agentize_request` packet or `briefing_packets`
- `run` -> `orchestration_runs`
- `evaluation` -> `success_criteria_findings`
- `writeback` -> `improvement_writebacks`
- `unresolved_delta` -> `standards_delta_items`
- `next_action` -> `services.next_action.get_next_actions`

## Provenance Rules

- `confirmed`: source row or fused next-action exists.
- `inferred`: preview projection from objective, route primitives, or agentized packet.
- `missing`: source table is absent, source row is absent, or preview has no real run-bound data yet.
- `contradictory`: replay sees an open blocker finding on a completed run.

## Agentize Dry-Run Contract

`agentize_request(..., dry_run=True)` wraps the implementation path in `SAVEPOINT`, then `ROLLBACK TO SAVEPOINT`, then `RELEASE SAVEPOINT`. Live mode remains the direct implementation path.

Focused tests cover:

- 100-call dry preview no-leak invariant
- dry packet shape returned without persisted packet rows
- live mode still returning the normal `AgentizedTaskPacket`
- outer transaction isolation while preview uses a nested savepoint

## CLI

`aios daily-flow` accepts mutually exclusive entry modes:

- `--objective <text> [--project <project_id>] [--dry-run] --json`
- `--run-id <id> --json`

Response data contains `trace`, `is_preview`, `objective`, `project_id`, and `step_count`.

## Contracts Audit

`contracts-audit` now includes:

- `name`: `DailyFlow`
- `status`: `partial` until `aios-ui/server/aios/daily-flow.ts` and later tRPC/UI surfaces ship
- `source_of_truth`: `services/daily_flow.py`, `services/agentize.py:agentize_request(dry_run=True)`, `services/aios_cli.py:cmd_daily_flow`

## Verification

- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_daily_flow.py tests/test_aios_cli.py tests/test_next_action.py tests/test_operator_search.py tests/test_architecture_enforcement.py -x -q` -> 109 passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check services/daily_flow.py services/agentize.py services/aios_cli.py tests/test_daily_flow.py tests/test_aios_cli.py tests/test_architecture_enforcement.py` -> passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format --check services/daily_flow.py services/agentize.py services/aios_cli.py tests/test_daily_flow.py tests/test_aios_cli.py tests/test_architecture_enforcement.py` -> passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run basedpyright services/daily_flow.py services/agentize.py services/aios_cli.py` -> passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run python -c "import services.aios_cli as m; p=m.create_parser(); p.parse_args(['daily-flow', '--objective', 'x'])"` -> passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run python -c "import services.aios_cli as m; p=m.create_parser(); p.parse_args(['daily-flow', '--run-id', 'r1'])"` -> passed

## Next Plan Readiness

Plan 10-04 can mirror the Python `DailyFlowTrace` shape in TypeScript and centralize matching drill-down path builders for UI projections. Plan 10-05 will add the tRPC router, and Plan 10-06 will render the trace on run and command-center surfaces.

Previewed traces remain inspection-only; this plan does not add a launch path.

---
*Phase: 10-operator-surfaces-query-and-daily-flow-visibility*
*Completed: 2026-06-01*
