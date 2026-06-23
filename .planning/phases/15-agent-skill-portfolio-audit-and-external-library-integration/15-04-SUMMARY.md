# Plan 15-04 Summary: Simplifier Architecture Review Skill

## Outcome

Created the global simplifier skill at `/Users/jakyeamos/.claude/skills/simplifier/SKILL.md`.

The skill is an intent-specific architecture review route for code review, refactoring, codebase cleanup, improving modules, complexity complaints, and diagnose architecture handoffs.

## Evidence

- No global `simplifier` skill existed before this plan.
- Read nearby architecture/audit/map-codebase skills before writing: `gsd-map-codebase`, `gsd-audit-fix`, `terrace-design`, and the newly created `diagnose` handoff.
- The skill defines all nine lenses: deep modules, shallow modules, deletion test, interface as test surface, seams, adapters, locality, leverage, and AI navigability.
- The skill requires a written architecture review report before refactors touching more than three files or moving/removing more than 50 lines.
- The report template includes candidate name, files involved, current friction, proposed simplification or deepening, expected test improvement, risk, confidence, and user approval.
- The skill explicitly treats deepening as a valid simplification outcome and rejects line-count-only cleanup.

## Verification

- `node /Users/jakyeamos/.claude/get-shit-done/bin/gsd-tools.cjs verify artifacts .planning/phases/15-agent-skill-portfolio-audit-and-external-library-integration/15-04-PLAN.md` passed.
- `node /Users/jakyeamos/.claude/get-shit-done/bin/gsd-tools.cjs verify references .planning/phases/15-agent-skill-portfolio-audit-and-external-library-integration/15-04-PLAN.md` passed.
- `node /Users/jakyeamos/.claude/get-shit-done/bin/gsd-tools.cjs verify key-links .planning/phases/15-agent-skill-portfolio-audit-and-external-library-integration/15-04-PLAN.md` passed.
- `rg` confirmed the report-first section, architecture handoff marker, user approval field, deepening language, and all nine lens labels exist in the global skill.

## Notes

- The global skill file is outside the AIOS git repository; this repo records the plan contract, summary, and planning truth updates.
