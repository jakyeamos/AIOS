# Quick Task 260623: Operating Language Skill Summary

Added a project-vendored `operating-language` skill and root `OPERATING_LANGUAGE.md`.

The skill defines how agents should extract and maintain domain language, architecture language, and agent-control leading words. The new operating-language artifact makes AIOS vocabulary explicit across project truth, context packets, workflow governance, skill routing, quality gates, operator surfaces, and closeout behavior.

`config/workflows/skills.json` now exposes the skill as a candidate registry entry with source metadata for AIOS routing and inspection.
