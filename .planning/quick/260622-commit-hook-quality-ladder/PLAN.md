# Quick Task 260622: Commit Hook Quality Ladder

## Goal

Add a pre-commit quality ladder that routes commits through AIOS standards, success criteria, and targeted confident-code checks before changes can land.

## Tasks

1. Add a reusable quality-ladder module and hook-facing CLI.
2. Add a versioned pre-commit hook that runs the ladder.
3. Add focused tests for standards inventory, success-criteria registry validation, and handler-before-send confident-code enforcement.

## Verification

- `uv run pytest tests/test_commit_quality_ladder.py -q`
- `python3 bin/aios-quality-ladder.py --no-context-validation`
- `pnpm context:validate`

