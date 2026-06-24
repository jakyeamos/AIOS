# TMCP Tier-One Readiness Summary

Date: 2026-06-23

## Completed

- Added the managed-run hard-default TMCP adoption requirement to Phase 20 Plan 20-07 instead of claiming it complete early.
- Added `aios skills graph-verify` with `--repair` and `--refresh` for existing generated libraries.
- Repaired/refreshed the local ignored `skills-library/skills.tmcp/graph.json`; verification now passes with 99 source-skill nodes, 99 manifest skills, and 2,848 source hashes.
- Expanded generated graph task vocabulary for planning and visual polish.
- Made runtime graph versioning include `graph.json` and `skills.lock`.
- Added selected source-skill hashes to packets and shortcut promotion checks so changed source material bypasses promoted shortcuts.
- Added overlay evidence fields and behavior-addition gating for namespace traversal.
- Updated ADR 0003 with the tier-one candidate contract and eval-claim boundary.

## Verification

- `uv run pytest -q tests/test_tmcp_runtime.py tests/test_skills_harvest.py` passed with 16 tests.
- `PYTHONPATH=.:bin UV_CACHE_DIR=/private/tmp/uv-cache-tmcp uv run pytest -q tests/test_orchestration_runtime.py::test_managed_runtime_completes_via_explicit_handshake tests/test_orchestration_runtime.py::test_managed_runtime_uses_promoted_tmcp_shortcut tests/test_orchestration_runtime.py::test_managed_runtime_routes_workflow_strategy_comparison_to_planning` passed with 3 tests.
- `uv run ruff check services/skills_harvest.py services/tmcp_runtime.py services/aios_cli.py tests/test_skills_harvest.py tests/test_tmcp_runtime.py` passed.
- `uv run python -m compileall services/tmcp_runtime.py services/skills_harvest.py services/aios_cli.py tests/test_tmcp_runtime.py tests/test_skills_harvest.py` passed.
- `pnpm context:validate` passed.
- JSON validation passed for `config/tmcp/canonical-graph.json`, `config/tmcp/registry.json`, and `skills-library/skills.tmcp/graph.json`.

## Remaining Blocker

TMCP still should not be called fully tier-one until Phase 20 Plan 20-07 implements and verifies a hard managed-run default adoption contract: every non-trivial managed run must compile, persist, and evaluate a TMCP packet unless an explicit bypass reason is logged.
