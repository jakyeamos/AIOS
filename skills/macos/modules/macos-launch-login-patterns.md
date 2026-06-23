# macOS Launch At Login Patterns

## When To Use

Use for launch-at-login toggles, background helpers, menu bar app startup, and
login item status.

## When Not To Use

Do not use for scheduled jobs, launch agents outside app scope, or server-side
startup scripts.

## Common Wrong Web Mental Model

"Startup behavior is an app setting stored in local config."

## Correct Native macOS Pattern

Use ServiceManagement login item APIs and expose a user-controlled setting. Do
not silently enable launch at login.

## Minimal Code Pattern

```swift
try SMAppService.mainApp.register()
try SMAppService.mainApp.unregister()
```

## Validation Notes

Verify the setting survives relaunch, can be disabled, respects user consent,
and does not create duplicate login items.

## Related Modules

- `macos-menu-bar-patterns.md`
- `macos-userdefaults-appstorage-patterns.md`

## Donor Provenance Pointer

Split from `macos-patterns/SKILL.md` at donor commit
`a60365ae85bfc3d1f2f8b260b080d77bfb2f3ec0`.
