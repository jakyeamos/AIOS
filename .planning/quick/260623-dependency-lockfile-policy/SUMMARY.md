# Quick Task 260623: Dependency And Lockfile Policy Summary

Added Rule 13 to `config/agent-rules.md` and mirrored it in `AGENTS.md`.

The rule makes committed package metadata authoritative over `node_modules`, prevents accidental package-manager migration or duplicate lockfiles, and treats missing frontend behavior-test tooling as a blocker when acceptance criteria require that coverage.

`PROJECT.md` now records the new dependency and lockfile authority rule as current AIOS truth.
