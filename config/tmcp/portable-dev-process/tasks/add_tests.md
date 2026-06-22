# Task: Add Tests

Task ID: `@task:add_tests`

## Trigger

Use when the user asks for tests, coverage, regression protection, test planning, or validation hardening.

## Required Modules

- `@module:command_discovery`
- `@module:test_authoring`

## Instructions

1. Discover existing test style and fixtures before writing new tests.
2. Prefer behavior-level assertions over implementation details.
3. Add focused tests near the changed surface.
4. Keep fixture setup minimal and deterministic.
5. Run the narrow new test, then any broader relevant gate.

## Exit

Exit with test coverage added, commands run, and remaining test gaps.

