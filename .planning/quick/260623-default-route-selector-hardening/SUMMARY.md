# Quick Task 260623: Default Route Selector Hardening Summary

Date: 2026-06-23

## Result

The default workflow selector no longer lets active workflow state create route
relevance by itself. Common bugfix and UI verification phrasing now routes to
implementation work instead of `academic_paper_v1`.

## Changed

- Replaced route-token scoring in `services/workflow_orchestration.py` with
  phrase matching plus explicit family evidence.
- Added code-work evidence for terms such as `fix`, `bug`, `ui`, `db`, `api`,
  `ci`, `test`, and `verify`.
- Added content-generation guards so paper-writing routes still work, but
  code-like objectives suppress `academic_paper_v1`.
- Added implementation fallback for code-work objectives when no more specific
  route wins.
- Added confidence blocking for weak or tied workflow evidence.
- Added route story regression coverage in `tests/test_task_routing.py`.

## Verification

- Passed: `uv run pytest -q tests/test_task_routing.py tests/test_workflow_orchestration.py::test_rank_workflow_candidates_for_recovery_objective tests/test_workflow_orchestration.py::test_recommend_prompt_family_for_implementation_workflow tests/test_workflow_orchestration.py::test_recommend_route_primitives_for_implementation_objective tests/test_aios_cli.py::test_start_work_creates_packet_and_links_current_session tests/test_aios_cli.py::test_start_work_blocks_ambiguous_route_before_packet_creation`
- Passed: `uv run ruff check services/workflow_orchestration.py tests/test_task_routing.py`
- Passed: copied-live-DB smoke with `python3 bin/aios.py --json --db /tmp/aios-routing-selector-fix.db start-work "Fix the amos-saas login redirect bug and verify the quality checks" --project 92e1b456b08dc985`, selecting `implementation-delivery`.

## Remaining Blocker

This fixes the default selector blocker from the routing user stories. The
separate daily-flow/next-action live-schema failure remains open.
