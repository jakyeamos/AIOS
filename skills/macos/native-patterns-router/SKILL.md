---
name: macos-native-patterns-router
version: 0.1.0
description: Route native macOS app questions to small semantic pattern modules without loading broad macOS knowledge by default.
source:
  donor: fayazara/macos-app-skills
  donor_commit: a60365ae85bfc3d1f2f8b260b080d77bfb2f3ec0
  source_files:
    - macos-patterns/SKILL.md
  transformation_type: split
always_loaded: false
intent_pointer: native macOS app pattern routing only
modules_dir: ../modules
allowed-tools:
  - Read
  - Grep
---

# macOS Native Patterns Router

Use this skill when the task asks for native macOS app behavior, not generic web
UI or cross-platform Apple advice. This router selects the smallest relevant
module set and stops. Do not load every module by default.

## Routing Rules

- Menu bar app, status item, `MenuBarExtra`, `NSStatusItem`, popover:
  `macos-menu-bar-patterns.md`
- Floating window, overlay, panel, window level, "z-index" for desktop UI:
  `macos-window-panel-patterns.md` and usually
  `macos-screen-geometry-patterns.md`
- Display bounds, notch, safe area, multi-monitor, coordinate conversion:
  `macos-screen-geometry-patterns.md`
- Keyboard shortcut, global hotkey, command key, event monitor:
  `macos-keyboard-shortcuts-patterns.md`
- Open file, save file, directory picker, import/export:
  `macos-file-picker-patterns.md`
- Clipboard, paste, copy, `navigator.clipboard`:
  `macos-pasteboard-patterns.md`
- Drag files, drop targets, promised files, drag session:
  `macos-drag-drop-patterns.md`
- Sidebar, inspector, split settings/details, master-detail:
  `macos-navigation-inspector-patterns.md`
- Launch at login, login item, background helper:
  `macos-launch-login-patterns.md`
- Preview file, reveal in Finder, open with default app:
  `macos-quicklook-workspace-patterns.md`
- Screen recording, window capture, display capture:
  `macos-screencapturekit-patterns.md`
- Preferences, persisted settings, `localStorage` mental model:
  `macos-userdefaults-appstorage-patterns.md`

## Selection Contract

1. Match task intent to one or more modules.
2. Load only the selected module files.
3. If the request is web-only, return `not_applicable`.
4. If the request is broad, ask for the concrete native surface before loading
   modules.
5. Prefer AppKit-native primitives when the behavior depends on system windows,
   panels, menus, pasteboard, drag/drop, screen capture, or workspace services.

## Always-Loaded Decision

This router and its modules are not always-loaded agent rules. They are
intent-specific pointers for native macOS app work. When changing agent files,
keep this behavior behind the router unless the rule applies to all development
work.
