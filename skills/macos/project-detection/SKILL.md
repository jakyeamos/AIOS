---
name: macos-project-detection
version: 0.1.0
description: Detect whether a repository contains a native macOS app, Swift Package, Xcode project, Xcode workspace, mixed app, or non-macOS project, then emit facts for downstream macOS build and skill routing.
source:
  donor: fayazara/macos-app-skills
  donor_commit: a60365ae85bfc3d1f2f8b260b080d77bfb2f3ec0
  source_files:
    - build/SKILL.md
    - macos-patterns/SKILL.md
  transformation_type: hardened
always_loaded: false
intent_pointer: macOS/Xcode project detection only
allowed-tools:
  - Read
  - Grep
  - Bash
---

# macOS Project Detection

Use this skill when a task mentions a macOS app, Xcode project, Xcode workspace,
Swift Package, scheme, target, SDK, or `xcodebuild` and the project shape is not
already known.

Do not load this skill for general Apple UI advice, web work, or non-macOS
repositories. This is an intent-specific pointer, not an always-loaded agent
rule.

## Output Contract

Emit a `MacOSProjectDetection` report with:

- `status`: `detected` or `not_applicable`
- `shape`: `native_macos_app`, `swift_package`, `xcode_project`,
  `xcode_workspace`, `mixed_app`, or `non_macos_project`
- `workspaces`: discovered `.xcworkspace` paths
- `projects`: discovered `.xcodeproj` paths
- `packages`: discovered `Package.swift` paths
- `schemes`: discovered schemes, grouped by workspace/project when possible
- `targets`: macOS-looking targets, bundle identifiers, platforms, and product
  types when available
- `xcode`: selected Xcode path, `DEVELOPER_DIR`, `xcodebuild -version`, and
  selected developer directory
- `sdk`: `macosx` SDK availability from `xcodebuild -showsdks`
- `warnings`: missing toolchain, ambiguous project shape, missing schemes, or
  non-macOS platform evidence
- `next_step`: recommended downstream skill or `not applicable`

## Detection Procedure

1. Search the repository root for `.xcworkspace`, `.xcodeproj`, and
   `Package.swift`, excluding generated and dependency directories such as
   `.git`, `DerivedData`, `node_modules`, `.build`, and `Pods`.
2. If none are found, return `status: not_applicable`,
   `shape: non_macos_project`, and stop.
3. Prefer workspace evidence over project-only evidence because workspaces often
   include package dependencies, CocoaPods, or multiple projects.
4. Classify shape:
   - workspace plus project or package: `mixed_app`
   - workspace only: `xcode_workspace`
   - project only: `xcode_project`
   - package only: `swift_package`
   - app target with macOS platform evidence: `native_macos_app`
5. Run read-only Xcode environment checks when `xcodebuild` is available:
   - `xcodebuild -version`
   - `xcode-select -p`
   - `xcodebuild -showsdks`
6. Record `DEVELOPER_DIR` when set. If multiple Xcode apps appear under
   `/Applications`, report them as a warning instead of switching toolchains.
7. Discover schemes:
   - for a workspace: `xcodebuild -list -workspace <workspace>`
   - for a project: `xcodebuild -list -project <project>`
   - for a package: `swift package describe` only when Swift is available
8. Detect macOS/platform signals from scheme output, project files, package
   manifests, app bundles, `platforms: [.macOS(...)]`, `SDKROOT = macosx`, or
   target product types.
9. If discovery is ambiguous, return facts and warnings instead of guessing.

## Applicability Rules

- If a repository only has iOS/watchOS/tvOS evidence, return
  `status: not_applicable` for macOS build verification unless the user
  explicitly asks for cross-platform Apple work.
- If a package has no macOS platform declaration but contains AppKit imports or
  macOS-specific targets, classify it as `swift_package` with a macOS warning.
- If a project cannot list schemes, keep the project detected and mark schemes
  as missing. Downstream build verification must not invent a scheme.

## Safety Rules

- Read project metadata only. Do not modify `.xcodeproj`, `.xcworkspace`,
  signing settings, package manifests, generated files, or Xcode preferences.
- Do not install Xcode, switch `DEVELOPER_DIR`, run package updates, or resolve
  dependencies without explicit user approval.
- Do not claim a repository is a macOS app unless there is macOS platform,
  target, product, or framework evidence.

## Downstream Routing

- If `status: not_applicable`, stop and explain that macOS build verification is
  not applicable.
- If schemes are missing, route to `macos-build-verify` with a missing-scheme
  blocker.
- If a workspace exists, route build verification to workspace-first mode.
- If only a project exists, route build verification to project fallback mode.
- If only a Swift Package exists, route to Swift package build verification
  rather than `xcodebuild` project mode.
