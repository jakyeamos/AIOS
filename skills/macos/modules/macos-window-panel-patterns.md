# macOS Window And Panel Patterns

## When To Use

Use for `NSWindow`, `NSPanel`, floating utilities, nonactivating panels,
desktop overlays, window levels, collection behavior, and activation policy.

## When Not To Use

Do not use for in-page layering, web modals, or simple SwiftUI view hierarchy
questions.

## Common Wrong Web Mental Model

"Use z-index to keep the view above everything."

## Correct Native macOS Pattern

Use the right window class and level: normal windows for documents, `NSPanel`
for utility/floating surfaces, and explicit collection behavior for spaces,
full-screen, and multi-display behavior.

## Minimal Code Pattern

```swift
let panel = NSPanel(
    contentRect: rect,
    styleMask: [.nonactivatingPanel, .borderless],
    backing: .buffered,
    defer: false
)
panel.level = .floating
panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
```

## Validation Notes

Test activation, focus, spaces/full-screen behavior, and whether the panel traps
clicks unexpectedly.

## Related Modules

- `macos-screen-geometry-patterns.md`
- `macos-menu-bar-patterns.md`

## Donor Provenance Pointer

Split from `macos-patterns/SKILL.md` at donor commit
`a60365ae85bfc3d1f2f8b260b080d77bfb2f3ec0`.
