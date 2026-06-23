# Plan 21-06 Summary: macOS Release Pipeline Skill

**Status:** Complete
**Requirement:** MACS-06
**Completed:** 2026-06-23

## What Changed

- Added `skills/macos/release-pipeline/SKILL.md`.
- Added `tests/skills/macos/test_release_pipeline.md`.
- Marked MACS-06 complete in `.planning/REQUIREMENTS.md`.

## Key Decisions

- Transformed donor release CLI behavior into dry-run planning and validation guidance only.
- Added hard approval gates before git commit, git push, GitHub release creation, appcast mutation, signing, notarization, artifact publishing, and version/build changes.
- Required preflight checks for version/build, duplicate appcast entries, release tools, GitHub auth, Sparkle signing, appcast XML validity, and secret safety.
- Required post-mutation evidence before claiming a release: DMG existence, size/signature or hash length, appcast parse success, GitHub release URL, and no committed/printed secrets.

## Verification

- `test -f skills/macos/release-pipeline/SKILL.md`
- `test -f tests/skills/macos/test_release_pipeline.md`
- `rg -n "dry-run|git commit|git push|gh release create|appcast|signing|notarization|artifact publishing|version|build number|create-dmg|gh auth|sign_update|XML|GitHub release URL|secret" skills/macos/release-pipeline/SKILL.md tests/skills/macos/test_release_pipeline.md`
- `pnpm context:validate`
- `git diff --check -- skills/macos/release-pipeline/SKILL.md tests/skills/macos/test_release_pipeline.md .planning/REQUIREMENTS.md .planning/STATE.md .planning/phases/21-macos-native-app-skill-pack/21-06-SUMMARY.md`
