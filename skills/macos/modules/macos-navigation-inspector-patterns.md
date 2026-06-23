# macOS Navigation And Inspector Patterns

## When To Use

Use for sidebars, split views, inspectors, settings/detail panes, and
master-detail native macOS layouts.

## When Not To Use

Do not use for marketing pages, mobile tab bars, or web-only routing.

## Common Wrong Web Mental Model

"A sidebar is just a responsive drawer."

## Correct Native macOS Pattern

Use `NavigationSplitView` for SwiftUI-native split navigation or AppKit split
views where existing architecture requires it. Use inspectors for contextual
detail rather than modal overload.

## Minimal Code Pattern

```swift
NavigationSplitView {
    List(selection: $selection) { itemsView }
} detail: {
    DetailView(selection: selection)
}
```

## Validation Notes

Verify keyboard navigation, selection persistence, window resizing, and whether
the inspector can be hidden or detached as expected.

## Related Modules

- `macos-userdefaults-appstorage-patterns.md`
- `macos-window-panel-patterns.md`

## Donor Provenance Pointer

Split from `macos-patterns/SKILL.md` at donor commit
`a60365ae85bfc3d1f2f8b260b080d77bfb2f3ec0`.
