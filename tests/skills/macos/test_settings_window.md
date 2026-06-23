# macOS Settings Window Behavior Tests

## Case: New Settings Window

Given project detection reports a native macOS app with no existing settings
architecture.

When `macos-settings-window` runs.

Then it selects the project lifecycle style, adds a minimal settings window
implementation, prevents duplicate windows, and runs build verification.

## Case: Repair Existing Settings

Given existing settings files, `NSWindowController`, or SwiftUI `Settings`
scene are present.

When the user asks to repair settings.

Then the skill extends the existing architecture and does not replace it without
explicit approval.

## Case: Menu-Bar Activation Behavior

Given a menu-bar utility uses hidden dock or accessory activation policy.

When settings are opened.

Then the skill checks app activation behavior and verifies the settings window
can appear and focus without permanently changing the intended policy.

## Case: macOS 26 Unavailable Fallback

Given the deployment target is below macOS 26.

When settings UI uses macOS 26-only visual APIs.

Then the skill requires availability guards or fallback styling and does not
raise the deployment target just for the effect.
