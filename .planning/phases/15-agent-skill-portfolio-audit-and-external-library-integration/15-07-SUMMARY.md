# Plan 15-07 Summary: Canonical Write-A-Skill Workflow

## Outcome

Created `docs/phase-15-skill-authoring-comparison.md` and the canonical global skill at `/Users/jakyeamos/.claude/skills/write-a-skill/SKILL.md`.

The canonical skill is an intent-specific authoring route for creating, improving, reviewing, or extracting skills from repeated workflows.

## Evidence

- The comparison matrix covers the local/plugin skill-authoring sources discovered in Plan 15-01 and records strengths, missing pieces, overlapping pieces, and merge target.
- The canonical skill includes concise SKILL.md/frontmatter structure, trigger-rich descriptions, progressive disclosure, reference-file routing, script guidance, example discipline, and the always-loaded-vs-intent-specific rule requested by the user.
- Existing plugin/cache skill-authoring files were not modified or retired.

## Verification

- `node /Users/jakyeamos/.claude/get-shit-done/bin/gsd-tools.cjs verify artifacts .planning/phases/15-agent-skill-portfolio-audit-and-external-library-integration/15-07-PLAN.md` passed.
- `node /Users/jakyeamos/.claude/get-shit-done/bin/gsd-tools.cjs verify references .planning/phases/15-agent-skill-portfolio-audit-and-external-library-integration/15-07-PLAN.md` passed.
- `node /Users/jakyeamos/.claude/get-shit-done/bin/gsd-tools.cjs verify key-links .planning/phases/15-agent-skill-portfolio-audit-and-external-library-integration/15-07-PLAN.md` passed.
- `rg` confirmed required skill authoring concepts in the canonical skill and comparison matrix.
- `git diff --check` passed.

## Notes

- Plan 15-07 was marked `autonomous: false`; the earlier user instruction to "accept all" was treated as approval to proceed after creating the comparison matrix.
- The global skill file is outside the AIOS git repository; this repo records the comparison matrix, plan contract, summary, and planning truth updates.
