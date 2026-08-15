# AIOS Python control plane

Last reviewed: 2026-08-15

- Reusable logic belongs in `services/`; CLI orchestration belongs in `bin/`. `services/` must not import from `bin/`.
- Public helpers use explicit return types and stable JSON-compatible shapes.
- Database and workflow mutations remain approval-aware, provenance-bearing, and covered by deterministic tests.
- Run focused pytest files while repairing a surface, then `PYTHONPATH=.:bin uv run pytest -q`, `uv run ruff check .`, and `uv run basedpyright`.
- Exercise changed CLI behavior through `uv run python bin/aios.py --json ...`; source-level tests alone do not prove the command surface.
