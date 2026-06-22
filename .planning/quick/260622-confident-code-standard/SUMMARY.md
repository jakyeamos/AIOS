# Quick Task 260622: Add Confident Code Standard

## Result

Added a maintainability standard requiring agents to update existing contracts, names, call sites, and tests when a feature expands an implicit default into multiple variants.

The standard now explicitly calls out the notification example: when `Notification` implicitly means email and SMS is added, prefer an explicit discriminator or equivalent existing local pattern, and rename stale email-only generic APIs such as `sendNotification()`.

Extended the same standard with an event-loop confidence rule: agents should not register response handlers before sending messages merely to guard against impossible races. Handler-before-send ordering must have a real runtime reason such as synchronous reentrancy, callback behavior, replay buffering, or a documented platform guarantee that requires it.

## Verification

- Passed after both confident-code cases: `pnpm context:validate`
