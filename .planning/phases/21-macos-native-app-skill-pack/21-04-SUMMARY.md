# Plan 21-04 Summary: Native macOS Pattern Router And Semantic Modules

**Status:** Complete
**Requirement:** MACS-04
**Completed:** 2026-06-23

## What Changed

- Added `skills/macos/native-patterns-router/SKILL.md`.
- Added twelve semantic modules under `skills/macos/modules/`.
- Added `tests/skills/macos/test_native_pattern_routing.md`.
- Marked MACS-04 complete in `.planning/REQUIREMENTS.md`.

## Key Decisions

- Kept native macOS pattern knowledge behind an intent-specific router instead of always-loaded agent instructions.
- Split broad donor material into focused modules for menu bar, window/panel, screen geometry, keyboard shortcuts, file picker, pasteboard, drag/drop, navigation/inspector, launch/login, Quick Look/workspace, ScreenCaptureKit, and UserDefaults/AppStorage.
- Required each module to include use/non-use boundaries, a wrong web mental model, the native macOS pattern, a minimal code pattern, validation notes, related modules, and donor provenance.
- Added routing fixtures that prove targeted module selection and non-loading for unrelated modules.

## Verification

- `find skills/macos/modules -maxdepth 1 -type f | wc -l`
- `rg -n "When To Use|When Not To Use|Common Wrong Web Mental Model|Correct Native macOS Pattern|Minimal Code Pattern|Validation Notes|Related Modules|Donor Provenance Pointer" skills/macos/modules`
- `rg -n "macos-menu-bar-patterns|macos-window-panel-patterns|macos-screen-geometry-patterns|macos-keyboard-shortcuts-patterns|macos-file-picker-patterns|macos-pasteboard-patterns|macos-drag-drop-patterns|macos-navigation-inspector-patterns|macos-launch-login-patterns|macos-quicklook-workspace-patterns|macos-screencapturekit-patterns|macos-userdefaults-appstorage-patterns|not_applicable|z-index|navigator.clipboard" skills/macos/native-patterns-router/SKILL.md tests/skills/macos/test_native_pattern_routing.md`
- `pnpm context:validate`
- `git diff --check -- skills/macos/native-patterns-router/SKILL.md skills/macos/modules tests/skills/macos/test_native_pattern_routing.md .planning/REQUIREMENTS.md .planning/STATE.md .planning/phases/21-macos-native-app-skill-pack/21-04-SUMMARY.md`
