---
phase: 10-operator-surfaces-query-and-daily-flow-visibility
plan: "01"
subsystem: operator-search
tags: [operator-surfaces, search, cli, drill-down, safe-projection]
requires:
  - phase: 09-continuous-learning-and-conservative-optimization
    provides: learning evidence and promotion lifecycle rows
provides:
  - Python cross-entity operator search backend
  - `aios operator-search` CLI command
  - OperatorSurface contracts-audit row
affects: [operator-search, cli, contracts-audit, drill-down-paths]
tech-stack:
  added: []
  patterns:
    - bounded LIKE search with recency and exact-key boosts
    - safe-column projection only
    - drill-down path construction per entity kind
key-files:
  created:
    - services/operator_search.py
    - tests/test_operator_search.py
    - .planning/phases/10-operator-surfaces-query-and-daily-flow-visibility/10-01-SUMMARY.md
  modified:
    - services/aios_cli.py
    - tests/test_aios_cli.py
    - tests/test_architecture_enforcement.py
key-decisions:
  - "No new SQLite tables or FTS index; search reads existing tables with per-kind caps."
  - "Python search shape is canonical for Plan 04's TypeScript mirror."
  - "OperatorSurface is `partial` until the UI mirror, tRPC router, and rendered UI land in later Phase 10 plans."
requirements-completed: []
requirements-partial: [OPER-01, OPER-03]
duration: 23min
completed: 2026-06-01
---

# Phase 10 Plan 01 Summary

**Python operator-search backend and CLI**

## Entity Contract

`EntityKind` contains 17 values:

`run`, `packet`, `writeback`, `finding`, `prompt_template`, `prompt_use`, `skill`, `workflow`, `knowledge_object`, `route_decision`, `delta_item`, `backfill_task`, `automation`, `experiment`, `divergent_run`, `learning_pattern`, `promotion_lifecycle_item`.

`OperatorSearchHit` shape:

`kind`, `id`, `title`, `summary`, `project_id`, `score`, `source_table`, `last_updated_at`, `drill_down_path`, `metadata`.

## Drill-Down Paths

- `run` -> `/runs/<id>`
- `packet` -> `/control?packet=<id>`
- `writeback` -> `/writebacks#<id>`
- `finding` -> `/runs/<run_id>?finding=<id>`
- `prompt_template` -> `/prompts#<id>`
- `prompt_use` -> `/prompts#use-<id>`
- `skill` -> `/workflows?skill=<id>`
- `workflow` -> `/workflows#<id>`
- `knowledge_object` -> `/knowledge#<id>`
- `route_decision` -> `/runs/<run_id>?route=<id>`
- `delta_item` -> `/projects/<project_id>?delta=<id>` or `/projects?delta=<id>`
- `backfill_task` -> `/projects/<project_id>?backfill=<id>` or `/projects?backfill=<id>`
- `automation` -> `/automations#<id>`
- `experiment` -> `/experiments#<id>`
- `divergent_run` -> `/divergent#<id>`
- `learning_pattern` -> `/control?pattern=<id>`
- `promotion_lifecycle_item` -> `/workflows?promotion=<id>`

## Scoring Constants

- `MAX_QUERY_LENGTH = 200`
- `DEFAULT_LIMIT = 50`
- `MAX_LIMIT = 200`
- `PER_KIND_CAP = 20`
- `RECENCY_BOOST_HALF_LIFE_DAYS = 14.0`
- `EXACT_KEY_BOOST = 0.3`

Scoring uses title LIKE contribution, summary LIKE contribution, exact-key boost, and exponential recency boost. Empty query returns recent activity across kinds.

## CLI

`aios operator-search` accepts:

- `--query <text>` required, capped at 200 chars
- `--kinds <EntityKind>` repeatable
- `--project <project_id>` optional
- `--limit <n>` default 50, max 200
- `--json`

Response data contains `hits`, `total_hits`, `query`, `kinds`, `project_id`, and `limit`.

## Contracts Audit

`contracts-audit` now includes:

- `name`: `OperatorSurface`
- `status`: `partial` until `aios-ui/server/aios/operator-search.ts` and the later tRPC/UI surfaces ship
- `source_of_truth`: `services/operator_search.py`, `services/aios_cli.py:cmd_operator_search`

## Verification

- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_operator_search.py tests/test_aios_cli.py tests/test_architecture_enforcement.py -x -q` -> 72 passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check services/operator_search.py services/aios_cli.py tests/test_operator_search.py tests/test_aios_cli.py tests/test_architecture_enforcement.py` -> passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format --check services/operator_search.py services/aios_cli.py tests/test_operator_search.py tests/test_aios_cli.py tests/test_architecture_enforcement.py` -> passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run basedpyright services/operator_search.py services/aios_cli.py` -> passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run python -c "import services.aios_cli as m; p=m.create_parser(); p.parse_args(['operator-search', '--query', 'x'])"` -> passed

## Next Plan Readiness

Plan 10-02 can build next-action fusion on top of the same drill-down discipline. Plan 10-04 must mirror `OperatorSearchHit` and `_drill_down_for` in TypeScript without adding a separate search truth.

---
*Phase: 10-operator-surfaces-query-and-daily-flow-visibility*
*Completed: 2026-06-01*
