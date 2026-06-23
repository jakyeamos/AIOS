# macOS Sparkle Auto-Update Behavior Tests

## Case: Missing Dependency

Given project detection reports a non-Mac-App-Store macOS app with no Sparkle
dependency.

When `macos-sparkle-auto-update` runs.

Then it asks before adding Sparkle and does not edit project files without
approval.

## Case: Existing Dependency

Given Sparkle is already present.

When the skill runs.

Then it reuses the existing dependency and checks updater lifecycle ownership
before adding new files.

## Case: Missing Info.plist Keys

Given Sparkle code exists but `SUFeedURL` or `SUPublicEDKey` is missing.

When validation runs.

Then the skill reports a plist blocker and asks before editing Info.plist.

## Case: Missing DEBUG Guard

Given update checks can hit a production feed from Debug builds.

When validation runs.

Then the skill reports a DEBUG guard failure and recommends a guarded update
policy before claiming success.

## Case: Appcast URL Mismatch

Given `SUFeedURL` does not match the intended update channel.

When validation runs.

Then the skill blocks and asks for the correct channel before changing URLs.

## Case: Private Key Leakage

Given Sparkle private signing key material appears in repo files.

When validation runs.

Then the skill stops, reports key leakage, and does not continue until the
secret is removed and rotation is considered.
