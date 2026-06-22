# Module: Hook Guidance

Module ID: `@module:hook_guidance`

Portable hook candidates:

- pre-commit: format, lint, typecheck, focused tests, secret scan
- pre-push: broader tests, build, architecture checks
- commit-msg: conventional or project-specific message shape
- post-checkout/post-merge: dependency freshness reminder

Hooks should be repo-local, documented, bypassable only through the host repo's policy, and fast enough for the lifecycle event. Do not install hooks without explicit user request.

