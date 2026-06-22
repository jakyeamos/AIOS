# Module: Quality Gate

Module ID: `@module:quality_gate`

Run the narrowest meaningful gate first, then broaden when the touched surface justifies it. Typical gates include lint, typecheck, tests, build, architecture checks, smoke checks, and browser verification.

When a command fails, preserve:

- command
- working directory
- exit status
- first meaningful error
- likely owner
- next action

Do not claim completion if a blocker-level gate failed unless the user explicitly accepts the tradeoff.

