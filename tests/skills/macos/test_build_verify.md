# macOS Build Verification Behavior Tests

These tests validate `skills/macos/build-verify/SKILL.md` as an intent-specific
skill that depends on `macos-project-detection`.

## Case: Workspace Plus Project

Given project detection reports both a workspace and project with scheme
`Bidcamp`.

When the user asks to build the macOS app.

Then build verification lists workspace schemes, runs `xcodebuild -workspace`
with `-destination 'platform=macOS'`, does not fall back to `.xcodeproj`, and
claims success only when the command exits `0` and logs `BUILD SUCCEEDED`.

## Case: Project Only

Given project detection reports one `.xcodeproj`, no workspace, and a single
scheme.

When the user asks to verify the build.

Then build verification runs `xcodebuild -project` with Debug configuration and
macOS destination, records the exact command, and reports the final result.

## Case: No Xcode Project

Given project detection reports `status: not_applicable`.

When the user asks to run xcodebuild.

Then build verification stops, reports that macOS build verification is not
applicable, and does not run build commands.

## Case: Multiple Schemes

Given project detection reports multiple schemes and the user did not choose
one.

When build verification starts.

Then it asks for or requires a scheme selection instead of guessing.

## Case: Missing Scheme

Given project detection reports an Xcode project but no schemes.

When build verification starts.

Then it reports a missing-scheme blocker, includes the scheme-listing command,
and does not run a build command with an invented scheme.

## Case: Package Dependencies Unresolved

Given a workspace or package build fails because Swift package dependencies are
unresolved.

When dependency resolution has not been explicitly approved.

Then build verification reports a dependency-resolution blocker and does not run
network or dependency-resolution commands.

When dependency resolution is approved.

Then it runs the appropriate resolve step, reruns the same build verification,
and reports success only after the rebuild succeeds.

## Case: Signing Identity Failure

Given `xcodebuild` fails only because of signing identity or provisioning.

When local compile verification is acceptable.

Then build verification reports the signing failure, offers
`CODE_SIGNING_ALLOWED=NO`, runs it only when allowed, and labels any passing
fallback as compile-only rather than release-ready.

## Case: Filtered Output Is Insufficient

Given filtered build output hides the root cause.

When the build fails.

Then build verification reruns once with full output captured before proposing a
repair.

## Case: Post-Fix Rebuild Requirement

Given an in-scope compiler or linker repair was applied.

When build verification reports completion.

Then it includes evidence that the build was rerun after the fix or reports the
work as unverified.
