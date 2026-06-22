# Module: Command Discovery

Module ID: `@module:command_discovery`

Discover commands from authoritative local sources in this order:

1. Agent instructions and project docs.
2. Package metadata and lockfiles.
3. Task runners such as Make, Just, Turbo, tox, nox, Cargo, Gradle, or Xcode schemes.
4. CI configuration.
5. Existing scripts and test conventions.

Prefer the project package manager. For JavaScript, infer from lockfiles and instructions; do not mix package managers casually.

Output command candidates with confidence and whether each command is read-only, mutating, networked, or expensive.

