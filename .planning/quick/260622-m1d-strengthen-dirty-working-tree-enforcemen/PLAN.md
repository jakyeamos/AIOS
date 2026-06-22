# Strengthen Dirty Working Tree Enforcement

## Scope

- Add a success criterion that treats an uncommitted git worktree at completion as a blocker.
- Feed stop-hook success criteria evaluation with actual `git status --porcelain` entries.
- Add focused tests for clean and dirty status evaluation.
- Update durable planning/truth surfaces for the enforcement change.

## Verification

- `uv run pytest -q tests/test_success_criteria.py`
- `uv run ruff check services/success_criteria.py bin/hook-stop.py tests/test_success_criteria.py`
- `uv run ruff format --check services/success_criteria.py bin/hook-stop.py tests/test_success_criteria.py`
