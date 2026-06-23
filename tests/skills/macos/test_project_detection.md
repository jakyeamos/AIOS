# macOS Project Detection Behavior Tests

These tests validate `skills/macos/project-detection/SKILL.md` as an
intent-specific skill. They are behavior fixtures for human and future automated
skill validation.

## Case: Workspace Plus Project

Given a repo contains `Bidcamp.xcworkspace`, `Bidcamp.xcodeproj`, and
`Package.swift`.

When `macos-project-detection` runs.

Then it emits `status: detected`, classifies the shape as `mixed_app`, records
both workspace and project paths, prefers the workspace for downstream build
verification, records packages, checks Xcode and macOS SDK availability, and
does not modify any project files.

## Case: Project Only

Given a repo contains `Bidcamp.xcodeproj` and no `.xcworkspace`.

When `macos-project-detection` runs.

Then it emits `status: detected`, classifies the shape as `xcode_project` or
`native_macos_app` when macOS target evidence exists, lists schemes with
`xcodebuild -list -project`, and routes downstream verification to project
fallback mode.

## Case: No Xcode Project

Given a repo contains no `.xcworkspace`, `.xcodeproj`, or `Package.swift`.

When `macos-project-detection` runs.

Then it emits `status: not_applicable`, classifies the shape as
`non_macos_project`, stops before build verification, and does not run
`xcodebuild`.

## Case: Swift Package Only

Given a repo contains `Package.swift` with macOS platform or AppKit evidence and
no Xcode workspace/project.

When `macos-project-detection` runs.

Then it emits `status: detected`, classifies the shape as `swift_package`,
records package facts, checks Swift/Xcode availability, and routes downstream
verification to Swift package build mode.

## Case: Multiple Schemes

Given a workspace or project lists several schemes.

When no scheme was requested by the user.

Then detection records all schemes and marks scheme selection ambiguous for
build verification instead of guessing.

## Case: Missing Scheme

Given a workspace or project exists but `xcodebuild -list` returns no buildable
schemes or fails to list schemes.

When detection completes.

Then it keeps the project detected, records a missing-scheme warning, and routes
build verification to a missing-scheme blocker.

## Case: Missing Xcode Or macOS SDK

Given project files exist but `xcodebuild` or the `macosx` SDK is unavailable.

When detection completes.

Then it reports project facts plus an Xcode/SDK warning and does not claim build
verification can proceed.
