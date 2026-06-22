# Quick Task 260622: User-Level Commit Quality Gate

## Goal

Install a portable user-level commit quality gate for repositories that do not run through AIOS yet.

## Tasks

1. Add a portable pre-commit script that does not require AIOS project context.
2. Add focused tests for the portable checks.
3. Configure global Git hooks to use the portable hook path while preserving AIOS repo-local hooks.

## Verification

- `uv run pytest tests/test_user_commit_quality_gate.py -q`
- `uv run ruff check bin/user-commit-quality-gate.py tests/test_user_commit_quality_gate.py`
- `.githooks-user/pre-commit`
- `git config --global --get core.hooksPath`

