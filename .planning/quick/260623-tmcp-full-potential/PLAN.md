# TMCP Full-Potential Implementation Plan

Date: 2026-06-23

## Objective

Make TMCP a graph-backed skill-composition layer for non-trivial AIOS-managed work while preserving `skills-library/skills.tmcp` as the canonical local graph and `config/tmcp/portable-dev-process` as an overlay namespace.

## Scope

- Add a tracked canonical graph build profile.
- Make `aios skills harvest` emit reproducible metadata, graph diff evidence, source hashes, and structured `skills.tmcp/graph.json`.
- Make `services.tmcp_runtime.compile_tmcp_packet()` prefer `graph.json` traversal while keeping a heuristic fallback.
- Include source-skill excerpts when graph metadata shows a precise canonical skill match.
- Materialize promoted shortcut artifacts from validated traversal receipts.
- Preserve overlay traversal only when registered namespace triggers add behavior.

## Verification

- `uv run python -m compileall services/tmcp_runtime.py services/skills_harvest.py services/aios_cli.py tests/test_tmcp_runtime.py tests/test_skills_harvest.py`
- `uv run pytest -q tests/test_tmcp_runtime.py tests/test_skills_harvest.py`
- `pnpm context:validate`
- `python3 -m json.tool config/tmcp/canonical-graph.json`
- `python3 -m json.tool config/tmcp/registry.json`
