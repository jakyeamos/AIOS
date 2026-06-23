---
name: macos-release-pipeline
version: 0.1.0
description: Plan and verify a dry-run-first macOS release pipeline with hard gates before git, GitHub release, appcast, signing, notarization, publishing, and version/build mutations.
source:
  donor: fayazara/macos-app-skills
  donor_commit: a60365ae85bfc3d1f2f8b260b080d77bfb2f3ec0
  source_files:
    - release/SKILL.md
    - release/cli/main.go
    - release/cli/release.example.json
  transformation_type: hardened
always_loaded: false
intent_pointer: macOS release planning and guarded publishing only
depends_on:
  - skills/macos/project-detection/SKILL.md
  - skills/macos/build-verify/SKILL.md
  - skills/macos/sparkle-auto-update/SKILL.md
---

# macOS Release Pipeline

Use this skill when the user asks to prepare, dry-run, validate, or execute a
macOS app release involving archives, DMGs, Sparkle appcasts, signing,
notarization, GitHub releases, or version/build numbers.

Default to dry-run planning. Do not mutate release state unless the user
explicitly approves the exact action.

## Hard Permission Gates

Never run these without explicit approval immediately before the action:

- `git commit`
- `git push`
- `gh release create`
- appcast XML modification
- signing release artifacts
- notarization submission
- artifact publishing or upload
- version or build number changes
- private key generation, reading, moving, or printing

## Preflight Checklist

1. Invoke `macos-project-detection`.
2. Invoke `macos-build-verify` for the release scheme/configuration.
3. Detect version and build number from project settings or Info.plist.
4. Check for duplicate build number in existing appcast entries.
5. Distinguish build verification from archive/export/notarization readiness.
6. Check required tools without installing them:
   - `xcodebuild`
   - `xcrun notarytool`
   - `create-dmg`
   - `gh`
   - Sparkle `sign_update`
7. Check GitHub CLI auth with a read-only auth status command.
8. Locate appcast path and parse it as XML before proposing changes.
9. Detect Sparkle `SUFeedURL`, `SUPublicEDKey`, and signing configuration.
10. Scan planned output and staged files for secret material.

## Dry-Run Output

Before any mutation, produce a release plan with:

- app name, scheme, bundle identifier, version, build number
- archive command and export/notarization steps
- DMG path and expected artifact names
- Sparkle signing command to be approved later
- appcast entry preview
- GitHub release tag/name/body/assets preview
- exact gated commands requiring approval
- rollback and repair plan

## Validation Requirements

After approved mutation, validate:

- DMG exists at the expected path.
- DMG size and signature/hash length are captured.
- Appcast XML parses successfully.
- Appcast entry points to the intended artifact URL.
- Duplicate build numbers are rejected.
- GitHub release URL is captured after creation.
- No private keys, notarization credentials, appcast signing secrets, or tokens
  are printed or committed.

## Rollback And Repair

- Failed archive: keep build artifacts local, report the failing command, and
  rerun build verification after repair.
- Failed notarization: do not publish artifacts; capture notary log path or ID.
- Failed appcast parse: restore or regenerate appcast before publishing.
- Failed GitHub release creation: do not push appcast changes that reference a
  missing release asset.
- Wrong version/build: stop before publishing and require explicit approval for
  any corrective version/build mutation.

## Completion Criteria

Report `planned` when only dry-run output was produced.

Report `released` only after approved mutations complete and all validation
requirements pass.

Report `blocked` when approval, credentials, tools, signing material,
notarization setup, appcast validity, GitHub auth, or duplicate build checks are
missing.
