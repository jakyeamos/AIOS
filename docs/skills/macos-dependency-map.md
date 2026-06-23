# macOS Skill Pack Dependency Map

The macOS skill pack is an intent-specific overlay. It must not be loaded for
all development work or for every mention of Apple platforms.

## Task Routes

| Intent | Route |
| --- | --- |
| Build, compile, check build, `xcodebuild` | `@task:macos.project.detect` -> `@task:macos.build.verify` |
| Native macOS architecture or pattern question | `@task:macos.patterns.route` -> selected `@module:macos.*` only |
| Settings or preferences window | `@task:macos.project.detect` -> `@task:macos.settings.window` -> `@task:macos.build.verify` |
| Sparkle, appcast, auto-update | `@task:macos.project.detect` -> `@task:macos.sparkle.auto_update` -> `@task:macos.build.verify` |
| Notch or top-display overlay | `@task:macos.project.detect` -> `@task:macos.notch.overlay` -> `@task:macos.build.verify` |
| Release, publish, DMG, notarize, GitHub release | `@task:macos.project.detect` -> `@task:macos.release.pipeline` -> permission gate -> dry-run -> approval -> execution |

## Required Modules

| Module ID | File |
| --- | --- |
| `@module:macos.menu_bar` | `skills/macos/modules/macos-menu-bar-patterns.md` |
| `@module:macos.window_panel` | `skills/macos/modules/macos-window-panel-patterns.md` |
| `@module:macos.screen_geometry` | `skills/macos/modules/macos-screen-geometry-patterns.md` |
| `@module:macos.keyboard_shortcuts` | `skills/macos/modules/macos-keyboard-shortcuts-patterns.md` |
| `@module:macos.file_picker` | `skills/macos/modules/macos-file-picker-patterns.md` |
| `@module:macos.pasteboard` | `skills/macos/modules/macos-pasteboard-patterns.md` |
| `@module:macos.drag_drop` | `skills/macos/modules/macos-drag-drop-patterns.md` |
| `@module:macos.navigation_inspector` | `skills/macos/modules/macos-navigation-inspector-patterns.md` |
| `@module:macos.launch_login` | `skills/macos/modules/macos-launch-login-patterns.md` |
| `@module:macos.quicklook_workspace` | `skills/macos/modules/macos-quicklook-workspace-patterns.md` |
| `@module:macos.screencapturekit` | `skills/macos/modules/macos-screencapturekit-patterns.md` |
| `@module:macos.userdetails_appstorage` | `skills/macos/modules/macos-userdefaults-appstorage-patterns.md` |

## Mutation Gates

- Settings architecture replacement requires explicit approval.
- Sparkle dependency, Info.plist, appcast, and key-material changes require
  explicit approval.
- Notch high window levels, click-through behavior, global event monitors, and
  intrusive overlay behavior require explicit approval.
- Release work requires dry-run output before any git, GitHub, appcast, signing,
  notarization, artifact publishing, or version/build mutation.

## Provenance

Source repository: `fayazara/macos-app-skills`.

Inspected commit: `a60365ae85bfc3d1f2f8b260b080d77bfb2f3ec0`.

Audited on 2026-06-23 in `docs/audits/macos-app-skills-audit.md`.

Transformation types:

- build verification: hardened
- native pattern modules: split
- settings window: adapted
- Sparkle auto-update: hardened
- notch overlay: adapted
- release pipeline: hardened/inferred from donor release CLI behavior

License note: donor source was used as transformation input. Verify the donor
license before copying donor code verbatim.
