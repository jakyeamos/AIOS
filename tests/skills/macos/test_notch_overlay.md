# macOS Notch Overlay Behavior Tests

## Case: Notch Mac

Given a built-in notched display is available.

When `macos-notch-overlay` runs.

Then it positions from `screen.frame`, detects safe-area/notch evidence, and
uses guarded `NSPanel` behavior when an overlay is required.

## Case: Non-Notch Mac

Given no notch evidence exists.

When the skill runs.

Then it uses a top-center fallback or disables the overlay for that display
instead of assuming notch geometry.

## Case: External Monitor

Given a notched Mac is connected to an external display.

When the overlay target is external.

Then the skill verifies display-specific geometry and does not reuse built-in
notch coordinates blindly.

## Case: Click-Through Overlay

Given the overlay requests click-through behavior or high window levels.

When implementation starts.

Then the skill requires explicit approval and documents the interaction risk.

## Case: Incorrect visibleFrame Usage

Given notch positioning uses `visibleFrame`.

When validation runs.

Then the skill reports incorrect geometry and recommends `screen.frame` unless
the design intentionally excludes menu bar/dock areas.
