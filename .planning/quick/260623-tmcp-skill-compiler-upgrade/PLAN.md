# TMCP Skill Compiler Upgrade Plan

Date: 2026-06-23

## Objective

Upgrade TMCP toward the intended result: stronger, more token-efficient, more flexible skills that compile only behavior-changing instruction needed for the current prompt.

## Scope

- Represent graph nodes as behavior atoms, not only file-derived Markdown nodes.
- Add token cost, behavior utility, redundancy hints, and omission risk metadata.
- Add runtime behavior diffing and packet optimization.
- Prefer source-skill section excerpts over whole files.
- Record negative selection, node usefulness, omitted requirements, and shortcut compiled-packet metadata.
- Refresh the canonical local graph metadata without rewriting the whole ignored skills library.

## Verification

- `uv run pytest -q tests/test_tmcp_runtime.py tests/test_skills_harvest.py`
- `PYTHONPATH=.:bin UV_CACHE_DIR=/private/tmp/uv-cache-tmcp uv run pytest -q tests/test_orchestration_runtime.py::test_managed_runtime_completes_via_explicit_handshake tests/test_orchestration_runtime.py::test_managed_runtime_uses_promoted_tmcp_shortcut tests/test_orchestration_runtime.py::test_managed_runtime_routes_workflow_strategy_comparison_to_planning`
- `uv run ruff check services/skills_harvest.py services/tmcp_runtime.py services/aios_cli.py tests/test_skills_harvest.py tests/test_tmcp_runtime.py bin/aios_orchestration_runtime.py`
- `uv run python -m compileall services/tmcp_runtime.py services/skills_harvest.py services/aios_cli.py bin/aios_orchestration_runtime.py tests/test_tmcp_runtime.py tests/test_skills_harvest.py`
- `pnpm context:validate`
- `aios skills graph-verify`
