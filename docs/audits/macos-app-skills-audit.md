# macOS App Skills Donor Audit

**Phase:** 21, macOS Native App Skill Pack
**Requirement:** MACS-02
**Date:** 2026-06-23
**Donor:** `fayazara/macos-app-skills`
**Inspected commit:** `a60365ae85bfc3d1f2f8b260b080d77bfb2f3ec0`
**Commit date:** 2026-05-28T00:40:54+05:30

## Scope

This audit inspects the donor repository and maps useful native macOS app development knowledge into AIOS-native skill, TMCP, provenance, validation, and safety conventions from `docs/audits/aios-skill-system-macos-pack-audit.md`.

No donor build, release, notarization, signing, appcast, `gh`, `create-dmg`, or Sparkle commands were run.

## Donor Inventory

| Donor Area | Files Inspected | Summary | Decision |
| --- | --- | --- | --- |
| Top-level overview | `README.md`, `skills.sh.json` | Six skills grouped as fundamentals, UI components, and distribution. Targets general agent skill systems. | Adapt grouping into AIOS task families. |
| Build | `build/SKILL.md` | Finds Xcode projects/workspaces, lists schemes, runs `xcodebuild`, handles beta Xcode and common failures. | Adapt and harden. |
| Native patterns | `macos-patterns/SKILL.md` | Broad reference for menu bar apps, activation policy, panels/windows, window levels, screen geometry, hotkeys, file pickers, pasteboard, drag/drop, inspectors, launch at login, Quick Look, NSWorkspace, ScreenCaptureKit, and UserDefaults/AppStorage. | Split into small TMCP modules. |
| Settings UI | `settings-ui/SKILL.md`, `settings-ui/references/*.swift` | NSWindowController-backed settings window, NavigationSplitView, grouped forms, macOS 26 availability checks, sample panes. | Adapt with version guards and UIKit/AppKit preference. |
| Sparkle auto-update | `auto-update/SKILL.md`, `auto-update/references/UpdaterManager.swift` | Sparkle SPM setup, `SPUStandardUpdaterController`, Info.plist keys, EdDSA key generation, appcast, DEBUG guards. | Harden with secret and release gates. |
| Notch UI | `notch-ui/SKILL.md`, `notch-ui/references/*.swift` | NSPanel overlay at high window level, notch shape, screen geometry, animations, non-notch fallback. | Adapt behind explicit UI intent and safety checks. |
| Release | `release/SKILL.md`, `release/cli/main.go`, `release/cli/main_test.go`, `release/cli/release.example.json` | Full GitHub/Sparkle release pipeline and Go CLI that creates DMG, signs, writes appcast, commits, pushes, and creates GitHub release. | Do not copy directly; transform into dry-run-first guarded release skill. |

## What Is Worth Adopting

- Build/project discovery flow: locate `.xcodeproj` / `.xcworkspace`, list schemes, choose Debug macOS destination, interpret build failures, and retry after fixes.
- Signing-disabled command-line build fallback for local verification.
- Xcode beta toolchain detection through `DEVELOPER_DIR` and `/Applications` inspection.
- Native macOS pattern vocabulary: `MenuBarExtra`, `NSStatusItem`, `NSPopover`, activation policy, `NSPanel`, window levels, collection behaviors, AppKit/Quartz coordinate conversion, hotkey tiers, open/save panels, pasteboard, drag/drop, inspectors, launch at login, Quick Look, NSWorkspace, ScreenCaptureKit, UserDefaults/AppStorage.
- Settings-window architecture: programmatic `NSWindowController`, `.fullSizeContentView`, `NavigationSplitView`, grouped `Form`, transparent scroll background, and availability wrapper for macOS 26-only APIs.
- Sparkle lifecycle constraints: create updater controller early, DEBUG guards, Info.plist keys, public/private EdDSA separation, menu-bar activation handling.
- Notch overlay geometry and fallback concept: use full `screen.frame` for notch positioning, detect `safeAreaInsets.top`, fall back on non-notch displays.
- Release pipeline checklist and config model: app name, repo, appcast path, minimum system version, derived data prefixes, duplicate build detection, and appcast entry generation.

## What Should Not Be Adopted Directly

