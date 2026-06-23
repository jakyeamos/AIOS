---
name: macos-build-verify
version: 0.1.0
description: Verify native macOS app builds with workspace-first xcodebuild logic, scheme discovery, destination/configuration selection, signing fallback, error repair recommendations, and post-fix rebuild requirements.
source:
  donor: fayazara/macos-app-skills
  donor_commit: a60365ae85bfc3d1f2f8b260b080d77bfb2f3ec0
  source_files:
    - build/SKILL.md
  transformation_type: hardened
always_loaded: false
intent_pointer: macOS build, compile, xcodebuild, or build-error verification only
depends_on:
  - skills/macos/project-detection/SKILL.md
allowed-tools:
  - Read
  - Grep
  - Bash
---

# macOS Build Verification

Use this skill when the user asks to build, compile, check build, run
`xcodebuild`, verify a native macOS app, or fix macOS build errors.

Always invoke `macos-project-detection` first unless an equivalent
`MacOSProjectDetection` report is already in context.

This is an intent-specific pointer. Do not add broad macOS build instructions to
always-loaded agent files.

## Preconditions

- Project detection returned `status: detected`.
- At least one workspace, project, or Swift package exists.
- Xcode or Swift tooling availability is known.
- The user asked for build verification or build-error repair.

If detection returned `not_applicable`, stop. Do not run build commands.

## Build Selection

1. Prefer `.xcworkspace` over `.xcodeproj`.
2. Fall back to `.xcodeproj` only when no workspace exists.
3. Use Swift Package build mode only when there is no workspace/project.
4. List schemes before building:
   - `xcodebuild -list -workspace <workspace>`
   - `xcodebuild -list -project <project>`
5. Select a scheme by explicit user request first, then exact app-name match,
   then the single available scheme. If multiple schemes remain, ask instead of
   guessing.
6. Select destination:
   - default: `platform=macOS`
   - only use simulator/device destinations when the user asks for a different
     Apple platform
7. Select configuration:
   - default: `Debug`
   - use `Release` only when the user asks for release validation or archive
     readiness

## Verification Commands

Workspace:

```zsh
xcodebuild -workspace <App.xcworkspace> -scheme <Scheme> -configuration Debug -destination 'platform=macOS' build
```

Project:

```zsh
xcodebuild -project <App.xcodeproj> -scheme <Scheme> -configuration Debug -destination 'platform=macOS' build
```

Swift Package:

```zsh
swift build
```

If package dependencies are unresolved and the user approved dependency
resolution, run the project-appropriate resolve command before rebuilding.

## Output Handling

- Success requires command exit code `0` and explicit `BUILD SUCCEEDED` for
  `xcodebuild`.
- Never claim success from partial logs, no-op output, or absence of errors.
- If filtered output omits the root cause, rerun once with full output captured.
- Preserve the failing command, selected workspace/project/package, scheme,
  destination, configuration, Xcode path, and SDK facts in the report.

## Error Repair Loop

For each failure:

1. Classify the failure:
   - missing scheme
   - missing SDK or Xcode toolchain
   - unresolved Swift package dependency
   - code signing identity or provisioning failure
   - deployment target / availability mismatch
   - compiler error
   - linker error
   - test host or app extension mismatch
2. Recommend the smallest project-specific repair.
3. Apply code repairs only when they are within the user's requested scope.
4. Do not mutate signing settings, team IDs, entitlements, provisioning
   profiles, package manifests, or Xcode project structure without explicit
   approval.
5. After every repair, rerun the same build command or explain why a different
   command is now required.

## Signing Fallback

When a local verification build fails only because of signing identity or
provisioning:

1. Report the signing failure exactly.
2. Offer a signing-disabled local verification command.
3. Run it only when allowed by the user's request and project policy:

```zsh
xcodebuild <workspace-or-project-and-scheme> -configuration Debug -destination 'platform=macOS' CODE_SIGNING_ALLOWED=NO build
```

This fallback verifies compilation only. It does not prove release readiness,
notarization readiness, entitlements correctness, or update-channel safety.

## Completion Criteria

- Report `success` only with `BUILD SUCCEEDED` or successful `swift build`.
- Report `blocked` when no scheme can be selected, Xcode/macOS SDK is missing,
  or permission is required for signing/dependency/project mutations.
- Report `failed` when the build still fails after in-scope repairs.
- Include the final command and whether a post-fix rebuild was run.
