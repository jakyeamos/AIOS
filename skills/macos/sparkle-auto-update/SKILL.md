---
name: macos-sparkle-auto-update
version: 0.1.0
description: Add or repair Sparkle auto-update integration for non-Mac-App-Store macOS apps with guarded dependency, Info.plist, appcast, and signing-key handling.
source:
  donor: fayazara/macos-app-skills
  donor_commit: a60365ae85bfc3d1f2f8b260b080d77bfb2f3ec0
  source_files:
    - auto-update/SKILL.md
    - auto-update/references/UpdaterManager.swift
  transformation_type: hardened
always_loaded: false
intent_pointer: Sparkle auto-update integration only
depends_on:
  - skills/macos/project-detection/SKILL.md
  - skills/macos/build-verify/SKILL.md
---

# macOS Sparkle Auto-Update

Use this skill when the user asks to add or repair Sparkle updates for a native
macOS app distributed outside the Mac App Store.

Do not use for Mac App Store distribution, generic release automation, or
server update APIs.

## Required Preflight

1. Invoke `macos-project-detection`.
2. Confirm distribution is non-Mac-App-Store. If the app is App Store-only,
   stop as not applicable.
3. Detect existing Sparkle dependency in package manifests, Xcode project
   references, imports, and updater code.
4. Detect existing Info.plist keys:
   - `SUFeedURL`
   - `SUPublicEDKey`
   - Sparkle-related scheduling and behavior keys
5. Search for private key leakage:
   - EdDSA private key literals
   - Sparkle signing private key files
   - generated key output in repo files

## Approval Gates

Require explicit approval before:

- adding Sparkle as a dependency
- editing `.xcodeproj`, package manifests, or Info.plist
- creating or modifying appcast files
- generating, moving, or reading private signing keys
- changing update feed URLs or public EdDSA keys
- enabling automatic update checks by default

## Implementation Guidance

- Reuse existing Sparkle integration when present.
- Create the updater controller early enough in app lifecycle that update checks
  and menu commands work.
- Keep `UpdaterManager` or equivalent ownership explicit and singleton-like.
- Add DEBUG guards so development builds do not accidentally check production
  update feeds.
- Treat `SUPublicEDKey` placeholders as blockers, not success.
- For menu-bar apps, ensure update UI can appear under the activation policy.

## Validation

Run `macos-build-verify` after any code, dependency, or plist change.

Manual validation should check:

- Debug builds do not hit production appcast unintentionally.
- `SUFeedURL` matches the intended update channel.
- `SUPublicEDKey` is present and not a placeholder.
- No private signing key material is committed.
- Sparkle UI can appear in menu-bar apps.

## Repair Recommendations

- Missing dependency: ask before adding Sparkle.
- Missing Info.plist keys: ask before editing plist.
- Placeholder public key: block until the real public key is supplied.
- Private key found in repo: stop, remove from source, rotate if exposed, and
  document the incident before continuing.
- Appcast URL mismatch: stop and request the intended channel before changing.