- Do not copy large all-in-one `macos-patterns/SKILL.md` into an always-loaded or single broad skill. Split it into task-routed modules.
- Do not directly copy release CLI behavior into AIOS. It performs high-risk side effects: DMG creation, Sparkle signing, appcast write, git commit, git push, and GitHub release creation.
- Do not make SwiftUI the default UI recommendation for all Apple UI work. AIOS user defaults prefer UIKit/AppKit unless SwiftUI already exists or is explicitly requested. For macOS skills, AppKit bridges are acceptable where they are required by platform APIs.
- Do not assume macOS 26 APIs are available. Liquid glass and scroll-edge APIs need availability gates and fallbacks.
- Do not blindly copy reference Swift files into user projects. Use them as patterns, then adapt names, app lifecycle, activation policy, deployment target, and existing architecture.
- Do not run donor commands during implementation. Build/release commands are validation guidance, not audit-time actions.

## AIOS Compatibility Gaps

- Donor skills are broad `SKILL.md` folders, not AIOS TMCP task/module/branch graphs.
- Donor front matter lacks AIOS registry fields such as lifecycle state, allowed stages, invariants, failure conditions, side effects, provenance, transformation type, and validation expectation.
- Donor release guidance assumes interactive terminal control and direct publishing privileges.
- Donor reference code is SwiftUI/AppKit-heavy and must be reconciled with project-specific architecture and AIOS Apple UI defaults.
- Donor release CLI tests cover pure helpers, but not a dry-run execution mode, permission prompts, secret scanning, or publish-gate enforcement.
- Donor does not provide a manifest dependency map for individual pattern modules.

## Safety Risks

- Release CLI executes `git add`, `git commit`, `git push`, and `gh release create`.
- Release CLI writes `appcast.xml` and creates/overwrites a DMG in `~/Downloads`.
- Sparkle setup involves EdDSA private key material in Keychain and public key values in Info.plist.
- Auto-update and release work can publish broken updates if build numbers, appcast URL, signing output, or release asset URL are wrong.
- Notch UI uses high window levels and click-through panels; wrong defaults can create intrusive overlays.
- Global hotkey guidance uses Carbon hotkeys and event monitors that require careful lifecycle cleanup.
- ScreenCaptureKit and accessibility-like behaviors may involve privacy prompts or sensitive screen content.

## Freshness And Version Risks

- Donor commit inspected is from 2026-05-28.
- Donor mentions macOS 26 Tahoe and Xcode 26 beta behavior. These APIs may change before final SDK release.
- Sparkle 2.x guidance should be checked against current Sparkle docs when implementation starts.
- GitHub CLI, `create-dmg`, notarization, Xcode archive/export, and appcast conventions may vary by project and installed toolchain.
- Reference code includes placeholders such as `{{AppName}}` and must not be treated as ready-to-commit code.

## Provenance And Transformation Map

| Source Area | Provenance | Transformation Type | AIOS Target |
| --- | --- | --- | --- |
| Build | `build/SKILL.md` | Hardened | `@task:macos_project_detect`, `@task:xcodebuild_verify`, `@module:xcode_environment`, `@module:scheme_discovery`, `@module:signing_fallback`, `@module:error_repair` |
| Native patterns | `macos-patterns/SKILL.md` | Split | `@task:macos_native_pattern` plus small modules for menu bar, panels, geometry, hotkeys, file picker, pasteboard, drag/drop, inspectors, launch/login, Quick Look, NSWorkspace, ScreenCaptureKit, and preferences storage |
| Settings UI | `settings-ui/SKILL.md`, `settings-ui/references/*.swift` | Adapted | `@task:macos_settings_window`, `@module:settings_window_controller`, `@module:navigation_split_settings`, `@module:availability_guards` |
| Sparkle | `auto-update/SKILL.md`, `auto-update/references/UpdaterManager.swift` | Hardened | `@task:sparkle_update`, `@module:sparkle_lifecycle`, `@module:sparkle_appcast_safety`, `@branch:secret_material_gate` |
| Notch UI | `notch-ui/SKILL.md`, `notch-ui/references/*.swift` | Adapted | `@task:notch_overlay`, `@module:notch_panel_geometry`, `@module:notch_shape`, `@branch:overlay_intrusion_gate` |
| Release guide | `release/SKILL.md` | Hardened | `@task:macos_release_pipeline`, `@module:notarization_safety`, `@module:sparkle_appcast_safety`, `@branch:release_publish_gate` |
| Release CLI | `release/cli/*` | Inferred | Dry-run checklist and validation model only; do not port as an executable default |
| Group metadata | `skills.sh.json` | Adapted | AIOS grouping: fundamentals, native patterns, UI components, distribution |

