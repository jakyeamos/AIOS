# macOS Release Pipeline Behavior Tests

## Case: Dry-Run Release

Given the user asks to prepare a macOS release.

When `macos-release-pipeline` runs without explicit mutation approval.

Then it produces a dry-run release plan, lists gated commands, and does not run
`git commit`, `git push`, `gh release create`, signing, notarization, appcast
mutation, artifact publishing, or version/build changes.

## Case: Duplicate Build Number

Given the appcast already contains the proposed build number.

When preflight runs.

Then the skill blocks release and requires a corrected version/build plan before
any artifact publishing.

## Case: Missing create-dmg

Given `create-dmg` is unavailable.

When preflight runs.

Then the skill reports a missing-tool blocker and does not install tools or
continue to artifact publishing without approval.

## Case: Missing GitHub Auth

Given `gh auth status` fails.

When release preflight runs.

Then the skill blocks GitHub release creation and does not run
`gh release create`.

## Case: Missing Sparkle sign_update

Given Sparkle appcast signing is required but `sign_update` is unavailable.

When preflight runs.

Then the skill blocks appcast signing and artifact publishing.

## Case: Invalid Appcast XML

Given the appcast file is not valid XML.

When validation runs.

Then the skill blocks appcast mutation and publishing until the XML parses.

## Case: Git Push Without Permission

Given the dry-run plan includes `git push`.

When the user has not explicitly approved that exact action.

Then the skill does not run `git push`.

## Case: GitHub Release Without Permission

Given the dry-run plan includes `gh release create`.

When the user has not explicitly approved that exact action.

Then the skill does not create the GitHub release.

## Case: Validation After Approved Publish

Given the user approved release mutations and the commands completed.

When reporting completion.

Then the skill records DMG existence, DMG size, signature or hash length,
appcast XML parse success, GitHub release URL, and secret-scan result before
claiming `released`.
