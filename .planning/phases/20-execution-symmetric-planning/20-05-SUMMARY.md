# Plan 20-05 Summary: Skill-As-Planning-Lens

**Status:** Complete  
**Requirement:** ESPL-05  
**Completed:** 2026-06-23

## What Changed

- Added `config/planning/skill-planning-lenses.json` with planning-mode behavior for initial high-value validation, security review, scope, and audit skills.
- Added `services/planning_skill_lenses.py` to resolve named skill planning requests and translate workflow skill metadata into planning constraints, validation gates, reviewable artifacts, and output expectations.
- Added `tests/test_planning_skill_lenses.py` covering testing skill planning, security review planning, direct skill-key requests, unknown requests, and planning-mode disallowed outputs.
- Marked ESPL-05 complete in `.planning/REQUIREMENTS.md`.

## Key Decisions

- Skill planning mode uses existing skill purpose, invariants, and failure conditions as planning constraints.
- Planning mode does not assume completed work and explicitly disallows completed-work review, final findings, pass/fail claims, and implementation output.
- Natural-language requests such as "testing principles" or "security review principles" resolve through a small planning registry rather than broad always-loaded instructions.

## Verification

- `uv run pytest -q tests/test_planning_skill_lenses.py`
- `uv run ruff check services/planning_skill_lenses.py tests/test_planning_skill_lenses.py`
- `python3 -m json.tool config/planning/skill-planning-lenses.json`
- `pnpm context:validate`
- `git diff --check`
