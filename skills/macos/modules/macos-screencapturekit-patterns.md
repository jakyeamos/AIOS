# macOS ScreenCaptureKit Patterns

## When To Use

Use for display capture, window capture, screen recording, picker-based capture,
and capture permission flows.

## When Not To Use

Do not use for screenshots from tests, static image rendering, or simple window
geometry.

## Common Wrong Web Mental Model

"Screen capture is equivalent to `getDisplayMedia`."

## Correct Native macOS Pattern

Use ScreenCaptureKit APIs, request user permission through the system flow, and
model selected displays/windows explicitly.

## Minimal Code Pattern

```swift
let content = try await SCShareableContent.excludingDesktopWindows(
    false,
    onScreenWindowsOnly: true
)
```

## Validation Notes

Verify screen recording permission, picker behavior, multiple displays, capture
stop cleanup, and sensitive-content handling.

## Related Modules

- `macos-screen-geometry-patterns.md`
- `macos-window-panel-patterns.md`

## Donor Provenance Pointer

Split from `macos-patterns/SKILL.md` at donor commit
`a60365ae85bfc3d1f2f8b260b080d77bfb2f3ec0`.
