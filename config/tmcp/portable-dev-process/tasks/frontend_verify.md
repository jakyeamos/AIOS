# Task: Frontend Verify

Task ID: `@task:frontend_verify`

## Trigger

Use for browser verification, UI changes, screenshots, visual regressions, interactive frontend behavior, responsive layout, or dev server smoke checks.

## Required Modules

- `@module:frontend_runtime`
- `@module:quality_gate`

## Instructions

1. Discover the app framework and dev command.
2. Start or reuse a dev server only when the app needs one.
3. Verify the actual changed route or interaction in a browser-capable tool when available.
4. Check desktop and mobile-sized viewports for layout overlap, blank states, and broken assets.
5. Pair visual verification with relevant lint/type/build checks when code changed.

## Exit

Exit with URL, verified paths, evidence gathered, and unresolved UI risks.

