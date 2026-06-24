# Quick Task 260623: AIOS Routing User Stories

Date: 2026-06-23

## Objective

Validate whether AIOS is ready for serious runs to route through it by executing a small set of routing acceptance stories against the current CLI/runtime surfaces.

## Boundary

- Use a copied SQLite database under `/tmp` so `start-work` exercises the real write path without polluting `data/aios.db`.
- Do not change product code during this validation unless a story exposes a small, clear defect that must be fixed immediately.
- Record evidence in this quick-task directory.
- `gsd-sdk` is not available on PATH, so this quick task uses the project quick-task artifact shape manually.

## User Stories

| ID | Story | Acceptance Evidence |
| --- | --- | --- |
| RS-01 | As an agent, I can start a simple AIOS bugfix and receive a routed project, workflow, packet, checks, and closeout handoff. | `start-work` returns `ok=true`, `route_status=ready`, a selected workflow, run id, packet id, and governed packet metadata. |
| RS-02 | As an agent, I can start broad UI verification and receive the user-story verification loop. | Hook/runtime tests pass for user-story verification injection; daily-flow preview shows the route from objective to run/evaluation/writeback stages. |
| RS-03 | As an agent, I can start non-AIOS repo work and get portable dev-process guidance without AIOS-local governance leaking into the route. | `start-work` with an explicit non-AIOS project routes to that project and packet/route metadata remains execution-oriented rather than AIOS-local standards-only. |
| RS-04 | As an agent, ambiguous intent blocks instead of guessing. | `start-work` with intentionally ambiguous objective returns `route-blocked` before packet creation. |
| RS-05 | As an operator, I can inspect why routes were selected. | `operator-search --kinds route_decision` finds route decision rows with drill-down paths. |
| RS-06 | As an agent/operator, partial or routed work has resumable/daily-flow evidence. | `daily-flow --objective --dry-run` and/or replay output exposes canonical steps including route, packet, run, evaluation, writeback, unresolved delta, and next action. |

## Checks

- CLI smoke: `python3 bin/aios.py --json --db /tmp/aios-routing-user-stories.db start-work ...`
- Route inspection: `python3 bin/aios.py --json --db /tmp/aios-routing-user-stories.db operator-search --query ... --kinds route_decision`
- Daily-flow: `python3 bin/aios.py --json --db /tmp/aios-routing-user-stories.db daily-flow --objective ... --dry-run`
- Hook injection regression: focused `uv run pytest` tests for user-story verification and start-work routing.