## Transformed Skill And Module List

Recommended AIOS skill folders:

- `skills/macos-project-detection/`
- `skills/macos-xcodebuild-verification/`
- `skills/macos-release-pipeline/`

Recommended TMCP namespace:

- `config/tmcp/macos-native-app/manifest.json`
- `config/tmcp/macos-native-app/router.md`
- `config/tmcp/macos-native-app/tasks/*.md`
- `config/tmcp/macos-native-app/modules/*.md`
- `config/tmcp/macos-native-app/branches/*.branch.md`
- `config/tmcp/macos-native-app/tests/routing-cases.json`

Recommended tasks:

- `macos_project_detect`
- `xcodebuild_verify`
- `macos_native_pattern`
- `macos_settings_window`
- `sparkle_update`
- `notch_overlay`
- `macos_release_pipeline`

Recommended modules:

- `xcode_environment`
- `project_workspace_detection`
- `scheme_discovery`
- `signing_fallback`
- `xcode_error_repair`
- `menu_bar`
- `activation_policy`
- `window_panel`
- `screen_geometry`
- `keyboard_shortcuts`
- `file_picker`
- `pasteboard`
- `drag_drop`
- `navigation_inspector`
- `launch_login`
- `quicklook_workspace`
- `screencapturekit`
- `userdefaults_appstorage`
- `settings_window_controller`
- `navigation_split_settings`
- `availability_guards`
- `sparkle_lifecycle`
- `sparkle_appcast_safety`
- `notch_panel_geometry`
- `notch_shape`
- `notarization_safety`

Recommended branches:

- `read_only_detect`
- `build_verification`
- `signing_required`
- `network_required`
- `secret_material_gate`
- `overlay_intrusion_gate`
- `release_publish_gate`
- `destructive_project_change`

## Proposed TMCP Routing Changes

Add a `macos_native_app` namespace to `config/tmcp/registry.json` only after the namespace files exist.

Routing triggers:

- `xcodebuild`, `.xcodeproj`, `.xcworkspace`, "scheme", "build macOS app" -> `@task:xcodebuild_verify`
- "menu bar app", "NSPanel", "window level", "hotkey", "pasteboard", "screen capture", "Quick Look" -> `@task:macos_native_pattern`
- "settings", "preferences", "liquid glass settings" -> `@task:macos_settings_window`
- "Sparkle", "auto update", "appcast", "SUFeedURL", "EdDSA" -> `@task:sparkle_update`
- "notch", "Dynamic Island", "notch overlay" -> `@task:notch_overlay`
- "release", "DMG", "notarize", "sign_update", "GitHub release" -> `@task:macos_release_pipeline`

Default branch behavior:

- Start read-only.
- Build verification may run `xcodebuild` only when the user asks to build/verify.
- Network, dependency install, signing, notarization, git push, release creation, appcast mutation, and key material require explicit permission and a dry-run summary first.

## Implementation Checklist

- Create pack-local manifest with provenance fields: `source_area`, `source_files`, `donor_commit`, `transformation_type`, `freshness_note`, `license_note`, `validation_expectation`.
- Add task and module markdown files using small IF/THEN routing language.
- Add hard release branches before adding release task content.
- Add private-key pattern checks for Sparkle material.
- Add broad-trigger checks to keep macOS modules task-routed.
- Add routing cases for build, settings, Sparkle, notch, native pattern, and release requests.
- Add tests that all manifest references resolve.
- Add tests that release-publish gates are required for appcast, git push, notarization, signing, and GitHub release actions.
- Add docs that donor reference code is source material, not drop-in AIOS output.

## Audit Verdict

The donor repo is valuable source material, especially for native macOS patterns, xcodebuild verification, AppKit/SwiftUI bridge patterns, Sparkle lifecycle, notch overlay geometry, and release pipeline sequencing.

AIOS should transform it into a task-routed macOS TMCP namespace with strict permission branches, provenance metadata, and behavioral tests. The release CLI should influence dry-run validation and safety gates, not become an automatically runnable default.
