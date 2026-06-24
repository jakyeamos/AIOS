# TMCP Full-Potential Implementation Summary

Date: 2026-06-23

## Completed

- Added `config/tmcp/canonical-graph.json` as the tracked canonical local TMCP build profile.
- Extended `services.skills_harvest` to persist graph profile metadata, source hashes, graph diffs, stale-source signals, large-drop protection, and generated `skills.tmcp/graph.json`.
- Extended harvest validation so generated graph paths must resolve.
- Added `--graph-profile` to `aios skills harvest`.
- Reworked `services.tmcp_runtime.compile_tmcp_packet()` to prefer graph-backed task, module, and source-skill scoring, with backward-compatible heuristic fallback and packet warnings.
- Added packet fields for `graph_metadata`, `candidate_scores`, and `source_skill_nodes`.
- Materialized promoted shortcuts into `skills.tmcp/shortcuts/` when receipt history proves repeated successful traversal with positive token ROI.
- Preserved `portable_dev_process` as an overlay namespace loaded only when manifest triggers add behavior.

## Verification

- `uv run python -m compileall services/tmcp_runtime.py services/skills_harvest.py services/aios_cli.py tests/test_tmcp_runtime.py tests/test_skills_harvest.py`
- `uv run pytest -q tests/test_tmcp_runtime.py tests/test_skills_harvest.py` passed with 13 tests.
- `pnpm context:validate` passed.
- `python3 -m json.tool config/tmcp/canonical-graph.json` passed.
- `python3 -m json.tool config/tmcp/registry.json` passed.

## Residual Risk

The ignored local `skills-library/` graph is reproducible from the tracked profile, but this change did not regenerate the full local 99-skill library in place. Runtime traversal falls back safely when `skills.tmcp/graph.json` is absent.
