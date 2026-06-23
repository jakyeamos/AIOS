---
name: macos-notch-overlay
version: 0.1.0
description: Add or repair a guarded macOS notch overlay with safe notch detection, non-notch fallback, panel/window-level warnings, click-through handling, and manual verification.
source:
  donor: fayazara/macos-app-skills
  donor_commit: a60365ae85bfc3d1f2f8b260b080d77bfb2f3ec0
  source_files:
    - notch-ui/SKILL.md
    - notch-ui/references/NotchWindow.swift
    - notch-ui/references/NotchShape.swift
  transformation_type: adapted
always_loaded: false
intent_pointer: macOS notch overlay implementation only
depends_on:
  - skills/macos/project-detection/SKILL.md
  - skills/macos/build-verify/SKILL.md
  - skills/macos/modules/macos-window-panel-patterns.md
  - skills/macos/modules/macos-screen-geometry-patterns.md
---

# macOS Notch Overlay

Use this skill when the user explicitly asks for a notch-aware overlay,
Dynamic-Island-like macOS UI, or display-top floating panel.

Do not use for ordinary popovers, menu bar extras, document windows, or web
overlays.

## Required Preflight

1. Invoke `macos-project-detection`.
2. Confirm the request is explicitly for notch/top-display overlay behavior.
3. Detect existing overlay/window/panel architecture.
4. Load only the window/panel and screen-geometry modules.
5. Identify target display behavior: built-in display only, active display,
   all displays, or external display fallback.

## Safety Gates

Require explicit approval before:

- using high window levels above `.floating`
- enabling click-through behavior
- joining all spaces or full-screen auxiliary spaces
- hiding normal activation/focus behavior
- adding global event monitors

## Implementation Guidance

- Detect notch availability safely through screen safe-area evidence and provide
  a non-notch fallback.
- Use `NSPanel` for overlay/floating utility behavior when AppKit control is
  needed; use `NSWindow` only for normal window behavior.
- Use `screen.frame` when positioning relative to the physical notch/top edge.
  Do not use `visibleFrame` for notch geometry unless intentionally excluding
  menu bar/dock areas.
- Handle external displays without notches by using a pill/top-center fallback
  or disabling the overlay on that display.
- Respect reduced motion and avoid mandatory animations.
- Keep overlays dismissible and non-intrusive by default.

## Validation

Run `macos-build-verify` after implementation. Manual validation should check:

- Notch Mac built-in display.
- Non-notch Mac fallback.
- External monitor behavior.
- Click-through and focus behavior.
- Multi-monitor movement.
- Reduced-motion setting.

## Repair Recommendations

- Overlay appears in wrong place: inspect `screen.frame` vs `visibleFrame` and
  coordinate conversion.
- Overlay steals focus: review `NSPanel` style masks and activation policy.
- Overlay is intrusive: lower window level, disable click-through, or add an
  explicit toggle.
- Non-notch display breaks layout: use fallback geometry or disable the overlay.
