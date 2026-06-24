# TMCP Tier-One Readiness Plan

Date: 2026-06-23

## Objective

Move TMCP from tier-one candidate toward tier-one default by planning the remaining managed-run default adoption gate and implementing the remaining local graph, scoring, shortcut, overlay, eval-claim, and contract gaps.

## Scope

- Add managed-run hard-default TMCP adoption to an AIOS phase plan.
- Verify and repair the canonical local 99-skill graph without destructive harvest regeneration.
- Strengthen graph-backed runtime scoring with project scope and updated trigger vocabulary.
- Make shortcut promotion respect selected source-skill hashes.
- Make overlay traversal require explicit matched triggers and behavior added beyond canonical nodes.
- Clarify the tier-one candidate contract and eval-claim boundary.

## Verification

- `uv run pytest -q tests/test_tmcp_runtime.py tests/test_skills_harvest.py`
- `PYTHONPATH=.:bin UV_CACHE_DIR=/private/tmp/uv-cache-tmcp uv run pytest -q tests/test_orchestration_runtime.py::test_managed_runtime_completes_via_explicit_handshake tests/test_orchestration_runtime.py::test_managed_runtime_uses_promoted_tmcp_shortcut tests/test_orchestration_runtime.py::test_managed_runtime_routes_workflow_strategy_comparison_to_planning`
- `uv run ruff check services/skills_harvest.py services/tmcp_runtime.py services/aios_cli.py tests/test_skills_harvest.py tests/test_tmcp_runtime.py`
- `uv run python -m compileall services/tmcp_runtime.py services/skills_harvest.py services/aios_cli.py tests/test_tmcp_runtime.py tests/test_skills_harvest.py`
- `pnpm context:validate`
- JSON validation for `config/tmcp/canonical-graph.json`, `config/tmcp/registry.json`, and `skills-library/skills.tmcp/graph.json`
