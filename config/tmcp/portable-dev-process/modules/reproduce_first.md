# Module: Reproduce First

Module ID: `@module:reproduce_first`

For debugging, observe the failure before changing code. If exact reproduction is impossible, state why and choose the closest representative input.

Prefer direct execution of the failing function, route, command, or UI path. Use mocks only when the real dependency is unavailable or unsafe.

After a fix, rerun the failing path and the smallest regression check that covers it.

