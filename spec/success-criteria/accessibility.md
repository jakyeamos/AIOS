---
id: accessibility
title: Accessibility Gate
scope: domain-specific
blocking: false
evaluation_method: heuristic
version: 1.0
---

## Intent

Ensure UI changes remain keyboard-operable, perceivable, understandable, and compatible with assistive technology.

## Applies When

Any task that changes user-facing UI, forms, navigation, dialogs, controls, dashboards, charts, or interactive states.

## Required Checks

- Keyboard navigation works for interactive controls.
- Focus states are visible and focus is trapped/restored for dialogs.
- Buttons, inputs, and icon controls have accessible labels.
- Color contrast is acceptable.
- Error messages and important state changes are announced when relevant.
- Clickable elements use semantic controls.

## Blockers

- Core workflow cannot be completed with keyboard controls.
- Critical control lacks an accessible name.
- Dialog or modal traps users or loses focus.
- Important error state is invisible to assistive technology.

## Warnings

- Non-core UI has incomplete accessibility evidence.
- Contrast or labeling needs follow-up.
- Chart or visualization needs a richer text alternative.

## Evidence To Provide

- Keyboard result.
- Screen reader label coverage.
- Focus behavior.
- Contrast concerns.
- Remaining accessibility risk.

## Related Criteria

- `thin-display`
- `performance-budget`
- `product-alignment`

## Example Good

A modal form uses semantic controls, labeled icon buttons, visible focus states, and returns focus to the opener.

## Example Bad

A clickable `div` opens a destructive action without keyboard support or a label.
