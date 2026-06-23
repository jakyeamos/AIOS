# Quick Task 260623-tns: Thermo-Nuclear Simplification Gate

**Date:** 2026-06-23
**Status:** In progress

## Goal

Add the AIOS-native Thermo-Nuclear Simplification quality gate as a first-class quality ratchet, preserving the existing Complexity + Simplification gate while giving Pre-PR, adoption/backfill, and shadow-eval workflows a named structural-review contract.

## Tasks

1. Register the gate in AIOS quality surfaces.
   - Files: `config/quality-gates.json`, `.aios-quality-gate.json`, `config/quality-pipeline.json`, `config/success-criteria/registry.json`, `spec/success-criteria/index.md`
   - Verify: registry checks and focused tests pass.
   - Done: `thermo_nuclear_simplification` is discoverable, configured, and mapped to success criteria.

2. Document the review contract.
   - Files: `docs/quality-gates/thermo-nuclear-simplification.md`, `docs/pre-pr/quality-ladder.md`, `docs/adoption/backfill-quality-ratchet.md`, `docs/quality/complexity-simplification-gate.md`, `spec/success-criteria/thermo-nuclear-simplification.md`
   - Verify: docs include modes, severities, scorecard, blocking rules, backfill posture, and output contract.
   - Done: reviewers and agents have one canonical contract to follow.

3. Add focused contract tests.
   - Files: `tests/test_commit_quality_ladder.py`
   - Verify: tests fail if the Thermo gate is removed from the allowlist, contract, pipeline, or success-criteria registry.
   - Done: `uv run pytest -q tests/test_commit_quality_ladder.py` passes.

## Verification

- Run focused registry tests.
- Run context validation if touched context or standards surfaces require it.
- Run the complexity/simplification review manually over changed files.
