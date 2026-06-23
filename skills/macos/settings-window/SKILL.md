---
name: macos-settings-window
version: 0.1.0
description: Add or repair a guarded native macOS settings/preferences window while preserving existing app lifecycle and settings architecture.
source:
  donor: fayazara/macos-app-skills
  donor_commit: a60365ae85bfc3d1f2f8b260b080d77bfb2f3ec0
  source_files:
    - settings-ui/SKILL.md
    - settings-ui/references/SettingsWindowController.swift
    - settings-ui/references/SettingsView.swift
  transformation_type: adapted
always_loaded: false
intent_pointer: macOS settings or preferences window implementation only
depends_on:
  - skills/macos/project-detection/SKILL.md
  - skills/macos/build-verify/SKILL.md
---

# macOS Settings Window

Use this skill when the user asks to add, repair, or modernize a native macOS
settings/preferences window.

Do not use for web settings pages, iOS settings screens, or broad Apple UI
advice. This is an intent-specific pointer, not an always-loaded rule.

## Required Preflight

1. Invoke `macos-project-detection`.
2. Detect lifecycle style:
   - SwiftUI `App` with `Settings` or `Window` scenes
   - AppKit `NSApplicationDelegate`
   - menu bar utility with hidden dock activation policy
   - mixed SwiftUI/AppKit bridge
3. Search for existing settings/preferences files, menu commands,
   `NSWindowController`, `Settings` scenes, and `UserDefaults` / `@AppStorage`
   keys.
4. If an existing settings architecture exists, repair or extend it. Do not
   replace it without explicit approval.

## Implementation Guidance

- Prefer the existing project architecture.
- Use `NSWindowController` when the app needs singleton settings windows,
  menu-bar activation control, AppKit lifecycle compatibility, or duplicate
  window prevention.
- Use SwiftUI `Settings` / `Window` scenes only when the app already uses
  SwiftUI app lifecycle and no AppKit singleton controller is needed.
- Keep file additions minimal: one controller and one settings view unless the
  existing project already separates panes.
- For menu-bar apps, ensure opening settings temporarily activates the app when
  needed and restores the intended activation policy after close.
- Prevent duplicate settings windows by reusing the existing controller/window.

## macOS 26 Fallbacks

- Gate macOS 26-only visual APIs with availability checks.
- Provide a non-liquid-glass fallback for older deployment targets.
- Do not raise the deployment target just to use a new settings effect.

## Validation

Run `macos-build-verify` after implementation. Manual validation should check:

- Settings opens from the app menu or status item.
- Reopening settings focuses the existing window instead of creating duplicates.
- Menu-bar apps handle activation policy correctly.
- macOS 26-only styles degrade on older deployment targets.

## Repair Recommendations

- Duplicate windows: centralize ownership in one `NSWindowController` or scene
  command path.
- Settings does not appear in menu-bar app: inspect activation policy and
  status item action routing.
- Build fails on availability: add `#available` guards or remove the new API.
- Existing settings architecture conflict: stop and ask before replacing it.
