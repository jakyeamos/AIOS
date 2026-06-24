# TMCP Skill Compiler Upgrade Summary

Date: 2026-06-23

## Completed

- Added behavior atoms to generated and repaired `skills.tmcp/graph.json` task/module/branch/source-skill rows.
- Added `token_cost`, `adds_behavior`, `redundant_with`, and `risk_if_omitted` metadata to graph nodes.
- Added runtime packet optimization that prunes redundant low-risk modules when selected source skills already cover the same behavior atoms.
- Added section-level source-skill excerpts that prefer procedure, decision, tool, validation, failure, trigger, and constraint sections over whole-file loading.
- Added negative selection evidence to `skipped_nodes` when behavior diffing or packet optimization prunes a plausible node.
- Added `behavior_atoms`, `packet_optimization`, `node_usefulness`, and `omitted_requirements` to compiled packets.
- Added additive receipt columns `node_usefulness_json` and `omitted_requirements_json`.
- Extended shortcut promotion artifacts with compiled-packet metadata and known-failure-case placeholders.
- Refreshed local `skills-library/skills.tmcp/graph.json`; read-only verification passes with 99 source-skill nodes and 2,848 source hashes.

## Verification

- `uv run pytest -q tests/test_tmcp_runtime.py tests/test_skills_harvest.py` passed with 17 tests.
- `PYTHONPATH=.:bin UV_CACHE_DIR=/private/tmp/uv-cache-tmcp uv run pytest -q tests/test_orchestration_runtime.py::test_managed_runtime_completes_via_explicit_handshake tests/test_orchestration_runtime.py::test_managed_runtime_uses_promoted_tmcp_shortcut tests/test_orchestration_runtime.py::test_managed_runtime_routes_workflow_strategy_comparison_to_planning` passed with 3 tests.
- `uv run ruff check services/skills_harvest.py services/tmcp_runtime.py services/aios_cli.py tests/test_skills_harvest.py tests/test_tmcp_runtime.py bin/aios_orchestration_runtime.py` passed.
- `uv run python -m compileall services/tmcp_runtime.py services/skills_harvest.py services/aios_cli.py bin/aios_orchestration_runtime.py tests/test_tmcp_runtime.py tests/test_skills_harvest.py` passed.
- `pnpm context:validate` passed.
- `UV_CACHE_DIR=/private/tmp/uv-cache-tmcp uv run python bin/aios.py --json skills graph-verify --library skills-library --graph-profile config/tmcp/canonical-graph.json` passed.
