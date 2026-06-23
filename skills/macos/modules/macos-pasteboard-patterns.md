# macOS Pasteboard Patterns

## When To Use

Use for copy, paste, clipboard history, system pasteboard integration, file URL
paste, and typed pasteboard content.

## When Not To Use

Do not use for internal state transfer, drag/drop sessions, or web-only
clipboard APIs.

## Common Wrong Web Mental Model

"Use `navigator.clipboard`."

## Correct Native macOS Pattern

Use `NSPasteboard.general`, declare content types, clear before writing, and
handle multiple representations when needed.

## Minimal Code Pattern

```swift
let pasteboard = NSPasteboard.general
pasteboard.clearContents()
pasteboard.setString(text, forType: .string)
```

## Validation Notes

Verify paste into native apps, multiple content types, privacy expectations, and
failure behavior when content is unavailable.

## Related Modules

- `macos-drag-drop-patterns.md`
- `macos-file-picker-patterns.md`

## Donor Provenance Pointer

Split from `macos-patterns/SKILL.md` at donor commit
`a60365ae85bfc3d1f2f8b260b080d77bfb2f3ec0`.
