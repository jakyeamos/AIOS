# Quick Task 260623: AIOS Routing User Stories Summary

Date: 2026-06-23

## Result

AIOS is not ready to route all serious runs through the default `start-work`
path yet.

The run envelope is strong: explicit project selection, packet persistence,
governed handoff sections, success-criteria injection, backend recommendation,
route-decision search, and ambiguity blocking all work. The default workflow
selector is not reliable enough for broad use because ordinary bugfix phrasing
routes to the academic paper workflow unless the objective includes a longer
implementation trigger such as `implement`.

## Evidence Boundary

- Copied live DB: `/tmp/aios-routing-user-stories.db`
- Live DB was not modified.
- `gsd-sdk` was not available on PATH, so the quick-task artifact was created
  manually.

## Story Results

| ID | Status | Evidence |
| --- | --- | --- |
| RS-01 | Fail | `start-work "Fix the AIOS start-work route metadata bug" --project 5bcd40a28db7463c` returned `ok=true` and persisted a governed packet, but selected `academic_paper_v1` / `content_generation` instead of `implementation-delivery`. |
| RS-02 | Partial | Broad UI verification also persisted a governed packet, but selected `academic_paper_v1` / `content_generation`. Focused hook injection tests passed. |
| RS-03 | Partial | Explicit non-AIOS project routing selected `amos-saas` correctly, but `Fix the amos-saas login redirect bug...` again selected `academic_paper_v1`. Rephrasing as `Implement the amos-saas login redirect fix...` selected `implementation-delivery`. |
| RS-04 | Pass | `start-work "Fix the bug"` returned `route-blocked` before packet creation with message: `No registered project matched the objective or current working directory strongly enough.` |
| RS-05 | Pass | `operator-search --query "login redirect" --kinds route_decision --json` found the route decision for the amos-saas run and returned `/runs/...?...` drill-down metadata. |
| RS-06 | Fail | `daily-flow --objective ... --dry-run --json` crashed on the copied live DB with `sqlite3.OperationalError: no such column: f.run_id`. |

## Root Causes

1. Workflow ranking ignores short but common implementation words.

   `services.workflow_orchestration._tokenize()` only keeps tokens with four or
   more characters. That drops `fix` and `bug`, so common bugfix objectives only
   receive the generic active-workflow score. `academic_paper_v1` sorts first
   among tied active workflows.

2. Daily-flow / next-action expects a test-only schema shape.

   `services.next_action._from_open_blockers()` selects and joins
   `success_criteria_findings.run_id`, but the real AIOS schema links findings
   through `evaluation_id`. The unit fixture in `tests/test_daily_flow.py`
   creates a `run_id` column, so focused tests pass while the copied live DB
   fails.

3. CLI JSON behavior is inconsistent for `operator-search`.

   `python3 bin/aios.py --json --db ... operator-search ...` exited
   successfully with no visible output. Supplying the subcommand-local `--json`
   produced the expected JSON envelope.

## Verification

- Passed: `uv run pytest -q tests/test_aios_cli.py::test_start_work_creates_packet_and_links_current_session tests/test_aios_cli.py::test_start_work_blocks_ambiguous_route_before_packet_creation tests/test_aios_cli.py::test_daily_flow_preview_cli tests/test_agent_rules_runtime.py -q`
- Manual CLI stories executed against `/tmp/aios-routing-user-stories.db`

## Readiness Call

Use AIOS now for explicitly phrased implementation work such as
`Implement ...`, especially when a project id is provided.

Do not make AIOS the default launcher for all serious runs until:

1. bugfix/debug phrasing routes to `implementation-delivery` or
   `failure-recovery` without requiring the word `implement`;
2. daily-flow/next-action works against the real checked-in/live schema;
3. route story tests run against a schema copied from `schema.sql` or the live
   DB shape, not only hand-built fixtures.
