# macOS File Picker Patterns

## When To Use

Use for open panels, save panels, directory selection, import, export, and
security-scoped file access.

## When Not To Use

Do not use for web file inputs, internal app navigation, or Finder reveal/open
actions.

## Common Wrong Web Mental Model

"File access is a browser upload input."

## Correct Native macOS Pattern

Use `NSOpenPanel` and `NSSavePanel`, configure allowed content types and
directory/file selection, and respect sandbox/security-scoped access.

## Minimal Code Pattern

```swift
let panel = NSOpenPanel()
panel.canChooseFiles = true
panel.canChooseDirectories = false
panel.allowsMultipleSelection = false
if panel.runModal() == .OK {
    let url = panel.url
}
```

## Validation Notes

Validate sandbox behavior, file type filters, cancellation, and bookmark or
security-scoped access when persistence is needed.

## Related Modules

- `macos-quicklook-workspace-patterns.md`
- `macos-drag-drop-patterns.md`

## Donor Provenance Pointer

Split from `macos-patterns/SKILL.md` at donor commit
`a60365ae85bfc3d1f2f8b260b080d77bfb2f3ec0`.
