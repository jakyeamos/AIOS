# Quick Task 260623: Default Route Selector Hardening

Date: 2026-06-23

## Objective

Fix the default workflow route selector so common bugfix, UI verification, and code-work phrasing does not fall through to the academic paper workflow.

## Scope

- Remove token-set-based route scoring from workflow selection.
- Require real phrase or family evidence before a workflow can rank.
- Prevent content-generation workflows from winning code-like objectives.
- Add implementation fallback for code-work phrasing.
- Add confidence blocking for weak or tied workflow evidence.
- Add route story regression tests.

## Verification

- `uv run pytest -q tests/test_task_routing.py tests/test_workflow_orchestration.py::test_rank_workflow_candidates_for_recovery_objective tests/test_workflow_orchestration.py::test_recommend_prompt_family_for_implementation_workflow tests/test_workflow_orchestration.py::test_recommend_route_primitives_for_implementation_objective tests/test_aios_cli.py::test_start_work_creates_packet_and_links_current_session tests/test_aios_cli.py::test_start_work_blocks_ambiguous_route_before_packet_creation`
- `uv run ruff check services/workflow_orchestration.py tests/test_task_routing.py`
- Real `start-work` smoke against `/tmp/aios-routing-selector-fix.db` for `Fix the amos-saas login redirect bug and verify the quality checks`.
