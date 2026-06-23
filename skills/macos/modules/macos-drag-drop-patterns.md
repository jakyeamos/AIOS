# macOS Drag And Drop Patterns

## When To Use

Use for dragging files, URLs, text, images, promised files, and drop targets in
native macOS views.

## When Not To Use

Do not use for pasteboard-only operations, web drag events, or simple reorder
controls that never cross an app boundary.

## Common Wrong Web Mental Model

"Drag and drop is a DOM event with arbitrary JSON payloads."

## Correct Native macOS Pattern

Use `NSItemProvider`, pasteboard types, SwiftUI `.onDrop`, or AppKit dragging
APIs based on the surface. Model file URL drops explicitly.

## Minimal Code Pattern

```swift
.onDrop(of: [.fileURL], isTargeted: $isTargeted) { providers in
    handleProviders(providers)
    return true
}
```

## Validation Notes

Test drops from Finder, cancellation, multiple files, unsupported types, and
sandbox access.

## Related Modules

- `macos-pasteboard-patterns.md`
- `macos-file-picker-patterns.md`

## Donor Provenance Pointer

Split from `macos-patterns/SKILL.md` at donor commit
`a60365ae85bfc3d1f2f8b260b080d77bfb2f3ec0`.
