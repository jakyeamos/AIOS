# Plan 15-02 Summary: Interrogate Skill Upgrade

## Outcome

Created the global interrogate skill at `/Users/jakyeamos/.claude/skills/interrogate/SKILL.md`.

The new skill is intent-specific, not always-loaded. It is triggered for plan review, PRD authoring, design sessions, ambiguous requirements, architecture decisions, unfamiliar codebase exploration, and terminology/domain-model uncertainty.

## Evidence

- No global `interrogate` skill existed in the Plan 15-01 inventory.
- The nearest local equivalent, `/Users/jakyeamos/.claude/skills/terrace-interrogate/SKILL.md`, was read before creating the global skill.
- The new skill references the Plan 15-01 backup path: `/Users/jakyeamos/.claude/skills-backup-20260623-130623/terrace-interrogate/SKILL.md`.
- The skill includes all six grill-with-docs behaviors: code-first clarification, repo-language challenge, glossary maintenance, ADR discipline, fuzzy-term sharpening, and user-claim verification.
- The skill preserves one-focused-question discipline and directs explicit Terrace workflows back to `terrace-interrogate`.

## Verification

- `node /Users/jakyeamos/.claude/get-shit-done/bin/gsd-tools.cjs verify artifacts .planning/phases/15-agent-skill-portfolio-audit-and-external-library-integration/15-02-PLAN.md` passed.
- `node /Users/jakyeamos/.claude/get-shit-done/bin/gsd-tools.cjs verify references .planning/phases/15-agent-skill-portfolio-audit-and-external-library-integration/15-02-PLAN.md` passed.
- `node /Users/jakyeamos/.claude/get-shit-done/bin/gsd-tools.cjs verify key-links .planning/phases/15-agent-skill-portfolio-audit-and-external-library-integration/15-02-PLAN.md` passed.
- `rg` confirmed the new skill contains the required backup reference, intent-specific pointer, one-question rule, and all six behavior labels.
- `git diff --check` passed.

## Notes

- The skill file is outside the AIOS git repository, so the repository commit records the plan contract, summary, and planning truth updates. The global skill itself remains in the user-level Claude skill directory.
