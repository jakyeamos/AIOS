# Plan 21-08 Summary: Behavioral Tests And Validation Command

**Status:** Complete
**Requirement:** MACS-08
**Completed:** 2026-06-23

## What Changed

- Added executable `scripts/validate-skills.sh`.
- Reused existing behavior fixtures under `tests/skills/macos/` for build detection, native pattern routing, settings UI, Sparkle, notch overlay, and release safety.
- Marked MACS-08 complete in `.planning/REQUIREMENTS.md`.

## Key Decisions

- Integrated validation as a repo-local script because no dedicated skill-pack validator existed.
- Validated unique skill IDs, manifest/router JSON, route pointer resolution, referenced file paths, source provenance, required task fields, behavioral test coverage, release publish gates, private-key patterns, and broad macOS always-load trigger exclusions.
- Kept validation local and deterministic; it does not invoke donor release/build commands.

## Verification

- `scripts/validate-skills.sh`
- `pnpm context:validate`
- `git diff --check -- scripts/validate-skills.sh .planning/REQUIREMENTS.md .planning/STATE.md .planning/phases/21-macos-native-app-skill-pack/21-08-SUMMARY.md`
