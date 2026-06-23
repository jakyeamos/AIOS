# macOS Menu Bar Patterns

## When To Use

Use for menu bar apps, status items, popovers, `MenuBarExtra`, `NSStatusItem`,
and apps that live primarily outside a normal dock window.

## When Not To Use

Do not use for ordinary document windows, floating overlays, or web navigation
menus.

## Common Wrong Web Mental Model

"A menu bar app is a fixed header or nav component."

## Correct Native macOS Pattern

Use `MenuBarExtra` for simple SwiftUI menu bar apps, or `NSStatusItem` plus
`NSPopover` when AppKit lifecycle control, custom windows, or activation policy
handling is required.

## Minimal Code Pattern

```swift
MenuBarExtra("Bidcamp", systemImage: "hammer") {
    Button("Open") { openMainWindow() }
    Divider()
    Button("Quit") { NSApp.terminate(nil) }
}
```

## Validation Notes

Verify the app runs without an unexpected dock icon when configured as a
menu-bar utility. Check activation policy and popover dismissal behavior.

## Related Modules

- `macos-window-panel-patterns.md`
- `macos-launch-login-patterns.md`

## Donor Provenance Pointer

Adapted from `macos-patterns/SKILL.md` at donor commit
`a60365ae85bfc3d1f2f8b260b080d77bfb2f3ec0`.
