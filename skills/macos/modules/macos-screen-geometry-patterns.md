# macOS Screen Geometry Patterns

## When To Use

Use for display bounds, visible frames, safe areas, notch-aware layout,
multi-monitor placement, backing scale, and AppKit/CoreGraphics coordinate
conversion.

## When Not To Use

Do not use for CSS layout, responsive web breakpoints, or ordinary SwiftUI
stack alignment.

## Common Wrong Web Mental Model

"The viewport origin and coordinate system are the same everywhere."

## Correct Native macOS Pattern

Use `NSScreen` and convert between AppKit and CoreGraphics coordinates
deliberately. Use `screen.frame` for full display geometry and
`screen.visibleFrame` when menu bar/dock exclusion is desired.

## Minimal Code Pattern

```swift
guard let screen = NSScreen.main else { return }
let fullFrame = screen.frame
let visibleFrame = screen.visibleFrame
let scale = screen.backingScaleFactor
```

## Validation Notes

Verify placement on multiple displays, scaled displays, full-screen spaces, and
notched displays when relevant.

## Related Modules

- `macos-window-panel-patterns.md`
- `macos-screencapturekit-patterns.md`

## Donor Provenance Pointer

Split from `macos-patterns/SKILL.md` at donor commit
`a60365ae85bfc3d1f2f8b260b080d77bfb2f3ec0`.
