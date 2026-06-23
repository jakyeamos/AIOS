# macOS Native Pattern Routing Behavior Tests

These behavior fixtures validate that
`skills/macos/native-patterns-router/SKILL.md` loads only the small semantic
modules needed for a native macOS task.

## Case: Menu Bar App

Given the user asks, "Build a macOS menu bar app with a popover."

Then the router selects `macos-menu-bar-patterns.md`.

And it may select `macos-window-panel-patterns.md` only when the requested
popover needs custom AppKit window or panel behavior.

And it does not load ScreenCaptureKit, file picker, pasteboard, drag/drop, or
release-related modules.

## Case: Floating Overlay

Given the user asks, "Make this macOS overlay float above other windows like a
z-index layer."

Then the router selects `macos-window-panel-patterns.md` and
`macos-screen-geometry-patterns.md`.

And the selected modules correct the web `z-index` mental model to native
`NSPanel`, window level, collection behavior, and display geometry.

## Case: Global Keyboard Shortcut

Given the user asks, "Add a global keyboard shortcut to capture the current
selection."

Then the router selects `macos-keyboard-shortcuts-patterns.md`.

And it does not load menu bar, file picker, pasteboard, or screen geometry
modules unless the task explicitly adds those concerns.

## Case: Clipboard Or Pasteboard

Given the user asks, "Use navigator.clipboard to copy from a native macOS app."

Then the router selects `macos-pasteboard-patterns.md`.

And the selected module corrects `navigator.clipboard` to
`NSPasteboard.general`.

## Case: Web-Only Task

Given the user asks for a browser clipboard feature in a Next.js app.

Then the router returns `not_applicable`.

And no native macOS modules are loaded.

## Case: Required Module Coverage

The router references all required modules:

- `macos-menu-bar-patterns.md`
- `macos-window-panel-patterns.md`
- `macos-screen-geometry-patterns.md`
- `macos-keyboard-shortcuts-patterns.md`
- `macos-file-picker-patterns.md`
- `macos-pasteboard-patterns.md`
- `macos-drag-drop-patterns.md`
- `macos-navigation-inspector-patterns.md`
- `macos-launch-login-patterns.md`
- `macos-quicklook-workspace-patterns.md`
- `macos-screencapturekit-patterns.md`
- `macos-userdefaults-appstorage-patterns.md`
