# macOS UserDefaults And AppStorage Patterns

## When To Use

Use for preferences, lightweight persisted settings, settings UI bindings, and
per-user app defaults.

## When Not To Use

Do not use for databases, secrets, large documents, sync-critical state, or
server cache.

## Common Wrong Web Mental Model

"Use `localStorage` for app state."

## Correct Native macOS Pattern

Use `UserDefaults` for simple preferences and `@AppStorage` for SwiftUI
bindings. Use Keychain for secrets and files/databases for structured data.

## Minimal Code Pattern

```swift
@AppStorage("launchAtLogin") private var launchAtLogin = false
UserDefaults.standard.set(true, forKey: "hasCompletedOnboarding")
```

## Validation Notes

Verify defaults, migration from old keys, reset behavior, and that secrets are
not stored in defaults.

## Related Modules

- `macos-navigation-inspector-patterns.md`
- `macos-launch-login-patterns.md`

## Donor Provenance Pointer

Split from `macos-patterns/SKILL.md` at donor commit
`a60365ae85bfc3d1f2f8b260b080d77bfb2f3ec0`.
