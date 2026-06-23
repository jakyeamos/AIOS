# Plan 21-05 Summary: Settings, Sparkle, And Notch Skills

**Status:** Complete
**Requirement:** MACS-05
**Completed:** 2026-06-23

## What Changed

- Added `skills/macos/settings-window/SKILL.md`.
- Added `skills/macos/sparkle-auto-update/SKILL.md`.
- Added `skills/macos/notch-overlay/SKILL.md`.
- Added behavior fixtures for settings, Sparkle, and notch overlay scenarios under `tests/skills/macos/`.
- Marked MACS-05 complete in `.planning/REQUIREMENTS.md`.

## Key Decisions

- Kept all three skills task-shaped and intent-specific rather than broad macOS reference context.
- Required macOS project detection and build verification where implementation changes are relevant.
- Gated settings architecture replacement, Sparkle dependency/plist/appcast/key changes, and intrusive notch overlay behavior behind explicit approval.
- Added fallback guidance for older macOS settings APIs, non-notch/external displays, and menu-bar activation policies.

## Verification

- `test -f skills/macos/settings-window/SKILL.md`
- `test -f skills/macos/sparkle-auto-update/SKILL.md`
- `test -f skills/macos/notch-overlay/SKILL.md`
- `rg -n "macos-project-detection|macos-build-verify|NSWindowController|activation policy|macOS 26|duplicate|approval" skills/macos/settings-window/SKILL.md tests/skills/macos/test_settings_window.md`
- `rg -n "non-Mac-App-Store|Sparkle|Info.plist|SUFeedURL|SUPublicEDKey|private key|DEBUG|appcast|approval|macos-build-verify" skills/macos/sparkle-auto-update/SKILL.md tests/skills/macos/test_sparkle_auto_update.md`
- `rg -n "notch|NSPanel|NSWindow|window levels|click-through|external|screen.frame|visibleFrame|reduced motion|manual validation|macos-build-verify" skills/macos/notch-overlay/SKILL.md tests/skills/macos/test_notch_overlay.md`
- `pnpm context:validate`
- `git diff --check -- skills/macos/settings-window/SKILL.md skills/macos/sparkle-auto-update/SKILL.md skills/macos/notch-overlay/SKILL.md tests/skills/macos/test_settings_window.md tests/skills/macos/test_sparkle_auto_update.md tests/skills/macos/test_notch_overlay.md .planning/REQUIREMENTS.md .planning/STATE.md .planning/phases/21-macos-native-app-skill-pack/21-05-SUMMARY.md`
