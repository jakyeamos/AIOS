# macOS Quick Look And Workspace Patterns

## When To Use

Use for file preview, reveal in Finder, open with default app, app launching,
URLs, and `NSWorkspace` integration.

## When Not To Use

Do not use for file picking, internal preview widgets, or web link routing.

## Common Wrong Web Mental Model

"Opening or previewing a file is just setting `window.location`."

## Correct Native macOS Pattern

Use Quick Look for previews and `NSWorkspace.shared` for Finder reveal, opening
files, URLs, and app interactions.

## Minimal Code Pattern

```swift
NSWorkspace.shared.activateFileViewerSelecting([url])
NSWorkspace.shared.open(url)
```

## Validation Notes

Verify sandbox access, missing-file behavior, user default app handling, and
Finder reveal on external volumes.

## Related Modules

- `macos-file-picker-patterns.md`
- `macos-screen-geometry-patterns.md`

## Donor Provenance Pointer

Split from `macos-patterns/SKILL.md` at donor commit
`a60365ae85bfc3d1f2f8b260b080d77bfb2f3ec0`.
