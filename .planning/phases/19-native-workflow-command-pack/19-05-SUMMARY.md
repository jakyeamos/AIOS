# Phase 19 Plan 19-05 Summary: Guarded Cleanup And Prototype Commands

## Completed Scope

- Extended `services/native_commands.py` with `de_slopify` and `prototype`.
- Wired CLI dispatch for:
  - `aios cleanup de-slopify`
  - `aios prototype`
- Implemented de-slopify as plan-by-default cleanup.
- Limited de-slopify apply mode to format-only cleanup: trailing whitespace and excessive blank lines.
- Added risky structural skip reporting for broad error handling, public APIs, TODO/agent markers, and generic naming.
- Implemented prototype sandbox writes under `.planning/prototypes/`, `prototypes/`, or `/private/tmp`.
- Added prototype output sections for question, location, experiment, result, proof boundaries, recommendation, promotion steps, and cleanup instructions.
- Extended `tests/test_native_commands.py` for guarded cleanup behavior, format-only apply, prototype path restrictions, and CLI JSON output.

## TMCP / Agent-Rule Placement Decision

No always-loaded agent files were edited. Cleanup and prototype behavior belongs in the intent-specific native command module and the existing native command registry metadata.

## Requirement Evidence

- `CMDP-07`: Complete. `aios cleanup de-slopify` preserves behavior by default, applies only low-risk formatting when explicitly requested, and lists risky structural changes separately. `aios prototype` writes only to explicit sandbox/prototype locations and emits cleanup/promotion guidance.

## Verification

- `uv run pytest -q tests/test_native_commands.py` -> 12 passed.
- `uv run ruff check services/native_commands.py tests/test_native_commands.py` -> passed.
- `python3 -m compileall -q services/native_commands.py services/aios_cli.py tests/test_native_commands.py` -> passed.

## Next Plan

Proceed to Phase 19 Plan 19-06: metadata logging, docs, and final command-pack verification.
