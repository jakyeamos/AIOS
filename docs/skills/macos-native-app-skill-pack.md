# macOS Native App Skill Pack

This pack adds intent-specific skills for native macOS app work. It is not an
always-loaded agent rule set. Use the TMCP router and manifest to load the
smallest behavior-changing packet for the current task.

## Added Skills And Modules

Skills:

- `skills/macos/project-detection/SKILL.md`
- `skills/macos/build-verify/SKILL.md`
- `skills/macos/native-patterns-router/SKILL.md`
- `skills/macos/settings-window/SKILL.md`
- `skills/macos/sparkle-auto-update/SKILL.md`
- `skills/macos/notch-overlay/SKILL.md`
- `skills/macos/release-pipeline/SKILL.md`

Semantic modules live under `skills/macos/modules/` for menu bar, window/panel,
screen geometry, keyboard shortcuts, file picker, pasteboard, drag/drop,
navigation/inspector, launch/login, Quick Look/workspace, ScreenCaptureKit, and
UserDefaults/AppStorage patterns.

## Routing Behavior

The router is `config/tmcp/macos-skills-router.json`.

- Build, compile, check build, or `xcodebuild`: project detection -> build
  verification.
- Native macOS architecture/pattern questions: native pattern router -> selected
  semantic modules only.
- Settings/preferences: project detection -> settings-window -> build
  verification.
- Sparkle/appcast/auto-update: project detection -> Sparkle auto-update -> build
  verification.
- Notch overlay: project detection -> notch overlay -> build verification.
- Release/publish: project detection -> release pipeline -> permission gate ->
  dry-run -> explicit approval -> execution.

Anti-triggers include web-only UI, generic Apple advice, iOS-only work, Mac App
Store update flows, ordinary popovers, and broad requests to load all macOS
knowledge.

## Safety Gates

- Project detection is read-only.
- Build verification cannot claim success without `BUILD SUCCEEDED` for
  `xcodebuild`.
- Settings architecture replacement requires explicit approval.
- Sparkle dependency, Info.plist, appcast, and private-key work require explicit
  approval.
- Notch high window levels, click-through behavior, global event monitors, and
  intrusive overlays require explicit approval.
- Release work defaults to dry-run and gates git commit, git push, GitHub
  release creation, appcast mutation, signing, notarization, artifact
  publishing, and version/build changes.

## Validation

Run:

```zsh
scripts/validate-skills.sh
pnpm context:validate
```

The validation script checks unique IDs, route pointers, referenced files,
source provenance, task fields, behavioral scenarios, release gates, private-key
patterns, and broad-trigger exclusions.

## Donor Pattern

Source audit: `docs/audits/macos-app-skills-audit.md`.

Donor repository: `fayazara/macos-app-skills`.

Inspected commit: `a60365ae85bfc3d1f2f8b260b080d77bfb2f3ec0`.

The donor repo was used as source material, not copied as executable release or
build automation.

## What Was Adopted From The Donor Repo

- Xcode project/workspace discovery and scheme-first build flow.
- Native macOS pattern vocabulary for menu bar apps, windows/panels, geometry,
  pasteboard, drag/drop, inspectors, launch/login, Quick Look, ScreenCaptureKit,
  and preferences storage.
- Settings-window AppKit/SwiftUI bridge concepts.
- Sparkle lifecycle, Info.plist, appcast, and signing concepts.
- Notch overlay geometry and non-notch fallback concepts.
- Release pipeline sequencing and validation checklist.

## What Was Intentionally Changed

- Broad donor guidance was split into task-routed skills and small modules.
- Release CLI behavior became dry-run-first validation and permission gates.
- SwiftUI guidance was constrained by existing architecture and AppKit/UIKit
  preference defaults.
- macOS 26 APIs require availability guards and fallback behavior.
- All risky dependency, signing, appcast, publishing, and project mutations are
  explicit-approval actions.

## What Was Intentionally Rejected

- No broad always-loaded macOS instruction block.
- No direct copy of donor release CLI behavior.
- No automatic git, GitHub release, notarization, appcast, signing, or version
  mutation.
- No private Sparkle key material in repo files.
- No claim that local signing-disabled builds prove release readiness.

## Remaining Risks

- Sparkle, notarization, GitHub CLI, and `create-dmg` behavior can drift with
  tool versions.
- macOS 26 API behavior should be rechecked against the installed SDK.
- Hardware-specific notch behavior requires manual verification on target
  displays.
- Donor license should be reviewed before copying donor code verbatim.

## Final Report Workflow

When reporting macOS skill-pack work, include:

- files added or modified
- skills and modules added
- TMCP routes and manifest entries changed
- tests and validation commands run
- validation results and failures
- assumptions and freshness notes
- accepted safety tradeoffs
- follow-up repair recommendations

Do not report release or build success from static documentation alone. Report
only the validation actually run.
