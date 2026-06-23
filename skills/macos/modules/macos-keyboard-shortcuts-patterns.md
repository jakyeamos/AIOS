# macOS Keyboard Shortcuts Patterns

## When To Use

Use for app commands, menu shortcuts, local event monitors, and global hotkeys.

## When Not To Use

Do not use for text input handling, web keydown-only handlers, or accessibility
automation.

## Common Wrong Web Mental Model

"A global shortcut is just a window-level keydown listener."

## Correct Native macOS Pattern

Prefer menu command shortcuts for app-scoped actions. Use event monitors for
local behavior and a dedicated hotkey mechanism only when a true global shortcut
is required.

## Minimal Code Pattern

```swift
Commands {
    CommandMenu("Bidcamp") {
        Button("Capture") { capture() }
            .keyboardShortcut("k", modifiers: [.command, .shift])
    }
}
```

## Validation Notes

Check conflicts with system shortcuts, focus behavior, cleanup of monitors, and
permission prompts for global behavior.

## Related Modules

- `macos-menu-bar-patterns.md`
- `macos-window-panel-patterns.md`

## Donor Provenance Pointer

Split from `macos-patterns/SKILL.md` at donor commit
`a60365ae85bfc3d1f2f8b260b080d77bfb2f3ec0`.
